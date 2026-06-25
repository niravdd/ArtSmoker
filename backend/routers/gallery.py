"""Gallery router — browse, filter, and serve generated assets."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.models.generation_result import GalleryItem
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gallery", tags=["gallery"])

# Metadata cache — populated during listing, invalidated by post-processing
_meta_cache: dict[str, dict] = {}


def _get_meta(asset_id: str) -> dict | None:
    """Load metadata — always reads from disk for freshness."""
    meta = store.load_generation_metadata(asset_id)
    if meta is not None:
        _meta_cache[asset_id] = meta
    return meta


@router.get("/")
def list_gallery(
    style_id: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List generated assets, newest first, with optional filtering and pagination."""
    try:
        return _list_gallery_impl(style_id, asset_type, limit, offset)
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        logger.error("Gallery list CRASHED: %s\n%s", exc, tb)
        return []


def _list_gallery_impl(style_id, asset_type, limit, offset):
    from backend.services.telemetry import track_gallery_load
    if offset == 0:
        track_gallery_load()
    try:
        asset_ids = store.list_generated_ids()
    except Exception as exc:
        logger.error("Gallery: failed to list IDs: %s", exc)
        return []
    items: list[GalleryItem] = []

    for aid in asset_ids:
        try:
            meta = _get_meta(aid)
            if meta is None:
                continue

            if style_id and meta.get("style_id") != style_id:
                continue
            if asset_type and meta.get("asset_type") != asset_type:
                continue

            svg_url: str | None = None
            svg_file = store.get_generated_file_path(aid, "asset.svg")
            if svg_file is not None:
                svg_url = f"/api/gallery/{aid}/svg"

            created_at_str = meta.get("created_at")
            try:
                created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
                # Normalize to naive UTC (strip timezone) for consistent sorting
                if created_at.tzinfo is not None:
                    created_at = created_at.replace(tzinfo=None)
            except (ValueError, TypeError):
                created_at = datetime.utcnow()

            # Resolve model label: from metadata, or look up from registry
            model_key = meta.get("image_model", "")
            model_label = meta.get("model_label", "")
            if not model_label and model_key:
                from backend.services.model_registry import get_image_model
                reg_model = get_image_model(model_key)
                if reg_model:
                    model_label = reg_model.get("label", model_key)
                else:
                    model_label = model_key.replace("_", " ").title()
                # Backfill to metadata for future loads
                meta["model_label"] = model_label
                try:
                    meta_path = store.generated_asset_dir(aid) / "metadata.json"
                    if meta_path.exists():
                        import json as _json
                        existing = _json.loads(meta_path.read_text())
                        existing["model_label"] = model_label
                        meta_path.write_text(_json.dumps(existing, indent=2, default=str))
                except Exception:
                    pass

            items.append(
                GalleryItem(
                    id=aid,
                    prompt=meta.get("prompt", meta.get("enhanced_prompt", "")),
                    style_id=meta.get("style_id"),
                    asset_type=meta.get("asset_type", ""),
                    image_model=model_key,
                    model_label=model_label,
                    png_url=f"/api/gallery/{aid}/png",
                    svg_url=svg_url,
                    created_at=created_at,
                    async_status=meta.get("async_status"),
                )
            )
        except Exception as exc:
            logger.warning("Gallery: skipping %s: %s", aid, exc)

    # Sort newest first
    items.sort(key=lambda x: x.created_at, reverse=True)

    # Paginate
    total = len(items)
    items = items[offset:offset + limit]

    logger.info(
        "Gallery: %d/%d items (offset=%d, limit=%d, style=%s, type=%s)",
        len(items), total, offset, limit, style_id, asset_type,
    )
    # Return as plain dicts to avoid Pydantic response_model serialization issues
    return [item.model_dump() for item in items]


@router.get("/batch/{batch_id}")
async def get_batch(batch_id: str):
    """Reconstruct a full batch result (options × variations) from a batch_id.

    Returns a structure matching GenerationResult so the frontend can
    reload a previous generation into the ImageStudio view.
    """
    asset_ids = store.list_generated_ids()
    # Collect all variants belonging to this batch
    batch_items: list[dict] = []
    for aid in asset_ids:
        if not aid.startswith(batch_id + "_"):
            continue
        meta = _get_meta(aid)
        if meta and meta.get("batch_id") == batch_id:
            batch_items.append(meta)

    if not batch_items:
        raise HTTPException(404, detail=f"Batch '{batch_id}' not found.")

    # Sort by option_index then variant_index
    batch_items.sort(key=lambda m: (m.get("option_index", 0), m.get("variant_index", 0)))

    # Group into options
    options_map: dict[int, dict] = {}
    for meta in batch_items:
        oi = meta.get("option_index", 0)
        if oi not in options_map:
            options_map[oi] = {
                "option_index": oi,
                "enhanced_prompt": meta.get("enhanced_prompt", ""),
                "variants": [],
            }
        svg_url = f"/api/gallery/{meta['id']}/svg" if meta.get("svg_path") else None
        async_status = meta.get("async_status")
        # Only set png_path if the image actually exists (not pending/failed async)
        has_image = (store.generated_asset_dir(meta["id"]) / "asset.png").exists()
        # Cache-bust: append version number so browser reloads after inpainting/editing
        current_ver = meta.get("current_version", 1)
        cache_bust = f"?v={current_ver}" if current_ver > 1 else ""
        variant = {
            "id": meta["id"],
            "variant_index": meta.get("variant_index", 0),
            "png_path": f"/api/gallery/{meta['id']}/png{cache_bust}" if has_image else "",
            "svg_path": svg_url if has_image else None,
            "png_filename": meta.get("png_filename", f"{meta['id']}.png"),
            "svg_filename": meta.get("svg_filename"),
            "model_used": meta.get("image_model"),
            "model_label": meta.get("model_label"),
        }
        # Carry async job info so frontend shows proper status
        if async_status and async_status != "complete":
            variant["async_job"] = {
                "job_id": meta.get("async_job_id", ""),
                "model_label": meta.get("model_label", ""),
                "status": "failed" if async_status == "failed" else "pending",
            }
        options_map[oi]["variants"].append(variant)

    # Set option status based on variant states
    for oi, opt_data in options_map.items():
        variants = opt_data["variants"]
        has_images = any(v.get("png_path") for v in variants)
        all_failed = all(v.get("async_job", {}).get("status") == "failed" for v in variants if v.get("async_job"))
        if has_images:
            opt_data["status"] = "success"
        elif all_failed and variants:
            opt_data["status"] = "failed"
            opt_data["status_detail"] = "All variations failed or timed out"
        elif any(v.get("async_job") for v in variants):
            opt_data["status"] = "pending"

    options = [options_map[k] for k in sorted(options_map.keys())]

    # Use first item for shared metadata
    first = batch_items[0]
    surviving_total = sum(len(o["variants"]) for o in options)
    # original_num_options/variations are set by delete handler; fall back to
    # num_options/variations (generation-time values stored per variant)
    original_options = (
        first.get("original_num_options")
        or first.get("num_options")
        or len(options)
    )
    original_variations = (
        first.get("original_num_variations")
        or first.get("num_variations")
        or max((len(o["variants"]) for o in options), default=1)
    )
    original_total = original_options * original_variations
    deleted_count = first.get("batch_deleted_count", 0)

    # Detect "All Models" batch and reconstruct model_map
    is_all_models = first.get("all_models", False)
    model_map = None
    if is_all_models:
        model_map = {}
        for opt in options:
            oi = opt["option_index"]
            # Get model from first variant in this option
            if opt["variants"]:
                v_meta = _get_meta(opt["variants"][0]["id"])
                if v_meta:
                    model_map[oi] = v_meta.get("image_model", "")
                    opt["image_model"] = v_meta.get("image_model", "")
                    opt["model_label"] = v_meta.get("model_label", "")
                    opt["enhanced_prompt"] = v_meta.get("enhanced_prompt", opt.get("enhanced_prompt", ""))
                    opt["negative_prompt"] = v_meta.get("negative_prompt", "")

    return {
        "id": batch_id,
        "prompt": first.get("prompt", ""),
        "original_prompt": first.get("original_prompt"),
        "enhanced_prompt": first.get("enhanced_prompt", first.get("refined_prompt", "")),
        "negative_prompt": first.get("negative_prompt"),
        "decomposed_data": first.get("decomposed_data"),
        "recomposed_prompt": first.get("recomposed_prompt"),
        "style_id": first.get("style_id"),
        "style_snapshot": first.get("style_snapshot"),
        "asset_type": first.get("asset_type", ""),
        "image_model": first.get("image_model", ""),
        "model_label": first.get("model_label", ""),
        "all_models": is_all_models,
        "model_map": model_map,
        "width": first.get("width", 1024),
        "height": first.get("height", 1024),
        "remove_background": first.get("remove_background", False),
        "generate_svg": first.get("generate_svg", False),
        "upscale": first.get("upscale", False),
        "num_options": len(options),
        "num_variations": max((len(o["variants"]) for o in options), default=1),
        "original_num_options": original_options,
        "original_num_variations": original_variations,
        "batch_deleted_count": deleted_count,
        "batch_surviving_count": surviving_total,
        "batch_original_total": original_total,
        "options": options,
        "created_at": first.get("created_at"),
    }


class DeleteRequest(BaseModel):
    ids: list[str]


@router.delete("/")
async def delete_assets(body: DeleteRequest):
    """Delete one or more gallery assets permanently.

    For batch-generated assets, updates the remaining siblings' metadata
    to record the deletion context (original batch size and deleted count),
    so the UI can inform the user when reloading a partial batch.
    """
    deleted = []
    not_found = []

    # Group deletions by batch_id so we can update siblings efficiently
    batch_deletions: dict[str, list[str]] = {}

    for asset_id in body.ids:
        meta = _get_meta(asset_id)
        if meta and meta.get("batch_id"):
            bid = meta["batch_id"]
            batch_deletions.setdefault(bid, []).append(asset_id)

        if store.delete_generated_asset(asset_id):
            _meta_cache.pop(asset_id, None)
            deleted.append(asset_id)
            logger.info("Deleted gallery asset: %s", asset_id)
        else:
            not_found.append(asset_id)

    # Update surviving siblings with deletion context
    if batch_deletions:
        all_ids = store.list_generated_ids()
        for bid, del_ids in batch_deletions.items():
            for aid in all_ids:
                if not aid.startswith(bid + "_") or aid in deleted:
                    continue
                sibling_meta = store.load_generation_metadata(aid)
                if not sibling_meta or sibling_meta.get("batch_id") != bid:
                    continue
                # Record how many were deleted from this batch.
                # original_num_options/variations preserve the generation-time values;
                # num_options/variations in metadata are the generation-time counts.
                prev_deleted = sibling_meta.get("batch_deleted_count", 0)
                orig_options = sibling_meta.get("original_num_options") or sibling_meta.get("num_options") or 1
                orig_variations = sibling_meta.get("original_num_variations") or sibling_meta.get("num_variations") or 1
                sibling_meta["batch_deleted_count"] = prev_deleted + len(del_ids)
                sibling_meta["original_num_options"] = orig_options
                sibling_meta["original_num_variations"] = orig_variations
                store.save_generation_metadata(aid, sibling_meta)
                _meta_cache.pop(aid, None)  # Invalidate cache

    return {"deleted": deleted, "not_found": not_found}


@router.get("/{asset_id}")
async def get_asset_metadata(asset_id: str):
    """Get the full metadata dictionary for a generated asset."""
    meta = _get_meta(asset_id)
    if meta is None:
        raise HTTPException(404, detail=f"Asset '{asset_id}' not found.")
    return meta


@router.get("/{asset_id}/version/{version}")
async def get_asset_version(asset_id: str, version: int):
    """Serve a specific PNG version of an asset."""
    filename = f"asset_v{version}.png"
    path = store.get_generated_file_path(asset_id, filename)
    if path is None:
        raise HTTPException(404, detail=f"Version {version} not found for asset '{asset_id}'.")
    return FileResponse(path, media_type="image/png", filename=f"{asset_id}_v{version}.png")


@router.get("/{asset_id}/version-svg/{version}")
async def get_asset_version_svg(asset_id: str, version: int):
    """Serve a specific SVG version of an asset."""
    filename = f"asset_v{version}.svg"
    path = store.get_generated_file_path(asset_id, filename)
    if path is None:
        raise HTTPException(404, detail=f"SVG version {version} not found for asset '{asset_id}'.")
    return FileResponse(path, media_type="image/svg+xml", filename=f"{asset_id}_v{version}.svg")


@router.get("/{asset_id}/png")
async def get_asset_png(asset_id: str):
    """Serve the PNG file for a generated asset."""
    path = store.get_generated_file_path(asset_id, "asset.png")
    if path is None:
        raise HTTPException(404, detail=f"PNG file not found for asset '{asset_id}'.")
    meta = _get_meta(asset_id)
    filename = (meta or {}).get("png_filename", f"{asset_id}.png")
    return FileResponse(path, media_type="image/png", filename=filename)


@router.get("/{asset_id}/svg")
async def get_asset_svg(asset_id: str):
    """Serve the SVG file for a generated asset."""
    path = store.get_generated_file_path(asset_id, "asset.svg")
    if path is None:
        raise HTTPException(404, detail=f"SVG file not found for asset '{asset_id}'.")
    meta = _get_meta(asset_id)
    filename = (meta or {}).get("svg_filename", f"{asset_id}.svg")
    return FileResponse(path, media_type="image/svg+xml", filename=filename)


@router.get("/{asset_id}/3d/{version}")
async def get_asset_3d(asset_id: str, version: int, variant: str | None = None):
    """Serve a GLB (3D model) file for a generated asset.

    3D sub-versioning: a version can hold multiple 3D variants. ``?variant=<id>``
    serves that specific variant file (asset_3d_v{N}__{id}.glb). Without it, the
    version's DEFAULT file is served — asset_3d_v{N}.glb, with asset_3d.glb as the
    v1 fallback for legacy assets that predate per-version files.
    """
    candidates = []
    if variant:
        candidates.append(f"asset_3d_v{version}__{variant}.glb")
    # The version's default file, then legacy fallbacks.
    candidates.append(f"asset_3d_v{version}.glb")
    if version == 1:
        candidates.append("asset_3d.glb")

    path = None
    for fn in candidates:
        path = store.get_generated_file_path(asset_id, fn)
        if path is not None:
            break
    if path is None:
        raise HTTPException(404, detail=f"3D model not found for asset '{asset_id}' version {version}.")
    return FileResponse(path, media_type="model/gltf-binary", filename=f"{asset_id}_3d.glb")
