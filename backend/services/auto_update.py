"""Auto-update on server start — pulls latest code from GitHub.

Similar to oh-my-zsh's auto-update on shell launch. Runs once at startup,
before the server begins accepting requests.

Protected files (user config) are backed up before pull and restored after:
  - backend/model_registry.json   (discovered models, pricing, regions)
  - backend/prompt_templates.json (user-customized LLM directives)

Safety:
  - Only runs git pull --ff-only (fast-forward only — no merge conflicts)
  - If working tree has uncommitted code changes, skips the pull entirely
  - Protected files are never overwritten by the pull
  - If anything fails, the server starts normally with existing code
  - Set ARTSMOKER_AUTO_UPDATE=false to disable
"""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Protected files list — no longer needed since user data is now stored in
# separate .user.json files (gitignored). Defaults files update via git pull,
# user overrides are never touched. Kept empty for backward compatibility.
PROTECTED_FILES = []


def check_and_update() -> dict:
    """Check for updates and pull if available. Returns status dict.

    Called once during server startup (lifespan handler).
    """
    result = {
        "checked": False,
        "updated": False,
        "from_version": "",
        "to_version": "",
        "skipped_reason": "",
        "error": "",
    }

    try:
        # 1. Check if we're in a git repo
        if not (PROJECT_ROOT / ".git").is_dir():
            result["skipped_reason"] = "Not a git repository"
            return result

        # 2. Check if auto-update is disabled
        import os
        if os.environ.get("ARTSMOKER_AUTO_UPDATE", "").lower() in ("false", "0", "no"):
            result["skipped_reason"] = "Disabled (ARTSMOKER_AUTO_UPDATE=false)"
            return result

        # 3. Check current branch (only update main)
        branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
        if branch != "main":
            result["skipped_reason"] = f"Not on main branch (on '{branch}')"
            return result

        # 4. Check for uncommitted code changes (excluding protected files)
        dirty = _git("status", "--porcelain").strip()
        if dirty:
            # Filter out protected files — only block if code files are dirty
            dirty_lines = [l for l in dirty.splitlines() if l.strip()]
            code_dirty = [l for l in dirty_lines
                          if not any(pf in l for pf in PROTECTED_FILES)]
            if code_dirty:
                result["skipped_reason"] = f"Uncommitted code changes ({len(code_dirty)} files)"
                return result

        # 5. Fetch latest from origin
        result["checked"] = True
        _git("fetch", "origin", "main", "--quiet")

        # 6. Check if there are new commits
        local_sha = _git("rev-parse", "HEAD").strip()
        remote_sha = _git("rev-parse", "origin/main").strip()

        if local_sha == remote_sha:
            result["skipped_reason"] = "Already up to date"
            return result

        # 7. Check how many commits behind
        behind = _git("rev-list", "--count", f"HEAD..origin/main").strip()
        logger.info("Update available: %s commit(s) behind origin/main", behind)

        # 8. Read current version before pull
        result["from_version"] = _read_version()

        # 9. Back up protected files
        backups = _backup_protected_files()

        # 10. Pull (fast-forward only — no merge commits)
        try:
            pull_output = _git("pull", "--ff-only", "origin", "main")
            logger.info("Git pull: %s", pull_output.strip())
        except subprocess.CalledProcessError as e:
            # Pull failed (likely diverged) — restore backups and skip
            _restore_protected_files(backups)
            result["skipped_reason"] = f"Pull failed (ff-only): {e.stderr or e.stdout}"
            return result

        # 11. Restore protected files
        _restore_protected_files(backups)

        # 12. Read new version after pull
        result["to_version"] = _read_version()
        result["updated"] = True

        logger.info(
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║  AUTO-UPDATE COMPLETE                                      ║\n"
            "║  %s → %s (%s commit(s))%s║\n"
            "║  Protected files preserved (model_registry, templates)     ║\n"
            "╚══════════════════════════════════════════════════════════════╝",
            result["from_version"],
            result["to_version"],
            behind,
            " " * (39 - len(result["from_version"]) - len(result["to_version"]) - len(behind)),
        )

        return result

    except Exception as exc:
        result["error"] = str(exc)
        logger.warning("Auto-update check failed (server will start normally): %s", exc)
        return result


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
                # Parse: APP_VERSION = "1.4-20260331_03"
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def _backup_protected_files() -> dict[str, bytes]:
    """Back up protected files before pull. Returns {relative_path: bytes}."""
    backups = {}
    for rel_path in PROTECTED_FILES:
        full_path = PROJECT_ROOT / rel_path
        if full_path.exists():
            backups[rel_path] = full_path.read_bytes()
            logger.debug("Backed up %s (%d bytes)", rel_path, len(backups[rel_path]))
    return backups


def _restore_protected_files(backups: dict[str, bytes]):
    """Restore protected files after pull."""
    for rel_path, content in backups.items():
        full_path = PROJECT_ROOT / rel_path
        full_path.write_bytes(content)
        logger.debug("Restored %s (%d bytes)", rel_path, len(content))
