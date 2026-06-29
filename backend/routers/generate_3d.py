"""3D model generation router — image-to-3D via TripoSG on SageMaker."""

import base64
import json
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.model_registry import get_registry, _save
from backend.services.sagemaker_deployer import get_deployment_s3_bucket, S3_MODEL_PREFIX
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate/3d", tags=["3d"])

import threading as _threading

# In-memory job tracker for 3D generation
_3d_jobs: dict[str, dict] = {}

# Serializes finalization so the frontend-driven /status route and the
# server-side poller can't both download + save the same job's GLB at once.
_3d_finalize_lock = _threading.Lock()

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


# The two image-to-3D pipelines a user can deploy + their generate-time identity.
# triposg = TripoSG geometry + a chosen texture backend; trellis2_image_to_3d =
# the standalone full TRELLIS.2 pipeline (geometry + texture in one model). Both
# take a single image and produce a GLB, so the 3D-generate flow handles both —
# the difference is metadata (texture_backend choice applies only to TripoSG).
_3D_CATALOG_KEYS = {
    "triposg": "triposg",
    "trellis2_image_to_3d": "trellis2_full",
}


def _list_3d_models() -> list[tuple[str, dict]]:
    """List ALL deployed image-to-3D instances (BOTH pipelines) in the registry.

    A user can deploy TripoSG (possibly several instance types) and/or the full
    TRELLIS.2 pipeline — each a separate registry entry keyed like
    ``<catalog>_<hash>``. Returns every deployed image-to-3D instance, newest-first
    by deployment timestamp so the most recent endpoint leads any chooser.
    """
    registry = get_registry()
    found: list[tuple[str, dict]] = []
    for section in ("image_models", "post_processing"):
        for key, cfg in registry.get(section, {}).items():
            if cfg.get("catalog_key") not in _3D_CATALOG_KEYS:
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


# Back-compat alias: existing callers used _list_triposg_models. It now returns
# BOTH pipelines (the callers that resolve a chosen instance work generically).
_list_triposg_models = _list_3d_models


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
    # 3D sub-versioning: when regenerating, "default" makes the new
    # variant this version's default 3D model; "variant" keeps it alongside the
    # existing default (which stays the served asset_3d.glb). First-ever 3D for a
    # version always becomes the default regardless.
    save_as: str = "default"  # "default" | "variant"

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
    """Check if ANY image-to-3D model (TripoSG or full TRELLIS.2) is deployed."""
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


# ── 3D sub-versioning ──────────────────────────────────────────────────────
# A single 2D image VERSION (v1, v2, …) can have MULTIPLE 3D models — one per
# pipeline / texture-backend / deployment / config the user tried. We store
# these as VARIANTS nested under each 2D version, with one marked default:
#
#   meta["three_d"] = {
#     "v1": {
#       "default_variant": "<variant_id>",
#       "variants": [ { variant_id, glb_filename, pipeline, params,
#                       model_key, job_id, instance_label, created_at, … } ]
#     }, …
#   }
#
# Files on disk (per asset dir):
#   asset_3d_v{N}.glb                     ← the DEFAULT variant for version N
#                                           (also asset_3d.glb for v1 — kept for
#                                           the legacy gallery route + thumbnails)
#   asset_3d_v{N}__{variant_id}.glb       ← every variant, addressable directly
#
# Backward compatibility: legacy assets only have a flat meta["three_d_versions"]
# list (one entry per version, no variants). _migrate_legacy_3d() lifts those
# into the nested shape on first access, and we ALSO keep writing a flattened
# three_d_versions (the default variant of each version) so any old reader works.


def _deploy_hash(model_key: str) -> str:
    """Short deployment discriminator from a deployed model_key.

    Deployed instance keys carry a hash suffix (e.g. ``trellis2_image_to_3d_afe4``
    → ``afe4``). Two deployments of the same model differ only by this suffix, so
    it disambiguates same-model multi-deploy variants. Falls back to the whole
    key when there's no suffix.
    """
    if not model_key:
        return "default"
    tail = model_key.rsplit("_", 1)[-1]
    # A real hash suffix is short + alphanumeric; otherwise use a trimmed key.
    if tail and len(tail) <= 6 and tail.isalnum():
        return tail
    return model_key[-8:]


def _pipeline_slug(pipeline_type: str, tex_backend: str = "") -> str:
    """Filesystem-safe pipeline identity for a variant id / filename.

    trellis2_full → ``trellis2``; triposg → ``triposg-<texbackend>`` so a TripoSG
    model textured by Hunyuan vs MV-Adapter vs TRELLIS.2 are distinct variants.
    """
    if pipeline_type == "trellis2_full":
        return "trellis2"
    tb = (tex_backend or "").strip().lower() or "default"
    return f"triposg-{tb}"


def _variant_id(pipeline_type: str, tex_backend: str, model_key: str) -> str:
    """Stable variant id = pipeline + deployment. Re-running the SAME pipeline on
    the SAME deployment replaces that variant; a different pipeline/backend/
    deployment yields a new one. Safe for use in a filename."""
    return f"{_pipeline_slug(pipeline_type, tex_backend)}__{_deploy_hash(model_key)}"


def _variant_instance_label(pipeline_type: str, cfg: dict) -> str:
    """Disambiguating label for a variant, shown in the AssetViewer switcher.

    Mirrors the 2D Image Studio model picker: pipeline name + DEPLOYMENT TIME
    (so two deployments of the same model are told apart by when they were
    deployed), e.g. "TRELLIS.2 Full (25Jun 14:18)" / "TripoSG (02Jun 12:14)".
    """
    base = "TRELLIS.2 Full" if pipeline_type == "trellis2_full" else "TripoSG"
    dep = (cfg or {}).get("deployment", {})
    created = dep.get("created_at", "")
    stamp = ""
    if created:
        try:
            stamp = datetime.fromisoformat(created).strftime("%d%b %H:%M")
        except Exception:
            stamp = created[:16]
    return f"{base} ({stamp})" if stamp else base


def _migrate_legacy_3d(meta: dict) -> dict:
    """Ensure meta has the nested three_d structure, lifting any legacy flat
    three_d_versions list into it. Idempotent. Returns the nested dict
    (meta["three_d"]). Does NOT save — caller persists if needed."""
    nested = meta.get("three_d")
    if isinstance(nested, dict) and nested:
        return nested
    nested = {}
    for entry in (meta.get("three_d_versions") or []):
        ver = entry.get("version", 1)
        pl = entry.get("pipeline", {}) or {}
        vid = _variant_id(pl.get("pipeline_type", "triposg"),
                          pl.get("texture_backend", ""),
                          entry.get("model_key", ""))
        variant = dict(entry)
        variant["variant_id"] = vid
        # Legacy files are named asset_3d.glb / asset_3d_v{N}.glb (no variant
        # suffix) — keep that filename so the existing file still resolves.
        variant.setdefault("glb_filename",
                            "asset_3d.glb" if ver == 1 else f"asset_3d_v{ver}.glb")
        nested[f"v{ver}"] = {"default_variant": vid, "variants": [variant]}
    meta["three_d"] = nested
    return nested


def _ensure_variant_files(asset_dir, asset_id: str, vbucket: dict, version: int) -> None:
    """Guarantee every variant owns a PRIVATE GLB file, distinct from the shared
    canonical default files (asset_3d.glb / asset_3d_v{N}.glb).

    Critical invariant (a data-loss bug otherwise): a migrated LEGACY variant
    points its glb_filename at the canonical name (asset_3d.glb), which is ALSO
    the file the current default is materialized into. If a *different* variant
    later becomes default, the canonical write clobbers the legacy variant's only
    copy. Fix: before any canonical write, copy each variant's bytes to its own
    `asset_3d_v{N}__{vid}.glb` and repoint glb_filename/glb_url there. Idempotent.
    """
    import shutil
    for v in vbucket.get("variants", []):
        vid = v.get("variant_id")
        if not vid:
            continue
        private = f"asset_3d_v{version}__{vid}.glb"
        priv_path = asset_dir / private
        if v.get("glb_filename") == private and priv_path.exists():
            continue  # already private + present
        if not priv_path.exists():
            # Copy from the variant's current (legacy/canonical) file if present.
            cur = v.get("glb_filename")
            src = asset_dir / cur if cur else None
            if not (src and src.exists()):
                # No source bytes to preserve — leave as-is (the serve route's
                # canonical fallback still works for the default).
                continue
            shutil.copy2(src, priv_path)
        v["glb_filename"] = private
        v["glb_url"] = f"/api/gallery/{asset_id}/3d/{version}?variant={vid}"


def _flatten_three_d_versions(nested: dict) -> list:
    """Build the legacy flat three_d_versions list (the DEFAULT variant of each
    version) from the nested structure, so old readers keep working."""
    out = []
    for vkey, vdata in nested.items():
        variants = vdata.get("variants", [])
        if not variants:
            continue
        default_id = vdata.get("default_variant")
        chosen = next((v for v in variants if v.get("variant_id") == default_id), variants[-1])
        out.append(chosen)
    return out


def _pipeline_info(key: str, cfg: dict) -> dict:
    """Resolve a deployed 3D instance's pipeline identity, license summary, and
    the user's deploy-time license acceptance — for the AssetViewer chooser.

    pipeline_type: 'triposg' (TripoSG geometry + a chosen texture backend) or
    'trellis2_full' (standalone full TRELLIS.2). The license summary + acceptance
    let the generate-time UI show "you accepted <license> on <date>" (NO new
    consent prompt — the authoritative attestation is at deploy time).
    """
    catalog_key = cfg.get("catalog_key", "")
    pipeline_type = _3D_CATALOG_KEYS.get(catalog_key, "triposg")
    dep = cfg.get("deployment", {})
    registry = get_registry()
    acceptances = registry.get("license_acceptances", {}) or {}

    license_name = ""
    license_url = ""
    commercial = None
    accepted = None  # {license_name, accepted_at} or None
    try:
        from backend.services.custom_models import get_catalog_model
        cat = get_catalog_model(catalog_key) or {}
        if pipeline_type == "trellis2_full":
            # Full pipeline: the model's own license_agreement is the contract.
            la = cat.get("license_agreement", {}) or {}
            license_name = la.get("license_name", cat.get("license", ""))
            license_url = la.get("license_url", "")
            commercial = True  # MIT + commercial DINOv3 (attribution required)
            accepted = acceptances.get(catalog_key) or acceptances.get(key)
        else:
            # TripoSG: the active TEXTURE BACKEND carries the license that matters.
            tex_backend = dep.get("texture_backend") or ""
            tb = ((cat.get("texture_backends", {}).get("options", {}) or {}).get(tex_backend, {}) or {})
            lic = tb.get("license", {}) or {}
            license_name = lic.get("name", "")
            license_url = lic.get("url", "")
            commercial = lic.get("commercial")
            # Texture-backend acceptance was recorded under "<model_key>:<backend>".
            accepted = (acceptances.get(f"{key}:{tex_backend}")
                        or acceptances.get(f"{catalog_key}:{tex_backend}")
                        or acceptances.get(catalog_key))
    except Exception:
        pass

    return {
        "pipeline_type": pipeline_type,
        "license_name": license_name,
        "license_url": license_url,
        "commercial": commercial,
        "license_accepted": bool(accepted),
        "license_accepted_at": (accepted or {}).get("accepted_at", ""),
    }


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
        # Pipeline identity + license summary + deploy-time acceptance (drives the
        # AssetViewer chooser + the "accepted on <date>, still valid" line).
        pinfo = _pipeline_info(key, cfg)
        # Est. cost per job = hourly rate × (latency / 3600), when both known.
        est_cost = None
        try:
            if cost_per_hr and latency_s:
                est_cost = round(float(cost_per_hr) * (float(latency_s) / 3600.0), 2)
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
            "est_cost_usd": est_cost,
            **pinfo,
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
    """Submit an image-to-3D job to a deployed 3D pipeline (TripoSG+texturer or
    the standalone full TRELLIS.2 pipeline — whichever instance is selected)."""
    # Honor the chooser selection if provided; else use the newest instance.
    model_key, cfg = _find_triposg_model(body.model_key)
    if not model_key or not cfg:
        if body.model_key:
            raise HTTPException(400, detail=f"Selected 3D model instance '{body.model_key}' is not a deployed image-to-3D endpoint.")
        raise HTTPException(400, detail="No image-to-3D model is deployed. Deploy TripoSG or TRELLIS.2 (Full) from Custom Models first.")

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
        # Whether this variant should become the version's default 3D
        # model on completion ("default") or be kept as a side variant ("variant").
        "set_default": body.save_as != "variant",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
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


@router.get("/active-all/{asset_id}")
async def get_active_3d_jobs(asset_id: str, version: int = 1):
    """Return ALL in-progress 3D jobs for an asset+version (parallel jobs).

    Unlike /active (single most-recent job), this lists every non-finalized job
    so the frontend can run + track multiple async generations of the same image
    in parallel (e.g. TripoSG and TRELLIS.2 at once). Each carries a short
    pipeline label for the in-progress strip. No supersession collapse here —
    each job is independent and finalizes into its own variant.
    """
    out = []
    for j in _3d_jobs.values():
        if j.get("asset_id") != asset_id or j.get("version", 1) != version:
            continue
        if j.get("status") in ("complete", "failed"):
            continue
        # Resolve a human label (pipeline + deploy time) like the variant chooser.
        mk = j.get("model_key", "")
        _, cfg = _find_triposg_model(mk)
        ptype = _3D_CATALOG_KEYS.get((cfg or {}).get("catalog_key", ""), "triposg") if cfg else "triposg"
        label = _variant_instance_label(ptype, cfg or {}) if cfg else (mk or "3D job")
        out.append({
            "job_id": j["job_id"],
            "status": j.get("status", "submitted"),
            "model_key": mk,
            "pipeline_type": ptype,
            "label": label,
            "submitted_at": j.get("submitted_at", ""),
        })
    out.sort(key=lambda x: x.get("submitted_at", ""))
    return {"asset_id": asset_id, "version": version, "jobs": out}


def _version_image_path(asset_id: str, version: int):
    """Resolve the PNG path for a 2D version (v1 = asset.png)."""
    fn = "asset.png" if (version or 1) == 1 else f"asset_v{version}.png"
    return store.get_generated_file_path(asset_id, fn)


class AnalyzeSourceRequest(BaseModel):
    asset_id: str
    version: int = 1


@router.post("/analyze-source")
async def analyze_3d_source(body: AnalyzeSourceRequest):
    """Vision-analyze a 2D source image before image-to-3D.

    Detects whether the subject is fully visible or CROPPED by the frame (which
    would yield an incomplete 3D model — e.g. a character cropped at the waist
    becomes legless). Returns a structured verdict the frontend uses to OFFER an
    outpaint completion (non-blocking). Conservative by design — defaults to
    "complete" on any uncertainty/error so it never blocks a good image.
    """
    img_path = _version_image_path(body.asset_id, body.version)
    if img_path is None:
        raise HTTPException(404, detail=f"Image not found for asset '{body.asset_id}' v{body.version}.")

    meta = store.load_generation_metadata(body.asset_id) or {}
    asset_type = (meta.get("asset_type") or "character").replace("_", " ")

    try:
        from backend.services.bedrock_client import invoke_llm
        from backend.services.prompt_templates import get_template, get_system_prompt
        prompt = get_template("three_d_source_analysis").format(asset_type=asset_type)
        system = get_system_prompt("three_d_source_analysis")
        raw = invoke_llm(prompt, system=system, complexity="complex",
                         images=[img_path.read_bytes()], max_tokens=400, temperature=0.0)
        # Strip any markdown fence and parse the JSON object.
        txt = (raw or "").strip()
        if "```" in txt:
            txt = txt.split("```")[1].lstrip("json").strip() if txt.count("```") >= 2 else txt
        start, end = txt.find("{"), txt.rfind("}")
        data = json.loads(txt[start:end + 1]) if start >= 0 and end > start else {}
    except Exception as e:
        logger.info("3D source analysis unavailable for %s v%s (%s) — defaulting to complete",
                    body.asset_id, body.version, e)
        return {"complete": True, "analyzed": False}

    complete = bool(data.get("complete", True))
    outp = data.get("suggest_outpaint", {}) or {}
    # Sanity-clamp outpaint pixels (the model returns 0-512 per edge).
    def _clamp(v):
        try: return max(0, min(512, int(v)))
        except (TypeError, ValueError): return 0
    suggest = {d: _clamp(outp.get(d, 0)) for d in ("down", "up", "left", "right")}
    any_outpaint = any(suggest.values())
    return {
        "analyzed": True,
        # Only call it incomplete if the model said so AND gave a usable outpaint
        # direction — otherwise there's nothing actionable, so treat as complete.
        "complete": complete or not any_outpaint,
        "subject": data.get("subject", ""),
        "crop_edges": data.get("crop_edges", []) or [],
        "missing": data.get("missing", []) or [],
        "suggest_outpaint": suggest,
        # Suggested completion prompt for the outpaint (what to draw in the new
        # area). The user can edit this before running; falls back to empty (the
        # outpaint model continues the subject on its own) if not provided.
        "outpaint_prompt": (data.get("outpaint_prompt", "") or "").strip()[:300],
        "reason": data.get("reason", ""),
    }


@router.get("/variants/{asset_id}/{version}")
async def list_3d_variants(asset_id: str, version: int):
    """List the 3D variants for an asset+version (3D sub-versioning).

    Returns the variants (each with its pipeline, deployment label, job id and
    stats) plus which one is the default. Legacy flat metadata is migrated on
    read. Used by the AssetViewer variant switcher.
    """
    meta = store.load_generation_metadata(asset_id) or {}
    nested = _migrate_legacy_3d(meta)
    vbucket = nested.get(f"v{version}") or {}
    return {
        "asset_id": asset_id,
        "version": version,
        "default_variant": vbucket.get("default_variant"),
        "variants": vbucket.get("variants", []),
    }


class SetDefaultVariantRequest(BaseModel):
    asset_id: str
    version: int = 1
    variant_id: str


@router.post("/variants/set-default")
async def set_default_3d_variant(body: SetDefaultVariantRequest):
    """Make a variant the version's default 3D model.

    Repoints default_variant and re-materializes the canonical files
    (asset_3d_v{N}.glb, plus asset_3d.glb for v1) from the chosen variant so the
    gallery/thumbnail/legacy route serve it.
    """
    meta = store.load_generation_metadata(body.asset_id) or {}
    nested = _migrate_legacy_3d(meta)
    vbucket = nested.get(f"v{body.version}")
    if not vbucket:
        raise HTTPException(404, detail=f"No 3D models for asset '{body.asset_id}' version {body.version}.")
    chosen = next((v for v in vbucket.get("variants", []) if v.get("variant_id") == body.variant_id), None)
    if not chosen:
        raise HTTPException(404, detail=f"Variant '{body.variant_id}' not found.")

    asset_dir = store.generated_asset_dir(body.asset_id)
    # Ensure every variant has a PRIVATE file first, so reading the chosen
    # variant's bytes can never read from (or be clobbered by) the canonical file.
    _ensure_variant_files(asset_dir, body.asset_id, vbucket, body.version)
    src = asset_dir / chosen["glb_filename"]
    if not src.exists():
        raise HTTPException(404, detail="Variant GLB file is missing on disk.")
    data = src.read_bytes()
    (asset_dir / f"asset_3d_v{body.version}.glb").write_bytes(data)
    if body.version == 1:
        (asset_dir / "asset_3d.glb").write_bytes(data)

    vbucket["default_variant"] = body.variant_id
    meta["three_d_versions"] = _flatten_three_d_versions(nested)
    store.save_generation_metadata(body.asset_id, meta)
    return {"ok": True, "default_variant": body.variant_id}


def _check_3d_job(job: dict, s3=None) -> dict:
    """Poll S3 for a 3D job's async output and finalize it if ready.

    This is the single source of truth for turning a `submitted`/`generating`
    job into a terminal `complete`/`failed` state: it downloads the GLB, saves
    it to the asset dir, writes the rich `three_d_versions` metadata, and cleans
    up S3 artifacts. It is intentionally side-effecting and idempotent-ish —
    once a job is terminal it returns the cached job without touching S3.

    Both callers share it so behavior is identical regardless of who drives it:
      • the frontend-driven GET /status/{job_id} route, and
      • the server-side background poller (_poll_loop), which finalizes jobs
        even when no browser is watching (e.g. the user closed the tab during a
        long SageMaker cold start).

    Returns a status dict (job_id/status/asset_id/version[/glb_url/error/...]).
    """
    job_id = job["job_id"]

    # Fast path: already finalized (avoids taking the lock for the common
    # "poll a done job" case).
    if job["status"] in ("complete", "failed"):
        return job

    if s3 is None:
        s3 = boto3.client("s3", region_name=_get_region())

    # Serialize finalization across the /status route and the background poller.
    # Re-check status after acquiring — the other caller may have just finished.
    with _3d_finalize_lock:
        if job["status"] in ("complete", "failed"):
            return job
        return _finalize_3d_job(job, s3)


def _finalize_3d_job(job: dict, s3) -> dict:
    """S3 poll + finalize body for one 3D job. Caller holds _3d_finalize_lock."""
    job_id = job["job_id"]
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

        asset_dir = store.generated_asset_dir(asset_id)
        asset_dir.mkdir(parents=True, exist_ok=True)

        # Extract mesh stats from output if available
        vertices = output_data.get("vertices", 0)
        faces = output_data.get("faces", 0)

        # Build a human-readable PIPELINE summary (which models/tools produced
        # this asset) for the AssetViewer 3D tab. Geometry model + texture backend
        # come from the job; the instance type + texture-model labels are resolved
        # from the deployed instance. output_data may report richer fields (PBR,
        # rasterizer) when the handler supplies them.
        _TEX_LABELS = {
            "hunyuan": "Hunyuan3D-Paint",
            "mvadapter": "MV-Adapter",
            "trellis2": "TRELLIS.2 (SLAT PBR texturing)",
        }
        _, _cfg = _find_triposg_model(job.get("model_key"))
        _instance = (_cfg or {}).get("deployment", {}).get("instance_type", "")
        _ptype = _3D_CATALOG_KEYS.get((_cfg or {}).get("catalog_key", ""), "triposg")
        _pinfo = _pipeline_info(job.get("model_key"), _cfg) if _cfg else {}
        if _ptype == "trellis2_full":
            # Standalone full TRELLIS.2 — geometry AND texture from one model; no
            # separate texture-backend choice.
            pipeline = {
                "geometry_model": "TRELLIS.2 (full pipeline)",
                "texture_backend": "trellis2_full",
                "texture_label": "TRELLIS.2 (integrated SLAT PBR)",
                "instance_type": _instance,
                "has_pbr": bool(output_data.get("has_pbr", True)),
                "rasterizer": output_data.get("rasterizer", ""),
            }
        else:
            _tex_backend = (job.get("params", {}).get("texture_backend")
                            or output_data.get("texture_backend") or "trellis2")
            pipeline = {
                "geometry_model": "TripoSG",
                "texture_backend": _tex_backend,
                "texture_label": _TEX_LABELS.get(_tex_backend, _tex_backend),
                "instance_type": _instance,
                "has_pbr": bool(output_data.get("has_pbr") or output_data.get("normal_map")),
                "rasterizer": output_data.get("rasterizer", ""),
            }
        # Record the user's pipeline choice + the license they accepted at deploy
        # (consent provenance) into the persisted metadata.
        pipeline["pipeline_type"] = _ptype
        pipeline["license_name"] = _pinfo.get("license_name", "")
        pipeline["license_accepted_at"] = _pinfo.get("license_accepted_at", "")
        pipeline["commercial"] = _pinfo.get("commercial")

        # ── Build the VARIANT record ──────────────────────────────────────
        # A 2D version can hold multiple 3D variants (different pipeline /
        # texture backend / deployment / config). The variant id is stable per
        # (pipeline, deployment): re-running the same pipeline on the same
        # endpoint REPLACES its variant; anything else is a new variant.
        vid = _variant_id(_ptype, pipeline.get("texture_backend", ""), job.get("model_key", ""))
        created_at = datetime.now(timezone.utc).isoformat()
        # Per-variant GLB file (addressable directly) + the version's default
        # file (asset_3d_v{N}.glb, plus asset_3d.glb for v1 — the legacy route).
        variant_filename = f"asset_3d_v{version}__{vid}.glb"
        (asset_dir / variant_filename).write_bytes(glb_bytes)

        variant = {
            "variant_id": vid,
            "version": version,
            "glb_filename": variant_filename,
            "glb_url": f"/api/gallery/{asset_id}/3d/{version}?variant={vid}",
            "size_bytes": len(glb_bytes),
            "vertices": vertices,
            "faces": faces,
            "params": job["params"],
            "pipeline": pipeline,
            "instance_label": _variant_instance_label(_ptype, _cfg or {}),
            # Exact provenance: which deployed endpoint produced this, and the
            # job that ran it — surfaced in the AssetViewer Metadata tab.
            "model_key": job.get("model_key", ""),
            "job_id": job_id,
            # tz-AWARE UTC (…+00:00). A naive utcnow().isoformat() has no zone
            # suffix → JS `new Date()` parses it as LOCAL time → wrong displayed
            # time (off by the local UTC offset). The suffix lets JS convert right.
            "created_at": created_at,
        }

        meta = store.load_generation_metadata(asset_id) or {}
        nested = _migrate_legacy_3d(meta)
        vkey = f"v{version}"
        vbucket = nested.setdefault(vkey, {"default_variant": None, "variants": []})
        # Replace any existing variant with the same id (same pipeline+deploy),
        # else append. Clean up the OLD variant's GLB file if its name changed.
        existing = next((v for v in vbucket["variants"] if v.get("variant_id") == vid), None)
        if existing:
            old_fn = existing.get("glb_filename")
            if old_fn and old_fn != variant_filename:
                (asset_dir / old_fn).unlink(missing_ok=True)
            vbucket["variants"] = [v if v.get("variant_id") != vid else variant
                                   for v in vbucket["variants"]]
        else:
            vbucket["variants"].append(variant)

        # Default-variant policy: a brand-new generation (no prior default) OR a
        # regen the user asked to "replace" becomes the default. A regen saved as
        # a NEW variant leaves the existing default untouched.
        make_default = (not vbucket.get("default_variant")) or bool(job.get("set_default", True))
        if make_default:
            vbucket["default_variant"] = vid

        # Give EVERY variant a private GLB file before any canonical write. A
        # migrated legacy variant points at asset_3d.glb (the same file we
        # materialize the default into) — without this, switching the default to
        # a different variant would overwrite the legacy variant's only copy.
        _ensure_variant_files(asset_dir, asset_id, vbucket, version)

        # Materialize the DEFAULT variant as the version's canonical file(s) so
        # the legacy gallery route (asset_3d.glb / asset_3d_v{N}.glb) serves it.
        # Reads from the default variant's now-PRIVATE file (never the canonical
        # file itself), so the copy is always from a stable, distinct source.
        default_id = vbucket["default_variant"]
        default_variant = next((v for v in vbucket["variants"] if v.get("variant_id") == default_id), variant)
        default_bytes = glb_bytes if default_variant is variant else \
            (asset_dir / default_variant["glb_filename"]).read_bytes()
        (asset_dir / f"asset_3d_v{version}.glb").write_bytes(default_bytes)
        if version == 1:
            (asset_dir / "asset_3d.glb").write_bytes(default_bytes)

        # Keep the legacy flat list in sync (default variant per version) so any
        # un-migrated reader still works.
        meta["three_d_versions"] = _flatten_three_d_versions(nested)
        meta["has_3d"] = True
        store.save_generation_metadata(asset_id, meta)

        # Update job status
        job["status"] = "complete"
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        job["glb_url"] = variant["glb_url"]
        job["variant_id"] = vid
        job["size_bytes"] = len(glb_bytes)
        job["vertices"] = vertices
        job["faces"] = faces
        job["pipeline"] = pipeline
        job["created_at"] = created_at

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


@router.get("/status/{job_id}")
async def get_3d_status(job_id: str):
    """Check status of a 3D generation job.

    Thin wrapper over _check_3d_job(): the background poller (_poll_loop) may
    have already finalized this job, in which case the cached terminal state is
    returned immediately. Otherwise this poll attempt drives the finalize.
    """
    job = _3d_jobs.get(job_id)
    if not job:
        raise HTTPException(404, detail=f"3D job '{job_id}' not found.")
    return _check_3d_job(job)


# ── Server-side background poller ──────────────────────────────────────────
# 3D async jobs are submitted to SageMaker and their GLB lands in S3 minutes
# later (often after a multi-minute cold start when the endpoint scaled to
# zero). Finalization (download GLB → save → write metadata) used to happen
# ONLY when the browser polled /status — so if the user closed the tab during a
# long cold start, a finished job's output was never saved. This poller closes
# that gap: it finalizes generating jobs regardless of whether any UI is
# watching, mirroring the 2D async-job poller (services/async_jobs.py).
_3d_poller_thread: "_threading.Thread | None" = None
_3d_poller_stop = _threading.Event()


def _3d_poll_loop():
    """Background loop: finalize in-progress 3D jobs by polling S3."""
    import time as _time
    while not _3d_poller_stop.is_set():
        try:
            pending = [j for j in list(_3d_jobs.values())
                       if j.get("status") not in ("complete", "failed")]
            if pending:
                s3 = boto3.client("s3", region_name=_get_region())
                for job in pending:
                    if _3d_poller_stop.is_set():
                        break
                    try:
                        _check_3d_job(job, s3)
                    except Exception as e:
                        logger.warning("3D job poll error (%s): %s",
                                       job.get("job_id"), e)
        except Exception as e:
            logger.debug("3D poll loop iteration error: %s", e)
        # 15s cadence: brisk enough that a finished GLB is saved promptly, but
        # light on S3 HEAD calls when a long cold start is in progress.
        _3d_poller_stop.wait(timeout=15)
    logger.debug("3D job poller stopped")


def start_3d_poller() -> None:
    """Start the background 3D-job poller (called from app startup).

    Idempotent — a second call while the thread is alive is a no-op. Must be
    invoked AFTER load_persisted_3d_jobs() so restored in-progress jobs are
    picked up immediately on boot.
    """
    global _3d_poller_thread
    if _3d_poller_thread and _3d_poller_thread.is_alive():
        return
    _3d_poller_stop.clear()
    _3d_poller_thread = _threading.Thread(
        target=_3d_poll_loop, daemon=True, name="three-d-job-poller")
    _3d_poller_thread.start()
    logger.info("3D job poller started")


def stop_3d_poller() -> None:
    """Stop the background 3D-job poller (called on shutdown)."""
    _3d_poller_stop.set()
