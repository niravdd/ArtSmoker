"""Amazon Bedrock **Mantle** client — OpenAI-compatible + Anthropic Messages APIs.

Amazon Bedrock exposes two inference endpoints (see SPEC §4.8):

  • ``bedrock-runtime`` — the Bedrock-native InvokeModel / Converse APIs, called
    via boto3 (handled in ``bedrock_client.py``). This is the path for the
    Claude tiers we use day-to-day; it stays the default.
  • ``bedrock-mantle`` — ``https://bedrock-mantle.{region}.api.aws`` — serves the
    OpenAI-compatible **Chat Completions** and **Responses** APIs plus the
    **Anthropic Messages** API. Some frontier models are reachable ONLY here
    (e.g. OpenAI ``gpt-5.x`` are Responses-only; Claude Mythos is Messages-only),
    so we need a first-class client for it.

This module is the Mantle transport. It is intentionally isolated from the
boto3 Converse path — adding it must not perturb anything that already works.

Auth: Mantle uses a **Bedrock bearer token**, not SigV4. We derive a short-term
token (≤12h, inherits the caller's IAM permissions) from the existing AWS
credentials via ``aws_bedrock_token_generator.provide_token`` — nothing is
stored. If a token is supplied out-of-band via ``AWS_BEARER_TOKEN_BEDROCK`` we
use that instead. Token values are NEVER logged.

Regions: Mantle is not available in every region. ``MANTLE_REGIONS`` lists the
supported set (from the AWS docs); ``mantle_region_for`` maps an arbitrary
region to the nearest supported one so a us-west-2-centric deployment still
works.
"""

import logging
import os
import threading
import time

from backend.config import settings

logger = logging.getLogger(__name__)

# Regions where the bedrock-mantle endpoint is offered (AWS docs, 2026-06).
# Keep as a plain set so it's easy to extend; the Sync can refresh nothing here
# (AWS has no programmatic list), so this is the source of truth for routing.
MANTLE_REGIONS = {
    "us-east-1", "us-east-2", "us-west-2",
    "ap-southeast-3", "ap-south-1", "ap-southeast-2", "ap-northeast-1",
    "eu-central-1", "eu-west-1", "eu-west-2", "eu-south-1", "eu-north-1",
    "sa-east-1", "us-gov-west-1",
}

# Fallback when the caller's region has no Mantle endpoint. us-west-2 matches
# this app's default model region (settings.aws_region_models).
_MANTLE_FALLBACK_REGION = "us-west-2"


def mantle_region_for(region: str | None) -> str:
    """Map an arbitrary AWS region to a Mantle-supported region.

    If the region itself supports Mantle, use it; otherwise fall back so a
    deployment configured for a non-Mantle region can still reach frontier
    models. Logged once per distinct miss so the operator can see the remap.
    """
    if region and region in MANTLE_REGIONS:
        return region
    fallback = _MANTLE_FALLBACK_REGION if _MANTLE_FALLBACK_REGION in MANTLE_REGIONS else "us-east-1"
    if region and region not in _mantle_region_for_warned:
        _mantle_region_for_warned.add(region)
        logger.info("Mantle not offered in %s — routing Mantle calls to %s", region, fallback)
    return fallback


_mantle_region_for_warned: set[str] = set()


# ── Bedrock bearer token (short-term, derived from AWS creds) ───────────────
# Cache one token per region with an expiry so we don't re-mint on every call
# but always refresh before the ~12h lifetime lapses.

_token_lock = threading.Lock()
_token_cache: dict[str, tuple[str, float]] = {}  # region -> (token, expires_at_epoch)
_TOKEN_TTL_SECONDS = 8 * 3600  # refresh well inside the ≤12h server lifetime


def _now() -> float:
    return time.time()


def get_bedrock_token(region: str) -> str | None:
    """Return a Bedrock bearer token for the given region (cached + refreshed).

    Priority:
      1. ``AWS_BEARER_TOKEN_BEDROCK`` env var, if the operator set one explicitly.
      2. A short-term token derived from the current AWS credentials via
         ``aws_bedrock_token_generator`` (no stored secret).
    Returns None if neither is available (Mantle then cleanly unavailable).
    The token value is never logged.
    """
    env_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if env_token:
        return env_token

    with _token_lock:
        cached = _token_cache.get(region)
        if cached and cached[1] > _now():
            return cached[0]
        try:
            from aws_bedrock_token_generator import provide_token
        except ImportError:
            logger.warning(
                "aws-bedrock-token-generator not installed — Mantle endpoint "
                "unavailable. Install it or set AWS_BEARER_TOKEN_BEDROCK."
            )
            return None
        try:
            try:
                token = provide_token(region=region)
            except TypeError:
                # Older/newer signature without a region kwarg.
                token = provide_token()
        except Exception as exc:
            logger.warning("Could not derive a Bedrock token for %s: %s", region, exc)
            return None
        if token:
            _token_cache[region] = (token, _now() + _TOKEN_TTL_SECONDS)
        return token


def mantle_available(region: str | None = None) -> bool:
    """Whether the Mantle endpoint is usable right now (deps + auth present)."""
    try:
        import openai  # noqa: F401
    except ImportError:
        return False
    return get_bedrock_token(mantle_region_for(region or settings.aws_region_models)) is not None


# ── OpenAI SDK client pointed at bedrock-mantle ─────────────────────────────

def _base_url(region: str) -> str:
    return f"https://bedrock-mantle.{region}.api.aws/v1"


def _get_openai_client(region: str):
    """Build a fresh OpenAI client for the Mantle endpoint in ``region``.

    Not cached: the bearer token rotates, and the OpenAI client captures the
    key at construction. Construction is cheap (no network), so we build per
    call with a current token.
    """
    from openai import OpenAI

    m_region = mantle_region_for(region)
    token = get_bedrock_token(m_region)
    if not token:
        raise RuntimeError(
            "No Bedrock bearer token available for Mantle. Install "
            "aws-bedrock-token-generator or set AWS_BEARER_TOKEN_BEDROCK."
        )
    return OpenAI(api_key=token, base_url=_base_url(m_region))


# ── Invokers (one per Mantle API surface) ───────────────────────────────────

def invoke_chat_completions(
    model_id: str,
    messages: list[dict],
    *,
    region: str | None = None,
    max_tokens: int = 4096,
    temperature: float | None = None,
    extra: dict | None = None,
) -> str:
    """OpenAI Chat Completions on Mantle. ``messages`` are OpenAI-format
    ({role, content}). Returns the assistant text."""
    client = _get_openai_client(region or settings.aws_region_models)
    kwargs: dict = {"model": model_id, "messages": messages, "max_completion_tokens": max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if extra:
        kwargs.update(extra)
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def invoke_responses(
    model_id: str,
    input_messages: list[dict],
    *,
    region: str | None = None,
    max_output_tokens: int = 4096,
    store: bool = False,
    extra: dict | None = None,
) -> str:
    """OpenAI Responses API on Mantle (required by frontier models e.g. GPT-5.x).

    ``store`` defaults to False so Bedrock retains no conversation data unless
    the caller opts in (the OpenAI default is True; we choose privacy-first).
    Returns the aggregated output text.
    """
    client = _get_openai_client(region or settings.aws_region_models)
    kwargs: dict = {
        "model": model_id,
        "input": input_messages,
        "max_output_tokens": max_output_tokens,
        "store": store,
    }
    if extra:
        kwargs.update(extra)
    resp = client.responses.create(**kwargs)
    # output_text is the SDK's convenience aggregation of text output items.
    return getattr(resp, "output_text", "") or ""


def invoke_messages(
    model_id: str,
    messages: list[dict],
    *,
    region: str | None = None,
    system: str = "",
    max_tokens: int = 4096,
    temperature: float | None = None,
    extra: dict | None = None,
) -> str:
    """Anthropic Messages API on Mantle (e.g. Claude Mythos is Messages-only).

    Uses the OpenAI SDK's raw request path against the ``/anthropic/v1/messages``
    route so we don't need a second SDK. ``messages`` are Anthropic-format
    ({role, content}). Returns the concatenated text blocks.
    """
    m_region = mantle_region_for(region or settings.aws_region_models)
    token = get_bedrock_token(m_region)
    if not token:
        raise RuntimeError("No Bedrock bearer token available for Mantle Messages.")
    import requests

    url = f"https://bedrock-mantle.{m_region}.api.aws/anthropic/v1/messages"
    body: dict = {"model": model_id, "messages": messages, "max_tokens": max_tokens}
    if system:
        body["system"] = system
    if temperature is not None:
        body["temperature"] = temperature
    if extra:
        body.update(extra)
    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    return "".join(parts)


# ── Endpoint/API capability resolution (registry-driven routing) ────────────
# AWS exposes no programmatic per-model API matrix, so we derive capabilities
# from provider/model-family heuristics grounded in the AWS compatibility docs
# (verified 2026-06). The result is written to the registry by Sync and is
# user-overridable in .user.json; the invoke path just reads the resolved
# invoke_endpoint/invoke_api. Routing policy (user-confirmed): Converse-first,
# Mantle only when a model can't be reached via Converse.

# Priority order: lowest-friction, most-capable-for-us first. Converse keeps
# Guardrails + us.* cross-region inference profiles and needs no bearer token.
_API_PRIORITY = ("converse", "chat_completions", "responses", "messages")

_ENDPOINT_FOR_API = {
    "converse": "bedrock-runtime",
    "invoke": "bedrock-runtime",
    "chat_completions": "bedrock-mantle",   # we call it via Mantle
    "responses": "bedrock-mantle",
    "messages": "bedrock-mantle",
}


def derive_model_apis(model_id: str, provider: str, *, on_mantle: bool = False,
                      on_runtime: bool = True) -> list[str]:
    """Best-effort list of APIs a model supports, from provider/family heuristics.

    Grounded in the AWS "API compatibility by models" matrix (2026-06):
      • Anthropic Claude on runtime → Converse (+ Invoke). On Mantle → Messages
        (NOT Chat Completions). Newer Claude (Mythos) is Messages-only on Mantle.
      • OpenAI gpt-5.x → Responses-only (Mantle). gpt-oss → Converse + Chat
        Completions + Responses.
      • Most other text models on runtime → Converse.
    ``on_mantle``/``on_runtime`` say which endpoint listings the model appeared
    in during Sync; they refine the heuristic. This is intentionally
    conservative and ALWAYS overridable via the registry.
    """
    mid = (model_id or "").lower()
    prov = (provider or "").lower()
    apis: list[str] = []

    if "anthropic" in prov or "claude" in mid:
        if on_runtime:
            apis += ["converse", "invoke"]
        if on_mantle:
            apis.append("messages")
        # A Claude that's mantle-only (no runtime) is Messages-only.
        if on_mantle and not on_runtime and "messages" not in apis:
            apis = ["messages"]
        return apis

    if "openai" in prov or mid.startswith("openai.") or "gpt" in mid:
        if "gpt-5" in mid or "gpt5" in mid:
            return ["responses"]  # frontier GPT-5.x are Responses-only
        if "gpt-oss" in mid:
            out = []
            if on_runtime:
                out += ["converse", "invoke"]
            out += ["chat_completions"]
            if on_mantle:
                out.append("responses")
            return out
        # Unknown OpenAI model: prefer chat_completions on Mantle.
        return ["chat_completions"] if on_mantle else (["converse"] if on_runtime else ["chat_completions"])

    # Everyone else: Converse on runtime is the safe default; add chat on Mantle.
    out = []
    if on_runtime:
        out.append("converse")
    if on_mantle:
        out.append("chat_completions")
    return out or ["converse"]


def resolve_invoke_path(apis: list[str]) -> tuple[str, str]:
    """Pick the single (endpoint, api) our app will use, Converse-first.

    Returns e.g. ("bedrock-runtime","converse") or ("bedrock-mantle","responses").
    Defaults to runtime/converse if the list is empty/unknown.
    """
    for api in _API_PRIORITY:
        if api in (apis or []):
            return _ENDPOINT_FOR_API.get(api, "bedrock-runtime"), api
    return "bedrock-runtime", "converse"


def list_mantle_models(region: str | None = None) -> list[str]:
    """List model IDs available on the Mantle endpoint (used by Sync). Empty on error."""
    try:
        client = _get_openai_client(region or settings.aws_region_models)
        return [m.id for m in client.models.list().data]
    except Exception as exc:
        logger.warning("Mantle models.list failed: %s", str(exc)[:200])
        return []
