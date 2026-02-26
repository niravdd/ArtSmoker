"""Style analysis service — uses Claude Opus vision to extract style profiles
from reference images, and Claude Sonnet to distil generation hints."""

import json
import logging
from pathlib import Path

from backend.models.style_profile import AnalyzedStyle
from backend.services.bedrock_client import invoke_claude
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

# ── Prompt templates ──────────────────────────────────────────────────────

_ANALYSIS_PROMPT = """\
You are an expert art director and visual style analyst. Carefully study the
reference images provided and extract a unified style profile as JSON.

Analyze the following attributes:
- **perspective**: The dominant camera/viewpoint (e.g. "top-down 3/4", "isometric",
  "side-scroll", "first-person", "flat 2D").
- **palette**: A list of 5-8 dominant hex color codes (e.g. ["#1a1a2e", "#e94560"]).
- **rendering**: The rendering technique (e.g. "cel-shaded", "pixel art",
  "watercolor", "vector flat", "realistic PBR").
- **line_weight**: Describe the line work (e.g. "thick black outlines",
  "no outlines", "thin sketch lines", "variable brush strokes").
- **mood**: The overall emotional feel (e.g. "dark and moody", "bright and playful",
  "serene pastoral", "gritty cyberpunk").
- **scale**: Relative scale of subjects (e.g. "close-up character portrait",
  "wide environment shot", "icon-sized micro detail").
- **background**: Background treatment (e.g. "transparent", "gradient wash",
  "detailed environment", "solid color").

Return ONLY valid JSON matching this exact schema (no markdown fences, no extra text):
{
  "perspective": "...",
  "palette": ["#hex1", "#hex2", ...],
  "rendering": "...",
  "line_weight": "...",
  "mood": "...",
  "scale": "...",
  "background": "..."
}
"""

_HINTS_PROMPT_TEMPLATE = """\
You are a concise prompt-engineering assistant. Given the analyzed visual style
below, write a single paragraph (max 120 words) of comma-separated generation
hints that an image model should follow to reproduce this style faithfully.

Analyzed style:
{style_json}

Respond with ONLY the hints paragraph — no preamble, no bullet points.
"""


# ── Public API ────────────────────────────────────────────────────────────

def analyze_style(style_id: str) -> AnalyzedStyle:
    """Analyze reference images for a style and return a structured profile.

    Uses Claude Opus (complexity="complex") with vision capabilities to examine
    all reference images stored under the given style_id.

    Args:
        style_id: The identifier of the style whose references should be analyzed.

    Returns:
        An AnalyzedStyle populated with the extracted attributes.

    Raises:
        FileNotFoundError: If the style has no reference images.
        ValueError: If Claude's response cannot be parsed as valid JSON.
    """
    # 1. Gather reference images from storage
    ref_filenames = store.list_reference_images(style_id)
    if not ref_filenames:
        raise FileNotFoundError(
            f"Style '{style_id}' has no reference images to analyze."
        )

    image_bytes_list: list[bytes] = []
    for filename in ref_filenames:
        img_path: Path | None = store.get_reference_image_path(style_id, filename)
        if img_path is None:
            logger.warning("Reference image not found on disk: %s/%s", style_id, filename)
            continue
        image_bytes_list.append(img_path.read_bytes())

    if not image_bytes_list:
        raise FileNotFoundError(
            f"Style '{style_id}' reference images listed but none readable on disk."
        )

    logger.info(
        "Analyzing %d reference image(s) for style '%s' using Claude Opus.",
        len(image_bytes_list),
        style_id,
    )

    # 2. Send images + analysis prompt to Claude Opus (complex)
    raw_response = invoke_claude(
        _ANALYSIS_PROMPT,
        complexity="complex",
        images=image_bytes_list,
        max_tokens=2048,
        temperature=0.3,
    )

    # 3. Parse the JSON response
    try:
        # Strip potential markdown fences if the model wraps them
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error(
            "Failed to parse style analysis JSON from Claude response: %s",
            raw_response[:500],
        )
        raise ValueError(
            f"Claude returned invalid JSON for style analysis: {exc}"
        ) from exc

    analyzed = AnalyzedStyle(**data)
    logger.info("Style analysis complete for '%s': %s", style_id, analyzed.model_dump())
    return analyzed


def generate_hints(style_id: str, analyzed_style: AnalyzedStyle) -> str:
    """Distil an AnalyzedStyle into a concise generation-hints string.

    Uses Claude Sonnet (complexity="fast") for quick, focused summarisation.

    Args:
        style_id: Style identifier (used for logging).
        analyzed_style: The previously analyzed style profile.

    Returns:
        A short, comma-separated paragraph of generation hints.
    """
    style_json = analyzed_style.model_dump_json(indent=2)
    prompt = _HINTS_PROMPT_TEMPLATE.format(style_json=style_json)

    logger.info("Generating hints for style '%s' using Claude Sonnet.", style_id)

    hints = invoke_claude(
        prompt,
        complexity="fast",
        max_tokens=512,
        temperature=0.5,
    )

    hints = hints.strip()
    logger.info("Generated hints for '%s': %s", style_id, hints[:120])
    return hints
