"""Pydantic models for generation results."""

from datetime import datetime
from pydantic import BaseModel, Field


class VariantResult(BaseModel):
    id: str
    variant_index: int
    png_path: str
    svg_path: str | None = None
    png_filename: str = ""
    svg_filename: str | None = None


class OptionResult(BaseModel):
    option_index: int
    refined_prompt: str
    variants: list[VariantResult] = Field(default_factory=list)


class GenerationResult(BaseModel):
    id: str
    prompt: str
    original_prompt: str | None = None
    style_id: str | None = None
    asset_type: str
    image_model: str
    width: int
    height: int
    num_options: int = 1
    num_variations: int = 1
    options: list[OptionResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GalleryItem(BaseModel):
    id: str
    prompt: str
    style_id: str | None = None
    asset_type: str
    png_url: str
    svg_url: str | None = None
    created_at: datetime
