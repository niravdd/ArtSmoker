"""Prompt engineering service — refines user prompts into detailed, optimised
image-generation prompts using Claude Sonnet (fast) and Claude Opus (complex)."""

import json
import logging

from backend.models.generation_request import AssetType, ImageModel
from backend.models.style_profile import StyleProfile
from backend.services.bedrock_client import invoke_claude

logger = logging.getLogger(__name__)

# Prompt character limits per image model
_MODEL_PROMPT_LIMITS: dict[str, int] = {
    ImageModel.NOVA_CANVAS.value: 900,
    ImageModel.TITAN_IMAGE.value: 480,
    ImageModel.SD35_LARGE.value: 2000,
    ImageModel.STABLE_IMAGE_ULTRA.value: 2000,
}
_DEFAULT_PROMPT_LIMIT = 900


def get_prompt_limit(image_model: str | None = None) -> int:
    """Get the prompt character limit for a given image model."""
    return _MODEL_PROMPT_LIMITS.get(image_model, _DEFAULT_PROMPT_LIMIT)

# ── Asset-type context snippets ───────────────────────────────────────────

_ASSET_TYPE_CONTEXT: dict[AssetType, str] = {
    AssetType.GAME_ASSET: (
        "OUTPUT TYPE: In-game sprite / tile / object asset.\n"
        "COMPOSITION: Single object, centered, isolated on a clean or transparent "
        "background. No scene context — just the asset by itself.\n"
        "FRAMING: Straight-on or the style's canonical perspective (e.g. isometric "
        "if the style is isometric). Fill ~70-80% of the frame.\n"
        "TECHNICAL: Clean sharp edges for easy background removal. Consistent "
        "directional lighting (top-left default). No drop shadows on the ground. "
        "Must tile or compose well with other game assets at various scales.\n"
        "DO NOT: Include text, UI elements, multiple objects, or scene backgrounds."
    ),
    AssetType.MARKETING_BANNER: (
        "OUTPUT TYPE: Marketing / promotional banner backdrop (illustration only, NO TEXT).\n"
        "COMPOSITION: Full-scene illustration with dramatic composition. Reserve "
        "the left or right third as a clear, visually quiet 'safe zone' where text "
        "will be added later in a design tool. This zone should have low detail, "
        "muted tones, or subtle gradient — easy to overlay text onto. Strong focal "
        "point in the opposite area.\n"
        "FRAMING: Wide/cinematic aspect ratio feel even within a square canvas. "
        "Camera pulled back to show an environment or hero scene.\n"
        "TECHNICAL: Rich, saturated colors with dramatic lighting (rim light, "
        "volumetric rays, or golden hour). Polished, publication-ready quality. "
        "Subtle depth-of-field for visual hierarchy.\n"
        "DO NOT: Render any text, letters, words, titles, or typography in the image. "
        "Image generation models cannot produce readable text. The text-safe zone "
        "must be empty — the user will add text in post-production. Also do not "
        "leave the image sparse or icon-like. This must feel like a full illustration."
    ),
    AssetType.ICON: (
        "OUTPUT TYPE: App icon / UI icon / in-game button icon.\n"
        "COMPOSITION: Single, bold, instantly recognizable symbol or object. "
        "Centered with generous padding (~15% margin). Maximum simplicity.\n"
        "FRAMING: Front-facing or slight 3/4 tilt. Object fills the frame but "
        "leaves breathing room at edges. No background scene.\n"
        "TECHNICAL: Very limited detail — must read clearly at 64x64 pixels. "
        "High contrast between foreground and background. 3-5 colors maximum. "
        "Bold shapes, no thin lines, no small text, no intricate patterns.\n"
        "DO NOT: Add complexity, fine detail, or scene context. Think of app "
        "store icons or toolbar buttons."
    ),
    AssetType.CHARACTER: (
        "OUTPUT TYPE: Character design / character portrait.\n"
        "COMPOSITION: Full-body or 3/4-body character, slightly off-center for "
        "visual interest. Character faces the viewer or is angled at 3/4 view. "
        "Isolated on clean/transparent background.\n"
        "FRAMING: Character fills ~60-75% of the vertical frame. Include head-to "
        "toe (or head-to-knee for portraits). Leave space above the head.\n"
        "TECHNICAL: Strong, readable silhouette — the character should be "
        "identifiable from silhouette alone. Expressive pose conveying personality. "
        "Consistent lighting. Clear facial features and costume details.\n"
        "DO NOT: Crop limbs awkwardly, add background environments, or include "
        "multiple characters. Focus on ONE character with clear personality."
    ),
    AssetType.ENVIRONMENT: (
        "OUTPUT TYPE: Environment / background / landscape scene.\n"
        "COMPOSITION: Full scenic illustration with clear depth layers — "
        "foreground elements (close, detailed), midground (main subject area), "
        "and background (distant, atmospheric). Use leading lines or natural "
        "framing to guide the eye.\n"
        "FRAMING: Wide establishing shot. Camera at a natural vantage point. "
        "Horizon line at lower or upper third, not dead center.\n"
        "TECHNICAL: Strong atmospheric perspective (distant objects lighter/hazier). "
        "Rich environmental storytelling through details. Mood-setting lighting "
        "(time of day, weather). The scene should feel inhabitable and alive.\n"
        "DO NOT: Make it flat or icon-like. This should feel like a place you "
        "could step into. Include environmental detail and atmosphere."
    ),
}

# ── Prompt templates ──────────────────────────────────────────────────────

_REFINE_PROMPT_TEMPLATE = """\
You are an expert image-generation prompt engineer for game art. Your job is
to expand the user's description into a detailed prompt for an AI image model.

=== ASSET TYPE GUIDELINES (adapt, don't force) ===
{asset_context}

=== STYLE GUIDELINES ===
{style_section}

=== USER REQUEST ===
"{user_prompt}"

INSTRUCTIONS — follow in PRIORITY ORDER:

1. **USER INTENT IS KING.** The user's explicit words override everything else.
   If the user says "real-world like" but the style says "toylike", follow the user.
   If the user describes a scene but the asset type says "single object", describe
   the scene. Never contradict what the user explicitly asked for.

2. **Intelligently interpret the asset type.** The asset type is a GUIDE, not a
   rigid template. A "game asset" could be an isolated object (barrel, sword),
   a tileable panel (ceiling, floor), a UI element, or a complex prop. Read what
   the user is describing and apply the appropriate composition:
   - Isolated objects → center on transparent background
   - Tileable panels/textures → edge-to-edge, seamless feel
   - Complex props with detail → fill the frame, show the detail
   - Scenes/vistas → depth, atmosphere, layered composition

3. **Style guidelines enhance, not override.** Use the style's palette, rendering
   technique, and proportions to INFORM the output — but if the user's description
   calls for something different, follow the user.

4. Add specific details about lighting, materials, color, and quality that serve
   the user's vision.

CRITICAL: Output MUST be under {max_chars} characters. Be concise but descriptive.

Respond with ONLY the refined prompt — no preamble, no quotation marks.
"""

_MARKETING_PROMPT_TEMPLATE = """\
You are a senior creative director specialising in game marketing materials.
Craft a highly detailed image-generation prompt for a marketing banner BACKDROP.

{style_section}

User's brief:
"{user_prompt}"

Requirements:
- The banner must be a visually striking ILLUSTRATION ONLY — no text, no letters,
  no words, no typography of any kind. AI image models cannot render readable text.
- If the user mentions a title or text (like "CARNIVAL SAGA"), ignore it for the
  image prompt. Instead, leave a clean, visually quiet area where text can be
  overlaid later in a design tool.
- Include a clear focal point with dramatic lighting and rich color.
- Leave a well-defined "safe zone" on the left or right third — low detail, muted
  tones, suitable for text overlay in post-production.
- Ensure the composition works at common banner aspect ratios (16:9, 3:1, 1:1).
- Incorporate any style hints so the banner is consistent with the game's visual identity.
- Specify professional quality markers: "high resolution", "polished", "publication ready".
- Mention specific lighting direction, color grading, and atmosphere.

CRITICAL: The prompt MUST be under {max_chars} characters. NO TEXT IN THE IMAGE.

Respond with ONLY the refined prompt — no preamble, no quotation marks.
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


# ── Refusal detection ─────────────────────────────────────────────────────

_REFUSAL_INDICATORS = [
    "i'm sorry", "i cannot", "i can't", "i am unable", "i'm unable",
    "i apologize", "not able to generate", "can't generate",
    "cannot generate", "not appropriate", "against my guidelines",
    "raises concerns", "misinformation risk", "what i can offer instead",
    "here's an alternative", "instead, i can",
]


def _check_for_refusal(refined: str) -> bool:
    """Check if Claude's response is a refusal rather than a valid prompt."""
    lower = refined.lower()
    return any(indicator in lower for indicator in _REFUSAL_INDICATORS)


class PromptRefusalError(Exception):
    """Raised when Claude refuses to refine a prompt due to content concerns."""
    def __init__(self, reason: str, original_response: str):
        self.reason = reason
        self.original_response = original_response
        super().__init__(reason)


def _validate_refined_prompt(refined: str, user_prompt: str) -> str:
    """Validate the refined prompt is usable. Raises PromptRefusalError if not."""
    if _check_for_refusal(refined):
        # Extract Claude's reasoning (first 200 chars of the refusal)
        reason = refined[:300].strip()
        raise PromptRefusalError(
            reason=f"The AI declined to refine this prompt: {reason}",
            original_response=refined,
        )
    return refined


# ── Public API ────────────────────────────────────────────────────────────

def refine_prompt(
    user_prompt: str,
    style_profile: StyleProfile | None,
    asset_type: AssetType,
    image_model: str | None = None,
) -> str:
    """Refine a user prompt into a detailed image-generation prompt.

    Uses Claude Sonnet (complexity="fast") for quick turnaround.
    Prompt length adapts to the target image model's limit.
    """
    max_chars = get_prompt_limit(image_model)
    asset_context = _ASSET_TYPE_CONTEXT.get(asset_type, "General-purpose image.")
    style_section = _build_style_section(style_profile)

    prompt = _REFINE_PROMPT_TEMPLATE.format(
        asset_context=asset_context,
        style_section=style_section,
        user_prompt=user_prompt,
        max_chars=max_chars,
    )

    logger.info(
        "Refining prompt for asset_type=%s, has_style=%s, model=%s, max_chars=%d",
        asset_type.value, style_profile is not None, image_model, max_chars,
    )

    refined = invoke_claude(
        prompt,
        complexity="fast",
        max_tokens=2048 if max_chars > 1000 else 1024,
        temperature=0.7,
    )

    refined = refined.strip()
    refined = _validate_refined_prompt(refined, user_prompt)
    if len(refined) > max_chars:
        refined = refined[:max_chars - 4].rsplit(" ", 1)[0]
    logger.info("Refined prompt (%d/%d chars): %s", len(refined), max_chars, refined[:150])
    return refined


def refine_marketing_prompt(
    user_prompt: str,
    style_profile: StyleProfile | None,
    image_model: str | None = None,
) -> str:
    """Refine a user prompt into a marketing-banner-specific generation prompt."""
    max_chars = get_prompt_limit(image_model)
    style_section = _build_style_section(style_profile)

    prompt = _MARKETING_PROMPT_TEMPLATE.format(
        style_section=style_section,
        user_prompt=user_prompt,
        max_chars=max_chars,
    )

    logger.info("Refining marketing prompt, has_style=%s, model=%s, max_chars=%d",
                style_profile is not None, image_model, max_chars)

    refined = invoke_claude(
        prompt,
        complexity="complex",
        max_tokens=2048 if max_chars > 1000 else 1536,
        temperature=0.7,
    )

    refined = refined.strip()
    refined = _validate_refined_prompt(refined, user_prompt)
    if len(refined) > max_chars:
        refined = refined[:max_chars - 4].rsplit(" ", 1)[0]
    logger.info("Refined marketing prompt (%d/%d chars): %s", len(refined), max_chars, refined[:150])
    return refined


# ── Multi-option concept generation ──────────────────────────────────────

_CONCEPTS_PROMPT_TEMPLATE = """\
You are a creative director generating DISTINCTLY DIFFERENT design concepts
for an AI image generator.

=== ASSET TYPE ===
{asset_context}

=== STYLE ===
{style_section}

=== USER REQUEST ===
"{user_prompt}"

Generate exactly {num_options} COMPLETELY DIFFERENT creative interpretations
of the user's request. Each concept must be a fundamentally different design —
not just color or pose variations, but different visual approaches, moods,
silhouettes, aesthetics, or character archetypes.

For example, if the user asks for "a warrior":
- Concept 1: Bulky armored knight, heavy plate mail, great-shield, stoic pose
- Concept 2: Agile ninja-like rogue, sleek dark outfit, dual daggers, dynamic crouch
- Concept 3: Tribal warrior, face paint, bone jewelry, wooden spear, fierce expression
- Concept 4: Futuristic cyber-soldier, glowing visor, energy blade, neon accents
- Concept 5: Ancient Greek hoplite, bronze helm, round shield, red cloak, spear

Each concept must:
1. **RESPECT THE USER'S INTENT FIRST** — their explicit words override asset type
   and style defaults. If they describe a tileable panel, don't force it into an
   isolated object. If they say "real-world like", don't make it toylike.
2. Use the asset type and style as GUIDELINES that inform, not override
3. Be a self-contained image-generation prompt under {max_chars} characters
4. Be visually distinct enough that an artist would see them as different options

Return a JSON array of strings — each string is a complete image-generation prompt.
Example: ["prompt 1...", "prompt 2...", ...]

Return ONLY the JSON array. No markdown fences, no explanation.
"""


def generate_concept_prompts(
    user_prompt: str,
    style_profile: StyleProfile | None,
    asset_type: AssetType,
    num_options: int = 5,
    image_model: str | None = None,
) -> list[str]:
    """Generate multiple distinctly different concept prompts from a single user request."""
    max_chars = get_prompt_limit(image_model)
    asset_context = _ASSET_TYPE_CONTEXT.get(asset_type, "General-purpose image.")
    style_section = _build_style_section(style_profile)

    prompt = _CONCEPTS_PROMPT_TEMPLATE.format(
        asset_context=asset_context,
        style_section=style_section,
        user_prompt=user_prompt,
        num_options=num_options,
        max_chars=max_chars,
    )

    logger.info(
        "Generating %d concept prompts for asset_type=%s, has_style=%s, model=%s, max_chars=%d",
        num_options, asset_type.value, style_profile is not None, image_model, max_chars,
    )

    raw = invoke_claude(
        prompt,
        complexity="complex",
        max_tokens=8192 if max_chars > 1000 else 4096,
        temperature=0.9,
    )

    # Parse JSON array from response
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_nl = cleaned.index("\n")
        cleaned = cleaned[first_nl + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        concepts = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse concepts JSON, falling back to single refined prompt")
        single = refine_prompt(user_prompt, style_profile, asset_type, image_model)
        return [single] * num_options

    if not isinstance(concepts, list):
        logger.warning("Concepts response is not a list, falling back")
        single = refine_prompt(user_prompt, style_profile, asset_type, image_model)
        return [single] * num_options

    # Truncate each prompt to model-specific limit
    result = []
    for c in concepts[:num_options]:
        p = str(c).strip()
        if len(p) > max_chars:
            p = p[:max_chars - 4].rsplit(" ", 1)[0]
        result.append(p)

    # Pad if Claude returned fewer than requested
    while len(result) < num_options:
        result.append(result[-1] if result else user_prompt)

    logger.info("Generated %d concept prompts (lengths: %s)", len(result), [len(p) for p in result])
    return result
