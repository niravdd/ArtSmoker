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
    track_prompt_refinement()

    return {"original": body.prompt, "refined": refined, "negative_prompt": negative or ""}


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
