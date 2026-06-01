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


def _find_triposg_model() -> tuple[str | None, dict | None]:
    """Find a deployed TripoSG model in the registry."""
    registry = get_registry()
    for section in ("image_models", "post_processing"):
        for key, cfg in registry.get(section, {}).items():
            if cfg.get("catalog_key") != "triposg":
                continue
            if cfg.get("model_source") != "custom_hosted":
                continue
            dep = cfg.get("deployment", {})
            if not dep.get("endpoint_name"):
                continue
            return key, cfg
    return None, None


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
    model_key, cfg = _find_triposg_model()
    if not model_key or not cfg:
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

    # TripoSG can take several minutes
    typical_latency = cfg.get("invoke", {}).get("typical_latency_seconds", 300)
    if typical_latency > 300:
        invoke_kwargs["InvocationTimeoutSeconds"] = min(3600, max(900, typical_latency * 2))

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
        },
        "submitted_at": datetime.utcnow().isoformat(),
    }
    _3d_jobs[job_id] = job

    logger.info("3D generation job %s submitted for asset %s (endpoint: %s)",
                job_id, body.asset_id, endpoint_name)

    return {
        "job_id": job_id,
        "status": "submitted",
        "asset_id": body.asset_id,
        "version": body.version,
    }


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

        logger.info("3D generation complete for asset %s: %d bytes, %d vertices, %d faces",
                    asset_id, len(glb_bytes), vertices, faces)

        # Clean up S3 artifacts (output + input)
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
