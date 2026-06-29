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
    "three_d_source_analysis": {
        "label": "3D Source Completeness Analysis",
        "description": "Vision analysis of a 2D image before image-to-3D, to detect whether the subject is cropped/incomplete so we can offer outpaint completion.",
        "used_by": "3D Generator — pre-submit source check (generate_3d.analyze_source)",
        "variables": ["{asset_type}"],
        "model": "complex LLM (with vision)",
        "system_prompt": "You are a 3D-asset pipeline reviewer. You judge whether a single 2D image is a COMPLETE depiction of its subject — suitable to convert into a full 3D model — or whether the subject is CROPPED by the image frame (parts cut off at an edge). Image-to-3D can only build geometry for what is visible, so a subject cropped at the bottom yields a legless/footless model. Respond with STRICT JSON only — no prose, no markdown.",
        "text": """Analyze this image of a {asset_type} for image-to-3D conversion.

Decide if the MAIN SUBJECT is fully visible, or cropped by the frame edges (parts cut off). Focus ONLY on framing/cropping — do NOT flag stylistic choices, partial occlusion by other objects, or intentionally abstract art.

Return STRICT JSON with exactly these keys:
{{
  "complete": true|false,                 // true if the whole subject is in-frame
  "subject": "short noun, e.g. 'humanoid character'",
  "crop_edges": ["bottom"|"top"|"left"|"right"],   // frame edges where the subject is cut off; [] if none
  "missing": ["legs","feet"],             // body parts/sections not visible due to cropping; [] if none
  "suggest_outpaint": {{"down": 0-512, "up": 0-512, "left": 0-512, "right": 0-512}}, // px to extend per edge to reveal the rest; 0 where not needed
  "outpaint_prompt": "short description of what to draw in the extended area",  // e.g. "the soldier's legs and combat boots, matching the armor"; "" if complete
  "reason": "one short sentence a user can read"
}}

Rules:
- If the subject is fully visible (head-to-toe for a character, whole object for a prop), set complete=true, empty arrays, all outpaint values 0, outpaint_prompt "".
- Only suggest outpaint on edges where the subject is genuinely cut off by the frame.
- outpaint_prompt should describe the MISSING parts to generate, consistent with the visible subject's style/materials (do NOT redescribe the whole image). Keep it under ~120 chars.
- Be conservative: when in doubt, prefer complete=true (avoid false alarms on well-framed art).
- Output ONLY the JSON object.""",
    },
    "image_refine_single": {
        "label": "Image Prompt Refinement (Single)",
        "description": "Refines a user prompt into a detailed image caption optimized for the target model.",
        "used_by": "Image Studio — single-model generation",
        "variables": ["{user_prompt}", "{model_name}", "{model_specific_instructions}", "{asset_context}", "{style_section}", "{max_chars}", "{optimal_length}"],
        "model": "fast or complex LLM",
        "text": """You are a professional concept artist creating an image description for an AI image generator. Your job: take the user's idea and write a DESCRIPTIVE CAPTION that will produce a stunning, professional-quality image.

=== MODEL: {model_name} ===
{model_specific_instructions}

=== ASSET TYPE (default guidance — user's words override this) ===
{asset_context}

=== STYLE ===
{style_section}

=== USER'S IDEA ===
"{user_prompt}"

RULES:

1. **PRESERVE EVERYTHING THE USER DESCRIBED.** If they mention a setting, scene, background, camera angle, or mood — keep it ALL. The asset type above is a default for simple prompts like "a cat". When the user describes more, follow their vision.

2. **ENHANCE WITH PROFESSIONAL DETAIL — do not invent or change the concept.** Your job is to make the user's idea look BETTER, not different. Add:
   - Structural accuracy: correct anatomy/proportions for characters, accurate construction for objects, proper perspective for scenes
   - Material quality: how surfaces actually look (metal reflections, fabric drape, wood grain, skin texture) — not just color names
   - Lighting: describe the light setup (warm key light direction, rim light for separation, ambient fill)
   - Composition: camera angle, framing, depth of field if appropriate

3. **KEEP THE SAME ART STYLE throughout.** Do NOT inject an art style the user didn't ask for. No "cel-shaded" unless they said cel-shaded. No "watercolor" unless they said watercolor. No "chibi" ever unless asked. If no style is specified, default to polished digital illustration / concept art.

4. **Write as a CAPTION describing what the image shows.** Not commands.
   - BAD: "Create a warrior. Make sure the anatomy is correct."
   - GOOD: "A muscular warrior in battle-worn plate armor, standing in a wide combat stance, one hand gripping a longsword at shoulder height, scarred face visible beneath a dented half-helm, warm golden light from upper-left catching the polished steel pauldrons"

5. **MODERATION-SAFE LANGUAGE.** AI image models have content filters. Avoid words that trigger false positives:
   - Use "beige" or "skin-toned" instead of "nude" (the color)
   - Use "barefoot" instead of "bare feet" or "naked feet"
   - Use "form-fitting" instead of "tight" or "skin-tight"
   - Use "exposed shoulders" instead of "bare shoulders"
   - Never use: nude, naked, bare skin, undressed, revealing, provocative, seductive — even in innocent contexts

6. **NEGATIVE: line** — include ONLY if the model supports negative prompts (check MODEL instructions above). If the model says NO negative prompts, skip this entirely and focus all effort on the positive caption.
   When included, use terms that prevent common failures:
   - For people/characters: bad anatomy, extra limbs, extra fingers, missing fingers, deformed hands, disproportionate
   - For all: blurry, low quality, text, watermark, signature, ugly, deformed

7. **PROMPT LENGTH: Target approximately {optimal_length}.** Maximum {max_chars} characters. Be precise, not verbose. Every word should paint the picture.

Output ONLY the caption (and NEGATIVE: line if applicable).""",
    },

    "image_concepts_multi": {
        "label": "Multi-Concept Generation",
        "description": "Generates 2-5 visually distinct creative concepts from one user prompt.",
        "used_by": "Image Studio — multi-option generation",
        "variables": ["{user_prompt}", "{num_options}", "{asset_context}", "{style_section}", "{max_chars}", "{optimal_length}", "{locked_elements}", "{variable_elements}", "{model_guidance}"],
        "model": "complex LLM (Opus)",
        "text": """You are a concept artist presenting {num_options} fundamentally different creative interpretations of one brief.

=== ASSET TYPE ===
{asset_context}

=== VISUAL STYLE (all options MUST follow this) ===
{style_section}

=== THE BRIEF ===
"{user_prompt}"

=== LOCKED (reproduce exactly in every option) ===
{locked_elements}

=== VARIABLE (make genuinely different choices for each option) ===
{variable_elements}

=== MODEL GUIDANCE ===
{model_guidance}

RULES:

1. **LOCKED elements appear in EVERY option exactly as described.** These are what the user explicitly asked for.

2. **VARIABLE elements MUST DIFFER between options.** Each option should explore a completely different creative direction for these elements. Not minor tweaks — bold, distinct choices. Think: different artists interpreting the same brief.
   Examples of real variation:
   - Option 1: warm golden hour, flowing silk dress, serene expression
   - Option 2: stormy overcast, leather armor, fierce determination
   - Option 3: cool moonlight, formal uniform, contemplative mood
   Each option should differ on at least 3 variable elements simultaneously.

3. **If STYLE guidance is provided above, ALL options follow it.** Style is the visual language — palette, rendering, mood. Content varies, style stays consistent.

4. **PROMPT LENGTH: Each option must be approximately {optimal_length}.** Concise and vivid. Do NOT pad with generic quality terms. Every word should describe something visible. Maximum {max_chars} characters per option.

5. **Write as descriptive captions.** Not commands. Paint what the viewer sees.

6. **MODERATION-SAFE LANGUAGE.** AI image models have content filters. Avoid words that trigger false positives:
   - Use "upper-body crop" or "waist-up portrait" instead of "bust crop" or "bust shot"
   - Use "form-fitting" instead of "tight" or "skin-tight"
   - Use "exposed shoulders" instead of "bare shoulders"
   - Never use: nude, naked, bare skin, bust, undressed, revealing, provocative, seductive

Return a JSON array of {num_options} strings. Each string is a complete image caption. If the model supports negative prompts, add one final entry prefixed with "NEGATIVE:" for shared exclusion terms.""",
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

Output ONLY valid JSON (no markdown, no code fences):
{{"rewritten_prompt": "the rewritten prompt text", "issues": ["list of issues addressed"], "explanation": "brief explanation of changes made"}}""",
    },

    "video_enhance_prompt": {
        "label": "Video Prompt Enhancement",
        "description": "Enhances a user prompt with camera movements, lighting, and temporal cues for video generation. The user's prompt is sent as the user message; this template is the system instruction.",
        "used_by": "Video Studio — AI-enhance prompt toggle",
        "variables": ["{prompt_limit}", "{model_guidance}", "{optimal_length}"],
        "model": "fast LLM (Sonnet)",
        "text": """You are a video generation prompt engineer. Enhance the user's prompt for AI video generation.

=== MODEL-SPECIFIC GUIDANCE ===
{model_guidance}

=== ENHANCEMENT RULES ===
1. PRESERVE the user's core intent, subject, and action — enhance, don't replace.
2. Add ONE clear camera movement appropriate to the scene (dolly, pan, track, aerial, arc, zoom, etc.).
3. Add lighting and atmosphere (golden hour, overcast, neon glow, volumetric fog).
4. Add temporal quality cues (smooth, gradual, cinematic motion, fluid).
5. If the user mentions things to avoid, weave avoidance into positive descriptions naturally — video models have no negative prompt support.
6. Write as a descriptive caption of a video that already exists — NOT as a command.
7. Target approximately {optimal_length}. Maximum {prompt_limit} characters.
8. Use specific sensory adjectives (weathered, luminous, cascading) not generic ones (beautiful, amazing, nice).

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

    # ── Prompt Designer ─────────────────────────────────────────────

    "prompt_decompose": {
        "label": "Prompt Decomposition",
        "description": "Decomposes a user prompt into structured visual components for the Prompt Designer.",
        "used_by": "Image Studio — Prompt Designer modal",
        "variables": ["{user_prompt}", "{style_section}", "{asset_context}", "{model_name}", "{model_specific_instructions}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "You decompose image generation prompts into structured visual components. Reply with ONLY a JSON object, no explanation or markdown fences.",
        "text": """Decompose this image generation prompt into structured visual components that an artist can individually edit.

Prompt: "{user_prompt}"

=== STYLE GUIDANCE (incorporate into fields below) ===
{style_section}

=== ASSET TYPE ===
{asset_context}

=== TARGET MODEL: {model_name} ===
{model_specific_instructions}

Analyze the prompt and return a JSON object. For EVERY field, include:
- "value": the visual description
- "source": "user" if the user explicitly stated this detail, or "inferred" if you are filling in a professional default

CRITICAL RULES:
1. User-stated details are SACRED. If the user said "red coat" — the clothing value MUST include "red coat" with source "user".
2. If STYLE GUIDANCE is provided above, EMBED it into the relevant fields. Style hints for palette go into style.color_palette. Style hints for perspective go into composition.camera_angle. Style hints for rendering go into style.art_style. Do NOT just acknowledge the style — make the field values reflect it.
3. For fields the user did not specify, fill in rich professional defaults with source "inferred".

{{
  "subject": {{
    "description": {{"value": "What/who is the main subject", "source": "user or inferred"}},
    "clothing": {{"value": "Detailed clothing description", "source": "user or inferred"}},
    "accessories": {{"value": "Items held, worn, or carried", "source": "user or inferred"}},
    "expression_pose": {{"value": "Expression and pose", "source": "user or inferred"}},
    "details": {{"value": "Distinctive features", "source": "user or inferred"}}
  }},
  "scene": {{
    "setting": {{"value": "Location", "source": "user or inferred"}},
    "background": {{"value": "What is behind the subject", "source": "user or inferred"}},
    "props": {{"value": "Objects in the scene", "source": "user or inferred"}},
    "time_of_day": {{"value": "Time and atmosphere", "source": "user or inferred"}}
  }},
  "composition": {{
    "camera_angle": {{"value": "Camera position", "source": "user or inferred"}},
    "framing": {{"value": "Framing and crop", "source": "user or inferred"}},
    "depth_of_field": {{"value": "Focus behavior", "source": "user or inferred"}}
  }},
  "lighting": {{
    "key_light": {{"value": "Main light", "source": "user or inferred"}},
    "fill_rim": {{"value": "Secondary lights", "source": "user or inferred"}},
    "mood": {{"value": "Light mood", "source": "user or inferred"}}
  }},
  "style": {{
    "art_style": {{"value": "Rendering approach", "source": "user or inferred"}},
    "quality": {{"value": "Detail and quality", "source": "user or inferred"}},
    "color_palette": [
      {{"name": "Color", "hex": "#HEX", "usage": "where used", "source": "user or inferred"}}
    ]
  }}
}}

Be SPECIFIC and VISUAL. Keep each field value CONCISE (1-2 sentences max). Do not write paragraphs.""",
    },

    "prompt_recompose": {
        "label": "Prompt Recomposition",
        "description": "Assembles structured visual components back into a flat image generation prompt.",
        "used_by": "Image Studio — Prompt Designer modal — Generate button",
        "variables": ["{structured_json}", "{model_name}", "{model_specific_instructions}", "{max_chars}", "{optimal_length}", "{style_section}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "You write image generation prompts from structured specifications. Output ONLY the prompt text (and NEGATIVE: line if the model supports it). No explanation.",
        "text": """Convert these structured visual specifications into a single image generation prompt for {model_name}.

=== MODEL INSTRUCTIONS ===
{model_specific_instructions}

=== STYLE GUIDANCE ===
{style_section}

=== SPECIFICATIONS ===
{structured_json}

Write a DESCRIPTIVE CAPTION (not commands) that incorporates the specifications above. Structure: subject first, then scene, then lighting, then style.

PROMPT LENGTH: Target approximately {optimal_length}. The model works best with concise, natural descriptions. Maximum hard limit: {max_chars} characters. Every word must paint the picture — no filler.

Follow the MODEL INSTRUCTIONS for whether to include a NEGATIVE: line. If the model says no negative prompts, skip it entirely.""",
    },

    # ── Asset Classification ─────────────────────────────────────────

    "asset_type_classify": {
        "label": "Asset Type Classification",
        "description": "Classifies a user prompt into the best-matching asset type before generation.",
        "used_by": "Image Studio — before generation, to suggest the right asset type",
        "variables": ["{user_prompt}"],
        "model": "fast LLM (Sonnet)",
        "system_prompt": "You classify image generation prompts. Reply with ONLY a JSON object, no explanation.",
        "text": """Classify this image generation prompt into the best asset type.

Prompt: "{user_prompt}"

Asset types:
- game_asset: A single isolated object, item, or prop on a transparent background. No scene, no people. Examples: a sword, a treasure chest, a potion bottle, a tree, a crystal.
- character: The PERSON or CREATURE is clearly the STAR of the image — the prompt is primarily about THEM (their appearance, outfit, pose, expression). A scene may be mentioned as backdrop, but the character is the focal point. Examples: "a warrior holding a sword", "a female sailor", "a cute fox", "a wizard casting a spell".
- environment: A scene, landscape, location, or setting. People or creatures may APPEAR in the scene, but the SCENE ITSELF is the subject — the composition is about the place, the atmosphere, the view. If the prompt describes a wide shot, a location "shown from outside", or focuses on the setting more than any individual, it's an environment. Examples: "a medieval village at sunset", "a train on tracks with mountains", "a woman piloting a train shown from outside with a village backdrop", "a busy marketplace with vendors".
- photorealistic: The user wants a result that looks like a real photograph — not illustration, painting, or stylized art. Cues: mentions "photo", "photograph", "realistic", "real", "DSLR", "camera", "shot on", "candid", or describes real-world scenes with an expectation of photographic realism. Also classify as photorealistic when the prompt describes real people in real settings without any art style mentioned.
- marketing_banner: A wide cinematic scene for promotional use. Only if the user explicitly mentions banner, promotional, marketing, or advertisement.
- icon: A simple bold symbol for UI use. Only if the user mentions icon or button.

KEY DISTINCTIONS:
- If the prompt describes a PERSON but the composition is about the SCENE (wide shot, shown from outside, backdrop focus, multiple elements described equally), classify as "environment" not "character". Only classify as "character" when the person IS the primary subject the viewer should focus on.
- If the prompt describes real people in everyday or real-world settings without mentioning an art style, prefer "photorealistic" over "character" or "environment".

Respond with ONLY this JSON (no markdown fences):
{{
  "recommended": "game_asset" | "character" | "environment" | "photorealistic" | "marketing_banner" | "icon",
  "reason": "One sentence explaining why",
  "confidence": "high" | "medium" | "low"
}}""",
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


# ── Load / Save (Layered: code defaults + user overrides) ────────────────
#
# Source of truth: the _DEFAULTS dict in this Python file (above).
#
# Two files:
#   prompt_templates.json      — git-tracked reference copy. NEVER written at
#                                runtime. Updated only by git pull from the repo.
#   prompt_templates.user.json — user overrides only (edited templates).
#                                Gitignored. Survives git pulls and code updates.
#
# Load order: code _DEFAULTS → overlay user overrides. User edits always win.
# User edits only write to .user.json — the git-tracked file is read-only.

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

    # Note: prompt_templates.json (git-tracked) is NEVER written at runtime.
    # Templates are loaded from the _DEFAULTS dict in code — the file is a
    # git-delivered reference only. This keeps the file clean for auto-updates.


def _stamp_deployment():
    """Stamp the user file to mark this deployment as initialized.

    Written to .user.json (gitignored) so fresh clones are always recognized
    as new deployments.
    """
    global _user_overrides
    _user_overrides["_deployment_initialized"] = datetime.utcnow().isoformat()
    _save_user()


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
