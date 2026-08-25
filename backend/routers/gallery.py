"""Gallery router — browse, filter, and serve generated assets."""

import io
import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.models.generation_request import AssetType
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


@router.post("/import", response_model=GalleryItem)
async def import_image(
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    title: str = Form(""),
    ip_owned: bool = Form(False),
    ip_licensed: bool = Form(False),
):
    """Import an existing image into the gallery as a first-class asset.

    Produces exactly the same on-disk structure as a generated asset (a
    data/generated/{id}/ dir with asset.png + metadata.json), so ALL downstream
    features — edit, versioning, 3D generation, source review — work unchanged.
    The image is normalized to PNG (the app's single image format) regardless of
    the uploaded format, EXIF is dropped, and the asset is flagged `imported` so
    the UI can distinguish it from a generated one. No AI is invoked; the prompt
    is empty (the user's optional title is stored as the prompt for display).
    """
    # Validate asset_type against the known enum (drives 3D eligibility + filters).
    try:
        atype = AssetType(asset_type).value
    except ValueError:
        raise HTTPException(400, detail=f"Invalid asset_type '{asset_type}'.")

    raw = await file.read()
    if not raw:
        raise HTTPException(400, detail="Empty file.")

    # Normalize to PNG via Pillow — accepts JPG/WebP/etc., strips metadata, and
    # guarantees the PNG-only invariant the rest of the pipeline relies on.
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw))
        im.load()
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        im = im.convert("RGBA" if has_alpha else "RGB")
        width, height = im.size
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    except Exception as e:
        raise HTTPException(400, detail=f"Not a readable image: {e}")

    asset_id = f"import_{uuid4().hex[:12]}"
    store.save_generated_image(asset_id, "asset.png", png_bytes)

    title = (title or "").strip()
    orig_name = (file.filename or "").strip()
    now = datetime.now(timezone.utc).isoformat()
    store.save_generation_metadata(asset_id, {
        "id": asset_id,
        # Flag + provenance so the UI can badge it and downstream can reason about it.
        "imported": True,
        "import_filename": orig_name,
        # Empty prompt (no AI ran); the optional title doubles as the display prompt.
        "prompt": title,
        "original_prompt": title,
        "enhanced_prompt": "",
        "negative_prompt": "",
        "asset_type": atype,
        # Sentinel model identity — not a registry key; gallery/AssetViewer show the label.
        "image_model": "imported",
        "model_label": "Imported image",
        "width": width,
        "height": height,
        "ip_owned": bool(ip_owned),
        "ip_licensed": bool(ip_licensed),
        "png_path": f"/api/gallery/{asset_id}/png",
        "png_filename": (orig_name if orig_name.lower().endswith(".png") else f"{asset_id}.png"),
        "created_at": now,
        # No async_status → treated as a complete/sync asset. Empty cost history.
        "cost_history": [],
    })
    logger.info("Imported image → %s (%dx%d, type=%s)", asset_id, width, height, atype)

    # Telemetry: user brought their own asset (no cost — no AI). Non-fatal.
    try:
        from backend.services.telemetry import track_image_import
        src_fmt = (orig_name.rsplit(".", 1)[-1].lower() if "." in orig_name else "")
        track_image_import(asset_type=atype, source_format=src_fmt)
    except Exception:
        pass

    return GalleryItem(
        id=asset_id,
        prompt=title,
        asset_type=atype,
        image_model="imported",
        model_label="Imported image",
        png_url=f"/api/gallery/{asset_id}/png",
        svg_url=None,
        created_at=datetime.fromisoformat(now),
        async_status=None,
    )


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

            # A generated 3D model exists if ANY .glb is present in the asset dir
            # (files are named asset_3d.glb / asset_3d_v{N}.glb / ...__{backend}__{hash}.glb).
            # Surfaced as a "3D" badge on the gallery card so 3D-ready assets are findable.
            try:
                has_3d = any(store.generated_asset_dir(aid).glob("*.glb"))
            except Exception:
                has_3d = False

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
                    has_3d=has_3d,
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
                "status": async_status if async_status in ("failed", "moderation_blocked") else "pending",
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
        "quality": first.get("quality", ""),
        "region": first.get("region", ""),
        # Reference-guided ("Image Inspiration") provenance — lets Image Studio
        # reopen the batch in the Image Inspiration tab with the reference images,
        # mode, and original instruction restored. Empty/false for normal jobs.
        "reference_guided": first.get("reference_guided", False),
        "reference_mode": first.get("reference_mode", "inspired"),
        "reference_prompt": first.get("reference_prompt", ""),
        "reference_image_urls": [
            f"/api/gallery/{first['id']}/reference/{fn}"
            for fn in (first.get("reference_images") or [])
        ],
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


@router.delete("/{asset_id}/version/{version}")
async def delete_asset_version(asset_id: str, version: int):
    """Delete ONE version of an asset — files + metadata references — leaving a
    tombstone record (sparse numbering: later versions are NEVER renumbered).

    Semantics (user-specified 2026-08-06):
      • The version's physical files are removed: asset_v{N}.png/.svg + every
        version-named sidecar (__mask, __cutout, __source, __prepad_src, the
        export artefacts asset__nobg_v{N}.*) + that version's 3D artifacts
        (asset_3d_v{N}*.glb and the three_d v{N} bucket).
      • The versions[] record is replaced by a TOMBSTONE: {version, deleted:
        true, deleted_at} — keeps numbering sparse/stable and records when.
      • If the deleted version was the CURRENT one, the next-lower surviving
        version is PROMOTED: its archived PNG/SVG become asset.png/asset.svg
        and current_version repoints to it.
      • Deleting the LAST surviving version deletes the WHOLE asset
        (returns {asset_deleted: true} so the UI can close/navigate).

    Corruption safety: all validation runs FIRST; the promotion copy (new
    current's bytes → asset.png) happens BEFORE the old files are removed and
    BEFORE metadata is saved — so a crash mid-way leaves extra files (harmless)
    rather than a metadata record pointing at missing files. File deletions are
    per-file best-effort with failures collected and reported.
    """
    import shutil
    from backend.services.asset_locks import asset_write_lock

    # Serialize against the sync/async edit writers — a version save landing
    # mid-delete would otherwise race this read-modify-write of metadata.json.
    with asset_write_lock(asset_id):
        return _delete_asset_version_locked(asset_id, version)


def _delete_asset_version_locked(asset_id: str, version: int):
    """Body of delete_asset_version — caller MUST hold the asset write lock."""
    import shutil

    # ── Validate everything up-front (no side effects yet) ──────────────────
    meta = store.load_generation_metadata(asset_id)
    if meta is None:
        raise HTTPException(404, detail=f"Asset '{asset_id}' not found.")
    versions = meta.get("versions") or []
    if not versions:
        # Un-versioned asset (single implicit version) — treat as whole-asset.
        if version != 1:
            raise HTTPException(404, detail=f"Version {version} not found.")
        if not store.delete_generated_asset(asset_id):
            raise HTTPException(500, detail="Failed to delete the asset directory.")
        _meta_cache.pop(asset_id, None)
        logger.info("VERSION-DELETE: %s had no version records — whole asset deleted", asset_id)
        return {"asset_deleted": True, "deleted_version": version}

    vrec = next((v for v in versions if v.get("version") == version), None)
    if vrec is None:
        raise HTTPException(404, detail=f"Version {version} not found.")
    if vrec.get("deleted"):
        raise HTTPException(409, detail=f"Version {version} is already deleted.")

    surviving = [v for v in versions if not v.get("deleted") and v.get("version") != version]
    current_version = meta.get("current_version") or (len(versions) or 1)

    # ── Last surviving version → delete the whole asset ─────────────────────
    if not surviving:
        if not store.delete_generated_asset(asset_id):
            raise HTTPException(500, detail="Failed to delete the asset directory.")
        _meta_cache.pop(asset_id, None)
        logger.info("VERSION-DELETE: %s v%d was the last version — whole asset deleted",
                    asset_id, version)
        return {"asset_deleted": True, "deleted_version": version}

    asset_dir = store.generated_asset_dir(asset_id)
    now = datetime.now(timezone.utc).isoformat()
    was_current = (version == current_version)
    new_current = max(v["version"] for v in surviving) if was_current else current_version
    file_errors: list[str] = []

    # ── PROMOTION FIRST (copy before any delete — crash-safe ordering) ──────
    # If the current version is being deleted, materialize the new current's
    # bytes into asset.png/asset.svg BEFORE removing anything. The new current
    # keeps its archived asset_v{N}.png too (versioning convention tolerates
    # both existing; readers try archived-name first, then asset.png).
    if was_current:
        promo_png = asset_dir / f"asset_v{new_current}.png"
        if not promo_png.exists():
            raise HTTPException(
                500, detail=(f"Cannot promote v{new_current}: its archived file is missing. "
                             f"Nothing was deleted."))
        try:
            shutil.copy2(str(promo_png), str(asset_dir / "asset.png"))
            promo_svg = asset_dir / f"asset_v{new_current}.svg"
            if promo_svg.exists():
                shutil.copy2(str(promo_svg), str(asset_dir / "asset.svg"))
            else:
                # No SVG for the promoted version — remove the stale current SVG
                # rather than leave the deleted version's trace behind.
                (asset_dir / "asset.svg").unlink(missing_ok=True)
        except Exception as e:
            raise HTTPException(500, detail=f"Promotion failed ({e}). Nothing was deleted.")

    # ── Metadata: tombstone + repoint (saved BEFORE file removal) ────────────
    tombstone = {"version": version, "deleted": True, "deleted_at": now,
                 "type": vrec.get("type", ""), "model_label": vrec.get("model_label", "")}
    meta["versions"] = [tombstone if v.get("version") == version else v for v in versions]
    meta["current_version"] = new_current
    # Drop per-version references owned by the deleted version.
    if isinstance(meta.get("cutouts"), dict):
        meta["cutouts"].pop(str(version), None)
    three_d = meta.get("three_d")
    removed_3d_files: list[str] = []
    if isinstance(three_d, dict) and f"v{version}" in three_d:
        for variant in (three_d[f"v{version}"].get("variants") or []):
            fn = variant.get("glb_filename")
            if fn:
                removed_3d_files.append(fn)
        three_d.pop(f"v{version}", None)
    meta["three_d_versions"] = [e for e in (meta.get("three_d_versions") or [])
                                if e.get("version") != version]
    try:
        store.save_generation_metadata(asset_id, meta)
    except Exception as e:
        raise HTTPException(500, detail=f"Metadata update failed ({e}). Files were not removed; the asset may show a stale current version — retry.")  # nosec B608 -- error-message f-string, not SQL (this app has no database)
    _meta_cache.pop(asset_id, None)

    # ── Physical files LAST (metadata no longer references any of them) ─────
    candidates = [
        f"asset_v{version}.png", f"asset_v{version}.svg",
        f"asset_v{version}__mask.png", f"asset_v{version}__source.png",
        # Shared cutout PNG + its vector SVG (canonical), plus the legacy export
        # names for assets created before cutout unification. dict.fromkeys below
        # dedupes (canonical PNG == the 3D __cutout name).
        _cutout_png_name(version), _cutout_svg_name(version),
        _legacy_cutout_png_name(version), _legacy_cutout_svg_name(version),
        f"asset_3d_v{version}.glb",
    ] + removed_3d_files
    # Any other version-suffixed sidecars (e.g. edit_{job}__prepad, future ones)
    try:
        for p in asset_dir.glob(f"asset_3d_v{version}__*.glb"):
            candidates.append(p.name)
    except Exception:
        pass
    deleted_files = []
    for name in dict.fromkeys(candidates):  # dedupe, keep order
        try:
            p = asset_dir / name
            if p.exists():
                p.unlink()
                deleted_files.append(name)
        except Exception as e:
            file_errors.append(f"{name}: {e}")

    if file_errors:
        # Metadata is already consistent (tombstoned) — leftover files are
        # orphans, not corruption. Report honestly so the user can retry/inspect.
        logger.warning("VERSION-DELETE: %s v%d tombstoned but %d file(s) could not be removed: %s",
                       asset_id, version, len(file_errors), "; ".join(file_errors))
    logger.info("VERSION-DELETE: %s v%d deleted (%d files) — current now v%d%s",
                asset_id, version, len(deleted_files), new_current,
                " (promoted)" if was_current else "")
    return {
        "asset_deleted": False,
        "deleted_version": version,
        "deleted_at": now,
        "current_version": new_current,
        "promoted": was_current,
        "deleted_files": deleted_files,
        "file_errors": file_errors,   # non-empty = orphaned files remain (not corruption)
        "surviving_versions": [v["version"] for v in surviving],
    }


@router.get("/{asset_id}")
async def get_asset_metadata(asset_id: str):
    """Get the full metadata dictionary for a generated asset.

    Enriches the stored metadata with `storage_dir` — the absolute on-disk
    directory holding this asset's files — so the viewer can show the exact
    file path for whichever version is currently selected (current version =
    asset.png; older versions = asset_v{N}.png, per the versioning convention).
    """
    meta = _get_meta(asset_id)
    if meta is None:
        raise HTTPException(404, detail=f"Asset '{asset_id}' not found.")
    meta = dict(meta)  # copy so we never mutate the cached dict
    try:
        meta["storage_dir"] = str(store.generated_asset_dir(asset_id).resolve())
    except Exception:
        meta["storage_dir"] = ""
    return meta


@router.get("/{asset_id}/version/{version}")
async def get_asset_version(asset_id: str, version: int):
    """Serve a specific PNG version of an asset.

    Honors the 2D versioning convention: the CURRENT version lives as asset.png;
    only OLDER versions are archived as asset_v{N}.png. Try the archived file
    first, then fall back to asset.png (covers the current version) so callers
    that pass the current version number still resolve.
    """
    path = store.get_generated_file_path(asset_id, f"asset_v{version}.png") \
        or store.get_generated_file_path(asset_id, "asset.png")
    if path is None:
        raise HTTPException(404, detail=f"Version {version} not found for asset '{asset_id}'.")
    return FileResponse(path, media_type="image/png", filename=f"{asset_id}_v{version}.png")


@router.get("/{asset_id}/version-svg/{version}")
async def get_asset_version_svg(asset_id: str, version: int):
    """Serve a specific SVG version of an asset.

    Mirrors the PNG version endpoint: the CURRENT version's with-bg SVG lives as
    asset.svg (only OLDER versions are archived as asset_v{N}.svg), so fall back
    to asset.svg when the version-specific file is absent."""
    path = store.get_generated_file_path(asset_id, f"asset_v{version}.svg") \
        or store.get_generated_file_path(asset_id, "asset.svg")
    if path is None:
        raise HTTPException(404, detail=f"SVG version {version} not found for asset '{asset_id}'.")
    return FileResponse(path, media_type="image/svg+xml", filename=f"{asset_id}_v{version}.svg")


@router.get("/{asset_id}/mask/{mask_file}")
async def get_asset_mask(asset_id: str, mask_file: str):
    """Serve a persisted edit-mask sidecar (shows WHERE a fill/erase was applied).

    Restricted to the mask-sidecar naming convention (…__mask.png) so this can
    only serve mask files, never arbitrary paths (no traversal)."""
    import os as _os
    safe = _os.path.basename(mask_file)
    if not safe.endswith("__mask.png"):
        raise HTTPException(400, detail="Not a mask file.")
    path = store.get_generated_file_path(asset_id, safe)
    if path is None:
        raise HTTPException(404, detail="Mask not found.")
    return FileResponse(path, media_type="image/png", filename=safe)


@router.get("/{asset_id}/reference/{ref_file}")
async def get_asset_reference(asset_id: str, ref_file: str):
    """Serve a persisted reference image for an 'Image Inspiration' job (used to
    restore the Reference Studio on reload).

    Restricted to the reference naming convention (reference_N.png) so this can
    only serve reference files, never arbitrary paths (no traversal)."""
    import os as _os
    import re as _re
    safe = _os.path.basename(ref_file)
    if not _re.fullmatch(r"reference_\d+\.png", safe):
        raise HTTPException(400, detail="Not a reference file.")
    path = store.get_generated_file_path(asset_id, safe)
    if path is None:
        raise HTTPException(404, detail="Reference image not found.")
    return FileResponse(path, media_type="image/png", filename=safe)


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


# ── Export variants: background-removed cutouts (PNG + SVG) ────────────────
#
# The Export tab offers, per version, three artefacts:
#   1. with-bg SVG   — the existing vector trace of the full image (asset.svg /
#                      asset_v{N}.svg)
#   2. no-bg PNG     — a transparent cutout (one background removal)
#   3. no-bg SVG     — a FREE local vector trace of that same cutout
# So a single background removal (local rembg = free, or paid Bedrock) serves
# both no-bg artefacts. Cutouts are cached per version (asset__nobg_v{N}.png /
# .svg) so editing the asset (new version) never serves a stale cutout.


# The background-removed cutout is ONE shared artefact per version, used by BOTH
# the 3D workflow (Improve-the-Source / mesher prep, which writes
# asset_v{N}__cutout.png via generate_3d._ensure_cutout) AND the Export & Cutouts
# tab. They perform the identical operation (remove_background of the version
# image), so the canonical name IS the 3D sidecar name — no separate export file.
# The old export name (asset__nobg_v{N}.*) is still READ for assets made before
# this unification.
def _cutout_png_name(version: int) -> str:
    return f"asset_v{version}__cutout.png"


def _cutout_svg_name(version: int) -> str:
    return f"asset_v{version}__cutout.svg"


def _legacy_cutout_png_name(version: int) -> str:
    return f"asset__nobg_v{version}.png"


def _legacy_cutout_svg_name(version: int) -> str:
    return f"asset__nobg_v{version}.svg"


def _withbg_svg_name(version: int, current_version: int) -> str:
    """The with-bg SVG file for a version (current lives as asset.svg)."""
    return "asset.svg" if version == current_version else f"asset_v{version}.svg"


def _resolve_version(meta: dict, version: int | None) -> int:
    cur = meta.get("current_version") or (len(meta.get("versions", [])) or 1)
    return version or cur


def _version_png_path(asset_id: str, version: int, current_version: int):
    """PNG bytes source for a version (current = asset.png, else asset_v{N}.png)."""
    if version == current_version:
        return store.get_generated_file_path(asset_id, "asset.png")
    return store.get_generated_file_path(asset_id, f"asset_v{version}.png") \
        or store.get_generated_file_path(asset_id, "asset.png")


def _is_version_bg_free(asset_id: str, version: int, meta: dict) -> bool:
    """True when the 2D version is already a transparent cutout (a bg_free 3D
    source-prep commit, or a remove_background edit) — then the version image IS
    its own no-bg cutout and no separate file is needed. Delegates to the single
    source of truth in the 3D router."""
    try:
        from backend.routers.generate_3d import _version_is_bg_free
        return _version_is_bg_free(asset_id, version, meta)
    except Exception:
        return False


def _resolve_cutout_png(asset_id: str, version: int, meta: dict, current_version: int):
    """Path to the version's no-bg cutout PNG (the SINGLE shared artefact):
    the version image itself when the version is already background-free, else the
    canonical shared cutout (asset_v{N}__cutout.png, written by 3D or Export), else
    the legacy export file. None if no cutout exists yet."""
    if _is_version_bg_free(asset_id, version, meta):
        return _version_png_path(asset_id, version, current_version)
    return (store.get_generated_file_path(asset_id, _cutout_png_name(version))
            or store.get_generated_file_path(asset_id, _legacy_cutout_png_name(version)))


def _resolve_cutout_svg(asset_id: str, version: int):
    """Path to the version's no-bg vector SVG (canonical, else legacy)."""
    return (store.get_generated_file_path(asset_id, _cutout_svg_name(version))
            or store.get_generated_file_path(asset_id, _legacy_cutout_svg_name(version)))


def _export_status(asset_id: str, meta: dict, version: int, current_version: int) -> dict:
    """Which export artefacts already exist for a version, with serve URLs. The
    no-bg cutout is the SHARED artefact — so a cutout created by the 3D workflow
    shows here too (and a background-free version needs no separate file)."""
    withbg_svg = store.get_generated_file_path(asset_id, _withbg_svg_name(version, current_version))
    nobg_png = _resolve_cutout_png(asset_id, version, meta, current_version)
    nobg_svg = _resolve_cutout_svg(asset_id, version)
    cut_meta = (meta.get("cutouts") or {}).get(str(version), {})
    bg_free = _is_version_bg_free(asset_id, version, meta)
    return {
        "version": version,
        "withbg_svg": {
            "exists": withbg_svg is not None,
            "url": (f"/api/gallery/{asset_id}/version-svg/{version}"
                    if withbg_svg is not None else None),
        },
        "nobg_png": {
            "exists": nobg_png is not None,
            "url": (f"/api/gallery/{asset_id}/cutout-png/{version}"
                    if nobg_png is not None else None),
        },
        "nobg_svg": {
            "exists": nobg_svg is not None,
            "url": (f"/api/gallery/{asset_id}/cutout-svg/{version}"
                    if nobg_svg is not None else None),
        },
        # A background-free version is its own cutout with no removal cost.
        "method": ("none" if bg_free else cut_meta.get("method")),
        "cost_usd": cut_meta.get("cost_usd", 0),
        "bg_free": bg_free,
    }


@router.get("/{asset_id}/export-status")
async def get_export_status(asset_id: str, version: int | None = Query(default=None)):
    """Report which export artefacts (with-bg SVG, no-bg PNG, no-bg SVG) exist."""
    meta = _get_meta(asset_id)
    if meta is None:
        raise HTTPException(404, detail=f"Asset '{asset_id}' not found.")
    current_version = meta.get("current_version") or (len(meta.get("versions", [])) or 1)
    v = _resolve_version(meta, version)
    return _export_status(asset_id, meta, v, current_version)


class ExportVariantsRequest(BaseModel):
    method: str = "local"          # "local" (rembg, free) | "bedrock" (paid SD)
    version: int | None = None     # defaults to the current version
    # force=False (default): reuse an existing cutout PNG, only filling in a
    # MISSING SVG (never re-removes the background). force=True: regenerate and
    # overwrite BOTH (the UI asks the user first when both already exist).
    force: bool = False


@router.post("/{asset_id}/export-variants")
async def create_export_variants(asset_id: str, body: ExportVariantsRequest):
    """Produce (and cache) the background-removed cutout PNG + its vector SVG.

    A single background removal yields the transparent PNG; the no-bg SVG is then
    a free local vtracer trace of that cutout. Also ensures the with-bg SVG for
    the version exists (traced locally). Idempotent per (version, method): if the
    cutout already exists for the requested method it is reused, not regenerated.
    """
    from backend.services.post_processor import (
        convert_to_svg,
        remove_background,
        BG_METHOD_LOCAL,
        BG_METHOD_BEDROCK,
    )

    meta = _get_meta(asset_id)
    if meta is None:
        raise HTTPException(404, detail=f"Asset '{asset_id}' not found.")

    method = BG_METHOD_LOCAL if body.method == BG_METHOD_LOCAL else BG_METHOD_BEDROCK
    force = bool(body.force)   # regenerate + overwrite both (UI confirms first)
    current_version = meta.get("current_version") or (len(meta.get("versions", [])) or 1)
    version = _resolve_version(meta, body.version)

    src_path = _version_png_path(asset_id, version, current_version)
    if src_path is None:
        raise HTTPException(404, detail=f"No image for asset '{asset_id}' version {version}.")

    asset_dir = store.generated_asset_dir(asset_id)
    cut_meta_all = meta.get("cutouts") or {}
    prior = cut_meta_all.get(str(version), {})

    # Ensure the with-bg SVG for this version exists (free local trace).
    withbg_svg_path = asset_dir / _withbg_svg_name(version, current_version)
    if not withbg_svg_path.exists():
        try:
            convert_to_svg(src_path.read_bytes(), withbg_svg_path)
        except Exception:
            logger.exception("with-bg SVG trace failed for %s v%d", asset_id, version)

    cutout_png_path = asset_dir / _cutout_png_name(version)
    cutout_svg_path = asset_dir / _cutout_svg_name(version)

    cost_usd = 0.0
    bg_free = _is_version_bg_free(asset_id, version, meta)

    if bg_free:
        # The version image is ALREADY a transparent cutout (3D source-prep commit
        # / remove_background edit) — no removal, no separate PNG file. The PNG can
        # never be "regenerated" (it IS the version image), so force only affects
        # the SVG: (re)trace it when forced or when it's missing.
        reuse = True
        if force or _resolve_cutout_svg(asset_id, version) is None:
            try:
                convert_to_svg(src_path.read_bytes(), cutout_svg_path)
            except Exception:
                logger.exception("no-bg SVG trace failed for %s v%d (bg-free)", asset_id, version)
        cut_meta_all[str(version)] = {"method": "none", "cost_usd": 0.0}
        meta["cutouts"] = cut_meta_all
        store.save_generation_metadata(asset_id, meta)
        _meta_cache.pop(asset_id, None)
        meta = _get_meta(asset_id) or meta
    else:
        # ONE shared cutout: reuse the canonical/legacy PNG if it already exists
        # (whether the 3D workflow or a prior export made it) — the operation is
        # identical, so the background is never removed twice. force=True (user
        # confirmed a regenerate-both) always redoes the PNG; otherwise reuse it
        # and only fill in a missing SVG. A method change alone does NOT silently
        # regenerate — the UI routes that through the same force confirmation.
        existing = (store.get_generated_file_path(asset_id, _cutout_png_name(version))
                    or store.get_generated_file_path(asset_id, _legacy_cutout_png_name(version)))
        reuse = existing is not None and not force

        if not reuse:
            try:
                nobg_bytes = remove_background(src_path.read_bytes(), method=method)
            except Exception as exc:
                # nosemgrep -- logs the root cause for operators, then re-raises; intentional error-level at the boundary
                logger.exception("Background removal failed for %s v%d (%s)", asset_id, version, method)
                raise HTTPException(502, detail=f"Background removal failed: {exc}")

            cutout_png_path.write_bytes(nobg_bytes)
            try:
                convert_to_svg(nobg_bytes, cutout_svg_path)
            except Exception:
                logger.exception("no-bg SVG trace failed for %s v%d", asset_id, version)

            if method == BG_METHOD_BEDROCK:
                try:
                    from backend.routers.generate import _get_model_price
                    from backend.services.post_processor import _find_model_key_by_purpose
                    bg_key = _find_model_key_by_purpose("remove_background")
                    cost_usd = float(_get_model_price(bg_key)) if bg_key else 0.0
                except Exception:
                    cost_usd = 0.0

            cut_meta_all[str(version)] = {"method": method, "cost_usd": round(cost_usd, 6)}
            meta["cutouts"] = cut_meta_all
            if cost_usd:
                history = meta.get("cost_history", [])
                history.append({"action": "remove_background", "model": "bedrock", "cost_usd": round(cost_usd, 6)})
                meta["cost_history"] = history
                meta["estimated_total_cost_usd"] = round(
                    sum(c.get("cost_usd", 0) for c in history), 6
                )
            store.save_generation_metadata(asset_id, meta)
            _meta_cache.pop(asset_id, None)
            meta = _get_meta(asset_id) or meta
        else:
            # Reusing the shared cutout PNG (existing): DON'T re-remove the
            # background — only fill in a MISSING SVG by tracing the existing PNG
            # (the "PNG exists, no SVG → just make the SVG" case). The PNG's
            # method record is left untouched (tracing doesn't change how the
            # cutout was produced), so we never mislabel a reused cutout's method.
            if _resolve_cutout_svg(asset_id, version) is None:
                try:
                    convert_to_svg(existing.read_bytes(), cutout_svg_path)
                except Exception:
                    logger.exception("no-bg SVG trace failed for %s v%d (reuse)", asset_id, version)

    logger.info(
        "Export variants for %s v%d: method=%s bg_free=%s reuse=%s cost=$%.4f",
        asset_id, version, method, bg_free, reuse, cost_usd,
    )
    # Telemetry: the cutout/SVG export is billable Bedrock work when a background is
    # actually removed — track it (parity with the Image Studio post-process path,
    # which was tracked; this entry point previously wasn't, hiding the cost).
    if not reuse:
        try:
            from backend.services.telemetry import track_post_process
            track_post_process(
                action="cutout_export",
                model=("bedrock" if method == BG_METHOD_BEDROCK else "local"),
                cost_usd=round(cost_usd, 6), num_assets=1,
            )
        except Exception:
            pass
    status = _export_status(asset_id, meta, version, current_version)
    status["reused"] = reuse
    status["cost_incurred_usd"] = 0.0 if reuse else round(cost_usd, 6)
    return status


@router.get("/{asset_id}/cutout-png/{version}")
async def get_cutout_png(asset_id: str, version: int):
    """Serve the background-removed (transparent) PNG cutout for a version — the
    SHARED cutout (canonical/legacy), or the version image itself when it's
    already background-free."""
    meta = _get_meta(asset_id) or {}
    cur = meta.get("current_version") or (len(meta.get("versions", [])) or 1)
    path = _resolve_cutout_png(asset_id, version, meta, cur)
    if path is None:
        raise HTTPException(404, detail=f"Cutout PNG not found for '{asset_id}' v{version}.")
    return FileResponse(path, media_type="image/png", filename=f"{asset_id}_v{version}_nobg.png")


@router.get("/{asset_id}/cutout-svg/{version}")
async def get_cutout_svg(asset_id: str, version: int):
    """Serve the background-removed vector SVG cutout for a version."""
    path = _resolve_cutout_svg(asset_id, version)
    if path is None:
        raise HTTPException(404, detail=f"Cutout SVG not found for '{asset_id}' v{version}.")
    return FileResponse(path, media_type="image/svg+xml", filename=f"{asset_id}_v{version}_nobg.svg")


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


@router.get("/{asset_id}/3d/{version}/export/{fmt}")
async def get_asset_3d_export(asset_id: str, version: int, fmt: str,
                              variant: str | None = None, target: str = "generic"):
    """Serve an engine-ready export of a generated 3D asset.

    fmt ∈ {glb, fbx, usd}. GLB is served PRISTINE (glTF is Y-up by spec and importers
    convert on load — a re-oriented GLB would be malformed). FBX + USD are oriented
    for `target` (generic/unreal/unity/godot/maya/3dsmax) and converted LAZILY on
    first request — ONLY the requested format is built (an explicit download is the
    user's intent; we don't spawn formats they didn't ask for and clutter storage) —
    cached PER TARGET so switching targets never overwrites a previously-built one.
    Fidelity note: geometry + UVs + base color + normal survive; metallic/roughness
    re-hooks on engine import (a format limitation).
    """
    from backend.services import mesh_export
    fmt = (fmt or "").lower()
    if fmt not in ("glb", "fbx", "usd"):
        raise HTTPException(400, detail=f"Unsupported export format '{fmt}'.")
    if target not in mesh_export.TARGETS:
        target = mesh_export.DEFAULT_TARGET

    # Locate the source GLB using the SAME candidate order as the GLB endpoint.
    glb_candidates = []
    if variant:
        glb_candidates.append(f"asset_3d_v{version}__{variant}.glb")
    glb_candidates.append(f"asset_3d_v{version}.glb")
    if version == 1:
        glb_candidates.append("asset_3d.glb")
    glb_path = None
    glb_name = None
    for fn in glb_candidates:
        p = store.get_generated_file_path(asset_id, fn)
        if p is not None:
            glb_path, glb_name = p, fn
            break
    if glb_path is None:
        raise HTTPException(404, detail=f"3D model not found for asset '{asset_id}' version {version}.")

    # GLB: the pristine original, target-independent.
    if fmt == "glb":
        return FileResponse(glb_path, media_type="model/gltf-binary", filename=f"{asset_id}_3d.glb")

    # FBX / USD(z): per-target cache beside the GLB (…__{target}.fbx / …__{target}.usdz).
    base = glb_name[:-4]  # strip ".glb"
    ext = "fbx" if fmt == "fbx" else "usdz"
    asset_dir = store.generated_asset_dir(asset_id)
    out_path = asset_dir / f"{base}__{target}.{ext}"

    if not out_path.exists() or out_path.stat().st_size == 0:
        import asyncio
        from backend.services.safe_write import named_write_lock

        def _convert():
            # Serialize per (asset, version, variant, target, fmt) across workers so
            # two concurrent downloads don't both run Blender; second waiter finds cache.
            with named_write_lock(f"export-{asset_id}-{version}-{variant or 'default'}-{target}-{fmt}"):
                if out_path.exists() and out_path.stat().st_size > 0:
                    return
                # Build ONLY the requested format — don't spawn files the user didn't
                # ask for. convert_mesh maps "usd" → the .usdz path we pass.
                mesh_export.convert_mesh(str(glb_path), {fmt: out_path}, target)

        try:
            await asyncio.to_thread(_convert)   # Blender is blocking → off the event loop
        except mesh_export.MeshExportError as e:
            from backend.services import telemetry
            telemetry.track_error(error_type="mesh_export", message=str(e)[:200])
            raise HTTPException(503, detail=f"Export unavailable: {e}")

    # Adoption telemetry: an export download is always intentional (fetch-based UI),
    # so track unconditionally here. <a download> anchors are tracked separately via
    # the /track-download beacon (this endpoint is never used as a display src).
    try:
        from backend.services.telemetry import track_download
        _m = _get_meta(asset_id) or {}
        track_download(file_format=fmt, asset_type=_m.get("asset_type", ""), kind="export",
                       engine_target=target, model=_m.get("image_model", ""), variant=variant or "")
    except Exception:
        pass
    return FileResponse(out_path, media_type="application/octet-stream",
                        filename=f"{asset_id}_3d_{target}.{ext}")


class TrackDownloadRequest(BaseModel):
    url: str = ""


# URL-path → (format, kind) patterns for the download beacon. Matched against the
# path portion of the gallery serve URLs the <a download> anchors point at.
_DL_PATTERNS = [
    (re.compile(r"^/api/gallery/([^/]+)/png$"), "png", "asset"),
    (re.compile(r"^/api/gallery/([^/]+)/svg$"), "svg", "asset"),
    (re.compile(r"^/api/gallery/([^/]+)/version/\d+$"), "png", "version"),
    (re.compile(r"^/api/gallery/([^/]+)/version-svg/\d+$"), "svg", "version"),
    (re.compile(r"^/api/gallery/([^/]+)/cutout-png/\d+$"), "png", "cutout"),
    (re.compile(r"^/api/gallery/([^/]+)/cutout-svg/\d+$"), "svg", "cutout"),
    (re.compile(r"^/api/gallery/([^/]+)/3d/\d+$"), "glb", "asset"),
]


@router.post("/track-download")
async def track_download_beacon(body: TrackDownloadRequest):
    """Adoption telemetry beacon: the frontend fires this (sendBeacon) when a user
    clicks any <a download> anchor. The URL is parsed server-side and enriched from
    the asset's metadata — the serve endpoints themselves can't be hooked because
    the SAME URLs render in-app previews (every thumbnail would count as a download).
    """
    from urllib.parse import urlparse, parse_qs
    try:
        parsed = urlparse(body.url or "")
        path = parsed.path
        for pat, fmt, kind in _DL_PATTERNS:
            m = pat.match(path)
            if not m:
                continue
            asset_id = m.group(1)
            meta = _get_meta(asset_id) or {}
            variant = (parse_qs(parsed.query).get("variant") or [""])[0]
            from backend.services.telemetry import track_download
            track_download(file_format=fmt, asset_type=meta.get("asset_type", ""), kind=kind,
                           model=meta.get("image_model", ""), variant=variant)
            return {"tracked": True}
    except Exception:
        pass
    return {"tracked": False}
