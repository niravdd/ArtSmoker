"""Style analysis service — uses Claude Opus vision to extract style profiles
from reference images, and Claude Sonnet to distil generation hints."""

import hashlib
import json
import logging
import random
from pathlib import Path

from backend.config import settings
from backend.models.style_profile import AnalyzedStyle
from backend.services.bedrock_client import invoke_claude
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

# ── Prompt templates ──────────────────────────────────────────────────────

_ANALYSIS_PROMPT = """\
You are an expert art director and visual style analyst. Carefully study the
reference images provided and extract a unified style profile as JSON.

{user_guidance_section}

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
{{
  "perspective": "...",
  "palette": ["#hex1", "#hex2", ...],
  "rendering": "...",
  "line_weight": "...",
  "mood": "...",
  "scale": "...",
  "background": "..."
}}
"""

_HINTS_PROMPT_TEMPLATE = """\
You are a concise prompt-engineering assistant. Given the analyzed visual style
and the artist's own guidance below, write a single paragraph (max 120 words)
of comma-separated generation hints that an image model should follow to
reproduce this style faithfully.

Analyzed style (from AI vision analysis of reference images):
{style_json}

{user_guidance_section}

Your output should combine the objective visual analysis with the artist's
intent. The artist's guidance takes priority where it provides additional
context that the visual analysis alone might miss (e.g. the name of the style,
the intended use case, or the emotional tone).

Respond with ONLY the hints paragraph — no preamble, no bullet points.
"""


# ── Smart sampling ────────────────────────────────────────────────────────

def _smart_sample(
    images: list[tuple[str, bytes]],
    n: int,
) -> list[tuple[str, bytes]]:
    """Select a diverse representative subset of images for analysis.

    Strategy:
    1. Always include the first and last image (alphabetically).
    2. Sort remaining by file size and pick at evenly-spaced intervals.
       Different file sizes suggest different content/complexity, giving
       Claude a broader view of the style's range.
    3. Also ensure images from different "groups" (subdirectory prefixes
       in the filename) are represented when possible.
    """
    if len(images) <= n:
        return images

    selected: dict[str, tuple[str, bytes]] = {}

    # Always include first and last (alphabetically sorted by name)
    selected[images[0][0]] = images[0]
    selected[images[-1][0]] = images[-1]

    # Group by filename prefix (before underscore or first letter)
    # to ensure subdirectory diversity
    groups: dict[str, list[tuple[str, bytes]]] = {}
    for name, data in images:
        prefix = name.split("_")[0] if "_" in name else name[0].lower()
        groups.setdefault(prefix, []).append((name, data))

    # Pick one from each group first (round-robin)
    group_keys = sorted(groups.keys())
    for key in group_keys:
        if len(selected) >= n:
            break
        # Pick the median-sized image from each group
        group = sorted(groups[key], key=lambda x: len(x[1]))
        mid = group[len(group) // 2]
        if mid[0] not in selected:
            selected[mid[0]] = mid

    # Fill remaining slots by file-size diversity (evenly-spaced intervals)
    if len(selected) < n:
        remaining = [(name, data) for name, data in images if name not in selected]
        remaining.sort(key=lambda x: len(x[1]))
        needed = n - len(selected)
        step = max(1, len(remaining) // (needed + 1))
        for i in range(0, len(remaining), step):
            if len(selected) >= n:
                break
            name, data = remaining[i]
            if name not in selected:
                selected[name] = (name, data)

    result = list(selected.values())
    logger.info(
        "Smart sample: %d images selected from %d total (%d groups detected).",
        len(result), len(images), len(groups),
    )
    return result


# ── Public API ────────────────────────────────────────────────────────────

def analyze_style(style_id: str, user_hints: str = "") -> AnalyzedStyle:
    """Analyze reference images for a style and return a structured profile.

    Uses Claude Opus (complexity="complex") with vision capabilities to examine
    all reference images stored under the given style_id.

    Args:
        style_id: The identifier of the style whose references should be analyzed.
        user_hints: Optional user-provided generation hints to give Claude
                    additional context about the artist's intent.

    Returns:
        An AnalyzedStyle populated with the extracted attributes.

    Raises:
        FileNotFoundError: If the style has no reference images.
        ValueError: If Claude's response cannot be parsed as valid JSON.
    """
    ref_filenames = store.list_reference_images(style_id)
    if not ref_filenames:
        raise FileNotFoundError(
            f"Style '{style_id}' has no reference images to analyze."
        )

    # Read all available images with their sizes for smart sampling
    all_images: list[tuple[str, bytes]] = []
    for filename in ref_filenames:
        img_path: Path | None = store.get_reference_image_path(style_id, filename)
        if img_path is None:
            logger.warning("Reference image not found on disk: %s/%s", style_id, filename)
            continue
        all_images.append((filename, img_path.read_bytes()))

    if not all_images:
        raise FileNotFoundError(
            f"Style '{style_id}' reference images listed but none readable on disk."
        )

    # Smart sampling: if we have more images than the analysis limit,
    # select a diverse representative subset
    max_for_analysis = settings.max_analysis_images
    if len(all_images) > max_for_analysis:
        sampled = _smart_sample(all_images, max_for_analysis)
        logger.info(
            "Sampled %d/%d images for analysis of style '%s'.",
            len(sampled), len(all_images), style_id,
        )
        image_bytes_list = [img for _, img in sampled]
    else:
        image_bytes_list = [img for _, img in all_images]

    # Build the user guidance section
    total_count = len(all_images)
    sample_count = len(image_bytes_list)

    guidance_parts = []
    if user_hints:
        guidance_parts.append(
            "=== ARTIST'S GUIDANCE ===\n"
            "The artist has provided the following description of this style. Use it\n"
            "to inform your analysis — it may describe intent, naming, or context\n"
            "that is not visible in the images alone:\n"
            f'"{user_hints}"'
        )
    if sample_count < total_count:
        guidance_parts.append(
            f"=== NOTE ===\n"
            f"You are seeing {sample_count} representative images sampled from a "
            f"collection of {total_count} total reference images. The sample was "
            f"chosen to represent the full diversity of the style. Base your analysis "
            f"on these images as representative of the complete set."
        )

    guidance = "\n\n".join(guidance_parts)

    prompt = _ANALYSIS_PROMPT.format(user_guidance_section=guidance)

    logger.info(
        "Analyzing %d/%d reference image(s) for style '%s' (user hints: %s) using Claude Opus.",
        sample_count, total_count, style_id, bool(user_hints),
    )

    raw_response = invoke_claude(
        prompt,
        complexity="complex",
        images=image_bytes_list,
        max_tokens=2048,
        temperature=0.3,
    )

    # Parse the JSON response
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
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


def generate_hints(style_id: str, analyzed_style: AnalyzedStyle, user_hints: str = "") -> str:
    """Distil an AnalyzedStyle into a concise generation-hints string.

    Uses Claude Sonnet (complexity="fast") for quick, focused summarisation.
    Incorporates any user-provided hints so the output reflects both the
    objective visual analysis and the artist's stated intent.

    Args:
        style_id: Style identifier (used for logging).
        analyzed_style: The previously analyzed style profile.
        user_hints: Optional user-provided hints to incorporate.

    Returns:
        A short, comma-separated paragraph of generation hints.
    """
    style_json = analyzed_style.model_dump_json(indent=2)

    if user_hints:
        guidance = (
            "Artist's own guidance (incorporate this context into the hints):\n"
            f'"{user_hints}"\n'
        )
    else:
        guidance = "No additional artist guidance provided."

    prompt = _HINTS_PROMPT_TEMPLATE.format(
        style_json=style_json,
        user_guidance_section=guidance,
    )

    logger.info("Generating hints for style '%s' (user hints: %s) using Claude Sonnet.", style_id, bool(user_hints))

    hints = invoke_claude(
        prompt,
        complexity="fast",
        max_tokens=512,
        temperature=0.5,
    )

    hints = hints.strip()
    logger.info("Generated hints for '%s': %s", style_id, hints[:120])
    return hints
