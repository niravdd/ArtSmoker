"""Shared AWS Bedrock client with connection pooling and model routing."""

import base64
import json
import logging

import boto3
from botocore.config import Config as BotoConfig

from backend.config import settings

logger = logging.getLogger(__name__)

_boto_config = BotoConfig(
    retries={"max_attempts": 3, "mode": "adaptive"},
    max_pool_connections=10,
)

# Lazy-initialised clients keyed by region
_clients: dict[str, boto3.client] = {}


def _get_client(region: str):
    if region not in _clients:
        session_kwargs = {}
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile
        session = boto3.Session(region_name=region, **session_kwargs)
        _clients[region] = session.client(
            "bedrock-runtime", config=_boto_config
        )
    return _clients[region]


def get_models_client():
    """Client for Claude / Stability models (us-west-2)."""
    return _get_client(settings.aws_region_models)


def get_images_client():
    """Client for Nova Canvas / Titan Image / Nova Sonic (us-east-1)."""
    return _get_client(settings.aws_region_images)


# ── Startup validation ────────────────────────────────────────────────────

def validate_aws_credentials() -> dict:
    """Validate AWS credentials and Bedrock model access on startup.

    Returns a dict with check results:
        {
            "credentials": True/False,
            "identity": "arn:aws:...",
            "models_region": True/False,
            "images_region": True/False,
            "errors": ["..."]
        }
    """
    result = {
        "credentials": False,
        "identity": None,
        "models_region": False,
        "images_region": False,
        "errors": [],
    }

    # 1. Check credentials resolve (STS GetCallerIdentity)
    try:
        session_kwargs = {}
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile
        session = boto3.Session(**session_kwargs)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        result["credentials"] = True
        result["identity"] = identity.get("Arn", "unknown")
        logger.info("AWS credentials valid: %s", result["identity"])
    except Exception as exc:
        msg = f"AWS credentials not configured or invalid: {exc}"
        result["errors"].append(msg)
        logger.error(msg)
        return result

    # 2. Check Bedrock access in models region (us-west-2)
    try:
        client = get_models_client()
        client.converse(
            modelId=settings.claude_sonnet_model_id,
            messages=[{"role": "user", "content": [{"text": "hi"}]}],
            inferenceConfig={"maxTokens": 1, "temperature": 0},
        )
        result["models_region"] = True
        logger.info("Bedrock models region (%s) OK — Claude accessible.", settings.aws_region_models)
    except Exception as exc:
        msg = f"Bedrock models region ({settings.aws_region_models}): {exc}"
        result["errors"].append(msg)
        logger.warning(msg)

    # 3. Check Bedrock access in images region (us-east-1)
    try:
        client = get_images_client()
        # Light check: invoke Nova Canvas with an intentionally tiny/fast request
        # We just need to confirm access, not generate a real image
        client.invoke_model(
            modelId=settings.nova_canvas_model_id,
            contentType="application/json",
            accept="application/json",
            body='{"taskType":"TEXT_IMAGE","textToImageParams":{"text":"test"},"imageGenerationConfig":{"numberOfImages":1,"width":512,"height":512}}',
        )
        result["images_region"] = True
        logger.info("Bedrock images region (%s) OK — Nova Canvas accessible.", settings.aws_region_images)
    except client.exceptions.ValidationException:
        # ValidationException means we reached the model — access works
        result["images_region"] = True
        logger.info("Bedrock images region (%s) OK — Nova Canvas accessible.", settings.aws_region_images)
    except Exception as exc:
        msg = f"Bedrock images region ({settings.aws_region_images}): {exc}"
        result["errors"].append(msg)
        logger.warning(msg)

    return result


# ── Claude helpers ────────────────────────────────────────────────────────

def _pick_claude_model(complexity: str) -> str:
    if complexity == "complex":
        return settings.claude_opus_model_id
    return settings.claude_sonnet_model_id


def invoke_claude(
    prompt: str,
    *,
    complexity: str = "fast",
    images: list[bytes] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Invoke a Claude model via Bedrock Converse API.

    Args:
        prompt: The text prompt.
        complexity: "fast" → Sonnet, "complex" → Opus.
        images: Optional list of PNG image bytes to include as vision input.
        max_tokens: Max response tokens.
        temperature: Sampling temperature.

    Returns:
        The text response from Claude.
    """
    model_id = _pick_claude_model(complexity)
    client = get_models_client()

    content_blocks: list[dict] = []
    if images:
        for img_bytes in images:
            content_blocks.append({
                "image": {
                    "format": "png",
                    "source": {"bytes": img_bytes},
                }
            })
    content_blocks.append({"text": prompt})

    messages = [{"role": "user", "content": content_blocks}]

    try:
        response = client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        )
        return response["output"]["message"]["content"][0]["text"]
    except client.exceptions.AccessDeniedException:
        logger.warning(
            "Access denied for %s, falling back to %s",
            model_id, settings.claude_fallback_model_id,
        )
        response = client.converse(
            modelId=settings.claude_fallback_model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        )
        return response["output"]["message"]["content"][0]["text"]


# ── Generic image generation (registry-driven) ──────────────────────────

def _set_nested(obj: dict, path: str, value):
    """Set a value at a dot-path in a nested dict. E.g. 'a.b.c' sets obj['a']['b']['c']."""
    keys = path.split(".")
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = value


def _get_nested(obj: dict, path: str):
    """Get a value from a dot-path, supporting array indexing like 'images[0]'."""
    import re as _re
    for part in path.split("."):
        m = _re.match(r"(\w+)\[(\d+)\]", part)
        if m:
            obj = obj[m.group(1)][int(m.group(2))]
        else:
            obj = obj[part]
    return obj


def invoke_image_model(
    model_key: str,
    prompt: str,
    *,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    quality: str | None = None,
    region_override: str | None = None,
) -> bytes:
    """Generic image generation using any model defined in the registry.

    Reads the model config and format family from model_registry.json to
    construct the request body dynamically. No per-model code needed.
    Returns PNG image bytes.
    """
    from backend.services.model_registry import get_image_model, get_registry
    import copy

    model_config = get_image_model(model_key)
    if not model_config:
        raise ValueError(f"Unknown image model: {model_key}")

    model_id = model_config["model_id"]
    region = region_override or model_config["region"]
    family_name = model_config.get("format_family", "")

    registry = get_registry()
    family = registry.get("format_families", {}).get(family_name)
    if not family:
        raise ValueError(f"Unknown format family '{family_name}' for model '{model_key}'")

    # Start with the family body template and merge model-specific overrides
    body = copy.deepcopy(family["body_template"])
    extra = model_config.get("extra_body", {})
    _deep_merge(body, extra)

    # Apply quality tier override if specified
    if quality:
        quality_options = model_config.get("quality_options", [])
        for qopt in quality_options:
            if qopt.get("value") == quality and qopt.get("body_override"):
                _deep_merge(body, qopt["body_override"])
                break

    # Set prompt
    _set_nested(body, family["prompt_path"], prompt)

    # Set negative prompt
    if negative_prompt and family.get("negative_prompt_path"):
        _set_nested(body, family["negative_prompt_path"], negative_prompt)

    # Set dimensions or aspect ratio
    dims_mode = family.get("dimensions_mode", "pixels")
    if dims_mode == "aspect_ratio":
        body["aspect_ratio"] = _dimensions_to_aspect_ratio(width, height)
    elif dims_mode == "pixels":
        dim_paths = family.get("dimensions_paths", {})
        if dim_paths.get("width"):
            _set_nested(body, dim_paths["width"], width)
        if dim_paths.get("height"):
            _set_nested(body, dim_paths["height"], height)

    # Set seed
    if seed is not None and family.get("seed_path"):
        _set_nested(body, family["seed_path"], seed)

    # Invoke
    client = _get_client(region)
    label = model_config.get("label", model_key)
    logger.info("Invoking %s (%s) in %s: prompt=%d chars, seed=%s",
                label, model_id, region, len(prompt), seed)

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())

    # Extract image from response
    try:
        image_data = _get_nested(result, family["response_image_path"])
    except (KeyError, IndexError, TypeError):
        error_msg = result.get("error", result.get("message", str(result)))
        logger.error("%s returned no image: %s", label, error_msg)
        raise RuntimeError(f"{label} generation failed: {error_msg}")

    return base64.b64decode(image_data)


def _deep_merge(base: dict, override: dict):
    """Recursively merge override into base (mutates base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ── Legacy image generation helpers (kept for backward compatibility) ────

def invoke_nova_canvas(
    prompt: str,
    *,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Amazon Nova Canvas. Returns PNG bytes.

    Follows Nova Canvas prompting best practices:
    https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html

    - prompt: Descriptive caption (not commands). Subject first, style last.
    - negative_prompt: Terms to exclude (no negation words needed).
      Sent via the negativeText parameter.
    """
    client = get_images_client()
    text_params = {"text": prompt}
    if negative_prompt:
        text_params["negativeText"] = negative_prompt

    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": text_params,
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": width,
            "height": height,
            "quality": "premium",
        },
    }
    if seed is not None:
        body["imageGenerationConfig"]["seed"] = seed

    response = client.invoke_model(
        modelId=settings.nova_canvas_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    if "images" not in result:
        error_msg = result.get("error", result.get("message", str(result)))
        logger.error("Nova Canvas returned no images: %s", error_msg)
        raise RuntimeError(f"Nova Canvas generation failed: {error_msg}")
    return base64.b64decode(result["images"][0])


def invoke_titan_image(
    prompt: str,
    *,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Amazon Titan Image Generator v2. Returns PNG bytes."""
    client = get_images_client()
    text_params = {"text": prompt}
    if negative_prompt:
        text_params["negativeText"] = negative_prompt
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": text_params,
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": width,
            "height": height,
        },
    }
    if seed is not None:
        body["imageGenerationConfig"]["seed"] = seed

    response = client.invoke_model(
        modelId=settings.titan_image_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    if "images" not in result:
        error_msg = result.get("error", result.get("message", str(result)))
        logger.error("Titan Image returned no images: %s", error_msg)
        raise RuntimeError(f"Titan Image generation failed: {error_msg}")
    return base64.b64decode(result["images"][0])


def _dimensions_to_aspect_ratio(width: int, height: int) -> str:
    """Convert pixel dimensions to the nearest Stability AI aspect ratio string."""
    ratio = width / height
    # Stability supports: 1:1, 16:9, 9:16, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21
    aspect_ratios = [
        (1.0, "1:1"), (16/9, "16:9"), (9/16, "9:16"),
        (3/2, "3:2"), (2/3, "2:3"), (4/5, "4:5"), (5/4, "5:4"),
        (21/9, "21:9"), (9/21, "9:21"),
    ]
    closest = min(aspect_ratios, key=lambda x: abs(x[0] - ratio))
    return closest[1]


def invoke_sd35_large(
    prompt: str,
    *,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Stable Diffusion 3.5 Large. Returns PNG bytes.

    SD 3.5 supports rich prompts (2000 chars), quality boosters
    ('masterpiece, best quality'), and negative prompts for cleanup.
    """
    client = get_models_client()
    body = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": _dimensions_to_aspect_ratio(width, height),
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt
    if seed is not None:
        body["seed"] = seed

    response = client.invoke_model(
        modelId=settings.sd35_large_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    if "images" not in result:
        error_msg = result.get("error", result.get("message", str(result)))
        logger.error("SD 3.5 Large returned no images: %s", error_msg)
        raise RuntimeError(f"SD 3.5 Large generation failed: {error_msg}")
    return base64.b64decode(result["images"][0])


def invoke_stable_image_ultra(
    prompt: str,
    *,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Stable Image Ultra. Returns PNG bytes.

    Ultra supports rich prompts, photorealistic quality boosters,
    and negative prompts for quality cleanup.
    """
    client = get_models_client()
    body = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": _dimensions_to_aspect_ratio(width, height),
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt
    if seed is not None:
        body["seed"] = seed

    response = client.invoke_model(
        modelId=settings.stable_image_ultra_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    if "images" not in result:
        error_msg = result.get("error", result.get("message", str(result)))
        logger.error("Stable Image Ultra returned no images: %s", error_msg)
        raise RuntimeError(f"Stable Image Ultra generation failed: {error_msg}")
    return base64.b64decode(result["images"][0])


# ── Post-processing helpers ──────────────────────────────────────────────

def invoke_remove_background(image_bytes: bytes) -> bytes:
    """Remove background using Stability AI. Returns PNG bytes."""
    client = get_models_client()
    response = client.invoke_model(
        modelId=settings.stability_remove_bg_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "image": base64.b64encode(image_bytes).decode(),
        }),
    )
    result = json.loads(response["body"].read())
    return base64.b64decode(result["image"])


def invoke_upscale(image_bytes: bytes, prompt: str = "") -> bytes:
    """Upscale image using Stability AI Creative Upscale. Returns PNG bytes.

    Uses JPEG output to avoid the 16MB response payload limit, then
    converts back to PNG. Retries on throttling (ServiceUnavailable).
    """
    import time

    client = get_models_client()
    body_payload = json.dumps({
        "image": base64.b64encode(image_bytes).decode(),
        "prompt": prompt or "high quality upscale",
        "output_format": "jpeg",
    })

    # Retry with exponential backoff for throttling
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.invoke_model(
                modelId=settings.stability_upscale_model_id,
                contentType="application/json",
                accept="application/json",
                body=body_payload,
            )
            break
        except client.exceptions.ServiceUnavailableException:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt + 1
            logger.warning("Upscale throttled, retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
            time.sleep(wait)

    result = json.loads(response["body"].read())
    jpeg_bytes = base64.b64decode(result["images"][0] if "images" in result else result["image"])

    # Convert JPEG to PNG for consistency
    from PIL import Image as PILImage
    import io
    img = PILImage.open(io.BytesIO(jpeg_bytes))
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG")
    return png_buf.getvalue()
