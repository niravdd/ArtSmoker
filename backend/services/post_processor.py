"""Post-processing pipeline — background removal, upscaling, and SVG conversion."""

import io
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.services.bedrock_client import invoke_remove_background, invoke_upscale

logger = logging.getLogger(__name__)


# ── Background removal ────────────────────────────────────────────────────

def remove_background(image_bytes: bytes) -> bytes:
    """Remove the background from a PNG image.

    Uses the Stability AI background-removal model via Bedrock.

    Args:
        image_bytes: Input PNG image bytes.

    Returns:
        PNG image bytes with the background removed (transparent).

    Raises:
        Exception: Propagates errors from the Bedrock API.
    """
    logger.info("Removing background from image (%d bytes).", len(image_bytes))
    result = invoke_remove_background(image_bytes)
    logger.info(
        "Background removed: input=%d bytes, output=%d bytes.",
        len(image_bytes),
        len(result),
    )
    return result


# ── Upscaling ─────────────────────────────────────────────────────────────

def upscale_image(image_bytes: bytes, prompt: str = "") -> bytes:
    """Upscale an image using Stability AI Creative Upscale.

    Args:
        image_bytes: Input PNG image bytes.
        prompt: Optional prompt to guide the upscale quality.

    Returns:
        Upscaled PNG image bytes.

    Raises:
        Exception: Propagates errors from the Bedrock API.
    """
    logger.info("Upscaling image (%d bytes), prompt=%r.", len(image_bytes), prompt[:80])
    result = invoke_upscale(image_bytes, prompt)
    logger.info(
        "Upscale complete: input=%d bytes, output=%d bytes.",
        len(image_bytes),
        len(result),
    )
    return result


# ── SVG conversion ────────────────────────────────────────────────────────

def _has_command(cmd: str) -> bool:
    """Check whether a CLI command is available on the system PATH."""
    return shutil.which(cmd) is not None


def _convert_with_vtracer(png_path: Path, svg_path: Path) -> bool:
    """Attempt SVG conversion using vtracer CLI.

    Returns True on success, False if vtracer is unavailable or fails.
    """
    if not _has_command("vtracer"):
        logger.debug("vtracer not found on PATH.")
        return False

    try:
        subprocess.run(
            [
                "vtracer",
                "--input", str(png_path),
                "--output", str(svg_path),
                "--colormode", "color",
                "--hierarchical", "stacked",
                "--filter_speckle", "4",
                "--color_precision", "6",
                "--layer_difference", "16",
                "--corner_threshold", "60",
                "--length_threshold", "4.0",
                "--max_iterations", "10",
                "--splice_threshold", "45",
                "--path_precision", "3",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        logger.info("vtracer conversion succeeded: %s", svg_path)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("vtracer conversion failed: %s", exc)
        return False


def _convert_with_potrace(png_path: Path, svg_path: Path) -> bool:
    """Attempt SVG conversion using potrace CLI (bitmap tracer).

    potrace expects a PBM/PGM/PPM/BMP input, so we convert via Pillow first.
    Returns True on success, False if potrace is unavailable or fails.
    """
    if not _has_command("potrace"):
        logger.debug("potrace not found on PATH.")
        return False

    try:
        from PIL import Image

        # Convert PNG to BMP for potrace input
        img = Image.open(png_path).convert("RGBA")
        # Create a white-background composite for tracing
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        composite = Image.alpha_composite(background, img).convert("L")
        bmp_path = png_path.with_suffix(".bmp")
        composite.save(bmp_path, format="BMP")

        subprocess.run(
            [
                "potrace",
                str(bmp_path),
                "--svg",
                "--output", str(svg_path),
                "--turdsize", "2",
                "--alphamax", "1.0",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )

        # Clean up intermediate BMP
        bmp_path.unlink(missing_ok=True)

        logger.info("potrace conversion succeeded: %s", svg_path)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ImportError) as exc:
        logger.warning("potrace conversion failed: %s", exc)
        return False


def _convert_with_pillow_fallback(png_path: Path, svg_path: Path) -> bool:
    """Create a basic SVG by embedding the PNG as a base64 data URI.

    This is a last-resort fallback when no vector tracing tool is available.
    The result is not a true vector SVG — it embeds the raster image.
    Returns True on success.
    """
    try:
        import base64

        from PIL import Image

        img = Image.open(png_path)
        width, height = img.size

        png_bytes = png_path.read_bytes()
        b64_data = base64.b64encode(png_bytes).decode("ascii")

        svg_content = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">\n'
            f'  <image width="{width}" height="{height}" '
            f'xlink:href="data:image/png;base64,{b64_data}"/>\n'
            f'</svg>\n'
        )

        svg_path.write_text(svg_content, encoding="utf-8")
        logger.info(
            "Pillow fallback SVG created (embedded raster): %s (%d bytes)",
            svg_path,
            len(svg_content),
        )
        return True
    except (ImportError, OSError) as exc:
        logger.error("Pillow fallback SVG conversion failed: %s", exc)
        return False


def convert_to_svg(png_bytes: bytes, output_path: Path) -> Path:
    """Convert PNG bytes to an SVG file.

    Attempts conversion in order of preference:
    1. vtracer (high-quality colour vector tracing)
    2. potrace (monochrome bitmap tracing)
    3. Pillow fallback (embeds raster PNG inside an SVG wrapper)

    Args:
        png_bytes: The source PNG image as bytes.
        output_path: Desired output path for the SVG file.

    Returns:
        The path to the created SVG file.

    Raises:
        RuntimeError: If all conversion methods fail.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write PNG to a temp file for CLI tools
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(png_bytes)
        tmp_png_path = Path(tmp.name)

    try:
        # Try vtracer first
        if _convert_with_vtracer(tmp_png_path, output_path):
            return output_path

        # Fall back to potrace
        if _convert_with_potrace(tmp_png_path, output_path):
            return output_path

        # Last resort: Pillow-based embedded raster SVG
        if _convert_with_pillow_fallback(tmp_png_path, output_path):
            return output_path

        raise RuntimeError(
            "All SVG conversion methods failed. Ensure vtracer, potrace, "
            "or Pillow is available."
        )
    finally:
        # Clean up temp file
        tmp_png_path.unlink(missing_ok=True)


# ── Pipeline orchestrator ─────────────────────────────────────────────────

def process_asset(
    image_bytes: bytes,
    refined_prompt: str,
    remove_bg: bool = True,
    do_upscale: bool = False,
    do_svg: bool = True,
    svg_output_path: Path | None = None,
) -> tuple[bytes, Path | None]:
    """Run the full post-processing pipeline on a generated image.

    Steps are applied in order:
    1. Background removal (if remove_bg=True)
    2. Upscaling (if do_upscale=True)
    3. SVG conversion (if do_svg=True and svg_output_path is provided)

    Args:
        image_bytes: Raw PNG bytes from the image generator.
        refined_prompt: The prompt used for generation (passed to upscaler).
        remove_bg: Whether to remove the background.
        do_upscale: Whether to upscale the image.
        do_svg: Whether to convert to SVG.
        svg_output_path: File path for the SVG output (required if do_svg=True).

    Returns:
        A tuple of (final_png_bytes, svg_path_or_none).
    """
    current_bytes = image_bytes
    svg_path: Path | None = None

    logger.info(
        "Post-processing pipeline: remove_bg=%s, upscale=%s, svg=%s",
        remove_bg,
        do_upscale,
        do_svg,
    )

    # Step 1: Background removal
    if remove_bg:
        try:
            current_bytes = remove_background(current_bytes)
        except Exception:
            logger.exception("Background removal failed; continuing with original image.")

    # Step 2: Upscaling
    if do_upscale:
        try:
            current_bytes = upscale_image(current_bytes, prompt=refined_prompt)
        except Exception:
            logger.exception("Upscaling failed; continuing with current image.")

    # Step 3: SVG conversion
    if do_svg and svg_output_path is not None:
        try:
            svg_path = convert_to_svg(current_bytes, svg_output_path)
        except Exception:
            logger.exception("SVG conversion failed; skipping SVG output.")
            svg_path = None

    logger.info(
        "Post-processing complete: final_size=%d bytes, svg=%s",
        len(current_bytes),
        svg_path,
    )
    return current_bytes, svg_path
