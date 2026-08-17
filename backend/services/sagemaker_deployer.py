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
from datetime import datetime, timezone, timedelta
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

# S3 prefix for model weights and handler code
S3_MODEL_PREFIX = "artsmoker/custom-models"

# SageMaker instance families that ship with local NVMe SSD instance storage.
# These REJECT the VolumeSizeInGB / attachable-EBS parameter — SageMaker
# auto-mounts their local NVMe. Setting VolumeSizeInGB on them fails with
# "VolumeSize parameter is not allowed for the selected Instance type".
# (Confirmed for g5 via a live deploy error; g6/g6e/g4dn/p4d/p5 all use NVMe.)
_NVME_INSTANCE_FAMILIES = ("g5", "g6", "g6e", "g4dn", "g7e", "p4d", "p5", "p5e", "p5en", "p6")


def _instance_has_local_nvme(instance: str) -> bool:
    """True if the instance type's family auto-mounts local NVMe (no EBS volume).

    Matches on the family token between 'ml.' and the next '.', so 'ml.g5.xlarge'
    → 'g5'. Exact-token match avoids false hits (e.g. 'g5' must not match 'g56').
    """
    parts = instance.split(".")  # ['ml', 'g5', 'xlarge']
    family = parts[1] if len(parts) >= 2 and parts[0] == "ml" else ""
    return family in _NVME_INSTANCE_FAMILIES


# Custom Python packages bundled into model.tar.gz per inference library.
# These ship under code/<pkg>/ on the container alongside inference.py.
# Shared by the deploy packager and the dev hot-reload overlay so both agree
# on which packages a given model carries. Model-agnostic: keyed by library.
_LIBRARY_BUNDLED_PACKAGES = {
    # Three texturing backends bundled, selected via ARTSMOKER_TEXTURE_BACKEND /
    # per-request texture_backend: mvadapter (Apache-2.0, default), hy3dpaint
    # (Hunyuan3D-Paint, best quality, Tencent community license), trellis2
    # (TRELLIS.2, MIT + commercial DINOv3 — commercial-clean, native PBR).
    # 'stablex' = vendored ControlNetVAEModel (Apache-2.0) for the StableNormal /
    # StableDelight YOSO one-step forwards (their weights' controlnet is a
    # ControlNetVAEModel subclass; stock diffusers ControlNetModel can't drive it).
    # (MVPainter removed 2026-06-25 — license-tainted + dominated; see SPEC §5.10.1.)
    "image_to_3d": ["triposg", "mvadapter", "hy3dpaint", "stablex"],
    # Full standalone TRELLIS.2 image→3D pipeline: the `trellis2` package + its
    # CUDA exts are git-cloned/built at runtime (_ensure_trellis2), so NOTHING
    # needs vendoring here — the handler's only bundled-pkg imports are
    # function-local to the TripoSG path, which this library never calls.
    "trellis2_image_to_3d": [],
}


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


# Short-lived cache of head_bucket accessibility results so we don't probe S3 on
# every single async invocation. Keyed by bucket name → (ok, reason, ts).
_bucket_access_cache: dict = {}
_BUCKET_ACCESS_TTL_SECONDS = 120


def check_deployment_bucket(require_access: bool = True, use_cache: bool = True) -> dict:
    """Preflight: is the custom-model S3 bucket configured AND (optionally) reachable?

    Single source of truth reused by deploy, async-invoke, and the status
    endpoint so every path fails with the SAME clear guidance instead of a raw
    boto3 error deep in a call. Returns:
      {"ok": bool, "bucket": str, "reason": str, "message": str}
    reason ∈ {"", "not_configured", "not_found", "access_denied", "error"}.
    `require_access=False` checks only that a bucket NAME is set (cheap, no S3
    call). `require_access=True` also does a cached head_bucket."""
    bucket = get_deployment_s3_bucket()
    if not bucket:
        return {
            "ok": False, "bucket": "", "reason": "not_configured",
            "message": "No S3 bucket is configured for custom models. Set one in "
                       "Model Settings → Custom Models before deploying or running "
                       "self-hosted (custom) models.",
        }
    if not require_access:
        return {"ok": True, "bucket": bucket, "reason": "", "message": ""}

    # Cached accessibility probe.
    if use_cache:
        cached = _bucket_access_cache.get(bucket)
        if cached is not None:
            ok, reason, ts = cached
            try:
                import time as _t
                fresh = (_t.time() - ts) < _BUCKET_ACCESS_TTL_SECONDS
            except Exception:
                fresh = False
            if fresh:
                return {"ok": ok, "bucket": bucket, "reason": reason,
                        "message": _bucket_access_message(bucket, reason)}

    ok, reason = True, ""
    try:
        s3 = boto3.client("s3", region_name=_get_region())
        s3.head_bucket(Bucket=bucket)
    except Exception as exc:
        code = ""
        resp = getattr(exc, "response", None)
        if isinstance(resp, dict):
            code = str(resp.get("Error", {}).get("Code", ""))
        if code in ("404", "NoSuchBucket"):
            ok, reason = False, "not_found"
        elif code in ("403", "AccessDenied", "401"):
            ok, reason = False, "access_denied"
        else:
            ok, reason = False, "error"
    try:
        import time as _t
        _bucket_access_cache[bucket] = (ok, reason, _t.time())
    except Exception:
        pass
    return {"ok": ok, "bucket": bucket, "reason": reason,
            "message": _bucket_access_message(bucket, reason)}


def _bucket_access_message(bucket: str, reason: str) -> str:
    if reason == "not_found":
        return (f"The configured S3 bucket \"{bucket}\" was not found. Re-check the "
                f"name in Model Settings → Custom Models, or create it.")
    if reason == "access_denied":
        return (f"Access to S3 bucket \"{bucket}\" was denied. Check the bucket's "
                f"region and that your AWS credentials can read/write it.")
    if reason == "error":
        return (f"Could not verify S3 bucket \"{bucket}\". Check your AWS "
                f"credentials/region and try again.")
    return ""


def invalidate_bucket_access_cache(bucket: str = "") -> None:
    """Drop cached accessibility results (call after the user changes the bucket)."""
    if bucket:
        _bucket_access_cache.pop(bucket, None)
    else:
        _bucket_access_cache.clear()


def get_bucket_dependencies() -> dict:
    """Report whether the configured bucket has DEPENDENCIES that make it unsafe
    to change. Once a custom model is deployed, SageMaker bakes the bucket into
    the endpoint's immutable ModelDataUrl / S3OutputPath, so switching buckets
    would silently break live endpoints (they keep reading/writing the old
    bucket). We therefore LOCK the bucket to read-only once anything depends on
    it. Dependencies = any deployed custom endpoint, any in-flight job, or any
    existing ArtSmoker artifacts already in the bucket.

    Returns {"locked": bool, "reasons": [str], "endpoints": [str],
             "pending_jobs": int, "has_s3_data": bool}."""
    from backend.services.model_registry import get_registry
    reg = get_registry()

    # 1. Deployed custom endpoints (across all studio sections).
    endpoints = []
    for section in ("image_models", "post_processing", "video_models", "three_d_models"):
        for key, cfg in (reg.get(section, {}) or {}).items():
            ep = (cfg.get("deployment", {}) or {}).get("endpoint_name")
            if ep:
                endpoints.append(ep)

    # 2. In-flight async jobs (2D/3D).
    pending = 0
    try:
        from backend.services.async_jobs import get_pending_count
        pending = get_pending_count()
    except Exception:
        pending = 0

    # 3. Existing ArtSmoker artifacts in the bucket (e.g. cached weights left by a
    #    torn-down model). Cheap: list one key under our prefix.
    has_s3_data = False
    bucket = get_deployment_s3_bucket()
    if bucket:
        try:
            s3 = boto3.client("s3", region_name=_get_region())
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{S3_MODEL_PREFIX}/", MaxKeys=1)
            has_s3_data = resp.get("KeyCount", 0) > 0
        except Exception:
            has_s3_data = False  # can't tell → don't lock on this signal alone

    reasons = []
    if endpoints:
        reasons.append(f"{len(endpoints)} deployed custom model endpoint(s)")
    if pending:
        reasons.append(f"{pending} in-flight job(s)")
    if has_s3_data:
        reasons.append("existing ArtSmoker data in the bucket")

    return {
        "locked": bool(reasons),
        "reasons": reasons,
        "endpoints": endpoints,
        "pending_jobs": pending,
        "has_s3_data": has_s3_data,
    }


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

        # Write FULL invoke config as JSON file — no env var truncation risk.
        # The handler reads this first, falls back to INVOKE_CONFIG env var.
        from .custom_models import get_catalog_model
        catalog_model = get_catalog_model(model_key)
        if catalog_model:
            invoke_config = catalog_model.get("invoke", {})
            # Include secondary_sources in invoke config so handler can resolve them
            if catalog_model.get("secondary_sources"):
                invoke_config = dict(invoke_config)
                invoke_config["secondary_sources"] = catalog_model["secondary_sources"]
            # Strip fields not needed by the handler (same list as INVOKE_CONFIG env var)
            invoke_for_file = {k: v for k, v in invoke_config.items() if k not in (
                "prompt_guidance", "supported_sizes",
            )}
            config_path = code_dir / "invoke_config.json"
            config_path.write_text(json.dumps(invoke_for_file, indent=2, default=str))
            logger.info("Wrote invoke_config.json (%d bytes) to model.tar.gz", config_path.stat().st_size)

        # Bundle custom Python packages referenced by the model.
        # These are pre-packaged in backend/sagemaker_handlers/bundled_packages/<name>/
        # and get included alongside inference.py so they're importable on the container.
        bundled_packages_dir = handlers_dir / "bundled_packages"
        if catalog_model and bundled_packages_dir.is_dir():
            library = catalog_model.get("invoke", {}).get("library", "")
            # Determine which packages to bundle based on library type.
            # Shared map (also used by the dev hot-reload overlay).
            packages_to_bundle = _LIBRARY_BUNDLED_PACKAGES.get(library, [])
            for pkg_name in packages_to_bundle:
                pkg_src = bundled_packages_dir / pkg_name
                if pkg_src.is_dir():
                    pkg_dest = code_dir / pkg_name
                    shutil.copytree(str(pkg_src), str(pkg_dest))
                    pkg_files = sum(1 for _ in pkg_dest.rglob("*.py"))
                    logger.info("Bundled package '%s' (%d .py files) into model.tar.gz",
                                pkg_name, pkg_files)

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
                    build_only: bool = False,
                    texture_backend: str | None = None,
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
        instance = instance_type or model["requirements"]["recommended_instance"]
        # Unique endpoint name: model + instance type + short ID.
        # Allows multiple deployments of the same model on different hardware.
        # SageMaker model name = endpoint_name + "-model", max 63 chars.
        # Endpoint name: artsmoker-{model_key}-{short_id} (no instance type — user never sees it)
        import hashlib, time as _t
        short_id = hashlib.md5(f"{model_key}{instance}{_t.time()}".encode()).hexdigest()[:4]
        base = f"artsmoker-{model_key.replace('_', '-')}"
        max_base = 57 - len(short_id) - 1  # 1 for the hyphen before short_id
        if len(base) > max_base:
            base = base[:max_base]
        endpoint_name = f"{base}-{short_id}"

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
    container_env = _get_model_environment(model_key, model, hf_token=resolved_hf_token,
                                           texture_backend=texture_backend)

    # Build mode: save cache after model load (no inference needed).
    # Used when the build instance can't run inference (e.g., OOM on smaller GPUs)
    # but has enough RAM for quantization. Cache is then served from a different instance.
    if build_only:
        container_env["ARTSMOKER_BUILD_ONLY"] = "true"
        _build_only_endpoints.add(endpoint_name)

    # Create Amazon SageMaker model — delete and recreate if it already exists
    # (ensures env vars and container image are always up to date)
    sm_model_name = f"{endpoint_name}-model"
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
    disk_gb = model.get("requirements", {}).get("disk_gb", 0)
    # Instances with local NVMe storage reject VolumeSizeInGB (auto-mounted).
    has_nvme = _instance_has_local_nvme(instance)
    variant_config = {
        "VariantName": "primary",
        "ModelName": sm_model_name,
        "InstanceType": instance,
        "InitialInstanceCount": 1,
    }
    if disk_gb > 30 and not has_nvme:
        variant_config["VolumeSizeInGB"] = disk_gb
    config_params = {
        "EndpointConfigName": config_name,
        "ProductionVariants": [variant_config],
    }

    if endpoint_type == "async":
        max_concurrent = model.get("invoke", {}).get("max_concurrent_invocations", 1)
        config_params["AsyncInferenceConfig"] = {
            "OutputConfig": {
                "S3OutputPath": f"s3://{bucket}/{S3_MODEL_PREFIX}/inference-output/{model_key}/",
                # Without a failure path, a crashing inference leaves NO S3
                # artifact at all — the poller can't tell "failed in 1s" from
                # "still processing" and jobs sit 'generating' until the stale
                # timeout (15 min+). With it, SageMaker writes the model's error
                # here and the poller fails the job in seconds with the real cause.
                "S3FailurePath": f"s3://{bucket}/{S3_MODEL_PREFIX}/inference-failures/{model_key}/",
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

    # Effective texture backend baked into this endpoint (for the 3D chooser/
    # estimate). Same source order as _get_model_environment: deploy choice >
    # catalog invoke.texture_backend > server env.
    _eff_tb = (texture_backend
               or model.get("invoke", {}).get("texture_backend")
               or os.environ.get("ARTSMOKER_TEXTURE_BACKEND"))
    return {
        "endpoint_name": endpoint_name,
        "model_name": sm_model_name,
        "config_name": config_name,
        "endpoint_type": endpoint_type,
        "instance_type": instance,
        # Explicit deployment location: the invoker + async poller resolve their
        # AWS clients from this (falls back to the home region when absent, but
        # every new deploy self-describes so cross-region entries "just work").
        "region": _get_region(),
        "status": "Creating",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "texture_backend": _eff_tb,
    }


def update_endpoint_config(model_key: str) -> dict:
    """Update a deployed endpoint's handler code, env vars, and S3 paths in-place.

    Does NOT teardown the endpoint — creates a new Model + EndpointConfig and calls
    update_endpoint for a blue-green swap. SageMaker provisions a new instance with
    the updated handler, then terminates the old one. Endpoint name, auto-scaling,
    and CloudWatch alarms are all preserved.

    Use this to:
    - Deploy updated inference.py code (e.g., S3 cache support)
    - Switch to a new S3 bucket
    - Update env vars from changed catalog config
    """
    from .custom_models import get_catalog_model
    model = get_catalog_model(model_key)
    if not model:
        raise ValueError(f"Model {model_key} not found in catalog")

    # Look up endpoint name from registry
    from .model_registry import get_registry
    reg = get_registry()
    endpoint_name = ""
    for section in ["image_models", "video_models", "post_processing", "utility_models"]:
        entry = reg.get(section, {}).get(model_key, {})
        ep = entry.get("deployment", {}).get("endpoint_name", "")
        if ep:
            endpoint_name = ep
            break
    if not endpoint_name:
        endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"

    sm = boto3.client("sagemaker", region_name=_get_region())

    # Verify endpoint exists
    try:
        desc = sm.describe_endpoint(EndpointName=endpoint_name)
        if desc["EndpointStatus"] not in ("InService", "Updating"):
            raise ValueError(f"Endpoint {endpoint_name} is {desc['EndpointStatus']} — cannot update")
    except sm.exceptions.ClientError:
        raise ValueError(f"Endpoint {endpoint_name} does not exist")

    # Get current endpoint config to preserve instance type
    current_config = sm.describe_endpoint_config(
        EndpointConfigName=desc.get("EndpointConfigName", f"{endpoint_name}-config")
    )
    current_variant = current_config["ProductionVariants"][0]
    instance = current_variant["InstanceType"]

    bucket = get_deployment_s3_bucket()

    # 1. Upload fresh handler code
    logger.info("Uploading updated handler for %s...", model_key)
    upload_handler_to_s3(model_key)

    # 2. Retrieve HF token if needed
    resolved_hf_token = _retrieve_hf_token() if model.get("requires_hf_auth") else None

    # 3. Create new SageMaker Model (delete old first)
    sm_model_name = f"{endpoint_name}-model"
    model_data_url = f"s3://{bucket}/{S3_MODEL_PREFIX}/{model_key}/model.tar.gz"
    container_env = _get_model_environment(model_key, model, hf_token=resolved_hf_token)

    try:
        sm.delete_model(ModelName=sm_model_name)
    except Exception:
        pass
    sm.create_model(
        ModelName=sm_model_name,
        PrimaryContainer={
            "Image": _get_inference_container(model),
            "ModelDataUrl": model_data_url,
            "Environment": container_env,
        },
        ExecutionRoleArn=_get_sagemaker_role(),
    )

    # 4. Create new EndpointConfig (delete old, create fresh with new bucket paths)
    config_name = f"{endpoint_name}-config"
    max_concurrent = model.get("invoke", {}).get("max_concurrent_invocations", 1)
    disk_gb = model.get("requirements", {}).get("disk_gb", 0)
    has_nvme = _instance_has_local_nvme(instance)
    variant_config = {
        "VariantName": "primary",
        "ModelName": sm_model_name,
        "InstanceType": instance,
        "InitialInstanceCount": 1,
    }
    if disk_gb > 30 and not has_nvme:
        variant_config["VolumeSizeInGB"] = disk_gb
    config_params = {
        "EndpointConfigName": config_name,
        "ProductionVariants": [variant_config],
        "AsyncInferenceConfig": {
            "OutputConfig": {
                "S3OutputPath": f"s3://{bucket}/{S3_MODEL_PREFIX}/inference-output/{model_key}/",
            },
            "ClientConfig": {
                "MaxConcurrentInvocationsPerInstance": max_concurrent,
            },
        },
    }

    try:
        sm.delete_endpoint_config(EndpointConfigName=config_name)
    except Exception:
        pass
    sm.create_endpoint_config(**config_params)

    # 5. Update endpoint — triggers blue-green deployment
    sm.update_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=config_name,
    )

    # Clear caches so status reflects the update
    clear_readiness_cache(endpoint_name)
    _endpoint_status_cache.pop(endpoint_name, None)

    logger.info("Endpoint %s update triggered — blue-green swap with new handler + bucket", endpoint_name)
    return {
        "endpoint_name": endpoint_name,
        "status": "Updating",
        "instance_type": instance,
        "new_bucket": bucket,
        "detail": "Blue-green deployment in progress — new instance loading with updated handler",
    }


# Cache endpoint status to avoid repeated slow SageMaker API calls
_endpoint_status_cache: dict = {}  # endpoint_name → {"result": dict, "time": float}
_ENDPOINT_CACHE_TTL = 30  # seconds

# Model readiness cache — tracks which endpoints have confirmed model loading
# Once "loaded in" is seen in logs, the endpoint is marked ready permanently
# (until the cache is cleared by teardown or server restart)
_model_readiness: dict = {}  # endpoint_name → {"ready": bool, "detail": str, "checked_at": float}
_readiness_monitors: set = set()  # endpoints with active background monitors

# Registry sections that can hold a deployed custom endpoint. Custom image models
# live under "image_models"; 3D pipelines (TripoSG / TRELLIS.2-full) live under
# "post_processing". Readiness persistence MUST scan BOTH — otherwise a 3D
# endpoint's model_ready flag is never written (nor cleared on teardown), which
# left the 3D picker permanently showing "warming up" even after the model loaded.
_DEPLOYABLE_REGISTRY_SECTIONS = ("image_models", "post_processing")


def _check_model_readiness(endpoint_name: str) -> dict:
    """Check if the model is actually loaded and ready, not just InService.

    Uses a tiered approach:
    1. Check cache — if already confirmed ready, return immediately
    2. Quick CloudWatch log scan — look for 'loaded in' or error markers
    3. Start background monitor if not yet confirmed (polls every 30s)

    Returns: {"ready": bool, "detail": str}
    """
    import time as _time

    # 1. Cached readiness (permanent once confirmed in memory)
    cached = _model_readiness.get(endpoint_name)
    if cached and cached.get("ready"):
        return cached

    # 1b. Check registry for persisted readiness (survives server restart).
    # Scan both image_models and post_processing (3D pipelines live in the latter).
    try:
        from backend.services.model_registry import get_registry
        reg = get_registry()
        for section in _DEPLOYABLE_REGISTRY_SECTIONS:
            for key, cfg in reg.get(section, {}).items():
                dep = cfg.get("deployment", {})
                if dep.get("endpoint_name") == endpoint_name and dep.get("model_ready"):
                    result = {"ready": True, "detail": "Confirmed ready (from registry)"}
                    _model_readiness[endpoint_name] = result
                    return result
    except Exception:
        pass

    # 2. Quick log scan (non-blocking, fast)
    readiness = _scan_logs_for_readiness(endpoint_name)
    if readiness["ready"]:
        _model_readiness[endpoint_name] = readiness
        logger.info("Model ready confirmed for %s: %s", endpoint_name, readiness["detail"])
        # Persist to registry so readiness survives server restart
        _persist_readiness_to_registry(endpoint_name)
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

        # Two-pass log scan:
        # 1. filter_log_events with "loaded in" pattern — fast server-side scan
        #    across the entire log history. Catches model load even after hours of pings.
        # 2. get_log_events tail for progress/error detection (checkpoint shards, etc.)
        #
        # The old approach (get_log_events limit=500) failed because 500 events
        # covers only ~40 min of pings, but model load can take 60+ min.

        # Pass 1: Check if model already loaded (fast — scans entire history server-side)
        try:
            loaded_events = logs_client.filter_log_events(
                logGroupName=log_group,
                logStreamNames=[stream_name],
                filterPattern='"loaded in"',
                limit=5,
            )
            for e in reversed(loaded_events.get("events", [])):
                msg = e["message"].strip()
                if "loaded in" in msg and "Model" in msg:
                    try:
                        detail = msg[msg.index("Model"):msg.index("Model") + 80]
                    except (ValueError, IndexError):
                        detail = "Model loaded"
                    return {"ready": True, "detail": detail, "last_activity_ms": e.get("timestamp", 0)}
        except Exception:
            pass  # Fall through to tail scan

        # Pass 2: Tail scan for progress and errors (recent events only)
        raw_events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=False,
            limit=500,
        )
        # Filter out ping healthchecks and metric collector noise
        events = {"events": [
            e for e in raw_events.get("events", [])
            if "/ping" not in e["message"] and "MetricCollector" not in e["message"]
        ]}

        import re as _re

        # Scan backwards (newest first) to find the most recent status
        latest_progress = ""
        found_failure = None
        last_activity_ts = None  # Timestamp of most recent meaningful log event

        for e in reversed(events.get("events", [])):
            msg = e["message"].strip()
            event_ts = e.get("timestamp", 0)

            # Track last meaningful activity (any non-empty filtered event)
            if last_activity_ts is None:
                last_activity_ts = event_ts

            # Success: model loaded — ONLY match our handler's log, not MMS internal log.
            # Handler: "Model flux2_dev loaded in 189.4s (library=diffusers)"
            # MMS emits "Model model loaded io_fd=..." even when the handler CRASHES
            # (it just means the worker connected, not that model_fn succeeded).
            if "loaded in" in msg and "Model" in msg and "library=" in msg:
                try:
                    detail = msg[msg.index("Model"):msg.index("Model") + 80]
                except (ValueError, IndexError):
                    detail = "Model loaded"
                return {"ready": True, "detail": detail, "last_activity_ms": event_ts}

            # Failure indicators (take the most recent one)
            if not found_failure:
                if "CUDA out of memory" in msg:
                    found_failure = "Failed: GPU out of memory"
                elif "NameError" in msg:
                    found_failure = "Failed: handler code error"
                elif "Quantization failed" in msg:
                    found_failure = "Failed: quantization error"

            # Progress indicators — take the first (most recent) match
            if not latest_progress:
                if "checkpoint shards" in msg and "%" in msg:
                    pct_match = _re.search(r'(\d+)%', msg)
                    fraction_match = _re.search(r'(\d+)/(\d+)\s*\[', msg)
                    if pct_match and fraction_match:
                        done, total = fraction_match.group(1), fraction_match.group(2)
                        latest_progress = f"Loading weights: shard {done}/{total} ({pct_match.group(1)}%)"
                    elif pct_match:
                        latest_progress = f"Loading weights... {pct_match.group(1)}%"
                elif "pipeline comp" in msg and "%" in msg:
                    pct_match = _re.search(r'(\d+)%', msg)
                    if pct_match:
                        latest_progress = f"Assembling pipeline... {pct_match.group(1)}%"
                elif "Enabling" in msg and "offload" in msg:
                    latest_progress = "Configuring memory offload..."
                elif "Quantizing" in msg:
                    latest_progress = "Quantizing model..."
                elif "Loading" in msg and "with library" in msg:
                    latest_progress = "Downloading model..."

            # Once we have a progress update, no need to scan further back
            if latest_progress:
                break

        if found_failure:
            return {"ready": False, "detail": found_failure, "failed": True, "last_activity_ms": last_activity_ts}
        if latest_progress:
            return {"ready": False, "detail": latest_progress, "last_activity_ms": last_activity_ts}
        return {"ready": False, "detail": "Initializing container...", "last_activity_ms": last_activity_ts}

    except Exception as e:
        # Log group may not exist yet
        if "ResourceNotFoundException" in str(e):
            return {"ready": False, "detail": "Waiting for container to start..."}
        return {"ready": False, "detail": "Checking..."}


def _set_registry_model_ready(endpoint_name: str, ready: bool) -> bool:
    """Set/clear deployment.model_ready on the endpoint's registry entry.

    Mutates the in-memory registry (the single source of truth that live reads
    go through) and persists it via the registry module's own _save(), so memory
    and the user.json file stay in sync — no separate raw file write. Scans both
    image_models and post_processing (3D pipelines live in the latter). Returns
    True if the endpoint was found.
    """
    try:
        from backend.services.model_registry import get_registry, registry_transaction
        # Read-only scan first (this can be polled): locate the endpoint's entry
        # without taking the write lock or persisting. Only open a transaction —
        # which reloads + writes — when there's actually a match to mutate.
        reg = get_registry()
        target = None
        for section in _DEPLOYABLE_REGISTRY_SECTIONS:
            for key, cfg in reg.get(section, {}).items():
                if isinstance(cfg, dict) and cfg.get("deployment", {}).get("endpoint_name") == endpoint_name:
                    target = (section, key)
                    break
            if target:
                break
        if not target:
            return False
        section, key = target
        # Rebase the mutation onto the latest disk state (re-find after reload,
        # since the transaction rebuilds the registry from disk).
        with registry_transaction() as reg2:
            cfg = reg2.get(section, {}).get(key)
            if isinstance(cfg, dict):
                dep = cfg.setdefault("deployment", {})
                if ready:
                    dep["model_ready"] = True
                else:
                    dep.pop("model_ready", None)
        logger.info("model_ready=%s for %s in registry (%s)", ready, endpoint_name, section)
        return True
    except Exception as e:
        logger.debug("Failed to set model_ready for %s: %s", endpoint_name, e)
    return False


def _persist_readiness_to_registry(endpoint_name: str):
    """Persist model readiness so it survives server restarts.

    On next server start, _check_model_readiness reads this and skips log scanning.
    Cleared on teardown (deployment entry removed) or redeploy.
    """
    _set_registry_model_ready(endpoint_name, True)


def _resolve_deployment_identity(endpoint_name: str) -> tuple[str, str, str]:
    """(friendly_label, instance_type, deployed_key) for an endpoint, from the
    registry. Falls back to the endpoint name if not found. Read this BEFORE a
    teardown that would remove the registry entry."""
    label, instance, deployed_key = endpoint_name, "", ""
    try:
        from .model_registry import get_registry
        reg = get_registry()
        for section in ("image_models", "video_models", "post_processing", "utility_models"):
            for k, entry in reg.get(section, {}).items():
                dep = entry.get("deployment", {}) or {}
                if dep.get("endpoint_name") == endpoint_name:
                    return entry.get("label", k), dep.get("instance_type", ""), k
    except Exception:
        pass
    return label, instance, deployed_key


def _handle_background_deploy_ready(endpoint_name: str):
    """A deploy finished loading in the background (the 5-60 min load may have
    outlasted the user's session). Leave a durable "ready to use" notice — the
    positive counterpart to the failure notice — plus a lifecycle telemetry event.
    Best-effort; never raises."""
    label, instance, deployed_key = _resolve_deployment_identity(endpoint_name)
    try:
        from .notices import add_notice
        add_notice(
            kind="deploy_ready",
            title="Model ready to use",
            message=(f"{label}{f' ({instance})' if instance else ''} finished loading and is "
                     f"ready. It will activate on your first request (scales to zero when idle)."),
            level="success",
            dedup_key=f"deploy_ready:{endpoint_name}",
        )
    except Exception as exc:
        logger.debug("Could not record deploy-ready notice: %s", exc)
    try:
        from .telemetry import track_custom_model_deploy_ready
        track_custom_model_deploy_ready(model=deployed_key or label, instance=instance)
    except Exception:
        pass


def _handle_background_deploy_failure(endpoint_name: str, reason: str):
    """A deploy failed in the background (browser may be closed). Clean it up
    AND leave the user a durable notice so they learn about it on next visit.

    Resolves the friendly label/instance from the registry (before teardown
    removes the entry), tears the endpoint down (it can't recover), records a
    dismissible notice, and emits telemetry. Best-effort — each step guarded so
    a failure in one doesn't abort the others.
    """
    label, instance, deployed_key = _resolve_deployment_identity(endpoint_name)

    # Human-readable reason (first sentence — SageMaker reasons are verbose).
    short_reason = (reason or "").split(".")[0].strip() or "Unknown error"

    # Record the user notice (durable, dismissible; shown on next app load).
    try:
        from .notices import add_notice
        add_notice(
            kind="deploy_failed",
            title="Deployment failed while you were away",
            message=(f"{label}{f' ({instance})' if instance else ''} failed to deploy: "
                     f"{short_reason}. It was automatically removed — you can redeploy "
                     f"from Model Settings → Custom Models."),
            level="error",
            dedup_key=f"deploy_failed:{endpoint_name}",
        )
    except Exception as exc:
        logger.debug("Could not record deploy-failure notice: %s", exc)

    # Telemetry (durable historical record of capacity/deploy failures).
    try:
        from .telemetry import track_custom_model_deploy_failed
        track_custom_model_deploy_failed(model=deployed_key or label, instance=instance, reason=short_reason)
    except Exception:
        pass

    # Auto-teardown — the endpoint is a dead end. Prefer the deployed key so the
    # registry entry + auto-scaling + S3 I/O paths are all cleaned.
    try:
        teardown_endpoint(deployed_key or endpoint_name, delete_s3=False, endpoint_name=endpoint_name)
        logger.info("Auto-tore-down failed endpoint %s after background detection", endpoint_name)
    except Exception as exc:
        logger.warning("Auto-teardown of failed %s hit an error: %s", endpoint_name, exc)
    # Best-effort: also clear in-memory deploy-progress so the UI resets cleanly.
    try:
        from backend.routers.custom_deploy import _clear_deploy_status, _unregister_custom_model
        if deployed_key:
            _unregister_custom_model(deployed_key)
            _clear_deploy_status(deployed_key)
    except Exception:
        pass


def _start_readiness_monitor(endpoint_name: str):
    """Start a background thread that polls logs until the model is ready."""
    import threading, time as _time

    _readiness_monitors.add(endpoint_name)

    def _monitor():
        try:
            for attempt in range(120):  # Up to 60 min (120 × 30s)
                _time.sleep(30)

                # Check the ENDPOINT-level status first. A capacity failure
                # (InsufficientInstanceCapacity) fails at PROVISIONING — the
                # container never starts, so no logs ever appear and a
                # logs-only scan would just time out at 60 min. Catching the
                # SageMaker "Failed" state here is what makes offline failure
                # detection work.
                try:
                    ep_status = check_endpoint_status(endpoint_name)
                    if ep_status.get("status") == "Failed":
                        reason = ep_status.get("failure_reason", "") or "Unknown failure"
                        logger.warning("Background monitor: %s FAILED at provisioning — %s", endpoint_name, reason)
                        _model_readiness[endpoint_name] = {"ready": False, "failed": True, "detail": reason}
                        _handle_background_deploy_failure(endpoint_name, reason)
                        break
                except Exception:
                    pass  # transient status-check error → keep polling

                readiness = _scan_logs_for_readiness(endpoint_name)

                if readiness.get("ready"):
                    _model_readiness[endpoint_name] = readiness
                    logger.info("Background monitor: %s is ready — %s", endpoint_name, readiness["detail"])
                    _persist_readiness_to_registry(endpoint_name)
                    # Now safe to register auto-scaling (model is loaded, won't be killed)
                    _register_auto_scaling_after_ready(endpoint_name)
                    # Tell the user their deploy finished (they may have closed the
                    # browser during the 5-60 min load) — the positive counterpart
                    # to the failure notice.
                    _handle_background_deploy_ready(endpoint_name)
                    break

                if readiness.get("failed"):
                    _model_readiness[endpoint_name] = readiness
                    detail = readiness.get("detail", "Model failed to load")
                    logger.warning("Background monitor: %s failed — %s", endpoint_name, detail)
                    _handle_background_deploy_failure(endpoint_name, detail)
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
    """Clear readiness cache for an endpoint (called on teardown/redeploy).

    Clears both in-memory cache and registry-persisted model_ready flag.
    """
    _model_readiness.pop(endpoint_name, None)
    _readiness_monitors.discard(endpoint_name)
    _auto_scaling_registered.discard(endpoint_name)

    # Clear persisted readiness from the registry (in-memory + file via _save).
    _set_registry_model_ready(endpoint_name, False)


def clear_endpoint_status_cache(endpoint_name: str = ""):
    """Drop the 30s status cache so the next check_endpoint_status re-queries AWS.

    With no argument, clears the entire cache (used by the manual "Refresh
    Status" button so it always reflects truly-current endpoint state).
    """
    if endpoint_name:
        _endpoint_status_cache.pop(endpoint_name, None)
    else:
        _endpoint_status_cache.clear()


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
        desired_count = 0

        for v in resp.get("ProductionVariants", []):
            instance_count = v.get("CurrentInstanceCount", 0)
            desired_count = v.get("DesiredInstanceCount", instance_count)

        if status == "InService" and instance_count > 0:
            # Only check readiness when an instance is actually running.
            # With 0 instances (scaled to zero), the endpoint is idle — not warming up.
            readiness = _check_model_readiness(endpoint_name)
            warming_up = not readiness["ready"]
            warmup_detail = readiness.get("detail", "")

            # If model is NOT ready yet (loading after scale-out), ensure auto-scaling
            # is paused so scale-in doesn't kill the instance mid-load.
            if warming_up and endpoint_name in _auto_scaling_registered:
                _deregister_auto_scaling_during_load(endpoint_name)

        elif status == "InService" and instance_count == 0:
            # Scaled to zero — clear in-memory readiness so next scale-out
            # re-scans logs, but do NOT clear registry model_ready flag.
            # model_ready in the registry means "validated at least once" and
            # persists until teardown/redeploy so the dropdown keeps listing it.
            _model_readiness.pop(endpoint_name, None)
            _readiness_monitors.discard(endpoint_name)

        result = {
            "endpoint_name": endpoint_name,
            "status": status,
            "warming_up": warming_up,
            "warmup_detail": warmup_detail,
            "instance_count": instance_count,
            # desired > current = scale-out requested but not yet fulfilled —
            # e.g. blocked on InsufficientInstanceCapacity. The resubmit logic
            # keys on this: resubmitting cannot help while provisioning is stuck.
            "desired_instance_count": desired_count,
            "creation_time": resp.get("CreationTime", "").isoformat() if resp.get("CreationTime") else "",
            "last_modified": resp.get("LastModifiedTime", "").isoformat() if resp.get("LastModifiedTime") else "",
            # Surface the real reason for a Failed endpoint (e.g.
            # "InsufficientInstanceCapacity …") so the UI can explain WHY and the
            # auto-teardown path can act. Empty for healthy endpoints.
            "failure_reason": resp.get("FailureReason", "") if status == "Failed" else "",
        }
        _endpoint_status_cache[endpoint_name] = {"result": result, "time": _time.time()}
        return result
    except Exception as e:
        result = {"endpoint_name": endpoint_name, "status": "NotFound", "warming_up": False, "error": str(e)}
        _endpoint_status_cache[endpoint_name] = {"result": result, "time": _time.time()}
        return result


def teardown_endpoint(model_key: str, delete_s3: bool = False, endpoint_name: str = "") -> dict:
    """Delete an Amazon SageMaker endpoint, S3 artifacts, and HF token secret."""
    if not endpoint_name:
        # Look up from registry: try exact key first, then prefix match
        # (deployed keys have hash suffix, e.g., model_key_e64f)
        from .model_registry import get_registry
        reg = get_registry()
        for section in ["image_models", "video_models", "post_processing", "utility_models"]:
            entry = reg.get(section, {}).get(model_key, {})
            ep = entry.get("deployment", {}).get("endpoint_name", "")
            if ep:
                endpoint_name = ep
                break
            # Prefix match: catalog key → deployed instance key
            for key, entry in reg.get(section, {}).items():
                if key.startswith(model_key + "_") or key == model_key:
                    ep = entry.get("deployment", {}).get("endpoint_name", "")
                    if ep:
                        endpoint_name = ep
                        model_key = key
                        break
            if endpoint_name:
                break
        if not endpoint_name:
            endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
    clear_readiness_cache(endpoint_name)
    _endpoint_status_cache.pop(endpoint_name, None)
    sm_model_name = f"{endpoint_name}-model"
    config_name = f"{endpoint_name}-config"

    region = _get_region()
    sm = boto3.client("sagemaker", region_name=region)
    deleted = []

    # Auto-scaling: remove policies, alarms, and scalable target FIRST
    # (must happen before endpoint deletion or they become orphaned)
    resource_id = f"endpoint/{endpoint_name}/variant/primary"
    try:
        aas = boto3.client("application-autoscaling", region_name=region)
        policies = aas.describe_scaling_policies(
            ServiceNamespace="sagemaker", ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        )
        for p in policies.get("ScalingPolicies", []):
            aas.delete_scaling_policy(
                PolicyName=p["PolicyName"], ServiceNamespace="sagemaker",
                ResourceId=resource_id, ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            )
            deleted.append(f"scaling-policy:{p['PolicyName']}")
        aas.deregister_scalable_target(
            ServiceNamespace="sagemaker", ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        )
        deleted.append("scalable-target")
    except Exception:
        pass
    _auto_scaling_registered.discard(endpoint_name)

    # Cancel any keep-warm revert timer and clear the persisted warm marker
    # (the endpoint is going away — nothing left to revert or auto-bill).
    try:
        _timer = _warm_timers.pop(endpoint_name, None)
        if _timer is not None:
            _timer.cancel()
        from .model_registry import clear_warm_marker
        clear_warm_marker(endpoint_name)
    except Exception:
        pass

    try:
        cw = boto3.client("cloudwatch", region_name=region)
        alarms = cw.describe_alarms(AlarmNamePrefix=f"{endpoint_name}-")
        alarm_names = [a["AlarmName"] for a in alarms.get("MetricAlarms", [])]
        if alarm_names:
            cw.delete_alarms(AlarmNames=alarm_names)
            deleted.append(f"alarms:{alarm_names}")
    except Exception:
        pass

    try:
        sm.delete_endpoint(EndpointName=endpoint_name)
        deleted.append(f"endpoint:{endpoint_name}")
    except Exception as e:
        if "in-progress" in str(e).lower() or "cannot update" in str(e).lower():
            import time as _time
            logger.info("Endpoint %s is updating — waiting to retry deletion...", endpoint_name)
            for _attempt in range(10):
                _time.sleep(30)
                try:
                    desc = sm.describe_endpoint(EndpointName=endpoint_name)
                    if desc["EndpointStatus"] == "InService":
                        sm.delete_endpoint(EndpointName=endpoint_name)
                        deleted.append(f"endpoint:{endpoint_name}")
                        break
                except Exception:
                    break
            else:
                logger.warning("Failed to delete endpoint %s after retries: %s", endpoint_name, e)
        else:
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

    # ── Sweep ORPHANED configs/models/alarms from PRIOR deploys of this model ──
    # Each redeploy mints a fresh endpoint name with a new hash suffix
    # (artsmoker-<model>-<instance>-<hash>). Older deploys that failed or were
    # torn down incompletely leave behind their endpoint-config, model, and
    # backlog alarm (only the CURRENT endpoint's are named-deleted above).
    # Without this sweep they accumulate indefinitely.
    #
    # SAFETY — the criterion is ENDPOINT EXISTENCE, not age. An artifact is an
    # orphan iff NO endpoint that would use it exists. Two guards:
    #   1. EXACT sibling shape — the artifact's endpoint must be precisely
    #      "<base_prefix>-<single-hash-segment>". This stops a prefix-overlap
    #      false match where one model's name is a prefix of another's
    #      (e.g. tearing down qwen-image must NOT match qwen-image-edit-2511-*).
    #   2. NO ASSOCIATED ENDPOINT — the artifact's derived endpoint must exist in
    #      NEITHER of two sources, so we never delete a file some endpoint needs:
    #        (a) AWS list_endpoints — every lifecycle state (Creating, InService,
    #            Updating, Failed, RollingBack, …). Anything AWS knows about, in
    #            any state, is protected.
    #        (b) the REGISTRY's recorded endpoint_names — covers an in-flight
    #            deploy that has registered its endpoint but whose CreateEndpoint
    #            may not be visible in list_endpoints yet. This closes the
    #            deploy-sequence race by EXISTENCE (intended endpoint), not by a
    #            timer. Our deploy is a synchronous CreateModel→Config→Endpoint,
    #            so by the time any concurrent teardown enumerates + deletes, the
    #            endpoint is present in (a) or (b).
    # If the artifact's endpoint is in neither set, nothing needs the file → sweep.
    # Best-effort; never blocks teardown.
    try:
        # Base prefix = endpoint name minus the trailing "-<hash>" segment
        # (e.g. artsmoker-hunyuan-image-3-0-nf4-6928 → artsmoker-hunyuan-image-3-0-nf4)
        base_prefix = endpoint_name.rsplit("-", 1)[0] if "-" in endpoint_name else endpoint_name

        # (a) endpoints AWS knows about, in ANY state
        known_eps = set()
        try:
            _paginator = sm.get_paginator("list_endpoints")
            for _pg in _paginator.paginate():
                for _e in _pg.get("Endpoints", []):
                    known_eps.add(_e["EndpointName"])
        except Exception:
            pass
        # (b) endpoints the app has recorded/intends (covers in-flight deploys)
        try:
            from .model_registry import get_registry
            _reg = get_registry()
            for _sec in ("image_models", "video_models", "post_processing", "utility_models"):
                for _entry in _reg.get(_sec, {}).values():
                    _ep = (_entry.get("deployment") or {}).get("endpoint_name")
                    if _ep:
                        known_eps.add(_ep)
        except Exception:
            pass

        def _endpoint_of(name: str) -> str:
            if name.endswith("-config"):
                return name[:-len("-config")]
            if name.endswith("-model"):
                return name[:-len("-model")]
            if name.endswith("-has-backlog"):
                return name[:-len("-has-backlog")]
            return name

        def _is_exact_sibling(ep: str) -> bool:
            # ep must be EXACTLY base_prefix + "-" + one hash segment (no extra
            # model-name segments) → precludes matching a different, longer model.
            if not ep.startswith(base_prefix + "-"):
                return False
            tail = ep[len(base_prefix) + 1:]
            return bool(tail) and "-" not in tail

        def _safe_to_delete(artifact_name: str) -> bool:
            ep = _endpoint_of(artifact_name)
            if not _is_exact_sibling(ep):
                return False          # guard 1: exact sibling shape
            if ep in known_eps:
                return False          # guard 2: an endpoint exists/intends to use it
            return True

        # Orphaned endpoint-configs
        try:
            for _c in sm.list_endpoint_configs(NameContains=base_prefix, MaxResults=100).get("EndpointConfigs", []):
                cn = _c["EndpointConfigName"]
                if cn != config_name and _safe_to_delete(cn):
                    try:
                        sm.delete_endpoint_config(EndpointConfigName=cn)
                        deleted.append(f"orphan-config:{cn}")
                    except Exception:
                        pass
        except Exception:
            pass

        # Orphaned models
        try:
            for _m in sm.list_models(NameContains=base_prefix, MaxResults=100).get("Models", []):
                mn = _m["ModelName"]
                if mn != sm_model_name and _safe_to_delete(mn):
                    try:
                        sm.delete_model(ModelName=mn)
                        deleted.append(f"orphan-model:{mn}")
                    except Exception:
                        pass
        except Exception:
            pass

        # Orphaned backlog alarms
        try:
            cw = boto3.client("cloudwatch", region_name=region)
            orphan_alarms = []
            for _a in cw.describe_alarms(AlarmNamePrefix=base_prefix, MaxRecords=100).get("MetricAlarms", []):
                an = _a["AlarmName"]
                if _safe_to_delete(an):
                    orphan_alarms.append(an)
            if orphan_alarms:
                cw.delete_alarms(AlarmNames=orphan_alarms)
                deleted.append(f"orphan-alarms:{len(orphan_alarms)}")
        except Exception:
            pass
    except Exception as exc:
        logger.debug("Orphan sweep skipped for %s: %s", endpoint_name, exc)

    if delete_s3:
        try:
            bucket = get_deployment_s3_bucket()
            s3 = boto3.resource("s3", region_name=_get_region())
            bucket_obj = s3.Bucket(bucket)
            # Clean the model artifacts/cache AND the async inference I/O paths.
            # Async input is keyed by endpoint_name; output is keyed by the
            # catalog_key (base, e.g. "triposg"). Clean instance key and catalog
            # key to be safe.
            # Resolve the CATALOG key. The model-cache and (for HF models) the
            # handler artifacts are written under the catalog key, NOT the deployed
            # instance key (the deployer's ARTSMOKER_CACHE_PREFIX uses the catalog
            # key). Prefer the registry's recorded catalog_key; else derive it by
            # matching the instance key against known catalog keys (instance keys are
            # "<catalog_key>_<hash>"). Without this, a delete_s3 teardown leaves the
            # cache at {catalog_key}/model-cache/ behind, and a later redeploy silently
            # reuses those STALE quantized weights instead of re-quantizing fresh.
            catalog_key = ""
            try:
                from .model_registry import get_registry as _gr
                _reg = _gr()
                for _sec in ["image_models", "video_models", "post_processing", "utility_models"]:
                    _entry = _reg.get(_sec, {}).get(model_key, {})
                    if _entry:
                        catalog_key = _entry.get("catalog_key", "")
                        break
            except Exception:
                pass
            if not catalog_key:
                try:
                    from .custom_models import get_catalog as _gc
                    _cat = _gc()
                    _cat_keys = set(_cat.get("models", _cat).keys())
                    if model_key in _cat_keys:
                        catalog_key = model_key
                    else:
                        for _ck in _cat_keys:
                            if model_key.startswith(_ck + "_"):
                                catalog_key = _ck
                                break
                except Exception:
                    pass
            prefixes = [
                f"{S3_MODEL_PREFIX}/{model_key}/",
                f"{S3_MODEL_PREFIX}/inference-input/{endpoint_name}/",
                f"{S3_MODEL_PREFIX}/inference-output/{model_key}/",
            ]
            # Clean the catalog-key artifacts + model-cache too (the cache lives at
            # {catalog_key}/model-cache/). This is the fix for stale-cache reuse.
            if catalog_key and catalog_key != model_key:
                prefixes.append(f"{S3_MODEL_PREFIX}/{catalog_key}/")
                prefixes.append(f"{S3_MODEL_PREFIX}/inference-output/{catalog_key}/")
            for prefix in prefixes:
                bucket_obj.objects.filter(Prefix=prefix).delete()
                deleted.append(f"s3:{bucket}/{prefix}")
        except Exception as e:
            logger.warning("Failed to delete S3 artifacts: %s", e)

    # Clean async jobs — both in-memory and S3-persisted
    try:
        from backend.services.async_jobs import _jobs
        job_keys = [k for k, v in _jobs.items()
                    if model_key in str(v.get("model_key", ""))
                    or endpoint_name in str(v.get("endpoint_name", ""))]
        for k in job_keys:
            del _jobs[k]
        if job_keys:
            deleted.append(f"async-jobs-memory:{len(job_keys)}")

        bucket_name = get_deployment_s3_bucket()
        if bucket_name:
            s3_client = boto3.client("s3", region_name=_get_region())
            # Clean both the 2D async-jobs and 3D-jobs persisted records that
            # belong to this model/endpoint.
            for _prefix in ("artsmoker/async-jobs/", "artsmoker/3d-jobs/"):
                resp = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=_prefix)
                for obj in resp.get("Contents", []):
                    try:
                        body = s3_client.get_object(Bucket=bucket_name, Key=obj["Key"])
                        job_data = json.loads(body["Body"].read())
                        if (model_key in str(job_data.get("model_key", ""))
                                or endpoint_name in str(job_data.get("endpoint_name", ""))):
                            s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                            deleted.append(f"job-s3:{obj['Key']}")
                    except Exception:
                        pass
    except Exception as e:
        logger.debug("Async job cleanup during teardown: %s", e)

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


# ── S3 Model Cache Helpers ──────────────────────────────────────────────

_CACHE_SUBFOLDER = "model-cache"


def check_model_cache_exists(model_key: str) -> dict:
    """Check if an S3 model cache exists for the given model."""
    bucket = get_deployment_s3_bucket()
    if not bucket:
        return {"cached": False}

    try:
        s3 = boto3.client("s3", region_name=_get_region())
        info_key = f"{S3_MODEL_PREFIX}/{model_key}/{_CACHE_SUBFOLDER}/.cache-info.json"
        resp = s3.get_object(Bucket=bucket, Key=info_key)
        cache_info = json.loads(resp["Body"].read().decode())
        return {
            "cached": True,
            "saved_at": cache_info.get("saved_at", ""),
            "version_key": cache_info.get("version_key", ""),
            "model_key": cache_info.get("model_key", ""),
            "library": cache_info.get("library", ""),
        }
    except Exception:
        return {"cached": False}


def invalidate_model_cache(model_key: str) -> dict:
    """Delete the S3 model cache, forcing a fresh download on next deploy."""
    bucket = get_deployment_s3_bucket()
    if not bucket:
        return {"deleted": False, "reason": "no bucket"}

    try:
        s3 = boto3.resource("s3", region_name=_get_region())
        prefix = f"{S3_MODEL_PREFIX}/{model_key}/{_CACHE_SUBFOLDER}/"
        bucket_obj = s3.Bucket(bucket)
        objects = list(bucket_obj.objects.filter(Prefix=prefix))
        if not objects:
            return {"deleted": False, "reason": "no cache found"}
        bucket_obj.objects.filter(Prefix=prefix).delete()
        logger.info("Invalidated model cache for %s: %d files deleted", model_key, len(objects))
        return {"deleted": True, "files": len(objects)}
    except Exception as e:
        return {"deleted": False, "reason": str(e)}


# Track which endpoints already have auto-scaling registered to avoid duplicates
_auto_scaling_registered: set[str] = set()
# Build-only endpoints — skip auto-scaling entirely (manual teardown after cache save)
_build_only_endpoints: set[str] = set()


def get_endpoint_health(endpoint_name: str) -> dict:
    """Check if an endpoint is alive and making progress.

    Returns a health assessment for use by the async job poller to decide
    whether to keep waiting or give up on pending jobs.

    Returns:
        {
            "alive": bool,       # Endpoint exists and is in a working state
            "progressing": bool,  # Actively loading model or processing
            "ready": bool,       # Model loaded and ready for inference
            "failed": bool,      # Confirmed failure (OOM, code error, etc.)
            "detail": str,       # Human-readable status
            "stale_seconds": int, # Seconds since last meaningful log activity
        }
    """
    import time as _time

    try:
        status_info = check_endpoint_status(endpoint_name)
    except Exception:
        return {"alive": False, "progressing": False, "ready": False, "failed": False,
                "detail": "Cannot reach endpoint", "stale_seconds": 0}

    ep_status = status_info.get("status", "NotFound")
    instances = status_info.get("instance_count", 0)
    warming = status_info.get("warming_up", False)

    # Endpoint gone or failed
    if ep_status in ("Failed", "NotFound"):
        return {"alive": False, "progressing": False, "ready": False, "failed": True,
                "detail": f"Endpoint {ep_status}", "stale_seconds": 0}

    # Endpoint is creating or updating (scaling out)
    if ep_status in ("Creating", "Updating"):
        return {"alive": True, "progressing": True, "ready": False, "failed": False,
                "detail": "Scaling out...", "stale_seconds": 0}

    # InService, no instances, but scale-out already REQUESTED (desired>current):
    # provisioning is in flight or blocked (e.g. InsufficientInstanceCapacity).
    # Report progressing — resubmitting cannot help until an instance lands, so
    # the resubmit path must WAIT here instead of burning its retry budget.
    if ep_status == "InService" and instances == 0 and status_info.get("desired_instance_count", 0) > 0:
        return {"alive": True, "progressing": True, "ready": False, "failed": False,
                "detail": "Scale-out requested — waiting for capacity", "stale_seconds": 0}

    # InService but no instances — scaled to zero, waiting for auto-scale
    if ep_status == "InService" and instances == 0:
        return {"alive": True, "progressing": False, "ready": False, "failed": False,
                "detail": "Scaled to zero — waiting for scale-out", "stale_seconds": 0}

    # InService with instances — check model readiness via logs
    if ep_status == "InService" and instances > 0:
        if not warming:
            return {"alive": True, "progressing": False, "ready": True, "failed": False,
                    "detail": "Ready", "stale_seconds": 0}

        # Model is loading — scan logs for progress and staleness
        readiness = _scan_logs_for_readiness(endpoint_name)

        if readiness.get("failed"):
            return {"alive": True, "progressing": False, "ready": False, "failed": True,
                    "detail": readiness.get("detail", "Failed"), "stale_seconds": 0}

        # Compute staleness from last log activity
        last_ms = readiness.get("last_activity_ms") or 0
        stale_seconds = int(_time.time() - last_ms / 1000) if last_ms else 0

        return {"alive": True, "progressing": True, "ready": False, "failed": False,
                "detail": readiness.get("detail", "Loading..."), "stale_seconds": stale_seconds}

    return {"alive": True, "progressing": False, "ready": False, "failed": False,
            "detail": f"Status: {ep_status}", "stale_seconds": 0}


def _compute_container_timeout(model: dict) -> int:
    """Compute MMS container timeout based on model characteristics.

    The timeout must cover both model loading and inference. For models with
    quantization or large parameter counts, loading can take much longer than
    inference. We compute based on available signals from the catalog.
    """
    invoke = model.get("invoke", {})
    reqs = model.get("requirements", {})

    # Inference time
    typical_latency = invoke.get("typical_latency_seconds", 300)

    # Model loading signals: quantization, VRAM requirements, source type
    has_quantization = bool(invoke.get("quantization_components"))
    min_vram = reqs.get("min_vram_gb", 0)
    source_type = model.get("source", {}).get("type", "")

    # Estimate load time based on model characteristics
    if min_vram >= 100:
        # Very large model (e.g. 80B bf16 ~160 GB) — download + load + kernel compilation
        estimated_load = 4800  # 80 min
    elif has_quantization and min_vram >= 24:
        # Large quantized model (e.g. FLUX.2 dev 32B) — loading alone can take 60+ min
        estimated_load = 4800  # 80 min
    elif has_quantization:
        # Smaller quantized model
        estimated_load = 1800  # 30 min
    elif min_vram >= 24:
        # Large model without quantization
        estimated_load = 2400  # 40 min
    elif source_type == "huggingface":
        # Standard HF model — download + load
        estimated_load = 900  # 15 min
    else:
        # Pre-bundled or small model
        estimated_load = 600  # 10 min

    # Timeout = max(load estimate, 3x inference time) — covers both phases
    timeout = max(estimated_load, typical_latency * 3)
    return timeout


def _deregister_auto_scaling_during_load(endpoint_name: str):
    """Remove auto-scaling while the model is loading after a scale-out.

    Without this, the scale-in policy could kill the instance mid-load
    (cooldown starts from the scale-out activity, and model load may exceed it).
    Auto-scaling is re-registered by _register_auto_scaling_after_ready() once
    the readiness monitor confirms the model is fully loaded.
    """
    if endpoint_name not in _auto_scaling_registered:
        return

    try:
        region = _get_region()
        aas = boto3.client("application-autoscaling", region_name=region)
        resource_id = f"endpoint/{endpoint_name}/variant/primary"

        # Remove scaling policies first
        policies = aas.describe_scaling_policies(
            ServiceNamespace="sagemaker", ResourceId=resource_id,
        )
        for p in policies.get("ScalingPolicies", []):
            aas.delete_scaling_policy(
                PolicyName=p["PolicyName"],
                ServiceNamespace="sagemaker",
                ResourceId=resource_id,
                ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            )

        # Deregister the scalable target
        aas.deregister_scalable_target(
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        )
        _auto_scaling_registered.discard(endpoint_name)
        logger.info("Auto-scaling paused for %s — model loading, will re-register when ready", endpoint_name)
    except Exception as e:
        logger.debug("Auto-scaling deregister for %s: %s", endpoint_name, e)


def _register_auto_scaling_after_ready(endpoint_name: str):
    """Register auto-scaling AFTER the model is confirmed ready.

    Called from the readiness monitor or quick log scan. This ensures
    the scale-to-zero policy is only applied once the model is loaded,
    preventing scale-in from killing instances during long model loads.

    Idempotent: checks AWS for existing policies before registering.
    """
    if endpoint_name in _auto_scaling_registered:
        return  # Already registered this session

    if endpoint_name in _build_only_endpoints:
        logger.info("Skipping auto-scaling for %s — build-only deploy (cache save in progress)", endpoint_name)
        return

    # Check if auto-scaling already exists in AWS (survives server restarts)
    try:
        import boto3
        aas = boto3.client("application-autoscaling", region_name=_get_region())
        resource_id = f"endpoint/{endpoint_name}/variant/primary"
        resp = aas.describe_scaling_policies(
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        )
        if resp.get("ScalingPolicies"):
            _auto_scaling_registered.add(endpoint_name)
            logger.debug("Auto-scaling already configured for %s — skipping", endpoint_name)
            return
    except Exception:
        pass  # If check fails, proceed with registration attempt

    # Compute cooldown from model config.
    # Endpoint name has a hash suffix (e.g., "...-int8-620a") that the catalog key lacks.
    # Try full key, then strip the hash suffix, searching both catalog and nested "models".
    from .custom_models import get_catalog
    catalog = get_catalog()
    model_key = endpoint_name.replace("artsmoker-", "").replace("-", "_")
    base_key = "_".join(model_key.rsplit("_", 1)[:-1])
    model = (catalog.get(model_key) or catalog.get(base_key)
             or catalog.get("models", {}).get(model_key)
             or catalog.get("models", {}).get(base_key) or {})
    invoke = model.get("invoke", {})
    typical = invoke.get("typical_latency_seconds", 300)
    cooldown = max(600, typical * 2)

    try:
        _setup_auto_scaling(endpoint_name, scale_in_cooldown=cooldown)
        _auto_scaling_registered.add(endpoint_name)
        logger.info("Auto-scaling configured for %s (scale to zero + scale from zero)", endpoint_name)
        logger.info("Auto-scaling registered for %s (cooldown=%ds) — model confirmed ready", endpoint_name, cooldown)
        _apply_deploy_scale_in_grace(endpoint_name)
    except Exception as e:
        logger.warning("Auto-scaling setup failed for %s after model ready: %s — retrying in background", endpoint_name, e)
        _retry_auto_scaling_in_background(endpoint_name, scale_in_cooldown=cooldown)


def _apply_deploy_scale_in_grace(endpoint_name: str):
    """Protect a freshly-ready endpoint from scaling to zero before its first job.

    A brand-new endpoint has zero traffic, so the scale-to-zero alarm fires within
    ~1 min of going live and can drain the instance just as the user's first job
    arrives (observed: a job's instance killed mid-inference, recovered only via
    the backlog/scale-from-zero self-heal after a multi-minute stall). The
    ScaleInCooldown gates only the interval BETWEEN scale-ins, not this first one.

    Fix: pin MinCapacity=1 for settings.deploy_scale_in_grace_minutes, then
    auto-revert to 0 (normal scale-to-zero resumes). Reuses the keep-warm
    machinery (marker + revert timer) so a server restart is covered too. No-op
    if the grace is 0 or a warm pin is already active.
    """
    try:
        from backend.config import settings
        grace_min = getattr(settings, "deploy_scale_in_grace_minutes", 0) or 0
        if grace_min <= 0:
            return
        from .model_registry import get_warm_markers
        if get_warm_markers().get(endpoint_name):
            return  # already pinned (explicit keep-warm) — don't shorten its window
        model_key = endpoint_name.replace("artsmoker-", "").replace("-", "_")
        # Reuse set_keep_warm: pins MinCapacity=1, persists a marker, schedules the
        # auto-revert. Bounded, self-reverting, restart-safe.
        set_keep_warm(model_key, hours=grace_min / 60.0,
                      endpoint_name=endpoint_name, extend_window=False)
        logger.info("Deploy scale-in grace: pinned %s warm for %d min (protects first job)",
                    endpoint_name, grace_min)
    except Exception as e:
        logger.debug("Deploy scale-in grace skipped for %s: %s", endpoint_name, e)


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
            "Cooldown": 60,
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


# ── Dev keep-warm (pin an instance during local iteration) ─────────────────
#
# A deployed g6e/g5 instance is hard to acquire (capacity scarcity). During dev
# iteration we don't want to lose it to scale-in between test jobs, nor leave it
# billing all day. Keep-warm pins MinCapacity=1 for a bounded window (default
# 8 hours) and schedules an automatic revert to normal scale-to-zero autoscaling.
# A persisted marker (model_registry.user.json "_warm_mode") lets the revert
# survive a server restart, so a dev box can never silently bill forever.
#
# These functions are gated to dev-mode by the router; they make no change to
# production behavior on their own.

# In-process revert timers, keyed by endpoint_name → threading.Timer
_warm_timers: dict = {}

# Default keep-warm window — long enough for a full day of dev iteration,
# short enough to bound accidental cost. Overridable per call.
DEFAULT_WARM_HOURS = 8


def resolve_endpoint_name(model_key: str) -> str:
    """Resolve a deployed endpoint name from a model/catalog key.

    Mirrors the registry lookup teardown_endpoint() uses: exact key first,
    then prefix match (deployed instance keys carry a hash suffix, e.g.
    "triposg_cd45"). Returns "" if no deployed endpoint is found.
    """
    from .model_registry import get_registry
    reg = get_registry()
    for section in ["image_models", "video_models", "post_processing", "utility_models"]:
        entry = reg.get(section, {}).get(model_key, {})
        ep = entry.get("deployment", {}).get("endpoint_name", "")
        if ep:
            return ep
        for key, entry in reg.get(section, {}).items():
            if key.startswith(model_key + "_") or key == model_key:
                ep = entry.get("deployment", {}).get("endpoint_name", "")
                if ep:
                    return ep
    return ""


def _set_min_capacity(endpoint_name: str, min_capacity: int):
    """Update the scalable target's MinCapacity, preserving MaxCapacity=1.

    Requires the scalable target to already exist (registered by
    _setup_auto_scaling once the model is ready). Raises if it doesn't.
    """
    aas = boto3.client("application-autoscaling", region_name=_get_region())
    resource_id = f"endpoint/{endpoint_name}/variant/primary"
    # Confirm the scalable target exists — keep-warm only makes sense on a
    # ready endpoint that already has scale-to-zero autoscaling.
    resp = aas.describe_scalable_targets(
        ServiceNamespace="sagemaker",
        ResourceIds=[resource_id],
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
    )
    if not resp.get("ScalableTargets"):
        raise RuntimeError(
            f"No scalable target for {endpoint_name} — endpoint not ready "
            "or auto-scaling not yet registered. Wait for the model to load."
        )
    aas.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=min_capacity,
        MaxCapacity=1,
    )


def set_keep_warm(model_key: str, hours: float = DEFAULT_WARM_HOURS,
                  endpoint_name: str = "", extend_window: bool = True) -> dict:
    """Pin an endpoint warm (MinCapacity=1) for `hours`, then auto-revert.

    Sets MinCapacity=1 so SageMaker keeps one instance running and the
    scale-to-zero policy can't kill it. Persists a warm marker and schedules
    an automatic revert to normal autoscaling after the window elapses.

    extend_window:
      True  (explicit /keep-warm call) — (re)set the window to now + hours.
      False (auto-trigger from a job)  — if a warm marker already exists, keep
            its original expiry untouched (the window is NOT cumulative; we
            stick with the first one set). Only create a window if none exists.

    Dev-mode only — the router/caller enforces this.
    """
    if not endpoint_name:
        endpoint_name = resolve_endpoint_name(model_key)
    if not endpoint_name:
        raise RuntimeError(f"No deployed endpoint found for {model_key}")

    hours = max(0.05, float(hours))  # floor at 3 minutes; guard against 0/negative

    from .model_registry import get_warm_markers, set_warm_marker
    existing = get_warm_markers().get(endpoint_name)

    # Non-extending auto-trigger with a live window: re-assert MinCapacity=1
    # (cheap, idempotent) but leave the original expiry in place.
    if existing and not extend_window:
        try:
            expires = datetime.fromisoformat(existing.get("expires_at", ""))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires > datetime.now(timezone.utc):
                _set_min_capacity(endpoint_name, 1)
                # Ensure a revert timer is armed (e.g., after a restart it may not be).
                if endpoint_name not in _warm_timers:
                    _schedule_warm_revert(
                        endpoint_name,
                        (expires - datetime.now(timezone.utc)).total_seconds(),
                    )
                logger.info("Keep-warm: %s already warm until %s — window unchanged",
                            endpoint_name, existing.get("expires_at"))
                return {
                    "status": "warm",
                    "endpoint_name": endpoint_name,
                    "model_key": model_key,
                    "expires_at": existing.get("expires_at"),
                    "revert_cooldown_seconds": existing.get("cooldown_seconds"),
                    "window_unchanged": True,
                }
        except Exception:
            pass  # malformed marker — fall through and set a fresh window

    _set_min_capacity(endpoint_name, 1)

    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    expires_iso = expires.isoformat()

    # Cooldown to restore on revert — derive from catalog like the normal path.
    cooldown = _warm_revert_cooldown(endpoint_name)

    set_warm_marker(endpoint_name, model_key, expires_iso, cooldown)
    _schedule_warm_revert(endpoint_name, hours * 3600.0)

    logger.info("Keep-warm: %s pinned MinCapacity=1 until %s (%.1fh)",
                endpoint_name, expires_iso, hours)
    return {
        "status": "warm",
        "endpoint_name": endpoint_name,
        "model_key": model_key,
        "hours": hours,
        "expires_at": expires_iso,
        "revert_cooldown_seconds": cooldown,
    }


def reset_warm_mode(model_key: str, cooldown_seconds: int | None = None,
                    endpoint_name: str = "") -> dict:
    """Revert an endpoint to normal scale-to-zero autoscaling immediately.

    Sets MinCapacity=0 (so the instance scales in once idle), cancels any
    pending revert timer, and clears the persisted warm marker. Use mid-window
    to stop billing when you no longer need the warm box.
    """
    if not endpoint_name:
        endpoint_name = resolve_endpoint_name(model_key)
    if not endpoint_name:
        raise RuntimeError(f"No deployed endpoint found for {model_key}")

    # Capture the marker (before it's cleared) — needed for both the cooldown and
    # the actual warm-window cost accounting below.
    from .model_registry import get_warm_markers
    marker = get_warm_markers().get(endpoint_name, {}) or {}
    if cooldown_seconds is None:
        # Prefer the cooldown recorded when warm was set; fall back to catalog.
        cooldown_seconds = marker.get("cooldown_seconds") or _warm_revert_cooldown(endpoint_name)

    # Cancel any in-process revert timer.
    timer = _warm_timers.pop(endpoint_name, None)
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            pass

    _set_min_capacity(endpoint_name, 0)
    # Re-assert the scale-to-zero target tracking cooldown (idempotent).
    try:
        _setup_auto_scaling(endpoint_name, scale_in_cooldown=int(cooldown_seconds))
    except Exception as e:
        logger.warning("reset_warm_mode: re-applying autoscaling for %s failed: %s",
                       endpoint_name, e)

    # ── Keep-warm cost accounting ───────────────────────────────────────────
    # A pinned endpoint bills one instance for the whole warm window (up to 8h of
    # GPU time) — previously untracked. On revert, price the ACTUAL warm duration
    # (marker.set_at → now) at the deployed instance's per-region rate and record
    # it as background infra cost + a telemetry event. Non-fatal.
    try:
        set_at = marker.get("set_at", "")
        mkey = marker.get("model_key") or model_key
        if set_at:
            warmed = datetime.fromisoformat(set_at)
            if warmed.tzinfo is None:
                warmed = warmed.replace(tzinfo=timezone.utc)
            warm_seconds = max(0.0, (datetime.now(timezone.utc) - warmed).total_seconds())
            from .model_registry import get_registry
            from .custom_models import get_instance_hourly_rate
            reg = get_registry()
            inst, dep_region = "", ""
            for section in ("image_models", "video_models", "post_processing"):
                dep = reg.get(section, {}).get(mkey, {}).get("deployment", {}) if mkey else {}
                if dep.get("instance_type"):
                    inst, dep_region = dep["instance_type"], dep.get("region", "")
                    break
            rate = get_instance_hourly_rate(inst, None, dep_region)
            warm_cost = round((warm_seconds / 3600.0) * rate, 6) if rate else 0.0
            if warm_cost > 0:
                from .cost_tracker import add_background_cost
                add_background_cost("keep_warm_infra", warm_cost,
                                    f"{mkey} keep-warm {warm_seconds/3600:.2f}h @ ${rate:.2f}/hr")
                from .telemetry import track_custom_model_invoke
                track_custom_model_invoke(model=mkey, cost_usd=warm_cost,
                                          latency_ms=int(warm_seconds * 1000),
                                          predictor_type="keep_warm")
    except Exception as e:
        logger.debug("Keep-warm cost accounting failed for %s: %s", endpoint_name, e)

    from .model_registry import clear_warm_marker
    clear_warm_marker(endpoint_name)

    logger.info("Reset-warm: %s reverted to MinCapacity=0 (scale-in cooldown=%ss)",
                endpoint_name, cooldown_seconds)
    return {
        "status": "normal",
        "endpoint_name": endpoint_name,
        "model_key": model_key,
        "scale_in_cooldown_seconds": int(cooldown_seconds),
    }


def _warm_revert_cooldown(endpoint_name: str) -> int:
    """Compute the scale-in cooldown to restore on revert (catalog-derived)."""
    try:
        from .custom_models import get_catalog
        catalog = get_catalog()
        model_key = endpoint_name.replace("artsmoker-", "").replace("-", "_")
        base_key = "_".join(model_key.rsplit("_", 1)[:-1])
        model = (catalog.get(model_key) or catalog.get(base_key)
                 or catalog.get("models", {}).get(model_key)
                 or catalog.get("models", {}).get(base_key) or {})
        typical = model.get("invoke", {}).get("typical_latency_seconds", 300)
        return max(600, typical * 2)
    except Exception:
        return 600


def _schedule_warm_revert(endpoint_name: str, delay_seconds: float):
    """Schedule an in-process timer to auto-revert keep-warm after the window.

    Restart-safety does NOT depend on this timer — the persisted marker plus
    resume_warm_markers() at startup covers a server restart. This timer is the
    fast path for a long-running process.
    """
    import threading

    # Replace any existing timer for this endpoint.
    existing = _warm_timers.pop(endpoint_name, None)
    if existing is not None:
        try:
            existing.cancel()
        except Exception:
            pass

    def _revert():
        _warm_timers.pop(endpoint_name, None)
        try:
            # model_key is informational here; endpoint_name drives the revert.
            reset_warm_mode("", endpoint_name=endpoint_name)
            logger.info("Keep-warm window elapsed — auto-reverted %s", endpoint_name)
        except Exception as e:
            logger.warning("Auto-revert of keep-warm for %s failed: %s", endpoint_name, e)

    t = threading.Timer(delay_seconds, _revert)
    t.daemon = True
    t.name = f"warm-revert-{endpoint_name}"
    t.start()
    _warm_timers[endpoint_name] = t


def dev_overlay_s3_key(model_key: str) -> str:
    """S3 key for a model's dev hot-reload overlay archive."""
    return f"{S3_MODEL_PREFIX}/{model_key}/dev/overlay.tar.gz"


def push_dev_overlay(model_key: str) -> dict:
    """Package the current handler + bundled packages and stage them in S3.

    Builds an overlay.tar.gz with the SAME layout the deploy packager uses
    (rooted at "code/": inference.py + each bundled package for this model's
    library), and uploads it to the model's dev overlay key. The warm endpoint's
    handler detects the new ETag on the next inference and hot-reloads it.

    Model-agnostic: bundles whatever _LIBRARY_BUNDLED_PACKAGES maps the model's
    library to (empty for models with no bundled packages — then the overlay is
    just inference.py, which is still a valid hot-reload).
    """
    import shutil
    import tarfile

    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise RuntimeError("No S3 bucket configured for dev overlay.")

    handlers_dir = Path(__file__).resolve().parent.parent / "sagemaker_handlers"
    src_handler = handlers_dir / "inference.py"
    if not src_handler.exists():
        raise FileNotFoundError(f"Inference handler not found: {src_handler}")

    # Resolve bundled packages for this model's library. The arg may be a
    # DEPLOYED instance key (e.g. "triposg_9c88") which is NOT a catalog key;
    # map it to its catalog model via the registry's catalog_key field, then
    # fall back to stripping the hash suffix, then the raw key.
    from .custom_models import get_catalog_model
    catalog_key = model_key
    try:
        from .model_registry import get_registry
        reg = get_registry()
        for section in ("image_models", "video_models", "post_processing", "utility_models"):
            entry = reg.get(section, {}).get(model_key, {})
            if entry.get("catalog_key"):
                catalog_key = entry["catalog_key"]
                break
    except Exception:
        pass
    catalog_model = (get_catalog_model(catalog_key)
                     or get_catalog_model("_".join(model_key.rsplit("_", 1)[:-1]))
                     or get_catalog_model(model_key))
    library = (catalog_model or {}).get("invoke", {}).get("library", "")
    packages = _LIBRARY_BUNDLED_PACKAGES.get(library, [])

    temp_dir = Path(tempfile.mkdtemp(prefix=f"artsmoker_overlay_{model_key}_"))
    try:
        code_dir = temp_dir / "code"
        code_dir.mkdir()
        shutil.copy2(str(src_handler), str(code_dir / "inference.py"))

        bundled_dir = handlers_dir / "bundled_packages"
        bundled = []
        for pkg in packages:
            pkg_src = bundled_dir / pkg
            if pkg_src.is_dir():
                shutil.copytree(str(pkg_src), str(code_dir / pkg))
                bundled.append(pkg)

        tar_path = temp_dir / "overlay.tar.gz"
        with tarfile.open(str(tar_path), "w:gz") as tar:
            tar.add(str(code_dir), arcname="code")

        # The overlay MUST land at the key the running container watches
        # (ARTSMOKER_HOTRELOAD_KEY, baked from the container's MODEL_KEY at
        # deploy). MODEL_KEY is the CATALOG key (e.g. "triposg"), not the
        # deployed instance key ("triposg_9c88"), so push to the catalog-key
        # path — otherwise the container never sees the overlay.
        overlay_model_key = catalog_key or model_key
        key = dev_overlay_s3_key(overlay_model_key)
        s3 = boto3.client("s3", region_name=_get_region())
        s3.upload_file(str(tar_path), bucket, key)
        size = tar_path.stat().st_size
    finally:
        import shutil as _sh
        _sh.rmtree(str(temp_dir), ignore_errors=True)

    logger.info("Dev overlay pushed for %s → s3://%s/%s (%d bytes, packages=%s)",
                model_key, bucket, key, size, bundled)
    return {
        "status": "pushed",
        "model_key": model_key,
        "s3_uri": f"s3://{bucket}/{key}",
        "bytes": size,
        "bundled_packages": bundled,
        "note": "Applied on the next inference to the warm endpoint.",
    }


def clear_dev_overlay(model_key: str) -> dict:
    """Remove a model's dev overlay from S3 (handler reverts to deployed code)."""
    bucket = get_deployment_s3_bucket()
    if not bucket:
        return {"status": "noop", "reason": "no bucket"}
    key = dev_overlay_s3_key(model_key)
    try:
        boto3.client("s3", region_name=_get_region()).delete_object(Bucket=bucket, Key=key)
    except Exception as e:
        return {"status": "error", "reason": str(e)}
    logger.info("Dev overlay cleared for %s (s3://%s/%s)", model_key, bucket, key)
    return {"status": "cleared", "model_key": model_key, "s3_uri": f"s3://{bucket}/{key}"}


def resume_warm_markers():
    """On server startup, honor persisted keep-warm markers.

    For each marker: if the window already elapsed, revert immediately
    (prevents billing forever after a crash). Otherwise re-arm the in-process
    revert timer for the remaining time. Safe to call when no markers exist.
    """
    try:
        from .model_registry import get_warm_markers
        markers = get_warm_markers()
    except Exception as e:
        logger.debug("resume_warm_markers: could not read markers: %s", e)
        return

    if not markers:
        return

    now = datetime.now(timezone.utc)
    for endpoint_name, marker in list(markers.items()):
        try:
            expires_at = marker.get("expires_at", "")
            expires = datetime.fromisoformat(expires_at) if expires_at else now
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            remaining = (expires - now).total_seconds()
            model_key = marker.get("model_key", "")
            if remaining <= 0:
                logger.info("Keep-warm marker for %s already expired — reverting", endpoint_name)
                reset_warm_mode(model_key, endpoint_name=endpoint_name)
            else:
                logger.info("Keep-warm marker for %s resumed — %.1fh remaining",
                            endpoint_name, remaining / 3600.0)
                _schedule_warm_revert(endpoint_name, remaining)
        except Exception as e:
            logger.warning("resume_warm_markers: failed for %s: %s", endpoint_name, e)


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
                           hf_token: str | None = None,
                           texture_backend: str | None = None) -> dict:
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
        # Invoke config as JSON for the container handler. SageMaker silently truncates
        # env vars — strip fields the handler doesn't need to stay well under the limit.
        # Handler needs: library, loader_class, torch_dtype, quantization_components,
        # predictor_type, output_type, enable_vae_slicing, max_concurrent_invocations.
        # Handler does NOT need: prompt_guidance, input_fields, supports_negative_prompt,
        # max_prompt_length, typical_latency_seconds (all server-side only).
        "INVOKE_CONFIG": json.dumps(
            {k: v for k, v in invoke.items() if k not in (
                "prompt_guidance", "input_fields", "supports_negative_prompt",
                "max_prompt_length", "typical_latency_seconds", "supported_sizes",
            )},
            default=str,
        ),
        # CUDA memory management
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        # MMS response size limit — default is 6.5 MB, insufficient for 3D meshes
        # (GLB files can be 10-50 MB). Set to 100 MB for all models.
        "MMS_MAX_RESPONSE_SIZE": "104857600",
        # Single MMS worker — large models (FLUX.2) need all available RAM/VRAM.
        # Multiple workers compete for resources and cause OOM or worker kills.
        "SAGEMAKER_MODEL_SERVER_WORKERS": "1",
        # Container/inference timeout. MMS's default_response_timeout governs how
        # long a single /invocations request may run before the worker is deemed
        # unresponsive and rebooted (the request 500s). The HF DLC's prepacked
        # config.properties hardcodes a default (~11 min observed), so we must
        # override it explicitly. We set it three ways for robustness across DLC
        # versions:
        #   1. SAGEMAKER_MODEL_SERVER_TIMEOUT — sagemaker-inference maps this to
        #      config.properties default_response_timeout.
        #   2. SAGEMAKER_MODEL_SERVER_TIMEOUT_SECONDS — the finer-grained key that
        #      is appended last and takes precedence in newer toolkits.
        #   3. enable_envvars_config + MMS_DEFAULT_RESPONSE_TIMEOUT — lets MMS read
        #      the property straight from the env, bypassing the prepacked file.
        # All set from the catalog (image_to_3d depth-9 geometry alone is ~11 min
        # on a 4-vCPU instance, so this must be generous).
        "SAGEMAKER_MODEL_SERVER_TIMEOUT": str(_compute_container_timeout(model)),
        "SAGEMAKER_MODEL_SERVER_TIMEOUT_SECONDS": str(_compute_container_timeout(model)),
        "MMS_DEFAULT_RESPONSE_TIMEOUT": str(_compute_container_timeout(model)),
        "MMS_ENABLE_ENVVARS_CONFIG": "true",
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
    # Grain-debug lever: upcast only the VAE to fp32 at decode (cheap; the VAE is
    # tiny). Catalog opt-in so we can A/B it against the NF4-dtype fix on redeploy.
    if invoke.get("vae_upcast_fp32"):
        env["VAE_UPCAST_FP32"] = "true"

    # S3 model cache — handler saves quantized weights after first load,
    # loads from cache on subsequent cold starts (skips HF download + quantization)
    bucket = get_deployment_s3_bucket()
    if bucket:
        env["ARTSMOKER_CACHE_BUCKET"] = bucket
        env["ARTSMOKER_CACHE_PREFIX"] = f"{S3_MODEL_PREFIX}/{model_key}/model-cache"
        env["ARTSMOKER_CACHE_VERSION"] = model.get("version", "1.0")

    # Texture pipeline diagnostics — uploads intermediate multi-view artifacts
    # to S3 for inspection. Toggle via ARTSMOKER_TEXTURE_DEBUG on the server.
    if os.environ.get("ARTSMOKER_TEXTURE_DEBUG") == "1":
        env["ARTSMOKER_TEXTURE_DEBUG"] = "1"

    # Texturing backend baked into the endpoint: "trellis2" (default) or
    # "hunyuan" (or the retired "mvadapter" fallback). Sets which backend's native
    # ops are built + which pipe is preloaded at model load. Per-request
    # texture_backend still overrides at
    # inference. Source order: the user's per-DEPLOY choice (texture_backend arg,
    # from the deploy dialog) wins; else catalog invoke.texture_backend (survives
    # server restarts); else the server's ARTSMOKER_TEXTURE_BACKEND env.
    _tb = texture_backend or invoke.get("texture_backend") or os.environ.get("ARTSMOKER_TEXTURE_BACKEND")
    if _tb:
        env["ARTSMOKER_TEXTURE_BACKEND"] = _tb
        logger.info("Texture backend for %s endpoint: %s", model_key, _tb)

    # Dev hot-reload — on a dev box, let the handler check S3 for a code
    # overlay (overlay.tar.gz) before each inference, so we can push handler +
    # bundled-package fixes onto a warm instance without redeploying. No effect
    # in prod (flag absent) and the handler treats it as opt-in.
    try:
        from .auto_update import is_dev_mode
        if is_dev_mode():
            env["ARTSMOKER_DEV_HOTRELOAD"] = "1"
            if bucket:
                env["ARTSMOKER_HOTRELOAD_KEY"] = dev_overlay_s3_key(model_key)
    except Exception:
        pass

    # NCCL fix for pip-upgraded torch: the DLC Dockerfile has
    # ENV LD_PRELOAD="/usr/local/lib/libnccl.so" baked in, which forces the
    # old NCCL (v2.23) to load before any process starts. When pip upgrades
    # torch to 2.8, it installs NCCL 2.27+ but the LD_PRELOAD loads the old one.
    # Fix: override LD_PRELOAD via SageMaker container env var (equivalent to
    # docker run -e, overrides Dockerfile ENV defaults) to point to pip-installed NCCL.
    base_reqs = model.get("python_requirements", {}).get("base", [])
    needs_torch_upgrade = any("torch==2.8" in r or "torch>=2.8" in r for r in base_reqs)
    if needs_torch_upgrade:
        # Override ALL NVIDIA library paths: NCCL, cuDNN, and other CUDA libs.
        # The DLC container's system libraries (CUDA 12.4) are too old for torch 2.8.
        # Pip-installed versions (via torch's dependencies) are at the correct version
        # but the system ones load first. Prepend ALL pip-installed NVIDIA lib paths.
        nvidia_base = "/opt/conda/lib/python3.12/site-packages/nvidia"
        nvidia_libs = [
            f"{nvidia_base}/nccl/lib",
            f"{nvidia_base}/cudnn/lib",
            f"{nvidia_base}/cublas/lib",
            f"{nvidia_base}/cufft/lib",
            f"{nvidia_base}/curand/lib",
            f"{nvidia_base}/cusolver/lib",
            f"{nvidia_base}/cusparse/lib",
            f"{nvidia_base}/cuda_runtime/lib",
            f"{nvidia_base}/cuda_nvrtc/lib",
            f"{nvidia_base}/cuda_cupti/lib",
        ]
        nvidia_ld = ":".join(nvidia_libs)
        env["LD_PRELOAD"] = f"{nvidia_base}/nccl/lib/libnccl.so.2"
        default_ld = "/opt/conda/lib:/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu"
        env["LD_LIBRARY_PATH"] = f"{nvidia_ld}:{default_ld}"

        # FlashInfer: use pre-compiled jit-cache, disable JIT fallback (no nvcc 12.9 on DLC)
        model_reqs = model.get("python_requirements", {}).get("model", [])
        if any("flashinfer" in r for r in model_reqs):
            env["FLASHINFER_DISABLE_JIT"] = "1"
            env["FLASHINFER_CUDA_ARCH_LIST"] = "12.0f"

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
