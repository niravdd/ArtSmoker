"""Pydantic models for generation requests."""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    GAME_ASSET = "game_asset"
    MARKETING_BANNER = "marketing_banner"
    ICON = "icon"
    CHARACTER = "character"
    ENVIRONMENT = "environment"
    PHOTOREALISTIC = "photorealistic"


class ImageModel(str, Enum):
    """Known image models — kept for backward compatibility.

    New models added via the registry are accepted as plain strings
    by the GenerationRequest validator. This enum is NOT the source
    of truth — the model registry is.
    """
    SD35_LARGE = "sd35_large"
    STABLE_IMAGE_ULTRA = "stable_image_ultra"


def _is_valid_model_key(key: str) -> bool:
    """Check if a model key is valid — either a known enum or in the registry."""
    # Check enum first (fast path)
    try:
        ImageModel(key)
        return True
    except ValueError:
        pass
    # Check registry (for dynamically added models)
    try:
        from backend.services.model_registry import get_image_model
        return bool(get_image_model(key))
    except Exception:
        return False


class GenerationRequest(BaseModel):
    prompt: str
    original_prompt: str | None = None
    pre_composed: bool = False  # If True, prompt was already AI-composed — skip refinement
    moderation_original: str | None = None  # Pre-moderation-rewrite prompt
    style_id: str | None = None
    asset_type: AssetType = AssetType.PHOTOREALISTIC
    image_model: str = "sd35_large"  # Any valid registry key (not limited to ImageModel enum)
    quality: str | None = None  # Quality tier override (e.g. "standard", "premium"). None = model's default.
    region: str | None = None  # Override region for the model (None = use model's default)
    width: int = 1024
    height: int = 1024
    num_options: int = Field(default=5, ge=1, le=5)
    num_variations: int = Field(default=5, ge=1, le=5)
    # User-chosen base seed (None = server-random, the legacy behavior). Each
    # (option, variation) slot derives a deterministic distinct seed from it —
    # same base + same settings reproduce the same batch.
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    remove_background: bool = True
    generate_svg: bool = True
    upscale: bool = False
    negative_prompt: str = ""  # Carried from Compose step when pre_composed=True
    decomposed_data: dict | None = None  # From Prompt Designer — persisted to metadata
    recomposed_prompt: str | None = None  # From Prompt Designer recompose step
    vary_fields: dict | None = None  # Lock/vary overrides per field from PromptDesigner
    all_models: bool = False  # Generate with multiple models (all enabled or selected subset)
    selected_models: list[str] | None = None  # Specific model keys for multi-model generation
    model_optimized_prompts: bool = False  # Tailor prompts per model (only when all_models=True)
    ip_owned: bool = False
    ip_licensed: bool = False
    ui_lang: str = ""  # Frontend language selection — soft hint for prompt language detection
    # ── Reference-guided generation (Image Studio "Reference-guided" tab) ──
    # 1–3 base64-encoded reference images the user supplies to guide generation.
    # reference_mode: "match" = pixel-faithful edit via a deployed custom model
    # (e.g. Qwen-Image-Edit); "inspired" = vision-LLM reads the images + prompt,
    # writes an enhanced prompt, and a standard text-to-image model generates.
    # Empty reference_images → normal text-to-image (the existing flow).
    reference_images: list[str] | None = None
    reference_mode: str = "inspired"  # "match" | "inspired"
    # Captured server-side (the user's raw Step-2 instruction) BEFORE body.prompt is
    # replaced by the edit/enhanced prompt, so an Image-Inspiration job can restore
    # the original instruction into the Reference Studio on Gallery reload.
    reference_prompt: str = ""
    # "Inspired" mode enhanced prompts, one per option. The frontend sends these
    # when the user PREVIEWED (and possibly edited) the interpretations — the
    # backend then uses them verbatim (no second vision call). Also populated
    # server-side by _prepare_reference_generation when the vision analysis runs
    # at generate time, so both the single-model and all-models pipelines read
    # the final option concepts from ONE place.
    reference_enhanced_prompts: list[str] | None = None
    # "Remix" mode strengths, one per option (the strength ladder — what the UI
    # shows is exactly what runs). Each is Stability image-to-image strength:
    # lower = closer to the reference. Clamped server-side to [0.05, 0.95].
    reference_strengths: list[float] | None = None

    @field_validator("image_model")
    @classmethod
    def validate_image_model(cls, v):
        if v == "all_models":
            return v  # Special value for all-models mode, not a real model
        if not _is_valid_model_key(v):
            raise ValueError(f"Unknown image model: '{v}'. Must be a key in the model registry.")
        return v


class PromptRefineRequest(BaseModel):
    prompt: str
    style_id: str | None = None
    asset_type: AssetType = AssetType.PHOTOREALISTIC
    image_model: str | None = None
