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

from backend.services.model_registry import get_registry, registry_transaction
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


def load_persisted_3d_jobs() -> int:
    """Restore 3D jobs from S3 on startup (called from app startup).

    Loads in-progress jobs into _3d_jobs so they survive a server restart.
    Prunes stale records: terminal (complete/failed) jobs and stuck jobs
    (submitted/generating with no update for >2h) are deleted from S3 so
    they don't accumulate — complements the 1-day S3 lifecycle rule.

    Returns the number of ACTIVE (still in-progress) jobs restored, so the caller
    can start the poller only when there's work — no idle thread otherwise.
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
        return loaded
    except Exception as e:
        logger.debug("Failed to load persisted 3D jobs: %s", e)
        return 0


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
            # Fall back to the catalog's DEFAULT backend when the deployment didn't
            # persist an explicit choice (older TripoSG deploys stored no
            # texture_backend, but generation still uses the default) — otherwise the
            # license summary comes back empty and the panel silently hides.
            tex_cfg = cat.get("texture_backends", {}) or {}
            tex_backend = dep.get("texture_backend") or tex_cfg.get("default") or ""
            tb = ((tex_cfg.get("options", {}) or {}).get(tex_backend, {}) or {})
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
            tex_cfg = cat.get("texture_backends", {}) or {}
            tb_opts = tex_cfg.get("options", {}) or {}
            # Same default fallback as the license summary: an unset texture_backend
            # means the catalog default is used at generation time.
            if not tex_backend:
                tex_backend = tex_cfg.get("default") or ""
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
    with registry_transaction() as registry:
        registry["three_d_defaults"] = {
            "steps": body.steps,
            "guidance_scale": body.guidance_scale,
            "faces": body.faces,
            "octree_depth": body.octree_depth,
            "quality": body.quality,
        }
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

    # 3D generates from the version's CUTOUT (background-removed version image) —
    # the SAME artefact the Export tab shows, so the "SOURCE FOR 3D" preview and
    # the actual 3D input always match. Improvements are committed as their OWN 2D
    # version (commit-time versioning), so we never read a persistent __source
    # sidecar here — that's transient, scoped to an active improve-dialog session.
    # A bg_free version is its own cutout. (The handler also strips BG server-side
    # as a backstop, so a raw version still works.)
    image_path = _ensure_cutout(body.asset_id, body.version)
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

    # Upload payload to S3 for async invocation. Preflight the prerequisite with
    # the shared check so 3D fails with the SAME clear, actionable message as the
    # 2D custom path (presence-only — don't head_bucket on this hot path).
    from backend.services.sagemaker_deployer import check_deployment_bucket
    _bcheck = check_deployment_bucket(require_access=False)
    if not _bcheck["ok"]:
        raise HTTPException(400, detail=_bcheck["message"])
    bucket = get_deployment_s3_bucket()

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
        # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
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
    # Ensure the background poller is running to finalize this job even if the
    # browser closes. The poller self-stops when idle, so submits are the on-
    # demand trigger (mirrors the 2D _ensure_poller on submit). Idempotent.
    start_3d_poller()

    # Warm the FBX exporter (headless Blender) in the background now that a 3D model
    # is being generated, so it's ready before the user clicks "Download FBX".
    # Reuses a system Blender if present (no download); idempotent + never blocks.
    try:
        from backend.services import mesh_export
        mesh_export.preprovision_async()
    except Exception as exc:
        logger.debug("Blender pre-provision skipped: %s", exc)

    # Dev-box convenience: auto-pin the endpoint warm (non-cumulative). Shares
    # the same helper as 2D async jobs. No-op outside dev mode.
    try:
        from backend.services.async_jobs import _maybe_auto_keep_warm
        _maybe_auto_keep_warm(model_key, endpoint_name)
    except Exception as exc:
        logger.debug("3D auto keep-warm skipped: %s", exc)

    logger.info("3D generation job %s submitted for asset %s (endpoint: %s)",
                job_id, body.asset_id, endpoint_name)

    # Telemetry: action event (cost=0; GPU compute cost is reported at completion
    # by _track_3d_completion) + adoption milestone. Non-fatal.
    try:
        from backend.services.telemetry import track_3d_generation, track_first_generation
        _, _cfg = _find_triposg_model(model_key)
        _pt = _3D_CATALOG_KEYS.get((_cfg or {}).get("catalog_key", ""), "triposg")
        _inst = (_cfg or {}).get("deployment", {}).get("instance_type", "")
        _atype = (store.load_generation_metadata(body.asset_id) or {}).get("asset_type", "")
        track_3d_generation(model=model_key, pipeline=_pt, asset_type=_atype,
                            quality=body.quality or "", instance=_inst)
        track_first_generation(model=model_key, asset_type=_atype, studio="three_d")
    except Exception as exc:
        logger.debug("3D generation telemetry skipped: %s", exc)

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


def _version_image_path(asset_id: str, version: int, meta: dict = None):
    """Resolve the PNG path for a 2D version, ADAPTING to the existing 2D
    versioning/file-naming convention (do not change that convention):

      • the CURRENT (latest) version is always `asset.png`
      • OLDER versions are archived as `asset_v{N}.png`

    So the file for version N is `asset.png` when N is the current version, else
    `asset_v{N}.png`. We resolve current_version from metadata; if the expected
    file is missing we fall back across both names so a single-version asset (only
    `asset.png`) or any edge case still resolves rather than 404-ing.
    """
    if meta is None:
        meta = store.load_generation_metadata(asset_id) or {}
    current = meta.get("current_version") or (len(meta.get("versions", [])) or 1)
    candidates = []
    if version and version == current:
        candidates.append("asset.png")
        candidates.append(f"asset_v{version}.png")
    else:
        candidates.append(f"asset_v{version}.png")
        candidates.append("asset.png")
    for fn in candidates:
        p = store.get_generated_file_path(asset_id, fn)
        if p is not None:
            return p
    return None


def _alpha_edge_crop(img_bytes: bytes, touch_frac: float = 0.04, margin_px: int = 2):
    """Deterministic crop detection from a background-removed (RGBA) cutout.

    Once the background is gone, the subject's silhouette is the alpha channel.
    If that silhouette RUNS INTO a frame edge (a meaningful fraction of the edge
    row/column is opaque with ~no transparent margin), the subject is cut off
    there — provable, no LLM guessing. This is far more reliable than a vision
    model on a plain cutout (the empty void below e.g. a pair of boots often
    fools the LLM into "complete"). Returns None for non-transparent images (no
    alpha signal to trust) or on any error, so callers fall back to the LLM.

    Returns { "crop_edges": [...], "suggest_outpaint": {down,up,left,right} } or None.
    """
    try:
        import io
        import numpy as np
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        alpha = np.asarray(im.split()[-1])
        H, W = alpha.shape
        # No real transparency (fully opaque) → not a cutout; no signal to use.
        if (alpha > 16).mean() > 0.98:
            return None
        opaque = alpha > 16
        edges = {
            "up":    opaque[0, :].mean(),
            "down":  opaque[-1, :].mean(),
            "left":  opaque[:, 0].mean(),
            "right": opaque[:, -1].mean(),
        }
        # A transparent margin (in px) between the silhouette and each edge; if the
        # edge itself carries enough opaque pixels, the margin is ~0 → cropped there.
        cols_any = opaque.any(axis=0)
        rows_any = opaque.any(axis=1)
        crop_edges, suggest = [], {"down": 0, "up": 0, "left": 0, "right": 0}
        # Extension size scales with how much the subject fills the frame (a bigger
        # subject needs a bigger reveal); clamp to the model's 0-512 range.
        for edge, frac in edges.items():
            if frac >= touch_frac:
                crop_edges.append(edge)
        # Map edges → outpaint directions with a sensible default reveal (256px),
        # larger (384px) when the subject dominates that edge (>25% opaque).
        for edge in crop_edges:
            suggest[edge] = 384 if edges[edge] > 0.25 else 256
        if not crop_edges:
            return None
        return {"crop_edges": crop_edges, "suggest_outpaint": suggest}
    except Exception:
        return None


def _fit_image_for_vision(img_bytes: bytes, max_bytes: int = 3_600_000, max_dim: int = 2048) -> bytes:
    """Downscale/re-encode an image so it fits under Bedrock's vision limit.

    Bedrock Converse rejects images over 5 MB — but that limit is measured on the
    BASE64-encoded payload, which is ~1.34× the raw bytes. So a 4.3 MB PNG becomes
    ~5.7 MB base64 and still fails. Hence max_bytes defaults to ~3.6 MB raw
    (×1.34 ≈ 4.8 MB base64, safely under 5 MB). Background-removed cutouts are
    large lossless RGBA PNGs (a 1536×1792 cutout is 4–6 MB raw), so a raw send
    fails with a ValidationException and the whole analysis silently defaults to
    "complete". This shrinks the longest side to `max_dim` and, if still too big,
    steps the dimensions down until the PNG is under `max_bytes` — preserving
    transparency (kept as PNG) so the alpha silhouette the model reasons about is
    intact. Returns the original bytes unchanged if already small enough or on any
    error (caller still guards)."""
    if len(img_bytes) <= max_bytes:
        return img_bytes
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes))
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        im = im.convert("RGBA" if has_alpha else "RGB")
        # Cap the longest side, then keep halving until under the byte budget.
        w, h = im.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        for _ in range(6):
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes:
                return data
            im = im.resize((max(1, im.width * 3 // 4), max(1, im.height * 3 // 4)), Image.LANCZOS)
        return data  # best effort after the loop
    except Exception:
        return img_bytes


def _version_is_bg_free(asset_id: str, version: int, meta: dict = None) -> bool:
    """Whether a 2D version is already a background-free cutout (per its edit
    provenance), so we can serve it directly without another removal."""
    if meta is None:
        meta = store.load_generation_metadata(asset_id) or {}
    for v in (meta.get("versions") or []):
        if v.get("version") == version:
            ec = v.get("edit_context") or {}
            return bool(v.get("bg_free")          # explicit marker (3D source-prep commit)
                    or v.get("type") == "remove_background"
                    or ec.get("op") == "remove_background")
    return False


# ── Source sidecars (3D-only, never versions) ──────────────────────────────
# The "Improve the Source" flow prepares an image for 3D WITHOUT creating 2D
# versions (the user didn't ask to version it; only the Edit tab does that).
# Two sidecar files per source version, keyed to it:
#   asset_v{N}__cutout.png   — background-removed cutout of version N (immutable
#                              cache; removal runs at most once, reused on every
#                              Generate/Regenerate).
#   asset_v{N}__source.png   — the PREPARED 3D source: starts as the cutout, then
#                              Extend/Fill OVERWRITE it (no accumulation — at most
#                              one working file; re-extend always redoes from the
#                              cutout so the canvas never compounds).
# 3D generation reads __source (falling back to __cutout, then the raw version).

def _sidecar_name(version: int, kind: str) -> str:
    return f"asset_v{version}__{kind}.png"


def _ensure_cutout(asset_id: str, version: int, meta: dict = None,
                   bg_method: str = "local") -> "Path | None":
    """Return the path to version N's background-removed cutout, creating+caching
    it once if needed. If the version is already background-free, that file IS the
    cutout. Returns None only if the source image can't be found. Non-fatal on a
    removal error (returns the original path so callers still have an image).

    ``bg_method`` selects the remover: ``"local"`` (free rembg) or ``"bedrock"``
    (paid SD). Cached cutout is reused regardless of method — a method change only
    takes effect after the cached sidecar is cleared (e.g. via op="reset")."""
    if meta is None:
        meta = store.load_generation_metadata(asset_id) or {}
    src = _version_image_path(asset_id, version, meta)
    if src is None:
        return None
    if _version_is_bg_free(asset_id, version, meta):
        return src
    cached = store.get_generated_file_path(asset_id, _sidecar_name(version, "cutout"))
    if cached is not None:
        return cached
    try:
        from backend.services.post_processor import remove_background
        out = remove_background(src.read_bytes(), method=bg_method)
        return store.save_generated_image(asset_id, _sidecar_name(version, "cutout"), out)
    except Exception as e:
        logger.info("Cutout BG-removal failed for %s v%s (%s) — using original", asset_id, version, e)
        return src


def _prepared_source_path(asset_id: str, version: int, meta: dict = None):
    """The image 3D should consume for version N: the prepared __source sidecar if
    it exists (user ran Extend/Fill), else the cached __cutout, else the raw
    version. This is the single resolver used by both the preview and generation."""
    if meta is None:
        meta = store.load_generation_metadata(asset_id) or {}
    for kind in ("source", "cutout"):
        p = store.get_generated_file_path(asset_id, _sidecar_name(version, kind))
        if p is not None:
            return p
    return _version_image_path(asset_id, version, meta)


@router.get("/source-preview/{asset_id}/{version}")
async def source_preview(asset_id: str, version: int, prepared: bool = False):
    """Serve the image the 3D pipeline uses for a version.

    Default (prepared=False) = the version's CUTOUT — the same artefact the Export
    tab and 3D generation use, so the form's "SOURCE FOR 3D" preview always matches
    what gets converted (and Export). prepared=True additionally prefers the active
    improve-dialog working file (__source, an Extend/Fill result) — used ONLY by the
    open review dialog to show its in-session edits. Never creates a 2D version."""
    from fastapi.responses import FileResponse
    meta = store.load_generation_metadata(asset_id) or {}
    path = None
    if prepared:
        path = store.get_generated_file_path(asset_id, _sidecar_name(version, "source"))
    path = path or _ensure_cutout(asset_id, version, meta)
    if path is None:
        raise HTTPException(404, detail=f"Image not found for asset '{asset_id}' v{version}.")
    return FileResponse(path, media_type="image/png")


class PrepareSourceRequest(BaseModel):
    asset_id: str
    version: int = 1
    op: str                         # "cutout" | "extend" | "inpaint" | "reset"
    prompt: str = ""
    # Extend (outpaint) directions in px.
    up: int = 0
    down: int = 0
    left: int = 0
    right: int = 0
    mask: str | None = None         # base64 PNG mask (inpaint only)
    # Background-removal method for the cutout/re-strip: "local" (free, on-device
    # rembg) or "bedrock" (paid Amazon Bedrock SD). Defaults to local — the 3D
    # mesher only needs the background gone, not a feathered edge, so the free
    # path is the sensible default; the UI still offers Bedrock explicitly.
    bg_method: str = "local"
    # Optional model override for op="extend". Default "" keeps the existing
    # behavior (first enabled Bedrock outpainting model). If set to a model whose
    # model_purpose is "image_edit" (e.g. Qwen-Image-Edit), the extend runs via
    # the instruction-outpaint recipe (pre-pad + complete-the-band + blend-back).
    edit_model: str = ""


@router.post("/prepare-source")
async def prepare_source(body: PrepareSourceRequest):
    """Prepare a version's 3D source IN PLACE via sidecar files — NO 2D versions.

    op:
      • cutout  — ensure the background-removed cutout exists (idempotent cache).
      • extend  — outpaint the CUTOUT (never a prior extension → no compounding),
                  re-strip its background, and save as the prepared __source.
      • inpaint — fill/replace a masked region of the CURRENT prepared source,
                  re-strip, save back to __source.
      • reset   — drop the prepared __source (revert to the plain cutout).

    Returns { ok, analysis } where analysis is the completeness re-review of the
    resulting source, so the caller can show the verdict without a second call.
    """
    from backend.services.bedrock_client import invoke_image_model
    from backend.services.post_processor import remove_background, _find_model_key_by_purpose
    from backend.services.cost_tracker import reset_costs, get_total_cost, get_cost_breakdown
    import base64 as _b64

    meta = store.load_generation_metadata(body.asset_id) or {}
    aid, ver = body.asset_id, body.version

    if body.op == "reset":
        p = store.get_generated_file_path(aid, _sidecar_name(ver, "source"))
        if p is not None:
            try: p.unlink()
            except Exception: pass
        return {"ok": True}

    # Track the Bedrock spend for this source-prep step. These ops (BG-removal,
    # outpaint/inpaint, and the vision LLM inside _analyze_source_bytes) all call
    # add_cost internally; without a request-scoped reset + flush that cost was
    # orphaned and discarded. Flush it to a telemetry cost event at each return.
    reset_costs()

    def _flush_source_cost():
        """Report the accumulated source-prep cost (Bedrock edits + vision LLM)."""
        try:
            total = get_total_cost()
            if total > 0:
                from backend.services.telemetry import track_image_edit
                track_image_edit(edit_type=f"3d_source_{body.op}",
                                 model="source_prep", cost_usd=total)
        except Exception:
            pass

    # Base cutout (created/cached once) — the immutable clean starting point.
    cutout = _ensure_cutout(aid, ver, meta, bg_method=body.bg_method)
    if cutout is None:
        raise HTTPException(404, detail=f"Image not found for asset '{aid}' v{ver}.")

    if body.op == "cutout":
        result = {"ok": True, "analysis": _analyze_source_bytes(cutout.read_bytes(), meta)}
        _flush_source_cost()
        return result

    try:
        if body.op == "extend":
            dirs = {k: max(0, min(2000, int(getattr(body, k) or 0)))
                    for k in ("up", "down", "left", "right")}
            if not any(dirs.values()):
                raise HTTPException(400, detail="Set at least one extend direction (up/down/left/right).")
            # Instruction editor chosen (e.g. Qwen-Image-Edit): pre-pad the canvas,
            # ask the model to complete ONLY the band(s), blend the original back.
            # Runs synchronously (waits on the async endpoint) — same UX contract
            # as the Bedrock path. Isolated: only fires when the UI explicitly
            # selects an image_edit-purpose model; default path is unchanged.
            _edit_cfg = None
            if body.edit_model:
                from backend.services.model_registry import get_image_model
                _edit_cfg = get_image_model(body.edit_model) or {}
            if _edit_cfg and _edit_cfg.get("model_purpose") == "image_edit":
                from backend.services.instruction_outpaint import (
                    pad_image_for_outpaint, build_outpaint_instruction,
                    restore_geometry_and_blend)
                from backend.services.sagemaker_invoker import invoke_instruction_edit_sync
                _src = cutout.read_bytes()
                padded, geom = pad_image_for_outpaint(
                    _src, left=dirs["left"], right=dirs["right"],
                    up=dirs["up"], down=dirs["down"])
                instruction = build_outpaint_instruction(
                    (body.prompt or "").strip(), left=dirs["left"],
                    right=dirs["right"], up=dirs["up"], down=dirs["down"])
                out = invoke_instruction_edit_sync(body.edit_model, instruction, padded)
                out = restore_geometry_and_blend(out, _src, geom)
            else:
                key = _find_model_key_by_purpose("outpainting")
                if not key:
                    raise HTTPException(400, detail="No outpainting model available.")
                # ALWAYS extend the CUTOUT (never a prior __source) so the canvas
                # never compounds — re-extend redoes it larger from the clean base.
                out = invoke_image_model(
                    key, (body.prompt or "").strip(), source_image=cutout.read_bytes(),
                    extra_params={k: v for k, v in dirs.items() if v > 0},
                )
        elif body.op == "inpaint":
            if not body.mask:
                raise HTTPException(400, detail="A mask is required to fill/replace a region.")
            key = _find_model_key_by_purpose("inpainting")
            if not key:
                raise HTTPException(400, detail="No inpainting model available.")
            # Fill/replace works on the CURRENT prepared source (or the cutout if none).
            base = store.get_generated_file_path(aid, _sidecar_name(ver, "source")) or cutout
            out = invoke_image_model(
                key, (body.prompt or "").strip(), source_image=base.read_bytes(),
                mask_image=_b64.b64decode(body.mask),
            )
        else:
            raise HTTPException(400, detail=f"Unknown op '{body.op}'.")
    except HTTPException:
        raise
    except Exception as e:
        # Surface a validation-style error as 400, else 502.
        msg = str(e)
        code = 400 if "ValidationException" in type(e).__name__ or "ValidationException" in msg else 502
        raise HTTPException(code, detail=f"Source {body.op} failed: {msg}")

    # Stability edit models re-bake a background, so re-strip to keep a clean cutout.
    try:
        out = remove_background(out, method=body.bg_method)
    except Exception as e:
        logger.info("Post-%s re-strip failed for %s v%s (%s) — keeping as-is", body.op, aid, ver, e)
    saved = store.save_generated_image(aid, _sidecar_name(ver, "source"), out)
    result = {"ok": True, "analysis": _analyze_source_bytes(saved.read_bytes(), meta)}
    _flush_source_cost()
    return result


class ThreeDCommitSourceRequest(BaseModel):
    asset_id: str
    version: int = 1
    # Ops the user ran in the improve dialog (for the version's `type` + provenance).
    ops: list[str] = []
    prompt: str = ""


@router.post("/commit-source")
async def commit_source(body: ThreeDCommitSourceRequest):
    """Materialize a version's PREPARED 3D source (the `__source` sidecar produced
    by Improve-the-Source Extend/Fill) as a NEW 2D version — so the improved image
    is a first-class, visible version and any 3D generated from it attributes to
    THAT version, not the untouched Original.

    Commit-time versioning: the improve dialog experiments freely on the sidecar
    (unlimited rounds, no version churn); this is called ONCE, on "Use this for
    3D", only when an improvement was actually made. If there's no `__source`
    sidecar (user made no changes), it's a no-op → {committed: false}.

    Mirrors the Edit tab's versioned save (archive current → save new asset.png →
    append version record → repoint current_version), under the SAME per-asset
    write lock, with sparse max+1 numbering. The committed image is already
    background-free (the improve flow re-strips after each op), so it's marked
    bg_free and pre-cached as the new version's __cutout (3D skips re-removal).
    """
    import io
    import shutil
    from backend.services.asset_locks import asset_write_lock

    aid, ver = body.asset_id, body.version
    with asset_write_lock(aid):
        meta = store.load_generation_metadata(aid) or {}
        if not meta:
            raise HTTPException(404, detail=f"Asset '{aid}' not found.")

        src_path = store.get_generated_file_path(aid, _sidecar_name(ver, "source"))
        if src_path is None or not src_path.exists():
            # No prepared source = user made no changes → nothing to version.
            return {"committed": False, "version": ver}
        improved_bytes = src_path.read_bytes()

        asset_dir = store.generated_asset_dir(aid)
        versions = meta.get("versions", [])
        if not versions:
            # Seed the implicit original as v1 so the new version is v2+ (same as /edit).
            versions.append({
                "version": 1, "type": "original",
                "prompt": meta.get("prompt", ""),
                "enhanced_prompt": meta.get("enhanced_prompt", ""),
                "image_model": meta.get("image_model", ""),
                "model_label": meta.get("model_label", ""),
                "timestamp": meta.get("created_at", ""),
            })
        # Sparse max+1 (tombstones/deletions never reuse a number) — matches /edit.
        next_version = max(v.get("version", 0) for v in versions) + 1

        # Archive the outgoing current asset.png/.svg under its TRUE current number.
        current_png = asset_dir / "asset.png"
        if current_png.exists():
            prev_v = meta.get("current_version") or (next_version - 1)
            prev_png = asset_dir / f"asset_v{prev_v}.png"
            if not prev_png.exists():
                shutil.copy2(str(current_png), str(prev_png))
            current_svg = asset_dir / "asset.svg"
            prev_svg = asset_dir / f"asset_v{prev_v}.svg"
            if current_svg.exists() and not prev_svg.exists():
                shutil.copy2(str(current_svg), str(prev_svg))

        # The improved (bg-free) image becomes the new current version. No separate
        # __cutout sidecar is stored: the version record's `bg_free: true` (below)
        # makes _version_is_bg_free short-circuit _ensure_cutout to the version's
        # OWN image, and _prepared_source_path falls back to it too — so the version
        # IS its cutout everywhere 3D needs one (no duplicate file).
        store.save_generated_image(aid, "asset.png", improved_bytes)

        # Regenerate the current SVG from the new image (best-effort).
        try:
            from backend.services.post_processor import process_asset
            process_asset(image_bytes=improved_bytes, enhanced_prompt=(body.prompt or ""),
                          remove_bg=False, do_upscale=False, do_svg=True,
                          svg_output_path=asset_dir / "asset.svg")
        except Exception as e:
            logger.warning("commit-source: SVG generation failed for %s v%s (%s)", aid, next_version, e)

        # Version type from the ops the user actually ran (extend→outpainting,
        # fill→inpainting), so the record + version-bar label are truthful.
        _ops = set(body.ops or [])
        vtype = "outpainting" if "extend" in _ops else ("inpainting" if "inpaint" in _ops else "source_prep")
        _dims = {"width": None, "height": None}
        try:
            from PIL import Image as _PILImage
            with _PILImage.open(io.BytesIO(improved_bytes)) as _img:
                _dims = {"width": _img.width, "height": _img.height}
        except Exception:
            pass

        versions.append({
            "version": next_version,
            "type": vtype,
            "prompt": (body.prompt or "").strip(),
            "enhanced_prompt": (body.prompt or "").strip(),
            "image_model": meta.get("image_model", ""),
            "model_label": meta.get("model_label", ""),
            "result_dims": _dims if _dims.get("width") else None,
            # Already-background-free (improve flow re-strips) — see _version_is_bg_free.
            "bg_free": True,
            # Provenance: this version was committed from the 3D Improve-the-Source flow.
            "edit_context": {"trigger": "3d_source_completion",
                             "committed_from_version": ver, "ops": sorted(_ops)},
            "timestamp": datetime.utcnow().isoformat(),
        })

        new_meta = dict(meta)
        new_meta.update({
            "original_prompt": meta.get("original_prompt") or meta.get("prompt", ""),
            "original_image_model": meta.get("original_image_model") or meta.get("image_model", ""),
            "versions": versions,
            "current_version": next_version,
            "width": _dims.get("width") or meta.get("width"),
            "height": _dims.get("height") or meta.get("height"),
            "last_edited_at": datetime.utcnow().isoformat(),
            "last_edit_type": vtype,
        })
        store.save_generation_metadata(aid, new_meta)

        # The prepared source is now consumed into the new version — drop the OLD
        # version's __source sidecar so re-reviewing it won't re-show the change.
        try:
            src_path.unlink(missing_ok=True)
        except Exception:
            pass

    logger.info("commit-source: %s v%s improved-source committed as new v%d (type=%s)",
                aid, ver, next_version, vtype)
    return {"committed": True, "version": next_version, "type": vtype}


class AnalyzeSourceRequest(BaseModel):
    asset_id: str
    version: int = 1


def _analyze_source_bytes(img_bytes: bytes, meta: dict) -> dict:
    """Core completeness analysis on raw image bytes (shared by /analyze-source and
    /prepare-source). Vision LLM + deterministic alpha-edge override. Conservative:
    defaults to complete/analyzed=false on any error so it never blocks a good image."""
    asset_type = (meta.get("asset_type") or "character").replace("_", " ")
    # Feed the ORIGINAL generation prompt so the LLM judges completeness against
    # the intended subject (any subject — living, object, fictional, any/no limbs).
    source_prompt = (
        (meta.get("refined_prompt") or meta.get("enhanced_prompt")
         or meta.get("recomposed_prompt") or meta.get("prompt")
         or meta.get("original_prompt") or "").strip()
        or "(no prompt recorded — judge purely from the image)"
    )[:1200]

    try:
        from backend.services.bedrock_client import invoke_llm
        from backend.services.prompt_templates import get_template, get_system_prompt
        prompt = get_template("three_d_source_analysis").format(
            asset_type=asset_type, source_prompt=source_prompt)
        system = get_system_prompt("three_d_source_analysis")
        # Fit under Bedrock's 5 MB vision limit — BG-removed cutouts are large RGBA
        # PNGs (~6.6 MB) that otherwise fail with a ValidationException, silently
        # defaulting the whole analysis to "complete".
        vision_bytes = _fit_image_for_vision(img_bytes)
        raw = invoke_llm(prompt, system=system, complexity="complex",
                         images=[vision_bytes], max_tokens=400, temperature=0.0)
        txt = (raw or "").strip()
        if "```" in txt:
            txt = txt.split("```")[1].lstrip("json").strip() if txt.count("```") >= 2 else txt
        start, end = txt.find("{"), txt.rfind("}")
        data = json.loads(txt[start:end + 1]) if start >= 0 and end > start else {}
    except Exception as e:
        logger.info("3D source analysis unavailable (%s) — defaulting to complete", e)
        return {"complete": True, "analyzed": False}

    complete = bool(data.get("complete", True))
    outp = data.get("suggest_outpaint", {}) or {}
    def _clamp(v):
        try: return max(0, min(512, int(v)))
        except (TypeError, ValueError): return 0
    suggest = {d: _clamp(outp.get(d, 0)) for d in ("down", "up", "left", "right")}
    crop_edges = data.get("crop_edges", []) or []

    # Deterministic alpha-edge crop check OVERRIDES the LLM when it fires (a
    # silhouette touching a frame edge is provable, unlike the LLM which is fooled
    # by the empty void below a cutout subject).
    alpha = _alpha_edge_crop(img_bytes)
    alpha_override = bool(alpha and alpha["crop_edges"])
    if alpha_override:
        complete = False
        crop_edges = sorted(set(crop_edges) | set(alpha["crop_edges"]))
        for d, v in alpha["suggest_outpaint"].items():
            suggest[d] = max(suggest.get(d, 0), _clamp(v))

    any_outpaint = any(suggest.values())
    llm_defect = (data.get("defect", "") or "").strip().lower()
    if alpha_override:
        defect = "cropped"
        reason = "The subject's silhouette runs into the frame edge (" + ", ".join(crop_edges) + "), so part of it is cut off."
    else:
        defect = llm_defect or ("cropped" if (not (complete or not any_outpaint)) else "none")
        reason = data.get("reason", "")
    return {
        "analyzed": True,
        "complete": complete or not any_outpaint,
        "subject": data.get("subject", ""),
        "crop_edges": crop_edges,
        "missing": data.get("missing", []) or [],
        "suggest_outpaint": suggest,
        "outpaint_prompt": (data.get("outpaint_prompt", "") or "").strip()[:300],
        "defect": defect,
        "defect_area": (data.get("defect_area", "") or "").strip()[:200],
        "reason": reason,
    }


@router.post("/analyze-source")
async def analyze_3d_source(body: AnalyzeSourceRequest):
    """Vision-analyze a version's PREPARED 3D source (cutout/__source sidecar) for
    completeness, so the UI can offer an outpaint/fill completion. Conservative —
    defaults to "complete" on any uncertainty so it never blocks a good image."""
    meta = store.load_generation_metadata(body.asset_id) or {}
    # Analyze exactly what 3D will consume: the prepared source (or cutout).
    img_path = _prepared_source_path(body.asset_id, body.version, meta)
    if img_path is None:
        raise HTTPException(404, detail=f"Image not found for asset '{body.asset_id}' v{body.version}.")
    # Track the vision-LLM spend (was orphaned — add_cost with no request flush).
    from backend.services.cost_tracker import reset_costs, get_total_cost
    reset_costs()
    result = _analyze_source_bytes(img_path.read_bytes(), meta)
    try:
        total = get_total_cost()
        if total > 0:
            from backend.services.telemetry import track_image_edit
            track_image_edit(edit_type="3d_source_analyze", model="vision_llm", cost_usd=total)
    except Exception:
        pass
    return result


class RecordSourceReviewRequest(BaseModel):
    asset_id: str
    version: int
    review: dict


@router.post("/record-source-review")
async def record_source_review(body: RecordSourceReviewRequest):
    """Persist a completion re-review verdict onto a 2D version's record.

    After an outpaint round, the result is re-analyzed; this stores that verdict
    on the new version (meta.versions[].source_review) so the full iteration
    history — each result's completeness verdict + what was still missing — is
    reviewable later, not just shown transiently in the popup.
    """
    r = body.review or {}
    review = {
        "complete": bool(r.get("complete", True)),
        "missing": r.get("missing", []) or [],
        "crop_edges": r.get("crop_edges", []) or [],
        "reason": r.get("reason", ""),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    # Per-asset lock: shared with the 3D finalize + 2D edit/commit writers so
    # this RMW of metadata.json can't lost-update against a concurrent write.
    from backend.services.asset_locks import asset_write_lock
    with asset_write_lock(body.asset_id):
        meta = store.load_generation_metadata(body.asset_id) or {}
        for v in meta.get("versions", []):
            if v.get("version") == body.version:
                v["source_review"] = review
                store.save_generation_metadata(body.asset_id, meta)
                return {"ok": True}
    return {"ok": False, "detail": "version not found"}


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
    # Serialize with the other metadata writers on this asset (3D finalize, 2D
    # edit/commit) — all take this per-asset lock, so concurrent writes to
    # metadata.json can't lost-update each other.
    from backend.services.asset_locks import asset_write_lock
    with asset_write_lock(body.asset_id):
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


def _3d_instance_hourly_rate(model_key: str, cfg: dict = None) -> float:
    """Hourly USD rate for a 3D endpoint's deployed instance — REGISTRY ONLY.

    Resolves the DEPLOYED instance type's rate via the shared registry-backed
    resolver (no hardcoded prices). Falls back to the catalog's recommended
    instance if the deployment didn't record a type. Returns 0.0 if the registry
    has no rate (caller treats 0 as 'unknown' and reports cost 0 rather than
    guessing)."""
    from backend.services.custom_models import get_catalog_model, get_instance_hourly_rate
    if cfg is None:
        _, cfg = _find_triposg_model(model_key)
    cfg = cfg or {}
    catalog_key = cfg.get("catalog_key", "")
    dep = cfg.get("deployment", {}) or {}
    inst = dep.get("instance_type", "")
    region = dep.get("region") or _get_region()
    rate = get_instance_hourly_rate(inst, catalog_key, region)
    if not rate:
        # Deployment didn't record an instance type — price the catalog default.
        rec = ((get_catalog_model(catalog_key) or {}).get("requirements", {}) or {}).get("recommended_instance", "")
        rate = get_instance_hourly_rate(rec, catalog_key, region)
    return rate


def _track_3d_completion(job: dict) -> None:
    """Record telemetry + compute cost for a finished 3D job.

    3D runs on a GPU SageMaker endpoint (the app's most expensive op) but has
    its own poller and never routed through async_jobs, so it missed all cost
    tracking. Compute cost = instance hourly rate × actual duration (submit →
    complete). Mirrors async_jobs._track_completion: an add_cost entry for the
    session breakdown, a custom-model invoke event, and a studio .cost event so
    PulseBoard's aggregate total includes 3D spend. Non-fatal."""
    try:
        model_key = job.get("model_key", "")
        _, cfg = _find_triposg_model(model_key)
        rate = _3d_instance_hourly_rate(model_key, cfg)
        # Duration submit → now (this runs at finalize). Cap at 30 min to bound a
        # stuck/relayed timestamp (3D jobs legitimately run up to ~18 min).
        dur = 0.0
        try:
            sub = job.get("submitted_at", "")
            if sub:
                dur = (datetime.now(timezone.utc) - datetime.fromisoformat(sub)).total_seconds()
        except Exception:
            pass
        dur = max(0.0, min(dur, 1800.0))
        # Amortized cooldown share — the endpoint stays warm after the last job before
        # scaling to zero, and that idle time is billed. Parity with async_jobs
        # (_calculate_compute_cost): attribute a share to this job. 3D's scale-in
        # cooldown is latency-derived (max(600, typical×2)); 3D jobs run ~sequentially,
        # so amortize across in-flight 3D jobs (+1) rather than assuming a big batch.
        _lat = int((cfg.get("invoke", {}) or {}).get("typical_latency_seconds", 0) or 0)
        _cooldown_s = max(600, _lat * 2)
        _inflight = sum(1 for j in _3d_jobs.values()
                        if j.get("status") in ("submitted", "processing", "in_progress", "generating")) or 1
        cooldown_share = (_cooldown_s / _inflight / 3600.0) * rate if rate else 0.0
        compute_cost = round((dur / 3600.0) * rate + cooldown_share, 6) if rate else 0.0
        label = f"3D {model_key} ({dur:.0f}s + {_cooldown_s // _inflight}s cooldown @ ${rate:.2f}/hr)"

        from backend.services.cost_tracker import add_background_cost
        if compute_cost > 0:
            # Background accumulator (this runs in the poller daemon thread, not a
            # request) — flushed to system.infra_cost like other background spend.
            add_background_cost("three_d_compute", compute_cost, label)

        from backend.services.telemetry import track_custom_model_invoke, track_image_cost
        track_custom_model_invoke(
            model=model_key, cost_usd=compute_cost,
            latency_ms=int(dur * 1000), predictor_type="image_to_3d",
        )
        if compute_cost > 0:
            track_image_cost(cost_usd=compute_cost, model=model_key,
                             breakdown=f"3D compute: {label}")
    except Exception as e:
        logger.debug("3D completion tracking failed for %s: %s", job.get("job_id"), e)


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
        # Whether the texture bake actually succeeded. The handler returns
        # textured=false when it fell back to a neutral-gray untextured mesh (bake
        # error). Default True for older/missing output so we never mislabel a good
        # mesh. Recorded so the AssetViewer can show a clear fallback notice — the
        # user still gets a usable mesh (no wasted time/cost), just informed.
        _textured = bool(output_data.get("textured", True))
        if _ptype == "trellis2_full":
            # Standalone full TRELLIS.2 — geometry AND texture from one model; no
            # separate texture-backend choice.
            pipeline = {
                "geometry_model": "TRELLIS.2 (full pipeline)",
                "texture_backend": "trellis2_full",
                "texture_label": "TRELLIS.2 (integrated SLAT PBR)",
                "instance_type": _instance,
                "textured": _textured,
                "has_pbr": _textured and bool(output_data.get("has_pbr", True)),
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
                "textured": _textured,
                "has_pbr": _textured and bool(output_data.get("has_pbr") or output_data.get("normal_map")),
                "rasterizer": output_data.get("rasterizer", ""),
            }
        # Record the user's pipeline choice + the license they accepted at deploy
        # (consent provenance) into the persisted metadata.
        pipeline["pipeline_type"] = _ptype
        pipeline["license_name"] = _pinfo.get("license_name", "")
        pipeline["license_accepted_at"] = _pinfo.get("license_accepted_at", "")
        pipeline["commercial"] = _pinfo.get("commercial")

        # Attribution flags — a durable per-asset record of third-party components
        # whose license REQUIRES visible attribution wherever the asset is surfaced.
        # DINOv3 (Meta) is TRELLIS.2's image encoder and mandates a "Built with
        # DINOv3" notice; it's used by BOTH the standalone TRELLIS.2 pipeline and the
        # `trellis2` texture backend on TripoSG (only when texturing actually ran).
        _uses_dinov3 = (_ptype == "trellis2_full") or (
            _textured and pipeline.get("texture_backend") == "trellis2")
        if _uses_dinov3:
            pipeline["attributions"] = ["Built with DINOv3"]

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

        # Serialize the metadata read-modify-write against the 2D edit/commit
        # writers (which hold the SAME per-asset lock). Without this, a 3D job
        # finalizing while the user commits a new 2D version on the same asset
        # would lost-update metadata.json (drop the new version, or the 3D). The
        # global _3d_finalize_lock only serializes 3D finalizes against EACH
        # OTHER, not against the 2D writers. Lock order here is
        # _3d_finalize_lock (held by the caller) → asset_write_lock; the 2D
        # writers take only asset_write_lock, so there's no deadlock.
        from backend.services.asset_locks import asset_write_lock
        with asset_write_lock(asset_id):
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

        # ── Telemetry + cost (was entirely missing for 3D) ──────────────────
        # GPU compute cost (instance hourly × duration) + the GLB S3 download.
        _track_3d_completion(job)
        try:
            from backend.services.cost_tracker import add_background_s3_cost
            add_background_s3_cost("get", len(glb_bytes), "3D GLB output download",
                                   region=_get_region())
        except Exception:
            pass

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
            # Self-stop when there are no pending jobs left — don't idle a thread
            # polling S3 with nothing to finalize. It restarts on the next 3D
            # submit (start_3d_poller). Mirrors the 2D poller + the boot gate:
            # a poller runs only while there's work.
            if not pending:
                logger.info("3D job poller stopping — no in-progress jobs left")
                break
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
    # One actionable line reporting what it found + what it will do (not just
    # "started"). Pending = jobs it will watch S3 for and finalize.
    pending = [j for j in _3d_jobs.values() if j.get("status") not in ("complete", "failed")]
    if pending:
        logger.info("3D job poller started — watching %d in-progress job(s) (%s); polling S3 every "
                    "15s to download + finalize each GLB as it lands",
                    len(pending), ", ".join(j.get("job_id", "?") for j in pending))
    else:
        logger.info("3D job poller started — no in-progress jobs; idle-watching, will finalize "
                    "any new job's GLB from S3 every 15s")


def stop_3d_poller() -> None:
    """Stop the background 3D-job poller (called on shutdown)."""
    _3d_poller_stop.set()
