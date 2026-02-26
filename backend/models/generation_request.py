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


class GenerationRequest(BaseModel):
    prompt: str
    style_id: str | None = None
    asset_type: AssetType = AssetType.GAME_ASSET
    image_model: ImageModel = ImageModel.NOVA_CANVAS
    width: int = 1024
    height: int = 1024
    remove_background: bool = True
    generate_svg: bool = True
    upscale: bool = False


class PromptRefineRequest(BaseModel):
    prompt: str
    style_id: str | None = None
    asset_type: AssetType = AssetType.GAME_ASSET
