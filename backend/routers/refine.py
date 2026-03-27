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

    try:
        refined = refine_prompt(body.prompt, style_profile, body.asset_type, image_model=body.image_model)
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
