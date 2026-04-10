"""ArtSmoker telemetry — anonymous usage tracking via PulseBoard.

Tracks deployments, feature usage, and estimated costs.
Fully opt-out: set ARTSMOKER_TELEMETRY=false to disable all tracking.

No PII is collected. Only anonymous machine fingerprint, version, OS,
and aggregate feature usage counters.

Event naming convention: <studio/area>.<action>
  system.*            — server lifecycle, frontend load, errors
  image_studio.*      — 2D image generation, editing, post-processing
  video_studio.*      — video generation
  type_studio.*       — text overlay generation
  chat_studio.*       — LLM chat sessions
  style_library.*     — style analysis
  gallery.*           — gallery browsing
  model_settings.*    — model registry admin
  custom_models.*     — self-hosted model deploy/teardown/invoke (no cost — cost tracked by studio events)

Cost rule: ONE event per generation carries cost_usd. The studio .generate event
includes actual cost. Operational events (custom_models.invoke) carry cost_usd=0.
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
        return
    _pb = PulseBoard(
        api_key="pb_516e85fdb5904c6fa9ec99cf661468d4",
        endpoint="https://d3fjcw1jutg51a.cloudfront.net/ingest",
    )


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
                           num_variations: int = 1, duration_ms: float = 0,
                           breakdown: str = ""):
    """Track a complete image generation with actual cost.

    Called ONCE per generation at the end — not at the start.
    cost_usd is the actual total (LLM refinement + image model + post-processing).
    """
    _track("image_studio.generate", model=model, cost_usd=cost_usd,
           num_options=num_options, num_variations=num_variations,
           duration_ms=duration_ms, breakdown=breakdown)


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


# ── Auto-Update Events ────────────────────────────────────────────

def track_auto_update(updated: bool = False, from_version: str = "", to_version: str = "",
                      commits: int = 0, skipped_reason: str = ""):
    _track("system.auto_update", updated=updated, from_version=from_version,
           to_version=to_version, commits=commits, skipped_reason=skipped_reason)


# ── Custom Model Events ───────────────────────────────────────────

def track_custom_model_deploy(model: str = "", endpoint_type: str = "", instance: str = ""):
    _track("custom_models.deploy", model=model, endpoint_type=endpoint_type, instance=instance)


def track_custom_model_invoke(model: str = "", cost_usd: float = 0, latency_ms: float = 0,
                              predictor_type: str = ""):
    _track("custom_models.invoke", model=model, cost_usd=cost_usd,
           latency_ms=latency_ms, predictor_type=predictor_type)


def track_custom_model_teardown(model: str = ""):
    _track("custom_models.teardown", model=model)
