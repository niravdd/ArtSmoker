"""SageMaker Deployer — handles model download, S3 upload, and endpoint creation.

Lifecycle:
  1. download_model()  — pulls weights from source (GitHub/HuggingFace) to local temp
  2. upload_to_s3()    — uploads weights to user's S3 bucket
  3. deploy_endpoint() — creates SageMaker endpoint (async or real-time)
  4. check_status()    — polls endpoint status
  5. teardown()        — deletes endpoint and optionally S3 artifacts

HuggingFace tokens are accepted as a parameter for gated models,
used once during download, and immediately discarded — never stored.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

# S3 prefix for model weights
S3_MODEL_PREFIX = "artsmoker/custom-models"


def get_deployment_s3_bucket() -> str:
    """Get the S3 bucket for custom model storage.

    Uses the same bucket as video generation (configured in Model Settings).
    Falls back to ARTSMOKER_CUSTOM_MODELS_BUCKET env var.
    """
    from backend.services.model_registry import get_registry
    reg = get_registry()
    # Try video settings bucket first (already configured)
    bucket = reg.get("video_settings", {}).get("s3_bucket", "")
    if bucket:
        return bucket
    return os.environ.get("ARTSMOKER_CUSTOM_MODELS_BUCKET", "")


def download_model(model_key: str, hf_token: str | None = None,
                   progress_callback=None) -> Path:
    """Download model weights from the original source to a local temp directory.

    For HuggingFace repos: uses huggingface_hub to download.
    For GitHub releases: uses direct URL download.

    hf_token is used ONLY for this download and not stored anywhere.

    Returns the local directory containing the downloaded files.
    """
    from backend.services.custom_models import get_catalog_model

    model = get_catalog_model(model_key)
    if not model:
        raise ValueError(f"Unknown model: {model_key}")

    source = model["source"]
    source_type = source["type"]

    if model.get("requires_hf_auth") and not hf_token:
        raise ValueError(
            f"Model '{model['label']}' requires HuggingFace authentication. "
            f"Please accept the license at {model.get('hf_license_url', 'HuggingFace')} "
            f"and provide your HuggingFace token."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix=f"artsmoker_{model_key}_"))

    if source_type == "huggingface":
        _download_hf_model(source["repo_id"], temp_dir, hf_token, progress_callback)
    elif source_type == "github_release":
        _download_github_release(source["url"], temp_dir, progress_callback)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    logger.info("Downloaded %s to %s", model["label"], temp_dir)
    return temp_dir


def _download_hf_model(repo_id: str, dest_dir: Path, token: str | None = None,
                       progress_callback=None):
    """Download a HuggingFace model repo."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        raise RuntimeError(
            "huggingface_hub is required for downloading HuggingFace models. "
            "Install with: pip install huggingface_hub"
        )

    if progress_callback:
        progress_callback(f"Downloading {repo_id} from HuggingFace...")

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest_dir),
        token=token,  # Used for this download only, not stored
        ignore_patterns=["*.md", "*.txt", ".gitattributes"],
    )


def _download_github_release(url: str, dest_dir: Path, progress_callback=None):
    """Download a file from a GitHub release URL."""
    import urllib.request

    filename = url.split("/")[-1]
    dest_path = dest_dir / filename

    if progress_callback:
        progress_callback(f"Downloading {filename}...")

    urllib.request.urlretrieve(url, str(dest_path))


def upload_to_s3(local_dir: Path, model_key: str,
                 progress_callback=None) -> str:
    """Upload downloaded model files to S3, including the inference handler.

    Bundles the universal inference.py handler with the model weights
    so SageMaker knows how to load and invoke the model.

    Returns the S3 URI (s3://bucket/prefix/model_key/).
    """
    # Copy the universal inference handler into the model directory
    import shutil
    handler_src = Path(__file__).resolve().parent.parent / "sagemaker_handlers" / "inference.py"
    code_dir = local_dir / "code"
    code_dir.mkdir(exist_ok=True)
    if handler_src.exists():
        shutil.copy2(str(handler_src), str(code_dir / "inference.py"))
    else:
        logger.warning("Inference handler not found at %s", handler_src)
    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise ValueError(
            "No S3 bucket configured. Set up an S3 bucket in Video Settings "
            "or set ARTSMOKER_CUSTOM_MODELS_BUCKET environment variable."
        )

    s3 = boto3.client("s3")
    prefix = f"{S3_MODEL_PREFIX}/{model_key}"

    if progress_callback:
        progress_callback(f"Uploading to s3://{bucket}/{prefix}/...")

    file_count = 0
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = Path(root) / file
            relative_path = local_path.relative_to(local_dir)
            s3_key = f"{prefix}/{relative_path}"
            s3.upload_file(str(local_path), bucket, s3_key)
            file_count += 1

    logger.info("Uploaded %d files to s3://%s/%s/", file_count, bucket, prefix)
    return f"s3://{bucket}/{prefix}/"


def deploy_endpoint(model_key: str, endpoint_type: str = "async",
                    instance_type: str | None = None,
                    progress_callback=None) -> dict:
    """Create a SageMaker endpoint for the model.

    endpoint_type: "async" (scale-to-zero, cheaper) or "realtime" (always-on, faster)
    instance_type: override the default instance type from the catalog

    Returns deployment info: endpoint_name, status, arn, etc.
    """
    from backend.services.custom_models import get_catalog_model

    model = get_catalog_model(model_key)
    if not model:
        raise ValueError(f"Unknown model: {model_key}")

    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise ValueError("No S3 bucket configured.")

    instance = instance_type or model["requirements"]["recommended_instance"]
    endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"

    if progress_callback:
        progress_callback(f"Creating SageMaker {endpoint_type} endpoint: {endpoint_name}...")

    # Use SageMaker SDK to create the endpoint
    sm = boto3.client("sagemaker")

    model_data_url = f"s3://{bucket}/{S3_MODEL_PREFIX}/{model_key}/"

    # Create SageMaker model
    sm_model_name = f"artsmoker-{model_key.replace('_', '-')}-model"
    try:
        sm.create_model(
            ModelName=sm_model_name,
            PrimaryContainer={
                "Image": _get_inference_container(model),
                "ModelDataUrl": model_data_url,
                "Environment": _get_model_environment(model_key, model),
            },
            ExecutionRoleArn=_get_sagemaker_role(),
        )
    except sm.exceptions.ClientError as e:
        if "Cannot create already existing model" in str(e):
            logger.info("SageMaker model %s already exists, reusing", sm_model_name)
        else:
            raise

    # Create endpoint config
    config_name = f"{endpoint_name}-config"
    config_params = {
        "EndpointConfigName": config_name,
        "ProductionVariants": [{
            "VariantName": "primary",
            "ModelName": sm_model_name,
            "InstanceType": instance,
            "InitialInstanceCount": 1,
        }],
    }

    if endpoint_type == "async":
        config_params["AsyncInferenceConfig"] = {
            "OutputConfig": {
                "S3OutputPath": f"s3://{bucket}/{S3_MODEL_PREFIX}/inference-output/{model_key}/",
            },
            "ClientConfig": {
                "MaxConcurrentInvocationsPerInstance": 4,
            },
        }

    try:
        sm.create_endpoint_config(**config_params)
    except sm.exceptions.ClientError as e:
        if "Cannot create already existing" in str(e):
            logger.info("Endpoint config %s already exists, reusing", config_name)
        else:
            raise

    # Create endpoint
    try:
        sm.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name,
        )
        logger.info("Creating SageMaker endpoint: %s (type=%s, instance=%s)",
                     endpoint_name, endpoint_type, instance)
    except sm.exceptions.ClientError as e:
        if "Cannot create already existing" in str(e):
            logger.info("Endpoint %s already exists", endpoint_name)
        else:
            raise

    return {
        "endpoint_name": endpoint_name,
        "model_name": sm_model_name,
        "config_name": config_name,
        "endpoint_type": endpoint_type,
        "instance_type": instance,
        "status": "Creating",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def check_endpoint_status(endpoint_name: str) -> dict:
    """Check the status of a SageMaker endpoint."""
    try:
        sm = boto3.client("sagemaker")
        resp = sm.describe_endpoint(EndpointName=endpoint_name)
        return {
            "endpoint_name": endpoint_name,
            "status": resp["EndpointStatus"],
            "creation_time": resp.get("CreationTime", "").isoformat() if resp.get("CreationTime") else "",
            "last_modified": resp.get("LastModifiedTime", "").isoformat() if resp.get("LastModifiedTime") else "",
        }
    except Exception as e:
        return {"endpoint_name": endpoint_name, "status": "NotFound", "error": str(e)}


def teardown_endpoint(model_key: str, delete_s3: bool = False) -> dict:
    """Delete a SageMaker endpoint and optionally its S3 artifacts."""
    endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
    sm_model_name = f"artsmoker-{model_key.replace('_', '-')}-model"
    config_name = f"{endpoint_name}-config"

    sm = boto3.client("sagemaker")
    deleted = []

    try:
        sm.delete_endpoint(EndpointName=endpoint_name)
        deleted.append(f"endpoint:{endpoint_name}")
    except Exception as e:
        logger.warning("Failed to delete endpoint %s: %s", endpoint_name, e)

    try:
        sm.delete_endpoint_config(EndpointConfigName=config_name)
        deleted.append(f"config:{config_name}")
    except Exception:
        pass

    try:
        sm.delete_model(ModelName=sm_model_name)
        deleted.append(f"model:{sm_model_name}")
    except Exception:
        pass

    if delete_s3:
        try:
            bucket = get_deployment_s3_bucket()
            s3 = boto3.resource("s3")
            prefix = f"{S3_MODEL_PREFIX}/{model_key}/"
            bucket_obj = s3.Bucket(bucket)
            bucket_obj.objects.filter(Prefix=prefix).delete()
            deleted.append(f"s3:{bucket}/{prefix}")
        except Exception as e:
            logger.warning("Failed to delete S3 artifacts: %s", e)

    return {"deleted": deleted}


# ── Private helpers ───────────────────────────────────────────────────────

def _get_inference_container(model: dict) -> str:
    """Get the appropriate SageMaker Deep Learning Container URI."""
    # HuggingFace DLC for PyTorch inference
    region = boto3.Session().region_name or "us-west-2"
    account_map = {
        "us-east-1": "763104351884",
        "us-west-2": "763104351884",
        "eu-west-1": "763104351884",
        "ap-northeast-1": "763104351884",
    }
    account = account_map.get(region, "763104351884")

    lib = model["requirements"].get("inference_library", "diffusers")
    if lib in ("diffusers", "transformers"):
        # HuggingFace PyTorch inference container
        return f"{account}.dkr.ecr.{region}.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-gpu-py310-cu121-ubuntu22.04"
    else:
        # Generic PyTorch container
        return f"{account}.dkr.ecr.{region}.amazonaws.com/pytorch-inference:2.1.0-gpu-py310-cu121-ubuntu22.04"


def _get_model_environment(model_key: str, model: dict) -> dict:
    """Get environment variables for the SageMaker container.

    These env vars tell the universal inference handler (inference.py)
    how to load and invoke this specific model. ALL configuration comes
    from the catalog — the handler reads env vars, not model-specific code.
    """
    invoke = model.get("invoke", {})

    env = {
        "MODEL_KEY": model_key,
        "INFERENCE_LIBRARY": invoke.get("library", "diffusers"),
        "PREDICTOR_TYPE": invoke.get("predictor_type", "text_to_image"),
        "HF_MODEL_ID": model["source"].get("repo_id", ""),
        "SAGEMAKER_PROGRAM": "inference.py",
        "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code",
        # Full invoke config as JSON for advanced use
        "INVOKE_CONFIG": json.dumps(invoke, default=str),
    }

    # Map catalog invoke fields to handler env vars
    if invoke.get("loader_class"):
        env["LOADER_CLASS"] = invoke["loader_class"]
    if invoke.get("loader_task"):
        env["LOADER_TASK"] = invoke["loader_task"]
    if invoke.get("torch_dtype"):
        env["TORCH_DTYPE"] = invoke["torch_dtype"]
    if invoke.get("trust_remote_code"):
        env["TRUST_REMOTE_CODE"] = "true"
    if invoke.get("enable_cpu_offload"):
        env["ENABLE_CPU_OFFLOAD"] = "true"
    if invoke.get("processor_class"):
        env["PROCESSOR_CLASS"] = invoke["processor_class"]
    if invoke.get("loader_variant"):
        env["LOADER_VARIANT"] = invoke["loader_variant"]

    return env


def _get_sagemaker_role() -> str:
    """Get the SageMaker execution role ARN.

    Tries: ARTSMOKER_SAGEMAKER_ROLE env var → default name pattern → error.
    """
    role = os.environ.get("ARTSMOKER_SAGEMAKER_ROLE")
    if role:
        return role

    # Try to find an existing SageMaker role
    try:
        iam = boto3.client("iam")
        roles = iam.list_roles(PathPrefix="/service-role/")
        for r in roles.get("Roles", []):
            if "SageMaker" in r["RoleName"] or "sagemaker" in r["RoleName"]:
                return r["Arn"]
    except Exception:
        pass

    raise ValueError(
        "No SageMaker execution role found. Create one with AmazonSageMakerFullAccess "
        "and set ARTSMOKER_SAGEMAKER_ROLE=arn:aws:iam::ACCOUNT:role/ROLE_NAME"
    )
