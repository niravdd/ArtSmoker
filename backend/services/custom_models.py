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
      4. On-demand AWS Pricing API query — ONLY when the registry has no rate at
         all (a genuine gap). The result is cached into the in-memory
         `sagemaker_pricing` so the same computation never re-queries online within
         a session; a subsequent AWS Sync persists it durably. (Normal operation is
         registry-served — no network — per the "record during Sync" rule.)
    Returns 0.0 only if the registry AND an on-demand query both yield nothing —
    callers surface a "pricing unavailable" state rather than guessing a number.
    Single source of truth: updating the registry (via Sync or the on-demand cache)
    updates every cost computation (3D, async 2D, keep-warm) at once.
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

    # 4: on-demand AWS Pricing API fallback for a registry gap (cached in-memory).
    rate = _fetch_instance_rate_ondemand(instance_type, region, reg)
    if rate:
        return rate
    return 0.0


def _fetch_instance_rate_ondemand(instance_type: str, region: str | None, reg: dict) -> float:
    """On-demand AWS Pricing API lookup for a single instance when the registry has
    no rate (a gap the Sync hasn't captured yet). Registry stays the primary source;
    this only fires as a fallback. The fetched rates are cached into the in-memory
    `sagemaker_pricing` dict so the same cost computation never re-queries online in
    this session — a later AWS Sync records them durably. Returns 0.0 if the online
    lookup also fails, so the caller can report "pricing unavailable" (never a guess).
    """
    try:
        from backend.routers.admin import _fetch_sagemaker_pricing
        fetched = _fetch_sagemaker_pricing([region] if region else None)
        if fetched:
            sm = reg.setdefault("sagemaker_pricing", {})
            sm.update(fetched)  # session cache; durable persistence happens on Sync
            if region and fetched.get(f"{instance_type}|{region}"):
                return float(fetched[f"{instance_type}|{region}"])
            for k, v in fetched.items():
                if k.startswith(instance_type + "|") and v:
                    return float(v)
    except Exception as exc:
        logger.warning("On-demand SageMaker price fetch failed for %s|%s: %s",
                       instance_type, region, exc)
    return 0.0


def get_custom_model_economics() -> dict:
    """Per-generation economics for every DEPLOYED custom-hosted image model.

    Scale-to-zero endpoints bill by GPU time, not per image — a warm request
    costs hourly × typical latency, while a single request against an idle
    endpoint also pays the ~5–15 min cold-start spin-up. This is the ONE shared
    computation the UI surfaces (Edit tab, Reference "Match" chooser) so the
    warm/cold numbers can never drift from the pricing the rest of the app uses
    (same get_instance_hourly_rate + invoke.typical_latency_seconds sources as
    the Image Studio estimate).

    Returns { model_key: { hourly_usd, typical_latency_seconds, warm_cost_usd,
                           cold_cost_min_usd, cold_cost_max_usd } } — entries
    appear only when BOTH an hourly rate and a latency are known (no fabricated
    numbers, per the registry-only pricing rule).
    """
    from backend.services.model_registry import get_registry

    COLD_MIN_MINUTES, COLD_MAX_MINUTES = 5, 15  # matches the cold_start_warning copy
    out: dict = {}
    for key, cfg in (get_registry().get("image_models", {}) or {}).items():
        if cfg.get("model_source") != "custom_hosted":
            continue
        dep = cfg.get("deployment") or {}
        instance = dep.get("instance_type")
        if not instance:
            continue
        latency = (cfg.get("invoke") or {}).get("typical_latency_seconds")
        try:
            hourly = get_instance_hourly_rate(instance, cfg.get("catalog_key"), dep.get("region"))
        except Exception:
            hourly = 0
        if not hourly or not latency:
            continue
        out[key] = {
            "hourly_usd": round(hourly, 4),
            "typical_latency_seconds": latency,
            "warm_cost_usd": round(hourly * latency / 3600.0, 4),
            "cold_cost_min_usd": round(hourly * COLD_MIN_MINUTES / 60.0, 2),
            "cold_cost_max_usd": round(hourly * COLD_MAX_MINUTES / 60.0, 2),
        }
    return out


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
