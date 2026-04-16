"""Prompt engineering service — refines user prompts into detailed, optimised
image-generation prompts using Claude Sonnet (fast) and Claude Opus (complex)."""

import contextvars
import json
import logging

from backend.models.generation_request import AssetType, ImageModel
from backend.models.style_profile import StyleProfile
from backend.services.bedrock_client import invoke_llm
from backend.services.prompt_templates import get_template

logger = logging.getLogger(__name__)

# Prompt character limits per image model
_MODEL_PROMPT_LIMITS: dict[str, int] = {
    ImageModel.NOVA_CANVAS.value: 900,
    ImageModel.TITAN_IMAGE.value: 480,
    ImageModel.SD35_LARGE.value: 2000,
    ImageModel.STABLE_IMAGE_ULTRA.value: 2000,
}
_DEFAULT_PROMPT_LIMIT = 900

# Request-scoped storage for the last negative prompt (thread/async safe)
_last_negative_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_last_negative_var", default=""
)


def get_prompt_limit(image_model: str | None = None) -> int:
    """Get the prompt character limit for a given image model.

    Checks the model registry first (prompt_limit field), falls back to
    the hardcoded dict, then the default.
    """
    # Check registry first (covers custom models and any model with prompt_limit)
    if image_model:
        from backend.services.model_registry import get_image_model
        reg = get_image_model(image_model)
        if reg and reg.get("prompt_limit"):
            return reg["prompt_limit"]
    return _MODEL_PROMPT_LIMITS.get(image_model, _DEFAULT_PROMPT_LIMIT)


def get_model_guidance(image_model: str | None = None) -> str:
    """Get model-specific prompt guidance from the registry.

    Each model can have a 'prompt_guidance' field in its invoke config
    that tells the LLM how to best prompt that specific model.
    Returns empty string if no guidance found.
    """
    if not image_model:
        return ""
    from backend.services.model_registry import get_image_model
    reg = get_image_model(image_model)
    if reg:
        return reg.get("invoke", {}).get("prompt_guidance", "") or reg.get("prompt_guidance", "")
    return ""


def supports_negative_prompt(image_model: str | None = None) -> bool:
    """Check if a model supports negative prompts (from registry)."""
    if not image_model:
        return True  # Default: assume yes for Bedrock models
    from backend.services.model_registry import get_image_model
    reg = get_image_model(image_model)
    if reg:
        return reg.get("invoke", {}).get("supports_negative_prompt", True)
    return True

# ── Asset-type context snippets ───────────────────────────────────────────

_ASSET_TYPE_CONTEXT: dict[AssetType, str] = {
    AssetType.GAME_ASSET: (
        "DEFAULT INTENT: Isolated game-ready object/prop on transparent background.\n"
        "Apply ONLY if the user's prompt is a simple noun (e.g. 'a sword', 'a tree').\n"
        "If the user describes a scene, character, or setting — follow THEIR description, not this default.\n"
        "When this default applies: centered composition, clean edges, consistent top-left lighting, no ground shadows."
    ),
    AssetType.MARKETING_BANNER: (
        "INTENT: Cinematic promotional illustration with a text-safe zone.\n"
        "Wide dramatic composition with depth. Reserve one-third of the frame as a clean area for text overlay.\n"
        "Rich saturated colors, dramatic lighting (rim light, volumetric rays, golden hour).\n"
        "CRITICAL: Do NOT render any text, letters, or typography — the text zone must be empty for post-production."
    ),
    AssetType.ICON: (
        "INTENT: Simple, bold symbol for UI use.\n"
        "Single recognizable shape, centered, generous padding. Must read at 64x64 pixels.\n"
        "High contrast, 3-5 colors maximum, bold shapes, no fine detail."
    ),
    AssetType.CHARACTER: (
        "INTENT: Character illustration — the figure is the star.\n"
        "If the user describes a setting or scene, INCLUDE IT — the character should be IN that context.\n"
        "If the user gives only a character name/description, use a clean or contextual background.\n"
        "Focus on: readable silhouette, expressive pose, clear facial features, detailed costume/armor.\n"
        "Full-body or 3/4-body, character fills 60-75% of frame."
    ),
    AssetType.ENVIRONMENT: (
        "INTENT: Scenic illustration with depth and atmosphere.\n"
        "Three depth layers: foreground (detailed), midground (main subject), background (atmospheric haze).\n"
        "Leading lines, natural framing. Horizon at upper or lower third.\n"
        "Environmental storytelling through details. Mood-setting lighting (time of day, weather)."
    ),
}

# ── Prompt templates ──────────────────────────────────────────────────────
#
# Prompt engineering follows official model guidelines:
# - Nova Canvas: https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html
# - General Nova: https://docs.aws.amazon.com/nova/latest/userguide/prompting-general-tips.html
# - Stable Diffusion: quality tokens, weighted descriptors, structured ordering
#
# Key rules applied:
# 1. Write as descriptive CAPTIONS, not commands (Nova Canvas requirement)
# 2. Follow structure: Subject → Environment → Pose → Lighting → Camera → Style
# 3. No negation words in the main prompt (use negativeText parameter instead)
# 4. Most important details first, quality markers last (truncation safety)
# 5. For SD models: use quality boosters, style tokens, and detailed descriptors

# _REFINE_PROMPT_TEMPLATE loaded from prompt_templates registry as 'image_refine_single'

# Model-specific instructions inserted into the template
# See: https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html
_MODEL_INSTRUCTIONS = {
    "nova_canvas": (
        "Nova Canvas works best with descriptive captions, NOT commands.\n"
        "Structure: Subject → Environment → Pose → Lighting → Camera → Style.\n"
        "Place most important details first (prompt may be truncated at 1024 chars).\n"
        "NEVER use 'no', 'not', 'without' — use the NEGATIVE line instead.\n"
        "Quality markers: 'high detail', 'professional quality', 'sharp edges'."
    ),
    "titan_image": (
        "Titan Image works best with clear, concise descriptive captions.\n"
        "Keep prompts short (480 char limit). Focus on subject and style.\n"
        "NEVER use negation words — use the NEGATIVE line instead."
    ),
    # Stable Diffusion 3.5 Large prompt best practices:
    # - Supports much longer prompts (2000 chars) — use the space for rich detail
    # - Quality boosters improve output: 'masterpiece', 'best quality', 'highly detailed'
    # - Style tokens are effective: 'digital painting', 'concept art', 'artstation'
    # - Supports weighted emphasis via natural language (not CLIP weighting syntax)
    # - Negative prompts are very effective for cleanup
    "sd35_large": (
        "Stable Diffusion 3.5 Large supports rich, detailed prompts up to 2000 chars.\n"
        "USE quality boosters: 'masterpiece, best quality, highly detailed, sharp focus'.\n"
        "USE style tokens: 'digital painting', 'concept art', 'trending on artstation',\n"
        "'illustration', '8k resolution', 'unreal engine render', etc.\n"
        "Detailed descriptors work well: describe materials, textures, lighting precisely.\n"
        "Negative prompts are very effective — use the NEGATIVE line for quality cleanup.\n"
        "Common useful negatives: 'blurry, low quality, deformed, ugly, bad anatomy'."
    ),
    "stable_image_ultra": (
        "Stable Image Ultra supports rich, detailed prompts up to 2000 chars.\n"
        "USE quality boosters: 'masterpiece, best quality, highly detailed, sharp focus,\n"
        "professional photography, 8k uhd'.\n"
        "Photorealistic prompts excel: describe lighting, materials, atmosphere in detail.\n"
        "Negative prompts are effective — use the NEGATIVE line for quality cleanup."
    ),
}
_DEFAULT_MODEL_INSTRUCTIONS = (
    "Write a descriptive caption. Place subject first, style last.\n"
    "NEVER use negation words — use the NEGATIVE line instead."
)

# _MARKETING_PROMPT_TEMPLATE loaded from prompt_templates registry as 'image_refine_marketing'


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

def _get_model_label(image_model: str | None) -> str:
    """Get a human-readable model name for prompt instructions."""
    labels = {
        "nova_canvas": "Amazon Nova Canvas",
        "titan_image": "Amazon Titan Image v2",
        "sd35_large": "Stable Diffusion 3.5 Large",
        "stable_image_ultra": "Stable Image Ultra",
    }
    return labels.get(image_model, "AI image model")


def _parse_negative_prompt(raw: str) -> tuple[str, str]:
    """Split a refined prompt into (main_prompt, negative_prompt).

    If Claude included a "NEGATIVE:" line, extract it separately.
    The negative prompt is sent via the model's negativeText parameter
    (Nova Canvas) or negative_prompt parameter (SD models).

    See: https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html
    """
    lines = raw.strip().split('\n')
    main_lines = []
    negative = ""
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("NEGATIVE:"):
            negative = stripped[9:].strip()
        elif stripped:
            main_lines.append(stripped)
    return ' '.join(main_lines), negative


import re as _re


def _extract_json_array(raw: str) -> list | None:
    """Robustly extract a JSON array from an LLM response.

    Handles multiple formats:
    - Clean JSON: ["prompt1", "prompt2"]
    - Markdown code block: ```json\n[...]\n```
    - Text before/after JSON: "Here are the concepts:\n[...]"
    - Multiple code blocks (takes the first JSON array found)
    - Numbered list fallback: "1. prompt1\n2. prompt2"
    """
    text = raw.strip()

    # Strip markdown code blocks (```json ... ``` or ``` ... ```)
    if "```" in text:
        # Find content between first ``` and last ```
        parts = text.split("```")
        for part in parts[1::2]:  # odd-indexed parts are inside code blocks
            inner = part.strip()
            # Remove language hint (json, JSON, etc.)
            if inner.lower().startswith("json"):
                inner = inner[4:].strip()
            if inner.startswith("["):
                try:
                    return json.loads(inner)
                except json.JSONDecodeError:
                    pass

    # Try to find a JSON array anywhere in the text (first [ to last ])
    first_bracket = text.find("[")
    if first_bracket >= 0:
        # Find the matching closing bracket
        depth = 0
        for i in range(first_bracket, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    candidate = text[first_bracket:i + 1]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, list):
                            return result
                    except json.JSONDecodeError:
                        break

    # Fallback: try parsing the whole text as JSON
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Last resort: extract numbered list items ("1. ...\n2. ...\n")
    numbered = _re.findall(r'^\d+[\.\)]\s*["\']?(.+?)["\']?\s*$', text, _re.MULTILINE)
    if len(numbered) >= 2:
        logger.info("Extracted %d prompts from numbered list (not JSON)", len(numbered))
        return numbered

    # Also try lines that look like quoted strings
    quoted = _re.findall(r'^["\'](.+?)["\']$', text, _re.MULTILINE)
    if len(quoted) >= 2:
        logger.info("Extracted %d prompts from quoted lines", len(quoted))
        return quoted

    return None

# Pattern: "No X", "no X, no Y", "without X", "DO NOT include X" etc.
# Captures the negation phrase and the term(s) that follow.
_NEGATION_PATTERN = _re.compile(
    r'\b(?:no|not|without|don\'t|do\s+not|never)\s+'
    r'([^,.;]+(?:,\s*(?:no\s+)?[^,.;]+)*)',
    _re.IGNORECASE,
)


def _strip_negation_phrases(prompt: str) -> tuple[str, str]:
    """Remove negation phrases from a prompt and return (cleaned_prompt, extracted_negatives).

    E.g. "A warrior on a field. No text, no UI, no dice, no scene background."
    → ("A warrior on a field.", "text, UI, dice, scene background")
    """
    negatives = []
    # Words to strip from the start of extracted negative terms
    _STRIP_LEADING = _re.compile(
        r'^(?:include\s+|add\s+|have\s+|render\s+|show\s+|use\s+|put\s+|place\s+|'
        r'any\s+|the\s+|a\s+|an\s+|without\s+|in\s+)',
        _re.IGNORECASE,
    )
    def _collect(match):
        raw = match.group(1).strip().rstrip('.,;')
        # Split "no X, no Y, no Z" into individual terms
        terms = _re.split(r',\s*(?:no\s+|without\s+)?', raw, flags=_re.IGNORECASE)
        for t in terms:
            t = t.strip().rstrip('.,;')
            # Strip leading verbs/articles for cleaner negative terms
            t = _STRIP_LEADING.sub('', t).strip()
            if t and len(t) > 1:
                negatives.append(t)
        return ''  # Remove the whole negation phrase

    cleaned = _NEGATION_PATTERN.sub(_collect, prompt)
    # Clean up: remove double spaces, trailing punctuation artifacts
    cleaned = _re.sub(r'\s{2,}', ' ', cleaned).strip()
    cleaned = _re.sub(r'[,;]\s*[,;]', ',', cleaned)  # collapse double commas
    cleaned = _re.sub(r'\.\s*\.', '.', cleaned)  # collapse double periods
    cleaned = cleaned.strip(' ,;')

    return cleaned, ', '.join(negatives)


def _deduplicate_negative(parts: list[str]) -> str:
    """Combine and deduplicate negative prompt fragments from multiple sources."""
    all_terms = []
    seen = set()
    for part in parts:
        for term in part.split(','):
            term = term.strip().lower()
            if term and term not in seen:
                seen.add(term)
                all_terms.append(term)
    return ', '.join(all_terms)


def refine_prompt(
    user_prompt: str,
    style_profile: StyleProfile | None,
    asset_type: AssetType,
    image_model: str | None = None,
) -> str:
    """Refine a user prompt into a detailed image-generation prompt.

    Uses Claude Sonnet for quick turnaround. Prompt structure follows
    official model guidelines:
    - Nova Canvas: descriptive captions, Subject→Environment→Pose→Lighting→Camera→Style
    - SD 3.5: quality boosters, style tokens, rich detail
    - All models: no negation words in main prompt (extracted to negative_prompt)

    Returns the main prompt text. Negative prompt is stored separately
    via _parse_negative_prompt when the generation pipeline calls this.
    """
    max_chars = get_prompt_limit(image_model)
    asset_context = _ASSET_TYPE_CONTEXT.get(asset_type, "General-purpose image.")
    style_section = _build_style_section(style_profile)
    model_name = _get_model_label(image_model)
    # Model-specific prompt guidance: check registry first (extensible), then hardcoded
    model_instructions = get_model_guidance(image_model) or _MODEL_INSTRUCTIONS.get(image_model, _DEFAULT_MODEL_INSTRUCTIONS)

    prompt = get_template('image_refine_single').format(
        asset_context=asset_context,
        style_section=style_section,
        user_prompt=user_prompt,
        max_chars=max_chars,
        model_name=model_name,
        model_specific_instructions=model_instructions,
    )

    logger.info(
        "Refining prompt for asset_type=%s, has_style=%s, model=%s, max_chars=%d",
        asset_type.value, style_profile is not None, image_model, max_chars,
    )

    refined = invoke_llm(
        prompt,
        complexity="fast",
        max_tokens=2048 if max_chars > 1000 else 1024,
        temperature=0.7,
    )

    refined = refined.strip()
    refined = _validate_refined_prompt(refined, user_prompt)

    # Parse out any NEGATIVE: line
    main_prompt, negative = _parse_negative_prompt(refined)

    # Skip negative prompts for models that don't support them (e.g., FLUX)
    if negative and not supports_negative_prompt(image_model):
        logger.info("Skipping negative prompt for %s (not supported)", image_model)
        negative = ""
    elif negative:
        logger.info("Extracted negative prompt: %s", negative[:100])

    # Store negative prompt for retrieval by the generation pipeline
    _last_negative_var.set(negative)

    if len(main_prompt) > max_chars:
        main_prompt = main_prompt[:max_chars - 4].rsplit(" ", 1)[0]
    logger.info("Refined prompt (%d/%d chars): %s", len(main_prompt), max_chars, main_prompt[:150])
    return main_prompt

def refine_prompt_structured(
    user_prompt: str,
    style_profile: StyleProfile | None,
    asset_type: AssetType,
    image_model: str | None = None,
) -> tuple[str, dict]:
    """Refine a prompt using structured decompose→recompose pipeline.

    Always decomposes the prompt into visual components (subject, scene,
    lighting, composition, style) then recomposes into an optimised prompt.
    This produces higher quality results than single-shot refinement because
    it forces the LLM to consider each visual aspect explicitly.

    Returns: (refined_prompt, decomposed_data)
        - refined_prompt: the final recomposed prompt for the model
        - decomposed_data: the structured components (for display in UI)
    """
    from backend.services.prompt_templates import get_template, get_system_prompt

    max_chars = get_prompt_limit(image_model)
    asset_context = _ASSET_TYPE_CONTEXT.get(asset_type, "General-purpose image.")
    style_section = _build_style_section(style_profile)
    model_name = _get_model_label(image_model)
    model_instructions = get_model_guidance(image_model) or _MODEL_INSTRUCTIONS.get(image_model, _DEFAULT_MODEL_INSTRUCTIONS)

    # Step 1: Decompose — break the prompt into structured visual components
    decompose_prompt_text = get_template('prompt_decompose').format(
        asset_context=asset_context,
        style_section=style_section,
        user_prompt=user_prompt,
        model_name=model_name,
        model_specific_instructions=model_instructions,
    )

    logger.info("Structured refinement: decomposing prompt for %s, model=%s", asset_type.value, image_model)

    raw_decompose = invoke_llm(
        decompose_prompt_text,
        system=get_system_prompt('prompt_decompose'),
        complexity="fast",
        max_tokens=2048,
        temperature=0.5,
    ).strip()

    # Parse decomposed JSON
    import re as _re
    cleaned = raw_decompose
    cleaned = _re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = _re.sub(r"\n?```\s*$", "", cleaned)
    try:
        decomposed = json.loads(cleaned.strip())
    except Exception:
        # Fallback: if decomposition fails, use single-shot refinement
        logger.warning("Structured decomposition failed — falling back to single-shot refinement")
        refined = refine_prompt(user_prompt, style_profile, asset_type, image_model)
        return refined, {}

    # Step 2: Recompose — build an optimised prompt from the components
    recompose_prompt_text = get_template('prompt_recompose').format(
        structured_json=json.dumps(decomposed, indent=2),
        model_name=model_name,
        max_chars=max_chars,
    )

    raw_recompose = invoke_llm(
        recompose_prompt_text,
        system=get_system_prompt('prompt_recompose'),
        complexity="fast",
        max_tokens=1500,
        temperature=0.3,
    ).strip()

    # Split out NEGATIVE line
    main_prompt = raw_recompose
    negative = ""
    for marker in ["NEGATIVE:", "Negative:"]:
        if marker in raw_recompose:
            parts = raw_recompose.split(marker, 1)
            main_prompt = parts[0].strip()
            negative = parts[1].strip()
            break

    # Skip negative prompts for models that don't support them
    if negative and not supports_negative_prompt(image_model):
        negative = ""
    _last_negative_var.set(negative)

    if len(main_prompt) > max_chars:
        main_prompt = main_prompt[:max_chars - 4].rsplit(" ", 1)[0]

    logger.info("Structured refinement complete (%d chars): %s", len(main_prompt), main_prompt[:150])
    return main_prompt, decomposed


def get_last_negative_prompt() -> str:
    """Retrieve the negative prompt from the most recent refine_prompt call."""
    return _last_negative_var.get()


def refine_marketing_prompt(
    user_prompt: str,
    style_profile: StyleProfile | None,
    image_model: str | None = None,
) -> str:
    """Refine a user prompt into a marketing-banner-specific generation prompt."""
    max_chars = get_prompt_limit(image_model)
    style_section = _build_style_section(style_profile)

    prompt = get_template('image_refine_marketing').format(
        style_section=style_section,
        user_prompt=user_prompt,
        max_chars=max_chars,
    )

    logger.info("Refining marketing prompt, has_style=%s, model=%s, max_chars=%d",
                style_profile is not None, image_model, max_chars)

    refined = invoke_llm(
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

# _CONCEPTS_PROMPT_TEMPLATE loaded from prompt_templates registry as 'image_concepts_multi'


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

    prompt = get_template('image_concepts_multi').format(
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

    raw = invoke_llm(
        prompt,
        complexity="complex",
        max_tokens=8192 if max_chars > 1000 else 4096,
        temperature=0.9,
    )

    # Parse JSON array from response — robust extraction
    concepts = _extract_json_array(raw)

    if concepts is None:
        logger.warning("Failed to parse concepts JSON from LLM response (%d chars), falling back to single refined prompt. Response start: %s",
                       len(raw), raw[:200])
        single = refine_prompt(user_prompt, style_profile, asset_type, image_model)
        return [single] * num_options

    if not isinstance(concepts, list) or len(concepts) == 0:
        logger.warning("Concepts response is empty or not a list, falling back")
        single = refine_prompt(user_prompt, style_profile, asset_type, image_model)
        return [single] * num_options

    # Check if the last entry is a NEGATIVE: line (shared exclusions)
    negative_parts = []
    actual_prompts = []
    for c in concepts:
        p = str(c).strip()
        if p.upper().startswith("NEGATIVE:"):
            negative_parts.append(p[9:].strip())
        else:
            actual_prompts.append(p)

    # Post-process each concept prompt: strip negation phrases and collect
    # them into the shared negative prompt. The AI often embeds "No X, no Y"
    # directly in concept prompts despite being told not to.
    cleaned_prompts = []
    for p in actual_prompts[:num_options]:
        cleaned, per_prompt_neg = _strip_negation_phrases(p)
        if per_prompt_neg:
            negative_parts.append(per_prompt_neg)
        cleaned_prompts.append(cleaned)

    # Deduplicate and store the combined negative prompt
    negative = _deduplicate_negative(negative_parts)
    if negative:
        _last_negative_var.set(negative)
        logger.info("Concept generation negative prompt: %s", negative[:100])

    # Truncate each prompt to model-specific limit
    result = []
    for p in cleaned_prompts:
        if len(p) > max_chars:
            p = p[:max_chars - 4].rsplit(" ", 1)[0]
        result.append(p)

    # Pad if Claude returned fewer than requested
    while len(result) < num_options:
        result.append(result[-1] if result else user_prompt)

    logger.info("Generated %d concept prompts (lengths: %s)", len(result), [len(p) for p in result])
    return result
