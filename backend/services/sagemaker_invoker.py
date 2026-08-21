"""Amazon SageMaker Invoker — routes inference requests to custom model endpoints.

Handles both async (scale-to-zero) and real-time Amazon SageMaker endpoints.
Integrates with ArtSmoker's cost tracking and error handling.

For async endpoints:
  1. Send request → get S3 output location
  2. Poll S3 until result appears (or timeout)
  3. Download and return result

For real-time endpoints:
  1. Send request → get result immediately
"""

import base64
import json
import logging
import time

import boto3
from botocore.config import Config as BotoConfig

logger = logging.getLogger(__name__)

# Timeout config for Amazon SageMaker calls
_SM_CONFIG = BotoConfig(
    connect_timeout=10,
    read_timeout=120,  # Image generation can take up to 60s
    retries={"max_attempts": 2},
)


def _get_region() -> str:
    """Get the AWS region from session or config default."""
    region = boto3.Session().region_name
    if region:
        return region
    from backend.config import settings
    return settings.aws_region_models


def _endpoint_region(model_config: dict) -> str:
    """Region an endpoint actually lives in.

    The deployment block may carry an explicit `region` (endpoints deployed
    outside the home region, e.g. during a capacity drought). Falls back to the
    session/config region — identical to the old behavior for every existing
    entry, which carries no `region` key.
    """
    return (model_config.get("deployment", {}) or {}).get("region") or _get_region()


def _endpoint_bucket(model_config: dict) -> str:
    """S3 bucket for an endpoint's async input — SageMaker async I/O should live
    in the endpoint's own region. Falls back to the configured home bucket."""
    override = (model_config.get("deployment", {}) or {}).get("s3_bucket")
    if override:
        return override
    from backend.services.sagemaker_deployer import get_deployment_s3_bucket
    return get_deployment_s3_bucket()


def invoke_custom_model(
    model_key: str,
    payload: dict,
    timeout_seconds: int = 600,  # 10 min — async endpoints may need cold start time
) -> dict:
    """Invoke a custom model deployed on Amazon SageMaker.

    Detects whether the endpoint is async or real-time from the model registry
    and routes accordingly.

    Args:
        model_key: Registry key (e.g., 'flux1_schnell')
        payload: Model-specific input (prompt, image, params)
        timeout_seconds: Max wait time for async endpoints

    Returns:
        dict with 'image' (base64 PNG) or 'error' key
    """
    from backend.services.model_registry import get_registry

    registry = get_registry()

    # Find the model in any registry section
    model_config = None
    for section in ("image_models", "video_models", "post_processing", "utility_models"):
        if model_key in registry.get(section, {}):
            model_config = registry[section][model_key]
            break

    if not model_config:
        raise ValueError(f"Custom model '{model_key}' not found in registry. Is it deployed?")

    deployment = model_config.get("deployment", {})
    endpoint_name = deployment.get("endpoint_name")
    endpoint_type = deployment.get("endpoint_type", "realtime")

    if not endpoint_name:
        raise ValueError(f"Model '{model_key}' has no Amazon SageMaker endpoint configured.")

    try:
        if endpoint_type == "async":
            # Non-blocking: submit to SageMaker, register with the async job tracker,
            # return a sentinel immediately. The background poller computes the actual
            # instance-hour compute cost on completion (async_jobs._track_completion).
            result = _submit_async_job(endpoint_name, model_key, model_config, payload)
            return result
        else:
            import time as _time
            _t0 = _time.time()
            result = _invoke_realtime(endpoint_name, payload, region=_endpoint_region(model_config))
            _elapsed = _time.time() - _t0

        # Cost = instance $/hr × actual invocation seconds — the real compute basis
        # (same as the async path), NOT a per-image guess. Hourly rate is registry-
        # sourced (get_instance_hourly_rate); 0.0 when pricing is unavailable, so we
        # record 0 rather than fabricate. This block must NEVER fail the generation —
        # a pricing hiccup is cosmetic, so it is fully guarded.
        try:
            from backend.services.cost_tracker import add_cost
            from backend.services.custom_models import get_instance_hourly_rate
            _deploy = model_config.get("deployment", {})
            _hourly = get_instance_hourly_rate(
                _deploy.get("instance_type"), model_config.get("catalog_key"),
                _deploy.get("region") or _endpoint_region(model_config))
            compute_cost = round(_hourly * _elapsed / 3600, 6) if _hourly else 0.0
            if compute_cost > 0:
                add_cost("custom_model", compute_cost,
                         f"{model_config.get('label', model_key)}: {_elapsed:.0f}s × ${_hourly}/hr")
            from backend.services.telemetry import track_custom_model_invoke
            track_custom_model_invoke(
                model=model_key, cost_usd=compute_cost, latency_ms=_elapsed * 1000.0,
                predictor_type=model_config.get("invoke", {}).get("predictor_type", ""),
                cost_is_estimate=(_hourly == 0.0),
            )
        except Exception:
            logger.debug("custom_model cost tracking skipped (non-fatal)", exc_info=True)

        return result

    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.error("Custom model invocation failed (%s): %s", model_key, exc)
        raise RuntimeError(f"Custom model '{model_config.get('label', model_key)}' failed: {exc}")


def _invoke_realtime(endpoint_name: str, payload: dict, region: str | None = None) -> dict:
    """Invoke a real-time Amazon SageMaker endpoint."""
    sm_runtime = boto3.client("sagemaker-runtime", region_name=region or _get_region(), config=_SM_CONFIG)

    response = sm_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/json",
        Body=json.dumps(payload),
    )

    result = json.loads(response["Body"].read().decode("utf-8"))
    return result


def _submit_async_job(endpoint_name: str, model_key: str, model_config: dict, payload: dict) -> dict:
    """Submit an async job to SageMaker and register with the job tracker.

    Returns immediately with an async_submitted sentinel — does NOT poll.
    The background poller in async_jobs.py handles S3 output detection
    and gallery storage.
    """
    import uuid
    from backend.services.async_jobs import submit_job
    from backend.services.sagemaker_deployer import get_deployment_s3_bucket

    region = _endpoint_region(model_config)
    sm_runtime = boto3.client("sagemaker-runtime", region_name=region, config=_SM_CONFIG)

    input_location = _upload_async_input(endpoint_name, payload, region=region,
                                         bucket=_endpoint_bucket(model_config))
    invoke_kwargs = {
        "EndpointName": endpoint_name,
        "ContentType": "application/json",
        "InputLocation": input_location,
    }
    typical_latency = model_config.get("invoke", {}).get("typical_latency_seconds", 0)
    if typical_latency > 300:
        invoke_kwargs["InvocationTimeoutSeconds"] = min(3600, max(900, typical_latency * 2))
    response = sm_runtime.invoke_endpoint_async(**invoke_kwargs)

    output_location = response.get("OutputLocation")
    if not output_location:
        raise RuntimeError("Async invocation returned no output location")
    # Present when the endpoint config sets S3FailurePath — the model's error
    # body lands here on a failed inference, letting the poller fail the job in
    # seconds with the real cause (older endpoints without it return nothing).
    failure_location = response.get("FailureLocation", "")

    # Parse S3 output location
    parts = output_location.replace("s3://", "").split("/", 1)
    s3_bucket, s3_key = parts[0], parts[1]

    # Register with the async job tracker (non-blocking)
    job_id = str(uuid.uuid4())[:8]
    job = submit_job(
        job_id=job_id,
        model_key=model_key,
        model_label=model_config.get("label", model_key),
        prompt=payload.get("prompt", ""),
        full_payload=payload,
        output_location=output_location,
        input_location=input_location,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        endpoint_name=endpoint_name,
        region=region,
        failure_location=failure_location,
    )

    # Return sentinel — the caller knows this is async (not a final image)
    return {"async_submitted": True, "job_id": job_id, "model": model_key, "model_label": model_config.get("label", model_key)}


def _upload_async_input(endpoint_name: str, payload: dict,
                        region: str | None = None, bucket: str | None = None) -> str:
    """Upload async input to S3 and return the S3 URI.

    region/bucket default to the home region + configured deployment bucket;
    cross-region endpoints pass their own (async I/O must be same-region).
    """
    from backend.services.sagemaker_deployer import (
        get_deployment_s3_bucket, check_deployment_bucket, S3_MODEL_PREFIX,
    )

    # Preflight the PREREQUISITE only: is a bucket NAME configured? A custom async
    # model needs the S3 bucket for its input/output, so fail with clear guidance
    # HERE (before any boto3 call) rather than a raw put_object(Bucket="") error
    # mid-generation. We deliberately do NOT head_bucket on this hot path — that
    # can 403 for a perfectly usable bucket under tight/cross-account IAM and would
    # false-block working generation. A genuine access error surfaces from the
    # put_object below and is handled by the async job reliability layer.
    if not bucket:
        check = check_deployment_bucket(require_access=False)
        if not check["ok"]:
            raise ValueError(check["message"])
        bucket = get_deployment_s3_bucket()
    key = f"{S3_MODEL_PREFIX}/inference-input/{endpoint_name}/{int(time.time() * 1000)}.json"

    payload_bytes = json.dumps(payload).encode()
    s3 = boto3.client("s3", region_name=region or _get_region())
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload_bytes,
        ContentType="application/json",
    )

    from backend.services.cost_tracker import add_s3_cost
    add_s3_cost("put", len(payload_bytes), "async inference input", region=region or _get_region())

    return f"s3://{bucket}/{key}"


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    """Parse s3://bucket/key into (bucket, key)."""
    parts = uri.replace("s3://", "").split("/", 1)
    return parts[0], parts[1]


# ── Integration with ArtSmoker's image generation ────────────────────────

def is_custom_model(model_key: str) -> bool:
    """Check if a model key refers to a custom Amazon SageMaker model."""
    from backend.services.model_registry import get_registry
    registry = get_registry()
    for section in ("image_models", "video_models", "post_processing", "utility_models"):
        model = registry.get(section, {}).get(model_key, {})
        if model.get("model_source") == "custom_hosted":
            return True
    return False


def invoke_custom_image_model(
    model_key: str,
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    negative_prompt: str = "",
    **kwargs,
) -> bytes:
    """Invoke a custom image generation model and return PNG bytes.

    Reads invocation config from the model registry (not hardcoded).
    The config defines input_fields with types and defaults — we build
    the payload dynamically from those.
    """
    from backend.services.model_registry import get_registry

    # Find model config in registry
    registry = get_registry()
    model_config = None
    for section in ("image_models", "video_models"):
        if model_key in registry.get(section, {}):
            model_config = registry[section][model_key]
            break
    if not model_config:
        raise ValueError(f"Custom model '{model_key}' not found in registry.")

    invoke = model_config.get("invoke", {})
    input_fields = invoke.get("input_fields", {})

    # Build payload from input_fields spec — apply defaults from registry
    payload = {}
    for field_name, field_spec in input_fields.items():
        if field_name == "prompt":
            payload["prompt"] = prompt
        elif field_name == "width":
            payload["width"] = width
        elif field_name == "height":
            payload["height"] = height
        elif field_name == "seed":
            if seed is not None:
                payload["seed"] = seed
        elif field_name == "negative_prompt":
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
        elif field_name in kwargs:
            payload[field_name] = kwargs[field_name]
        elif "default" in field_spec:
            payload[field_name] = field_spec["default"]

    result = invoke_custom_model(model_key, payload)

    # Async jobs return a sentinel — not image data
    if result.get("async_submitted"):
        return result  # Caller handles async flow

    image_b64 = result.get("image", "")
    if not image_b64:
        raise RuntimeError("Custom model returned no image data")

    return base64.b64decode(image_b64)


def invoke_instruction_edit_sync(model_key: str, prompt: str, image_bytes: bytes,
                                 timeout_seconds: int = 900) -> bytes:
    """Run an instruction-edit (image_edit) job and WAIT for the result bytes.

    For flows that need a synchronous result from an async-type endpoint (e.g.
    the 3D "Improve the Source" extend op). Deliberately BYPASSES the async job
    tracker: tracker jobs are gallery-bound (completion saves a new asset or
    version), which is wrong for sidecar flows. Submits directly, polls the S3
    output location, and returns the edited image bytes.

    Raises RuntimeError on timeout (with a warm-up hint — a scale-to-zero
    endpoint may need minutes to provision + load) or on model failure.
    """
    import base64 as _b64
    from backend.services.model_registry import get_image_model

    model_config = get_image_model(model_key) or {}
    endpoint_name = (model_config.get("deployment") or {}).get("endpoint_name", "")
    if not endpoint_name:
        raise RuntimeError(f"No deployed endpoint for model '{model_key}'")
    ep_region = _endpoint_region(model_config)

    payload = {
        "prompt": prompt,
        "reference_images": [_b64.b64encode(image_bytes).decode()],
        "negative_prompt": " ",
    }
    # Honor registry-driven inference defaults (steps, cfg) when defined —
    # same `input_fields` schema the async submit path uses.
    for field_name, spec in (model_config.get("invoke", {}).get("input_fields", {}) or {}).items():
        if field_name not in payload and isinstance(spec, dict) and "default" in spec:
            payload[field_name] = spec["default"]

    sm_runtime = boto3.client("sagemaker-runtime", region_name=ep_region, config=_SM_CONFIG)
    input_location = _upload_async_input(endpoint_name, payload, region=ep_region,
                                         bucket=_endpoint_bucket(model_config))
    response = sm_runtime.invoke_endpoint_async(
        EndpointName=endpoint_name,
        ContentType="application/json",
        InputLocation=input_location,
    )
    output_location = response.get("OutputLocation")
    if not output_location:
        raise RuntimeError("Async invocation returned no output location")
    out_bucket, out_key = _parse_s3_uri(output_location)

    s3 = boto3.client("s3", region_name=ep_region)
    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            try:
                body = s3.get_object(Bucket=out_bucket, Key=out_key)["Body"].read()
            except s3.exceptions.NoSuchKey:
                time.sleep(10)  # nosemgrep --deliberate async-output S3 poll interval
                continue
            except Exception:
                time.sleep(10)  # nosemgrep --deliberate async-output S3 poll interval
                continue
            result = json.loads(body)
            image_b64 = result.get("image", "")
            if not image_b64:
                raise RuntimeError(f"Edit model returned no image: {str(result)[:200]}")
            return _b64.b64decode(image_b64)
        raise RuntimeError(
            f"Instruction edit timed out after {timeout_seconds}s — the endpoint may be "
            f"scaled to zero (cold start takes several minutes). Warm it up with a "
            f"gallery edit first, or retry shortly.")
    finally:
        # Best-effort cleanup of the input + output artifacts (no tracker owns them).
        for loc in (input_location, output_location):
            try:
                b, k = _parse_s3_uri(loc)
                s3.delete_object(Bucket=b, Key=k)
            except Exception:
                pass


def invoke_custom_post_process(
    model_key: str,
    image_bytes: bytes,
    **kwargs,
) -> bytes:
    """Invoke a custom post-processing model (upscale, bg removal, etc.)."""
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {"image": image_b64, **kwargs}

    result = invoke_custom_model(model_key, payload)

    output_b64 = result.get("image", "")
    if not output_b64:
        raise RuntimeError(f"Custom post-processing model returned no image data")

    return base64.b64decode(output_b64)
