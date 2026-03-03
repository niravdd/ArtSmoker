"""Image generation service — routes generation requests to the appropriate
Bedrock image model with retry logic for API throttling."""

import logging
import random
import time

from backend.models.generation_request import ImageModel
from backend.services.bedrock_client import (
    invoke_nova_canvas,
    invoke_sd35_large,
    invoke_stable_image_ultra,
    invoke_titan_image,
)

logger = logging.getLogger(__name__)

_SEED_MAX = 2**31 - 1
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds


def generate_image(
    refined_prompt: str,
    model: ImageModel,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    status_callback=None,
) -> bytes:
    """Generate an image from a refined prompt using the specified model.

    Retries up to 3 times with exponential backoff on throttling/transient errors.
    Calls status_callback(dict) with progress updates if provided.
    Returns PNG image bytes.
    """
    if seed is None:
        seed = random.randint(0, _SEED_MAX)

    def emit(event):
        if status_callback:
            status_callback(event)

    logger.info(
        "Generating image: model=%s, size=%dx%d, seed=%d, prompt_len=%d",
        model.value, width, height, seed, len(refined_prompt),
    )

    invoke_fn = {
        ImageModel.NOVA_CANVAS: invoke_nova_canvas,
        ImageModel.TITAN_IMAGE: invoke_titan_image,
        ImageModel.SD35_LARGE: invoke_sd35_large,
        ImageModel.STABLE_IMAGE_ULTRA: invoke_stable_image_ultra,
    }.get(model)

    if invoke_fn is None:
        raise ValueError(f"Unsupported image model: {model}")

    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            if attempt > 0:
                emit({"type": "retry", "attempt": attempt + 1, "max_retries": _MAX_RETRIES,
                      "message": f"Retrying image generation (attempt {attempt + 1}/{_MAX_RETRIES})..."})
            image_bytes = invoke_fn(refined_prompt, width=width, height=height, seed=seed)
            logger.info("Image generated: model=%s, %d bytes", model.value, len(image_bytes))
            return image_bytes
        except Exception as exc:
            last_exc = exc
            exc_str = str(exc).lower()
            # Content moderation / prompt rejection errors are NOT retriable
            non_retriable = any(k in exc_str for k in [
                "content moderation", "generation failed", "not allowed",
                "blocked", "unsafe", "policy",
            ])
            retriable = not non_retriable and any(k in exc_str for k in [
                "throttl", "too many", "service unavailable",
                "timed out", "connection", "rate exceeded",
            ])
            if retriable and attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Image generation failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, _MAX_RETRIES, delay, exc,
                )
                emit({"type": "throttled", "attempt": attempt + 1, "delay": round(delay, 1),
                      "message": f"API throttled, waiting {delay:.0f}s before retry..."})
                time.sleep(delay)
            else:
                break

    logger.error("Image generation failed after %d attempts: %s", _MAX_RETRIES, last_exc)
    raise last_exc
