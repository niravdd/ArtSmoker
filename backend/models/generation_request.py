"""Pydantic models for generation requests."""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    GAME_ASSET = "game_asset"
    MARKETING_BANNER = "marketing_banner"
    ICON = "icon"
    CHARACTER = "character"
    ENVIRONMENT = "environment"


class ImageModel(str, Enum):
    """Known image models — kept for backward compatibility.

    New models added via the registry are accepted as plain strings
    by the GenerationRequest validator. This enum is NOT the source
    of truth — the model registry is.
    """
    NOVA_CANVAS = "nova_canvas"
    TITAN_IMAGE = "titan_image"
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
    asset_type: AssetType = AssetType.GAME_ASSET
    image_model: str = "nova_canvas"  # Any valid registry key (not limited to ImageModel enum)
    region: str | None = None  # Override region for the model (None = use model's default)
    width: int = 1024
    height: int = 1024
    num_options: int = Field(default=5, ge=1, le=5)
    num_variations: int = Field(default=5, ge=1, le=5)
    remove_background: bool = True
    generate_svg: bool = True
    upscale: bool = False
    negative_prompt: str = ""  # Carried from Compose step when pre_composed=True
    all_models: bool = False  # Generate with all enabled image models (one per option)
    model_optimized_prompts: bool = False  # Tailor prompts per model (only when all_models=True)
    ip_owned: bool = False
    ip_licensed: bool = False

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
    asset_type: AssetType = AssetType.GAME_ASSET
    image_model: str | None = None
