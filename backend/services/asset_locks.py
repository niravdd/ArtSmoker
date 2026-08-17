"""Per-asset write lock — serialize metadata.json read-modify-writes.

Every writer of a gallery asset's metadata.json (the sync edit save in
/api/generate/edit, the async edit completion in async_jobs, the 3D finalize /
set-default / source-review writers, and version delete / commit-source) holds
`asset_write_lock(asset_id)` around its whole read-modify-write. Without it, two
writers can compute the same next_version and clobber each other's records.

Cross-process: the app runs multi-worker in production (gunicorn — see README),
so the lock combines an in-process threading.Lock with a POSIX fcntl.flock on a
per-asset lock file (data/.locks/asset_<id>.lock). That serializes both threads
in one worker AND separate worker processes on the same host. See
services/safe_write._WriteLock. Paired with atomic_write_text in the store, a
concurrent read never sees a partial file and no write is lost.
"""

from backend.services.safe_write import _WriteLock, _LOCK_DIR


def _safe_key(asset_id: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in asset_id)


def asset_write_lock(asset_id: str) -> _WriteLock:
    """Return the process/thread-safe write lock for a gallery asset. Usable as
    a context manager (`with asset_write_lock(id):`) or via acquire()/release()."""
    key = _safe_key(asset_id)
    return _WriteLock(f"asset:{key}", _LOCK_DIR / f"asset_{key}.lock")
