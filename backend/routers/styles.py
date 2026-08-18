"""Style profiles router — CRUD operations, reference image management, and
style analysis triggers."""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import IMAGE_EXTENSIONS as _IMAGE_EXTENSIONS, MODEL_EXTENSIONS_WITH_TEXTURES, settings
from backend.services.import_dedup import deduplicate_imports
from backend.services.texture_extractor import extract_textures
from backend.models.style_profile import (
    AnalyzedStyle,
    StyleProfile,
    StyleProfileCreate,
    StyleProfileUpdate,
)
from backend.services.style_analyzer import analyze_style, generate_hints
from backend.storage.local_store import store


def _auto_reanalyze(style_id: str, hints: str = "") -> None:
    """Re-run style analysis in the background if reference images exist.

    Silently catches errors — callers should not fail if re-analysis fails.
    """
    refs = store.list_reference_images(style_id)
    if not refs:
        return
    try:
        analyzed: AnalyzedStyle = analyze_style(style_id, user_hints=hints)
        new_hints: str = generate_hints(style_id, analyzed, user_hints=hints)
        data = store.load_style_profile(style_id)
        if data:
            data["analyzed_style"] = analyzed.model_dump()
            data["generation_hints"] = new_hints
            store.save_style_profile(style_id, data)
        logger.info("Auto re-analysis complete for style '%s'.", style_id)
    except Exception:
        logger.exception("Auto re-analysis failed for style '%s'; changes still saved.", style_id)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/styles", tags=["styles"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert a human-readable name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _load_or_404(style_id: str) -> StyleProfile:
    """Load a style profile from storage or raise 404."""
    data = store.load_style_profile(style_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Style '{style_id}' not found.")
    return StyleProfile(**data)


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/", response_model=StyleProfile, status_code=201)
async def create_style(body: StyleProfileCreate):
    """Create a new style profile.

    Generates a slug-based identifier from the provided name and persists
    the profile to local storage.
    """
    style_id = _slugify(body.name)
    if not style_id:
        raise HTTPException(status_code=400, detail="Name produces an empty slug.")

    # Check for duplicates
    existing = store.load_style_profile(style_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Style '{style_id}' already exists.",
        )

    profile = StyleProfile(
        id=style_id,
        name=body.name,
        description=body.description,
        generation_hints=body.generation_hints,
        created_at=datetime.utcnow(),
    )
    store.save_style_profile(style_id, profile.model_dump(mode="json"))
    logger.info("Created style profile: %s", style_id)
    return profile


@router.get("/", response_model=list[StyleProfile])
async def list_styles():
    """List all style profiles."""
    style_ids = store.list_style_ids()
    profiles: list[StyleProfile] = []
    for sid in style_ids:
        data = store.load_style_profile(sid)
        if data is not None:
            profiles.append(StyleProfile(**data))
    return profiles


@router.get("/{style_id}", response_model=StyleProfile)
async def get_style(style_id: str):
    """Get a single style profile by its identifier."""
    return _load_or_404(style_id)


@router.patch("/{style_id}", response_model=StyleProfile)
async def update_style(style_id: str, body: StyleProfileUpdate):
    """Update fields on an existing style profile.

    Only the fields provided in the request body are updated; all others
    remain unchanged.
    """
    profile = _load_or_404(style_id)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")

    merged = profile.model_dump()
    for key, value in update_data.items():
        # Top-level replace for every field (incl. nested models like analyzed_style)
        merged[key] = value

    updated_profile = StyleProfile(**merged)
    store.save_style_profile(style_id, updated_profile.model_dump(mode="json"))
    logger.info("Updated style profile: %s (fields: %s)", style_id, list(update_data.keys()))

    # Re-analyze if generation_hints changed
    if "generation_hints" in update_data and update_data["generation_hints"] != profile.generation_hints:
        _auto_reanalyze(style_id, hints=updated_profile.generation_hints)
        # Reload after re-analysis
        data = store.load_style_profile(style_id)
        if data:
            updated_profile = StyleProfile(**data)

    return updated_profile


@router.delete("/{style_id}")
async def delete_style(style_id: str):
    """Delete a style profile and all its associated data."""
    # Verify it exists first
    _load_or_404(style_id)

    store.delete_style(style_id)
    logger.info("Deleted style profile: %s", style_id)
    return {"deleted": True}


@router.post("/{style_id}/references", response_model=list[str])
async def upload_references(style_id: str, files: list[UploadFile]):
    """Upload one or more reference images for a style profile.

    The images are saved to local storage and the profile's reference_images
    list is updated accordingly.
    """
    # Verify the style exists
    profile = _load_or_404(style_id)

    current_count = len(profile.reference_images)
    if current_count + len(files) > settings.max_reference_images:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot upload {len(files)} image(s). "
                f"Style already has {current_count}/{settings.max_reference_images} references."
            ),
        )

    saved_filenames: list[str] = []
    for upload in files:
        if not upload.filename:
            continue
        contents = await upload.read()
        if not contents:
            continue
        store.save_reference_image(style_id, upload.filename, contents)
        saved_filenames.append(upload.filename)
        logger.info("Saved reference image: %s/%s (%d bytes)", style_id, upload.filename, len(contents))

    # Update the profile's reference image list
    all_refs = store.list_reference_images(style_id)
    merged = profile.model_dump()
    merged["reference_images"] = all_refs
    store.save_style_profile(style_id, merged)

    # Re-analyze with updated references
    _auto_reanalyze(style_id, hints=profile.generation_hints)

    return saved_filenames


@router.get("/{style_id}/references/{filename}")
async def get_reference_image(style_id: str, filename: str):
    """Serve a reference image file for a style profile."""
    # Verify the style exists
    _load_or_404(style_id)

    path = store.get_reference_image_path(style_id, filename)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reference image '{filename}' not found for style '{style_id}'.",
        )
    return FileResponse(path)


class ImportRequest(BaseModel):
    path: str
    auto_analyze: bool = True


def _import_from_local(src: str, style_id: str, available: int) -> list[str]:
    """Import images from a local/network directory path."""
    src_dir = Path(src.strip().strip('"').strip("'")).expanduser().resolve()
    if not src_dir.is_dir():
        raise HTTPException(400, detail=f"Directory not found: {src}")

    # Recursively find all image files in subdirectories
    all_image_files = sorted(
        f for f in src_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in _IMAGE_EXTENSIONS
    )

    # Also find 3D model files that may contain embedded textures
    model_files = sorted(
        f for f in src_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in MODEL_EXTENSIONS_WITH_TEXTURES
    )

    if not all_image_files and not model_files:
        raise HTTPException(400, detail=f"No image or 3D model files found in {src} (searched recursively)")

    # Smart deduplication: strip rotation variants and animation frames,
    # prioritize rendered output folders over raw/intermediate files
    image_files = deduplicate_imports(all_image_files, src_dir, max_count=available)
    logger.info(
        "Import for style '%s': %d total files → %d after deduplication (limit %d)",
        style_id, len(all_image_files), len(image_files), available,
    )

    saved: list[str] = []
    seen_names: set[str] = set()

    # 1. Import deduplicated image files (symlinked)
    for img_path in image_files:
        filename = img_path.name
        if filename in seen_names:
            filename = f"{img_path.parent.name}_{filename}"
        seen_names.add(filename)
        store.link_reference_image(style_id, filename, img_path)
        saved.append(filename)
        logger.info("Linked reference: %s/%s -> %s", style_id, filename, img_path.resolve())

    # 2. Extract textures from 3D model files (copied, not linked)
    remaining = available - len(saved)
    if remaining > 0 and model_files:
        for model_path in model_files:
            if remaining <= 0:
                break
            try:
                textures = extract_textures(model_path)
                for tex_name, tex_bytes in textures:
                    if remaining <= 0:
                        break
                    # Prefix with model filename to avoid collisions
                    prefixed = f"{model_path.stem}_{tex_name}"
                    if prefixed in seen_names:
                        continue
                    seen_names.add(prefixed)
                    store.save_reference_image(style_id, prefixed, tex_bytes)
                    saved.append(prefixed)
                    remaining -= 1
                    logger.info("Extracted texture: %s/%s from %s (%d bytes)",
                                style_id, prefixed, model_path.name, len(tex_bytes))
            except Exception as exc:
                logger.warning("Failed to extract textures from %s: %s", model_path, exc)
    return saved


def _import_from_s3(src: str, style_id: str, available: int) -> list[str]:
    """Import images from an S3 URI (s3://bucket/prefix)."""
    import boto3

    # Parse s3://bucket/prefix
    stripped = src[5:]  # remove "s3://"
    slash_idx = stripped.find("/")
    if slash_idx == -1:
        bucket = stripped
        prefix = ""
    else:
        bucket = stripped[:slash_idx]
        prefix = stripped[slash_idx + 1:].rstrip("/")

    session_kwargs = {}
    if settings.aws_profile:
        session_kwargs["profile_name"] = settings.aws_profile
    session = boto3.Session(**session_kwargs)
    s3 = session.client("s3")

    # List all objects under the prefix (paginated, recursive)
    list_kwargs = {"Bucket": bucket}
    if prefix:
        list_kwargs["Prefix"] = prefix + "/" if not prefix.endswith("/") else prefix

    contents = []
    try:
        while True:
            response = s3.list_objects_v2(**list_kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            list_kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except Exception as exc:
        raise HTTPException(400, detail=f"Failed to list S3 objects: {exc}") from exc
    try:
        from backend.services.cost_tracker import add_s3_cost
        add_s3_cost("list", 0, "style S3 image listing")
    except Exception:
        pass
    if not contents:
        raise HTTPException(400, detail=f"No objects found at {src}")

    # Filter to image files
    image_keys = [
        obj["Key"] for obj in contents
        if any(obj["Key"].lower().endswith(ext) for ext in _IMAGE_EXTENSIONS)
        and not obj["Key"].endswith("/")
    ]
    if not image_keys:
        raise HTTPException(400, detail=f"No image files found at {src}")

    to_import = image_keys[:available]
    saved: list[str] = []
    for key in to_import:
        filename = key.rsplit("/", 1)[-1]
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            data = obj["Body"].read()
            store.save_reference_image(style_id, filename, data)
            saved.append(filename)
            logger.info("Imported from S3: %s/%s (%d bytes)", style_id, filename, len(data))
            try:
                from backend.services.cost_tracker import add_s3_cost
                add_s3_cost("get", len(data), f"style image import ({filename})")
            except Exception:
                pass
        except Exception as exc:
            logger.warning("Failed to download s3://%s/%s: %s", bucket, key, exc)

    if not saved:
        raise HTTPException(502, detail="Failed to download any images from S3")
    return saved


@router.post("/{style_id}/import", response_model=StyleProfile)
async def import_references(style_id: str, body: ImportRequest):
    """Import reference images from a local directory or S3 URI.

    Accepts:
      - Local/network paths:  /path/to/images, ~/Downloads/assets
      - S3 URIs:              s3://bucket-name/prefix/path

    Images are copied into the style's references folder. Optionally
    triggers AI style analysis after import.
    """
    profile = _load_or_404(style_id)

    current_count = len(profile.reference_images)
    available = settings.max_reference_images - current_count
    if available <= 0:
        raise HTTPException(
            400,
            detail=f"Style already has {current_count}/{settings.max_reference_images} reference images.",
        )

    src = body.path.strip().strip('"').strip("'")
    if src.startswith("s3://"):
        saved = _import_from_s3(src, style_id, available)
    else:
        saved = _import_from_local(src, style_id, available)

    # Update profile's reference list
    all_refs = store.list_reference_images(style_id)
    merged = profile.model_dump()
    merged["reference_images"] = all_refs
    store.save_style_profile(style_id, merged)

    logger.info("Imported %d images from %s into style '%s'", len(saved), src, style_id)

    # Optionally auto-analyze
    if body.auto_analyze and all_refs:
        try:
            existing_hints = profile.generation_hints or ""
            analyzed: AnalyzedStyle = analyze_style(style_id, user_hints=existing_hints)
            hints: str = generate_hints(style_id, analyzed, user_hints=existing_hints)
            merged = store.load_style_profile(style_id) or merged
            merged["analyzed_style"] = analyzed.model_dump()
            merged["generation_hints"] = hints
            store.save_style_profile(style_id, merged)
            logger.info("Auto-analysis complete for style '%s'.", style_id)
        except Exception:
            logger.exception("Auto-analysis failed for '%s'; images still imported.", style_id)

    final = store.load_style_profile(style_id)
    return StyleProfile(**final)


@router.post("/{style_id}/analyze", response_model=StyleProfile)
async def analyze_style_endpoint(style_id: str):
    """Trigger style analysis on the reference images.

    Runs the style analyzer to extract visual attributes from the uploaded
    reference images, then generates concise generation hints. Both the
    analyzed_style and generation_hints fields are persisted to the profile.
    """
    profile = _load_or_404(style_id)

    if not profile.reference_images:
        raise HTTPException(
            status_code=400,
            detail=f"Style '{style_id}' has no reference images to analyze.",
        )

    from backend.services.cost_tracker import reset_costs, get_total_cost
    reset_costs()

    try:
        existing_hints = profile.generation_hints or ""
        analyzed: AnalyzedStyle = analyze_style(style_id, user_hints=existing_hints)
        hints: str = generate_hints(style_id, analyzed, user_hints=existing_hints)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Style analysis failed for '%s'.", style_id)
        raise HTTPException(
            status_code=500,
            detail=f"Style analysis failed: {exc}",
        ) from exc

    # Persist the updated profile
    merged = profile.model_dump()
    merged["analyzed_style"] = analyzed.model_dump()
    merged["generation_hints"] = hints
    updated_profile = StyleProfile(**merged)
    store.save_style_profile(style_id, updated_profile.model_dump(mode="json"))

    logger.info("Style analysis complete for '%s'.", style_id)

    from backend.services.telemetry import track_style_analysis, track_style_cost
    track_style_analysis(num_images=len(profile.reference_images))
    track_style_cost(cost_usd=get_total_cost())

    return updated_profile
