"""File and S3 browser endpoints — for populating path inputs in the frontend."""

import logging
from pathlib import Path

import boto3
from fastapi import APIRouter, HTTPException, Query

from backend.config import IMAGE_EXTENSIONS, MODEL_EXTENSIONS_WITH_TEXTURES, settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/browse", tags=["browse"])


# ── Local filesystem browser ─────────────────────────────────────────────

@router.get("/local")
async def browse_local(path: str = Query(default="~")):
    """List contents of a local directory.

    Returns directories and image files, sorted with directories first.

    SECURITY NOTE: This endpoint is designed for local/trusted use only.
    It allows browsing any directory the server process can access.
    Do not expose this endpoint to untrusted networks without adding
    authentication and path restrictions.
    """
    target = Path(path.strip().strip('"').strip("'")).expanduser().resolve()

    if not target.exists():
        raise HTTPException(400, detail=f"Path does not exist: {path}")
    if not target.is_dir():
        # If they pointed at a file, return its parent directory contents
        # with the file highlighted
        target = target.parent

    asset_exts = IMAGE_EXTENSIONS | MODEL_EXTENSIONS_WITH_TEXTURES
    items = []

    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                items.append({
                    "name": entry.name,
                    "type": "directory",
                    "path": str(entry),
                })
            elif entry.is_file() and entry.suffix.lower() in asset_exts:
                items.append({
                    "name": entry.name,
                    "type": "file",
                    "path": str(entry),
                    "size": entry.stat().st_size,
                })
    except PermissionError:
        raise HTTPException(403, detail=f"Permission denied: {target}")

    return {
        "current": str(target),
        "parent": str(target.parent) if target != target.parent else None,
        "items": items,
        "image_count": sum(1 for i in items if i["type"] == "file"),
    }


# ── S3 browser ───────────────────────────────────────────────────────────

def _get_s3_client():
    session_kwargs = {}
    if settings.aws_profile:
        session_kwargs["profile_name"] = settings.aws_profile
    session = boto3.Session(**session_kwargs)
    return session.client("s3")


@router.get("/s3/buckets")
async def list_s3_buckets():
    """List all S3 buckets accessible to the current AWS credentials."""
    try:
        s3 = _get_s3_client()
        response = s3.list_buckets()
        buckets = [
            {"name": b["Name"], "created": b["CreationDate"].isoformat()}
            for b in response.get("Buckets", [])
        ]
        return {"buckets": buckets}
    except Exception as exc:
        raise HTTPException(502, detail=f"Failed to list S3 buckets: {exc}")


@router.post("/s3/create-bucket")
async def create_s3_bucket(body: dict):
    """Create a new S3 bucket. Returns the bucket name and region."""
    bucket_name = body.get("name", "").strip()
    region = body.get("region", "").strip() or None

    if not bucket_name:
        raise HTTPException(400, detail="Bucket name is required")

    # Basic S3 bucket name validation
    import re
    if not re.match(r'^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$', bucket_name):
        raise HTTPException(400, detail="Invalid bucket name. Use lowercase letters, numbers, hyphens, and dots. 3-63 characters.")

    try:
        s3 = _get_s3_client()
        create_kwargs = {"Bucket": bucket_name}
        # us-east-1 doesn't accept LocationConstraint
        if region and region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**create_kwargs)
        logger.info("Created S3 bucket: %s in %s", bucket_name, region or "us-east-1")
        return {"name": bucket_name, "region": region or "us-east-1", "created": True}
    except s3.exceptions.BucketAlreadyOwnedByYou:
        return {"name": bucket_name, "region": region or "us-east-1", "created": False, "message": "Bucket already exists and is owned by you"}
    except Exception as exc:
        raise HTTPException(400, detail=f"Failed to create bucket: {exc}")


@router.get("/s3")
async def browse_s3(
    bucket: str = Query(...),
    prefix: str = Query(default=""),
):
    """List contents of an S3 bucket at a given prefix.

    Returns 'directories' (common prefixes) and image files.
    """
    asset_exts = IMAGE_EXTENSIONS | MODEL_EXTENSIONS_WITH_TEXTURES

    # Ensure prefix ends with / if non-empty
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    try:
        s3 = _get_s3_client()
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter="/",
            MaxKeys=500,
        )
    except Exception as exc:
        raise HTTPException(502, detail=f"Failed to browse S3: {exc}")

    dirs = []
    for cp in response.get("CommonPrefixes", []):
        p = cp["Prefix"]
        name = p.rstrip("/").rsplit("/", 1)[-1]
        dirs.append({
            "name": name,
            "type": "directory",
            "prefix": p,
            "uri": f"s3://{bucket}/{p}",
        })

    files = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key == prefix:
            continue
        name = key.rsplit("/", 1)[-1]
        if any(name.lower().endswith(ext) for ext in asset_exts):
            files.append({
                "name": name,
                "type": "file",
                "key": key,
                "size": obj["Size"],
                "uri": f"s3://{bucket}/{key}",
            })

    # Compute parent prefix
    parent = None
    if prefix:
        parts = prefix.rstrip("/").rsplit("/", 1)
        parent = parts[0] + "/" if len(parts) > 1 else ""

    return {
        "bucket": bucket,
        "prefix": prefix,
        "parent": parent,
        "uri": f"s3://{bucket}/{prefix}" if prefix else f"s3://{bucket}/",
        "items": dirs + files,
        "image_count": len(files),
    }
