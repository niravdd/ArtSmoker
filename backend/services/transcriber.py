"""Voice transcription service — Amazon Nova Sonic 2.0 speech-to-text via
Bedrock's InvokeModelWithBidirectionalStream API.

boto3 has NO bidirectional-streaming support, so this uses the experimental
Smithy-based SDK (`aws_sdk_bedrock_runtime`, async). Credentials are bridged
from the app's boto3 session so auth behaves identically to every other AWS
call (profiles/SSO/instance roles all work). Nova Sonic is a speech-to-speech
model; the TRANSCRIPT is the USER-role text the service emits as its ASR of
the input audio — we capture that and close the session (a brief assistant
reply may stream before completion; it is ignored).

Input contract: 16 kHz, 16-bit, mono PCM WAV (the frontend's VoiceInput
converts browser recordings to this before upload).
"""

import asyncio
import base64
import io
import json
import logging
import uuid
import wave

from backend.config import settings

logger = logging.getLogger(__name__)

# 0.5 s of 16 kHz 16-bit mono per audioInput event.
_CHUNK_BYTES = 16000
_STREAM_TIMEOUT_S = 60


def _pcm_from_wav(audio_bytes: bytes) -> tuple[bytes, int]:
    """Extract raw PCM frames + sample rate from a 16-bit mono WAV.

    Raises ValueError for anything else — the frontend guarantees this format
    (VoiceInput down-mixes/resamples in the browser), so a mismatch means a
    caller bypassed it.
    """
    with wave.open(io.BytesIO(audio_bytes)) as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ValueError(
                f"Expected 16-bit mono PCM WAV, got {w.getsampwidth() * 8}-bit "
                f"{w.getnchannels()}-channel"
            )
        return w.readframes(w.getnframes()), w.getframerate()


class _Boto3CredentialsResolver:
    """Smithy identity resolver backed by the app's boto3 session — the same
    credential chain (env/profile/SSO/instance role) as every other AWS call.
    Resolved per stream, so short-lived credentials refresh naturally."""

    def __init__(self):
        self._creds = None  # botocore credentials object (self-refreshing)

    async def get_identity(self, **kwargs):
        import boto3
        from smithy_aws_core.identity import AWSCredentialsIdentity

        if self._creds is None:
            self._creds = boto3.Session().get_credentials()
        if self._creds is None:
            raise RuntimeError("No AWS credentials available for Nova Sonic streaming")
        frozen = self._creds.get_frozen_credentials()
        return AWSCredentialsIdentity(
            access_key_id=frozen.access_key,
            secret_access_key=frozen.secret_key,
            session_token=frozen.token,
        )


def _sonic_events(prompt_name: str, content_name: str, sample_rate: int):
    """The Nova Sonic session/prompt/content envelope (input side)."""
    session_start = {"event": {"sessionStart": {"inferenceConfiguration": {
        "maxTokens": 1024, "topP": 0.9, "temperature": 0.7}}}}
    # audioOutputConfiguration is REQUIRED by promptStart even though the
    # assistant's spoken reply is discarded — we only want the USER transcript.
    prompt_start = {"event": {"promptStart": {
        "promptName": prompt_name,
        "textOutputConfiguration": {"mediaType": "text/plain"},
        "audioOutputConfiguration": {
            "mediaType": "audio/lpcm", "sampleRateHertz": 24000,
            "sampleSizeBits": 16, "channelCount": 1,
            "voiceId": "matthew", "encoding": "base64", "audioType": "SPEECH",
        },
    }}}
    # Sonic REQUIRES the first content block to be SYSTEM-role text (the
    # stream is rejected otherwise: "First content must have SYSTEM role").
    # The assistant's reply is discarded — only the USER-role ASR matters —
    # so the instruction just keeps that reply minimal.
    sys_name = f"{content_name}-sys"
    system_events = [
        {"event": {"contentStart": {
            "promptName": prompt_name, "contentName": sys_name,
            "type": "TEXT", "interactive": True, "role": "SYSTEM",
            "textInputConfiguration": {"mediaType": "text/plain"},
        }}},
        {"event": {"textInput": {
            "promptName": prompt_name, "contentName": sys_name,
            "content": "You are a transcription service. Reply only: OK",
        }}},
        {"event": {"contentEnd": {
            "promptName": prompt_name, "contentName": sys_name}}},
    ]
    content_start = {"event": {"contentStart": {
        "promptName": prompt_name, "contentName": content_name,
        "type": "AUDIO", "interactive": True, "role": "USER",
        "audioInputConfiguration": {
            "mediaType": "audio/lpcm", "sampleRateHertz": sample_rate,
            "sampleSizeBits": 16, "channelCount": 1,
            "audioType": "SPEECH", "encoding": "base64",
        },
    }}}
    return session_start, prompt_start, system_events, content_start


async def _sonic_transcribe(
    pcm: bytes, sample_rate: int, model_id: str, region: str,
) -> tuple[str | None, int, int]:
    """Run one bidirectional-stream session; returns (transcript, in_tok, out_tok)."""
    from aws_sdk_bedrock_runtime.client import (
        AsyncBedrockRuntimeClient,
        InvokeModelWithBidirectionalStreamOperationInput,
    )
    from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
    from aws_sdk_bedrock_runtime.models import (
        BidirectionalInputPayloadPart,
        InvokeModelWithBidirectionalStreamInputChunk,
    )

    from smithy_http.aio.crt import AWSCRTHTTPClient

    # resolve() is the only supported constructor (env/config-file resolution);
    # the overrides pin the endpoint/region, swap in the boto3-bridged creds,
    # and use the CRT transport — the default AIOHTTPClient cannot do the
    # duplex (bidirectional) event streaming this operation requires.
    config = await AsyncBedrockRuntimeConfig.resolve(
        endpoint_uri=f"https://bedrock-runtime.{region}.amazonaws.com",
        region=region,
        aws_credentials_identity_resolver=_Boto3CredentialsResolver(),
        transport=AWSCRTHTTPClient(),
    )
    client = AsyncBedrockRuntimeClient(config=config)
    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(model_id=model_id)
    )

    async def send(evt: dict):
        await stream.input_stream.send(InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps(evt).encode())
        ))

    prompt_name, content_name = str(uuid.uuid4()), str(uuid.uuid4())
    session_start, prompt_start, system_events, content_start = _sonic_events(
        prompt_name, content_name, sample_rate)

    transcript_parts: list[str] = []
    in_tokens = out_tokens = 0
    user_done = asyncio.Event()

    async def reader():
        nonlocal in_tokens, out_tokens
        # Role of the currently-open TEXT content block, keyed by contentName —
        # USER-role text is the ASR transcript; ASSISTANT text is the model's
        # reply (ignored).
        roles: dict[str, str] = {}
        output = await stream.await_output()
        out = output[1] if isinstance(output, tuple) else output
        while True:
            event_data = await out.receive()
            if event_data is None:
                break
            part = getattr(event_data, "value", None)
            raw = getattr(part, "bytes_", None) if part else None
            if not raw:
                continue
            evt = json.loads(raw.decode("utf-8")).get("event", {})
            if "contentStart" in evt:
                cs = evt["contentStart"]
                roles[cs.get("contentName", "")] = cs.get("role", "")
            elif "textOutput" in evt:
                to = evt["textOutput"]
                role = to.get("role") or roles.get(to.get("contentName", ""), "")
                if role == "USER" and to.get("content"):
                    transcript_parts.append(to["content"])
            elif "contentEnd" in evt:
                ce = evt["contentEnd"]
                if roles.get(ce.get("contentName", "")) == "USER" and transcript_parts:
                    user_done.set()
            elif "usageEvent" in evt:
                ue = evt["usageEvent"]
                in_tokens = ue.get("totalInputTokens", in_tokens) or in_tokens
                out_tokens = ue.get("totalOutputTokens", out_tokens) or out_tokens
            elif "completionEnd" in evt:
                user_done.set()
                break

    reader_task = asyncio.create_task(reader())
    try:
        await send(session_start)
        await send(prompt_start)
        for evt in system_events:
            await send(evt)
        await send(content_start)
        # Sonic detects end-of-speech via VAD, so pre-recorded audio needs
        # trailing SILENCE to trigger the turn (2 s of zeros) — and the audio
        # content block stays OPEN until the transcript arrives (closing it
        # and going quiet trips Sonic's 55 s idle timeout instead).
        padded = pcm + b"\x00" * (2 * sample_rate * 2)
        b64 = base64.b64encode
        for i in range(0, len(padded), _CHUNK_BYTES):
            await send({"event": {"audioInput": {
                "promptName": prompt_name, "contentName": content_name,
                "content": b64(padded[i:i + _CHUNK_BYTES]).decode("ascii"),
            }}})
            await asyncio.sleep(0.01)  # don't flood the stream

        # Wait for the USER-role transcript (Sonic's ASR of the input), then
        # close the content/prompt/session — the assistant reply isn't needed.
        # Waiting on the reader TOO makes protocol errors fail fast instead of
        # burning the full timeout.
        done_waiter = asyncio.create_task(user_done.wait())
        await asyncio.wait({done_waiter, reader_task},
                           timeout=_STREAM_TIMEOUT_S,
                           return_when=asyncio.FIRST_COMPLETED)
        done_waiter.cancel()
        if reader_task.done() and reader_task.exception():
            raise reader_task.exception()
        if not user_done.is_set():
            logger.warning("Nova Sonic: no USER transcript within %ss", _STREAM_TIMEOUT_S)
        await send({"event": {"contentEnd": {
            "promptName": prompt_name, "contentName": content_name}}})
        await send({"event": {"promptEnd": {"promptName": prompt_name}}})
        await send({"event": {"sessionEnd": {}}})
        # Give usageEvent/completionEnd a moment to arrive, then stop reading.
        try:
            await asyncio.wait_for(asyncio.shield(reader_task), timeout=5)
        except (asyncio.TimeoutError, Exception):  # nosec B110 -- tail harvest is best-effort; primary errors were raised above  # nosemgrep
            pass
    finally:
        reader_task.cancel()
        try:
            await stream.input_stream.close()
        except Exception:  # nosec B110 -- best-effort close of a spent stream  # nosemgrep
            pass

    transcript = " ".join(p.strip() for p in transcript_parts if p.strip()).strip()
    return (transcript or None), in_tokens, out_tokens


async def _attempt_streaming_transcription(
    audio_bytes: bytes,
    content_type: str,
) -> str | None:
    """Transcribe via Nova Sonic; None → caller returns the setup placeholder."""
    from backend.services.model_registry import get_category

    voice_cat = get_category("voice")
    model_id = voice_cat.get("current", "amazon.nova-2-sonic-v1:0")  # registry-first
    region = voice_cat.get("region") or settings.aws_region_images

    try:
        pcm, sample_rate = _pcm_from_wav(audio_bytes)
    except Exception as exc:
        logger.warning("Transcription input is not 16-bit mono PCM WAV (%s): %s",
                       content_type, exc)
        return None
    if not pcm:
        return None

    try:
        logger.info(
            "Nova Sonic transcription: model=%s region=%s pcm=%dB @%dHz",
            model_id, region, len(pcm), sample_rate,
        )
        transcript, in_tokens, out_tokens = await _sonic_transcribe(
            pcm, sample_rate, model_id, region)
    except ImportError:
        logger.warning(
            "aws_sdk_bedrock_runtime not installed — Nova Sonic streaming "
            "unavailable (pip install aws_sdk_bedrock_runtime)."
        )
        return None
    except Exception as exc:
        if "AccessDenied" in type(exc).__name__ or "AccessDenied" in str(exc):
            logger.warning(
                "Access denied for Nova Sonic model '%s' in %s — the IAM role "
                "needs bedrock:InvokeModelWithBidirectionalStream.",
                model_id, region,
            )
            return None
        logger.exception("Nova Sonic streaming transcription failed.")
        return None

    if not transcript:
        logger.warning("Nova Sonic returned no USER transcript.")
        return None

    logger.info("Nova Sonic transcription complete: %d chars, usage %d in / %d out",
                len(transcript), in_tokens, out_tokens)
    # Cost: ONLY from the registry's own price for this model — never a
    # generic-default fallback (that would fabricate a wrong rate).
    if in_tokens or out_tokens:
        try:
            from backend.services.cost_tracker import _registry_llm_price, add_cost
            price = _registry_llm_price(model_id, region)
            if price:
                cost = round((in_tokens / 1e6) * price.get("input_per_mtok", 0)
                             + (out_tokens / 1e6) * price.get("output_per_mtok", 0), 6)
                if cost > 0:
                    add_cost("transcription", cost,
                             f"{model_id}: {in_tokens} in, {out_tokens} out")
        except Exception:
            logger.debug("Transcription cost tracking skipped", exc_info=True)
    return transcript


async def transcribe_audio(
    audio_bytes: bytes,
    content_type: str = "audio/wav",
) -> str:
    """Transcribe audio bytes to text using Amazon Nova Sonic.

    Expects 16-bit mono PCM WAV (the frontend converts recordings before
    upload). Falls back to a recognizable placeholder string when streaming
    is unavailable — the frontend detects the "[Audio received" prefix and
    shows a friendly notice instead of inserting it as prompt text.
    """
    if not audio_bytes:
        logger.warning("transcribe_audio called with empty audio bytes.")
        return ""

    logger.info(
        "Transcription requested: %d bytes, content_type=%s",
        len(audio_bytes),
        content_type,
    )

    transcript = await _attempt_streaming_transcription(audio_bytes, content_type)
    if transcript is not None:
        return transcript

    logger.info(
        "Returning placeholder — Nova Sonic streaming transcription is not "
        "fully configured. Audio received: %d bytes (%s).",
        len(audio_bytes),
        content_type,
    )
    return (
        f"[Audio received but transcription requires Nova Sonic streaming "
        f"setup. Received {len(audio_bytes)} bytes of {content_type} audio. "
        f"Please configure the bidirectional streaming API for full "
        f"transcription.]"
    )
