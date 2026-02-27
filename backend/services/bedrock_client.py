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


# ── Image generation helpers ─────────────────────────────────────────────

def invoke_nova_canvas(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Amazon Nova Canvas. Returns PNG bytes."""
    client = get_images_client()
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt},
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
    return base64.b64decode(result["images"][0])


def invoke_titan_image(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Amazon Titan Image Generator v2. Returns PNG bytes."""
    client = get_images_client()
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt,
        },
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
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Stable Diffusion 3.5 Large. Returns PNG bytes."""
    client = get_models_client()
    body = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": _dimensions_to_aspect_ratio(width, height),
    }
    if seed is not None:
        body["seed"] = seed

    response = client.invoke_model(
        modelId=settings.sd35_large_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    return base64.b64decode(result["images"][0])


def invoke_stable_image_ultra(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image with Stable Image Ultra. Returns PNG bytes."""
    client = get_models_client()
    body = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": _dimensions_to_aspect_ratio(width, height),
    }
    if seed is not None:
        body["seed"] = seed

    response = client.invoke_model(
        modelId=settings.stable_image_ultra_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
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
    """Upscale image using Stability AI Creative Upscale. Returns PNG bytes."""
    client = get_models_client()
    response = client.invoke_model(
        modelId=settings.stability_upscale_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "image": base64.b64encode(image_bytes).decode(),
            "prompt": prompt or "high quality upscale",
        }),
    )
    result = json.loads(response["body"].read())
    return base64.b64decode(result["image"])
