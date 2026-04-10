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

# Infrastructure pricing defaults per region — overridden by registry "infra_pricing" section.
# Prices vary by region (US standard shown). Registry can override per-region.
_INFRA_PRICING_DEFAULTS = {
    "us-east-1": {"s3_put_per_1k": 0.005, "s3_get_per_1k": 0.0004, "s3_transfer_out_per_gb": 0.09},
    "us-west-2": {"s3_put_per_1k": 0.005, "s3_get_per_1k": 0.0004, "s3_transfer_out_per_gb": 0.09},
    "ap-southeast-2": {"s3_put_per_1k": 0.0055, "s3_get_per_1k": 0.00044, "s3_transfer_out_per_gb": 0.114},
    "eu-west-1": {"s3_put_per_1k": 0.0054, "s3_get_per_1k": 0.00043, "s3_transfer_out_per_gb": 0.09},
}
_INFRA_FALLBACK = {"s3_put_per_1k": 0.005, "s3_get_per_1k": 0.0004, "s3_transfer_out_per_gb": 0.09}


def _get_infra_pricing(region: str | None = None) -> dict:
    """Get infrastructure pricing for a region. Registry overrides take precedence."""
    try:
        from backend.services.model_registry import get_registry
        reg_pricing = get_registry().get("infra_pricing", {})
        if region and region in reg_pricing:
            return {**_INFRA_FALLBACK, **reg_pricing[region]}
        if reg_pricing:
            return {**_INFRA_FALLBACK, **reg_pricing}
    except Exception:
        pass
    if region:
        return _INFRA_PRICING_DEFAULTS.get(region, _INFRA_FALLBACK)
    return _INFRA_FALLBACK

# LLM pricing per million tokens (from Bedrock pricing page, March 2026)
# These are defaults — should be moved to the registry for dynamic updates
LLM_PRICING = {
    "us.anthropic.claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "us.anthropic.claude-opus-4-6-v1": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
}


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
    """Compute S3 cost for one operation + data transfer."""
    pricing = _get_infra_pricing(region)
    op = operation.lower()
    if op in ("put", "post", "copy", "list"):
        req_cost = pricing["s3_put_per_1k"] / 1000
    elif op in ("get", "select", "head"):
        req_cost = pricing["s3_get_per_1k"] / 1000
    elif op == "delete":
        return 0.0
    else:
        req_cost = pricing["s3_put_per_1k"] / 1000
    transfer_cost = (size_bytes / (1024 ** 3)) * pricing["s3_transfer_out_per_gb"] if size_bytes > 0 else 0.0
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


def compute_llm_cost(model_id: str, input_tokens: int, output_tokens: int,
                     input_price_per_mtok: float | None = None,
                     output_price_per_mtok: float | None = None) -> float:
    """Compute the cost of an LLM call from token usage.

    If explicit pricing is provided (e.g., from chat_models registry), it is used directly.
    Otherwise falls back to the hardcoded LLM_PRICING dict, then to Sonnet pricing.
    """
    if input_price_per_mtok is not None and output_price_per_mtok is not None:
        input_cost = (input_tokens / 1_000_000) * input_price_per_mtok
        output_cost = (output_tokens / 1_000_000) * output_price_per_mtok
        return round(input_cost + output_cost, 6)

    pricing = LLM_PRICING.get(model_id)
    if not pricing:
        # Try partial match
        for key, p in LLM_PRICING.items():
            if key in model_id or model_id in key:
                pricing = p
                break
    if not pricing:
        # Try chat_models registry for discovered models
        try:
            from backend.services.model_registry import get_registry
            reg = get_registry()
            for cm in reg.get("chat_models", {}).values():
                if cm.get("model_id") == model_id:
                    in_p = cm.get("input_price_per_1k", 0)
                    out_p = cm.get("output_price_per_1k", 0)
                    if in_p or out_p:
                        input_cost = (input_tokens / 1_000_000) * (in_p * 1000)
                        output_cost = (output_tokens / 1_000_000) * (out_p * 1000)
                        return round(input_cost + output_cost, 6)
        except Exception:
            pass
        # Default to Sonnet pricing as a reasonable estimate
        pricing = {"input_per_mtok": 3.00, "output_per_mtok": 15.00}

    input_cost = (input_tokens / 1_000_000) * pricing["input_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_mtok"]
    return round(input_cost + output_cost, 6)
