"""User notices — durable, dismissible "what happened while you were away" store.

Some things happen in the background with no user watching: a self-hosted model
deploy that succeeds/fails ~20 min after the browser was closed, an endpoint
auto-torn-down on failure, etc. Logging isn't enough — the user should be told,
next time they open the app, in plain language.

Persisted to S3 (the same deployment bucket async-jobs use, under
`artsmoker/notices/`) so notices survive server restarts and are consistent with
how the rest of the app stores background state — NOT a local file. An in-memory
list mirrors S3 for fast reads; every mutation writes through to S3.

The frontend polls /api/health, which surfaces unseen notices as a dismissible
banner; the user dismisses them via /api/notices/{id}/dismiss.

Deliberately minimal: single-user self-hosted tool — no per-user scoping, no
push/email — just "record now, show on next load, let them dismiss".
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_S3_PREFIX = "artsmoker/notices/"
_S3_KEY = _S3_PREFIX + "notices.json"   # single rolling document (small, bounded)
_MAX_NOTICES = 200                       # keep the doc bounded — drop oldest beyond this
_lock = threading.RLock()

_cache: list | None = None               # in-memory mirror; None = not yet loaded
_cache_loaded = False


def _s3():
    """(client, bucket) or (None, None) if no deployment bucket is configured."""
    try:
        import boto3
        from backend.services.sagemaker_deployer import get_deployment_s3_bucket
        from backend.config import settings
        bucket = get_deployment_s3_bucket()
        if not bucket:
            return None, None
        return boto3.client("s3", region_name=settings.aws_region_models), bucket
    except Exception as exc:
        logger.debug("Notices S3 client unavailable: %s", exc)
        return None, None


def _load() -> list:
    """Return the notices list, loading from S3 once into the in-memory cache."""
    global _cache, _cache_loaded
    with _lock:
        if _cache_loaded and _cache is not None:
            return _cache
        notices = []
        s3, bucket = _s3()
        if s3 and bucket:
            try:
                obj = s3.get_object(Bucket=bucket, Key=_S3_KEY)
                notices = json.loads(obj["Body"].read())
                if not isinstance(notices, list):
                    notices = []
            except s3.exceptions.NoSuchKey:
                notices = []
            except Exception as exc:
                # A ClientError for a missing key also lands here on some setups.
                if "NoSuchKey" not in str(exc) and "Not Found" not in str(exc):
                    logger.debug("Notices S3 load failed: %s", exc)
                notices = []
        _cache = notices
        _cache_loaded = True
        return _cache


def _save(notices: list):
    global _cache
    with _lock:
        _cache = notices
        _cache_loaded = True
        s3, bucket = _s3()
        if not (s3 and bucket):
            logger.debug("Notices: no S3 bucket — kept in memory only")
            return
        try:
            body = json.dumps(notices, indent=2).encode("utf-8")
            s3.put_object(Bucket=bucket, Key=_S3_KEY, Body=body, ContentType="application/json")
            try:
                from backend.services.cost_tracker import add_background_s3_cost
                add_background_s3_cost("put", len(body), "notices persist")
            except Exception:
                pass
        except Exception as exc:
            logger.warning("Notices S3 save failed: %s", exc)


def add_notice(kind: str, title: str, message: str, level: str = "info",
               dedup_key: str = "") -> dict:
    """Record a durable user notice.

    kind: machine tag (e.g. "deploy_failed", "deploy_ready"). level:
    "info"|"success"|"warning"|"error". dedup_key: if set, an existing UNSEEN
    notice with the same dedup_key is replaced rather than duplicated.
    """
    with _lock:
        notices = list(_load())
        if dedup_key:
            notices = [n for n in notices if not (n.get("dedup_key") == dedup_key and not n.get("seen"))]
        notice = {
            "id": uuid.uuid4().hex[:12],
            "kind": kind,
            "title": title,
            "message": message,
            "level": level,
            "dedup_key": dedup_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seen": False,
        }
        notices.append(notice)
        if len(notices) > _MAX_NOTICES:
            notices = notices[-_MAX_NOTICES:]
        _save(notices)
        logger.info("Notice recorded [%s/%s]: %s", kind, level, title)
        return notice


def list_unseen() -> list:
    """Notices the user hasn't dismissed yet (newest first)."""
    with _lock:
        return list(reversed([n for n in _load() if not n.get("seen")]))


def list_all() -> list:
    """All notices, newest first (for a future history view)."""
    with _lock:
        return list(reversed(_load()))


def dismiss(notice_id: str) -> bool:
    with _lock:
        notices = _load()
        found = False
        for n in notices:
            if n.get("id") == notice_id and not n.get("seen"):
                n["seen"] = True
                found = True
        if found:
            _save(notices)
        return found


def dismiss_all() -> int:
    with _lock:
        notices = _load()
        n = 0
        for x in notices:
            if not x.get("seen"):
                x["seen"] = True
                n += 1
        if n:
            _save(notices)
        return n
