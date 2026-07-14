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
) -> dict:
    """Vision-analyze reference images + the user's instruction → enhanced prompt.

    Returns a dict:
      {
        "analyzed": bool,          # False if analysis failed (caller falls back)
        "subject": str,
        "preserve": str,
        "intent": str,
        "enhanced_prompt": str,    # the model-ready caption ("" if not analyzed)
        "negative_prompt": str,
        "notes": str,
      }
    Conservative: on ANY error returns analyzed=False so the caller can fall back
    to the user's raw prompt rather than blocking generation.
    """
    user_prompt = (user_prompt or "").strip()
    if not images or not user_prompt:
        return {"analyzed": False, "enhanced_prompt": "", "negative_prompt": ""}

    try:
        from backend.services.bedrock_client import invoke_llm
        from backend.services.prompt_templates import get_template, get_system_prompt
        from backend.routers.generate_3d import _fit_image_for_vision

        # Cap at 3 references (Qwen's optimal band; also keeps vision payload sane).
        vision_imgs = [_fit_image_for_vision(b) for b in images[:3]]
        prompt = get_template("reference_intent_extraction").format(
            user_prompt=user_prompt[:1200],
            num_images=len(vision_imgs),
            asset_type=(asset_type or "photorealistic").replace("_", " "),
            max_chars=_MAX_PROMPT_CHARS,
        )
        system = get_system_prompt("reference_intent_extraction")
        raw = invoke_llm(
            prompt, system=system, complexity="complex",
            images=vision_imgs, max_tokens=700, temperature=0.4,
        )
        txt = (raw or "").strip()
        if "```" in txt:
            txt = txt.split("```")[1].lstrip("json").strip() if txt.count("```") >= 2 else txt
        start, end = txt.find("{"), txt.rfind("}")
        data = json.loads(txt[start:end + 1]) if start >= 0 and end > start else {}
    except Exception as e:
        logger.info("Reference intent analysis unavailable (%s) — falling back to raw prompt", e)
        return {"analyzed": False, "enhanced_prompt": "", "negative_prompt": ""}

    enhanced = (data.get("enhanced_prompt") or "").strip()[:_MAX_PROMPT_CHARS]
    if not enhanced:
        return {"analyzed": False, "enhanced_prompt": "", "negative_prompt": ""}

    return {
        "analyzed": True,
        "subject": (data.get("subject") or "").strip()[:200],
        "preserve": (data.get("preserve") or "").strip()[:300],
        "intent": (data.get("intent") or "").strip()[:300],
        "enhanced_prompt": enhanced,
        "negative_prompt": (data.get("negative_prompt") or "").strip()[:300],
        "notes": (data.get("notes") or "").strip()[:300],
    }
