"""Server-side 3D mesh export — GLB → FBX via a headless Blender subprocess.

Design (see the project design notes): end-users NEVER install anything. Blender is
a server-side concern, provisioned automatically and presented as processing:

  1. REUSE a working system Blender if one is found (detection cascade:
     locate → version-gate ≥3.0 → smoke-test — "exists" ≠ "works").
  2. Else SILENTLY download a portable Blender into `settings.blender_tools_dir`
     (repo-root `tools/`, gitignored) — our "managed" copy.
  3. Convert by running Blender headless against our own `blender/convert.py`.

Only the MANAGED copy is ever auto-updated; a reused system Blender is never
touched. Conversion is invoked lazily (on first FBX request) by the caller; this
module also exposes `preprovision_async()` to warm Blender in the background when a
3D model is first generated.

Security notes for the scanners:
  * Blender is a FIXED binary we detect or download; convert.py is OUR script; the
    GLB/FBX paths are server-generated — never request/user input. subprocess calls
    are list-form (no shell) and carry a bare `# nosemgrep -- reason`.
  * Downloads use urllib to a URL we build for the official download.blender.org
    host (scheme+host asserted) → `# nosec B310`.
  * Archive extraction validates every member path against the destination before
    extracting (no path traversal).
"""
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tarfile
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.config import APP_VERSION, settings
from backend.services.safe_write import named_write_lock

logger = logging.getLogger(__name__)

# blender.org's CDN 403s the default "Python-urllib" User-Agent — set an honest one.
_USER_AGENT = f"ArtSmoker/{APP_VERSION} (mesh-export)"

# Oldest Blender where both add-ons ship AND glTF PBR import is solid. Hard floor
# is 2.80; 3.0 is the safe production floor.
MIN_VERSION = (3, 0, 0)
# Used only if endoflife.date is unreachable when we must download.
_PINNED_FALLBACK = (5, 1, 2)
_ENDOFLIFE_URL = "https://endoflife.date/api/blender.json"
_DOWNLOAD_HOST_PREFIX = "https://download.blender.org/"

_CONVERT_SCRIPT = Path(__file__).resolve().parent / "blender" / "convert.py"

# Smoke-test: prove libs load + bundled Python runs + BOTH add-ons enable.
_SMOKE_EXPR = (
    "import bpy, addon_utils; "
    "addon_utils.enable('io_scene_gltf2'); "
    "addon_utils.enable('io_scene_fbx'); "
    "print('ARTSMOKER_OK', bpy.app.version_string)"
)


class MeshExportError(RuntimeError):
    """Raised when FBX export cannot be produced (Blender missing / convert failed)."""


@dataclass
class BlenderInstall:
    path: str                 # absolute path to the blender executable
    version: tuple            # (X, Y, Z)
    source: str               # 'system' (reused) | 'managed' (our download)


# ── small helpers ─────────────────────────────────────────────────────────────

def _fmt(v) -> str:
    return ".".join(str(x) for x in v) if v else "unknown"


def _parse_ver(s):
    if not s:
        return None
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", str(s))
    return tuple(int(x) for x in m.groups()) if m else None


def _tools_dir() -> Path:
    return Path(settings.blender_tools_dir)


def _get_state() -> dict:
    from backend.services import model_registry
    return model_registry.get_blender_state()


def _set_state(**fields):
    from backend.services import model_registry
    model_registry.set_blender_state(**fields)


# ── platform / URL resolution ───────────────────────────────────────────────

def _platform_key():
    """Return (os_tag, (blender_platform, archive_ext)) for the current host."""
    sysname = platform.system()
    machine = platform.machine().lower()
    if sysname == "Linux":
        return "linux", ("linux-x64", "tar.xz")
    if sysname == "Windows":
        return "windows", ("windows-x64", "zip")
    if sysname == "Darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
        return "macos", (f"macos-{arch}", "dmg")
    raise MeshExportError(f"unsupported platform for Blender download: {sysname}")


def _download_url(version) -> str:
    x, y, z = version
    _, (plat, ext) = _platform_key()
    return f"{_DOWNLOAD_HOST_PREFIX}release/Blender{x}.{y}/blender-{x}.{y}.{z}-{plat}.{ext}"


def _resolve_latest_stable() -> tuple:
    """Latest STABLE Blender X.Y.Z via endoflife.date (newest cycle first)."""
    try:
        req = urllib.request.Request(
            _ENDOFLIFE_URL, headers={"Accept": "application/json", "User-Agent": _USER_AGENT})
        # nosemgrep -- fixed endoflife.date API URL (no user input); read-only version lookup
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 -- https api, audited host
            data = json.loads(resp.read().decode("utf-8"))
        ver = _parse_ver((data or [{}])[0].get("latest"))
        if ver:
            return ver
    except Exception as e:  # noqa: BLE001 - network/parse issues fall back to pin
        logger.warning("Blender: could not resolve latest version (%s) — using pinned %s",
                        e, _fmt(_PINNED_FALLBACK))
    return _PINNED_FALLBACK


# ── candidate discovery ─────────────────────────────────────────────────────

def _find_exe_in(root) -> Path | None:
    """Find the Blender executable inside an extracted/installed tree."""
    root = Path(root)
    if not root.exists():
        return None
    sysname = platform.system()
    if sysname == "Darwin":
        hits = sorted(root.glob("**/Blender.app/Contents/MacOS/Blender"))
    elif sysname == "Windows":
        hits = sorted(root.glob("**/blender.exe"))
    else:
        hits = sorted(p for p in root.glob("**/blender") if p.is_file() and os.access(p, os.X_OK))
    return hits[0] if hits else None


def _managed_candidates():
    """Our downloaded copies, newest first: [(exe_path, 'managed'), ...]."""
    out, seen = [], set()
    exe = _get_state().get("managed_exe")
    if exe and Path(exe).exists():
        out.append((exe, "managed"))
        seen.add(exe)
    tools = _tools_dir()
    if tools.exists():
        # Sort version dirs newest-first by parsed version.
        dirs = sorted(tools.glob("blender-*"),
                      key=lambda d: (_parse_ver(d.name.replace("blender-", "")) or (0, 0, 0)),
                      reverse=True)
        for d in dirs:
            e = _find_exe_in(d)
            if e and str(e) not in seen:
                out.append((str(e), "managed"))
                seen.add(str(e))
    return out


def _system_candidates():
    """Reusable system installs: PATH first, then OS-standard locations.

    NOTE (verified): `which blender` misses /Applications/Blender.app on macOS, so
    PATH alone is insufficient — we must probe known locations too.
    """
    out = []
    which = shutil.which("blender")
    if which:
        out.append((which, "system"))
    sysname = platform.system()
    if sysname == "Darwin":
        out.append(("/Applications/Blender.app/Contents/MacOS/Blender", "system"))
    elif sysname == "Windows":
        import glob
        for p in sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"), reverse=True):
            out.append((p, "system"))
    else:  # Linux
        for p in ("/usr/bin/blender", "/usr/local/bin/blender", "/opt/blender/blender",
                  "/snap/bin/blender", "/var/lib/flatpak/exports/bin/org.blender.Blender"):
            out.append((p, "system"))
    # De-dup, keep only existing.
    seen, existing = set(), []
    for path, src in out:
        if path and path not in seen and Path(path).exists():
            existing.append((path, src))
            seen.add(path)
    return existing


# ── version-gate + smoke-test ────────────────────────────────────────────────

def _blender_version(path) -> tuple | None:
    try:
        # nosemgrep -- fixed blender binary path (detected/managed by us), no user input
        r = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.debug("Blender: --version failed for %s: %s", path, e)
        return None
    first = (r.stdout or "").strip().splitlines()[:1]
    if not first:
        return None
    m = re.match(r"^Blender\s+(\d+)\.(\d+)\.(\d+)", first[0])
    return tuple(int(x) for x in m.groups()) if m else None


def _smoke_test(path) -> bool:
    """Definitive 'exists AND works': libs load, bundled Python runs, add-ons enable."""
    try:
        # nosemgrep -- fixed blender binary (detected/managed by us) + a fixed --python-expr; no user input
        r = subprocess.run(
            [str(path), "--background", "--factory-startup", "--python-exit-code", "1",
             "--python-expr", _SMOKE_EXPR],
            capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.debug("Blender: smoke-test errored for %s: %s", path, e)
        return False
    return r.returncode == 0 and "ARTSMOKER_OK" in (r.stdout or "")


# ── download + extract ───────────────────────────────────────────────────────

def _download(url, dest):
    if not url.startswith(_DOWNLOAD_HOST_PREFIX):
        raise MeshExportError(f"refusing non-official Blender URL: {url}")
    logger.info("Blender: downloading %s", url)
    # urlretrieve can't set headers and blender.org 403s the default UA, so build a
    # Request with an honest User-Agent and stream the (~400 MB) body to disk.
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    # nosemgrep -- fixed download.blender.org release URL (host asserted above); not user input
    with urllib.request.urlopen(req, timeout=600) as resp:  # nosec B310 -- https official Blender release, audited host
        with open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh, length=1024 * 1024)


def _guard_member(dest_root: Path, name: str):
    """Reject archive members that would escape the destination (path traversal)."""
    target = (dest_root / name).resolve()
    root = dest_root.resolve()
    if target != root and root not in target.parents:
        raise MeshExportError(f"unsafe path in archive: {name!r}")


def _safe_extract_tar(archive: Path, dest: Path):
    with tarfile.open(archive, "r:xz") as tf:
        members = tf.getmembers()
        for m in members:
            _guard_member(dest, m.name)
        tf.extractall(dest)  # nosec B202 -- every member validated to stay within dest (see _guard_member)


def _safe_extract_zip(archive: Path, dest: Path):
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            _guard_member(dest, name)
        zf.extractall(dest)  # nosec B202 -- every member validated to stay within dest (see _guard_member)


def _extract_dmg(archive: Path, dest: Path):
    mount = dest / ".mnt"
    mount.mkdir(parents=True, exist_ok=True)
    # nosemgrep -- fixed 'hdiutil' binary + our own dmg/mount paths; no user input
    subprocess.run(["hdiutil", "attach", "-nobrowse", "-quiet", "-mountpoint", str(mount), str(archive)],
                   check=True, capture_output=True, text=True, timeout=120)
    try:
        apps = list(mount.glob("*.app"))
        if not apps:
            raise MeshExportError("no .app found inside Blender .dmg")
        shutil.copytree(apps[0], dest / apps[0].name)
    finally:
        # nosemgrep -- fixed 'hdiutil' binary + our own mount path; no user input
        subprocess.run(["hdiutil", "detach", "-quiet", str(mount)],
                       capture_output=True, text=True, timeout=60)
        try:
            mount.rmdir()
        except OSError:
            pass


def _download_and_extract(version) -> Path | None:
    """Download + extract a portable Blender X.Y.Z into tools/; return its exe path."""
    tools = _tools_dir()
    tools.mkdir(parents=True, exist_ok=True)
    _, (_, ext) = _platform_key()
    url = _download_url(version)
    verdir = tools / f"blender-{_fmt(version)}"
    archive = tools / f"blender-{_fmt(version)}.{ext}"
    try:
        _download(url, archive)
        if verdir.exists():
            shutil.rmtree(verdir, ignore_errors=True)
        verdir.mkdir(parents=True, exist_ok=True)
        if ext == "tar.xz":
            _safe_extract_tar(archive, verdir)
        elif ext == "zip":
            _safe_extract_zip(archive, verdir)
        elif ext == "dmg":
            _extract_dmg(archive, verdir)
        exe = _find_exe_in(verdir)
        if not exe:
            raise MeshExportError("extracted Blender but could not locate its executable")
        if platform.system() != "Windows":
            # Owner-only exec bit (least privilege): only the server process runs it.
            # zip extraction drops unix perms; tar.xz preserves them — this normalizes.
            try:
                os.chmod(exe, 0o700)
            except OSError:
                pass
        return exe
    except Exception as e:  # noqa: BLE001 - surface a clean message; details logged
        logger.error("Blender: download/extract of v%s failed: %s", _fmt(version), e)
        return None
    finally:
        try:
            archive.unlink()
        except OSError:
            pass


# ── resolution + caching ─────────────────────────────────────────────────────

_INSTALL_CACHE: BlenderInstall | None = None
_CACHE_LOCK = threading.Lock()


def _invalidate_cache():
    global _INSTALL_CACHE
    with _CACHE_LOCK:
        _INSTALL_CACHE = None


def _validate_candidate(path, source) -> BlenderInstall | None:
    ver = _blender_version(path)
    if not ver:
        return None
    if ver < MIN_VERSION:
        logger.info("Blender: skipping %s (v%s < required %s)", path, _fmt(ver), _fmt(MIN_VERSION))
        return None
    if not _smoke_test(path):
        logger.warning("Blender: candidate %s (v%s) failed smoke-test — skipping", path, _fmt(ver))
        return None
    return BlenderInstall(path=str(path), version=ver, source=source)


def _resolve_install(allow_download) -> BlenderInstall | None:
    if settings.blender_prefer_managed_latest:
        candidates = _managed_candidates()          # our copy only
    else:
        candidates = _managed_candidates() + _system_candidates()  # reuse anything working

    for path, source in candidates:
        inst = _validate_candidate(path, source)
        if inst:
            logger.info("Blender: using %s install — v%s at %s (smoke-test OK)",
                        inst.source, _fmt(inst.version), inst.path)
            return inst

    if not allow_download:
        return None

    target = _resolve_latest_stable()
    logger.info("Blender: no usable install found — downloading portable v%s (~400 MB) to %s",
                _fmt(target), _tools_dir())
    exe = _download_and_extract(target)
    if not exe:
        logger.error("Blender: automatic download failed — FBX export unavailable.%s", _linux_lib_hint())
        return None
    inst = _validate_candidate(exe, "managed")
    if not inst:
        logger.error("Blender: downloaded v%s but it failed validation — unusable.%s",
                     _fmt(target), _linux_lib_hint())
        return None
    _set_state(managed_version=_fmt(inst.version), managed_exe=inst.path)
    logger.info("Blender: download OK, smoke-test passed — using managed v%s at %s",
                _fmt(inst.version), inst.path)
    return inst


def ensure_blender(allow_download: bool = True) -> BlenderInstall | None:
    """Return a usable Blender (reused system or managed download), or None.

    Provisioning is serialized across workers via a cross-process file lock so two
    concurrent FBX requests never double-download.
    """
    global _INSTALL_CACHE
    with _CACHE_LOCK:
        if _INSTALL_CACHE and Path(_INSTALL_CACHE.path).exists():
            return _INSTALL_CACHE
    with named_write_lock("blender_provision"):
        with _CACHE_LOCK:
            if _INSTALL_CACHE and Path(_INSTALL_CACHE.path).exists():
                return _INSTALL_CACHE
        inst = _resolve_install(allow_download=allow_download)
        if inst:
            with _CACHE_LOCK:
                _INSTALL_CACHE = inst
        return inst


def _linux_lib_hint() -> str:
    if platform.system() != "Linux":
        return ""
    return (" On Linux, Blender needs X11/GL client libs even headless — one-time: "
            "sudo apt install libx11-6 libxi6 libxfixes3 libxrender1 libxkbcommon0 "
            "libgl1 libglx-mesa0 libsm6 libice6 libxt6 libxext6")


# ── engine targets (axis/scale) + conversion ─────────────────────────────────

# Per-target orientation for FBX (export_scene.fbx) + USD (wm.usd_export). GLB is
# intentionally NOT re-oriented — glTF is spec-locked to Y-up and importers convert
# on load; only FBX/USD support and benefit from a target up-axis. Scale stays 1.0
# (engines apply their own unit convention on import); we fix the far-more-impactful
# AXIS so meshes import upright. Config-driven — add engines here, no code change.
TARGETS = {
    "generic": {"label": "Generic (glTF, Y-up)",
                "fbx": {"axis_up": "Y", "axis_forward": "-Z"}, "usd": {"up": "Y", "fwd": "-Z"}},
    "unreal":  {"label": "Unreal Engine (Z-up)",
                "fbx": {"axis_up": "Z", "axis_forward": "X"},  "usd": {"up": "Z", "fwd": "Y"}},
    "unity":   {"label": "Unity (Y-up)",
                "fbx": {"axis_up": "Y", "axis_forward": "Z"},  "usd": {"up": "Y", "fwd": "Z"}},
    "godot":   {"label": "Godot (Y-up)",
                "fbx": {"axis_up": "Y", "axis_forward": "-Z"}, "usd": {"up": "Y", "fwd": "-Z"}},
    "maya":    {"label": "Maya (Y-up)",
                "fbx": {"axis_up": "Y", "axis_forward": "Z"},  "usd": {"up": "Y", "fwd": "Z"}},
    "3dsmax":  {"label": "3ds Max (Z-up)",
                "fbx": {"axis_up": "Z", "axis_forward": "-Y"}, "usd": {"up": "Z", "fwd": "Y"}},
}
DEFAULT_TARGET = "generic"
EXPORT_FORMATS = ("fbx", "usd")   # GLB is served pristine, never re-exported

_FBX_BASE = {"path_mode": "COPY", "embed_textures": True,
             "use_selection": False, "bake_space_transform": False, "global_scale": 1.0}
# USD export (wm.usd_export): export_textures_mode is an enum (NEW writes/packs
# textures — for .usdz they're packaged into the single file). Orientation needs
# convert_orientation=True + the up/forward SELECTION enums (which use the
# NEGATIVE_* spelling, unlike FBX's "-Z").
_USD_BASE = {"export_materials": True, "export_textures_mode": "NEW", "convert_orientation": True}

# FBX axis enums use "-Z"; USD selection enums use "NEGATIVE_Z".
_USD_AXIS = {"X": "X", "Y": "Y", "Z": "Z",
             "-X": "NEGATIVE_X", "-Y": "NEGATIVE_Y", "-Z": "NEGATIVE_Z"}


def _fbx_kwargs(target):
    t = TARGETS.get(target, TARGETS[DEFAULT_TARGET])["fbx"]
    return {**_FBX_BASE, "axis_up": t["axis_up"], "axis_forward": t["axis_forward"]}


def _usd_kwargs(target):
    t = TARGETS.get(target, TARGETS[DEFAULT_TARGET])["usd"]
    return {**_USD_BASE,
            "export_global_up_selection": _USD_AXIS.get(t["up"], t["up"]),
            "export_global_forward_selection": _USD_AXIS.get(t["fwd"], t["fwd"])}


def convert_mesh(glb_path, outputs: dict, target: str = DEFAULT_TARGET, *, timeout: int = 600) -> dict:
    """Convert a GLB to the requested formats for `target` in ONE Blender pass.

    outputs = {"fbx": <path>, "usd": <path>} (any subset). Returns {fmt: Path} for the
    files actually written. Raises MeshExportError on failure.
    """
    import json as _json
    import tempfile
    glb_path = Path(glb_path)
    if not glb_path.exists():
        raise MeshExportError(f"source GLB not found: {glb_path}")
    if not outputs:
        raise MeshExportError("no output formats requested")
    inst = ensure_blender(allow_download=True)
    if inst is None:
        raise MeshExportError("Blender is unavailable — cannot export." + _linux_lib_hint())

    spec = {}
    if "fbx" in outputs:
        Path(outputs["fbx"]).parent.mkdir(parents=True, exist_ok=True)
        spec["fbx"] = {"path": str(outputs["fbx"]), "kwargs": _fbx_kwargs(target)}
    if "usd" in outputs:
        Path(outputs["usd"]).parent.mkdir(parents=True, exist_ok=True)
        spec["usd"] = {"path": str(outputs["usd"]), "kwargs": _usd_kwargs(target)}

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        _json.dump(spec, tf)
        spec_path = tf.name
    try:
        # nosemgrep -- fixed blender binary (detected/managed by us) + our own convert.py; GLB path + spec are server-generated, not user input
        r = subprocess.run(
            [inst.path, "--background", "--factory-startup", "--python-exit-code", "1",
             "--python", str(_CONVERT_SCRIPT), "--", str(glb_path), spec_path],
            capture_output=True, text=True, timeout=timeout,
        )
    finally:
        try:
            os.unlink(spec_path)
        except OSError:
            pass

    if r.returncode != 0 or "ARTSMOKER_CONVERT_OK" not in (r.stdout or ""):
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        detail = tail[-1] if tail else "unknown error"
        logger.error("Blender: mesh convert failed (exit %s, target=%s): %s", r.returncode, target, detail)
        raise MeshExportError(f"Blender export failed (exit {r.returncode}): {detail}")

    written = {}
    for fmt, p in outputs.items():
        p = Path(p)
        if p.exists() and p.stat().st_size > 0:
            written[fmt] = p
    if not written:
        raise MeshExportError("Blender reported success but produced no output")
    logger.info("Blender: exported %s for target '%s' via v%s (%s)",
                "+".join(sorted(written)), target, _fmt(inst.version), glb_path.name)
    return written


def convert_glb_to_fbx(glb_path, fbx_path, *, timeout: int = 300) -> Path:
    """Back-compat single-format helper (generic target, FBX only)."""
    return convert_mesh(glb_path, {"fbx": Path(fbx_path)}, DEFAULT_TARGET, timeout=timeout)["fbx"]


# ── update management (managed copy only) ─────────────────────────────────────

def _within_days(iso_ts: str, days: int) -> bool:
    try:
        then = datetime.fromisoformat(iso_ts)
    except (ValueError, TypeError):
        return False
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - then).days < days


def check_for_update(force: bool = False) -> dict:
    """Check for (and, if newer, install) an update to the MANAGED Blender copy.

    Never updates a reused system Blender. `force=True` = the Model Settings button;
    otherwise gated by `blender_auto_update` + a ~30-day cadence. Safe: download the
    new build alongside, smoke-test it FIRST, switch only if it passes, keep the old
    one as fallback. Returns a small status dict for the UI/logs.
    """
    state = _get_state()
    if not force:
        if not settings.blender_auto_update:
            return {"checked": False, "reason": "auto-update disabled"}
        last = state.get("last_update_check")
        if last and _within_days(last, 30):
            return {"checked": False, "reason": "checked within the last 30 days"}

    _set_state(last_update_check=datetime.now(timezone.utc).isoformat())
    latest = _resolve_latest_stable()

    current = ensure_blender(allow_download=False)
    if current and current.source == "system":
        # We reuse the user's install as-is; never auto-update someone else's software.
        logger.info("Blender: update-check — reusing system v%s (latest stable is v%s; managed copy not used)",
                    _fmt(current.version), _fmt(latest))
        return {"checked": True, "updated": False, "reason": "using system Blender (not managed)",
                "current": _fmt(current.version), "latest": _fmt(latest)}

    managed_ver = _parse_ver(state.get("managed_version"))
    if managed_ver and managed_ver >= latest:
        return {"checked": True, "updated": False, "current": _fmt(managed_ver), "latest": _fmt(latest)}

    logger.info("Blender: newer stable available (v%s > v%s) — updating managed copy",
                _fmt(latest), _fmt(managed_ver) if managed_ver else "none")
    exe = _download_and_extract(latest)
    inst = _validate_candidate(exe, "managed") if exe else None
    if not inst:
        logger.error("Blender: update to v%s failed validation — keeping previous copy", _fmt(latest))
        return {"checked": True, "updated": False, "error": "new build failed smoke-test",
                "current": _fmt(managed_ver) if managed_ver else None, "latest": _fmt(latest)}

    _set_state(managed_version=_fmt(inst.version), managed_exe=inst.path)
    _invalidate_cache()
    logger.info("Blender: updated managed copy to v%s", _fmt(inst.version))
    return {"checked": True, "updated": True, "current": _fmt(inst.version), "latest": _fmt(latest)}


# ── background warm-up + status ───────────────────────────────────────────────

def preprovision_async():
    """Warm Blender in a daemon thread (called on first 3D generation) so it's ready
    before anyone clicks 'Download FBX'. Best-effort; never blocks or raises."""
    def _run():
        try:
            # ensure_blender caches after the first resolve, so this is a cheap
            # no-op on every 3D submit after the first — debug-level to avoid
            # repeating alongside the once-per-process detection line.
            inst = ensure_blender(allow_download=True)
            if inst:
                logger.debug("Blender: pre-provision ready — v%s (%s)", _fmt(inst.version), inst.source)
        except Exception as e:  # noqa: BLE001
            logger.warning("Blender: pre-provision failed: %s", e)
    threading.Thread(target=_run, name="blender-preprovision", daemon=True).start()


def get_status() -> dict:
    """Status for the Model Settings UI (detection only — never triggers a download)."""
    inst = ensure_blender(allow_download=False)
    state = _get_state()
    return {
        "available": inst is not None,
        "version": _fmt(inst.version) if inst else None,
        "source": inst.source if inst else None,           # 'system' | 'managed' | None
        "path": inst.path if inst else None,
        "prefer_managed_latest": settings.blender_prefer_managed_latest,
        "auto_update": settings.blender_auto_update,
        "last_update_check": state.get("last_update_check"),
        "managed_version": state.get("managed_version"),
        "tools_dir": str(_tools_dir()),
    }
