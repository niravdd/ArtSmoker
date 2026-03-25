"""Admin router — model registry management and Bedrock model discovery."""

import logging

import boto3
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from backend.services.model_registry import (
    add_image_model,
    add_video_model,
    get_registry,
    get_video_settings,
    reload,
    update_category,
    update_image_model,
    update_post_processing,
    update_video_model,
    update_video_settings,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Registry CRUD ─────────────────────────────────────────────────────────

@router.get("/models")
async def get_models():
    """Return the full model registry."""
    from backend.services.telemetry import track_model_settings_load
    track_model_settings_load()
    return get_registry()


@router.put("/models")
async def replace_registry(request: Request):
    """Replace the entire model registry with the provided JSON.

    Used by the raw JSON editor in Model Settings. Validates the JSON
    has required top-level keys before saving.
    """
    from backend.services.model_registry import get_registry, _save, _load
    import json as _json

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, detail="Invalid JSON")

    required = ["categories", "image_models"]
    missing = [k for k in required if k not in body]
    if missing:
        raise HTTPException(400, detail=f"Missing required keys: {', '.join(missing)}")

    # Replace the in-memory registry and save to disk
    registry = get_registry()
    registry.clear()
    registry.update(body)
    _save()
    logger.info("Full registry replaced via PUT /api/admin/models")

    return {"status": "saved", "keys": list(body.keys())}


class CategoryUpdate(BaseModel):
    current: str | None = None
    region: str | None = None
    provider: str | None = None


@router.patch("/models/category/{name}")
async def update_model_category(name: str, body: CategoryUpdate):
    """Update a model category (fast_llm, complex_llm, fallback_llm, voice)."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail="No updates provided")
    result = update_category(name, updates)
    logger.info("Updated category '%s': %s", name, updates)
    return result


class ImageModelUpdate(BaseModel):
    label: str | None = None
    model_id: str | None = None
    region: str | None = None
    enabled: bool | None = None
    prompt_limit: int | None = None
    supports_dimensions: bool | None = None
    supports_aspect_ratio: bool | None = None
    moderation_strictness: str | None = None


@router.patch("/models/image/{key}")
async def update_image_model_config(key: str, body: ImageModelUpdate):
    """Update an image model configuration."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail="No updates provided")
    result = update_image_model(key, updates)
    logger.info("Updated image model '%s': %s", key, updates)
    return result


class VideoModelUpdate(BaseModel):
    enabled: bool | None = None
    region: str | None = None
    prompt_limit: int | None = None


@router.patch("/models/video/{key}")
async def update_video_model_config(key: str, body: VideoModelUpdate):
    """Update a video model configuration."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail="No updates provided")
    result = update_video_model(key, updates)
    logger.info("Updated video model '%s': %s", key, updates)
    return result


class NewImageModel(BaseModel):
    key: str
    label: str
    model_id: str
    region: str
    provider: str = ""
    enabled: bool = True
    prompt_limit: int = 900
    supports_dimensions: bool = True
    supports_aspect_ratio: bool = False
    moderation_strictness: str = "moderate"
    request_format: dict = {}


@router.post("/models/image")
async def add_new_image_model(body: NewImageModel):
    """Add a new image model to the registry."""
    config = body.model_dump(exclude={"key"})
    result = add_image_model(body.key, config)
    logger.info("Added image model '%s': %s", body.key, body.model_id)
    return result


class PostProcessUpdate(BaseModel):
    model_id: str | None = None
    region: str | None = None
    enabled: bool | None = None


@router.patch("/models/postprocess/{key}")
async def update_postprocess_model(key: str, body: PostProcessUpdate):
    """Update a post-processing model configuration."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail="No updates provided")
    result = update_post_processing(key, updates)
    logger.info("Updated post-processing '%s': %s", key, updates)
    return result


@router.post("/models/reload")
async def reload_registry():
    """Reload the model registry from disk."""
    reload()
    return {"status": "reloaded"}


@router.get("/models/image-options")
async def get_image_model_options(region: str | None = Query(default=None)):
    """Return enabled image models for the frontend dropdown.

    This is the source of truth for model selection — the frontend
    should NOT hardcode model lists. Returns models sorted by provider
    then label.

    Optional `region` filter: if provided, only returns models available
    in that region. If omitted, returns all enabled models.
    """
    from backend.services.model_registry import get_enabled_image_models, get_registry
    enabled = get_enabled_image_models()
    registry = get_registry()
    pricing = registry.get("image_pricing", {})

    models = []
    for key, cfg in sorted(enabled.items(), key=lambda x: (x[1].get("provider", ""), x[1].get("label", x[0]))):
        if cfg.get("model_purpose") != "text_to_image":
            continue  # Only text-to-image models for the generation dropdown

        available_regions = cfg.get("available_regions", [cfg.get("region", "")])

        # Region filter: check if model is available in the requested region
        if region:
            if region not in available_regions:
                continue

        # Build per-region pricing with quality breakdown
        # Try matching pricing data by multiple name variants
        model_label = cfg.get("label", key)
        name_variants = [model_label, model_label.replace("Amazon ", ""), model_label.replace("Stable ", ""), key]
        quality_opts = cfg.get("quality_options", [])
        default_q = cfg.get("default_quality", "")

        region_pricing = []
        for r in available_regions:
            # Build quality-specific prices for this region
            quality_prices = {}
            for name_variant in name_variants:
                for q in (quality_opts or [{"value": ""}]):
                    qv = q.get("value", "")
                    # Try full key first: model|region|quality|1024
                    for size in ["1024", "512", ""]:
                        price_info = pricing.get(f"{name_variant}|{r}|{qv}|{size}", {})
                        if price_info.get("price_usd") and price_info.get("is_t2i", True):
                            if qv not in quality_prices:
                                quality_prices[qv] = price_info["price_usd"]
                            break
                if quality_prices:
                    break  # Found prices with this name variant

            # Fallback: simple key
            if not quality_prices:
                for name_variant in name_variants:
                    price_info = pricing.get(f"{name_variant}|{r}", {})
                    if price_info.get("price_usd"):
                        quality_prices[""] = price_info["price_usd"]
                        break

            # Default price = default quality tier, or first available, or base_price from registry
            base_price = cfg.get("base_price_usd")
            default_price = quality_prices.get(default_q) or quality_prices.get("") or next(iter(quality_prices.values()), None) or base_price

            region_pricing.append({
                "region": r,
                "price_usd": default_price,
                "quality_prices": quality_prices if quality_prices else None,
            })
        # Sort: known prices ascending, then unknown at the end
        region_pricing.sort(key=lambda x: (x["price_usd"] is None, x["price_usd"] or 0))

        # Default region = cheapest known, or first available
        default_region = region_pricing[0]["region"] if region_pricing else cfg.get("region", "")

        models.append({
            "key": key,
            "label": model_label,
            "provider": cfg.get("provider", ""),
            "region": default_region,
            "available_regions": [rp["region"] for rp in region_pricing],
            "region_pricing": region_pricing,
            "prompt_limit": cfg.get("prompt_limit", 900),
            "moderation_strictness": cfg.get("moderation_strictness", "moderate"),
            "format_family": cfg.get("format_family", ""),
            "quality_options": cfg.get("quality_options", []),
            "default_quality": cfg.get("default_quality"),
            "base_price_usd": cfg.get("base_price_usd"),
        })

    # Collect all regions that have at least one model
    all_regions = sorted(set(
        r for m in models for r in m.get("available_regions", [])
    ))

    return {"models": models, "available_regions": all_regions}


@router.get("/models/video-options")
async def get_video_model_options():
    """Return enabled video models for the Video Studio dropdown."""
    from backend.services.model_registry import get_enabled_video_models, get_registry
    enabled = get_enabled_video_models()
    registry = get_registry()

    models = []
    for key, cfg in sorted(enabled.items(), key=lambda x: (x[1].get("provider", ""), x[1].get("label", x[0]))):
        family_name = cfg.get("format_family", "")
        family = registry.get("format_families", {}).get(family_name, {})
        models.append({
            "key": key,
            "label": cfg.get("label", key),
            "model_id": cfg.get("model_id", ""),
            "provider": cfg.get("provider", ""),
            "region": cfg.get("region", ""),
            "available_regions": cfg.get("available_regions", []),
            "format_family": family_name,
            "prompt_limit": cfg.get("prompt_limit", 512),
            "supports_image_input": cfg.get("supports_image_input", False),
            "base_price_per_second_usd": cfg.get("base_price_per_second_usd"),
            "parameters": family.get("parameters", {}),
            "task_types": family.get("task_types", {}),
        })

    return {"models": models}


@router.get("/video/settings")
async def get_video_settings_endpoint():
    """Return current video storage settings."""
    return get_video_settings()


class VideoSettingsUpdate(BaseModel):
    s3_bucket: str | None = None
    s3_prefix: str | None = None
    store_local: bool | None = None


@router.put("/video/settings")
async def update_video_settings_endpoint(body: VideoSettingsUpdate):
    """Update video storage settings. Validates S3 bucket access before saving."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail="No updates provided")

    # If changing bucket, validate access first
    if "s3_bucket" in updates and updates["s3_bucket"]:
        bucket = updates["s3_bucket"]
        try:
            s3 = boto3.Session().client("s3")
            # Test: can we list objects (read) and put a test object (write)?
            s3.head_bucket(Bucket=bucket)
            prefix = updates.get("s3_prefix", get_video_settings().get("s3_prefix", "artsmoker/video/"))
            test_key = f"{prefix}_access_test.txt"
            s3.put_object(Bucket=bucket, Key=test_key, Body=b"ArtSmoker access test")
            s3.delete_object(Bucket=bucket, Key=test_key)
            updates["s3_validated"] = True
            updates["s3_bucket_arn"] = f"arn:aws:s3:::{bucket}"
            logger.info("S3 bucket '%s' validated: read/write OK", bucket)
        except s3.exceptions.NoSuchBucket:
            raise HTTPException(400, detail=f"Bucket '{bucket}' does not exist. Use Browse to select an existing bucket or create a new one.")
        except Exception as exc:
            error_str = str(exc)
            if "404" in error_str or "Not Found" in error_str:
                raise HTTPException(400, detail=f"Bucket '{bucket}' not found. Use Browse to select an existing bucket or create a new one.")
            if "403" in error_str or "Forbidden" in error_str or "AccessDenied" in error_str:
                raise HTTPException(400, detail=f"Access denied to bucket '{bucket}'. Check your AWS permissions.")
            raise HTTPException(400, detail=f"S3 bucket validation failed: {exc}")

    result = update_video_settings(updates)
    return result


# ── Bedrock Model Discovery ──────────────────────────────────────────────

import re as _re


def _model_family_key(model_id: str) -> str:
    """Extract a base family key, aggressively grouping model versions.

    Groups: all Claude Opus 4.x together, all Claude Sonnet 4.x together,
    all Llama 3.x together, etc. Keeps only provider + model line + major version.
    """
    key = model_id
    # Strip everything after first colon
    key = key.split(":")[0]
    # Strip -vN suffix
    key = _re.sub(r'-v\d+(\.\d+)?$', '', key)
    # Strip date suffixes
    key = _re.sub(r'-\d{8}$', '', key)

    # Claude: group all minor versions (opus-4, opus-4-1, opus-4-5, opus-4-6 → opus-4)
    key = _re.sub(r'(claude-(?:opus|sonnet|haiku)-\d+)-\d+', r'\1', key)

    # Llama: group context variants (llama3-1-70b, llama3-2-90b keep as-is, but strip -instruct)
    key = _re.sub(r'-instruct$', '', key)

    # Nova: strip throughput variants
    key = _re.sub(r'(nova-\w+)-\d+k$', r'\1', key)

    return key


def _deduplicate_models(models: list[dict]) -> list[dict]:
    """Keep only the latest version per model family per provider.

    Groups by provider + family key, keeps the one with the longest
    model_id (which typically has the most specific version).
    """
    families: dict[str, dict] = {}
    for m in models:
        key = f"{m['provider']}::{_model_family_key(m['model_id'])}"
        existing = families.get(key)
        if not existing or len(m['model_id']) >= len(existing['model_id']):
            families[key] = m
    return sorted(families.values(), key=lambda m: (m['provider'], m['model_id']))


@router.post("/discover/{region}/auto-register")
async def auto_register_image_models(region: str):
    """Discover image generation models in a region and register/update them.

    Only processes text-to-image models (TEXT input → IMAGE output).
    Maps providers to format families automatically:
    - Amazon → amazon_text_to_image
    - Stability AI → stability_text_to_image

    For new models: registers with enabled=False (admin must enable).
    For existing models: adds the region to available_regions if not already present.
    Returns summary of new registrations and region updates.
    """
    try:
        session = boto3.Session()
        bedrock = session.client("bedrock", region_name=region)
        response = bedrock.list_foundation_models()
    except Exception as exc:
        raise HTTPException(502, detail=f"Failed to list models in {region}: {exc}")

    from backend.services.model_registry import (
        get_registry, add_image_model, get_image_model, update_image_model,
        add_video_model, get_video_model, update_video_model,
    )

    registry = get_registry()
    # Build model_id → list of registry keys lookup for existing models
    # Map both the stored model_id and the raw version (without us. prefix)
    # so that Bedrock's raw IDs match our stored inference profile IDs.
    # Multiple entries may share the same model_id (e.g. inpaint/outpaint variants).
    existing_by_model_id: dict[str, list[str]] = {}
    for key, cfg in registry.get("image_models", {}).items():
        stored_id = cfg.get("model_id", "")
        existing_by_model_id.setdefault(stored_id, []).append(key)
        if stored_id.startswith("us."):
            existing_by_model_id.setdefault(stored_id[3:], []).append(key)
    existing_video_by_model_id: dict[str, list[str]] = {}
    for key, cfg in registry.get("video_models", {}).items():
        stored_id = cfg.get("model_id", "")
        existing_video_by_model_id.setdefault(stored_id, []).append(key)
        if stored_id.startswith("us."):
            existing_video_by_model_id.setdefault(stored_id[3:], []).append(key)

    # Classify image models by purpose and format family based on model_id keywords.
    def _classify_image_model(model_id: str, provider: str, input_modalities: list[str]):
        """Determine model_purpose and format_family from model_id and provider."""
        mid = model_id.lower()
        has_image_input = "IMAGE" in input_modalities

        # Stability AI services — classify by model ID keywords
        if provider == "Stability AI":
            if "inpaint" in mid:
                return "inpainting", "stability_inpaint", 10000, 0.07
            if "outpaint" in mid:
                return "outpainting", "stability_outpaint", 10000, 0.06
            if "erase" in mid:
                return "erase", "stability_erase", 0, 0.07
            if "search-replace" in mid or "search_replace" in mid:
                return "search_replace", "stability_search_replace", 10000, 0.07
            if "search-recolor" in mid or "recolor" in mid:
                return "search_recolor", "stability_search_recolor", 10000, 0.07
            if "control-sketch" in mid:
                return "control_sketch", "stability_control", 10000, 0.07
            if "control-structure" in mid:
                return "control_structure", "stability_control", 10000, 0.07
            if "style-guide" in mid:
                return "style_guide", "stability_control", 10000, 0.07
            if "style-transfer" in mid:
                return "style_transfer", "stability_style_transfer", 10000, 0.08
            if "remove-background" in mid:
                return "remove_background", "stability_remove_bg", 0, 0.07
            if "creative-upscale" in mid:
                return "upscale_creative", "stability_upscale", 10000, 0.60
            if "conservative-upscale" in mid:
                return "upscale_conservative", "stability_upscale", 10000, 0.40
            if "fast-upscale" in mid:
                return "upscale_fast", "stability_upscale", 0, 0.03
            # Default: text-to-image
            return "text_to_image", "stability_text_to_image", 2000, 0.08

        # Amazon models
        if provider == "Amazon":
            return "text_to_image", "amazon_text_to_image", 900, 0.06

        return "text_to_image", None, 900, None

    def _classify_video_model(model_id: str, provider: str, input_modalities: list[str]):
        """Determine format_family and pricing for video models."""
        mid = model_id.lower()
        has_image_input = "IMAGE" in input_modalities
        if "nova-reel" in mid:
            return "text_to_video", "nova_reel", 512, 0.08, has_image_input
        if "ray" in mid or "luma" in mid:
            return "text_to_video", "luma_ray", 5000, 1.50, has_image_input
        return "text_to_video", None, 512, None, has_image_input

    registered = []
    updated = []

    for m in response.get("modelSummaries", []):
        model_id = m.get("modelId", "")
        output = m.get("outputModalities", [])
        inp = m.get("inputModalities", [])
        provider = m.get("providerName", "")

        is_image = "IMAGE" in output
        is_video = "VIDEO" in output

        # Must produce images or video
        if not is_image and not is_video:
            continue

        # ── Video models ─────────────────────────────────────────────
        if is_video:
            purpose, family, prompt_limit, base_price, has_img_input = _classify_video_model(model_id, provider, inp)
            if not family:
                logger.warning("Unknown video provider '%s' for model %s — skipping", provider, model_id)
                continue

            if model_id in existing_video_by_model_id:
                for existing_key in existing_video_by_model_id[model_id]:
                    existing_cfg = get_video_model(existing_key)
                    if not existing_cfg:
                        continue
                    backfill = {}
                    if not existing_cfg.get("input_modalities"):
                        backfill["input_modalities"] = inp
                    if not existing_cfg.get("output_modalities"):
                        backfill["output_modalities"] = output
                    if not existing_cfg.get("model_arn"):
                        backfill["model_arn"] = m.get("modelArn", "")
                    if not existing_cfg.get("model_lifecycle"):
                        backfill["model_lifecycle"] = m.get("modelLifecycle", {}).get("status", "")
                    if "streaming_supported" not in existing_cfg:
                        backfill["streaming_supported"] = m.get("responseStreamingSupported", False)
                    if not existing_cfg.get("customizations_supported"):
                        backfill["customizations_supported"] = m.get("customizationsSupported", [])

                    regions = existing_cfg.get("available_regions", [existing_cfg.get("region", "")])
                    if region not in regions:
                        regions.append(region)
                        regions.sort()
                        backfill["available_regions"] = regions
                        updated.append({"key": existing_key, "model_id": model_id, "added_region": region, "media": "video"})

                    if backfill:
                        update_video_model(existing_key, backfill)
                continue

            # Include version in key: amazon.nova-reel-v1:1 → nova_reel_v1_1
            raw_key = model_id.split(".")[-1].replace("-", "_").replace(":", "_")
            key = raw_key
            if get_video_model(key):
                key = f"{key}_{region.replace('-', '_')}"

            # Build user-friendly label from model_id version
            # "amazon.nova-reel-v1:0" → "Nova Reel v1.0", "luma.ray-v2:0" → "Ray v2.0"
            model_name = m.get("modelName", model_id)
            tail = model_id.split(".")[-1]  # "nova-reel-v1:1" or "ray-v2:0"
            version_str = tail.replace(":", ".").split("-")[-1]  # "v1.1" or "v2.0"
            # Avoid duplication: if model name already contains the major version, replace it
            major_v = version_str.split(".")[0]  # "v1" or "v2"
            if model_name.lower().endswith(major_v):
                label = f"{model_name[:-len(major_v)]}{version_str}"
            else:
                label = f"{model_name} {version_str}"

            config = {
                "label": label,
                "model_id": model_id,
                "region": region,
                "available_regions": [region],
                "provider": provider,
                "enabled": True,
                "model_purpose": purpose,
                "format_family": family,
                "prompt_limit": prompt_limit,
                "supports_image_input": has_img_input,
                "base_price_per_second_usd": base_price,
                "inference_types": m.get("inferenceTypesSupported", []),
                "input_modalities": inp,
                "output_modalities": output,
                "model_arn": m.get("modelArn", ""),
                "model_lifecycle": m.get("modelLifecycle", {}).get("status", ""),
                "streaming_supported": m.get("responseStreamingSupported", False),
                "customizations_supported": m.get("customizationsSupported", []),
            }
            add_video_model(key, config)
            existing_video_by_model_id[model_id] = key
            registered.append({"key": key, "model_id": model_id, "label": config["label"],
                              "region": region, "purpose": purpose, "media": "video"})
            logger.info("Auto-registered video: %s (%s) in %s", key, model_id, region)
            continue

        # ── Image models ─────────────────────────────────────────────
        # Classify the model
        purpose, family, prompt_limit, base_price = _classify_image_model(model_id, provider, inp)
        if not family:
            logger.warning("Unknown provider '%s' for model %s — skipping", provider, model_id)
            continue

        # Already registered? → update available_regions + backfill metadata for ALL matching entries
        if model_id in existing_by_model_id:
            for existing_key in existing_by_model_id[model_id]:
                existing_cfg = get_image_model(existing_key)
                if not existing_cfg:
                    continue
                # Backfill Bedrock metadata if missing
                backfill = {}
                if not existing_cfg.get("input_modalities"):
                    backfill["input_modalities"] = inp
                if not existing_cfg.get("output_modalities"):
                    backfill["output_modalities"] = output
                if not existing_cfg.get("model_arn"):
                    backfill["model_arn"] = m.get("modelArn", "")
                if not existing_cfg.get("model_lifecycle"):
                    backfill["model_lifecycle"] = m.get("modelLifecycle", {}).get("status", "")
                if "streaming_supported" not in existing_cfg:
                    backfill["streaming_supported"] = m.get("responseStreamingSupported", False)
                if not existing_cfg.get("customizations_supported"):
                    backfill["customizations_supported"] = m.get("customizationsSupported", [])

                regions = existing_cfg.get("available_regions", [existing_cfg.get("region", "")])
                if region not in regions:
                    regions.append(region)
                    regions.sort()
                    backfill["available_regions"] = regions
                    updated.append({"key": existing_key, "model_id": model_id, "added_region": region})
                    logger.info("Updated %s: added region %s (now %s)", existing_key, region, regions)

                if backfill:
                    update_image_model(existing_key, backfill)
            # Create Amazon inpaint/outpaint variants if they don't exist
            # Find the base text_to_image entry for this model_id
            base_key = None
            base_cfg = None
            for ek in existing_by_model_id[model_id]:
                ec = get_image_model(ek)
                if ec and ec.get("model_purpose") == "text_to_image":
                    base_key, base_cfg = ek, ec
                    break
            if provider == "Amazon" and base_cfg:
                model_name = m.get("modelName", "")
                for variant_purpose, variant_family, variant_suffix in [
                    ("inpainting", "amazon_inpainting", "_inpaint"),
                    ("outpainting", "amazon_outpainting", "_outpaint"),
                ]:
                    variant_key = base_key + variant_suffix
                    if not get_image_model(variant_key):
                        variant_config = {
                            "label": f"{model_name or base_cfg.get('label', '')} {variant_purpose.title()}",
                            "model_id": model_id,
                            "region": region,
                            "available_regions": [region],
                            "provider": provider,
                            "enabled": True,
                            "model_purpose": variant_purpose,
                            "format_family": variant_family,
                            "prompt_limit": base_cfg.get("prompt_limit", 900),
                            "moderation_strictness": base_cfg.get("moderation_strictness", "moderate"),
                            "base_price_usd": base_cfg.get("base_price_usd"),
                            "extra_body": base_cfg.get("extra_body", {}),
                        }
                        add_image_model(variant_key, variant_config)
                        registered.append({"key": variant_key, "model_id": model_id,
                                          "label": variant_config["label"], "region": region,
                                          "purpose": variant_purpose})
                    else:
                        ex = get_image_model(variant_key)
                        if ex:
                            vr = ex.get("available_regions", [])
                            if region not in vr:
                                vr.append(region)
                                vr.sort()
                                update_image_model(variant_key, {"available_regions": vr})
            continue

        # Generate a registry key from model_id
        key = model_id.split(".")[-1].split(":")[0].replace("-", "_")
        if get_image_model(key):
            key = f"{key}_{region.replace('-', '_')}"

        # Models that require INFERENCE_PROFILE need the US prefix (us.{model_id})
        # This is determined by the inferenceTypesSupported field from Bedrock discovery
        inference_types = m.get("inferenceTypesSupported", [])
        effective_model_id = model_id
        if "INFERENCE_PROFILE" in inference_types and not model_id.startswith("us."):
            effective_model_id = f"us.{model_id}"

        config = {
            "label": m.get("modelName", model_id),
            "model_id": effective_model_id,
            "region": region,
            "available_regions": [region],
            "provider": provider,
            "enabled": True,  # Discovered and enabled by default — admin can disable
            "model_purpose": purpose,
            "format_family": family,
            "prompt_limit": prompt_limit,
            "moderation_strictness": "moderate",
            "base_price_usd": base_price,
            "inference_types": inference_types,
            "input_modalities": inp,
            "output_modalities": output,
            "model_arn": m.get("modelArn", ""),
            "model_lifecycle": m.get("modelLifecycle", {}).get("status", ""),
            "streaming_supported": m.get("responseStreamingSupported", False),
            "customizations_supported": m.get("customizationsSupported", []),
            "extra_body": {},
        }

        add_image_model(key, config)
        registered.append({"key": key, "model_id": model_id, "label": config["label"],
                          "region": region, "purpose": purpose})
        logger.info("Auto-registered: %s (%s) purpose=%s in %s", key, model_id, purpose, region)

        # Amazon multi-purpose models: also create inpainting/outpainting variants
        if provider == "Amazon" and purpose == "text_to_image":
            model_name = m.get("modelName", "")
            for variant_purpose, variant_family, variant_suffix in [
                ("inpainting", "amazon_inpainting", "_inpaint"),
                ("outpainting", "amazon_outpainting", "_outpaint"),
            ]:
                variant_key = key + variant_suffix
                if not get_image_model(variant_key):
                    variant_config = {
                        "label": f"{model_name} {variant_purpose.title()}",
                        "model_id": model_id,
                        "region": region,
                        "available_regions": [region],
                        "provider": provider,
                        "enabled": True,
                        "model_purpose": variant_purpose,
                        "format_family": variant_family,
                        "prompt_limit": prompt_limit,
                        "moderation_strictness": "moderate",
                        "base_price_usd": base_price,
                        "extra_body": config.get("extra_body", {}),
                    }
                    add_image_model(variant_key, variant_config)
                    registered.append({"key": variant_key, "model_id": model_id,
                                      "label": variant_config["label"], "region": region,
                                      "purpose": variant_purpose})

    return {
        "region": region,
        "registered": registered,
        "updated": updated,
        "new_count": len(registered),
        "updated_count": len(updated),
        "message": (
            f"Registered {len(registered)} new, updated {len(updated)} existing"
            if registered or updated else "No changes — all models already registered"
        ),
    }


def _fetch_image_pricing() -> dict:
    """Fetch per-image pricing from the AWS Pricing API.

    Returns a dict keyed by 'model_name|region' with price_usd values.
    Only called during refresh-all — results are stored in the registry.
    The Pricing API is only available in us-east-1.
    """
    try:
        import json as _json
        client = boto3.Session().client("pricing", region_name="us-east-1")
        prices = {}
        next_token = None

        while True:
            kwargs = {"ServiceCode": "AmazonBedrock", "MaxResults": 100}
            if next_token:
                kwargs["NextToken"] = next_token
            resp = client.get_products(**kwargs)

            for p in resp.get("PriceList", []):
                pd = _json.loads(p)
                attrs = pd.get("product", {}).get("attributes", {})
                usage = attrs.get("usagetype", "")

                for terms in pd.get("terms", {}).values():
                    for term in terms.values():
                        for dim in term.get("priceDimensions", {}).values():
                            unit = dim.get("unit", "")
                            if unit == "image":
                                model_name = attrs.get("model", "")
                                region = attrs.get("regionCode", "")
                                price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                                if model_name and region and price > 0:
                                    # Parse quality and size from usage type
                                    # e.g. "USE1-NovaCanvas-T2I-1024-Premium"
                                    u = usage.upper()
                                    is_t2i = "T2I" in u

                                    # Extract quality tier dynamically from the usage string
                                    # by splitting on delimiters and finding non-numeric,
                                    # non-structural tokens (not region prefix, model name, T2I/I2I)
                                    parts = _re.split(r"[-_]", usage)
                                    _STRUCTURAL = {"T2I", "I2I", "Custom"}
                                    quality_tier = ""
                                    size_tier = ""
                                    for part in parts:
                                        if _re.match(r"^\d+$", part):
                                            size_tier = part  # e.g. "1024", "2048", "512"
                                        elif part not in _STRUCTURAL and not _re.match(r"^[A-Z]{2,4}\d", part) and len(part) > 3:
                                            # Not a region prefix, not a structural keyword,
                                            # not a short code — likely a quality tier
                                            if part.lower() not in model_name.lower():
                                                quality_tier = part.lower()  # e.g. "premium", "standard"

                                    # Store with full key: model|region|quality|size
                                    full_key = f"{model_name}|{region}|{quality_tier}|{size_tier}"
                                    # Also store a simpler key for backward compat
                                    simple_key = f"{model_name}|{region}"

                                    if is_t2i or full_key not in prices:
                                        prices[full_key] = {
                                            "model_name": model_name,
                                            "region": region,
                                            "quality": quality_tier,
                                            "size": size_tier,
                                            "price_usd": price,
                                            "usage_type": usage[:80],
                                            "is_t2i": is_t2i,
                                        }
                                    # Keep simple key as fallback (T2I 1024 standard)
                                    if is_t2i and size_tier == "1024" and quality_tier == "standard":
                                        prices[simple_key] = {
                                            "model_name": model_name,
                                            "region": region,
                                            "price_usd": price,
                                            "usage_type": usage[:80],
                                        }

            next_token = resp.get("NextToken")
            if not next_token:
                break

        logger.info("Fetched %d image pricing entries from AWS Pricing API", len(prices))
        return prices
    except Exception as exc:
        logger.warning("Failed to fetch pricing data: %s", exc)
        return {}


def _get_bedrock_regions() -> list[str]:
    """Dynamically discover all AWS regions that support Bedrock.

    Uses boto3's service region metadata — no hardcoded list.
    This automatically includes new regions as AWS adds Bedrock support.
    """
    try:
        session = boto3.Session()
        regions = session.get_available_regions("bedrock")
        if regions:
            return sorted(regions)
    except Exception as exc:
        logger.warning("Failed to discover Bedrock regions: %s", exc)

    # Fallback: minimum known regions if dynamic discovery fails
    return ["us-east-1", "us-west-2"]


@router.get("/regions")
async def list_bedrock_regions():
    """Return Bedrock-supported AWS regions from the registry.

    Reads from the cached list in model_registry.json — does NOT call AWS.
    The list is refreshed only when refresh-all is called.
    """
    from backend.services.model_registry import get_registry
    registry = get_registry()
    regions = registry.get("bedrock_regions", [])
    if not regions:
        # First time — no regions cached yet. Return a minimal fallback.
        regions = ["us-east-1", "us-west-2"]
    return {"regions": regions, "count": len(regions)}


@router.post("/discover/refresh-all")
async def refresh_all_regions():
    """Scan ALL Bedrock-supported AWS regions for image + video models and update the registry."""
    from backend.services.telemetry import track_model_settings_refresh
    track_model_settings_refresh()

    from backend.services.model_registry import get_registry, _save

    # Step 1: Discover regions from AWS
    all_regions = _get_bedrock_regions()

    # Step 2: Persist regions + fetch pricing data
    registry = get_registry()
    registry["bedrock_regions"] = all_regions
    _save()
    logger.info("Stored %d Bedrock regions in registry", len(all_regions))

    # Step 2b: Fetch per-image pricing from AWS Pricing API
    pricing_data = _fetch_image_pricing()
    if pricing_data:
        registry["image_pricing"] = pricing_data
        _save()
        logger.info("Stored pricing for %d model-region combos", len(pricing_data))

    # Step 2c: Reset all available_regions before scanning — so stale regions
    # are pruned automatically. Each region scan in Step 3 re-adds itself.
    from backend.services.model_registry import update_image_model
    for key in list(registry.get("image_models", {}).keys()):
        update_image_model(key, {"available_regions": []})

    # Step 3: Scan each region for models — each scan adds its region back

    results = {}
    total_new = 0
    total_updated = 0
    errors = 0

    for region in all_regions:
        try:
            result = await auto_register_image_models(region)
            results[region] = {
                "new": result["new_count"],
                "updated": result["updated_count"],
            }
            total_new += result["new_count"]
            total_updated += result["updated_count"]
        except Exception as exc:
            results[region] = {"error": str(exc)[:100]}
            errors += 1

    # Step 4: Prune — check which models in the registry are still available.
    # After Step 3, each model's available_regions reflects what was discovered.
    # Models with empty available_regions (not found in any region) get disabled.
    registry = get_registry()
    disabled = []
    for key, cfg in list(registry.get("image_models", {}).items()):
        regions = cfg.get("available_regions", [])
        if not regions and cfg.get("enabled"):
            update_image_model(key, {"enabled": False})
            disabled.append(key)
            logger.info("Disabled model %s — no longer found in any region", key)

    return {
        "regions_scanned": len(all_regions),
        "total_new": total_new,
        "total_updated": total_updated,
        "disabled": disabled,
        "errors": errors,
        "per_region": results,
    }


@router.get("/discover/{region}")
async def discover_models(region: str):
    """Discover available foundation models in a Bedrock region.

    Returns deduplicated models grouped by provider and capability.
    Only shows the latest version of each model family.
    """
    try:
        session = boto3.Session()
        bedrock = session.client("bedrock", region_name=region)
        response = bedrock.list_foundation_models()
    except Exception as exc:
        raise HTTPException(502, detail=f"Failed to list models in {region}: {exc}")

    models = []
    for m in response.get("modelSummaries", []):
        model_id = m.get("modelId", "")
        modalities = m.get("outputModalities", [])
        input_modalities = m.get("inputModalities", [])

        models.append({
            "model_id": model_id,
            "model_name": m.get("modelName", ""),
            "provider": m.get("providerName", ""),
            "input_modalities": input_modalities,
            "output_modalities": modalities,
            "is_image_generator": "IMAGE" in modalities and "TEXT" in input_modalities,
            "is_video_generator": "VIDEO" in modalities and "TEXT" in input_modalities,
            "is_text_model": "TEXT" in modalities and "TEXT" in input_modalities,
            "is_image_input": "IMAGE" in input_modalities,
            "customizations": m.get("customizationsSupported", []),
            "streaming": m.get("responseStreamingSupported", False),
        })

    # Group by capability
    image_generators = _deduplicate_models([m for m in models if m["is_image_generator"]])
    video_generators = _deduplicate_models([m for m in models if m["is_video_generator"]])
    text_models = _deduplicate_models([m for m in models if m["is_text_model"] and not m["is_image_generator"] and not m["is_video_generator"]])
    vision_models = _deduplicate_models([m for m in models if m["is_image_input"] and m["is_text_model"]])

    # Deduplicate the full set for the count
    all_deduped = _deduplicate_models(models)

    return {
        "region": region,
        "total_raw": len(models),
        "total_deduplicated": len(all_deduped),
        "image_generators": image_generators,
        "video_generators": video_generators,
        "text_models": text_models,
        "vision_models": vision_models,
    }
