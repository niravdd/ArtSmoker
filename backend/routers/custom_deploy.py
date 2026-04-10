"""Custom Model Deployment API — manage self-hosted 3rd-party models.

Endpoints for browsing the catalog, downloading, deploying, and managing
custom models on Amazon SageMaker in the user's AWS account.

HuggingFace models: the Amazon SageMaker container pulls weights directly
from HuggingFace at startup (no local download or S3 upload of weights).
For gated models, the HF token is stored encrypted in AWS Secrets Manager
and automatically cleaned up when the model is torn down.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/custom-models", tags=["custom-models"])


# ── Catalog ───────────────────────────────────────────────────────────────

@router.get("/catalog")
def list_catalog():
    """List all available custom models with deployment status.

    Sync (not async) so boto3 calls don't block the event loop.
    FastAPI runs sync endpoints in a threadpool automatically.

    Only checks Amazon SageMaker status for models that are registered in the
    model registry (i.e., previously deployed). Undeployed models skip
    the status check — much faster.
    """
    from backend.services.custom_models import get_catalog
    from backend.services.model_registry import get_registry
    from backend.services.sagemaker_deployer import check_endpoint_status

    catalog = dict(get_catalog())  # Copy built-in catalog
    # Merge user-added models
    user_catalog = _load_user_catalog()
    for key, entry in user_catalog.items():
        if not key.startswith("_"):
            catalog[key] = {**entry, "_user_added": True}
    registry = get_registry()
    result = []

    # Build set of deployed custom model keys from registry
    deployed_keys = set()
    for section in ("image_models", "video_models", "post_processing", "utility_models"):
        for key, cfg in registry.get(section, {}).items():
            if cfg.get("model_source") == "custom_hosted":
                deployed_keys.add(key)

    # Also check in-progress deployments
    for key in _deploy_status:
        if _deploy_status[key].get("stage") in ("preparing", "downloading", "uploading", "deploying"):
            deployed_keys.add(key)

    for key, model in catalog.items():
        endpoint_name = f"artsmoker-{key.replace('_', '-')}"

        # Only check Amazon SageMaker for models we know are deployed
        if key in deployed_keys:
            status = check_endpoint_status(endpoint_name)
            deploy_progress = _deploy_status.get(key, {})
        else:
            status = {"status": "NotFound"}
            deploy_progress = _deploy_status.get(key, {})

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
            "warming_up": status.get("warming_up", False),
            "deploy_progress": deploy_progress.get("progress", ""),
            "deploy_stage": deploy_progress.get("stage", ""),
            "endpoint_name": endpoint_name if status.get("status") != "NotFound" else None,
            "user_added": model.get("_user_added", False),
            "bundle": _get_bundle_info(key),
            "warm_up_info": {
                "cold_start_minutes": "5-10" if model.get("requirements", {}).get("min_vram_gb", 0) > 12 else "3-5",
                "inference_seconds": model.get("invoke", {}).get("typical_latency_seconds", "?"),
                "idle_timeout": "~15 min before scaling to zero (async)",
            },
        })

    return {"models": result, "bundles": _get_all_bundles_info()}


def _get_bundle_info(model_key: str) -> dict | None:
    from backend.services.custom_models import get_bundle_for_model, get_bundle
    bundle_key = get_bundle_for_model(model_key)
    if not bundle_key:
        return None
    bundle = get_bundle(bundle_key)
    return {
        "key": bundle_key,
        "label": bundle["label"],
        "shared_with": [m for m in bundle["models"] if m != model_key],
    }


def _get_all_bundles_info() -> list:
    from backend.services.custom_models import get_all_bundles
    result = []
    for key, bundle in get_all_bundles().items():
        result.append({
            "key": key,
            "label": bundle["label"],
            "description": bundle["description"],
            "models": bundle["models"],
            "instance": bundle["recommended_instance"],
        })
    return result


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
    hf_token: str | None = None  # For gated models — stored encrypted in Secrets Manager


_deploy_status: dict = {}  # model_key → {"stage": str, "progress": str, "error": str}


@router.post("/deploy")
async def deploy_model(body: DeployRequest):
    """Start deploying a model in a background thread.

    Returns immediately with a status. Frontend polls /deploy-status/{key} for progress.

    For HuggingFace models: uploads only the inference handler to S3, then creates
    the Amazon SageMaker endpoint. The container pulls model weights directly from
    HuggingFace at startup (no local download of multi-GB weights).

    For gated models: a single shared HF token is stored encrypted in AWS
    Secrets Manager (not as a plain-text env var). If a token already exists
    from a previous deployment, it's reused automatically — no need to ask
    the user again. If the token fails, the user is prompted for a new one.

    For non-HuggingFace models: downloads weights locally, uploads to S3,
    then creates the endpoint.
    """
    from backend.services.custom_models import get_catalog_model
    from backend.services.sagemaker_deployer import has_hf_token

    model = get_catalog_model(body.model_key)
    if not model:
        raise HTTPException(404, detail=f"Unknown model: {body.model_key}")

    # Smart token flow: only ask for token if gated AND no token stored yet
    if model.get("requires_hf_auth") and not body.hf_token and not has_hf_token():
        raise HTTPException(400, detail={
            "error": "hf_auth_required",
            "message": "This model requires HuggingFace authentication.",
            "license_url": model.get("hf_license_url", ""),
            "instructions": (
                "1. Visit the license URL and accept the terms\n"
                "2. Go to huggingface.co/settings/tokens → create a Read-only token\n"
                "3. Provide the token in the deployment dialog\n"
                "A Read-only token is sufficient. Your token is stored encrypted in AWS Secrets Manager\n"
                "in your account and reused for all gated models. You can remove it anytime."
            ),
        })

    # Run deployment in background thread — return immediately
    import threading

    def _run_deploy():
        key = body.model_key
        source_type = model.get("source", {}).get("type", "")

        try:
            if source_type == "huggingface":
                # ── HuggingFace direct pull: no local download ──────────────
                # Upload only the inference handler to S3 (a few KB).
                # The Amazon SageMaker container will pull model weights
                # directly from HuggingFace at startup via HF_MODEL_ID.
                from backend.services.sagemaker_deployer import upload_handler_to_s3, deploy_endpoint

                _deploy_status[key] = {
                    "stage": "preparing",
                    "progress": "Uploading inference handler to S3...",
                    "error": "",
                }
                upload_handler_to_s3(key)

                _deploy_status[key] = {
                    "stage": "deploying",
                    "progress": "Creating Amazon SageMaker endpoint (container will pull model from HuggingFace)...",
                    "error": "",
                }
                deployment = deploy_endpoint(
                    key,
                    endpoint_type=body.endpoint_type,
                    instance_type=body.instance_type,
                    hf_token=body.hf_token,  # Stored in Secrets Manager, not plain-text env var
                )

                _register_custom_model(key, model, deployment)
                _deploy_status[key] = {
                    "stage": "complete",
                    "progress": (
                        "Endpoint created — container is pulling model from HuggingFace and starting up. "
                        "This typically takes 5-15 min depending on model size."
                    ),
                    "error": "",
                }

            else:
                # ── Non-HuggingFace: download locally → upload to S3 ────────
                from backend.services.sagemaker_deployer import download_model, upload_to_s3, deploy_endpoint
                import shutil

                _deploy_status[key] = {
                    "stage": "downloading",
                    "progress": f"Downloading {model['label']} weights...",
                    "error": "",
                }

                def _update_progress(msg):
                    _deploy_status[key]["progress"] = msg

                local_dir = download_model(key, progress_callback=_update_progress)
                try:
                    _deploy_status[key] = {"stage": "uploading", "progress": "Uploading to S3...", "error": ""}
                    upload_to_s3(local_dir, key, progress_callback=_update_progress)

                    _deploy_status[key] = {
                        "stage": "deploying",
                        "progress": "Creating Amazon SageMaker endpoint...",
                        "error": "",
                    }
                    deployment = deploy_endpoint(key, endpoint_type=body.endpoint_type, instance_type=body.instance_type)

                    _register_custom_model(key, model, deployment)
                    _deploy_status[key] = {
                        "stage": "complete",
                        "progress": "Endpoint created — waiting for it to become active (5-10 min).",
                        "error": "",
                    }
                finally:
                    shutil.rmtree(local_dir, ignore_errors=True)

        except Exception as exc:
            logger.exception("Custom model deployment failed: %s", key)
            error_msg = str(exc)
            # Provide user-friendly guidance for common errors
            if "403" in error_msg or "not in the authorized list" in error_msg:
                license_url = model.get("hf_license_url", f"https://huggingface.co/{model.get('source', {}).get('repo_id', '')}")
                error_msg = (
                    f"Access denied. You need to accept the model's license on HuggingFace first.\n\n"
                    f"1. Visit {license_url}\n"
                    f"2. Click 'Accept' on the license agreement\n"
                    f"3. Come back and try deploying again\n\n"
                    f"If you already accepted the license, your stored token may be invalid or expired. "
                    f"Try deploying again with a fresh token."
                )
            elif "401" in error_msg or "Unauthorized" in error_msg:
                error_msg = (
                    "Invalid or expired HuggingFace token. "
                    "Please deploy again with a fresh token from huggingface.co/settings/tokens."
                )
            elif "404" in error_msg:
                error_msg = "Model repository not found. Please verify the model URL is correct."
            elif "secretsmanager" in error_msg.lower() or "AccessDeniedException" in error_msg:
                error_msg = (
                    "Could not store HuggingFace token in AWS Secrets Manager. "
                    "Ensure your IAM role has secretsmanager:CreateSecret and secretsmanager:PutSecretValue permissions."
                )
            _deploy_status[key] = {"stage": "failed", "progress": "", "error": error_msg}

    thread = threading.Thread(target=_run_deploy, daemon=True)
    thread.start()

    return {
        "status": "started",
        "model_key": body.model_key,
        "label": model["label"],
        "message": "Deployment started in background. Check status in Custom Models tab.",
    }


@router.get("/deploy-status/{model_key}")
async def get_deploy_progress(model_key: str):
    """Get the current deployment progress for a model being deployed."""
    status = _deploy_status.get(model_key, {"stage": "unknown", "progress": "", "error": ""})
    return status


# ── Status & Management ───────────────────────────────────────────────────

@router.get("/status/{model_key}")
def check_deployment_status(model_key: str):
    """Check the deployment status of a custom model on Amazon SageMaker."""
    from backend.services.sagemaker_deployer import check_endpoint_status
    endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
    return check_endpoint_status(endpoint_name)


# ── HuggingFace Token Management ─────────────────────────────────────────

@router.get("/hf-token-status")
def check_hf_token_status():
    """Check if a HuggingFace token is stored in Secrets Manager."""
    from backend.services.sagemaker_deployer import has_hf_token, get_hf_token_arn
    stored = has_hf_token()
    return {"stored": stored, "arn": get_hf_token_arn() if stored else None}


class UpdateHfTokenRequest(BaseModel):
    hf_token: str


@router.post("/hf-token")
async def update_hf_token(body: UpdateHfTokenRequest):
    """Store or update the shared HuggingFace token.

    One token is shared across all gated models. Stored encrypted in
    AWS Secrets Manager. Existing deployed models will use the new token
    on their next cold start.
    """
    from backend.services.sagemaker_deployer import store_hf_token
    if not body.hf_token.strip():
        raise HTTPException(400, detail="Token cannot be empty")
    arn = store_hf_token(body.hf_token.strip())
    return {"status": "stored", "arn": arn}


@router.delete("/hf-token")
async def remove_hf_token():
    """Delete the shared HuggingFace token from Secrets Manager.

    Warning: gated models will fail on next cold start without a token.
    """
    from backend.services.sagemaker_deployer import delete_hf_token
    deleted = delete_hf_token()
    return {"status": "deleted" if deleted else "not_found"}


@router.delete("/teardown/{model_key}")
async def teardown_model(model_key: str, delete_s3: bool = False):
    """Delete a deployed custom model endpoint.

    Optionally deletes S3 artifacts (handler code). The model can be
    redeployed later. The shared HF token is NOT deleted (other models may need it).
    """
    from backend.services.sagemaker_deployer import teardown_endpoint

    result = teardown_endpoint(model_key, delete_s3=delete_s3)

    # Remove from model registry
    _unregister_custom_model(model_key)

    return {"status": "deleted", **result}


class RedeployRequest(BaseModel):
    endpoint_type: str = "async"
    instance_type: str | None = None
    hf_token: str | None = None  # For gated models


@router.post("/redeploy/{model_key}")
async def redeploy_model(model_key: str, body: RedeployRequest):
    """Tear down and redeploy a custom model.

    Tears down existing endpoint (including Secrets Manager token),
    then creates a fresh deployment.
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


# ── User-Added Models (Extensibility) ─────────────────────────────────────

class DetectRequest(BaseModel):
    repo_url: str           # HuggingFace URL or repo ID
    hf_token: str | None = None  # For gated repos (transient)


@router.post("/detect")
async def detect_model(body: DetectRequest):
    """Auto-detect model configuration from a HuggingFace repo.

    Inspects repo metadata (config.json, model_index.json, README)
    without downloading weights. Returns a pre-filled catalog entry
    for the user to review before adding.

    hf_token is used for this API call only and NOT stored.
    """
    from backend.services.model_detector import detect_from_hf_repo

    # Normalize URL to repo ID
    repo_id = body.repo_url.strip()
    repo_id = repo_id.rstrip("/")
    if "huggingface.co/" in repo_id:
        repo_id = repo_id.split("huggingface.co/")[-1]
    if repo_id.startswith("https://"):
        repo_id = repo_id.replace("https://", "")

    try:
        entry = detect_from_hf_repo(repo_id, hf_token=body.hf_token)
        return {"status": "detected", "repo_id": repo_id, "entry": entry}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        logger.exception("Model detection failed for %s", repo_id)
        raise HTTPException(502, detail=f"Detection failed: {e}")


class AddModelRequest(BaseModel):
    key: str                # Unique catalog key (e.g., "my_custom_sdxl")
    entry: dict             # Full catalog entry (from detect + user edits)


@router.post("/add")
async def add_user_model(body: AddModelRequest):
    """Add a user-defined model to the custom catalog.

    Saves to custom_models.user.json (gitignored) — survives code updates.
    The model then appears in the Custom Models tab and can be deployed.
    """
    key = body.key.strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        raise HTTPException(400, detail="Model key is required")

    # Validate required fields
    entry = body.entry
    required = ["label", "category", "source", "invoke"]
    missing = [f for f in required if f not in entry]
    if missing:
        raise HTTPException(400, detail=f"Missing required fields: {missing}")

    # Save to user catalog file
    _save_user_model(key, entry)

    return {"status": "added", "key": key, "label": entry.get("label", key)}


@router.delete("/remove-user-model/{model_key}")
async def remove_user_model(model_key: str):
    """Remove a user-added model from the catalog.

    Only removes from the user catalog (custom_models.user.json).
    Built-in catalog models cannot be removed.
    """
    from backend.services.custom_models import MODEL_CATALOG
    if model_key in MODEL_CATALOG:
        raise HTTPException(400, detail="Cannot remove built-in catalog models. Use teardown to remove the deployment.")

    removed = _remove_user_model(model_key)
    if not removed:
        raise HTTPException(404, detail=f"User model '{model_key}' not found")
    return {"status": "removed", "key": model_key}


def _get_user_catalog_path():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent / "custom_models.user.json"


def _load_user_catalog() -> dict:
    import json
    path = _get_user_catalog_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save_user_model(key: str, entry: dict):
    import json
    from datetime import datetime, timezone
    catalog = _load_user_catalog()
    catalog[key] = entry
    catalog["_last_updated"] = datetime.now(timezone.utc).isoformat()
    path = _get_user_catalog_path()
    path.write_text(json.dumps(catalog, indent=2, default=str))
    logger.info("Saved user model '%s' to %s", key, path)


def _remove_user_model(key: str) -> bool:
    import json
    catalog = _load_user_catalog()
    if key in catalog:
        del catalog[key]
        path = _get_user_catalog_path()
        path.write_text(json.dumps(catalog, indent=2, default=str))
        return True
    return False


# ── Registry Integration ──────────────────────────────────────────────────

def _register_custom_model(model_key: str, catalog_entry: dict, deployment: dict):
    """Register a deployed custom model in ArtSmoker's model registry.

    This makes the model appear in the appropriate studio dropdowns.
    """
    from backend.services.model_registry import get_registry, _save

    registry = get_registry()
    category = catalog_entry["category"]

    invoke = catalog_entry.get("invoke", {})

    from backend.services.sagemaker_deployer import _get_region
    deploy_region = _get_region()

    entry = {
        "label": catalog_entry["label"],
        "model_id": f"sagemaker:{deployment['endpoint_name']}",
        "provider": catalog_entry["provider"],
        "region": deploy_region,
        "available_regions": [deploy_region],
        "enabled": True,
        "model_source": "custom_hosted",
        "format_family": f"sagemaker_{deployment['endpoint_type']}",
        "last_updated": catalog_entry.get("last_updated", ""),
        "deployment": {
            "endpoint_name": deployment["endpoint_name"],
            "endpoint_type": deployment["endpoint_type"],
            "instance_type": deployment["instance_type"],
            "created_at": deployment.get("created_at"),
        },
        "base_price_usd": catalog_entry["pricing"].get("estimated_cost_per_image",
                          catalog_entry["pricing"].get("estimated_cost_per_video", 0)),
        "invoke": invoke,  # Full invocation config from catalog
    }

    if category == "image_generation":
        registry.setdefault("image_models", {})[model_key] = {
            **entry,
            "model_purpose": "text_to_image",
            "prompt_limit": invoke.get("max_prompt_length", 2048),
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
