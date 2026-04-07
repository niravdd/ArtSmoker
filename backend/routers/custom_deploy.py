"""Custom Model Deployment API — manage self-hosted 3rd-party models.

Endpoints for browsing the catalog, downloading, deploying, and managing
custom models on SageMaker in the user's AWS account.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/custom-models", tags=["custom-models"])


# ── Catalog ───────────────────────────────────────────────────────────────

@router.get("/catalog")
async def list_catalog():
    """List all available custom models with deployment status."""
    from backend.services.custom_models import get_catalog
    from backend.services.sagemaker_deployer import check_endpoint_status

    catalog = get_catalog()
    result = []

    for key, model in catalog.items():
        endpoint_name = f"artsmoker-{key.replace('_', '-')}"
        status = check_endpoint_status(endpoint_name)

        result.append({
            "key": key,
            "label": model["label"],
            "description": model["description"],
            "category": model["category"],
            "studio": model["studio"],
            "provider": model["provider"],
            "license": model["license"],
            "requires_hf_auth": model.get("requires_hf_auth", False),
            "hf_license_url": model.get("hf_license_url"),
            "version": model.get("version"),
            "last_updated": model.get("last_updated"),
            "requirements": model["requirements"],
            "pricing": model["pricing"],
            "deployment_status": status.get("status", "NotFound"),
            "endpoint_name": endpoint_name if status.get("status") != "NotFound" else None,
        })

    return {"models": result}


@router.get("/catalog/{model_key}")
async def get_catalog_model(model_key: str):
    """Get detailed info for a specific model."""
    from backend.services.custom_models import get_catalog_model as _get
    model = _get(model_key)
    if not model:
        raise HTTPException(404, detail=f"Unknown model: {model_key}")
    return model


# ── Deploy ────────────────────────────────────────────────────────────────

class DeployRequest(BaseModel):
    model_key: str
    endpoint_type: str = "async"  # "async" or "realtime"
    instance_type: str | None = None
    hf_token: str | None = None  # Used once for download, NOT stored


@router.post("/deploy")
async def deploy_model(body: DeployRequest):
    """Download model weights and deploy a SageMaker endpoint.

    For gated models, hf_token is used ONCE to download weights and
    then immediately discarded. It is NEVER stored.

    Steps:
      1. Download weights from source → local temp
      2. Upload to user's S3 bucket
      3. Create SageMaker endpoint (async or realtime)
      4. Register in model registry

    Returns deployment status and endpoint name.
    """
    from backend.services.custom_models import get_catalog_model
    from backend.services.sagemaker_deployer import (
        download_model, upload_to_s3, deploy_endpoint,
    )
    import shutil

    model = get_catalog_model(body.model_key)
    if not model:
        raise HTTPException(404, detail=f"Unknown model: {body.model_key}")

    if model.get("requires_hf_auth") and not body.hf_token:
        raise HTTPException(400, detail={
            "error": "hf_auth_required",
            "message": f"This model requires HuggingFace authentication.",
            "license_url": model.get("hf_license_url", ""),
            "instructions": (
                "1. Visit the license URL and accept the terms\n"
                "2. Get your HuggingFace token from https://huggingface.co/settings/tokens\n"
                "3. Provide the token in the deployment dialog\n"
                "Your token is used once for download and NOT stored."
            ),
        })

    try:
        # Step 1: Download
        logger.info("Deploying %s: downloading weights...", model["label"])
        local_dir = download_model(body.model_key, hf_token=body.hf_token)

        try:
            # Step 2: Upload to S3
            logger.info("Deploying %s: uploading to S3...", model["label"])
            s3_uri = upload_to_s3(local_dir, body.model_key)

            # Step 3: Deploy endpoint
            logger.info("Deploying %s: creating SageMaker endpoint...", model["label"])
            deployment = deploy_endpoint(
                body.model_key,
                endpoint_type=body.endpoint_type,
                instance_type=body.instance_type,
            )

            # Step 4: Register in model registry
            _register_custom_model(body.model_key, model, deployment)

            return {
                "status": "deploying",
                "model_key": body.model_key,
                "label": model["label"],
                "endpoint_name": deployment["endpoint_name"],
                "endpoint_type": body.endpoint_type,
                "instance_type": deployment["instance_type"],
                "s3_uri": s3_uri,
                "message": (
                    f"Deployment started. The endpoint will take 5-10 minutes to become active. "
                    f"Check status in Model Settings → Custom Models."
                ),
            }
        finally:
            # Clean up temp directory (weights are in S3 now)
            shutil.rmtree(local_dir, ignore_errors=True)

    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        logger.exception("Custom model deployment failed: %s", body.model_key)
        raise HTTPException(502, detail=f"Deployment failed: {e}")


# ── Status & Management ───────────────────────────────────────────────────

@router.get("/status/{model_key}")
async def check_deployment_status(model_key: str):
    """Check the deployment status of a custom model."""
    from backend.services.sagemaker_deployer import check_endpoint_status
    endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
    return check_endpoint_status(endpoint_name)


@router.delete("/teardown/{model_key}")
async def teardown_model(model_key: str, delete_s3: bool = False):
    """Delete a deployed custom model endpoint.

    Optionally deletes S3 artifacts (model weights). The model can be
    redeployed later by downloading weights again.
    """
    from backend.services.sagemaker_deployer import teardown_endpoint

    result = teardown_endpoint(model_key, delete_s3=delete_s3)

    # Remove from model registry
    _unregister_custom_model(model_key)

    return {"status": "deleted", **result}


class RedeployRequest(BaseModel):
    endpoint_type: str = "async"
    instance_type: str | None = None
    hf_token: str | None = None  # For re-downloading gated models


@router.post("/redeploy/{model_key}")
async def redeploy_model(model_key: str, body: RedeployRequest):
    """Re-download and redeploy a custom model.

    Tears down existing endpoint, re-downloads latest weights,
    and creates a fresh endpoint. Use for updates/patches.
    """
    from backend.services.sagemaker_deployer import teardown_endpoint

    # Teardown existing
    teardown_endpoint(model_key, delete_s3=True)

    # Re-deploy (reuse the deploy endpoint logic)
    deploy_body = DeployRequest(
        model_key=model_key,
        endpoint_type=body.endpoint_type,
        instance_type=body.instance_type,
        hf_token=body.hf_token,
    )
    return await deploy_model(deploy_body)


# ── Registry Integration ──────────────────────────────────────────────────

def _register_custom_model(model_key: str, catalog_entry: dict, deployment: dict):
    """Register a deployed custom model in ArtSmoker's model registry.

    This makes the model appear in the appropriate studio dropdowns.
    """
    from backend.services.model_registry import get_registry, _save

    registry = get_registry()
    category = catalog_entry["category"]

    entry = {
        "label": catalog_entry["label"],
        "model_id": f"sagemaker:{deployment['endpoint_name']}",
        "provider": catalog_entry["provider"],
        "region": boto3.Session().region_name or "us-west-2",
        "enabled": True,
        "model_source": "custom_hosted",
        "format_family": f"sagemaker_{deployment['endpoint_type']}",
        "deployment": {
            "endpoint_name": deployment["endpoint_name"],
            "endpoint_type": deployment["endpoint_type"],
            "instance_type": deployment["instance_type"],
            "created_at": deployment.get("created_at"),
        },
        "base_price_usd": catalog_entry["pricing"].get("estimated_cost_per_image", 0),
        "invocation": catalog_entry["invocation"],
    }

    if category == "image_generation":
        registry.setdefault("image_models", {})[model_key] = {
            **entry,
            "model_purpose": "text_to_image",
            "prompt_limit": catalog_entry["invocation"].get("max_prompt_length", 2048),
            "moderation_strictness": "none",
        }
    elif category == "post_processing":
        registry.setdefault("post_processing", {})[model_key] = {
            **entry,
            "purpose": model_key,  # e.g., "real_esrgan" → purpose for filtering
        }
    elif category == "video_generation":
        registry.setdefault("video_models", {})[model_key] = entry
    elif category == "utility":
        registry.setdefault("utility_models", {})[model_key] = entry

    _save()
    logger.info("Registered custom model %s in registry (category=%s)", model_key, category)


def _unregister_custom_model(model_key: str):
    """Remove a custom model from the registry."""
    from backend.services.model_registry import get_registry, _save

    registry = get_registry()
    removed = False

    for section in ("image_models", "video_models", "post_processing", "utility_models"):
        if model_key in registry.get(section, {}):
            del registry[section][model_key]
            removed = True

    if removed:
        _save()
        logger.info("Unregistered custom model %s from registry", model_key)


# Need boto3 for _register_custom_model
import boto3
