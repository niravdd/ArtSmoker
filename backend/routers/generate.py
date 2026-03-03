"""Image generation router — orchestrates the full generation pipeline.

Supports two-level generation:
  Options  — distinctly different creative concepts (different prompts)
  Variations — seed variations of each concept (same prompt, different seeds)

Includes an SSE streaming endpoint for real-time progress updates.
"""

import json
import logging
import queue
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse

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
    status_callback=None,
) -> tuple[bytes, str | None]:
    image_bytes = generate_image(
        refined_prompt=refined_prompt,
        model=body.image_model,
        width=body.width,
        height=body.height,
        seed=seed,
        status_callback=status_callback,
    )
    svg_output_path = (
        store.generated_asset_dir(asset_id) / "asset.svg"
        if body.generate_svg else None
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
    style_snapshot: dict | None = None,
    progress_queue: queue.Queue | None = None,
) -> VariantResult:
    asset_id = f"{batch_id}_o{option_index}_v{variant_index}"

    # Create a status callback that enriches events with option/variant info
    def _status_cb(event):
        if progress_queue:
            event["option"] = option_index
            event["variation"] = variant_index
            progress_queue.put(event)

    final_bytes, svg_url = _generate_single_image(
        asset_id=asset_id,
        refined_prompt=refined_prompt,
        body=body,
        seed=seed,
        status_callback=_status_cb,
    )

    png_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.png"
    svg_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.svg" if svg_url else None

    store.save_generation_metadata(asset_id, {
        "id": asset_id,
        "batch_id": batch_id,
        "option_index": option_index,
        "variant_index": variant_index,
        "original_prompt": body.original_prompt,
        "moderation_original": body.moderation_original,
        "prompt": body.prompt,
        "refined_prompt": refined_prompt,
        "style_id": body.style_id,
        "style_snapshot": style_snapshot,
        "asset_type": body.asset_type.value,
        "image_model": body.image_model.value,
        "width": body.width,
        "height": body.height,
        "seed": seed,
        "remove_background": body.remove_background,
        "generate_svg": body.generate_svg,
        "upscale": body.upscale,
        "png_path": f"/api/gallery/{asset_id}/png",
        "svg_path": svg_url,
        "png_filename": png_filename,
        "svg_filename": svg_filename,
        "created_at": datetime.utcnow().isoformat(),
    })

    result = VariantResult(
        id=asset_id,
        variant_index=variant_index,
        png_path=f"/api/gallery/{asset_id}/png",
        svg_path=svg_url,
        png_filename=png_filename,
        svg_filename=svg_filename,
    )

    # Notify progress
    if progress_queue:
        progress_queue.put({
            "type": "image_done",
            "option": option_index,
            "variation": variant_index,
        })

    return result


# ── Core generation logic (shared by both endpoints) ─────────────────────

def _run_generation(body: GenerationRequest, progress_cb=None):
    """Run the full generation pipeline. Calls progress_cb(event_dict) at each stage."""

    def emit(event):
        if progress_cb:
            progress_cb(event)

    batch_id = str(uuid4())
    n_opts = body.num_options
    n_vars = body.num_variations
    total = n_opts * n_vars

    emit({"type": "started", "batch_id": batch_id, "total": total,
          "num_options": n_opts, "num_variations": n_vars})

    # Load style
    style_profile: StyleProfile | None = None
    if body.style_id:
        data = store.load_style_profile(body.style_id)
        if data is None:
            raise HTTPException(404, detail=f"Style '{body.style_id}' not found.")
        style_profile = StyleProfile(**data)

    # Snapshot key style data for embedding in each asset's metadata
    style_snapshot = None
    if style_profile:
        style_snapshot = {
            "name": style_profile.name,
            "description": style_profile.description,
            "generation_hints": style_profile.generation_hints,
            "analyzed_style": style_profile.analyzed_style.model_dump() if style_profile.analyzed_style else None,
        }

    # Generate concept prompts
    emit({"type": "stage", "stage": "prompts",
          "message": f"Creating {n_opts} concept prompt{'s' if n_opts > 1 else ''}..."})

    try:
        if n_opts == 1:
            if body.asset_type == AssetType.MARKETING_BANNER:
                concept_prompts = [refine_marketing_prompt(body.prompt, style_profile)]
            else:
                concept_prompts = [refine_prompt(body.prompt, style_profile, body.asset_type)]
        else:
            concept_prompts = generate_concept_prompts(
                body.prompt, style_profile, body.asset_type, n_opts,
            )
    except Exception as exc:
        raise HTTPException(502, detail=f"Prompt generation failed: {exc}") from exc

    emit({"type": "stage", "stage": "generating",
          "message": f"Generating {total} images...", "prompts_done": len(concept_prompts)})

    # Build tasks
    prompt_slug = _slugify_prompt(body.prompt)
    all_tasks = []
    for oi, concept_prompt in enumerate(concept_prompts):
        seeds = random.sample(range(0, _SEED_MAX), n_vars)
        for vi in range(n_vars):
            all_tasks.append((oi, vi, concept_prompt, seeds[vi]))

    # Generate images with progress tracking
    progress_q = queue.Queue()
    variant_map: dict[int, list[VariantResult]] = {i: [] for i in range(n_opts)}
    errors: list[str] = []
    completed = 0

    max_workers = 3 if body.upscale else min(total, 5)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
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
                style_snapshot=style_snapshot,
                progress_queue=progress_q,
            )
            futures[future] = (oi, vi)

        for future in as_completed(futures):
            oi, vi = futures[future]
            try:
                variant_map[oi].append(future.result())
                completed += 1
                # Drain the progress queue
                while not progress_q.empty():
                    evt = progress_q.get_nowait()
                    evt["completed"] = completed
                    evt["total"] = total
                    emit(evt)
            except Exception as exc:
                completed += 1
                logger.exception("Option %d / Variant %d failed in batch %s.", oi, vi, batch_id)
                errors.append(f"o{oi}_v{vi}: {exc}")
                emit({"type": "image_error", "option": oi, "variation": vi,
                      "completed": completed, "total": total, "error": str(exc)})

    # Assemble
    options = []
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

    emit({"type": "stage", "stage": "finalizing", "message": "Finalizing..."})

    result = GenerationResult(
        id=batch_id,
        prompt=body.prompt,
        original_prompt=body.original_prompt,
        style_id=body.style_id,
        asset_type=body.asset_type.value,
        image_model=body.image_model.value,
        width=body.width,
        height=body.height,
        num_options=n_opts,
        num_variations=n_vars,
        options=options,
    )

    emit({"type": "complete", "result": result.model_dump(mode="json")})
    return result


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/", response_model=GenerationResult)
async def generate_asset(body: GenerationRequest):
    """Synchronous generation endpoint (no streaming progress)."""
    return _run_generation(body)


@router.post("/stream")
async def generate_asset_stream(body: GenerationRequest):
    """SSE streaming endpoint — sends real-time progress events.

    Events:
      - started:     {batch_id, total, num_options, num_variations}
      - stage:       {stage, message}
      - image_done:  {option, variation, completed, total}
      - image_error: {option, variation, completed, total, error}
      - complete:    {result: GenerationResult}
      - error:       {detail: string}
    """
    event_queue = queue.Queue()

    def sse_format(data: dict) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    def generate():
        def progress_cb(event):
            event_queue.put(event)

        # Run generation in a thread so we can yield SSE events
        from concurrent.futures import ThreadPoolExecutor as TPE
        with TPE(max_workers=1) as executor:
            future = executor.submit(_run_generation, body, progress_cb)

            # Yield events as they arrive
            while not future.done():
                try:
                    event = event_queue.get(timeout=0.5)
                    yield sse_format(event)
                except queue.Empty:
                    # Send keepalive to prevent timeout
                    yield ": keepalive\n\n"

            # Drain remaining events
            while not event_queue.empty():
                event = event_queue.get_nowait()
                yield sse_format(event)

            # Check for exceptions
            exc = future.exception()
            if exc:
                yield sse_format({"type": "error", "detail": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Moderation analysis ───────────────────────────────────────────────────

class ModerationRequest(BaseModel):
    prompt: str
    error_message: str = ""
    image_model: str = "nova_canvas"


@router.post("/analyze-moderation")
async def analyze_moderation(body: ModerationRequest):
    """Analyze why a prompt was flagged by content moderation and suggest a safe rewrite.

    Returns the analysis, the rewritten prompt, and a list of flagged issues.
    """
    from backend.services.bedrock_client import invoke_claude

    analysis_prompt = f"""A user's image generation prompt was blocked by AWS Bedrock's content moderation system for the model "{body.image_model}".

The error was: "{body.error_message}"

The original prompt was:
"{body.prompt}"

Please analyze this and respond with ONLY a JSON object (no markdown fences):
{{
  "issues": [
    "Brief description of each issue that likely triggered moderation (e.g. 'Reference to copyrighted IP: One Piece', 'Violence: fighting with swords toward camera')"
  ],
  "explanation": "A friendly 1-2 sentence explanation for the user about why their prompt was flagged",
  "rewritten_prompt": "A rewritten version of the prompt that preserves the creative intent but avoids all moderation triggers. Keep it under 900 characters. Remove copyrighted IP names, soften violence/weapon language, and rephrase any potentially sensitive content."
}}"""

    try:
        raw = invoke_claude(analysis_prompt, complexity="fast", max_tokens=2048, temperature=0.3)
        # Parse JSON
        import re as _re
        cleaned = raw.strip()
        cleaned = _re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = _re.sub(r"\n?```\s*$", "", cleaned)
        result = json.loads(cleaned.strip())
        return result
    except Exception as exc:
        logger.exception("Moderation analysis failed")
        return {
            "issues": ["Unable to analyze — the AI service returned an error"],
            "explanation": "The prompt was blocked by content moderation. Try removing references to violence, copyrighted characters, or sensitive content.",
            "rewritten_prompt": "",
        }


# ── Post-processing on existing assets ────────────────────────────────────

class PostProcessRequest(BaseModel):
    asset_ids: list[str]
    remove_background: bool = False
    generate_svg: bool = False
    upscale: bool = False


@router.post("/post-process")
async def post_process_assets(body: PostProcessRequest):
    """Apply post-processing (remove bg, upscale, SVG) to existing gallery assets.

    Does not regenerate — works on existing PNGs. Processes sequentially
    with a small delay between upscale calls to avoid API throttling.
    """
    import time

    from backend.services.post_processor import (
        convert_to_svg,
        remove_background,
        upscale_image,
    )

    results = []
    errors = []
    total = len(body.asset_ids)

    for idx, asset_id in enumerate(body.asset_ids):
        path = store.get_generated_file_path(asset_id, "asset.png")
        if path is None:
            errors.append(f"{asset_id}: not found")
            continue

        try:
            current_bytes = path.read_bytes()
            meta = store.load_generation_metadata(asset_id) or {}
            changed = False

            # 1. Background removal
            if body.remove_background:
                try:
                    current_bytes = remove_background(current_bytes)
                    changed = True
                    logger.info("BG removed for %s (%d/%d)", asset_id, idx + 1, total)
                except Exception as exc:
                    logger.warning("BG removal failed for %s: %s", asset_id, exc)

            # 2. Upscale (with throttle delay)
            if body.upscale:
                if idx > 0:
                    time.sleep(1)  # Throttle between upscale calls
                try:
                    prompt = meta.get("refined_prompt", meta.get("prompt", ""))
                    current_bytes = upscale_image(current_bytes, prompt)
                    changed = True
                    logger.info("Upscaled %s (%d/%d)", asset_id, idx + 1, total)
                except Exception as exc:
                    logger.warning("Upscale failed for %s: %s", asset_id, exc)

            # Save updated PNG if changed
            if changed:
                store.save_generated_image(asset_id, "asset.png", current_bytes)

            # 3. SVG conversion (local, no API throttling needed)
            svg_url = meta.get("svg_path")
            if body.generate_svg:
                try:
                    svg_out = store.generated_asset_dir(asset_id) / "asset.svg"
                    convert_to_svg(current_bytes, svg_out)
                    svg_url = f"/api/gallery/{asset_id}/svg"
                    logger.info("SVG created for %s (%d/%d)", asset_id, idx + 1, total)
                except Exception as exc:
                    logger.warning("SVG conversion failed for %s: %s", asset_id, exc)

            # Update metadata
            meta["remove_background"] = body.remove_background
            meta["generate_svg"] = body.generate_svg
            meta["upscale"] = body.upscale
            if svg_url:
                meta["svg_path"] = svg_url
            store.save_generation_metadata(asset_id, meta)

            results.append({"id": asset_id, "svg_url": svg_url})
        except Exception as exc:
            logger.exception("Post-processing failed for %s", asset_id)
            errors.append(f"{asset_id}: {exc}")

    return {"processed": results, "errors": errors}
