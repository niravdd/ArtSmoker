"""Image generation service — routes generation requests to the appropriate
Bedrock image model (Nova Canvas, Titan Image, SD 3.5 Large, Stable Image Ultra)."""

import logging
import random

from backend.models.generation_request import ImageModel
from backend.services.bedrock_client import (
    invoke_nova_canvas,
    invoke_sd35_large,
    invoke_stable_image_ultra,
    invoke_titan_image,
)

logger = logging.getLogger(__name__)

_SEED_MAX = 2**31 - 1


def generate_image(
    refined_prompt: str,
    model: ImageModel,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image from a refined prompt using the specified model.

    Returns PNG image bytes.
    """
    if seed is None:
        seed = random.randint(0, _SEED_MAX)

    logger.info(
        "Generating image: model=%s, size=%dx%d, seed=%d, prompt_len=%d",
        model.value, width, height, seed, len(refined_prompt),
    )

    if model == ImageModel.NOVA_CANVAS:
        image_bytes = invoke_nova_canvas(refined_prompt, width=width, height=height, seed=seed)
    elif model == ImageModel.TITAN_IMAGE:
        image_bytes = invoke_titan_image(refined_prompt, width=width, height=height, seed=seed)
    elif model == ImageModel.SD35_LARGE:
        image_bytes = invoke_sd35_large(refined_prompt, width=width, height=height, seed=seed)
    elif model == ImageModel.STABLE_IMAGE_ULTRA:
        image_bytes = invoke_stable_image_ultra(refined_prompt, width=width, height=height, seed=seed)
    else:
        raise ValueError(f"Unsupported image model: {model}")

    logger.info("Image generated: model=%s, %d bytes", model.value, len(image_bytes))
    return image_bytes
