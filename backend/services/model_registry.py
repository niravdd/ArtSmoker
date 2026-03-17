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

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "model_registry.json"
_registry: dict = {}


def _load():
    """Load the registry from disk."""
    global _registry
    try:
        _registry = json.loads(_REGISTRY_PATH.read_text())
        logger.info("Model registry loaded: %d image models, %d categories",
                     len(_registry.get("image_models", {})),
                     len(_registry.get("categories", {})))
    except Exception as exc:
        logger.error("Failed to load model registry: %s", exc)
        _registry = {"categories": {}, "image_models": {}, "post_processing": {}}


def _save():
    """Persist the registry to disk."""
    _registry["last_updated"] = datetime.utcnow().isoformat()
    _REGISTRY_PATH.write_text(json.dumps(_registry, indent=2, default=str))
    logger.info("Model registry saved.")


# ── Load on import ────────────────────────────────────────────────────────
_load()


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
    """Return enabled image model keys sorted by moderation strictness (least strict first).

    This ordering is used by 'All Models' generation so less strict models
    run first (more likely to succeed), giving faster feedback.
    """
    enabled = get_enabled_image_models()
    return sorted(
        enabled.keys(),
        key=lambda k: _STRICTNESS_ORDER.get(enabled[k].get("moderation_strictness", "moderate"), 0),
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

def update_category(name: str, updates: dict) -> dict:
    """Update a model category (fast_llm, complex_llm, etc.)."""
    if name not in _registry.get("categories", {}):
        _registry.setdefault("categories", {})[name] = {}
    _registry["categories"][name].update(updates)
    _save()
    return _registry["categories"][name]


def update_image_model(key: str, updates: dict) -> dict:
    """Update an image model config."""
    if key not in _registry.get("image_models", {}):
        _registry.setdefault("image_models", {})[key] = {}
    _registry["image_models"][key].update(updates)
    _save()
    return _registry["image_models"][key]


def add_image_model(key: str, config: dict) -> dict:
    """Add a new image model to the registry."""
    _registry.setdefault("image_models", {})[key] = config
    _save()
    return config


def update_post_processing(key: str, updates: dict) -> dict:
    """Update a post-processing model config."""
    if key not in _registry.get("post_processing", {}):
        _registry.setdefault("post_processing", {})[key] = {}
    _registry["post_processing"][key].update(updates)
    _save()
    return _registry["post_processing"][key]


def reload():
    """Reload registry from disk (e.g. after external edit)."""
    _load()
