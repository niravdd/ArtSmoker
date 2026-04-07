"""Voice transcription service — uses Amazon Nova Sonic via Bedrock for
speech-to-text conversion."""

import base64
import json
import logging
import uuid

from backend.config import settings
from backend.services.bedrock_client import _get_client

logger = logging.getLogger(__name__)


def _build_session_config_event(session_id: str) -> dict:
    """Build the session configuration event for Nova Sonic streaming."""
    return {
        "event": {
            "sessionConfiguration": {
                "sessionId": session_id,
                "inputAudioConfiguration": {
                    "mediaType": "audio/webm",
                    "encoding": "opus",
                    "sampleRateHertz": 48000,
                    "channelCount": 1,
                },
                "outputTextConfiguration": {
                    "mediaType": "text/plain",
                },
                "inferenceConfiguration": {
                    "maxTokens": 1024,
                    "temperature": 0.0,
                },
            }
        }
    }


def _build_audio_input_event(audio_b64: str, content_type: str) -> dict:
    """Build an audio input event for the streaming API."""
    return {
        "event": {
            "audioInput": {
                "audio": audio_b64,
                "contentType": content_type,
            }
        }
    }


def _build_end_of_audio_event() -> dict:
    """Build the end-of-audio signal event."""
    return {
        "event": {
            "endOfAudio": {}
        }
    }


def _attempt_streaming_transcription(
    audio_bytes: bytes,
    content_type: str,
) -> str | None:
    """Attempt transcription using Nova Sonic's bidirectional streaming API.

    Nova Sonic uses the InvokeModelWithBidirectionalStream API which requires
    an async event stream. This implementation provides a synchronous wrapper.

    Returns the transcribed text, or None if the streaming API is unavailable
    or encounters an error.
    """
    try:
        from backend.services.model_registry import get_category
        voice_cat = get_category("voice")
        model_id = voice_cat.get("current", "amazon.nova-sonic-v1:0")  # From registry, code default as last resort
        region = voice_cat.get("region") or settings.aws_region_images
        client = _get_client(region)
        session_id = str(uuid.uuid4())

        # Check if the bidirectional streaming API is available
        if not hasattr(client, "invoke_model_with_bidirectional_stream"):
            logger.info(
                "Bidirectional streaming API not available on this client. "
                "This requires a compatible boto3 version with streaming support."
            )
            return None

        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

        # Build the event stream payload
        events = [
            _build_session_config_event(session_id),
            _build_audio_input_event(audio_b64, content_type),
            _build_end_of_audio_event(),
        ]

        logger.info(
            "Invoking Nova Sonic streaming transcription: model=%s, "
            "session=%s, audio_size=%d bytes, content_type=%s",
            model_id,
            session_id,
            len(audio_bytes),
            content_type,
        )

        # Invoke the bidirectional streaming API
        response = client.invoke_model_with_bidirectional_stream(
            modelId=model_id,
            body=json.dumps(events),
        )

        # Collect transcript fragments from the response stream
        transcript_parts: list[str] = []
        event_stream = response.get("body", [])

        for event in event_stream:
            if isinstance(event, dict):
                # Look for text output events
                text_output = event.get("textOutput", {})
                if "text" in text_output:
                    transcript_parts.append(text_output["text"])

                # Also check for transcription-specific events
                transcription = event.get("transcription", {})
                if "text" in transcription:
                    transcript_parts.append(transcription["text"])

                # Check for contentBlockDelta (Converse-style)
                delta = event.get("contentBlockDelta", {}).get("delta", {})
                if "text" in delta:
                    transcript_parts.append(delta["text"])

        if transcript_parts:
            full_transcript = " ".join(transcript_parts).strip()
            logger.info(
                "Nova Sonic transcription complete: %d chars",
                len(full_transcript),
            )
            return full_transcript

        logger.warning("Nova Sonic returned no transcript fragments.")
        return None

    except Exception as exc:
        exc_name = type(exc).__name__
        if "AccessDenied" in exc_name or "AccessDenied" in str(exc):
            logger.warning(
                "Access denied for Nova Sonic model '%s'. "
                "Ensure the model is enabled in the %s region.",
                model_id,
                region,
            )
            return None
        logger.exception(
            "Nova Sonic streaming transcription failed; "
            "will fall back to placeholder."
        )
        return None


def transcribe_audio(
    audio_bytes: bytes,
    content_type: str = "audio/webm",
) -> str:
    """Transcribe audio bytes to text using Amazon Nova Sonic.

    This function first attempts to use Nova Sonic's bidirectional streaming
    API for real-time transcription. If the streaming API is unavailable or
    encounters an error, it returns a placeholder message indicating that the
    audio was received but full transcription requires streaming setup.

    Args:
        audio_bytes: Raw audio data bytes.
        content_type: MIME type of the audio (default: "audio/webm").

    Returns:
        The transcribed text, or a placeholder message if transcription
        could not be completed.
    """
    if not audio_bytes:
        logger.warning("transcribe_audio called with empty audio bytes.")
        return ""

    logger.info(
        "Transcription requested: %d bytes, content_type=%s",
        len(audio_bytes),
        content_type,
    )

    # Attempt streaming transcription with Nova Sonic
    transcript = _attempt_streaming_transcription(audio_bytes, content_type)
    if transcript is not None:
        return transcript

    # Fallback: acknowledge receipt but indicate streaming setup is needed
    logger.info(
        "Returning placeholder — Nova Sonic streaming transcription is not "
        "fully configured. Audio received: %d bytes (%s).",
        len(audio_bytes),
        content_type,
    )
    return (
        "[Audio received but transcription requires Nova Sonic streaming setup. "
        f"Received {len(audio_bytes)} bytes of {content_type} audio. "
        "Please configure the bidirectional streaming API for full transcription.]"
    )
