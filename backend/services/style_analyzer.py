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
You are an expert art director and visual style analyst specializing in game
asset production. Carefully study ALL the reference images provided. These are
individual game asset sprites — typically isolated objects on transparent
backgrounds. Analyze the RENDERING STYLE, not the composition (since each
image shows a single object).

{user_guidance_section}

Analyze these attributes by examining the full set of images together:

- **perspective**: Camera/viewpoint used consistently across assets (e.g.
  "isometric 30-degree dimetric", "top-down orthographic", "side-scroll",
  "3/4 top-down"). Be specific about the angle.
- **palette**: 5-8 dominant hex colors, grouped by material where possible
  (e.g. "stone: #A0926B, wood: #8B7355, metal: #4A4A4A, accent: #C44B3F").
- **rendering**: Precise rendering technique. Not just "3D" but specifics like
  "pre-rendered 3D to 2D sprites with soft ambient occlusion and subtle surface
  textures (visible stone mortar, wood grain)". Mention texture detail level.
- **line_weight**: How edges and forms are defined (e.g. "no outlines, form
  defined by material shading and soft shadow edges" or "thin dark outlines
  with interior detail lines").
- **mood**: Overall emotional/thematic feel (e.g. "dark medieval dungeon,
  slightly whimsical miniature scale" or "bright cheerful cartoon city").
- **scale**: Proportions and sizing system (e.g. "chunky miniature proportions,
  ~128px isometric tile grid, slightly exaggerated toylike scale").
- **background**: Background treatment (e.g. "transparent with semi-transparent
  drop shadow at base, consistent 45-degree shadow angle").
- **materials**: Key material rendering details — how stone, wood, metal,
  fabric etc. are differentiated visually. This is crucial for generating
  new assets that match.
- **detail_level**: Level of surface detail (e.g. "medium — visible mortar
  lines on stone, wood plank grain, simplified metal reflections, no fine
  ornamentation").

Return ONLY valid JSON matching this exact schema (no markdown fences, no extra text):
{{
  "perspective": "...",
  "palette": ["#hex1", "#hex2", ...],
  "rendering": "...",
  "line_weight": "...",
  "mood": "...",
  "scale": "...",
  "background": "...",
  "materials": "...",
  "detail_level": "..."
}}
"""

_HINTS_PROMPT_TEMPLATE = """\
You are a concise prompt-engineering expert for AI image generation. Given the
analyzed visual style below, write generation hints that an AI image model
MUST follow to produce assets matching this exact style.

Analyzed style (from AI vision analysis of reference images):
{style_json}

{user_guidance_section}

Write a SINGLE PARAGRAPH (max 200 words) that covers ALL of these in order:
1. Perspective/camera angle (be specific — "isometric 30-degree dimetric" not just "isometric")
2. Rendering technique with material specifics (how stone, wood, metal look)
3. Color palette (name the key material colors)
4. Proportions and scale (chunky? realistic? miniature?)
5. Edge treatment (outlines? shading-defined? soft edges?)
6. Shadow and lighting (direction, softness, transparency)
7. Detail level (what surface details are visible, what is simplified)
8. Background treatment

The hints should be specific enough that an image model can produce an asset
that seamlessly blends with the existing reference images. Generic descriptions
like "isometric, earth tones" are NOT sufficient. Be precise about materials,
proportions, and rendering details.

Respond with ONLY the hints paragraph — no preamble, no bullet points.
"""


# ── Cohesion check prompt (Phase 1 — fast, cheap via Sonnet) ──────────────

_COHESION_CHECK_PROMPT = """\
You are a visual style analyst. Look at these reference images and determine
whether they represent a SINGLE cohesive visual style or a DIVERSE collection
with multiple themes/styles.

Respond with ONLY a JSON object (no markdown fences):
{{
  "cohesion": "high" | "medium" | "low",
  "reasoning": "One sentence explaining why",
  "common_patterns": "What is consistent across ALL images (if anything)",
  "variation_areas": "What varies between images (if anything)"
}}

- "high": All images share the same rendering style, perspective, palette, and
  design language. Variations are only in subject matter, not visual treatment.
- "medium": Images share structural patterns (sizing, composition, quality level)
  but themes/palettes differ (e.g. multiple event themes for the same game).
- "low": Images are from completely different visual styles with little in common.
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

    # ── Phase 1: Cohesion check (fast, cheap — Sonnet with 8 images) ──
    total_count = len(all_images)
    sample_count = len(image_bytes_list)

    cohesion_sample = image_bytes_list[:min(8, sample_count)]
    cohesion_info = ""
    try:
        logger.info("Phase 1: Checking cohesion for style '%s' with %d images (Sonnet).", style_id, len(cohesion_sample))
        cohesion_raw = invoke_claude(
            _COHESION_CHECK_PROMPT,
            complexity="fast",
            images=cohesion_sample,
            max_tokens=512,
            temperature=0.2,
        )
        # Parse cohesion result
        cleaned_coh = cohesion_raw.strip()
        if cleaned_coh.startswith("```"):
            cleaned_coh = cleaned_coh[cleaned_coh.index("\n") + 1:]
        if cleaned_coh.endswith("```"):
            cleaned_coh = cleaned_coh[:-3]
        cohesion_data = json.loads(cleaned_coh.strip())
        cohesion_level = cohesion_data.get("cohesion", "medium")
        cohesion_info = (
            f"=== COHESION ASSESSMENT (from pre-analysis) ===\n"
            f"Cohesion level: {cohesion_level}\n"
            f"Common patterns: {cohesion_data.get('common_patterns', 'N/A')}\n"
            f"Variation areas: {cohesion_data.get('variation_areas', 'N/A')}\n"
        )
        if cohesion_level == "low":
            cohesion_info += (
                "\nIMPORTANT: These images are diverse. Focus on extracting what IS "
                "consistent (production quality, sizing conventions, composition "
                "patterns, design language) rather than forcing a single palette or theme."
            )
        elif cohesion_level == "medium":
            cohesion_info += (
                "\nNOTE: These images share structural patterns but differ in theme. "
                "Extract the common design language and production standards. For "
                "palette, identify the overall color approach rather than specific colors."
            )
        logger.info("Phase 1 result for '%s': cohesion=%s", style_id, cohesion_level)
    except Exception as exc:
        logger.warning("Cohesion check failed for '%s', proceeding without: %s", style_id, exc)

    # ── Phase 2: Full analysis (Opus with all sampled images) ──
    guidance_parts = []
    if user_hints:
        guidance_parts.append(
            "=== ARTIST'S GUIDANCE ===\n"
            "The artist has provided the following description of this style. Use it\n"
            "to inform your analysis — it may describe intent, naming, or context\n"
            "that is not visible in the images alone:\n"
            f'"{user_hints}"'
        )
    if cohesion_info:
        guidance_parts.append(cohesion_info)
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
        "Phase 2: Analyzing %d/%d reference image(s) for style '%s' (user hints: %s) using Claude Opus.",
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
