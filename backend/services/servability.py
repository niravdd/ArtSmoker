"""Per-Region chat-model servability — which Regions actually answer a model.

A Region can list a model (and its inference profile can cover the Region) yet
never answer it: the request hangs until the read timeout, or AWS rejects it as
not found / not served there. The listings can't show this, so AWS Sync sends
each enabled chat model a tiny request in every Region its pinned id routes from
and records the dead ones on the entry:

    unservable_regions = {<id kind>: {<Region>: {"reason", "detected_at"}}}

``<id kind>`` is the id's profile prefix (``global``, ``us``, ``eu``, …) or ``""``
for a plain id — a Region dead for one profile can serve another. The record is
per account (a user-only field, kept in user.json), re-probed by every Sync. A
chat request that times out records its Region too, until the next Sync.
Pickers and auto-routing skip recorded Regions (``chat._model_usable_regions``).
"""

import logging
import threading
from datetime import datetime, timezone

from backend.config import settings

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_S = 20.0
PROBE_MAX_TOKENS = 16    # the Responses API rejects fewer than 16 output tokens
OK = "ok"
LEGACY = "legacy_access_denied"  # per account → lifecycle_unavailable, not a Region fact
# Reasons where AWS itself says the model can't be invoked there (any account).
# A model with only these, in every Region, is not registered at all.
NOT_SERVED = {"not_found", "unsupported"}

# Bedrock ValidationException wording for "this id isn't invocable here" (as
# opposed to a bad request parameter, which says nothing about the Region).
_UNSUPPORTED_HINTS = ("model identifier", "on-demand throughput")
# Wording for a Region that won't run the model for THIS account (its data-
# retention mode isn't offered there) — the model works elsewhere, so the Region
# is skipped but the model is kept.
NOT_AVAILABLE = "not_available"
_NOT_AVAILABLE_HINTS = ("retention mode",)
# Mantle 400 wording for an unknown model or a route the model doesn't serve.
_MANTLE_NOT_SERVED_HINTS = ("not found", "does not exist", "does not support")

_clients: dict = {}
_clients_lock = threading.Lock()


def id_kind(model_id: str) -> str:
    """Profile prefix of a model id (``global``/``us``/``eu``/…), ``""`` if plain.
    Geos come from the registry (strip_geo_prefix) — none are hardcoded here."""
    from backend.services.model_registry import strip_geo_prefix
    mid = model_id or ""
    return "" if strip_geo_prefix(mid) == mid else mid.split(".", 1)[0]


def unservable_for(cfg: dict, model_id: str) -> dict:
    """Recorded dead Regions ({Region: info}) for ``model_id``'s id kind."""
    return ((cfg.get("unservable_regions") or {}).get(id_kind(model_id))) or {}


def region_rejection(message: str) -> str | None:
    """What a Converse ValidationException says about its Region: NOT_AVAILABLE,
    ``unsupported``, or None when it's about the request, not the Region."""
    low = (message or "").lower()
    if any(h in low for h in _NOT_AVAILABLE_HINTS):
        return NOT_AVAILABLE
    if any(h in low for h in _UNSUPPORTED_HINTS):
        return "unsupported"
    return None


def _runtime_client(region: str):
    """A bedrock-runtime client with a short read timeout and no retries, so a
    hung Region costs the probe seconds, not the default minutes."""
    with _clients_lock:
        if region not in _clients:
            import boto3
            from botocore.config import Config
            session = (boto3.Session(region_name=region, profile_name=settings.aws_profile)
                       if settings.aws_profile else boto3.Session(region_name=region))
            _clients[region] = session.client("bedrock-runtime", config=Config(
                connect_timeout=5, read_timeout=PROBE_TIMEOUT_S,
                retries={"total_max_attempts": 1, "mode": "standard"},
                max_pool_connections=32))
        return _clients[region]


def _probe_converse(model_id: str, region: str) -> str | None:
    """One Converse call (retried once on a timeout). Returns OK, a definitive
    reason, or None when inconclusive (throttling, 5xx, credentials, …)."""
    from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError
    for attempt in (1, 2):
        try:
            _runtime_client(region).converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": "Reply with OK."}]}],
                inferenceConfig={"maxTokens": PROBE_MAX_TOKENS})
            return OK
        except (ReadTimeoutError, ConnectTimeoutError):
            if attempt == 2:
                return "timeout"
        except ClientError as exc:
            from backend.services.model_registry import is_legacy_unavailable_error
            code = (exc.response or {}).get("Error", {}).get("Code", "")
            if is_legacy_unavailable_error(exc):
                return LEGACY  # this account lost access to a Legacy model
            if code == "ResourceNotFoundException":
                return "not_found"
            if code == "AccessDeniedException":
                return "access_denied"
            if code == "ValidationException":
                return region_rejection(str(exc))
            return None
        except Exception:
            return None
    return None


def _probe_mantle(model_id: str, provider: str, region: str) -> str | None:
    """Try the model's Mantle routes in the order chat uses them (registry-derived
    first, then the self-heal fallbacks). OK on the first that answers; else
    ``timeout`` if a route hung, else a reason only when every route failed
    definitively."""
    import openai
    import requests
    from backend.services import mantle_client as mc
    msgs = [{"role": "user", "content": "Reply with OK."}]
    api_model = mc._bare_mantle_id(model_id)
    reasons = set()
    for idx, (base_path, route) in enumerate(mc.mantle_invocation_candidates(model_id, provider)):
        # The primary route gets a second try on a timeout; a fallback route one.
        for attempt in ((1, 2) if idx == 0 else (2,)):
            try:
                if route == "messages":
                    mc.invoke_messages(model_id, msgs, region=region,
                                       max_tokens=PROBE_MAX_TOKENS, timeout=PROBE_TIMEOUT_S)
                else:
                    client = mc._get_openai_client(region, base_path).with_options(
                        timeout=PROBE_TIMEOUT_S)
                    if route == "responses":
                        client.responses.create(model=api_model, input=msgs,
                                                max_output_tokens=PROBE_MAX_TOKENS, store=False)
                    elif route == "chat_completions":
                        client.chat.completions.create(model=api_model, messages=msgs,
                                                       max_completion_tokens=PROBE_MAX_TOKENS)
                    else:
                        reasons.add(None)
                        break
                return OK
            except (openai.APITimeoutError, requests.Timeout):
                if attempt == 2:
                    reasons.add("timeout")  # hung — chat moves on to the next route too
            except openai.NotFoundError:
                reasons.add("not_found")
                break
            except (openai.PermissionDeniedError, mc.MantleAccessError):
                reasons.add("access_denied")
                break
            except openai.BadRequestError as exc:
                low = str(exc).lower()
                reasons.add("not_found" if any(h in low for h in _MANTLE_NOT_SERVED_HINTS) else None)
                break
            except requests.HTTPError as exc:
                resp = getattr(exc, "response", None)
                status = getattr(resp, "status_code", 0)
                low = (getattr(resp, "text", "") or "").lower()
                if status == 404 or (status == 400 and any(h in low for h in _MANTLE_NOT_SERVED_HINTS)):
                    reasons.add("not_found")
                elif status == 403:
                    reasons.add("access_denied")
                else:
                    reasons.add(None)
                break
            except Exception:
                reasons.add(None)
                break
    if "timeout" in reasons:
        return "timeout"  # no route answered and one hung — chat would hang here too
    if None in reasons or not reasons:
        return None
    return "access_denied" if "access_denied" in reasons else "not_found"


def probe_region(model_id: str, cfg: dict, region: str) -> str | None:
    """Whether ``region`` answers ``model_id`` on the endpoint chat uses for it.
    OK, a definitive reason (``timeout``/``not_found``/``unsupported``/
    ``access_denied``/LEGACY), or None when the result says nothing about the Region."""
    try:
        if cfg.get("invoke_endpoint") == "bedrock-mantle":
            return _probe_mantle(model_id, cfg.get("provider", ""), region)
        return _probe_converse(model_id, region)
    except Exception as exc:
        logger.debug("Servability probe failed for %s@%s: %s", model_id, region, exc)
        return None


def mark_region_unservable(model_id: str, region: str, reason: str = "timeout") -> None:
    """Record (per account, user.json) that ``region`` didn't answer ``model_id``,
    so pickers and auto-routing skip it until the next Sync re-probes."""
    from backend.services.model_registry import mark_chat_region_unservable
    if not mark_chat_region_unservable(model_id, id_kind(model_id), region, {
            "reason": reason, "detected_at": datetime.now(timezone.utc).isoformat()}):
        return
    logger.warning("Chat: %s did not answer in %s (%s) — Region skipped until the next "
                   "AWS Sync", model_id, region, reason)
