"""Per-asset write locks — serialize version saves on the same gallery asset.

The sync edit save (/api/generate/edit) and the async edit completion
(async_jobs._update_gallery_on_edit_complete) both read-modify-write the same
metadata.json (versions[] append + current_version + archive of asset.png).
Unserialized, two completions landing within the same window can compute the
same next_version — one version record silently clobbers the other and the
archived PNGs disagree with the records.

Process-local by design: both writers live in this FastAPI process (the async
poller is a thread, not a separate process), so a threading.Lock per asset_id
is sufficient. Locks are created on demand and kept for the process lifetime —
they're tiny, and dropping them early would reopen the race.
"""

import threading

_locks: dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


def asset_write_lock(asset_id: str) -> threading.Lock:
    """Return the (shared, process-wide) write lock for a gallery asset."""
    with _registry_lock:
        lock = _locks.get(asset_id)
        if lock is None:
            lock = _locks[asset_id] = threading.Lock()
        return lock
