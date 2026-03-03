"""Extract embedded textures from 3D model files (glTF/GLB).

glTF (.gltf) stores textures as base64-encoded data URIs in JSON.
GLB (.glb) stores textures as binary chunks referenced by byte offsets.
Both are parsed to extract PNG/JPEG image data.
"""

import base64
import io
import json
import logging
import struct
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_textures_from_gltf(file_path: Path) -> list[tuple[str, bytes]]:
    """Extract embedded textures from a .gltf file.

    Returns a list of (filename, image_bytes) tuples.
    """
    try:
        data = json.loads(file_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse glTF file %s: %s", file_path, exc)
        return []

    textures = []
    images = data.get("images", [])

    for i, image_def in enumerate(images):
        uri = image_def.get("uri", "")
        name = image_def.get("name", f"texture_{i}")

        if uri.startswith("data:"):
            # Embedded base64 data URI: data:image/png;base64,iVBOR...
            try:
                header, b64_data = uri.split(",", 1)
                img_bytes = base64.b64decode(b64_data)
                ext = ".png" if "png" in header else ".jpg"
                filename = f"{_sanitize(name)}{ext}"
                textures.append((filename, img_bytes))
                logger.info("Extracted texture from glTF: %s (%d bytes)", filename, len(img_bytes))
            except Exception as exc:
                logger.warning("Failed to decode base64 texture %d in %s: %s", i, file_path, exc)
        elif uri and not uri.startswith("http"):
            # External file reference (relative path)
            ref_path = file_path.parent / uri
            if ref_path.is_file():
                textures.append((ref_path.name, ref_path.read_bytes()))
                logger.info("Found external texture ref: %s", ref_path.name)

    return textures


def extract_textures_from_glb(file_path: Path) -> list[tuple[str, bytes]]:
    """Extract embedded textures from a .glb (binary glTF) file.

    GLB structure:
    - 12-byte header: magic(4) + version(4) + length(4)
    - Chunk 0 (JSON): length(4) + type(4) + data
    - Chunk 1 (BIN):  length(4) + type(4) + data (binary buffer)
    """
    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        logger.warning("Failed to read GLB file %s: %s", file_path, exc)
        return []

    if len(raw) < 12:
        logger.warning("GLB file too small: %s", file_path)
        return []

    # Parse header
    magic, version, total_length = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67:  # 'glTF' in little-endian
        logger.warning("Not a valid GLB file (bad magic): %s", file_path)
        return []

    # Parse chunks
    offset = 12
    json_data = None
    bin_data = None

    while offset < len(raw):
        if offset + 8 > len(raw):
            break
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        chunk_start = offset + 8

        if chunk_type == 0x4E4F534A:  # 'JSON'
            json_data = raw[chunk_start:chunk_start + chunk_length]
        elif chunk_type == 0x004E4942:  # 'BIN\0'
            bin_data = raw[chunk_start:chunk_start + chunk_length]

        offset = chunk_start + chunk_length
        # Align to 4-byte boundary
        if offset % 4:
            offset += 4 - (offset % 4)

    if json_data is None:
        logger.warning("No JSON chunk in GLB: %s", file_path)
        return []

    try:
        gltf = json.loads(json_data)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse GLB JSON chunk: %s: %s", file_path, exc)
        return []

    textures = []
    images = gltf.get("images", [])
    buffer_views = gltf.get("bufferViews", [])

    for i, image_def in enumerate(images):
        name = image_def.get("name", f"texture_{i}")
        mime = image_def.get("mimeType", "image/png")
        ext = ".png" if "png" in mime else ".jpg"

        # Check for bufferView reference (embedded in binary chunk)
        bv_index = image_def.get("bufferView")
        if bv_index is not None and bin_data and bv_index < len(buffer_views):
            bv = buffer_views[bv_index]
            bv_offset = bv.get("byteOffset", 0)
            bv_length = bv.get("byteLength", 0)
            img_bytes = bin_data[bv_offset:bv_offset + bv_length]
            filename = f"{_sanitize(name)}{ext}"
            textures.append((filename, img_bytes))
            logger.info("Extracted texture from GLB: %s (%d bytes)", filename, len(img_bytes))

        # Check for data URI (same as glTF)
        elif "uri" in image_def:
            uri = image_def["uri"]
            if uri.startswith("data:"):
                try:
                    _, b64_data = uri.split(",", 1)
                    img_bytes = base64.b64decode(b64_data)
                    filename = f"{_sanitize(name)}{ext}"
                    textures.append((filename, img_bytes))
                except Exception as exc:
                    logger.warning("Failed to decode base64 in GLB %s: %s", file_path, exc)

    return textures


def extract_textures(file_path: Path) -> list[tuple[str, bytes]]:
    """Extract textures from a 3D model file. Auto-detects format by extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".gltf":
        return extract_textures_from_gltf(file_path)
    elif suffix == ".glb":
        return extract_textures_from_glb(file_path)
    else:
        logger.warning("Unsupported model format for texture extraction: %s", suffix)
        return []


def _sanitize(name: str) -> str:
    """Sanitize a texture name for use as a filename."""
    import re
    name = re.sub(r"[^\w\s.-]", "", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    return name[:60] or "texture"
