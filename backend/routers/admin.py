"""Admin router — model registry management and Bedrock model discovery."""

import logging

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.model_registry import (
    add_image_model,
    get_registry,
    reload,
    update_category,
    update_image_model,
    update_post_processing,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Registry CRUD ─────────────────────────────────────────────────────────

@router.get("/models")
async def get_models():
    """Return the full model registry."""
    return get_registry()


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
async def get_image_model_options():
    """Return enabled image models for the frontend dropdown.

    This is the source of truth for model selection — the frontend
    should NOT hardcode model lists. Returns models sorted by provider
    then label, with 'All Available Models' as a virtual entry.
    """
    from backend.services.model_registry import get_enabled_image_models
    enabled = get_enabled_image_models()
    models = []
    for key, cfg in sorted(enabled.items(), key=lambda x: (x[1].get("provider", ""), x[1].get("label", x[0]))):
        if cfg.get("model_purpose") != "text_to_image":
            continue  # Only text-to-image models for the generation dropdown
        models.append({
            "key": key,
            "label": cfg.get("label", key),
            "provider": cfg.get("provider", ""),
            "region": cfg.get("region", ""),
            "prompt_limit": cfg.get("prompt_limit", 900),
            "moderation_strictness": cfg.get("moderation_strictness", "moderate"),
            "format_family": cfg.get("format_family", ""),
        })
    return {"models": models}


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
    """Discover image generation models in a region and auto-register new ones.

    Only registers text-to-image models (TEXT input → IMAGE output).
    Maps providers to format families automatically:
    - Amazon → amazon_text_to_image
    - Stability AI → stability_text_to_image

    Already-registered models (by model_id) are skipped.
    Returns the list of newly registered models.
    """
    try:
        session = boto3.Session()
        bedrock = session.client("bedrock", region_name=region)
        response = bedrock.list_foundation_models()
    except Exception as exc:
        raise HTTPException(502, detail=f"Failed to list models in {region}: {exc}")

    from backend.services.model_registry import get_registry, add_image_model, get_image_model

    registry = get_registry()
    existing_model_ids = {
        cfg.get("model_id") for cfg in registry.get("image_models", {}).values()
    }

    # Provider → format family mapping
    _PROVIDER_FAMILY = {
        "Amazon": "amazon_text_to_image",
        "Stability AI": "stability_text_to_image",
    }
    # Default prompt limits by provider
    _PROVIDER_PROMPT_LIMITS = {
        "Amazon": 900,
        "Stability AI": 2000,
    }

    registered = []
    for m in response.get("modelSummaries", []):
        model_id = m.get("modelId", "")
        output = m.get("outputModalities", [])
        inp = m.get("inputModalities", [])
        provider = m.get("providerName", "")

        # Only text-to-image generators
        if "IMAGE" not in output:
            continue
        # Must accept TEXT input (not just IMAGE manipulation)
        if "TEXT" not in inp:
            continue
        # Skip image-manipulation models (require IMAGE input)
        # Pure text-to-image: input is TEXT only, or TEXT+IMAGE but model name suggests generation
        # Heuristic: skip if model name contains editing keywords
        model_name = m.get("modelName", "").lower()
        is_manipulation = any(kw in model_id.lower() for kw in [
            "upscale", "remove-background", "erase", "inpaint",
            "outpaint", "recolor", "replace", "control", "style-transfer",
        ])
        if is_manipulation:
            continue

        # Skip already registered
        if model_id in existing_model_ids:
            continue

        # Determine format family
        family = _PROVIDER_FAMILY.get(provider)
        if not family:
            logger.warning("Unknown provider '%s' for model %s — skipping auto-register", provider, model_id)
            continue

        # Generate a key from model_id: e.g. "stability.sd3-5-large-v1:0" → "sd3_5_large"
        key = model_id.split(".")[-1].split(":")[0].replace("-", "_")
        # Ensure unique key
        if get_image_model(key):
            key = f"{key}_{region.replace('-', '_')}"

        prompt_limit = _PROVIDER_PROMPT_LIMITS.get(provider, 900)
        config = {
            "label": m.get("modelName", model_id),
            "model_id": model_id,
            "region": region,
            "provider": provider,
            "enabled": False,  # Discovered but not enabled by default
            "model_purpose": "text_to_image",
            "format_family": family,
            "prompt_limit": prompt_limit,
            "moderation_strictness": "moderate",
            "extra_body": {},
        }

        add_image_model(key, config)
        registered.append({"key": key, "model_id": model_id, "label": config["label"], "region": region})
        logger.info("Auto-registered image model: %s (%s) in %s", key, model_id, region)

    return {
        "region": region,
        "registered": registered,
        "count": len(registered),
        "message": f"Registered {len(registered)} new model(s)" if registered else "No new models to register",
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
            "is_text_model": "TEXT" in modalities and "TEXT" in input_modalities,
            "is_image_input": "IMAGE" in input_modalities,
            "customizations": m.get("customizationsSupported", []),
            "streaming": m.get("responseStreamingSupported", False),
        })

    # Group by capability
    image_generators = _deduplicate_models([m for m in models if m["is_image_generator"]])
    text_models = _deduplicate_models([m for m in models if m["is_text_model"] and not m["is_image_generator"]])
    vision_models = _deduplicate_models([m for m in models if m["is_image_input"] and m["is_text_model"]])

    # Deduplicate the full set for the count
    all_deduped = _deduplicate_models(models)

    return {
        "region": region,
        "total_raw": len(models),
        "total_deduplicated": len(all_deduped),
        "image_generators": image_generators,
        "text_models": text_models,
        "vision_models": vision_models,
    }
