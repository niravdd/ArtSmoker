"""Admin router — model registry management and Bedrock model discovery."""

import logging

import boto3
from botocore.config import Config as _BotoConfig
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

# Shorter timeouts for discovery — skip unreachable regions quickly
_DISCOVERY_CONFIG = _BotoConfig(connect_timeout=10, read_timeout=15, retries={"max_attempts": 1})

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
    has required top-level keys before saving. With the layered system,
    this writes changes as user overrides (differences from defaults).
    """
    from backend.services.model_registry import get_registry, _save, _load

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, detail="Invalid JSON")

    # Validate BEFORE modifying anything
    required = ["categories", "image_models"]
    missing = [k for k in required if k not in body]
    if missing:
        raise HTTPException(400, detail=f"Missing required keys: {', '.join(missing)}")

    # Replace the in-memory registry and save (writes diff to .user.json)
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
    pinned: bool | None = None


@router.patch("/models/category/{name}")
async def update_model_category(name: str, body: CategoryUpdate):
    """Update a model category (fast_llm, complex_llm, fallback_llm, voice).

    A manual `current` change pins the category (pinned=True) so the AWS-Sync
    auto-roll won't override the user's explicit pick — it will only notify when
    a newer Claude is available. Pass pinned=False explicitly to opt back into
    auto-roll.
    """
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail="No updates provided")
    # Explicitly choosing a model = pinning it (unless the caller says otherwise).
    if "current" in updates and "pinned" not in updates:
        updates["pinned"] = True
    result = update_category(name, updates, user_pref=True)
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
    result = update_image_model(key, updates, user_pref=True)
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
    result = update_video_model(key, updates, user_pref=True)
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
    result = update_post_processing(key, updates, user_pref=True)
    logger.info("Updated post-processing '%s': %s", key, updates)
    return result


@router.post("/models/reload")
async def reload_registry():
    """Reload the model registry from disk."""
    reload()
    from backend.services.model_registry import get_registry
    reg = get_registry()
    image_count = len(reg.get("image_models", {}))
    chat_count = len(reg.get("chat_models", {}))
    logger.info("Model registry reloaded: %d image models, %d chat models", image_count, chat_count)
    return {"status": "reloaded", "image_models": image_count, "chat_models": chat_count}


@router.post("/models/promote")
async def promote_registry():
    """Promote discovered data from user registry to git-tracked base.

    Copies model definitions, regions, pricing to model_registry.json.
    Rewrites model_registry.user.json to contain only user-specific
    overrides (enabled/disabled, deployment config, video settings).
    Run after Sync to make discoveries available to all users via git push.
    """
    from backend.services.model_registry import promote_to_base
    result = promote_to_base()
    return {"status": "promoted", **result}


# ── Prompt Templates ──────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates():
    """Return all editable prompt templates with metadata."""
    from backend.services.prompt_templates import get_all_templates
    return {"templates": get_all_templates()}


class TemplateUpdate(BaseModel):
    text: str
    fix_variables: bool = False  # If true, use LLM to fix missing variables before saving


@router.patch("/templates/{name}")
async def update_template_endpoint(name: str, body: TemplateUpdate):
    """Update a prompt template's text. Validates required variables.

    If variables are missing and fix_variables=True, uses an LLM to intelligently
    insert them in the right places. Otherwise returns 400 with details.
    """
    from backend.services.prompt_templates import update_template, validate_template, get_all_templates

    # Check if template exists
    templates = get_all_templates()
    if name not in templates:
        raise HTTPException(404, detail=f"Unknown template: {name}")

    # Validate variables first
    missing = validate_template(name, body.text)

    if missing and body.fix_variables:
        # Use LLM to fix the template — insert missing variables in the right places
        from backend.services.bedrock_client import invoke_llm
        tmpl = templates[name]
        var_descriptions = ", ".join(missing)

        try:
            from backend.services.prompt_templates import get_system_prompt
            fixed = invoke_llm(
                prompt=get_template('admin_template_fix_variables').format(
                    missing_variables=var_descriptions,
                    template_text=body.text,
                ),
                system=get_system_prompt('admin_template_fix_variables'),
                max_tokens=4000,
                temperature=0.1,
                complexity="fast",
            ).strip()

            # Verify the fix actually has the variables
            still_missing = validate_template(name, fixed)
            if still_missing:
                raise HTTPException(400, detail=f"LLM fix attempted but variables still missing: {', '.join(still_missing)}. Please add them manually: {', '.join(missing)}")

            # Save the fixed version
            result = update_template(name, fixed, force=True)
            result["auto_fixed"] = True
            result["fixed_variables"] = missing
            return result

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(502, detail=f"Auto-fix failed: {exc}. Please add manually: {', '.join(missing)}")

    elif missing:
        raise HTTPException(400, detail={
            "message": f"Required variables missing: {', '.join(missing)}",
            "missing_variables": missing,
            "hint": "These variables are substituted at runtime. Removing them breaks the feature. Click 'Fix & Save' to auto-insert them.",
        })

    # No missing variables — save directly
    try:
        result = update_template(name, body.text, force=True)
        return result
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))


@router.post("/templates/{name}/reset")
async def reset_template_endpoint(name: str):
    """Reset a prompt template to its default."""
    from backend.services.prompt_templates import reset_template
    try:
        result = reset_template(name)
        return result
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))


@router.post("/templates/reset-all")
async def reset_all_templates_endpoint():
    """Reset all prompt templates to defaults."""
    from backend.services.prompt_templates import reset_all_templates
    reset_all_templates()
    return {"status": "all templates reset to defaults"}


class TemplateEnhanceRequest(BaseModel):
    model_id: str
    region: str | None = None
    instructions: str = ""  # Optional user instructions for how to improve


@router.post("/templates/{name}/enhance")
async def enhance_template(name: str, body: TemplateEnhanceRequest):
    """Use an LLM to refine/improve a prompt template.

    Sends the current template text + its metadata to the chosen model,
    asking it to improve the directive while preserving all variables.
    Returns the suggested improved text for the user to review.
    """
    from backend.services.prompt_templates import get_all_templates
    from backend.services.bedrock_client import invoke_llm
    from backend.services.cost_tracker import reset_costs
    reset_costs()

    templates = get_all_templates()
    if name not in templates:
        raise HTTPException(404, detail=f"Unknown template: {name}")

    tmpl = templates[name]
    current_text = tmpl["text"]
    variables = tmpl.get("variables", [])
    var_list = ", ".join(variables) if variables else "none"

    user_instructions = ""
    if body.instructions:
        user_instructions = f"\nThe user specifically requests: {body.instructions}"

    enhance_prompt = get_template('admin_template_enhance').format(
        template_label=tmpl['label'],
        template_description=tmpl['description'],
        template_used_by=tmpl['used_by'],
        variable_list=var_list,
        user_instructions=user_instructions,
        current_text=current_text,
    )

    try:
        improved = invoke_llm(
            enhance_prompt,
            model_id=body.model_id,
            region_override=body.region or "us-west-2",
            max_tokens=4000,
            temperature=0.3,
        ).strip()

        # Verify all variables are preserved
        missing_vars = []
        for var in variables:
            if var.startswith("{") and var.endswith("}"):
                var_name = var.strip("{}")
                if "{" + var_name + "}" not in improved:
                    missing_vars.append(var)

        return {
            "original": current_text,
            "improved": improved,
            "model_id": body.model_id,
            "missing_variables": missing_vars,
            "warning": f"Variables missing in improved text: {missing_vars}" if missing_vars else None,
        }
    except Exception as exc:
        raise HTTPException(502, detail=f"Enhancement failed: {exc}")


@router.get("/models/image-options")
def get_image_model_options(region: str | None = Query(default=None)):
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
    for key, cfg in enabled.items():
        if cfg.get("model_purpose") != "text_to_image":
            continue  # Only text-to-image models for the generation dropdown

        # Custom-hosted models: show if endpoint exists and model has been
        # validated at least once (model_ready in registry). This covers:
        #   - Scaled to zero: listed (async jobs queue in SageMaker backlog)
        #   - Scaling out: listed (jobs already queuing)
        #   - First deploy, never loaded: hidden until first successful load
        #   - Teardown/redeploy: hidden (model_ready cleared)
        if cfg.get("model_source") == "custom_hosted":
            try:
                from backend.services.sagemaker_deployer import check_endpoint_status
                ep_name = cfg.get("deployment", {}).get("endpoint_name", "")
                if not ep_name:
                    continue
                ep_status = check_endpoint_status(ep_name)
                if ep_status.get("status") not in ("InService", "Updating"):
                    continue  # Not deployed or failed
                model_ready_ever = cfg.get("deployment", {}).get("model_ready", False)
                if not model_ready_ever and ep_status.get("warming_up"):
                    continue  # First deploy, never validated — hide until loaded
            except Exception:
                continue

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
            "model_source": cfg.get("model_source", "foundation"),
            "supported_sizes": cfg.get("invoke", {}).get("supported_sizes"),
            "_last_updated": cfg.get("last_updated", cfg.get("invoke", {}).get("last_updated", "")),
        })

    # Sort: provider ascending, then newest model first within each provider.
    # Models with last_updated sort by date descending (FLUX.2 > FLUX.1).
    # Models without last_updated sort by label descending (Nova Canvas > Titan Image,
    # SD 3.5 > SDXL Turbo) — version numbers in labels naturally order correctly.
    def _model_sort_key(m):
        provider = m["provider"]
        date = m.pop("_last_updated", "") or ""
        if date:
            # Negate date digits for descending: "2025-06-01" → "7974-93-98"
            neg_date = "".join(chr(ord('9') - ord(c)) if c.isdigit() else c for c in date)
        else:
            # No date → sort before dated models (assumed current/recent)
            neg_date = ""
        # Negate label for descending: complement ASCII so "Z" < "A" in sort
        neg_label = "".join(chr(255 - ord(c)) if c.isascii() else c for c in m["label"])
        return (provider, neg_date, neg_label)
    models.sort(key=_model_sort_key)

    # Collect all regions that have at least one model
    all_regions = sorted(set(
        r for m in models for r in m.get("available_regions", [])
    ))

    return {"models": models, "available_regions": all_regions}


@router.get("/models/video-options")
def get_video_model_options():
    """Return enabled video models for the Video Studio dropdown."""
    from backend.services.model_registry import get_enabled_video_models, get_registry
    enabled = get_enabled_video_models()
    registry = get_registry()

    models = []
    for key, cfg in sorted(enabled.items(), key=lambda x: (x[1].get("provider", ""), x[1].get("label", x[0]))):
        # Custom-hosted models: show if validated at least once (model_ready).
        # Hide only during first deploy (never loaded) or if endpoint is gone.
        if cfg.get("model_source") == "custom_hosted":
            try:
                from backend.services.sagemaker_deployer import check_endpoint_status
                ep_name = cfg.get("deployment", {}).get("endpoint_name", "")
                if not ep_name:
                    continue
                ep_status = check_endpoint_status(ep_name)
                if ep_status.get("status") not in ("InService", "Updating"):
                    continue
                model_ready_ever = cfg.get("deployment", {}).get("model_ready", False)
                if not model_ready_ever and ep_status.get("warming_up"):
                    continue
            except Exception:
                continue

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
            try:
                from backend.services.cost_tracker import add_s3_cost
                add_s3_cost("put", 24, "S3 access validation test")
            except Exception:
                pass
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


def _normalize_model_id(model_id: str) -> str:
    """Bare, comparable form of a model id for cross-endpoint matching.

    Strips the ``us.`` inference-profile prefix and any trailing throughput /
    context / version qualifiers (``:0``, ``:200k``, ``-v1:0``) so the SAME
    model discovered via different endpoints/listings collapses to one identity.
    Examples:
      ``us.anthropic.claude-sonnet-4-6``            -> ``anthropic.claude-sonnet-4-6``
      ``openai.gpt-oss-120b-1:0``                   -> ``openai.gpt-oss-120b``
      ``anthropic.claude-3-sonnet-20240229-v1:0:200k`` -> ``anthropic.claude-3-sonnet-20240229``
    """
    mid = (model_id or "")
    if mid.startswith("us."):
        mid = mid[3:]
    mid = mid.split(":")[0]                       # drop :throughput / :context
    mid = _re.sub(r"-v\d+$", "", mid)             # drop trailing -vN
    # Drop a trailing throughput-variant "-N" ONLY when it directly follows a
    # parameter-size token like "120b"/"20b"/"7b" (e.g. "gpt-oss-120b-1" ->
    # "gpt-oss-120b"). This must NOT touch version minors ("claude-sonnet-4-6")
    # or date stamps ("claude-3-sonnet-20240229").
    mid = _re.sub(r"(\d+b)-\d+$", r"\1", mid)
    return mid


def _chat_model_key(model_id: str) -> str:
    """Stable, readable registry key for a chat model.

    Drops only the leading provider segment (NOT split on every dot — model ids
    embed dots in version numbers, e.g. ``zai.glm-4.7`` whose naive
    ``split('.')[-1]`` would yield the bare fragment ``7``), strips a ``:``
    qualifier, then sanitizes to ``[a-z0-9_]``. ``zai.glm-4.7`` -> ``glm_4_7``;
    ``us.anthropic.claude-opus-4-8`` -> ``claude_opus_4_8``.
    """
    mid = (model_id or "")
    if mid.startswith("us."):
        mid = mid[3:]
    body = mid.split(":")[0]
    if "." in body:
        body = body.split(".", 1)[1]              # strip provider prefix only
    return body.replace(".", "_").replace("-", "_").replace("/", "_")


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

    # Claude: keep major.minor (opus-4-5, opus-4-6, opus-4-7 are distinct models).
    # Only group patch versions: opus-4-6-v1 and opus-4-6-v2 → opus-4-6
    key = _re.sub(r'(claude-(?:opus|sonnet|haiku)-\d+-\d+)-\d+', r'\1', key)

    # Llama: group context variants (llama3-1-70b, llama3-2-90b keep as-is, but strip -instruct)
    key = _re.sub(r'-instruct$', '', key)

    # Nova: strip throughput variants
    key = _re.sub(r'(nova-\w+)-\d+k$', r'\1', key)

    return key


def _deduplicate_models(models: list[dict]) -> list[dict]:
    """Keep only the latest version per model family per provider.

    Groups by provider + family key, keeps the newest (ACTIVE > LEGACY,
    then by model name alphabetically for tie-breaking).
    """
    families: dict[str, dict] = {}
    for m in models:
        key = f"{m['provider']}::{_model_family_key(m['model_id'])}"
        existing = families.get(key)
        if not existing:
            families[key] = m
        else:
            # Keep newest: ACTIVE > LEGACY, then by name (newer versions sort higher)
            new_lifecycle = m.get('lifecycle', 'ACTIVE')
            old_lifecycle = existing.get('lifecycle', 'ACTIVE')
            if (new_lifecycle == 'ACTIVE' and old_lifecycle == 'LEGACY') or \
               (new_lifecycle == old_lifecycle and m.get('label', '') > existing.get('label', '')):
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
        bedrock = boto3.Session().client("bedrock", region_name=region, config=_DISCOVERY_CONFIG)
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
        """Determine model_purpose, format_family, prompt_limit, base_price, optimal_prompt_words from model_id and provider."""
        mid = model_id.lower()
        has_image_input = "IMAGE" in input_modalities

        # Stability AI services — classify by model ID keywords
        if provider == "Stability AI":
            if "inpaint" in mid:
                return "inpainting", "stability_inpaint", 10000, 0.07, 0
            if "outpaint" in mid:
                return "outpainting", "stability_outpaint", 10000, 0.06, 0
            if "erase" in mid:
                return "erase", "stability_erase", 0, 0.07, 0
            if "search-replace" in mid or "search_replace" in mid:
                return "search_replace", "stability_search_replace", 10000, 0.07, 0
            if "search-recolor" in mid or "recolor" in mid:
                return "search_recolor", "stability_search_recolor", 10000, 0.07, 0
            if "control-sketch" in mid:
                return "control_sketch", "stability_control", 10000, 0.07, 0
            if "control-structure" in mid:
                return "control_structure", "stability_control", 10000, 0.07, 0
            if "style-guide" in mid:
                return "style_guide", "stability_control", 10000, 0.07, 0
            if "style-transfer" in mid:
                return "style_transfer", "stability_style_transfer", 10000, 0.08, 0
            if "remove-background" in mid:
                return "remove_background", "stability_remove_bg", 0, 0.07, 0
            if "creative-upscale" in mid:
                return "upscale_creative", "stability_upscale", 10000, 0.60, 0
            if "conservative-upscale" in mid:
                return "upscale_conservative", "stability_upscale", 10000, 0.40, 0
            if "fast-upscale" in mid:
                return "upscale_fast", "stability_upscale", 0, 0.03, 0
            # Default: text-to-image (SD 3.5, Stable Image Ultra/Core)
            opw = 120 if "sd3" in mid or "3.5" in mid else 100
            return "text_to_image", "stability_text_to_image", 2000, 0.08, opw

        # Amazon models (Nova Canvas, Titan Image)
        if provider == "Amazon":
            opw = 40 if "titan" in mid else 80
            return "text_to_image", "amazon_text_to_image", 900, 0.06, opw

        return "text_to_image", None, 900, None, 80

    def _classify_video_model(model_id: str, provider: str, input_modalities: list[str]):
        """Determine format_family, pricing, and optimal_prompt_words for video models."""
        mid = model_id.lower()
        has_image_input = "IMAGE" in input_modalities
        if "nova-reel" in mid:
            return "text_to_video", "nova_reel", 512, 0.08, has_image_input, 50
        if "ray" in mid or "luma" in mid:
            return "text_to_video", "luma_ray", 5000, 1.50, has_image_input, 60
        return "text_to_video", None, 512, None, has_image_input, 50

    def _register_chat_model(m: dict, region: str, registry: dict, registered: list):
        """Register a text LLM into the chat_models registry section."""
        model_id = m.get("modelId", "")
        provider = m.get("providerName", "")
        inp = m.get("inputModalities", [])
        inference_types = m.get("inferenceTypesSupported", [])

        effective_id = model_id
        if "INFERENCE_PROFILE" in inference_types and not model_id.startswith("us."):
            effective_id = f"us.{model_id}"

        chat_models = registry.setdefault("chat_models", {})

        # Key: provider-stripped, version-safe (dotted-version ids like
        # zai.glm-4.7 must NOT collapse to a bare "7" — see _chat_model_key).
        key = _chat_model_key(model_id)
        family_key = _model_family_key(model_id)

        # Check if a model from this family is already registered
        existing_key = None
        for k, cfg in chat_models.items():
            if _model_family_key(cfg.get("model_id", "").replace("us.", "")) == family_key:
                existing_key = k
                break

        if existing_key:
            # Update regions
            existing = chat_models[existing_key]
            regions = existing.get("available_regions", [])
            if region not in regions:
                regions.append(region)
                regions.sort()
                existing["available_regions"] = regions

            # Keep the NEWEST model version in the family.
            # Compare by lifecycle (ACTIVE > LEGACY) then by model name/id.
            existing_lifecycle = existing.get("lifecycle", "ACTIVE")
            new_lifecycle = m.get("modelLifecycle", {}).get("status", "ACTIVE")
            new_name = m.get("modelName", "")
            existing_name = existing.get("label", "")

            is_newer = (
                (new_lifecycle == "ACTIVE" and existing_lifecycle == "LEGACY") or
                (new_lifecycle == existing_lifecycle and new_name > existing_name)
            )
            if is_newer:
                existing["model_id"] = effective_id
                existing["model_arn"] = m.get("modelArn", "")
                existing["label"] = new_name
                existing["lifecycle"] = new_lifecycle
                existing["inference_types"] = inference_types
                # Keep the existing key — renaming causes conflicts between
                # base and user registry files on reload.
            return

        has_vision = "IMAGE" in inp
        streaming = m.get("responseStreamingSupported", False)

        # Endpoint/API capability: this model came from the
        # bedrock-runtime listing, so it's runtime-reachable. Mantle-also and
        # mantle-only models are reconciled in a later pass (_reconcile_mantle_models).
        from backend.services.mantle_client import derive_model_apis, resolve_invoke_path
        apis = derive_model_apis(effective_id, provider, on_mantle=False, on_runtime=True)
        invoke_endpoint, invoke_api = resolve_invoke_path(apis)

        chat_models[key] = {
            "label": m.get("modelName", model_id),
            "model_id": effective_id,
            "region": region,
            "available_regions": [region],
            "provider": provider,
            "enabled": True,
            "model_source": "foundation",
            "model_arn": m.get("modelArn", ""),
            "has_vision": has_vision,
            "streaming_supported": streaming,
            "max_context_tokens": 128000,  # Default — admin can override per model
            "customizations_supported": m.get("customizationsSupported", []),
            "inference_types": inference_types,
            "lifecycle": m.get("modelLifecycle", {}).get("status", "ACTIVE"),
            "endpoints": ["bedrock-runtime"],
            "apis": apis,
            "invoke_endpoint": invoke_endpoint,
            "invoke_api": invoke_api,
        }
        registered.append({"key": key, "model_id": model_id, "label": chat_models[key]["label"],
                          "region": region, "purpose": "chat", "media": "text"})

    registered = []
    updated = []

    for m in response.get("modelSummaries", []):
        model_id = m.get("modelId", "")
        output = m.get("outputModalities", [])
        inp = m.get("inputModalities", [])
        provider = m.get("providerName", "")

        is_image = "IMAGE" in output
        is_video = "VIDEO" in output
        is_text = "TEXT" in output and "TEXT" in inp

        # ── Text/LLM models → chat_models registry ───────────────────
        if is_text and not is_image and not is_video:
            _register_chat_model(m, region, registry, registered)
            continue

        # Must produce images or video for the sections below
        if not is_image and not is_video:
            continue

        # ── Video models ─────────────────────────────────────────────
        if is_video:
            purpose, family, prompt_limit, base_price, has_img_input, video_opw = _classify_video_model(model_id, provider, inp)
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
                "model_source": "foundation",
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
                "optimal_prompt_words": video_opw,
            }
            add_video_model(key, config)
            existing_video_by_model_id.setdefault(model_id, []).append(key)
            registered.append({"key": key, "model_id": model_id, "label": config["label"],
                              "region": region, "purpose": purpose, "media": "video"})
            logger.info("Auto-registered video: %s (%s) in %s", key, model_id, region)
            continue

        # ── Image models ─────────────────────────────────────────────
        # Classify the model
        purpose, family, prompt_limit, base_price, optimal_words = _classify_image_model(model_id, provider, inp)
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
                if not existing_cfg.get("optimal_prompt_words") and optimal_words:
                    backfill["optimal_prompt_words"] = optimal_words

                regions = existing_cfg.get("available_regions", [existing_cfg.get("region", "")])
                if region not in regions:
                    regions.append(region)
                    regions.sort()
                    backfill["available_regions"] = regions
                    updated.append({"key": existing_key, "model_id": model_id, "added_region": region})
                    logger.debug("Updated %s: added region %s (now %s)", existing_key, region, regions)

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
            "model_source": "foundation",
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
        if optimal_words:
            config["optimal_prompt_words"] = optimal_words

        add_image_model(key, config)
        existing_by_model_id.setdefault(model_id, []).append(key)
        existing_by_model_id.setdefault(effective_model_id, []).append(key)
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

        logger.debug("Fetched %d image pricing entries from AWS Pricing API", len(prices))
        return prices
    except Exception as exc:
        logger.warning("Failed to fetch pricing data: %s", exc)
        return {}


def _fetch_sagemaker_pricing(regions: list[str] | None = None) -> dict:
    """Fetch per-region SageMaker real-time HOSTING instance pricing from the AWS
    Pricing API (ServiceCode=AmazonSageMaker).

    All custom-model + 3D compute-cost math is (instance $/hr × duration), so the
    hourly rate must be live and per-region — SageMaker instances cost more in
    some regions. This queries the Pricing API (only available in us-east-1) for
    the 'Hosting' product family (real-time inference endpoints), for the ml.*
    GPU families we deploy on, across the given regions.

    Returns { "ml.g6e.xlarge|us-west-2": 2.61, ... } (instance|region → USD/hour).
    Empty dict on failure (callers fall back to catalog seed rates). Filtered to
    the instance families ArtSmoker deploys (g5/g6/g6e/g7e/p4/p5) to keep the
    scan small; extend the prefix list if new families are added to the catalog.
    """
    try:
        import json as _json
        client = boto3.Session().client("pricing", region_name="us-east-1")
        # Region code → the Pricing API 'regionCode' attribute equals the region id.
        target_regions = set(regions or [])
        # GPU families ArtSmoker deploys on (real-time inference). Extend if the
        # catalog adds new families.
        want_prefixes = ("ml.g5", "ml.g6", "ml.g6e", "ml.g7e", "ml.p4", "ml.p5", "ml.p6")
        rates: dict = {}
        # component=Hosting isolates real-time INFERENCE endpoints (skips Studio,
        # Training, Batch, Notebook) — verified as a valid Pricing API filter field.
        base_filters = [
            {"Type": "TERM_MATCH", "Field": "component", "Value": "Hosting"},
        ]
        next_token = None
        pages = 0
        while pages < 80:  # safety bound (hosting SKUs across all regions/instances)
            pages += 1
            kwargs = {"ServiceCode": "AmazonSageMaker", "Filters": base_filters, "MaxResults": 100}
            if next_token:
                kwargs["NextToken"] = next_token
            resp = client.get_products(**kwargs)
            for p in resp.get("PriceList", []):
                pd = _json.loads(p)
                attrs = pd.get("product", {}).get("attributes", {})
                inst = attrs.get("instanceName", "") or attrs.get("instanceType", "")
                region = attrs.get("regionCode", "")
                if not inst or not region:
                    continue
                if target_regions and region not in target_regions:
                    continue
                if not any(inst.startswith(pfx) for pfx in want_prefixes):
                    continue
                for terms in pd.get("terms", {}).get("OnDemand", {}).values():
                    for dim in terms.get("priceDimensions", {}).values():
                        if dim.get("unit", "").lower() != "hrs":
                            continue
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0") or 0)
                        if price > 0:
                            rates[f"{inst}|{region}"] = round(price, 4)
            next_token = resp.get("NextToken")
            if not next_token:
                break
        logger.info("Fetched %d SageMaker instance-region pricing entries from AWS Pricing API", len(rates))
        return rates
    except Exception as exc:
        logger.warning("Failed to fetch SageMaker pricing: %s", exc)
        return {}


def _fetch_llm_pricing() -> dict:
    """Fetch per-model, per-region LLM TOKEN pricing from the AWS Pricing API.

    LLM cost = (input_tokens × input_price) + (output_tokens × output_price), so
    the per-token price must be live and per-model — previously it fell back to a
    stale hardcoded 3-entry dict, defaulting unknown models to Sonnet pricing.
    Scans AmazonBedrock products for token-priced rows (unit '1K tokens' /
    '1M tokens') and splits input vs output by the usagetype ('-input-tokens' /
    '-output-tokens'). Normalizes everything to USD per 1K tokens.

    Returns { "<model>|<region>": {"input_per_1k": x, "output_per_1k": y}, ... }.
    Empty on failure (callers keep the static seed). Pricing API is us-east-1 only.
    """
    try:
        import json as _json
        client = boto3.Session().client("pricing", region_name="us-east-1")
        prices: dict = {}
        next_token, pages = None, 0
        while pages < 120:  # bound the scan (token SKUs across all models/regions)
            pages += 1
            kwargs = {"ServiceCode": "AmazonBedrock", "MaxResults": 100}
            if next_token:
                kwargs["NextToken"] = next_token
            resp = client.get_products(**kwargs)
            for p in resp.get("PriceList", []):
                pd = _json.loads(p)
                attrs = pd.get("product", {}).get("attributes", {})
                model_name = attrs.get("model", "")
                region = attrs.get("regionCode", "")
                usage = (attrs.get("usagetype", "") or "").lower()
                if not model_name or not region:
                    continue
                # Only token-priced input/output rows (skip images, throughput, etc.).
                is_input = "input-tokens" in usage or "input_tokens" in usage
                is_output = "output-tokens" in usage or "output_tokens" in usage
                if not (is_input or is_output):
                    continue
                for terms in pd.get("terms", {}).get("OnDemand", {}).values():
                    for dim in terms.get("priceDimensions", {}).values():
                        unit = dim.get("unit", "")
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0") or 0)
                        if price <= 0 or unit not in ("1K tokens", "1M tokens"):
                            continue
                        per_1k = price if unit == "1K tokens" else price / 1000.0
                        key = f"{model_name}|{region}"
                        entry = prices.setdefault(key, {})
                        # Prefer the standard (non-priority/batch/cache) tier: keep the
                        # LOWEST price seen per direction (batch/cache < priority).
                        fld = "input_per_1k" if is_input else "output_per_1k"
                        if fld not in entry or per_1k < entry[fld]:
                            entry[fld] = round(per_1k, 8)
            next_token = resp.get("NextToken")
            if not next_token:
                break
        logger.info("Fetched LLM token pricing for %d model-region combos from AWS Pricing API", len(prices))
        return prices
    except Exception as exc:
        logger.warning("Failed to fetch LLM pricing: %s", exc)
        return {}


def _apply_llm_pricing(registry: dict, llm_pricing: dict) -> int:
    """Stamp fetched token prices onto chat_models entries (Option A — per-model,
    reusing input_price_per_1k/output_price_per_1k that compute_llm_cost reads).

    Matches each chat_models entry to a fetched '<model>|<region>' price by trying
    the model's available regions, then any region for that model name. The AWS
    Pricing API 'model' attribute is a display name (e.g. 'Claude 3 Sonnet'), so we
    match loosely against the registry's name/model_id (case/space/punct-insensitive
    token overlap). Unmatched models are left unpriced (fall back to the seed).
    Returns the count of entries priced."""
    if not llm_pricing:
        return 0

    def _norm(s):
        import re
        return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

    # Index fetched prices by normalized model name → {region: {in,out}}.
    by_name: dict = {}
    for key, px in llm_pricing.items():
        name, _, region = key.partition("|")
        by_name.setdefault(_norm(name), {})[region] = px

    priced = 0
    for cm in (registry.get("chat_models", {}) or {}).values():
        label = cm.get("name") or cm.get("model_label") or ""
        mid = cm.get("model_id") or ""
        cand_norms = {_norm(label), _norm(mid.split(".")[-1].split(":")[0].replace("-", " "))}
        regions = cm.get("available_regions") or ([cm.get("region")] if cm.get("region") else [])
        match = None
        for pname, byreg in by_name.items():
            if not pname:
                continue
            # Token-overlap match: every word of the shorter name appears in the other.
            a, b = set(pname.split()), None
            for cn in cand_norms:
                if not cn:
                    continue
                b = set(cn.split())
                short, long = (a, b) if len(a) <= len(b) else (b, a)
                if short and short.issubset(long):
                    # Pick the price for a region the model is in, else any region.
                    px = next((byreg[r] for r in regions if r in byreg), None) or next(iter(byreg.values()), None)
                    if px:
                        match = px
                        break
            if match:
                break
        if match and (match.get("input_per_1k") or match.get("output_per_1k")):
            cm["input_price_per_1k"] = match.get("input_per_1k", 0)
            cm["output_price_per_1k"] = match.get("output_per_1k", 0)
            priced += 1
    return priced


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


def _account_enabled_regions() -> set[str] | None:
    """Regions ENABLED for this AWS account, via the Account API.

    Returns a set of region names, or None if we couldn't determine it (e.g.
    the role lacks `account:ListRegions`). Callers fall back to scan-all on None.
    Not-enabled regions otherwise fail mid-scan with `UnrecognizedClientException`
    (403) or hang on connect timeouts — filtering them up front makes Sync fast
    and quiet.
    """
    try:
        acct = boto3.client("account", config=_DISCOVERY_CONFIG)
        enabled: set[str] = set()
        paginator = acct.get_paginator("list_regions")
        for page in paginator.paginate(
            RegionOptStatusContains=["ENABLED", "ENABLED_BY_DEFAULT"]
        ):
            for r in page.get("Regions", []):
                name = r.get("RegionName")
                if name:
                    enabled.add(name)
        return enabled or None
    except Exception as exc:
        logger.info("account:ListRegions unavailable (%s) — Sync will scan all regions",
                    type(exc).__name__)
        return None


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


def _claude_version_tuple(model_id: str) -> tuple:
    """Parse a sortable version key from a Claude model_id.

    Returns (major, minor, date) so newer models sort higher. Examples:
      us.anthropic.claude-sonnet-4-6     → (4, 6, 0)
      us.anthropic.claude-opus-4-6-v1    → (4, 6, 0)  (patch -vN ignored for line)
      anthropic.claude-3-5-sonnet-20241022-v2:0 → (3, 5, 20241022)
    Unparseable IDs sort lowest. Used to find the newest Sonnet/Opus on Sync.
    """
    mid = model_id.lower()
    major = minor = date = 0
    # Minor is 1-3 digits — never an 8-digit date (claude-sonnet-4-20250514 form).
    m = _re.search(r'claude-(?:opus|sonnet|haiku)-(\d+)-(\d{1,3})(?!\d)', mid)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
    else:
        m = _re.search(r'claude-(\d+)-(\d{1,3})(?!\d)', mid)  # older claude-3-5-... form
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
    dm = _re.search(r'-(\d{8})(?:-|$|:)', mid)
    if dm:
        date = int(dm.group(1))
    return (major, minor, date)


def _reconcile_mantle_models(registry: dict) -> int:
    """Reconcile the bedrock-mantle catalog into chat_models.

    The bedrock-runtime ListFoundationModels scan (done per-region above) does
    NOT surface Mantle-only models (OpenAI GPT-5.x, Claude Mythos, …). This pass
    queries the Mantle ``models.list`` and:
      • marks discovered runtime models that are ALSO on Mantle (adds
        "bedrock-mantle" to their ``endpoints`` and the Mantle APIs to ``apis``),
      • adds Mantle-only models as new chat_models entries (endpoints=[mantle]).
    Every entry's ``invoke_endpoint``/``invoke_api`` is (re)resolved Converse-first.
    No-op (returns 0) if Mantle is unavailable (deps/token absent) — purely
    additive, never disturbs the runtime catalog. User overrides in .user.json
    win on reload as usual.
    """
    from backend.services.mantle_client import (
        mantle_available, list_mantle_models, derive_model_apis,
        resolve_invoke_path, mantle_region_for,
    )
    from backend.services.model_registry import get_registry

    if not mantle_available():
        logger.info("Mantle unavailable (no SDK/token) — skipping Mantle reconciliation")
        return 0

    region = mantle_region_for(None)
    mantle_ids = list_mantle_models(region)
    if not mantle_ids:
        return 0

    chat_models = registry.setdefault("chat_models", {})

    # Index existing entries by their bare model_id (strip us. profile prefix)
    # so we can match Mantle IDs (which are bare, e.g. "openai.gpt-5.4") against
    # our stored IDs (which may be "us.anthropic.…").
    # Match Mantle ids against stored ids by their NORMALIZED form (strip us.
    # prefix + throughput/version qualifiers), so e.g. the runtime entry for
    # ``openai.gpt-oss-120b-1:0`` merges with the Mantle id ``openai.gpt-oss-120b``
    # instead of creating a duplicate.
    by_norm: dict[str, str] = {}
    for k, cfg in chat_models.items():
        by_norm[_normalize_model_id(cfg.get("model_id", ""))] = k

    def _provider_from_id(mid: str) -> str:
        head = mid.split(".")[0].lower()
        return {"openai": "OpenAI", "anthropic": "Anthropic", "meta": "Meta",
                "mistral": "Mistral AI", "deepseek": "DeepSeek", "qwen": "Qwen",
                "zai": "Z.AI", "google": "Google", "nvidia": "NVIDIA",
                "amazon": "Amazon", "ai21": "AI21 Labs", "cohere": "Cohere",
                "writer": "Writer", "minimax": "MiniMax", "moonshot": "Moonshot AI",
                "twelvelabs": "TwelveLabs", "xai": "xAI"}.get(head, head.title())

    # Drop date-suffixed aliases (e.g. "openai.gpt-5.4-2026-03-05") when the
    # undated base ("openai.gpt-5.4") is also listed — they're the same model.
    import re as _re2
    _id_set = set(mantle_ids)
    def _is_dupe_dated_alias(mid: str) -> bool:
        base = _re2.sub(r"-\d{4}-\d{2}-\d{2}$", "", mid)
        return base != mid and base in _id_set

    reconciled = 0
    for mid in mantle_ids:
        if _is_dupe_dated_alias(mid):
            continue
        existing_key = by_norm.get(_normalize_model_id(mid))
        if existing_key:
            cfg = chat_models[existing_key]
            provider = cfg.get("provider", "")
            eps = set(cfg.get("endpoints") or ["bedrock-runtime"])
            eps.add("bedrock-mantle")
            cfg["endpoints"] = sorted(eps)
            on_runtime = "bedrock-runtime" in eps
            cfg["apis"] = derive_model_apis(cfg.get("model_id", mid), provider,
                                            on_mantle=True, on_runtime=on_runtime)
            cfg["invoke_endpoint"], cfg["invoke_api"] = resolve_invoke_path(cfg["apis"])
            reconciled += 1
        else:
            # Mantle-only model — add a fresh entry (shared keymaker; version-safe).
            provider = _provider_from_id(mid)
            key = _chat_model_key(mid)
            if key in chat_models:
                key = mid.replace(".", "_").replace("-", "_").replace(":", "_").replace("/", "_")
            by_norm[_normalize_model_id(mid)] = key  # so dated aliases/dupes match this
            apis = derive_model_apis(mid, provider, on_mantle=True, on_runtime=False)
            inv_ep, inv_api = resolve_invoke_path(apis)
            chat_models[key] = {
                "label": mid,
                "model_id": mid,
                "region": region,
                "available_regions": [region],
                "provider": provider,
                "enabled": True,
                "model_source": "foundation",
                "model_arn": "",
                "has_vision": False,
                "streaming_supported": True,
                "max_context_tokens": 128000,
                "customizations_supported": [],
                "inference_types": [],
                "lifecycle": "ACTIVE",
                "endpoints": ["bedrock-mantle"],
                "apis": apis,
                "invoke_endpoint": inv_ep,
                "invoke_api": inv_api,
            }
            reconciled += 1
    logger.info("Mantle reconciliation: %d model(s) (of %d listed)", reconciled, len(mantle_ids))
    return reconciled


def _stamp_all_chat_model_routing(registry: dict) -> int:
    """Ensure EVERY chat_models entry carries endpoint/API routing fields.

    The per-model stamping in _register_chat_model only fires for newly-created
    entries; pre-existing models and the update-existing branch never got
    `endpoints`/`apis`/`invoke_endpoint`/`invoke_api`. This backfills any entry
    missing them (runtime-reachable unless Mantle reconciliation already marked
    it otherwise), so routing is explicit for all models — not relying on the
    invoke-time Converse default. Idempotent. Returns count stamped.
    """
    from backend.services.mantle_client import derive_model_apis, resolve_invoke_path
    cm = registry.get("chat_models", {})
    stamped = 0
    for cfg in cm.values():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("invoke_endpoint") and cfg.get("invoke_api") and cfg.get("apis"):
            continue  # already stamped (e.g. by Mantle reconciliation)
        eps = cfg.get("endpoints") or ["bedrock-runtime"]
        cfg["endpoints"] = eps
        apis = derive_model_apis(
            cfg.get("model_id", ""), cfg.get("provider", ""),
            on_mantle=("bedrock-mantle" in eps), on_runtime=("bedrock-runtime" in eps))
        cfg["apis"] = apis
        cfg["invoke_endpoint"], cfg["invoke_api"] = resolve_invoke_path(apis)
        stamped += 1
    if stamped:
        logger.info("Routing backfill: stamped %d chat model(s) with endpoint/API fields", stamped)
    return stamped


def _auto_roll_llm_categories(registry: dict, progress=None) -> list:
    """Smartly roll fast_llm/complex_llm to the newest available Claude on Sync.

    End-users aren't tech-savvy and can get stranded on an older/deprecated model.
    On every AWS Sync we re-point:
      • fast_llm    → newest ACTIVE Claude **Sonnet** discovered in chat_models
      • complex_llm → newest ACTIVE Claude **Opus** discovered in chat_models
    Selection prefers `us.` cross-region inference profiles, ACTIVE over LEGACY,
    and the highest (major, minor, date) via _claude_version_tuple. The category
    region is preserved if the chosen model is available there, else it falls back
    to the model's home region.

    Respects explicit user pins: if categories.{name}.pinned is True (set when the
    user manually picks a model in Model Settings), we DON'T switch — we only log
    that a newer model is available. Writes to the BASE registry via _save() so the
    smart default ships to everyone; user.json overrides still win on reload.

    Returns a list of human-readable notices (also pushed to `progress`).
    """
    notices = []
    chat_models = registry.get("chat_models", {})
    if not chat_models:
        return notices

    def _ranked(line: str):
        """ACTIVE Claude entries for 'sonnet'/'opus', sorted oldest→newest.
        Each item is (key, cfg). De-duplicated by version so 'second newest'
        means a genuinely different version, not a regional/profile twin."""
        cands = []
        for k, cfg in chat_models.items():
            mid = cfg.get("model_id", "").lower()
            if "claude" not in mid or line not in mid:
                continue
            if cfg.get("provider", "").lower() not in ("anthropic", ""):
                continue
            lifecycle = (cfg.get("lifecycle") or "ACTIVE").upper()
            prefer_profile = 1 if cfg.get("model_id", "").startswith("us.") else 0
            active = 1 if lifecycle == "ACTIVE" else 0
            cands.append(((active, prefer_profile) + _claude_version_tuple(mid), k, cfg))
        cands.sort(key=lambda t: t[0])
        # Keep one entry per distinct version tuple (newest profile wins), so
        # _ranked()[-2] is the previous *version*, not a duplicate of the newest.
        by_ver = {}
        for sortkey, k, cfg in cands:
            by_ver[_claude_version_tuple(cfg.get("model_id", "").lower())] = (k, cfg)
        return [by_ver[v] for v in sorted(by_ver)]

    def _newest(line: str):
        """Newest ACTIVE Claude model entry for 'sonnet'/'opus'. Returns (key, cfg) or None."""
        ranked = _ranked(line)
        return ranked[-1] if ranked else None

    targets = (("fast_llm", "sonnet", "Fast LLM"), ("complex_llm", "opus", "Complex LLM"))
    for cat_name, line, label in targets:
        best = _newest(line)
        if not best:
            continue
        _key, cfg = best
        new_id = cfg.get("model_id", "")
        if not new_id:
            continue
        cat = registry.setdefault("categories", {}).setdefault(cat_name, {})
        cur_id = cat.get("current", "")

        # Preserve category region if the chosen model is offered there.
        avail = cfg.get("available_regions", []) or []
        cur_region = cat.get("region", "")
        new_region = cur_region if cur_region in avail else cfg.get("region", cur_region)

        if new_id == cur_id and new_region == cur_region:
            continue  # already on the newest — nothing to do

        # Is the newer model actually newer than the current pick?
        is_upgrade = _claude_version_tuple(new_id) > _claude_version_tuple(cur_id)

        if cat.get("pinned"):
            if is_upgrade:
                msg = (f"{label}: staying on pinned {cur_id} — newer {new_id} "
                       f"is available (unpin in Model Settings to switch)")
                notices.append(msg)
                if progress:
                    progress(msg)
            continue

        if not is_upgrade and cur_id:
            continue  # don't downgrade or sidestep

        cat["current"] = new_id
        cat["region"] = new_region
        cat["provider"] = cfg.get("provider", "Anthropic") or "Anthropic"
        cat.setdefault("api_type", "converse")
        # Self-correcting param gate: stamp whether this model still takes
        # `temperature` so _build_inference_config stays data-driven.
        _probe_and_record_temperature(new_id, new_region, registry)
        msg = f"{label}: auto-switched to newest Claude → {new_id} ({new_region})"
        notices.append(msg)
        logger.info(msg)
        if progress:
            progress(msg)

    # fallback_llm: roll to the SECOND-newest Sonnet — one version behind fast_llm.
    # The fallback is the safety net on AccessDeniedException, so it must be a
    # genuinely DIFFERENT (still-current) model, not a clone of the primary. If
    # only one Sonnet version exists, degrade to that one. Respects pins.
    fb_cat = registry.setdefault("categories", {}).setdefault("fallback_llm", {})
    if not fb_cat.get("pinned"):
        sonnets = _ranked("sonnet")
        if sonnets:
            # prefer second-newest; fall back to newest if only one version
            _fb_key, fb_cfg = sonnets[-2] if len(sonnets) >= 2 else sonnets[-1]
            fb_id = fb_cfg.get("model_id", "")
            fb_cur = fb_cat.get("current", "")
            if fb_id and fb_id != fb_cur:
                avail = fb_cfg.get("available_regions", []) or []
                cur_region = fb_cat.get("region", "")
                fb_region = cur_region if cur_region in avail else fb_cfg.get("region", cur_region)
                fb_cat["current"] = fb_id
                fb_cat["region"] = fb_region
                fb_cat["provider"] = fb_cfg.get("provider", "Anthropic") or "Anthropic"
                fb_cat.setdefault("api_type", "converse")
                _probe_and_record_temperature(fb_id, fb_region, registry)
                msg = f"Fallback LLM: auto-switched to prior-version Sonnet → {fb_id} ({fb_region})"
                notices.append(msg)
                logger.info(msg)
                if progress:
                    progress(msg)

    return notices


def _probe_and_record_temperature(model_id: str, region: str, registry: dict):
    """Probe a model with `temperature` once and record support on its chat_models
    entry, so the param gate (_model_supports_temperature) needs no hardcoding.

    A 1-token Converse call: if it succeeds, temperature is supported; if it fails
    specifically because temperature is unsupported/deprecated, record that. Other
    errors (throttling, access) are ignored — we don't want to mislabel on a fluke.
    """
    try:
        import boto3 as _b
        client = _b.client("bedrock-runtime", region_name=region)
        try:
            client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": "hi"}]}],
                inferenceConfig={"maxTokens": 1, "temperature": 0.0},
            )
            supports = True
        except Exception as exc:
            txt = str(exc).lower()
            if "temperature" in txt and ("not support" in txt or "deprecated" in txt
                                         or "unsupported" in txt or "invalid" in txt):
                supports = False
            else:
                return  # inconclusive — leave the entry untouched
        # Record on every chat_models entry sharing this model_id.
        for cfg in registry.get("chat_models", {}).values():
            if cfg.get("model_id") == model_id:
                cfg["supports_temperature"] = supports
        logger.info("Param gate: %s supports_temperature=%s", model_id, supports)
    except Exception as exc:
        logger.debug("Temperature probe skipped for %s: %s", model_id, exc)


@router.post("/discover/refresh-all")
async def refresh_all_regions():
    """Scan ALL Bedrock-supported AWS regions and update the registry.

    The scan is blocking (boto3 region discovery + ~33 region scans + pricing).
    Run it in a worker thread so the event loop stays free to serve the
    ``/api/sync-progress`` SSE stream concurrently — otherwise the progress
    overlay shows nothing until the whole sync finishes (the bug fixed here).
    """
    import asyncio
    return await asyncio.to_thread(_run_refresh_all_regions)


def _run_refresh_all_regions():
    """Synchronous body of the AWS Sync (runs in a worker thread)."""
    import asyncio
    from backend.services.telemetry import track_model_settings_refresh
    track_model_settings_refresh()

    from backend.services.model_registry import get_registry, _save
    from backend.main import _server_state

    def _progress(msg):
        _server_state["sync_message"] = msg
        _server_state.setdefault("sync_log", []).append(msg)

    # Silence per-model save logs during bulk Sync (save once at the end)
    _save._silent = True
    _server_state["sync_in_progress"] = True
    _server_state["sync_log"] = []

    # Initialized before the try so the post-finally summary never NameErrors.
    all_regions: list[str] = []
    scan_regions: list[str] = []
    regions_not_enabled: list[str] = []
    account_listregions_denied = False

    try:
        # Step 1: Discover regions from AWS
        _progress("Discovering Amazon Bedrock regions...")
        all_regions = _get_bedrock_regions()

        # Step 2: Persist regions + fetch pricing data
        _progress(f"Found {len(all_regions)} regions. Fetching model pricing...")
        registry = get_registry()
        registry["bedrock_regions"] = all_regions  # full Bedrock-supported list (cached)
        logger.debug("Stored %d Bedrock regions in registry", len(all_regions))

        # Step 2a: Filter to regions ENABLED for this account before scanning.
        # Not-enabled regions otherwise fail with UnrecognizedClientException(403)
        # or hang on connect timeouts (~8-45s each) — slow + noisy. If we can't
        # read enabled regions (role lacks account:ListRegions), scan all and note it.
        _enabled = _account_enabled_regions()
        if _enabled is not None:
            regions_not_enabled = sorted(set(all_regions) - _enabled)
            scan_regions = [r for r in all_regions if r in _enabled]
            registry["regions_not_enabled"] = regions_not_enabled
            if regions_not_enabled:
                logger.info("Skipping %d region(s) not enabled for this account: %s",
                            len(regions_not_enabled), ", ".join(regions_not_enabled))
        else:
            account_listregions_denied = True
            scan_regions = all_regions
            registry.pop("regions_not_enabled", None)

        # Step 2b: Fetch per-image pricing from AWS Pricing API
        pricing_data = _fetch_image_pricing()
        if pricing_data:
            registry["image_pricing"] = pricing_data
            logger.debug("Stored pricing for %d model-region combos", len(pricing_data))

        # Step 2b-ii: Fetch per-region SageMaker instance pricing (for custom-model
        # + 3D compute cost). Scanned across the regions we're about to scan.
        sm_pricing = _fetch_sagemaker_pricing(scan_regions)
        if sm_pricing:
            registry["sagemaker_pricing"] = sm_pricing
            logger.debug("Stored SageMaker pricing for %d instance-region combos", len(sm_pricing))

        # Step 2c: Reset all available_regions before scanning — so stale regions
        # are pruned automatically. Each region scan in Step 3 re-adds itself.
        from backend.services.model_registry import update_image_model
        for key in list(registry.get("image_models", {}).keys()):
            update_image_model(key, {"available_regions": []})
        # Also reset chat_models regions
        for key in list(registry.get("chat_models", {}).keys()):
            registry["chat_models"][key]["available_regions"] = []

        # Step 3: Scan each ENABLED region for foundation + custom + imported models
        _progress(f"Scanning {len(scan_regions)} enabled regions for available models...")

        results = {}
        total_new = 0
        total_updated = 0
        total_custom = 0
        errors = 0

        for idx, region in enumerate(scan_regions):
            _progress(f"Scanning region {idx + 1}/{len(scan_regions)}: {region}...")
            try:
                result = asyncio.run(auto_register_image_models(region))
                results[region] = {
                    "new": result["new_count"],
                    "updated": result["updated_count"],
                }
                total_new += result["new_count"]
                total_updated += result["updated_count"]
                region_total = result["new_count"] + result["updated_count"]
                _progress(f"Done {region} — {region_total} model{'s' if region_total != 1 else ''} found")
            except Exception as exc:
                results[region] = {"error": str(exc)[:100]}
                errors += 1
                _progress(f"Skipped {region} ({str(exc)[:40]})")

            # Discover custom + imported models in this region
            try:
                custom_result = _discover_custom_models(region)
                custom_count = custom_result.get("registered_count", 0) + custom_result.get("updated_count", 0)
                if custom_count > 0:
                    results[region] = results.get(region, {})
                    results[region]["custom"] = custom_count
                    total_custom += custom_count
            except Exception as exc:
                logger.warning("Custom model discovery failed in %s: %s", region, exc)

        # Report not-enabled regions as ONE clean summary line (no per-region spam).
        if regions_not_enabled:
            _progress(f"Regions not enabled ({len(regions_not_enabled)}): "
                      + ", ".join(regions_not_enabled))
        elif account_listregions_denied:
            _progress("Note: add the account:ListRegions permission for faster, "
                      "quieter syncs (couldn't pre-filter to enabled regions).")

        # Step 4: Prune — check which Bedrock models are still available.
        _progress("Finalizing — checking model availability...")
        # After Step 3, each model's available_regions reflects what was discovered.
        # Models with empty available_regions (not found in any region) get disabled.
        # Custom-hosted models are EXEMPT — they don't use Bedrock regions.
        registry = get_registry()

        # Step 4b: Reconcile the bedrock-mantle catalog FIRST (before pruning) —
        # mark which discovered models are ALSO on Mantle, and add Mantle-only
        # models (e.g. OpenAI GPT-5.x, Claude Mythos) that never appear in the
        # bedrock-runtime listing. Stamps endpoints/apis/invoke_* per model.
        # Doing this before the prune ensures mantle-reachable models carry their
        # `endpoints` when the prune runs, so they're correctly exempted.
        _progress("Reconciling Amazon Bedrock Mantle model catalog...")
        try:
            mantle_added = _reconcile_mantle_models(registry)
            if mantle_added:
                _progress(f"Mantle: {mantle_added} model(s) reconciled")
        except Exception as exc:
            logger.warning("Mantle reconciliation skipped: %s", exc)

        # Step 4c: Backfill endpoint/API routing on EVERY chat model (incl.
        # pre-existing + update-path entries the per-model stamping missed), so
        # routing is explicit for all models. Runs even if Mantle is unavailable.
        try:
            _stamp_all_chat_model_routing(registry)
        except Exception as exc:
            logger.warning("Routing backfill skipped: %s", exc)

        # Step 4d: Prune — disable models not found in any region this scan.
        disabled = []
        for key, cfg in list(registry.get("image_models", {}).items()):
            if cfg.get("model_source") == "custom_hosted":
                continue
            regions = cfg.get("available_regions", [])
            if not regions and cfg.get("enabled", True):
                update_image_model(key, {"enabled": False})
                disabled.append(key)
                logger.debug("Disabled image model %s — no longer found in any region", key)
        for key, cfg in list(registry.get("chat_models", {}).items()):
            # Mantle-reachable models are EXEMPT — they live on the bedrock-mantle
            # endpoint, which the per-region runtime scan (list_foundation_models)
            # structurally can't see, so they always have empty available_regions.
            # Disabling them here would wipe every Mantle-only model (GPT-5.x,
            # Grok, etc.) on each sync.
            if "bedrock-mantle" in (cfg.get("endpoints") or []):
                continue
            regions = cfg.get("available_regions", [])
            if not regions and cfg.get("enabled", True):
                registry["chat_models"][key]["enabled"] = False
                disabled.append(key)
                logger.debug("Disabled chat model %s — no longer found in any region", key)
        for key, cfg in list(registry.get("video_models", {}).items()):
            if cfg.get("model_source") == "custom_hosted":
                continue
            regions = cfg.get("available_regions", [])
            if not regions and cfg.get("enabled", True):
                registry["video_models"][key]["enabled"] = False
                disabled.append(key)
                logger.debug("Disabled video model %s — no longer found in any region", key)

        # Step 4c: Stamp live per-model LLM token pricing onto chat_models (runs
        # AFTER the region scan, which fills available_regions used for matching).
        try:
            llm_pricing = _fetch_llm_pricing()
            if llm_pricing:
                n_priced = _apply_llm_pricing(registry, llm_pricing)
                _progress(f"Applied LLM token pricing to {n_priced} model(s).")
                logger.info("LLM token pricing applied to %d chat model(s)", n_priced)
        except Exception as exc:
            logger.warning("LLM pricing apply skipped: %s", exc)

        # Step 5: Smartly roll fast_llm/complex_llm to the newest Claude available.
        # Keeps non-technical users off deprecated models without manual config.
        # Auto-switch + notify; respects explicit user pins (categories.*.pinned).
        _progress("Selecting newest Claude models for fast/complex tasks...")
        try:
            roll_notices = _auto_roll_llm_categories(registry, _progress)
            for _n in roll_notices:
                logger.info("Auto-roll: %s", _n)
        except Exception as exc:
            logger.warning("LLM auto-roll skipped: %s", exc)

        # Stamp as discovered — written to .user.json (gitignored) so fresh clones still trigger auto-Sync
        from datetime import datetime, timezone
        from backend.services.model_registry import _save_user_pref
        _save_user_pref("_meta", "aws_account_discovered", "timestamp", datetime.now(timezone.utc).isoformat())

    finally:
        _save._silent = False
        _server_state["sync_in_progress"] = False
        _server_state["sync_message"] = ""

    # Single save at the end — all changes accumulated in memory during Sync
    _save()

    # Auto-promote: copy discovered data to git-tracked base file,
    # rewrite user file to only user-specific overrides
    from backend.services.model_registry import promote_to_base
    promote_result = promote_to_base()
    logger.info("Sync complete: %d new, %d updated across %d enabled regions (%d errors, %d not enabled). Promoted %d base models, %d user overrides.",
                total_new, total_updated, len(scan_regions), errors, len(regions_not_enabled),
                promote_result["base_models"], promote_result["user_overrides"])

    # Telemetry: track sync completion + first-sync milestone
    from backend.services.telemetry import track_sync_complete, track_first_sync
    registry = get_registry()
    img_count = sum(1 for v in registry.get("image_models", {}).values() if v.get("model_purpose") == "text_to_image")
    chat_count = len(registry.get("chat_models", {}))
    track_sync_complete(regions=len(scan_regions), new_models=total_new, updated_models=total_updated, errors=errors)
    if total_new > 0:
        track_first_sync(regions=len(scan_regions), image_models=img_count, chat_models=chat_count)

    return {
        "regions_scanned": len(scan_regions),
        "regions_not_enabled": regions_not_enabled,
        "total_new": total_new,
        "total_updated": total_updated,
        "total_custom": total_custom,
        "disabled": disabled,
        "errors": errors,
        "per_region": results,
        "promoted": promote_result,
    }


@router.get("/discover/{region}")
async def discover_models(region: str):
    """Discover available foundation models in a Bedrock region.

    Returns deduplicated models grouped by provider and capability.
    Only shows the latest version of each model family.
    """
    try:
        bedrock = boto3.Session().client("bedrock", region_name=region, config=_DISCOVERY_CONFIG)
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


# ── Custom & Imported Model Discovery ─────────────────────────────────────


def _find_base_model_in_registry(base_model_arn: str, registry: dict) -> dict | None:
    """Look up a base model in the existing registry by its ARN or model_id.

    This is the dynamic approach: instead of hardcoding which base models map
    to which format families, we look at what's already registered from
    ListFoundationModels discovery. The base model's format_family, purpose,
    and output modalities are inherited by its custom/fine-tuned variants.
    """
    if not base_model_arn:
        return None

    # Extract the model_id portion from the ARN
    # e.g. "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-canvas-v1:0"
    # → "amazon.nova-canvas-v1:0"
    base_model_id = base_model_arn.rsplit("/", 1)[-1] if "/" in base_model_arn else base_model_arn

    # Search image_models
    for key, cfg in registry.get("image_models", {}).items():
        stored_id = cfg.get("model_id", "")
        stored_arn = cfg.get("model_arn", "")
        # Match by model_id (with or without us. prefix), or by ARN
        if stored_id in (base_model_id, f"us.{base_model_id}") or stored_arn == base_model_arn:
            return {**cfg, "_registry_key": key, "_model_type": "image"}

    # Search video_models
    for key, cfg in registry.get("video_models", {}).items():
        stored_id = cfg.get("model_id", "")
        stored_arn = cfg.get("model_arn", "")
        if stored_id in (base_model_id, f"us.{base_model_id}") or stored_arn == base_model_arn:
            return {**cfg, "_registry_key": key, "_model_type": "video"}

    return None


def _discover_custom_models(region: str) -> dict:
    """Discover custom (fine-tuned) and imported models in a region.

    Calls ListCustomModels, ListImportedModels, and ListProvisionedModelThroughputs.
    Auto-registers usable models with format families inherited dynamically from
    their base model (looked up in the existing registry — no hardcoded mappings).

    Fine-tuned models require provisioned throughput or on-demand deployment to invoke,
    so we also check ListProvisionedModelThroughputs to find invocable models.
    Imported models can be invoked directly via their ARN.
    """
    from backend.services.model_registry import (
        get_registry, add_image_model, get_image_model, update_image_model,
        add_video_model, get_video_model, update_video_model,
        _save,
    )

    bedrock = boto3.Session().client("bedrock", region_name=region, config=_DISCOVERY_CONFIG)
    registry = get_registry()

    registered = []
    updated_list = []

    # ── 1. Find invocable custom models ─────────────────────────────────────
    # Custom models need either a deployment or provisioned throughput to invoke.
    # InvokeModel accepts custom-model-deployment ARNs and provisioned-model ARNs
    # (not raw custom-model ARNs). We check both sources.
    invocable_by_model_arn: dict[str, str] = {}  # model_arn → invocation_arn

    # 1a. Custom model deployments (on-demand, newer API)
    try:
        resp = bedrock.list_custom_model_deployments(statusEquals="Active")
        for dep in resp.get("modelDeploymentSummaries", []):
            model_arn = dep.get("modelArn", "")
            dep_arn = dep.get("modelDeploymentArn", "")
            if model_arn and dep_arn:
                invocable_by_model_arn[model_arn] = dep_arn
    except Exception as exc:
        logger.debug("ListCustomModelDeployments not available in %s: %s", region, exc)

    # 1b. Provisioned throughputs (traditional)
    try:
        paginator = bedrock.get_paginator("list_provisioned_model_throughputs")
        for page in paginator.paginate(statusEquals="InService"):
            for pt in page.get("provisionedModelSummaries", []):
                model_arn = pt.get("modelArn", "")
                prov_arn = pt.get("provisionedModelArn", "")
                if model_arn and prov_arn and model_arn not in invocable_by_model_arn:
                    invocable_by_model_arn[model_arn] = prov_arn
    except Exception as exc:
        logger.debug("ListProvisionedModelThroughputs not available in %s: %s", region, exc)

    # ── 2. Custom models (fine-tuned, distilled, etc.) ────────────────────
    try:
        custom_models = []
        kwargs = {}
        while True:
            resp = bedrock.list_custom_models(**kwargs)
            custom_models.extend(resp.get("modelSummaries", []))
            if resp.get("nextToken"):
                kwargs["nextToken"] = resp["nextToken"]
            else:
                break
    except Exception as exc:
        logger.debug("ListCustomModels not available in %s: %s", region, exc)
        custom_models = []

    for cm in custom_models:
        model_arn = cm.get("modelArn", "")
        model_name = cm.get("modelName", "")
        base_model_arn = cm.get("baseModelArn", "")
        customization_type = cm.get("customizationType", "")

        # Only process Active models
        if cm.get("modelStatus", "Active") != "Active":
            continue

        # Determine invocation ID (provisioned throughput ARN if available)
        invocation_id = invocable_by_model_arn.get(model_arn, model_arn)
        is_invocable = model_arn in invocable_by_model_arn

        # Generate registry key
        key = f"custom_{model_name.lower().replace(' ', '_').replace('-', '_')}"
        key = _re.sub(r"[^a-z0-9_]", "", key)[:60]

        # Look up base model in the existing registry to inherit format family
        base_info = _find_base_model_in_registry(base_model_arn, registry)

        if base_info:
            model_type = base_info["_model_type"]  # "image" or "video"
            purpose = base_info.get("model_purpose", "text_to_image")
            format_family = base_info.get("format_family", "")
            prompt_limit = base_info.get("prompt_limit", 900)

            if model_type == "image":
                existing = get_image_model(key)
                if existing:
                    backfill = {"model_source": "custom", "customization_type": customization_type}
                    if invocation_id != existing.get("model_id"):
                        backfill["model_id"] = invocation_id
                    update_image_model(key, backfill)
                    updated_list.append({"key": key, "model_arn": model_arn})
                else:
                    config = {
                        "label": f"{model_name} (Custom)",
                        "model_id": invocation_id,
                        "model_arn": model_arn,
                        "base_model_arn": base_model_arn,
                        "region": region,
                        "available_regions": [region],
                        "provider": "Custom",
                        "enabled": is_invocable,
                        "model_purpose": purpose,
                        "format_family": format_family,
                        "model_source": "custom",
                        "customization_type": customization_type,
                        "prompt_limit": prompt_limit,
                        "moderation_strictness": "moderate",
                        "base_price_usd": None,
                        "extra_body": base_info.get("extra_body", {}),
                    }
                    add_image_model(key, config)
                    registered.append({"key": key, "model_name": model_name, "type": f"custom_{model_type}"})
                    logger.info("Registered custom %s model: %s (%s) in %s", model_type, key, model_name, region)

            elif model_type == "video":
                existing = get_video_model(key)
                if existing:
                    update_video_model(key, {"model_source": "custom", "customization_type": customization_type})
                    updated_list.append({"key": key, "model_arn": model_arn})
                else:
                    config = {
                        "label": f"{model_name} (Custom)",
                        "model_id": invocation_id,
                        "model_arn": model_arn,
                        "base_model_arn": base_model_arn,
                        "region": region,
                        "available_regions": [region],
                        "provider": "Custom",
                        "enabled": is_invocable,
                        "model_purpose": purpose,
                        "format_family": format_family,
                        "model_source": "custom",
                        "customization_type": customization_type,
                        "prompt_limit": prompt_limit,
                    }
                    add_video_model(key, config)
                    registered.append({"key": key, "model_name": model_name, "type": "custom_video"})
        else:
            # Base model not found in registry — likely a text/LLM model.
            # Register as a custom LLM alternative.
            llm_key = f"custom_llm_{key}"
            custom_llms = registry.setdefault("categories", {}).setdefault("custom_llms", {
                "label": "Custom LLMs",
                "description": "Fine-tuned and custom text models",
                "models": {},
            })
            if llm_key not in custom_llms.get("models", {}):
                custom_llms.setdefault("models", {})[llm_key] = {
                    "label": f"{model_name} (Custom)",
                    "model_id": invocation_id,
                    "model_arn": model_arn,
                    "base_model_arn": base_model_arn,
                    "region": region,
                    "model_source": "custom",
                    "customization_type": customization_type,
                    "enabled": is_invocable,
                }
                registered.append({"key": llm_key, "model_name": model_name, "type": "custom_llm"})

    # ── 3. Imported models ────────────────────────────────────────────────
    try:
        imported_models = []
        kwargs = {}
        while True:
            resp = bedrock.list_imported_models(**kwargs)
            imported_models.extend(resp.get("modelSummaries", []))
            if resp.get("nextToken"):
                kwargs["nextToken"] = resp["nextToken"]
            else:
                break
    except Exception as exc:
        logger.debug("ListImportedModels not available in %s: %s", region, exc)
        imported_models = []

    for im in imported_models:
        model_arn = im.get("modelArn", "")
        model_name = im.get("modelName", "")
        architecture = im.get("modelArchitecture", "")
        instruct_supported = im.get("instructSupported", False)

        # Imported models are invocable directly via their ARN
        key = f"imported_{model_name.lower().replace(' ', '_').replace('-', '_')}"
        key = _re.sub(r"[^a-z0-9_]", "", key)[:60]

        # All imported models are registered as LLM alternatives
        # (Bedrock import currently supports transformer text/vision architectures)
        custom_llms = registry.setdefault("categories", {}).setdefault("custom_llms", {
            "label": "Custom LLMs",
            "description": "Fine-tuned and imported text models",
            "models": {},
        })
        if key not in custom_llms.get("models", {}):
            custom_llms.setdefault("models", {})[key] = {
                "label": f"{model_name} (Imported)",
                "model_id": model_arn,
                "model_arn": model_arn,
                "region": region,
                "model_source": "imported",
                "architecture": architecture,
                "instruct_supported": instruct_supported,
                "enabled": True,
            }
            registered.append({"key": key, "model_name": model_name, "type": "imported_llm"})
            logger.info("Registered imported model: %s (%s, %s) in %s", key, model_name, architecture, region)

    # Save registry
    if registered or updated_list:
        _save()

    return {
        "region": region,
        "registered": registered,
        "updated": updated_list,
        "registered_count": len(registered),
        "updated_count": len(updated_list),
    }
