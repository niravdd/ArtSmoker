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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from backend.models.generation_request import AssetType, GenerationRequest, ImageModel
from backend.models.generation_result import GenerationResult, OptionResult, VariantResult
from backend.models.style_profile import StyleProfile
from backend.services.image_generator import generate_image
from backend.services.post_processor import process_asset
from backend.services.prompt_engineer import (
    PromptRefusalError,
    generate_concept_prompts,
    get_last_negative_prompt,
    refine_marketing_prompt,
    refine_prompt,
)
from backend.services.prompt_templates import get_template
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generate"])

_SEED_MAX = 2**31 - 1


def _get_model_price(model_key) -> float:
    """Get the per-image price for a model from the registry."""
    key = model_key.value if hasattr(model_key, 'value') else str(model_key)
    try:
        from backend.services.model_registry import get_image_model
        cfg = get_image_model(key)
        return cfg.get("base_price_usd", 0) or 0 if cfg else 0
    except Exception:
        return 0


def _get_model_region(model_key) -> str:
    """Get the region for a model from the registry."""
    key = model_key.value if hasattr(model_key, 'value') else str(model_key)
    try:
        from backend.services.model_registry import get_image_model
        cfg = get_image_model(key)
        return cfg.get("region", "") if cfg else ""
    except Exception:
        return ""


def _slugify_prompt(prompt: str, max_len: int = 40) -> str:
    """Create a filesystem-safe slug from a prompt. Translates non-English text first."""
    # If prompt contains non-ASCII, translate to English for a meaningful slug
    if any(ord(c) > 127 for c in prompt):
        try:
            from backend.services.prompt_translator import translate_to_english
            result = translate_to_english(prompt)
            if result["was_translated"]:
                prompt = result["translated"]
        except Exception:
            pass  # Fall through to slugify whatever we have
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
    negative_prompt: str = "",
    model_override: ImageModel | None = None,
    status_callback=None,
) -> tuple[bytes, str | None]:
    effective_model = model_override or body.image_model
    image_bytes = generate_image(
        refined_prompt=refined_prompt,
        model=effective_model,
        width=body.width,
        height=body.height,
        seed=seed,
        negative_prompt=negative_prompt,
        quality=body.quality,
        region_override=body.region,
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
    negative_prompt: str = "",
    body: GenerationRequest,
    seed: int,
    prompt_slug: str,
    model_override: ImageModel | None = None,
    model_label: str | None = None,
    style_snapshot: dict | None = None,
    translation_result: dict | None = None,
    progress_queue: queue.Queue | None = None,
    cancel_event: threading.Event | None = None,
    cost_accumulator=None,
) -> VariantResult:
    # Share cost accumulator with this worker thread so image costs are tracked
    if cost_accumulator:
        from backend.services.cost_tracker import install_shared_accumulator
        install_shared_accumulator(cost_accumulator)

    asset_id = f"{batch_id}_o{option_index}_v{variant_index}"

    # Check if batch has been cancelled (moderation block on another task)
    if cancel_event and cancel_event.is_set():
        raise RuntimeError("Batch cancelled due to content moderation block on another variant")

    # Create a status callback that enriches events with option/variant info
    def _status_cb(event):
        if progress_queue:
            event["option"] = option_index
            event["variation"] = variant_index
            progress_queue.put(event)

    # Check again right before the expensive API call
    if cancel_event and cancel_event.is_set():
        raise RuntimeError("Batch cancelled due to content moderation block")

    final_bytes, svg_url = _generate_single_image(
        asset_id=asset_id,
        refined_prompt=refined_prompt,
        body=body,
        seed=seed,
        negative_prompt=negative_prompt,
        model_override=model_override,
        status_callback=_status_cb,
    )

    # Check after generation but before saving (another task may have triggered cancel)
    if cancel_event and cancel_event.is_set():
        raise RuntimeError("Batch cancelled due to content moderation block")

    png_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.png"
    svg_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.svg" if svg_url else None

    effective_model = model_override or body.image_model
    store.save_generation_metadata(asset_id, {
        "id": asset_id,
        "batch_id": batch_id,
        "option_index": option_index,
        "variant_index": variant_index,
        "num_options": body.num_options,
        "num_variations": body.num_variations,
        "all_models": body.all_models,
        "original_prompt": body.original_prompt,
        "moderation_original": body.moderation_original,
        "prompt": body.prompt,
        "original_language": translation_result["source_lang"] if translation_result else "en",
        "original_language_prompt": translation_result["original"] if translation_result and translation_result["was_translated"] else None,
        "refined_prompt": refined_prompt,
        "negative_prompt": negative_prompt,
        "style_id": body.style_id,
        "style_snapshot": style_snapshot,
        "asset_type": body.asset_type.value,
        "image_model": effective_model.value if hasattr(effective_model, 'value') else str(effective_model),
        "model_label": model_label or "",
        "quality": body.quality or "",
        "region": _get_model_region(effective_model),
        "width": body.width,
        "height": body.height,
        "seed": seed,
        "remove_background": body.remove_background,
        "generate_svg": body.generate_svg,
        "upscale": body.upscale,
        "upscaled": body.upscale,  # True if upscale was requested (process_asset ran it)
        "ip_owned": body.ip_owned,
        "ip_licensed": body.ip_licensed,
        "png_path": f"/api/gallery/{asset_id}/png",
        "svg_path": svg_url,
        "png_filename": png_filename,
        "svg_filename": svg_filename,
        "created_at": datetime.utcnow().isoformat(),
        "estimated_image_cost_usd": _get_model_price(effective_model),
        "cost_history": [{"action": "generate", "model": effective_model.value if hasattr(effective_model, 'value') else str(effective_model), "cost_usd": _get_model_price(effective_model)}],
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
    from backend.services.cost_tracker import reset_costs, get_total_cost, get_cost_breakdown
    reset_costs()  # Start fresh cost tracking for this request

    # Dispatch to All Models pipeline if requested
    if body.all_models:
        return _run_all_models_generation(body, progress_cb)

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

    # Translate non-English prompts to English before refinement
    translation_result = None
    try:
        from backend.services.prompt_translator import translate_to_english
        translation_result = translate_to_english(body.prompt)
        if translation_result["was_translated"]:
            logger.info("Prompt translated from %s to English: '%s' → '%s'",
                        translation_result["source_lang"],
                        body.prompt[:50], translation_result["translated"][:50])
            body.prompt = translation_result["translated"]
    except Exception as exc:
        logger.warning("Prompt translation failed, using original: %s", exc)

    # Generate concept prompts (skip if pre-composed by the user)
    if body.pre_composed and n_opts == 1:
        # User already composed the prompt via "Compose Generation Prompt" — use as-is
        concept_prompts = [body.prompt]
        emit({"type": "stage", "stage": "prompts",
              "message": "Using your composed prompt..."})
        logger.info("Using pre-composed prompt for batch %s (skipping refinement).", batch_id)
    else:
        emit({"type": "stage", "stage": "prompts",
              "message": f"Creating {n_opts} concept prompt{'s' if n_opts > 1 else ''}..."})

    if not body.pre_composed or n_opts > 1:
        model_id = body.image_model
        try:
            if body.pre_composed and n_opts > 1:
                concept_prompts = generate_concept_prompts(
                    body.prompt, style_profile, body.asset_type, n_opts, image_model=model_id,
                )
            elif n_opts == 1:
                if body.asset_type == AssetType.MARKETING_BANNER:
                    concept_prompts = [refine_marketing_prompt(body.prompt, style_profile, image_model=model_id)]
                else:
                    concept_prompts = [refine_prompt(body.prompt, style_profile, body.asset_type, image_model=model_id)]
            else:
                concept_prompts = generate_concept_prompts(
                    body.prompt, style_profile, body.asset_type, n_opts, image_model=model_id,
                )
        except PromptRefusalError as refusal:
            logger.warning("Claude refused to refine prompt: %s", refusal.reason[:200])
            emit({"type": "prompt_refused",
                  "reason": refusal.reason,
                  "original_response": refusal.original_response[:500],
                  "message": "The AI declined to process this prompt due to content concerns."})
            emit({"type": "stage", "stage": "finalizing", "message": "Prompt refused."})
            result = GenerationResult(
                id=batch_id, prompt=body.prompt, original_prompt=body.original_prompt,
                moderation_original=body.moderation_original, style_id=body.style_id,
                asset_type=body.asset_type.value, image_model=body.image_model,
                width=body.width, height=body.height,
                num_options=n_opts, num_variations=n_vars, options=[],
            )
            emit({"type": "complete", "result": result.model_dump(mode="json"), "prompt_refused": True})
            return result
        except Exception as exc:
            raise HTTPException(502, detail=f"Prompt generation failed: {exc}") from exc

    # Capture the negative prompt: either from refinement (set by refine_prompt /
    # generate_concept_prompts) or carried from the Compose step via the request body
    negative_prompt = get_last_negative_prompt()
    if not negative_prompt and body.negative_prompt:
        negative_prompt = body.negative_prompt
        logger.info("Using negative prompt from pre-composed request: %s", negative_prompt[:100])
    elif negative_prompt:
        logger.info("Using negative prompt from refinement: %s", negative_prompt[:100])

    # Emit the composed/refined prompts so the frontend can display them
    emit({"type": "prompts_ready",
          "prompts": concept_prompts,
          "negative_prompt": negative_prompt or "",
          "pre_composed": body.pre_composed})

    emit({"type": "stage", "stage": "generating",
          "message": f"Generating {total} images...", "prompts_done": len(concept_prompts)})

    prompt_slug = _slugify_prompt(body.prompt)
    progress_q = queue.Queue()
    cancel_event = threading.Event()
    variant_map: dict[int, list[VariantResult]] = {i: [] for i in range(n_opts)}
    errors: list[str] = []
    completed = 0

    # ── Canary request: test first concept prompt before dispatching batch ──
    canary_seed = random.randint(0, _SEED_MAX)
    emit({"type": "stage", "stage": "canary",
          "message": "Testing prompt with image model..."})
    try:
        _canary_result = _build_variant(
            batch_id=batch_id,
            option_index=0,
            variant_index=0,
            refined_prompt=concept_prompts[0],
            negative_prompt=negative_prompt,
            body=body,
            seed=canary_seed,
            prompt_slug=prompt_slug,
            style_snapshot=style_snapshot,
            translation_result=translation_result,
            progress_queue=progress_q,
        )
        variant_map[0].append(_canary_result)
        completed += 1
        # Drain canary progress events
        while not progress_q.empty():
            evt = progress_q.get_nowait()
            evt["completed"] = completed
            evt["total"] = total
            emit(evt)
        emit({"type": "image_done", "option": 0, "variation": 0,
              "completed": completed, "total": total})
    except Exception as canary_exc:
        # Canary failed — check if it's a moderation/non-retriable error
        exc_str = str(canary_exc).lower()
        is_moderation = any(k in exc_str for k in [
            "generation failed", "moderation", "blocked", "not allowed",
            "unsafe", "policy",
        ])
        if is_moderation:
            # Don't dispatch any more tasks — report immediately
            logger.warning("Canary request blocked by moderation in batch %s: %s", batch_id, canary_exc)
            emit({"type": "moderation_blocked", "error": str(canary_exc),
                  "message": "Image generation blocked by content moderation"})
            errors.append(f"canary: {canary_exc}")
            # Set cancel event so the batch and assembly know moderation triggered
            cancel_event.set()
            # Skip the entire parallel batch
            emit({"type": "stage", "stage": "finalizing", "message": "Generation cancelled due to content moderation."})
            # Fall through — cancel_event.is_set() will be checked in assembly
        else:
            # Retriable/transient error on canary — still try the batch
            logger.warning("Canary failed with transient error, proceeding with batch: %s", canary_exc)
            completed += 1
            errors.append(f"o0_v0: {canary_exc}")

    # ── Parallel batch: dispatch remaining tasks (skip canary's o0_v0) ──
    # (cancel_event already created above, may be set by canary moderation block)

    # Build remaining tasks (exclude o0_v0 which was the canary)
    all_tasks = []
    for oi, concept_prompt in enumerate(concept_prompts):
        seeds = random.sample(range(0, _SEED_MAX), n_vars)
        for vi in range(n_vars):
            if oi == 0 and vi == 0:
                continue  # Already done as canary
            all_tasks.append((oi, vi, concept_prompt, seeds[vi]))

    if all_tasks and not cancel_event.is_set():
        emit({"type": "stage", "stage": "generating",
              "message": f"Generating remaining {len(all_tasks)} images..."})

        from backend.services.cost_tracker import share_accumulator_with_thread
        shared_acc = share_accumulator_with_thread()
        max_workers = 3 if body.upscale else min(len(all_tasks), 5)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for oi, vi, prompt, seed in all_tasks:
                future = pool.submit(
                    _build_variant,
                    batch_id=batch_id,
                    option_index=oi,
                    variant_index=vi,
                    refined_prompt=prompt,
                    negative_prompt=negative_prompt,
                    body=body,
                    seed=seed,
                    prompt_slug=prompt_slug,
                    style_snapshot=style_snapshot,
                    translation_result=translation_result,
                    progress_queue=progress_q,
                    cancel_event=cancel_event,
                    cost_accumulator=shared_acc,
                )
                futures[future] = (oi, vi)

            for future in as_completed(futures):
                oi, vi = futures[future]
                try:
                    variant_map[oi].append(future.result())
                    completed += 1
                    while not progress_q.empty():
                        evt = progress_q.get_nowait()
                        evt["completed"] = completed
                        evt["total"] = total
                        emit(evt)
                except Exception as exc:
                    completed += 1
                    exc_str = str(exc).lower()
                    is_moderation = any(k in exc_str for k in [
                        "generation failed", "moderation", "blocked",
                        "not allowed", "unsafe", "policy", "cancelled",
                    ])
                    if is_moderation and not cancel_event.is_set():
                        if body.pre_composed:
                            # Pre-composed/rewritten prompt — don't cancel batch.
                            # The canary passed, so this is a seed-dependent block.
                            # Let remaining tasks complete and return partial results.
                            logger.warning("Moderation block on o%d_v%d in batch %s (pre-composed — continuing batch).", oi, vi, batch_id)
                            emit({"type": "image_error", "option": oi, "variation": vi,
                                  "completed": completed, "total": total,
                                  "error": "Blocked by content moderation (seed-dependent — other variants may succeed)"})
                        else:
                            # Raw prompt — cancel remaining (prompt itself may be problematic)
                            cancel_event.set()
                            logger.warning("Moderation block in batch %s, cancelling remaining tasks.", batch_id)
                            emit({"type": "moderation_blocked", "error": str(exc),
                                  "option": oi, "variation": vi,
                                  "message": "Content moderation blocked — cancelling remaining"})
                    elif not cancel_event.is_set():
                        logger.exception("Option %d / Variant %d failed in batch %s.", oi, vi, batch_id)
                    errors.append(f"o{oi}_v{vi}: {exc}")
                    emit({"type": "image_error", "option": oi, "variation": vi,
                          "completed": completed, "total": total, "error": str(exc)})

    # Check if moderation blocked the batch
    moderation_triggered = cancel_event.is_set()

    if moderation_triggered and not body.pre_composed:
        # Raw prompt batch cancelled by moderation — discard all results
        logger.warning("Batch %s cancelled due to moderation. Cleaning up partial results.", batch_id)
        for oi_variants in variant_map.values():
            for v in oi_variants:
                try:
                    store.delete_generated_asset(v.id)
                except Exception:
                    pass
        emit({"type": "stage", "stage": "finalizing", "message": "Generation cancelled due to content moderation."})

        result = GenerationResult(
            id=batch_id,
            prompt=body.prompt,
            original_prompt=body.original_prompt,
            moderation_original=body.moderation_original,
            style_id=body.style_id,
            asset_type=body.asset_type.value,
            image_model=body.image_model,
            width=body.width,
            height=body.height,
            num_options=n_opts,
            num_variations=n_vars,
            options=[],  # Empty — moderation blocked
        )
        emit({"type": "complete", "result": result.model_dump(mode="json"), "moderation_blocked": True})
        return result

    # Collect blocked variants for retry info
    blocked_variants = [e for e in errors if "moderation" in e.lower() or "blocked" in e.lower()]

    if moderation_triggered and body.pre_composed:
        # Pre-composed/rewritten prompt — some variants blocked by seed-dependent moderation.
        # Keep the successful images and return partial results.
        successful_count = sum(len(v) for v in variant_map.values())
        logger.info("Batch %s partial: %d succeeded, %d blocked (pre-composed — keeping results).",
                     batch_id, successful_count, len(blocked_variants))
        emit({"type": "stage", "stage": "finalizing",
              "message": f"Completing with {successful_count} images ({len(blocked_variants)} blocked by moderation on specific seeds)"})

    # Assemble successful results
    options = []
    for oi in range(n_opts):
        variants = sorted(variant_map.get(oi, []), key=lambda v: v.variant_index)
        if variants:  # Only include options that have at least one variant
            options.append(OptionResult(
                option_index=oi,
                refined_prompt=concept_prompts[oi],
                negative_prompt=negative_prompt,
                image_model=body.image_model,
                variants=variants,
            ))

    succeeded = sum(len(o.variants) for o in options)
    if succeeded == 0:
        raise HTTPException(502, detail=f"All images failed: {'; '.join(errors[:5])}")

    emit({"type": "stage", "stage": "finalizing", "message": "Finalizing..."})

    # Compute total actual cost from all Bedrock calls in this request
    actual_cost = get_total_cost()
    cost_breakdown = get_cost_breakdown()

    result = GenerationResult(
        id=batch_id,
        prompt=body.prompt,
        original_prompt=body.original_prompt,
        negative_prompt=negative_prompt or None,
        style_id=body.style_id,
        asset_type=body.asset_type.value,
        image_model=body.image_model,
        width=body.width,
        height=body.height,
        num_options=n_opts,
        num_variations=n_vars,
        options=options,
        blocked_count=len(blocked_variants) if blocked_variants else 0,
        total_cost_usd=actual_cost,
        cost_breakdown=cost_breakdown,
    )

    # Send accurate cost to telemetry
    from backend.services.telemetry import track_image_cost
    track_image_cost(cost_usd=actual_cost, model=body.image_model,
                     breakdown=json.dumps(cost_breakdown, default=str))

    emit({"type": "complete", "result": result.model_dump(mode="json")})
    return result


# ── All Models generation ─────────────────────────────────────────────────

def _run_all_models_generation(body: GenerationRequest, progress_cb=None):
    """Generate with every enabled image model — one option per model, 1 variation each.

    Each model runs independently: moderation blocks on one model don't
    cancel others. Per-model status is reported in real-time via SSE.
    """
    from backend.services.model_registry import (
        get_enabled_image_model_keys_sorted,
        get_image_model_label,
    )

    def emit(event):
        if progress_cb:
            progress_cb(event)

    batch_id = str(uuid4())
    model_keys = get_enabled_image_model_keys_sorted()
    n_models = len(model_keys)

    if n_models == 0:
        raise HTTPException(400, detail="No image models are enabled.")

    model_labels = {k: get_image_model_label(k) for k in model_keys}
    total = n_models  # 1 variation per model

    emit({"type": "started", "batch_id": batch_id, "total": total,
          "num_options": n_models, "num_variations": 1,
          "all_models": True, "model_labels": model_labels})

    # Load style
    style_profile: StyleProfile | None = None
    if body.style_id:
        data = store.load_style_profile(body.style_id)
        if data is None:
            raise HTTPException(404, detail=f"Style '{body.style_id}' not found.")
        style_profile = StyleProfile(**data)

    style_snapshot = None
    if style_profile:
        style_snapshot = {
            "name": style_profile.name,
            "description": style_profile.description,
            "generation_hints": style_profile.generation_hints,
            "analyzed_style": style_profile.analyzed_style.model_dump() if style_profile.analyzed_style else None,
        }

    # Translate non-English prompts to English
    translation_result = None
    try:
        from backend.services.prompt_translator import translate_to_english
        translation_result = translate_to_english(body.prompt)
        if translation_result["was_translated"]:
            logger.info("All-models: translated %s → English: '%s'",
                        translation_result["source_lang"], translation_result["translated"][:50])
            body.prompt = translation_result["translated"]
    except Exception as exc:
        logger.warning("Prompt translation failed in all-models, using original: %s", exc)

    # Generate prompts — one shared prompt or one per model
    emit({"type": "stage", "stage": "prompts",
          "message": f"Creating prompts for {n_models} models..."})

    concept_prompts: dict[str, str] = {}  # model_key → prompt
    negative_prompts: dict[str, str] = {}  # model_key → negative

    try:
        if body.model_optimized_prompts:
            # Model-optimized: refine once per model for tailored prompts
            for mk in model_keys:
                if body.asset_type == AssetType.MARKETING_BANNER:
                    concept_prompts[mk] = refine_marketing_prompt(
                        body.prompt, style_profile, image_model=mk)
                else:
                    concept_prompts[mk] = refine_prompt(
                        body.prompt, style_profile, body.asset_type, image_model=mk)
                negative_prompts[mk] = get_last_negative_prompt()
                logger.info("Model-optimized prompt for %s: %s", mk, concept_prompts[mk][:80])
        else:
            # Same prompt for all: refine once (model-neutral)
            if body.pre_composed:
                shared_prompt = body.prompt
                shared_negative = body.negative_prompt or ""
            else:
                if body.asset_type == AssetType.MARKETING_BANNER:
                    shared_prompt = refine_marketing_prompt(body.prompt, style_profile)
                else:
                    shared_prompt = refine_prompt(body.prompt, style_profile, body.asset_type)
                shared_negative = get_last_negative_prompt()
                if not shared_negative and body.negative_prompt:
                    shared_negative = body.negative_prompt
            for mk in model_keys:
                # Truncate shared prompt to each model's specific limit
                from backend.services.prompt_engineer import get_prompt_limit as _get_limit
                limit = _get_limit(mk)
                truncated = shared_prompt
                if len(truncated) > limit:
                    truncated = truncated[:limit - 4].rsplit(" ", 1)[0]
                    logger.info("Truncated prompt for %s: %d -> %d chars (limit %d)",
                                mk, len(shared_prompt), len(truncated), limit)
                concept_prompts[mk] = truncated
                negative_prompts[mk] = shared_negative
    except PromptRefusalError as refusal:
        logger.warning("Prompt refused in all-models generation: %s", refusal.reason[:200])
        emit({"type": "prompt_refused", "reason": refusal.reason,
              "original_response": refusal.original_response[:500],
              "message": "The AI declined to process this prompt."})
        result = GenerationResult(
            id=batch_id, prompt=body.prompt, original_prompt=body.original_prompt,
            style_id=body.style_id, asset_type=body.asset_type.value,
            image_model="all_models", width=body.width, height=body.height,
            num_options=n_models, num_variations=1, all_models=True, options=[],
        )
        emit({"type": "complete", "result": result.model_dump(mode="json"), "prompt_refused": True})
        return result
    except Exception as exc:
        raise HTTPException(502, detail=f"Prompt generation failed: {exc}") from exc

    # Emit prompts
    emit({"type": "prompts_ready",
          "prompts": [concept_prompts[mk] for mk in model_keys],
          "negative_prompt": negative_prompts.get(model_keys[0], ""),
          "pre_composed": body.pre_composed,
          "all_models": True,
          "model_labels": {i: model_labels[mk] for i, mk in enumerate(model_keys)}})

    # Generate one image per model — independently, no cooperative cancellation
    emit({"type": "stage", "stage": "generating",
          "message": f"Generating with {n_models} models..."})

    prompt_slug = _slugify_prompt(body.prompt)
    model_map: dict[int, str] = {}
    options: list[OptionResult] = []
    completed = 0

    max_workers = 3 if body.upscale else min(n_models, 5)
    progress_q = queue.Queue()

    from backend.services.cost_tracker import share_accumulator_with_thread
    shared_acc = share_accumulator_with_thread()

    def _generate_for_model(option_index: int, model_key: str) -> OptionResult:
        """Generate one variant with a specific model. Returns OptionResult with status."""
        from backend.services.telemetry import track_image_generation
        from backend.services.model_registry import get_image_model as _get_model
        model_enum = model_key  # Now a plain string, not an enum
        label = model_labels[model_key]
        prompt = concept_prompts[model_key]
        negative = negative_prompts.get(model_key, "")
        seed = random.randint(0, _SEED_MAX)

        try:
            variant = _build_variant(
                batch_id=batch_id,
                option_index=option_index,
                variant_index=0,
                refined_prompt=prompt,
                negative_prompt=negative,
                body=body,
                seed=seed,
                prompt_slug=prompt_slug,
                model_override=model_enum,
                model_label=label,
                style_snapshot=style_snapshot,
                translation_result=translation_result,
                progress_queue=progress_q,
                cost_accumulator=shared_acc,
            )
            # Track each model individually (no cost — actual cost sent by generation_cost at the end)
            track_image_generation(
                model=model_key,
                cost_usd=0,
                num_options=1,
                num_variations=1,
            )
            return OptionResult(
                option_index=option_index,
                refined_prompt=prompt,
                negative_prompt=negative,
                image_model=model_key,
                model_label=label,
                status="success",
                variants=[variant],
            )
        except Exception as exc:
            exc_str = str(exc).lower()
            is_moderation = any(k in exc_str for k in [
                "generation failed", "moderation", "blocked",
                "not allowed", "unsafe", "policy",
            ])
            status = "moderation_blocked" if is_moderation else "error"
            logger.warning("All-models: %s failed (%s): %s", label, status, exc)
            return OptionResult(
                option_index=option_index,
                refined_prompt=prompt,
                negative_prompt=negative,
                image_model=model_key,
                model_label=label,
                status=status,
                status_detail=str(exc),
                variants=[],
            )

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for i, mk in enumerate(model_keys):
            model_map[i] = mk
            future = pool.submit(_generate_for_model, i, mk)
            futures[future] = (i, mk)

        for future in as_completed(futures):
            i, mk = futures[future]
            opt_result = future.result()
            options.append(opt_result)
            completed += 1

            # Drain progress events
            while not progress_q.empty():
                evt = progress_q.get_nowait()
                evt["completed"] = completed
                evt["total"] = total
                emit(evt)

            # Emit per-model status
            emit({"type": "model_status",
                  "model": mk,
                  "model_label": model_labels[mk],
                  "option_index": i,
                  "status": opt_result.status,
                  "status_detail": opt_result.status_detail,
                  "completed": completed,
                  "total": total})

    # Sort options by original model order
    options.sort(key=lambda o: o.option_index)

    succeeded = sum(1 for o in options if o.status == "success")
    blocked = sum(1 for o in options if o.status == "moderation_blocked")
    failed = sum(1 for o in options if o.status == "error")

    emit({"type": "stage", "stage": "finalizing", "message": "Finalizing..."})

    from backend.services.cost_tracker import get_total_cost, get_cost_breakdown
    actual_cost = get_total_cost()
    cost_breakdown = get_cost_breakdown()

    result = GenerationResult(
        id=batch_id,
        prompt=body.prompt,
        original_prompt=body.original_prompt,
        negative_prompt=negative_prompts.get(model_keys[0], ""),
        style_id=body.style_id,
        asset_type=body.asset_type.value,
        image_model="all_models",
        width=body.width,
        height=body.height,
        num_options=n_models,
        num_variations=1,
        all_models=True,
        model_map=model_map,
        options=options,
        total_cost_usd=actual_cost,
        cost_breakdown=cost_breakdown,
    )

    from backend.services.telemetry import track_image_cost
    track_image_cost(cost_usd=actual_cost, model="all_models",
                     breakdown=json.dumps(cost_breakdown, default=str))

    # Summary
    summary_parts = []
    if succeeded:
        summary_parts.append(f"{succeeded} succeeded")
    if blocked:
        blocked_names = [o.model_label for o in options if o.status == "moderation_blocked"]
        summary_parts.append(f"{blocked} blocked ({', '.join(blocked_names)})")
    if failed:
        summary_parts.append(f"{failed} failed")

    emit({"type": "complete",
          "result": result.model_dump(mode="json"),
          "all_models_summary": {
              "succeeded": succeeded,
              "blocked": blocked,
              "failed": failed,
              "total_models": n_models,
              "summary": "; ".join(summary_parts),
          }})
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
    # Track telemetry — event count only (no cost here — actual cost sent by generation_cost at the end)
    if not body.all_models:
        from backend.services.telemetry import track_image_generation
        track_image_generation(
            model=body.image_model or "",
            cost_usd=0,  # Actual cost tracked by cost_tracker and sent in generation_cost event
            num_options=body.num_options,
            num_variations=body.num_variations,
        )

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


# ── Image Editing Services (Inpaint, Outpaint, Erase) ─────────────────────

class ImageEditRequest(BaseModel):
    """Request for image editing services (inpaint, outpaint, erase, etc.)."""
    source_image_id: str  # Gallery asset ID to edit
    model: str  # Registry key of the editing model (e.g. 'stability_inpaint')
    prompt: str = ""  # What to generate (required for inpaint, optional for erase)
    negative_prompt: str = ""
    mask: str | None = None  # Base64-encoded mask image (white = edit area)
    mask_prompt: str | None = None  # Natural language mask (Nova Canvas only)
    region: str | None = None
    seed: int | None = None
    # Outpaint-specific
    outpaint_left: int = 0
    outpaint_right: int = 0
    outpaint_up: int = 0
    outpaint_down: int = 0
    # Extra params (control_strength, grow_mask, creativity, etc.)
    extra_params: dict | None = None


@router.post("/edit")
async def edit_image(body: ImageEditRequest):
    """Apply an image editing service (inpaint, outpaint, erase, search-replace, etc.)."""
    from backend.services.bedrock_client import invoke_image_model
    from backend.services.model_registry import get_image_model, get_image_model_label
    from backend.services.post_processor import process_asset
    from backend.services.telemetry import track_image_edit
    from backend.services.cost_tracker import reset_costs, get_total_cost
    reset_costs()

    # Validate model exists and has an editing purpose
    model_config = get_image_model(body.model)
    if not model_config:
        raise HTTPException(404, detail=f"Unknown model: {body.model}")
    purpose = model_config.get("model_purpose", "")
    label = model_config.get("label", body.model)

    # Load source image from gallery
    source_path = store.get_generated_file_path(body.source_image_id, "asset.png")
    if source_path is None:
        raise HTTPException(404, detail=f"Source image not found: {body.source_image_id}")
    source_bytes = source_path.read_bytes()

    # Decode mask if provided
    mask_bytes = None
    if body.mask:
        import base64 as _b64
        try:
            mask_bytes = _b64.b64decode(body.mask)
        except Exception:
            raise HTTPException(400, detail="Invalid base64 mask data")

    # Build extra params for outpainting
    extra = body.extra_params or {}
    if purpose == "outpainting":
        if body.outpaint_left > 0:
            extra["left"] = body.outpaint_left
        if body.outpaint_right > 0:
            extra["right"] = body.outpaint_right
        if body.outpaint_up > 0:
            extra["up"] = body.outpaint_up
        if body.outpaint_down > 0:
            extra["down"] = body.outpaint_down

    # Translate non-English edit prompts — preserve originals for metadata
    from backend.services.prompt_translator import translate_to_english
    edit_original_language = "en"
    edit_original_prompts = {}  # field → original non-English text

    for field_name in ("prompt", "search_prompt", "select_prompt"):
        val = getattr(body, field_name, None)
        if not val:
            continue
        try:
            tr = translate_to_english(val)
            if tr["was_translated"]:
                edit_original_language = tr["source_lang"]
                edit_original_prompts[field_name] = val
                setattr(body, field_name, tr["translated"])
        except Exception:
            pass

    logger.info("Image edit: model=%s purpose=%s source=%s prompt=%s",
                body.model, purpose, body.source_image_id, body.prompt[:50] if body.prompt else "(none)")

    try:
        result_bytes = invoke_image_model(
            body.model,
            body.prompt,
            negative_prompt=body.negative_prompt,
            seed=body.seed,
            region_override=body.region,
            source_image=source_bytes,
            mask_image=mask_bytes,
            mask_prompt=body.mask_prompt,
            extra_params=extra if extra else None,
        )
    except Exception as exc:
        logger.error("Image edit failed: %s", exc)
        raise HTTPException(502, detail=f"Image editing failed: {exc}")

    # ── Versioned save: keep all previous versions, latest is always asset.png ──
    asset_id = body.source_image_id
    source_meta = store.load_generation_metadata(asset_id) or {}

    # Determine current version number
    versions = source_meta.get("versions", [])
    if not versions:
        # First edit — record the current state as version 1 (the original).
        # The actual file archiving (asset.png → asset_v1.png) happens below
        # in the "archive current" block before the new image is saved.
        versions.append({
            "version": 1,
            "type": "original",
            "prompt": source_meta.get("prompt", ""),
            "refined_prompt": source_meta.get("refined_prompt", ""),
            "negative_prompt": source_meta.get("negative_prompt", ""),
            "image_model": source_meta.get("image_model", ""),
            "model_label": source_meta.get("model_label", ""),
            "timestamp": source_meta.get("created_at", ""),
        })

    # New version number
    next_version = len(versions) + 1
    version_file = f"asset_v{next_version}.png"

    # Archive the current asset.png as the previous version before overwriting
    asset_dir = store.generated_asset_dir(asset_id)
    import shutil
    current_png = asset_dir / "asset.png"
    if current_png.exists():
        prev_version = next_version - 1
        prev_file = f"asset_v{prev_version}.png"
        if not (asset_dir / prev_file).exists():
            shutil.copy2(str(current_png), str(asset_dir / prev_file))
            logger.info("Archived asset.png → %s", prev_file)
        # Also archive current SVG if it exists
        current_svg = asset_dir / "asset.svg"
        prev_svg = f"asset_v{prev_version}.svg"
        if current_svg.exists() and not (asset_dir / prev_svg).exists():
            shutil.copy2(str(current_svg), str(asset_dir / prev_svg))

    # Save the new edited image as asset.png (becomes the latest)
    store.save_generated_image(asset_id, "asset.png", result_bytes)

    # Generate SVG for the new latest version
    try:
        from backend.services.post_processor import process_asset
        svg_output_path = asset_dir / "asset.svg"
        _, svg_path = process_asset(
            image_bytes=result_bytes,
            refined_prompt=body.prompt,
            remove_bg=False,
            do_upscale=False,
            do_svg=True,
            svg_output_path=svg_output_path,
        )
        if svg_path and svg_path.exists():
            logger.info("Generated SVG for latest version")
    except Exception as svg_err:
        logger.warning("SVG generation failed: %s", svg_err)

    # Add version record (this becomes the latest — archived by next edit)
    versions.append({
        "version": next_version,
        "type": purpose,
        "prompt": body.prompt,
        "negative_prompt": body.negative_prompt,
        "mask_prompt": body.mask_prompt,
        "original_language": edit_original_language,
        "original_language_prompts": edit_original_prompts if edit_original_prompts else None,
        "image_model": body.model,
        "model_label": label,
        "region": body.region or model_config.get("region", ""),
        "seed": body.seed,
        "extra_params": body.extra_params,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Update metadata — preserve ALL original fields, add version tracking
    new_meta = dict(source_meta)
    new_meta.update({
        "original_prompt": source_meta.get("original_prompt") or source_meta.get("prompt", ""),
        "original_image_model": source_meta.get("original_image_model") or source_meta.get("image_model", ""),
        "versions": versions,
        "current_version": next_version,
        "last_edited_at": datetime.utcnow().isoformat(),
        "last_edit_type": purpose,
        "last_edit_model": body.model,
        "last_edit_prompt": body.prompt,
    })
    store.save_generation_metadata(asset_id, new_meta)

    svg_url = new_meta.get("svg_path")
    png_filename = new_meta.get("png_filename", f"{asset_id}.png")

    # Track cost for this edit
    edit_cost = get_total_cost()
    edit_cfg = get_image_model(body.model) if body.model else {}
    track_image_edit(
        edit_type=edit_cfg.get("model_purpose", ""),
        model=body.model or "",
        cost_usd=edit_cost,
    )

    return {
        "id": asset_id,
        "png_url": f"/api/gallery/{asset_id}/png",
        "png_filename": png_filename,
        "edit_type": purpose,
        "model": body.model,
        "model_label": label,
    }


# ── Pre-screen (Safe Mode) ─────────────────────────────────────────────────

class PreScreenRequest(BaseModel):
    prompt: str
    image_model: str = "nova_canvas"


@router.post("/pre-screen")
async def pre_screen_prompt(body: PreScreenRequest):
    """Quick pre-screen using Claude Sonnet (fast, cheap) to check if a prompt
    will likely trigger moderation on the selected model.

    Returns: likely_safe, issues, suggested_model (if the prompt is better
    suited for a more permissive model).
    """
    from backend.services.bedrock_client import invoke_llm
    import re as _re

    from backend.services.model_registry import get_enabled_model_labels
    model_labels = get_enabled_model_labels()
    model_label = model_labels.get(body.image_model, body.image_model)

    # Translate non-English prompt for consistent moderation
    prompt_for_screen = body.prompt
    try:
        from backend.services.prompt_translator import translate_to_english
        tr = translate_to_english(body.prompt)
        if tr["was_translated"]:
            prompt_for_screen = tr["translated"]
    except Exception:
        pass

    screen_prompt = get_template('moderation_prescreen').format(
        prompt_for_screen=prompt_for_screen,
        model_label=model_label,
    )

    try:
        raw = invoke_llm(screen_prompt, complexity="fast", max_tokens=512, temperature=0.2)
        cleaned = raw.strip()
        cleaned = _re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = _re.sub(r"\n?```\s*$", "", cleaned)
        result = json.loads(cleaned.strip())

        # Normalize suggested_model to our internal key
        suggested = result.get("suggested_model")
        if suggested:
            # Build reverse map dynamically from registry (model_id → key, label → key)
            from backend.services.model_registry import get_enabled_image_models
            reverse_map = {}
            for k, cfg in get_enabled_image_models().items():
                reverse_map[cfg.get("model_id", "")] = k
                reverse_map[cfg.get("label", "")] = k
                reverse_map[k] = k  # key → key identity
            reverse_map.update({v: k for k, v in model_labels.items()})
            normalized = reverse_map.get(suggested, suggested)
            result["suggested_model"] = normalized
            result["suggested_model_label"] = model_labels.get(normalized, suggested)

        return result
    except Exception as exc:
        logger.warning("Pre-screen failed: %s", exc)
        return {"likely_safe": True, "issues": [], "explanation": "Pre-screening unavailable", "suggested_model": None}


# ── Moderation analysis ───────────────────────────────────────────────────

class ModerationRequest(BaseModel):
    prompt: str
    error_message: str = ""
    image_model: str = "nova_canvas"
    width: int = 512
    height: int = 512
    force_rewrite: bool = False  # Skip model switching, go straight to rewrite for the target model


# Model permissiveness order (most permissive first for fallback testing)
_ALTERNATIVE_MODELS = [
    ImageModel.SD35_LARGE,
    ImageModel.STABLE_IMAGE_ULTRA,
    ImageModel.TITAN_IMAGE,
    ImageModel.NOVA_CANVAS,
]


@router.post("/analyze-moderation")
async def analyze_moderation(body: ModerationRequest):
    """Smart moderation handling for game artists.

    Strategy (in order):
    1. Try the SAME prompt on alternative, more permissive models
       (game art with weapons/combat often passes on Stable Diffusion 3.5 but not Nova Canvas)
    2. Only if ALL models reject → rewrite the prompt (last resort)
    3. Returns: which model works, or a verified rewrite

    Preserves the artist's creative intent as much as possible.
    """
    from backend.services.bedrock_client import invoke_llm
    import re as _re

    original_model = body.image_model
    original_model_enum = ImageModel(original_model) if original_model in [m.value for m in ImageModel] else ImageModel.NOVA_CANVAS
    attempts: list[dict] = []
    test_seed = random.randint(0, _SEED_MAX)

    # ── Phase 1: Try alternative models with the SAME prompt ──────────
    # Skip this phase if force_rewrite is True (user explicitly wants a rewrite for their chosen model)
    if body.force_rewrite:
        logger.info("force_rewrite=True — skipping model switching, going straight to rewrite for %s", original_model)
        working_model = None
        models_to_try = []
    else:
        working_model = None
        models_to_try = [m for m in _ALTERNATIVE_MODELS if m != original_model_enum]

    for alt_model in models_to_try:
        logger.info("Moderation fallback: testing '%s' on %s...", body.prompt[:50], alt_model.value)
        try:
            generate_image(
                refined_prompt=body.prompt,
                model=alt_model,
                width=body.width,
                height=body.height,
                seed=test_seed,
            )
            working_model = alt_model
            logger.info("Moderation fallback: %s ACCEPTED the prompt.", alt_model.value)
            attempts.append({
                "phase": "model_test",
                "model": alt_model.value,
                "prompt": body.prompt,
                "status": "passed",
            })
            break
        except Exception as exc:
            logger.info("Moderation fallback: %s also rejected: %s", alt_model.value, str(exc)[:100])
            attempts.append({
                "phase": "model_test",
                "model": alt_model.value,
                "prompt": body.prompt,
                "status": "failed",
                "error": str(exc)[:200],
            })

    if working_model:
        # Found a model that accepts the prompt as-is!
        from backend.services.model_registry import get_enabled_model_labels as _get_labels
        model_labels = _get_labels()
        return {
            "action": "switch_model",
            "working_model": working_model.value,
            "working_model_label": model_labels.get(working_model.value, working_model.value),
            "original_model": original_model,
            "original_model_label": model_labels.get(original_model, original_model),
            "issues": [f"{model_labels.get(original_model, original_model)} has strict content moderation that blocks game art with combat/weapon content"],
            "explanation": (
                f"Your prompt works with {model_labels.get(working_model.value, working_model.value)} "
                f"but was blocked by {model_labels.get(original_model, original_model)}. "
                f"This is common for game art — Stable Diffusion 3.5 Large and Stable Image Ultra are more "
                f"permissive with action/combat content while still producing high-quality results."
            ),
            "rewritten_prompt": body.prompt,  # Same prompt, no rewrite needed
            "verified": True,
            "attempts": attempts,
        }

    # ── Phase 2: ALL models rejected → rewrite as last resort ─────────
    logger.warning("All models rejected the prompt. Proceeding to rewrite.")

    current_prompt = body.prompt
    all_issues: list[str] = [f"Blocked by all available models ({', '.join(m.value for m in _ALTERNATIVE_MODELS)})"]
    explanation = ""
    max_rewrites = 3

    from backend.services.model_registry import get_all_model_labels as _get_all_labels
    target_label = _get_all_labels().get(original_model, original_model)

    for attempt_num in range(max_rewrites):
        target_context = (
            f"The rewrite MUST pass {target_label}'s moderation filters specifically."
            if body.force_rewrite else
            f"The prompt was blocked by ALL available image generation models."
        )

        prompt_label = "Original" if attempt_num == 0 else "Previous rewrite that STILL FAILED"
        issues_text = json.dumps(all_issues, indent=2) if attempt_num > 0 else body.error_message

        rewrite_context = (
            f"A user's prompt was blocked by an AI image generation model's content moderation.\n"
            f"{target_context}\n\n"
            f"{prompt_label} prompt:\n"
            f'"{current_prompt}"\n\n'
            f"Specific issues identified:\n"
            f"{issues_text}\n\n"
        )

        rewrite_instruction = rewrite_context + get_template('moderation_rewrite')

        try:
            raw = invoke_llm(rewrite_instruction, complexity="fast", max_tokens=2048, temperature=0.3)
            cleaned = raw.strip()
            cleaned = _re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = _re.sub(r"\n?```\s*$", "", cleaned)
            parsed = json.loads(cleaned.strip())

            rewritten = parsed.get("rewritten_prompt", "")
            issues = parsed.get("issues", [])
            explanation = parsed.get("explanation", explanation)
            all_issues.extend(issues)

            if not rewritten:
                attempts.append({"phase": "rewrite", "attempt": attempt_num + 1, "prompt": current_prompt, "status": "rewrite_empty"})
                continue

            # Test rewrite: if force_rewrite, test against the TARGET model specifically;
            # otherwise test on the most permissive models first
            test_models = [original_model_enum] if body.force_rewrite else _ALTERNATIVE_MODELS
            for test_model in test_models:
                try:
                    generate_image(
                        refined_prompt=rewritten,
                        model=test_model,
                        width=body.width,
                        height=body.height,
                        seed=random.randint(0, _SEED_MAX),
                    )
                    logger.info("Rewrite attempt %d passed on %s.", attempt_num + 1, test_model.value)
                    attempts.append({
                        "phase": "rewrite",
                        "attempt": attempt_num + 1,
                        "prompt": rewritten,
                        "model_tested": test_model.value,
                        "status": "passed",
                    })
                    return {
                        "action": "rewrite",
                        "working_model": test_model.value,
                        "original_model": original_model,
                        "issues": list(set(all_issues)),
                        "explanation": explanation,
                        "rewritten_prompt": rewritten,
                        "verified": True,
                        "attempts": attempts,
                    }
                except Exception:
                    continue

            # Rewrite failed on all models too
            attempts.append({"phase": "rewrite", "attempt": attempt_num + 1, "prompt": rewritten, "status": "failed_all_models"})
            current_prompt = rewritten

        except Exception as exc:
            logger.warning("Rewrite analysis attempt %d failed: %s", attempt_num + 1, exc)
            attempts.append({"phase": "rewrite", "attempt": attempt_num + 1, "status": "analysis_error", "error": str(exc)})

    # Nothing worked — check if we ever got a real rewrite or if all attempts errored
    got_any_rewrite = any(a.get("phase") == "rewrite" and a.get("prompt") and a["prompt"] != body.prompt
                          for a in attempts)
    return {
        "action": "failed",
        "issues": list(set(all_issues)),
        "explanation": (
            "The AI service is currently unavailable. Please try again in a few minutes."
            if not got_any_rewrite else
            "This prompt was rejected by all models even after multiple rewrites. The content may need significant changes. Please try a substantially different description."
        ),
        "rewritten_prompt": current_prompt if got_any_rewrite and current_prompt != body.prompt else None,
        "verified": False,
        "attempts": attempts,
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
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_post_process
    reset_costs()

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

            cost_history = meta.get("cost_history", [])

            # 1. Background removal
            if body.remove_background:
                try:
                    current_bytes = remove_background(current_bytes)
                    changed = True
                    from backend.services.post_processor import _find_model_key_by_purpose
                    bg_key = _find_model_key_by_purpose("remove_background")
                    bg_price = _get_model_price(bg_key) if bg_key else 0
                    cost_history.append({"action": "remove_background", "model": bg_key or "", "cost_usd": bg_price})
                    logger.info("BG removed for %s (%d/%d)", asset_id, idx + 1, total)
                except Exception as exc:
                    logger.warning("BG removal failed for %s: %s", asset_id, exc)

            # 2. Upscale (with throttle delay) — skip if already upscaled
            if body.upscale:
                if meta.get("upscaled"):
                    logger.info("Skipping upscale for %s — already upscaled", asset_id)
                else:
                    if idx > 0:
                        time.sleep(1)  # Throttle between upscale calls
                    try:
                        prompt = meta.get("refined_prompt", meta.get("prompt", ""))
                        current_bytes = upscale_image(current_bytes, prompt)
                        changed = True
                        meta["upscaled"] = True
                        from backend.services.post_processor import _find_model_key_by_purpose
                        up_key = _find_model_key_by_purpose("upscale_creative")
                        up_price = _get_model_price(up_key) if up_key else 0
                        cost_history.append({"action": "upscale", "model": up_key or "", "cost_usd": up_price})
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
            meta["cost_history"] = cost_history
            meta["estimated_total_cost_usd"] = round(sum(c.get("cost_usd", 0) for c in cost_history), 6)
            if svg_url:
                meta["svg_path"] = svg_url
            store.save_generation_metadata(asset_id, meta)

            results.append({"id": asset_id, "svg_url": svg_url})
        except Exception as exc:
            logger.exception("Post-processing failed for %s", asset_id)
            errors.append(f"{asset_id}: {exc}")

    # Track post-processing cost
    pp_cost = get_total_cost()
    if pp_cost > 0:
        actions = []
        if body.remove_background:
            actions.append("remove_background")
        if body.upscale:
            actions.append("upscale")
        track_post_process(action="+".join(actions), cost_usd=pp_cost)

    return {"processed": results, "errors": errors}
