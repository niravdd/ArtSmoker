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

            items.append(
                GalleryItem(
                    id=aid,
                    prompt=meta.get("prompt", ""),
                    style_id=meta.get("style_id"),
                    asset_type=meta.get("asset_type", ""),
                    png_url=f"/api/gallery/{aid}/png",
                    svg_url=svg_url,
                    created_at=created_at,
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
                "refined_prompt": meta.get("refined_prompt", ""),
                "variants": [],
            }
        svg_url = f"/api/gallery/{meta['id']}/svg" if meta.get("svg_path") else None
        options_map[oi]["variants"].append({
            "id": meta["id"],
            "variant_index": meta.get("variant_index", 0),
            "png_path": f"/api/gallery/{meta['id']}/png",
            "svg_path": svg_url,
            "png_filename": meta.get("png_filename", f"{meta['id']}.png"),
            "svg_filename": meta.get("svg_filename"),
        })

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
                    opt["refined_prompt"] = v_meta.get("refined_prompt", opt.get("refined_prompt", ""))
                    opt["negative_prompt"] = v_meta.get("negative_prompt", "")

    return {
        "id": batch_id,
        "prompt": first.get("prompt", ""),
        "original_prompt": first.get("original_prompt"),
        "negative_prompt": first.get("negative_prompt"),
        "style_id": first.get("style_id"),
        "style_snapshot": first.get("style_snapshot"),
        "asset_type": first.get("asset_type", ""),
        "image_model": first.get("image_model", ""),
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
