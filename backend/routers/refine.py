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
        logger.exception("Prompt refinement failed.")
        raise HTTPException(
            status_code=502,
            detail=f"Prompt refinement failed: {exc}",
        ) from exc

    negative = get_last_negative_prompt()
    logger.info("Prompt refined: %d chars -> %d chars (negative: %s)", len(body.prompt), len(refined), negative[:80] if negative else "none")

    from backend.services.telemetry import track_prompt_refinement
    track_prompt_refinement(cost_usd=get_total_cost())

    # Detect asset type mismatch — suggest a better type if the prompt implies a scene
    suggestion = _detect_asset_type_mismatch(body.prompt, body.asset_type)

    result = {"original": body.prompt, "refined": refined, "negative_prompt": negative or ""}
    if suggestion:
        result["asset_type_suggestion"] = suggestion
    return result


from pydantic import BaseModel as _BaseModel


class TranslatePreviewRequest(_BaseModel):
    text: str
    source_lang: str = ""


@router.post("/translate-preview")
async def translate_preview(body: TranslatePreviewRequest):
    """Lightweight translation preview — detects language and translates to English.

    Used by the frontend to show a bilingual prompt view (original + English)
    before generation. Fast: single LLM call (~$0.001, <1s).
    """
    from backend.services.prompt_translator import translate_to_english, detect_language

    if not body.text or not body.text.strip():
        return {"original": body.text, "translated": body.text, "source_lang": "en", "was_translated": False}

    result = translate_to_english(body.text, source_lang=body.source_lang)
    return result
