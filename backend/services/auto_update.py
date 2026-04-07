"""Auto-update — pulls latest code from GitHub and restarts if needed.

Two modes:
  1. Startup update: runs once before the server starts accepting requests.
     If code was updated, restarts the process so new code loads fresh.

  2. Periodic update: background scheduler checks every 24 hours. If the
     server has been idle (no requests for 60+ seconds), pulls and restarts.
     The frontend is notified before restart so users can re-submit.

Safety:
  - If tracked files have uncommitted changes (developer testing), skips entirely
  - Uses git pull --ff-only first; falls back to reset --hard if diverged
  - Runtime state is in gitignored .user.json files — never lost
  - User data is in data/ directory — never touched by git
  - If anything fails, the server continues with existing code
  - Set ARTSMOKER_AUTO_UPDATE=false to disable both modes
"""

import atexit
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Protected files list — empty since layered config (.user.json pattern)
PROTECTED_FILES = []

# ── Shared state ─────────────────────────────────────────────────────────

_last_request_time: float = 0.0  # Updated by middleware on every request
_restart_pending: bool = False    # Set when a restart is needed after update
_update_status: dict = {          # Readable by frontend via /api/update-status
    "checking": False,
    "last_check": 0,
    "last_update": 0,
    "restarting": False,
    "message": "",
}

# Idle threshold (seconds) — only restart if no requests for this long
IDLE_THRESHOLD = 60

# Check interval (seconds) — how often the background scheduler runs
CHECK_INTERVAL_HOURS = 24


def record_request():
    """Called by middleware on every incoming request to track activity."""
    global _last_request_time
    _last_request_time = time.time()


def is_idle() -> bool:
    """Check if the server has been idle for IDLE_THRESHOLD seconds."""
    if _last_request_time == 0:
        return True  # No requests yet
    return (time.time() - _last_request_time) > IDLE_THRESHOLD


def get_update_status() -> dict:
    """Get current auto-update status for the frontend."""
    return dict(_update_status)


# ── Startup Update ───────────────────────────────────────────────────────

def check_and_update() -> dict:
    """Check for updates and pull if available. Returns status dict.

    Called once during server startup (lifespan handler), BEFORE the
    event loop starts. If code is updated, triggers a process restart
    so the new code loads fresh.
    """
    result = {
        "checked": False,
        "updated": False,
        "from_version": "",
        "to_version": "",
        "commits": 0,
        "skipped_reason": "",
        "error": "",
    }

    try:
        if not _can_update():
            result["skipped_reason"] = _can_update._reason
            return result

        result["checked"] = True
        commits, from_ver, to_ver = _pull_latest()

        if commits == 0:
            result["skipped_reason"] = "Already up to date"
            return result

        result["updated"] = True
        result["from_version"] = from_ver
        result["to_version"] = to_ver
        result["commits"] = commits

        logger.info(
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║  AUTO-UPDATE COMPLETE — RESTARTING                         ║\n"
            "║  %s → %s (%d commit(s))%s║\n"
            "╚══════════════════════════════════════════════════════════════╝",
            from_ver, to_ver, commits,
            " " * max(1, 39 - len(from_ver) - len(to_ver) - len(str(commits))),
        )

        # Send telemetry before restart (won't have another chance)
        try:
            from backend.services.telemetry import init as _telemetry_init, track_auto_update
            _telemetry_init()
            track_auto_update(updated=True, from_version=from_ver, to_version=to_ver, commits=commits)
        except Exception:
            pass

        # Restart — since we're pre-event-loop, os.execv is safe
        _restart_process()
        # _restart_process replaces the process, so this line is never reached

    except Exception as exc:
        result["error"] = str(exc)
        logger.warning("Auto-update check failed (server will start normally): %s", exc)

    return result


# ── Periodic Background Update ───────────────────────────────────────────

_scheduler_thread: threading.Thread | None = None
_scheduler_stop = threading.Event()


def start_periodic_checker():
    """Start the background thread that checks for updates every 24 hours.

    Only triggers an update+restart when the server is idle (no requests
    for 60+ seconds). If not idle, retries every 5 minutes.
    """
    global _scheduler_thread

    if os.environ.get("ARTSMOKER_AUTO_UPDATE", "").lower() in ("false", "0", "no"):
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _scheduler_thread = threading.Thread(target=_periodic_check_loop, daemon=True, name="auto-update-scheduler")
    _scheduler_thread.start()
    logger.debug("Auto-update scheduler started (interval: %dh, idle threshold: %ds)",
                 CHECK_INTERVAL_HOURS, IDLE_THRESHOLD)


def stop_periodic_checker():
    """Stop the background update scheduler."""
    _scheduler_stop.set()


def _periodic_check_loop():
    """Background loop: sleep for CHECK_INTERVAL_HOURS, then check for updates."""
    interval = CHECK_INTERVAL_HOURS * 3600

    while not _scheduler_stop.is_set():
        # Sleep for the check interval (wake up if stop is signaled)
        _scheduler_stop.wait(timeout=interval)
        if _scheduler_stop.is_set():
            break

        # Time to check — but only if idle
        if not _can_update():
            continue

        # Wait for idle (check every 30s, give up after 30 minutes)
        waited = 0
        while not is_idle() and waited < 1800:
            logger.debug("Auto-update: server busy, waiting for idle... (%ds)", waited)
            _scheduler_stop.wait(timeout=30)
            if _scheduler_stop.is_set():
                return
            waited += 30

        if not is_idle():
            logger.info("Auto-update: server still busy after 30 min wait, skipping this cycle")
            continue

        # Server is idle — check for updates
        try:
            _update_status["checking"] = True
            _update_status["message"] = "Checking for updates..."
            logger.info("Auto-update: periodic check (server idle for %ds)",
                        int(time.time() - _last_request_time) if _last_request_time else 0)

            _git("fetch", "origin", "main", "--quiet")
            local_sha = _git("rev-parse", "HEAD").strip()
            remote_sha = _git("rev-parse", "origin/main").strip()

            if local_sha == remote_sha:
                _update_status["checking"] = False
                _update_status["last_check"] = time.time()
                _update_status["message"] = ""
                logger.debug("Auto-update: already up to date")
                continue

            behind = int(_git("rev-list", "--count", f"HEAD..origin/main").strip())
            logger.info("Auto-update: %d commit(s) available, updating...", behind)

            from_ver = _read_version()
            try:
                _git("pull", "--ff-only", "origin", "main")
            except subprocess.CalledProcessError:
                logger.warning("Auto-update: ff-only failed, falling back to hard reset")
                _git("reset", "--hard", "origin/main")
            to_ver = _read_version()

            _update_status["last_update"] = time.time()
            _update_status["message"] = f"Updated {from_ver} → {to_ver} ({behind} commits). Restarting..."
            _update_status["restarting"] = True
            logger.info("Auto-update: %s → %s (%d commits). Restarting server...", from_ver, to_ver, behind)

            # Track telemetry before restart
            try:
                from backend.services.telemetry import track_auto_update
                track_auto_update(updated=True, from_version=from_ver, to_version=to_ver, commits=behind)
            except Exception:
                pass

            # Give frontend 2 seconds to see the "restarting" status
            time.sleep(2)

            # Trigger graceful shutdown → atexit handler will re-exec
            _schedule_restart()

        except subprocess.CalledProcessError as e:
            _update_status["checking"] = False
            _update_status["message"] = ""
            logger.warning("Auto-update: pull failed: %s", e.stderr or e.stdout)
        except Exception as exc:
            _update_status["checking"] = False
            _update_status["message"] = ""
            logger.warning("Auto-update: periodic check failed: %s", exc)


# ── Core helpers ─────────────────────────────────────────────────────────

def _can_update() -> bool:
    """Check if auto-update is possible (git repo, main branch, no local dev work).

    Skips update if there are uncommitted changes to tracked files — protects
    developers who are testing local code changes before committing.
    Gitignored files (.user.json, data/) are NOT checked since they're
    never touched by git operations.
    """
    _can_update._reason = ""

    if not (PROJECT_ROOT / ".git").is_dir():
        _can_update._reason = "Not a git repository"
        return False

    if os.environ.get("ARTSMOKER_AUTO_UPDATE", "").lower() in ("false", "0", "no"):
        _can_update._reason = "Disabled (ARTSMOKER_AUTO_UPDATE=false)"
        return False

    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != "main":
        _can_update._reason = f"Not on main branch (on '{branch}')"
        return False

    # Check for uncommitted changes to TRACKED files (protects developer work).
    # git status --porcelain shows only tracked-file changes (not gitignored).
    dirty = _git("status", "--porcelain").strip()
    if dirty:
        dirty_count = len([l for l in dirty.splitlines() if l.strip()])
        _can_update._reason = f"Local changes detected ({dirty_count} files) — skipping to protect your work"
        return False

    return True

_can_update._reason = ""


def _pull_latest() -> tuple[int, str, str]:
    """Fetch and pull latest code. Returns (commit_count, from_version, to_version).
    Returns (0, "", "") if already up to date.

    Strategy:
    - _can_update() already confirmed no uncommitted changes to tracked files
    - Runtime state is in gitignored .user.json files (never touched by git)
    - So git pull --ff-only SHOULD always succeed (clean tree, no divergence)
    - If it fails (unexpected state), falls back to git reset --hard as last resort
    """
    _git("fetch", "origin", "main", "--quiet")

    local_sha = _git("rev-parse", "HEAD").strip()
    remote_sha = _git("rev-parse", "origin/main").strip()

    if local_sha == remote_sha:
        return 0, "", ""

    behind = int(_git("rev-list", "--count", f"HEAD..origin/main").strip())
    from_ver = _read_version()

    try:
        # Preferred: fast-forward pull (safe, preserves local commits if any)
        _git("pull", "--ff-only", "origin", "main")
    except subprocess.CalledProcessError:
        # Fallback: hard reset (for non-technical users where local branch diverged)
        logger.warning("Auto-update: ff-only failed, falling back to hard reset")
        _git("reset", "--hard", "origin/main")

    to_ver = _read_version()
    return behind, from_ver, to_ver


def _restart_process():
    """Replace the current process with a fresh one (pre-event-loop only).

    Uses os.execv which replaces the process image — all modules reload fresh.
    Only safe to call BEFORE the event loop starts (no open connections/sockets).
    """
    logger.info("Restarting process with updated code...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _schedule_restart():
    """Trigger a graceful shutdown that will re-exec the process.

    For use when the event loop is running (periodic update). The atexit
    handler performs the actual os.execv after uvicorn finishes cleanup.
    """
    global _restart_pending
    _restart_pending = True
    # SIGINT triggers uvicorn's graceful shutdown
    os.kill(os.getpid(), signal.SIGINT)


def _atexit_restart():
    """atexit handler — re-exec the process if a restart was scheduled."""
    if _restart_pending:
        logger.info("Performing scheduled restart with updated code...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

# Register the atexit handler (runs after uvicorn's shutdown is complete)
atexit.register(_atexit_restart)


def _git(*args) -> str:
    """Run a git command in the project root. Returns stdout."""
    cmd = ["git", "-C", str(PROJECT_ROOT)] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)
    return r.stdout


def _read_version() -> str:
    """Read APP_VERSION from config.py."""
    config_path = PROJECT_ROOT / "backend" / "config.py"
    try:
        for line in config_path.read_text().splitlines():
            if line.startswith("APP_VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"
