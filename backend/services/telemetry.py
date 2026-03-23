"""ArtSmoker telemetry — anonymous usage tracking via PulseBoard.

Tracks deployments, feature usage, and estimated costs.
Fully opt-out: set ARTSMOKER_TELEMETRY=false to disable all tracking.

No PII is collected. Only anonymous machine fingerprint, version, OS,
and aggregate feature usage counters.
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


# ── Lifecycle Events ─────────────────────────────────────────────────

def track_server_start():
    _track("server_start")


def track_server_stop():
    _track("server_stop")


# ── Frontend Events ──────────────────────────────────────────────────

def track_frontend_load(client_os: str = "", client_browser: str = "", screen: str = ""):
    _track("frontend_load", client_os=client_os, client_browser=client_browser, screen=screen)


# ── Generation Events ────────────────────────────────────────────────

def track_image_generation(model: str = "", cost_usd: float = 0, num_options: int = 1,
                           num_variations: int = 1, duration_ms: float = 0):
    _track("generate_2d_image", model=model, cost_usd=cost_usd,
           num_options=num_options, num_variations=num_variations,
           duration_ms=duration_ms)


def track_type_generation(duration_ms: float = 0):
    _track("generate_type_text", duration_ms=duration_ms)


def track_video_generation(model: str = "", cost_usd: float = 0, duration_seconds: int = 0):
    _track("generate_video", model=model, cost_usd=cost_usd,
           video_duration=duration_seconds)


def track_image_edit(edit_type: str = "", model: str = "", cost_usd: float = 0):
    _track("image_edit", edit_type=edit_type, model=model, cost_usd=cost_usd)


# ── Feature Usage Events ─────────────────────────────────────────────

def track_gallery_load():
    _track("gallery_load")


def track_model_settings_load():
    _track("model_settings_load")


def track_model_settings_refresh():
    _track("model_settings_refresh")


def track_style_analysis(num_images: int = 0):
    _track("style_analysis", num_images=num_images)


def track_voice_transcription():
    _track("voice_transcription")


def track_prompt_refinement():
    _track("prompt_refinement")


# ── Error Events ─────────────────────────────────────────────────────

def track_error(error_type: str = "", message: str = ""):
    _track("error", error_type=error_type, message=message[:200])
