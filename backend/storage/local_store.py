"""Local filesystem storage with an S3-compatible interface for future migration."""

import json
import shutil
from pathlib import Path

from backend.config import settings


class LocalStore:
    """Thin wrapper around the local filesystem.

    Methods mirror a subset of S3 semantics so swapping to boto3 S3 later is
    straightforward.
    """

    def __init__(self) -> None:
        self.styles_dir = settings.styles_dir
        self.generated_dir = settings.generated_dir
        self.video_dir = settings.video_dir
        self.styles_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

    # ── Style profiles ────────────────────────────────────────────────────

    def style_dir(self, style_id: str) -> Path:
        d = self.styles_dir / style_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_style_profile(self, style_id: str, data: dict) -> Path:
        path = self.style_dir(style_id) / "profile.json"
        path.write_text(json.dumps(data, indent=2, default=str))
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
        d = self.generated_dir / asset_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_generated_image(self, asset_id: str, filename: str, data: bytes) -> Path:
        path = self.generated_asset_dir(asset_id) / filename
        path.write_bytes(data)
        return path

    def save_generation_metadata(self, asset_id: str, data: dict) -> Path:
        path = self.generated_asset_dir(asset_id) / "metadata.json"
        path.write_text(json.dumps(data, indent=2, default=str))
        return path

    def load_generation_metadata(self, asset_id: str) -> dict | None:
        path = self.generated_asset_dir(asset_id) / "metadata.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_generated_ids(self) -> list[str]:
        return sorted(
            d.name for d in self.generated_dir.iterdir()
            if d.is_dir() and (d / "metadata.json").exists()
        )

    def get_generated_file_path(self, asset_id: str, filename: str) -> Path | None:
        path = self.generated_asset_dir(asset_id) / filename
        return path if path.exists() else None

    def delete_generated_asset(self, asset_id: str) -> bool:
        d = self.generated_dir / asset_id
        if d.exists() and d.is_dir():
            shutil.rmtree(d)
            return True
        return False


store = LocalStore()
