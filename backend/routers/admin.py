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
    from backend.services.model_registry import registry_transaction

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, detail="Invalid JSON")

    # Validate BEFORE modifying anything
    required = ["categories", "image_models"]
    missing = [k for k in required if k not in body]
    if missing:
        raise HTTPException(400, detail=f"Missing required keys: {', '.join(missing)}")

    # Replace the in-memory registry and save (writes diff to .user.json),
    # atomically under the cross-process lock so a concurrent worker write can't
    # interleave. The admin editor is authoritatively replacing the whole
    # document, so a clear()+update(body) overwrite is intended.
    with registry_transaction() as registry:
        registry.clear()
        registry.update(body)
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
    system_prompt: str | None = None  # Optional: also update the LLM system message (None = leave unchanged)


@router.patch("/templates/{name}")
async def update_template_endpoint(name: str, body: TemplateUpdate):
    """Update a prompt template's text. Validates required variables.

    If variables are missing and fix_variables=True, uses an LLM to intelligently
    insert them in the right places. Otherwise returns 400 with details.
    """
    from backend.services.prompt_templates import update_template, validate_template, get_all_templates
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    reset_costs()  # scope any auto-fix LLM cost to THIS request

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

            # Save the fixed version (also persist system_prompt if provided)
            result = update_template(name, fixed, force=True, system_prompt=body.system_prompt)
            result["auto_fixed"] = True
            result["fixed_variables"] = missing
            return result

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(502, detail=f"Auto-fix failed: {exc}. Please add manually: {', '.join(missing)}")
        finally:
            track_aux_llm_cost("template_fix_variables", get_total_cost(), studio="model_settings")

    elif missing:
        raise HTTPException(400, detail={
            "message": f"Required variables missing: {', '.join(missing)}",
            "missing_variables": missing,
            "hint": "These variables are substituted at runtime. Removing them breaks the feature. Click 'Fix & Save' to auto-insert them.",
        })

    # No missing variables — save directly (also persist system_prompt if provided)
    try:
        result = update_template(name, body.text, force=True, system_prompt=body.system_prompt)
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
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
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

    from backend.routers.chat import _resolve_chat_region
    try:
        improved = invoke_llm(
            enhance_prompt,
            model_id=body.model_id,
            # The picked model's own route (its pinned Region / a Region its
            # profile covers) — never an assumed home Region.
            region=body.region or _resolve_chat_region(body.model_id),
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
    finally:
        track_aux_llm_cost("template_enhance", get_total_cost(), studio="model_settings")


@router.get("/models/image-options")
def get_image_model_options(region: str | None = Query(default=None)):
    """Return enabled image models for the frontend dropdown.

    This is the source of truth for model selection — the frontend
    should NOT hardcode model lists. Returns models sorted alphabetically
    by label (case-insensitive).

    Optional `region` filter: if provided, only returns models available
    in that region. If omitted, returns all enabled models.
    """
    from backend.services.model_registry import get_enabled_image_models, get_registry, get_model_supported_sizes
    from backend.services.cost_tracker import resolve_image_price
    from backend.services.custom_models import get_instance_hourly_rate
    enabled = get_enabled_image_models()
    registry = get_registry()

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

        # Build per-region pricing via the SHARED resolver (resolve_image_price) —
        # the exact matching the cost path uses, so display and billing never
        # diverge. No duplicate matching logic here.
        model_label = cfg.get("label", key)
        quality_opts = cfg.get("quality_options", [])
        default_q = cfg.get("default_quality", "")

        region_pricing = []
        for r in available_regions:
            quality_prices = {}
            for q in (quality_opts or [{"value": ""}]):
                qv = q.get("value", "")
                p = resolve_image_price(cfg, key, r, qv)
                if p is not None:
                    quality_prices[qv] = p
            base_price = cfg.get("base_price_usd")
            default_price = (quality_prices.get(default_q) or quality_prices.get("")
                             or next(iter(quality_prices.values()), None) or base_price)
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
            # Capability flags (e.g. image_to_image) — the Image Studio filters
            # the model dropdown by these in reference "Remix" mode.
            "capabilities": cfg.get("capabilities") or {},
            # Custom-hosted models are hourly-billed: expose the live rate + typical
            # latency so the studio shows a compute-time-based estimate, not per-image.
            "custom_hourly_usd": (
                get_instance_hourly_rate(
                    (cfg.get("deployment", {}) or {}).get("instance_type"),
                    cfg.get("catalog_key"),
                    (cfg.get("deployment", {}) or {}).get("region"))
                if cfg.get("model_source") == "custom_hosted" else None),
            "typical_latency_seconds": (cfg.get("invoke", {}) or {}).get("typical_latency_seconds"),
            "supported_sizes": get_model_supported_sizes(cfg),
            "_last_updated": cfg.get("last_updated", cfg.get("invoke", {}).get("last_updated", "")),
        })

    # Sort alphabetically by label (case-insensitive) so the dropdown reads
    # A→Z regardless of provider or release date.
    for m in models:
        m.pop("_last_updated", None)
    models.sort(key=lambda m: m["label"].casefold())

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


# Amazon Bedrock cross-region inference-profile geo prefixes. A profile id is
# geo-scoped: ``us.`` routes only within US Regions, ``eu.``/``apac.``/``in.``/…
# within those geographies, and ``global.`` from ANY commercial Region where the
# model is offered. The set of geos is whatever ListInferenceProfiles returned
# (registry ``inference_profiles``) — see model_registry.inference_profile_geos.
# Stripping the prefix yields the bare model id for cross-endpoint/family
# matching; picking the RIGHT prefix (per invoke Region) is what keeps an
# inference-profile model actually invocable.
def _strip_geo_prefix(mid: str) -> str:
    """Return the bare model id with any cross-region geo prefix removed."""
    from backend.services.model_registry import strip_geo_prefix
    return strip_geo_prefix(mid)


def _has_geo_prefix(mid: str) -> bool:
    return _strip_geo_prefix(mid) != (mid or "")


def _profile_prefix_for_region(region: str, profile_map: dict | None = None) -> str:
    """Fallback prefix for a profile-only model the discovered map doesn't list.

    Nothing is known about THIS model's profiles, so take the geo whose profiles
    (for other models) cover ``region`` — the configured residency geo when it is
    one of them — learned from the discovered map, never from the Region's name.
    A geo profile covering its own Region is the safest guess (``global.`` isn't
    offered for every model); ``global.`` only when no geo is known for the Region.
    The next Sync's pin post-pass re-derives it once the model's profiles appear.
    """
    geos = sorted(_region_geos(profile_map).get(region) or ())
    pref = _preferred_residency_geo()
    if pref in geos:
        return pref + "."
    return geos[0] + "." if geos else "global."


def _discover_inference_profiles(bedrock_client) -> dict:
    """Map ``normalized base model id -> {geo_prefix: set(Regions the profile covers)}``.

    Built from ``list_inference_profiles(SYSTEM_DEFINED)`` in ONE Region: it returns
    the cross-region profiles usable FROM that Region (its geo + ``global``) and,
    per profile, the underlying model Regions (parsed from each ``models[].modelArn``).
    This is the AUTHORITATIVE source for residency-aware routing — no guessing a geo
    from a Region name. Empty on any error (caller falls back to the Region heuristic).
    """
    out: dict = {}
    try:
        token = None
        while True:
            kw = {"typeEquals": "SYSTEM_DEFINED", "maxResults": 200}
            if token:
                kw["nextToken"] = token
            resp = bedrock_client.list_inference_profiles(**kw)
            for p in resp.get("inferenceProfileSummaries", []):
                pid = p.get("inferenceProfileId", "")
                if "." not in pid or p.get("status") != "ACTIVE":
                    continue
                # SYSTEM_DEFINED profile ids are '<geo>.<provider>.<model>' — the
                # geo is taken as AWS names it (a new geography needs no code).
                prefix, base = pid.split(".", 1)
                if "." not in base:
                    continue
                regions = {a.split(":")[3] for m in (p.get("models") or [])
                           if len((a := m.get("modelArn", "")).split(":")) > 4 and a.split(":")[3]}
                out.setdefault(_normalize_model_id(base), {}).setdefault(prefix, set()).update(regions)
            token = resp.get("nextToken")
            if not token:
                break
    except Exception as exc:
        # Visible, not silent: an invisible discovery failure would make the whole
        # residency post-pass no-op with no trace (it keys off this map).
        logger.warning("inference-profile discovery failed (%s) — residency pins for "
                       "this Region fall back to the heuristic", exc)
    return out


def _select_profile_prefix(model_id: str, region: str, profile_map: dict,
                           residency: str | None = None):
    """Inference-profile prefix for invoking ``model_id`` from ``region``.

    No residency constraint (the default, ``preferred_residency_geo`` unset):
    ``global.`` when AWS offers it (callable from any source Region), else a geo
    profile that covers the Region. With a residency constraint: a geo profile
    covering the Region first (data stays in that geography), ``global.`` only
    when none does. ``""`` when only the in-Region base id exists; ``None`` when
    the model isn't in the discovered map (caller then uses the Region heuristic).
    """
    profs = profile_map.get(_normalize_model_id(model_id))
    if not profs:
        return None
    if residency is None:
        residency = _preferred_residency_geo()
    geo = sorted(pre for pre, regs in profs.items() if pre != "global" and region in regs)
    if "global" in profs and not (residency and geo):
        return "global."
    if geo:
        return geo[0] + "."            # geo profile covering this Region
    return ""                          # only the in-Region base id exists


def _residency_scope(effective_id: str, base_id: str) -> str:
    """Human/label form of the residency posture implied by a chosen model id."""
    if effective_id == base_id:
        return "in-region"
    pre = effective_id.split(".", 1)[0]
    return "global" if pre == "global" else f"geo:{pre}"


def _region_geos(profile_map: dict) -> dict:
    """``Region -> {geo prefixes whose profiles cover it}`` from the discovered
    inference profiles (``global`` excluded — it covers everything)."""
    out: dict = {}
    for profs in (profile_map or {}).values():
        for geo, regions in (profs or {}).items():
            if geo != "global":
                for r in regions or ():
                    out.setdefault(r, set()).add(geo)
    return out


def _region_in_geo(region: str, geo: str, region_geos: dict) -> bool:
    """Whether ``region`` lies in geography ``geo``.

    Used only to prefer a Region in the deployment's preferred residency geo when
    pinning a model that has no cross-region profile (a plain regional model keeps
    its data in whatever Region it runs in). Authoritative when a discovered geo
    profile covers the Region; otherwise the Region's name prefix must start the
    geo name ('ap-*' ∈ 'apac', 'eu-*' ∈ 'eu').
    """
    if region in region_geos:
        return geo in region_geos[region]
    p = (region or "").split("-")[0]
    return bool(p) and geo.startswith(p)


def _preferred_residency_geo(registry: dict | None = None) -> str:
    """The OPTIONAL data-residency constraint (config.py / env), validated.

    ``""`` (the default) = no constraint — pins prefer ``global.``. A value is
    honoured only when it is a discovered geo profile prefix (``global`` is not a
    residency); anything else is ignored with a warning, i.e. treated as unset.
    """
    from backend.config import settings
    from backend.services.model_registry import inference_profile_geos
    geo = (getattr(settings, "preferred_residency_geo", "") or "").strip().lower()
    if not geo:
        return ""
    geos = inference_profile_geos(registry)
    if geo != "global" and (geo in geos or not geos):
        return geo
    logger.warning("preferred_residency_geo=%r is not a discovered geo profile (%s) — "
                   "ignored (no residency constraint)", geo, ", ".join(sorted(geos - {"global"})))
    return ""


def _resolve_residency_pins(registry: dict, progress=None) -> int:
    """Self-healing pin post-pass: re-derive every chat model's pin (``region`` +
    ``model_id`` prefix) from the profiles discovered this Sync, independent of
    the (alphabetical) order Regions were scanned in.

    For each model it evaluates ALL Regions where the model was found. With no
    residency constraint (the default): ``global.`` → a geo profile → a plain
    regional pin, preferring the home Region (config.py) and then its geography.
    With ``preferred_residency_geo`` set: an in-geo profile or Region → any geo
    profile → a plain regional pin elsewhere → ``global.``. This heals drift (e.g.
    an old ``us.<id>`` stuck on a non-US Region — an invalid combo that fails to
    invoke) and keeps pins deterministic rather than an accident of scan order.
    The pin is only the default route: lookups (capabilities, routing, pricing)
    resolve by foundation model, so any profile id AWS offers keeps working.

    Image models are healed too, but ONLY when they already carry a geo/global
    prefix (profile-based) — plain regional image pins are admin-curated and left
    untouched, keeping blast radius contained.
    """
    from backend.services.mantle_client import derive_model_apis, resolve_invoke_path
    from backend.config import settings
    pmap = registry.get("inference_profiles", {}) or {}
    pref = _preferred_residency_geo(registry)
    region_geos = _region_geos(pmap)
    if not pmap:
        # Nothing discovered → keep existing pins (safe no-op). Log it: a silent
        # skip here is exactly how a stale/failed discovery hides itself.
        msg = ("Residency: no inference profiles discovered this Sync — pins left "
               "unchanged (check earlier discovery warnings)")
        logger.warning(msg)
        if progress:
            progress(msg)
        return 0
    healed = 0

    def _best_pin(base: str, avail: list[str], home: str):
        """(region, prefix) for one model among the Regions it was found in.

        Rank: no constraint → global. (0), geo profile (1), plain regional (2);
        with `pref` → in-geo profile/Region (0), other geo profile (1), plain
        regional elsewhere (2), global. (3). Tie-break: a Region in the target
        geography (`pref`, else the home Region's own) → the configured home
        Region (config.py) → name order — consistent with the LLM categories and
        where the app operates, not an alphabetical accident.
        """
        home_geos = set(region_geos.get(home) or ())
        def _in_target(r):
            if pref:
                return _region_in_geo(r, pref, region_geos)
            return bool(home_geos & set(region_geos.get(r) or ()))
        best = None  # (sort_key, region, prefix)
        for r in avail:
            sel = _select_profile_prefix(base, r, pmap, pref)  # None | '' | geo. | 'global.'
            if sel is None or sel == "":
                # Plain regional model → residency IS the Region's own geo.
                prefix = ""
                rank = (0 if _region_in_geo(r, pref, region_geos) else 2) if pref else 2
            elif sel == "global.":
                rank, prefix = (3 if pref else 0), "global."
            else:
                prefix = sel
                rank = (0 if sel.rstrip(".") == pref else 1) if pref else 1
            key = (rank, 0 if _in_target(r) else 1, 0 if r == home else 1, r)
            if best is None or key < best[0]:
                best = (key, r, prefix)
        return (best[1], best[2]) if best else (None, "")

    def _heal(section: str, profile_only: bool, home: str):
        nonlocal healed
        for key, cfg in (registry.get(section, {}) or {}).items():
            # Mantle-ONLY models carry no runtime Region, so the region scan leaves
            # available_regions empty → the check below skips them. Dual models
            # (bedrock-mantle + bedrock-runtime) DO get scanned Regions and are
            # residency-pinned on their runtime Region like any other.
            avail = cfg.get("available_regions") or []
            if cfg.get("invoke_endpoint") == "bedrock-mantle" and cfg.get("mantle_regions"):
                # Served by Mantle → only Regions whose Mantle catalog lists it.
                avail = [r for r in avail if r in cfg["mantle_regions"]]
            if not avail:
                continue
            cur_id = cfg.get("model_id", "")
            if profile_only and not _has_geo_prefix(cur_id):
                continue  # leave plain regional image pins alone (admin-curated)
            # id_base preserves the FULL id (version/suffix) — only the geo prefix is
            # stripped — so the rebuilt model_id stays invokable. lookup_key is the
            # aggressively-normalized form used ONLY to index the profile map.
            id_base = _strip_geo_prefix(cur_id)
            lookup_key = _normalize_model_id(id_base)
            region, prefix = _best_pin(id_base, avail, home)
            if not region:
                continue
            new_id = prefix + id_base
            avail_profiles = sorted((pmap.get(lookup_key) or {}).keys())
            if cfg.get("model_id") == new_id and cfg.get("region") == region:
                # Still refresh the recorded posture (cheap, keeps it authoritative).
                cfg["residency_scope"] = _residency_scope(new_id, id_base)
                cfg["inference_profiles"] = avail_profiles
                continue
            cfg["model_id"] = new_id
            cfg["region"] = region
            cfg["residency_scope"] = _residency_scope(new_id, id_base)
            cfg["inference_profiles"] = avail_profiles
            if section == "chat_models":
                # model_id changed → re-derive endpoint/API routing to match.
                apis = derive_model_apis(
                    new_id, cfg.get("provider", ""),
                    on_mantle="bedrock-mantle" in (cfg.get("endpoints") or []),
                    on_runtime=True,
                )
                cfg["apis"] = apis
                cfg["invoke_endpoint"], cfg["invoke_api"] = resolve_invoke_path(apis)
            healed += 1

    # Home Region from config.py, per section (LLMs vs images). Used only as a
    # within-geo tie-break — the residency rank + preferred geo always dominate.
    _heal("chat_models", profile_only=False, home=settings.aws_region_models)
    _heal("image_models", profile_only=True, home=settings.aws_region_images)
    # Profile-based post-processing tools (upscale / background removal) are the
    # same Bedrock models as their image_models twins — follow the twin's pin.
    for cfg in (registry.get("post_processing", {}) or {}).values():
        cur_id = cfg.get("model_id", "") if isinstance(cfg, dict) else ""
        if not _has_geo_prefix(cur_id):
            continue  # plain / SageMaker ids are admin-curated
        base = _strip_geo_prefix(cur_id)
        twin = next((c for c in (registry.get("image_models", {}) or {}).values()
                     if _strip_geo_prefix(c.get("model_id", "")) == base), None)
        if twin and twin.get("model_id") != cur_id:
            cfg["model_id"], cfg["region"] = twin["model_id"], twin.get("region") or cfg.get("region")
            healed += 1
    # Always report the outcome (even 0) — confirms the pass ran and how many
    # models it evaluated, so a no-op is distinguishable from "didn't run".
    posture = f"'{pref}' residency" if pref else "no residency constraint (global. preferred)"
    msg = (f"Profile pins: re-pinned {healed} model(s) — {posture} "
           f"({len(pmap)} models in the discovered profile map)")
    logger.info(msg)
    if progress:
        progress(msg)
    return healed


def _normalize_model_id(model_id: str) -> str:
    """Bare, comparable form of a model id for cross-endpoint matching.

    Strips the cross-region inference-profile prefix and any trailing throughput /
    context / version qualifiers (``:0``, ``:200k``, ``-v1:0``) so the SAME
    model discovered via different endpoints/listings collapses to one identity.
    Examples:
      ``us.anthropic.claude-sonnet-4-6``            -> ``anthropic.claude-sonnet-4-6``
      ``openai.gpt-oss-120b-1:0``                   -> ``openai.gpt-oss-120b``
      ``anthropic.claude-3-sonnet-20240229-v1:0:200k`` -> ``anthropic.claude-3-sonnet-20240229``
    """
    mid = _strip_geo_prefix(model_id)
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
    body = _strip_geo_prefix(model_id).split(":")[0]
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


def _lifecycle_fields(m: dict) -> dict:
    """Extract the AWS-objective lifecycle facts from a Bedrock model summary's
    `modelLifecycle` (ListFoundationModels/GetFoundationModel). These are the same
    for every account → they belong in the git-tracked base registry. Refreshed on
    each Sync (a model moves ACTIVE → LEGACY → EOL over time). Per-account access
    (`lifecycle_unavailable`) is separate and lives in user.json."""
    lc = m.get("modelLifecycle", {}) or {}
    def _iso(v):
        try:
            return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v else "")
        except Exception:
            return ""
    return {
        "lifecycle_status": lc.get("status", "ACTIVE"),
        "legacy_time": _iso(lc.get("legacyTime")),
        "end_of_life_time": _iso(lc.get("endOfLifeTime")),
    }


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
            new_lifecycle = m.get('lifecycle_status', 'ACTIVE')
            old_lifecycle = existing.get('lifecycle_status', 'ACTIVE')
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

    # Profile routing: the cross-region inference profiles usable FROM this Region
    # (its geo + global), each with the exact model Regions it covers. Drives
    # _select_profile_prefix (global. where offered, or the in-geo profile under an
    # optional residency constraint — see _register_chat_model). Empty on failure →
    # callers fall back to the region heuristic.
    profile_map = _discover_inference_profiles(bedrock)

    from backend.services.model_registry import (
        get_registry, add_image_model, get_image_model, update_image_model,
        add_video_model, get_video_model, update_video_model,
    )

    registry = get_registry()

    # NOTE: the discovered profile_map is NOT merged into the registry here. During a
    # full Sync this function makes system writes via add/update_image_model, whose
    # registry_transaction() reloads _registry from disk mid-call and would wipe any
    # in-memory accumulation (SPEC §17 batch-Sync rule). Instead we RETURN it and let
    # _run_refresh_all_regions accumulate it in a local dict, then assign it to the
    # registry in the transaction-free tail right before _resolve_residency_pins.
    # profile_map is still used below (per-Region effective_id); the post-pass is the
    # authoritative re-derivation.

    # Build model_id → list of registry keys lookup for existing models
    # Map both the stored model_id and the raw version (without us. prefix)
    # so that Bedrock's raw IDs match our stored inference profile IDs.
    # Multiple entries may share the same model_id (e.g. inpaint/outpaint variants).
    existing_by_model_id: dict[str, list[str]] = {}
    for key, cfg in registry.get("image_models", {}).items():
        stored_id = cfg.get("model_id", "")
        existing_by_model_id.setdefault(stored_id, []).append(key)
        bare = _strip_geo_prefix(stored_id)
        if bare != stored_id:
            existing_by_model_id.setdefault(bare, []).append(key)
    existing_video_by_model_id: dict[str, list[str]] = {}
    for key, cfg in registry.get("video_models", {}).items():
        stored_id = cfg.get("model_id", "")
        existing_video_by_model_id.setdefault(stored_id, []).append(key)
        bare = _strip_geo_prefix(stored_id)
        if bare != stored_id:
            existing_video_by_model_id.setdefault(bare, []).append(key)

    # Classify image models by purpose and format family based on model_id keywords.
    # Per-model prompt guidance = MODEL-SPECIFIC steering ("how to prompt THIS
    # model": caption vs instruction, structure, length band, negation handling).
    # Distinct from the prompt-template registry, which is content-intent ("how
    # the user wants their content"). Seeded here from official vendor docs so
    # the AWS Sync always records it onto the registry entry (create + backfill).
    # See memory: reference_prompt_length_guidance (2026 research, cited).
    _STABILITY_T2I_GUIDANCE = (
        "Responds well to rich, natural-language descriptions (~60-120 words). "
        "Excels at material texture, lighting, atmosphere, and compositional precision — "
        "let quality emerge from specific, vivid description rather than fixed quality-token prefixes. "
        "Negative prompts are effective: put exclusions in the NEGATIVE line, not in the main prompt."
    )
    _NOVA_CANVAS_GUIDANCE = (
        "Write a descriptive image CAPTION, not a command (~40-60 words). "
        "Order: subject → environment → pose → lighting → camera → style. "
        "Front-load the most important elements; place least-important details near the end "
        "(long prompts drop trailing detail). NEVER use 'no'/'not'/'without' — route exclusions to the NEGATIVE line."
    )
    _AMAZON_DEFAULT_GUIDANCE = (
        "Write a concise descriptive caption — subject first, style last. "
        "Front-load key details; keep it tight. Route exclusions to the NEGATIVE line, never 'no'/'not'/'without'."
    )

    def _classify_image_model(model_id: str, provider: str, input_modalities: list[str]):
        """Classify a Bedrock image model → (model_purpose, format_family, prompt_limit,
        base_price, optimal_prompt_words, prompt_guidance) from its id + provider.

        base_price comes from the registry's provider_price_defaults (source of record
        for models the AWS Pricing API can't price) via _provider_price_default — NOT
        hardcoded here; None when absent → base_price_usd stays unset → 'unavailable'.
        prompt_guidance is model-specific steering seeded from official docs; empty
        string ("") for edit/utility services that take no descriptive prompt."""
        mid = model_id.lower()

        def _pp(purpose):
            return _provider_price_default("image", f"{provider}|{purpose}")

        # Stability AI services — classify by model ID keywords
        if provider == "Stability AI":
            if "inpaint" in mid:
                return "inpainting", "stability_inpaint", 10000, _pp("inpainting"), 0, ""
            if "outpaint" in mid:
                return "outpainting", "stability_outpaint", 10000, _pp("outpainting"), 0, ""
            if "erase" in mid:
                return "erase", "stability_erase", 0, _pp("erase"), 0, ""
            if "search-replace" in mid or "search_replace" in mid:
                return "search_replace", "stability_search_replace", 10000, _pp("search_replace"), 0, ""
            if "search-recolor" in mid or "recolor" in mid:
                return "search_recolor", "stability_search_recolor", 10000, _pp("search_recolor"), 0, ""
            if "control-sketch" in mid:
                return "control_sketch", "stability_control", 10000, _pp("control_sketch"), 0, ""
            if "control-structure" in mid:
                return "control_structure", "stability_control", 10000, _pp("control_structure"), 0, ""
            if "style-guide" in mid:
                return "style_guide", "stability_control", 10000, _pp("style_guide"), 0, ""
            if "style-transfer" in mid:
                return "style_transfer", "stability_style_transfer", 10000, _pp("style_transfer"), 0, ""
            if "remove-background" in mid:
                return "remove_background", "stability_remove_bg", 0, _pp("remove_background"), 0, ""
            if "creative-upscale" in mid:
                return "upscale_creative", "stability_upscale", 10000, _pp("upscale_creative"), 0, ""
            if "conservative-upscale" in mid:
                return "upscale_conservative", "stability_upscale", 10000, _pp("upscale_conservative"), 0, ""
            if "fast-upscale" in mid:
                return "upscale_fast", "stability_upscale", 0, _pp("upscale_fast"), 0, ""
            # Default: text-to-image (SD 3.5, Stable Image Ultra/Core)
            opw = 120 if "sd3" in mid or "3.5" in mid else 100
            return "text_to_image", "stability_text_to_image", 2000, _pp("text_to_image"), opw, _STABILITY_T2I_GUIDANCE

        # Amazon models (Nova Canvas, Titan Image)
        if provider == "Amazon":
            if "titan" in mid:
                return "text_to_image", "amazon_text_to_image", 900, _pp("text_to_image"), 40, _AMAZON_DEFAULT_GUIDANCE
            # Nova Canvas — caption-style, drops trailing detail on long prompts
            return "text_to_image", "amazon_text_to_image", 900, _pp("text_to_image"), 55, _NOVA_CANVAS_GUIDANCE

        return "text_to_image", None, 900, None, 80, ""

    def _classify_video_model(model_id: str, provider: str, input_modalities: list[str]):
        """Determine format_family, pricing, and optimal_prompt_words for video models.
        base_price comes from the registry (provider_price_defaults), not hardcoded."""
        mid = model_id.lower()
        has_image_input = "IMAGE" in input_modalities
        if "nova-reel" in mid:
            return "text_to_video", "nova_reel", 512, _provider_price_default("video", "nova_reel"), has_image_input, 50
        if "ray" in mid or "luma" in mid:
            return "text_to_video", "luma_ray", 5000, _provider_price_default("video", "luma_ray"), has_image_input, 60
        return "text_to_video", None, 512, None, has_image_input, 50

    def _register_chat_model(m: dict, region: str, registry: dict, registered: list):
        """Register a text LLM into the chat_models registry section."""
        model_id = m.get("modelId", "")
        provider = m.get("providerName", "")
        inp = m.get("inputModalities", [])
        inference_types = m.get("inferenceTypesSupported", [])

        effective_id = model_id
        if "INFERENCE_PROFILE" in inference_types and not _has_geo_prefix(model_id):
            # Discovered profiles decide the prefix (_select_profile_prefix); fall back to the
            # region heuristic only when this model isn't in the profile map.
            sel = _select_profile_prefix(model_id, region, profile_map)
            prefix = sel if sel is not None else _profile_prefix_for_region(region, profile_map)
            effective_id = prefix + model_id
        avail_profiles = sorted((profile_map.get(_normalize_model_id(model_id)) or {}).keys())
        residency_scope = _residency_scope(effective_id, model_id)

        chat_models = registry.setdefault("chat_models", {})

        # Key: provider-stripped, version-safe (dotted-version ids like
        # zai.glm-4.7 must NOT collapse to a bare "7" — see _chat_model_key).
        key = _chat_model_key(model_id)
        family_key = _model_family_key(model_id)

        # Check if a model from this family is already registered
        existing_key = None
        for k, cfg in chat_models.items():
            if _model_family_key(_strip_geo_prefix(cfg.get("model_id", ""))) == family_key:
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
            # Plain (in-Region) invocation differs by Region — some Regions serve
            # the model only through an inference profile.
            existing["on_demand_regions"] = sorted(
                set(existing.get("on_demand_regions") or [])
                | ({region} if "ON_DEMAND" in inference_types else set()))

            # Keep the NEWEST model version in the family.
            # Compare by lifecycle (ACTIVE > LEGACY) then by model name/id.
            existing_lifecycle = existing.get("lifecycle_status", "ACTIVE")
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
                existing["inference_types"] = inference_types
                existing["inference_profiles"] = avail_profiles
                existing["residency_scope"] = residency_scope
                # Keep the existing key — renaming causes conflicts between
                # base and user registry files on reload.
            # Lifecycle for pre-existing entries is refreshed authoritatively by
            # _backfill_chat_lifecycle() after discovery — the per-family dedup here
            # (inference-profile ids, context suffixes) can't reliably self-match.
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
            "on_demand_regions": [region] if "ON_DEMAND" in inference_types else [],
            "inference_profiles": avail_profiles,
            "residency_scope": residency_scope,
            **_lifecycle_fields(m),
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
                    backfill.update(_lifecycle_fields(m))  # refresh lifecycle every Sync
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
                **_lifecycle_fields(m),
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
        purpose, family, prompt_limit, base_price, optimal_words, model_guidance = _classify_image_model(model_id, provider, inp)
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
                backfill.update(_lifecycle_fields(m))  # refresh lifecycle every Sync
                if "streaming_supported" not in existing_cfg:
                    backfill["streaming_supported"] = m.get("responseStreamingSupported", False)
                if not existing_cfg.get("customizations_supported"):
                    backfill["customizations_supported"] = m.get("customizationsSupported", [])
                if not existing_cfg.get("optimal_prompt_words") and optimal_words:
                    backfill["optimal_prompt_words"] = optimal_words
                # Per-model prompt guidance (model-specific steering). Stored
                # top-level for Bedrock foundation models (no invoke block);
                # get_model_guidance() reads invoke.prompt_guidance first, then
                # top-level. Only backfill when absent in BOTH places, so a
                # user's manual edit is never overwritten.
                if (model_guidance
                        and not existing_cfg.get("prompt_guidance")
                        and not existing_cfg.get("invoke", {}).get("prompt_guidance")):
                    backfill["prompt_guidance"] = model_guidance

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

        # Models that require INFERENCE_PROFILE need a geo/global prefix, chosen by
        # _select_profile_prefix from the discovered profiles (global. where offered
        # unless a residency is configured); fall back to the region heuristic when
        # the model isn't in the discovered profile map.
        inference_types = m.get("inferenceTypesSupported", [])
        effective_model_id = model_id
        if "INFERENCE_PROFILE" in inference_types and not _has_geo_prefix(model_id):
            sel = _select_profile_prefix(model_id, region, profile_map)
            prefix = sel if sel is not None else _profile_prefix_for_region(region, profile_map)
            effective_model_id = prefix + model_id

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
            **_lifecycle_fields(m),
            "streaming_supported": m.get("responseStreamingSupported", False),
            "customizations_supported": m.get("customizationsSupported", []),
            "extra_body": {},
        }
        if optimal_words:
            config["optimal_prompt_words"] = optimal_words
        if model_guidance:
            config["prompt_guidance"] = model_guidance  # model-specific steering (see _classify_image_model)

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
        # JSON-safe {base: {prefix: [regions]}} for this Region — accumulated by the
        # Sync (survives the transactional registry reloads above) and consumed by
        # the residency post-pass.
        "inference_profiles": {b: {p: sorted(r) for p, r in profs.items()}
                               for b, profs in profile_map.items()},
        "message": (
            f"Registered {len(registered)} new, updated {len(updated)} existing"
            if registered or updated else "No changes — all models already registered"
        ),
    }


def _fetch_image_pricing() -> dict:
    """Per-image pricing from the AWS Price List (SPEC §14.2).

    Returns a dict keyed 'model_name|region|quality|size' (Nova Canvas-style
    rows whose usagetype carries quality + size) plus a 'model_name|region'
    simple key. Marketplace-sold models (Stable Diffusion 3.5 Large, Stable
    Image Ultra/Core) live under AmazonBedrockFoundationModels with ONE flat
    per-image price → simple key only. Empty dict on failure.
    """
    from backend.services.official_pricing import price_list_products, on_demand_dimensions, product_model_name
    try:
        products = price_list_products()
    except Exception as exc:
        logger.warning("Failed to fetch pricing data: %s", exc)
        return {}
    prices = {}
    for pd in products:
        attrs = pd.get("product", {}).get("attributes", {})
        usage = attrs.get("usagetype", "") or ""
        model_name = product_model_name(attrs)
        region = attrs.get("regionCode", "") or ""
        for unit, price in on_demand_dimensions(pd):
            if unit.lower() != "image" or not (model_name and region and price > 0):
                continue
            if pd.get("_service_code") == "AmazonBedrockFoundationModels":
                # e.g. 'USE1-MP:USE1_created_image-Units' — one output-image price.
                prices.setdefault(f"{model_name}|{region}", {
                    "model_name": model_name, "region": region,
                    "price_usd": price, "usage_type": usage[:80],
                })
                continue
            # Parse quality and size from usage type
            # e.g. "USE1-NovaCanvas-T2I-1024-Premium"
            is_t2i = "T2I" in usage.upper()

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

    logger.debug("Fetched %d image pricing entries from the AWS Price List", len(prices))
    return prices


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


def _refresh_gpu_instance_rates(registry: dict) -> int:
    """Overwrite the deploy-selection table `custom_model_catalog.gpu_instances[*]
    .cost_per_hour_usd` with the LIVE per-region rates already fetched into
    `sagemaker_pricing`, so the deploy UI and the cost math read the SAME source
    (they previously drifted). Reference region: us-east-1, else us-west-2, else any
    synced region for that instance. No new AWS call — reuses sagemaker_pricing.
    Returns the count of instance rows updated."""
    sm = registry.get("sagemaker_pricing", {}) or {}
    gi = (registry.get("custom_model_catalog", {}) or {}).get("gpu_instances", {})
    if not sm or not gi:
        return 0
    updated = 0
    for inst, specs in gi.items():
        if not isinstance(specs, dict):
            continue
        rate = (sm.get(f"{inst}|us-east-1") or sm.get(f"{inst}|us-west-2")
                or next((v for k, v in sm.items() if k.startswith(inst + "|") and v), None))
        if rate and specs.get("cost_per_hour_usd") != round(float(rate), 4):
            specs["cost_per_hour_usd"] = round(float(rate), 4)
            updated += 1
    if updated:
        logger.info("Refreshed %d gpu_instances hourly rate(s) from live sagemaker_pricing", updated)
    return updated


def _fetch_video_pricing(regions: list[str] | None = None) -> dict:
    """Per-region, per-SECOND video pricing from the AWS Price List (SPEC §14.2):
    Nova Reel (AmazonBedrock, unit 'video' billed per second) and Luma Ray
    (AmazonBedrockService 'Ray v2' / Marketplace 'Luma Ray2', unit 'Second').
    Rows are tiered by output resolution — the `imageresolution` attribute or the
    usagetype ('…-Medfps-HDRes' / '…StandardRes') — recorded as `by_tier`
    ({"hd": 1.5, "standard": 0.75}); `price_per_second` is the HD rate (the
    default output). Returns
    { "<model>|<region>": {"model_name","region","price_per_second","by_tier","usage_type"} }.
    Empty on failure."""
    from backend.services.official_pricing import price_list_products, on_demand_dimensions, product_model_name
    try:
        products = price_list_products()
    except Exception as exc:
        logger.warning("Failed to fetch video pricing: %s", exc)
        return {}
    target = set(regions or [])
    prices: dict = {}
    for pd in products:
        attrs = pd.get("product", {}).get("attributes", {})
        model_name = product_model_name(attrs)
        region = attrs.get("regionCode", "") or ""
        if not model_name or not region or (target and region not in target):
            continue
        usage = attrs.get("usagetype", "") or ""
        tier = (attrs.get("imageresolution") or "").lower()
        if tier not in ("hd", "standard"):
            u = usage.lower()
            tier = "hd" if "hdres" in u else "standard" if "standardres" in u else "hd"
        for unit, price in on_demand_dimensions(pd):
            if unit.lower() not in ("video", "second", "seconds") or price <= 0:
                continue
            e = prices.setdefault(f"{model_name}|{region}", {
                "model_name": model_name, "region": region, "by_tier": {},
                "usage_type": usage[:80],
            })
            e["by_tier"].setdefault(tier, price)
    for e in prices.values():
        e["price_per_second"] = e["by_tier"].get("hd") or min(e["by_tier"].values())
    logger.info("Fetched %d video pricing entries from the AWS Price List", len(prices))
    return prices


def _record_infra_pricing(registry: dict) -> int:
    """Record standard per-region S3 infra rates into `registry.infra_pricing` so
    cost tracking is registry-SOURCED rather than relying on cost_tracker's built-in
    fallback. Only fills regions NOT already present, so a manual
    registry override is never clobbered. (S3 request/transfer pricing is effectively
    static; a live fetch adds fragility for fractions-of-a-cent, so we seed the known
    standard rates into the registry as the source of record.) Returns rows added."""
    # Standard per-region S3 rates (request Tier1/Tier2 + data-transfer-out). This is
    # the recording SEED; cost_tracker reads only the registry at compute time.
    _S3_STANDARD_RATES = {
        "us-east-1": {"s3_put_per_1k": 0.005, "s3_get_per_1k": 0.0004, "s3_transfer_out_per_gb": 0.09},
        "us-west-2": {"s3_put_per_1k": 0.005, "s3_get_per_1k": 0.0004, "s3_transfer_out_per_gb": 0.09},
        "ap-southeast-2": {"s3_put_per_1k": 0.0055, "s3_get_per_1k": 0.00044, "s3_transfer_out_per_gb": 0.114},
        "eu-west-1": {"s3_put_per_1k": 0.0054, "s3_get_per_1k": 0.00043, "s3_transfer_out_per_gb": 0.09},
    }
    infra = registry.setdefault("infra_pricing", {})
    added = 0
    for region, rates in _S3_STANDARD_RATES.items():
        if region not in infra:
            infra[region] = dict(rates)
            added += 1
    if added:
        logger.info("Recorded standard S3 infra pricing for %d region(s) into the registry", added)
    return added


def _provider_price_default(kind: str, key: str):
    """Look up a per-unit price from the registry's `provider_price_defaults` —
    the REGISTRATION seed for a newly discovered image/video model, until the
    same Sync's official-pricing pass (_apply_media_pricing) replaces it with
    the AWS-published rate. `kind` is 'image' or 'video'; `key` is
    'Provider|purpose' (image) or the family (video). Returns None when absent →
    base_price_usd stays unset → 'unavailable'. Prices live in the registry,
    NOT hardcoded in code."""
    try:
        from backend.services.model_registry import get_registry
        return (get_registry().get("provider_price_defaults", {}) or {}).get(kind, {}).get(key)
    except Exception:
        return None


def _official_pricing_model_ids(registry: dict) -> set:
    """Foundation-model ids (geo prefix stripped) of every Bedrock model in the
    registry — the ids agreement offers are looked up by. Custom-hosted and
    imported models (SageMaker / ARNs) are excluded: they're priced per hour."""
    from backend.services.official_pricing import base_model_id
    ids = set()
    for section in ("chat_models", "image_models", "video_models"):
        for cfg in (registry.get(section, {}) or {}).values():
            if not isinstance(cfg, dict) or cfg.get("model_source") in ("custom_hosted", "imported", "custom"):
                continue
            mid = base_model_id(cfg.get("model_id") or "")
            if "." in mid and not mid.startswith("arn:"):
                ids.add(mid)
    voice = ((registry.get("categories", {}) or {}).get("voice") or {}).get("current")
    if voice:
        ids.add(base_model_id(voice))
    return ids


def _fetch_llm_pricing(registry: dict | None = None) -> dict:
    """Gather every official Amazon Bedrock price source (SPEC §14.1):

      * AWS Price List token rows — by display name AND by exact model id (the
        `-mantle-` usagetypes embed the id). One shared, uncapped scan.
      * Agreement-offer rate cards for every Bedrock model in `registry`
        (Marketplace-sold models: Claude, OpenAI frontier, Stability, …).
      * Bedrock User Guide model cards (price tables + long-context threshold).

    Token rates are USD per 1K; standard on-demand tier only (Batch / Flex /
    Priority / Reserved / cache tiers are never requested by ArtSmoker).
    Returns {"by_name", "by_id", "codes", "offers", "cards"}, or {} when every
    source failed (callers keep the previously synced prices)."""
    from backend.services import official_pricing as op
    try:
        products = op.price_list_products()
    except Exception as exc:
        logger.warning("Price List fetch failed: %s", exc)
        products = []
    codes = op.region_code_map(products)
    tokens = op.price_list_token_rates(products) if products else {"by_name": {}, "by_id": {}}
    offers: dict = {}
    if registry:
        try:
            offers = op.agreement_rate_cards(_official_pricing_model_ids(registry))
        except Exception as exc:
            logger.warning("Agreement-offer pricing skipped: %s", exc)
    try:
        cards = op.model_card_pricing()
    except Exception as exc:
        logger.warning("Model-card pricing skipped: %s", exc)
        cards = {}
    if not (tokens["by_name"] or tokens["by_id"] or offers or cards):
        return {}
    logger.info("Official pricing: %d named + %d id-keyed Price List rate sets, %d rate card(s), %d model card(s)",
                len(tokens["by_name"]), len(tokens["by_id"]), len(offers), len(cards))
    # Vendor names for name matching — learned from the Price List and the
    # registry's own models (ListFoundationModels providers), never a fixed list.
    models = [cfg for section in ("chat_models", "image_models", "video_models")
              for cfg in ((registry or {}).get(section, {}) or {}).values()]
    return {"by_name": tokens["by_name"], "by_id": tokens["by_id"], "codes": codes,
            "offers": offers, "cards": cards, "vendors": op.vendor_names(products, models)}


def _id_candidates(base_id: str) -> list:
    """A foundation-model id and its revision-less forms, for exact-id lookups:
    'openai.gpt-oss-120b-1:0' → [..., 'openai.gpt-oss-120b']."""
    out = [base_id.lower()]
    for pat in (r":\d+$", r"-v\d+(:\d+)?$", r"-\d+:\d+$"):
        c = _re.sub(pat, "", out[0])
        if c not in out:
            out.append(c)
    return out


def _by_region_index(flat: dict) -> dict:
    """{'<key>|<region>': rates} → {key: {region: rates}}."""
    idx: dict = {}
    for k, rates in (flat or {}).items():
        key, _, region = k.rpartition("|")
        idx.setdefault(key, {})[region] = rates
    return idx


def _pinned_rates(by_region: dict, cfg: dict):
    """The rate set for a model's pinned Region (else a Region it's available
    in, else any) — the display / default price."""
    from backend.services.official_pricing import rates_for_region
    for r in [cfg.get("region")] + list(cfg.get("available_regions") or []):
        rs = rates_for_region(by_region, r)
        if rs:
            return rs
    return next(iter(by_region.values()), None)


def _apply_llm_pricing(registry: dict, llm_pricing: dict) -> int:
    """Stamp official token prices onto every chat_models entry (SPEC §14.1).

    Source precedence per model — the first that prices it wins:
      1. Agreement-offer rate card for its exact foundation-model id;
      2. Price List rows keyed by the exact model id (Mantle usagetypes);
      3. its model card's price table;
      4. Price List rows matched by display name (NameIndex).
    The model card's long-context threshold applies whatever the source.

    Writes `token_pricing` = {"source", "rates" (pinned Region), "by_region"
    (only when rates differ by Region), "long_context_threshold_tokens"},
    `unit_pricing` for non-token units (search units, video seconds), and the
    flat input/output_price_per_1k for the pinned id (display + legacy). A model
    no source prices loses stale prices and reads "pricing unavailable" — except
    a hand-stamped `pricing_source` price, kept until AWS publishes one.
    Returns the count of entries priced."""
    if not llm_pricing:
        return 0
    import json
    from backend.services import official_pricing as op

    codes = llm_pricing.get("codes") or {}
    offers = llm_pricing.get("offers") or {}
    cards = llm_pricing.get("cards") or {}
    by_id = _by_region_index(llm_pricing.get("by_id"))
    by_name = _by_region_index(llm_pricing.get("by_name"))
    names = op.NameIndex(by_name.keys(), llm_pricing.get("vendors") or ())

    priced = 0
    unpriced = []
    for key, cm in (registry.get("chat_models", {}) or {}).items():
        invoked = cm.get("model_id") or ""
        base = op.base_model_id(invoked)
        cands = _id_candidates(base)
        card = next((cards[c] for c in cands if c in cards), None) or cards.get(base)
        by_region, units, source = {}, {}, None
        if base in offers:
            parsed = op.parse_token_rate_card(offers[base], codes)
            by_region, units = parsed["rates"], parsed["units"]
            source = "agreement_offer" if by_region else None
        if not by_region:
            by_region = next((by_id[c] for c in cands if c in by_id), {})
            source = "price_list" if by_region else None
        if not by_region and card and card.get("rates"):
            by_region, source = {"*": card["rates"]}, "model_card"
        if not by_region:
            # Tied names are one model listed twice — merge, the wider-coverage
            # name winning a Region both price.
            tied = names.matches(cm.get("label") or "", invoked, cm.get("provider") or "")
            for n in sorted(tied, key=lambda n: len(by_name.get(n, {}))):
                by_region = {**by_region, **by_name.get(n, {})}
            source = "price_list" if by_region else None

        rates = _pinned_rates(by_region, cm) if by_region else None
        io = op.pick_token_rate(rates, invoked) if rates else None
        if not io or not (io[0] or io[1]):
            if not cm.get("pricing_source"):
                for fld in ("input_price_per_1k", "output_price_per_1k", "token_pricing_by_region",
                            "token_pricing", "unit_pricing"):
                    cm.pop(fld, None)
            unpriced.append(key)
            continue
        cm["input_price_per_1k"], cm["output_price_per_1k"] = io
        tp = {"source": source, "rates": rates}
        # Keep the full per-Region map ONLY when rates actually differ — most
        # models price uniformly, and the pinned set suffices.
        if len({json.dumps(v, sort_keys=True) for v in by_region.values()}) > 1:
            tp["by_region"] = by_region
        if card and card.get("threshold_tokens"):
            tp["long_context_threshold_tokens"] = card["threshold_tokens"]
        cm["token_pricing"] = tp
        u = _pinned_rates(units, cm) if units else None
        if u:
            cm["unit_pricing"] = u
        else:
            cm.pop("unit_pricing", None)
        cm.pop("token_pricing_by_region", None)  # superseded by token_pricing.by_region
        cm.pop("pricing_source", None)  # official price supersedes a manual stamp
        priced += 1
    if unpriced:
        logger.info("No official token price for %d chat model(s) (not in the Price List, "
                    "rate cards or model cards): %s", len(unpriced), ", ".join(sorted(unpriced)))

    # Voice category (Nova Sonic): speech-input models never enter chat_models
    # (the sync filter requires TEXT input), so stamp the token price onto the
    # category entry itself — _registry_llm_price checks categories as its last
    # step, which prices voice transcription (image_studio.voice_input.cost).
    voice = (registry.get("categories", {}) or {}).get("voice")
    if isinstance(voice, dict) and voice.get("current"):
        # Normalize the FULL model id (keep the ":0" version digit): e.g.
        # "amazon.nova-2-sonic-v1:0" → {amazon,nova,2,sonic,v1,0}, so the
        # Price List's "Nova Sonic 2.0" ({nova,sonic,2,0}) is a subset.
        vtok = set(op.norm_name(voice["current"]).split())
        # BEST match (most tokens), not first: "Nova Sonic" and "Nova Sonic 2.0"
        # are both subsets of nova-2-sonic-v1 — the longer name is the right one.
        best = None
        for pname, byreg in by_name.items():
            ptok = set(op.norm_name(pname).split())
            if ptok and ptok.issubset(vtok) and (best is None or len(ptok) > len(best[0])):
                best = (ptok, byreg)
        if best:
            byreg = best[1]
            px = op.rates_for_region(byreg, voice.get("region")) or next(iter(byreg.values()), None)
            io = op.pick_token_rate(px, voice["current"]) if px else None
            if not io and px:
                io = (px.get("input_per_1k", px.get("global_input_per_1k", 0)),
                      px.get("output_per_1k", px.get("global_output_per_1k", 0)))
            if io and (io[0] or io[1]):
                voice["input_price_per_1k"], voice["output_price_per_1k"] = io
                priced += 1
    return priced


def _match_offer_dimension(rows: list, label: str):
    """The rate-card rows for one model out of a SHARED offer — Stability's
    image services all carry one 13-dimension card ('One image output from
    Creative Upscale', …). The description words after 'from' must all appear
    in the model's label; the most specific (longest) description wins and an
    ambiguous tie prices nothing (never a guess)."""
    from backend.services.official_pricing import norm_name
    ltoks = set(norm_name(label).split())
    best, best_len, tie = None, 0, False
    for desc in {r["description"] for r in rows}:
        d = desc.split(" from ", 1)[-1]
        dtoks = set(norm_name(d).split())
        if not dtoks or not dtoks <= ltoks:
            continue
        if len(dtoks) > best_len:
            best, best_len, tie = desc, len(dtoks), False
        elif len(dtoks) == best_len:
            tie = True
    if not best or tie:
        return []
    return [r for r in rows if r["description"] == best]


def _apply_media_pricing(registry: dict, official: dict) -> int:
    """Price every Bedrock image + video model from official sources (SPEC §14.2).

    Image models: an agreement-offer rate card (Stability image services) takes
    precedence; else the Price List image rows (`image_pricing`, from
    _fetch_image_pricing) matched to the model by NameIndex. Video models: the
    Price List video rows (`video_pricing`, per-resolution `by_tier`).
    Matched rows are re-keyed under the model's registry key
    ('<model_key>|<region>[|quality|size]') so cost resolution is an exact
    lookup, and base_price_usd / base_price_per_second_usd is set to the pinned
    Region's official rate. Returns the count of models priced."""
    from backend.services import official_pricing as op
    codes = (official or {}).get("codes") or {}
    offers = (official or {}).get("offers") or {}
    vendors = (official or {}).get("vendors") or ()
    priced = 0
    unpriced = []

    img = registry.setdefault("image_pricing", {})
    img_names = op.NameIndex({v.get("model_name") for v in img.values()
                              if isinstance(v, dict) and v.get("model_name")
                              and v.get("source") != "agreement_offer"}, vendors)
    img_by_name: dict = {}
    for k, v in img.items():
        if isinstance(v, dict) and v.get("model_name") and v.get("source") != "agreement_offer":
            img_by_name.setdefault(v["model_name"], {})[k] = v
    for key, cfg in (registry.get("image_models", {}) or {}).items():
        if not isinstance(cfg, dict) or cfg.get("model_source") in ("custom_hosted", "imported", "custom"):
            continue
        label = cfg.get("label") or ""
        base = op.base_model_id(cfg.get("model_id") or "")
        per_region: dict = {}
        rows = op.parse_media_rate_card(offers.get(base) or [], codes)
        if rows:
            regions = {r["region"] for r in rows}
            chosen = rows if all(len({r["price"] for r in rows if r["region"] == g}) == 1
                                 for g in regions) else _match_offer_dimension(rows, label)
            for r in chosen:
                img[f"{key}|{r['region']}"] = {"model_name": key, "region": r["region"],
                                               "price_usd": r["price"], "usage_type": r["dimension"][:80],
                                               "source": "agreement_offer"}
                per_region[r["region"]] = r["price"]
        if not per_region:
            tied = img_names.matches(label, cfg.get("model_id") or "", cfg.get("provider") or "")
            merged: dict = {}  # one model listed under tied names — wider coverage wins
            for n in sorted(tied, key=lambda n: len(img_by_name.get(n) or {})):
                merged.update((k.split("|", 1)[1], (n, v)) for k, v in (img_by_name.get(n) or {}).items())
            for rest, (name, v) in merged.items():
                if name != key:
                    img[f"{key}|{rest}"] = dict(v, model_name=key)
                simple = "|" not in rest or (v.get("is_t2i") and v.get("quality") == "standard"
                                             and v.get("size") == "1024")
                if simple or v["region"] not in per_region:
                    per_region[v["region"]] = v["price_usd"]
        if not per_region:
            unpriced.append(key)
            continue
        pin = next((r for r in [cfg.get("region")] + list(cfg.get("available_regions") or [])
                    if r in per_region), None) or next(iter(per_region))
        cfg["base_price_usd"] = per_region[pin]
        priced += 1

    vid = registry.setdefault("video_pricing", {})
    vid_names = op.NameIndex({v.get("model_name") for v in vid.values()
                              if isinstance(v, dict) and v.get("model_name")}, vendors)
    for key, cfg in (registry.get("video_models", {}) or {}).items():
        if not isinstance(cfg, dict) or cfg.get("model_source") in ("custom_hosted", "imported", "custom"):
            continue
        tied = vid_names.matches(cfg.get("label") or "", cfg.get("model_id") or "", cfg.get("provider") or "")
        coverage = {n: sum(1 for v in vid.values() if isinstance(v, dict) and v.get("model_name") == n)
                    for n in tied}
        per_region = {}  # one model listed under tied names — wider coverage wins
        for n in sorted(tied, key=coverage.get):
            per_region.update({v["region"]: v for v in vid.values()
                               if isinstance(v, dict) and v.get("model_name") == n})
        if not per_region:
            unpriced.append(key)
            continue
        for region, v in per_region.items():
            if v.get("model_name") != key:
                vid[f"{key}|{region}"] = dict(v, model_name=key)
        pin = next((r for r in [cfg.get("region")] + list(cfg.get("available_regions") or [])
                    if r in per_region), None) or next(iter(per_region))
        cfg["base_price_per_second_usd"] = per_region[pin]["price_per_second"]
        priced += 1
    if unpriced:
        logger.info("No official media price for %d model(s): %s", len(unpriced), ", ".join(sorted(unpriced)))
    return priced


def _sync_official_pricing(registry: dict, progress=None) -> int:
    """The AWS Sync's official-pricing pass (both Sync paths): token prices
    onto chat models + per-image / per-second prices onto media models. Runs
    after the region scan (needs available_regions + the media Price List
    sections recorded earlier in the same Sync). Mutates `registry` in place —
    the caller saves. Returns models priced."""
    official = _fetch_llm_pricing(registry)
    if not official:
        return 0
    n_llm = _apply_llm_pricing(registry, official)
    n_media = _apply_media_pricing(registry, official)
    if progress:
        progress(f"Applied official pricing to {n_llm} chat and {n_media} image/video model(s).")
    logger.info("Official pricing applied: %d chat, %d image/video model(s)", n_llm, n_media)
    return n_llm + n_media


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

    # Fallback if dynamic discovery fails: the configured home Regions
    from backend.config import settings
    return sorted({settings.aws_region_models, settings.aws_region_images})


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
        # First time — no regions cached yet. Fall back to the configured home Regions.
        from backend.config import settings
        regions = sorted({settings.aws_region_models, settings.aws_region_images})
    return {"regions": regions, "count": len(regions)}


def _claude_version_tuple(model_id: str) -> tuple:
    """Parse a sortable version key from a Claude model_id.

    Returns (major, minor, date) so newer models sort higher. Examples:
      us.anthropic.claude-sonnet-4-6     → (4, 6, 0)
      us.anthropic.claude-opus-4-6-v1    → (4, 6, 0)  (patch -vN ignored for line)
      us.anthropic.claude-opus-5         → (5, 0, 0)  (major-only, no minor)
      us.anthropic.claude-sonnet-5       → (5, 0, 0)
      anthropic.claude-3-5-sonnet-20241022-v2:0 → (3, 5, 20241022)
    Unparseable IDs sort lowest. Used to find the newest Sonnet/Opus on Sync.
    """
    mid = model_id.lower()
    major = minor = date = 0
    # Named-tier form: claude-<tier>-<major>[-<minor>]. The minor is OPTIONAL — a
    # major-only release like claude-opus-5 has no minor (treat as .0). Minor is
    # 1-3 digits, never an 8-digit date (claude-sonnet-4-20250514 form).
    m = _re.search(r'claude-(?:opus|sonnet|haiku)-(\d+)(?:-(\d{1,3})(?!\d))?', mid)
    if m:
        major = int(m.group(1))
        minor = int(m.group(2)) if m.group(2) else 0
    else:
        # Older claude-<major>-<minor>-<tier> form (e.g. claude-3-5-sonnet).
        m = _re.search(r'claude-(\d+)-(\d{1,3})(?!\d)', mid)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
    dm = _re.search(r'-(\d{8})(?:-|$|:)', mid)
    if dm:
        date = int(dm.group(1))
    return (major, minor, date)


def _reconcile_mantle_models(registry: dict, scan_regions: list | None = None) -> int:
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
    from concurrent.futures import ThreadPoolExecutor
    from backend.services.mantle_client import (
        mantle_available, list_mantle_models, derive_model_apis,
        resolve_invoke_path, mantle_region_for, MANTLE_REGIONS,
    )

    if not mantle_available():
        logger.info("Mantle unavailable (no SDK/token) — skipping Mantle reconciliation")
        return 0

    # The Mantle catalog differs by Region (a model listed in one Region can 404 in
    # another), so list every Mantle Region and record where each model is served.
    region = mantle_region_for(None)
    mantle_regions = sorted(r for r in MANTLE_REGIONS
                            if scan_regions is None or r in scan_regions or r == region)
    with ThreadPoolExecutor(max_workers=min(8, len(mantle_regions) or 1)) as pool:
        listings = dict(zip(mantle_regions, pool.map(list_mantle_models, mantle_regions)))
    if not listings.get(region):
        return 0  # home listing failed → keep the recorded Mantle data
    served_in: dict[str, set] = {}
    for r, ids in listings.items():
        for mid in ids:
            served_in.setdefault(_normalize_model_id(mid), set()).add(r)
    mantle_ids = sorted({mid for ids in listings.values() for mid in ids})

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

    def _pin_mantle_region(cfg: dict, served: list) -> None:
        # A Mantle-served model's pin must be a Region whose Mantle lists it.
        cfg["mantle_regions"] = served
        if cfg.get("invoke_endpoint") == "bedrock-mantle" and served and cfg.get("region") not in served:
            cfg["region"] = region if region in served else served[0]

    for cfg in chat_models.values():
        cfg.pop("mantle_regions", None)  # re-derived below from this Sync's listings

    reconciled = 0
    for mid in mantle_ids:
        if _is_dupe_dated_alias(mid):
            continue
        served = sorted(served_in.get(_normalize_model_id(mid), ()))
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
            _pin_mantle_region(cfg, served)
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
                "lifecycle_status": "ACTIVE",
                "endpoints": ["bedrock-mantle"],
                "apis": apis,
                "invoke_endpoint": inv_ep,
                "invoke_api": inv_api,
            }
            _pin_mantle_region(chat_models[key], served)
            reconciled += 1
    logger.info("Mantle reconciliation: %d model(s) (of %d listed across %d Regions)",
                reconciled, len(mantle_ids), sum(1 for ids in listings.values() if ids))
    return reconciled


def _stamp_all_chat_model_routing(registry: dict) -> int:
    """(Re)derive endpoint/API routing for EVERY chat_models entry from the
    registry's api_compatibility matrix. Runs LAST in Sync (after Mantle
    reconciliation), so it's the single authoritative pass that makes routing
    reflect the current matrix + each model's discovered endpoint presence.

    It re-derives ALWAYS — not just for entries missing fields — because the
    matrix is the source of truth and derive_model_apis is deterministic. That's
    what makes a matrix edit (or a model gaining Converse on bedrock-runtime)
    propagate on the NEXT Sync with no code change. (The earlier skip-if-present
    optimization silently pinned already-stamped models to stale routing — e.g. a
    runtime-only GPT-5.x that never hit Mantle reconciliation.) Idempotent;
    per-model overrides in model_registry.user.json still apply over base at load.
    Returns the count whose routing actually changed.
    """
    from backend.services.mantle_client import derive_model_apis, resolve_invoke_path
    cm = registry.get("chat_models", {})
    changed = 0
    for cfg in cm.values():
        if not isinstance(cfg, dict):
            continue
        eps = cfg.get("endpoints") or ["bedrock-runtime"]
        cfg["endpoints"] = eps
        apis = derive_model_apis(
            cfg.get("model_id", ""), cfg.get("provider", ""),
            on_mantle=("bedrock-mantle" in eps), on_runtime=("bedrock-runtime" in eps))
        ep, api = resolve_invoke_path(apis)
        if (cfg.get("apis"), cfg.get("invoke_endpoint"), cfg.get("invoke_api")) != (apis, ep, api):
            cfg["apis"], cfg["invoke_endpoint"], cfg["invoke_api"] = apis, ep, api
            changed += 1
    if changed:
        logger.info("Routing: re-derived endpoint/API for %d chat model(s) from the registry matrix", changed)
    return changed


def _backfill_chat_lifecycle(registry: dict) -> int:
    """Refresh lifecycle (status / EOL / legacy times) for EVERY chat model from AWS.

    _register_chat_model keeps ONE representative per model family and stores
    inference-profile ids (``us.<id>``) plus context-window suffixes (``:200k``),
    so its in-loop match can't reliably refresh pre-existing entries — only freshly
    created ones pick up lifecycle. This pass fetches the authoritative
    ``modelLifecycle`` per pinned Region (it differs by Region) and applies it to each
    chat entry by a normalized model id that tolerates the geo prefix and context
    suffix. Mirrors the per-region backfill image/video models already get in
    discovery. Idempotent. Returns the number of entries updated.
    """
    cm = registry.get("chat_models", {})
    if not cm:
        return 0
    from backend.config import settings
    # Listed per pinned Region (cached): a model offered only outside the home
    # Region (an apac./eu. pin) is absent from the home Region's listing.
    lc_by_region: dict = {}

    def _lc_map(region: str) -> dict:
        if region not in lc_by_region:
            try:
                bedrock = boto3.Session().client("bedrock", region_name=region, config=_DISCOVERY_CONFIG)
                summaries = bedrock.list_foundation_models().get("modelSummaries", [])
                lc_by_region[region] = {m.get("modelId", ""): _lifecycle_fields(m)
                                        for m in summaries if m.get("modelId")}
            except Exception as exc:
                logger.warning("Chat lifecycle listing failed in %s: %s", region, exc)
                lc_by_region[region] = {}
        return lc_by_region[region]

    def _lookup(lc_map: dict, norm: str):
        fields = lc_map.get(norm)
        if fields is None:
            # Stored id may carry a context suffix (…-v1:0:200k) beyond the
            # canonical listing id (…-v1:0) — match on that boundary.
            for cid, f in lc_map.items():
                if cid and norm.startswith(cid + ":"):
                    return f
        return fields

    if not _lc_map(settings.aws_region_models):
        logger.warning("Chat lifecycle backfill skipped (listing failed)")
        return 0

    updated = 0
    for cfg in cm.values():
        if not isinstance(cfg, dict):
            continue
        norm = _strip_geo_prefix(cfg.get("model_id", ""))
        # Lifecycle is per Region (a model retired in one geography can still be
        # ACTIVE in another) — the pinned Region, where calls go, is authoritative.
        fields = _lookup(_lc_map(cfg["region"]), norm) if cfg.get("region") else None
        if fields is None:
            fields = _lookup(_lc_map(settings.aws_region_models), norm)
        if not fields:
            continue
        if (cfg.get("lifecycle_status") != fields["lifecycle_status"]
                or (cfg.get("end_of_life_time") or "") != fields["end_of_life_time"]
                or (cfg.get("legacy_time") or "") != fields["legacy_time"]):
            cfg.update(fields)
            updated += 1
    if updated:
        logger.info("Chat lifecycle backfill: refreshed %d chat model(s)", updated)
    return updated


def _auto_roll_llm_categories(registry: dict, progress=None) -> list:
    """Smartly roll fast_llm/complex_llm to the newest available Claude on Sync.

    End-users aren't tech-savvy and can get stranded on an older/deprecated model.
    On every AWS Sync we re-point:
      • fast_llm    → newest ACTIVE Claude **Sonnet** discovered in chat_models
      • complex_llm → newest ACTIVE Claude **Opus** discovered in chat_models
    Selection prefers cross-region inference profiles (any geo or global.), ACTIVE over LEGACY,
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
            lifecycle = (cfg.get("lifecycle_status") or "ACTIVE").upper()
            prefer_profile = 1 if _has_geo_prefix(cfg.get("model_id", "")) else 0
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

    def _route_region(model_cfg: dict, cur_region: str) -> str:
        """Region for a category switching to ``model_cfg``'s pinned id: keep the
        category's Region only if that id can be invoked from it (a geo profile
        routes only from its own geography), else the model's pinned Region."""
        from backend.routers.chat import _usable_regions
        usable = _usable_regions(model_cfg.get("model_id", ""), model_cfg.get("available_regions") or [],
                                 registry.get("inference_profiles", {}))
        return cur_region if cur_region in usable else (model_cfg.get("region") or cur_region)

    def _follow_repin(cat: dict, label: str) -> None:
        """Keep a category on its model's CURRENT pin. The Sync re-pins chat
        models (profile + Region); a category still holding another profile id of
        the same foundation model follows it — not an upgrade, so this applies to
        user-pinned categories too (the user picked the model, not the route)."""
        cur_id = cat.get("current", "")
        base = _strip_geo_prefix(cur_id)
        twins = [c for c in chat_models.values() if c.get("model_id")
                 and c.get("enabled", True) is not False
                 and _strip_geo_prefix(c["model_id"]) == base] if cur_id else []
        if not twins or any(c["model_id"] == cur_id for c in twins):
            return
        twin = twins[0]
        cat["current"] = twin["model_id"]
        cat["region"] = _route_region(twin, cat.get("region", ""))
        msg = f"{label}: follows the model's current pin → {cat['current']} ({cat['region']})"
        notices.append(msg)
        logger.info(msg)
        if progress:
            progress(msg)

    for cat_name, label in (("fast_llm", "Fast LLM"), ("complex_llm", "Complex LLM"),
                            ("fallback_llm", "Fallback LLM")):
        cat = (registry.get("categories", {}) or {}).get(cat_name)
        if isinstance(cat, dict):
            _follow_repin(cat, label)

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

        # Preserve the category's Region if the chosen id can be invoked from it.
        cur_region = cat.get("region", "")
        new_region = _route_region(cfg, cur_region)

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
                fb_region = _route_region(fb_cfg, fb_cat.get("region", ""))
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

    # ── New-tier discovery (generic; not locked to Sonnet/Opus) ──────────────
    # Auto-roll only manages the KNOWN tiers above (Sonnet→fast, Opus→fallback,
    # Opus→complex) — deliberately, so a brand-new tier is never SILENTLY swapped
    # into a category (it could be specialized or cheaper-but-weaker, not a true
    # upgrade for that slot). But we must never hide a new frontier model either:
    # any ACTIVE Claude of an UNMANAGED tier (e.g. 'fable', or a future tier) that
    # no category currently uses is surfaced as a notice so the user can assign it
    # in Model Settings. This is fully generic — it keys off whatever tier token
    # appears in the model_id, with zero hardcoded model names.
    managed_tiers = {"sonnet", "opus"}  # tiers the auto-roll already places
    assigned_bases = {  # by foundation model — any profile of it counts as assigned
        _strip_geo_prefix((registry.get("categories", {}).get(c, {}) or {}).get("current", ""))
        for c in ("fast_llm", "complex_llm", "fallback_llm", "voice")
    }
    seen_new_tiers = set()
    for k, cfg in chat_models.items():
        mid = (cfg.get("model_id", "") or "").lower()
        if "claude" not in mid:
            continue
        if (cfg.get("lifecycle_status") or "ACTIVE").upper() != "ACTIVE":
            continue
        m = _re.search(r'claude-([a-z]+)-', mid)  # the tier token, e.g. 'fable'
        tier = m.group(1) if m else None
        if not tier or tier in managed_tiers or tier in seen_new_tiers:
            continue
        if _strip_geo_prefix(cfg.get("model_id", "")) in assigned_bases:
            continue  # already assigned to a category — not "new/unused"
        seen_new_tiers.add(tier)
        label = cfg.get("label") or cfg.get("model_id", "")
        msg = (f"New Claude model available: {label} ({cfg.get('model_id','')}) — "
               f"a new '{tier}' tier not auto-assigned. Review in Model Settings to "
               f"use it for a category or in Chat Studio.")
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
        # Record on every chat_models entry of this foundation model (a capability
        # of the model, whichever profile was probed).
        base = _strip_geo_prefix(model_id)
        for cfg in registry.get("chat_models", {}).values():
            if _strip_geo_prefix(cfg.get("model_id") or "") == base:
                cfg["supports_temperature"] = supports
        logger.info("Param gate: %s supports_temperature=%s", model_id, supports)
    except Exception as exc:
        logger.debug("Temperature probe skipped for %s: %s", model_id, exc)


def _backfill_temperature_support(registry: dict, progress=None) -> int:
    """Populate `supports_temperature` on EVERY enabled, Converse-reachable chat
    model that doesn't have it yet — so the param gate is controlled by the REGISTRY
    (recorded on Sync), not a code heuristic that drifts as models update or new
    ones ship. Incremental: skips entries already recorded, so it's a one-time cost
    per model (≈0 on steady-state syncs). Mantle-routed models can't be Converse-
    probed and are skipped; the runtime self-heal (record_temperature_unsupported)
    still covers anything new between syncs. The value promotes to the git-tracked
    base registry (a model-intrinsic capability, identical for every account)."""
    probed = 0
    for cfg in registry.get("chat_models", {}).values():
        if cfg.get("enabled") is False:
            continue
        if cfg.get("supports_temperature") is not None:
            continue  # already known — don't re-probe
        if (cfg.get("lifecycle_status") or "ACTIVE").upper() == "EOL":
            continue
        # Only the bedrock-runtime Converse path can be probed this way.
        if (cfg.get("invoke_endpoint") or "bedrock-runtime") != "bedrock-runtime":
            continue
        mid, region = cfg.get("model_id"), cfg.get("region")
        if not mid or not region:
            continue
        _probe_and_record_temperature(mid, region, registry)
        if cfg.get("supports_temperature") is not None:
            probed += 1
    if probed:
        msg = f"Param gate: recorded temperature-support for {probed} chat model(s)"
        logger.info(msg)
        if progress:
            progress(msg)
    return probed


@router.get("/3d/export-targets")
async def export_targets():
    """Engine targets + per-engine prep-op option lists for the 3D export
    dropdowns (Target Engine / Texture Packing / LODs / Collision / Lightmap UV2).
    Config-driven; the packing list varies per engine (Unity can't use UE ORM)."""
    from backend.services import mesh_export
    return {
        "targets": [{"key": k, "label": v["label"]} for k, v in mesh_export.TARGETS.items()],
        "default": mesh_export.DEFAULT_TARGET,
        "options": {k: mesh_export.export_options_for(k) for k in mesh_export.TARGETS},
    }


@router.get("/blender/status")
async def blender_status():
    """Status of the FBX exporter's Blender (reused system copy vs our managed
    download, version, tools dir). Detection only — never triggers a download."""
    from backend.services import mesh_export
    import asyncio
    # Detection runs a subprocess smoke-test → offload off the event loop.
    return await asyncio.to_thread(mesh_export.get_status)


@router.post("/blender/update")
async def blender_update():
    """On-demand check + update of the MANAGED Blender copy (the Model Settings
    'Update Blender' button). Never touches a reused system Blender. May download
    a new build → run off the event loop."""
    from backend.services import mesh_export
    import asyncio
    return await asyncio.to_thread(mesh_export.check_for_update, True)


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
    # Batch-write mode: transactional system writes (add/update_image_model, …)
    # mutate the live registry directly instead of reload→save, so net-new in-memory
    # entries (e.g. a freshly-discovered chat model) aren't wiped mid-Sync (SPEC §17).
    from backend.services.model_registry import set_batch_write
    set_batch_write(True)
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
        # Keep the deploy-selection gpu_instances table in lockstep with the live
        # sagemaker_pricing (they previously drifted). No extra AWS call.
        _refresh_gpu_instance_rates(registry)

        # Step 2b-iii: Per-region, per-resolution VIDEO pricing ($/second — Nova
        # Reel, Luma Ray), from the same shared Price List scan.
        vid_pricing = _fetch_video_pricing(scan_regions)
        if vid_pricing:
            registry["video_pricing"] = vid_pricing
            logger.debug("Stored video pricing for %d model-region combos", len(vid_pricing))

        # Step 2b-iv: Record standard S3 infra pricing into the registry so S3 cost
        # tracking is registry-sourced (fills only missing regions; keeps overrides).
        _record_infra_pricing(registry)

        # Step 2c: Reset all available_regions before scanning — so stale regions
        # are pruned automatically. Each region scan in Step 3 re-adds itself.
        from backend.services.model_registry import update_image_model
        for key in list(registry.get("image_models", {}).keys()):
            update_image_model(key, {"available_regions": []})
        # Also reset chat_models regions
        for key in list(registry.get("chat_models", {}).keys()):
            registry["chat_models"][key]["available_regions"] = []
            if "on_demand_regions" in registry["chat_models"][key]:
                registry["chat_models"][key]["on_demand_regions"] = []

        # Step 3: Scan each ENABLED region for foundation + custom + imported models
        _progress(f"Scanning {len(scan_regions)} enabled regions for available models...")

        results = {}
        total_new = 0
        total_updated = 0
        total_custom = 0
        errors = 0
        # Accumulate discovered inference profiles in a LOCAL dict (immune to the
        # registry_transaction reloads inside auto_register's image writes). Assigned
        # to the registry once, in the transaction-free tail, before the residency
        # post-pass. {normalized_base: {prefix: set(covered Regions)}}.
        combined_profiles: dict = {}
        new_model_ids: set = set()  # net-new model ids this Sync (for an auditable log)

        for idx, region in enumerate(scan_regions):
            _progress(f"Scanning region {idx + 1}/{len(scan_regions)}: {region}...")
            try:
                result = asyncio.run(auto_register_image_models(region))
                results[region] = {
                    "new": result["new_count"],
                    "updated": result["updated_count"],
                }
                for r in result.get("registered", []):
                    if r.get("model_id"):
                        new_model_ids.add(r["model_id"])
                for base, profs in (result.get("inference_profiles") or {}).items():
                    dst = combined_profiles.setdefault(base, {})
                    for pre, regs in profs.items():
                        dst[pre] = sorted(set(dst.get(pre, [])) | set(regs))
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

        # Auditable net-new log: names the models registered fresh this Sync. With
        # batch-write mode these now persist, so a steady-state re-Sync should log 0.
        if new_model_ids:
            logger.info("Sync: %d net-new model(s) this run: %s",
                        len(new_model_ids), ", ".join(sorted(new_model_ids)))

        # Step 4b: Reconcile the bedrock-mantle catalog FIRST (before pruning) —
        # mark which discovered models are ALSO on Mantle, and add Mantle-only
        # models (e.g. OpenAI GPT-5.x, Claude Mythos) that never appear in the
        # bedrock-runtime listing. Stamps endpoints/apis/invoke_* per model.
        # Doing this before the prune ensures mantle-reachable models carry their
        # `endpoints` when the prune runs, so they're correctly exempted.
        _progress("Reconciling Amazon Bedrock Mantle model catalog...")
        try:
            mantle_added = _reconcile_mantle_models(registry, scan_regions)
            if mantle_added:
                _progress(f"Mantle: {mantle_added} model(s) reconciled")
        except Exception as exc:
            logger.warning("Mantle reconciliation skipped: %s", exc)

        # Publish the accumulated inference-profile map to the registry now — in the
        # transaction-free Sync tail, so it isn't wiped by the registry_transaction
        # reloads that ran during per-Region discovery. This is the single source of
        # truth the residency post-pass reads.
        registry["inference_profiles"] = {
            b: {p: sorted(r) for p, r in profs.items()}
            for b, profs in combined_profiles.items()
        }

        # Step 4b-bis: Pin post-pass — re-derive each model's Region + profile prefix
        # from the profiles discovered this Sync (global. where offered unless an
        # optional residency is configured in config.py). Order-independent; heals
        # drift (e.g. a us.<id> stuck on a non-US Region). Runs BEFORE routing/
        # lifecycle backfill so those see the corrected model_ids. Logs its outcome.
        try:
            _resolve_residency_pins(registry, _progress)
        except Exception as exc:
            logger.warning("Residency realignment skipped: %s", exc)

        # Step 4c: Backfill endpoint/API routing on EVERY chat model (incl.
        # pre-existing + update-path entries the per-model stamping missed), so
        # routing is explicit for all models. Runs even if Mantle is unavailable.
        try:
            _stamp_all_chat_model_routing(registry)
        except Exception as exc:
            logger.warning("Routing backfill skipped: %s", exc)

        # Step 4c-bis: Backfill lifecycle (status/EOL) on EVERY chat model. The
        # per-family dedup in _register_chat_model can't reliably self-match
        # pre-existing entries (inference-profile ids + context suffixes), so
        # only newly-created chat models got lifecycle; this makes it authoritative
        # for all (parity with image/video, which backfill per-region in discovery).
        try:
            _backfill_chat_lifecycle(registry)
        except Exception as exc:
            logger.warning("Chat lifecycle backfill skipped: %s", exc)

        # Step 4c-ter: Record temperature-support on every enabled Converse chat
        # model (registry-controlled param gate — no code heuristic to drift as
        # models update/ship). Incremental: only probes entries not already known.
        _progress("Recording model parameter support (temperature)...")
        try:
            _backfill_temperature_support(registry, _progress)
        except Exception as exc:
            logger.warning("Temperature-support backfill skipped: %s", exc)

        # Step 4d: Prune — disable models not found in any region this scan.
        disabled = []
        for key, cfg in list(registry.get("image_models", {}).items()):
            if cfg.get("model_source") == "custom_hosted":
                continue
            regions = cfg.get("available_regions", [])
            if not regions and cfg.get("enabled", True):
                # Mutate the accumulating registry dict directly (like the
                # chat/video loops below) — NOT via update_image_model(), whose
                # transaction would reload from disk mid-Sync and wipe the
                # in-memory changes accumulated so far. Sync is a single
                # read→accumulate→save-once batch (see the _save() at the end).
                registry["image_models"][key]["enabled"] = False
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

        # Step 4e: Official pricing (SPEC §14) — token prices onto chat_models,
        # per-image / per-second prices onto image + video models. Runs AFTER the
        # region scan, which fills the available_regions used to pick each
        # model's pinned rate.
        _progress("Applying official Amazon Bedrock pricing...")
        try:
            _sync_official_pricing(registry, _progress)
        except Exception as exc:
            logger.warning("Official pricing apply skipped: %s", exc)

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
        set_batch_write(False)   # restore normal reload→save transactions
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
        # Match by foundation model (any geo/global profile prefix), or by ARN
        if _strip_geo_prefix(stored_id) == base_model_id or stored_arn == base_model_arn:
            return {**cfg, "_registry_key": key, "_model_type": "image"}

    # Search video_models
    for key, cfg in registry.get("video_models", {}).items():
        stored_id = cfg.get("model_id", "")
        stored_arn = cfg.get("model_arn", "")
        if _strip_geo_prefix(stored_id) == base_model_id or stored_arn == base_model_arn:
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

    # Save registry. Like Sync, discovery is a read-once → accumulate across
    # (slow) AWS calls → save-once batch: a per-mutation transaction would wipe
    # the accumulation on reload, and wrapping the whole function would hold the
    # cross-process lock across the AWS scans. The wholesale save is intentional
    # (discovery data is AWS-authoritative) and remains atomic + locked.
    if registered or updated_list:
        _save()

    return {
        "region": region,
        "registered": registered,
        "updated": updated_list,
        "registered_count": len(registered),
        "updated_count": len(updated_list),
    }
