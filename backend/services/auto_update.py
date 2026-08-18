"""Auto-update — version-gated code updates from GitHub.

Two modes:
  1. Startup update: runs once before the server starts accepting requests.
     If a newer version exists on origin/main, pulls and restarts.

  2. Periodic update: background scheduler checks every 24 hours. If the
     server has been idle (no requests for 60+ seconds), pulls and restarts.
     The frontend is notified before restart so users can re-submit.

Version gating:
  - Only updates if remote APP_VERSION in config.py is NEWER than local
  - This prevents pulling incomplete/untested code — only version bumps trigger updates
  - Developers bump APP_VERSION when a release is ready

Safety:
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


def is_dev_mode() -> bool:
    """Whether this is a development box (enables hot-reload + keep-warm).

    Resolves from two sources, either of which enables it:
      1. config Settings.dev_mode — loaded from the gitignored .env file
         (ARTSMOKER_DEV_MODE), so it persists across server restarts.
      2. The raw ARTSMOKER_DEV_MODE environment variable — an inline override
         (e.g. `ARTSMOKER_DEV_MODE=true uvicorn ...`) for one-off sessions.
    """
    if os.environ.get("ARTSMOKER_DEV_MODE", "").lower() in ("true", "1", "yes"):
        return True
    try:
        from backend.config import settings
        return bool(getattr(settings, "dev_mode", False))
    except Exception:
        return False


# ── Startup Update ───────────────────────────────────────────────────────

def check_and_update() -> dict:
    """Check for updates and pull if available. Returns status dict.

    Called once during server startup (lifespan handler), BEFORE the
    event loop starts. Only pulls if the remote APP_VERSION is newer
    than the local version — prevents pulling incomplete code.
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
        local_ver = _read_version()

        # Fetch remote and check version BEFORE pulling
        _git("fetch", "origin", "main", "--quiet")
        remote_ver = _read_remote_version()

        if not remote_ver or remote_ver == "unknown":
            result["skipped_reason"] = "Could not read remote version"
            return result

        if not _is_newer_version(remote_ver, local_ver):
            result["skipped_reason"] = f"Already up to date (v{local_ver})"
            return result

        # Remote version is newer — pull the update
        logger.info("Auto-update: newer version available: %s → %s", local_ver, remote_ver)
        commits = _do_pull()

        if commits == 0:
            result["skipped_reason"] = f"Already up to date (v{local_ver})"
            return result

        result["updated"] = True
        result["from_version"] = local_ver
        result["to_version"] = remote_ver
        result["commits"] = commits

        logger.info(
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║  AUTO-UPDATE COMPLETE — RESTARTING                         ║\n"
            "║  %s → %s (%d commit(s))%s║\n"
            "╚══════════════════════════════════════════════════════════════╝",
            local_ver, remote_ver, commits,
            " " * max(1, 39 - len(local_ver) - len(remote_ver) - len(str(commits))),
        )

        # Send telemetry before restart (won't have another chance)
        try:
            from backend.services.telemetry import init as _telemetry_init, track_auto_update
            _telemetry_init()
            track_auto_update(updated=True, from_version=local_ver, to_version=remote_ver, commits=commits)
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
    for 60+ seconds) AND a newer version is available on origin/main.
    """
    global _scheduler_thread

    if os.environ.get("ARTSMOKER_AUTO_UPDATE", "").lower() in ("false", "0", "no"):
        return

    if is_dev_mode():
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

        # Time to check — but only if conditions are met
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

        # Server is idle — check for version update
        try:
            _update_status["checking"] = True
            _update_status["message"] = "Checking for updates..."

            local_ver = _read_version()
            _git("fetch", "origin", "main", "--quiet")
            remote_ver = _read_remote_version()

            if not remote_ver or not _is_newer_version(remote_ver, local_ver):
                _update_status["checking"] = False
                _update_status["last_check"] = time.time()
                _update_status["message"] = ""
                logger.debug("Auto-update: no newer version (local=%s, remote=%s)", local_ver, remote_ver)
                continue

            logger.info("Auto-update: newer version %s → %s, updating...", local_ver, remote_ver)
            commits = _do_pull()

            _update_status["last_update"] = time.time()
            _update_status["message"] = f"Updated {local_ver} → {remote_ver}. Restarting..."
            _update_status["restarting"] = True
            logger.info("Auto-update: %s → %s (%d commits). Restarting server...", local_ver, remote_ver, commits)

            # Track telemetry before restart
            try:
                from backend.services.telemetry import track_auto_update
                track_auto_update(updated=True, from_version=local_ver, to_version=remote_ver, commits=commits)
            except Exception:
                pass

            # Give frontend 2 seconds to see the "restarting" status
            time.sleep(2)  # nosemgrep --deliberate pre-restart delay

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
    """Check if auto-update is possible."""
    _can_update._reason = ""

    if not (PROJECT_ROOT / ".git").is_dir():
        _can_update._reason = "Not a git repository"
        return False

    if os.environ.get("ARTSMOKER_AUTO_UPDATE", "").lower() in ("false", "0", "no"):
        _can_update._reason = "Disabled (ARTSMOKER_AUTO_UPDATE=false)"
        return False

    if is_dev_mode():
        _can_update._reason = "Skipped"
        return False

    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != "main":
        _can_update._reason = f"Not on main branch (on '{branch}')"
        return False

    return True

_can_update._reason = ""


def _is_newer_version(remote: str, local: str) -> bool:
    """Check if the remote version string is newer than the local one.

    Version format: "1.6-20260408_01" (major.minor-YYYYMMDD_seq)
    Comparison: string comparison works because the date+seq format is
    lexicographically ordered (newer dates sort after older ones).
    """
    if not remote or not local or remote == "unknown" or local == "unknown":
        return False
    return remote > local


def _read_remote_version() -> str:
    """Read APP_VERSION from the remote origin/main config.py (without pulling).

    Uses git show to read the file content from the fetched remote branch.
    """
    try:
        content = _git("show", "origin/main:backend/config.py")
        for line in content.splitlines():
            if line.startswith("APP_VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def _do_pull() -> int:
    """Pull latest code from origin/main. Returns commit count.

    For non-dev machines: uses git reset --hard (always succeeds).
    Runtime state is in gitignored .user.json files — safe to overwrite
    all tracked files.
    """
    local_sha = _git("rev-parse", "HEAD").strip()
    remote_sha = _git("rev-parse", "origin/main").strip()

    if local_sha == remote_sha:
        return 0

    behind = int(_git("rev-list", "--count", f"HEAD..origin/main").strip())

    # Force reset to origin/main — safe because:
    # (a) _can_update() blocks dev mode machines
    # (b) runtime state is in .user.json (gitignored)
    # (c) user data is in data/ (gitignored)
    _git("reset", "--hard", "origin/main")

    return behind


def _restart_process():
    """Replace the current process with a fresh one (pre-event-loop only).

    Uses os.execv which replaces the process image — all modules reload fresh.
    Only safe to call BEFORE the event loop starts (no open connections/sockets).
    """
    logger.info("Restarting process with updated code...")
    # Re-exec THIS interpreter with its own argv — no external/untrusted input.
    os.execv(sys.executable, [sys.executable] + sys.argv)  # nosemgrep


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
        # Re-exec THIS interpreter with its own argv — no external/untrusted input.
        os.execv(sys.executable, [sys.executable] + sys.argv)  # nosemgrep

# Register the atexit handler (runs after uvicorn's shutdown is complete)
atexit.register(_atexit_restart)


def _git(*args) -> str:
    """Run a git command in the project root. Returns stdout."""
    cmd = ["git", "-C", str(PROJECT_ROOT)] + list(args)
    # List-form (no shell), fixed "git" binary; args come only from internal
    # callers (hardcoded subcommands), never from request/user input.
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # nosemgrep
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)
    return r.stdout


def _read_version() -> str:
    """Read APP_VERSION from the local config.py."""
    config_path = PROJECT_ROOT / "backend" / "config.py"
    try:
        for line in config_path.read_text().splitlines():
            if line.startswith("APP_VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"
