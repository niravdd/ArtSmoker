"""Pydantic models for style profiles."""

from datetime import datetime
from pydantic import BaseModel, Field


class AnalyzedStyle(BaseModel):
    perspective: str = ""
    palette: list[str] = Field(default_factory=list)
    rendering: str = ""
    line_weight: str = ""
    mood: str = ""
    scale: str = ""
    background: str = "transparent"
    materials: str = ""
    detail_level: str = ""


class StyleProfile(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reference_images: list[str] = Field(default_factory=list)
    analyzed_style: AnalyzedStyle = Field(default_factory=AnalyzedStyle)
    generation_hints: str = ""


class StyleProfileCreate(BaseModel):
    name: str
    description: str = ""
    generation_hints: str = ""


class StyleProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    analyzed_style: AnalyzedStyle | None = None
    generation_hints: str | None = None
