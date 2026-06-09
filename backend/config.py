"""Application configuration — AWS model IDs, paths, defaults."""

from pathlib import Path
from pydantic_settings import BaseSettings

APP_VERSION = "1.9-20260609_04"

class Settings(BaseSettings):
    # ── AWS ───────────────────────────────────────────────────────────────
    aws_region_models: str = "us-west-2"
    aws_region_images: str = "us-east-1"
    aws_profile: str | None = None

    # Note: LLM model IDs are configured in model_registry.json (categories section).
    # No hardcoded model IDs here — everything comes from the registry.

    # ── Paths ─────────────────────────────────────────────────────────────
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    styles_dir: Path = data_dir / "styles"
    generated_dir: Path = data_dir / "generated"
    video_dir: Path = data_dir / "video"

    # ── Telemetry ──────────────────────────────────────────────────────────
    telemetry_enabled: bool = True

    # ── Dev box ────────────────────────────────────────────────────────────
    # Marks this machine as a development box. When true, custom-model deploys
    # auto-bake hot-reload + keep-warm into the SageMaker container so a
    # hard-won instance survives dev iteration. Set via ARTSMOKER_DEV_MODE in
    # .env (loaded below). is_dev_mode() reads this OR the raw env var.
    dev_mode: bool = False

    # ── Generation defaults ───────────────────────────────────────────────
    default_image_width: int = 1024
    default_image_height: int = 1024
    max_reference_images: int = 100
    max_analysis_images: int = 20

    model_config = {
        "env_prefix": "ARTSMOKER_",
        # Load a local, gitignored .env so dev-box settings (e.g. dev_mode)
        # persist across server restarts without an inline env var. Use an
        # ABSOLUTE path (project root) so it loads regardless of the working
        # directory the server is launched from.
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


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
