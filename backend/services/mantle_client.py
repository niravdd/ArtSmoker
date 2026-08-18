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


def _derive_token(region: str) -> str | None:
    """Derive + cache a short-term Bedrock token from the current AWS creds."""
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
            # nosemgrep -- logs the region + error only; no token value is interpolated
            logger.warning("Could not derive a Bedrock token for %s: %s", region, exc)
            return None
        if token:
            _token_cache[region] = (token, _now() + _TOKEN_TTL_SECONDS)
        return token


def get_bedrock_token(region: str, *, force_derive: bool = False) -> str | None:
    """Return a Bedrock bearer token for the given region (cached + refreshed).

    Priority:
      1. ``AWS_BEARER_TOKEN_BEDROCK`` env var, if the operator set one explicitly
         (an operator-owned override — we never rewrite it).
      2. A short-term token derived from the current AWS credentials via
         ``aws_bedrock_token_generator`` (cached ~8h; no stored secret).
    Returns None if neither is available (Mantle then cleanly unavailable).
    The token value is never logged.

    ``force_derive=True`` skips the env var and derives fresh — used by the
    retry path when an env-var token turns out to be stale/expired (so we
    self-heal without mutating ``os.environ`` or changing the operator's value).
    """
    if not force_derive:
        env_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
        if env_token:
            return env_token
    return _derive_token(region)


def _is_auth_error(exc: Exception) -> bool:
    """True if the exception looks like an expired/invalid bearer token (401/403)."""
    code = getattr(getattr(exc, "response", None), "status_code", None)
    if code in (401, 403):
        return True
    txt = str(exc).lower()
    return ("401" in txt or "403" in txt or "expired" in txt or "unauthorized" in txt
            or "invalid" in txt and "token" in txt or "security token" in txt)


class MantleAccessError(RuntimeError):
    """Raised when Amazon Bedrock Mantle is unreachable for permission/setup
    reasons, with an actionable, user-facing message (no raw stack/HTTP noise)."""


# Actionable guidance shared by every Mantle access failure. Names the exact
# AWS managed policies (verified against the AWS docs) so the operator knows the
# fix, not just that "something failed".
_MANTLE_ACCESS_HELP = (
    "Amazon Bedrock Mantle access was denied. This model is only reachable via "
    "the bedrock-mantle endpoint, which needs Mantle inference permissions on "
    "the IAM identity ArtSmoker runs as. To fix, attach one of these AWS managed "
    "policies (or an equivalent): \"AmazonBedrockMantleInferenceAccess\" "
    "(read + CreateInference + bearer-token calls — recommended) or "
    "\"AmazonBedrockMantleFullAccess\". For third-party models (OpenAI, GLM, "
    "Grok, etc.), AWS Marketplace subscribe permissions may also be required; "
    "an account admin can subscribe once in the Bedrock console. Meanwhile, "
    "Claude models that run via the Converse endpoint keep working without this."
)


def _permission_denied_error(region: str, exc: Exception) -> "MantleAccessError":
    """Build a clear MantleAccessError from a denied Mantle response."""
    detail = str(exc)
    # Keep the message actionable but include a short raw hint for diagnostics.
    return MantleAccessError(f"{_MANTLE_ACCESS_HELP} (region {region}; detail: {detail[:160]})")


def _mantle_call(region: str, fn):
    """Run a Mantle call, retrying ONCE with a freshly-derived token on auth error.

    ``fn(client)`` performs the actual request. On the first 401/403 we discard
    the (possibly stale env-var or cached) token, derive a fresh one from AWS
    creds, rebuild the client, and retry. os.environ is never modified — the
    operator's AWS_BEARER_TOKEN_BEDROCK stays as they set it.

    A short-term token is signed LOCALLY (no AWS call), so a true *permission*
    gap doesn't surface at derivation — it surfaces as a 401/403 from Mantle.
    If the retry with a fresh token STILL gets denied, that's a genuine IAM/
    Marketplace permission problem, not a stale token: we raise MantleAccessError
    with the exact managed policies to attach.
    """
    m_region = mantle_region_for(region)
    try:
        return fn(_build_client(m_region))
    except Exception as exc:
        if not _is_auth_error(exc):
            raise
        # Invalidate any cached derived token for this region, then force-derive.
        with _token_lock:
            _token_cache.pop(m_region, None)
        fresh = get_bedrock_token(m_region, force_derive=True)
        if not fresh:
            raise MantleAccessError(_MANTLE_ACCESS_HELP)
        logger.info("Mantle auth failed for %s — retrying with a freshly derived token", m_region)
        try:
            return fn(_build_client(m_region, token=fresh))
        except Exception as exc2:
            # Fresh token still denied → real permission/Marketplace gap, not staleness.
            if _is_auth_error(exc2):
                # nosemgrep -- logs the region + error only; no token value is interpolated
                logger.warning("Mantle access denied for %s even with a fresh token: %s",
                               m_region, str(exc2)[:200])
                raise _permission_denied_error(m_region, exc2) from exc2
            raise


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


def _build_client(region: str, token: str | None = None):
    """Build a fresh OpenAI client for the Mantle endpoint in ``region``.

    Not cached: the bearer token rotates, and the OpenAI client captures the
    key at construction. Construction is cheap (no network), so we build per
    call with a current token. Pass ``token`` to use a specific (e.g. freshly
    re-derived) token; otherwise the standard priority applies.
    ``region`` must already be Mantle-supported (callers pass mantle_region_for).
    """
    from openai import OpenAI

    tok = token or get_bedrock_token(region)
    if not tok:
        raise MantleAccessError(
            "Amazon Bedrock Mantle is unavailable: no bearer token could be "
            "obtained. Either the active AWS credentials couldn't sign a token "
            "(check the credentials ArtSmoker runs as), the "
            "aws-bedrock-token-generator package isn't installed, or no "
            "AWS_BEARER_TOKEN_BEDROCK is set. Claude models via the Converse "
            "endpoint are unaffected."
        )
    return OpenAI(api_key=tok, base_url=_base_url(region))


def _get_openai_client(region: str):
    """Back-compat: build a client for an arbitrary region (region-mapped)."""
    return _build_client(mantle_region_for(region))


# ── Invokers (one per Mantle API surface) ───────────────────────────────────

def _capture_usage(usage_out: dict | None, usage_obj) -> None:
    """Copy input/output token counts from a provider usage object into usage_out
    (so the caller can compute cost). Handles OpenAI (prompt_tokens/completion_tokens),
    Responses (input_tokens/output_tokens), and Anthropic (input_tokens/output_tokens)
    shapes. No-op if usage_out is None or the object is missing fields."""
    if usage_out is None or usage_obj is None:
        return
    def _get(o, name):
        return getattr(o, name, None) if not isinstance(o, dict) else o.get(name)
    inp = _get(usage_obj, "prompt_tokens") or _get(usage_obj, "input_tokens") or 0
    out = _get(usage_obj, "completion_tokens") or _get(usage_obj, "output_tokens") or 0
    usage_out["input_tokens"] = int(inp or 0)
    usage_out["output_tokens"] = int(out or 0)


def invoke_chat_completions(
    model_id: str,
    messages: list[dict],
    *,
    region: str | None = None,
    max_tokens: int = 4096,
    temperature: float | None = None,
    extra: dict | None = None,
    usage_out: dict | None = None,
) -> str:
    """OpenAI Chat Completions on Mantle. ``messages`` are OpenAI-format
    ({role, content}). Returns the assistant text. If ``usage_out`` is provided,
    it's populated with input_tokens/output_tokens for cost tracking."""
    kwargs: dict = {"model": model_id, "messages": messages, "max_completion_tokens": max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if extra:
        kwargs.update(extra)

    def _do(client):
        resp = client.chat.completions.create(**kwargs)
        _capture_usage(usage_out, getattr(resp, "usage", None))
        return resp.choices[0].message.content or ""

    return _mantle_call(region or settings.aws_region_models, _do)


def invoke_responses(
    model_id: str,
    input_messages: list[dict],
    *,
    region: str | None = None,
    max_output_tokens: int = 4096,
    store: bool = False,
    extra: dict | None = None,
    usage_out: dict | None = None,
) -> str:
    """OpenAI Responses API on Mantle (required by frontier models e.g. GPT-5.x).

    ``store`` defaults to False so Bedrock retains no conversation data unless
    the caller opts in (the OpenAI default is True; we choose privacy-first).
    Returns the aggregated output text. If ``usage_out`` is provided, it's
    populated with input_tokens/output_tokens for cost tracking.
    """
    kwargs: dict = {
        "model": model_id,
        "input": input_messages,
        "max_output_tokens": max_output_tokens,
        "store": store,
    }
    if extra:
        kwargs.update(extra)

    def _do(client):
        resp = client.responses.create(**kwargs)
        _capture_usage(usage_out, getattr(resp, "usage", None))
        # output_text is the SDK's convenience aggregation of text output items.
        return getattr(resp, "output_text", "") or ""

    return _mantle_call(region or settings.aws_region_models, _do)


def invoke_messages(
    model_id: str,
    messages: list[dict],
    *,
    region: str | None = None,
    system: str = "",
    max_tokens: int = 4096,
    temperature: float | None = None,
    extra: dict | None = None,
    usage_out: dict | None = None,
) -> str:
    """Anthropic Messages API on Mantle (e.g. Claude Mythos is Messages-only).

    Uses the OpenAI SDK's raw request path against the ``/anthropic/v1/messages``
    route so we don't need a second SDK. ``messages`` are Anthropic-format
    ({role, content}). Returns the concatenated text blocks. If ``usage_out`` is
    provided, it's populated with input_tokens/output_tokens for cost tracking.
    """
    m_region = mantle_region_for(region or settings.aws_region_models)
    import requests

    url = f"https://bedrock-mantle.{m_region}.api.aws/anthropic/v1/messages"
    body: dict = {"model": model_id, "messages": messages, "max_tokens": max_tokens}
    if system:
        body["system"] = system
    if temperature is not None:
        body["temperature"] = temperature
    if extra:
        body.update(extra)

    def _post(token: str):
        headers = {
            "Authorization": f"Bearer {token}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=body, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        _capture_usage(usage_out, data.get("usage"))
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    token = get_bedrock_token(m_region)
    if not token:
        raise MantleAccessError(_MANTLE_ACCESS_HELP)
    try:
        return _post(token)
    except Exception as exc:
        # Self-heal a stale env-var/cached token: derive fresh + retry once.
        if not _is_auth_error(exc):
            raise
        with _token_lock:
            _token_cache.pop(m_region, None)
        fresh = get_bedrock_token(m_region, force_derive=True)
        if not fresh:
            raise MantleAccessError(_MANTLE_ACCESS_HELP)
        logger.info("Mantle Messages auth failed for %s — retrying with a fresh token", m_region)
        try:
            return _post(fresh)
        except Exception as exc2:
            if _is_auth_error(exc2):
                # nosemgrep -- logs the region + error only; no token value is interpolated
                logger.warning("Mantle Messages access denied for %s even with a fresh token: %s",
                               m_region, str(exc2)[:200])
                raise _permission_denied_error(m_region, exc2) from exc2
            raise


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
