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
    negative_prompt: str = ""
    image_model: str | None = None  # Actual model used (set in "All Models" mode)
    model_label: str | None = None  # Human-readable model name
    status: str = "success"  # "success", "moderation_blocked", "error"
    status_detail: str | None = None  # Error message or moderation reason
    variants: list[VariantResult] = Field(default_factory=list)


class GenerationResult(BaseModel):
    id: str
    prompt: str
    original_prompt: str | None = None
    negative_prompt: str | None = None
    style_id: str | None = None
    asset_type: str
    image_model: str  # Selected model (or "all_models" when all_models=True)
    width: int
    height: int
    num_options: int = 1
    num_variations: int = 1
    all_models: bool = False  # True when generated across all enabled models
    model_map: dict[int, str] | None = None  # option_index → model_key (All Models mode only)
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
