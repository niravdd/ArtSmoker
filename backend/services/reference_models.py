"""Reference-guided generation — deployed-model discovery and gating.

The "Match the reference" mode needs a self-hosted reference-capable edit model
(e.g. Qwen-Image-Edit) deployed on SageMaker. This mirrors the 3D gating pattern
(generate_3d._list_3d_models / check_3d_available): the "Inspired by" mode never
needs a custom model (it uses a Bedrock vision LLM + a standard text-to-image
model), so ONLY "Match" is gated.

A model is "reference-capable" if its catalog entry declares
``capabilities.reference_guided: true`` (so new commercially-licensed edit models
added to the catalog light up automatically — registry-driven, no code change).
"""

import logging

from backend.services.model_registry import get_registry
from backend.services.custom_models import get_catalog

logger = logging.getLogger(__name__)


def _reference_catalog_keys() -> set[str]:
    """Catalog keys whose models can do reference-guided generation.

    Registry-driven: any custom_model_catalog entry with
    ``capabilities.reference_guided == true``.
    """
    keys = set()
    for key, entry in (get_catalog() or {}).items():
        caps = entry.get("capabilities", {}) or {}
        if caps.get("reference_guided"):
            keys.add(key)
    return keys


def list_reference_models() -> list[tuple[str, dict]]:
    """All DEPLOYED reference-capable image-edit instances, newest-first.

    Each deployed instance is a registry entry keyed like ``<catalog>_<hash>``
    with a ``deployment.endpoint_name``. Returns (model_key, config) tuples.
    """
    ref_keys = _reference_catalog_keys()
    if not ref_keys:
        return []

    registry = get_registry()
    found: list[tuple[str, dict]] = []
    for section in ("image_models", "post_processing"):
        for key, cfg in registry.get(section, {}).items():
            if cfg.get("catalog_key") not in ref_keys:
                continue
            if cfg.get("model_source") != "custom_hosted":
                continue
            dep = cfg.get("deployment", {})
            if not dep.get("endpoint_name"):
                continue
            found.append((key, cfg))

    found.sort(
        key=lambda item: item[1].get("deployment", {}).get("created_at", "") or "",
        reverse=True,
    )
    return found


def find_reference_model(model_key: str | None = None) -> tuple[str | None, dict | None]:
    """Resolve a deployed reference-capable model.

    With ``model_key`` → that specific deployed instance (honors a chooser
    selection); otherwise the newest deployed instance. (None, None) if no match.
    """
    models = list_reference_models()
    if not models:
        return None, None
    if model_key:
        for key, cfg in models:
            if key == model_key:
                return key, cfg
        return None, None
    return models[0]


def supported_reference_models() -> list[dict]:
    """The reference-capable models ArtSmoker SUPPORTS (catalog, not deployments).

    Registry-driven: every custom_model_catalog entry with
    ``capabilities.reference_guided`` — so the UI can name what's supported
    generically (today Qwen-Image-Edit; any future catalog addition lights up
    with no code change). Sorted by label for stable display.
    """
    out = []
    catalog = get_catalog() or {}
    for key in sorted(_reference_catalog_keys()):
        entry = catalog.get(key, {}) or {}
        out.append({"catalog_key": key, "label": entry.get("label", key)})
    out.sort(key=lambda m: m["label"].lower())
    return out


def reference_generation_available() -> dict:
    """Is ANY reference-capable model deployed + enabled?

    Shape mirrors generate_3d.check_3d_available so the frontend can gate the
    "Match the reference" mode and, when unavailable, route the user to the
    Custom Models deploy flow for the recommended catalog model.

    Also returns (registry-driven, never hardcoded):
      - ``models``:    ALL deployed reference-capable instances (newest first) —
                       powers the match-mode model chooser.
      - ``supported``: the catalog models that CAN do this once deployed —
                       powers a generic "deploy one of these" message.
    """
    supported = supported_reference_models()
    # Warm/cold per-edit economics (scale-to-zero endpoints bill GPU time, not
    # per image) — shared computation with the Edit tab's cost hint.
    from backend.services.custom_models import get_custom_model_economics
    economics = get_custom_model_economics()
    deployed = [
        {
            "model_key": key,
            "label": cfg.get("label", key),
            "endpoint_name": cfg.get("deployment", {}).get("endpoint_name"),
            "model_ready": bool(cfg.get("model_ready")),
            "economics": economics.get(key),
        }
        for key, cfg in list_reference_models()
        if cfg.get("enabled", True)
    ]

    model_key, cfg = find_reference_model()
    if not model_key or not cfg:
        # Point the user at the recommended catalog model to deploy.
        ref_keys = _reference_catalog_keys()
        deploy_key = "qwen_image_edit_bf16" if "qwen_image_edit_bf16" in ref_keys else (
            next(iter(sorted(ref_keys)), None)
        )
        return {
            "available": False,
            "model_key": None,
            "endpoint_name": None,
            "deploy_catalog_key": deploy_key,
            "models": [],
            "supported": supported,
        }

    dep = cfg.get("deployment", {})
    endpoint_name = dep.get("endpoint_name")
    enabled = cfg.get("enabled", True)
    return {
        "available": bool(endpoint_name and enabled),
        "model_key": model_key,
        "endpoint_name": endpoint_name,
        "label": cfg.get("label", model_key),
        "model_ready": bool(cfg.get("model_ready")),
        "models": deployed,
        "supported": supported,
    }
