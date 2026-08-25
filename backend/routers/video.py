"""Video router — text-to-video generation, job management, and video serving."""

import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from backend.config import settings
from backend.services.model_registry import get_video_settings
from backend.services.prompt_templates import get_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])

# In-memory job tracker (persisted to disk on completion)
_active_jobs: dict[str, dict] = {}


# ── Request models ───────────────────────────────────────────────────────

class VideoGenerateRequest(BaseModel):
    model_key: str
    prompt: str
    task_type: str | None = None
    duration: int | str | None = None
    aspect_ratio: str | None = None
    resolution: str | None = None
    loop: bool | None = None
    seed: int | None = None
    source_image: str | None = None  # base64 encoded
    end_image: str | None = None  # base64 encoded
    shots: list[dict] | None = None
    region_override: str | None = None
    enhance_prompt: bool = True
    ui_lang: str = ""  # Frontend language selection — soft hint for prompt language detection


class VideoReviseRequest(BaseModel):
    video_id: str
    prompt: str
    model_key: str | None = None
    seed: int | None = None
    enhance_prompt: bool = True


# ── Generate ─────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_video(req: VideoGenerateRequest):
    """Start a video generation job.

    Returns immediately with a job_id. Frontend polls /status/{job_id}.
    """
    from backend.services.video_generator import start_video_generation
    from backend.services.bedrock_client import invoke_llm
    from backend.services.telemetry import track_video_generation, track_video_cost, track_first_generation
    from backend.services.model_registry import get_video_model
    import base64

    from backend.services.cost_tracker import reset_costs, get_total_cost
    reset_costs()

    # Estimate video model cost: price_per_second × duration — REGISTRY-sourced and
    # region-aware (video_pricing[model|region] when Sync-recorded, else the model's
    # base_price_per_second_usd). Uses the actual region the job will run in.
    dur = int(req.duration or 6)
    vid_cfg = get_video_model(req.model_key) if req.model_key else {}
    from backend.services.cost_tracker import resolve_video_price_per_sec
    _vregion = req.region_override or (vid_cfg.get("region") if vid_cfg else "") or ""
    price_per_sec = resolve_video_price_per_sec(vid_cfg, req.model_key or "", _vregion)
    estimated_video_cost = round((price_per_sec or 0) * dur, 4)

    vs = get_video_settings()
    if not vs.get("s3_bucket"):
        raise HTTPException(400, detail="S3 bucket not configured. Go to Settings → Video to set up your S3 bucket.")

    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(400, detail="Prompt is required")

    # Translate non-English prompts to English
    original_language_prompt = None
    original_language = "en"
    try:
        from backend.services.prompt_translator import translate_to_english
        tr = translate_to_english(prompt, ui_lang=req.ui_lang)
        original_language = tr["source_lang"]
        if tr["was_translated"]:
            original_language_prompt = prompt
            prompt = tr["translated"]
            logger.info("Video: translated %s → English: '%s'", original_language, prompt[:50])
    except Exception as exc:
        logger.warning("Video prompt translation failed: %s", exc)

    # Enhance prompt via LLM for better video results
    enhanced_prompt = prompt
    negative_concepts = ""
    if req.enhance_prompt:
        try:
            result = _enhance_video_prompt(prompt, req.model_key)
            enhanced_prompt = result["enhanced_prompt"]
            negative_concepts = result["negative_concepts"]
        except Exception as exc:
            logger.warning("Video prompt enhancement failed, using original: %s", exc)

    # Cost split (audit item T-c): the LLM enhancement cost was ACTUALLY spent at
    # request time → report it now. The video-model cost is reported at COMPLETION
    # (in _finalize_completed_job) so a failed/cancelled job never books video
    # spend that Bedrock didn't bill.
    llm_cost = round(get_total_cost(), 6)
    track_first_generation(model=req.model_key, studio="video")
    track_video_generation(model=req.model_key, duration_seconds=dur,
                           task_type=req.task_type or "")
    if llm_cost > 0:
        track_video_cost(cost_usd=llm_cost, model=req.model_key)

    # Decode source image if provided
    source_image = None
    if req.source_image:
        try:
            source_image = base64.b64decode(req.source_image)
        except Exception:
            raise HTTPException(400, detail="Invalid source_image base64")

    end_image = None
    if req.end_image:
        try:
            end_image = base64.b64decode(req.end_image)
        except Exception:
            raise HTTPException(400, detail="Invalid end_image base64")

    try:
        job = start_video_generation(
            model_key=req.model_key,
            prompt=enhanced_prompt,
            task_type=req.task_type,
            duration=req.duration,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
            loop=req.loop,
            seed=req.seed,
            source_image=source_image,
            end_image=end_image,
            shots=req.shots,
            region_override=req.region_override,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.error("Video generation failed: %s", exc)
        raise HTTPException(502, detail=f"Bedrock async invoke failed: {exc}")

    job["original_prompt"] = prompt
    job["original_language"] = original_language
    job["original_language_prompt"] = original_language_prompt
    job["enhanced_prompt"] = enhanced_prompt
    job["negative_concepts"] = negative_concepts
    # Video-model cost, reported at completion (see _finalize_completed_job).
    job["video_cost_usd"] = round(estimated_video_cost, 4)
    _active_jobs[job["job_id"]] = job

    return job


# ── Status polling ───────────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_video_status(job_id: str):
    """Check the status of a video generation job.

    Returns the job info with updated status. On completion, triggers
    thumbnail extraction and metadata saving.
    """
    from backend.services.video_generator import (
        get_job_status, download_video_from_s3, extract_thumbnail,
        get_video_metadata, get_s3_video_url,
    )

    job = _active_jobs.get(job_id)
    if not job:
        # Try loading from disk
        job = _load_job_from_disk(job_id)
        if not job:
            raise HTTPException(404, detail=f"Job {job_id} not found")

    # If already finalized, return cached status
    if job.get("status") in ("Completed", "Failed"):
        return job

    # Poll Bedrock
    try:
        status = get_job_status(job["invocation_arn"], job["region"])
    except Exception as exc:
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
        logger.error("Failed to poll job %s: %s", job_id, exc)
        raise HTTPException(502, detail=f"Failed to poll job status: {exc}")

    job["status"] = status["status"]
    job["end_time"] = status.get("end_time", "")
    job["failure_message"] = status.get("failure_message", "")

    if status["status"] == "Completed":
        _finalize_completed_job(job)

    if status["status"] == "Failed":
        job["completed_at"] = datetime.utcnow().isoformat()
        _save_job_to_disk(job)

    return job


# ── List jobs ────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_video_jobs(status: str | None = None, limit: int = 50):
    """List video generation jobs (active + recent completed from disk)."""
    jobs = list(_active_jobs.values())

    # Also load completed jobs from disk
    video_dir = settings.video_dir
    if video_dir.exists():
        for d in sorted(video_dir.iterdir(), reverse=True):
            if d.is_dir() and (d / "job.json").exists():
                if len(jobs) >= limit:
                    break
                try:
                    meta = json.loads((d / "job.json").read_text())
                    if meta.get("job_id") not in _active_jobs:
                        jobs.append(meta)
                except Exception:
                    pass

    if status:
        jobs = [j for j in jobs if j.get("status") == status]

    # Sort by started_at descending
    jobs.sort(key=lambda j: j.get("started_at", ""), reverse=True)
    return {"jobs": jobs[:limit]}


# ── Video serving ────────────────────────────────────────────────────────

@router.get("/{video_id}/mp4")
async def serve_video(video_id: str):
    """Serve a video MP4.

    If stored locally, serves the file directly.
    If S3-only, redirects to a presigned URL.
    """
    from backend.services.video_generator import get_s3_video_url, download_video_from_s3

    local_path = settings.video_dir / video_id / "video.mp4"
    if local_path.exists():
        return FileResponse(local_path, media_type="video/mp4")

    # Try S3 presigned URL
    job = _load_job_from_disk(video_id)
    if job and job.get("s3_bucket") and job.get("s3_prefix"):
        vs = get_video_settings()
        if not vs.get("store_local"):
            # S3-only mode: redirect to presigned URL
            url = get_s3_video_url(job["s3_bucket"], job["s3_prefix"])
            if url:
                return RedirectResponse(url)
        else:
            # Should be local but missing — try downloading
            dl_path = download_video_from_s3(
                job["s3_bucket"], job["s3_prefix"],
                settings.video_dir / video_id,
            )
            if dl_path and dl_path.exists():
                return FileResponse(dl_path, media_type="video/mp4")

    raise HTTPException(404, detail="Video not found")


@router.get("/{video_id}/thumbnail")
async def serve_thumbnail(video_id: str):
    """Serve the video thumbnail image."""
    thumb_path = settings.video_dir / video_id / "thumbnail.jpg"
    if thumb_path.exists():
        return FileResponse(thumb_path, media_type="image/jpeg")
    raise HTTPException(404, detail="Thumbnail not found")


@router.get("/{video_id}/metadata")
async def get_video_metadata_endpoint(video_id: str):
    """Return full metadata for a video asset."""
    job = _load_job_from_disk(video_id)
    if not job:
        raise HTTPException(404, detail=f"Video {video_id} not found")
    return job


# ── Revise ───────────────────────────────────────────────────────────────

@router.post("/revise")
async def revise_video(req: VideoReviseRequest):
    """Re-generate a video with a modified prompt (revision).

    Links the new job to the original video in metadata.
    """
    original = _load_job_from_disk(req.video_id)
    if not original:
        raise HTTPException(404, detail=f"Original video {req.video_id} not found")

    # Build a new generation request inheriting settings from the original
    gen_req = VideoGenerateRequest(
        model_key=req.model_key or original.get("model_key", ""),
        prompt=req.prompt,
        task_type=original.get("task_type"),
        duration=original.get("duration"),
        aspect_ratio=original.get("aspect_ratio"),
        resolution=original.get("resolution"),
        loop=original.get("loop"),
        seed=req.seed if req.seed is not None else original.get("seed"),
        enhance_prompt=req.enhance_prompt,
    )

    result = await generate_video(gen_req)
    result["revision_of"] = req.video_id
    result["revision_prompt"] = req.prompt
    _active_jobs[result["job_id"]] = result

    # Link revision in original metadata
    original.setdefault("revisions", []).append({
        "job_id": result["job_id"],
        "prompt": req.prompt,
        "created_at": result["started_at"],
    })
    _save_job_to_disk(original)

    return result


# ── Delete ───────────────────────────────────────────────────────────────

@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """Delete a video asset (local files + optionally S3)."""
    import shutil

    local_dir = settings.video_dir / video_id
    job = _load_job_from_disk(video_id)

    deleted_local = False
    if local_dir.exists():
        shutil.rmtree(local_dir)
        deleted_local = True

    # Remove from active jobs
    _active_jobs.pop(video_id, None)

    return {"deleted": video_id, "deleted_local": deleted_local}


# ── Internal helpers ─────────────────────────────────────────────────────

def _finalize_completed_job(job: dict):
    """Handle a completed video job: download, thumbnail, metadata."""
    from backend.services.video_generator import (
        download_video_from_s3, extract_thumbnail, get_video_metadata,
    )

    # Report the video-model cost NOW that generation actually completed (the
    # per-second price × requested duration; Bedrock bills successful renders).
    # Failed jobs never reach here → no phantom spend. The LLM-enhancement share
    # was reported at request time, when it was actually incurred.
    try:
        _vcost = float(job.get("video_cost_usd") or 0)
        if _vcost > 0:
            from backend.services.telemetry import track_video_cost
            track_video_cost(cost_usd=_vcost, model=job.get("model_key", ""))
    except Exception:
        pass

    job_id = job["job_id"]
    local_dir = settings.video_dir / job_id
    local_dir.mkdir(parents=True, exist_ok=True)

    vs = get_video_settings()

    # Always download to extract thumbnail and metadata
    mp4_path = download_video_from_s3(
        job["s3_bucket"], job["s3_prefix"], local_dir,
    )

    if mp4_path and mp4_path.exists():
        # Extract thumbnail
        thumb_path = local_dir / "thumbnail.jpg"
        extract_thumbnail(mp4_path, thumb_path)

        # Extract video metadata
        video_meta = get_video_metadata(mp4_path)
        job.update(video_meta)

        # If S3-only mode, delete the local MP4 (keep thumbnail + metadata)
        if not vs.get("store_local", True):
            mp4_path.unlink(missing_ok=True)
            job["video_stored"] = "s3"
        else:
            job["video_stored"] = "local"
    else:
        job["video_stored"] = "s3"
        logger.warning("Could not download MP4 for job %s", job_id)

    job["completed_at"] = datetime.utcnow().isoformat()
    job["video_id"] = job_id  # Alias for gallery integration
    job["asset_type"] = "video"

    # Thumbnail URL for gallery
    job["thumbnail_url"] = f"/api/video/{job_id}/thumbnail"
    job["video_url"] = f"/api/video/{job_id}/mp4"

    _save_job_to_disk(job)


def _save_job_to_disk(job: dict):
    """Persist job metadata to the video directory."""
    job_id = job.get("job_id") or job.get("video_id")
    if not job_id:
        return
    d = settings.video_dir / job_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "job.json").write_text(json.dumps(job, indent=2, default=str))


def _load_job_from_disk(job_id: str) -> dict | None:
    """Load job metadata from disk."""
    path = settings.video_dir / job_id / "job.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _enhance_video_prompt(prompt: str, model_key: str) -> dict:
    """Enhance a user prompt for video generation using LLM.

    Adds cinematic vocabulary, camera movement, temporal coherence cues.
    Since video models don't support negative prompts, any "avoid" concepts
    are woven into the positive prompt as avoidance language.
    Respects per-model prompt limits.

    Returns: {"enhanced_prompt": str, "negative_concepts": str}
    """
    from backend.services.bedrock_client import invoke_llm
    from backend.services.model_registry import get_video_model

    model_config = get_video_model(model_key)
    prompt_limit = model_config.get("prompt_limit", 512) if model_config else 512
    optimal_words = model_config.get("optimal_prompt_words", 50) if model_config else 50
    model_guidance = model_config.get("prompt_guidance", "") if model_config else ""
    if not model_guidance:
        family = model_config.get("format_family", "") if model_config else ""
        model_guidance = "Richly descriptive, up to 5000 characters." if "luma" in family else "Concise descriptive caption, 512 character limit."

    from backend.services.prompt_templates import get_system_prompt
    system_prompt = get_system_prompt('video_enhance_prompt').format(
        prompt_limit=prompt_limit,
        model_guidance=model_guidance,
        optimal_length=f"{optimal_words} words",
    )
    user_message = get_template('video_enhance_prompt').format(user_prompt=prompt)

    try:
        result = invoke_llm(
            prompt=user_message,
            system=system_prompt,
            max_tokens=700,
            complexity="fast",
        )

        enhanced = prompt
        negative = ""

        for line in result.strip().splitlines():
            line = line.strip()
            if line.upper().startswith("ENHANCED:"):
                enhanced = line[len("ENHANCED:"):].strip()
            elif line.upper().startswith("AVOID:"):
                neg = line[len("AVOID:"):].strip()
                if neg.lower() != "none":
                    negative = neg

        # If parsing failed (no ENHANCED: line), use the whole response
        if enhanced == prompt and "ENHANCED:" not in result.upper():
            enhanced = result.strip()

        # Truncate to model limit
        if len(enhanced) > prompt_limit:
            enhanced = enhanced[:prompt_limit - 3].rsplit(" ", 1)[0] + "..."

        return {"enhanced_prompt": enhanced, "negative_concepts": negative}
    except Exception as exc:
        logger.warning("Prompt enhancement failed: %s", exc)
        return {"enhanced_prompt": prompt, "negative_concepts": ""}
