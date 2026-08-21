"""Async Jobs — non-blocking generation for self-hosted custom models.

Custom models on Amazon SageMaker use async endpoints (S3 input/output).
Instead of making the user wait 3-5 minutes per image while polling S3,
we submit the job and return immediately. A background thread polls S3
for results and saves completed images to the gallery.

Gallery metadata is persisted at SUBMISSION time (before the image exists)
with status="pending_async". When the image arrives, the metadata is
updated and the image file is saved. This ensures nothing is lost even
if the server restarts — the gallery entry exists from the moment the
job is submitted.
"""

import base64
import io
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.services.safe_write import atomic_write_text

logger = logging.getLogger(__name__)

# ── Job storage (in-memory, survives for the session) ────────────────────

_jobs: dict = {}  # job_id → job dict
_lock = threading.Lock()
_poller_thread: threading.Thread | None = None
_poller_stop = threading.Event()
_poller_lifecycle_lock = threading.Lock()  # serializes _ensure_poller so only one poller thread ever exists

# Job statuses
PENDING = "pending"
GENERATING = "generating"
COMPLETE = "complete"
FAILED = "failed"

# Resubmission constants
STALE_JOB_THRESHOLD_SECONDS = 900   # 15 min before considering resubmission
MAX_RESUBMITS = 3                    # Max resubmission attempts per job
RESUBMIT_COOLDOWN_SECONDS = 60       # Min seconds between resubmission attempts

# Host-wide save-failure backoff. A disk-full / disk-I/O error is a HOST problem,
# not a per-job one — every queued job's save would fail identically. So on such
# an error we abort the rest of the current poll cycle and back the whole poller
# off (rather than spinning through N identical failures + N wasted S3 downloads
# every cycle). Jobs stay PENDING with their S3 output preserved and retry
# automatically once the condition clears — on both always-on and on-demand
# (scale-to-zero) servers, and across restarts (resume_pending_jobs re-checks).
_HOST_SAVE_BACKOFF_SECONDS = 300     # 5 min pause after a host-wide save failure


class HostSaveError(Exception):
    """Raised when a gallery save fails for a HOST-WIDE reason (no disk space,
    disk I/O error) — i.e. retrying other jobs this cycle is pointless. Carries
    the original error for logging."""


def _is_host_wide_save_error(exc: BaseException) -> bool:
    """True if the exception indicates a host-level storage failure (affects ALL
    jobs), vs a per-job failure (e.g. corrupt image bytes for this one job).
    Checks OSError errno (ENOSPC=no space, EIO=I/O error, EROFS=read-only fs,
    EDQUOT=quota) and, defensively, the message text."""
    import errno
    e = exc
    # Unwrap common wrappers to find an OSError if present.
    seen = set()
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        if isinstance(e, OSError) and e.errno in (
            errno.ENOSPC, errno.EIO, errno.EROFS, errno.EDQUOT, errno.EMFILE, errno.ENFILE,
        ):
            return True
        e = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    msg = str(exc).lower()
    return any(s in msg for s in (
        "no space left", "disk full", "input/output error", "read-only file system",
        "quota exceeded", "too many open files",
    ))


def submit_job(
    job_id: str,
    model_key: str,
    model_label: str,
    prompt: str,
    full_payload: dict,
    output_location: str,
    input_location: str = "",
    s3_bucket: str = "",
    s3_key: str = "",
    option_index: int = 0,
    variation_index: int = 0,
    generation_id: str = "",
    endpoint_name: str = "",
    region: str = "",
    failure_location: str = "",
) -> dict:
    """Register a new async job for background polling.

    Called by the invoker after invoke_endpoint_async succeeds.
    Persists metadata to the gallery immediately (before image arrives).
    Returns the job dict immediately — no waiting.
    """
    now = datetime.now(timezone.utc).isoformat()
    asset_id = f"async_{job_id}"

    job = {
        "job_id": job_id,
        "asset_id": asset_id,
        "model_key": model_key,
        "model_label": model_label,
        "prompt": prompt[:200],
        "full_prompt": prompt,
        "full_payload": full_payload,
        "output_location": output_location,
        "input_location": input_location,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "option_index": option_index,
        "variation_index": variation_index,
        "generation_id": generation_id or asset_id,
        "endpoint_name": endpoint_name,
        # Region the ENDPOINT + its async S3 I/O live in. Empty = home region
        # (settings.aws_region_models) — every pre-existing job/endpoint.
        "region": region or "",
        # S3 URI where SageMaker writes the model's error body on a FAILED
        # inference (needs S3FailurePath in the endpoint config; empty for
        # older endpoints — those fall back to the stale-timeout path).
        "failure_location": failure_location or "",
        "status": PENDING,
        "progress": 0,
        "submitted_at": now,
        "completed_at": None,
        "image_path": None,
        "error": None,
        "resubmit_count": 0,
        "last_resubmit_at": None,
    }

    # Persist metadata to gallery NOW (before image arrives)
    # Note: gallery metadata is saved by the generate router (same code path as sync)
    # We only manage the async job tracking and S3 polling here.

    with _lock:
        _jobs[job_id] = job

    # Persist job to S3 immediately (survives server restart)
    _persist_job_to_s3(job)

    # Ensure the background poller is running
    _ensure_poller()

    # Dev-box convenience: when running on a dev machine, automatically pin the
    # endpoint warm so we don't lose a hard-won instance between test jobs.
    # Non-cumulative (extend_window=False): the first job sets the window; later
    # jobs re-assert MinCapacity=1 but never push the expiry forward. Best-effort
    # — never let this break job submission.
    if endpoint_name:
        _maybe_auto_keep_warm(model_key, endpoint_name)

    logger.info("Async job submitted: %s (%s) → %s", job_id, model_label, output_location)
    return job


def _maybe_auto_keep_warm(model_key: str, endpoint_name: str):
    """Auto-pin the endpoint warm (non-cumulative). Best-effort.

    Gated on BOTH dev_mode AND the explicit ARTSMOKER_AUTO_KEEP_WARM flag, which
    defaults OFF (see Settings.auto_keep_warm). With it off, endpoints rely
    purely on scale-to-zero / scale-from-zero autoscaling and never get pinned
    by a job — avoiding the silent multi-hour GPU billing this used to cause.
    On-demand warming via the /keep-warm API is unaffected.
    """
    try:
        from backend.config import settings
        if not settings.auto_keep_warm:
            return
        from backend.services.auto_update import is_dev_mode
        if not is_dev_mode():
            return
        from backend.services.sagemaker_deployer import set_keep_warm, DEFAULT_WARM_HOURS
        set_keep_warm(model_key, hours=DEFAULT_WARM_HOURS,
                      endpoint_name=endpoint_name, extend_window=False)
    except Exception as e:
        logger.debug("Auto keep-warm skipped for %s: %s", endpoint_name, e)


def get_all_jobs() -> list:
    """Get all jobs (pending, complete, failed), newest first.

    Adds queue_position (1-based) to active jobs so the frontend can show
    which job is currently processing vs waiting in queue.
    SageMaker async processes jobs FIFO — position 1 = currently generating.
    """
    with _lock:
        all_jobs = sorted(_jobs.values(), key=lambda j: j["submitted_at"], reverse=True)
        # Assign queue positions to active jobs (oldest first = position 1)
        active = sorted(
            [j for j in all_jobs if j["status"] in (PENDING, GENERATING)],
            key=lambda j: j["submitted_at"],
        )
        for i, job in enumerate(active):
            job["queue_position"] = i + 1
            job["queue_total"] = len(active)
        return all_jobs


def get_pending_count() -> int:
    """Get count of jobs still in progress."""
    with _lock:
        return sum(1 for j in _jobs.values() if j["status"] in (PENDING, GENERATING))


def has_active_jobs() -> bool:
    """Check if there are any pending/generating jobs (for smart frontend polling)."""
    with _lock:
        return any(j["status"] in (PENDING, GENERATING) for j in _jobs.values())


def update_job_asset_id(job_id: str, asset_id: str, generate_svg: bool = False, remove_bg: bool = False, upscale: bool = False):
    """Update a job's asset_id and post-processing flags (called from generate router).

    Also re-persists to S3 so the correct asset_id survives server restarts.
    """
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job["asset_id"] = asset_id
            job["generate_svg"] = generate_svg
            job["remove_bg"] = remove_bg
            job["upscale"] = upscale
    # Re-persist with updated asset_id (initial persist had the default async_{job_id})
    if job:
        _persist_job_to_s3(job)


def update_job_edit_context(job_id: str, edit_asset_id: str, edit_purpose: str = "image_edit",
                            edit_prompt: str = "", edit_seed=None, edit_spec: dict | None = None):
    """Tag an async job as an EDIT of an existing asset (called from /edit).

    Marks job_kind="edit" so the poller's completion routes to the version-aware
    save (archive current version → save result as a new version of edit_asset_id)
    instead of creating a fresh gallery asset. Re-persists so it survives restart.

    `edit_spec` carries the rest of the edit provenance (negative_prompt, mask_prompt,
    region, model_label, extra_params, outpaint_px, source_dims, mask_file, …) so the
    async edit version record reaches PARITY with the sync one and the Metadata view
    is identical whether the edit ran sync or async.
    """
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job["job_kind"] = "edit"
            job["edit_asset_id"] = edit_asset_id
            job["edit_purpose"] = edit_purpose
            job["edit_prompt"] = edit_prompt
            job["edit_seed"] = edit_seed
            job["edit_spec"] = edit_spec or {}
    if job:
        _persist_job_to_s3(job)


def clear_completed():
    """Remove all completed and failed jobs from the tracker."""
    with _lock:
        to_remove = [jid for jid, j in _jobs.items() if j["status"] in (COMPLETE, FAILED)]
        for jid in to_remove:
            del _jobs[jid]
    return len(to_remove)


# ── Gallery Persistence ──────────────────────────────────────────────────

def _persist_gallery_metadata(job: dict):
    """Save generation metadata to gallery at submission time.

    This ensures the gallery entry exists even if the server restarts
    before the image arrives. The metadata includes the full prompt,
    model info, payload, and a status flag.
    """
    from backend.config import settings

    asset_id = job["asset_id"]
    variant_dir = settings.generated_dir / f"{asset_id}_o{job['option_index']}_v{job['variation_index']}"
    variant_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "id": f"{asset_id}_o{job['option_index']}_v{job['variation_index']}",
        "batch_id": job["generation_id"],
        "option_index": job["option_index"],
        "variant_index": job["variation_index"],
        "original_prompt": job["full_prompt"],
        "enhanced_prompt": job["full_prompt"],
        "negative_prompt": job["full_payload"].get("negative_prompt", ""),
        "image_model": job["model_key"],
        "model_label": job["model_label"],
        "seed": job["full_payload"].get("seed"),
        "width": job["full_payload"].get("width", 1024),
        "height": job["full_payload"].get("height", 1024),
        "async_job_id": job["job_id"],
        "async_status": "pending",
        "async_output_location": job["output_location"],
        "source": "async_sagemaker",
        "created_at": job["submitted_at"],
    }
    # Atomic: this is a fresh full-file write to a unique per-variant dir (no
    # read-modify-write, so no lost-update risk), but a concurrent gallery read
    # must never catch a half-written file.
    atomic_write_text(variant_dir / "metadata.json", json.dumps(meta, indent=2))
    logger.debug("Gallery metadata persisted for async job %s", job["job_id"])


def _update_gallery_on_complete(job: dict, image_bytes: bytes):
    """Save image, run post-processing (SVG/upscale/bg-remove), update metadata.

    Runs the same post-processing pipeline as sync jobs to ensure
    consistent gallery entries. Edit jobs (job_kind=="edit") take a separate
    version-aware path that archives the current version and saves the result
    as a NEW version of the SAME asset (mirroring the sync /edit save).
    """
    if job.get("job_kind") == "edit":
        return _update_gallery_on_edit_complete(job, image_bytes)

    from backend.config import settings
    from backend.storage.local_store import store

    asset_id = job.get("asset_id", f"async_{job['job_id']}")

    # Run post-processing (same pipeline as sync jobs)
    final_bytes = image_bytes
    svg_path = None
    try:
        from backend.services.post_processor import process_asset
        svg_output_path = store.generated_asset_dir(asset_id) / "asset.svg" if job.get("generate_svg") else None
        final_bytes, svg_path = process_asset(
            image_bytes=image_bytes,
            enhanced_prompt=job.get("full_prompt", ""),
            remove_bg=job.get("remove_bg", False),
            do_upscale=job.get("upscale", False),
            do_svg=job.get("generate_svg", False),
            svg_output_path=svg_output_path,
        )
    except Exception as e:
        logger.warning("Async post-processing failed for %s: %s", asset_id, e)

    # Save the (possibly post-processed) image
    store.save_generated_image(asset_id, "asset.png", final_bytes)
    image_path = str(store.generated_asset_dir(asset_id) / "asset.png")

    # Update existing metadata (created by generate router at submission time).
    meta_path = store.generated_asset_dir(asset_id) / "metadata.json"
    try:
        meta = json.loads(meta_path.read_text())
    except Exception:
        meta = {}

    # Defensive backfill: if the submission-time metadata is missing (empty file
    # / never written for this slot), a completed image would otherwise land with
    # no model identity → the gallery renders it as "Failed" despite a valid image.
    # Populate the essential identity fields from the job so a real result is
    # always attributed correctly.
    if not meta.get("image_model"):
        meta.setdefault("id", asset_id)
        meta["image_model"] = job.get("model_key", "")
        meta["model_label"] = job.get("model_label", "")
        if job.get("prompt"):
            meta.setdefault("prompt", job.get("prompt"))
        if job.get("full_prompt"):
            meta.setdefault("enhanced_prompt", job.get("full_prompt"))
        for k in ("option_index", "variation_index", "generation_id"):
            if job.get(k) is not None:
                meta.setdefault(k, job.get(k))

    meta.update({
        "async_status": "complete",
        "async_completed_at": datetime.now(timezone.utc).isoformat(),
        "png_path": f"/api/gallery/{asset_id}/png",
        "png_filename": "asset.png",
        "svg_path": f"/api/gallery/{asset_id}/svg" if svg_path else None,
        "image_size_bytes": len(final_bytes),
    })
    meta_path.write_text(json.dumps(meta, indent=2))

    return image_path


def _update_gallery_on_edit_complete(job: dict, image_bytes: bytes):
    """Version-aware completion for async EDIT jobs (e.g. Qwen-Image-Edit).

    Serialized per-asset against the sync /edit save (and other async edit
    completions on the same asset) — both read-modify-write metadata.json;
    unserialized they can compute the same next_version and clobber a record.
    """
    from backend.services.asset_locks import asset_write_lock
    with asset_write_lock(job["edit_asset_id"]):
        return _update_gallery_on_edit_complete_locked(job, image_bytes)


def _update_gallery_on_edit_complete_locked(job: dict, image_bytes: bytes):
    """Body of the async edit completion — caller MUST hold the asset lock.

    Mirrors the sync /edit versioned save: archive the current asset.png as the
    previous version, then save the edited result as a NEW version of the SAME
    asset (job["edit_asset_id"]). Edit context is carried on the job dict at
    submit time (edit_asset_id, edit_purpose, edit_prompt, edit_model, ...).
    """
    import shutil
    from backend.storage.local_store import store

    asset_id = job["edit_asset_id"]
    source_meta = store.load_generation_metadata(asset_id) or {}
    asset_dir = store.generated_asset_dir(asset_id)

    # Instruction-editor outpaint: restore padded-canvas geometry and blend the
    # original source pixels back over the result (same treatment as the sync
    # path in /api/generate/edit — see instruction_outpaint.py). The pre-pad
    # source was saved as a job sidecar at submit time.
    _spec_pre = job.get("edit_spec", {}) or {}
    geom = _spec_pre.get("outpaint_geometry")
    prepad_file = _spec_pre.get("prepad_source_file")
    if geom and prepad_file:
        try:
            from backend.services.instruction_outpaint import restore_geometry_and_blend
            prepad_path = asset_dir / prepad_file
            if prepad_path.exists():
                image_bytes = restore_geometry_and_blend(
                    image_bytes, prepad_path.read_bytes(), geom)
                prepad_path.unlink(missing_ok=True)  # sidecar no longer needed
            else:
                logger.warning("Outpaint pre-pad sidecar missing for %s (%s) — using raw result",
                               job["job_id"], prepad_file)
        except Exception as e:
            logger.warning("Async outpaint geometry restore failed for %s (using raw result): %s",
                           job["job_id"], e)

    versions = source_meta.get("versions", [])
    if not versions:
        versions.append({
            "version": 1, "type": "original",
            "prompt": source_meta.get("prompt", ""),
            "enhanced_prompt": source_meta.get("enhanced_prompt", ""),
            "image_model": source_meta.get("image_model", ""),
            "model_label": source_meta.get("model_label", ""),
            "timestamp": source_meta.get("created_at", ""),
        })
    # Max-based (not len+1): version deletion leaves TOMBSTONE records and
    # numbering is sparse — a new version must never reuse a deleted number.
    next_version = max(v.get("version", 0) for v in versions) + 1

    # Archive current asset.png (+svg) as the previous version. Archive under
    # the TRUE current_version (not next-1): with sparse numbering after a
    # version delete, next-1 may be a deleted number — asset.png's bytes belong
    # to current_version, whatever its number is.
    current_png = asset_dir / "asset.png"
    if current_png.exists():
        _prev_v = source_meta.get("current_version") or (next_version - 1)
        prev_file = f"asset_v{_prev_v}.png"
        if not (asset_dir / prev_file).exists():
            shutil.copy2(str(current_png), str(asset_dir / prev_file))
        current_svg = asset_dir / "asset.svg"
        prev_svg = f"asset_v{_prev_v}.svg"
        if current_svg.exists() and not (asset_dir / prev_svg).exists():
            shutil.copy2(str(current_svg), str(asset_dir / prev_svg))

    # Save edited result as the new latest, regenerate SVG
    store.save_generated_image(asset_id, "asset.png", image_bytes)
    try:
        from backend.services.post_processor import process_asset
        process_asset(image_bytes=image_bytes, enhanced_prompt=job.get("edit_prompt", ""),
                      remove_bg=False, do_upscale=False, do_svg=True,
                      svg_output_path=asset_dir / "asset.svg")
    except Exception as e:
        logger.warning("Async edit SVG generation failed for %s: %s", asset_id, e)

    # Bring the async edit version record to PARITY with the sync path (same
    # fields → identical Metadata display regardless of sync/async execution).
    _spec = job.get("edit_spec", {}) or {}
    _new_dims = {"width": None, "height": None}
    try:
        from PIL import Image as _PILImage
        with _PILImage.open(io.BytesIO(image_bytes)) as _img:
            _new_dims = {"width": _img.width, "height": _img.height}
    except Exception:
        pass
    versions.append({
        "version": next_version, "type": job.get("edit_purpose", "image_edit"),
        "prompt": job.get("edit_prompt", ""),
        "edit_prompt_sent": _spec.get("edit_prompt_sent"),
        # Parity with sync: the enhanced/sent instruction when a transform ran,
        # else the user's words (edit_prompt now carries the RAW user prompt).
        "enhanced_prompt": _spec.get("edit_prompt_sent") or job.get("edit_prompt", ""),
        "negative_prompt": _spec.get("negative_prompt", ""),
        "mask_prompt": _spec.get("mask_prompt"),
        "mask_file": _spec.get("mask_file"),
        "source_dims": _spec.get("source_dims"),
        "result_dims": _new_dims if _new_dims.get("width") else _spec.get("result_dims"),
        **({"outpaint_px": _spec["outpaint_px"]} if _spec.get("outpaint_px") else {}),
        "image_model": job.get("model_key", ""),
        "model_label": job.get("model_label", "") or _spec.get("model_label", ""),
        "region": _spec.get("region", ""),
        "extra_params": _spec.get("extra_params"),
        "seed": job.get("edit_seed"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    new_meta = dict(source_meta)
    new_meta.update({
        "original_prompt": source_meta.get("original_prompt") or source_meta.get("prompt", ""),
        "versions": versions,
        "current_version": next_version,
        "last_edited_at": datetime.now(timezone.utc).isoformat(),
        "last_edit_type": job.get("edit_purpose", "image_edit"),
        "last_edit_model": job.get("model_key", ""),
        "last_edit_prompt": job.get("edit_prompt", ""),
        "png_path": f"/api/gallery/{asset_id}/png",
    })
    store.save_generation_metadata(asset_id, new_meta)
    logger.info("Async edit complete: %s → version %d (%s)", asset_id, next_version, job.get("model_key"))
    return str(asset_dir / "asset.png")


def _update_gallery_on_failure(job: dict):
    """Update gallery metadata when an async job fails.

    Distinguishes a content-moderation block (the model refused the prompt) from
    a technical failure, so the Gallery can show "Model Censored" instead of the
    ambiguous "Failed". Uses the shared is_moderation_error() classifier so the
    verdict matches the synchronous/multi-model paths.
    """
    from backend.config import settings
    from backend.services.image_generator import is_moderation_error

    asset_id = job["asset_id"]
    variant_dir = settings.generated_dir / f"{asset_id}_o{job['option_index']}_v{job['variation_index']}"
    meta_path = variant_dir / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            error = job.get("error", "Unknown error")
            meta["async_status"] = "moderation_blocked" if is_moderation_error(error) else "failed"
            meta["async_error"] = error
            meta_path.write_text(json.dumps(meta, indent=2))
        except Exception:
            pass


# ── Background Poller ────────────────────────────────────────────────────

def _ensure_poller():
    """Start the background poller if not already running.

    The alive-check + thread creation run under _poller_lifecycle_lock so two
    callers (e.g. a submit_job racing the startup path) can't both pass an
    unlocked check and spawn duplicate poller threads — duplicate pollers were a
    source of the same job being finalized multiple times (duplicate versions).
    """
    global _poller_thread
    with _poller_lifecycle_lock:
        if _poller_thread and _poller_thread.is_alive():
            return

        # Restore persisted jobs from S3 (if any from before last restart)
        load_persisted_jobs()

        _poller_stop.clear()
        _poller_thread = threading.Thread(target=_poll_loop, daemon=True, name="async-job-poller")
        _poller_thread.start()
    # One actionable line, mirroring the 3D poller: what it found + what it'll do.
    pending = [j for j in _jobs.values() if j["status"] in (PENDING, GENERATING)]
    if pending:
        logger.info("Async job poller started — watching %d in-progress job(s) (%s); polling S3 every "
                    "30s to download + finalize each output as it lands",
                    len(pending), ", ".join(str(j.get("job_id", "?")) for j in pending))
    else:
        logger.info("Async job poller started — no in-progress jobs; idle-watching, will finalize "
                    "any new job's output from S3 every 30s")


def stop_poller():
    """Stop the background poller (called on shutdown)."""
    _poller_stop.set()


_endpoint_warm_state: dict = {}  # endpoint_name → {warm_start, last_job_time, hourly_rate, job_count}
_last_bg_cost_flush = 0.0


def _poll_loop():
    """Background loop: check S3 for completed async jobs every 30 seconds.
    Also tracks custom model endpoint warm periods and flushes background costs."""
    global _last_bg_cost_flush
    import boto3
    import time as _time
    from backend.config import settings

    region = settings.aws_region_models
    _last_bg_cost_flush = _time.time()

    while not _poller_stop.is_set():
        pending = []
        with _lock:
            pending = [j for j in _jobs.values() if j["status"] in (PENDING, GENERATING)]

        if not pending:
            _flush_background_costs_if_due()
            _check_warm_period_closures()
            # Self-stop when there is genuinely nothing left to do — no pending
            # jobs AND no open warm period (which still needs cost/closure
            # housekeeping). Avoids a thread idling forever after work drains; it
            # restarts on the next job submit (_ensure_poller). Mirrors the boot
            # gate: a poller runs only while there's work.
            if not _endpoint_warm_state:
                logger.info("Async job poller stopping — no in-progress jobs or warm endpoints left")
                break
            _poller_stop.wait(timeout=5)
            continue

        s3 = boto3.client("s3", region_name=region)
        _regional_s3 = {}  # region → client (cross-region endpoints, e.g. capacity-drought deploys)

        host_save_failure = False
        for job in pending:
            if _poller_stop.is_set():
                break
            _job_region = job.get("region") or region
            if _job_region != region and _job_region not in _regional_s3:
                _regional_s3[_job_region] = boto3.client("s3", region_name=_job_region)
            _job_s3 = _regional_s3.get(_job_region, s3)
            try:
                _check_job(job, _job_s3)
            except HostSaveError:
                # Host-wide storage failure — the remaining jobs in this cycle
                # would fail identically (the detailed message + retry-guidance
                # is already logged in _check_job). Abort the cycle and back off;
                # all jobs stay PENDING with their S3 output preserved.
                host_save_failure = True
                break
            except Exception as e:
                logger.warning("Async job poll error (%s): %s", job["job_id"], e)

        _flush_background_costs_if_due()
        _check_warm_period_closures()

        if host_save_failure:
            # Long backoff: give the operator/host time to free space or recover
            # the disk before we retry the whole queue. Interruptible by stop.
            logger.warning("%d image job(s) waiting on disk recovery — retrying in %d min. Free up disk space to speed this up.",
                           len(pending), _HOST_SAVE_BACKOFF_SECONDS // 60)
            _poller_stop.wait(timeout=_HOST_SAVE_BACKOFF_SECONDS)
            if not _poller_stop.is_set():
                logger.info("Retrying %d pending image job(s) now (disk backoff elapsed)…", len(pending))
        else:
            # Poll interval — 10 seconds while jobs are active (fast feedback)
            _poller_stop.wait(timeout=10)

    # Final flush on shutdown
    _flush_background_costs_if_due(force=True)
    logger.debug("Async job poller stopped")


def _track_warm_period_start(job: dict):
    """Record when an endpoint becomes warm (first job starts generating)."""
    ep = _resolve_endpoint_for_job(job) or f"artsmoker-{job['model_key'].replace('_', '-')}"
    if ep in _endpoint_warm_state:
        return  # already tracking
    # Registry-sourced hourly rate via the single resolver (get_instance_hourly_rate:
    # sagemaker_pricing → catalog seed → on-demand). No hardcoded fallback — 0.0 when
    # unknown, so the keep-warm figure is honest rather than a fabricated rate.
    hourly_rate = 0.0
    try:
        from backend.services.custom_models import get_catalog_model, get_instance_hourly_rate
        catalog = get_catalog_model(job["model_key"]) or {}
        recommended = catalog.get("requirements", {}).get("recommended_instance", "")
        inst = job.get("instance_type") or recommended
        hourly_rate = get_instance_hourly_rate(inst, job["model_key"], job.get("region")) or 0.0
    except Exception:
        hourly_rate = 0.0

    _endpoint_warm_state[ep] = {
        "warm_start": datetime.now(timezone.utc),
        "last_job_time": datetime.now(timezone.utc),
        "hourly_rate": hourly_rate,
        "job_count": 0,
        "model_key": job["model_key"],
    }
    logger.debug("Warm period started for %s (rate=$%.2f/hr)", ep, hourly_rate)


def _track_warm_period_job_complete(job: dict):
    """Update warm-period state when a job completes."""
    ep = _resolve_endpoint_for_job(job) or f"artsmoker-{job['model_key'].replace('_', '-')}"
    state = _endpoint_warm_state.get(ep)
    if state:
        state["last_job_time"] = datetime.now(timezone.utc)
        state["job_count"] += 1


def _check_warm_period_closures():
    """Close warm periods for endpoints that have been idle > cooldown."""
    now = datetime.now(timezone.utc)
    closed = []
    for ep, state in _endpoint_warm_state.items():
        idle_seconds = (now - state["last_job_time"]).total_seconds()
        # Scale-in cooldown is 600s + 60s buffer
        if idle_seconds > 660 and not _has_pending_for_endpoint(ep):
            warm_seconds = (now - state["warm_start"]).total_seconds()
            warm_cost = (warm_seconds / 3600.0) * state["hourly_rate"]
            try:
                from backend.services.cost_tracker import add_background_cost
                add_background_cost(
                    "custom_model_infra",
                    warm_cost,
                    f"{ep}: {warm_seconds:.0f}s warm, {state['job_count']} jobs, ${warm_cost:.4f}",
                )
            except Exception:
                pass
            logger.info("Warm period closed for %s: %ds, %d jobs, $%.4f",
                        ep, warm_seconds, state["job_count"], warm_cost)
            closed.append(ep)
    for ep in closed:
        del _endpoint_warm_state[ep]


def _has_pending_for_endpoint(endpoint_name: str) -> bool:
    """Check if any pending jobs target this endpoint."""
    with _lock:
        for j in _jobs.values():
            if j["status"] in (PENDING, GENERATING):
                job_ep = _resolve_endpoint_for_job(j) or f"artsmoker-{j['model_key'].replace('_', '-')}"
                if job_ep == endpoint_name:
                    return True
    return False


def _flush_background_costs_if_due(force: bool = False):
    """Periodically flush accumulated background costs to telemetry."""
    global _last_bg_cost_flush
    import time as _time
    now = _time.time()
    if not force and (now - _last_bg_cost_flush) < 300:  # every 5 min
        return
    _last_bg_cost_flush = now
    try:
        from backend.services.cost_tracker import get_background_total, get_background_costs, reset_background_costs
        total = get_background_total()
        if total > 0:
            breakdown = get_background_costs()
            from backend.services.telemetry import _track
            _track("system.infra_cost", cost_usd=total,
                   breakdown=str(breakdown))
            reset_background_costs()
            logger.debug("Flushed background costs: $%.6f", total)
    except Exception as e:
        logger.debug("Background cost flush failed: %s", e)


# ── Endpoint Resolution & Job Resubmission ──────────────────────────────

def _resolve_endpoint_for_job(job: dict) -> str:
    """Resolve the current SageMaker endpoint name for a job.

    Priority:
    1. The endpoint_name stored at submission time — verify it still exists
    2. Look up by model_key prefix in registry (handles redeployed endpoints)
    3. Return empty string if no endpoint found (model torn down)
    """
    # 1. Check stored endpoint
    stored_ep = job.get("endpoint_name", "")
    if stored_ep:
        try:
            from backend.services.model_registry import get_registry
            registry = get_registry()
            for section in ("image_models", "video_models", "post_processing", "utility_models"):
                for key, cfg in registry.get(section, {}).items():
                    if cfg.get("deployment", {}).get("endpoint_name") == stored_ep:
                        return stored_ep
        except Exception:
            pass

    # 2. Look up by model_key prefix in registry (handles redeployment)
    model_key = job.get("model_key", "")
    if model_key:
        try:
            from backend.services.model_registry import get_registry
            registry = get_registry()
            for section in ("image_models", "video_models", "post_processing", "utility_models"):
                for key, cfg in registry.get(section, {}).items():
                    ep = cfg.get("deployment", {}).get("endpoint_name", "")
                    if ep and (key == model_key or key.startswith(model_key + "_")):
                        return ep
        except Exception:
            pass

    return ""


def _check_stale_and_resubmit(job: dict, s3):
    """Check if a pending job is stale and resubmit if the endpoint scaled to zero.

    Called when S3 output is not found (NoSuchKey). Uses endpoint health to
    distinguish "still processing" from "silently dropped by scale-to-zero".
    """
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(job["submitted_at"])).total_seconds()

    # Not stale yet — wait for normal processing
    if elapsed < STALE_JOB_THRESHOLD_SECONDS:
        _update_progress(job)
        return

    # Max retries exceeded
    if job.get("resubmit_count", 0) >= MAX_RESUBMITS:
        with _lock:
            job["status"] = FAILED
            job["error"] = f"Job failed after {MAX_RESUBMITS} resubmission attempts — output never appeared"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _cleanup_s3(job, s3)
        _persist_job_to_s3(job)
        logger.warning("Async job %s failed after %d resubmissions", job["job_id"], MAX_RESUBMITS)
        return

    # Cooldown between resubmission attempts
    last_resubmit = job.get("last_resubmit_at")
    if last_resubmit:
        since_last = (datetime.now(timezone.utc) - datetime.fromisoformat(last_resubmit)).total_seconds()
        if since_last < RESUBMIT_COOLDOWN_SECONDS:
            _update_progress(job)
            return

    # Resolve current endpoint
    endpoint_name = _resolve_endpoint_for_job(job)
    if not endpoint_name:
        with _lock:
            job["status"] = FAILED
            job["error"] = "Endpoint not found — model may have been torn down"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _cleanup_s3(job, s3)
        _persist_job_to_s3(job)
        logger.warning("Async job %s failed: no endpoint found for model_key=%s", job["job_id"], job.get("model_key"))
        return

    # Check endpoint health
    try:
        from backend.services.sagemaker_deployer import get_endpoint_health
        health = get_endpoint_health(endpoint_name)
    except Exception as e:
        logger.debug("Health check failed for %s: %s — will retry next cycle", endpoint_name, e)
        _update_progress(job)
        return

    if health.get("failed"):
        with _lock:
            job["status"] = FAILED
            job["error"] = f"Endpoint failed: {health.get('detail', 'unknown')}"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _cleanup_s3(job, s3)
        _persist_job_to_s3(job)
        return

    if not health.get("alive"):
        with _lock:
            job["status"] = FAILED
            job["error"] = f"Endpoint no longer exists: {health.get('detail', 'unknown')}"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _cleanup_s3(job, s3)
        _persist_job_to_s3(job)
        return

    if health.get("ready") or health.get("progressing"):
        # Endpoint is alive and working — job may still be processing. Don't resubmit.
        _update_progress(job)
        return

    # Endpoint is alive but has 0 instances (scaled to zero).
    # The SageMaker async backlog was silently dropped. Resubmit.
    _resubmit_job(job, endpoint_name, s3)


def _resubmit_job(job: dict, endpoint_name: str, s3):
    """Resubmit an async job using the original S3 input file.

    The resubmission itself triggers HasBacklogWithoutCapacity → scale-from-zero.
    """
    import boto3
    from backend.config import settings

    input_location = job.get("input_location", "")
    if not input_location:
        with _lock:
            job["status"] = FAILED
            job["error"] = "Cannot resubmit: original input file location not stored"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _persist_job_to_s3(job)
        logger.error("Async job %s cannot resubmit: no input_location", job["job_id"])
        return

    # Verify input file still exists
    try:
        input_parts = input_location.replace("s3://", "").split("/", 1)
        s3.head_object(Bucket=input_parts[0], Key=input_parts[1])
    except Exception:
        with _lock:
            job["status"] = FAILED
            job["error"] = "Cannot resubmit: original input file no longer exists in S3"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _persist_job_to_s3(job)
        logger.error("Async job %s cannot resubmit: input file missing at %s", job["job_id"], input_location)
        return

    old_output = job.get("output_location", "")

    try:
        # Resubmit in the JOB's region (cross-region endpoints carry it; empty =
        # home region for every pre-existing job).
        sm_runtime = boto3.client("sagemaker-runtime",
                                  region_name=job.get("region") or settings.aws_region_models)

        response = sm_runtime.invoke_endpoint_async(
            EndpointName=endpoint_name,
            ContentType="application/json",
            InputLocation=input_location,
        )

        new_output = response.get("OutputLocation")
        if not new_output:
            raise RuntimeError("Resubmission returned no output location")

        now = datetime.now(timezone.utc).isoformat()
        resubmit_count = job.get("resubmit_count", 0) + 1
        new_parts = new_output.replace("s3://", "").split("/", 1)

        with _lock:
            job["output_location"] = new_output
            # The failure artifact follows the NEW invocation too.
            job["failure_location"] = response.get("FailureLocation", "") or job.get("failure_location", "")
            job["s3_bucket"] = new_parts[0]
            job["s3_key"] = new_parts[1]
            job["endpoint_name"] = endpoint_name
            job["resubmit_count"] = resubmit_count
            job["last_resubmit_at"] = now
            job["status"] = PENDING
            job["progress"] = 0
            job["stage"] = "resubmitted"
            job["stage_label"] = f"Resubmitted (attempt {resubmit_count}/{MAX_RESUBMITS})"

        _persist_job_to_s3(job)

        logger.info("Async job %s resubmitted (attempt %d/%d) to %s — new output: %s",
                     job["job_id"], resubmit_count, MAX_RESUBMITS, endpoint_name, new_output[-50:])

    except Exception as e:
        logger.warning("Async job %s resubmission failed: %s", job["job_id"], e)
        resubmit_count = job.get("resubmit_count", 0) + 1
        with _lock:
            job["resubmit_count"] = resubmit_count
            job["last_resubmit_at"] = datetime.now(timezone.utc).isoformat()
        if resubmit_count >= MAX_RESUBMITS:
            with _lock:
                job["status"] = FAILED
                job["error"] = f"Resubmission failed after {MAX_RESUBMITS} attempts: {e}"
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
            _update_gallery_on_failure(job)
            _cleanup_s3(job, s3)
        _persist_job_to_s3(job)


def _claim_finalization(job: dict) -> bool:
    """Atomically claim a job for finalization. Returns True to the FIRST caller
    only; False to every subsequent one.

    Finalization (writing the gallery result/version, flipping status, deleting
    S3) is NOT atomic — the version-append reads+writes the versions array, and
    status only flips afterward. Multiple poller threads (accumulated because
    _ensure_poller's alive-check wasn't locked, plus resume_pending_jobs racing
    the poller at startup) can each see the same freshly-arrived S3 output while
    the job is still PENDING and re-run the whole append → duplicate versions
    (confirmed: one edit produced 4 byte-identical versions 325ms apart). This
    claim, taken under _lock before any gallery write, guarantees exactly one
    finalizer per job. Idempotent + terminal-safe."""
    with _lock:
        if job.get("status") in (COMPLETE, FAILED) or job.get("_finalizing"):
            return False
        job["_finalizing"] = True
        return True


def _check_job(job: dict, s3):
    """Check if an async job's output has appeared in S3."""
    output_location = job["output_location"]

    # Parse S3 URI
    parts = output_location.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]

    # Check for a failure artifact FIRST, at both possible locations:
    #  1. job["failure_location"] — where SageMaker ACTUALLY writes the model's
    #     error when the endpoint config sets S3FailurePath (returned as
    #     FailureLocation at invoke time). This is the real mechanism — it fails
    #     a crashing job in seconds instead of waiting out the stale timeout.
    #  2. legacy "{output}.failure" convention — kept for older jobs/endpoints.
    _failure_candidates = []
    if job.get("failure_location"):
        fparts = job["failure_location"].replace("s3://", "").split("/", 1)
        if len(fparts) == 2:
            _failure_candidates.append((fparts[0], fparts[1]))
    _failure_candidates.append((bucket, key + ".failure"))
    for f_bucket, f_key in _failure_candidates:
        try:
            failure_obj = s3.get_object(Bucket=f_bucket, Key=f_key)
            failure_body = failure_obj["Body"].read().decode("utf-8", errors="replace")
        except Exception:
            continue  # no artifact at this candidate
        if not _claim_finalization(job):
            return  # another finalizer already handled this job
        with _lock:
            job["status"] = FAILED
            job["error"] = failure_body[:500] if failure_body else "Model returned an error (no details)"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _cleanup_s3(job, s3)
        # Also delete the failure artifact itself
        try:
            s3.delete_object(Bucket=f_bucket, Key=f_key)
        except Exception:
            pass
        logger.warning("Async job %s failed (error output in S3): %s", job["job_id"], job["error"][:200])
        return

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()

        # Track S3 download cost
        try:
            from backend.services.cost_tracker import add_background_s3_cost
            add_background_s3_cost("get", len(body), "async job output download")
        except Exception:
            pass

        # Parse the output (our handler returns {"image": "base64...", "format": "base64_png"})
        result = json.loads(body.decode("utf-8"))
        image_b64 = result.get("image", "")

        # Atomically claim this job BEFORE any gallery write — exactly one
        # finalizer proceeds, preventing duplicate versions from concurrent pollers.
        if not _claim_finalization(job):
            return

        if not image_b64:
            with _lock:
                job["status"] = FAILED
                job["error"] = "Model returned no image data"
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
            _update_gallery_on_failure(job)
            return

        # Decode and save to gallery. This is the CRITICAL, must-not-lose step.
        # If saving raises, we MUST NOT clean up S3 (the output is the only copy)
        # and MUST release the finalization claim so the next poll retries —
        # otherwise a transient disk/IO error would silently wedge the job
        # (claimed, never completed, output eventually deleted). The S3 output is
        # deleted ONLY after the gallery file is verified durable on disk.
        image_bytes = base64.b64decode(image_b64)
        completed_at = datetime.now(timezone.utc)
        try:
            image_path = _update_gallery_on_complete(job, image_bytes)
            # Verify the gallery image is actually on disk and non-empty BEFORE
            # we consider the job done / delete the S3 output. A silent write
            # failure must not lead to cleanup.
            if not (image_path and os.path.isfile(image_path) and os.path.getsize(image_path) > 0):
                raise IOError(f"gallery image not durable on disk: {image_path}")
        except Exception as save_err:
            # Release the claim so the poller retries next cycle; leave the job
            # PENDING and the S3 output intact (recoverable). Never reaches cleanup.
            with _lock:
                job["_finalizing"] = False
                job["_save_attempts"] = job.get("_save_attempts", 0) + 1
            if _is_host_wide_save_error(save_err):
                # Host-level storage failure — every other queued job would fail
                # the same way. Abort the cycle and back the poller off instead of
                # burning through N identical failures + N wasted S3 downloads.
                # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
                logger.error("⚠ Disk problem saving image (%s). Pausing image saves for %d min; "
                             "no jobs lost — they'll retry automatically once disk space/health recovers.",
                             save_err, _HOST_SAVE_BACKOFF_SECONDS // 60)
                raise HostSaveError(str(save_err)) from save_err
            logger.warning("Couldn't save image for job %s (attempt %d): %s — kept in queue, will retry.",
                           job["job_id"], job["_save_attempts"], save_err)
            return

        # Calculate actual compute cost based on instance uptime
        submitted = datetime.fromisoformat(job["submitted_at"])
        if submitted.tzinfo is None:
            submitted = submitted.replace(tzinfo=timezone.utc)
        duration_seconds = (completed_at - submitted).total_seconds()
        duration_seconds = min(duration_seconds, 900)  # Cap at 15 min
        compute_cost = _calculate_compute_cost(job["model_key"], duration_seconds)

        _track_warm_period_job_complete(job)

        with _lock:
            job["status"] = COMPLETE
            job["image_path"] = image_path
            job["completed_at"] = completed_at.isoformat()
            job["progress"] = 100
            job["duration_seconds"] = round(duration_seconds, 1)
            job["compute_cost_usd"] = compute_cost

        # Track telemetry + cost
        _track_completion(job, duration_seconds, compute_cost)

        # Clean up ALL S3 artifacts: input, output, AND job metadata — ONLY now
        # that the gallery image is verified durable on disk (checked above).
        _cleanup_s3(job, s3)

        # If this job had previously failed to save (disk problem), announce the
        # recovery so the user knows the queue is draining again.
        if job.get("_save_attempts"):
            logger.info("✓ Recovered: job %s saved after %d earlier failed attempt(s) — disk healthy again.",
                        job["job_id"], job["_save_attempts"])

        logger.info("Async job complete: %s → %s (%d bytes, %.0fs, ~$%.4f)",
                     job["job_id"], image_path, len(image_bytes), duration_seconds, compute_cost)

    except HostSaveError:
        # Host-wide storage failure — must propagate to the poll loop so it
        # aborts the rest of the cycle and backs off (not swallowed as a
        # per-job S3 hiccup). Job already left PENDING + S3 preserved above.
        raise

    except s3.exceptions.NoSuchKey:
        _check_stale_and_resubmit(job, s3)

    except Exception as e:
        if "NoSuchKey" in str(e) or "404" in str(e):
            _check_stale_and_resubmit(job, s3)
        else:
            logger.debug("Async job %s: S3 check error (will retry): %s", job["job_id"], e)


def _update_progress(job: dict):
    """Update job stage based on elapsed time, queue position, and endpoint state.

    SageMaker async has no intermediate progress — only submitted → complete.
    We use queue position to show which job is actively generating vs queued.
    """
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(job["submitted_at"])).total_seconds()
    queue_pos = job.get("queue_position", 1)

    # Queue position 1 = currently generating, >1 = waiting in queue
    if queue_pos > 1:
        stage = "queued"
        stage_label = f"Queued — #{queue_pos} in line"
    elif elapsed < 10:
        stage = "submitted"
        stage_label = "Submitted — waiting for endpoint"
    elif elapsed < 600:
        stage = "generating"
        stage_label = "Generating — model is processing"
    else:
        stage = "generating"
        stage_label = "Still processing — large model may need extra time"

    with _lock:
        was_pending = job["status"] == PENDING
        job["status"] = GENERATING
        job["stage"] = stage
        job["stage_label"] = stage_label
        job["elapsed_seconds"] = int(elapsed)
    if was_pending:
        _track_warm_period_start(job)


def _calculate_compute_cost(model_key: str, duration_seconds: float) -> float:
    """Calculate the actual compute cost based on instance uptime.

    Uses the instance type's hourly rate from the catalog, prorated to
    the actual generation duration. Includes a share of the cooldown
    cost (the instance stays up for 10 min after the last job, so that
    cost is amortized across all jobs in the batch).

    Note: This is ONLY the SageMaker compute cost. LLM costs (prompt
    refinement, classification, etc.) are tracked separately by the
    cost_tracker during the generation request and added to the session
    total. The final telemetry event includes both.
    """
    from backend.services.custom_models import get_catalog_model
    from backend.services.model_registry import get_registry

    # Hourly rate — REGISTRY ONLY (never hardcoded). Prefer the DEPLOYED instance
    # type's rate (what's actually billing); fall back to the catalog's
    # recommended instance. All rates come from the catalog's
    # pricing.instance_cost_per_hour via the shared resolver, so updating the
    # registry updates every cost computation at once.
    from backend.services.custom_models import get_instance_hourly_rate
    catalog_model = get_catalog_model(model_key)
    catalog_key = None
    if catalog_model:
        # get_catalog_model is keyed by catalog_key already in most flows; but the
        # deployed model_key may differ, so resolve the catalog_key from the model.
        catalog_key = (catalog_model.get("catalog_key")
                       or get_registry().get("image_models", {}).get(model_key, {}).get("catalog_key")
                       or get_registry().get("video_models", {}).get(model_key, {}).get("catalog_key"))

    registry = get_registry()
    deployed_instance = ""
    deployed_region = ""
    for section in ("image_models", "video_models"):
        dep = registry.get(section, {}).get(model_key, {}).get("deployment", {})
        if dep.get("instance_type"):
            deployed_instance = dep["instance_type"]
            deployed_region = dep.get("region", "")
            break

    hourly_rate = get_instance_hourly_rate(deployed_instance, catalog_key, deployed_region)
    if hourly_rate == 0 and catalog_model:
        recommended = catalog_model.get("requirements", {}).get("recommended_instance", "")
        hourly_rate = get_instance_hourly_rate(recommended, catalog_key, deployed_region)

    # Prorate: cost = (duration_seconds / 3600) * hourly_rate
    generation_cost = (duration_seconds / 3600.0) * hourly_rate

    # Add amortized cooldown cost: the instance stays up for 10 min (600s)
    # after the last job. This cost is shared across all jobs in the batch.
    # Estimate: assume ~5 jobs per batch (conservative)
    _COOLDOWN_SECONDS = 600
    _ESTIMATED_BATCH_SIZE = max(1, get_pending_count() + 1)
    cooldown_share = (_COOLDOWN_SECONDS / _ESTIMATED_BATCH_SIZE / 3600.0) * hourly_rate

    total_cost = generation_cost + cooldown_share
    return round(total_cost, 6)


def _track_completion(job: dict, duration_seconds: float, compute_cost: float):
    """Track telemetry and cost for a completed async job."""
    try:
        from backend.services.cost_tracker import add_cost
        add_cost("custom_model", compute_cost,
                 f"{job['model_label']} × 1 ({duration_seconds:.0f}s @ instance rate)")
    except Exception:
        pass

    try:
        from backend.services.telemetry import track_custom_model_invoke, track_image_cost
        # Invocation event with compute cost (for raw event visibility)
        track_custom_model_invoke(
            model=job["model_key"],
            cost_usd=compute_cost,
            latency_ms=int(duration_seconds * 1000),
            predictor_type="text_to_image",
        )
        # Cost event (consistent with sync path)
        track_image_cost(
            cost_usd=compute_cost,
            model=job["model_key"],
        )
    except Exception:
        pass


# ── S3 Cleanup & Persistence ────────────────────────────────────────────

_JOBS_S3_PREFIX = "artsmoker/async-jobs/"
_lifecycle_ensured: set[str] = set()


def _ensure_s3_lifecycle(bucket: str):
    """Ensure S3 lifecycle rule exists for async-jobs auto-cleanup (1 day).

    Runs at most once per bucket per server session. Idempotent — checks
    if the rule already exists before adding.
    """
    if bucket in _lifecycle_ensured:
        return
    _lifecycle_ensured.add(bucket)
    try:
        import boto3
        from backend.config import settings
        s3 = boto3.client("s3", region_name=settings.aws_region_models)
        rule_id = "artsmoker-async-jobs-cleanup"
        try:
            existing = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
            rules = existing.get("Rules", [])
        except Exception:
            rules = []
        if any(r.get("ID") == rule_id for r in rules):
            return
        rules.append({
            "ID": rule_id,
            "Filter": {"Prefix": _JOBS_S3_PREFIX},
            "Status": "Enabled",
            "Expiration": {"Days": 1},
        })
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration={"Rules": rules},
        )
        logger.info("S3 lifecycle: %s/%s auto-expires after 1 day", bucket, _JOBS_S3_PREFIX)
    except Exception as exc:
        logger.debug("S3 lifecycle setup: %s", exc)


def _cleanup_s3(job: dict, s3):
    """Delete ALL S3 artifacts for a completed/failed job: output, input, and job metadata.

    Each delete is independent — a failure on one does not skip the others.

    Marks the job `_s3_cleaned` so any subsequent _persist_job_to_s3 becomes a
    no-op — otherwise a cleanup-then-persist sequence (several terminal branches
    historically did both) would immediately re-create the job file we just
    deleted, leaving completed/failed jobs lingering in S3 forever.
    """
    from backend.services.sagemaker_deployer import get_deployment_s3_bucket
    bucket = get_deployment_s3_bucket()
    job["_s3_cleaned"] = True

    # 1. Delete output file
    output_loc = job.get("output_location", "")
    if output_loc:
        try:
            parts = output_loc.replace("s3://", "").split("/", 1)
            s3.delete_object(Bucket=parts[0], Key=parts[1])
        except Exception as e:
            logger.debug("S3 cleanup output for job %s: %s", job["job_id"], e)

    # 2. Delete input file
    input_loc = job.get("input_location", "")
    if input_loc:
        try:
            parts = input_loc.replace("s3://", "").split("/", 1)
            s3.delete_object(Bucket=parts[0], Key=parts[1])
        except Exception as e:
            logger.debug("S3 cleanup input for job %s: %s", job["job_id"], e)

    # 3. Delete persisted job metadata from S3
    if bucket:
        try:
            s3.delete_object(Bucket=bucket, Key=f"{_JOBS_S3_PREFIX}{job['job_id']}.json")
        except Exception as e:
            logger.debug("S3 cleanup metadata for job %s: %s", job["job_id"], e)


def _persist_job_to_s3(job: dict):
    """Persist job state to S3 so it survives server restarts.

    Jobs are stored as JSON files under artsmoker/async-jobs/{job_id}.json
    in the same S3 bucket used for model storage.
    """
    # Never re-create a job file that _cleanup_s3 has already deleted (terminal
    # job). This is the invariant that keeps a cleanup-then-persist ordering
    # bug from resurrecting completed/failed jobs in S3.
    if job.get("_s3_cleaned"):
        return
    try:
        import boto3
        from backend.services.sagemaker_deployer import get_deployment_s3_bucket
        from backend.config import settings

        bucket = get_deployment_s3_bucket()
        if not bucket:
            return
        _ensure_s3_lifecycle(bucket)

        # Persist everything needed to resume polling after server restart:
        # - S3 output location (where to poll for the result)
        # - Gallery info (where to save the image)
        # - Full prompt + payload (for metadata)
        persist = {
            "job_id": job["job_id"],
            "asset_id": job.get("asset_id"),
            "model_key": job["model_key"],
            "model_label": job["model_label"],
            "prompt": job.get("prompt", ""),
            "full_prompt": job.get("full_prompt", ""),
            "full_payload": job.get("full_payload", {}),
            "output_location": job.get("output_location", ""),
            "input_location": job.get("input_location", ""),
            "s3_bucket": job.get("s3_bucket", ""),
            "s3_key": job.get("s3_key", ""),
            "option_index": job.get("option_index", 0),
            "variation_index": job.get("variation_index", 0),
            "generation_id": job.get("generation_id", ""),
            "generate_svg": job.get("generate_svg", False),
            "remove_bg": job.get("remove_bg", False),
            "upscale": job.get("upscale", False),
            "endpoint_name": job.get("endpoint_name", ""),
            "resubmit_count": job.get("resubmit_count", 0),
            "last_resubmit_at": job.get("last_resubmit_at"),
            # Edit-job context — persist so a version-aware edit resumes correctly
            # after a server restart (else the poller would save it as a fresh asset).
            "job_kind": job.get("job_kind"),
            "edit_asset_id": job.get("edit_asset_id"),
            "edit_purpose": job.get("edit_purpose"),
            "edit_prompt": job.get("edit_prompt"),
            "edit_seed": job.get("edit_seed"),
            "edit_spec": job.get("edit_spec"),  # parity provenance — survive restart
            "status": job["status"],
            "progress": job.get("progress", 0),
            "submitted_at": job["submitted_at"],
            "completed_at": job.get("completed_at"),
            "image_path": job.get("image_path"),
            "error": job.get("error"),
            "duration_seconds": job.get("duration_seconds"),
            "compute_cost_usd": job.get("compute_cost_usd"),
        }

        persist_bytes = json.dumps(persist, indent=2, default=str).encode()
        s3 = boto3.client("s3", region_name=settings.aws_region_models)
        s3.put_object(
            Bucket=bucket,
            Key=f"{_JOBS_S3_PREFIX}{job['job_id']}.json",
            Body=persist_bytes,
            ContentType="application/json",
        )
        try:
            from backend.services.cost_tracker import add_background_s3_cost
            add_background_s3_cost("put", len(persist_bytes), "job metadata persist")
        except Exception:
            pass
        logger.debug("Persisted job %s to S3", job["job_id"])
    except Exception as e:
        logger.debug("Failed to persist job %s to S3: %s", job["job_id"], e)


def load_persisted_jobs():
    """Load jobs from S3 on startup — restores jobs from before last restart.

    Pending/generating jobs resume polling. Completed/failed jobs are loaded
    for display in the Pending Jobs panel but don't need polling.
    Cleans up completed/failed job files older than 24 hours.
    """
    try:
        import boto3
        from backend.services.sagemaker_deployer import get_deployment_s3_bucket
        from backend.config import settings

        bucket = get_deployment_s3_bucket()
        if not bucket:
            return 0

        s3 = boto3.client("s3", region_name=settings.aws_region_models)
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=_JOBS_S3_PREFIX)
        files = resp.get("Contents", [])
        try:
            from backend.services.cost_tracker import add_background_s3_cost
            add_background_s3_cost("list", 0, "load persisted jobs listing")
        except Exception:
            pass

        loaded = 0
        pending = 0
        cleanup = []
        with _lock:
            for f in files:
                try:
                    obj = s3.get_object(Bucket=bucket, Key=f["Key"])
                    job_bytes = obj["Body"].read()
                    try:
                        from backend.services.cost_tracker import add_background_s3_cost as _bg_s3
                        _bg_s3("get", len(job_bytes), "load persisted job")
                    except Exception:
                        pass
                    job = json.loads(job_bytes.decode("utf-8"))
                    job_id = job.get("job_id")
                    if not job_id or job_id in _jobs:
                        continue

                    status = job.get("status", "")

                    # Clean up old completed/failed jobs (>24h)
                    submitted = job.get("submitted_at", "")
                    if submitted and status in (COMPLETE, FAILED):
                        age = (datetime.now(timezone.utc) - datetime.fromisoformat(submitted)).total_seconds()
                        if age > 86400:
                            cleanup.append(f["Key"])
                            continue

                    _jobs[job_id] = job
                    loaded += 1
                    if status in (PENDING, GENERATING):
                        pending += 1
                except Exception:
                    pass

        # Clean up old job files from S3
        for key in cleanup:
            try:
                s3.delete_object(Bucket=bucket, Key=key)
            except Exception:
                pass

        if loaded:
            logger.info("Restored %d async jobs from S3 (%d pending, %d cleaned up)",
                        loaded, pending, len(cleanup))
        return loaded
    except Exception as e:
        logger.debug("Failed to load persisted jobs: %s", e)
        return 0


def resume_pending_jobs() -> int:
    """Check all pending/generating jobs against S3 outputs on startup.

    For each pending job:
    - If output exists in S3: download image, save to gallery, mark complete, clean up S3
    - If output doesn't exist and job is >15 min old: mark failed (timed out)
    - If output doesn't exist and job is recent: leave as pending (poller will handle)

    Returns count of jobs resolved (completed + failed).
    """
    import boto3
    from backend.config import settings

    s3 = boto3.client("s3", region_name=settings.aws_region_models)
    resolved = 0

    with _lock:
        pending = [j for j in _jobs.values() if j["status"] in (PENDING, GENERATING)]

    for job in pending:
        try:
            output_location = job.get("output_location", "")
            if not output_location:
                continue

            parts = output_location.replace("s3://", "").split("/", 1)
            bucket, key = parts[0], parts[1]

            try:
                # Use head_object first to get LastModified (actual generation time)
                head = s3.head_object(Bucket=bucket, Key=key)
                s3_completed = head["LastModified"].astimezone(timezone.utc)

                obj = s3.get_object(Bucket=bucket, Key=key)
                body = obj["Body"].read()
                try:
                    from backend.services.cost_tracker import add_background_s3_cost
                    add_background_s3_cost("head", 0, "resume job head check")
                    add_background_s3_cost("get", len(body), "resume job output download")
                except Exception:
                    pass
                result = json.loads(body.decode("utf-8"))
                image_b64 = result.get("image", "")

                # Claim before finalizing — resume runs at startup CONCURRENTLY
                # with the live poller (both started in main.py lifespan), so both
                # can see the same output; the claim ensures only one saves it.
                if image_b64 and _claim_finalization(job):
                    image_bytes = base64.b64decode(image_b64)
                    # CRITICAL save (same guarantee as the live poller): if the
                    # gallery write fails or isn't durable on disk, release the
                    # claim, leave the job PENDING + S3 output intact, and skip
                    # cleanup so a later poll retries. Never delete the only copy
                    # of the image before it's safely in the gallery.
                    try:
                        image_path = _update_gallery_on_complete(job, image_bytes)
                        if not (image_path and os.path.isfile(image_path) and os.path.getsize(image_path) > 0):
                            raise IOError(f"gallery image not durable on disk: {image_path}")
                    except Exception as save_err:
                        with _lock:
                            job["_finalizing"] = False
                        if _is_host_wide_save_error(save_err):
                            # Host-level storage failure — stop resuming the rest;
                            # they'd all fail identically. Jobs stay PENDING + S3
                            # preserved; the live poller (with backoff) retries.
                            logger.error("⚠ Disk problem while restoring saved jobs (%s). Stopping restore; "
                                         "no jobs lost — the poller will retry them once disk recovers.", save_err)
                            break
                        logger.warning("Couldn't restore job %s: %s — kept in queue, will retry.",
                                       job["job_id"], save_err)
                        continue

                    # Use S3 object timestamp as the real completion time
                    # (not "now", which includes wait time after server restart)
                    submitted = datetime.fromisoformat(job["submitted_at"])
                    if submitted.tzinfo is None:
                        submitted = submitted.replace(tzinfo=timezone.utc)
                    duration = (s3_completed - submitted).total_seconds()
                    # Cap duration at 15 min — anything longer means the job
                    # waited in queue while the endpoint was at zero
                    duration = min(duration, 900)
                    compute_cost = _calculate_compute_cost(job["model_key"], duration)

                    with _lock:
                        job["status"] = COMPLETE
                        job["image_path"] = image_path
                        job["completed_at"] = s3_completed.isoformat()
                        job["progress"] = 100
                        job["duration_seconds"] = round(duration, 1)
                        job["compute_cost_usd"] = compute_cost

                    _track_completion(job, duration, compute_cost)
                    # Terminal state: _cleanup_s3 deletes the persisted job file
                    # (and input/output). Do NOT _persist_job_to_s3 afterwards —
                    # that would immediately re-create the file we just deleted,
                    # leaving a completed job lingering in S3 forever. (The live
                    # poller's completion path, above, is cleanup-only for the
                    # same reason.)
                    _cleanup_s3(job, s3)
                    resolved += 1
                    logger.info("Resumed job %s: complete (%d bytes, ~$%.4f)",
                                job["job_id"], len(image_bytes), compute_cost)
                else:
                    with _lock:
                        job["status"] = FAILED
                        job["error"] = "No image data in output"
                        job["completed_at"] = datetime.now(timezone.utc).isoformat()
                    _update_gallery_on_failure(job)
                    # Terminal state — cleanup only, no re-persist (see above).
                    _cleanup_s3(job, s3)
                    resolved += 1

            except Exception as e:
                if "NoSuchKey" in str(e) or "404" in str(e):
                    # Output not ready — check endpoint health before giving up
                    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(job["submitted_at"])).total_seconds()
                    should_fail = False
                    ep_name = _resolve_endpoint_for_job(job)
                    if ep_name and elapsed > 300:
                        try:
                            from backend.services.sagemaker_deployer import get_endpoint_health
                            health = get_endpoint_health(ep_name)
                            if health["failed"] or not health["alive"]:
                                should_fail = True
                            elif health["progressing"] and health.get("stale_seconds", 0) > 1800:
                                should_fail = True  # Stalled
                        except Exception:
                            pass
                    if should_fail:
                        with _lock:
                            job["status"] = FAILED
                            job["error"] = f"Timed out ({int(elapsed)}s) — endpoint may have failed or been deleted"
                            job["completed_at"] = datetime.now(timezone.utc).isoformat()
                        _update_gallery_on_failure(job)
                        _persist_job_to_s3(job)
                        resolved += 1
                    # else: still pending, poller will check later
                else:
                    logger.warning("Resume check failed for %s: %s", job["job_id"], e)

        except Exception as e:
            logger.warning("Resume job %s error: %s", job["job_id"], e)

    return resolved
