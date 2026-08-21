"""Prompt refinement router — exposes the prompt engineering service as a
standalone endpoint for previewing refined prompts before generation."""

import logging

from fastapi import APIRouter, HTTPException

from backend.models.generation_request import PromptRefineRequest
from backend.models.style_profile import StyleProfile
from backend.services.prompt_engineer import get_last_negative_prompt, refine_prompt
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/refine-prompt", tags=["refine"])


@router.post("/classify-asset-type")
async def classify_asset_type(body: PromptRefineRequest):
    """Use an LLM to classify the ideal asset type for a prompt.

    Returns the recommended type and reason. If it differs from the
    user's current selection, the frontend shows a dialog to switch.
    """
    from backend.services.bedrock_client import invoke_llm
    from backend.services.prompt_templates import get_template, get_system_prompt
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    import json as _json, re as _re

    reset_costs()  # scope LLM cost to THIS request (worker threads are reused)
    try:
        prompt_text = get_template('asset_type_classify').format(user_prompt=body.prompt)
        raw = invoke_llm(
            prompt_text,
            system=get_system_prompt('asset_type_classify'),
            max_tokens=200,
            temperature=0.1,
            complexity="fast",
        ).strip()
        cleaned = _re.sub(r"^```(?:json)?\s*\n?", "", raw)
        cleaned = _re.sub(r"\n?```\s*$", "", cleaned)
        result = _json.loads(cleaned.strip())

        recommended = result.get("recommended", "game_asset")
        reason = result.get("reason", "")
        confidence = result.get("confidence", "medium")

        # Only suggest a change if the recommended type differs from current
        current = body.asset_type.value if hasattr(body.asset_type, 'value') else str(body.asset_type)
        if recommended != current and confidence in ("high", "medium"):
            return {
                "current": current,
                "suggested": recommended,
                "reason": reason,
                "confidence": confidence,
                "mismatch": True,
            }
        return {"current": current, "suggested": current, "mismatch": False}

    except Exception as exc:
        logger.warning("Asset type classification failed: %s", exc)
        return {"current": str(body.asset_type), "suggested": str(body.asset_type), "mismatch": False}
    finally:
        # Report the LLM cost even if post-call parsing failed — no missed spend.
        track_aux_llm_cost("classify_asset_type", get_total_cost())


def _detect_asset_type_mismatch(prompt: str, asset_type) -> dict | None:
    """Detect when the user's prompt implies a different asset type than selected.

    Returns a suggestion dict or None if the current type seems appropriate.
    """
    from backend.models.generation_request import AssetType
    lower = prompt.lower()
    words = len(prompt.split())

    # Scene/environment indicators — user describes a setting, not an isolated object
    scene_keywords = [
        # Explicit scene words
        "scene", "landscape", "environment", "background", "panorama", "cinematic",
        "wide shot", "camera angle", "dramatic sky",
        # Natural environments
        "village", "city", "town", "forest", "ocean", "sea", "mountain", "valley",
        "desert", "beach", "river", "lake", "island", "cave", "dungeon",
        # Sky/weather
        "sunset", "sunrise", "horizon", "sky", "clouds", "rain", "storm", "weather",
        "golden hour", "moonlight", "starry",
        # Structures as settings
        "castle", "temple", "church", "tavern", "marketplace", "harbor", "port",
        "bridge", "tower", "ruins", "garden", "courtyard",
        # Vehicles as settings (character ON something)
        "on a ship", "on a boat", "on a horse", "on a dragon", "on a throne",
        "on deck", "at the helm", "behind the wheel",
        # Spatial prepositions (character IN a place)
        "standing in", "walking through", "sitting on", "sitting in", "looking at",
        "standing on", "riding", "sailing", "flying over",
        "behind the", "in front of", "in the distance", "surrounded by",
        # Composition cues
        "towering", "billowing", "churning", "sprawling", "vast",
    ]

    # Character/figure indicators — prompt describes a person or humanoid
    character_keywords = [
        # Explicit character words
        "character", "figure", "person", "hero", "heroine", "protagonist",
        # Professions/roles
        "warrior", "knight", "archer", "mage", "wizard", "witch", "thief", "rogue",
        "pirate", "captain", "soldier", "guard", "samurai", "ninja", "assassin",
        "sailor", "pilot", "merchant", "blacksmith", "healer", "priest", "monk",
        "king", "queen", "prince", "princess", "emperor", "goddess", "god",
        "hunter", "ranger", "bard", "paladin", "necromancer", "druid",
        # Gender/age descriptors (strong character signal)
        "female", "male", "woman", "man", "girl", "boy", "lady", "lord",
        "young", "old", "elderly", "child", "teen",
        # Body/appearance
        "wearing", "holding", "wielding", "carrying", "gripping",
        "standing", "sitting", "kneeling", "crouching", "running", "fighting",
        "full body", "half body", "portrait", "face", "pose",
        "armor", "cloak", "robe", "dress", "uniform", "outfit", "helmet",
        "sword", "bow", "staff", "shield", "weapon",
        # Hair/features
        "hair", "eyes", "beard", "scar",
    ]

    scene_hits = sum(1 for kw in scene_keywords if kw in lower)
    char_hits = sum(1 for kw in character_keywords if kw in lower)

    if asset_type == AssetType.GAME_ASSET:
        # Character in a scene — suggest Character type
        if char_hits >= 2 and scene_hits >= 1:
            return {
                "current": "game_asset",
                "suggested": "character",
                "reason": "Your prompt describes a character in a setting. 'Character' type keeps the figure as the focal point while preserving scene context. 'Game Asset' forces an isolated sprite on a transparent background.",
            }
        # Pure character (no scene) — suggest Character type
        if char_hits >= 2:
            return {
                "current": "game_asset",
                "suggested": "character",
                "reason": "Your prompt describes a character. 'Character' type optimizes for figure proportions, pose, and silhouette readability.",
            }
        # Scene/environment — suggest Environment type
        if scene_hits >= 2:
            return {
                "current": "game_asset",
                "suggested": "environment",
                "reason": "Your prompt describes a scene or environment. 'Environment' type preserves the full composition with depth and atmosphere. 'Game Asset' forces an isolated object on a transparent background.",
            }

    return None


@router.post("/")
async def refine_prompt_endpoint(body: PromptRefineRequest):
    """Refine a user prompt into a detailed image-generation prompt.

    Optionally loads a style profile to incorporate generation hints into the
    refined output. Returns both the original and refined prompts for
    comparison.
    """
    # Load style profile if specified
    style_profile: StyleProfile | None = None
    if body.style_id:
        data = store.load_style_profile(body.style_id)
        if data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Style '{body.style_id}' not found.",
            )
        style_profile = StyleProfile(**data)
        logger.info("Loaded style profile '%s' for prompt refinement.", body.style_id)

    # Translate non-English prompt before refinement
    prompt_to_refine = body.prompt
    original_language = "en"
    try:
        from backend.services.prompt_translator import translate_to_english
        tr = translate_to_english(body.prompt)
        original_language = tr["source_lang"]
        if tr["was_translated"]:
            prompt_to_refine = tr["translated"]
    except Exception:
        pass

    from backend.services.cost_tracker import reset_costs, get_total_cost
    reset_costs()

    try:
        refined = refine_prompt(prompt_to_refine, style_profile, body.asset_type, image_model=body.image_model)
    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.exception("Prompt refinement failed.")
        raise HTTPException(
            status_code=502,
            detail=f"Prompt refinement failed: {exc}",
        ) from exc

    negative = get_last_negative_prompt()
    logger.info("Prompt refined: %d chars -> %d chars (negative: %s)", len(body.prompt), len(refined), negative[:80] if negative else "none")

    from backend.services.telemetry import track_prompt_refinement
    track_prompt_refinement(cost_usd=get_total_cost(),
                            asset_type=body.asset_type.value if body.asset_type else "")

    # Detect asset type mismatch — suggest a better type if the prompt implies a scene
    suggestion = _detect_asset_type_mismatch(body.prompt, body.asset_type)

    result = {"original": body.prompt, "refined": refined, "negative_prompt": negative or ""}
    if suggestion:
        result["asset_type_suggestion"] = suggestion
    return result


from pydantic import BaseModel as _BaseModel


# ── Prompt Designer (Decompose / Recompose) ──────────────────────────────

class DecomposeRequest(_BaseModel):
    prompt: str
    style_id: str | None = None
    asset_type: str = "photorealistic"
    image_model: str = ""


@router.post("/decompose")
async def decompose_prompt(body: DecomposeRequest):
    """Decompose a user prompt into structured visual components.

    If the prompt is non-English, translates it first and includes both
    the original and English versions in the response. The decomposition
    always works on the English version for consistent, high-quality results.

    Returns a JSON structure with editable fields: subject, scene,
    composition, lighting, style (including color palette with hex + swatches).
    """
    from backend.services.bedrock_client import invoke_llm
    from backend.services.prompt_templates import get_template, get_system_prompt
    from backend.services.prompt_engineer import _build_style_section, _asset_type_context
    from backend.models.generation_request import AssetType
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    import json as _json, re as _re

    reset_costs()  # scope LLM cost (translation + decomposition) to THIS request
    # Translate non-English prompts to English for consistent decomposition
    prompt_for_decompose = body.prompt
    original_language = "en"
    original_prompt = None
    try:
        from backend.services.prompt_translator import translate_to_english
        tr = translate_to_english(body.prompt)
        if tr["was_translated"]:
            original_language = tr["source_lang"]
            original_prompt = body.prompt  # Keep the original non-English text
            prompt_for_decompose = tr["translated"]
            logger.info("Prompt Designer: translated %s → English for decomposition", original_language)
    except Exception:
        pass

    # Build context
    style_profile = None
    if body.style_id:
        data = store.load_style_profile(body.style_id)
        if data:
            from backend.models.style_profile import StyleProfile
            style_profile = StyleProfile(**data)
    style_section = _build_style_section(style_profile)

    try:
        asset_enum = AssetType(body.asset_type)
    except ValueError:
        asset_enum = AssetType.GAME_ASSET
    asset_context = _asset_type_context(asset_enum)

    from backend.services.prompt_engineer import _get_model_label, get_model_guidance, _DEFAULT_MODEL_INSTRUCTIONS
    model_name = _get_model_label(body.image_model) if body.image_model else "AI image generator"
    model_instructions = (get_model_guidance(body.image_model) or _DEFAULT_MODEL_INSTRUCTIONS) if body.image_model else _DEFAULT_MODEL_INSTRUCTIONS

    prompt_text = get_template('prompt_decompose').format(
        user_prompt=prompt_for_decompose,
        style_section=style_section,
        asset_context=asset_context,
        model_name=model_name,
        model_specific_instructions=model_instructions,
    )

    try:
        raw = invoke_llm(
            prompt_text,
            system=get_system_prompt('prompt_decompose'),
            max_tokens=2000,
            temperature=0.3,
            complexity="fast",
        ).strip()
        cleaned = _re.sub(r"^```(?:json)?\s*\n?", "", raw)
        cleaned = _re.sub(r"\n?```\s*$", "", cleaned)
        result = _json.loads(cleaned.strip())

        # Include translation metadata so frontend can show both versions
        result["_meta"] = {
            "original_prompt": original_prompt,  # None if already English
            "english_prompt": prompt_for_decompose,
            "original_language": original_language,
            "was_translated": original_prompt is not None,
        }

        return result
    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.exception("Prompt decomposition failed")
        raise HTTPException(502, detail=f"Decomposition failed: {exc}")
    finally:
        # Report LLM cost (translation + decomposition) even on failure — no missed spend.
        track_aux_llm_cost("prompt_decompose", get_total_cost())


class RecomposeRequest(_BaseModel):
    structured: dict
    image_model: str = "sd35_large"


@router.post("/recompose")
async def recompose_prompt(body: RecomposeRequest):
    """Recompose structured visual components into a flat image generation prompt."""
    from backend.services.bedrock_client import invoke_llm
    from backend.services.prompt_templates import get_template, get_system_prompt
    from backend.services.prompt_engineer import get_prompt_limit, get_optimal_length, get_model_guidance, _get_model_label, _build_style_section, _DEFAULT_MODEL_INSTRUCTIONS
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    import json as _json, re as _re

    reset_costs()  # scope LLM cost to THIS request
    max_chars = get_prompt_limit(body.image_model)
    optimal_length = get_optimal_length(body.image_model)
    model_name = _get_model_label(body.image_model)
    model_instructions = get_model_guidance(body.image_model) or _DEFAULT_MODEL_INSTRUCTIONS

    prompt_text = get_template('prompt_recompose').format(
        structured_json=_json.dumps(body.structured, indent=2),
        model_name=model_name,
        model_specific_instructions=model_instructions,
        max_chars=max_chars,
        optimal_length=f"{optimal_length} words",
        style_section="(Style already embedded in the structured specifications above)",
    )

    try:
        raw = invoke_llm(
            prompt_text,
            system=get_system_prompt('prompt_recompose'),
            max_tokens=1500,
            temperature=0.3,
            complexity="fast",
        ).strip()

        # Split out NEGATIVE line
        main_prompt = raw
        negative = ""
        for marker in ["NEGATIVE:", "Negative:"]:
            if marker in raw:
                parts = raw.split(marker, 1)
                main_prompt = parts[0].strip()
                negative = parts[1].strip()
                break

        return {
            "prompt": main_prompt,
            "negative_prompt": negative,
            "model": body.image_model,
            "chars": len(main_prompt),
        }
    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.exception("Prompt recomposition failed")
        raise HTTPException(502, detail=f"Recomposition failed: {exc}")
    finally:
        track_aux_llm_cost("prompt_recompose", get_total_cost())


class TranslatePreviewRequest(_BaseModel):
    text: str
    source_lang: str = ""
    ui_lang: str = ""


@router.post("/translate-preview")
async def translate_preview(body: TranslatePreviewRequest):
    """Lightweight translation preview — detects language and translates to English.

    Used by the frontend to show a bilingual prompt view (original + English)
    before generation. Fast: single LLM call (~$0.001, <1s).

    ``ui_lang`` (the frontend language selection) is forwarded as a soft
    detection hint — content signals still take precedence.
    """
    from backend.services.prompt_translator import translate_to_english

    if not body.text or not body.text.strip():
        return {"original": body.text, "translated": body.text, "source_lang": "en", "was_translated": False}

    result = translate_to_english(body.text, source_lang=body.source_lang, ui_lang=body.ui_lang)
    return result
