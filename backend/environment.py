"""ArtSmoker's Python environment: check it at startup, fix it if needed, continue.

``python -m backend.main`` calls :func:`ensure` before anything else, from
whatever Python the user started it with. It returns the interpreter that
should run the app, normally the project's own ``.venv``:

1. Quick check (no subprocess, no network): the venv's interpreter and base
   install still exist, and the packages were installed from the current
   ``requirements.txt`` (a fingerprint written after each install).
2. Fix, only when that fails:
   - requirements changed (or the venv was made by hand): install into it;
   - the venv is gone or broken (e.g. a package manager removed the Python it
     was built on): find the Pythons installed on this machine, newest first,
     and use the first one every package has a ready-made build for (a pip dry
     run decides, so a new Python is used as soon as its packages support it).
     The old venv is kept aside until the new one has installed and imports.
3. A prepared environment of the user's own (another venv, conda, a Docker
   image with the packages installed) is used as is; nothing is managed.

Standard library only, and Python 3.8-compatible syntax: this runs before the
venv exists, possibly on an old system Python.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV = PROJECT_ROOT / ".venv"
REQUIREMENTS = PROJECT_ROOT / "backend" / "requirements.txt"
STAMP = VENV / ".artsmoker-env.json"
# The one fixed bound: aws_sdk_bedrock_runtime (Nova Sonic voice) needs 3.12+.
# There is no upper bound; whether a newer Python works is detected (see above).
MIN_PYTHON = (3, 12)
_WINDOWS = os.name == "nt"


def _say(msg: str) -> None:
    """One line for the person starting ArtSmoker (and the log file, if on)."""
    line = time.strftime("%Y-%m-%d %H:%M:%S") + "  SETUP       " + msg
    print(line, file=sys.stderr, flush=True)
    if os.environ.get("ARTSMOKER_LOG_TO_FILE", "true").lower() not in ("0", "false", "no"):
        try:
            path = Path(os.environ.get("ARTSMOKER_LOG_FILE") or PROJECT_ROOT / "logs" / "artsmoker.log")
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def venv_python(venv: Path = VENV) -> Path:
    return venv / ("Scripts/python.exe" if _WINDOWS else "bin/python")


def _requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def _read_cfg(venv: Path = VENV) -> dict:
    cfg = {}
    try:
        for line in (venv / "pyvenv.cfg").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    except OSError:
        pass
    return cfg


def _version(text: str):
    m = re.match(r"(\d+)\.(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _venv_intact() -> bool:
    """The venv's interpreter and the Python install it was built on still exist."""
    cfg = _read_cfg()
    ver = _version(cfg.get("version_info") or cfg.get("version", ""))
    home = cfg.get("home", "")
    return (venv_python().exists() and bool(home) and Path(home).is_dir()
            and ver is not None and ver >= MIN_PYTHON)


def _stamp_matches(req_hash: str) -> bool:
    try:
        return json.loads(STAMP.read_text(encoding="utf-8")).get("requirements_sha256") == req_hash
    except (OSError, ValueError, AttributeError):
        return False


def write_stamp() -> None:
    """Record that the venv's packages match the current requirements.txt."""
    try:
        STAMP.write_text(json.dumps({
            "requirements_sha256": _requirements_hash(),
            "python": _read_cfg().get("version_info") or _read_cfg().get("version", ""),
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }, indent=1), encoding="utf-8")
    except OSError:
        pass


def _in_our_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except OSError:
        return False


def _required_names() -> list:
    """Distribution names in requirements.txt (lines with an environment marker
    are left out: they apply to some platforms only)."""
    names = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and ";" not in line:
            m = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line)
            if m:
                names.append(m.group(0))
    return names


def _prepared_elsewhere() -> bool:
    """Started from an environment of the user's own (another venv, conda, a
    container image) that already has every package installed."""
    if _in_our_venv():
        return False
    from importlib import metadata
    try:
        for name in _required_names():
            metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return False
    return True


def _run(cmd, **kw) -> subprocess.CompletedProcess:
    # nosemgrep -- list-form, no shell; args are interpreter paths found on this machine + fixed pip/venv flags
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), **kw)


def _pip_install(py: Path, fresh: bool = False) -> bool:
    if fresh:
        _say("Installing ArtSmoker's packages (a few minutes)...")
    r = _run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "--quiet",
              "--prefer-binary", "-r", str(REQUIREMENTS)])
    return r.returncode == 0


def _imports_ok(py: Path) -> bool:
    """The installed packages load, including the compiled ones that tie a
    package to a Python version (background removal's rembg/onnxruntime)."""
    r = _run([str(py), "-c", "import fastapi, uvicorn, pydantic_settings, boto3, PIL, numpy, rembg"],
             capture_output=True, text=True)
    if r.returncode != 0:
        _say("  The packages installed but don't load: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    return r.returncode == 0


def _probe(exe: str):
    """(major, minor, micro) of a base (non-venv, GIL) Python, or None."""
    try:
        r = _run([exe, "-c", "import sys, sysconfig; print('%d.%d.%d' % sys.version_info[:3]); "
                  "print(int(sys.prefix != sys.base_prefix)); print(int(bool(sysconfig.get_config_var('Py_GIL_DISABLED'))))"],
                 capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = r.stdout.split()
    if r.returncode != 0 or len(lines) != 3 or lines[1] == "1" or lines[2] == "1":
        return None
    return tuple(int(x) for x in lines[0].split("."))


def _candidate_paths() -> list:
    """Every Python executable we can find on this machine (unverified)."""
    found = [sys.executable, getattr(sys, "_base_executable", "") or ""]
    name = re.compile(r"^python(3(\.\d+)?)?(\.exe)?$", re.I)
    dirs = os.environ.get("PATH", "").split(os.pathsep)
    if _WINDOWS:
        try:   # the py launcher lists every installed Python
            r = _run(["py", "-0p"], capture_output=True, text=True, timeout=15)
            found += re.findall(r"([A-Za-z]:\\[^\r\n]*python\.exe)", r.stdout)
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        dirs += ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
        dirs += [str(p) for p in Path("/Library/Frameworks/Python.framework/Versions").glob("*/bin")]
    for d in dirs:
        try:
            found += [str(p) for p in Path(d).iterdir() if name.match(p.name)]
        except OSError:
            continue
    return [f for f in found if f]


def find_pythons() -> list:
    """Installed base Pythons at or above MIN_PYTHON, newest first: [(version, path)]."""
    probed, accepted, out = set(), set(), []
    for exe in _candidate_paths():
        if exe in probed or "WindowsApps" in exe:   # the Store alias opens the Store
            continue
        probed.add(exe)
        ver = _probe(exe)                  # rejects venvs before de-duplicating:
        if not ver or ver[:2] < MIN_PYTHON:  # a venv's python resolves to its base
            continue
        try:
            key = os.path.realpath(exe)
        except OSError:
            continue
        if key not in accepted:
            accepted.add(key)
            out.append((ver, exe))
    return sorted(out, reverse=True)


def _packages_available(exe: str):
    """Whether every package in requirements.txt has a ready-made build for this
    Python (a pip dry run: resolves only, installs nothing). True / False, or
    None when it can't be told (no pip in that Python, no internet)."""
    if _run([exe, "-m", "pip", "--version"], capture_output=True).returncode != 0:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        r = _run([exe, "-m", "pip", "install", "--dry-run", "--quiet", "--disable-pip-version-check",
                  "--ignore-installed", "--only-binary", ":all:", "--target", tmp, "-r", str(REQUIREMENTS)],
                 capture_output=True, text=True)
    if r.returncode == 0:
        return True
    if re.search(r"No matching distribution|ResolutionImpossible|Could not find a version", r.stderr):
        return False
    return None


def _rebuild() -> Path:
    pythons = find_pythons()
    if not pythons:
        _explain_no_python([])
    tried = []
    for ver, exe in pythons:
        label = "Python %d.%d" % ver[:2]
        available = _packages_available(exe)
        if available is False:
            _say("%s: ArtSmoker's packages aren't all available for it yet; trying the next one." % label)
            tried.append(label + " (packages not available yet)")
            continue
        # None (couldn't check: no pip there, or offline): try it; the install decides.
        _say("Setting up ArtSmoker's environment with %s..." % label)
        aside = None
        if VENV.exists():
            aside = VENV.with_name(".venv.previous")
            shutil.rmtree(aside, ignore_errors=True)
            try:
                VENV.rename(aside)        # kept until the new one works
            except OSError as e:
                _say("Can't set the old environment aside (%s). Close any program using the "
                     ".venv folder and start ArtSmoker again." % e)
                sys.exit(1)
        ok = _run([exe, "-m", "venv", str(VENV)]).returncode == 0
        ok = ok and _pip_install(venv_python(), fresh=True) and _imports_ok(venv_python())
        if ok:
            write_stamp()
            if aside is not None:
                shutil.rmtree(aside, ignore_errors=True)
            _say("Environment ready (%s)." % label)
            return venv_python()
        shutil.rmtree(VENV, ignore_errors=True)
        if aside is not None:
            aside.rename(VENV)            # put the previous one back
        tried.append(label + " (install failed)")
        _say("%s didn't work out; trying the next one." % label)
    _explain_no_python(tried)


def _explain_no_python(tried: list):
    _say("ArtSmoker can't start: no Python on this computer can run its packages.")
    if tried:
        _say("  Tried: " + "; ".join(tried) + ".")
    _say("  Install Python %d.%d or newer that its packages support (e.g. Python 3.14), then start "
         "ArtSmoker again:" % MIN_PYTHON)
    if _WINDOWS:
        _say("    https://www.python.org/downloads/ (tick \"Add python.exe to PATH\")")
    elif sys.platform == "darwin":
        _say("    brew install python@3.14   (or https://www.python.org/downloads/)")
    else:
        _say("    your package manager, e.g. sudo apt install python3.12 python3.12-venv")
    _say("  If this computer has no internet access, setting up needs it once.")
    sys.exit(1)


def ensure() -> str:
    """The interpreter to run ArtSmoker with, after checking (and if needed
    fixing) its environment."""
    if _prepared_elsewhere():
        return sys.executable
    req_hash = _requirements_hash()
    if _venv_intact():
        if _stamp_matches(req_hash):
            return str(venv_python())                      # the usual case: instant
        _say("Updating ArtSmoker's packages..." if STAMP.exists()
             else "Checking ArtSmoker's packages (once)...")
        if _pip_install(venv_python()) and _imports_ok(venv_python()):
            write_stamp()
            return str(venv_python())
        _say("Updating in place didn't work; setting the environment up again.")
    elif VENV.exists():
        _say("ArtSmoker's environment no longer works (for example, the Python it was "
             "built on was removed); setting it up again.")
    else:
        _say("First start: setting up ArtSmoker's environment.")
    return str(_rebuild())


def is_current(py: str) -> bool:
    """Whether `py` is the interpreter already running this process."""
    if py == sys.executable:
        return True
    return _in_our_venv() and py == str(venv_python())


def relaunch(py: str, argv: list):
    """Continue in the chosen interpreter: same command, same arguments."""
    if os.environ.get("ARTSMOKER_ENV_RELAUNCHED"):   # never loop
        _say("Continuing with %s (already relaunched once)." % sys.executable)
        return
    os.environ["ARTSMOKER_ENV_RELAUNCHED"] = "1"
    cmd = [py, "-m", "backend.main"] + list(argv)
    if _WINDOWS:   # no exec on Windows: run it and pass its exit code through
        try:
            rc = _run(cmd).returncode
        except KeyboardInterrupt:
            rc = 0
        sys.exit(rc)
    os.chdir(str(PROJECT_ROOT))
    # nosemgrep -- re-execs ArtSmoker's own entry point in its own venv interpreter; fixed args
    os.execv(py, cmd)


if __name__ == "__main__":
    # `python -m backend.environment`: check and fix only, then exit (e.g. a
    # systemd ExecStartPre before gunicorn). Prints the interpreter to run with.
    print(ensure())
