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
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from backend.models.generation_request import AssetType, GenerationRequest, ImageModel
from backend.models.generation_result import GenerationResult, OptionResult, VariantResult
from backend.models.style_profile import StyleProfile
from backend.services.image_generator import generate_image, is_moderation_error
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


def _derive_seed(base: int | None, option_index: int, variant_index: int, n_vars: int) -> int:
    """Per-image seed for one (option, variation) slot.

    With a user base seed, every slot gets a deterministic, distinct offset
    (wrapped into the valid range) — so the same base + same settings reproduce
    the same batch, and in an all-models run the same (concept, variation) slot
    shares its seed across models, keeping outputs comparable. No base = the
    legacy behavior: an independent random seed per image."""
    if base is None:
        return random.randint(0, _SEED_MAX)
    return (int(base) + option_index * max(1, n_vars) + variant_index) % (_SEED_MAX + 1)


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


def _get_positive_magic(model_key) -> str:
    """The model-specific 'positive magic' suffix (e.g. ', Ultra HD, 4K, …') that
    a custom SageMaker handler appends to the prompt at inference time. It's added
    remotely and never returned, so we resolve + record it here so the metadata
    can show the FULL text the model actually saw (enhanced_prompt + this suffix)."""
    key = model_key.value if hasattr(model_key, 'value') else str(model_key)
    try:
        from backend.services.model_registry import get_image_model
        cfg = get_image_model(key)
        return (cfg.get("invoke", {}) or {}).get("positive_magic", "") if cfg else ""
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


def _consolidate_decomposed(decomposed_data: dict | None) -> str:
    """Flatten Prompt-Designer decomposed fields into one plain-text string.

    This is the DETERMINISTIC Step-2 consolidation (no LLM): it space-joins every
    field value across sections. It is both the text shown in the read-only Step-2
    box AND the value stored as the "source" of the Step-3 enhanced prompt. Returns
    "" when there's no decomposed data (e.g. a plain type-and-Generate that never
    used the Designer)."""
    if not decomposed_data or not isinstance(decomposed_data, dict):
        return ""
    parts = []
    for section in decomposed_data.values():
        if isinstance(section, dict):
            for field in section.values():
                if isinstance(field, dict) and field.get("value"):
                    parts.append(str(field["value"]).strip())
                elif isinstance(field, str) and field.strip():
                    parts.append(field.strip())
    return " ".join(parts)


def _resolve_model_size(model_key: str, width: int, height: int) -> tuple[int, int]:
    """Resolve the best supported size for a model.

    If the model declares supported_sizes in its registry config, returns the
    best match — prioritizing ASPECT RATIO, then MAXIMUM resolution within that
    aspect. Otherwise returns the requested size as-is.

    Two principles:
      1. Aspect ratio must win: a 16:9 request (1920x1080) snapped to a square
         1328x1328 (closer by raw area) distorts the composition. Match aspect
         first (→ 1664x928) to preserve the intended framing.
      2. No compromise on quality: among sizes sharing the closest aspect, pick
         the HIGHEST resolution the model supports (never downscale to a smaller
         supported size just because it's numerically nearer the request). The
         model's supported sizes are all quality-validated, so bigger = better.
    """
    from backend.services.model_registry import get_image_model
    cfg = get_image_model(model_key) if model_key else None
    if not cfg:
        return width, height
    sizes = cfg.get("invoke", {}).get("supported_sizes", [])
    if not sizes:
        return width, height
    if width <= 0 or height <= 0:
        return width, height
    req_aspect = width / height
    # Rank by (aspect distance ASC, then area DESC) — closest aspect, then the
    # largest resolution in that aspect. log-ratio gives a symmetric aspect
    # distance (portrait and landscape treated evenly).
    import math
    def _score(s):
        aspect_dist = round(abs(math.log((s["w"] / s["h"]) / req_aspect)), 3)
        return (aspect_dist, -(s["w"] * s["h"]))  # negative area → prefer largest
    best = min(sizes, key=_score)
    if best["w"] == width and best["h"] == height:
        return width, height
    logger.info("Size %dx%d not directly supported by %s — using best (aspect-first, max-res): %dx%d",
                width, height, model_key, best["w"], best["h"])
    return best["w"], best["h"]


def _generate_single_image(
    *,
    asset_id: str,
    enhanced_prompt: str,
    body: GenerationRequest,
    seed: int,
    negative_prompt: str = "",
    model_override: ImageModel | None = None,
    option_index: int = 0,
    status_callback=None,
) -> tuple[bytes | dict, str | None]:
    effective_model = model_override or body.image_model
    # Resolve closest supported size for this model (safety net — frontend should warn first)
    model_key_str = effective_model.value if hasattr(effective_model, 'value') else str(effective_model)
    gen_w, gen_h = _resolve_model_size(model_key_str, body.width, body.height)

    # Reference-guided pixel conditioning:
    #   "match" — forward the decoded reference image(s) to the edit model
    #             (e.g. Qwen-Image-Edit).
    #   "remix" — forward the FIRST reference to a Bedrock image-to-image model
    #             with the option's strength (the strength ladder: options share
    #             one prompt, each runs at its own strength).
    #   "inspired" carries no images here — its guidance is already baked into
    #   enhanced_prompt upstream, so it generates as a normal text-to-image.
    ref_bytes = None
    extra_params = None
    if body.reference_images and body.reference_mode in ("match", "remix"):
        import base64 as _b64
        limit = 1 if body.reference_mode == "remix" else 3
        ref_bytes = []
        for ref in body.reference_images[:limit]:
            try:
                ref_bytes.append(_b64.b64decode(ref))
            except Exception:
                pass
        ref_bytes = ref_bytes or None
        if body.reference_mode == "remix" and ref_bytes:
            strengths = body.reference_strengths or [0.5]
            strength = strengths[min(option_index, len(strengths) - 1)]
            extra_params = {"mode": "image-to-image", "strength": strength}

    result = generate_image(
        enhanced_prompt=enhanced_prompt,
        model=effective_model,
        width=gen_w,
        height=gen_h,
        seed=seed,
        negative_prompt=negative_prompt,
        quality=body.quality,
        region_override=body.region,
        reference_images=ref_bytes,
        extra_params=extra_params,
        status_callback=status_callback,
    )

    # Async custom models return a sentinel dict — no image to process yet.
    # The background poller in async_jobs.py will handle gallery storage.
    if isinstance(result, dict) and result.get("async_submitted"):
        return result, None

    image_bytes = result
    svg_output_path = (
        store.generated_asset_dir(asset_id) / "asset.svg"
        if body.generate_svg else None
    )
    final_bytes, svg_path = process_asset(
        image_bytes=image_bytes,
        enhanced_prompt=enhanced_prompt,
        remove_bg=body.remove_background,
        do_upscale=body.upscale,
        do_svg=body.generate_svg,
        svg_output_path=svg_output_path,
    )
    store.save_generated_image(asset_id, "asset.png", final_bytes)
    svg_url = f"/api/gallery/{asset_id}/svg" if svg_path and svg_path.exists() else None
    return final_bytes, svg_url


def _persist_reference_inputs(asset_id: str, body: GenerationRequest,
                              option_index: int = 0) -> dict:
    """For reference-guided ('Image Inspiration') jobs, save the reference image(s)
    into the asset dir and return the metadata needed to fully restore the job on
    Gallery reload. Returns {} for normal text-to-image jobs.

    Images are copied PER-ASSET (self-contained) so a reload always finds them even
    if sibling variants are later deleted. Remix assets also record the strength
    THIS option ran at (the ladder maps one strength per option).
    """
    if not body.reference_images:
        return {}
    import base64 as _b64
    filenames = []
    for i, r in enumerate(body.reference_images[:3], start=1):
        try:
            data = _b64.b64decode(r)
        except Exception:
            continue
        fn = f"reference_{i}.png"
        try:
            store.save_generated_image(asset_id, fn, data)
            filenames.append(fn)
        except Exception as exc:
            logger.warning("Could not persist reference image %s for %s: %s", i, asset_id, exc)
    meta = {
        "reference_guided": True,
        "reference_mode": body.reference_mode or "inspired",
        "reference_prompt": (body.reference_prompt or "").strip(),
        "reference_images": filenames,
    }
    if body.reference_mode == "remix" and body.reference_strengths:
        s = body.reference_strengths
        meta["reference_strength"] = s[min(option_index, len(s) - 1)]
    return meta


def _prepare_reference_generation(body: GenerationRequest, progress_cb=None) -> None:
    """Resolve a reference-guided ("Image Inspiration") job's prompts BEFORE
    pipeline dispatch — shared by the single-model AND all-models paths. It MUST
    run before the all_models dispatch: the multi-model pipeline has no reference
    handling of its own and would silently ignore the images.

      "match"    — the instruction is shaped for the deployed edit model and the
                   reference image(s) are forwarded as pixel conditioning
                   downstream (_generate_single_image). Genuinely single-model /
                   single-concept: forced here regardless of what the UI sent,
                   and the edit model is resolved + validated via the registry
                   (never hardcoded to a specific model).
      "inspired" — a vision LLM turns the reference(s) + instruction into
                   num_options DISTINCT enhanced prompts in ONE call. If the
                   frontend already previewed (and possibly edited) them, those
                   are honored verbatim — no second vision call, no drift from
                   what the user saw. The results are plain text-to-image
                   prompts, so ANY model — and any model fan-out — can render
                   them.

    Mutates body: prompt / negative_prompt / num_options / pre_composed /
    reference_prompt / reference_enhanced_prompts (+ for match: image_model,
    all_models, selected_models). Sets model_optimized_prompts=False for both
    modes — the vision analysis IS the single prompt enhancement for reference
    jobs (no second per-model refine).
    """
    def emit(event):
        if progress_cb:
            progress_cb(event)

    # Preserve the user's raw Step-2 instruction (as typed, pre-translation) so
    # a Gallery reload restores exactly what they wrote.
    body.reference_prompt = body.prompt
    body.model_optimized_prompts = False

    # Translate a non-English instruction first (same as the text flow) so the
    # shaping/vision LLM works from English. The pipelines' own translate steps
    # are skipped for reference jobs — this already covered it.
    try:
        from backend.services.prompt_translator import translate_to_english
        tr = translate_to_english(body.prompt, ui_lang=body.ui_lang)
        if tr["was_translated"]:
            logger.info("Reference instruction translated from %s to English", tr["source_lang"])
            body.prompt = tr["translated"]
    except Exception as exc:
        logger.warning("Reference instruction translation failed, using original: %s", exc)

    if body.reference_mode == "match":
        # Pixel-faithful edit: the reference images go to ONE deployed edit
        # model — a model fan-out or multiple concepts genuinely don't apply.
        body.all_models = False
        body.selected_models = None
        body.num_options = 1
        body.reference_enhanced_prompts = None
        # Resolve + validate the edit model via the registry: honor an explicit
        # chooser pick when it's (still) deployed, else the newest deployed
        # reference-capable instance. Registry-driven — new catalog models with
        # capabilities.reference_guided light up with no code change.
        from backend.services.reference_models import find_reference_model, supported_reference_models
        mk, _cfg = find_reference_model(body.image_model)
        if not mk:
            mk, _cfg = find_reference_model()
        if not mk:
            supported = ", ".join(m["label"] for m in supported_reference_models())
            raise HTTPException(400, detail=(
                "“Match the reference” needs one of these image-editing models deployed: "
                f"{supported or 'a reference-capable edit model'}. "
                "Deploy one under Model Settings → Custom Models."))
        body.image_model = mk

        emit({"type": "stage", "stage": "prompts",
              "message": "Preparing reference-matched generation..."})
        # Shape the raw instruction into an optimal edit instruction for the
        # edit model (registry-driven prompt tuning, same idea as refine_prompt
        # for generators). Best-effort — falls back to the raw prompt on error.
        try:
            from backend.services.bedrock_client import invoke_llm
            from backend.services.prompt_templates import get_template, get_system_prompt
            from backend.services.prompt_engineer import get_model_guidance, get_prompt_limit
            _guidance = get_model_guidance(body.image_model)
            _tmpl = get_template("reference_edit_instruction").format(
                user_prompt=body.prompt[:1500],
                model_name=body.image_model or "the edit model",
                model_specific_instructions=_guidance or "(no model-specific guidance)",
                max_chars=get_prompt_limit(body.image_model),
            )
            _shaped = invoke_llm(
                _tmpl, system=get_system_prompt("reference_edit_instruction"),
                complexity="fast", max_tokens=400, temperature=0.3,
            ).strip()
            if _shaped:
                body.prompt = _shaped
        except Exception as exc:
            logger.warning("Edit-instruction shaping failed, using raw prompt: %s", exc)
        body.pre_composed = True
        logger.info("Reference-guided generation: mode=match, %d reference image(s), "
                    "model=%s, %d variation(s)",
                    len(body.reference_images), body.image_model, body.num_variations)
        return

    if body.reference_mode == "remix":
        # Classic strength-based img2img: the reference PIXELS go straight to a
        # Bedrock image-to-image model — no vision analysis, no deploy. Keeps
        # composition/palette (not identity); the strength ladder maps one
        # strength per option (same prompt across all of them).
        body.all_models = False
        body.selected_models = None
        # Resolve + validate the model via the registry capability flag —
        # honor the chooser pick when capable, else the first capable enabled
        # model. Never hardcoded; a new capable model lights up automatically.
        from backend.services.model_registry import get_enabled_image_models
        capable = {k: c for k, c in get_enabled_image_models().items()
                   if (c.get("capabilities") or {}).get("image_to_image")
                   and c.get("model_source") != "custom_hosted"}
        if not capable:
            raise HTTPException(400, detail=(
                "“Remix the reference” needs an image-to-image capable model "
                "(e.g. Stable Diffusion 3.5 Large) enabled in the registry."))
        if body.image_model not in capable:
            body.image_model = next(iter(capable))
        # Strength ladder: what the UI showed is exactly what runs (clamped).
        strengths = [max(0.05, min(0.95, float(s)))
                     for s in (body.reference_strengths or []) if s is not None]
        if not strengths:
            strengths = [0.5]
        strengths = strengths[:5]
        body.reference_strengths = strengths
        body.num_options = len(strengths)

        emit({"type": "stage", "stage": "prompts",
              "message": "Preparing reference remix..."})
        # ONE standard enhancement pass (same refine as a plain generation —
        # style- and model-aware); the pixels carry the reference, so a refusal
        # or failure safely falls back to the raw instruction.
        try:
            style_profile = None
            if body.style_id:
                _sdata = store.load_style_profile(body.style_id)
                if _sdata:
                    style_profile = StyleProfile(**_sdata)
            enhanced = refine_prompt(body.prompt, style_profile, body.asset_type,
                                     image_model=body.image_model)
            if enhanced:
                body.prompt = enhanced
        except Exception as exc:
            logger.warning("Remix prompt refinement failed, using raw instruction: %s", exc)
        # Same prompt for every option — options differ by STRENGTH, not concept.
        body.reference_enhanced_prompts = [body.prompt] * len(strengths)
        body.pre_composed = True
        logger.info("Reference-guided generation: mode=remix, model=%s, strengths=%s, "
                    "%d variation(s)", body.image_model, strengths, body.num_variations)
        return

    # ── "inspired" ──────────────────────────────────────────────────────────
    n_opts = max(1, min(5, body.num_options or 1))
    analyzed_live = False
    # Previewed (and possibly edited) prompts from the frontend win — the user
    # saw and approved these exact texts.
    concepts = [(p or "").strip()[:1500]
                for p in (body.reference_enhanced_prompts or []) if (p or "").strip()]
    concepts = concepts[:n_opts]
    if concepts:
        emit({"type": "stage", "stage": "prompts",
              "message": "Using your previewed reference prompt(s)..."})
    else:
        emit({"type": "stage", "stage": "prompts",
              "message": "Analyzing your reference image(s)..."})
        try:
            from backend.services.reference_analyzer import analyze_reference_images
            import base64 as _b64
            ref_imgs = []
            for r in body.reference_images[:3]:
                try:
                    ref_imgs.append(_b64.b64decode(r))
                except Exception:
                    pass
            analysis = analyze_reference_images(
                ref_imgs, body.prompt, asset_type=body.asset_type.value,
                num_options=n_opts,
            )
        except Exception as exc:
            logger.warning("Reference analysis failed, using raw prompt: %s", exc)
            analysis = None
        if analysis and analysis.get("analyzed"):
            analyzed_live = True
            concepts = analysis.get("enhanced_prompts") or [analysis["enhanced_prompt"]]
            if analysis.get("negative_prompt") and not body.negative_prompt:
                body.negative_prompt = analysis["negative_prompt"]

    if concepts:
        body.reference_enhanced_prompts = concepts
        body.num_options = len(concepts)
        body.prompt = concepts[0]
    else:
        # Analysis unavailable → generate directly from the raw instruction,
        # as a single concept (variations still vary by seed).
        body.reference_enhanced_prompts = None
        body.num_options = 1
    body.pre_composed = True
    logger.info(
        "Reference-guided generation: mode=inspired, %d reference image(s), "
        "%d option(s) × %d variation(s)%s%s",
        len(body.reference_images), body.num_options, body.num_variations,
        (" (vision-analyzed)" if analyzed_live else ""),
        (" (user-previewed prompts)" if (concepts and not analyzed_live) else ""),
    )


def _build_variant(
    *,
    batch_id: str,
    option_index: int,
    variant_index: int,
    enhanced_prompt: str,
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

    gen_result, svg_url = _generate_single_image(
        asset_id=asset_id,
        enhanced_prompt=enhanced_prompt,
        body=body,
        seed=seed,
        negative_prompt=negative_prompt,
        model_override=model_override,
        option_index=option_index,
        status_callback=_status_cb,
    )

    # Async custom models return a sentinel — image will arrive later via background poller
    if isinstance(gen_result, dict) and gen_result.get("async_submitted"):
        # Save FULL metadata now (identical to sync jobs) — image arrives later
        effective_model = model_override or body.image_model
        _ref_meta = _persist_reference_inputs(asset_id, body, option_index)
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
            "enhanced_prompt": enhanced_prompt,
            "negative_prompt": negative_prompt,
            # The positive-magic suffix the handler appends at inference (recorded
            # so the display can show the full text the model actually saw).
            "positive_magic": _get_positive_magic(effective_model),
            # Step-2 provenance — always present but EMPTY (falsy) when the Prompt
            # Designer wasn't used, so it never contaminates downstream prompt
            # enhancement (all consumers use `... or ...`). The post-generation
            # patch overwrites with the real consolidation when the Designer WAS
            # used. "Not used" wording is a display-only concern (frontend).
            "recomposed_prompt": "",
            "decomposed_data": None,
            "style_id": body.style_id,
            "style_snapshot": style_snapshot,
            "asset_type": body.asset_type.value,
            "image_model": effective_model.value if hasattr(effective_model, 'value') else str(effective_model),
            "model_label": model_label or "",
            "quality": body.quality or "",
            "region": body.region or _get_model_region(effective_model),
            "width": body.width,
            "height": body.height,
            "seed": seed,
            "remove_background": body.remove_background,
            "generate_svg": body.generate_svg,
            "upscale": body.upscale,
            "ip_owned": body.ip_owned,
            "ip_licensed": body.ip_licensed,
            "png_path": f"/api/gallery/{asset_id}/png",
            "created_at": datetime.utcnow().isoformat(),
            "async_status": "pending",
            "async_job_id": gen_result.get("job_id"),
            **_ref_meta,
        })

        # Update the async job with the asset_id so the poller knows where to save
        try:
            from backend.services.async_jobs import update_job_asset_id
            update_job_asset_id(gen_result["job_id"], asset_id, body.generate_svg, body.remove_background, body.upscale)
        except Exception as e:
            logger.error("Failed to update async job asset_id for %s: %s", gen_result["job_id"], e)

        return VariantResult(
            id=asset_id,
            variant_index=variant_index,
            png_path="",
            svg_path=None,
            seed=seed,
            prompt_used=enhanced_prompt,
            model_used=str(model_override or body.image_model),
            model_label=model_label or "",
            async_job=gen_result,
        )

    final_bytes = gen_result

    # Check after generation but before saving (another task may have triggered cancel)
    if cancel_event and cancel_event.is_set():
        raise RuntimeError("Batch cancelled due to content moderation block")

    png_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.png"
    svg_filename = f"{prompt_slug}_opt{option_index + 1}_var{variant_index + 1}.svg" if svg_url else None

    effective_model = model_override or body.image_model
    _ref_meta = _persist_reference_inputs(asset_id, body, option_index)
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
        "enhanced_prompt": enhanced_prompt,
        "negative_prompt": negative_prompt,
        # The positive-magic suffix the handler appends at inference (recorded so
        # the display can show the full text the model actually saw).
        "positive_magic": _get_positive_magic(effective_model),
        # Step-2 provenance — always present for a consistent metadata shape, but
        # EMPTY (falsy) when the Prompt Designer wasn't used. Must stay empty (not
        # a sentinel string): the frontend echoes recomposed_prompt back into the
        # Generate payload and downstream code does `recomposed_prompt or prompt`
        # / `... or meta.get("recomposed_prompt") or ...` — a non-empty sentinel
        # would contaminate prompt enhancement. The "not used" wording is a
        # DISPLAY-ONLY concern, applied in the frontend. The post-generation patch
        # overwrites these with the real consolidation when the Designer was used.
        "recomposed_prompt": "",
        "decomposed_data": None,
        "style_id": body.style_id,
        "style_snapshot": style_snapshot,
        "asset_type": body.asset_type.value,
        "image_model": effective_model.value if hasattr(effective_model, 'value') else str(effective_model),
        "model_label": model_label or "",
        "quality": body.quality or "",
        "region": body.region or _get_model_region(effective_model),
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
        **_ref_meta,
    })

    result = VariantResult(
        id=asset_id,
        variant_index=variant_index,
        png_path=f"/api/gallery/{asset_id}/png",
        svg_path=svg_url,
        png_filename=png_filename,
        svg_filename=svg_filename,
        seed=seed,
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

    # Forward LLM retry/fallback status events (from bedrock_client, deep in the
    # prompt pipeline) to the SSE stream so the UI can show "AI not responding,
    # retrying / switching to backup". Runs in this worker thread, where the
    # synchronous invoke_llm calls happen. Fresh thread per streaming request
    # (per-request ThreadPoolExecutor), so no cross-request leakage.
    if progress_cb:
        from backend.services.bedrock_client import set_llm_notifier
        set_llm_notifier(progress_cb)

    # Reference-guided ("Image Inspiration"): resolve the prompts BEFORE dispatch
    # so BOTH pipelines (single-model and all-models) run from the same concepts.
    # For "match" this also forces single-model (and may clear all_models).
    if body.reference_images:
        _prepare_reference_generation(body, progress_cb)

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

    # Translate non-English prompts to English before refinement. Reference jobs
    # skip this — _prepare_reference_generation already translated the raw
    # instruction, and body.prompt now holds the (English) enhanced prompt.
    translation_result = None
    if not body.reference_images:
        try:
            from backend.services.prompt_translator import translate_to_english
            translation_result = translate_to_english(body.prompt, ui_lang=body.ui_lang)
            if translation_result["was_translated"]:
                logger.info("Prompt translated from %s to English: '%s' → '%s'",
                            translation_result["source_lang"],
                            body.prompt[:50], translation_result["translated"][:50])
                body.prompt = translation_result["translated"]
        except Exception as exc:
            logger.warning("Prompt translation failed, using original: %s", exc)

    # Use decomposed/recomposed data from frontend if provided (Prompt Designer flow).
    # Otherwise the backend will decompose independently (direct Generate flow).
    decomposed_data = body.decomposed_data or {}
    recomposed_prompt = body.recomposed_prompt or None

    # A reloaded batch's stored per-option final prompts for THIS model — reused
    # verbatim (no concept LLM) so an unchanged re-run reproduces the batch.
    _saved_concepts = None
    if body.saved_concept_prompts and not body.reference_enhanced_prompts:
        _cand = body.saved_concept_prompts.get(str(body.image_model)) or []
        if len(_cand) >= n_opts:
            _saved_concepts = [str(p) for p in _cand[:n_opts]]

    # Generate concept prompts (skip if pre-composed by the user)
    if body.reference_enhanced_prompts:
        # Reference-guided ("inspired"): the vision-derived (or user-previewed/
        # edited) prompts ARE the option concepts — one per option, already the
        # single enhancement pass. No further refinement.
        concept_prompts = list(body.reference_enhanced_prompts)
        emit({"type": "stage", "stage": "prompts",
              "message": "Using your reference-enhanced prompt(s)..."})
        logger.info("Using %d reference-enhanced concept(s) for batch %s (skipping refinement).",
                    len(concept_prompts), batch_id)
    elif _saved_concepts:
        # Unchanged re-run of a reloaded batch: its recorded final prompts ARE
        # the option concepts — reused verbatim for an exact repeat.
        concept_prompts = _saved_concepts
        emit({"type": "stage", "stage": "prompts",
              "message": "Reusing this batch's saved prompts..."})
        logger.info("Reusing %d saved concept prompt(s) for batch %s (skipping refinement).",
                    len(concept_prompts), batch_id)
    elif body.pre_composed and n_opts == 1:
        # User already composed the prompt via "Compose Generation Prompt" — use as-is
        recomposed_prompt = recomposed_prompt or body.prompt
        concept_prompts = [body.prompt]
        emit({"type": "stage", "stage": "prompts",
              "message": "Using your composed prompt..."})
        logger.info("Using pre-composed prompt for batch %s (skipping refinement).", batch_id)
    else:
        emit({"type": "stage", "stage": "prompts",
              "message": f"Creating {n_opts} concept prompt{'s' if n_opts > 1 else ''}..."})

    if ((not body.pre_composed or n_opts > 1)
            and not body.reference_enhanced_prompts and not _saved_concepts):
        model_id = body.image_model
        try:
            if body.asset_type == AssetType.MARKETING_BANNER and n_opts == 1:
                concept_prompts = [refine_marketing_prompt(body.prompt, style_profile, image_model=model_id)]
            elif n_opts == 1:
                # Single option: ONE enhancement pass produces the Step-3 prompt
                # that goes to the model. We deliberately do NOT force
                # decompose→recompose here — decomposition is offered only via the
                # optional Prompt Designer, and when the user uses it the frontend
                # sends a pre-composed prompt (handled by the branch above). A
                # plain "type and Generate" gets a single refine, no imposed
                # decomposition and no redundant second enhancement. If the
                # frontend did supply a recomposed prompt, enhance that; else the
                # raw prompt. (refine_prompt sets the negative-prompt contextvar.)
                enhanced = refine_prompt(
                    recomposed_prompt or body.prompt, style_profile, body.asset_type, image_model=model_id,
                )
                concept_prompts = [enhanced]
            else:
                # Multiple options: generate N distinct concepts in a single pass.
                # Uses decomposed_data for lock/vary variety WHEN the user supplied
                # it via the Designer; otherwise works from the raw prompt directly
                # (generate_concept_prompts has its own default vary logic). No
                # forced decomposition either way.
                concept_prompts = generate_concept_prompts(
                    body.prompt, style_profile, body.asset_type, n_opts, image_model=model_id,
                    decomposed_data=decomposed_data,
                    vary_fields=body.vary_fields,
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

    # Step-2 consolidation: flat plain-text join of the decomposed fields (the
    # "source" of the Step-3 enhanced prompt), distinct from the LLM-enhanced
    # Step-3 text. Empty for a plain type-and-Generate (no Designer used); falls
    # back to any frontend-supplied recomposed_prompt.
    display_recomposed = _consolidate_decomposed(decomposed_data) or (recomposed_prompt or "")

    emit({"type": "prompts_ready",
          "prompts": concept_prompts,
          "recomposed_prompt": display_recomposed,
          "negative_prompt": negative_prompt or "",
          "pre_composed": body.pre_composed,
          "decomposed": decomposed_data or {}})

    emit({"type": "stage", "stage": "generating",
          "message": f"Generating {total} images...", "prompts_done": len(concept_prompts)})

    prompt_slug = _slugify_prompt(body.prompt)
    progress_q = queue.Queue()
    cancel_event = threading.Event()
    variant_map: dict[int, list[VariantResult]] = {i: [] for i in range(n_opts)}
    errors: list[str] = []
    completed = 0

    # ── Canary request: test first concept prompt before dispatching batch ──
    canary_seed = _derive_seed(body.seed, 0, 0, n_vars)
    emit({"type": "stage", "stage": "canary",
          "message": "Testing prompt with image model..."})
    try:
        _canary_result = _build_variant(
            batch_id=batch_id,
            option_index=0,
            variant_index=0,
            enhanced_prompt=concept_prompts[0],
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
        is_moderation = is_moderation_error(canary_exc)
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
        # User base seed → deterministic per-slot seeds; else random per option.
        seeds = ([_derive_seed(body.seed, oi, vi, n_vars) for vi in range(n_vars)]
                 if body.seed is not None
                 else random.sample(range(0, _SEED_MAX), n_vars))
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
                    enhanced_prompt=prompt,
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
                    variant = future.result()
                    variant_map[oi].append(variant)
                    completed += 1
                    # Notify frontend about async jobs (submitted, not completed yet)
                    if hasattr(variant, 'async_job') and variant.async_job:
                        emit({"type": "async_submitted", "option": oi, "variation": vi,
                              "completed": completed, "total": total,
                              "job_id": variant.async_job.get("job_id", ""),
                              "model_label": variant.async_job.get("model_label", "")})
                    else:
                        while not progress_q.empty():
                            evt = progress_q.get_nowait()
                            evt["completed"] = completed
                            evt["total"] = total
                            emit(evt)
                except Exception as exc:
                    completed += 1
                    exc_str = str(exc).lower()
                    # Moderation block OR a batch-cancel signal (cancelled) both
                    # count here — a sibling task's moderation block cancels the rest.
                    is_moderation = is_moderation_error(exc) or "cancelled" in exc_str
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
                enhanced_prompt=concept_prompts[oi],
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

    # Persist the Step-2 recomposed prompt + decomposed data to all variant
    # metadata so they're available when loading from Gallery later. We store
    # `display_recomposed` (the flat consolidation of the decomposed fields) —
    # the SAME text shown in the Step-2 box — so the stored "source" of the
    # Step-3 enhanced prompt matches exactly what the user saw. Only meaningful
    # when the user used the Prompt Designer; a plain type-and-Generate leaves
    # it empty (no imposed decomposition).
    if display_recomposed or decomposed_data:
        for opt in options:
            for v in opt.variants:
                try:
                    meta_path = store.generated_asset_dir(v.id) / "metadata.json"
                    if meta_path.exists():
                        meta = json.loads(meta_path.read_text())
                        if display_recomposed:
                            meta["recomposed_prompt"] = display_recomposed
                        if decomposed_data:
                            meta["decomposed_data"] = decomposed_data
                        meta_path.write_text(json.dumps(meta, indent=2))
                except Exception:
                    pass  # Non-fatal

    # Send accurate cost to telemetry
    from backend.services.telemetry import track_image_cost
    track_image_cost(cost_usd=actual_cost, model=body.image_model,
                     breakdown=json.dumps(cost_breakdown, default=str))

    emit({"type": "complete", "result": result.model_dump(mode="json")})
    return result


# ── All Models generation ─────────────────────────────────────────────────

def _run_all_models_generation(body: GenerationRequest, progress_cb=None):
    """Generate with every enabled image model — supports multiple options and variations per model.

    Each model runs independently: moderation blocks on one model don't
    cancel others. Per-model/option status is reported in real-time via SSE.

    With N models × O options × V variations, the result has N*O OptionResults,
    each with V VariantResults. Options are flattened: option_index maps to
    (model, concept_index) via model_map. Frontend groups by model for display.
    """
    from backend.services.model_registry import (
        get_enabled_image_model_keys_sorted,
        get_image_model_label,
        get_image_model,
    )
    from backend.services.prompt_engineer import (
        generate_concept_prompts,
        get_prompt_limit as _get_limit,
    )

    def emit(event):
        if progress_cb:
            progress_cb(event)

    batch_id = str(uuid4())
    all_keys = get_enabled_image_model_keys_sorted()
    if body.selected_models:
        model_keys = [k for k in all_keys if k in body.selected_models]
    else:
        model_keys = all_keys

    # Sort: custom-hosted (async) first so their SageMaker submissions
    # happen immediately, triggering scale-out while Bedrock models run.
    model_keys.sort(key=lambda k: 0 if get_image_model(k).get("model_source") == "custom_hosted" else 1)

    n_models = len(model_keys)

    if n_models == 0:
        raise HTTPException(400, detail="No image models are enabled.")

    n_opts = body.num_options      # user-selected (1-5)
    n_vars = body.num_variations   # user-selected (1-5)
    total_flat_options = n_models * n_opts
    total_images = total_flat_options * n_vars

    model_labels = {k: get_image_model_label(k) for k in model_keys}

    emit({"type": "started", "batch_id": batch_id, "total": total_images,
          "num_options": total_flat_options, "num_variations": n_vars,
          "all_models": True, "model_labels": model_labels,
          "models_count": n_models, "options_per_model": n_opts})

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

    # Translate non-English prompts to English. Reference jobs skip this —
    # _prepare_reference_generation already translated the raw instruction and
    # body.prompt now holds the (English) enhanced prompt.
    translation_result = None
    if not body.reference_images:
        try:
            from backend.services.prompt_translator import translate_to_english
            translation_result = translate_to_english(body.prompt, ui_lang=body.ui_lang)
            if translation_result["was_translated"]:
                logger.info("All-models: translated %s → English: '%s'",
                            translation_result["source_lang"], translation_result["translated"][:50])
                body.prompt = translation_result["translated"]
        except Exception as exc:
            logger.warning("Prompt translation failed in all-models, using original: %s", exc)

    # ── Generate concept prompts ──────────────────────────────────────
    # concept_prompts: model_key → list of n_opts prompts
    # negative_prompts: model_key → list of n_opts negatives
    emit({"type": "stage", "stage": "prompts",
          "message": f"Creating {n_opts} concept{'s' if n_opts > 1 else ''} for {n_models} models..."})

    concept_prompts: dict[str, list[str]] = {}
    negative_prompts: dict[str, list[str]] = {}

    # Step-2 provenance: use ONLY frontend-provided Designer data (the user opted
    # into decomposition). We do NOT force-decompose here — a plain "type and
    # Generate" across all models gets a single refine per model, same as the
    # single-model path. all_models_decomposed feeds concept variety when present.
    all_models_decomposed = body.decomposed_data or None
    all_models_recomposed = _consolidate_decomposed(all_models_decomposed) or (body.recomposed_prompt or None)

    # A reloaded all-models job: reuse the stored per-model, per-option final
    # prompts verbatim when the set is COMPLETE for every requested model —
    # no concept LLM, so an unchanged re-run reproduces the whole batch.
    _saved_all = None
    if body.saved_concept_prompts and not body.reference_enhanced_prompts:
        if all(len(body.saved_concept_prompts.get(mk) or []) >= n_opts for mk in model_keys):
            _saved_all = {mk: [str(p) for p in body.saved_concept_prompts[mk][:n_opts]]
                          for mk in model_keys}

    try:
        if _saved_all:
            for mk in model_keys:
                concept_prompts[mk] = _saved_all[mk]
                negative_prompts[mk] = [body.negative_prompt or ""] * n_opts
            emit({"type": "stage", "stage": "prompts",
                  "message": "Reusing this batch's saved prompts..."})
            logger.info("Reusing saved concepts for %d model(s) (skipping refinement).",
                        len(model_keys))
        elif body.model_optimized_prompts:
            # Model-optimized: tailored prompts per model
            for mk in model_keys:
                if n_opts == 1:
                    if body.asset_type == AssetType.MARKETING_BANNER:
                        p = refine_marketing_prompt(body.prompt, style_profile, image_model=mk)
                    else:
                        # ONE refine pass — no forced decomposition.
                        p = refine_prompt(body.recomposed_prompt or body.prompt, style_profile, body.asset_type, image_model=mk)
                    concept_prompts[mk] = [p]
                    negative_prompts[mk] = [get_last_negative_prompt()]
                else:
                    # Multiple options — generate N distinct concepts per model
                    prompts = generate_concept_prompts(
                        body.prompt, style_profile, body.asset_type,
                        num_options=n_opts, image_model=mk,
                        decomposed_data=all_models_decomposed,
                        vary_fields=body.vary_fields)
                    concept_prompts[mk] = prompts
                    negative_prompts[mk] = [get_last_negative_prompt()] * n_opts
                logger.info("Model-optimized: %s got %d concept(s)", mk, len(concept_prompts[mk]))
        else:
            # Shared prompts: generate once, truncate per model
            if body.reference_enhanced_prompts:
                # Reference-guided ("inspired"): the vision-derived (or user-
                # previewed/edited) prompts ARE the option concepts, shared by
                # every model — already the single enhancement pass, so no
                # re-refine here (and _prepare_reference_generation forces
                # model_optimized_prompts off for reference jobs).
                shared_prompts = list(body.reference_enhanced_prompts)
                shared_negatives = [body.negative_prompt or ""] * len(shared_prompts)
            elif body.pre_composed:
                shared_prompts = [body.prompt]
                shared_negatives = [body.negative_prompt or ""]
            elif n_opts == 1:
                if body.asset_type == AssetType.MARKETING_BANNER:
                    p = refine_marketing_prompt(body.prompt, style_profile)
                else:
                    # ONE refine pass — no forced decomposition.
                    p = refine_prompt(body.recomposed_prompt or body.prompt, style_profile, body.asset_type)
                shared_prompts = [p]
                shared_negatives = [get_last_negative_prompt() or body.negative_prompt or ""]
            else:
                shared_prompts = generate_concept_prompts(
                    body.prompt, style_profile, body.asset_type, num_options=n_opts,
                    decomposed_data=all_models_decomposed,
                    vary_fields=body.vary_fields)
                shared_negatives = [get_last_negative_prompt()] * n_opts

            # Pad if fewer prompts returned than requested
            while len(shared_prompts) < n_opts:
                shared_prompts.append(shared_prompts[-1])
            while len(shared_negatives) < n_opts:
                shared_negatives.append(shared_negatives[-1] if shared_negatives else "")

            for mk in model_keys:
                limit = _get_limit(mk)
                truncated = []
                for sp in shared_prompts:
                    t = sp
                    if len(t) > limit:
                        t = t[:limit - 4].rsplit(" ", 1)[0]
                    truncated.append(t)
                concept_prompts[mk] = truncated
                negative_prompts[mk] = shared_negatives[:n_opts]
    except PromptRefusalError as refusal:
        logger.warning("Prompt refused in all-models generation: %s", refusal.reason[:200])
        emit({"type": "prompt_refused", "reason": refusal.reason,
              "original_response": refusal.original_response[:500],
              "message": "The AI declined to process this prompt."})
        result = GenerationResult(
            id=batch_id, prompt=body.prompt, original_prompt=body.original_prompt,
            style_id=body.style_id, asset_type=body.asset_type.value,
            image_model="all_models", width=body.width, height=body.height,
            num_options=total_flat_options, num_variations=n_vars,
            all_models=True, options=[],
        )
        emit({"type": "complete", "result": result.model_dump(mode="json"), "prompt_refused": True})
        return result
    except Exception as exc:
        raise HTTPException(502, detail=f"Prompt generation failed: {exc}") from exc

    # Emit prompts (first concept per model for preview)
    emit({"type": "prompts_ready",
          "prompts": [concept_prompts[mk][0] for mk in model_keys],
          "recomposed_prompt": all_models_recomposed or "",
          "negative_prompt": negative_prompts.get(model_keys[0], [""])[0],
          "pre_composed": body.pre_composed,
          "decomposed": all_models_decomposed or {},
          "all_models": True,
          "model_labels": {i: model_labels[mk] for i, mk in enumerate(model_keys)},
          "options_per_model": n_opts})

    # ── Build task list: flatten (model, concept, variation) ──────────
    emit({"type": "stage", "stage": "generating",
          "message": f"Generating {total_images} images across {n_models} models..."})

    prompt_slug = _slugify_prompt(body.prompt)
    model_map: dict[int, str] = {}  # flat_option_index → model_key
    # Track variants per flat option for assembly
    variant_map: dict[int, list] = {}  # flat_option_index → [VariantResult]
    option_meta: dict[int, dict] = {}  # flat_option_index → {prompt, negative, model_key, label}

    # Build the flat task list
    all_tasks = []  # [(flat_option_idx, variant_idx, model_key, prompt, negative)]
    flat_idx = 0
    for mk in model_keys:
        prompts = concept_prompts[mk]
        negatives = negative_prompts[mk]
        for concept_idx in range(n_opts):
            model_map[flat_idx] = mk
            option_meta[flat_idx] = {
                "prompt": prompts[concept_idx],
                "negative": negatives[concept_idx] if concept_idx < len(negatives) else "",
                "model_key": mk,
                "label": model_labels[mk],
                "concept_idx": concept_idx,
            }
            variant_map[flat_idx] = []
            for var_idx in range(n_vars):
                # Derived from (concept, variation) — NOT the flat index — so the
                # same slot shares its seed across models (comparable outputs).
                seed = _derive_seed(body.seed, concept_idx, var_idx, n_vars)
                all_tasks.append((flat_idx, var_idx, mk, prompts[concept_idx],
                                  negatives[concept_idx] if concept_idx < len(negatives) else "",
                                  seed))
            flat_idx += 1

    completed = 0
    total = len(all_tasks)
    max_workers = 3 if body.upscale else min(total, 6)
    progress_q = queue.Queue()

    from backend.services.cost_tracker import share_accumulator_with_thread
    shared_acc = share_accumulator_with_thread()

    def _generate_variant(flat_opt_idx: int, var_idx: int, model_key: str,
                          prompt: str, negative: str, seed: int):
        """Generate one variant. Returns (flat_opt_idx, var_idx, VariantResult_or_Exception)."""
        label = model_labels[model_key]
        try:
            variant = _build_variant(
                batch_id=batch_id,
                option_index=flat_opt_idx,
                variant_index=var_idx,
                enhanced_prompt=prompt,
                negative_prompt=negative,
                body=body,
                seed=seed,
                prompt_slug=prompt_slug,
                model_override=model_key,
                model_label=label,
                style_snapshot=style_snapshot,
                translation_result=translation_result,
                progress_queue=progress_q,
                cost_accumulator=shared_acc,
            )
            return (flat_opt_idx, var_idx, variant, None)
        except Exception as exc:
            return (flat_opt_idx, var_idx, None, exc)

    # ── Execute all tasks in parallel ─────────────────────────────────
    task_status: dict[int, str] = {}  # flat_opt_idx → worst status

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for task in all_tasks:
            future = pool.submit(_generate_variant, *task)
            futures[future] = task[:3]  # (flat_opt_idx, var_idx, model_key)

        for future in as_completed(futures):
            flat_opt_idx, var_idx, mk = futures[future]
            flat_opt_idx, var_idx, variant, exc = future.result()
            completed += 1

            if variant:
                variant_map[flat_opt_idx].append(variant)
                task_status.setdefault(flat_opt_idx, "success")
                # Notify frontend about async jobs (custom models)
                if hasattr(variant, 'async_job') and variant.async_job:
                    emit({"type": "async_submitted",
                          "option": flat_opt_idx, "variation": var_idx,
                          "completed": completed, "total": total,
                          "job_id": variant.async_job.get("job_id", ""),
                          "model_label": variant.async_job.get("model_label", model_labels.get(mk, ""))})
            else:
                is_mod = is_moderation_error(exc)
                status = "moderation_blocked" if is_mod else "error"
                # Worst status wins
                if task_status.get(flat_opt_idx) == "success" or flat_opt_idx not in task_status:
                    task_status[flat_opt_idx] = status
                logger.warning("All-models: %s concept %d var %d failed (%s): %s",
                               model_labels[mk], option_meta[flat_opt_idx]["concept_idx"],
                               var_idx, status, exc)

            # Drain progress events
            while not progress_q.empty():
                evt = progress_q.get_nowait()
                evt["completed"] = completed
                evt["total"] = total
                emit(evt)

            # Emit per-task progress
            meta = option_meta[flat_opt_idx]
            emit({"type": "model_status",
                  "model": mk,
                  "model_label": model_labels[mk],
                  "option_index": flat_opt_idx,
                  "concept_index": meta["concept_idx"],
                  "variant_index": var_idx,
                  "status": "success" if variant else task_status.get(flat_opt_idx, "error"),
                  "status_detail": str(exc) if exc else None,
                  "completed": completed,
                  "total": total})

    # ── Assemble OptionResults ────────────────────────────────────────
    options: list[OptionResult] = []
    for fi in range(flat_idx):
        meta = option_meta[fi]
        variants = sorted(variant_map.get(fi, []), key=lambda v: v.variant_index)
        status = task_status.get(fi, "error" if not variants else "success")
        # If at least one variant succeeded, mark as success
        if variants and status != "success":
            status = "success"
        status_detail = None
        if status != "success":
            status_detail = f"All {n_vars} variation(s) failed for {meta['label']} concept {meta['concept_idx'] + 1}"

        options.append(OptionResult(
            option_index=fi,
            enhanced_prompt=meta["prompt"],
            negative_prompt=meta["negative"],
            image_model=meta["model_key"],
            model_label=meta["label"],
            status=status,
            status_detail=status_detail,
            variants=variants,
        ))

    # Telemetry: one generate event per model (not per task)
    from backend.services.telemetry import track_image_generation, track_first_generation
    track_first_generation(model=model_keys[0] if model_keys else "", asset_type=body.asset_type.value if body.asset_type else "", studio="image")
    for mk in model_keys:
        model_opts = [o for o in options if o.image_model == mk]
        model_variants = sum(len(o.variants) for o in model_opts)
        if model_variants > 0:
            track_image_generation(
                model=mk,
                num_options=n_opts,
                num_variations=n_vars,
                asset_type=body.asset_type.value if body.asset_type else "",
                reference_mode=(body.reference_mode if body.reference_images else ""),
            )

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
        negative_prompt=negative_prompts.get(model_keys[0], [""])[0],
        style_id=body.style_id,
        asset_type=body.asset_type.value,
        image_model="all_models",
        width=body.width,
        height=body.height,
        num_options=total_flat_options,
        num_variations=n_vars,
        all_models=True,
        model_map=model_map,
        options=options,
        total_cost_usd=actual_cost,
        cost_breakdown=cost_breakdown,
    )

    # Persist recomposed + decomposed to all variant metadata. Per-asset RMW —
    # under asset_write_lock + atomic write (SPEC §17), never a bare write_text.
    if all_models_recomposed or all_models_decomposed:
        from backend.services.asset_locks import asset_write_lock
        from backend.services.safe_write import atomic_write_text
        for opt in options:
            for v in opt.variants:
                try:
                    with asset_write_lock(v.id):
                        meta_path = store.generated_asset_dir(v.id) / "metadata.json"
                        if meta_path.exists():
                            meta = json.loads(meta_path.read_text())
                            if all_models_recomposed:
                                meta["recomposed_prompt"] = all_models_recomposed
                            if all_models_decomposed:
                                meta["decomposed_data"] = all_models_decomposed
                            atomic_write_text(meta_path, json.dumps(meta, indent=2))
                except Exception:
                    pass

    from backend.services.telemetry import track_image_cost
    track_image_cost(cost_usd=actual_cost, model="all_models",
                     breakdown=json.dumps(cost_breakdown, default=str))

    # Summary
    succeeded_models = len(set(o.image_model for o in options if o.status == "success"))
    blocked_models = set(o.model_label for o in options if o.status == "moderation_blocked")
    failed_models = set(o.model_label for o in options if o.status == "error")

    summary_parts = []
    if succeeded_models:
        total_images_ok = sum(len(o.variants) for o in options if o.status == "success")
        summary_parts.append(f"{total_images_ok} images from {succeeded_models} models")
    if blocked_models:
        summary_parts.append(f"{len(blocked_models)} blocked ({', '.join(blocked_models)})")
    if failed_models:
        summary_parts.append(f"{len(failed_models)} failed ({', '.join(failed_models)})")

    emit({"type": "complete",
          "result": result.model_dump(mode="json"),
          "all_models_summary": {
              "succeeded": succeeded,
              "blocked": blocked,
              "failed": failed,
              "total_models": n_models,
              "options_per_model": n_opts,
              "variations": n_vars,
              "total_images": sum(len(o.variants) for o in options),
              "summary": "; ".join(summary_parts),
          }})
    return result


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/estimate-cost")
async def estimate_generation_cost(body: GenerationRequest):
    """Return a cost estimate without generating. For pre-generation UI display."""
    from backend.services.model_registry import get_enabled_image_model_keys_sorted, get_image_model

    if body.all_models and body.selected_models:
        all_keys = get_enabled_image_model_keys_sorted()
        model_keys = [k for k in all_keys if k in body.selected_models]
    elif body.all_models:
        model_keys = get_enabled_image_model_keys_sorted()
    else:
        model_keys = [body.image_model] if body.image_model else []

    n_opts = body.num_options
    n_vars = body.num_variations
    images_per_model = n_opts * n_vars

    from backend.services.cost_tracker import resolve_image_price
    image_costs = {}
    for mk in model_keys:
        model = get_image_model(mk)
        mk_str = mk.value if hasattr(mk, "value") else str(mk)
        region = body.region or model.get("region", "")
        # Registry-sourced, region + quality aware (same resolver as the cost path);
        # registry base_price_usd as fallback; None → "pricing unavailable" (no guess).
        price = resolve_image_price(model, mk_str, region, body.quality or "")
        if price is None:
            price = model.get("base_price_usd")
        subtotal = round((price or 0) * images_per_model, 4)
        image_costs[mk] = {
            "label": model.get("label", mk),
            "price_per_image": round(price, 4) if price is not None else None,
            "count": images_per_model,
            "subtotal": subtotal,
            "price_available": price is not None,
        }

    # LLM cost estimate: ~$0.005 per refinement call
    if body.model_optimized_prompts and body.all_models:
        llm_calls = len(model_keys) * max(1, n_opts)
    else:
        llm_calls = max(1, n_opts)
    llm_estimate = llm_calls * 0.005

    total_images = len(model_keys) * images_per_model
    total = sum(c["subtotal"] for c in image_costs.values()) + llm_estimate

    return {
        "total_estimate_usd": round(total, 4),
        "total_images": total_images,
        "models_count": len(model_keys),
        "options_per_model": n_opts,
        "variations": n_vars,
        "image_costs": image_costs,
        "llm_estimate_usd": round(llm_estimate, 4),
    }


# ── Reference-guided generation (Reference-guided tab) ────────────────────

@router.get("/reference-available")
async def reference_generation_available():
    """Is a reference-capable edit model (e.g. Qwen-Image-Edit) deployed?

    Used by the frontend to gate the "Match the reference" mode. When
    unavailable, `deploy_catalog_key` tells the UI which catalog model to route
    the user to in the Custom Models deploy flow (mirrors the 3D gating pattern).
    "Inspired by" mode needs no custom model and is always available.
    """
    from backend.services.reference_models import reference_generation_available as _avail
    return _avail()


class AnalyzeReferenceRequest(BaseModel):
    """Preview the 'Inspired by' enhanced prompt(s) derived from reference images."""
    images: list[str]  # 1–3 base64-encoded PNGs
    prompt: str        # mandatory user instruction — what to do with the reference
    asset_type: str = "photorealistic"
    ui_lang: str = ""  # frontend language — soft hint for prompt translation
    # One DISTINCT interpretation per generation option (mirrors the sidebar's
    # Options setting) — the preview shows exactly what each option will render.
    num_options: int = Field(default=1, ge=1, le=5)


@router.post("/analyze-reference")
async def analyze_reference(body: AnalyzeReferenceRequest):
    """Vision-analyze reference image(s) + the user's instruction → enhanced prompt.

    Powers the 'Inspired by the reference' preview so the user can see (and the
    tab can show) the prompt the model will actually receive. Requires a prompt.
    """
    import base64 as _b64
    from backend.services.reference_analyzer import analyze_reference_images
    from backend.services.cost_tracker import reset_costs, get_total_cost

    if not body.prompt or not body.prompt.strip():
        raise HTTPException(400, detail="A prompt describing what to do with the reference is required.")
    if not body.images:
        raise HTTPException(400, detail="At least one reference image is required.")

    reset_costs()

    # Translate a non-English instruction to English BEFORE vision analysis, so the
    # preview matches what real generation produces (which translates in
    # _run_generation). Same path as the main Prompt→Image flow.
    prompt = body.prompt
    try:
        from backend.services.prompt_translator import translate_to_english
        tr = translate_to_english(prompt, ui_lang=body.ui_lang)
        if tr["was_translated"]:
            prompt = tr["translated"]
    except Exception:
        pass

    imgs = []
    for r in body.images[:3]:
        try:
            imgs.append(_b64.b64decode(r))
        except Exception:
            raise HTTPException(400, detail="Invalid base64 image data.")

    result = analyze_reference_images(imgs, prompt, asset_type=body.asset_type,
                                      num_options=body.num_options)
    _cost = round(get_total_cost(), 6)
    result["cost_usd"] = _cost
    # Report to PulseBoard — this standalone vision-LLM call was previously untracked.
    from backend.services.telemetry import track_aux_llm_cost
    track_aux_llm_cost("analyze_reference", _cost)
    return result


@router.post("/", response_model=GenerationResult)
async def generate_asset(body: GenerationRequest):
    """Synchronous generation endpoint (no streaming progress)."""
    # Same action-event telemetry as /stream (the event lives in the endpoint
    # wrappers, not _run_generation — without this, sync single-model generations
    # emitted a cost event but no image_studio.generate action).
    if not body.all_models:
        from backend.services.telemetry import track_image_generation, track_first_generation
        track_first_generation(model=body.image_model or "", asset_type=body.asset_type.value if body.asset_type else "", studio="image")
        track_image_generation(
            model=body.image_model or "",
            num_options=body.num_options,
            num_variations=body.num_variations,
            asset_type=body.asset_type.value if body.asset_type else "",
            quality=body.quality or "",
            reference_mode=(body.reference_mode if body.reference_images else ""),
        )
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
    # Track telemetry — action event (no cost — cost sent separately via image_studio.cost)
    if not body.all_models:
        from backend.services.telemetry import track_image_generation, track_first_generation
        track_first_generation(model=body.image_model or "", asset_type=body.asset_type.value if body.asset_type else "", studio="image")
        track_image_generation(
            model=body.image_model or "",
            num_options=body.num_options,
            num_variations=body.num_variations,
            asset_type=body.asset_type.value if body.asset_type else "",
            quality=body.quality or "",
            reference_mode=(body.reference_mode if body.reference_images else ""),
        )

    event_queue = queue.Queue()

    def sse_format(data: dict) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    # Check for asset type mismatch (before starting generation)
    asset_suggestion = None
    try:
        from backend.routers.refine import _detect_asset_type_mismatch
        asset_suggestion = _detect_asset_type_mismatch(body.prompt, body.asset_type)
    except Exception:
        pass  # Non-critical — don't block generation

    def generate():
        # Emit asset type suggestion as first event if detected
        if asset_suggestion:
            yield sse_format({"type": "asset_type_suggestion", **asset_suggestion})

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
    # Optional: edit a SPECIFIC version instead of the current one. Used by the
    # 3D source-completion flow to always re-outpaint from the ORIGINAL cropped
    # version (never the already-outpainted result), so the canvas never
    # compounds. Omitted → edits the current version (asset.png), as before.
    source_version: int | None = None
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

    # Breadcrumb ID for this edit request: every lifecycle log line (EDIT-START /
    # EDIT-ASYNC / EDIT-DONE / EDIT-FAIL) carries it, so "did my edit run, and
    # what happened?" is answerable with a single grep of the server log.
    import uuid as _uuid
    edit_trace_id = _uuid.uuid4().hex[:8]

    # Validate model exists and has an editing purpose
    model_config = get_image_model(body.model)
    if not model_config:
        raise HTTPException(404, detail=f"Unknown model: {body.model}")
    purpose = model_config.get("model_purpose", "")
    label = model_config.get("label", body.model)

    # Load source image from gallery. Default = current version (asset.png).
    # When source_version is given, honor the 2D versioning convention: the
    # current version lives as asset.png; older versions are archived as
    # asset_v{N}.png. Try the archived name, then fall back to asset.png.
    source_path = None
    if body.source_version:
        src_meta = store.load_generation_metadata(body.source_image_id) or {}
        cur = src_meta.get("current_version") or (len(src_meta.get("versions", [])) or 1)
        if body.source_version != cur:
            source_path = store.get_generated_file_path(body.source_image_id, f"asset_v{body.source_version}.png")
    if source_path is None:
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

    # Build extra params for outpainting.
    # `_meta` is a RESERVED provenance key (not a model param): callers (e.g. the
    # Character→3D source-completion flow) stash context here to record in the
    # version metadata. Pull it out BEFORE building the model call so it never
    # leaks to the image API.
    extra = dict(body.extra_params or {})
    edit_meta = extra.pop("_meta", None)

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

    # General instruction-driven edit models (e.g. Qwen-Image-Edit, model_purpose
    # "image_edit") are mask-free and don't understand Stability's search_prompt/
    # select_prompt/direction fields. When such a model is used for ANY Edit-tab
    # mode, fold the mode's intent into ONE natural instruction and drop the
    # Stability-only extras so they don't leak as unknown kwargs.
    is_instruction_editor = purpose == "image_edit"
    _outpaint_geometry = None   # set only by the instruction-editor outpaint path
    _pre_pad_source = None
    # The user's words (in English — translation above ran first), captured
    # BEFORE the machine transforms below (search folding, outpaint instruction
    # build). Without this snapshot the version record would store the built
    # instruction as the "user prompt". The pre-translation original is kept
    # separately in edit_original_prompts.
    user_prompt_raw = (body.prompt or "").strip()
    if is_instruction_editor:
        _search = extra.get("search_prompt") or extra.get("select_prompt") or ""
        _instr = (body.prompt or "").strip()
        if _search and _instr:
            body.prompt = f"{_instr} (target: {_search})"
        elif _search and not _instr:
            body.prompt = f"Edit the {_search} in the image as instructed"
        # Outpaint for instruction editors: these models CANNOT grow a canvas —
        # told to "extend the image" they REFRAME (pan/crop) and lose content.
        # Instead: pre-pad the source with noise band(s), instruct the model to
        # complete ONLY the band(s), then restore geometry + blend the original
        # back after the result returns (see instruction_outpaint.py).
        if any(v > 0 for v in (body.outpaint_left, body.outpaint_right,
                               body.outpaint_up, body.outpaint_down)):
            from backend.services.instruction_outpaint import (
                pad_image_for_outpaint, build_outpaint_instruction)
            _pre_pad_source = source_bytes
            source_bytes, _outpaint_geometry = pad_image_for_outpaint(
                source_bytes, left=body.outpaint_left, right=body.outpaint_right,
                up=body.outpaint_up, down=body.outpaint_down)
            body.prompt = build_outpaint_instruction(
                body.prompt, left=body.outpaint_left, right=body.outpaint_right,
                up=body.outpaint_up, down=body.outpaint_down)
        # Strip Stability-only fields; Qwen takes only prompt + reference image(s).
        for _k in ("search_prompt", "select_prompt", "left", "right", "up", "down",
                   "grow_mask", "creativity", "control_strength"):
            extra.pop(_k, None)

    if not is_instruction_editor and purpose == "outpainting":
        if body.outpaint_left > 0:
            extra["left"] = body.outpaint_left
        if body.outpaint_right > 0:
            extra["right"] = body.outpaint_right
        if body.outpaint_up > 0:
            extra["up"] = body.outpaint_up
        if body.outpaint_down > 0:
            extra["down"] = body.outpaint_down
        # Guard up-front: the outpaint API requires at least one non-zero
        # direction. Without this the request reaches Bedrock and comes back as a
        # ValidationException that fell through to a generic 502. Return a clean,
        # actionable 400 instead.
        if not any(k in extra for k in ("left", "right", "up", "down")):
            raise HTTPException(
                400,
                detail="Nothing to extend — set at least one direction (left, right, up or down) to a non-zero amount.",
            )

    # Smart prompt transformation for inpainting:
    # Users often write removal instructions ("Remove X", "Delete X", "Get rid of X")
    # but the Stability Inpaint API expects a GENERATIVE prompt describing what should
    # APPEAR in the masked area. Transform removal prompts into generative descriptions.
    edit_prompt = body.prompt
    if purpose == "inpainting" and edit_prompt:
        import re as _re
        removal_patterns = [
            r"^(?:remove|delete|erase|get rid of|clear|clean up|take out|eliminate)\s+(?:the\s+)?",
            r"^(?:hide|cover|mask|paint over|fill in|replace)\s+(?:the\s+)?",
        ]
        is_removal = any(_re.match(p, edit_prompt, _re.IGNORECASE) for p in removal_patterns)
        if is_removal:
            # Use LLM to transform the removal prompt into a generative description
            try:
                from backend.services.bedrock_client import invoke_llm
                transform_prompt = get_template('inpaint_removal_transform').format(
                    edit_prompt=edit_prompt,
                )
                generative_prompt = invoke_llm(transform_prompt, complexity="fast", max_tokens=100, temperature=0.3).strip()
                if generative_prompt:
                    logger.info("Inpaint prompt transformed: '%s' → '%s'", edit_prompt[:50], generative_prompt[:50])
                    edit_prompt = generative_prompt
            except Exception as e:
                logger.warning("Inpaint prompt transform failed (using original): %s", e)

    logger.info("EDIT-START [%s]: model=%s purpose=%s source=%s v=%s mask=%s prompt=%s",
                edit_trace_id, body.model, purpose, body.source_image_id,
                body.source_version or "current", "yes" if mask_bytes else "no",
                edit_prompt[:50] if edit_prompt else "(none)")

    try:
        result_bytes = invoke_image_model(
            body.model,
            edit_prompt,
            negative_prompt=body.negative_prompt,
            seed=body.seed,
            region_override=body.region,
            source_image=source_bytes,
            mask_image=mask_bytes,
            mask_prompt=body.mask_prompt,
            extra_params=extra if extra else None,
        )
    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.error("EDIT-FAIL [%s]: model=%s source=%s error=%s",
                     edit_trace_id, body.model, body.source_image_id, exc)
        # Flush any partial spend (a Bedrock call that billed before failing) so the
        # cost isn't orphaned — the success-path event at the end never runs.
        try:
            _partial = get_total_cost()
            if _partial > 0:
                track_image_edit(edit_type=(get_image_model(body.model) or {}).get("model_purpose", "") if body.model else "",
                                 model=body.model or "", cost_usd=round(_partial, 6))
        except Exception:
            pass
        # A model ValidationException is a bad-input problem (400), not a gateway
        # failure (502) — surface the underlying detail so the UI can show it.
        if "ValidationException" in type(exc).__name__ or "ValidationException" in str(exc):
            raise HTTPException(400, detail=f"Image editing rejected: {exc}")
        raise HTTPException(502, detail=f"Image editing failed: {exc}")

    # Async custom edit models (e.g. Qwen-Image-Edit on a scale-to-zero endpoint)
    # return a sentinel, not image bytes — the edit runs in the background and the
    # poller saves the result as a new version. Tag the job with edit context so
    # the poller knows WHICH asset/version to write, then return an async response.
    if isinstance(result_bytes, dict) and result_bytes.get("async_submitted"):
        try:
            from backend.services.async_jobs import update_job_edit_context
            # Persist the drawn mask now (name by job id — the version number isn't
            # known until the async result lands) so the completion can reference it.
            _async_mask_file = None
            if mask_bytes:
                try:
                    _async_mask_file = f"edit_{result_bytes['job_id']}__mask.png"
                    store.save_generated_image(body.source_image_id, _async_mask_file, mask_bytes)
                except Exception:
                    _async_mask_file = None
            _src_meta = store.load_generation_metadata(body.source_image_id) or {}
            _outpaint = {}
            if any((body.outpaint_left, body.outpaint_right, body.outpaint_up, body.outpaint_down)):
                _outpaint = {"left": body.outpaint_left, "right": body.outpaint_right,
                             "up": body.outpaint_up, "down": body.outpaint_down}
            # Instruction-editor outpaint: persist the ORIGINAL (pre-pad) source as
            # a job sidecar + the pad geometry, so the async completion can restore
            # the canvas size and blend the original pixels back over the result.
            _geom_file = None
            if _outpaint_geometry is not None:
                try:
                    _geom_file = f"edit_{result_bytes['job_id']}__prepad_src.png"
                    store.save_generated_image(body.source_image_id, _geom_file, _pre_pad_source)
                except Exception:
                    _geom_file = None
            update_job_edit_context(
                result_bytes["job_id"],
                edit_asset_id=body.source_image_id,
                edit_purpose=purpose,
                # The USER's words (pre-transform) — the machine-built instruction
                # goes in edit_spec.edit_prompt_sent for truthful display.
                edit_prompt=user_prompt_raw or edit_prompt,
                edit_seed=body.seed,
                # Parity provenance so the async version record == the sync one.
                edit_spec={
                    "edit_prompt_sent": edit_prompt if edit_prompt and edit_prompt != (user_prompt_raw or body.prompt) else None,
                    "negative_prompt": body.negative_prompt,
                    "mask_prompt": body.mask_prompt,
                    "mask_file": _async_mask_file,
                    "region": body.region or model_config.get("region", ""),
                    "model_label": label,
                    "extra_params": extra if extra else None,
                    "source_dims": {"width": _src_meta.get("width"), "height": _src_meta.get("height")}
                                   if _src_meta.get("width") else None,
                    **({"outpaint_px": _outpaint} if _outpaint else {}),
                    **({"outpaint_geometry": _outpaint_geometry,
                        "prepad_source_file": _geom_file} if _outpaint_geometry else {}),
                },
            )
        except Exception as e:
            logger.error("Failed to tag async edit job %s: %s", result_bytes.get("job_id"), e)
        logger.info("EDIT-ASYNC [%s]: handed to async job %s (%s) — completion logged by the poller",
                    edit_trace_id, result_bytes.get("job_id"), label)
        return {
            "id": body.source_image_id,
            "async": True,
            "async_job_id": result_bytes.get("job_id"),
            "model": body.model,
            "model_label": label,
            "message": "Edit is processing — the new version will appear when ready.",
        }

    # Instruction-editor outpaint (sync): the model may return a different
    # resolution bucket and regenerates the whole frame — restore the padded
    # canvas size and blend the ORIGINAL pixels back over the original region.
    if _outpaint_geometry is not None and isinstance(result_bytes, (bytes, bytearray)):
        try:
            from backend.services.instruction_outpaint import restore_geometry_and_blend
            result_bytes = restore_geometry_and_blend(
                result_bytes, _pre_pad_source, _outpaint_geometry)
        except Exception as e:
            logger.warning("Outpaint geometry restore failed (using raw result): %s", e)

    # ── Versioned save: keep all previous versions, latest is always asset.png ──
    asset_id = body.source_image_id

    # Serialize against the async edit completion (async_jobs) — both writers
    # read-modify-write this asset's metadata.json; unserialized, simultaneous
    # completions can compute the same next_version and clobber a record.
    from backend.services.asset_locks import asset_write_lock
    _asset_lock = asset_write_lock(asset_id)
    _asset_lock.acquire()
    try:

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
                "enhanced_prompt": source_meta.get("enhanced_prompt", ""),
                "negative_prompt": source_meta.get("negative_prompt", ""),
                "image_model": source_meta.get("image_model", ""),
                "model_label": source_meta.get("model_label", ""),
                "timestamp": source_meta.get("created_at", ""),
            })

        # New version number
        # Max-based (not len+1): version deletion leaves TOMBSTONE records and
        # numbering is sparse — a new version must never reuse a deleted number.
        next_version = max(v.get("version", 0) for v in versions) + 1
        version_file = f"asset_v{next_version}.png"

        # Archive the current asset.png as the previous version before overwriting.
        # Archive under the TRUE current_version (not next_version-1): with sparse
        # numbering after a version delete, next-1 may be a deleted number and the
        # bytes in asset.png belong to current_version, whatever its number is.
        asset_dir = store.generated_asset_dir(asset_id)
        import shutil
        current_png = asset_dir / "asset.png"
        if current_png.exists():
            prev_version = source_meta.get("current_version") or (next_version - 1)
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
                enhanced_prompt=body.prompt,
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
        # Persist the drawn inpaint/erase mask as a sidecar so the Metadata can show
        # WHERE the edit was applied (previously the mask was decoded, sent, and
        # discarded). Named per-version; referenced in the version record as mask_file.
        _mask_file = None
        if mask_bytes:
            try:
                _mask_file = f"asset_v{next_version}__mask.png"
                store.save_generated_image(asset_id, _mask_file, mask_bytes)
            except Exception as e:
                logger.warning("Could not persist edit mask for %s: %s", asset_id, e)
                _mask_file = None

        # Capture the canvas dimensions before/after this edit so the metadata can
        # show exactly how the image changed (esp. how an outpaint/extend grew it).
        _old_dims = {"width": source_meta.get("width"), "height": source_meta.get("height")}
        _new_dims = {"width": None, "height": None}
        try:
            from PIL import Image as _PILImage
            import io as _io
            with _PILImage.open(_io.BytesIO(result_bytes)) as _img:
                _new_dims = {"width": _img.width, "height": _img.height}
        except Exception:
            pass
        # Per-edge outpaint grow amounts (0 when not an outpaint / not specified).
        _outpaint = {}
        if any((body.outpaint_left, body.outpaint_right, body.outpaint_up, body.outpaint_down)):
            _outpaint = {
                "left": body.outpaint_left, "right": body.outpaint_right,
                "up": body.outpaint_up, "down": body.outpaint_down,
            }

        versions.append({
            "version": next_version,
            "type": purpose,
            # The USER's words as typed (pre-transform snapshot) — body.prompt may
            # have been rewritten by the instruction-editor folding/outpaint build.
            "prompt": user_prompt_raw or body.prompt,
            # The ACTUAL instruction sent to the editor after any transform (inpaint
            # removal→generative rewrite, instruction-editor folding). Differs from
            # `prompt` when a transform ran — record both so the display is truthful.
            "edit_prompt_sent": edit_prompt if edit_prompt and edit_prompt != (user_prompt_raw or body.prompt) else None,
            "negative_prompt": body.negative_prompt,
            # The refined/enhanced text (for an edit, the instruction is the prompt;
            # kept for uniform per-version display alongside generated versions).
            "enhanced_prompt": edit_prompt or body.prompt,
            "mask_prompt": body.mask_prompt,
            "mask_file": _mask_file,
            # Canvas dimensions before/after + per-edge grow (outpaint/extend spec).
            "source_dims": _old_dims if _old_dims.get("width") else None,
            "result_dims": _new_dims if _new_dims.get("width") else None,
            **({"outpaint_px": _outpaint} if _outpaint else {}),
            "original_language": edit_original_language,
            "original_language_prompts": edit_original_prompts if edit_original_prompts else None,
            "image_model": body.model,
            "model_label": label,
            "region": body.region or model_config.get("region", ""),
            "seed": body.seed,
            "extra_params": extra if extra else None,
            # Provenance for programmatic edits (e.g. 3D source-completion outpaint):
            # what triggered it, the analysis verdict, directions + prompt used.
            **({"edit_context": edit_meta} if edit_meta else {}),
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
    finally:
        _asset_lock.release()

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

    logger.info("EDIT-DONE [%s]: %s v%d saved (model=%s, cost=$%.4f)",
                edit_trace_id, asset_id, next_version, body.model, edit_cost)

    return {
        "id": asset_id,
        "png_url": f"/api/gallery/{asset_id}/png",
        "png_filename": png_filename,
        "edit_type": purpose,
        "model": body.model,
        "model_label": label,
        # The new version this edit created (latest). Lets callers (e.g. the
        # 3D source-completion flow) switch to it without a second metadata fetch.
        "version": next_version,
    }


# ── Edit-prompt suggestion (per-mode, model-aware) ─────────────────────────

class SuggestEditPromptRequest(BaseModel):
    """Ask the vision LLM to propose an edit prompt for a specific edit mode.

    Reads the asset's ORIGINAL generation prompt + the rendered image, infers
    what the user most likely wants for `mode`, and writes it in the STYLE the
    target `model` expects (caption for Stability, instruction for Qwen-Edit)."""
    asset_id: str
    version: int | None = None       # which 2D version to read (default: current)
    mode: str                        # inpaint | erase | outpaint | search_replace | search_recolor
    model: str = ""                  # the selected edit model key (drives output style)


# What each edit mode does — fed to the LLM so its suggestion fits the operation.
_EDIT_MODE_INTENT = {
    "outpaint": "Extend the canvas outward and generate NEW content in the added border area (reveal cropped parts, add more environment/margin). It cannot change existing pixels.",
    "inpaint": "Fill or repair a user-masked region with new, plausible content that blends with the rest of the image.",
    "erase": "Remove an unwanted element from a user-masked region and reconstruct a clean background behind it.",
    "search_replace": "Find an existing object by description and swap it for a different object.",
    "search_recolor": "Find an existing object/region by description and change its colour or material.",
}
# UI labels use 'extend'/'fill' etc.; normalize to the internal mode keys.
_EDIT_MODE_ALIASES = {"extend": "outpaint", "fill": "inpaint", "replace": "search_replace", "recolor": "search_recolor"}


@router.post("/suggest-edit-prompt")
async def suggest_edit_prompt(body: SuggestEditPromptRequest):
    """Propose a ready-to-use edit prompt for a given mode, from the image + intent."""
    from backend.services.bedrock_client import invoke_llm
    from backend.services.prompt_templates import get_template, get_system_prompt
    from backend.services.prompt_engineer import supports_negative_prompt  # cheap registry probe
    from backend.routers.generate_3d import _fit_image_for_vision
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    import re as _re

    reset_costs()  # scope LLM cost to THIS request
    mode = _EDIT_MODE_ALIASES.get(body.mode, body.mode)
    if mode not in _EDIT_MODE_INTENT:
        raise HTTPException(400, detail=f"Unknown edit mode '{body.mode}'.")

    meta = store.load_generation_metadata(body.asset_id) or {}
    # Resolve the version image the SAME way /edit does (current = asset.png).
    ver = body.version
    source_path = None
    if ver:
        cur = meta.get("current_version") or (len(meta.get("versions", [])) or 1)
        if ver != cur:
            source_path = store.get_generated_file_path(body.asset_id, f"asset_v{ver}.png")
    if source_path is None:
        source_path = store.get_generated_file_path(body.asset_id, "asset.png")
    if source_path is None:
        raise HTTPException(404, detail=f"Source image not found: {body.asset_id}")

    source_prompt = (
        (meta.get("enhanced_prompt") or meta.get("recomposed_prompt")
         or meta.get("prompt") or meta.get("original_prompt") or "").strip()
        or "(no prompt recorded — infer purely from the image)"
    )[:1200]
    asset_type = (meta.get("asset_type") or "image").replace("_", " ")

    # Model-aware output style: instruction editors (Qwen) want an imperative
    # instruction; caption/diffusion editors (Stability) want a descriptive caption
    # of the desired result. Derive from the registry, not a hardcoded model list.
    from backend.services.model_registry import get_image_model
    mcfg = get_image_model(body.model) if body.model else None
    minv = (mcfg or {}).get("invoke", {})
    is_instruction = (mcfg or {}).get("model_purpose") == "image_edit" or bool(minv.get("instruction_following"))
    if is_instruction:
        style_directive = ("Write an INSTRUCTION telling the editor what to do, as an imperative command "
                           "(e.g. 'Add …', 'Replace the … with …', 'Remove the …', 'Change the … to …'). "
                           "This model follows instructions; do NOT write a scene caption.")
    else:
        style_directive = ("Write a concise DESCRIPTIVE CAPTION of the desired RESULT in that region "
                           "(what should be present, its material/colour/lighting to blend seamlessly) — "
                           "NOT an imperative instruction. This is a diffusion editor guided by a caption.")

    try:
        prompt = get_template("edit_prompt_suggestion").format(
            mode=mode, mode_intent=_EDIT_MODE_INTENT[mode],
            style_directive=style_directive, source_prompt=source_prompt, asset_type=asset_type)
        system = get_system_prompt("edit_prompt_suggestion")
        vision_bytes = _fit_image_for_vision(source_path.read_bytes())
        raw = invoke_llm(prompt, system=system, complexity="complex",
                         images=[vision_bytes], max_tokens=400, temperature=0.2)
        txt = (raw or "").strip()
        txt = _re.sub(r"^```(?:json)?\s*\n?", "", txt)
        txt = _re.sub(r"\n?```\s*$", "", txt)
        s, e = txt.find("{"), txt.rfind("}")
        data = json.loads(txt[s:e + 1]) if s >= 0 and e > s else {}
    except Exception as exc:
        logger.warning("Edit-prompt suggestion failed for %s (%s): %s", body.asset_id, mode, exc)
        raise HTTPException(502, detail="Prompt suggestion is unavailable right now. Please try again.")
    finally:
        # Runs on both success and failure — report the LLM cost either way.
        track_aux_llm_cost("suggest_edit_prompt", get_total_cost())

    def _clamp(v):
        try: return max(0, min(1024, int(v)))
        except (TypeError, ValueError): return 0
    outp = data.get("suggest_outpaint", {}) or {}
    return {
        "mode": mode,
        "prompt": (data.get("prompt", "") or "").strip()[:500],
        "search_prompt": (data.get("search_prompt", "") or "").strip()[:200],
        "reasoning": (data.get("reasoning", "") or "").strip()[:300],
        "suggest_outpaint": {d: _clamp(outp.get(d, 0)) for d in ("down", "up", "left", "right")},
    }


# ── Pre-screen (Safe Mode) ─────────────────────────────────────────────────

class PreScreenRequest(BaseModel):
    prompt: str
    image_model: str = "sd35_large"


@router.post("/pre-screen")
async def pre_screen_prompt(body: PreScreenRequest):
    """Quick pre-screen using Claude Sonnet (fast, cheap) to check if a prompt
    will likely trigger moderation on the selected model.

    Returns: likely_safe, issues, suggested_model (if the prompt is better
    suited for a more permissive model).
    """
    from backend.services.bedrock_client import invoke_llm
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    import re as _re

    reset_costs()  # scope LLM cost (translation + pre-screen) to THIS request
    from backend.services.model_registry import get_enabled_model_labels, get_enabled_image_models
    model_labels = get_enabled_model_labels()
    model_label = model_labels.get(body.image_model, body.image_model)

    # Moderation behaviour is REGISTRY-DRIVEN per the target model — never hardcoded
    # to any specific model (e.g. Nova Canvas). Use the selected model's configured
    # moderation_strictness, and offer the enabled text-to-image models (label:
    # strictness) as permissive-fallback options. Self-hosted / unset → "permissive"
    # (no managed content moderation), so those rarely block.
    _enabled = get_enabled_image_models()
    model_strictness = (_enabled.get(body.image_model, {}).get("moderation_strictness")
                        or "permissive")
    model_options = "\n".join(
        f"- {cfg.get('label', k)}: {cfg.get('moderation_strictness') or 'permissive'}"
        for k, cfg in _enabled.items()
        if cfg.get('model_purpose', 'text_to_image') == 'text_to_image'
    ) or "(none)"

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
        model_strictness=model_strictness,
        model_options=model_options,
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
    finally:
        track_aux_llm_cost("pre_screen", get_total_cost())


# ── Moderation analysis ───────────────────────────────────────────────────

class ModerationRequest(BaseModel):
    prompt: str
    error_message: str = ""
    image_model: str = "sd35_large"
    width: int = 512
    height: int = 512
    force_rewrite: bool = False  # Skip model switching, go straight to rewrite for the target model


# Model permissiveness order (most permissive first for fallback testing)
_ALTERNATIVE_MODELS = [
    ImageModel.SD35_LARGE,
    ImageModel.STABLE_IMAGE_ULTRA,
]


@router.post("/analyze-moderation")
async def analyze_moderation(body: ModerationRequest):
    """Wrapper: scope + report the FULL cost of moderation analysis (image-gen
    fallback attempts + rewrite LLM calls) to telemetry, then delegate. This
    standalone endpoint's spend was previously unreported. The finally covers every
    return path AND failures — no missed cost."""
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    reset_costs()
    try:
        return await _analyze_moderation_impl(body)
    finally:
        track_aux_llm_cost("analyze_moderation", get_total_cost())


async def _analyze_moderation_impl(body: ModerationRequest):
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
    original_model_enum = ImageModel(original_model) if original_model in [m.value for m in ImageModel] else ImageModel.SD35_LARGE
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
                enhanced_prompt=body.prompt,
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

        rewrite_instruction = get_template('moderation_rewrite').format(
            target_context=target_context,
            prompt_label=prompt_label,
            current_prompt=current_prompt,
            issues_text=issues_text,
        )

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
                        enhanced_prompt=rewritten,
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
                        time.sleep(1)  # nosemgrep --deliberate throttle between upscale calls
                    try:
                        prompt = meta.get("enhanced_prompt", meta.get("prompt", ""))
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
        track_post_process(action="+".join(actions), cost_usd=pp_cost, num_assets=total)

    return {"processed": results, "errors": errors}


# ── Async Jobs (self-hosted custom models) ───────────────────────────────

@router.get("/async-jobs")
def get_async_jobs():
    """Get all async generation jobs (pending, complete, failed)."""
    from backend.services.async_jobs import get_all_jobs, get_pending_count, has_active_jobs
    return {"jobs": get_all_jobs(), "pending_count": get_pending_count(), "has_active": has_active_jobs()}


@router.post("/async-jobs/clear")
def clear_async_jobs():
    """Clear completed and failed jobs from the tracker."""
    from backend.services.async_jobs import clear_completed
    removed = clear_completed()
    return {"cleared": removed}
