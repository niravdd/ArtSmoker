"""ArtSmoker entry point — stable import target + cross-platform supervisor.

Two roles, selected by how this module is used:

  • Imported (``uvicorn backend.main:app`` / ``gunicorn backend.main:app``, or
    the child's ``from backend.main import _server_state``): it lazily
    re-exports the ASGI ``app`` and shared ``_server_state`` from
    :mod:`backend.app`. Every existing launch command keeps working verbatim.

  • Run directly (``python -m backend.main``): it starts the supervisor that
    runs the app in a child process and can restart that child in place for
    auto-updates — reliably and on every OS, including Windows.

The re-export is LAZY on purpose: the supervisor process must not import the
whole FastAPI app (routers, AWS clients, logging banners) just to spawn a
child. Only genuine attribute access — by uvicorn/gunicorn resolving
``backend.main:app``, or the child's lazy ``from backend.main import
_server_state`` — loads :mod:`backend.app`.

Supervisor topology
-------------------
``python -m backend.main`` with ARTSMOKER_SUPERVISED unset → the PARENT
(supervisor): it spawns ``python -m backend.main`` again with a per-launch
ARTSMOKER_SUPERVISED nonce in the child's environment, waits, and respawns the
child whenever it exits with RESTART_EXIT_CODE (an auto-update / restart
request). Any other exit is propagated and the supervisor stops. The same nonce
is how the child knows it is supervised (auto_update.is_supervised()).

The child runs uvicorn programmatically against ``backend.app:app`` (not
``backend.main:app`` — avoids re-importing this launcher) so a restart is just
uvicorn's graceful shutdown returning from ``server.run()`` followed by
``sys.exit(RESTART_EXIT_CODE)``. No os.execv, no os.kill — Windows-safe.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def __getattr__(name):
    # PEP 562 module-level attribute hook. `app` and `_server_state` are the only
    # names other code reaches through backend.main; both live in backend.app.
    # `_server_state` is a dict mutated in place (never reassigned), so this
    # re-export and backend.app share the one object — state stays consistent.
    if name in ("app", "_server_state"):
        from backend import app as _app_module
        return getattr(_app_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ── Supervisor + child runner (python -m backend.main) ─────────────────────

def _parse_host_port(argv):
    """Parse --host/--port (env-overridable) for the supervised launch.

    Defaults match uvicorn's own (127.0.0.1:8000); ARTSMOKER_HOST / ARTSMOKER_PORT
    provide env fallbacks. Unknown args are ignored so the launcher stays
    forgiving. --help prints usage and exits (handled by argparse).
    """
    import argparse
    import os

    parser = argparse.ArgumentParser(
        prog="python -m backend.main",
        description="Run ArtSmoker under the cross-platform auto-restart supervisor.",
    )
    parser.add_argument("--host", default=os.environ.get("ARTSMOKER_HOST", "127.0.0.1"),
                        help="Bind address (default: 127.0.0.1, or $ARTSMOKER_HOST)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("ARTSMOKER_PORT", "8000")),
                        help="Bind port (default: 8000, or $ARTSMOKER_PORT)")
    args, _unknown = parser.parse_known_args(argv)
    return args.host, args.port


def _setup_supervisor_logging():
    """Minimal logging for the SUPERVISOR process (which never imports the app).

    Writes to stderr (captured by systemd/journal, Docker, or nohup) AND — for
    headless boxes with no console — appends to the same session log file the
    child uses, so restart/rollback events are recoverable there too. Both are
    best-effort and never block startup.
    """
    import logging

    log = logging.getLogger("artsmoker.supervisor")
    log.setLevel(logging.INFO)
    log.propagate = False
    if log.handlers:
        return log  # already set up (defensive; supervisor is one process)

    fmt = logging.Formatter("%(asctime)s  SUPERVISOR  %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(sh)

    try:
        from backend.config import settings  # cheap: config only, not the app
        if getattr(settings, "log_to_file", False):
            p = Path(settings.log_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(p, mode="a", encoding="utf-8")  # append-only, line-safe
            fh.setFormatter(fmt)
            log.addHandler(fh)
    except Exception:
        pass  # console logging still works
    return log


def _run_child(host, port):
    """Child role: run uvicorn programmatically and honor an in-place restart.

    server.run() blocks until graceful shutdown — triggered by Ctrl-C/SIGTERM
    (normal stop) or by auto_update.request_restart() (which sets
    server.should_exit). On return, if a restart was requested we exit with
    RESTART_EXIT_CODE so the supervisor respawns us with fresh code; otherwise
    we exit 0 and the supervisor stops too.
    """
    import logging

    import uvicorn

    from backend.services import auto_update

    log = logging.getLogger("artsmoker.supervisor")

    # backend.app owns all logging (coloured console + append-only file); passing
    # log_config=None stops uvicorn from resetting the logging config on startup.
    config = uvicorn.Config("backend.app:app", host=host, port=port, log_config=None)
    server = uvicorn.Server(config)
    auto_update.register_server(server)

    server.run()  # blocks until graceful shutdown

    if auto_update.restart_requested():
        log.info("App child: restart requested — exiting %d for supervisor respawn.",
                 auto_update.RESTART_EXIT_CODE)
        return auto_update.RESTART_EXIT_CODE
    return 0


def _supervise(host, port, child_cmd=None):
    """Parent role: run the app in a child process, respawn on restart requests.

    Cross-OS: uses subprocess + exit codes (no os.execv / signal-based re-exec).
    Ctrl-C/SIGTERM to the supervisor are forwarded to the child and stop the
    whole thing cleanly (no respawn). A child exit of RESTART_EXIT_CODE means
    "an update was applied, come back on fresh code" → respawn. Any other exit
    is propagated.

    `child_cmd` overrides the spawned command (tests only); production always
    respawns ``python -m backend.main`` as the app child.
    """
    import os
    import secrets
    import signal
    import subprocess
    import sys
    import time

    from backend.services.auto_update import RESTART_EXIT_CODE

    log = _setup_supervisor_logging()

    # Crash-loop guard: a healthy restart is rare (an applied update, gated by a
    # version bump). If the child keeps exiting RESTART_EXIT_CODE in a tight loop
    # (a bug that re-triggers a restart every boot), stop respawning instead of
    # busy-spinning. A normal crash exits non-42 and already stops the supervisor.
    _RESTART_BURST_MAX = 5      # respawns...
    _RESTART_BURST_WINDOW = 60  # ...allowed within this many seconds
    _restart_times: list = []

    child_env = dict(os.environ)
    # Per-launch nonce: marks the child as supervised (auto_update.is_supervised()).
    child_env["ARTSMOKER_SUPERVISED"] = secrets.token_hex(8)
    if child_cmd is None:
        child_cmd = [sys.executable, "-m", "backend.main", "--host", str(host), "--port", str(port)]

    state = {"stopping": False, "proc": None}

    def _handle_stop(signum, _frame):
        # Operator asked the supervisor to stop — forward to the child and don't
        # respawn. The child (uvicorn) shuts down gracefully on the same signal.
        state["stopping"] = True
        proc = state["proc"]
        if proc is not None and proc.poll() is None:
            try:
                proc.send_signal(signum)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass

    for _signame in ("SIGINT", "SIGTERM", "SIGHUP"):
        _sig = getattr(signal, _signame, None)
        if _sig is not None:
            try:
                signal.signal(_sig, _handle_stop)
            except (ValueError, OSError):
                pass  # not settable on this platform / not main thread

    log.info("Supervisor started (pid %d) — serving %s:%d; auto-updates restart the app in place.",
             os.getpid(), host, port)

    while True:
        proc = subprocess.Popen(child_cmd, env=child_env, cwd=str(PROJECT_ROOT))
        state["proc"] = proc
        try:
            rc = proc.wait()
        except KeyboardInterrupt:
            # Ctrl-C reached the supervisor directly — forward and wait for the
            # child to finish its graceful shutdown.
            state["stopping"] = True
            try:
                proc.send_signal(getattr(signal, "SIGINT", signal.SIGTERM))
            except Exception:
                pass
            try:
                rc = proc.wait(timeout=30)
            except Exception:
                proc.kill()
                rc = proc.wait()

        if state["stopping"]:
            # Operator-initiated stop: the child shuts down gracefully but exits
            # with the forwarded signal's code (e.g. -15 for SIGTERM). That's a
            # clean stop from our side, so report success (0) — systemd/Docker
            # then see a normal exit, not a failure.
            log.info("Supervisor stopping (child exit %s).", rc)
            return 0
        if rc == RESTART_EXIT_CODE:
            now = time.monotonic()
            _restart_times[:] = [t for t in _restart_times if now - t < _RESTART_BURST_WINDOW]
            _restart_times.append(now)
            if len(_restart_times) > _RESTART_BURST_MAX:
                log.error("Child requested %d restarts within %ds — likely a restart loop. "
                          "Supervisor giving up to avoid a busy-spin; fix the app and relaunch.",
                          len(_restart_times), _RESTART_BURST_WINDOW)
                return 1
            log.info("Child requested restart — respawning with current code.")
            continue
        log.info("Child exited (code %s) with no restart request — supervisor exiting.", rc)
        return rc


def main(argv=None):
    """Entry point for ``python -m backend.main``.

    Role is chosen by the ARTSMOKER_SUPERVISED env var: absent → supervisor
    (parent); present → app child. The parent normalizes --host/--port and
    passes them to the child explicitly.
    """
    import os
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    host, port = _parse_host_port(argv)

    if os.environ.get("ARTSMOKER_SUPERVISED"):
        rc = _run_child(host, port)
    else:
        rc = _supervise(host, port)
    sys.exit(rc if isinstance(rc, int) else 0)


if __name__ == "__main__":
    main()
