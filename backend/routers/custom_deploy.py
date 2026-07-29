"""Custom Model Deployment API — manage self-hosted 3rd-party models.

Endpoints for browsing the catalog, downloading, deploying, and managing
custom models on Amazon SageMaker in the user's AWS account.

HuggingFace models: the Amazon SageMaker container pulls weights directly
from HuggingFace at startup (no local download or S3 upload of weights).
For gated models, the HF token is stored encrypted in AWS Secrets Manager
and automatically cleaned up when the model is torn down.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/custom-models", tags=["custom-models"])


# ── Helpers ───────────────────────────────────────────────────────────────

# Cache existence check — lightweight HEAD request, cached per session
_cache_status: dict[str, bool] = {}


def _check_cache_quick(model_key: str) -> bool:
    """Quick check if model has S3 cache. Cached in-memory for the request."""
    if model_key in _cache_status:
        return _cache_status[model_key]
    try:
        from backend.services.sagemaker_deployer import check_model_cache_exists
        result = check_model_cache_exists(model_key)
        _cache_status[model_key] = result.get("cached", False)
        return _cache_status[model_key]
    except Exception:
        return False


def _record_license_acceptance(model_key: str, license_name: str):
    """Record that the user accepted a model's license in the user registry."""
    try:
        from backend.services.model_registry import get_registry, _save
        from datetime import datetime, timezone

        registry = get_registry()
        acceptances = registry.setdefault("license_acceptances", {})
        acceptances[model_key] = {
            "license_name": license_name,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        }
        _save()
        logger.info("Recorded license acceptance for %s (%s)", model_key, license_name)
    except Exception as e:
        logger.warning("Failed to record license acceptance for %s: %s", model_key, e)


def _hf_repos_for_model(model: dict) -> list[dict]:
    """Enumerate the HuggingFace repos a model pulls at runtime + their gated flag.

    A model's weights come from its `source` repo PLUS any HF repos listed in
    `license_agreement.dependencies` (e.g. TRELLIS.2 pulls facebook/dinov3, which
    is gated). De-duplicates by repo_id, preserving order (source first). Each
    entry: {repo_id, name, gated (declared), license_url}. Used by the gated-access
    pre-check so we probe EVERY repo the deploy will need, not just the main one.
    """
    repos: dict[str, dict] = {}

    def _add(repo_id, name=None, gated=False, url=None):
        if not repo_id:
            return
        rid = repo_id.strip()
        # Normalise a full URL down to "org/name".
        if "huggingface.co/" in rid:
            rid = rid.split("huggingface.co/")[-1].strip("/")
        if not rid or rid in repos:
            return
        repos[rid] = {
            "repo_id": rid,
            "name": name or rid,
            "gated": bool(gated),
            "license_url": url or f"https://huggingface.co/{rid}",
        }

    src = model.get("source", {}) or {}
    if src.get("type") == "huggingface":
        _add(src.get("repo_id"), gated=model.get("requires_hf_auth", False))

    for dep in (model.get("license_agreement", {}) or {}).get("dependencies", []) or []:
        repo = dep.get("repo_id") or dep.get("hf_repo") or dep.get("url", "")
        if "huggingface.co/" in (repo or "") or dep.get("repo_id") or dep.get("hf_repo"):
            _add(repo, name=dep.get("name"), gated=dep.get("gated", False),
                 url=dep.get("url"))

    return list(repos.values())


def _check_gated_access(model: dict, token: str | None) -> dict:
    """Probe each HF repo a model needs and report per-repo accessibility.

    Uses huggingface_hub.auth_check(repo_id, token=...) which distinguishes:
      • accessible        → ok
      • GatedRepoError    → token valid but gate not yet accepted by this account
      • RepositoryNotFound→ private/typo/token lacks visibility
      • 401/no token      → authentication missing
    Returns {has_token, repos:[{repo_id, gated, accessible, status, action, license_url}],
             all_clear, blocking:[repo_id,...]}. `action` gives the exact next step.
    """
    from huggingface_hub import auth_check
    from huggingface_hub.utils import (
        GatedRepoError, RepositoryNotFoundError, HfHubHTTPError,
    )

    repos = _hf_repos_for_model(model)
    out = {"has_token": bool(token), "repos": [], "all_clear": True, "blocking": []}

    for r in repos:
        rid = r["repo_id"]
        entry = {
            "repo_id": rid, "name": r["name"], "gated": r["gated"],
            "license_url": r["license_url"], "accessible": False,
            "status": "unknown", "action": "",
        }
        try:
            auth_check(rid, token=token)
            entry.update(accessible=True, status="ok", action="")
        except GatedRepoError:
            entry.update(
                accessible=False, status="gated_not_accepted", gated=True,
                action=(f"Open {r['license_url']} while signed in to the SAME "
                        "HuggingFace account as your token, and click "
                        "“Agree and access repository”. Then retry."),
            )
        except RepositoryNotFoundError:
            entry.update(
                accessible=False, status="not_found",
                action=(f"Repo not visible to this token. Confirm the name "
                        f"({rid}) and that your token can read it."),
            )
        except HfHubHTTPError as exc:
            code = getattr(getattr(exc, "response", None), "status_code", None)
            if code in (401, 403):
                entry.update(
                    accessible=False, status="auth_required",
                    action=("Add or refresh your HuggingFace token "
                            "(huggingface.co/settings/tokens, Read scope)."),
                )
            else:
                entry.update(accessible=False, status="error", action=str(exc)[:200])
        except Exception as exc:
            entry.update(accessible=False, status="error", action=str(exc)[:200])

        if not entry["accessible"]:
            out["all_clear"] = False
            out["blocking"].append(rid)
        out["repos"].append(entry)

    return out


# ── Catalog ───────────────────────────────────────────────────────────────

@router.get("/catalog")
def list_catalog(force: bool = False):
    """List all available custom models with deployment status.

    Sync (not async) so boto3 calls don't block the event loop.
    FastAPI runs sync endpoints in a threadpool automatically.

    Only checks Amazon SageMaker status for models that are registered in the
    model registry (i.e., previously deployed). Undeployed models skip
    the status check — much faster.

    `force=true` (sent by the manual "Refresh Status" button) bypasses the 30s
    endpoint-status cache so the user gets truly-current state on demand,
    instead of a stale cached value that makes the button look like a no-op.
    """
    from backend.services.custom_models import get_catalog
    from backend.services.model_registry import get_registry
    from backend.services.sagemaker_deployer import check_endpoint_status, clear_endpoint_status_cache

    if force:
        clear_endpoint_status_cache()

    catalog = dict(get_catalog())  # Copy built-in catalog
    # Merge user-added models
    user_catalog = _load_user_catalog()
    for key, entry in user_catalog.items():
        if not key.startswith("_"):
            catalog[key] = {**entry, "_user_added": True}
    registry = get_registry()
    result = []

    # Build set of deployed custom model keys from registry
    deployed_keys = set()
    for section in ("image_models", "video_models", "post_processing", "utility_models"):
        for key, cfg in registry.get(section, {}).items():
            if cfg.get("model_source") == "custom_hosted":
                deployed_keys.add(key)

    # Also check in-progress deployments
    for key in _deploy_status:
        if _deploy_status[key].get("stage") in ("preparing", "downloading", "uploading", "deploying"):
            deployed_keys.add(key)

    # Build mapping: catalog_key → LIST of deployed instances.
    # Each catalog model can have multiple deployments on different instances.
    catalog_to_deployed: dict[str, list] = {}
    for dk in deployed_keys:
        for ck in catalog:
            if dk == ck or dk.startswith(ck + "_"):
                ep_name = ""
                instance_type = ""
                deploy_label = ""
                for section in ("image_models", "video_models", "post_processing", "utility_models"):
                    entry = registry.get(section, {}).get(dk, {})
                    if entry:
                        ep_name = entry.get("deployment", {}).get("endpoint_name", "")
                        instance_type = entry.get("deployment", {}).get("instance_type", "")
                        deploy_label = entry.get("label", dk)
                        break
                if ep_name:
                    catalog_to_deployed.setdefault(ck, []).append({
                        "deployed_key": dk,
                        "endpoint_name": ep_name,
                        "instance_type": instance_type,
                        "label": deploy_label,
                    })
                break

    for key, model in catalog.items():
        if model.get("hidden"):
            continue
        deployed_instances = catalog_to_deployed.get(key, [])

        # Build per-instance status for each deployment
        instances_data = []
        for inst in deployed_instances:
            status = check_endpoint_status(inst["endpoint_name"])
            deploy_progress = _deploy_status.get(inst["deployed_key"], {})
            ep_status = status.get("status", "NotFound")
            failure_reason = status.get("failure_reason", "")

            # A Failed endpoint is a dead end — it can't serve and can't recover.
            # Schedule an auto-teardown (removes the endpoint/config/model/registry
            # entry AND clears stale deploy-progress) so the model resets to a
            # clean, deployable state without the user having to hunt for a Remove
            # button. Deliberate + idempotent: guarded by a set so we schedule it
            # once per endpoint; the actual teardown runs in the background and is
            # a no-op if already gone. The user still sees WHY it failed
            # (failure_reason) on this response before the next refresh clears it.
            if ep_status == "Failed":
                _schedule_failed_teardown(inst["deployed_key"], inst["endpoint_name"], failure_reason)

            instances_data.append({
                "deployed_key": inst["deployed_key"],
                "endpoint_name": inst["endpoint_name"],
                "instance_type": inst["instance_type"],
                "label": inst["label"],
                "status": ep_status,
                "failure_reason": failure_reason,
                "warming_up": status.get("warming_up", False),
                "warmup_detail": status.get("warmup_detail", ""),
                "instance_count": status.get("instance_count", 0),
                "deploy_progress": deploy_progress.get("progress", ""),
                "deploy_stage": deploy_progress.get("stage", ""),
            })

        # Top-level status: use first instance for backward compat, or NotFound
        first = instances_data[0] if instances_data else None
        deploy_progress = _deploy_status.get(key, {})

        result.append({
            "key": key,
            "label": model["label"],
            "description": model["description"],
            "category": model["category"],
            "model_purpose": model.get("model_purpose", ""),
            "studio": model["studio"],
            "provider": model["provider"],
            "license": model["license"],
            "requires_hf_auth": model.get("requires_hf_auth", False),
            "hf_license_url": model.get("hf_license_url"),
            "license_agreement": model.get("license_agreement"),
            "version": model.get("version"),
            "last_updated": model.get("last_updated"),
            "requirements": model["requirements"],
            "pricing": model["pricing"],
            "deployment_status": first["status"] if first else "NotFound",
            "failure_reason": first.get("failure_reason", "") if first else "",
            "warming_up": first["warming_up"] if first else False,
            "warmup_detail": first["warmup_detail"] if first else "",
            "instance_count": first["instance_count"] if first else 0,
            "deploy_progress": deploy_progress.get("progress", first["deploy_progress"] if first else ""),
            "deploy_stage": deploy_progress.get("stage", first["deploy_stage"] if first else ""),
            "endpoint_name": first["endpoint_name"] if first else None,
            "deployed_instances": instances_data,
            "user_added": model.get("_user_added", False),
            "bundle": _get_bundle_info(key),
            "has_cache": _check_cache_quick(key),
            "warm_up_info": {
                "cold_start_minutes": "5-10" if model.get("requirements", {}).get("min_vram_gb", 0) > 12 else "3-5",
                "inference_seconds": model.get("invoke", {}).get("typical_latency_seconds", "?"),
                "idle_timeout": "~15 min before scaling to zero (async)",
            },
        })

    # Surface the deployment S3 bucket status. A bucket is REQUIRED to deploy any
    # custom model (the inference handler / model.tar.gz is uploaded there) and is
    # also where async-jobs + notices persist. If it's missing, the frontend shows
    # an upfront prompt so the user configures it BEFORE hitting a deploy failure.
    from backend.services.sagemaker_deployer import get_deployment_s3_bucket, get_bucket_dependencies
    _bkt = get_deployment_s3_bucket() or ""
    # bucket_locked: has dependencies → the UI shows a read-only record (no change
    # offered) since a deployed endpoint permanently binds this bucket.
    _deps = get_bucket_dependencies() if _bkt else {"locked": False, "reasons": []}
    return {
        "models": result,
        "bundles": _get_all_bundles_info(),
        "deployment_bucket": _bkt,
        "bucket_locked": _deps["locked"],
        "bucket_lock_reasons": _deps["reasons"],
    }


def _get_bundle_info(model_key: str) -> dict | None:
    from backend.services.custom_models import get_bundle_for_model, get_bundle
    bundle_key = get_bundle_for_model(model_key)
    if not bundle_key:
        return None
    bundle = get_bundle(bundle_key)
    return {
        "key": bundle_key,
        "label": bundle["label"],
        "shared_with": [m for m in bundle["models"] if m != model_key],
    }


def _get_all_bundles_info() -> list:
    from backend.services.custom_models import get_all_bundles
    result = []
    for key, bundle in get_all_bundles().items():
        result.append({
            "key": key,
            "label": bundle.get("label", key),
            "description": bundle.get("description", ""),
            "models": bundle.get("models", []),
            "instance": bundle.get("requirements", {}).get("recommended_instance", ""),
        })
    return result


@router.get("/catalog/{model_key}")
async def get_catalog_model(model_key: str):
    """Get detailed info for a specific model."""
    from backend.services.custom_models import get_catalog_model as _get
    model = _get(model_key)
    if not model:
        raise HTTPException(404, detail=f"Unknown model: {model_key}")
    return model


@router.get("/instance-options/{model_key}")
async def get_instance_options(model_key: str):
    """Return viable GPU instances for deploying a model, ranked by suitability.

    Checks the user's SageMaker service quotas and evaluates each instance
    against the model's VRAM requirements. Returns only viable options
    with cost, speed estimate, and recommendation level.
    """
    from backend.services.custom_models import get_catalog_model as _get
    from backend.services.model_registry import get_registry

    model = _get(model_key)
    if not model:
        raise HTTPException(404, detail=f"Unknown model: {model_key}")

    reg = get_registry()
    gpu_catalog = reg.get("custom_model_catalog", {}).get("gpu_instances", {})
    model_vram = model.get("requirements", {}).get("min_vram_gb", 8)
    model_dtype = model.get("invoke", {}).get("torch_dtype", "float16")
    needs_bf16 = model_dtype == "bfloat16"
    recommended = model.get("requirements", {}).get("recommended_instance", "")

    # Query account quotas — capture both value and quota code for all instances
    import boto3
    from backend.services.sagemaker_deployer import _get_region
    region = _get_region()
    quotas: dict[str, int] = {}       # instance_type → current quota value
    quota_codes: dict[str, str] = {}  # instance_type → QuotaCode (for requesting increases)
    try:
        sq = boto3.client("service-quotas", region_name=region)
        paginator = sq.get_paginator("list_service_quotas")
        for page in paginator.paginate(ServiceCode="sagemaker"):
            for q in page.get("Quotas", []):
                name = q.get("QuotaName", "")
                if "endpoint" in name.lower() and "usage" in name.lower():
                    instance = name.replace(" for endpoint usage", "").strip()
                    quotas[instance] = int(q.get("Value", 0))
                    quota_codes[instance] = q.get("QuotaCode", "")
    except Exception as e:
        logger.warning("Failed to query service quotas: %s", e)

    # Query pending/recent quota requests for context
    quota_requests: dict[str, dict] = {}  # instance_type → most recent request info
    try:
        req_paginator = sq.get_paginator("list_requested_service_quota_change_history_by_quota")
        for qcode_instance, qcode in quota_codes.items():
            if quotas.get(qcode_instance, 0) > 0:
                continue  # Already have quota, no need to check requests
            try:
                for page in req_paginator.paginate(ServiceCode="sagemaker", QuotaCode=qcode):
                    for req in page.get("RequestedQuotas", []):
                        status = req.get("Status", "")
                        if status in ("PENDING", "CASE_OPENED", "CASE_CLOSED", "APPROVED"):
                            existing = quota_requests.get(qcode_instance)
                            if not existing or req.get("Created", "") > existing.get("created", ""):
                                quota_requests[qcode_instance] = {
                                    "request_id": req.get("Id", ""),
                                    "case_id": req.get("CaseId"),
                                    "status": status,
                                    "desired_value": req.get("DesiredValue", 0),
                                    "created": str(req.get("Created", "")),
                                    "last_updated": str(req.get("LastUpdated", "")),
                                }
            except Exception:
                pass
    except Exception as e:
        logger.debug("Failed to query quota request history: %s", e)

    # Count how many endpoints already use each instance type
    instance_usage: dict[str, int] = {}
    try:
        sm = boto3.client("sagemaker", region_name=region)
        ep_paginator = sm.get_paginator("list_endpoints")
        for page in ep_paginator.paginate(NameContains="artsmoker", StatusEquals="InService"):
            for ep in page.get("Endpoints", []):
                try:
                    cfg = sm.describe_endpoint_config(
                        EndpointConfigName=sm.describe_endpoint(
                            EndpointName=ep["EndpointName"]
                        )["EndpointConfigName"]
                    )
                    for pv in cfg.get("ProductionVariants", []):
                        it = pv.get("InstanceType", "")
                        if it:
                            instance_usage[it] = instance_usage.get(it, 0) + 1
                except Exception:
                    pass
    except Exception as e:
        logger.debug("Failed to count endpoint instance usage: %s", e)

    allowed_instances = model.get("requirements", {}).get("allowed_instances")

    options = []
    for instance_type, specs in gpu_catalog.items():
        if instance_type.startswith("_"):
            continue

        # Model-specific instance filtering (e.g., FLUX.2 only on g6e.4xl+)
        if allowed_instances and instance_type not in allowed_instances:
            continue

        total_vram = specs.get("total_vram_gb", 0)
        vram_per_gpu = specs.get("vram_per_gpu_gb", 0)
        gpus = specs.get("gpus", 1)
        supports_bf16 = specs.get("bf16", True)
        cost = specs.get("cost_per_hour_usd", 0)
        quota = quotas.get(instance_type, 0)
        in_use = instance_usage.get(instance_type, 0)
        available = max(0, quota - in_use)
        needs_quota = available <= 0

        # Skip if bf16 needed but not supported
        if needs_bf16 and not supports_bf16:
            continue

        # Skip if model needs more system RAM than instance has
        # (e.g., runtime quantization needs lots of RAM)
        min_ram = model.get("requirements", {}).get("min_ram_gb", 0)
        instance_ram = specs.get("ram_gb", 0)
        if min_ram > 0 and instance_ram < min_ram:
            continue

        # Evaluate viability
        uses_offload = model.get("invoke", {}).get("enable_model_cpu_offload") or model.get("invoke", {}).get("enable_sequential_cpu_offload")
        uses_quantization = bool(model.get("invoke", {}).get("quantization_components"))

        if total_vram >= model_vram * 1.3:
            viability = "recommended"
            speed_note = "Model fits comfortably"
        elif total_vram >= model_vram:
            viability = "viable"
            speed_note = "Fits with some headroom"
        elif uses_offload and vram_per_gpu >= model_vram * 0.8:
            # With offloading, only one component on GPU at a time
            viability = "viable"
            speed_note = "Uses CPU offloading — slightly slower"
        elif uses_quantization and vram_per_gpu >= 16:
            # With quantization, model shrinks significantly — 16GB+ GPUs can handle it
            viability = "viable"
            speed_note = "Uses quantization + offloading"
        elif total_vram >= model_vram * 0.5 and gpus >= 2:
            viability = "doubtful"
            speed_note = "Tight — may require sharding or aggressive offloading"
        else:
            continue  # Not viable

        # Estimate speed relative to recommended instance
        if instance_type == recommended:
            viability = "recommended"
            speed_note = "Recommended by model catalog"

        # Speed estimate based on GPU generation and count
        cc = specs.get("compute_capability", 7.0)
        if cc >= 8.9:
            speed_tier = "Fast"
        elif cc >= 8.0:
            speed_tier = "Good"
        elif cc >= 7.5:
            speed_tier = "Moderate"
        else:
            speed_tier = "Slow"

        if gpus > 1 and total_vram >= model_vram:
            speed_note = f"{speed_tier} — {gpus}× {specs['gpu_type']} ({total_vram}GB total)"
        elif gpus == 1:
            speed_note = f"{speed_tier} — {specs['gpu_type']} ({vram_per_gpu}GB)"
        else:
            speed_note = f"{speed_tier} — {gpus}× {specs['gpu_type']}"

        opt = {
            "instance_type": instance_type,
            "gpus": gpus,
            "gpu_type": specs.get("gpu_type", ""),
            "total_vram_gb": total_vram,
            "vram_per_gpu_gb": vram_per_gpu,
            "ram_gb": specs.get("ram_gb", 0),
            "cost_per_hour_usd": cost,
            "quota": quota,
            "quota_in_use": in_use,
            "quota_available": available,
            "viability": viability,
            "speed_note": speed_note,
            "is_recommended": instance_type == recommended,
            "needs_quota": needs_quota,
        }
        if needs_quota:
            opt["quota_code"] = quota_codes.get(instance_type, "")
            if quota > 0 and in_use >= quota:
                opt["quota_reason"] = "all_in_use"
            else:
                opt["quota_reason"] = "no_quota"
            req_info = quota_requests.get(instance_type)
            if req_info:
                opt["quota_request"] = req_info
        options.append(opt)

    # Sort: available first, then recommended, then viability, then cost
    viability_order = {"recommended": 0, "viable": 1, "doubtful": 2}
    options.sort(key=lambda o: (
        1 if o["needs_quota"] else 0,
        0 if o["is_recommended"] else 1,
        viability_order.get(o["viability"], 9),
        o["cost_per_hour_usd"],
    ))

    return {
        "model_key": model_key,
        "model_label": model.get("label", model_key),
        "min_vram_gb": model_vram,
        "recommended_instance": recommended,
        "region": region,
        "options": options,
    }


# ── Quota Request ─────────────────────────────────────────────────────────

class QuotaRequestBody(BaseModel):
    instance_type: str
    quota_code: str
    desired_value: int = 1


@router.post("/quota-request")
async def request_quota_increase(body: QuotaRequestBody):
    """Submit a service quota increase request for a SageMaker endpoint instance type."""
    import boto3
    from backend.services.sagemaker_deployer import _get_region
    region = _get_region()

    sq = boto3.client("service-quotas", region_name=region)

    # First check current quota — it may already be sufficient
    try:
        current = sq.get_service_quota(ServiceCode="sagemaker", QuotaCode=body.quota_code)
        current_val = int(current["Quota"].get("Value", 0))
        if current_val >= body.desired_value:
            return {
                "status": "already_sufficient",
                "message": f"Quota for {body.instance_type} is already {current_val} (requested {body.desired_value}).",
                "current_quota": current_val,
            }
    except Exception:
        pass

    # Check for existing pending request
    try:
        history_paginator = sq.get_paginator("list_requested_service_quota_change_history_by_quota")
        for page in history_paginator.paginate(ServiceCode="sagemaker", QuotaCode=body.quota_code):
            for req in page.get("RequestedQuotas", []):
                if req.get("Status") in ("PENDING", "CASE_OPENED"):
                    return {
                        "status": "already_pending",
                        "message": f"A quota request for {body.instance_type} is already pending (Case: {req.get('CaseId', 'N/A')}).",
                        "case_id": req.get("CaseId"),
                        "request_id": req.get("Id"),
                        "created": str(req.get("Created", "")),
                    }
    except Exception:
        pass

    # Submit the request
    try:
        resp = sq.request_service_quota_increase(
            ServiceCode="sagemaker",
            QuotaCode=body.quota_code,
            DesiredValue=float(body.desired_value),
        )
        req = resp.get("RequestedQuota", {})
        logger.info("Quota increase requested: %s → %d for %s (case: %s)",
                     body.instance_type, body.desired_value,
                     req.get("Id", "?"), req.get("CaseId", "auto"))
        return {
            "status": "submitted",
            "message": f"Quota increase requested for {body.instance_type} in {region}. AWS typically processes GPU requests within 1-3 business days.",
            "request_id": req.get("Id", ""),
            "case_id": req.get("CaseId"),
            "desired_value": body.desired_value,
            "region": region,
        }
    except Exception as e:
        logger.error("Quota request failed for %s: %s", body.instance_type, e)
        raise HTTPException(502, detail=f"Failed to submit quota request: {e}")


# ── Deploy ────────────────────────────────────────────────────────────────

class DeployRequest(BaseModel):
    model_key: str
    endpoint_type: str = "async"  # "async" or "realtime"
    instance_type: str | None = None
    hf_token: str | None = None  # For gated models — stored encrypted in Secrets Manager
    build_only: bool = False  # Build mode: cache weights after load, don't expect inference
    license_accepted: bool = False  # User confirmed model license agreement before deploying
    # For models with selectable texturing pipelines (e.g. TripoSG): the backend
    # the user chose in the deploy dialog ("trellis2" | "hunyuan"; default
    # trellis2). Validated against the catalog's texture_backends; some (Hunyuan,
    # non-commercial) require an explicit attestation. (MVPainter removed
    # 2026-06-25 — license-tainted + dominated.)
    texture_backend: str | None = None
    texture_license_accepted: bool = False  # Attestation for a non-commercial texture backend


_deploy_status: dict = {}  # model_key → {"stage": str, "progress": str, "error": str}
_failed_teardown_scheduled: set = set()  # endpoint_names we've already auto-torn-down


def _schedule_failed_teardown(deployed_key: str, endpoint_name: str, reason: str):
    """Auto-tear-down a Failed endpoint, once, in the background.

    A Failed SageMaker endpoint (e.g. InsufficientInstanceCapacity) can't serve
    and can't be recovered — the only action is to delete it. Rather than leave
    it cluttering the UI with no clear path, we clean it up automatically:
    teardown_endpoint (endpoint/config/model + auto-scaling + registry) then
    clear stale deploy-progress, so the model returns to a clean deployable
    state. Idempotent (guarded by _failed_teardown_scheduled) and best-effort —
    runs off-thread so it never blocks the catalog response.
    """
    if endpoint_name in _failed_teardown_scheduled:
        return
    _failed_teardown_scheduled.add(endpoint_name)
    logger.warning("Auto-tearing-down FAILED endpoint %s (reason: %s)", endpoint_name, reason or "unknown")

    def _run():
        try:
            from backend.services.sagemaker_deployer import teardown_endpoint
            teardown_endpoint(deployed_key, delete_s3=False)
        except Exception as exc:
            logger.warning("Auto-teardown of failed %s hit an error: %s", endpoint_name, exc)
        try:
            _unregister_custom_model(deployed_key)
        except Exception:
            pass
        _clear_deploy_status(deployed_key)
        # Allow a future re-detection if somehow the endpoint reappears.
        _failed_teardown_scheduled.discard(endpoint_name)

    import threading
    threading.Thread(target=_run, daemon=True, name=f"failed-teardown-{endpoint_name}").start()


def _clear_deploy_status(model_key: str):
    """Drop in-memory deploy-progress for a model (and its catalog base).

    Called on teardown and on terminal failure so the Custom Models list stops
    reporting a stale "deploying…" state. Deploys may key _deploy_status by the
    catalog key OR the hash-suffixed instance key, so clear both: the exact key
    and every entry whose catalog base matches it.
    """
    from backend.services.custom_models import get_catalog
    try:
        catalog = get_catalog()
    except Exception:
        catalog = {}
    # Catalog base of the given key (strip a trailing hash segment if the exact
    # key isn't itself a catalog key, e.g. hunyuan_image_3_0_bf16_9c7c → base).
    base = model_key
    if model_key not in catalog:
        for ck in catalog:
            if model_key == ck or model_key.startswith(ck + "_"):
                base = ck
                break
    for k in list(_deploy_status.keys()):
        if k == model_key or k == base or k.startswith(base + "_"):
            _deploy_status.pop(k, None)


@router.post("/deploy")
async def deploy_model(body: DeployRequest):
    """Start deploying a model in a background thread.

    Returns immediately with a status. Frontend polls /deploy-status/{key} for progress.

    For HuggingFace models: uploads only the inference handler to S3, then creates
    the Amazon SageMaker endpoint. The container pulls model weights directly from
    HuggingFace at startup (no local download of multi-GB weights).

    For gated models: a single shared HF token is stored encrypted in AWS
    Secrets Manager (not as a plain-text env var). If a token already exists
    from a previous deployment, it's reused automatically — no need to ask
    the user again. If the token fails, the user is prompted for a new one.

    For non-HuggingFace models: downloads weights locally, uploads to S3,
    then creates the endpoint.
    """
    from backend.services.custom_models import get_catalog_model
    from backend.services.sagemaker_deployer import has_hf_token, get_deployment_s3_bucket

    model = get_catalog_model(body.model_key)
    if not model:
        raise HTTPException(404, detail=f"Unknown model: {body.model_key}")

    # Guardrail: a deployment S3 bucket is REQUIRED — the inference handler
    # (model.tar.gz) is uploaded there and SageMaker's ModelDataUrl points at it.
    # The frontend disables Deploy without a bucket; this rejects a direct API
    # call cleanly (fail fast) instead of erroring deep inside the deploy thread.
    if not get_deployment_s3_bucket():
        raise HTTPException(400, detail=(
            "No S3 bucket configured. Set an S3 bucket in Model Settings → "
            "Video Studio before deploying custom models."
        ))

    # Enforce license agreement acceptance before deployment
    license_info = model.get("license_agreement", {})
    if license_info.get("required") and not body.license_accepted:
        raise HTTPException(400, detail="License agreement must be accepted before deploying this model.")

    # Record license acceptance in user registry
    if body.license_accepted:
        _record_license_acceptance(body.model_key, license_info.get("license_name", model.get("license", "")))

    # ── Texture backend selection (e.g. TripoSG: trellis2 vs hunyuan) ──────────
    # Validate the chosen backend against the catalog, enforce its instance
    # baseline, and require attestation for a non-commercial backend (Hunyuan).
    tex_meta = model.get("texture_backends") or {}
    tex_options = tex_meta.get("options") or {}
    chosen_tb = body.texture_backend or tex_meta.get("default")
    if tex_options and chosen_tb:
        if chosen_tb not in tex_options:
            raise HTTPException(400, detail=f"Unknown texture backend: {chosen_tb}")
        tb = tex_options[chosen_tb]
        tb_lic = tb.get("license", {})
        # Non-commercial backend → require the explicit attestation checkbox.
        if tb_lic.get("attestation_required") and not body.texture_license_accepted:
            raise HTTPException(400, detail={
                "error": "texture_license_required",
                "message": (
                    f"{tb.get('label', chosen_tb)} uses a {tb_lic.get('name','non-commercial')} license. "
                    "Confirm you hold a valid license or will use it within its non-commercial terms."
                ),
                "license_name": tb_lic.get("name", ""),
                "license_url": tb_lic.get("url", ""),
            })
        # Enforce the backend's instance baseline (per the catalog allowed_instances).
        allowed = tb.get("allowed_instances") or model.get("requirements", {}).get("allowed_instances", [])
        if body.instance_type and allowed and body.instance_type not in allowed:
            raise HTTPException(400, detail=(
                f"{tb.get('label', chosen_tb)} requires one of: {', '.join(allowed)} "
                f"(got {body.instance_type})."
            ))
        # Default the instance to the backend's recommendation if none given.
        if not body.instance_type and tb.get("recommended_instance"):
            body.instance_type = tb["recommended_instance"]
        if body.texture_license_accepted:
            _record_license_acceptance(
                f"{body.model_key}:{chosen_tb}", tb_lic.get("name", chosen_tb))

    # Smart token flow: only ask for token if gated AND no token stored yet
    if model.get("requires_hf_auth") and not body.hf_token and not has_hf_token():
        raise HTTPException(400, detail={
            "error": "hf_auth_required",
            "message": "This model requires HuggingFace authentication.",
            "license_url": model.get("hf_license_url", ""),
            "instructions": (
                "1. Visit the license URL and accept the terms\n"
                "2. Go to huggingface.co/settings/tokens → create a Read-only token\n"
                "3. Provide the token in the deployment dialog\n"
                "A Read-only token is sufficient. Your token is stored encrypted in AWS Secrets Manager\n"
                "in your account and reused for all gated models. You can remove it anytime."
            ),
        })

    # Run deployment in background thread — return immediately
    import threading

    def _run_deploy():
        key = body.model_key
        source_type = model.get("source", {}).get("type", "")

        try:
            if source_type == "huggingface":
                # ── HuggingFace direct pull: no local download ──────────────
                # Upload only the inference handler to S3 (a few KB).
                # The Amazon SageMaker container will pull model weights
                # directly from HuggingFace at startup via HF_MODEL_ID.
                from backend.services.sagemaker_deployer import upload_handler_to_s3, deploy_endpoint

                _deploy_status[key] = {
                    "stage": "preparing",
                    "progress": "Uploading inference handler to S3...",
                    "error": "",
                }
                upload_handler_to_s3(key)

                _deploy_status[key] = {
                    "stage": "deploying",
                    "progress": "Creating Amazon SageMaker endpoint (container will pull model from HuggingFace)...",
                    "error": "",
                }
                deployment = deploy_endpoint(
                    key,
                    endpoint_type=body.endpoint_type,
                    instance_type=body.instance_type,
                    hf_token=body.hf_token,  # Stored in Secrets Manager, not plain-text env var
                    build_only=body.build_only,
                    texture_backend=chosen_tb,  # user's deploy-dialog choice (None if N/A)
                )

                _register_custom_model(key, model, deployment)
                _deploy_status[key] = {
                    "stage": "complete",
                    "progress": (
                        "Endpoint created — container is pulling model from HuggingFace and starting up. "
                        "This typically takes 5-15 min depending on model size."
                    ),
                    "error": "",
                }
                try:
                    from backend.services.telemetry import track_custom_model_deploy, track_first_custom_deploy
                    track_custom_model_deploy(model=key, endpoint_type=body.endpoint_type,
                                             instance=body.instance_type or "")
                    track_first_custom_deploy(model=key, instance=body.instance_type or "")
                except Exception:
                    pass

            else:
                # ── Non-HuggingFace: download locally → upload to S3 ────────
                from backend.services.sagemaker_deployer import download_model, upload_to_s3, deploy_endpoint
                import shutil

                _deploy_status[key] = {
                    "stage": "downloading",
                    "progress": f"Downloading {model['label']} weights...",
                    "error": "",
                }

                def _update_progress(msg):
                    _deploy_status[key]["progress"] = msg

                local_dir = download_model(key, progress_callback=_update_progress)
                try:
                    _deploy_status[key] = {"stage": "uploading", "progress": "Uploading to S3...", "error": ""}
                    upload_to_s3(local_dir, key, progress_callback=_update_progress)

                    _deploy_status[key] = {
                        "stage": "deploying",
                        "progress": "Creating Amazon SageMaker endpoint...",
                        "error": "",
                    }
                    deployment = deploy_endpoint(key, endpoint_type=body.endpoint_type, instance_type=body.instance_type, texture_backend=chosen_tb)

                    _register_custom_model(key, model, deployment)
                    _deploy_status[key] = {
                        "stage": "complete",
                        "progress": "Endpoint created — waiting for it to become active (5-10 min).",
                        "error": "",
                    }
                    try:
                        from backend.services.telemetry import track_custom_model_deploy
                        track_custom_model_deploy(model=key, endpoint_type=body.endpoint_type,
                                                  instance=body.instance_type or "")
                    except Exception:
                        pass
                finally:
                    shutil.rmtree(local_dir, ignore_errors=True)

        except Exception as exc:
            logger.exception("Custom model deployment failed: %s", key)
            error_msg = str(exc)
            # Provide user-friendly guidance for common errors
            if "403" in error_msg or "not in the authorized list" in error_msg:
                license_url = model.get("hf_license_url", f"https://huggingface.co/{model.get('source', {}).get('repo_id', '')}")
                error_msg = (
                    f"Access denied. You need to accept the model's license on HuggingFace first.\n\n"
                    f"1. Visit {license_url}\n"
                    f"2. Click 'Accept' on the license agreement\n"
                    f"3. Come back and try deploying again\n\n"
                    f"If you already accepted the license, your stored token may be invalid or expired. "
                    f"Try deploying again with a fresh token."
                )
            elif "401" in error_msg or "Unauthorized" in error_msg:
                error_msg = (
                    "Invalid or expired HuggingFace token. "
                    "Please deploy again with a fresh token from huggingface.co/settings/tokens."
                )
            elif "404" in error_msg:
                error_msg = "Model repository not found. Please verify the model URL is correct."
            elif "secretsmanager" in error_msg.lower() or "AccessDeniedException" in error_msg:
                error_msg = (
                    "Could not store HuggingFace token in AWS Secrets Manager. "
                    "Ensure your IAM role has secretsmanager:CreateSecret and secretsmanager:PutSecretValue permissions."
                )
            _deploy_status[key] = {"stage": "failed", "progress": "", "error": error_msg}

    thread = threading.Thread(target=_run_deploy, daemon=True)
    thread.start()

    # Record a "deploy started" notice so the deployment lifecycle
    # (started → ready|failed → removed) has a complete, durable history —
    # informational, so it doesn't nag; the ready/failed notices carry the weight.
    try:
        from backend.services.notices import add_notice
        inst = f" on {body.instance_type}" if body.instance_type else ""
        add_notice(
            kind="deploy_started",
            title="Deployment started",
            message=(f"{model['label']}{inst} is deploying — the container pulls the model "
                     f"from HuggingFace and loads it (typically 5-15 min). You'll be notified "
                     f"when it's ready."),
            level="info",
            dedup_key=f"deploy_started:{body.model_key}",
        )
    except Exception:
        pass

    return {
        "status": "started",
        "model_key": body.model_key,
        "label": model["label"],
        "message": "Deployment started in background. Check status in Custom Models tab.",
    }


@router.get("/deploy-status/{model_key}")
async def get_deploy_progress(model_key: str):
    """Get the current deployment progress for a model being deployed."""
    status = _deploy_status.get(model_key, {"stage": "unknown", "progress": "", "error": ""})
    return status


# ── Status & Management ───────────────────────────────────────────────────

@router.get("/status/{model_key}")
def check_deployment_status(model_key: str):
    """Check the deployment status of a custom model on Amazon SageMaker."""
    from backend.services.sagemaker_deployer import check_endpoint_status
    endpoint_name = f"artsmoker-{model_key.replace('_', '-')}"
    return check_endpoint_status(endpoint_name)


# ── HuggingFace Token Management ─────────────────────────────────────────

@router.get("/hf-token-status")
def check_hf_token_status():
    """Check if a HuggingFace token is stored in Secrets Manager."""
    from backend.services.sagemaker_deployer import has_hf_token, get_hf_token_arn
    stored = has_hf_token()
    return {"stored": stored, "arn": get_hf_token_arn() if stored else None}


@router.get("/s3-bucket-status")
def check_s3_bucket_status(verify: bool = False):
    """Report whether the custom-model S3 bucket is configured (and optionally
    reachable), PLUS whether it's locked (has dependencies). Drives the Custom
    Models setter's current-state + the Image Studio / 3D preflight.

    `verify=false` (default) = cheap presence check (no head_bucket).
    `verify=true` = also head_bucket (used when the user explicitly checks).

    `locked=True` means a custom endpoint is deployed / a job is in-flight /
    ArtSmoker data exists in the bucket — SageMaker has baked this bucket into
    immutable endpoint config, so it must NOT be changed. The setter enforces
    this server-side; the UI shows a read-only record.
    """
    from backend.services.sagemaker_deployer import check_deployment_bucket, get_bucket_dependencies
    result = check_deployment_bucket(require_access=verify)
    if result.get("bucket"):
        deps = get_bucket_dependencies()
        result["locked"] = deps["locked"]
        result["lock_reasons"] = deps["reasons"]
    else:
        result["locked"] = False
        result["lock_reasons"] = []
    return result


class UpdateS3BucketRequest(BaseModel):
    s3_bucket: str


@router.post("/s3-bucket")
async def set_s3_bucket(body: UpdateS3BucketRequest):
    """Set the custom-model S3 bucket from Model Settings → Custom Models.

    Writes the SAME `video_settings.s3_bucket` that get_deployment_s3_bucket()
    reads (custom models and Video Studio share one bucket by design), and
    validates it (head_bucket + read/write test) via the shared video-settings
    update path — so there is one validated write path, not two.

    REFUSES to change the bucket once it's LOCKED (a custom endpoint is deployed,
    a job is in-flight, or ArtSmoker data exists in the current bucket). Switching
    then would silently break live endpoints — SageMaker baked the old bucket into
    their immutable ModelDataUrl / S3OutputPath at deploy time. Setting the SAME
    value is always allowed (idempotent no-op).
    """
    from backend.routers.admin import update_video_settings_endpoint, VideoSettingsUpdate
    from backend.services.sagemaker_deployer import (
        invalidate_bucket_access_cache, get_deployment_s3_bucket, get_bucket_dependencies,
    )

    name = (body.s3_bucket or "").strip()
    if not name:
        raise HTTPException(400, detail="Bucket name cannot be empty")

    current = get_deployment_s3_bucket()
    if name != current and current:
        deps = get_bucket_dependencies()
        if deps["locked"]:
            raise HTTPException(
                409,
                detail=(
                    f"The S3 bucket can't be changed: {', '.join(deps['reasons'])} depend on "
                    f"\"{current}\". SageMaker permanently binds deployed endpoints to their "
                    f"bucket, so switching would break them. Tear down deployed custom models "
                    f"(and let in-flight jobs finish) before changing the bucket."
                ),
            )

    # Reuse the video-settings update path (validates then persists). It raises
    # HTTPException(400, ...) with a clear message on NoSuchBucket / access errors.
    result = await update_video_settings_endpoint(VideoSettingsUpdate(s3_bucket=name))
    invalidate_bucket_access_cache()  # freshly-validated bucket — drop stale probe
    return {"status": "saved", "s3_bucket": name, "video_settings": result}


@router.get("/gated-access/{model_key}")
def check_gated_access(model_key: str):
    """Pre-check whether the stored HF token can access every repo this model needs.

    Drives the deploy dialog's gated-repo UX: instead of a bare "gated · accept on
    HF" badge, the frontend can show, per repo, a ✓ (accessible) or ✗ with the exact
    next step (accept the gate on HF, or add a token). Probes the SAME repos the
    deploy will pull — the model's source plus any gated dependencies (e.g.
    TRELLIS.2 → facebook/dinov3). Uses the shared stored token; never returns it.
    """
    from backend.services.custom_models import get_catalog_model
    from backend.services.sagemaker_deployer import _retrieve_hf_token, has_hf_token

    model = get_catalog_model(model_key)
    if not model:
        raise HTTPException(404, detail=f"Unknown model: {model_key}")

    token = _retrieve_hf_token() if has_hf_token() else None
    result = _check_gated_access(model, token)
    result["model_key"] = model_key
    result["requires_hf_auth"] = bool(model.get("requires_hf_auth"))
    # If gated repos exist but no token is stored, surface the token step first.
    if not result["has_token"] and any(r["gated"] for r in result["repos"]):
        result["needs_token"] = True
    return result


class UpdateHfTokenRequest(BaseModel):
    hf_token: str


@router.post("/hf-token")
async def update_hf_token(body: UpdateHfTokenRequest):
    """Store or update the shared HuggingFace token.

    One token is shared across all gated models. Stored encrypted in
    AWS Secrets Manager. Existing deployed models will use the new token
    on their next cold start.
    """
    from backend.services.sagemaker_deployer import store_hf_token
    if not body.hf_token.strip():
        raise HTTPException(400, detail="Token cannot be empty")
    arn = store_hf_token(body.hf_token.strip())
    return {"status": "stored", "arn": arn}


@router.delete("/hf-token")
async def remove_hf_token():
    """Delete the shared HuggingFace token from Secrets Manager.

    Warning: gated models will fail on next cold start without a token.
    """
    from backend.services.sagemaker_deployer import delete_hf_token
    deleted = delete_hf_token()
    return {"status": "deleted" if deleted else "not_found"}


@router.delete("/teardown/{model_key}")
async def teardown_model(model_key: str, delete_s3: bool = False):
    """Delete a deployed custom model endpoint.

    Optionally deletes S3 artifacts (handler code). The model can be
    redeployed later. The shared HF token is NOT deleted (other models may need it).
    """
    from backend.services.sagemaker_deployer import teardown_endpoint

    result = teardown_endpoint(model_key, delete_s3=delete_s3)

    # Remove from model registry
    _unregister_custom_model(model_key)

    # Clear any in-memory deploy-progress for this model. Without this, a stale
    # "deploying / container is pulling…" entry survives teardown and keeps the
    # Custom Models UI showing the model as mid-deploy (no Deploy button), even
    # after the endpoint + registry entry are gone — persisting across browser
    # refreshes since it's server-side state. Clear the exact key AND its catalog
    # base (hash-suffixed instance key → catalog key) so the model resets to a
    # clean, deployable state.
    _clear_deploy_status(model_key)

    try:
        from backend.services.telemetry import track_custom_model_teardown
        track_custom_model_teardown(model=model_key)
    except Exception:
        pass

    # Record a "removed" notice for lifecycle history (user-initiated teardown;
    # the auto-teardown-on-failure path records its own failure notice instead).
    try:
        from backend.services.notices import add_notice
        from backend.services.custom_models import get_catalog_model
        # Resolve a friendly label if possible; the registry entry is already gone
        # by now (unregistered above), so fall back to the key.
        friendly = model_key
        try:
            cm = get_catalog_model(model_key) or get_catalog_model("_".join(model_key.rsplit("_", 1)[:-1]))
            if cm and cm.get("label"):
                friendly = cm["label"]
        except Exception:
            pass
        add_notice(
            kind="deploy_removed",
            title="Model removed",
            message=f"{friendly} was torn down. You can redeploy it any time from Model Settings → Custom Models.",
            level="info",
        )
    except Exception:
        pass

    return {"status": "deleted", **result}


@router.post("/keep-warm/{model_key}")
async def keep_warm(model_key: str, hours: float = 8.0):
    """Pin a deployed endpoint warm (MinCapacity=1) for `hours`, then auto-revert.

    Dev-mode only. Keeps one hard-won instance running through dev iteration
    instead of losing it to scale-in between test jobs. After the window
    elapses (default 8 hours) the endpoint auto-reverts to normal
    scale-to-zero autoscaling. A persisted marker makes the revert survive a
    server restart, so the instance is always eventually released.

    Explicit call → starts a fresh window. Use /reset-warm to revert early.
    """
    from backend.services.auto_update import is_dev_mode
    if not is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Keep-warm is a dev-only feature (set ARTSMOKER_DEV_MODE).",
        )
    from backend.services.sagemaker_deployer import set_keep_warm
    try:
        return set_keep_warm(model_key, hours=hours, extend_window=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset-warm/{model_key}")
async def reset_warm(model_key: str, cooldown_seconds: int | None = None):
    """Revert a kept-warm endpoint to normal scale-to-zero autoscaling now.

    Dev-mode only. Sets MinCapacity=0 so the idle instance scales in (stops
    billing), cancels the pending auto-revert timer, and clears the warm
    marker. `cooldown_seconds` overrides the scale-in cooldown to restore;
    defaults to the value recorded when keep-warm was set.
    """
    from backend.services.auto_update import is_dev_mode
    if not is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Reset-warm is a dev-only feature (set ARTSMOKER_DEV_MODE).",
        )
    from backend.services.sagemaker_deployer import reset_warm_mode
    try:
        return reset_warm_mode(model_key, cooldown_seconds=cooldown_seconds)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/warm-status/{model_key}")
async def warm_status(model_key: str):
    """Report keep-warm state for an endpoint (dev-mode only)."""
    from backend.services.auto_update import is_dev_mode
    if not is_dev_mode():
        return {"dev_mode": False, "warm": False}
    from backend.services.sagemaker_deployer import resolve_endpoint_name
    from backend.services.model_registry import get_warm_markers
    ep = resolve_endpoint_name(model_key)
    marker = get_warm_markers().get(ep, {}) if ep else {}
    return {"dev_mode": True, "warm": bool(marker), "endpoint_name": ep, **marker}


@router.post("/dev-overlay/{model_key}")
async def push_overlay(model_key: str):
    """Push the current handler + bundled packages as a hot-reload overlay.

    Dev-mode only. Packages inference.py and the model's bundled packages and
    stages them in S3; the warm endpoint applies them on the next inference —
    no redeploy, no scale-in. Model-agnostic.
    """
    from backend.services.auto_update import is_dev_mode
    if not is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Hot-reload overlay is a dev-only feature (set ARTSMOKER_DEV_MODE).",
        )
    from backend.services.sagemaker_deployer import push_dev_overlay
    try:
        return push_dev_overlay(model_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/dev-overlay/{model_key}")
async def remove_overlay(model_key: str):
    """Remove a model's hot-reload overlay; the endpoint reverts to deployed code."""
    from backend.services.auto_update import is_dev_mode
    if not is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Hot-reload overlay is a dev-only feature (set ARTSMOKER_DEV_MODE).",
        )
    from backend.services.sagemaker_deployer import clear_dev_overlay
    return clear_dev_overlay(model_key)


@router.get("/cache/{model_key}")
async def check_cache(model_key: str):
    """Check if a model has cached weights in S3 (from a previous successful load)."""
    from backend.services.sagemaker_deployer import check_model_cache_exists
    return check_model_cache_exists(model_key)


@router.delete("/cache/{model_key}")
async def invalidate_cache(model_key: str):
    """Delete cached model weights, forcing fresh download + quantization on next deploy."""
    from backend.services.sagemaker_deployer import invalidate_model_cache
    return invalidate_model_cache(model_key)


@router.post("/update-handler/{model_key}")
def update_handler(model_key: str):
    """Update a deployed endpoint's handler code and config in-place.

    Does NOT teardown — does a blue-green config swap. New instance gets
    the latest inference.py, env vars, and S3 bucket paths. Preserves
    endpoint name and auto-scaling.
    """
    from backend.services.sagemaker_deployer import update_endpoint_config
    try:
        result = update_endpoint_config(model_key)
        return result
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(502, detail=f"Update failed: {e}")


class RedeployRequest(BaseModel):
    endpoint_type: str = "async"
    instance_type: str | None = None
    hf_token: str | None = None  # For gated models


@router.post("/redeploy/{model_key}")
async def redeploy_model(model_key: str, body: RedeployRequest):
    """Tear down and redeploy a custom model.

    Tears down existing endpoint (including Secrets Manager token),
    then creates a fresh deployment.
    """
    from backend.services.sagemaker_deployer import teardown_endpoint, get_deployment_s3_bucket

    # Guardrail first — a redeploy without a bucket would tear down the existing
    # endpoint and then fail to redeploy. Reject before touching anything.
    if not get_deployment_s3_bucket():
        raise HTTPException(400, detail=(
            "No S3 bucket configured. Set an S3 bucket in Model Settings → "
            "Video Studio before redeploying custom models."
        ))

    # Teardown existing
    teardown_endpoint(model_key, delete_s3=True)

    # Re-deploy (reuse the deploy endpoint logic)
    deploy_body = DeployRequest(
        model_key=model_key,
        endpoint_type=body.endpoint_type,
        instance_type=body.instance_type,
        hf_token=body.hf_token,
    )
    return await deploy_model(deploy_body)


# ── User-Added Models (Extensibility) ─────────────────────────────────────

class DetectRequest(BaseModel):
    repo_url: str           # HuggingFace URL or repo ID
    hf_token: str | None = None  # For gated repos (transient)


@router.post("/detect")
async def detect_model(body: DetectRequest):
    """Auto-detect model configuration from a HuggingFace repo.

    Inspects repo metadata (config.json, model_index.json, README)
    without downloading weights. Returns a pre-filled catalog entry
    for the user to review before adding.

    hf_token is used for this API call only and NOT stored.
    """
    from backend.services.model_detector import detect_from_hf_repo

    # Normalize URL to repo ID
    repo_id = body.repo_url.strip()
    repo_id = repo_id.rstrip("/")
    if "huggingface.co/" in repo_id:
        repo_id = repo_id.split("huggingface.co/")[-1]
    if repo_id.startswith("https://"):
        repo_id = repo_id.replace("https://", "")

    try:
        entry = detect_from_hf_repo(repo_id, hf_token=body.hf_token)
        return {"status": "detected", "repo_id": repo_id, "entry": entry}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        logger.exception("Model detection failed for %s", repo_id)
        raise HTTPException(502, detail=f"Detection failed: {e}")


class AddModelRequest(BaseModel):
    key: str                # Unique catalog key (e.g., "my_custom_sdxl")
    entry: dict             # Full catalog entry (from detect + user edits)


@router.post("/add")
async def add_user_model(body: AddModelRequest):
    """Add a user-defined model to the custom catalog.

    Saves to custom_models.user.json (gitignored) — survives code updates.
    The model then appears in the Custom Models tab and can be deployed.
    """
    key = body.key.strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        raise HTTPException(400, detail="Model key is required")

    # Validate required fields
    entry = body.entry
    required = ["label", "category", "source", "invoke"]
    missing = [f for f in required if f not in entry]
    if missing:
        raise HTTPException(400, detail=f"Missing required fields: {missing}")

    # Save to user catalog file
    _save_user_model(key, entry)

    return {"status": "added", "key": key, "label": entry.get("label", key)}


@router.delete("/remove-user-model/{model_key}")
async def remove_user_model(model_key: str):
    """Remove a user-added model from the catalog.

    Only removes from the user catalog (custom_models.user.json).
    Built-in catalog models cannot be removed.
    """
    from backend.services.custom_models import get_catalog
    if model_key in get_catalog():
        raise HTTPException(400, detail="Cannot remove built-in catalog models. Use teardown to remove the deployment.")

    removed = _remove_user_model(model_key)
    if not removed:
        raise HTTPException(404, detail=f"User model '{model_key}' not found")
    return {"status": "removed", "key": model_key}


def _get_user_catalog_path():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent / "custom_models.user.json"


def _load_user_catalog() -> dict:
    import json
    path = _get_user_catalog_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save_user_model(key: str, entry: dict):
    import json
    from datetime import datetime, timezone
    catalog = _load_user_catalog()
    catalog[key] = entry
    catalog["_last_updated"] = datetime.now(timezone.utc).isoformat()
    path = _get_user_catalog_path()
    path.write_text(json.dumps(catalog, indent=2, default=str))
    logger.info("Saved user model '%s' to %s", key, path)


def _remove_user_model(key: str) -> bool:
    import json
    catalog = _load_user_catalog()
    if key in catalog:
        del catalog[key]
        path = _get_user_catalog_path()
        path.write_text(json.dumps(catalog, indent=2, default=str))
        return True
    return False


# ── Registry Integration ──────────────────────────────────────────────────

def _register_custom_model(model_key: str, catalog_entry: dict, deployment: dict):
    """Register a deployed custom model in ArtSmoker's model registry.

    This makes the model appear in the appropriate studio dropdowns.
    Uses a unique registry key derived from the endpoint name (includes instance type),
    so multiple deployments of the same model on different hardware coexist.
    """
    from backend.services.model_registry import get_registry, _save

    registry = get_registry()
    category = catalog_entry["category"]

    invoke = catalog_entry.get("invoke", {})

    from backend.services.sagemaker_deployer import _get_region
    deploy_region = _get_region()

    # Unique registry key: use endpoint name (includes instance suffix)
    # e.g., "artsmoker-flux2-dev-g6e-2xlarge" → "flux2_dev_g6e_2xlarge"
    ep_name = deployment.get("endpoint_name", "")
    registry_key = ep_name.replace("artsmoker-", "").replace("-", "_") if ep_name else model_key

    # Label includes compact deploy timestamp for disambiguation.
    # Multiple deploys of the same model get distinct, user-friendly labels.
    # e.g., "FLUX.2 [dev] (16Apr 12:29)"
    from datetime import datetime
    deploy_ts = datetime.now().strftime("%-d%b %H:%M")
    label = f"{catalog_entry['label']} ({deploy_ts})"

    entry = {
        "label": label,
        "model_id": f"sagemaker:{deployment['endpoint_name']}",
        "provider": catalog_entry["provider"],
        "region": deploy_region,
        "available_regions": [deploy_region],
        "enabled": True,
        "model_source": "custom_hosted",
        "catalog_key": model_key,
        "format_family": f"sagemaker_{deployment['endpoint_type']}",
        "last_updated": catalog_entry.get("last_updated", ""),
        "deployment": {
            "endpoint_name": deployment["endpoint_name"],
            "endpoint_type": deployment["endpoint_type"],
            "instance_type": deployment["instance_type"],
            "created_at": deployment.get("created_at"),
        },
        "base_price_usd": catalog_entry["pricing"].get("estimated_cost_per_image",
                          catalog_entry["pricing"].get("estimated_cost_per_video", 0)),
        "invoke": invoke,  # Snapshot from catalog at deploy time
    }

    if category == "image_generation":
        # Purpose is catalog-driven so edit models (e.g. Qwen-Image-Edit,
        # model_purpose="image_edit") surface in the Edit tab + reference-guided
        # flow, while generators keep the text_to_image default.
        img_entry = {
            **entry,
            "model_purpose": catalog_entry.get("model_purpose", "text_to_image"),
            "prompt_limit": invoke.get("max_prompt_length", 2048),
            "moderation_strictness": "none",
        }
        if catalog_entry.get("capabilities"):
            img_entry["capabilities"] = catalog_entry["capabilities"]
        registry.setdefault("image_models", {})[registry_key] = img_entry
    elif category in ("post_processing", "3d_generation"):
        registry.setdefault("post_processing", {})[registry_key] = {
            **entry,
            "purpose": model_key,
        }
    elif category == "video_generation":
        registry.setdefault("video_models", {})[registry_key] = entry
    elif category == "utility":
        registry.setdefault("utility_models", {})[registry_key] = entry

    _save()
    logger.info("Registered custom model %s (key=%s) in registry (category=%s)", model_key, registry_key, category)


def _unregister_custom_model(model_key: str):
    """Remove a custom model from the registry (exact key or prefix match)."""
    from backend.services.model_registry import get_registry, _save

    registry = get_registry()
    removed = False

    for section in ("image_models", "video_models", "post_processing", "utility_models"):
        # Exact match
        if model_key in registry.get(section, {}):
            del registry[section][model_key]
            removed = True
        else:
            # Prefix match: catalog key → deployed instance key with hash suffix
            matches = [k for k in registry.get(section, {}) if k.startswith(model_key + "_")]
            for k in matches:
                del registry[section][k]
                removed = True

    if removed:
        _save()
        logger.info("Unregistered custom model %s from registry", model_key)


# Need boto3 for _register_custom_model
import boto3
