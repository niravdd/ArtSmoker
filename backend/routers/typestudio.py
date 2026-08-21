"""Type Studio router — composite text onto images or generate standalone text graphics.

Uses Claude as a creative director to design text layouts, and Pillow to render
the final composited image with effects (shadow, outline, glow).
"""

import io
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from backend.config import settings
from backend.services.bedrock_client import invoke_llm
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/type-studio", tags=["type-studio"])

# ── Pydantic models ───────────────────────────────────────────────────────

class TextLine(BaseModel):
    text: str
    font: str | None = None
    position: str = "center"


class TypeStudioRequest(BaseModel):
    source_image_id: str | None = None
    style_id: str | None = None
    lines: list[TextLine] = Field(..., min_length=1)
    style_note: str | None = None
    num_options: int = Field(default=1, ge=1, le=5)
    llm_complexity: str = "complex"  # "fast" or "complex" — which LLM category to use for layout
    remove_background: bool = False
    generate_svg: bool = True
    upscale: bool = False


class LayoutEffect(BaseModel):
    """Individual effect within a layout line (shadow, outline, glow)."""
    pass


class LayoutLine(BaseModel):
    text: str
    x: int
    y: int
    font_size: int = 48
    color: str = "#FFFFFF"
    font: str | None = None
    anchor: str = "mm"  # Pillow text anchor: "mm"=middle-middle, "lt"=left-top, etc.
    effects: dict = Field(default_factory=dict)


class LayoutSpec(BaseModel):
    lines: list[LayoutLine]
    canvas_width: int = 1024
    canvas_height: int = 1024


class FontInfo(BaseModel):
    name: str
    display_name: str = ""
    source: str  # "style", "global", or "system"
    path: str = ""  # URL path for serving (for non-system fonts)


class FontListResponse(BaseModel):
    fonts: list[FontInfo]


# ── Font helpers ──────────────────────────────────────────────────────────

GLOBAL_FONTS_DIR = settings.data_dir / "fonts"

# System font directories (macOS + Linux)
_SYSTEM_FONT_DIRS = [
    Path("/System/Library/Fonts/Supplemental"),  # macOS supplemental
    Path("/Library/Fonts"),                       # macOS all-users
    Path.home() / "Library/Fonts",               # macOS current user
    Path("/usr/share/fonts"),                     # Linux
    Path("/usr/local/share/fonts"),               # Linux local
    Path.home() / ".fonts",                       # Linux user
]

_FONT_EXTENSIONS = {".ttf", ".otf"}


def _font_display_name(filename: str) -> str:
    """Turn a font filename into a readable display name."""
    name = Path(filename).stem
    # Split camelCase and add spaces
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    name = re.sub(r'[-_]+', ' ', name)
    return name.strip()


def _get_font_dirs(style_id: str | None = None) -> list[tuple[Path, str]]:
    """Return a list of (directory, source_label) pairs to search for fonts."""
    dirs: list[tuple[Path, str]] = []
    if style_id:
        style_fonts = settings.styles_dir / style_id / "fonts"
        if style_fonts.is_dir():
            dirs.append((style_fonts, "style"))
    if GLOBAL_FONTS_DIR.is_dir():
        dirs.append((GLOBAL_FONTS_DIR, "global"))
    return dirs


def _resolve_font(font_name: str | None, style_id: str | None = None, size: int = 48) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Resolve a font name to a Pillow ImageFont, falling back to default."""
    if not font_name or font_name == "default":
        return ImageFont.load_default()

    # Check style-specific and global font directories
    for font_dir, _source in _get_font_dirs(style_id):
        font_path = font_dir / font_name
        if font_path.is_file():
            try:
                return ImageFont.truetype(str(font_path), size)
            except (OSError, IOError) as exc:
                logger.warning("Failed to load font %s: %s", font_path, exc)

    # Check system font directories
    for sys_dir in _SYSTEM_FONT_DIRS:
        font_path = sys_dir / font_name
        if font_path.is_file():
            try:
                return ImageFont.truetype(str(font_path), size)
            except (OSError, IOError) as exc:
                logger.warning("Failed to load system font %s: %s", font_path, exc)

    logger.warning("Font '%s' not found, using default.", font_name)
    return ImageFont.load_default()


# ── Claude layout prompt ──────────────────────────────────────────────────

def _build_layout_prompt(
    request: TypeStudioRequest,
    canvas_width: int,
    canvas_height: int,
    style_guide: str | None = None,
) -> str:
    """Build the prompt asking Claude to act as a creative director for text layout."""
    lines_desc = "\n".join(
        f'  - Text: "{line.text}", Font: {line.font}, Position hint: {line.position}'
        for line in request.lines
    )

    has_image = request.source_image_id is not None
    image_context = (
        "The text will be composited onto an existing image. "
        "Choose positions that avoid covering important visual content. "
        "Use colors that contrast well with the image."
        if has_image
        else "This is standalone text on a transparent background. "
        "Center the composition and use bold, eye-catching colors."
    )

    style_section = ""
    if style_guide:
        style_section = f"\nStyle guide from the art style profile:\n{style_guide}\n"
    if request.style_note:
        style_section += f"\nAdditional style direction: {request.style_note}\n"

    num_opts = request.num_options

    layout_example = f"""{{
  "lines": [
    {{
      "text": "THE TEXT",
      "x": {canvas_width // 2},
      "y": 80,
      "font_size": 72,
      "color": "#FFD700",
      "font": "default",
      "anchor": "mm",
      "effects": {{
        "shadow": {{"offset": [3, 3], "color": "#000000", "opacity": 0.6}},
        "outline": {{"width": 2, "color": "#8B4513"}},
        "glow": {{"radius": 5, "color": "#FFD700", "opacity": 0.4}}
      }}
    }}
  ],
  "canvas_width": {canvas_width},
  "canvas_height": {canvas_height}
}}"""

    # Output-format instructions come from the editable registry templates; the
    # code injects the computed JSON schema example (it carries canvas pixel
    # values) and the option count.
    from backend.services.prompt_templates import get_template as _get_tmpl
    if num_opts > 1:
        output_instructions = _get_tmpl('typestudio_layout_output_multi').format(
            num_options=num_opts, layout_example=layout_example,
        )
    else:
        output_instructions = _get_tmpl('typestudio_layout_output_single').format(
            layout_example=layout_example,
        )

    return _get_tmpl('typestudio_layout').format(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        image_context=image_context,
        style_section=style_section,
        lines_desc=lines_desc,
        output_instructions=output_instructions,
    )


def _parse_layout_response(response_text: str, expect_multiple: bool = False) -> list[LayoutSpec]:
    """Parse Claude's JSON response into LayoutSpec(s), handling markdown fences.

    Returns a list of LayoutSpec objects. If expect_multiple is True, parses
    a JSON array; otherwise parses a single object and wraps in a list.
    """
    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.error("Failed to parse Claude layout response: %s\nResponse: %s", exc, response_text[:500])
        raise HTTPException(502, detail=f"AI returned invalid layout JSON: {exc}") from exc

    try:
        if isinstance(data, list):
            return [LayoutSpec(**item) for item in data]
        else:
            return [LayoutSpec(**data)]
    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.error("Layout spec validation failed: %s\nData: %s", exc, data)
        raise HTTPException(502, detail=f"Invalid layout spec from AI: {exc}") from exc


# ── Rendering engine ──────────────────────────────────────────────────────

def _hex_to_rgba(hex_color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    """Convert a hex color string to an RGBA tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(opacity * 255)
    return (r, g, b, a)


def _render_text_shadow(
    canvas: Image.Image,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    shadow_cfg: dict,
    anchor: str = "mm",
) -> None:
    """Render a drop shadow for text."""
    offset = shadow_cfg.get("offset", [3, 3])
    color = shadow_cfg.get("color", "#000000")
    opacity = shadow_cfg.get("opacity", 0.6)

    shadow_color = _hex_to_rgba(color, opacity)
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_layer)
    draw.text((x + offset[0], y + offset[1]), text, font=font, fill=shadow_color, anchor=anchor)
    canvas.alpha_composite(shadow_layer)


def _render_text_outline(
    canvas: Image.Image,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    outline_cfg: dict,
    anchor: str = "mm",
) -> None:
    """Render an outline around text by drawing at small offsets."""
    width = outline_cfg.get("width", 2)
    color = outline_cfg.get("color", "#000000")

    outline_color = _hex_to_rgba(color)
    outline_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(outline_layer)

    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color, anchor=anchor)

    canvas.alpha_composite(outline_layer)


def _render_text_glow(
    canvas: Image.Image,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    glow_cfg: dict,
    anchor: str = "mm",
) -> None:
    """Render a glow effect by drawing blurred text behind the main text."""
    radius = glow_cfg.get("radius", 5)
    color = glow_cfg.get("color", "#FFFFFF")
    opacity = glow_cfg.get("opacity", 0.4)

    glow_color = _hex_to_rgba(color, opacity)
    glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    draw.text((x, y), text, font=font, fill=glow_color, anchor=anchor)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=radius))
    canvas.alpha_composite(glow_layer)


def _render_layout(
    layout: LayoutSpec,
    source_image: Image.Image | None = None,
    style_id: str | None = None,
) -> bytes:
    """Render the text layout onto an image canvas. Returns PNG bytes."""
    # Create or use base canvas
    if source_image is not None:
        # Composite onto the source image
        canvas = source_image.convert("RGBA")
    else:
        # Standalone text on transparent background
        canvas = Image.new("RGBA", (layout.canvas_width, layout.canvas_height), (0, 0, 0, 0))

    for line in layout.lines:
        font = _resolve_font(line.font, style_id=style_id, size=line.font_size)
        effects = line.effects
        anchor = line.anchor or "mm"

        # 1. Glow (rendered first, behind everything)
        if "glow" in effects:
            _render_text_glow(canvas, line.text, line.x, line.y, font, effects["glow"], anchor)

        # 2. Shadow (behind outline and main text)
        if "shadow" in effects:
            _render_text_shadow(canvas, line.text, line.x, line.y, font, effects["shadow"], anchor)

        # 3. Outline (behind main text)
        if "outline" in effects:
            _render_text_outline(canvas, line.text, line.x, line.y, font, effects["outline"], anchor)

        # 4. Main text on top
        text_color = _hex_to_rgba(line.color)
        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        draw.text((line.x, line.y), line.text, font=font, fill=text_color, anchor=anchor)
        canvas.alpha_composite(text_layer)

    # Export as PNG bytes
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


# ── Shared pipeline logic ─────────────────────────────────────────────────

def _load_source_image(source_image_id: str) -> tuple[Image.Image, bytes]:
    """Load a source image from the gallery by asset ID. Returns (PIL Image, raw bytes)."""
    path = store.get_generated_file_path(source_image_id, "asset.png")
    if path is None:
        raise HTTPException(404, detail=f"Source image '{source_image_id}' not found in gallery.")
    image_bytes = path.read_bytes()
    image = Image.open(io.BytesIO(image_bytes))
    return image, image_bytes


def _load_style_guide(style_id: str) -> str | None:
    """Load a style profile's generation hints for Claude context."""
    profile = store.load_style_profile(style_id)
    if profile is None:
        logger.warning("Style '%s' not found, proceeding without style guide.", style_id)
        return None

    parts = []
    if profile.get("generation_hints"):
        parts.append(profile["generation_hints"])

    analyzed = profile.get("analyzed_style", {})
    if analyzed.get("palette"):
        parts.append(f"Color palette: {', '.join(analyzed['palette'])}")
    if analyzed.get("mood"):
        parts.append(f"Mood: {analyzed['mood']}")
    if analyzed.get("rendering"):
        parts.append(f"Rendering style: {analyzed['rendering']}")

    return "\n".join(parts) if parts else None


def _get_layouts_from_llm(
    request: TypeStudioRequest,
    canvas_width: int,
    canvas_height: int,
    style_guide: str | None,
    image_bytes: bytes | None,
) -> list[LayoutSpec]:
    """Call the configured LLM to design text layout(s) and return parsed LayoutSpec list.

    The LLM used is determined by request.llm_complexity — reads from the
    registry categories (fast_llm or complex_llm). User chooses in the UI.
    """
    prompt = _build_layout_prompt(request, canvas_width, canvas_height, style_guide)

    images = [image_bytes] if image_bytes else None
    # Higher temperature for multiple options to get creative diversity
    temp = 0.9 if request.num_options > 1 else 0.7
    complexity = request.llm_complexity if request.llm_complexity in ("fast", "complex") else "complex"
    response_text = invoke_llm(
        prompt,
        complexity=complexity,
        images=images,
        max_tokens=8192 if request.num_options > 1 else 4096,
        temperature=temp,
    )

    layouts = _parse_layout_response(response_text, expect_multiple=request.num_options > 1)
    return layouts[:request.num_options]


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/preview")
async def preview(request: TypeStudioRequest):
    """Generate a text-composited image and save it as a new gallery asset."""
    from backend.services.telemetry import track_type_generation, track_type_cost
    from backend.services.cost_tracker import reset_costs, get_total_cost
    reset_costs()

    # 1. Load source image if provided
    source_image: Image.Image | None = None
    image_bytes: bytes | None = None
    canvas_width = settings.default_image_width
    canvas_height = settings.default_image_height

    if request.source_image_id:
        source_image, image_bytes = _load_source_image(request.source_image_id)
        canvas_width, canvas_height = source_image.size

    # 2. Load style guide if provided
    style_guide: str | None = None
    style_snapshot: dict | None = None
    if request.style_id:
        style_guide = _load_style_guide(request.style_id)
        profile = store.load_style_profile(request.style_id)
        if profile:
            style_snapshot = {
                "name": profile.get("name"),
                "description": profile.get("description"),
                "generation_hints": profile.get("generation_hints"),
            }

    # 3. Get layouts from Claude (1 or more options)
    layouts = _get_layouts_from_llm(
        request, canvas_width, canvas_height, style_guide, image_bytes,
    )

    # 4. Render and save each option
    text_slug = re.sub(r"[^\w\s-]", "", request.lines[0].text.lower().strip())
    text_slug = re.sub(r"[\s_]+", "-", text_slug).strip("-")[:30]
    batch_id = f"text_{uuid4()}"
    now = datetime.utcnow().isoformat()

    options = []
    for i, layout in enumerate(layouts):
        # Re-create source image for each render (fresh copy)
        src_img = source_image.copy() if source_image else None
        rendered_bytes = _render_layout(layout, src_img, request.style_id)

        asset_id = f"{batch_id}_opt{i}" if len(layouts) > 1 else batch_id
        png_filename = f"{text_slug or 'text'}_opt{i + 1}.png" if len(layouts) > 1 else f"{text_slug or 'text'}_type-studio.png"

        # Apply post-processing
        from backend.services.post_processor import process_asset as _process_asset
        svg_out = store.generated_asset_dir(asset_id) / "asset.svg" if request.generate_svg else None
        final_bytes, svg_path = _process_asset(
            image_bytes=rendered_bytes,
            enhanced_prompt="",
            remove_bg=request.remove_background,
            do_upscale=request.upscale,
            do_svg=request.generate_svg,
            svg_output_path=svg_out,
        )
        store.save_generated_image(asset_id, "asset.png", final_bytes)

        svg_url = f"/api/gallery/{asset_id}/svg" if svg_path and svg_path.exists() else None
        svg_filename = f"{text_slug or 'text'}_opt{i + 1}.svg" if svg_url and len(layouts) > 1 else (f"{text_slug or 'text'}_type-studio.svg" if svg_url else None)

        metadata = {
            "id": asset_id,
            "batch_id": batch_id,
            "option_index": i,
            "type": "type-studio",
            "source_image_id": request.source_image_id,
            "style_id": request.style_id,
            "style_snapshot": style_snapshot,
            "style_note": request.style_note,
            "lines": [line.model_dump() for line in request.lines],
            "layout_spec": layout.model_dump(),
            "asset_type": "type_studio",
            "prompt": " | ".join(line.text for line in request.lines),
            "width": canvas_width,
            "height": canvas_height,
            "remove_background": request.remove_background,
            "generate_svg": request.generate_svg,
            "upscale": request.upscale,
            "png_path": f"/api/gallery/{asset_id}/png",
            "svg_path": svg_url,
            "png_filename": png_filename,
            "svg_filename": svg_filename,
            "created_at": now,
        }
        store.save_generation_metadata(asset_id, metadata)
        options.append({
            "id": asset_id,
            "option_index": i,
            "png_url": f"/api/gallery/{asset_id}/png",
            "svg_url": svg_url,
            "png_filename": png_filename,
            "svg_filename": svg_filename,
            "layout": layout.model_dump(),
        })

    # 5. Track cost and return result
    track_type_generation()
    track_type_cost(cost_usd=get_total_cost())

    return {
        "id": batch_id,
        "num_options": len(options),
        "options": options,
        "metadata": options[0] if len(options) == 1 else {"batch_id": batch_id, "num_options": len(options)},
    }


@router.get("/fonts", response_model=FontListResponse)
async def list_fonts(style_id: str | None = None):
    """List available fonts: style-specific first, then global, then system.

    System fonts are scanned from standard OS directories.
    Style/global fonts are served via /api/type-studio/font-file/ for browser preview.
    """
    fonts: list[FontInfo] = []
    seen: set[str] = set()

    # 1. Style-specific and global fonts (served by us for preview)
    for font_dir, source in _get_font_dirs(style_id):
        if not font_dir.is_dir():
            continue
        for font_file in sorted(font_dir.iterdir()):
            if font_file.is_file() and font_file.suffix.lower() in _FONT_EXTENSIONS:
                if font_file.name not in seen:
                    seen.add(font_file.name)
                    serve_path = f"/api/type-studio/font-file/{source}/{font_file.name}"
                    fonts.append(FontInfo(
                        name=font_file.name,
                        display_name=_font_display_name(font_file.name),
                        source=source,
                        path=serve_path,
                    ))

    # 2. System fonts
    for sys_dir in _SYSTEM_FONT_DIRS:
        if not sys_dir.is_dir():
            continue
        try:
            for font_file in sorted(sys_dir.iterdir()):
                if font_file.is_file() and font_file.suffix.lower() in _FONT_EXTENSIONS:
                    if font_file.name not in seen:
                        seen.add(font_file.name)
                        fonts.append(FontInfo(
                            name=font_file.name,
                            display_name=_font_display_name(font_file.name),
                            source="system",
                            path="",  # system fonts don't need serving
                        ))
        except PermissionError:
            continue

    return FontListResponse(fonts=fonts)


@router.get("/font-file/{source}/{filename}")
async def serve_font_file(source: str, filename: str):
    """Serve a font file for browser preview (@font-face).

    Source is either 'global' or a style_id.
    """
    from fastapi.responses import FileResponse

    # Validate source and filename to prevent path traversal
    if "/" in source or "\\" in source or ".." in source:
        raise HTTPException(400, detail="Invalid source parameter")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, detail="Invalid filename parameter")

    if source == "global":
        path = GLOBAL_FONTS_DIR / filename
    else:
        path = settings.styles_dir / source / "fonts" / filename

    # Ensure resolved path stays within expected directories
    resolved = path.resolve()
    if source == "global":
        if not str(resolved).startswith(str(GLOBAL_FONTS_DIR.resolve())):
            raise HTTPException(400, detail="Invalid font path")
    else:
        if not str(resolved).startswith(str(settings.styles_dir.resolve())):
            raise HTTPException(400, detail="Invalid font path")

    if not path.is_file():
        raise HTTPException(404, detail=f"Font file not found: {filename}")

    media = "font/ttf" if filename.lower().endswith(".ttf") else "font/otf"
    return FileResponse(path, media_type=media)


@router.post("/suggest")
async def suggest(request: TypeStudioRequest):
    """Return Claude's layout suggestion without rendering.

    Same pipeline as /preview steps 1-3, but skips rendering and saving.
    Useful for the frontend to preview the layout before committing.
    """
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    reset_costs()  # scope the layout-LLM cost to THIS request
    try:
        # 1. Load source image if provided
        image_bytes: bytes | None = None
        canvas_width = settings.default_image_width
        canvas_height = settings.default_image_height

        if request.source_image_id:
            source_image, image_bytes = _load_source_image(request.source_image_id)
            canvas_width, canvas_height = source_image.size

        # 2. Load style guide if provided
        style_guide: str | None = None
        if request.style_id:
            style_guide = _load_style_guide(request.style_id)

        # 3. Get layouts from Claude (no rendering)
        layouts = _get_layouts_from_llm(
            request, canvas_width, canvas_height, style_guide, image_bytes,
        )

        return {
            "layouts": [l.model_dump() for l in layouts],
            "num_options": len(layouts),
            "canvas_width": canvas_width,
            "canvas_height": canvas_height,
        }
    finally:
        # Layout suggestion is a standalone LLM call — report its cost (was untracked).
        track_aux_llm_cost("type_suggest", get_total_cost(), studio="type_studio")
