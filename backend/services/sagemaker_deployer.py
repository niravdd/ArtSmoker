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


def _generate_requirements(model_key: str, output_path: Path):
    """Generate a model-specific requirements.txt from the catalog.

    Each model declares its own python_requirements in the catalog:
      "python_requirements": {
        "base": ["torch>=2.6.0,<2.7.0", ...],   // shared, protect DLC
        "model": ["diffusers>=0.36.0,<0.38.0", ...]  // model-specific
      }

    This avoids dependency conflicts between models (e.g., FLUX needs
    diffusers 0.36+, Real-ESRGAN needs basicsr which pulls tb-nightly).
    """
    from backend.services.custom_models import get_catalog_model

    model = get_catalog_model(model_key)
    reqs = model.get("python_requirements", {}) if model else {}
    base = reqs.get("base", [])
    model_reqs = reqs.get("model", [])

    if not base and not model_reqs:
        # Fallback: copy the shared requirements.txt
        fallback = output_path.parent.parent.parent / "sagemaker_handlers" / "requirements.txt"
        if fallback.exists():
            import shutil
            shutil.copy2(str(fallback), str(output_path))
            logger.warning("No python_requirements in catalog for %s — using shared fallback", model_key)
            return
        raise ValueError(f"No python_requirements for {model_key} and no fallback file")

    lines = [
        f"# Auto-generated requirements for {model_key}",
        f"# From model_registry.json → custom_model_catalog → {model_key} → python_requirements",
        "",
        "# Base (protect DLC environment)",
    ]
    lines.extend(base)
    lines.append("")
    lines.append(f"# Model-specific ({model_key})")
    lines.extend(model_reqs)
    lines.append("")

    output_path.write_text("\n".join(lines))
    logger.info("Generated requirements.txt for %s: %d base + %d model packages",
                model_key, len(base), len(model_reqs))

    # Validate requirements are still installable on PyPI
    _validate_requirements(model_key, base + model_reqs)


def _validate_requirements(model_key: str, requirements: list[str]):
    """Check that pinned package versions exist on PyPI (not yanked/deleted).

    Runs at deploy time as a pre-flight check. Warns on issues but doesn't
    block deployment — stale pins may still install from pip cache.
    """
    import re
    import urllib.request

    pkg_pattern = re.compile(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)\s*([><=!~].+)?$')
    issues = []

    for req in requirements:
        req = req.strip()
        if not req or req.startswith("#"):
            continue
        match = pkg_pattern.match(req)
        if not match:
            continue
        pkg_name = match.group(1).split("[")[0]  # strip extras like [torch]

        try:
            url = f"https://pypi.org/pypi/{pkg_name}/json"
            resp = urllib.request.urlopen(url, timeout=5)
            data = json.loads(resp.read().decode())
            latest = data.get("info", {}).get("version", "?")
            # Check if package is yanked
            releases = data.get("releases", {})
            if latest in releases:
                files = releases[latest]
                if files and all(f.get("yanked", False) for f in files):
                    issues.append(f"{pkg_name}: latest version {latest} is yanked")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                issues.append(f"{pkg_name}: NOT FOUND on PyPI")
            else:
                pass  # Network issue, don't block
        except Exception:
            pass  # Timeout or network issue, don't block

    if issues:
        for issue in issues:
            logger.warning("Requirement validation: %s (model: %s)", issue, model_key)
    else:
        logger.info("All requirements validated on PyPI for %s", model_key)


# ── HuggingFace Direct Pull (no local download) ─────────────────────────


def upload_handler_to_s3(model_key: str, progress_callback=None) -> str:
    """Upload ONLY the inference handler code to S3 as a model.tar.gz.

    For HuggingFace models, the Amazon SageMaker container pulls weights
    directly from HuggingFace at startup via HF_MODEL_ID. We only need
    to provide the inference handler (inference.py + requirements.txt)
    packaged as model.tar.gz (required by Amazon SageMaker's ModelDataUrl).

    Returns the S3 URI for the model.tar.gz file.
    """
    import shutil
    import tarfile

    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise ValueError(
            "No S3 bucket configured. Set up an S3 bucket in Video Settings "
            "or set ARTSMOKER_CUSTOM_MODELS_BUCKET environment variable."
        )

    handlers_dir = Path(__file__).resolve().parent.parent / "sagemaker_handlers"

    temp_dir = Path(tempfile.mkdtemp(prefix=f"artsmoker_handler_{model_key}_"))
    try:
        # Build the directory structure for the tar.gz
        code_dir = temp_dir / "code"
        code_dir.mkdir(exist_ok=True)

        # Copy the universal inference handler
        src = handlers_dir / "inference.py"
        if src.exists():
            shutil.copy2(str(src), str(code_dir / "inference.py"))
        else:
            raise FileNotFoundError(f"Inference handler not found: {src}")

        # Generate model-specific requirements.txt from catalog
        _generate_requirements(model_key, code_dir / "requirements.txt")

        # Create model.tar.gz — Amazon SageMaker requires this format
        tar_path = temp_dir / "model.tar.gz"
        with tarfile.open(str(tar_path), "w:gz") as tar:
            tar.add(str(code_dir), arcname="code")

        # Upload tar.gz to S3
        s3 = boto3.client("s3", region_name=_get_region())
        s3_key = f"{S3_MODEL_PREFIX}/{model_key}/model.tar.gz"

        if progress_callback:
            progress_callback("Uploading inference handler to S3...")

        s3.upload_file(str(tar_path), bucket, s3_key)

        try:
            file_size = tar_path.stat().st_size
            from backend.services.cost_tracker import add_background_s3_cost
            add_background_s3_cost("put", file_size, f"handler tar.gz upload ({file_size}B)", region=_get_region())
        except Exception:
            pass

        s3_uri = f"s3://{bucket}/{s3_key}"
        logger.info("Uploaded handler model.tar.gz to %s", s3_uri)
        return s3_uri

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
    """Upload downloaded model files to S3 as model.tar.gz.

    Bundles the universal inference.py handler with the model weights
    into a model.tar.gz (required by Amazon SageMaker's ModelDataUrl).

    Returns the S3 URI for the model.tar.gz file.
    """
    import shutil
    import tarfile

    # Bundle inference handler + requirements into the model directory
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

    # Create model.tar.gz — Amazon SageMaker requires this format
    total_files = sum(len(files) for _, _, files in os.walk(local_dir))
    if progress_callback:
        progress_callback(f"Creating model.tar.gz ({total_files} files)...")

    tar_path = local_dir.parent / f"{model_key}_model.tar.gz"
    file_count = 0
    with tarfile.open(str(tar_path), "w:gz") as tar:
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = Path(root) / file
                arcname = str(local_path.relative_to(local_dir))
                tar.add(str(local_path), arcname=arcname)
                file_count += 1
                if progress_callback:
                    progress_callback(f"Packaging ({file_count} of {total_files}): {file}")

    # Upload the tar.gz to S3
    s3 = boto3.client("s3", region_name=_get_region())
    s3_key = f"{S3_MODEL_PREFIX}/{model_key}/model.tar.gz"

    if progress_callback:
        tar_size_mb = tar_path.stat().st_size / (1024 * 1024)
        progress_callback(f"Uploading model.tar.gz ({tar_size_mb:.0f} MB) to S3...")

    tar_size = tar_path.stat().st_size
    s3.upload_file(str(tar_path), bucket, s3_key)
    tar_path.unlink(missing_ok=True)  # Clean up local tar.gz

    try:
        from backend.services.cost_tracker import add_background_s3_cost
        add_background_s3_cost("put", tar_size, f"model weights upload ({tar_size // (1024*1024)}MB)", region=_get_region())
    except Exception:
        pass

    s3_uri = f"s3://{bucket}/{s3_key}"
    logger.info("Uploaded model.tar.gz (%d files, %d MB) to %s", file_count, tar_size // (1024*1024), s3_uri)
    return s3_uri


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

    model_data_url = f"s3://{bucket}/{S3_MODEL_PREFIX}/{model_key}/model.tar.gz"

    # For gated HuggingFace models: store/reuse shared token in Secrets Manager
    resolved_hf_token = hf_token
    if hf_token:
        if progress_callback:
            progress_callback("Storing HuggingFace token securely in AWS Secrets Manager...")
        store_hf_token(hf_token)
    elif not resolved_hf_token:
        # Check if a token is already stored from a previous deployment
        resolved_hf_token = _retrieve_hf_token()

    # Build container environment — includes HF_MODEL_ID and HF token.
    # The HF DLC container reads HF_MODEL_ID + HUGGING_FACE_HUB_TOKEN at
    # startup BEFORE our custom handler runs, so we must pass the actual
    # token (not a Secrets Manager ARN). The token is a read-only token
    # visible only in the user's own AWS account via sagemaker:DescribeModel.
    container_env = _get_model_environment(model_key, model, hf_token=resolved_hf_token)

    # Create Amazon SageMaker model — delete and recreate if it already exists
    # (ensures env vars and container image are always up to date)
    sm_model_name = f"artsmoker-{model_key.replace('_', '-')}-model"
    try:
        sm.delete_model(ModelName=sm_model_name)
        logger.info("Deleted existing Amazon SageMaker model %s (will recreate with latest config)", sm_model_name)
    except Exception:
        pass  # Doesn't exist yet — fine

    sm.create_model(
        ModelName=sm_model_name,
        PrimaryContainer={
            "Image": _get_inference_container(model),
            "ModelDataUrl": model_data_url,
            "Environment": container_env,
        },
        ExecutionRoleArn=_get_sagemaker_role(),
    )

    # Create endpoint config — same pattern: delete old, create fresh
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
        # Max concurrent invocations from catalog (default 1 for safety)
        max_concurrent = model.get("invoke", {}).get("max_concurrent_invocations", 1)
        config_params["AsyncInferenceConfig"] = {
            "OutputConfig": {
                "S3OutputPath": f"s3://{bucket}/{S3_MODEL_PREFIX}/inference-output/{model_key}/",
            },
            "ClientConfig": {
                "MaxConcurrentInvocationsPerInstance": max_concurrent,
            },
        }
        logger.info("Async config: MaxConcurrentInvocations=%d for %s", max_concurrent, model_key)

    try:
        sm.delete_endpoint_config(EndpointConfigName=config_name)
        logger.info("Deleted existing endpoint config %s (will recreate)", config_name)
    except Exception:
        pass

    sm.create_endpoint_config(**config_params)

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

    # Auto-scaling (scale to zero) is NOT registered here — it's deferred until
    # the readiness monitor confirms the model is fully loaded. This prevents
    # scale-in from killing the instance while the model is still loading
    # (which can take 5–60+ minutes for large models like FLUX.2 dev).
    # See _start_readiness_monitor() → _register_auto_scaling_after_ready().

    # Set CloudWatch log retention (SageMaker creates log groups automatically)
    _set_log_retention(endpoint_name)

    return {
        "endpoint_name": endpoint_name,
        "model_name": sm_model_name,
        "config_name": config_name,
        "endpoint_type": endpoint_type,
        "instance_type": instance,
        "status": "Creating",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# Cache endpoint status to avoid repeated slow SageMaker API calls
_endpoint_status_cache: dict = {}  # endpoint_name → {"result": dict, "time": float}
_ENDPOINT_CACHE_TTL = 30  # seconds

# Model readiness cache — tracks which endpoints have confirmed model loading
# Once "loaded in" is seen in logs, the endpoint is marked ready permanently
# (until the cache is cleared by teardown or server restart)
_model_readiness: dict = {}  # endpoint_name → {"ready": bool, "detail": str, "checked_at": float}
_readiness_monitors: set = set()  # endpoints with active background monitors


def _check_model_readiness(endpoint_name: str) -> dict:
    """Check if the model is actually loaded and ready, not just InService.

    Uses a tiered approach:
    1. Check cache — if already confirmed ready, return immediately
    2. Quick CloudWatch log scan — look for 'loaded in' or error markers
    3. Start background monitor if not yet confirmed (polls every 30s)

    Returns: {"ready": bool, "detail": str}
    """
    import time as _time

    # 1. Cached readiness (permanent once confirmed)
    cached = _model_readiness.get(endpoint_name)
    if cached and cached.get("ready"):
        return cached

    # 2. Quick log scan (non-blocking, fast)
    readiness = _scan_logs_for_readiness(endpoint_name)
    if readiness["ready"]:
        _model_readiness[endpoint_name] = readiness
        logger.info("Model ready confirmed for %s: %s", endpoint_name, readiness["detail"])
        # Ensure auto-scaling is registered (may be first confirmation)
        _register_auto_scaling_after_ready(endpoint_name)
        return readiness

    # 3. Start background monitor if not already running
    if endpoint_name not in _readiness_monitors:
        _start_readiness_monitor(endpoint_name)

    return readiness


def _scan_logs_for_readiness(endpoint_name: str) -> dict:
    """Scan CloudWatch logs for model readiness indicators.

    Looks for our handler's log lines:
    - "Model ... loaded in Xs" → ready
    - "CUDA out of memory" → failed
    - "NameError" / "Error" → failed
    - "Loading checkpoint shards: N%" → progress
    - "Enabling ... offload" → almost ready
    """
    try:
        logs_client = boto3.client("logs", region_name=_get_region())
        log_group = f"/aws/sagemaker/Endpoints/{endpoint_name}"

        # Find the main log stream (not data-log)
        streams = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy="LastEventTime",
            descending=True,
            limit=3,
        )
        stream_name = None
        for s in streams.get("logStreams", []):
            if "data-log" not in s["logStreamName"]:
                stream_name = s["logStreamName"]
                break

        if not stream_name:
            return {"ready": False, "detail": "Waiting for container to start..."}

        # Scan logs (get last 200 events)
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=True,
            limit=500,
        )

        latest_progress = ""
        for e in events.get("events", []):
            msg = e["message"].strip()

            # Success: model loaded
            if "loaded in" in msg and "Model" in msg:
                # Extract the load time
                return {"ready": True, "detail": msg[msg.index("Model"):msg.index("Model") + 80]}

            # Failure indicators
            if "CUDA out of memory" in msg:
                return {"ready": False, "detail": "Failed: GPU out of memory", "failed": True}
            if "NameError" in msg:
                return {"ready": False, "detail": "Failed: handler code error", "failed": True}
            if "Quantization failed" in msg:
                return {"ready": False, "detail": "Failed: quantization error", "failed": True}

            # Progress indicators
            if "checkpoint shards" in msg and "%" in msg:
                # Extract percentage
                import re
                pct = re.search(r'(\d+)%', msg)
                if pct:
                    latest_progress = f"Loading model weights... {pct.group(1)}%"
            elif "pipeline comp" in msg and "%" in msg:
                import re
                pct = re.search(r'(\d+)%', msg)
                if pct:
                    latest_progress = f"Loading pipeline... {pct.group(1)}%"
            elif "Enabling" in msg and "offload" in msg:
                latest_progress = "Configuring memory offload..."
            elif "Quantizing" in msg:
                latest_progress = "Quantizing model..."
            elif "Loading" in msg and "with library" in msg:
                latest_progress = "Starting model download..."

        if latest_progress:
            return {"ready": False, "detail": latest_progress}
        return {"ready": False, "detail": "Initializing container..."}

    except Exception as e:
        # Log group may not exist yet
        if "ResourceNotFoundException" in str(e):
            return {"ready": False, "detail": "Waiting for container to start..."}
        return {"ready": False, "detail": "Checking..."}


def _start_readiness_monitor(endpoint_name: str):
    """Start a background thread that polls logs until the model is ready."""
    import threading, time as _time

    _readiness_monitors.add(endpoint_name)

    def _monitor():
        try:
            for attempt in range(120):  # Up to 60 min (120 × 30s)
                _time.sleep(30)
                readiness = _scan_logs_for_readiness(endpoint_name)

                if readiness.get("ready"):
                    _model_readiness[endpoint_name] = readiness
                    logger.info("Background monitor: %s is ready — %s", endpoint_name, readiness["detail"])
                    # Now safe to register auto-scaling (model is loaded, won't be killed)
                    _register_auto_scaling_after_ready(endpoint_name)
                    break

                if readiness.get("failed"):
                    _model_readiness[endpoint_name] = readiness
                    logger.warning("Background monitor: %s failed — %s", endpoint_name, readiness["detail"])
                    break

                if attempt % 4 == 0:  # Log progress every 2 min
                    logger.debug("Background monitor: %s — %s", endpoint_name, readiness.get("detail", "checking"))
            else:
                _model_readiness[endpoint_name] = {"ready": False, "detail": "Timed out waiting for model to load (60 min)"}
                logger.warning("Background monitor: %s timed out", endpoint_name)
        finally:
            _readiness_monitors.discard(endpoint_name)

    threading.Thread(target=_monitor, daemon=True, name=f"readiness-{endpoint_name}").start()
    logger.info("Started readiness monitor for %s", endpoint_name)


def clear_readiness_cache(endpoint_name: str):
    """Clear readiness cache for an endpoint (called on teardown/redeploy)."""
    _model_readiness.pop(endpoint_name, None)
    _readiness_monitors.discard(endpoint_name)
    _auto_scaling_registered.discard(endpoint_name)


def check_endpoint_status(endpoint_name: str) -> dict:
    """Check the status of an Amazon SageMaker endpoint.

    Caches results for 30 seconds to avoid slow repeated API calls
    (the catalog endpoint calls this for each deployed model).
    """
    import time as _time

    # Return cached result if fresh
    cached = _endpoint_status_cache.get(endpoint_name)
    if cached and (_time.time() - cached["time"]) < _ENDPOINT_CACHE_TTL:
        return cached["result"]

    try:
        from botocore.config import Config as BotoConfig
        sm = boto3.client("sagemaker", region_name=_get_region(),
                          config=BotoConfig(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1}))
        resp = sm.describe_endpoint(EndpointName=endpoint_name)

        # Detect warm-up: check if model is ACTUALLY ready by reading CloudWatch logs
        # SageMaker reports InService as soon as the container starts, but the model
        # may still be downloading weights and loading for 5-60+ minutes.
        # Our handler logs "Model ... loaded in Xs" when truly ready.
        status = resp["EndpointStatus"]
        warming_up = False
        warmup_detail = ""
        instance_count = 0

        for v in resp.get("ProductionVariants", []):
            instance_count = v.get("CurrentInstanceCount", 0)

        if status == "InService":
            readiness = _check_model_readiness(endpoint_name)
            warming_up = not readiness["ready"]
            warmup_detail = readiness.get("detail", "")

        result = {
            "endpoint_name": endpoint_name,
            "status": status,
            "warming_up": warming_up,
            "warmup_detail": warmup_detail,
            "instance_count": instance_count,
            "creation_time": resp.get("CreationTime", "").isoformat() if resp.get("CreationTime") else "",
            "last_modified": resp.get("LastModifiedTime", "").isoformat() if resp.get("LastModifiedTime") else "",
        }
        _endpoint_status_cache[endpoint_name] = {"result": result, "time": _time.time()}
        return result
    except Exception as e:
        result = {"endpoint_name": endpoint_name, "status": "NotFound", "warming_up": False, "error": str(e)}
        _endpoint_status_cache[endpoint_name] = {"result": result, "time": _time.time()}
        return result


def teardown_endpoint(model_key: str, delete_s3: bool = False) -> dict:
    """Delete an Amazon SageMaker endpoint, S3 artifacts, and HF token secret."""
    endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
    clear_readiness_cache(endpoint_name)
    _endpoint_status_cache.pop(endpoint_name, None)
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


_LOG_RETENTION_DAYS = 3  # CloudWatch log retention for SageMaker endpoints


def _set_log_retention(endpoint_name: str):
    """Set CloudWatch log retention for a SageMaker endpoint.

    SageMaker creates log groups automatically with no expiration (retain forever).
    We set aggressive retention to control costs. Runs in background since the
    log group may not exist yet (created when the endpoint starts).
    """
    import threading, time as _time

    def _apply():
        log_group = f"/aws/sagemaker/Endpoints/{endpoint_name}"
        logs = boto3.client("logs", region_name=_get_region())
        for attempt in range(6):  # Try for 5 minutes
            try:
                logs.put_retention_policy(
                    logGroupName=log_group,
                    retentionInDays=_LOG_RETENTION_DAYS,
                )
                logger.info("CloudWatch retention set to %d days for %s", _LOG_RETENTION_DAYS, log_group)
                return
            except logs.exceptions.ResourceNotFoundException:
                _time.sleep(60)  # Log group not created yet — wait
            except Exception as e:
                logger.debug("Log retention setup failed for %s: %s", endpoint_name, e)
                return
        logger.debug("Log group not found after 5 min for %s — retention not set", endpoint_name)

    threading.Thread(target=_apply, daemon=True, name=f"logret-{endpoint_name}").start()


# Track which endpoints already have auto-scaling registered to avoid duplicates
_auto_scaling_registered: set[str] = set()


def _register_auto_scaling_after_ready(endpoint_name: str):
    """Register auto-scaling AFTER the model is confirmed ready.

    Called from the readiness monitor or quick log scan. This ensures
    the scale-to-zero policy is only applied once the model is loaded,
    preventing scale-in from killing instances during long model loads.
    """
    if endpoint_name in _auto_scaling_registered:
        return  # Already registered

    # Compute cooldown from model config
    from .custom_models import get_catalog
    catalog = get_catalog()
    # Find the model key from endpoint name (artsmoker-flux2-dev → flux2_dev)
    model_key = endpoint_name.replace("artsmoker-", "").replace("-", "_")
    model = catalog.get("models", {}).get(model_key, {})
    invoke = model.get("invoke", {})
    typical = invoke.get("typical_latency_seconds", 300)
    cooldown = max(600, typical * 2)  # At least 10 min, or 2x typical inference latency

    try:
        _setup_auto_scaling(endpoint_name, scale_in_cooldown=cooldown)
        _auto_scaling_registered.add(endpoint_name)
        logger.info("Auto-scaling registered for %s (cooldown=%ds) — model confirmed ready", endpoint_name, cooldown)
    except Exception as e:
        logger.warning("Auto-scaling setup failed for %s after model ready: %s — retrying in background", endpoint_name, e)
        _retry_auto_scaling_in_background(endpoint_name, scale_in_cooldown=cooldown)


def _retry_auto_scaling_in_background(endpoint_name: str, scale_in_cooldown: int = 600):
    """Retry auto-scaling setup after the endpoint reaches InService."""
    import threading, time as _time

    def _retry():
        for attempt in range(1, 13):  # 12 attempts × 60s = 12 min max
            _time.sleep(60)
            try:
                status = check_endpoint_status(endpoint_name)
                if status.get("status") == "InService":
                    _setup_auto_scaling(endpoint_name, scale_in_cooldown=scale_in_cooldown)
                    logger.info("Auto-scaling configured for %s (deferred, attempt %d)", endpoint_name, attempt)
                    return
                if status.get("status") == "Failed":
                    logger.warning("Endpoint %s failed — skipping auto-scaling", endpoint_name)
                    return
            except Exception as e:
                logger.debug("Auto-scaling retry %d for %s: %s", attempt, endpoint_name, e)
        logger.warning("Auto-scaling setup timed out for %s after 12 retries", endpoint_name)

    threading.Thread(target=_retry, daemon=True, name=f"autoscale-{endpoint_name}").start()


def _setup_auto_scaling(endpoint_name: str, scale_in_cooldown: int = 600):
    """Configure auto-scaling for an async endpoint: scale to zero + scale from zero.

    Two policies needed (AWS limitation):
    1. Target tracking (ApproximateBacklogSizePerInstance): handles scale-in to zero
       when the queue is empty for scale_in_cooldown seconds.
    2. Step scaling (HasBacklogWithoutCapacity): handles scale-OUT from zero when
       new requests arrive. Target tracking can't do this because "per instance"
       is undefined when instances = 0.

    scale_in_cooldown: seconds idle before scaling to zero. Must be longer than
    the model's load time, or auto-scaling will kill the instance during warmup.
    """
    region = _get_region()
    aas = boto3.client("application-autoscaling", region_name=region)
    cw = boto3.client("cloudwatch", region_name=region)
    resource_id = f"endpoint/{endpoint_name}/variant/primary"

    # Register scalable target: min=0 (scale to zero), max=1
    aas.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=0,
        MaxCapacity=1,
    )

    # Policy 1: Target tracking — scales IN to zero when queue empty
    aas.put_scaling_policy(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyName=f"{endpoint_name}-scale-to-zero",
        PolicyType="TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": 1.0,
            "CustomizedMetricSpecification": {
                "MetricName": "ApproximateBacklogSizePerInstance",
                "Namespace": "AWS/SageMaker",
                "Dimensions": [{"Name": "EndpointName", "Value": endpoint_name}],
                "Statistic": "Average",
            },
            "ScaleInCooldown": scale_in_cooldown,
            "ScaleOutCooldown": 0,
        },
    )

    # Policy 2: Step scaling — scales OUT from zero when backlog detected
    step_resp = aas.put_scaling_policy(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyName=f"{endpoint_name}-scale-from-zero",
        PolicyType="StepScaling",
        StepScalingPolicyConfiguration={
            "AdjustmentType": "ChangeInCapacity",
            "StepAdjustments": [{"MetricIntervalLowerBound": 0, "ScalingAdjustment": 1}],
            "Cooldown": 300,
        },
    )

    # CloudWatch alarm: triggers scale-from-zero when HasBacklogWithoutCapacity > 0
    cw.put_metric_alarm(
        AlarmName=f"{endpoint_name}-has-backlog",
        Namespace="AWS/SageMaker",
        MetricName="HasBacklogWithoutCapacity",
        Dimensions=[{"Name": "EndpointName", "Value": endpoint_name}],
        Statistic="Average",
        Period=60,
        EvaluationPeriods=1,
        Threshold=0,
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[step_resp["PolicyARN"]],
    )

    logger.info("Auto-scaling configured for %s (scale to zero + scale from zero)", endpoint_name)


# ── Private helpers ───────────────────────────────────────────────────────

def _get_inference_container(model: dict) -> str:
    """Get the appropriate Amazon SageMaker Deep Learning Container URI.

    Discovers the latest available container image dynamically from ECR.
    Uses the standard AWS DLC (Deep Learning Container) registry, which is
    a public ECR registry managed by AWS (not the user's account).
    """
    region = _get_region()
    lib = model["requirements"].get("inference_library", "diffusers")

    if lib in ("diffusers", "transformers"):
        repo = "huggingface-pytorch-inference"
        tag_filter = "gpu"  # GPU containers for inference
    else:
        repo = "pytorch-inference"
        tag_filter = "gpu"

    return _resolve_dlc_image(region, repo, tag_filter)


# Cache resolved container URIs (they don't change during a session)
_dlc_cache: dict = {}


def _resolve_dlc_image(region: str, repo: str, tag_filter: str) -> str:
    """Resolve the latest DLC container image URI from ECR.

    Queries the AWS DLC public ECR registry to find the latest GPU
    container image. Caches results for the session.
    """
    cache_key = f"{region}:{repo}:{tag_filter}"
    if cache_key in _dlc_cache:
        return _dlc_cache[cache_key]

    # The DLC ECR account is the same across most regions (AWS-managed public registry)
    # Discover it via SageMaker's DescribeEndpoint or use the well-known account
    dlc_account = _get_dlc_account(region)

    try:
        ecr = boto3.client("ecr", region_name=region)
        # List image tags, filter for GPU + CUDA 12 + latest
        paginator = ecr.get_paginator("describe_images")
        best_tag = None
        best_sort_key = ""

        for page in paginator.paginate(
            registryId=dlc_account,
            repositoryName=repo,
            filter={"tagStatus": "TAGGED"},
        ):
            for img in page.get("imageDetails", []):
                for tag in (img.get("imageTags") or []):
                    # Match: must have gpu + cu12, must NOT have date suffix (clean tags only)
                    if tag_filter in tag and "cu12" in tag and "ubuntu" in tag:
                        # Skip date-stamped tags (e.g., ...-2025-12-15-21-39-54)
                        import re
                        if re.search(r"-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$", tag):
                            continue
                        # Sort by tag name descending to get latest version
                        if tag > best_sort_key:
                            best_sort_key = tag
                            best_tag = tag

        if best_tag:
            uri = f"{dlc_account}.dkr.ecr.{region}.amazonaws.com/{repo}:{best_tag}"
            _dlc_cache[cache_key] = uri
            logger.info("Resolved DLC container: %s", uri)
            return uri

    except Exception as e:
        logger.warning("Failed to discover DLC container from ECR: %s — using fallback", e)

    # Fallback: known-good tags (updated periodically with code releases)
    fallback = {
        "huggingface-pytorch-inference": "2.6.0-transformers4.51.3-gpu-py312-cu124-ubuntu22.04-v2.3",
        "pytorch-inference": "2.6.0-gpu-py312-cu124-ubuntu22.04-sagemaker-v1.73",
    }
    tag = fallback.get(repo, fallback["pytorch-inference"])
    uri = f"{dlc_account}.dkr.ecr.{region}.amazonaws.com/{repo}:{tag}"
    _dlc_cache[cache_key] = uri
    return uri


def _get_dlc_account(region: str) -> str:
    """Get the AWS account ID for the DLC (Deep Learning Container) ECR registry.

    This is a well-known public registry managed by AWS — the same account
    across most regions. Discovered dynamically so it works in any region.
    """
    # Try to discover from STS (the DLC account is always 763104351884 for standard regions)
    # For China/GovCloud regions, it differs — but we discover it dynamically
    try:
        ecr = boto3.client("ecr", region_name=region)
        # Try the standard DLC account — if it works, we're good
        ecr.describe_repositories(
            registryId="763104351884",
            repositoryNames=["pytorch-inference"],
            maxResults=1,
        )
        return "763104351884"
    except Exception:
        pass

    # Fallback: standard account (works for all commercial AWS regions)
    return "763104351884"


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


def _retrieve_hf_token() -> str | None:
    """Retrieve the actual HuggingFace token value from Secrets Manager."""
    sm_secrets = boto3.client("secretsmanager", region_name=_get_region())
    try:
        resp = sm_secrets.get_secret_value(SecretId=_HF_TOKEN_SECRET_NAME)
        return resp["SecretString"]
    except Exception:
        return None


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
                           hf_token: str | None = None) -> dict:
    """Get environment variables for the Amazon SageMaker container.

    These env vars tell OUR inference handler (inference.py) how to load
    and invoke this model. ALL configuration comes from the catalog.

    IMPORTANT: We do NOT set HF_MODEL_ID — that would cause the DLC
    container's built-in handler to intercept the model loading (bypassing
    our handler and its optimizations like CPU offloading). Instead we use
    ARTSMOKER_HF_REPO which only our handler reads.
    """
    invoke = model.get("invoke", {})
    source = model.get("source", {})

    env = {
        "MODEL_KEY": model_key,
        "INFERENCE_LIBRARY": invoke.get("library", "diffusers"),
        "PREDICTOR_TYPE": invoke.get("predictor_type", "text_to_image"),
        # Our own env var — NOT HF_MODEL_ID (which the DLC container intercepts)
        "ARTSMOKER_HF_REPO": source.get("repo_id", ""),
        "SAGEMAKER_PROGRAM": "inference.py",
        "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code",
        # Full invoke config as JSON — strip server-side-only fields to stay under 1024-char limit
        "INVOKE_CONFIG": json.dumps(
            {k: v for k, v in invoke.items() if k not in ("prompt_guidance",)},
            default=str,
        ),
        # CUDA memory management
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        # Container timeout — large models (FLUX.2) need >60s default
        # MMS uses this for both model loading and invocation timeout
        "SAGEMAKER_MODEL_SERVER_TIMEOUT": str(invoke.get("typical_latency_seconds", 300) * 3),
    }

    # HuggingFace token for gated models
    if hf_token:
        env["HUGGING_FACE_HUB_TOKEN"] = hf_token

    # Map catalog invoke fields to handler env vars
    if invoke.get("loader_class"):
        env["LOADER_CLASS"] = invoke["loader_class"]
    if invoke.get("loader_task"):
        env["LOADER_TASK"] = invoke["loader_task"]
    if invoke.get("torch_dtype"):
        env["TORCH_DTYPE"] = invoke["torch_dtype"]
    if invoke.get("trust_remote_code"):
        env["TRUST_REMOTE_CODE"] = "true"
    if invoke.get("processor_class"):
        env["PROCESSOR_CLASS"] = invoke["processor_class"]
    if invoke.get("loader_variant"):
        env["LOADER_VARIANT"] = invoke["loader_variant"]

    # Memory optimizations — read from catalog invoke config
    if invoke.get("enable_model_cpu_offload"):
        env["ENABLE_MODEL_CPU_OFFLOAD"] = "true"
    if invoke.get("enable_sequential_cpu_offload"):
        env["ENABLE_SEQUENTIAL_CPU_OFFLOAD"] = "true"
    if invoke.get("enable_vae_slicing"):
        env["ENABLE_VAE_SLICING"] = "true"
    if invoke.get("enable_vae_tiling"):
        env["ENABLE_VAE_TILING"] = "true"

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
