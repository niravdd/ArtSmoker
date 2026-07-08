"""Custom Model Catalog — registry of self-hosted 3rd-party models.

The catalog defines everything needed to download, deploy, and invoke
each model. All behavior is driven by data in model_registry.json
(section: custom_model_catalog), not by model-specific code.

Adding a new model = adding a JSON entry to model_registry.json.

Layered config (same as rest of registry):
  model_registry.json       — git-tracked defaults (source of truth)
  model_registry.user.json  — gitignored runtime state + user overrides

When a model is deployed, the deployment state (endpoint_name, etc.)
gets written to the relevant studio section (image_models, video_models)
in the .user.json file.
"""

import logging

logger = logging.getLogger(__name__)


def _get_catalog_section() -> dict:
    """Read the custom_model_catalog section from the model registry."""
    from backend.services.model_registry import get_registry
    return get_registry().get("custom_model_catalog", {})


# ── Public API ────────────────────────────────────────────────────────────

def get_catalog() -> dict:
    """Return the full model catalog."""
    return _get_catalog_section().get("models", {})


def get_catalog_model(model_key: str) -> dict | None:
    """Return a single model from the catalog."""
    return get_catalog().get(model_key)


def get_instance_hourly_rate(instance_type: str, catalog_key: str = None,
                             region: str = None) -> float:
    """Resolve the public USD/hour rate for a SageMaker instance type — REGISTRY
    ONLY, never hardcoded.

    Resolution order (most authoritative first):
      1. `sagemaker_pricing[instance|region]` — LIVE, per-region rates fetched
         from the AWS Pricing API during Sync (region-accurate; the correct source).
      2. `sagemaker_pricing[instance|*]` — any synced region for that instance
         (better than a stale seed when the exact region wasn't scanned).
      3. Catalog `pricing.instance_cost_per_hour` seed — the static fallback that
         ships in the registry (region-agnostic; may lag AWS price changes).
    Returns 0.0 if nothing resolves — callers treat 0 as "unknown" and report cost
    0 rather than guessing. Single source of truth: updating the registry (via Sync
    or manually) updates every cost computation (3D, async 2D, keep-warm) at once.
    """
    if not instance_type:
        return 0.0
    from backend.services.model_registry import get_registry
    reg = get_registry()

    # 1 + 2: live synced per-region pricing (AWS Pricing API).
    sm = reg.get("sagemaker_pricing", {}) or {}
    if region:
        r = sm.get(f"{instance_type}|{region}")
        if r:
            return float(r)
    # Any region's synced rate for this instance (prefer over a static seed).
    for k, v in sm.items():
        if k.startswith(instance_type + "|") and v:
            return float(v)

    # 3: catalog seed fallback (static, region-agnostic).
    catalog = get_catalog()
    if catalog_key and catalog_key in catalog:
        rate = ((catalog[catalog_key].get("pricing", {}) or {})
                .get("instance_cost_per_hour", {}) or {}).get(instance_type)
        if rate:
            return float(rate)
    for entry in catalog.values():
        rate = ((entry.get("pricing", {}) or {})
                .get("instance_cost_per_hour", {}) or {}).get(instance_type)
        if rate:
            return float(rate)
    return 0.0


def get_catalog_by_category(category: str) -> dict:
    """Return models filtered by category."""
    return {k: v for k, v in get_catalog().items() if v.get("category") == category}


def get_catalog_by_studio(studio: str) -> dict:
    """Return models filtered by studio (image, video)."""
    return {k: v for k, v in get_catalog().items() if v.get("studio") == studio}


def get_bundle_for_model(model_key: str) -> str | None:
    """Return the bundle key for a model, or None if it needs a dedicated instance."""
    bundles = _get_catalog_section().get("bundles", {})
    for bundle_key, bundle in bundles.items():
        if model_key in bundle.get("models", []):
            return bundle_key
    return None


def get_bundle(bundle_key: str) -> dict | None:
    """Return a bundle definition."""
    return _get_catalog_section().get("bundles", {}).get(bundle_key)


def get_all_bundles() -> dict:
    """Return all bundle definitions."""
    return _get_catalog_section().get("bundles", {})


def is_dedicated(model_key: str) -> bool:
    """Check if a model needs its own dedicated instance."""
    return model_key in set(_get_catalog_section().get("dedicated_models", []))
