"""Application configuration — AWS model IDs, paths, defaults."""

from pathlib import Path
from pydantic_settings import BaseSettings

APP_VERSION = "1.9-20260629_05"

class Settings(BaseSettings):
    # ── AWS ───────────────────────────────────────────────────────────────
    aws_region_models: str = "us-west-2"
    aws_region_images: str = "us-east-1"
    aws_profile: str | None = None

    # Note: LLM model IDs are configured in model_registry.json (categories section).
    # No hardcoded model IDs here — everything comes from the registry.

    # ── Amazon Bedrock Mantle endpoint ────────────────────────────────────
    # The bedrock-mantle endpoint (OpenAI-compatible + Anthropic Messages APIs)
    # authenticates with a Bedrock bearer token, not SigV4. By default a
    # short-term token is derived from the active AWS credentials at runtime
    # (aws-bedrock-token-generator) — nothing to configure. To pin an explicit
    # key instead, set AWS_BEARER_TOKEN_BEDROCK in the environment; mantle_client
    # reads it directly. Mantle is used ONLY for models Converse can't reach
    # (e.g. OpenAI GPT-5.x); the Converse path needs no token.

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

    # Auto keep-warm: when true, submitting an inference job pins its endpoint
    # warm (MinCapacity=1) for DEFAULT_WARM_HOURS so dev iteration doesn't pay
    # repeated cold starts. DEFAULT OFF — an 8h pin per job is expensive and was
    # silently keeping GPU instances up. Endpoints now rely purely on the
    # scale-to-zero / scale-from-zero autoscaling policies; warm-pinning is an
    # explicit, opt-in action (the /keep-warm API still works on demand). Set
    # ARTSMOKER_AUTO_KEEP_WARM=true in .env to restore the old behavior.
    auto_keep_warm: bool = False

    # Deploy-time scale-in grace (minutes). A freshly-deployed endpoint has zero
    # traffic, so the scale-to-zero alarm trips ~1 min after it goes live and can
    # drain the instance BEFORE the user's first job runs (or mid-job). To avoid
    # that, when auto-scaling is first registered we pin MinCapacity=1 for this
    # window, then auto-revert to 0 (normal scale-to-zero resumes). The
    # ScaleInCooldown only gates the interval BETWEEN scale-ins, not this first
    # one — hence a dedicated grace. Set 0 to disable.
    deploy_scale_in_grace_minutes: int = 20

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
