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

import json
import logging
import re
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
        # PUBLIC PulseBoard project ingest key — a write-only telemetry identifier
        # (like a Sentry DSN or PostHog project key), intended to ship in source.
        # It only lets the app SEND anonymous usage events to this project; it is
        # NOT a secret credential and grants no read access. Allowlisted in
        # .gitleaks.toml so secret scanners don't misflag it as a leak.
        api_key="pb_516e85fdb5904c6fa9ec99cf661468d4",  # gitleaks:allow — public ingest key, not a secret
        endpoint="https://d3fjcw1jutg51a.cloudfront.net/ingest",
    )


# ── Privacy filter ───────────────────────────────────────────────────
# Telemetry carries ArtSmoker events only — never user data. Callers may pass raw
# error text, reasons or labels (their console/log lines keep the full detail);
# everything is filtered HERE, the single point every event passes through:
#   • per event: error/reason/breakdown fields are reduced to fixed codes/numbers;
#   • last-line guard: any string property that looks like a file path, URL, ARN,
#     12-digit account ID or email is replaced, and strings are length-capped.
_REDACTED = "[redacted]"
_MAX_STR = 500
_SENSITIVE = re.compile(
    r"(?:^|[\s'\"(=:,])(?:~|\.{1,2})?/[^\s/]+/"   # POSIX path (/a/b, ~/a/, ./a/)
    r"|[A-Za-z]:\\"                                # Windows path
    r"|[A-Za-z][A-Za-z0-9+.-]*://"                 # any URL (https://, s3://, file://)
    r"|\barn:aws"                                  # AWS ARN
    r"|(?<!\d)\d{12}(?!\d)"                        # AWS account ID
    r"|[\w.+-]+@[\w-]+\.[\w.]+"                    # email address
)
_CODE = re.compile(r"[A-Za-z0-9_.]{1,60}")
_AWS_ACTION = re.compile(r"[a-z0-9-]+:[A-Za-z0-9]+")
_AWS_ERROR_CODE = re.compile(r"\b([A-Z][A-Za-z]+(?:Exception|Error|Capacity|Exceeded|Fault|Denied))\b")


def _code(value: str, default: str = "other") -> str:
    """A bare identifier (exception class, fixed code) or `default`."""
    value = (value or "").strip()
    return value if _CODE.fullmatch(value) else (default if value else "")


def _reason_code(text: str) -> str:
    """An AWS error code found in a failure reason (e.g. InsufficientInstanceCapacity),
    else 'other' — never the reason text itself (it can name buckets, keys, ARNs)."""
    if not text:
        return ""
    m = _AWS_ERROR_CODE.search(text)
    return m.group(1) if m else "other"


def _breakdown_summary(breakdown) -> str:
    """Cost breakdown reduced to {component: {cost, count}} — the free-text `details`
    (labels, filenames, sizes) are dropped. Non-JSON breakdowns are dropped entirely."""
    try:
        data = json.loads(breakdown) if isinstance(breakdown, str) else breakdown
    except (TypeError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    out = {}
    for component, g in data.items():
        if isinstance(g, dict) and _CODE.fullmatch(str(component)):
            out[component] = {"cost": g.get("cost", 0), "count": g.get("count", 0)}
    return json.dumps(out) if out else ""


def _scrub(event: str, props: dict) -> dict:
    """Last-line guard over every string property (see the block comment above)."""
    for key, value in props.items():
        if not isinstance(value, str):
            continue
        if _SENSITIVE.search(value):
            logger.debug("Telemetry: redacted property %r on %s", key, event)
            props[key] = _REDACTED
        elif len(value) > _MAX_STR:
            props[key] = value[:_MAX_STR]
    return props


def _track(event: str, **props):
    """Fire-and-forget event. No-op if telemetry is disabled."""
    if _pb:
        props.setdefault("version", VERSION)
        event = re.sub(r"[^a-z0-9_.]", "_", (event or "").lower())[:100]
        _pb.track(event, **_scrub(event, props))


# ── System Events ────────────────────────────────────────────────────

def track_server_start():
    _track("system.server_start")


def track_server_stop():
    _track("system.server_stop")


def track_frontend_load(client_os: str = "", client_browser: str = "", screen: str = ""):
    _track("system.frontend_load", client_os=client_os, client_browser=client_browser, screen=screen)


def track_error(error_type: str = "", message: str = ""):
    """An error EVENT — the error type only. The message (exception text, request
    path) stays in the console/log; the only message sent is an AWS action name
    (service:Operation) for aws_permission_denied."""
    props = {"error_type": _code(error_type)}
    if error_type == "aws_permission_denied" and _AWS_ACTION.fullmatch(message or ""):
        props["action"] = message
    _track("system.error", **props)


# ── Image Studio Events ─────────────────────────────────────────────

def track_image_generation(model: str = "", num_options: int = 1,
                           num_variations: int = 1, asset_type: str = "",
                           quality: str = "", duration_ms: float = 0,
                           reference_mode: str = ""):
    """Image generation action. No cost — cost sent via track_image_cost.

    reference_mode ("inspired" | "match") tags an Image-Inspiration (reference-guided)
    job so PulseBoard can distinguish it; "" (default) = a normal text-to-image job.
    """
    _track("image_studio.generate", model=model, cost_usd=0,
           num_options=num_options, num_variations=num_variations,
           num_images=num_options * num_variations,
           asset_type=asset_type, quality=quality,
           duration_ms=duration_ms, reference_mode=reference_mode)


def track_image_cost(cost_usd: float = 0, model: str = "", breakdown: str = ""):
    """Actual cost for an image generation (LLM + image model + post-processing)."""
    _track("image_studio.cost", cost_usd=cost_usd, model=model, breakdown=_breakdown_summary(breakdown))


def track_image_edit(edit_type: str = "", model: str = "", cost_usd: float = 0):
    """Image editing — distinct event per edit type for PulseBoard filtering."""
    safe_type = edit_type.replace(" ", "_").lower() if edit_type else "unknown"
    _track(f"image_studio.edit.{safe_type}", model=model, cost_usd=cost_usd)
    if cost_usd > 0:
        _track("image_studio.edit.cost", cost_usd=cost_usd, model=model, edit_type=safe_type)


def track_post_process(action: str = "", model: str = "", cost_usd: float = 0,
                       num_assets: int = 0):
    """Post-processing action (upscale, remove background, SVG)."""
    _track("image_studio.post_process", action=action, model=model,
           cost_usd=cost_usd, num_assets=num_assets)
    if cost_usd > 0:
        _track("image_studio.post_process.cost", cost_usd=cost_usd, action=action)


def track_prompt_refinement(cost_usd: float = 0, asset_type: str = ""):
    _track("image_studio.prompt_preview", cost_usd=cost_usd, asset_type=asset_type)
    if cost_usd > 0:
        _track("image_studio.prompt_preview.cost", cost_usd=cost_usd)


def track_voice_transcription(cost_usd: float = 0):
    """Voice transcription action; cost (Nova Sonic tokens × registry price) is a
    separate .cost event per convention — $0 until the Sync captures Sonic pricing
    AND the stream reports usage (never a fabricated default rate)."""
    _track("image_studio.voice_input", cost_usd=0)
    if cost_usd > 0:
        _track("image_studio.voice_input.cost", cost_usd=cost_usd)


def track_aux_llm_cost(operation: str = "", cost_usd: float = 0, studio: str = "image_studio"):
    """Cost for a STANDALONE auxiliary LLM operation that runs as its own request —
    prompt classify/decompose/recompose, reference analysis, moderation pre-check,
    edit-prompt suggestion, template enhance, chat compact — i.e. NOT folded into a
    generation request's cost event. Emits an action event plus a `.cost` event so
    PulseBoard's aggregate total_cost includes this spend (previously unreported).

    Pass the request-scoped get_total_cost() as cost_usd; the endpoint MUST call
    reset_costs() at entry so the figure isn't contaminated by a prior request that
    ran on the same worker thread (costs are ContextVar/thread-scoped)."""
    op = (operation or "aux").replace(" ", "_").replace("-", "_").lower()
    _track(f"{studio}.aux.{op}", cost_usd=0)
    if cost_usd and cost_usd > 0:
        _track(f"{studio}.aux.cost", cost_usd=cost_usd, operation=op)


# ── Collections (Set Generation) Events — SPEC §18.10 ───────────────
# Action events carry cost_usd=0; real spend is a separate `collection_studio.cost`
# event (the .cost convention) so PulseBoard's aggregate total includes it once.

def _collection_cost(cost_usd: float, operation: str):
    if cost_usd and cost_usd > 0:
        _track("collection_studio.cost", cost_usd=cost_usd, operation=operation)

def track_collection_designed(batch_count: int = 0, models: str = "", cost_usd: float = 0):
    _track("collection_studio.designed", cost_usd=0, batch_count=batch_count, models=models)
    _collection_cost(cost_usd, "design")

def track_collection_roster_regenerated(cost_usd: float = 0):
    _track("collection_studio.roster_regenerated", cost_usd=0)
    _collection_cost(cost_usd, "roster_regenerate")

def track_collection_art_direction_edited(cost_usd: float = 0, operation: str = "recompose_all"):
    # operation: "art_direction" (draft it, POST /art-direction) | "recompose_all"
    _track("collection_studio.art_direction_edited", cost_usd=0)
    _collection_cost(cost_usd, operation)

def track_collection_art_direction_lifted(cost_usd: float = 0):
    _track("collection_studio.art_direction_lifted", cost_usd=0)
    _collection_cost(cost_usd, "lift_art_direction")

def track_collection_mode_enabled():
    # UI-only (the Collections toggle makes no API call); sent by the client beacon.
    _track("collection_studio.mode_enabled", cost_usd=0)

def track_collection_batch_regenerated(cost_usd: float = 0):
    _track("collection_studio.batch_regenerated", cost_usd=0)
    _collection_cost(cost_usd, "batch_regenerate")

def track_collection_generation(batches: int = 0, options: int = 1, variations: int = 1, models: str = "",
                                image_inspired: bool = False):
    _track("collection_studio.generate", cost_usd=0, batches=batches, options=options,
           variations=variations, num_images=batches * options * variations, models=models,
           image_inspired=image_inspired)

def track_collection_generation_complete(success: int = 0, partial: int = 0, cost_usd: float = 0):
    _track("collection_studio.generate_complete", cost_usd=0, success=success, partial=partial)
    _collection_cost(cost_usd, "generation")

def track_collection_hero_anchor_used(batch_count: int = 0):
    _track("collection_studio.hero_anchor", cost_usd=0, batch_count=batch_count)

def track_collection_3d_handoff(job_count: int = 0):
    # Fired only when ≥1 job was submitted; the 3D compute cost is reported per job
    # at completion (generate_3d), like a single-asset 3D run.
    _track("collection_studio.3d_handoff", cost_usd=0, job_count=job_count)

def track_collection_export(engine: str = "", fmt: str = "", model_count: int = 0):
    # One event per collection 3D zip (the per-model builds fire no asset.dl.*).
    _track("collection_studio.export", cost_usd=0, engine=engine, format=fmt, model_count=model_count)

def track_collection_download(artefacts: str = "", file_count: int = 0, job_count: int = 0):
    # One event per collection image zip. Cutouts it had to make are reported by the
    # single-asset export (image_studio.post_process, with any Bedrock cost).
    _track("collection_studio.download", cost_usd=0, artefacts=artefacts,
           file_count=file_count, job_count=job_count)

def track_collection_version_selected(version: int = 0):
    _track("collection_studio.version_selected", cost_usd=0, version=version)

def track_collection_asset_type_checked(current: str = "", suggested: str = "",
                                        mismatch: bool = False, unsupported: bool = False):
    # Pre-spend Asset-Type check; its LLM cost rides classify_asset_type's aux .cost event.
    _track("collection_studio.asset_type_checked", cost_usd=0, current=current,
           suggested=suggested, mismatch=mismatch, unsupported=unsupported)


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


def track_version_check(source: str = "", current: str = "", latest: str = "",
                        update_available: bool = False, error: str = ""):
    """A version check was performed — fired on EVERY check regardless of outcome,
    so long-running servers emit a daily heartbeat and the fleet's version-check
    cadence is visible. The SOURCE is encoded in the event NAME (PulseBoard
    aggregates/displays by name only):
        system.start.version_check   (server startup)
        system.24h.version_check     (the daily background scheduler)
        system.manual.version_check  (the /check-update endpoint)
    Distinct from system.auto_update, which fires only when an update is applied."""
    tag = {"startup": "start", "periodic": "24h", "manual": "manual"}.get(source, source or "unknown")
    # `error` (exception / git output — can hold local paths or remote URLs) is
    # reduced to a flag; the detail is in the auto-update log line.
    _track(f"system.{tag}.version_check", source=source, current=current, latest=latest,
           update_available=update_available, failed=bool(error))


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
                              predictor_type: str = "", cost_is_estimate: bool = False):
    """Invocation tracking with compute cost for visibility.

    cost_usd is the SageMaker compute cost (actual if from async_jobs,
    estimated if from sync invoker). Labeled with est_cost_usd vs cost_usd
    so PulseBoard can distinguish. Aggregate totals come only from .cost events.
    """
    studio = _resolve_custom_studio(model)
    props = {"model": model, "latency_ms": latency_ms, "predictor_type": predictor_type}
    if cost_is_estimate:
        props["est_cost_usd"] = cost_usd
        props["cost_usd"] = 0  # Don't show estimated as if actual
    else:
        props["cost_usd"] = cost_usd
    _track(f"{studio}.custom.invoke", **props)


def track_custom_model_teardown(model: str = ""):
    studio = _resolve_custom_studio(model)
    _track(f"{studio}.custom.teardown", model=model)


def track_custom_model_deploy_failed(model: str = "", instance: str = "", reason: str = ""):
    """A self-hosted deploy failed (e.g. InsufficientInstanceCapacity) and was
    auto-torn-down. Recorded so recurring capacity shortages are visible over time."""
    studio = _resolve_custom_studio(model)
    _track(f"{studio}.custom.deploy_failed", model=model, instance=instance, reason=_reason_code(reason))


def track_custom_model_deploy_ready(model: str = "", instance: str = ""):
    """A self-hosted deploy finished loading and is ready to serve. Completes the
    deploy lifecycle (deploy → ready|failed → teardown) in telemetry."""
    studio = _resolve_custom_studio(model)
    _track(f"{studio}.custom.deploy_ready", model=model, instance=instance)


# ── Image-to-3D Events ───────────────────────────────────────────────
# 3D runs on a self-hosted GPU SageMaker endpoint. Action event at submit
# (cost=0); the actual GPU compute cost is reported at completion via
# track_custom_model_invoke + image_studio.cost (see generate_3d._track_3d_completion).

def track_3d_generation(model: str = "", pipeline: str = "", asset_type: str = "",
                        quality: str = "", instance: str = ""):
    """Image-to-3D generation submitted. No cost — compute cost sent at completion."""
    _track("image_studio.three_d.generate", model=model, cost_usd=0,
           pipeline=pipeline, asset_type=asset_type, quality=quality, instance=instance)


# ── Gallery Import Event ─────────────────────────────────────────────

def track_download(file_format: str = "", asset_type: str = "", kind: str = "",
                   engine_target: str = "", model: str = "", variant: str = ""):
    """A user downloaded an asset file — adoption signal for format/engine preference.

    PulseBoard aggregates ONLY by event NAME (event_types counters) — properties land
    on raw events but are never aggregated/shown per event. So the two preference
    dimensions are encoded IN the name (judiciously — ~15 distinct names, mirrors the
    image_studio.edit.{type} pattern; "dl" keeps names short on the dashboard):
        asset.dl.png / .svg / .glb            (2D + pristine GLB)
        asset.dl.fbx.unreal / .usd.unity / …  (engine exports)
    file_format: png | svg | glb | fbx | usd. kind: asset | version | cutout | export.
    engine_target (fbx/usd only): generic/unreal/unity/godot/maya/3dsmax. Remaining
    detail (kind/model/variant) stays in properties for the raw-events view. Cost 0.
    """
    fmt = (file_format or "unknown").lower().replace(".", "_")
    event = f"asset.dl.{fmt}"
    # Engine suffix for engine-prepared exports (incl. processed GLB); the RAW glb
    # download comes via the beacon with no engine_target → stays asset.dl.glb.
    if engine_target and fmt in ("fbx", "usd", "glb"):
        event += f".{engine_target.lower().replace('.', '_')}"
    _track(event, format=fmt, asset_type=asset_type, kind=kind,
           engine_target=engine_target, model=model, variant=variant, cost_usd=0)


def track_image_import(asset_type: str = "", source_format: str = ""):
    """User imported an existing image into the gallery (no AI, no cost)."""
    _track("gallery.import", asset_type=asset_type, source_format=source_format)


# ── Adoption Funnel Events ───────────────────────────────────────────
# Track first-time milestones in the user journey from install to active use.
# Each milestone fires ONCE per install (tracked via local flag file).

_milestones_fired: set[str] = set()


def _track_milestone(milestone: str, **props):
    """Fire a milestone event once per install. No-op on repeats."""
    if milestone in _milestones_fired:
        return
    # Check persistent flag
    from pathlib import Path
    flag_dir = Path("data/.telemetry")
    flag_file = flag_dir / f"{milestone}.done"
    if flag_file.exists():
        _milestones_fired.add(milestone)
        return
    # Fire and persist
    _track(f"adoption.{milestone}", **props)
    _milestones_fired.add(milestone)
    try:
        flag_dir.mkdir(parents=True, exist_ok=True)
        flag_file.write_text("")
    except Exception:
        pass


def track_first_sync(regions: int = 0, image_models: int = 0, chat_models: int = 0):
    """First successful Sync — user connected ArtSmoker to their AWS account."""
    _track_milestone("first_sync", regions=regions, image_models=image_models, chat_models=chat_models)


def track_sync_complete(regions: int = 0, new_models: int = 0, updated_models: int = 0, errors: int = 0):
    """Every Sync completion — shows active usage patterns (not a milestone)."""
    _track("adoption.sync_complete", regions=regions, new_models=new_models, updated_models=updated_models, errors=errors)


def track_first_generation(model: str = "", asset_type: str = "", studio: str = "image"):
    """First image/video ever generated — user actually used the tool."""
    _track_milestone("first_generation", model=model, asset_type=asset_type, studio=studio)


def track_first_custom_deploy(model: str = "", instance: str = ""):
    """First custom model deployment — user is self-hosting."""
    _track_milestone("first_custom_deploy", model=model, instance=instance)
