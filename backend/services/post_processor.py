"""Post-processing pipeline — background removal, upscaling, and SVG conversion."""

import io
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.services.bedrock_client import invoke_image_model

logger = logging.getLogger(__name__)

# Background-removal methods. "local" is free (rembg + u2net, runs on CPU);
# "bedrock" is the paid Amazon Bedrock SD remover (higher quality, per-call cost).
BG_METHOD_LOCAL = "local"
BG_METHOD_BEDROCK = "bedrock"


def _find_model_key_by_purpose(purpose: str) -> str | None:
    """Find the first enabled model key matching the given purpose from the registry."""
    from backend.services.model_registry import get_enabled_image_models
    for key, cfg in get_enabled_image_models().items():
        if cfg.get("model_purpose") == purpose:
            return key
    return None


# ── Background removal ────────────────────────────────────────────────────

# rembg session is expensive to build (loads the ONNX model) — build once, reuse.
_rembg_session = None


def _get_rembg_session():
    """Lazily build and cache the rembg u2net session.

    u2net is the default rembg model; its weights are Apache-2.0 (commercial-safe)
    and it auto-downloads once to ~/.u2net/, then runs fully offline on CPU.
    """
    global _rembg_session
    if _rembg_session is None:
        from rembg import new_session
        _rembg_session = new_session("u2net")
    return _rembg_session


def remove_background_local(image_bytes: bytes) -> bytes:
    """Remove the background locally with rembg (u2net) — free, on-device, no API cost.

    Args:
        image_bytes: Input PNG image bytes.

    Returns:
        PNG image bytes with the background removed (transparent).
    """
    from rembg import remove

    logger.info("Removing background locally (rembg/u2net) from image (%d bytes).", len(image_bytes))
    # post_process_mask cleans up the alpha edge; force PNG bytes out.
    result = remove(
        image_bytes,
        session=_get_rembg_session(),
        post_process_mask=True,
        force_return_bytes=True,
    )
    logger.info("Background removed locally: input=%d bytes, output=%d bytes.", len(image_bytes), len(result))
    return result


def remove_background_bedrock(image_bytes: bytes) -> bytes:
    """Remove the background via the Amazon Bedrock SD remover (paid, higher quality).

    Uses the registry to find the remove_background model and invokes it
    via the generic image model invoker.

    Args:
        image_bytes: Input PNG image bytes.

    Returns:
        PNG image bytes with the background removed (transparent).
    """
    logger.info("Removing background via Amazon Bedrock from image (%d bytes).", len(image_bytes))
    model_key = _find_model_key_by_purpose("remove_background")
    if not model_key:
        raise RuntimeError("No enabled remove_background model found in registry.")
    result = invoke_image_model(model_key, source_image=image_bytes)
    logger.info("Background removed (Bedrock): input=%d bytes, output=%d bytes.", len(image_bytes), len(result))
    return result


def remove_background(image_bytes: bytes, method: str = BG_METHOD_BEDROCK) -> bytes:
    """Remove the background from a PNG image using the requested method.

    Default is ``"bedrock"`` to preserve the behavior (and cost accounting) of
    existing callers — the generation post-processing toggle and the 3D-prep
    cutout both historically used the paid Bedrock remover. New callers that want
    the free local path pass ``method="local"`` explicitly.

    Args:
        image_bytes: Input PNG image bytes.
        method: ``"local"`` (rembg/u2net, free) or ``"bedrock"`` (paid SD remover).

    Returns:
        PNG image bytes with the background removed (transparent).
    """
    if method == BG_METHOD_LOCAL:
        return remove_background_local(image_bytes)
    return remove_background_bedrock(image_bytes)


# ── Upscaling ─────────────────────────────────────────────────────────

def upscale_image(image_bytes: bytes, prompt: str = "") -> bytes:
    """Upscale an image using the registry's upscale model.

    Args:
        image_bytes: Input PNG image bytes.
        prompt: Optional prompt to guide the upscale quality.

    Returns:
        Upscaled PNG image bytes.
    """
    logger.info("Upscaling image (%d bytes), prompt=%r.", len(image_bytes), prompt[:80] if prompt else "")
    model_key = _find_model_key_by_purpose("upscale_creative")
    if not model_key:
        model_key = _find_model_key_by_purpose("upscale_conservative")
    if not model_key:
        model_key = _find_model_key_by_purpose("upscale_fast")
    if not model_key:
        raise RuntimeError("No enabled upscale model found in registry.")
    result = invoke_image_model(model_key, prompt=prompt or "high quality upscale", source_image=image_bytes)
    logger.info("Upscale complete: input=%d bytes, output=%d bytes.", len(image_bytes), len(result))
    return result


# ── SVG conversion ────────────────────────────────────────────────────────

def _has_command(cmd: str) -> bool:
    """Check whether a CLI command is available on the system PATH."""
    return shutil.which(cmd) is not None


# Tuned tracing params (speckle-filtered, colour-precise). Passed to the vtracer
# binding when the platform's wheel accepts them; some wheels (observed: the
# 0.6.15 macOS-arm64 wheel) segfault when ANY kwarg is passed, so the subprocess
# runner below falls back to vtracer's built-in defaults (which are already
# colour/stacked/spline) if a parameterized run crashes.
_VTRACER_PARAMS = dict(
    filter_speckle=4,
    color_precision=6,
    layer_difference=16,
    corner_threshold=60,
    length_threshold=4.0,
    max_iterations=10,
    splice_threshold=45,
    path_precision=3,
)

# Child-process script: trace PNG→SVG via the vtracer binding. Kept as a module
# invocation string so a native crash (SIGSEGV) is contained in the child and can
# never take down the uvicorn worker. argv: <png> <svg> <params-json|"">.
_VTRACER_CHILD = (
    "import sys, json, vtracer;"
    "kw = json.loads(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else {};"
    "vtracer.convert_image_to_svg_py(sys.argv[1], sys.argv[2], **kw)"
)


def _run_vtracer_child(png_path: Path, svg_path: Path, params: dict | None) -> bool:
    """Run the vtracer binding in a child process; True iff it exited cleanly.

    Isolating vtracer in a subprocess means a native segfault (some wheels crash
    on kwargs) is contained — the child dies, we detect the non-zero/killed exit
    and fall back, instead of the crash killing the API server.
    """
    import json
    import sys

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _VTRACER_CHILD, str(png_path), str(svg_path),
             json.dumps(params or {})],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("vtracer child process error: %s", exc)
        return False

    if proc.returncode == 0 and svg_path.exists() and svg_path.stat().st_size > 0:
        return True
    logger.warning(
        "vtracer child failed (rc=%s, params=%s): %s",
        proc.returncode, bool(params), (proc.stderr or "").strip()[:200],
    )
    return False


def _convert_with_vtracer(png_path: Path, svg_path: Path) -> bool:
    """Convert PNG→SVG using vtracer (true colour vector tracing).

    Runs vtracer in a subprocess for crash-isolation. Tries the tuned params
    first; if that run fails or crashes (kwargs segfault on some wheels), retries
    with vtracer's built-in defaults (already colour/stacked/spline). Returns
    True on success, False if vtracer is unavailable or both attempts fail.
    """
    try:
        import vtracer  # noqa: F401 — presence check only; work happens in the child
    except ImportError:
        logger.debug("vtracer not installed.")
        # Legacy CLI fallback, if a vtracer binary happens to be on PATH.
        return _convert_with_vtracer_cli(png_path, svg_path)

    # Attempt 1: tuned params. Attempt 2: no params (crash-safe defaults).
    if _run_vtracer_child(png_path, svg_path, _VTRACER_PARAMS):
        logger.info("vtracer conversion succeeded (tuned params): %s", svg_path)
        return True
    if _run_vtracer_child(png_path, svg_path, None):
        logger.info("vtracer conversion succeeded (default params): %s", svg_path)
        return True
    return False


def _convert_with_vtracer_cli(png_path: Path, svg_path: Path) -> bool:
    """Legacy fallback: the vtracer CLI, if present on PATH."""
    if not _has_command("vtracer"):
        logger.debug("vtracer CLI not found on PATH.")
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
        logger.info("vtracer (cli) conversion succeeded: %s", svg_path)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("vtracer CLI conversion failed: %s", exc)
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
    enhanced_prompt: str,
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
        enhanced_prompt: The prompt used for generation (passed to upscaler).
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
            current_bytes = upscale_image(current_bytes, prompt=enhanced_prompt)
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
