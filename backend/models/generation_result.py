"""Pydantic models for generation results."""

from datetime import datetime
from pydantic import BaseModel, Field


class GenerationResult(BaseModel):
    id: str
    prompt: str
    refined_prompt: str
    style_id: str | None = None
    asset_type: str
    image_model: str
    png_path: str
    svg_path: str | None = None
    width: int
    height: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GalleryItem(BaseModel):
    id: str
    prompt: str
    style_id: str | None = None
    asset_type: str
    png_url: str
    svg_url: str | None = None
    created_at: datetime
