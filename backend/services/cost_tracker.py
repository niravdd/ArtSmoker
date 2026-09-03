"""Request-scoped cost tracker for comprehensive AWS spend tracking.

Accumulates costs from all Bedrock calls within a single generation request:
LLM calls (prompt enhancement, concept generation, pre-check, moderation rewrite),
image generation, post-processing, video generation, and moderation overhead.

Uses contextvars for thread-safe, request-scoped accumulation.

Usage:
    from backend.services.cost_tracker import reset_costs, add_cost, get_total_cost, get_cost_breakdown

    reset_costs()  # At the start of a request
    add_cost("llm_prompt_enhance", 0.003, detail="Sonnet: 1200 in, 400 out")
    add_cost("image_generation", 0.06, detail="nova_canvas × 1")
    ...
    breakdown = get_cost_breakdown()  # {component: {cost, count, details}}
    total = get_total_cost()          # float
"""

import logging
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

def _get_infra_pricing(region: str | None = None) -> dict:
    """S3/infra rates — REGISTRY ONLY (`infra_pricing`, recorded by the Sync via
    admin._record_infra_pricing). No hardcoded code fallback: if the registry has no
    rates yet (fresh install, pre-Sync), returns {} and S3 cost is reported as 0
    until a Sync records them. Exact region first, else any recorded region (S3 rates
    are near-uniform), else empty."""
    try:
        from backend.services.model_registry import get_registry
        reg_pricing = get_registry().get("infra_pricing", {}) or {}
        if region and region in reg_pricing:
            return reg_pricing[region]
        if reg_pricing:
            return next(iter(reg_pricing.values()))
    except Exception:
        pass
    return {}


@dataclass
class CostEntry:
    component: str
    cost_usd: float
    detail: str = ""


@dataclass
class CostAccumulator:
    entries: list[CostEntry] = field(default_factory=list)

    def add(self, component: str, cost_usd: float, detail: str = ""):
        self.entries.append(CostEntry(component=component, cost_usd=cost_usd, detail=detail))

    def total(self) -> float:
        return sum(e.cost_usd for e in self.entries)

    def breakdown(self) -> dict:
        """Return {component: {cost, count, details[]}}."""
        groups: dict = {}
        for e in self.entries:
            if e.component not in groups:
                groups[e.component] = {"cost": 0.0, "count": 0, "details": []}
            groups[e.component]["cost"] += e.cost_usd
            groups[e.component]["count"] += 1
            if e.detail:
                groups[e.component]["details"].append(e.detail)
        # Round costs
        for g in groups.values():
            g["cost"] = round(g["cost"], 6)
        return groups

    def reset(self):
        self.entries.clear()


# Context variable — each request/thread gets its own accumulator
_cost_ctx: ContextVar[CostAccumulator] = ContextVar("cost_tracker")


def _get_accumulator() -> CostAccumulator:
    try:
        return _cost_ctx.get()
    except LookupError:
        acc = CostAccumulator()
        _cost_ctx.set(acc)
        return acc


def reset_costs():
    """Reset the cost tracker for a new request."""
    _get_accumulator().reset()


def share_accumulator_with_thread():
    """Get the current accumulator so it can be shared with child threads.

    Call in the parent thread to get the accumulator, then call
    `install_shared_accumulator(acc)` in each child thread.
    This solves the ContextVar isolation problem with ThreadPoolExecutor.
    """
    return _get_accumulator()


def install_shared_accumulator(acc: CostAccumulator):
    """Install a shared accumulator in the current thread's context.

    Call at the start of a worker thread function to share costs
    back to the parent thread's accumulator.
    """
    _cost_ctx.set(acc)


def add_cost(component: str, cost_usd: float, detail: str = ""):
    """Add a cost entry. Called from invoke_llm, invoke_image_model, etc."""
    if cost_usd > 0:
        _get_accumulator().add(component, cost_usd, detail)


def get_total_cost() -> float:
    """Get the total accumulated cost for this request."""
    return round(_get_accumulator().total(), 6)


def get_cost_breakdown() -> dict:
    """Get a breakdown of costs by component."""
    return _get_accumulator().breakdown()


def _compute_s3_cost(operation: str, size_bytes: int, region: str | None) -> float:
    """Compute S3 cost for one operation + data transfer. Returns 0.0 when infra
    pricing isn't recorded in the registry yet (pre-Sync) — no hardcoded fallback."""
    pricing = _get_infra_pricing(region)
    if not pricing:
        return 0.0
    op = operation.lower()
    if op == "delete":
        return 0.0
    if op in ("get", "select", "head"):
        req_cost = pricing.get("s3_get_per_1k", 0) / 1000
    else:  # put/post/copy/list + anything else
        req_cost = pricing.get("s3_put_per_1k", 0) / 1000
    transfer_cost = (size_bytes / (1024 ** 3)) * pricing.get("s3_transfer_out_per_gb", 0) if size_bytes > 0 else 0.0
    return req_cost + transfer_cost


def add_s3_cost(operation: str, size_bytes: int = 0, detail: str = "", region: str | None = None):
    """Track S3 operation cost within request scope."""
    cost = _compute_s3_cost(operation, size_bytes, region)
    if cost > 0:
        add_cost("s3", cost, detail or f"S3 {operation} ({size_bytes}B)")


# ── Background cost accumulator (for daemon threads) ────────────────────
# The ContextVar-based accumulator only works within request scope.
# Background threads (async job poller, deployer) use this instead.

_bg_accumulator = CostAccumulator()
_bg_lock = threading.Lock()


def add_background_cost(component: str, cost_usd: float, detail: str = ""):
    """Track cost from background threads (not request-scoped)."""
    if cost_usd > 0:
        with _bg_lock:
            _bg_accumulator.add(component, cost_usd, detail)


def get_background_costs() -> dict:
    """Get accumulated background costs for periodic flush."""
    with _bg_lock:
        return _bg_accumulator.breakdown()


def get_background_total() -> float:
    with _bg_lock:
        return round(_bg_accumulator.total(), 6)


def reset_background_costs():
    with _bg_lock:
        _bg_accumulator.reset()


def add_background_s3_cost(operation: str, size_bytes: int = 0, detail: str = "", region: str | None = None):
    """Track S3 cost from background threads."""
    cost = _compute_s3_cost(operation, size_bytes, region)
    if cost > 0:
        add_background_cost("s3", cost, detail or f"S3 {operation} ({size_bytes}B)")


def _registry_llm_price(model_id: str, region: str | None = None) -> dict | None:
    """Look up per-token pricing for a model from the chat_models registry.

    Prices are stamped onto each chat_models entry by AWS Sync
    (_fetch_llm_pricing → _apply_llm_pricing) as input_price_per_1k /
    output_price_per_1k — the LIVE, per-model source. When token prices VARY by
    region, the full per-region map is also stored as `token_pricing_by_region`;
    if a `region` is passed we use that region's price, else the collapsed default.
    Matches by exact model_id first, then by the registry KEY, then a substring
    match (handles us./eu. cross-region prefixes vs the base id). Returns
    {input_per_mtok, output_per_mtok} or None if the registry has no price."""
    try:
        from backend.services.model_registry import get_registry
        cms = (get_registry().get("chat_models", {}) or {})
        def _priced(cm):
            # Region-specific price first (present only when prices vary by region),
            # else the collapsed default input_price_per_1k / output_price_per_1k.
            in_p = out_p = None
            if region:
                pr = (cm.get("token_pricing_by_region") or {}).get(region)
                if pr:
                    in_p, out_p = pr.get("input_per_1k"), pr.get("output_per_1k")
            if in_p is None and out_p is None:
                in_p = cm.get("input_price_per_1k")
                out_p = cm.get("output_price_per_1k")
            if in_p or out_p:
                # per-1k → per-mtok (×1000).
                return {"input_per_mtok": (in_p or 0) * 1000, "output_per_mtok": (out_p or 0) * 1000}
            return None
        # 1) exact model_id, 2) exact registry key, 3) substring either way.
        for cm in cms.values():
            if cm.get("model_id") == model_id:
                p = _priced(cm)
                if p: return p
        if model_id in cms:
            p = _priced(cms[model_id])
            if p: return p
        for key, cm in cms.items():
            mid = cm.get("model_id", "")
            if mid and (mid in model_id or model_id in mid):
                p = _priced(cm)
                if p: return p
        # 4) LLM-category entries (e.g. categories.voice = Nova Sonic) — models
        # that never enter chat_models (speech-only input) but get token prices
        # stamped by the same AWS Sync pricing pass.
        for cat in (get_registry().get("categories", {}) or {}).values():
            if isinstance(cat, dict) and cat.get("current") == model_id:
                p = _priced(cat)
                if p: return p
    except Exception:
        pass
    return None


def resolve_image_price(cfg: dict, model_key: str, region: str,
                        quality: str = "", size: str = "") -> float | None:
    """Registry-sourced per-image price for a Bedrock image model at a given
    region + quality — reads the Sync-recorded `image_pricing` section (keyed
    `model_name|region|quality|size`, with a `model_name|region` simple fallback).
    Mirrors the matching in admin.get_image_model_options so display and cost agree.

    Returns None when the registry has no price for this model/region — the caller
    then tries an on-demand fetch, then `base_price_usd`, and finally surfaces
    "pricing unavailable". NEVER returns a hardcoded guess.
    """
    try:
        from backend.services.model_registry import get_registry
        pricing = get_registry().get("image_pricing", {}) or {}
        if not pricing:
            return None
        label = cfg.get("label", "") or ""
        variants = [label, label.replace("Amazon ", ""), label.replace("Stable ", ""), model_key]
        sizes = ([size] if size else []) + [s for s in ("1024", "512", "") if s != size]
        # 1) precise: model|region|quality|size (T2I rows only)
        for v in variants:
            if not v:
                continue
            for s in sizes:
                pi = pricing.get(f"{v}|{region}|{quality}|{s}", {})
                if pi.get("price_usd") and pi.get("is_t2i", True):
                    return float(pi["price_usd"])
        # 2) simple: model|region
        for v in variants:
            if not v:
                continue
            pi = pricing.get(f"{v}|{region}", {})
            if pi.get("price_usd"):
                return float(pi["price_usd"])
    except Exception:
        pass
    return None


# One full on-demand image-pricing scan per session is enough — the fetch populates
# the whole `image_pricing` map, so this guards against re-scanning the AWS Pricing
# API on every generation when a model is genuinely absent from it.
_image_pricing_ondemand_done = False


def ondemand_image_price(cfg: dict, model_key: str, region: str,
                         quality: str = "", size: str = "") -> float | None:
    """On-demand AWS Pricing API fallback when `image_pricing` has no entry for this
    model (a registry gap). Fetches the full Bedrock image pricing ONCE per session,
    caches it into the in-memory registry (a later Sync persists it durably), then
    re-resolves. Returns None if the online lookup also fails → caller reports
    "pricing unavailable" (never a guess). Registry stays the primary source."""
    global _image_pricing_ondemand_done
    if _image_pricing_ondemand_done:
        return None
    try:
        from backend.routers.admin import _fetch_image_pricing
        from backend.services.model_registry import get_registry
        fetched = _fetch_image_pricing()
        _image_pricing_ondemand_done = True  # set regardless — one attempt per session
        if fetched:
            get_registry().setdefault("image_pricing", {}).update(fetched)
            return resolve_image_price(cfg, model_key, region, quality, size)
    except Exception as exc:
        _image_pricing_ondemand_done = True
        logger.warning("On-demand image price fetch failed for %s|%s: %s", model_key, region, exc)
    return None


def resolve_video_price_per_sec(vid_cfg: dict, model_key: str, region: str = "") -> float | None:
    """Registry-sourced per-SECOND video price for the given region — reads the
    Sync-recorded `video_pricing[model|region]` section when present, else the
    model's `base_price_per_second_usd`. Returns None if neither exists → caller
    surfaces "pricing unavailable" (never a hardcoded guess).

    Note: only Nova Reel is priced by the AWS Pricing API; 3rd-party video models
    (e.g. Luma Ray) aren't, so they use the registry-recorded base_price_per_second_usd
    — analogous to Stability on the image side.
    """
    try:
        from backend.services.model_registry import get_registry
        vp = get_registry().get("video_pricing", {}) or {}
        if region and vp:
            label = (vid_cfg or {}).get("label", "") or ""
            for v in (label, model_key, (vid_cfg or {}).get("model_id", "")):
                if not v:
                    continue
                pi = vp.get(f"{v}|{region}")
                pps = pi.get("price_per_second") if isinstance(pi, dict) else pi
                if pps:
                    return float(pps)
    except Exception:
        pass
    bp = (vid_cfg or {}).get("base_price_per_second_usd")
    return float(bp) if bp else None


def compute_llm_cost(model_id: str, input_tokens: int, output_tokens: int,
                     input_price_per_mtok: float | None = None,
                     output_price_per_mtok: float | None = None,
                     region: str | None = None) -> float:
    """Compute the cost of an LLM call from token usage.

    Pricing resolution order (most authoritative first):
      1. Explicit prices passed by the caller (e.g. a model config).
      2. LIVE per-model, per-REGION prices synced from the AWS Pricing API onto the
         chat_models registry (_registry_llm_price, using `region` when prices vary
         by region) — the ONLY source. If a model isn't priced there yet, cost is 0.0
         ("pricing unavailable") — there is no hardcoded fallback.
    """
    if input_price_per_mtok is not None and output_price_per_mtok is not None:
        input_cost = (input_tokens / 1_000_000) * input_price_per_mtok
        output_cost = (output_tokens / 1_000_000) * output_price_per_mtok
        return round(input_cost + output_cost, 6)

    # 2) Registry-ONLY — live, per-model, region-aware, Sync-maintained. No hardcoded
    # fallback: an unpriced model returns 0.0 (surfaced as "pricing unavailable")
    # until a Sync records its per-token price.
    pricing = _registry_llm_price(model_id, region)
    if not pricing:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * pricing["input_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_mtok"]
    return round(input_cost + output_cost, 6)
