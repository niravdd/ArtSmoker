"""Prompt Templates — manages editable LLM directive prompts.

All templates are stored in prompt_templates.json.
Users can view, edit, and reset templates via the admin API.
Code reads templates via get_template(name) instead of hardcoded strings.

Template variables use {curly_braces} and are substituted at runtime.
Templates may also have a system_prompt field for the LLM system message.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "prompt_templates.json"   # Git-tracked defaults
_USER_PATH = Path(__file__).resolve().parent.parent / "prompt_templates.user.json"  # User overrides (gitignored)
_templates: dict = {}  # Merged view: defaults + user overrides


# ── Default templates (code as source of truth for resets) ────────────────

_DEFAULTS = {
    "image_refine_single": {
        "label": "Image Prompt Refinement (Single)",
        "description": "Refines a user prompt into a detailed image caption optimized for the target model.",
        "used_by": "Image Studio — single-model generation",
        "variables": ["{user_prompt}", "{model_name}", "{model_specific_instructions}", "{asset_context}", "{style_section}", "{max_chars}"],
        "model": "fast or complex LLM",
        "text": """You are a creative director and concept artist with deep expertise in anatomy, architecture, vehicles, natural forms, and material science. Rewrite the user's description as a DESCRIPTIVE IMAGE CAPTION that gives the image model precise visual information. Target model: {model_name}.

=== TARGET MODEL: {model_name} ===
{model_specific_instructions}

=== ASSET TYPE GUIDELINES (adapt, don't force) ===
{asset_context}

=== STYLE GUIDELINES ===
{style_section}

=== USER REQUEST ===
"{user_prompt}"

INSTRUCTIONS — follow in PRIORITY ORDER:

1. **USER INTENT IS KING — this overrides ALL other rules.** Read the user's request carefully. If they describe a scene, environment, camera angle, background, or composition — FOLLOW THAT, even if the asset type says "isolated sprite" or "transparent background". The asset type is a DEFAULT that applies only when the user gives a bare noun like "a cat" or "a sword". When the user writes a detailed description with scene context, camera placement, or environmental details, they are telling you what they want — do NOT override it with asset type defaults. Never strip away elements the user explicitly described.

2. **ADD SUBJECT-SPECIFIC STRUCTURAL ACCURACY.** Identify what the subject IS and add domain knowledge:
   - Human/humanoid character: well-proportioned figure (7.5-8 head ratio), natural joint articulation, correct hand pose with proper finger placement on any held objects, believable weight distribution and balance, specific armor/clothing construction details
   - Animal/creature: species-accurate body proportions, correct limb structure (digitigrade vs plantigrade legs, wing membrane anatomy), accurate eye and ear placement, fur/feather/scale growth direction
   - Vehicle (car, ship, aircraft): mechanically accurate proportions, correct wheel/hull/wing geometry, proper panel lines and structural joins, authentic details for the vehicle type (rigging for sailboats, suspension geometry for cars)
   - Building/architecture: structurally sound construction (load-bearing elements, realistic roof pitch), period-accurate architectural features, proper scale relative to doors/windows
   - Natural object/prop: construction detail (joinery, hardware, fastenings), material-appropriate aging and wear, functional details that match real-world equivalents
   - Environment/scene: atmospheric perspective (sharp foreground fading to hazy distance), three distinct depth layers, scale reference elements, consistent light direction across the scene

3. **SPECIFY MATERIALS, NOT JUST COLORS.** Describe how surfaces behave:
   - Metal: reflection type (polished specular, brushed anisotropic, matte oxidized), edge wear, patina or rust at stress points
   - Wood: grain direction, species-appropriate tone, aging (darkening, cracks, weathering)
   - Fabric/cloth: drape following gravity, fold patterns at joints and stress points, weave texture (linen, silk, leather)
   - Skin/fur/scales: color variation zones, growth direction patterns, surface quality
   - Stone: surface roughness, lichen/moss growth, chipping or erosion patterns
   - Water: transparency level, reflection quality, surface state (calm, rippled, waves)

4. **PROFESSIONAL LIGHTING.** Default to three-point setup:
   - Warm key light from upper-left creating clear form shadows
   - Cool rim/edge light from back-right for subject separation
   - Soft ambient fill preventing crushed black areas
   Adapt the lighting if the user or style implies something different (e.g., dramatic, moody, flat).

5. **Write as a DESCRIPTIVE CAPTION, not a command.** Describe what the image SHOWS.
   - BAD: "Create an isometric dragon. Ensure clean edges."
   - GOOD: "An isometric dragon with overlapping emerald scales, leathery bat-like wing membranes stretched between visible finger-bone spars, digitigrade hind legs with raptor-joint ankles, barbed tail, crouched on transparent background"

6. **ALWAYS include a NEGATIVE: line** with failure-prevention terms appropriate to the subject:
   - Characters: blurry, bad anatomy, extra limbs, missing fingers, extra fingers, fused fingers, deformed hands, disproportionate body
   - Animals: extra legs, wrong number of toes, deformed face, anatomical errors
   - Vehicles: impossible geometry, floating wheels, broken perspective
   - All subjects: low quality, text, watermark, signature, cropped, jpeg artifacts, ugly

7. **Keep under {max_chars} characters.** Every word must give the model visual information. No filler.

Output ONLY the refined prompt and NEGATIVE: line. No explanations.""",
    },

    "image_concepts_multi": {
        "label": "Multi-Concept Generation",
        "description": "Generates 2-5 visually distinct creative concepts from one user prompt.",
        "used_by": "Image Studio — multi-option generation",
        "variables": ["{user_prompt}", "{num_options}", "{asset_context}", "{style_section}", "{max_chars}"],
        "model": "complex LLM (Opus)",
        "text": """You are a creative director and concept artist generating DISTINCTLY DIFFERENT design concepts for an AI image generator. You have deep knowledge of anatomy, architecture, materials, and visual design.

=== ASSET TYPE ===
{asset_context}

=== STYLE ===
{style_section}

=== USER REQUEST ===
"{user_prompt}"

Generate exactly {num_options} COMPLETELY DIFFERENT creative interpretations.

CRITICAL: "Different" means fundamentally different DESIGN APPROACHES — not just swapping colors or materials on the same composition. Each option must differ in at least 2 of these dimensions:
- Camera angle / perspective (low angle vs overhead vs eye-level vs isometric)
- Composition approach (close-up portrait vs full-body vs wide scene vs action shot)
- Art style / rendering (painterly vs photorealistic vs stylized vs cel-shaded)
- Mood / atmosphere (dramatic vs serene vs gritty vs whimsical)
- Character archetype / design direction (if applicable)

USER INTENT IS KING: If the user describes a specific scene, environment, or camera angle — ALL options must respect that context. Vary the creative approach WITHIN the user's description, don't strip away elements they explicitly asked for. The asset type is a default for bare prompts ("a cat") — when the user gives detailed scene context, follow it.

EVERY concept must include:
1. **Subject-specific structural accuracy** — correct anatomy for characters, species-accurate forms for creatures, mechanically plausible proportions for vehicles, structurally sound architecture
2. **Material rendering specifics** — describe surface properties (metal reflection, wood grain, fabric drape) not just colors
3. **Professional lighting** — key light direction, rim light, ambient fill
4. **NEGATIVE: line** — failure-prevention terms (bad anatomy, extra limbs, deformed, blurry, low quality, text, watermark)

Each concept must:
- Be a self-contained descriptive image caption under {max_chars} characters
- Be visually distinct enough that an artist would present them as genuinely different options to a client
- Describe what the image SHOWS (a caption, not a command)

Return a JSON array of strings — each string is a complete image-generation prompt. The LAST entry should be prefixed with "NEGATIVE:" containing shared exclusions for all concepts.""",
    },

    "image_refine_marketing": {
        "label": "Marketing Banner Refinement",
        "description": "Refines prompts specifically for marketing banners with text-safe zones.",
        "used_by": "Image Studio — marketing banner asset type",
        "variables": ["{user_prompt}", "{style_section}", "{max_chars}"],
        "model": "complex LLM (Opus)",
        "text": """You are a senior creative director specialising in game marketing materials with expertise in cinematic composition and visual storytelling. Create a detailed image generation prompt for a marketing banner.

{style_section}

User request: "{user_prompt}"

REQUIREMENTS:
1. **Cinematic wide composition** — dramatic camera angle, strong depth with foreground/midground/background layers, bold use of leading lines to draw the eye
2. **Text-safe zone** — reserve a clean area (roughly one-third) on the left or right side with no visual clutter, smooth gradient or atmospheric fade. Absolutely NO rendered text, typography, letters, or symbols anywhere in the image
3. **Material and environmental detail** — describe surfaces with physical accuracy (metal reflections, fabric weight, atmospheric haze, volumetric light shafts). Name specific materials rather than generic descriptions
4. **Professional lighting** — dramatic three-point setup: strong warm key light creating bold shadows, cool rim light for subject separation, atmospheric fill (god rays, volumetric fog, lens flare as appropriate)
5. **Emotional impact** — rich saturated colors, high dynamic range, cinematic depth-of-field with sharp subject and soft background
6. **NEGATIVE: line** — include: text, typography, letters, words, watermark, low quality, blurry, cropped, bad anatomy

Describe the scene as a CAPTION (what the image shows), not a command. Keep under {max_chars} characters. Output ONLY the prompt and NEGATIVE line.""",
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
{{
  "cohesion": "high" | "medium" | "low",
  "reasoning": "One sentence explaining why",
  "common_patterns": "What is consistent across ALL images (if anything)"
}}""",
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
{{
  "likely_safe": true/false,
  "issues": ["specific concern 1", "specific concern 2"],
  "explanation": "Brief explanation for the user",
  "suggested_model": "alternative model name if current is too strict, or null"
}}""",
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
        "variables": ["{prompt_limit}", "{model_guidance}"],
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
{model_guidance}

Output format (exactly two lines):
ENHANCED: <the enhanced prompt>
AVOID: <comma-separated list of things the user wants to avoid, or "none" if nothing to avoid>""",
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
- x, y pixel coordinates — this is the **anchor point** of the text
- anchor: how the text is aligned relative to (x, y):
  - "mm" = middle-middle (x, y is the CENTER of the text) — best for centered layouts
  - "lt" = left-top (x, y is the top-left corner)
  - "mt" = middle-top (x is center, y is top)
  - "la" = left-ascender
- Font size in pixels
- Color as a hex code (e.g. "#FFD700")
- The font filename to use (or "default" if no specific font)
- Visual effects: shadow, outline, and/or glow

CRITICAL for centering: To center text horizontally, set x to half the canvas width and use anchor "mm" or "mt". Do NOT try to calculate left-offset manually.

Position hints guide general placement:
- "top-center": x at center, y near the top, anchor "mt"
- "bottom-center": x at center, y near the bottom, anchor "mm"
- "center": x and y at canvas center, anchor "mm"
- "below-previous": same x as previous line, y offset by previous font_size + spacing
- Other hints should be interpreted creatively

Not every line needs every effect. Use effects judiciously to create hierarchy and readability.
The "effects" field for each line can contain any combination of "shadow", "outline", and "glow", or be empty.
Make sure text does not overflow the canvas boundaries. Account for font size when placing text.""",
    },

    "chat_context_compact": {
        "label": "Chat Context Compaction",
        "description": "Summarizes older messages to free context window space in Chat Studio.",
        "used_by": "Chat Studio — Compact button",
        "variables": ["{convo_text}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "You are a conversation summarizer. Output a clear, concise summary in 2-4 paragraphs. Include any specific names, numbers, code snippets, or decisions mentioned.",
        "text": "Summarize this conversation concisely, preserving key facts, decisions, and context that would be needed to continue the conversation naturally:\n\n{convo_text}",
    },

    "chat_title_generate": {
        "label": "Chat Session Title",
        "description": "Auto-generates a 3-8 word title from the first chat exchange.",
        "used_by": "Chat Studio — after first message exchange",
        "variables": ["{user_message}", "{assistant_snippet}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "You generate concise chat titles. Output ONLY the title — no quotes, no explanation, no prefix. 3-8 words maximum.",
        "text": "Generate a short title (3-8 words, no quotes, no punctuation at the end) for a chat conversation that starts with:\n\nUser: {user_message}\n\nAssistant: {assistant_snippet}\n\nTitle:",
    },

    "translate_detect_language": {
        "label": "Language Detection",
        "description": "Detects the language of ambiguous text (when Unicode heuristics are inconclusive).",
        "used_by": "Prompt translator — fallback detection",
        "variables": ["{text}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "Reply with only the 2-letter language code. Nothing else.",
        "text": "What language is this text? Reply with ONLY the ISO 639-1 code (en, ja, zh, ko, fr, es). Text: {text}",
    },

    "translate_to_english": {
        "label": "Translation to English",
        "description": "Translates non-English prompts to English for image/video models.",
        "used_by": "Prompt translator — all studios except Chat",
        "variables": ["{text}", "{lang_name}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "You are a precise translator. Output only the English translation. No explanations, no notes, no quotes around the text.",
        "text": "Translate the following {lang_name} text to English. Preserve the meaning, tone, and any technical terms. Output ONLY the English translation, nothing else.\n\nText: {text}",
    },

    # ── Admin Templates ────────────────────────────────────────────────

    "admin_template_enhance": {
        "label": "Template Enhancement",
        "description": "Improves an editable prompt template — makes it clearer and more effective.",
        "used_by": "Model Settings — Prompt Templates — Enhance with AI button",
        "variables": ["{template_label}", "{template_description}", "{template_used_by}", "{variable_list}", "{user_instructions}", "{current_text}"],
        "model": "user-selected LLM",
        "text": """You are an expert at writing LLM system prompts and directive templates for AI applications.

Below is a prompt template used in a game art generation tool called ArtSmoker. Your task is to improve it — make it clearer, more effective, and better at guiding the LLM to produce high-quality results.

Template name: {template_label}
Purpose: {template_description}
Used by: {template_used_by}
Variables that MUST be preserved exactly: {variable_list}
{user_instructions}

RULES:
1. PRESERVE all variables in {{curly_braces}} exactly as they are — the code substitutes these at runtime
2. Keep the same general structure and intent
3. Make instructions clearer and more specific
4. Add examples where helpful
5. Remove ambiguity
6. Output ONLY the improved template text — no explanations, no markdown fences

Current template:
---
{current_text}
---

Improved template:""",
    },

    "admin_template_fix_variables": {
        "label": "Template Variable Auto-Fixer",
        "description": "Inserts missing required variables back into an edited template.",
        "used_by": "Model Settings — Prompt Templates — Fix & Save button",
        "variables": ["{missing_variables}", "{template_text}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "You fix prompt templates by inserting missing variables. Output only the fixed template. Never remove existing content.",
        "text": """This prompt template is missing required variables that must be present for the system to work.

Missing variables: {missing_variables}

Each variable uses {{curly_brace}} syntax and gets replaced at runtime with actual values.
For example, {{user_prompt}} gets replaced with the user's actual text input.

Insert the missing variables in the most logical positions within this template.
Do NOT remove any existing content — only ADD the missing variables where they make sense.

Template:
---
{template_text}
---

Output ONLY the fixed template text with all variables inserted. No explanations.""",
    },
}


# ── Load / Save (Layered: defaults + user overrides) ─────────────────────
#
# Two files:
#   prompt_templates.json      — defaults from code _DEFAULTS, always regenerated
#                                on startup to stay current. Git-tracked.
#   prompt_templates.user.json — user overrides only (edited templates).
#                                Gitignored. Survives git pulls and code updates.
#
# Load order: code _DEFAULTS → overlay user overrides. User edits always win.
# Defaults file is written on every startup so it always reflects current code.
# User edits only write to .user.json — defaults file is never modified at runtime.

_user_overrides: dict = {}  # Raw user overrides (only modified templates)


def _load():
    """Load templates: code defaults → user overrides on top."""
    global _templates, _user_overrides

    # 1. Start from code _DEFAULTS (always the source of truth for defaults)
    _templates = {}
    for name, default in _DEFAULTS.items():
        _templates[name] = {**default, "modified": False}

    # 2. Overlay user overrides (local-only, gitignored)
    _user_overrides = {}
    if _USER_PATH.exists():
        try:
            _user_overrides = json.loads(_USER_PATH.read_text())
            for name, overrides in _user_overrides.items():
                if name.startswith("_"):
                    continue
                if name in _templates:
                    if "text" in overrides:
                        _templates[name]["text"] = overrides["text"]
                    if "system_prompt" in overrides:
                        _templates[name]["system_prompt"] = overrides["system_prompt"]
                    _templates[name]["modified"] = True
            user_count = len([k for k in _user_overrides if not k.startswith("_")])
            logger.info("Prompt templates loaded: %d defaults + %d user overrides", len(_DEFAULTS), user_count)
        except Exception as exc:
            logger.warning("Failed to read user overrides: %s", exc)
    else:
        logger.info("Prompt templates loaded: %d templates", len(_templates))
        # First deployment — stamp the user file so we know defaults have been initialized
        _stamp_deployment()

    # 3. Always regenerate defaults file from code (so it stays current after code updates)
    _write_defaults_file()


def _stamp_deployment():
    """Stamp the user file to mark this deployment as initialized.

    Written to .user.json (gitignored) so fresh clones are always recognized
    as new deployments.
    """
    global _user_overrides
    _user_overrides["_deployment_initialized"] = datetime.utcnow().isoformat()
    _save_user()


def _write_defaults_file():
    """Write code _DEFAULTS to the defaults file (git-tracked).

    Called on every startup so the file always reflects current code.
    This is what gets committed to git and updated by git pulls.
    """
    defaults_out = {}
    for name, default in _DEFAULTS.items():
        defaults_out[name] = {**default, "modified": False}
    defaults_out["_last_updated"] = datetime.utcnow().isoformat()
    _DEFAULTS_PATH.write_text(json.dumps(defaults_out, indent=2, ensure_ascii=False, default=str))


def _save_user():
    """Write only user-modified templates to the user overrides file."""
    if _user_overrides:
        _user_overrides["_last_updated"] = datetime.utcnow().isoformat()
        _USER_PATH.write_text(json.dumps(_user_overrides, indent=2, ensure_ascii=False, default=str))
    elif _USER_PATH.exists():
        # No overrides left — clean up the file
        _USER_PATH.unlink()


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


def get_system_prompt(name: str) -> str:
    """Get the system prompt for a template (if it has one). Returns empty string if none."""
    tmpl = _templates.get(name)
    if tmpl and tmpl.get("system_prompt"):
        return tmpl["system_prompt"]
    default = _DEFAULTS.get(name)
    if default and default.get("system_prompt"):
        return default["system_prompt"]
    return ""


def get_all_templates() -> dict:
    """Return all templates with metadata (for admin UI)."""
    result = {}
    for name, tmpl in _templates.items():
        if name.startswith("_"):
            continue
        entry = {
            "label": tmpl.get("label", name),
            "description": tmpl.get("description", ""),
            "used_by": tmpl.get("used_by", ""),
            "variables": tmpl.get("variables", []),
            "model": tmpl.get("model", ""),
            "text": tmpl.get("text", ""),
            "modified": tmpl.get("modified", False),
        }
        if tmpl.get("system_prompt"):
            entry["system_prompt"] = tmpl["system_prompt"]
        result[name] = entry
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


def update_template(name: str, text: str, force: bool = False, system_prompt: str | None = None) -> dict:
    """Update a template's text. Validates variables unless force=True.

    Writes to the user overrides file (gitignored), not the defaults file.
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
    if system_prompt is not None:
        _templates[name]["system_prompt"] = system_prompt
    if missing:
        _templates[name]["warning"] = f"Missing variables: {', '.join(missing)}"
    else:
        _templates[name].pop("warning", None)

    # Save to user overrides file (only the changed fields)
    _user_overrides[name] = {"text": text}
    if system_prompt is not None:
        _user_overrides[name]["system_prompt"] = system_prompt
    _save_user()

    return {**_templates[name], "missing_variables": missing}


def reset_template(name: str) -> dict:
    """Reset a template to its default text. Removes from user overrides."""
    if name not in _DEFAULTS:
        raise ValueError(f"Unknown template: {name}")
    _templates[name] = {**_DEFAULTS[name], "modified": False}
    # Remove from user overrides
    _user_overrides.pop(name, None)
    _save_user()
    return _templates[name]


def reset_all_templates():
    """Reset all templates to defaults. Clears all user overrides."""
    global _templates, _user_overrides
    _templates = {name: {**default, "modified": False} for name, default in _DEFAULTS.items()}
    _user_overrides = {}
    _save_user()
    return _templates
