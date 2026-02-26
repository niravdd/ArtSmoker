"""Image generation router — orchestrates the full generation pipeline from
prompt refinement through image generation and post-processing."""

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from backend.models.generation_request import AssetType, GenerationRequest
from backend.models.generation_result import GenerationResult
from backend.models.style_profile import StyleProfile
from backend.services.image_generator import generate_image
from backend.services.post_processor import process_asset
from backend.services.prompt_engineer import refine_marketing_prompt, refine_prompt
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.post("/", response_model=GenerationResult)
async def generate_asset(body: GenerationRequest):
    """Main generation endpoint.

    Runs the full asset generation pipeline:
    1. Load the style profile (if style_id is provided).
    2. Refine the user prompt using the appropriate prompt engineer.
    3. Generate an image with the selected model.
    4. Post-process the image (background removal, upscale, SVG conversion).
    5. Save the PNG, optional SVG, and metadata to storage.
    6. Return a GenerationResult with identifiers and paths.
    """
    asset_id = str(uuid4())
    logger.info(
        "Starting generation: id=%s, model=%s, asset_type=%s, style_id=%s",
        asset_id,
        body.image_model.value,
        body.asset_type.value,
        body.style_id,
    )

    # ── Step 1: Load style profile ─────────────────────────────────────
    style_profile: StyleProfile | None = None
    if body.style_id:
        data = store.load_style_profile(body.style_id)
        if data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Style '{body.style_id}' not found.",
            )
        style_profile = StyleProfile(**data)
        logger.info("Loaded style profile: %s", body.style_id)

    # ── Step 2: Refine the prompt ──────────────────────────────────────
    try:
        if body.asset_type == AssetType.MARKETING_BANNER:
            refined = refine_marketing_prompt(body.prompt, style_profile)
        else:
            refined = refine_prompt(body.prompt, style_profile, body.asset_type)
    except Exception as exc:
        logger.exception("Prompt refinement failed for asset %s.", asset_id)
        raise HTTPException(
            status_code=502,
            detail=f"Prompt refinement failed: {exc}",
        ) from exc

    # ── Step 3: Generate image ─────────────────────────────────────────
    try:
        image_bytes = generate_image(
            refined_prompt=refined,
            model=body.image_model,
            width=body.width,
            height=body.height,
        )
    except Exception as exc:
        logger.exception("Image generation failed for asset %s.", asset_id)
        raise HTTPException(
            status_code=502,
            detail=f"Image generation failed: {exc}",
        ) from exc

    # ── Step 4: Post-process ───────────────────────────────────────────
    svg_output_path = store.generated_asset_dir(asset_id) / "asset.svg" if body.generate_svg else None

    try:
        final_bytes, svg_path = process_asset(
            image_bytes=image_bytes,
            refined_prompt=refined,
            remove_bg=body.remove_background,
            do_upscale=body.upscale,
            do_svg=body.generate_svg,
            svg_output_path=svg_output_path,
        )
    except Exception as exc:
        logger.exception("Post-processing failed for asset %s.", asset_id)
        raise HTTPException(
            status_code=502,
            detail=f"Post-processing failed: {exc}",
        ) from exc

    # ── Step 5: Save outputs to storage ────────────────────────────────
    png_path = store.save_generated_image(asset_id, "asset.png", final_bytes)
    logger.info("Saved PNG: %s (%d bytes)", png_path, len(final_bytes))

    svg_relative: str | None = None
    if svg_path is not None and svg_path.exists():
        svg_relative = f"/api/gallery/{asset_id}/svg"
        logger.info("SVG available: %s", svg_path)

    metadata = {
        "id": asset_id,
        "prompt": body.prompt,
        "refined_prompt": refined,
        "style_id": body.style_id,
        "asset_type": body.asset_type.value,
        "image_model": body.image_model.value,
        "width": body.width,
        "height": body.height,
        "remove_background": body.remove_background,
        "generate_svg": body.generate_svg,
        "upscale": body.upscale,
        "png_path": str(png_path),
        "svg_path": str(svg_path) if svg_path else None,
        "created_at": datetime.utcnow().isoformat(),
    }
    store.save_generation_metadata(asset_id, metadata)
    logger.info("Saved metadata for asset %s.", asset_id)

    # ── Step 6: Return result ──────────────────────────────────────────
    result = GenerationResult(
        id=asset_id,
        prompt=body.prompt,
        refined_prompt=refined,
        style_id=body.style_id,
        asset_type=body.asset_type.value,
        image_model=body.image_model.value,
        png_path=f"/api/gallery/{asset_id}/png",
        svg_path=svg_relative,
        width=body.width,
        height=body.height,
    )

    logger.info("Generation complete: %s", asset_id)
    return result
