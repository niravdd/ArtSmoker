"""Style profiles router — CRUD operations, reference image management, and
style analysis triggers."""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.config import settings
from backend.models.style_profile import (
    AnalyzedStyle,
    StyleProfile,
    StyleProfileCreate,
    StyleProfileUpdate,
)
from backend.services.style_analyzer import analyze_style, generate_hints
from backend.storage.local_store import store

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
        if isinstance(value, dict):
            # For nested models like analyzed_style, merge at top level
            merged[key] = value
        else:
            merged[key] = value

    updated_profile = StyleProfile(**merged)
    store.save_style_profile(style_id, updated_profile.model_dump(mode="json"))
    logger.info("Updated style profile: %s (fields: %s)", style_id, list(update_data.keys()))
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

    try:
        analyzed: AnalyzedStyle = analyze_style(style_id)
        hints: str = generate_hints(style_id, analyzed)
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
    return updated_profile
