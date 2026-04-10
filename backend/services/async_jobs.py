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


def submit_job(
    job_id: str,
    model_key: str,
    model_label: str,
    prompt: str,
    full_payload: dict,
    output_location: str,
    s3_bucket: str,
    s3_key: str,
    option_index: int = 0,
    variation_index: int = 0,
    generation_id: str = "",
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
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "option_index": option_index,
        "variation_index": variation_index,
        "generation_id": generation_id or asset_id,
        "status": PENDING,
        "progress": 0,
        "submitted_at": now,
        "completed_at": None,
        "image_path": None,
        "error": None,
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

    logger.info("Async job submitted: %s (%s) → %s", job_id, model_label, output_location)
    return job


def get_all_jobs() -> list:
    """Get all jobs (pending, complete, failed), newest first."""
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j["submitted_at"], reverse=True)


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
        "refined_prompt": job["full_prompt"],
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
            refined_prompt=job.get("full_prompt", ""),
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

        # Poll interval — 30 seconds
        _poller_stop.wait(timeout=30)

    # Final flush on shutdown
    _flush_background_costs_if_due(force=True)
    logger.debug("Async job poller stopped")


def _track_warm_period_start(job: dict):
    """Record when an endpoint becomes warm (first job starts generating)."""
    ep = job.get("_endpoint_name") or f"artsmoker-{job['model_key'].replace('_', '-')}"
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
    ep = job.get("_endpoint_name") or f"artsmoker-{job['model_key'].replace('_', '-')}"
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
                job_ep = j.get("_endpoint_name") or f"artsmoker-{j['model_key'].replace('_', '-')}"
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


def _check_job(job: dict, s3):
    """Check if an async job's output has appeared in S3."""
    output_location = job["output_location"]

    # Parse S3 URI
    parts = output_location.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]

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

        # Clean up S3 input and output files (no longer needed)
        _cleanup_s3(job, s3)

        # Persist job state to S3 (survives server restarts)
        _persist_job_to_s3(job)

        logger.info("Async job complete: %s → %s (%d bytes, %.0fs, ~$%.4f)",
                     job["job_id"], image_path, len(image_bytes), duration_seconds, compute_cost)

    except s3.exceptions.NoSuchKey:
        _update_progress(job)

    except Exception as e:
        if "NoSuchKey" in str(e) or "404" in str(e):
            _update_progress(job)
        else:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(job["submitted_at"])).total_seconds()
            if elapsed > 900:  # 15 minute timeout
                with _lock:
                    job["status"] = FAILED
                    job["error"] = f"Timed out after {int(elapsed)}s"
                    job["completed_at"] = datetime.now(timezone.utc).isoformat()
                _update_gallery_on_failure(job)
                _cleanup_s3(job, s3)
                _persist_job_to_s3(job)
            else:
                logger.debug("Async job %s: S3 check error (will retry): %s", job["job_id"], e)


def _update_progress(job: dict):
    """Update job stage based on elapsed time and endpoint state.

    SageMaker async has no intermediate progress — only submitted → complete.
    We show honest stage-based status instead of fake percentages.
    """
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(job["submitted_at"])).total_seconds()

    # Determine stage from elapsed time and what we know
    # Cold start (model download + load): 0-600s for large models
    # Generation: 30-300s depending on model
    if elapsed < 10:
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
                    "ml.g5.2xlarge": 1.52,
                    "ml.g5.4xlarge": 2.03,
                    "ml.g6e.xlarge": 2.61,
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


def _cleanup_s3(job: dict, s3):
    """Delete the S3 input and output files after job completes or fails."""
    try:
        # Delete output file
        output_loc = job.get("output_location", "")
        if output_loc:
            parts = output_loc.replace("s3://", "").split("/", 1)
            s3.delete_object(Bucket=parts[0], Key=parts[1])

        # Delete input file (find it by endpoint name + timestamp pattern)
        # The input was uploaded to inference-input/{endpoint}/{timestamp}.json
        # We don't store the exact input key, so we skip input cleanup for now
        # (inputs are tiny ~1KB files, not worth the complexity)

        logger.debug("Cleaned up S3 output for job %s", job["job_id"])
    except Exception as e:
        logger.debug("S3 cleanup failed for job %s: %s", job["job_id"], e)


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
            "s3_bucket": job.get("s3_bucket", ""),
            "s3_key": job.get("s3_key", ""),
            "option_index": job.get("option_index", 0),
            "variation_index": job.get("variation_index", 0),
            "generation_id": job.get("generation_id", ""),
            "generate_svg": job.get("generate_svg", False),
            "remove_bg": job.get("remove_bg", False),
            "upscale": job.get("upscale", False),
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

        loaded = 0
        pending = 0
        cleanup = []
        with _lock:
            for f in files:
                try:
                    obj = s3.get_object(Bucket=bucket, Key=f["Key"])
                    job = json.loads(obj["Body"].read().decode("utf-8"))
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
                    # Output not ready — check if timed out
                    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(job["submitted_at"])).total_seconds()
                    if elapsed > 900:
                        with _lock:
                            job["status"] = FAILED
                            job["error"] = f"Timed out ({int(elapsed)}s) — endpoint may have been at zero capacity"
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
