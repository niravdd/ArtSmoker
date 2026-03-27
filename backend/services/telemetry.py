"""ArtSmoker telemetry — anonymous usage tracking via PulseBoard.

Tracks deployments, feature usage, and estimated costs.
Fully opt-out: set ARTSMOKER_TELEMETRY=false to disable all tracking.

No PII is collected. Only anonymous machine fingerprint, version, OS,
and aggregate feature usage counters.

Event naming convention: <studio/area>.<action>
  system.*            — server lifecycle, frontend load, errors
  image_studio.*      — 2D image generation, editing, post-processing, cost
  video_studio.*      — video generation
  type_studio.*       — text overlay generation
  chat_studio.*       — LLM chat sessions
  style_library.*     — style analysis
  gallery.*           — gallery browsing
  model_settings.*    — model registry admin
"""

import logging
import time

from backend.config import settings, APP_VERSION
from backend.services.pulseboard import PulseBoard

logger = logging.getLogger(__name__)

VERSION = APP_VERSION

_pb: PulseBoard | None = None


def init():
    """Initialize telemetry. Call once on app startup."""
    global _pb
    if not settings.telemetry_enabled:
        logger.info("Telemetry disabled (ARTSMOKER_TELEMETRY=false)")
        return
    _pb = PulseBoard(
        api_key="pb_516e85fdb5904c6fa9ec99cf661468d4",
        endpoint="https://d3fjcw1jutg51a.cloudfront.net/ingest",
    )
    logger.info("Telemetry initialized (PulseBoard)")


def _track(event: str, **props):
    """Fire-and-forget event. No-op if telemetry is disabled."""
    if _pb:
        props.setdefault("version", VERSION)
        _pb.track(event, **props)


# ── System Events ────────────────────────────────────────────────────

def track_server_start():
    _track("system.server_start")


def track_server_stop():
    _track("system.server_stop")


def track_frontend_load(client_os: str = "", client_browser: str = "", screen: str = ""):
    _track("system.frontend_load", client_os=client_os, client_browser=client_browser, screen=screen)


def track_error(error_type: str = "", message: str = ""):
    _track("system.error", error_type=error_type, message=message[:200])


# ── Image Studio Events ─────────────────────────────────────────────

def track_image_generation(model: str = "", cost_usd: float = 0, num_options: int = 1,
                           num_variations: int = 1, duration_ms: float = 0):
    """Image generation started. cost_usd=0 here — actual cost sent via track_image_cost."""
    _track("image_studio.generate", model=model, cost_usd=0,
           num_options=num_options, num_variations=num_variations,
           duration_ms=duration_ms)


def track_image_cost(cost_usd: float = 0, model: str = "", breakdown: str = ""):
    """Actual total cost for an image generation (LLM refinement + image model + post-processing)."""
    _track("image_studio.cost", cost_usd=cost_usd, model=model, breakdown=breakdown)


def track_image_edit(edit_type: str = "", model: str = "", cost_usd: float = 0):
    _track("image_studio.edit", edit_type=edit_type, model=model, cost_usd=cost_usd)


def track_post_process(action: str = "", model: str = "", cost_usd: float = 0):
    """Post-processing action (upscale, remove background)."""
    _track("image_studio.post_process", action=action, model=model, cost_usd=cost_usd)


def track_prompt_refinement(cost_usd: float = 0):
    _track("image_studio.prompt_preview", cost_usd=cost_usd)


def track_voice_transcription():
    _track("image_studio.voice_input")


# ── Video Studio Events ─────────────────────────────────────────────

def track_video_generation(model: str = "", cost_usd: float = 0, duration_seconds: int = 0):
    _track("video_studio.generate", model=model, cost_usd=cost_usd,
           video_duration=duration_seconds)


# ── Type Studio Events ──────────────────────────────────────────────

def track_type_generation(cost_usd: float = 0, duration_ms: float = 0):
    _track("type_studio.generate", cost_usd=cost_usd, duration_ms=duration_ms)


# ── Chat Studio Events ──────────────────────────────────────────────

def track_chat_session(
    model: str = "", messages: int = 0, input_tokens: int = 0,
    output_tokens: int = 0, cost_usd: float = 0, duration_seconds: int = 0,
    has_vision: bool = False, compacted: bool = False,
):
    """Single summary event per chat session interaction.

    Fired when a user navigates away from a session — captures the full
    session's cost and usage in one event, avoiding per-message clutter.
    """
    _track("chat_studio.session", model=model, cost_usd=cost_usd,
           messages=messages, input_tokens=input_tokens,
           output_tokens=output_tokens, duration_seconds=duration_seconds,
           has_vision=has_vision, compacted=compacted)


# ── Style Library Events ────────────────────────────────────────────

def track_style_analysis(num_images: int = 0, cost_usd: float = 0):
    _track("style_library.analysis", num_images=num_images, cost_usd=cost_usd)


# ── Gallery Events ──────────────────────────────────────────────────

def track_gallery_load():
    _track("gallery.load")


# ── Model Settings Events ───────────────────────────────────────────

def track_model_settings_load():
    _track("model_settings.load")


def track_model_settings_refresh():
    _track("model_settings.sync_aws")
