"""Application configuration — AWS model IDs, paths, defaults."""

from pathlib import Path
from pydantic_settings import BaseSettings

APP_VERSION = "1.6-20260402_01"


class Settings(BaseSettings):
    # ── AWS ───────────────────────────────────────────────────────────────
    aws_region_models: str = "us-west-2"
    aws_region_images: str = "us-east-1"
    aws_profile: str | None = None

    # ── LLM fallbacks (used only if registry categories are empty) ────────
    claude_sonnet_model_id: str = "us.anthropic.claude-sonnet-4-6"
    claude_opus_model_id: str = "us.anthropic.claude-opus-4-6-v1"
    claude_fallback_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # ── Voice ─────────────────────────────────────────────────────────────
    nova_sonic_model_id: str = "amazon.nova-2-sonic-v1:0"

    # ── Paths ─────────────────────────────────────────────────────────────
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    styles_dir: Path = data_dir / "styles"
    generated_dir: Path = data_dir / "generated"
    video_dir: Path = data_dir / "video"

    # ── Telemetry ──────────────────────────────────────────────────────────
    telemetry_enabled: bool = True

    # ── Generation defaults ───────────────────────────────────────────────
    default_image_width: int = 1024
    default_image_height: int = 1024
    max_reference_images: int = 100
    max_analysis_images: int = 20

    model_config = {"env_prefix": "ARTSMOKER_"}


settings = Settings()

# Centralized set of supported image/asset extensions for import
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif",
    ".tga", ".ico", ".svg",
}

# 3D model formats that may contain embedded textures (extracted separately)
MODEL_EXTENSIONS_WITH_TEXTURES = {
    ".glb", ".gltf",
}
