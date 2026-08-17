#!/usr/bin/env python3
"""ArtSmoker launcher — run the server and optionally tee ALL output to a file.

Purely command-line gated (no environment variables). With --log-file, the
combined stdout+stderr of the server AND every worker it spawns is mirrored to
the console and APPENDED to the given file, framed by per-session banners that
record when the session was launched and when it shut down (UTC-timestamped).
Because it captures the raw console stream, it records everything — Python log
records, uvicorn's own startup lines, and any tracebacks printed to stderr — not
just what goes through the logging module.

Usage:
  # append everything to a session-framed, append-only log file:
  python run.py --log-file artsmoker.log -- uvicorn backend.main:app --port 8000

  # multi-worker (production) — all workers land in the one file:
  python run.py --log-file artsmoker.log -- gunicorn backend.main:app \\
      -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

  # no --log-file: just runs the server, console only (identical to running it directly):
  python run.py -- uvicorn backend.main:app --reload

Everything after `--` is the server command, run verbatim. If omitted, it
defaults to `uvicorn backend.main:app`.
"""
import argparse
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone

# Strip ANSI colour codes for the FILE copy (the console keeps its colours).
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _banner(title: str, extra: str = "") -> str:
    line = "=" * 80
    stamp = datetime.now(timezone.utc).isoformat()
    return f"\n{line}\n=== ArtSmoker {title}  {stamp}  (pid {os.getpid()}){('  ' + extra) if extra else ''}\n{line}\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run the ArtSmoker server, optionally tee-ing all output to an append-only, session-framed log file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--log-file", metavar="PATH",
                    help="Append all server output to PATH (created if missing), framed by SESSION START/SHUTDOWN banners.")
    ap.add_argument("server_cmd", nargs=argparse.REMAINDER,
                    help="The server command to run, after `--` (default: uvicorn backend.main:app).")
    args = ap.parse_args()

    cmd = list(args.server_cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        cmd = ["uvicorn", "backend.main:app"]

    # No log file → exec the server directly (no tee overhead, identical to a
    # bare run; the launcher gets out of the way entirely).
    if not args.log_file:
        try:
            os.execvp(cmd[0], cmd)
        except FileNotFoundError:
            sys.stderr.write(f"run.py: command not found: {cmd[0]}\n")
            return 127

    # Tee mode: mirror the child's combined stream to console + append file.
    logf = open(args.log_file, "a", encoding="utf-8")  # 'a' = append-only; never truncates prior sessions
    start = datetime.now(timezone.utc)
    logf.write(_banner("SESSION START", f"cmd: {' '.join(cmd)}"))
    logf.flush()

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, text=True,
        )
    except FileNotFoundError:
        msg = f"run.py: command not found: {cmd[0]}\n"
        sys.stderr.write(msg)
        logf.write(msg)
        logf.write(_banner("SESSION SHUTDOWN", "exit=127 (server command not found)"))
        logf.flush(); logf.close()
        return 127

    # Forward Ctrl-C / SIGTERM to the child so it shuts down gracefully; we then
    # fall through to write the shutdown banner once it exits.
    def _forward(signum, _frame):
        try:
            proc.send_signal(signum)
        except ProcessLookupError:
            pass
    signal.signal(signal.SIGINT, _forward)
    signal.signal(signal.SIGTERM, _forward)

    try:
        for line in proc.stdout:                 # blocks until child writes / exits
            sys.stdout.write(line)
            sys.stdout.flush()
            logf.write(_ANSI.sub("", line))
            logf.flush()
    finally:
        proc.wait()
        end = datetime.now(timezone.utc)
        dur = (end - start).total_seconds()
        logf.write(_banner("SESSION SHUTDOWN", f"exit={proc.returncode}  ran {dur:.0f}s"))
        logf.flush()
        logf.close()
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
