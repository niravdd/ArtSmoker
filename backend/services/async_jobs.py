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
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Job storage (in-memory, survives for the session) ────────────────────

_jobs: dict = {}  # job_id → job dict
_lock = threading.Lock()
_poller_thread: threading.Thread | None = None
_poller_stop = threading.Event()

# Job statuses
PENDING = "pending"
GENERATING = "generating"
COMPLETE = "complete"
FAILED = "failed"

# Resubmission constants
STALE_JOB_THRESHOLD_SECONDS = 900   # 15 min before considering resubmission
MAX_RESUBMITS = 3                    # Max resubmission attempts per job
RESUBMIT_COOLDOWN_SECONDS = 60       # Min seconds between resubmission attempts


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
    (variant_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    logger.debug("Gallery metadata persisted for async job %s", job["job_id"])


def _update_gallery_on_complete(job: dict, image_bytes: bytes):
    """Save image, run post-processing (SVG/upscale/bg-remove), update metadata.

    Runs the same post-processing pipeline as sync jobs to ensure
    consistent gallery entries.
    """
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

    # Update existing metadata (created by generate router at submission time)
    meta_path = store.generated_asset_dir(asset_id) / "metadata.json"
    try:
        meta = json.loads(meta_path.read_text())
    except Exception:
        meta = {}

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


def _update_gallery_on_failure(job: dict):
    """Update gallery metadata when an async job fails."""
    from backend.config import settings

    asset_id = job["asset_id"]
    variant_dir = settings.generated_dir / f"{asset_id}_o{job['option_index']}_v{job['variation_index']}"
    meta_path = variant_dir / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            meta["async_status"] = "failed"
            meta["async_error"] = job.get("error", "Unknown error")
            meta_path.write_text(json.dumps(meta, indent=2))
        except Exception:
            pass


# ── Background Poller ────────────────────────────────────────────────────

def _ensure_poller():
    """Start the background poller if not already running."""
    global _poller_thread
    if _poller_thread and _poller_thread.is_alive():
        return

    # Restore persisted jobs from S3 (if any from before last restart)
    load_persisted_jobs()

    _poller_stop.clear()
    _poller_thread = threading.Thread(target=_poll_loop, daemon=True, name="async-job-poller")
    _poller_thread.start()


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
            _poller_stop.wait(timeout=5)
            continue

        s3 = boto3.client("s3", region_name=region)

        for job in pending:
            if _poller_stop.is_set():
                break
            try:
                _check_job(job, s3)
            except Exception as e:
                logger.warning("Async job poll error (%s): %s", job["job_id"], e)

        _flush_background_costs_if_due()
        _check_warm_period_closures()

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
    try:
        from backend.services.custom_models import get_catalog_model
        catalog = get_catalog_model(job["model_key"])
        if catalog:
            pricing = catalog.get("pricing", {})
            instance_costs = pricing.get("instance_cost_per_hour", {})
            recommended = catalog.get("requirements", {}).get("recommended_instance", "")
            hourly_rate = instance_costs.get(recommended, 0)
            if not hourly_rate and instance_costs:
                hourly_rate = min(instance_costs.values())
        else:
            hourly_rate = 1.41  # g5.xlarge fallback
    except Exception:
        hourly_rate = 1.41

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
        sm_runtime = boto3.client("sagemaker-runtime", region_name=settings.aws_region_models)

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


def _check_job(job: dict, s3):
    """Check if an async job's output has appeared in S3."""
    output_location = job["output_location"]

    # Parse S3 URI
    parts = output_location.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]

    # Check for failure file first — SageMaker writes errors to {output}.failure
    try:
        failure_key = key + ".failure"
        failure_obj = s3.get_object(Bucket=bucket, Key=failure_key)
        failure_body = failure_obj["Body"].read().decode("utf-8", errors="replace")
        with _lock:
            job["status"] = FAILED
            job["error"] = failure_body[:500] if failure_body else "Model returned an error (no details)"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _update_gallery_on_failure(job)
        _cleanup_s3(job, s3)
        # Also delete the failure file
        try:
            s3.delete_object(Bucket=bucket, Key=failure_key)
        except Exception:
            pass
        logger.warning("Async job %s failed (error output in S3): %s", job["job_id"], job["error"][:200])
        return
    except Exception:
        pass  # No failure file — check for success

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

        if not image_b64:
            with _lock:
                job["status"] = FAILED
                job["error"] = "Model returned no image data"
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
            _update_gallery_on_failure(job)
            return

        # Decode and save to gallery
        image_bytes = base64.b64decode(image_b64)
        completed_at = datetime.now(timezone.utc)
        image_path = _update_gallery_on_complete(job, image_bytes)

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

        # Clean up ALL S3 artifacts: input, output, AND job metadata.
        # Job is complete — gallery has the image, no need to keep S3 state.
        _cleanup_s3(job, s3)

        logger.info("Async job complete: %s → %s (%d bytes, %.0fs, ~$%.4f)",
                     job["job_id"], image_path, len(image_bytes), duration_seconds, compute_cost)

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

    # Try catalog first (has instance_cost_per_hour)
    catalog_model = get_catalog_model(model_key)
    hourly_rate = 0.0

    if catalog_model:
        pricing = catalog_model.get("pricing", {})
        instance_costs = pricing.get("instance_cost_per_hour", {})
        recommended = catalog_model.get("requirements", {}).get("recommended_instance", "")

        # Use the recommended instance's hourly rate
        if recommended and recommended in instance_costs:
            hourly_rate = instance_costs[recommended]
        elif instance_costs:
            # Fallback: use the first (cheapest) instance rate
            hourly_rate = min(instance_costs.values())

    if hourly_rate == 0:
        # Fallback: check deployed instance type in registry
        registry = get_registry()
        for section in ("image_models", "video_models"):
            reg_model = registry.get(section, {}).get(model_key, {})
            if reg_model.get("deployment", {}).get("instance_type"):
                # Default rates for common instances
                instance_type = reg_model["deployment"]["instance_type"]
                default_rates = {
                    "ml.g5.xlarge": 1.41,
                    "ml.g5.2xlarge": 2.82,
                    "ml.g5.4xlarge": 4.44,
                    "ml.g6e.xlarge": 2.61,
                    "ml.g6e.2xlarge": 2.8,
                    "ml.g6e.4xlarge": 3.76,
                    "ml.g6e.8xlarge": 5.66,
                    "ml.g7e.2xlarge": 4.37,
                    "ml.g7e.4xlarge": 5.19,
                    "ml.g7e.8xlarge": 6.85,
                    "ml.g7e.12xlarge": 10.75,
                }
                hourly_rate = default_rates.get(instance_type, 1.50)
                break

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
    """
    from backend.services.sagemaker_deployer import get_deployment_s3_bucket
    bucket = get_deployment_s3_bucket()

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

                if image_b64:
                    image_bytes = base64.b64decode(image_b64)
                    image_path = _update_gallery_on_complete(job, image_bytes)

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
                    _cleanup_s3(job, s3)
                    _persist_job_to_s3(job)
                    resolved += 1
                    logger.info("Resumed job %s: complete (%d bytes, ~$%.4f)",
                                job["job_id"], len(image_bytes), compute_cost)
                else:
                    with _lock:
                        job["status"] = FAILED
                        job["error"] = "No image data in output"
                        job["completed_at"] = datetime.now(timezone.utc).isoformat()
                    _update_gallery_on_failure(job)
                    _cleanup_s3(job, s3)
                    _persist_job_to_s3(job)
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
