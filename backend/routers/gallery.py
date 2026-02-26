"""Gallery router — browse, filter, and serve generated assets."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.models.generation_result import GalleryItem
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gallery", tags=["gallery"])

# In-memory metadata cache to avoid repeated JSON reads
_meta_cache: dict[str, dict] = {}


def _get_meta(asset_id: str) -> dict | None:
    """Load metadata with caching."""
    if asset_id not in _meta_cache:
        meta = store.load_generation_metadata(asset_id)
        if meta is None:
            return None
        _meta_cache[asset_id] = meta
    return _meta_cache[asset_id]


@router.get("/", response_model=list[GalleryItem])
async def list_gallery(
    style_id: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List generated assets, newest first, with optional filtering and pagination."""
    asset_ids = store.list_generated_ids()
    items: list[GalleryItem] = []

    for aid in asset_ids:
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

    # Sort newest first
    items.sort(key=lambda x: x.created_at, reverse=True)

    # Paginate
    total = len(items)
    items = items[offset:offset + limit]

    logger.info(
        "Gallery: %d/%d items (offset=%d, limit=%d, style=%s, type=%s)",
        len(items), total, offset, limit, style_id, asset_type,
    )
    return items


@router.get("/batch/{batch_id}")
async def get_batch(batch_id: str):
    """Reconstruct a full batch result (options × variations) from a batch_id.

    Returns a structure matching GenerationResult so the frontend can
    reload a previous generation into the Generator view.
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
    return {
        "id": batch_id,
        "prompt": first.get("prompt", ""),
        "original_prompt": first.get("original_prompt"),
        "style_id": first.get("style_id"),
        "asset_type": first.get("asset_type", ""),
        "image_model": first.get("image_model", ""),
        "width": first.get("width", 1024),
        "height": first.get("height", 1024),
        "num_options": len(options),
        "num_variations": max((len(o["variants"]) for o in options), default=1),
        "options": options,
        "created_at": first.get("created_at"),
    }


@router.get("/{asset_id}")
async def get_asset_metadata(asset_id: str):
    """Get the full metadata dictionary for a generated asset."""
    meta = _get_meta(asset_id)
    if meta is None:
        raise HTTPException(404, detail=f"Asset '{asset_id}' not found.")
    return meta


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
