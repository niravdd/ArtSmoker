"""ArtSmoker telemetry — anonymous usage tracking via PulseBoard.

Tracks deployments, feature usage, and estimated costs.
Fully opt-out: set ARTSMOKER_TELEMETRY=false to disable all tracking.

No PII is collected. Only anonymous machine fingerprint, version, OS,
and aggregate feature usage counters.

Event naming convention: <studio>.<action>
  system.*            — server lifecycle, frontend load, errors
  image_studio.*      — 2D image generation, editing, post-processing
  video_studio.*      — video generation
  type_studio.*       — text overlay generation
  chat_studio.*       — LLM chat sessions
  style_library.*     — style analysis
  gallery.*           — gallery browsing
  model_settings.*    — model registry admin
  custom_models.*     — self-hosted model deploy/teardown/invoke

Cost convention (consistent across ALL studios):
  <studio>.generate   — action event, cost_usd=0 (counts usage, captures metadata)
  <studio>.cost       — cost-only event, cost_usd=actual (PulseBoard increments total_cost_usd only)
  Other events carry cost inline when applicable (edits, post-processing).
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

def track_image_generation(model: str = "", num_options: int = 1,
                           num_variations: int = 1, asset_type: str = "",
                           quality: str = "", duration_ms: float = 0):
    """Image generation action. No cost — cost sent via track_image_cost."""
    _track("image_studio.generate", model=model, cost_usd=0,
           num_options=num_options, num_variations=num_variations,
           num_images=num_options * num_variations,
           asset_type=asset_type, quality=quality,
           duration_ms=duration_ms)


def track_image_cost(cost_usd: float = 0, model: str = "", breakdown: str = ""):
    """Actual cost for an image generation (LLM + image model + post-processing)."""
    _track("image_studio.cost", cost_usd=cost_usd, model=model, breakdown=breakdown)


def track_image_edit(edit_type: str = "", model: str = "", cost_usd: float = 0):
    """Image editing — distinct event per edit type for PulseBoard filtering."""
    # e.g. image_studio.edit.inpaint, image_studio.edit.outpaint
    safe_type = edit_type.replace(" ", "_").lower() if edit_type else "unknown"
    _track(f"image_studio.edit.{safe_type}", model=model, cost_usd=cost_usd)


def track_post_process(action: str = "", model: str = "", cost_usd: float = 0,
                       num_assets: int = 0):
    """Post-processing action (upscale, remove background, SVG)."""
    _track("image_studio.post_process", action=action, model=model,
           cost_usd=cost_usd, num_assets=num_assets)


def track_prompt_refinement(cost_usd: float = 0, asset_type: str = ""):
    _track("image_studio.prompt_preview", cost_usd=cost_usd, asset_type=asset_type)


def track_voice_transcription():
    _track("image_studio.voice_input")


# ── Video Studio Events ─────────────────────────────────────────────

def track_video_generation(model: str = "", duration_seconds: int = 0,
                           task_type: str = ""):
    """Video generation action. No cost — cost sent via track_video_cost."""
    _track("video_studio.generate", model=model, cost_usd=0,
           video_duration=duration_seconds, task_type=task_type)


def track_video_cost(cost_usd: float = 0, model: str = ""):
    """Actual cost for a video generation."""
    _track("video_studio.cost", cost_usd=cost_usd, model=model)


# ── Type Studio Events ──────────────────────────────────────────────

def track_type_generation(duration_ms: float = 0):
    """Type overlay generation action. No cost — cost sent via track_type_cost."""
    _track("type_studio.generate", cost_usd=0, duration_ms=duration_ms)


def track_type_cost(cost_usd: float = 0):
    """Actual cost for a type generation."""
    _track("type_studio.cost", cost_usd=cost_usd)


# ── Chat Studio Events ──────────────────────────────────────────────

def track_chat_session(
    model: str = "", messages: int = 0, input_tokens: int = 0,
    output_tokens: int = 0, duration_seconds: int = 0,
    has_vision: bool = False, compacted: bool = False,
):
    """Chat session summary. No cost — cost sent via track_chat_cost."""
    _track("chat_studio.session", model=model, cost_usd=0,
           messages=messages, input_tokens=input_tokens,
           output_tokens=output_tokens, duration_seconds=duration_seconds,
           has_vision=has_vision, compacted=compacted)


def track_chat_cost(cost_usd: float = 0, model: str = ""):
    """Actual cost for a chat session."""
    _track("chat_studio.cost", cost_usd=cost_usd, model=model)


# ── Style Library Events ────────────────────────────────────────────

def track_style_analysis(num_images: int = 0):
    """Style analysis action. No cost — cost sent via track_style_cost."""
    _track("style_library.analysis", cost_usd=0, num_images=num_images)


def track_style_cost(cost_usd: float = 0):
    """Actual cost for a style analysis."""
    _track("style_library.cost", cost_usd=cost_usd)


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
# Prefixed with studio name so they group with their parent studio in PulseBoard.
# e.g. image_studio.custom.deploy, video_studio.custom.invoke

def _resolve_custom_studio(model: str) -> str:
    """Resolve studio prefix from model key via catalog."""
    try:
        from backend.services.custom_models import get_catalog_model
        entry = get_catalog_model(model)
        if entry:
            return f"{entry['studio']}_studio"
    except Exception:
        pass
    return "image_studio"  # fallback


def track_custom_model_deploy(model: str = "", endpoint_type: str = "", instance: str = ""):
    studio = _resolve_custom_studio(model)
    _track(f"{studio}.custom.deploy", model=model, endpoint_type=endpoint_type, instance=instance)


def track_custom_model_invoke(model: str = "", cost_usd: float = 0, latency_ms: float = 0,
                              predictor_type: str = ""):
    """Operational invocation tracking. cost_usd should be 0 — cost goes on studio .cost event."""
    studio = _resolve_custom_studio(model)
    _track(f"{studio}.custom.invoke", model=model, cost_usd=cost_usd,
           latency_ms=latency_ms, predictor_type=predictor_type)


def track_custom_model_teardown(model: str = ""):
    studio = _resolve_custom_studio(model)
    _track(f"{studio}.custom.teardown", model=model)
