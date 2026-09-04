"""Thread- and process-safe file writes for the app's mutable JSON state.

Two primitives, used for every server write to per-asset metadata.json and the
model/prompt registries:

1. atomic_write_text() — write to a temp file in the SAME directory, fsync, then
   os.replace() onto the target. os.replace is atomic on POSIX (and Windows), so
   a reader ALWAYS sees either the complete old file or the complete new one —
   never a half-written/corrupt file — and a crash mid-write leaves the previous
   file intact. This is the primary defence against corruption on a shared host.

2. named_write_lock() / asset_write_lock() — a lock that serializes
   a read-modify-write across BOTH threads in one worker (threading.Lock) AND
   processes on the same host (an OS file lock on a lock file). So concurrent
   collaborators — whether served by one multi-threaded uvicorn worker or several
   worker processes on a shared EC2 box — can't lost-update the same file.

The cross-process file lock uses fcntl.flock on POSIX (Linux/macOS — our dev + EC2
targets) and msvcrt.locking on Windows, chosen once at import. On an exotic
platform with neither, the lock degrades to in-process only (still correct for
single-worker) and writes stay atomic regardless.
"""

import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Cross-process advisory lock backend, chosen once at import: fcntl on POSIX,
# msvcrt on Windows. Both expose the same _os_lock/_os_unlock — a blocking
# exclusive lock, and its release, over one byte of the lock file. _HAS_OSLOCK is
# False only on a platform with neither backend → the lock degrades to in-process
# only (see _WriteLock.acquire).
try:
    import fcntl  # POSIX advisory file locks (Linux/macOS)

    def _os_lock(fh):
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)

    def _os_unlock(fh):
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    _HAS_OSLOCK = True
except ImportError:  # pragma: no cover - non-POSIX (Windows)
    try:
        import msvcrt  # Windows mandatory byte-range locks

        def _os_lock(fh):
            # msvcrt locks a byte range at the current file position; we always
            # use one byte at offset 0. LK_LOCK retries internally for ~10s then
            # raises — loop so we block indefinitely, matching flock's LOCK_EX.
            fh.seek(0)
            while True:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                    return
                except OSError:
                    time.sleep(0.2)

        def _os_unlock(fh):
            # Must release the exact range that was locked (offset 0, one byte).
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)

        _HAS_OSLOCK = True
    except ImportError:  # pragma: no cover - neither backend available
        _HAS_OSLOCK = False

# Warn ONCE per process if cross-process locking degrades — a persistent
# environmental condition, so repeating it on every acquire would just spam.
_flock_degraded_warned = False


def atomic_write_text(path: "Path | str", text: str, encoding: str = "utf-8") -> None:
    """Atomically write `text` to `path` (temp-in-same-dir + fsync + os.replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Same directory so os.replace is a same-filesystem atomic rename.
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_bytes(path: "Path | str", data: bytes) -> None:
    """Atomically write `data` to `path` (temp-in-same-dir + fsync + os.replace).

    The bytes-mode twin of atomic_write_text — for content that must land
    byte-for-byte (e.g. images/fonts written by the auto-update file installer).
    Same atomicity guarantee: a reader sees the whole old or whole new file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path: "Path | str", data, *, indent: int = 2,
                      ensure_ascii: bool = False, default=str) -> None:
    """atomic_write_text of json.dumps(data, …)."""
    atomic_write_text(path, json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, default=default))


# ── Locks ──────────────────────────────────────────────────────────────────

_LOCK_DIR = Path(__file__).resolve().parent.parent.parent / "data" / ".locks"
_tlocks: dict[str, threading.RLock] = {}
_tlocks_guard = threading.Lock()

# Per-key flock recursion state: {key: {"depth": int, "fh": file}}. Guarded by
# the per-key RLock (only its owning thread ever touches its entry) plus this
# guard for the dict itself. Enables reentrancy: the SAME thread re-acquiring a
# key it already holds just bumps the depth instead of opening a second fd and
# self-deadlocking on flock.
_flock_state: dict[str, dict] = {}
_flock_guard = threading.Lock()


def _tlock_for(key: str) -> "threading.RLock":
    with _tlocks_guard:
        lk = _tlocks.get(key)
        if lk is None:
            lk = _tlocks[key] = threading.RLock()
        return lk


class _WriteLock:
    """Combined in-process (RLock) + cross-process (OS file lock) lock.

    Held around a read-modify-write so neither a sibling thread nor another
    worker process can interleave. Supports both `with lock:` and the explicit
    acquire()/release() protocol (some call sites use each).

    REENTRANT: a thread may acquire the same key it already holds (e.g. a
    registry_transaction whose body calls another locked writer) without
    deadlocking. The in-process RLock permits the same-thread re-acquire; the
    cross-process flock is opened once and reference-counted by depth, released
    only when the outermost acquire releases. Distinct threads and distinct
    processes still block each other — full mutual exclusion is preserved.
    """

    def __init__(self, key: str, lock_path: Path):
        self._key = key
        self._tlock = _tlock_for(key)
        self._lock_path = lock_path

    def acquire(self):
        # RLock first: for a re-entrant acquire this returns immediately and
        # guarantees the flock state below is only ever touched by its owner.
        self._tlock.acquire()
        if _HAS_OSLOCK:
            with _flock_guard:
                st = _flock_state.get(self._key)
                if st is not None:
                    # Same thread already holds the cross-process lock — bump.
                    st["depth"] += 1
                    return self
                try:
                    self._lock_path.parent.mkdir(parents=True, exist_ok=True)
                    # Deliberately long-lived: the handle must stay open while the
                    # OS lock is held; it's closed in release() and on the failure
                    # path below — not a leak.
                    fh = open(self._lock_path, "a+")  # nosemgrep
                    _os_lock(fh)
                    _flock_state[self._key] = {"depth": 1, "fh": fh}
                except Exception as exc:
                    # flock unavailable/failed → degrade to in-process lock only.
                    # Loud one-time warning: on a multi-worker host this means
                    # writes from OTHER worker processes are NO LONGER serialized
                    # (in-worker threads still are). Critical for troubleshooting
                    # lost-update reports on a shared box.
                    global _flock_degraded_warned
                    if not _flock_degraded_warned:
                        _flock_degraded_warned = True
                        logger.warning(
                            "Cross-process file lock unavailable (%s at %s) — degrading to "
                            "IN-PROCESS locking only. Concurrent writes from separate worker "
                            "processes are NOT serialized; safe only for a single-worker deploy. "
                            "Cause: %r", self._key, self._lock_path, exc)
                    try:
                        fh.close()  # type: ignore[has-type]
                    except (OSError, NameError, UnboundLocalError):
                        pass
        return self

    def release(self):
        if _HAS_OSLOCK:
            with _flock_guard:
                st = _flock_state.get(self._key)
                if st is not None:
                    st["depth"] -= 1
                    if st["depth"] <= 0:
                        try:
                            _os_unlock(st["fh"])
                        except Exception:
                            pass
                        try:
                            st["fh"].close()
                        except OSError:
                            pass
                        del _flock_state[self._key]
        self._tlock.release()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()
        return False


def named_write_lock(name: str) -> _WriteLock:
    """A process/thread-safe write lock keyed by an arbitrary name (e.g. the
    model or prompt registry). Lock file lives in data/.locks/."""
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in name)
    return _WriteLock(f"named:{name}", _LOCK_DIR / f"{safe}.lock")
