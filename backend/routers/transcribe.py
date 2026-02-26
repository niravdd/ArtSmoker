"""Audio transcription router — converts uploaded audio files to text using
Amazon Nova Sonic."""

import logging

from fastapi import APIRouter, HTTPException, UploadFile

from backend.services.transcriber import transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcribe", tags=["transcribe"])


@router.post("/")
async def transcribe_audio_endpoint(file: UploadFile):
    """Transcribe an uploaded audio file to text.

    Accepts an audio file (e.g. audio/webm, audio/wav) and returns the
    transcribed text using Amazon Nova Sonic.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    content_type = file.content_type or "audio/webm"
    logger.info(
        "Transcription request: filename=%s, size=%d bytes, content_type=%s",
        file.filename,
        len(audio_bytes),
        content_type,
    )

    try:
        text = transcribe_audio(audio_bytes, content_type)
    except Exception as exc:
        logger.exception("Transcription failed for file '%s'.", file.filename)
        raise HTTPException(
            status_code=502,
            detail=f"Transcription failed: {exc}",
        ) from exc

    logger.info("Transcription complete: %d chars", len(text))
    return {"text": text}
