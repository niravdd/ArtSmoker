"""Pydantic models for generation requests."""

from enum import Enum
from pydantic import BaseModel, Field


class AssetType(str, Enum):
    GAME_ASSET = "game_asset"
    MARKETING_BANNER = "marketing_banner"
    ICON = "icon"
    CHARACTER = "character"
    ENVIRONMENT = "environment"


class ImageModel(str, Enum):
    NOVA_CANVAS = "nova_canvas"
    TITAN_IMAGE = "titan_image"
    SD35_LARGE = "sd35_large"
    STABLE_IMAGE_ULTRA = "stable_image_ultra"


class GenerationRequest(BaseModel):
    prompt: str
    original_prompt: str | None = None
    pre_composed: bool = False  # If True, prompt was already AI-composed — skip refinement
    moderation_original: str | None = None  # Pre-moderation-rewrite prompt
    style_id: str | None = None
    asset_type: AssetType = AssetType.GAME_ASSET
    image_model: ImageModel = ImageModel.NOVA_CANVAS
    width: int = 1024
    height: int = 1024
    num_options: int = Field(default=5, ge=1, le=5)
    num_variations: int = Field(default=5, ge=1, le=5)
    remove_background: bool = True
    generate_svg: bool = True
    upscale: bool = False
    ip_owned: bool = False
    ip_licensed: bool = False


class PromptRefineRequest(BaseModel):
    prompt: str
    style_id: str | None = None
    asset_type: AssetType = AssetType.GAME_ASSET
    image_model: str | None = None
