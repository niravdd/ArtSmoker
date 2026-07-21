"""User notices — durable, dismissible "what happened while you were away" store.

Some events happen in the background with no user watching: a self-hosted model
deploy that fails ~20 min after the browser was closed, an endpoint auto-torn-down
on failure, etc. Logging them isn't enough — the user needs to be told, next time
they open the app, in plain language ("HunyuanImage 3.0 deploy failed:
InsufficientInstanceCapacity — auto-removed; you can redeploy").

This is a tiny persistent store (JSON on disk under data/) so notices survive a
server restart. The frontend polls /api/health, which surfaces unseen notices as
a dismissible banner; the user dismisses them via /api/notices/{id}/dismiss.

Deliberately minimal: single-user self-hosted tool, so no per-user scoping, no
push/email — just "record now, show on next load, let them dismiss".
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timezone

from backend.config import settings

logger = logging.getLogger(__name__)

_NOTICES_PATH = settings.data_dir / "notices.json"
_MAX_NOTICES = 100          # keep the file bounded — drop oldest beyond this
_lock = threading.Lock()


def _load() -> list:
    try:
        if _NOTICES_PATH.exists():
            return json.loads(_NOTICES_PATH.read_text())
    except Exception as exc:
        logger.debug("Notices load failed: %s", exc)
    return []


def _save(notices: list):
    try:
        _NOTICES_PATH.parent.mkdir(parents=True, exist_ok=True)
        _NOTICES_PATH.write_text(json.dumps(notices, indent=2))
    except Exception as exc:
        logger.warning("Notices save failed: %s", exc)


def add_notice(kind: str, title: str, message: str, level: str = "warning",
               dedup_key: str = "") -> dict:
    """Record a durable user notice.

    kind: machine tag (e.g. "deploy_failed"). level: "info"|"warning"|"error".
    dedup_key: if set, an existing UNSEEN notice with the same dedup_key is
    replaced rather than duplicated (avoids stacking identical failures).
    """
    with _lock:
        notices = _load()
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
        # Bound the file — keep the newest _MAX_NOTICES.
        if len(notices) > _MAX_NOTICES:
            notices = notices[-_MAX_NOTICES:]
        _save(notices)
        logger.info("Notice recorded [%s]: %s", kind, title)
        return notice


def list_unseen() -> list:
    """Return notices the user hasn't dismissed yet (newest first)."""
    with _lock:
        return list(reversed([n for n in _load() if not n.get("seen")]))


def dismiss(notice_id: str) -> bool:
    """Mark a single notice as seen. Returns True if it existed."""
    with _lock:
        notices = _load()
        found = False
        for n in notices:
            if n.get("id") == notice_id:
                n["seen"] = True
                found = True
        if found:
            _save(notices)
        return found


def dismiss_all() -> int:
    """Mark every notice as seen. Returns how many were newly dismissed."""
    with _lock:
        notices = _load()
        n_dismissed = 0
        for n in notices:
            if not n.get("seen"):
                n["seen"] = True
                n_dismissed += 1
        if n_dismissed:
            _save(notices)
        return n_dismissed
