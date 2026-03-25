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
from contextvars import ContextVar
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

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


def compute_llm_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Compute the cost of an LLM call from token usage."""
    pricing = LLM_PRICING.get(model_id)
    if not pricing:
        # Try partial match
        for key, p in LLM_PRICING.items():
            if key in model_id or model_id in key:
                pricing = p
                break
    if not pricing:
        # Default to Sonnet pricing as a reasonable estimate
        pricing = {"input_per_mtok": 3.00, "output_per_mtok": 15.00}

    input_cost = (input_tokens / 1_000_000) * pricing["input_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_mtok"]
    return round(input_cost + output_cost, 6)
