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

    # Track cost
    from backend.services.cost_tracker import add_cost
    estimated_cost = model_config.get("base_price_usd", 0)

    try:
        if endpoint_type == "async":
            # Non-blocking: submit to SageMaker, register with async job tracker,
            # return a sentinel immediately. The background poller handles the rest.
            result = _submit_async_job(endpoint_name, model_key, model_config, payload)
            return result
        else:
            result = _invoke_realtime(endpoint_name, payload)

        if estimated_cost > 0:
            add_cost("custom_model", estimated_cost, f"{model_config.get('label', model_key)} × 1")

        # Track invocation with compute cost (for raw event visibility)
        try:
            from backend.services.telemetry import track_custom_model_invoke
            track_custom_model_invoke(
                model=model_key, cost_usd=estimated_cost,
                predictor_type=model_config.get("invoke", {}).get("predictor_type", ""),
            )
        except Exception:
            pass

        return result

    except Exception as exc:
        logger.error("Custom model invocation failed (%s): %s", model_key, exc)
        raise RuntimeError(f"Custom model '{model_config.get('label', model_key)}' failed: {exc}")


def _invoke_realtime(endpoint_name: str, payload: dict) -> dict:
    """Invoke a real-time Amazon SageMaker endpoint."""
    sm_runtime = boto3.client("sagemaker-runtime", region_name=_get_region(), config=_SM_CONFIG)

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

    sm_runtime = boto3.client("sagemaker-runtime", region_name=_get_region(), config=_SM_CONFIG)

    input_location = _upload_async_input(endpoint_name, payload)
    response = sm_runtime.invoke_endpoint_async(
        EndpointName=endpoint_name,
        ContentType="application/json",
        InputLocation=input_location,
    )

    output_location = response.get("OutputLocation")
    if not output_location:
        raise RuntimeError("Async invocation returned no output location")

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
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )

    # Return sentinel — the caller knows this is async (not a final image)
    return {"async_submitted": True, "job_id": job_id, "model": model_key, "model_label": model_config.get("label", model_key)}


def _upload_async_input(endpoint_name: str, payload: dict) -> str:
    """Upload async input to S3 and return the S3 URI."""
    from backend.services.sagemaker_deployer import get_deployment_s3_bucket, S3_MODEL_PREFIX

    bucket = get_deployment_s3_bucket()
    key = f"{S3_MODEL_PREFIX}/inference-input/{endpoint_name}/{int(time.time() * 1000)}.json"

    s3 = boto3.client("s3", region_name=_get_region())
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload),
        ContentType="application/json",
    )

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
