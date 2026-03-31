"""Prompt Templates — manages editable LLM directive prompts.

All 13 system/directive prompts are stored in prompt_templates.json.
Users can view, edit, and reset templates via the admin API.
Code reads templates via get_template(name) instead of hardcoded strings.

Template variables use {curly_braces} and are substituted at runtime.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "prompt_templates.json"
_templates: dict = {}


# ── Default templates (code as source of truth for resets) ────────────────

_DEFAULTS = {
    "image_refine_single": {
        "label": "Image Prompt Refinement (Single)",
        "description": "Refines a user prompt into a detailed image caption optimized for the target model.",
        "used_by": "Image Studio — single-model generation",
        "variables": ["{user_prompt}", "{model_name}", "{model_specific_instructions}", "{asset_context}", "{style_section}", "{max_chars}"],
        "model": "fast or complex LLM",
        "text": """You are an expert image-generation prompt engineer for game art. Your job is to rewrite the user's description as a DESCRIPTIVE IMAGE CAPTION optimized for the target model: {model_name}.

=== TARGET MODEL: {model_name} ===
{model_specific_instructions}

=== ASSET TYPE GUIDELINES (adapt, don't force) ===
{asset_context}

=== STYLE GUIDELINES ===
{style_section}

=== USER REQUEST ===
"{user_prompt}"

INSTRUCTIONS — follow in PRIORITY ORDER:

1. **USER INTENT IS KING.** The user's explicit words override everything else. If the user says "real-world like" but the style says "toylike", follow the user. If the user describes a scene but the asset type says "single object", describe the scene. Never contradict what the user explicitly asked for.

2. **Intelligently interpret the asset type.** The asset type is a GUIDE, not a rigid template. Adapt the composition to what the user is actually describing.

3. **Write as a DESCRIPTIVE CAPTION, not a command.** Image models understand descriptions, not instructions. Write what the image SHOWS, not what to do.
   - BAD: "Create an isometric dragon. Ensure clean edges."
   - GOOD: "An isometric low-poly dragon, cel-shaded flat colors, clean sharp edges, centered on transparent background"

4. **Follow this structure order** (most important first):
   a. Subject and main action/pose
   b. Composition and framing
   c. Style and rendering technique
   d. Lighting and atmosphere
   e. Technical quality directives

5. **Keep under {max_chars} characters.** Be dense and descriptive, not verbose.

6. **Extract negative concepts.** If exclusions are needed, add a final line starting with NEGATIVE: followed by comma-separated terms. This will be sent via the model's negative prompt parameter.

Output ONLY the refined prompt (and optional NEGATIVE: line). No explanations.""",
    },

    "image_concepts_multi": {
        "label": "Multi-Concept Generation",
        "description": "Generates 2-5 visually distinct creative concepts from one user prompt.",
        "used_by": "Image Studio — multi-option generation",
        "variables": ["{user_prompt}", "{num_options}", "{asset_context}", "{style_section}", "{max_chars}"],
        "model": "complex LLM (Opus)",
        "text": """You are a creative director generating DISTINCTLY DIFFERENT design concepts for an AI image generator.

=== ASSET TYPE ===
{asset_context}

=== STYLE ===
{style_section}

=== USER REQUEST ===
"{user_prompt}"

Generate exactly {num_options} COMPLETELY DIFFERENT creative interpretations. Each concept must be a fundamentally different design — not just color or pose variations, but different visual approaches, moods, silhouettes, aesthetics, or character archetypes.

Each concept must:
1. RESPECT THE USER'S INTENT FIRST — their explicit words override asset type and style defaults
2. Be a self-contained image-generation prompt under {max_chars} characters
3. Be visually distinct enough that an artist would see them as different options

IMPORTANT: Do NOT use negation words in the prompts. Describe what you WANT positively. If exclusions are needed for ALL concepts, include a final entry prefixed with "NEGATIVE:" for shared exclusions.

Return a JSON array of strings — each string is a complete image-generation prompt.""",
    },

    "image_refine_marketing": {
        "label": "Marketing Banner Refinement",
        "description": "Refines prompts specifically for marketing banners with text-safe zones.",
        "used_by": "Image Studio — marketing banner asset type",
        "variables": ["{user_prompt}", "{style_section}", "{max_chars}"],
        "model": "complex LLM (Opus)",
        "text": "You are a senior creative director specialising in game marketing materials. Create a detailed image generation prompt for a marketing banner based on the user's request.\n\n{style_section}\n\nUser request: \"{user_prompt}\"\n\nCreate a cinematic, visually striking banner composition. Reserve a clear text-safe zone on one side. DO NOT render any text or typography — the text zone should be clean for post-production overlay.\n\nKeep under {max_chars} characters. Output ONLY the prompt.",
    },

    "style_analysis_full": {
        "label": "Style Analysis (Full)",
        "description": "Analyzes reference images for visual attributes: perspective, palette, rendering, lighting.",
        "used_by": "Style Library — Analyze Style button",
        "variables": ["{user_guidance_section}", "reference images (sent as vision input)"],
        "model": "complex LLM (Opus) with vision",
        "text": """You are an expert art director and visual style analyst specializing in game asset production. Carefully study ALL the reference images provided. These are individual game asset sprites — typically isolated objects on transparent backgrounds. Analyze the RENDERING STYLE, not the composition.

{user_guidance_section}

Analyze these attributes by examining the full set of images together:
- perspective: Camera/viewpoint (e.g. "isometric 30-degree dimetric", "top-down orthographic")
- palette: 5-8 dominant hex colors, grouped by material
- rendering: Flat/cel-shaded/hand-painted/3D-rendered, outline style, edge treatment
- lighting: Direction, style (ambient, directional, rim light), shadow treatment
- detail_level: Complexity (low-poly, high-detail), texture density
- line_work: Outline presence, weight, color
- texture_style: Smooth gradients, pixel art, painterly strokes
- composition_rules: Common framing, proportions, spacing patterns

Return a JSON object with these keys. Be specific and precise.""",
    },

    "style_hints_generation": {
        "label": "Style Hints Generation",
        "description": "Distills analyzed style into a concise generation directive paragraph.",
        "used_by": "Style Library — after style analysis completes",
        "variables": ["{style_json}", "{user_guidance_section}"],
        "model": "fast LLM (Sonnet)",
        "text": """You are a concise prompt-engineering expert for AI image generation. Given the analyzed visual style below, write generation hints that an AI image model MUST follow to produce assets matching this exact style.

Analyzed style (from AI vision analysis of reference images):
{style_json}

{user_guidance_section}

Write a SINGLE PARAGRAPH (max 200 words) that covers ALL of these in order:
1. Perspective/camera angle (be specific)
2. Rendering technique and edge treatment
3. Color palette (reference specific hex values)
4. Lighting direction and shadow style
5. Level of detail and texture approach

This paragraph will be prepended to every generation prompt. Be directive and precise.""",
    },

    "style_cohesion_check": {
        "label": "Style Cohesion Check",
        "description": "Quick check: do reference images represent a unified style or diverse collection?",
        "used_by": "Style Library — before full analysis",
        "variables": ["reference images (sent as vision input)"],
        "model": "fast LLM (Sonnet) with vision",
        "text": """You are a visual style analyst. Look at these reference images and determine whether they represent a SINGLE cohesive visual style or a DIVERSE collection with multiple themes/styles.

Respond with ONLY a JSON object (no markdown fences):
{
  "cohesion": "high" | "medium" | "low",
  "reasoning": "One sentence explaining why",
  "common_patterns": "What is consistent across ALL images (if anything)"
}""",
    },

    "moderation_prescreen": {
        "label": "Content Moderation Pre-Screen",
        "description": "Predicts if a prompt will be blocked by the target model.",
        "used_by": "Image Studio — prompt pre-check toggle",
        "variables": ["{prompt_for_screen}", "{model_label}"],
        "model": "fast LLM (Sonnet)",
        "text": """You are a content moderation analyst for AI image generation models.

Analyze this prompt for the model "{model_label}":
"{prompt_for_screen}"

Model strictness levels:
- Nova Canvas: VERY strict — blocks weapons, combat, fighting, copyrighted IP, aggressive poses
- Titan Image v2: Strict — similar to Nova Canvas
- Stable Diffusion 3.5 Large: Moderate — allows stylized weapons, fantasy combat, action poses
- Stable Image Ultra: Moderate — similar to SD 3.5 Large

Will this prompt likely be BLOCKED by {model_label}?

Respond with ONLY a JSON object (no markdown):
{
  "likely_safe": true/false,
  "issues": ["specific concern 1", "specific concern 2"],
  "explanation": "Brief explanation for the user",
  "suggested_model": "alternative model name if current is too strict, or null"
}""",
    },

    "moderation_rewrite": {
        "label": "Content Moderation Rewrite",
        "description": "Rewrites a blocked prompt to pass moderation while preserving creative intent. The original prompt and issues are prepended as context before this template.",
        "used_by": "Image Studio — moderation dialog rewrite button",
        "variables": ["(context: original prompt + issues prepended)"],
        "model": "fast LLM (Sonnet)",
        "text": """Your task: Rewrite this prompt to address EVERY identified issue above while preserving the user's creative intent as closely as possible.

Rules:
1. Address each specific issue listed above
2. For copyrighted IP references: replace with original character descriptions
3. For violence/aggression concerns: reframe as dynamic action poses
4. For weapons: use fantasy/stylized alternatives
5. Keep the same visual energy and mood
6. Stay under the original character count
7. Output ONLY the rewritten prompt, nothing else.""",
    },

    "video_enhance_prompt": {
        "label": "Video Prompt Enhancement",
        "description": "Enhances a user prompt with camera movements, lighting, and temporal cues for video generation. The user's prompt is sent as the user message; this template is the system instruction.",
        "used_by": "Video Studio — AI-enhance prompt toggle",
        "variables": ["{prompt_limit}", "(context: user prompt sent as message)"],
        "model": "fast LLM (Sonnet)",
        "text": """You are a video generation prompt engineer. Enhance the user's prompt for AI video generation.

Guidelines:
- Add specific camera movements (pan, zoom, dolly, tracking shot, aerial view)
- Include lighting and atmosphere details (golden hour, dramatic shadows, ambient glow)
- Add temporal cues for smooth motion (gradual, continuous, smooth transition)
- Keep the core intent and subject of the original prompt
- If the user mentions things to avoid, weave avoidance into the prompt naturally since video models have no negative prompt support
- Maximum {prompt_limit} characters for the enhanced prompt
- For game assets: emphasize clean motion, consistent style, looping-friendly if short

Respond in this format:
ENHANCED: <the enhanced prompt>
NEGATIVE_CONCEPTS: <comma-separated concepts to avoid, if any>""",
    },

    "typestudio_layout": {
        "label": "Type Studio Text Layout",
        "description": "Designs text positions, fonts, sizes, colors, and effects for image overlay.",
        "used_by": "Type Studio — Suggest Layout button",
        "variables": ["{canvas_width}", "{canvas_height}", "{image_context}", "{style_section}", "{lines_desc}"],
        "model": "complex or fast LLM",
        "text": """You are a creative director designing text layout for a game asset graphic.

Canvas dimensions: {canvas_width}x{canvas_height} pixels.
{image_context}
{style_section}
Text lines to layout:
{lines_desc}

Design a visually appealing text layout. For each line, specify:
- x, y pixel coordinates (anchor point of the text)
- anchor: alignment relative to (x, y) — "mm" (center), "lt" (left-top), "mt" (middle-top), "la" (left-ascender)
- font_size: in pixels (scale appropriately for the canvas)
- color: hex color that contrasts well with the background
- effects: optional array of shadow/outline/glow effects

Return a JSON array of layout options (1-5 different creative approaches). Each option is an array of line objects.""",
    },

    "chat_context_compact": {
        "label": "Chat Context Compaction",
        "description": "Summarizes older messages to free context window space in Chat Studio.",
        "used_by": "Chat Studio — Compact button",
        "variables": ["{convo_text}"],
        "model": "fast LLM (Sonnet)",
        "text": "Summarize this conversation concisely, preserving key facts, decisions, and context that would be needed to continue the conversation naturally:\n\n{convo_text}",
    },

    "chat_title_generate": {
        "label": "Chat Session Title",
        "description": "Auto-generates a 3-8 word title from the first chat exchange.",
        "used_by": "Chat Studio — after first message exchange",
        "variables": ["{user_message}", "{assistant_snippet}"],
        "model": "fast LLM (Sonnet)",
        "text": "Generate a short title (3-8 words, no quotes, no punctuation at the end) for a chat conversation that starts with:\n\nUser: {user_message}\n\nAssistant: {assistant_snippet}\n\nTitle:",
    },

    "translate_detect_language": {
        "label": "Language Detection",
        "description": "Detects the language of ambiguous text (when Unicode heuristics are inconclusive).",
        "used_by": "Prompt translator — fallback detection",
        "variables": ["{text}"],
        "model": "fast LLM (Sonnet)",
        "text": "What language is this text? Reply with ONLY the ISO 639-1 code (en, ja, zh, ko, fr, es). Text: {text}",
    },

    "translate_to_english": {
        "label": "Translation to English",
        "description": "Translates non-English prompts to English for image/video models.",
        "used_by": "Prompt translator — all studios except Chat",
        "variables": ["{text}", "{lang_name}"],
        "model": "fast LLM (Sonnet)",
        "text": "Translate the following {lang_name} text to English. Preserve the meaning, tone, and any technical terms. Output ONLY the English translation, nothing else.\n\nText: {text}",
    },
}


# ── Load / Save ───────────────────────────────────────────────────────────

def _load():
    """Load templates from disk, merging with defaults for any missing templates."""
    global _templates
    if _TEMPLATES_PATH.exists():
        try:
            _templates = json.loads(_TEMPLATES_PATH.read_text())
            logger.info("Prompt templates loaded: %d templates", len(_templates))
        except Exception as exc:
            logger.error("Failed to load prompt templates: %s", exc)
            _templates = {}
    else:
        _templates = {}

    # Merge defaults — add any missing templates, preserve user edits
    changed = False
    for name, default in _DEFAULTS.items():
        if name not in _templates:
            _templates[name] = {**default, "modified": False}
            changed = True
        else:
            # Ensure metadata fields exist (user may have edited text only)
            for key in ("label", "description", "used_by", "variables", "model"):
                if key not in _templates[name]:
                    _templates[name][key] = default[key]
                    changed = True

    if changed:
        _save()


def _save():
    """Persist templates to disk."""
    _templates["_last_updated"] = datetime.utcnow().isoformat()
    _TEMPLATES_PATH.write_text(json.dumps(_templates, indent=2, ensure_ascii=False, default=str))


# ── Load on import ────────────────────────────────────────────────────────
_load()


# ── Public API ────────────────────────────────────────────────────────────

def get_template(name: str) -> str:
    """Get the current text of a template by name. Returns default if not found."""
    tmpl = _templates.get(name)
    if tmpl:
        return tmpl.get("text", "")
    default = _DEFAULTS.get(name)
    if default:
        return default.get("text", "")
    logger.warning("Unknown prompt template: %s", name)
    return ""


def get_all_templates() -> dict:
    """Return all templates with metadata (for admin UI)."""
    result = {}
    for name, tmpl in _templates.items():
        if name.startswith("_"):
            continue
        result[name] = {
            "label": tmpl.get("label", name),
            "description": tmpl.get("description", ""),
            "used_by": tmpl.get("used_by", ""),
            "variables": tmpl.get("variables", []),
            "model": tmpl.get("model", ""),
            "text": tmpl.get("text", ""),
            "modified": tmpl.get("modified", False),
        }
    return result


def validate_template(name: str, text: str) -> list[str]:
    """Validate that all required variables are present in the template text.

    Returns a list of missing variables. Empty list = valid.
    """
    tmpl = _templates.get(name) or _DEFAULTS.get(name)
    if not tmpl:
        return []
    missing = []
    for var in tmpl.get("variables", []):
        # Only check {curly_brace} variables, skip context descriptions
        if var.startswith("{") and var.endswith("}"):
            var_name = var.strip("{}")
            if "{" + var_name + "}" not in text:
                missing.append(var)
    return missing


def update_template(name: str, text: str, force: bool = False) -> dict:
    """Update a template's text. Validates variables unless force=True.

    Returns the updated template dict. Raises ValueError if variables are missing
    and force is False.
    """
    if name not in _templates and name not in _DEFAULTS:
        raise ValueError(f"Unknown template: {name}")

    # Validate variables
    missing = validate_template(name, text)
    if missing and not force:
        raise ValueError(
            f"Cannot save: required variables missing from template text: {', '.join(missing)}. "
            f"These variables are substituted at runtime — removing them will break the feature. "
            f"To save anyway, use force=True (API: add ?force=true)."
        )

    if name not in _templates:
        _templates[name] = {**_DEFAULTS[name]}
    _templates[name]["text"] = text
    _templates[name]["modified"] = True
    if missing:
        _templates[name]["warning"] = f"Missing variables: {', '.join(missing)}"
    else:
        _templates[name].pop("warning", None)
    _save()
    return {**_templates[name], "missing_variables": missing}


def reset_template(name: str) -> dict:
    """Reset a template to its default text."""
    if name not in _DEFAULTS:
        raise ValueError(f"Unknown template: {name}")
    _templates[name] = {**_DEFAULTS[name], "modified": False}
    _save()
    return _templates[name]


def reset_all_templates():
    """Reset all templates to defaults."""
    global _templates
    _templates = {name: {**default, "modified": False} for name, default in _DEFAULTS.items()}
    _save()
    return _templates
