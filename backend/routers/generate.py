"""Image generation router — orchestrates the full generation pipeline.

Supports two-level generation:
  Options  — distinctly different creative concepts (different prompts)
  Variations — seed variations of each concept (same prompt, different seeds)
"""

import logging
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from backend.models.generation_request import AssetType, GenerationRequest
from backend.models.generation_result import GenerationResult, OptionResult, VariantResult
from backend.models.style_profile import StyleProfile
from backend.services.image_generator import generate_image
from backend.services.post_processor import process_asset
from backend.services.prompt_engineer import (
    generate_concept_prompts,
    refine_marketing_prompt,
    refine_prompt,
)
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generate"])

_SEED_MAX = 2**31 - 1


def _slugify_prompt(prompt: str, max_len: int = 40) -> str:
    """Turn a user prompt into a short, filesystem-safe slug."""
    slug = prompt.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0]
    return slug or "asset"


def _generate_single_image(
    *,
    asset_id: str,
    refined_prompt: str,
    body: GenerationRequest,
    seed: int,
) -> tuple[bytes, str | None]:
    """Generate and post-process one image. Returns (png_bytes, svg_url|None)."""
    image_bytes = generate_image(
        refined_prompt=refined_prompt,
        model=body.image_model,
        width=body.width,
        height=body.height,
        seed=seed,
    )

    svg_output_path = (
        store.generated_asset_dir(asset_id) / "asset.svg"
        if body.generate_svg
        else None
    )
    final_bytes, svg_path = process_asset(
        image_bytes=image_bytes,
        refined_prompt=refined_prompt,
        remove_bg=body.remove_background,
        do_upscale=body.upscale,
        do_svg=body.generate_svg,
        svg_output_path=svg_output_path,
    )

    store.save_generated_image(asset_id, "asset.png", final_bytes)

    svg_url = f"/api/gallery/{asset_id}/svg" if svg_path and svg_path.exists() else None
    return final_bytes, svg_url


def _build_variant(
    *,
    batch_id: str,
    option_index: int,
    variant_index: int,
    refined_prompt: str,
    body: GenerationRequest,
    seed: int,
    prompt_slug: str,
) -> VariantResult:
    """Generate one variant, save metadata, return result."""
    asset_id = f"{batch_id}_o{option_index}_v{variant_index}"

    final_bytes, svg_url = _generate_single_image(
        asset_id=asset_id,
        refined_prompt=refined_prompt,
        body=body,
        seed=seed,
    )

    # Build human-readable filename:  prompt-slug_opt1_var2.png
    png_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.png"
    svg_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.svg" if svg_url else None

    store.save_generation_metadata(asset_id, {
        "id": asset_id,
        "batch_id": batch_id,
        "option_index": option_index,
        "variant_index": variant_index,
        "prompt": body.prompt,
        "refined_prompt": refined_prompt,
        "style_id": body.style_id,
        "asset_type": body.asset_type.value,
        "image_model": body.image_model.value,
        "width": body.width,
        "height": body.height,
        "seed": seed,
        "png_path": f"/api/gallery/{asset_id}/png",
        "svg_path": svg_url,
        "png_filename": png_filename,
        "svg_filename": svg_filename,
        "created_at": datetime.utcnow().isoformat(),
    })

    return VariantResult(
        id=asset_id,
        variant_index=variant_index,
        png_path=f"/api/gallery/{asset_id}/png",
        svg_path=svg_url,
        png_filename=png_filename,
        svg_filename=svg_filename,
    )


@router.post("/", response_model=GenerationResult)
async def generate_asset(body: GenerationRequest):
    """Main generation endpoint.

    Two-level generation:
    1. Generate num_options distinct concept prompts (different designs).
    2. For each concept, generate num_variations seed variants.

    Total images = num_options x num_variations.
    """
    batch_id = str(uuid4())
    n_opts = body.num_options
    n_vars = body.num_variations
    total = n_opts * n_vars

    logger.info(
        "Starting batch %s: %d options x %d variations = %d images, model=%s, type=%s",
        batch_id, n_opts, n_vars, total,
        body.image_model.value, body.asset_type.value,
    )

    # ── Load style profile ────────────────────────────────────────────
    style_profile: StyleProfile | None = None
    if body.style_id:
        data = store.load_style_profile(body.style_id)
        if data is None:
            raise HTTPException(404, detail=f"Style '{body.style_id}' not found.")
        style_profile = StyleProfile(**data)

    # ── Generate concept prompts ──────────────────────────────────────
    try:
        if n_opts == 1:
            # Single option: just refine normally
            if body.asset_type == AssetType.MARKETING_BANNER:
                concept_prompts = [refine_marketing_prompt(body.prompt, style_profile)]
            else:
                concept_prompts = [refine_prompt(body.prompt, style_profile, body.asset_type)]
        else:
            concept_prompts = generate_concept_prompts(
                body.prompt, style_profile, body.asset_type, n_opts,
            )
    except Exception as exc:
        logger.exception("Prompt generation failed for batch %s.", batch_id)
        raise HTTPException(502, detail=f"Prompt generation failed: {exc}") from exc

    logger.info("Generated %d concept prompts for batch %s.", len(concept_prompts), batch_id)

    # ── Generate all images (parallel) ────────────────────────────────
    prompt_slug = _slugify_prompt(body.prompt)
    options: list[OptionResult] = []

    # Build all tasks: (option_idx, variant_idx, prompt, seed)
    all_tasks = []
    for oi, concept_prompt in enumerate(concept_prompts):
        seeds = random.sample(range(0, _SEED_MAX), n_vars)
        for vi in range(n_vars):
            all_tasks.append((oi, vi, concept_prompt, seeds[vi]))

    # Execute with thread pool (limit concurrency to avoid throttling)
    variant_map: dict[int, list[VariantResult]] = {i: [] for i in range(n_opts)}
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=min(total, 5)) as pool:
        futures = {}
        for oi, vi, prompt, seed in all_tasks:
            future = pool.submit(
                _build_variant,
                batch_id=batch_id,
                option_index=oi,
                variant_index=vi,
                refined_prompt=prompt,
                body=body,
                seed=seed,
                prompt_slug=prompt_slug,
            )
            futures[future] = (oi, vi)

        for future in as_completed(futures):
            oi, vi = futures[future]
            try:
                variant_map[oi].append(future.result())
            except Exception as exc:
                logger.exception("Option %d / Variant %d failed in batch %s.", oi, vi, batch_id)
                errors.append(f"o{oi}_v{vi}: {exc}")

    # Assemble results
    for oi in range(n_opts):
        variants = sorted(variant_map.get(oi, []), key=lambda v: v.variant_index)
        options.append(OptionResult(
            option_index=oi,
            refined_prompt=concept_prompts[oi],
            variants=variants,
        ))

    succeeded = sum(len(o.variants) for o in options)
    if succeeded == 0:
        raise HTTPException(502, detail=f"All images failed: {'; '.join(errors[:5])}")

    result = GenerationResult(
        id=batch_id,
        prompt=body.prompt,
        style_id=body.style_id,
        asset_type=body.asset_type.value,
        image_model=body.image_model.value,
        width=body.width,
        height=body.height,
        num_options=n_opts,
        num_variations=n_vars,
        options=options,
    )

    logger.info(
        "Batch %s complete: %d/%d images succeeded (%d errors).",
        batch_id, succeeded, total, len(errors),
    )
    return result
