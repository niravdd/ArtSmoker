"""Image generation service — routes generation requests to the appropriate
Bedrock image model (Nova Canvas or Titan Image)."""

import logging
import random

from backend.models.generation_request import ImageModel
from backend.services.bedrock_client import invoke_nova_canvas, invoke_titan_image

logger = logging.getLogger(__name__)

# Seed range for reproducibility control
_SEED_MAX = 2**31 - 1


def generate_image(
    refined_prompt: str,
    model: ImageModel,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Generate an image from a refined prompt using the specified model.

    Args:
        refined_prompt: The fully refined, detailed image-generation prompt.
        model: Which image model to use (NOVA_CANVAS or TITAN_IMAGE).
        width: Output image width in pixels.
        height: Output image height in pixels.
        seed: Optional seed for reproducibility. If None, a random seed is used.

    Returns:
        PNG image bytes.

    Raises:
        ValueError: If an unsupported model is specified.
        Exception: Propagates any errors from the underlying Bedrock API calls.
    """
    if seed is None:
        seed = random.randint(0, _SEED_MAX)

    logger.info(
        "Generating image: model=%s, size=%dx%d, seed=%d, prompt_len=%d",
        model.value,
        width,
        height,
        seed,
        len(refined_prompt),
    )

    if model == ImageModel.NOVA_CANVAS:
        image_bytes = invoke_nova_canvas(
            refined_prompt,
            width=width,
            height=height,
            seed=seed,
        )
    elif model == ImageModel.TITAN_IMAGE:
        image_bytes = invoke_titan_image(
            refined_prompt,
            width=width,
            height=height,
            seed=seed,
        )
    else:
        raise ValueError(f"Unsupported image model: {model}")

    logger.info(
        "Image generated successfully: model=%s, %d bytes",
        model.value,
        len(image_bytes),
    )
    return image_bytes
