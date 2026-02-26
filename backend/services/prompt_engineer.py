"""Prompt engineering service — refines user prompts into detailed, optimised
image-generation prompts using Claude Sonnet (fast) and Claude Opus (complex)."""

import logging

from backend.models.generation_request import AssetType
from backend.models.style_profile import StyleProfile
from backend.services.bedrock_client import invoke_claude

logger = logging.getLogger(__name__)

# ── Asset-type context snippets ───────────────────────────────────────────

_ASSET_TYPE_CONTEXT: dict[AssetType, str] = {
    AssetType.GAME_ASSET: (
        "This is a game asset. It must work well as a sprite or in-game element. "
        "Ensure clean edges suitable for background removal, consistent lighting, "
        "and a composition that works at various scales in a game UI or scene."
    ),
    AssetType.MARKETING_BANNER: (
        "This is a marketing banner. It should be visually striking, suitable for "
        "advertising. Leave clear space for headline text overlay. Use bold colors "
        "and dramatic composition that grabs attention at a glance."
    ),
    AssetType.ICON: (
        "This is an icon/app icon. It must be instantly recognisable at small sizes, "
        "use simple bold shapes, limited detail, and high contrast. Avoid fine text "
        "or intricate patterns that would be lost when scaled down."
    ),
    AssetType.CHARACTER: (
        "This is a character design. Show the character clearly with consistent "
        "proportions, well-defined silhouette, and personality conveyed through "
        "pose and expression. The character should read well against any background."
    ),
    AssetType.ENVIRONMENT: (
        "This is an environment / background scene. It should convey depth, "
        "atmosphere, and a sense of place. Include foreground, midground, and "
        "background layers. Lighting and mood are essential."
    ),
}

# ── Prompt templates ──────────────────────────────────────────────────────

_REFINE_PROMPT_TEMPLATE = """\
You are an expert image-generation prompt engineer. Your job is to take the
user's brief description and expand it into a detailed, richly descriptive
prompt optimised for an AI image generator (Amazon Nova Canvas / Titan Image).

Asset type context:
{asset_context}

{style_section}

User's original prompt:
"{user_prompt}"

Write a single, detailed image-generation prompt (100-200 words) that:
1. Incorporates the style hints (if provided) so the output matches the visual style.
2. Adds specific details about composition, lighting, color palette, and texture.
3. Specifies technical quality markers (e.g. "high detail", "clean edges",
   "professional quality").
4. Maintains the core intent of the user's original prompt.

Respond with ONLY the refined prompt — no preamble, no quotation marks, no
explanation.
"""

_MARKETING_PROMPT_TEMPLATE = """\
You are a senior creative director specialising in game marketing materials.
Craft a highly detailed image-generation prompt for a marketing banner.

{style_section}

User's brief:
"{user_prompt}"

Requirements:
- The banner must be visually striking and suitable for digital advertising.
- Include a clear focal point with dramatic lighting and rich color.
- Leave a well-defined "safe zone" on the left or right third for headline text overlay.
- Ensure the composition works at common banner aspect ratios (16:9, 3:1, 1:1).
- Incorporate any style hints so the banner is consistent with the game's visual identity.
- Specify professional quality markers: "high resolution", "polished", "publication ready".
- Mention specific lighting direction, color grading, and atmosphere.

Respond with ONLY the refined prompt — no preamble, no quotation marks, no
explanation.
"""


# ── Helpers ───────────────────────────────────────────────────────────────

def _build_style_section(style_profile: StyleProfile | None) -> str:
    """Build the style hints section for prompt templates."""
    if style_profile is None or not style_profile.generation_hints:
        return "Style hints: None provided — use your best artistic judgement."
    return (
        f"Style hints (follow these closely):\n"
        f"{style_profile.generation_hints}"
    )


# ── Public API ────────────────────────────────────────────────────────────

def refine_prompt(
    user_prompt: str,
    style_profile: StyleProfile | None,
    asset_type: AssetType,
) -> str:
    """Refine a user prompt into a detailed image-generation prompt.

    Uses Claude Sonnet (complexity="fast") for quick turnaround.

    Args:
        user_prompt: The user's brief description of what they want.
        style_profile: Optional style profile with generation_hints.
        asset_type: The type of asset being generated.

    Returns:
        A detailed, optimised prompt string ready for the image model.
    """
    asset_context = _ASSET_TYPE_CONTEXT.get(asset_type, "General-purpose image.")
    style_section = _build_style_section(style_profile)

    prompt = _REFINE_PROMPT_TEMPLATE.format(
        asset_context=asset_context,
        style_section=style_section,
        user_prompt=user_prompt,
    )

    logger.info(
        "Refining prompt for asset_type=%s, has_style=%s",
        asset_type.value,
        style_profile is not None,
    )

    refined = invoke_claude(
        prompt,
        complexity="fast",
        max_tokens=1024,
        temperature=0.7,
    )

    refined = refined.strip()
    logger.info("Refined prompt (%d chars): %s", len(refined), refined[:150])
    return refined


def refine_marketing_prompt(
    user_prompt: str,
    style_profile: StyleProfile | None,
) -> str:
    """Refine a user prompt into a marketing-banner-specific generation prompt.

    Uses Claude Opus (complexity="complex") for higher-quality creative output
    suited to marketing materials.

    Args:
        user_prompt: The user's brief description of the desired banner.
        style_profile: Optional style profile with generation_hints.

    Returns:
        A detailed marketing-banner prompt string.
    """
    style_section = _build_style_section(style_profile)

    prompt = _MARKETING_PROMPT_TEMPLATE.format(
        style_section=style_section,
        user_prompt=user_prompt,
    )

    logger.info("Refining marketing prompt, has_style=%s", style_profile is not None)

    refined = invoke_claude(
        prompt,
        complexity="complex",
        max_tokens=1536,
        temperature=0.7,
    )

    refined = refined.strip()
    logger.info("Refined marketing prompt (%d chars): %s", len(refined), refined[:150])
    return refined
