"""Reference-image intent analysis for the Image Studio "Inspired by" mode.

A vision LLM looks at 1–3 reference images TOGETHER WITH the user's instruction
and produces a single enhanced text-to-image prompt (plus subject/intent/negative
metadata). This is the "Inspired by the reference" path — it needs NO custom model
(Bedrock vision LLM + a standard text-to-image model), unlike "Match the reference"
which requires a deployed edit model (e.g. Qwen-Image-Edit).

Reuses the 3D flow's vision plumbing: `_fit_image_for_vision` keeps each image
under Bedrock Converse's ~5 MB limit, and the parse pattern mirrors
`generate_3d._analyze_source_bytes`.
"""

import json
import logging

logger = logging.getLogger(__name__)

_MAX_PROMPT_CHARS = 1500


def analyze_reference_images(
    images: list[bytes],
    user_prompt: str,
    asset_type: str = "photorealistic",
    num_options: int = 1,
) -> dict:
    """Vision-analyze reference images + the user's instruction → enhanced prompt(s).

    num_options > 1 asks the vision LLM for that many DISTINCT interpretations of
    the same reference + instruction in ONE call — each becomes one generation
    option (so a "2 options" reference job gets 2 genuinely different takes, all
    grounded in the reference, not seed-only variations).

    Returns a dict:
      {
        "analyzed": bool,            # False if analysis failed (caller falls back)
        "subject": str,
        "preserve": str,
        "intent": str,
        "enhanced_prompt": str,      # first interpretation ("" if not analyzed)
        "enhanced_prompts": [str],   # ALL interpretations (>=1 when analyzed)
        "negative_prompt": str,
        "notes": str,
      }
    Conservative: on ANY error returns analyzed=False so the caller can fall back
    to the user's raw prompt rather than blocking generation.
    """
    user_prompt = (user_prompt or "").strip()
    num_options = max(1, min(5, int(num_options or 1)))
    if not images or not user_prompt:
        return {"analyzed": False, "enhanced_prompt": "", "enhanced_prompts": [], "negative_prompt": ""}

    txt = ""
    try:
        from backend.services.bedrock_client import invoke_llm
        from backend.services.prompt_templates import get_template, get_system_prompt
        # Shared vision plumbing + the tolerant JSON parser (repairs // comments,
        # trailing prose, and max_tokens truncation — salvaging completed fields).
        from backend.routers.generate_3d import _fit_image_for_vision, _loads_tolerant_json_object

        # Cap at 3 references (Qwen's optimal band; also keeps vision payload sane).
        vision_imgs = [_fit_image_for_vision(b) for b in images[:3]]
        prompt = get_template("reference_intent_extraction").format(
            user_prompt=user_prompt[:1200],
            num_images=len(vision_imgs),
            asset_type=(asset_type or "photorealistic").replace("_", " "),
            max_chars=_MAX_PROMPT_CHARS,
            num_options=num_options,
        )
        system = get_system_prompt("reference_intent_extraction")
        data, last_err = {}, None
        # At temperature 0.4 the model occasionally emits JSON even the tolerant
        # parser can't repair (e.g. key:value pairs INSIDE the prompts array) —
        # a fresh sample almost always parses, so retry the call once.
        for attempt in range(2):
            raw = invoke_llm(
                # max_tokens must fit the FULL JSON (subject + preserve + intent +
                # N enhanced prompts up to ~1500 chars each + negative_prompt +
                # notes). 700 was too small even for one — verbose restyles
                # truncated the JSON before its closing brace, so parsing
                # silently yielded no prompt.
                prompt, system=system, complexity="complex",
                images=vision_imgs, max_tokens=1500 + 800 * (num_options - 1),
                temperature=0.4,
            )
            txt = (raw or "").strip()
            if "```" in txt:
                txt = txt.split("```")[1].lstrip("json").strip() if txt.count("```") >= 2 else txt
            start = txt.find("{")
            try:
                data = _loads_tolerant_json_object(txt[start:]) if start >= 0 else {}
                break
            except Exception as parse_err:
                last_err = parse_err
                logger.info("Reference intent parse failed (attempt %d: %s) — %s; raw: %r",
                            attempt + 1, parse_err,
                            "retrying with a fresh sample" if attempt == 0 else "giving up",
                            txt[:300])
        else:
            raise last_err
    except Exception as e:
        logger.info("Reference intent analysis unavailable (%s) — falling back to raw prompt; raw: %r",
                    e, txt[:300])
        return {"analyzed": False, "enhanced_prompt": "", "enhanced_prompts": [], "negative_prompt": ""}

    # Accept both shapes: "enhanced_prompts" (array — the multi-option contract)
    # and the legacy single "enhanced_prompt" (also what a user-overridden
    # template without {num_options} would produce).
    raw_prompts = data.get("enhanced_prompts")
    if not isinstance(raw_prompts, list):
        raw_prompts = [data.get("enhanced_prompt")]
    prompts = [(p or "").strip()[:_MAX_PROMPT_CHARS] for p in raw_prompts if (p or "").strip()]
    if not prompts:
        return {"analyzed": False, "enhanced_prompt": "", "enhanced_prompts": [], "negative_prompt": ""}
    prompts = prompts[:num_options]

    return {
        "analyzed": True,
        "subject": (data.get("subject") or "").strip()[:200],
        "preserve": (data.get("preserve") or "").strip()[:300],
        "intent": (data.get("intent") or "").strip()[:300],
        "enhanced_prompt": prompts[0],
        "enhanced_prompts": prompts,
        "negative_prompt": (data.get("negative_prompt") or "").strip()[:300],
        "notes": (data.get("notes") or "").strip()[:300],
    }
