"""Gallery router — browse, filter, and serve generated assets."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.models.generation_result import GalleryItem
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


@router.get("/", response_model=list[GalleryItem])
async def list_gallery(
    style_id: str | None = Query(default=None, description="Filter by style identifier"),
    asset_type: str | None = Query(default=None, description="Filter by asset type"),
):
    """List all generated assets with optional filtering.

    Returns a list of gallery items with URLs pointing to the PNG and SVG
    serving endpoints. Supports filtering by style_id and/or asset_type.
    """
    asset_ids = store.list_generated_ids()
    items: list[GalleryItem] = []

    for aid in asset_ids:
        meta = store.load_generation_metadata(aid)
        if meta is None:
            continue

        # Apply filters
        if style_id and meta.get("style_id") != style_id:
            continue
        if asset_type and meta.get("asset_type") != asset_type:
            continue

        # Determine SVG URL (only if the SVG file actually exists)
        svg_url: str | None = None
        svg_file = store.get_generated_file_path(aid, "asset.svg")
        if svg_file is not None:
            svg_url = f"/api/gallery/{aid}/svg"

        # Parse created_at, falling back to current time
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
                num_variants=1,
                created_at=created_at,
            )
        )

    logger.info(
        "Gallery listing: %d items (filters: style_id=%s, asset_type=%s)",
        len(items),
        style_id,
        asset_type,
    )
    return items


@router.get("/{asset_id}")
async def get_asset_metadata(asset_id: str):
    """Get the full metadata dictionary for a generated asset."""
    meta = store.load_generation_metadata(asset_id)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{asset_id}' not found.",
        )
    return meta


@router.get("/{asset_id}/png")
async def get_asset_png(asset_id: str):
    """Serve the PNG file for a generated asset."""
    path = store.get_generated_file_path(asset_id, "asset.png")
    if path is None:
        raise HTTPException(
            status_code=404,
            detail=f"PNG file not found for asset '{asset_id}'.",
        )
    meta = store.load_generation_metadata(asset_id)
    filename = (meta or {}).get("png_filename", f"{asset_id}.png")
    return FileResponse(
        path,
        media_type="image/png",
        filename=filename,
    )


@router.get("/{asset_id}/svg")
async def get_asset_svg(asset_id: str):
    """Serve the SVG file for a generated asset."""
    path = store.get_generated_file_path(asset_id, "asset.svg")
    if path is None:
        raise HTTPException(
            status_code=404,
            detail=f"SVG file not found for asset '{asset_id}'.",
        )
    meta = store.load_generation_metadata(asset_id)
    filename = (meta or {}).get("svg_filename", f"{asset_id}.svg")
    return FileResponse(
        path,
        media_type="image/svg+xml",
        filename=filename,
    )
