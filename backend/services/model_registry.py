"""Model Registry — manages all AI model configurations.

Loads from backend/model_registry.json, provides model info to the rest
of the system, and supports runtime updates via the admin API.

Replaces hardcoded model IDs in config.py and bedrock_client.py with
a dynamic, configurable registry.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "model_registry.json"       # Git-tracked defaults (READ-ONLY at runtime)
_USER_PREFS_PATH = Path(__file__).resolve().parent.parent / "model_registry.user.json"  # ALL runtime state (gitignored)
_registry: dict = {}

# Fields in model entries that are user preferences (saveable via _save_user_pref)
_USER_PREF_FIELDS = {"enabled"}


def _load():
    """Load the registry: git-tracked defaults + runtime state overlay.

    model_registry.json is the git-tracked base — contains code defaults,
    format families, and any models shipped with the repo. Updated ONLY by
    git pull (never written at runtime).

    model_registry.user.json contains ALL runtime modifications: Sync
    discoveries (models, regions, pricing), user preferences (enabled/disabled,
    category selections), custom model registrations, video settings. This file
    is gitignored and survives git pulls.

    Load order: main file → deep-merge user.json on top.
    New models added to main file via git pull appear automatically.
    """
    global _registry
    # 1. Load git-tracked defaults (read-only base)
    try:
        _registry = json.loads(_REGISTRY_PATH.read_text())
    except Exception as exc:
        logger.error("Failed to load model registry: %s", exc)
        _registry = {"categories": {}, "image_models": {}, "post_processing": {}}

    # 2. Deep-merge runtime state from user.json on top
    if _USER_PREFS_PATH.exists():
        try:
            runtime = json.loads(_USER_PREFS_PATH.read_text())
            merged = _deep_merge_runtime(runtime)
            logger.info("Model registry loaded: %d image models, %d chat models, %d categories (+%d runtime overrides)",
                        len(_registry.get("image_models", {})),
                        len(_registry.get("chat_models", {})),
                        len(_registry.get("categories", {})),
                        merged)
        except Exception as exc:
            logger.warning("Failed to load runtime state: %s", exc)
    else:
        logger.info("Model registry loaded: %d image models, %d categories",
                     len(_registry.get("image_models", {})),
                     len(_registry.get("categories", {})))


def _deep_merge_runtime(runtime: dict) -> int:
    """Deep-merge runtime state (user.json) into the loaded registry.

    For dict-of-models sections (image_models, chat_models, etc.):
      - Models in both files: runtime fields override main file fields
      - Models only in runtime: added (Sync discoveries, custom deploys)
      - Models only in main file: preserved (new models from git pull)

    For other sections (bedrock_regions, image_pricing, video_settings, etc.):
      - Runtime value replaces main file value entirely

    Returns count of entries merged.
    """
    # Sections that contain dict-of-models (merge at model level)
    MODEL_SECTIONS = {"image_models", "video_models", "chat_models", "post_processing",
                      "utility_models", "categories"}
    # Nested catalog sections: merge the 'models' sub-dict at model level
    CATALOG_SECTIONS = {"custom_model_catalog"}
    count = 0

    for key, value in runtime.items():
        if key == "_last_updated":
            _registry["last_updated"] = value
            continue

        if key in MODEL_SECTIONS and isinstance(value, dict) and isinstance(_registry.get(key), dict):
            # Deep merge: model-by-model
            for model_key, model_data in value.items():
                if isinstance(model_data, dict):
                    if model_key in _registry[key] and isinstance(_registry[key][model_key], dict):
                        # Both have this model — runtime fields override
                        _registry[key][model_key].update(model_data)
                    else:
                        # Model only in runtime (Sync discovery or custom deploy)
                        _registry[key][model_key] = model_data
                    count += 1
                else:
                    # Non-dict value (unlikely but handle gracefully)
                    _registry[key][model_key] = model_data
                    count += 1
        elif key in CATALOG_SECTIONS and isinstance(value, dict) and isinstance(_registry.get(key), dict):
            # Catalog section: deep merge 'models' sub-dict, replace others
            base = _registry[key]
            for sub_key, sub_value in value.items():
                if sub_key == "models" and isinstance(sub_value, dict) and isinstance(base.get("models"), dict):
                    for mk, md in sub_value.items():
                        if isinstance(md, dict) and mk in base["models"] and isinstance(base["models"][mk], dict):
                            # Merge: user fields override base, including nested invoke
                            if "invoke" in md and "invoke" in base["models"][mk]:
                                base["models"][mk]["invoke"].update(md["invoke"])
                                md_copy = {k: v for k, v in md.items() if k != "invoke"}
                                base["models"][mk].update(md_copy)
                            else:
                                base["models"][mk].update(md)
                        else:
                            base.setdefault("models", {})[mk] = md
                        count += 1
                else:
                    base[sub_key] = sub_value
                    count += 1
        else:
            # Non-model section — runtime replaces entirely
            _registry[key] = value
            count += 1

    return count


def _save():
    """Save the full registry to the runtime state file (user.json).

    NEVER writes to the git-tracked main file. All runtime changes —
    Sync discoveries, user preferences, custom model registrations,
    video settings — go to model_registry.user.json (gitignored).

    Preserves metadata keys (like _meta.aws_account_discovered) that
    were written by _save_user_pref() but aren't in the in-memory registry.
    """
    # Preserve existing metadata from user.json that _registry doesn't have
    existing_meta = {}
    if _USER_PREFS_PATH.exists():
        try:
            existing = json.loads(_USER_PREFS_PATH.read_text())
            # Preserve all underscore-prefixed keys except _last_updated
            for k, v in existing.items():
                if k.startswith("_") and k != "_last_updated":
                    existing_meta[k] = v
        except Exception:
            pass

    output = dict(_registry)
    # Strip sections that belong in the git-tracked main file, not user.json
    # (custom_model_catalog is in model_registry.json — only user OVERRIDES go to user.json)
    output.pop("custom_model_catalog", None)
    # Merge preserved metadata back in
    for k, v in existing_meta.items():
        if k not in output:
            output[k] = v
    output["_last_updated"] = datetime.now(timezone.utc).isoformat()
    _USER_PREFS_PATH.write_text(json.dumps(output, indent=2, default=str))
    if not _save._silent:
        logger.info("Model registry saved.")

_save._silent = False

# Fields per model that are user-specific and should NOT be promoted to the base file
_USER_ONLY_FIELDS = {"enabled", "deployment", "model_ready"}
# Top-level sections that are user-specific
_USER_ONLY_SECTIONS = {"_meta", "_last_updated", "video_settings", "license_acceptances"}


def promote_to_base():
    """Promote discovered data from in-memory registry to model_registry.json.

    Copies model definitions, regions, pricing, and capabilities to the
    git-tracked base file. Strips user-only fields (enabled, deployment).
    Then rewrites model_registry.user.json to contain only user-specific
    overrides (enabled/disabled, deployment config, video settings, metadata).

    Call this after a Sync to make discoveries available to all users via git.
    """
    base = json.loads(_REGISTRY_PATH.read_text())
    merged = dict(_registry)

    MODEL_SECTIONS = {"image_models", "video_models", "chat_models", "post_processing",
                      "utility_models", "categories"}

    # Step 1: Update base file with discovered data (strip user-only fields)
    for section in list(merged.keys()):
        if section in _USER_ONLY_SECTIONS:
            continue
        if section in MODEL_SECTIONS and isinstance(merged.get(section), dict):
            base_section = base.setdefault(section, {})
            for model_key, model_data in merged[section].items():
                if not isinstance(model_data, dict):
                    continue
                promoted = {k: v for k, v in model_data.items() if k not in _USER_ONLY_FIELDS}
                # Skip stale entries: not in base and no regions (orphan from old duplicates)
                if model_key not in base_section and not promoted.get("available_regions"):
                    if promoted.get("model_source") != "custom_hosted":
                        continue
                if model_key in base_section and isinstance(base_section[model_key], dict):
                    base_section[model_key].update(promoted)
                    for field in _USER_ONLY_FIELDS:
                        base_section[model_key].pop(field, None)
                else:
                    base_section[model_key] = promoted
            # Remove models from base that no longer exist in merged
            for k in list(base_section.keys()):
                if k not in merged[section]:
                    del base_section[k]

            # Clean up: remove entries with no regions (deprecated/stale)
            # and deduplicate entries sharing the same model_id
            if section in ("image_models", "video_models", "chat_models"):
                for k in list(base_section.keys()):
                    v = base_section[k]
                    if v.get("model_source") == "custom_hosted":
                        continue
                    if not v.get("available_regions"):
                        del base_section[k]
                        logger.debug("Cleanup: removed %s.%s (no available regions — deprecated)", section, k)

                model_id_map: dict[str, list[str]] = {}
                for k, v in base_section.items():
                    mid = v.get("model_id", "")
                    if mid:
                        model_id_map.setdefault(mid, []).append(k)
                for mid, keys in model_id_map.items():
                    if len(keys) <= 1:
                        continue
                    all_regions = set()
                    canonical = keys[0]
                    best_regions = 0
                    for k in keys:
                        regions = base_section[k].get("available_regions", [])
                        all_regions.update(regions)
                        if len(regions) > best_regions:
                            best_regions = len(regions)
                            canonical = k
                    base_section[canonical]["available_regions"] = sorted(all_regions)
                    for k in keys:
                        if k != canonical:
                            del base_section[k]
                            logger.debug("Dedup: removed %s.%s (duplicate of %s)", section, k, canonical)
        else:
            base[section] = merged.get(section, base.get(section))

    base["last_updated"] = datetime.now(timezone.utc).isoformat()
    _REGISTRY_PATH.write_text(json.dumps(base, indent=2, default=str))
    logger.info("Promoted discovered data to model_registry.json")

    # Step 2: Rewrite user file with only user-specific overrides
    user_output = {}

    # Preserve user-only top-level sections
    if _USER_PREFS_PATH.exists():
        try:
            existing_user = json.loads(_USER_PREFS_PATH.read_text())
            for k in _USER_ONLY_SECTIONS:
                if k in existing_user:
                    user_output[k] = existing_user[k]
        except Exception:
            pass

    # Per-model: only write user-only fields for models that exist in the
    # (deduped) base, plus custom deployments that are user-only by nature
    for section in MODEL_SECTIONS:
        merged_section = merged.get(section, {})
        base_section = base.get(section, {})
        user_section = {}
        for model_key, model_data in merged_section.items():
            if not isinstance(model_data, dict):
                continue
            user_fields = {}
            for field in _USER_ONLY_FIELDS:
                if field in model_data:
                    user_fields[field] = model_data[field]
            if not user_fields:
                continue
            # Write if model exists in base OR has deployment (custom model)
            if model_key in base_section or "deployment" in user_fields:
                user_section[model_key] = user_fields
        if user_section:
            user_output[section] = user_section

    # Preserve video_settings and license_acceptances from merged
    for k in ("video_settings", "license_acceptances"):
        if k in merged:
            user_output[k] = merged[k]

    user_output["_last_updated"] = datetime.now(timezone.utc).isoformat()
    _USER_PREFS_PATH.write_text(json.dumps(user_output, indent=2, default=str))
    logger.info("Cleaned user overrides in model_registry.user.json")

    return {
        "base_models": sum(len(base.get(s, {})) for s in MODEL_SECTIONS if isinstance(base.get(s), dict)),
        "user_overrides": sum(len(user_output.get(s, {})) for s in MODEL_SECTIONS if isinstance(user_output.get(s), dict)),
    }


def _save_user_pref(section: str, key: str, field: str, value):
    """Save a single user preference override to the user prefs file.

    Called when the user makes a preference change (enable/disable, category selection).
    """
    prefs = {}
    if _USER_PREFS_PATH.exists():
        try:
            prefs = json.loads(_USER_PREFS_PATH.read_text())
        except Exception:
            prefs = {}

    if section not in prefs:
        prefs[section] = {}
    if key not in prefs[section]:
        prefs[section][key] = {}
    prefs[section][key][field] = value
    prefs["_last_updated"] = datetime.utcnow().isoformat()

    _USER_PREFS_PATH.write_text(json.dumps(prefs, indent=2, default=str))


# ── Format family definitions (code as source of truth) ──────────────────

_STYLE_PRESETS = ["3d-model", "analog-film", "anime", "cinematic", "comic-book",
                  "digital-art", "enhance", "fantasy-art", "isometric", "line-art",
                  "low-poly", "modeling-compound", "neon-punk", "origami",
                  "photographic", "pixel-art", "tile-texture"]

_DEFAULT_FORMAT_FAMILIES = {
    "amazon_text_to_image": {
        "description": "Amazon text-to-image models (Nova Canvas, Titan Image). taskType/textToImageParams with pixel dimensions.",
        "prompt_path": "textToImageParams.text",
        "negative_prompt_path": "textToImageParams.negativeText",
        "seed_path": "imageGenerationConfig.seed",
        "dimensions_mode": "pixels",
        "dimensions_paths": {"width": "imageGenerationConfig.width", "height": "imageGenerationConfig.height"},
        "response_image_path": "images[0]",
        "body_template": {"taskType": "TEXT_IMAGE", "textToImageParams": {}, "imageGenerationConfig": {"numberOfImages": 1}},
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 1024, "description": "Descriptive caption"},
            "negative_prompt": {"type": "string", "required": False, "max_length": 1024},
            "width": {"type": "integer", "required": False, "default": 1024, "min": 320, "max": 4096, "step": 64},
            "height": {"type": "integer", "required": False, "default": 1024, "min": 320, "max": 4096, "step": 64},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 2147483647},
            "quality": {"type": "enum", "required": False, "options": ["standard", "premium"], "default": "premium", "path": "imageGenerationConfig.quality"},
        },
    },
    "stability_text_to_image": {
        "description": "Stability AI text-to-image models. Flat prompt field with aspect ratios.",
        "prompt_path": "prompt", "negative_prompt_path": "negative_prompt",
        "seed_path": "seed", "dimensions_mode": "aspect_ratio",
        "response_image_path": "images[0]",
        "body_template": {"output_format": "png"},
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 10000},
            "negative_prompt": {"type": "string", "required": False, "max_length": 10000},
            "aspect_ratio": {"type": "enum", "required": False, "options": ["1:1","16:9","9:16","3:2","2:3","4:5","5:4","21:9","9:21"], "default": "1:1"},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
            "style_preset": {"type": "enum", "required": False, "options": _STYLE_PRESETS},
        },
    },
    "amazon_inpainting": {
        "description": "Amazon Nova Canvas / Titan Image inpainting. taskType INPAINTING with mask.",
        "prompt_path": "inPaintingParams.text", "negative_prompt_path": "inPaintingParams.negativeText",
        "image_path": "inPaintingParams.image", "mask_prompt_path": "inPaintingParams.maskPrompt",
        "mask_image_path": "inPaintingParams.maskImage", "seed_path": "imageGenerationConfig.seed",
        "response_image_path": "images[0]",
        "body_template": {"taskType": "INPAINTING", "inPaintingParams": {}, "imageGenerationConfig": {"numberOfImages": 1}},
        "parameters": {
            "prompt": {"type": "string", "required": False, "description": "What to generate. Omit to remove content."},
            "negative_prompt": {"type": "string", "required": False},
            "image": {"type": "image", "required": True},
            "mask_image": {"type": "image", "required": False, "description": "Black/white mask (white = edit area)"},
            "mask_prompt": {"type": "string", "required": False, "description": "Natural language mask (Nova Canvas only)"},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 2147483647},
        },
    },
    "amazon_outpainting": {
        "description": "Amazon Nova Canvas / Titan Image outpainting. taskType OUTPAINTING.",
        "prompt_path": "outPaintingParams.text", "negative_prompt_path": "outPaintingParams.negativeText",
        "image_path": "outPaintingParams.image", "seed_path": "imageGenerationConfig.seed",
        "response_image_path": "images[0]",
        "body_template": {"taskType": "OUTPAINTING", "outPaintingParams": {"outPaintingMode": "DEFAULT"}, "imageGenerationConfig": {"numberOfImages": 1}},
        "parameters": {
            "prompt": {"type": "string", "required": False},
            "negative_prompt": {"type": "string", "required": False},
            "image": {"type": "image", "required": True},
            "outPaintingMode": {"type": "enum", "required": False, "options": ["DEFAULT","PRECISE"], "default": "DEFAULT"},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 2147483647},
        },
    },
    "stability_inpaint": {
        "description": "Stability AI Inpaint. Mask-based generative fill.",
        "prompt_path": "prompt", "negative_prompt_path": "negative_prompt",
        "image_path": "image", "mask_path": "mask", "seed_path": "seed",
        "response_image_path": "images[0]",
        "body_template": {"output_format": "png", "grow_mask": 15},
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 10000},
            "negative_prompt": {"type": "string", "required": False, "max_length": 10000},
            "image": {"type": "image", "required": True, "constraints": "64px min, max 9,437,184 pixels"},
            "mask": {"type": "image", "required": False, "description": "Black/white mask (white = inpaint area)"},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "grow_mask": {"type": "integer", "required": False, "min": 0, "max": 20, "default": 5},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
            "style_preset": {"type": "enum", "required": False, "options": _STYLE_PRESETS},
        },
    },
    "stability_outpaint": {
        "description": "Stability AI Outpaint. Extends image in any direction.",
        "prompt_path": "prompt", "image_path": "image", "seed_path": "seed",
        "response_image_path": "images[0]",
        "body_template": {"output_format": "png", "creativity": 0.5},
        "parameters": {
            "prompt": {"type": "string", "required": False, "max_length": 10000},
            "image": {"type": "image", "required": True},
            "left": {"type": "integer", "required": False, "min": 0, "max": 2000, "default": 0},
            "right": {"type": "integer", "required": False, "min": 0, "max": 2000, "default": 0},
            "up": {"type": "integer", "required": False, "min": 0, "max": 2000, "default": 0},
            "down": {"type": "integer", "required": False, "min": 0, "max": 2000, "default": 0},
            "creativity": {"type": "float", "required": False, "min": 0.1, "max": 1.0, "default": 0.5},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
            "style_preset": {"type": "enum", "required": False, "options": _STYLE_PRESETS},
        },
    },
    "stability_erase": {
        "description": "Stability AI Erase. Removes objects via mask.",
        "image_path": "image", "mask_path": "mask", "seed_path": "seed",
        "response_image_path": "images[0]",
        "body_template": {"output_format": "png", "grow_mask": 15},
        "parameters": {
            "image": {"type": "image", "required": True},
            "mask": {"type": "image", "required": False, "description": "Black/white mask (white = erase area)"},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "grow_mask": {"type": "integer", "required": False, "min": 0, "max": 20, "default": 5},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
        },
    },
    "stability_remove_bg": {
        "description": "Stability AI Remove Background. Only accepts image + output_format.",
        "image_path": "image",
        "response_image_path": "images[0]",
        "body_template": {"output_format": "png"},
        "parameters": {
            "image": {"type": "image", "required": True},
            "output_format": {"type": "enum", "required": False, "options": ["png", "webp"], "default": "png"},
        },
    },
    "stability_search_replace": {
        "description": "Stability AI Search & Replace. Finds and replaces objects by prompt.",
        "prompt_path": "prompt", "image_path": "image", "seed_path": "seed",
        "response_image_path": "images[0]",
        "extra_fields": {"search_prompt": "search_prompt"},
        "body_template": {"output_format": "png", "grow_mask": 5},
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 10000, "description": "Replacement object"},
            "search_prompt": {"type": "string", "required": True, "max_length": 10000, "description": "Object to find"},
            "image": {"type": "image", "required": True},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "grow_mask": {"type": "integer", "required": False, "min": 0, "max": 20, "default": 5},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
            "style_preset": {"type": "enum", "required": False, "options": _STYLE_PRESETS},
        },
    },
    "stability_search_recolor": {
        "description": "Stability AI Search & Recolor. Changes color of objects by prompt.",
        "prompt_path": "prompt", "image_path": "image", "seed_path": "seed",
        "response_image_path": "images[0]",
        "extra_fields": {"select_prompt": "select_prompt"},
        "body_template": {"output_format": "png", "grow_mask": 5},
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 10000, "description": "Target color"},
            "select_prompt": {"type": "string", "required": True, "max_length": 10000, "description": "Object to recolor"},
            "image": {"type": "image", "required": True},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "grow_mask": {"type": "integer", "required": False, "min": 0, "max": 20, "default": 5},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
            "style_preset": {"type": "enum", "required": False, "options": _STYLE_PRESETS},
        },
    },
    "stability_control": {
        "description": "Stability AI Control (Sketch/Structure). Image guided by sketch or structure.",
        "prompt_path": "prompt", "negative_prompt_path": "negative_prompt",
        "image_path": "image", "seed_path": "seed",
        "response_image_path": "images[0]",
        "body_template": {"output_format": "png", "control_strength": 0.7},
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 10000},
            "negative_prompt": {"type": "string", "required": False, "max_length": 10000},
            "image": {"type": "image", "required": True, "description": "Sketch or structural reference"},
            "control_strength": {"type": "float", "required": False, "min": 0, "max": 1, "default": 0.7},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
            "style_preset": {"type": "enum", "required": False, "options": _STYLE_PRESETS},
        },
    },
    "stability_style_transfer": {
        "description": "Stability AI Style Transfer. Applies style from reference to target.",
        "prompt_path": "prompt", "negative_prompt_path": "negative_prompt",
        "seed_path": "seed", "response_image_path": "images[0]",
        "body_template": {"output_format": "png", "composition_fidelity": 0.9, "style_strength": 1.0, "change_strength": 0.9},
        "parameters": {
            "prompt": {"type": "string", "required": False, "max_length": 10000},
            "negative_prompt": {"type": "string", "required": False, "max_length": 10000},
            "init_image": {"type": "image", "required": True, "path": "init_image", "description": "Target image"},
            "style_image": {"type": "image", "required": True, "path": "style_image", "description": "Style reference"},
            "composition_fidelity": {"type": "float", "required": False, "min": 0, "max": 1, "default": 0.9},
            "style_strength": {"type": "float", "required": False, "min": 0, "max": 1, "default": 1.0},
            "change_strength": {"type": "float", "required": False, "min": 0.1, "max": 1.0, "default": 0.9},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "output_format": {"type": "enum", "required": False, "options": ["png","jpeg","webp"], "default": "png"},
            "style_preset": {"type": "enum", "required": False, "options": _STYLE_PRESETS},
        },
    },
    "stability_upscale": {
        "description": "Stability AI Creative/Conservative Upscale. Accepts image + prompt + creativity.",
        "image_path": "image",
        "prompt_path": "prompt",
        "seed_path": "seed",
        "response_image_path": "images[0]",
        "body_template": {"output_format": "jpeg", "creativity": 0.3},
        "parameters": {
            "image": {"type": "image", "required": True},
            "prompt": {"type": "string", "required": False, "description": "Guide the upscale quality"},
            "negative_prompt": {"type": "string", "required": False},
            "creativity": {"type": "float", "required": False, "min": 0, "max": 1, "default": 0.3},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 4294967294},
            "output_format": {"type": "enum", "required": False, "options": ["png", "jpeg", "webp"], "default": "jpeg"},
        },
    },
    # ── Video generation families ──────────────────────────────────────
    "nova_reel": {
        "description": "Amazon Nova Reel text-to-video. Async invocation, outputs MP4 to S3.",
        "media_type": "video",
        "invocation_mode": "async",
        "prompt_path": "textToVideoParams.text",
        "seed_path": "videoGenerationConfig.seed",
        "body_template": {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {},
            "videoGenerationConfig": {
                "durationSeconds": 6,
                "fps": 24,
                "dimension": "1280x720",
            },
        },
        "task_types": {
            "TEXT_VIDEO": {
                "description": "Single 6-second shot from text (optional image input)",
                "prompt_path": "textToVideoParams.text",
                "image_path": "textToVideoParams.images[0]",
                "body_template": {"taskType": "TEXT_VIDEO", "textToVideoParams": {}, "videoGenerationConfig": {"durationSeconds": 6, "fps": 24, "dimension": "1280x720"}},
                "max_duration": 6,
                "prompt_limit": 512,
            },
            "MULTI_SHOT_AUTOMATED": {
                "description": "AI-segmented multi-shot up to 2 minutes (no image input)",
                "prompt_path": "multiShotAutomatedParams.text",
                "body_template": {"taskType": "MULTI_SHOT_AUTOMATED", "multiShotAutomatedParams": {}, "videoGenerationConfig": {"fps": 24, "dimension": "1280x720"}},
                "min_duration": 12,
                "max_duration": 120,
                "duration_step": 6,
                "prompt_limit": 4000,
            },
            "MULTI_SHOT_MANUAL": {
                "description": "Custom per-shot control with optional images per shot, up to 2 minutes",
                "prompt_path": "multiShotManualParams.shots",
                "body_template": {"taskType": "MULTI_SHOT_MANUAL", "multiShotManualParams": {"shots": []}, "videoGenerationConfig": {"fps": 24, "dimension": "1280x720"}},
                "max_duration": 120,
                "duration_step": 6,
                "prompt_limit": 512,
            },
        },
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 512, "description": "Video scene description"},
            "seed": {"type": "integer", "required": False, "min": 0, "max": 2147483646, "default": 42},
            "duration": {"type": "integer", "required": False, "min": 6, "max": 120, "step": 6, "default": 6, "unit": "seconds"},
            "dimension": {"type": "enum", "required": False, "options": ["1280x720"], "default": "1280x720"},
            "fps": {"type": "enum", "required": False, "options": [24], "default": 24},
            "source_image": {"type": "image", "required": False, "description": "Reference image (1280x720, 8-bit RGB, JPEG/PNG)"},
        },
    },
    "luma_ray": {
        "description": "Luma AI Ray v2 text-to-video. Async invocation, outputs MP4 to S3.",
        "media_type": "video",
        "invocation_mode": "async",
        "prompt_path": "prompt",
        "body_template": {
            "prompt": "",
            "aspect_ratio": "16:9",
            "loop": False,
            "duration": "5s",
            "resolution": "720p",
        },
        "parameters": {
            "prompt": {"type": "string", "required": True, "max_length": 5000, "description": "Video scene description"},
            "aspect_ratio": {"type": "enum", "required": False, "options": ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9", "9:21"], "default": "16:9"},
            "duration": {"type": "enum", "required": False, "options": ["5s", "9s"], "default": "5s"},
            "resolution": {"type": "enum", "required": False, "options": ["720p", "540p"], "default": "720p"},
            "loop": {"type": "boolean", "required": False, "default": False, "description": "Generate a seamlessly looping video"},
            "source_image": {"type": "image", "required": False, "description": "Start frame (min 512x512, max 4096x4096, JPEG/PNG)"},
            "end_image": {"type": "image", "required": False, "description": "End frame keyframe"},
        },
    },
}


_DEFAULT_CATEGORIES = {
    "fast_llm": {
        "current": "us.anthropic.claude-sonnet-4-6",
        "region": "us-west-2",
        "provider": "Anthropic",
        "api_type": "converse",
        "label": "Fast LLM (Sonnet)",
        "description": "Quick tasks: prompt refinement, hints, pre-check, cohesion check",
    },
    "complex_llm": {
        "current": "us.anthropic.claude-opus-4-6-v1",
        "region": "us-west-2",
        "provider": "Anthropic",
        "api_type": "converse",
        "label": "Complex LLM (Opus)",
        "description": "Complex tasks: style analysis, concept generation, Type Studio layout",
    },
    "fallback_llm": {
        "current": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "region": "us-west-2",
        "provider": "Anthropic",
        "api_type": "converse",
        "label": "Fallback LLM",
        "description": "Fallback on AccessDeniedException from primary models",
    },
    "voice": {
        "current": "amazon.nova-sonic-v1:0",
        "region": "us-east-1",
        "provider": "Amazon",
        "api_type": "bidirectional_stream",
        "label": "Voice (Nova Sonic)",
        "description": "Speech-to-text transcription via bidirectional streaming",
    },
}

_DEFAULT_IMAGE_MODELS = {
    "nova_canvas": {
        "label": "Amazon Nova Canvas",
        "model_id": "amazon.nova-canvas-v1:0",
        "region": "us-east-1",
        "provider": "Amazon",
        "enabled": True,
        "model_purpose": "text_to_image",
        "format_family": "amazon_text_to_image",
        "prompt_limit": 1024,
        "moderation_strictness": "very_strict",
        "base_price_usd": 0.06,
    },
    "titan_image": {
        "label": "Amazon Titan Image v2",
        "model_id": "amazon.titan-image-generator-v2:0",
        "region": "us-east-1",
        "provider": "Amazon",
        "enabled": True,
        "model_purpose": "text_to_image",
        "format_family": "amazon_text_to_image",
        "prompt_limit": 480,
        "moderation_strictness": "strict",
        "base_price_usd": 0.01,
    },
    "sd35_large": {
        "label": "Stable Diffusion 3.5 Large",
        "model_id": "stability.sd3-5-large-v1:0",
        "region": "us-west-2",
        "provider": "Stability AI",
        "enabled": True,
        "model_purpose": "text_to_image",
        "format_family": "stability_text_to_image",
        "prompt_limit": 2048,
        "moderation_strictness": "moderate",
        "base_price_usd": 0.08,
    },
    "stable_image_ultra": {
        "label": "Stable Image Ultra",
        "model_id": "stability.stable-image-ultra-v1:1",
        "region": "us-west-2",
        "provider": "Stability AI",
        "enabled": True,
        "model_purpose": "text_to_image",
        "format_family": "stability_text_to_image",
        "prompt_limit": 2048,
        "moderation_strictness": "moderate",
        "base_price_usd": 0.14,
    },
}

_DEFAULT_POST_PROCESSING = {
    "remove_background": {
        "label": "Remove Background",
        "model_id": "us.stability.stable-image-remove-background-v1:0",
        "region": "us-west-2",
        "provider": "Stability AI",
        "enabled": True,
        "purpose": "remove_background",
        "base_price_usd": 0.07,
    },
    "upscale": {
        "label": "Creative Upscale",
        "model_id": "stability.stable-creative-upscale-v1:0",
        "region": "us-west-2",
        "provider": "Stability AI",
        "enabled": True,
        "purpose": "upscale_creative",
        "base_price_usd": 0.60,
    },
}


def ensure_format_families():
    """Ensure all known format families exist in the registry with complete parameter specs.

    This is the code-as-source-of-truth for format families. The registry stores
    the runtime copy. Admin can customize via the JSON editor — their changes
    are preserved (we only add missing families, never overwrite existing ones).
    """
    global _registry
    changed = False
    families = _registry.setdefault("format_families", {})

    for name, default in _DEFAULT_FORMAT_FAMILIES.items():
        if name not in families:
            families[name] = default
            changed = True
            logger.info("Added missing format family: %s", name)
        elif "parameters" not in families[name]:
            # Existing family missing parameter specs — add them
            families[name]["parameters"] = default.get("parameters", {})
            changed = True
            logger.info("Added parameters to format family: %s", name)

    if changed:
        _save()


def ensure_code_defaults():
    """Ensure all code-defined defaults exist in the registry.

    Populates missing categories, base image models, and post-processing
    entries from code defaults. Existing entries are never overwritten —
    only missing ones are added. This means a deleted model_registry.json
    gets rebuilt with a working foundation on startup.
    """
    global _registry
    changed = False

    # Categories
    cats = _registry.setdefault("categories", {})
    for name, default in _DEFAULT_CATEGORIES.items():
        if name not in cats:
            cats[name] = default
            changed = True
            logger.info("Added default category: %s", name)

    # Base image models
    models = _registry.setdefault("image_models", {})
    for key, default in _DEFAULT_IMAGE_MODELS.items():
        if key not in models:
            models[key] = default
            changed = True
            logger.info("Added default image model: %s", key)

    # Post-processing
    pp = _registry.setdefault("post_processing", {})
    for key, default in _DEFAULT_POST_PROCESSING.items():
        if key not in pp:
            pp[key] = default
            changed = True
            logger.info("Added default post-processing: %s", key)

    if changed:
        _save()


# ── Load on import ────────────────────────────────────────────────────────
_load()
ensure_format_families()
ensure_code_defaults()


# ── Public API ────────────────────────────────────────────────────────────

def get_registry() -> dict:
    """Return the full registry."""
    return _registry


def get_category(name: str) -> dict:
    """Get a model category config (fast_llm, complex_llm, etc.)."""
    return _registry.get("categories", {}).get(name, {})


def get_llm_model_id(complexity: str) -> str:
    """Get the Bedrock model ID for the given complexity level."""
    if complexity == "complex":
        return get_category("complex_llm").get("current", "")
    return get_category("fast_llm").get("current", "")


def get_llm_region(complexity: str) -> str:
    """Get the AWS region for the given LLM complexity."""
    if complexity == "complex":
        return get_category("complex_llm").get("region", "us-west-2")
    return get_category("fast_llm").get("region", "us-west-2")


def get_fallback_model_id() -> str:
    """Get the fallback LLM model ID."""
    return get_category("fallback_llm").get("current", "")


def get_image_model(key: str) -> dict:
    """Get image model config by key (e.g. 'sd35_large')."""
    return _registry.get("image_models", {}).get(key, {})


def get_enabled_image_models() -> dict:
    """Get all enabled image models."""
    return {k: v for k, v in _registry.get("image_models", {}).items() if v.get("enabled", True)}


_STRICTNESS_ORDER = {"moderate": 0, "strict": 1, "very_strict": 2}


def get_enabled_image_model_keys_sorted() -> list[str]:
    """Return enabled text-to-image model keys sorted by moderation strictness.

    Only includes models with purpose 'text_to_image' — excludes inpainting,
    outpainting, erase, upscale, remove_background, and other editing models.
    Sorted least strict first so 'All Models' generation gets faster feedback.
    """
    enabled = get_enabled_image_models()
    t2i = {k: v for k, v in enabled.items() if v.get("model_purpose") == "text_to_image"}
    return sorted(
        t2i.keys(),
        key=lambda k: _STRICTNESS_ORDER.get(t2i[k].get("moderation_strictness", "moderate"), 0),
    )


def get_image_model_id(key: str) -> str:
    """Get the Bedrock model ID for an image model key."""
    return get_image_model(key).get("model_id", "")


def get_image_model_region(key: str) -> str:
    """Get the AWS region for an image model."""
    return get_image_model(key).get("region", "us-east-1")


def get_prompt_limit(key: str) -> int:
    """Get the prompt character limit for an image model."""
    return get_image_model(key).get("prompt_limit", 900)


def get_image_model_label(key: str) -> str:
    """Get the human-readable label for an image model."""
    return get_image_model(key).get("label", key)


def get_post_processing(key: str) -> dict:
    """Get post-processing model config."""
    return _registry.get("post_processing", {}).get(key, {})


# ── All model labels (for UI dropdowns and dialogs) ───────────────────────

def get_all_model_labels() -> dict[str, str]:
    """Return {key: label} for all image models."""
    return {k: v.get("label", k) for k, v in _registry.get("image_models", {}).items()}


def get_enabled_model_labels() -> dict[str, str]:
    """Return {key: label} for enabled image models only."""
    return {k: v.get("label", k) for k, v in get_enabled_image_models().items()}


# ── Admin API functions ───────────────────────────────────────────────────

def update_category(name: str, updates: dict, user_pref: bool = False) -> dict:
    """Update a model category (fast_llm, complex_llm, etc.).

    user_pref=True: User action from Model Settings UI → writes ONLY to .user.json.
    user_pref=False: System action (Sync, code) → writes to main file.
    """
    if name not in _registry.get("categories", {}):
        _registry.setdefault("categories", {})[name] = {}
    _registry["categories"][name].update(updates)
    if user_pref:
        for field, value in updates.items():
            _save_user_pref("categories", name, field, value)
    else:
        _save()
    return _registry["categories"][name]


def update_image_model(key: str, updates: dict, user_pref: bool = False) -> dict:
    """Update an image model config.

    user_pref=True: User action (enable/disable from UI) → writes ONLY to .user.json.
    user_pref=False: System action (Sync from AWS) → writes to main file.
    """
    if key not in _registry.get("image_models", {}):
        _registry.setdefault("image_models", {})[key] = {}
    _registry["image_models"][key].update(updates)
    if user_pref:
        for field in _USER_PREF_FIELDS:
            if field in updates:
                _save_user_pref("image_models", key, field, updates[field])
    else:
        _save()
    return _registry["image_models"][key]


def add_image_model(key: str, config: dict) -> dict:
    """Add a new image model to the registry."""
    _registry.setdefault("image_models", {})[key] = config
    _save()
    return config


def update_post_processing(key: str, updates: dict, user_pref: bool = False) -> dict:
    """Update a post-processing model config."""
    if key not in _registry.get("post_processing", {}):
        _registry.setdefault("post_processing", {})[key] = {}
    _registry["post_processing"][key].update(updates)
    if user_pref:
        for field in _USER_PREF_FIELDS:
            if field in updates:
                _save_user_pref("post_processing", key, field, updates[field])
    else:
        _save()
    return _registry["post_processing"][key]


def reload():
    """Reload registry from disk (e.g. after external edit)."""
    _load()


# ── Video model functions ─────────────────────────────────────────────────

def get_video_model(key: str) -> dict:
    """Get video model config by key."""
    return _registry.get("video_models", {}).get(key, {})


def get_enabled_video_models() -> dict:
    """Get all enabled video models."""
    return {k: v for k, v in _registry.get("video_models", {}).items() if v.get("enabled", True)}


def get_video_model_keys_sorted() -> list[str]:
    """Return enabled video model keys sorted by label."""
    enabled = get_enabled_video_models()
    return sorted(enabled.keys(), key=lambda k: enabled[k].get("label", k))


def add_video_model(key: str, config: dict) -> dict:
    """Add a new video model to the registry."""
    _registry.setdefault("video_models", {})[key] = config
    _save()
    return config


def update_video_model(key: str, updates: dict, user_pref: bool = False) -> dict:
    """Update a video model config."""
    if key not in _registry.get("video_models", {}):
        _registry.setdefault("video_models", {})[key] = {}
    _registry["video_models"][key].update(updates)
    if user_pref:
        for field in _USER_PREF_FIELDS:
            if field in updates:
                _save_user_pref("video_models", key, field, updates[field])
    else:
        _save()
    return _registry["video_models"][key]


# ── Video settings (S3 bucket, storage preference) ────────────────────────

def get_video_settings() -> dict:
    """Get video-related settings from the registry."""
    return _registry.get("video_settings", {
        "s3_bucket": "",
        "s3_prefix": "artsmoker/video/",
        "store_local": True,
        "s3_validated": False,
    })


def update_video_settings(updates: dict) -> dict:
    """Update video settings in the registry."""
    current = _registry.get("video_settings", {
        "s3_bucket": "",
        "s3_prefix": "artsmoker/video/",
        "store_local": True,
        "s3_validated": False,
    })
    current.update(updates)
    _registry["video_settings"] = current
    _save()
    return current
