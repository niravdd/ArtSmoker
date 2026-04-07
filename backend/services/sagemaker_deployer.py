"""Amazon SageMaker Deployer — handles endpoint creation for custom models.

Lifecycle:
  For HuggingFace models (direct pull — no local download):
    1. upload_handler_to_s3() — uploads only inference.py handler code to S3
    2. deploy_endpoint()      — creates Amazon SageMaker endpoint with HF_MODEL_ID
       (container pulls weights directly from HuggingFace at startup)

  For non-HuggingFace models (GitHub releases, etc.):
    1. download_model()  — pulls weights from source to local temp
    2. upload_to_s3()    — uploads weights + handler to S3
    3. deploy_endpoint() — creates Amazon SageMaker endpoint

  Common:
    4. check_status()    — polls endpoint status
    5. teardown()        — deletes endpoint and optionally S3 artifacts

HuggingFace tokens for gated models are passed as an environment variable
to the Amazon SageMaker container (HUGGING_FACE_HUB_TOKEN). This is a
read-only token stored only in your own AWS account's Amazon SageMaker
model configuration.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

# S3 prefix for model weights and handler code
S3_MODEL_PREFIX = "artsmoker/custom-models"


def _get_region() -> str:
    """Get the AWS region — from session, env, or config default (us-west-2)."""
    region = boto3.Session().region_name
    if region:
        return region
    from backend.config import settings
    return settings.aws_region_models


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


def is_hf_source(model_key: str) -> bool:
    """Check if a model uses HuggingFace as its source (eligible for direct pull)."""
    from backend.services.custom_models import get_catalog_model
    model = get_catalog_model(model_key)
    if not model:
        return False
    return model.get("source", {}).get("type") == "huggingface"


# ── HuggingFace Direct Pull (no local download) ─────────────────────────


def upload_handler_to_s3(model_key: str, progress_callback=None) -> str:
    """Upload ONLY the inference handler code to S3 (no model weights).

    For HuggingFace models, the Amazon SageMaker container pulls weights
    directly from HuggingFace at startup via HF_MODEL_ID. We only need
    to provide the inference handler (inference.py + requirements.txt).

    Returns the S3 URI for the handler code directory.
    """
    import shutil

    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise ValueError(
            "No S3 bucket configured. Set up an S3 bucket in Video Settings "
            "or set ARTSMOKER_CUSTOM_MODELS_BUCKET environment variable."
        )

    handlers_dir = Path(__file__).resolve().parent.parent / "sagemaker_handlers"

    # Create temp directory with just the handler code
    temp_dir = Path(tempfile.mkdtemp(prefix=f"artsmoker_handler_{model_key}_"))
    try:
        code_dir = temp_dir / "code"
        code_dir.mkdir(exist_ok=True)
        for fname in ("inference.py", "requirements.txt"):
            src = handlers_dir / fname
            if src.exists():
                shutil.copy2(str(src), str(code_dir / fname))
            else:
                logger.warning("Handler file not found: %s", src)

        s3 = boto3.client("s3", region_name=_get_region())
        prefix = f"{S3_MODEL_PREFIX}/{model_key}"

        if progress_callback:
            progress_callback("Uploading inference handler to S3...")

        file_count = 0
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                local_path = Path(root) / file
                relative_path = local_path.relative_to(temp_dir)
                s3_key = f"{prefix}/{relative_path}"
                s3.upload_file(str(local_path), bucket, s3_key)
                file_count += 1

        logger.info("Uploaded %d handler files to s3://%s/%s/", file_count, bucket, prefix)
        return f"s3://{bucket}/{prefix}/"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── Non-HuggingFace: Local Download + S3 Upload ─────────────────────────


def download_model(model_key: str, hf_token: str | None = None,
                   progress_callback=None) -> Path:
    """Download model weights from a non-HuggingFace source to local temp.

    For GitHub releases: uses direct URL download.
    NOT used for HuggingFace models (those use direct pull via HF_MODEL_ID).

    Returns the local directory containing the downloaded files.
    """
    from backend.services.custom_models import get_catalog_model

    model = get_catalog_model(model_key)
    if not model:
        raise ValueError(f"Unknown model: {model_key}")

    source = model["source"]
    source_type = source["type"]

    if source_type == "huggingface":
        raise ValueError(
            f"Model '{model_key}' is a HuggingFace model — use direct pull "
            f"(upload_handler_to_s3 + deploy_endpoint with hf_token) instead."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix=f"artsmoker_{model_key}_"))

    if source_type == "github_release":
        _download_github_release(source["url"], temp_dir, progress_callback)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    logger.info("Downloaded %s to %s", model["label"], temp_dir)
    return temp_dir


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
    so Amazon SageMaker knows how to load and invoke the model.

    Returns the S3 URI (s3://bucket/prefix/model_key/).
    """
    # Bundle inference handler + requirements into the model directory
    import shutil
    handlers_dir = Path(__file__).resolve().parent.parent / "sagemaker_handlers"
    code_dir = local_dir / "code"
    code_dir.mkdir(exist_ok=True)
    for fname in ("inference.py", "requirements.txt"):
        src = handlers_dir / fname
        if src.exists():
            shutil.copy2(str(src), str(code_dir / fname))
        else:
            logger.warning("Handler file not found: %s", src)
    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise ValueError(
            "No S3 bucket configured. Set up an S3 bucket in Video Settings "
            "or set ARTSMOKER_CUSTOM_MODELS_BUCKET environment variable."
        )

    s3 = boto3.client("s3", region_name=_get_region())
    prefix = f"{S3_MODEL_PREFIX}/{model_key}"

    # Count total files first for progress reporting
    total_files = sum(len(files) for _, _, files in os.walk(local_dir))

    if progress_callback:
        progress_callback(f"Uploading to S3 (0 of {total_files} files)...")

    file_count = 0
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = Path(root) / file
            relative_path = local_path.relative_to(local_dir)
            s3_key = f"{prefix}/{relative_path}"
            s3.upload_file(str(local_path), bucket, s3_key)
            file_count += 1
            if progress_callback:
                progress_callback(f"Uploading to S3 ({file_count} of {total_files} files): {file}")

    logger.info("Uploaded %d files to s3://%s/%s/", file_count, bucket, prefix)
    return f"s3://{bucket}/{prefix}/"


# ── Endpoint Deployment ──────────────────────────────────────────────────


def deploy_endpoint(model_key: str, endpoint_type: str = "async",
                    instance_type: str | None = None,
                    hf_token: str | None = None,
                    progress_callback=None) -> dict:
    """Create an Amazon SageMaker endpoint for the model.

    endpoint_type: "async" (scale-to-zero, cheaper) or "realtime" (always-on, faster)
    instance_type: override the default instance type from the catalog
    hf_token: HuggingFace token for gated models — stored as container env var

    For HuggingFace models: container pulls weights via HF_MODEL_ID at startup.
    For other models: weights must already be in S3 (via upload_to_s3).

    Returns deployment info: endpoint_name, status, arn, etc.
    """
    from backend.services.custom_models import get_catalog_model, get_bundle_for_model, get_bundle

    model = get_catalog_model(model_key)
    if not model:
        raise ValueError(f"Unknown model: {model_key}")

    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise ValueError("No S3 bucket configured.")

    # Check if this model belongs to a bundle (shared instance)
    bundle_key = get_bundle_for_model(model_key)
    if bundle_key:
        bundle = get_bundle(bundle_key)
        endpoint_name = f"artsmoker-bundle-{bundle_key}"
        instance = instance_type or bundle["recommended_instance"]
        logger.info("Model %s belongs to bundle '%s' (endpoint: %s)", model_key, bundle_key, endpoint_name)
    else:
        endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
        instance = instance_type or model["requirements"]["recommended_instance"]

    if progress_callback:
        progress_callback(f"Creating Amazon SageMaker {endpoint_type} endpoint: {endpoint_name}...")

    sm = boto3.client("sagemaker", region_name=_get_region())

    model_data_url = f"s3://{bucket}/{S3_MODEL_PREFIX}/{model_key}/"

    # For gated HuggingFace models: store/reuse shared token in Secrets Manager
    hf_token_secret_arn = None
    if hf_token:
        if progress_callback:
            progress_callback("Storing HuggingFace token securely in AWS Secrets Manager...")
        hf_token_secret_arn = store_hf_token(hf_token)
    else:
        # Check if a token is already stored from a previous deployment
        hf_token_secret_arn = get_hf_token_arn()

    # Build container environment — includes HF_MODEL_ID and secret ARN (not raw token)
    container_env = _get_model_environment(model_key, model, hf_token_secret_arn=hf_token_secret_arn)

    # Create Amazon SageMaker model
    sm_model_name = f"artsmoker-{model_key.replace('_', '-')}-model"
    try:
        sm.create_model(
            ModelName=sm_model_name,
            PrimaryContainer={
                "Image": _get_inference_container(model),
                "ModelDataUrl": model_data_url,
                "Environment": container_env,
            },
            ExecutionRoleArn=_get_sagemaker_role(),
        )
    except sm.exceptions.ClientError as e:
        if "Cannot create already existing model" in str(e):
            logger.info("Amazon SageMaker model %s already exists, reusing", sm_model_name)
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
        logger.info("Creating Amazon SageMaker endpoint: %s (type=%s, instance=%s)",
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
    """Check the status of an Amazon SageMaker endpoint."""
    try:
        sm = boto3.client("sagemaker", region_name=_get_region())
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
    """Delete an Amazon SageMaker endpoint, S3 artifacts, and HF token secret."""
    endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
    sm_model_name = f"artsmoker-{model_key.replace('_', '-')}-model"
    config_name = f"{endpoint_name}-config"

    sm = boto3.client("sagemaker", region_name=_get_region())
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

    # Note: shared HF token is NOT deleted on teardown — other gated models may need it.
    # Use delete_hf_token() explicitly to remove it.

    if delete_s3:
        try:
            bucket = get_deployment_s3_bucket()
            s3 = boto3.resource("s3", region_name=_get_region())
            prefix = f"{S3_MODEL_PREFIX}/{model_key}/"
            bucket_obj = s3.Bucket(bucket)
            bucket_obj.objects.filter(Prefix=prefix).delete()
            deleted.append(f"s3:{bucket}/{prefix}")
        except Exception as e:
            logger.warning("Failed to delete S3 artifacts: %s", e)

    return {"deleted": deleted}


# ── Private helpers ───────────────────────────────────────────────────────

def _get_inference_container(model: dict) -> str:
    """Get the appropriate Amazon SageMaker Deep Learning Container URI."""
    # HuggingFace DLC for PyTorch inference
    region = _get_region()
    account_map = {
        "us-east-1": "763104351884",
        "us-west-2": "763104351884",
        "eu-west-1": "763104351884",
        "ap-northeast-1": "763104351884",
    }
    account = account_map.get(region, "763104351884")

    lib = model["requirements"].get("inference_library", "diffusers")
    if lib in ("diffusers", "transformers"):
        # HuggingFace PyTorch inference container (latest available)
        return f"{account}.dkr.ecr.{region}.amazonaws.com/huggingface-pytorch-inference:2.6.0-transformers4.51.3-gpu-py312-cu124-ubuntu22.04-v2.3"
    else:
        # Generic PyTorch container
        return f"{account}.dkr.ecr.{region}.amazonaws.com/pytorch-inference:2.6.0-gpu-py312-cu124-ubuntu22.04-sagemaker-v1.73"


# Single shared HuggingFace token for all gated models
_HF_TOKEN_SECRET_NAME = "artsmoker/hf-token"


def store_hf_token(hf_token: str) -> str:
    """Store a HuggingFace token in AWS Secrets Manager (encrypted).

    Uses a SINGLE shared secret for all models — not one per model.
    Returns the secret ARN. The token is encrypted at rest and only accessible
    by the Amazon SageMaker execution role.
    """
    sm_secrets = boto3.client("secretsmanager", region_name=_get_region())

    try:
        # Update existing secret
        resp = sm_secrets.update_secret(
            SecretId=_HF_TOKEN_SECRET_NAME,
            SecretString=hf_token,
        )
        logger.info("Updated shared HF token in Secrets Manager")
        return resp["ARN"]
    except sm_secrets.exceptions.ResourceNotFoundException:
        pass

    # Create new secret
    resp = sm_secrets.create_secret(
        Name=_HF_TOKEN_SECRET_NAME,
        Description="Shared HuggingFace token for ArtSmoker gated models (read-only, auto-managed)",
        SecretString=hf_token,
    )
    logger.info("Stored shared HF token in Secrets Manager: %s", _HF_TOKEN_SECRET_NAME)
    return resp["ARN"]


def get_hf_token_arn() -> str | None:
    """Get the ARN of the stored HuggingFace token, or None if not stored yet."""
    sm_secrets = boto3.client("secretsmanager", region_name=_get_region())
    try:
        resp = sm_secrets.describe_secret(SecretId=_HF_TOKEN_SECRET_NAME)
        return resp["ARN"]
    except Exception:
        return None


def has_hf_token() -> bool:
    """Check if a HuggingFace token is already stored in Secrets Manager."""
    return get_hf_token_arn() is not None


def delete_hf_token():
    """Delete the shared HuggingFace token from Secrets Manager.

    Called explicitly by the user (not automatically on teardown,
    since other gated models may still need it).
    """
    sm_secrets = boto3.client("secretsmanager", region_name=_get_region())
    try:
        sm_secrets.delete_secret(
            SecretId=_HF_TOKEN_SECRET_NAME,
            ForceDeleteWithoutRecovery=True,
        )
        logger.info("Deleted shared HF token from Secrets Manager")
        return True
    except Exception as e:
        logger.debug("No HF token to delete: %s", e)
        return False


def _get_model_environment(model_key: str, model: dict,
                           hf_token_secret_arn: str | None = None) -> dict:
    """Get environment variables for the Amazon SageMaker container.

    These env vars tell the universal inference handler (inference.py)
    how to load and invoke this specific model. ALL configuration comes
    from the catalog — the handler reads env vars, not model-specific code.

    For HuggingFace models: HF_MODEL_ID tells the handler to pull from HF.
    For gated models: HF_TOKEN_SECRET_ARN points to the encrypted token
    in AWS Secrets Manager (handler fetches it at startup).
    """
    invoke = model.get("invoke", {})
    source = model.get("source", {})

    env = {
        "MODEL_KEY": model_key,
        "INFERENCE_LIBRARY": invoke.get("library", "diffusers"),
        "PREDICTOR_TYPE": invoke.get("predictor_type", "text_to_image"),
        "HF_MODEL_ID": source.get("repo_id", ""),
        "SAGEMAKER_PROGRAM": "inference.py",
        "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code",
        # Full invoke config as JSON for advanced use
        "INVOKE_CONFIG": json.dumps(invoke, default=str),
    }

    # Pointer to encrypted HF token in Secrets Manager (not the token itself)
    if hf_token_secret_arn:
        env["HF_TOKEN_SECRET_ARN"] = hf_token_secret_arn

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
    """Get the Amazon SageMaker execution role ARN.

    Amazon SageMaker's CreateModel API requires an ExecutionRoleArn — a role
    that the Amazon SageMaker service assumes to pull model data from S3 and
    run the inference container. This is NOT a separate role — it's the SAME
    role the user already has for ArtSmoker (Bedrock + S3), just with
    sagemaker.amazonaws.com added to its trust policy.

    Discovery (fully automatic):
    1. Running on EC2/ECS → use the current instance role (add Amazon SageMaker trust if missing)
    2. Find existing ArtSmoker role in the account → use it
    3. Auto-create one if nothing found (local dev scenario)
    """
    sts = boto3.client("sts", region_name=_get_region())
    try:
        identity = sts.get_caller_identity()
        arn = identity.get("Arn", "")
        account = identity.get("Account", "")

        # 1. Running as an IAM role (EC2/ECS) → use it directly
        if ":assumed-role/" in arn:
            role_name = arn.split(":assumed-role/")[1].split("/")[0]
            role_arn = f"arn:aws:iam::{account}:role/{role_name}"
            # Ensure the role has sagemaker trust policy
            _ensure_sagemaker_trust(role_name)
            return role_arn

        # 2. Look for existing ArtSmoker or Amazon SageMaker roles
        iam = boto3.client("iam", region_name=_get_region())
        try:
            for name in ["ArtSmokerSageMakerRole", "ArtSmokerEC2Role"]:
                try:
                    resp = iam.get_role(RoleName=name)
                    return resp["Role"]["Arn"]
                except iam.exceptions.NoSuchEntityException:
                    continue
        except Exception:
            pass

        # 3. Auto-create the role
        return _create_sagemaker_role(account)

    except Exception as e:
        logger.warning("Amazon SageMaker role discovery failed: %s", e)
        raise ValueError(
            "Could not find or create an Amazon SageMaker execution role. "
            "Ensure your IAM permissions include iam:CreateRole and iam:AttachRolePolicy, "
            "or deploy on EC2 with an IAM instance role."
        )


def _ensure_sagemaker_trust(role_name: str):
    """Ensure a role has sagemaker.amazonaws.com in its trust policy."""
    iam = boto3.client("iam", region_name=_get_region())
    try:
        resp = iam.get_role(RoleName=role_name)
        trust = resp["Role"].get("AssumeRolePolicyDocument", {})
        statements = trust.get("Statement", [])
        has_sagemaker = any(
            "sagemaker.amazonaws.com" in str(s.get("Principal", {}))
            for s in statements
        )
        if not has_sagemaker:
            # Add sagemaker to the trust policy
            statements.append({
                "Effect": "Allow",
                "Principal": {"Service": "sagemaker.amazonaws.com"},
                "Action": "sts:AssumeRole",
            })
            trust["Statement"] = statements
            iam.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust),
            )
            logger.info("Added sagemaker.amazonaws.com trust to role %s", role_name)
    except Exception as e:
        logger.debug("Could not update trust policy for %s: %s", role_name, e)


def _create_sagemaker_role(account: str) -> str:
    """Auto-create an ArtSmokerSageMakerRole with required permissions."""
    iam = boto3.client("iam", region_name=_get_region())
    role_name = "ArtSmokerSageMakerRole"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": ["sagemaker.amazonaws.com", "ec2.amazonaws.com"]},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="ArtSmoker Amazon SageMaker execution role (auto-created)",
        )
        role_arn = resp["Role"]["Arn"]

        # Attach Amazon SageMaker and S3 permissions
        for policy_arn in [
            "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        ]:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        # Add Secrets Manager read access so containers can fetch HF tokens
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="ArtSmokerSecretsAccess",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": f"arn:aws:secretsmanager:*:{account}:secret:artsmoker/*",
                }],
            }),
        )

        logger.info("Auto-created Amazon SageMaker role: %s (propagation may take ~10s)", role_arn)
        return role_arn

    except iam.exceptions.EntityAlreadyExistsException:
        return f"arn:aws:iam::{account}:role/{role_name}"
    except Exception as e:
        raise ValueError(f"Failed to create Amazon SageMaker role: {e}. Ensure your IAM has iam:CreateRole permission.")
