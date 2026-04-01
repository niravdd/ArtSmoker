"""Model Registry — manages all AI model configurations.

Loads from backend/model_registry.json, provides model info to the rest
of the system, and supports runtime updates via the admin API.

Replaces hardcoded model IDs in config.py and bedrock_client.py with
a dynamic, configurable registry.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "model_registry.json"       # Main registry (source of truth)
_USER_PREFS_PATH = Path(__file__).resolve().parent.parent / "model_registry.user.json"  # User preference overrides (gitignored)
_registry: dict = {}

# Fields in model entries that are USER PREFERENCES (not structural data).
# These are the only fields that go into .user.json — everything else
# (discovered models, pricing, regions, format families) stays in the main file.
_USER_PREF_FIELDS = {"enabled"}
# Top-level sections that are user preferences
_USER_PREF_SECTIONS = {"categories"}


def _load():
    """Load the registry: main file + user preference overrides.

    model_registry.json is the single source of truth — contains everything:
    format families, discovered models, pricing, regions. Updated by Sync from
    AWS and by code (format family defaults).

    model_registry.user.json contains ONLY user preference overrides:
    enabled/disabled flags, category model selections. These survive Sync
    refreshes and git pulls.
    """
    global _registry
    # 1. Load main registry (the full source of truth)
    try:
        _registry = json.loads(_REGISTRY_PATH.read_text())
    except Exception as exc:
        logger.error("Failed to load model registry: %s", exc)
        _registry = {"categories": {}, "image_models": {}, "post_processing": {}}

    # 2. Overlay user preference overrides
    if _USER_PREFS_PATH.exists():
        try:
            prefs = json.loads(_USER_PREFS_PATH.read_text())
            overrides_applied = _apply_user_prefs(_registry, prefs)
            if overrides_applied:
                logger.info("Model registry loaded: %d image models, %d categories (+%d user prefs)",
                            len(_registry.get("image_models", {})),
                            len(_registry.get("categories", {})),
                            overrides_applied)
            else:
                logger.info("Model registry loaded: %d image models, %d categories",
                            len(_registry.get("image_models", {})),
                            len(_registry.get("categories", {})))
        except Exception as exc:
            logger.warning("Failed to load user prefs: %s", exc)
    else:
        logger.info("Model registry loaded: %d image models, %d categories",
                     len(_registry.get("image_models", {})),
                     len(_registry.get("categories", {})))


def _apply_user_prefs(registry: dict, prefs: dict) -> int:
    """Apply user preference overrides to the loaded registry. Returns count applied."""
    count = 0
    for section, overrides in prefs.items():
        if section.startswith("_") or not isinstance(overrides, dict):
            continue
        if section in _USER_PREF_SECTIONS:
            # Category selections — deep merge
            if section in registry and isinstance(registry[section], dict):
                for key, val in overrides.items():
                    if key in registry[section] and isinstance(val, dict):
                        registry[section][key].update(val)
                    else:
                        registry[section][key] = val
                    count += 1
        elif section in registry and isinstance(registry[section], dict):
            # Model sections (image_models, video_models, chat_models, post_processing)
            # Only apply _USER_PREF_FIELDS
            for model_key, model_prefs in overrides.items():
                if model_key in registry[section] and isinstance(model_prefs, dict):
                    for field in _USER_PREF_FIELDS:
                        if field in model_prefs:
                            registry[section][model_key][field] = model_prefs[field]
                            count += 1
    return count


def _save():
    """Save the registry to the main file (source of truth for structural data).

    Called after Sync from AWS and system operations. Before writing, strips
    user preference overrides from the output so the main file always reflects
    the system/default state. User preferences live only in .user.json.
    """
    import copy
    # Deep copy to avoid mutating in-memory registry
    output = copy.deepcopy(_registry)

    # Strip user preference fields — restore them to defaults so the main file
    # stays clean. User prefs are reapplied from .user.json on next load.
    if _USER_PREFS_PATH.exists():
        try:
            prefs = json.loads(_USER_PREFS_PATH.read_text())
            _strip_user_prefs_from_output(output, prefs)
        except Exception:
            pass

    output["last_updated"] = datetime.utcnow().isoformat()
    _REGISTRY_PATH.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Model registry saved.")


def _strip_user_prefs_from_output(output: dict, prefs: dict):
    """Remove user preference overrides from the output before writing to main file.

    For each user pref (e.g., image_models.titan_image.enabled=False), look up
    what the value was BEFORE user changed it and restore it in the output.
    This way the main file always has the 'system default' for preference fields.
    """
    # Load the previous main file to get pre-user-pref values
    try:
        original = json.loads(_REGISTRY_PATH.read_text())
    except Exception:
        return  # Can't diff, skip stripping

    for section, overrides in prefs.items():
        if section.startswith("_") or not isinstance(overrides, dict):
            continue
        if section in _USER_PREF_SECTIONS:
            # Categories — restore original values
            if section in output and section in original:
                for key, fields in overrides.items():
                    if isinstance(fields, dict) and key in output[section] and key in original.get(section, {}):
                        for field in fields:
                            if field in original[section].get(key, {}):
                                output[section][key][field] = original[section][key][field]
        elif section in output and isinstance(output[section], dict):
            # Model sections — restore user pref fields to original
            for model_key, model_prefs in overrides.items():
                if isinstance(model_prefs, dict) and model_key in output[section]:
                    for field in _USER_PREF_FIELDS:
                        if field in model_prefs and model_key in original.get(section, {}):
                            orig_val = original[section][model_key].get(field)
                            if orig_val is not None:
                                output[section][model_key][field] = orig_val


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
        "body_template": {"output_format": "png", "grow_mask": 5},
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
        "body_template": {"output_format": "png", "grow_mask": 5},
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
    return {k: v for k, v in _registry.get("image_models", {}).items() if v.get("enabled")}


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
    return {k: v for k, v in _registry.get("video_models", {}).items() if v.get("enabled")}


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
