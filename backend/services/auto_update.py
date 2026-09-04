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

import hashlib
import hmac
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
_restart_pending: bool = False    # An update was applied; a restart is needed to activate it
_update_status: dict = {          # Readable by frontend via /api/update-status
    "checking": False,
    "last_check": 0,
    "last_update": 0,
    "restarting": False,       # a restart is actively in progress
    "restart_pending": False,  # update staged on disk; waiting for a (possibly manual) restart
    "staged_version": "",      # the version staged on disk awaiting restart
    "restart_mode": "",        # how the last restart was dispatched (supervised/gunicorn/…)
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


# ── Restart control (supervisor-aware, cross-OS) ─────────────────────────
# The supervisor (`python -m backend.main`) runs the app in a child process and
# respawns it when the child exits with RESTART_EXIT_CODE. These primitives let
# any code (auto-update, the /api/restart-server endpoint) ask the running
# server to stop gracefully so it can be restarted with fresh code — WITHOUT
# os.execv / os.kill, which are unreliable on Windows and under process managers.

RESTART_EXIT_CODE = 42  # child exits with this to ask the supervisor to respawn

_uvicorn_server = None            # set by the child runner when supervised
_restart_requested = threading.Event()


def is_supervised() -> bool:
    """True when this process was launched by our supervisor (child role).

    The supervisor sets ARTSMOKER_SUPERVISED in the child's environment; a bare
    `uvicorn`/`gunicorn` launch never has it.
    """
    return bool(os.environ.get("ARTSMOKER_SUPERVISED"))


def register_server(server) -> None:
    """Child runner registers its live uvicorn Server so a restart can stop it."""
    global _uvicorn_server
    _uvicorn_server = server


def request_restart() -> bool:
    """Ask the running (supervised) server to stop for a fresh-code restart.

    Sets the restart flag and trips uvicorn's graceful-shutdown switch. When the
    child's server.run() returns, the child exits with RESTART_EXIT_CODE and the
    supervisor respawns it. Returns True if an in-process supervised stop was
    triggered; False when this process is not our supervised child (the caller
    then falls back to gunicorn-reload / manager-exit / manual per topology).
    """
    _restart_requested.set()
    srv = _uvicorn_server
    if srv is not None:
        srv.should_exit = True  # uvicorn graceful shutdown → server.run() returns
        return True
    return False


def restart_requested() -> bool:
    """Whether a restart was requested during this process's lifetime."""
    return _restart_requested.is_set()


def _gunicorn_master_pid():
    """Return the gunicorn master PID if we are a gunicorn worker, else None.

    Detection: SIGHUP exists (POSIX — gunicorn has no Windows support), gunicorn
    is imported in the process (true for the arbiter and its forked workers, not
    for a bare `uvicorn` CLI launch), and our parent is that arbiter. HUP-ing the
    master triggers a graceful worker reload onto fresh code with no master
    downtime — the right restart for the documented multi-worker deployment.
    """
    if not hasattr(signal, "SIGHUP"):
        return None
    if "gunicorn" not in sys.modules:
        return None
    ppid = os.getppid()
    return ppid if ppid and ppid > 1 else None


def _mark_restarting(mode: str, message: str) -> None:
    _update_status["restarting"] = True
    _update_status["restart_pending"] = True
    _update_status["restart_mode"] = mode
    _update_status["message"] = message


def mark_restart_pending(staged_version: str = "", message: str = "") -> None:
    """Flag that an update is staged on disk and a restart is needed to activate.

    Used for the unmanaged/HOLD case where we cannot safely self-restart: the
    server keeps serving the OLD code but advertises the pending restart through
    /api/update-status (remotely reachable) so a headless operator can act.
    """
    global _restart_pending
    _restart_pending = True
    _update_status["restart_pending"] = True
    _update_status["restarting"] = False
    if staged_version:
        _update_status["staged_version"] = staged_version
    _update_status["message"] = message or (
        f"Update to v{staged_version} staged — restart the server to activate it."
        if staged_version else "Update staged — restart the server to activate it."
    )


def perform_restart(explicit: bool = False) -> dict:
    """Restart the running server via the best mechanism for how it was launched.

    Priority:
      1. Supervised child (`python -m backend.main`) → request_restart(): uvicorn
         graceful shutdown, child exits RESTART_EXIT_CODE, supervisor respawns on
         fresh code. Cross-OS, self-healing.
      2. Gunicorn worker (POSIX) → SIGHUP the master: graceful worker reload, no
         master downtime.
      3. Unmanaged bare process → cannot guarantee a clean restart:
           • explicit=True (operator asked via /api/restart-server): honor intent
             — SIGTERM ourselves for a graceful shutdown (a process manager
             relaunches us; if none, the operator does). On a platform without
             SIGTERM (Windows bare launch) report manual-required instead of a
             hard kill.
           • explicit=False (background auto-update): DO NOT exit an unmanaged
             process — stage it (mark_restart_pending) and surface it, so nobody
             is left with a silently-dead headless box.

    Returns {"mode", "restarting", "message"}.
    """
    if is_supervised():
        request_restart()
        msg = "Restarting to activate the update…"
        _mark_restarting("supervised", msg)
        logger.info("Auto-update: supervised restart requested — child will respawn on fresh code.")
        return {"mode": "supervised", "restarting": True, "message": msg}

    master = _gunicorn_master_pid()
    if master is not None:
        try:
            os.kill(master, signal.SIGHUP)  # graceful worker reload onto fresh code
            msg = "Reloading workers to activate the update…"
            _mark_restarting("gunicorn", msg)
            logger.info("Auto-update: signaled gunicorn master (pid %d) to reload workers.", master)
            return {"mode": "gunicorn", "restarting": True, "message": msg}
        except Exception as exc:
            logger.warning("Auto-update: gunicorn reload signal failed (%s) — falling back.", exc)

    # Unmanaged bare process (e.g. plain `uvicorn`, nohup).
    if explicit and hasattr(signal, "SIGTERM"):
        msg = ("Stopping to restart — a process manager will relaunch it; "
               "if there is none, start it again manually.")
        _mark_restarting("unmanaged-exit", msg)
        logger.info("Auto-update: operator requested restart on an unmanaged process — "
                    "sending SIGTERM for a graceful shutdown.")

        def _self_terminate():
            # Brief delay so the HTTP response for /api/restart-server flushes first.
            time.sleep(1.0)  # nosemgrep --deliberate: let the response flush before shutdown
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
                pass

        threading.Thread(target=_self_terminate, daemon=True, name="restart-self-term").start()
        return {"mode": "unmanaged-exit", "restarting": True, "message": msg}

    # No safe automatic restart available — stage it and ask for a manual one.
    mark_restart_pending(
        message=("Update staged. This process cannot restart itself automatically — "
                 "restart it manually, or relaunch via `python -m backend.main` for "
                 "automatic restarts."),
    )
    logger.warning("Auto-update: applied update but cannot self-restart (unmanaged, non-supervised). "
                   "Holding on current code; restart required. Status at /api/update-status.")
    return {"mode": "manual", "restarting": False, "message": _update_status["message"]}


def get_pending_work() -> list:
    """Best-effort list of reasons the server is 'busy' (for restart quiescence).

    Empty list ⇒ quiescent. Async image/3D jobs are intentionally NOT hard
    blockers — they are persisted to S3 and resumed after a restart by design —
    but they are reported so an operator can choose to wait. Never raises.
    """
    reasons = []
    try:
        from backend.app import _server_state
        if _server_state.get("sync_in_progress"):
            reasons.append("a model-registry Sync is running")
    except Exception:
        pass
    try:
        from backend.services.async_jobs import get_pending_count
        n = get_pending_count()
        if n:
            reasons.append(f"{n} image job(s) in progress (will resume after restart)")
    except Exception:
        pass
    try:
        from backend.routers import generate_3d
        n3d = sum(1 for j in getattr(generate_3d, "_3d_jobs", {}).values()
                  if j.get("status") not in ("complete", "failed"))
        if n3d:
            reasons.append(f"{n3d} 3D job(s) in progress (will resume after restart)")
    except Exception:
        pass
    return reasons


# A single maintainer workstation must skip auto-update so that a
# `git reset --hard` restart never discards in-flight uncommitted work (it also
# enables hot-reload + keep-warm for dev iteration). That box carries an opaque
# token in its gitignored .env; only the token's hash lives here, matched in
# constant time. Every normal install lacks the token → is_dev_mode() is False
# → auto-update runs. This digest is a one-way hash, not a secret.
_MAINTAINER_INSTANCE_DIGEST = "3641fbb31385a4ccd86b731d1cd7a88d24dd60a1776519b0c92683871e73bf83"  # gitleaks:allow -- SHA-256 of a token; not reversible, safe to commit


def is_dev_mode() -> bool:
    """Whether this is the maintainer workstation (hot-reload + keep-warm,
    and auto-update is skipped here only).

    The only signal is the opaque per-instance token in the gitignored .env
    (config Settings.instance_key). We compare its hash against an embedded
    digest — the token itself never appears in the source. Absent/mismatched
    token → False, so all normal installs auto-update. Fail-safe: any error
    resolves to False (auto-update proceeds).
    """
    try:
        from backend.config import settings
        token = (getattr(settings, "instance_key", "") or "").strip()
        if not token:
            return False
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, _MAINTAINER_INSTANCE_DIGEST)
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
        result["from_version"] = local_ver

        # Fetch remote and check version BEFORE pulling
        _git("fetch", "origin", "main", "--quiet")
        remote_ver = _read_remote_version()
        # Always record what we saw — the startup version_check event reads these.
        result["to_version"] = remote_ver if remote_ver and remote_ver != "unknown" else ""

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

            # Every periodic check emits a version_check event (updated or not) —
            # the daily heartbeat that a long-running server IS checking.
            _newer = bool(remote_ver) and _is_newer_version(remote_ver, local_ver)
            try:
                from backend.services.telemetry import track_version_check
                track_version_check(source="periodic", current=local_ver,
                                    latest=remote_ver or "", update_available=_newer)
            except Exception:
                pass

            if not _newer:
                _update_status["checking"] = False
                _update_status["last_check"] = time.time()
                _update_status["message"] = ""
                logger.debug("Auto-update: no newer version (local=%s, remote=%s)", local_ver, remote_ver)
                continue

            logger.info("Auto-update: newer version %s → %s, updating...", local_ver, remote_ver)
            commits = _do_pull()

            _update_status["last_update"] = time.time()
            _update_status["staged_version"] = remote_ver
            _update_status["message"] = f"Updated {local_ver} → {remote_ver}. Restarting..."
            _update_status["restart_pending"] = True
            logger.info("Auto-update: %s → %s (%d commits). Restarting server...", local_ver, remote_ver, commits)

            # Track telemetry before restart
            try:
                from backend.services.telemetry import track_auto_update
                track_auto_update(updated=True, from_version=local_ver, to_version=remote_ver, commits=commits)
            except Exception:
                pass

            # Give frontend 2 seconds to see the "restarting" status
            time.sleep(2)  # nosemgrep --deliberate pre-restart delay

            # Restart via the best mechanism for how this server was launched
            # (supervised respawn / gunicorn reload / unmanaged HOLD). Background
            # update ⇒ explicit=False, so an unmanaged process is never killed
            # from under the operator — it holds and advertises restart_pending.
            outcome = perform_restart(explicit=False)
            logger.info("Auto-update: applied %s → %s; restart mode=%s (%s)",
                        local_ver, remote_ver, outcome["mode"], outcome["message"])

        except subprocess.CalledProcessError as e:
            _update_status["checking"] = False
            _update_status["message"] = ""
            logger.warning("Auto-update: pull failed: %s", e.stderr or e.stdout)
            try:
                from backend.services.telemetry import track_version_check
                track_version_check(source="periodic", error=str(e.stderr or e.stdout or e))
            except Exception:
                pass
        except Exception as exc:
            _update_status["checking"] = False
            _update_status["message"] = ""
            logger.warning("Auto-update: periodic check failed: %s", exc)
            try:
                from backend.services.telemetry import track_version_check
                track_version_check(source="periodic", error=str(exc))
            except Exception:
                pass


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
    """Restart right after applying a STARTUP update (before the app serves).

    This runs early in the lifespan handler — the socket may be bound but no
    requests are served yet and no pollers are running, so an abrupt exit is
    safe (nothing to drain).

      • Supervised child → exit with RESTART_EXIT_CODE; the supervisor respawns
        us on fresh code. Cross-OS clean (no os.execv).
      • Otherwise → re-exec in place with os.execv (long-standing bare-launch
        behavior). For a bare Windows launch, prefer `python -m backend.main`
        (supervised) for reliable restarts.
    """
    if is_supervised():
        logger.info("Auto-update: restarting (supervised) to load updated code...")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(RESTART_EXIT_CODE)
    logger.info("Auto-update: restarting process with updated code...")
    # Re-exec THIS interpreter with its own argv — no external/untrusted input.
    os.execv(sys.executable, [sys.executable] + sys.argv)  # nosemgrep


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
