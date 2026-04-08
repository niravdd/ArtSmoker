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
    _persist_gallery_metadata(job)

    with _lock:
        _jobs[job_id] = job

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
    """Save the image and update gallery metadata when the async job completes."""
    from backend.config import settings

    asset_id = job["asset_id"]
    variant_dir = settings.generated_dir / f"{asset_id}_o{job['option_index']}_v{job['variation_index']}"
    variant_dir.mkdir(parents=True, exist_ok=True)

    # Save image
    image_path = variant_dir / "asset.png"
    image_path.write_bytes(image_bytes)

    # Update metadata
    meta_path = variant_dir / "metadata.json"
    try:
        meta = json.loads(meta_path.read_text())
    except Exception:
        meta = {}

    meta.update({
        "async_status": "complete",
        "async_completed_at": datetime.now(timezone.utc).isoformat(),
        "png_path": f"/api/gallery/{asset_id}_o{job['option_index']}_v{job['variation_index']}/png",
        "png_filename": "asset.png",
        "image_size_bytes": len(image_bytes),
    })
    meta_path.write_text(json.dumps(meta, indent=2))

    return str(image_path)


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
    _poller_stop.clear()
    _poller_thread = threading.Thread(target=_poll_loop, daemon=True, name="async-job-poller")
    _poller_thread.start()


def stop_poller():
    """Stop the background poller (called on shutdown)."""
    _poller_stop.set()


def _poll_loop():
    """Background loop: check S3 for completed async jobs every 30 seconds."""
    import boto3
    from backend.config import settings

    region = settings.aws_region_models

    while not _poller_stop.is_set():
        pending = []
        with _lock:
            pending = [j for j in _jobs.values() if j["status"] in (PENDING, GENERATING)]

        if not pending:
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

        # Poll interval — 30 seconds
        _poller_stop.wait(timeout=30)

    logger.debug("Async job poller stopped")


def _check_job(job: dict, s3):
    """Check if an async job's output has appeared in S3."""
    output_location = job["output_location"]

    # Parse S3 URI
    parts = output_location.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()

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
        image_path = _update_gallery_on_complete(job, image_bytes)

        with _lock:
            job["status"] = COMPLETE
            job["image_path"] = image_path
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            job["progress"] = 100

        logger.info("Async job complete: %s → %s (%d bytes)", job["job_id"], image_path, len(image_bytes))

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
            else:
                logger.debug("Async job %s: S3 check error (will retry): %s", job["job_id"], e)


def _update_progress(job: dict):
    """Estimate progress based on elapsed time."""
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(job["submitted_at"])).total_seconds()
    # Estimate based on typical latency (~180s for dev, ~30s for schnell)
    typical = 180 if "dev" in job["model_key"] else 30
    progress = min(95, int((elapsed / typical) * 100))
    with _lock:
        job["status"] = GENERATING
        job["progress"] = progress
