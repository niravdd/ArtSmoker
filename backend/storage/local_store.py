"""Local filesystem storage with an S3-compatible interface for future migration."""

import json
import logging
import shutil
from pathlib import Path

from backend.config import settings
from backend.services.safe_write import atomic_write_text

logger = logging.getLogger(__name__)


class LocalStore:
    """Thin wrapper around the local filesystem.

    Methods mirror a subset of S3 semantics so swapping to boto3 S3 later is
    straightforward.
    """

    def __init__(self) -> None:
        self.styles_dir = settings.styles_dir
        # `images_dir` is the current location (data/images). A legacy
        # `data/generated` from before the rename is migrated on startup.
        self.images_dir = settings.images_dir
        self.legacy_generated_dir = settings.legacy_generated_dir
        self.video_dir = settings.video_dir
        self.styles_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_generated_dir()
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

    # ── Legacy storage migration (data/generated → data/images) ───────────
    def _migrate_legacy_generated_dir(self) -> None:
        """One-time, transparent startup migration of the old asset directory.

        Clean case — legacy `data/generated` exists and `data/images` does NOT:
        rename it (atomic, no copy, no data loss). If BOTH exist we do NOT touch
        anything here (that would need a MERGE and risks collisions) — the Gallery
        surfaces a prompt and calls ``merge_legacy_generated_dir`` on user consent.
        """
        legacy, current = self.legacy_generated_dir, self.images_dir
        try:
            if legacy.exists() and legacy.is_dir() and not current.exists():
                legacy.rename(current)
                logger.info("Migrated legacy asset dir: %s → %s", legacy, current)
        except Exception as exc:
            # Never block startup on migration — fall back to using data/images
            # (the Gallery safety prompt will still offer to migrate later).
            logger.warning("Legacy asset-dir migration skipped (%s → %s): %r", legacy, current, exc)

    def legacy_migration_status(self) -> dict:
        """Report whether a legacy `data/generated` still holds assets alongside
        the new `data/images` — drives the Gallery safety prompt."""
        legacy = self.legacy_generated_dir
        legacy_count = 0
        if legacy.exists() and legacy.is_dir():
            try:
                legacy_count = sum(
                    1 for d in legacy.iterdir()
                    if d.is_dir() and (d / "metadata.json").exists()
                )
            except OSError:
                legacy_count = 0
        return {
            "legacy_present": legacy.exists() and legacy_count > 0,
            "legacy_count": legacy_count,
            "legacy_path": str(legacy),
            "current_path": str(self.images_dir),
        }

    def merge_legacy_generated_dir(self) -> dict:
        """Move each legacy asset dir from `data/generated` into `data/images`
        (user-consented via the Gallery). Skips ids that already exist in the new
        location (never overwrites), then removes the emptied legacy dir."""
        legacy = self.legacy_generated_dir
        moved, skipped = 0, 0
        if not (legacy.exists() and legacy.is_dir()):
            return {"moved": 0, "skipped": 0, "legacy_present": False}
        for d in list(legacy.iterdir()):
            if not d.is_dir():
                continue
            dest = self.images_dir / d.name
            if dest.exists():
                skipped += 1
                continue
            try:
                shutil.move(str(d), str(dest))
                moved += 1
            except Exception as exc:
                logger.warning("Could not migrate asset %s: %r", d.name, exc)
                skipped += 1
        # Remove the legacy dir only if it's now empty.
        try:
            if not any(legacy.iterdir()):
                legacy.rmdir()
        except OSError:
            pass
        logger.info("Legacy asset merge: moved=%d skipped=%d", moved, skipped)
        return {"moved": moved, "skipped": skipped, "legacy_present": legacy.exists()}

    # ── Style profiles ────────────────────────────────────────────────────

    def style_dir(self, style_id: str) -> Path:
        d = self.styles_dir / style_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_style_profile(self, style_id: str, data: dict) -> Path:
        path = self.style_dir(style_id) / "profile.json"
        atomic_write_text(path, json.dumps(data, indent=2, default=str))
        return path

    def load_style_profile(self, style_id: str) -> dict | None:
        path = self.style_dir(style_id) / "profile.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_style_ids(self) -> list[str]:
        return sorted(
            d.name for d in self.styles_dir.iterdir()
            if d.is_dir() and (d / "profile.json").exists()
        )

    def delete_style(self, style_id: str) -> bool:
        d = self.style_dir(style_id)
        if d.exists():
            shutil.rmtree(d)
            return True
        return False

    def save_reference_image(self, style_id: str, filename: str, data: bytes) -> Path:
        path = self.style_dir(style_id) / "references" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def link_reference_image(self, style_id: str, filename: str, source_path: Path) -> Path:
        """Create a relative symlink to a local image instead of copying it."""
        import os
        link_path = self.style_dir(style_id) / "references" / filename
        link_path.parent.mkdir(parents=True, exist_ok=True)
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        # Use relative path so symlinks survive directory moves
        rel_target = os.path.relpath(source_path.resolve(), link_path.parent.resolve())
        link_path.symlink_to(rel_target)
        return link_path

    def list_reference_images(self, style_id: str) -> list[str]:
        refs_dir = self.style_dir(style_id) / "references"
        if not refs_dir.exists():
            return []
        return sorted(f.name for f in refs_dir.iterdir() if f.is_file())

    def get_reference_image_path(self, style_id: str, filename: str) -> Path | None:
        path = self.style_dir(style_id) / "references" / filename
        return path if path.exists() else None

    # ── Generated assets ──────────────────────────────────────────────────

    def generated_asset_dir(self, asset_id: str) -> Path:
        d = self.images_dir / asset_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_generated_image(self, asset_id: str, filename: str, data: bytes) -> Path:
        path = self.generated_asset_dir(asset_id) / filename
        path.write_bytes(data)
        return path

    def save_generation_metadata(self, asset_id: str, data: dict) -> Path:
        # Atomic write (temp-in-same-dir + os.replace): a concurrent reader never
        # sees a half-written metadata.json, and a crash mid-write leaves the
        # previous file intact. Callers that read-modify-write hold
        # asset_write_lock(asset_id) around the whole sequence (this method does
        # NOT take that lock — doing so would deadlock those callers).
        path = self.generated_asset_dir(asset_id) / "metadata.json"
        atomic_write_text(path, json.dumps(data, indent=2, default=str))
        return path

    def load_generation_metadata(self, asset_id: str) -> dict | None:
        path = self.generated_asset_dir(asset_id) / "metadata.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_generated_ids(self) -> list[str]:
        return sorted(
            d.name for d in self.images_dir.iterdir()
            if d.is_dir() and (d / "metadata.json").exists()
        )

    def get_generated_file_path(self, asset_id: str, filename: str) -> Path | None:
        path = self.generated_asset_dir(asset_id) / filename
        return path if path.exists() else None

    def delete_generated_asset(self, asset_id: str) -> bool:
        d = self.images_dir / asset_id
        if d.exists() and d.is_dir():
            shutil.rmtree(d)
            return True
        return False


store = LocalStore()
