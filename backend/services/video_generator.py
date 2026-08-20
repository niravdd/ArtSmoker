"""Video generation service — async Bedrock invocation, S3 management, thumbnails.

Handles text-to-video generation via StartAsyncInvoke for Nova Reel and Luma Ray v2.
All model parameters are read from the registry — no hardcoded invocation structures.
"""

import base64
import copy
import json
import logging
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import boto3

from backend.config import settings
from backend.services.model_registry import (
    get_registry,
    get_video_model,
    get_video_settings,
)

logger = logging.getLogger(__name__)

# ── S3 / Bedrock client helpers ──────────────────────────────────────────

_s3_clients: dict[str, object] = {}


def _get_s3_client(region: str = "us-east-1"):
    if region not in _s3_clients:
        session_kwargs = {}
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile
        session = boto3.Session(region_name=region, **session_kwargs)
        _s3_clients[region] = session.client("s3")
    return _s3_clients[region]


def _get_runtime_client(region: str):
    """Get a bedrock-runtime client for the given region."""
    from backend.services.bedrock_client import _get_client
    return _get_client(region)


# ── Video generation ─────────────────────────────────────────────────────

def start_video_generation(
    model_key: str,
    prompt: str,
    *,
    task_type: str | None = None,
    duration: int | str | None = None,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    loop: bool | None = None,
    seed: int | None = None,
    source_image: bytes | None = None,
    end_image: bytes | None = None,
    shots: list[dict] | None = None,
    region_override: str | None = None,
) -> dict:
    """Start an async video generation job.

    Returns: {job_id, invocation_arn, model_key, s3_output_uri, ...}
    """
    model_config = get_video_model(model_key)
    if not model_config:
        raise ValueError(f"Unknown video model: {model_key}")

    model_id = model_config["model_id"]
    region = region_override or model_config["region"]
    family_name = model_config.get("format_family", "")

    registry = get_registry()
    family = registry.get("format_families", {}).get(family_name)
    if not family:
        raise ValueError(f"Unknown format family '{family_name}' for video model '{model_key}'")

    vs = get_video_settings()
    s3_bucket = vs.get("s3_bucket")
    if not s3_bucket:
        raise ValueError("S3 bucket not configured. Set it in Video Settings before generating.")

    s3_prefix = vs.get("s3_prefix", "artsmoker/video/").rstrip("/")
    job_id = str(uuid.uuid4())[:12]
    s3_output_uri = f"s3://{s3_bucket}/{s3_prefix}/{job_id}/"

    # Build the request body from the format family
    body = _build_video_body(
        family=family,
        prompt=prompt,
        task_type=task_type,
        duration=duration,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        loop=loop,
        seed=seed,
        source_image=source_image,
        end_image=end_image,
        shots=shots,
        model_config=model_config,
    )

    # Invoke
    client = _get_runtime_client(region)
    label = model_config.get("label", model_key)
    logger.info("Starting async video generation: %s (%s) in %s, job=%s",
                label, model_id, region, job_id)

    try:
        response = client.start_async_invoke(
            modelId=model_id,
            modelInput=body,
            outputDataConfig={
                "s3OutputDataConfig": {"s3Uri": s3_output_uri}
            },
        )
    except Exception as _inv_exc:
        # Reactive lifecycle gate (same as images): a Legacy video model this account
        # can no longer access → record per-user so it drops from the picker. Only on
        # a real confirmed failure — a Legacy model still in active use keeps working.
        from backend.services.model_registry import is_legacy_unavailable_error, mark_lifecycle_unavailable
        if is_legacy_unavailable_error(_inv_exc):
            mark_lifecycle_unavailable("video_models", model_key)
            logger.warning("Video model %s is Legacy and no longer accessible for this account — excluded from pickers", model_key)
        raise

    invocation_arn = response["invocationArn"]
    logger.info("Async invoke started: arn=%s", invocation_arn)

    return {
        "job_id": job_id,
        "invocation_arn": invocation_arn,
        "model_key": model_key,
        "model_label": label,
        "model_id": model_id,
        "region": region,
        "s3_output_uri": s3_output_uri,
        "s3_bucket": s3_bucket,
        "s3_prefix": f"{s3_prefix}/{job_id}/",
        "prompt": prompt,
        "task_type": task_type or family.get("body_template", {}).get("taskType", ""),
        "started_at": datetime.utcnow().isoformat(),
        "status": "InProgress",
    }


def _build_video_body(
    family: dict,
    prompt: str,
    task_type: str | None,
    duration: int | str | None,
    aspect_ratio: str | None,
    resolution: str | None,
    loop: bool | None,
    seed: int | None,
    source_image: bytes | None,
    end_image: bytes | None,
    shots: list[dict] | None,
    model_config: dict,
) -> dict:
    """Build the model-specific request body from the format family."""
    from backend.services.bedrock_client import _set_nested, _deep_merge

    # If family has task_types (Nova Reel), pick the right sub-template
    task_types = family.get("task_types", {})
    if task_types and task_type and task_type in task_types:
        tt = task_types[task_type]
        body = copy.deepcopy(tt["body_template"])
        prompt_path = tt.get("prompt_path", family.get("prompt_path", "prompt"))
    else:
        body = copy.deepcopy(family["body_template"])
        prompt_path = family.get("prompt_path", "prompt")

    # Set prompt — handle multi-shot manual differently
    if task_type == "MULTI_SHOT_MANUAL" and shots:
        body["multiShotManualParams"]["shots"] = []
        for shot in shots:
            shot_entry = {"text": shot.get("text", "")}
            if shot.get("image"):
                img_bytes = shot["image"] if isinstance(shot["image"], bytes) else base64.b64decode(shot["image"])
                shot_entry["image"] = {
                    "format": "png",
                    "source": {"bytes": base64.b64encode(img_bytes).decode("ascii")},
                }
            body["multiShotManualParams"]["shots"].append(shot_entry)
    elif prompt_path:
        _set_nested(body, prompt_path, prompt)

    # Set seed
    seed_path = family.get("seed_path")
    if seed is not None and seed_path:
        _set_nested(body, seed_path, seed)

    # Duration — Nova Reel uses integer seconds in videoGenerationConfig
    if duration is not None:
        if "videoGenerationConfig" in body:
            body["videoGenerationConfig"]["durationSeconds"] = int(duration)
        elif "duration" in body:
            # Luma Ray uses string like "5s"
            body["duration"] = str(duration) if str(duration).endswith("s") else f"{duration}s"

    # Aspect ratio (Luma Ray)
    if aspect_ratio is not None and "aspect_ratio" in body:
        body["aspect_ratio"] = aspect_ratio

    # Resolution (Luma Ray)
    if resolution is not None and "resolution" in body:
        body["resolution"] = resolution

    # Loop (Luma Ray)
    if loop is not None and "loop" in body:
        body["loop"] = loop

    # Source image (image-to-video)
    if source_image:
        img_b64 = base64.b64encode(source_image).decode("ascii")
        if "textToVideoParams" in body:
            # Nova Reel: images array in textToVideoParams
            body["textToVideoParams"]["images"] = [{
                "format": "png",
                "source": {"bytes": img_b64},
            }]
        elif "keyframes" in body or family.get("parameters", {}).get("source_image"):
            # Luma Ray: keyframes.frame0
            body["keyframes"] = {
                "frame0": {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                }
            }

    # End image (Luma Ray only)
    if end_image:
        img_b64 = base64.b64encode(end_image).decode("ascii")
        body.setdefault("keyframes", {})["frame1"] = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": img_b64,
            },
        }

    return body


# ── Job status polling ───────────────────────────────────────────────────

def get_job_status(invocation_arn: str, region: str) -> dict:
    """Poll the status of an async video generation job.

    Returns: {status, invocation_arn, submit_time, end_time, failure_message, output_uri}
    """
    client = _get_runtime_client(region)
    response = client.get_async_invoke(invocationArn=invocation_arn)

    result = {
        "status": response.get("status", "Unknown"),
        "invocation_arn": invocation_arn,
        "submit_time": str(response.get("submitTime", "")),
        "end_time": str(response.get("endTime", "")),
        "failure_message": response.get("failureMessage", ""),
    }

    # Extract S3 output URI if completed
    odc = response.get("outputDataConfig", {})
    s3cfg = odc.get("s3OutputDataConfig", {})
    result["s3_output_uri"] = s3cfg.get("s3Uri", "")

    return result


# ── Video download & thumbnail extraction ────────────────────────────────

def download_video_from_s3(s3_bucket: str, s3_prefix: str, local_dir: Path) -> Path | None:
    """Download the output.mp4 from S3 to a local directory.

    Returns the local path to the MP4, or None if not found.
    """
    s3 = _get_s3_client()
    local_dir.mkdir(parents=True, exist_ok=True)

    # List objects to find the MP4
    prefix = s3_prefix.rstrip("/") + "/"
    try:
        resp = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
        try:
            from backend.services.cost_tracker import add_s3_cost
            add_s3_cost("list", 0, "video output listing")
        except Exception:
            pass
    except Exception as exc:
        logger.error("Failed to list S3 objects: %s", exc)
        return None

    mp4_key = None
    for obj in resp.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".mp4") and "output" in key.lower():
            mp4_key = key
            break
    if not mp4_key:
        # Fallback: any MP4 that isn't a shot fragment
        for obj in resp.get("Contents", []):
            if obj["Key"].endswith(".mp4"):
                mp4_key = obj["Key"]
                break

    if not mp4_key:
        logger.warning("No MP4 found in s3://%s/%s", s3_bucket, prefix)
        return None

    local_path = local_dir / "video.mp4"
    logger.info("Downloading s3://%s/%s → %s", s3_bucket, mp4_key, local_path)
    s3.download_file(s3_bucket, mp4_key, str(local_path))

    # Track S3 download cost (video files can be 5-100MB)
    try:
        file_size = local_path.stat().st_size
        from backend.services.cost_tracker import add_s3_cost
        add_s3_cost("get", file_size, f"video download ({file_size // 1024}KB)")
    except Exception:
        pass

    return local_path


def extract_thumbnail(video_path: Path, output_path: Path) -> bool:
    """Extract the first frame from an MP4 as a JPEG thumbnail.

    Uses ffmpeg if available, otherwise falls back to a placeholder.
    """
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video_path),
                "-vframes", "1", "-q:v", "2",
                "-vf", "scale=480:-1",
                str(output_path),
            ],
            capture_output=True, timeout=15, check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg thumbnail extraction failed: %s", exc)
        return False


def get_video_metadata(video_path: Path) -> dict:
    """Extract video metadata (duration, resolution, fps) using ffprobe.

    Returns dict with duration_seconds, width, height, fps, file_size_bytes.
    """
    meta = {"file_size_bytes": video_path.stat().st_size if video_path.exists() else 0}
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(video_path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            fmt = info.get("format", {})
            meta["duration_seconds"] = float(fmt.get("duration", 0))

            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    meta["width"] = stream.get("width", 0)
                    meta["height"] = stream.get("height", 0)
                    # Parse fps from r_frame_rate (e.g. "24/1")
                    fps_str = stream.get("r_frame_rate", "0/1")
                    parts = fps_str.split("/")
                    if len(parts) == 2 and int(parts[1]) > 0:
                        meta["fps"] = round(int(parts[0]) / int(parts[1]), 2)
                    break
    except Exception as exc:
        logger.warning("ffprobe metadata extraction failed: %s", exc)

    return meta


def get_s3_video_url(s3_bucket: str, s3_prefix: str, expires: int = 3600) -> str | None:
    """Generate a presigned S3 URL for streaming a video.

    Used when store_local is False — the frontend streams directly from S3.
    """
    s3 = _get_s3_client()
    prefix = s3_prefix.rstrip("/") + "/"

    try:
        resp = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
        try:
            from backend.services.cost_tracker import add_s3_cost
            add_s3_cost("list", 0, "video presigned URL listing")
        except Exception:
            pass
    except Exception:
        return None

    mp4_key = None
    for obj in resp.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".mp4"):
            if "output" in key.lower():
                mp4_key = key
                break
            if mp4_key is None:
                mp4_key = key

    if not mp4_key:
        return None

    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": s3_bucket, "Key": mp4_key},
        ExpiresIn=expires,
    )
