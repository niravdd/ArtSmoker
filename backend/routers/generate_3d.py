"""3D model generation router — image-to-3D via TripoSG on SageMaker."""

import base64
import json
import logging
import time
from datetime import datetime
from uuid import uuid4

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.model_registry import get_registry, _save
from backend.services.sagemaker_deployer import get_deployment_s3_bucket, S3_MODEL_PREFIX
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate/3d", tags=["3d"])

# In-memory job tracker for 3D generation
_3d_jobs: dict[str, dict] = {}

# S3 prefix for persisted 3D jobs — kept SEPARATE from the 2D async-jobs prefix
# (artsmoker/async-jobs/) so the two systems never read each other's records.
_3D_JOBS_S3_PREFIX = "artsmoker/3d-jobs/"


_3d_lifecycle_ensured: set = set()


def _ensure_3d_jobs_lifecycle(bucket: str) -> None:
    """Add a 1-day auto-expiry lifecycle rule for the 3d-jobs prefix.

    Idempotent, runs at most once per bucket per session. Ensures stale,
    failed, or stuck 3D job records don't accumulate in S3 indefinitely.
    """
    if bucket in _3d_lifecycle_ensured:
        return
    _3d_lifecycle_ensured.add(bucket)
    try:
        s3 = boto3.client("s3", region_name=_get_region())
        rule_id = "artsmoker-3d-jobs-cleanup"
        try:
            existing = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
            rules = existing.get("Rules", [])
        except Exception:
            rules = []
        if any(r.get("ID") == rule_id for r in rules):
            return
        rules.append({
            "ID": rule_id,
            "Filter": {"Prefix": _3D_JOBS_S3_PREFIX},
            "Status": "Enabled",
            "Expiration": {"Days": 1},
        })
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration={"Rules": rules},
        )
        logger.info("S3 lifecycle: %s/%s auto-expires after 1 day", bucket, _3D_JOBS_S3_PREFIX)
    except Exception as exc:
        logger.debug("3D jobs lifecycle setup: %s", exc)


def _persist_3d_job(job: dict) -> None:
    """Persist a 3D job to S3 so it survives server restarts.

    Mirrors the 2D async_jobs pattern but under its own prefix. Best-effort:
    failures are logged and never block the request.
    """
    try:
        bucket = get_deployment_s3_bucket()
        if not bucket:
            return
        _ensure_3d_jobs_lifecycle(bucket)
        s3 = boto3.client("s3", region_name=_get_region())
        body = json.dumps(job, default=str).encode()
        s3.put_object(
            Bucket=bucket,
            Key=f"{_3D_JOBS_S3_PREFIX}{job['job_id']}.json",
            Body=body,
            ContentType="application/json",
        )
    except Exception as e:
        logger.debug("Failed to persist 3D job %s: %s", job.get("job_id"), e)


def _delete_persisted_3d_job(job_id: str) -> None:
    """Remove a persisted 3D job from S3 (after terminal cleanup)."""
    try:
        bucket = get_deployment_s3_bucket()
        if not bucket:
            return
        s3 = boto3.client("s3", region_name=_get_region())
        s3.delete_object(Bucket=bucket, Key=f"{_3D_JOBS_S3_PREFIX}{job_id}.json")
    except Exception as e:
        logger.debug("Failed to delete persisted 3D job %s: %s", job_id, e)


def load_persisted_3d_jobs() -> None:
    """Restore 3D jobs from S3 on startup (called from app startup).

    Loads in-progress jobs into _3d_jobs so they survive a server restart.
    Prunes stale records: terminal (complete/failed) jobs and stuck jobs
    (submitted/generating with no update for >2h) are deleted from S3 so
    they don't accumulate — complements the 1-day S3 lifecycle rule.
    """
    try:
        from datetime import datetime as _dt, timezone as _tz
        bucket = get_deployment_s3_bucket()
        if not bucket:
            return
        s3 = boto3.client("s3", region_name=_get_region())
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=_3D_JOBS_S3_PREFIX)
        loaded, pruned = 0, 0
        now = _dt.now(_tz.utc)
        for obj in resp.get("Contents", []):
            try:
                body = s3.get_object(Bucket=bucket, Key=obj["Key"])
                job = json.loads(body["Body"].read())
            except Exception:
                continue
            jid = job.get("job_id")
            if not jid:
                continue
            status = job.get("status", "")
            # Prune terminal jobs and stuck non-terminal jobs (>2h old).
            stale = status in ("complete", "failed")
            if not stale:
                try:
                    submitted = job.get("submitted_at", "")
                    age_h = (now - _dt.fromisoformat(submitted)).total_seconds() / 3600 if submitted else 0
                    if age_h > 2:
                        stale = True
                except Exception:
                    pass
            if stale:
                _delete_persisted_3d_job(jid)
                # Keep terminal jobs in memory for status lookups; drop stuck ones.
                if status in ("complete", "failed"):
                    _3d_jobs[jid] = job
                pruned += 1
                continue
            _3d_jobs[jid] = job
            loaded += 1
        if loaded or pruned:
            logger.info("3D jobs restored: %d active, %d stale pruned", loaded, pruned)
    except Exception as e:
        logger.debug("Failed to load persisted 3D jobs: %s", e)


def _list_triposg_models() -> list[tuple[str, dict]]:
    """List ALL deployed TripoSG instances in the registry.

    A user can deploy TripoSG on several instance types (e.g. g6e and g5),
    each a separate registry entry keyed like ``triposg_<hash>``. Returns
    every entry that is a deployed TripoSG instance, sorted newest-first by
    deployment timestamp so the most recent endpoint leads any chooser.
    """
    registry = get_registry()
    found: list[tuple[str, dict]] = []
    for section in ("image_models", "post_processing"):
        for key, cfg in registry.get(section, {}).items():
            if cfg.get("catalog_key") != "triposg":
                continue
            if cfg.get("model_source") != "custom_hosted":
                continue
            dep = cfg.get("deployment", {})
            if not dep.get("endpoint_name"):
                continue
            found.append((key, cfg))

    def _created(item: tuple[str, dict]) -> str:
        # Sort by deployment.created_at (ISO8601); missing → empty sorts last.
        return item[1].get("deployment", {}).get("created_at", "") or ""

    found.sort(key=_created, reverse=True)
    return found


def _find_triposg_model(model_key: str | None = None) -> tuple[str | None, dict | None]:
    """Resolve a deployed TripoSG model.

    If ``model_key`` is given, return that specific deployed instance (so the
    user's chooser selection is honored); otherwise return the newest deployed
    instance. Returns (None, None) if no match.
    """
    models = _list_triposg_models()
    if not models:
        return None, None
    if model_key:
        for key, cfg in models:
            if key == model_key:
                return key, cfg
        return None, None  # requested instance not found / not a triposg instance
    return models[0]  # newest


def _get_region() -> str:
    region = boto3.Session().region_name
    if region:
        return region
    from backend.config import settings
    return settings.aws_region_models


# ── Request / Response models ─────────────────────────────────────────────

class ThreeDDefaultsRequest(BaseModel):
    steps: int = 50
    guidance_scale: float = 7.0
    faces: int = 200000
    octree_depth: int = 7
    quality: str = "standard"


class ThreeDGenerateRequest(BaseModel):
    asset_id: str
    version: int = 1
    # Optional: target a specific deployed TripoSG instance (from the chooser).
    # When omitted, the newest deployed instance is used.
    model_key: str | None = None
    quality: str = "standard"
    steps: int = 50
    # Frontend sends `guidance` and `max_faces`/`mesh_resolution`; accept those
    # names as aliases so the user's quality-preset choices actually reach the model.
    guidance: float | None = None
    guidance_scale: float = 7.0
    seed: int | None = None
    max_faces: int | None = None
    faces: int = 200000
    mesh_resolution: int | None = None
    octree_depth: int = 7
    # Texturing backend: "mvadapter" (default) or "hunyuan" (Hunyuan3D-Paint).
    # When omitted, the endpoint's server default (ARTSMOKER_TEXTURE_BACKEND) is used.
    texture_backend: str | None = None
    # Diagnostic/debug passthroughs for the texture bake (forwarded to the handler
    # only when set): toggle per-gate coverage logging + A/B the Kaolin rasterizer
    # convention (y-flip / z-sign) and rasterizer choice without a redeploy.
    debug_texture: int | None = None
    rasterizer: str | None = None
    kaolin_yflip: int | None = None
    kaolin_zsign: float | None = None
    kaolin_outflip: int | None = None
    kaolin_nflip: int | None = None
    delight: int | None = None
    ref_lift: float | None = None
    normal_map: int | None = None
    # TRELLIS.2 texture-quality knobs (forwarded only when set): PBR atlas size
    # (2048 default in TRELLIS.2 → 4096 for sharpness) + SLAT voxel resolution.
    texture_size: int | None = None
    tex_resolution: int | None = None

    def resolved_guidance(self) -> float:
        return self.guidance if self.guidance is not None else self.guidance_scale

    def resolved_faces(self) -> int:
        return self.max_faces if self.max_faces is not None else self.faces

    def resolved_octree_depth(self) -> int:
        # Frontend mesh_resolution (grid size) → TripoSG octree depth.
        # 128→7, 256→8, 512→9. Higher = finer geometry (facial detail).
        if self.mesh_resolution is not None:
            return {128: 7, 256: 8, 512: 9}.get(self.mesh_resolution, 8)
        return self.octree_depth


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/available")
async def check_3d_available():
    """Check if a 3D generation model (TripoSG) is deployed and available."""
    model_key, cfg = _find_triposg_model()
    if not model_key or not cfg:
        return {"available": False, "model_key": None, "endpoint_name": None}

    dep = cfg.get("deployment", {})
    endpoint_name = dep.get("endpoint_name")
    enabled = cfg.get("enabled", True)

    available = bool(endpoint_name and enabled)
    return {
        "available": available,
        "model_key": model_key,
        "endpoint_name": endpoint_name,
    }


def _instance_label(key: str, cfg: dict) -> str:
    """Human-friendly label for a deployed TripoSG instance chooser option.

    Prefers the registry label (which already carries a deploy timestamp, e.g.
    "TripoSG (02Jun 12:14)"); otherwise composes one from instance type +
    created_at so each instance is distinguishable by when it was deployed.
    """
    label = cfg.get("label")
    if label:
        return label
    dep = cfg.get("deployment", {})
    inst = dep.get("instance_type", "")
    created = dep.get("created_at", "")
    stamp = ""
    if created:
        try:
            stamp = datetime.fromisoformat(created).strftime("%d%b %H:%M")
        except Exception:
            stamp = created[:16]
    parts = ["TripoSG"]
    if inst:
        parts.append(inst.replace("ml.", ""))
    if stamp:
        parts.append(f"({stamp})")
    return " ".join(parts)


@router.get("/instances")
async def list_3d_instances(verify: bool = True):
    """List all deployed TripoSG instances the user can target.

    Powers the model chooser in the 3D dialog — like the Image Studio model
    chooser, but scoped to deployed TripoSG endpoints. Newest first. Each entry
    carries a timestamped label so users can pick a specific endpoint.

    Self-healing: when ``verify`` (default), each entry's endpoint is checked
    against live SageMaker. Entries whose endpoint no longer exists (NotFound)
    or has Failed (e.g. a deploy that lost the capacity race) are skipped AND
    auto-unregistered from the registry, so stale rows don't accumulate. Pass
    verify=false to skip the AWS round-trips (fast, registry-only).
    """
    check_status = None
    unregister = None
    if verify:
        try:
            from backend.services.sagemaker_deployer import check_endpoint_status
            from backend.routers.custom_deploy import _unregister_custom_model
            check_status = check_endpoint_status
            unregister = _unregister_custom_model
        except Exception:
            check_status = None  # fall back to registry-only if imports fail
            unregister = None

    instances = []
    stale: list[str] = []
    for key, cfg in _list_triposg_models():
        dep = cfg.get("deployment", {})
        endpoint_name = dep.get("endpoint_name")

        live_status = None
        if check_status and endpoint_name:
            try:
                live_status = check_status(endpoint_name).get("status")
            except Exception:
                live_status = None  # network hiccup → don't drop the entry
            # Drop + unregister endpoints that are gone or failed.
            if live_status in ("NotFound", "Failed"):
                stale.append(key)
                continue

        enabled = cfg.get("enabled", True)
        ready = bool(dep.get("model_ready") or cfg.get("model_ready"))
        inst_type = dep.get("instance_type", "")
        # Texture backend + est. cost/time for the 3D form's live estimate. Pull
        # the per-backend latency + per-instance hourly cost from the catalog so
        # the UI can show "~N min, ~$X" per choice (registry-driven, no hardcode).
        tex_backend = dep.get("texture_backend") or ""
        cost_per_hr = None
        latency_s = None
        try:
            from backend.services.custom_models import get_catalog_model
            cat = get_catalog_model(cfg.get("catalog_key", "triposg")) or {}
            cost_per_hr = (cat.get("pricing", {}).get("instance_cost_per_hour", {}) or {}).get(inst_type)
            tb_opts = (cat.get("texture_backends", {}).get("options", {}) or {})
            if tex_backend and tex_backend in tb_opts:
                latency_s = tb_opts[tex_backend].get("typical_latency_seconds")
            if latency_s is None:
                latency_s = cat.get("invoke", {}).get("typical_latency_seconds")
        except Exception:
            pass
        instances.append({
            "model_key": key,
            "endpoint_name": endpoint_name,
            "instance_type": inst_type,
            "created_at": dep.get("created_at", ""),
            "status": live_status or ("InService" if ready else "Unknown"),
            "model_ready": ready,
            "enabled": bool(enabled),
            "available": bool(endpoint_name and enabled),
            "label": _instance_label(key, cfg),
            "texture_backend": tex_backend,
            "cost_per_hour_usd": cost_per_hr,
            "typical_latency_seconds": latency_s,
        })

    # Self-heal: remove stale registry entries (endpoint deleted or failed).
    if stale and unregister:
        for key in stale:
            try:
                unregister(key)
                logger.info("Removed stale TripoSG registry entry %s (endpoint gone/failed)", key)
            except Exception as e:
                logger.warning("Could not unregister stale TripoSG entry %s: %s", key, e)

    return {"instances": instances, "count": len(instances)}


@router.get("/defaults")
async def get_3d_defaults():
    """Return user's saved default 3D generation parameters."""
    registry = get_registry()
    defaults = registry.get("three_d_defaults")
    if defaults and isinstance(defaults, dict):
        return {
            "steps": defaults.get("steps", 50),
            "guidance_scale": defaults.get("guidance_scale", 7.0),
            "faces": defaults.get("faces", 200000),
            "octree_depth": defaults.get("octree_depth", 7),
            "quality": defaults.get("quality", "standard"),
        }
    return {
        "steps": 50,
        "guidance_scale": 7.0,
        "faces": 200000,
        "octree_depth": 7,
        "quality": "standard",
    }


@router.put("/defaults")
async def save_3d_defaults(body: ThreeDDefaultsRequest):
    """Save user's default 3D generation parameters."""
    registry = get_registry()
    registry["three_d_defaults"] = {
        "steps": body.steps,
        "guidance_scale": body.guidance_scale,
        "faces": body.faces,
        "octree_depth": body.octree_depth,
        "quality": body.quality,
    }
    _save()
    return {"saved": True}


@router.post("/")
async def generate_3d(body: ThreeDGenerateRequest):
    """Submit a 3D generation job (image-to-3D via TripoSG)."""
    # Honor the chooser selection if provided; else use the newest instance.
    model_key, cfg = _find_triposg_model(body.model_key)
    if not model_key or not cfg:
        if body.model_key:
            raise HTTPException(400, detail=f"Selected 3D model instance '{body.model_key}' is not a deployed TripoSG endpoint.")
        raise HTTPException(400, detail="No 3D generation model (TripoSG) is deployed.")

    dep = cfg.get("deployment", {})
    endpoint_name = dep.get("endpoint_name")
    enabled = cfg.get("enabled", True)

    if not endpoint_name or not enabled:
        raise HTTPException(400, detail="3D generation model is not deployed. Deploy from Custom Models first.")

    # Read the source image
    if body.version == 1:
        image_path = store.get_generated_file_path(body.asset_id, "asset.png")
    else:
        image_path = store.get_generated_file_path(body.asset_id, f"asset_v{body.version}.png")

    if image_path is None:
        raise HTTPException(404, detail=f"Image not found for asset '{body.asset_id}' version {body.version}.")

    image_bytes = image_path.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Build payload — use resolved values so the frontend's quality-preset
    # choices (guidance, max_faces, mesh_resolution) actually reach the model.
    _octree = body.resolved_octree_depth()
    payload = {
        "image": image_b64,
        "num_inference_steps": body.steps,
        "guidance_scale": body.resolved_guidance(),
        "seed": body.seed,
        "faces": body.resolved_faces(),
        "dense_octree_depth": _octree,
        "hierarchical_octree_depth": _octree + 1,
    }
    # Per-request texturing backend override (else endpoint server default).
    if body.texture_backend:
        payload["texture_backend"] = body.texture_backend

    # Debug/diagnostic passthroughs for the texture bake (rasterizer convention
    # A/B testing without a redeploy). Only forwarded when set. See
    # _generate_texture_mvpainter's per-request override block.
    for _f in ("debug_texture", "rasterizer", "kaolin_yflip", "kaolin_zsign", "kaolin_outflip", "kaolin_nflip", "delight", "ref_lift", "normal_map", "texture_size", "tex_resolution"):
        _v = getattr(body, _f, None)
        if _v is not None:
            payload[_f] = _v

    # Upload payload to S3 for async invocation
    bucket = get_deployment_s3_bucket()
    if not bucket:
        raise HTTPException(400, detail="S3 bucket not configured for custom model storage.")

    region = _get_region()
    input_key = f"{S3_MODEL_PREFIX}/inference-input/{endpoint_name}/{int(time.time() * 1000)}.json"
    payload_bytes = json.dumps(payload).encode()

    s3 = boto3.client("s3", region_name=region)
    s3.put_object(
        Bucket=bucket,
        Key=input_key,
        Body=payload_bytes,
        ContentType="application/json",
    )
    input_location = f"s3://{bucket}/{input_key}"

    # Invoke endpoint async
    from botocore.config import Config as BotoConfig
    sm_config = BotoConfig(connect_timeout=10, read_timeout=120, retries={"max_attempts": 2})
    sm_runtime = boto3.client("sagemaker-runtime", region_name=region, config=sm_config)

    invoke_kwargs = {
        "EndpointName": endpoint_name,
        "ContentType": "application/json",
        "InputLocation": input_location,
    }

    # TripoSG image-to-3D is long-running: at high quality (octree depth 9) the
    # CPU-bound marching-cubes surface extraction alone takes ~10 min, plus
    # multi-view generation + texture baking — a full run can be ~16-18 min.
    # SageMaker async gives the container InvocationTimeoutSeconds to process
    # each request; if it elapses, the request is recycled (worker restarts,
    # job lost). ALWAYS set it (the old `> 300` guard skipped it because the
    # catalog under-reported latency as 60s), with a generous 1800s (30 min)
    # floor for headroom and the 3600s (1 hr) SageMaker async ceiling.
    typical_latency = cfg.get("invoke", {}).get("typical_latency_seconds", 300)
    invoke_kwargs["InvocationTimeoutSeconds"] = min(3600, max(1800, typical_latency * 2))

    try:
        response = sm_runtime.invoke_endpoint_async(**invoke_kwargs)
    except Exception as exc:
        logger.error("3D generation async invoke failed: %s", exc)
        raise HTTPException(502, detail=f"Failed to submit 3D generation job: {exc}")

    output_location = response.get("OutputLocation")
    if not output_location:
        raise HTTPException(502, detail="Async invocation returned no output location")

    # Parse output location
    parts = output_location.replace("s3://", "").split("/", 1)
    s3_bucket, s3_key = parts[0], parts[1]

    # Create job tracking entry
    job_id = str(uuid4())[:8]
    job = {
        "job_id": job_id,
        "status": "submitted",
        "asset_id": body.asset_id,
        "version": body.version,
        "model_key": model_key,
        "endpoint_name": endpoint_name,
        "input_location": input_location,
        "output_location": output_location,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "params": {
            "steps": body.steps,
            "guidance_scale": body.resolved_guidance(),
            "seed": body.seed,
            "faces": body.resolved_faces(),
            "octree_depth": _octree,
            "texture_backend": body.texture_backend,
        },
        "submitted_at": datetime.utcnow().isoformat(),
    }
    _3d_jobs[job_id] = job
    _persist_3d_job(job)  # survive server restart

    # Dev-box convenience: auto-pin the endpoint warm (non-cumulative). Shares
    # the same helper as 2D async jobs. No-op outside dev mode.
    try:
        from backend.services.async_jobs import _maybe_auto_keep_warm
        _maybe_auto_keep_warm(model_key, endpoint_name)
    except Exception as exc:
        logger.debug("3D auto keep-warm skipped: %s", exc)

    logger.info("3D generation job %s submitted for asset %s (endpoint: %s)",
                job_id, body.asset_id, endpoint_name)

    return {
        "job_id": job_id,
        "status": "submitted",
        "asset_id": body.asset_id,
        "version": body.version,
    }


@router.get("/active/{asset_id}")
async def get_active_3d_job(asset_id: str, version: int = 1):
    """Return the in-progress 3D job for an asset+version, if any.

    Lets the frontend show a 'regeneration in progress' state after a page
    reload (when its in-memory job tracking is gone). Returns the most recent
    non-finalized job, or {active: false}.
    """
    mine = [j for j in _3d_jobs.values()
            if j.get("asset_id") == asset_id and j.get("version", 1) == version]
    candidates = [j for j in mine if j.get("status") not in ("complete", "failed")]
    if not candidates:
        return {"active": False}
    job = sorted(candidates, key=lambda j: j.get("submitted_at", ""), reverse=True)[0]

    # Supersession guard: if a job for this asset+version has already COMPLETED
    # at/after this candidate was submitted, the candidate is stale (e.g. its
    # async output was lost / never delivered) and must NOT keep the frontend
    # spinning. Mark it failed and report the asset as done.
    newest_complete = max(
        (j.get("completed_at", "") for j in mine if j.get("status") == "complete"),
        default="",
    )
    if newest_complete and newest_complete >= job.get("submitted_at", ""):
        job["status"] = "failed"
        job["error"] = "Superseded by a newer completed 3D job (stale async output)."
        _persist_3d_job(job)
        return {"active": False}

    return {"active": True, "job_id": job["job_id"], "status": job["status"]}


@router.get("/status/{job_id}")
async def get_3d_status(job_id: str):
    """Check status of a 3D generation job."""
    job = _3d_jobs.get(job_id)
    if not job:
        raise HTTPException(404, detail=f"3D job '{job_id}' not found.")

    # If already finalized, return cached
    if job["status"] in ("complete", "failed"):
        return job

    # Check S3 for output
    s3 = boto3.client("s3", region_name=_get_region())

    try:
        s3.head_object(Bucket=job["s3_bucket"], Key=job["s3_key"])
    except Exception as e:
        if "404" in str(e) or "NoSuchKey" in str(e) or "Not Found" in str(e):
            # Output not ready yet — check for failure marker
            failure_key = job["s3_key"] + ".failure"
            try:
                failure_resp = s3.get_object(Bucket=job["s3_bucket"], Key=failure_key)
                failure_msg = failure_resp["Body"].read().decode("utf-8", errors="replace")
                job["status"] = "failed"
                job["error"] = failure_msg[:500]
                _persist_3d_job(job)
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "asset_id": job["asset_id"],
                    "version": job["version"],
                    "error": failure_msg[:500],
                }
            except Exception:
                pass
            job["status"] = "generating"
            return {
                "job_id": job_id,
                "status": "generating",
                "asset_id": job["asset_id"],
                "version": job["version"],
            }
        logger.warning("Unexpected S3 error checking 3D job %s: %s", job_id, e)
        job["status"] = "generating"
        return {
            "job_id": job_id,
            "status": "generating",
            "asset_id": job["asset_id"],
            "version": job["version"],
        }

    # Output exists — download and save GLB
    try:
        response = s3.get_object(Bucket=job["s3_bucket"], Key=job["s3_key"])
        output_bytes = response["Body"].read()

        # Parse the output (handler returns JSON with base64 GLB)
        output_data = json.loads(output_bytes.decode("utf-8"))
        glb_b64 = output_data.get("mesh") or output_data.get("glb") or output_data.get("output")
        if not glb_b64:
            job["status"] = "failed"
            job["error"] = "No mesh data in model output"
            _persist_3d_job(job)
            return {
                "job_id": job_id,
                "status": "failed",
                "asset_id": job["asset_id"],
                "version": job["version"],
                "error": "No mesh data in model output",
            }

        glb_bytes = base64.b64decode(glb_b64)
        version = job["version"]
        asset_id = job["asset_id"]

        # Save GLB file — always overwrites the current version (no history)
        asset_dir = store.generated_asset_dir(asset_id)
        asset_dir.mkdir(parents=True, exist_ok=True)
        glb_path = asset_dir / "asset_3d.glb"
        glb_path.write_bytes(glb_bytes)

        # Clean up any old versioned files
        for old in asset_dir.glob("asset_3d_v*.glb"):
            old.unlink(missing_ok=True)

        # Extract mesh stats from output if available
        vertices = output_data.get("vertices", 0)
        faces = output_data.get("faces", 0)

        # Build a human-readable PIPELINE summary (which models/tools produced
        # this asset) for the AssetViewer 3D tab. Geometry model + texture backend
        # come from the job; the instance type + texture-model labels are resolved
        # from the deployed instance. output_data may report richer fields (PBR,
        # rasterizer) when the handler supplies them.
        _TEX_LABELS = {
            "mvpainter": "MVPainter (multi-view PBR bake)",
            "hunyuan": "Hunyuan3D-Paint",
            "mvadapter": "MV-Adapter",
            "trellis2": "TRELLIS.2 (SLAT PBR texturing)",
        }
        _tex_backend = (job.get("params", {}).get("texture_backend")
                        or output_data.get("texture_backend") or "mvpainter")
        _, _cfg = _find_triposg_model(job.get("model_key"))
        _instance = (_cfg or {}).get("deployment", {}).get("instance_type", "")
        pipeline = {
            "geometry_model": "TripoSG",
            "texture_backend": _tex_backend,
            "texture_label": _TEX_LABELS.get(_tex_backend, _tex_backend),
            "instance_type": _instance,
            "has_pbr": bool(output_data.get("has_pbr") or output_data.get("normal_map")),
            "rasterizer": output_data.get("rasterizer", ""),
        }

        # Update asset metadata — single entry, replaced on regenerate
        meta = store.load_generation_metadata(asset_id) or {}
        meta["three_d_versions"] = [{
            "version": version,
            "glb_filename": "asset_3d.glb",
            "glb_url": f"/api/gallery/{asset_id}/3d/{version}",
            "size_bytes": len(glb_bytes),
            "vertices": vertices,
            "faces": faces,
            "params": job["params"],
            "pipeline": pipeline,
            "created_at": datetime.utcnow().isoformat(),
        }]
        meta["has_3d"] = True
        store.save_generation_metadata(asset_id, meta)

        # Update job status
        job["status"] = "complete"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["glb_url"] = f"/api/gallery/{asset_id}/3d/{version}"
        job["size_bytes"] = len(glb_bytes)
        job["vertices"] = vertices
        job["faces"] = faces
        job["pipeline"] = pipeline
        job["created_at"] = meta["three_d_versions"][0]["created_at"]

        logger.info("3D generation complete for asset %s: %d bytes, %d vertices, %d faces",
                    asset_id, len(glb_bytes), vertices, faces)

        # Persist terminal state, then clean up S3 artifacts (output + input)
        _persist_3d_job(job)
        try:
            s3.delete_object(Bucket=job["s3_bucket"], Key=job["s3_key"])
            if job.get("input_location"):
                inp_parts = job["input_location"].replace("s3://", "").split("/", 1)
                if len(inp_parts) == 2:
                    s3.delete_object(Bucket=inp_parts[0], Key=inp_parts[1])
        except Exception:
            pass

        return {
            "job_id": job_id,
            "status": "complete",
            "asset_id": asset_id,
            "version": version,
            "glb_url": f"/api/gallery/{asset_id}/3d/{version}",
            "size_bytes": len(glb_bytes),
            "vertices": vertices,
            "faces": faces,
        }

    except Exception as exc:
        logger.error("Failed to process 3D output for job %s: %s", job_id, exc)
        job["status"] = "failed"
        job["error"] = str(exc)[:500]
        _persist_3d_job(job)
        # Clean up S3 artifacts even on failure
        try:
            s3.delete_object(Bucket=job["s3_bucket"], Key=job["s3_key"])
            if job.get("input_location"):
                inp_parts = job["input_location"].replace("s3://", "").split("/", 1)
                if len(inp_parts) == 2:
                    s3.delete_object(Bucket=inp_parts[0], Key=inp_parts[1])
        except Exception:
            pass
        return {
            "job_id": job_id,
            "status": "failed",
            "asset_id": job["asset_id"],
            "version": job["version"],
            "error": str(exc)[:500],
        }
