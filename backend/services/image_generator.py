"""Image generation service — routes generation requests to the appropriate
Bedrock image model via the generic registry-driven invoker, with retry
logic for API throttling."""

import logging
import random
import time

from backend.services.bedrock_client import invoke_image_model

logger = logging.getLogger(__name__)

_SEED_MAX = 2**31 - 1
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds


def generate_image(
    enhanced_prompt: str,
    model,  # str or ImageModel enum — any valid registry key
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    negative_prompt: str = "",
    quality: str | None = None,
    region_override: str | None = None,
    status_callback=None,
) -> bytes:
    """Generate an image from a refined prompt using the specified model.

    Uses the generic registry-driven invoker — any model registered in
    model_registry.json with a valid format_family can be used.

    Retries up to 3 times with exponential backoff on throttling/transient errors.
    Calls status_callback(dict) with progress updates if provided.
    Returns PNG image bytes.
    """
    if seed is None:
        seed = random.randint(0, _SEED_MAX)

    # Normalize model to string key
    model_key = model.value if hasattr(model, 'value') else str(model)

    def emit(event):
        if status_callback:
            status_callback(event)

    logger.info(
        "Generating image: model=%s, size=%dx%d, seed=%d, prompt_len=%d",
        model_key, width, height, seed, len(enhanced_prompt),
    )

    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            if attempt > 0:
                emit({"type": "retry", "attempt": attempt + 1, "max_retries": _MAX_RETRIES,
                      "message": f"Retrying image generation (attempt {attempt + 1}/{_MAX_RETRIES})..."})
            result = invoke_image_model(
                model_key,
                enhanced_prompt,
                width=width,
                height=height,
                seed=seed,
                negative_prompt=negative_prompt,
                quality=quality,
                region_override=region_override,
            )
            # Async custom models return a sentinel dict, not image bytes
            if isinstance(result, dict) and result.get("async_submitted"):
                logger.info("Async job submitted: model=%s, job_id=%s", model_key, result.get("job_id"))
                return result  # Propagate sentinel to the caller
            logger.info("Image generated: model=%s, %d bytes", model_key, len(result))
            return result
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
