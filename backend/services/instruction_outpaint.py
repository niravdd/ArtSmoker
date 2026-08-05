"""Outpaint support for mask-free INSTRUCTION edit models (e.g. Qwen-Image-Edit).

Instruction editors regenerate the whole frame at the input's size — they cannot
grow a canvas. Told to "extend the image", they instead REFRAME (pan/crop) the
scene, losing content (validated 2026-08-05: a bottom-extend request returned the
warrior's legs but cut off her head).

The working recipe (validated on the Ohio g6e.12xl endpoint the same day):
  1. PRE-PAD the source canvas by the requested pixels per edge; fill the new
     band(s) with an edge-average colour + gaussian noise. The fill gives the
     model lighting/palette cues while clearly reading as "unfinished".
  2. Instruct the model to replace ONLY the unfinished band(s) — never say
     "extend the image", which triggers the reframe behaviour.
  3. The model may return a nearby resolution bucket (e.g. 768x1728 → 672x1536);
     RESIZE the result back to the padded canvas size.
  4. BLEND the original source pixels back over the original region with a
     feathered seam at the pad boundary, so the existing image is preserved
     pixel-exact and only the new band is model-generated (matches what users
     expect from mask-based outpaint).

Used by: /api/generate/edit (sync + async completion) and the 3D
"Improve the Source" extend op. Bedrock mask-based outpaint models are
completely unaffected — callers gate on model_purpose == "image_edit".
"""

import io
import logging

logger = logging.getLogger(__name__)

# Feather width (px) for blending the original region back over the result.
_SEAM_FEATHER_PX = 24


def pad_image_for_outpaint(image_bytes: bytes, left: int = 0, right: int = 0,
                           up: int = 0, down: int = 0) -> tuple[bytes, dict]:
    """Expand the canvas by the given pixels per edge, noise-filling new bands.

    Returns (padded_png_bytes, geometry) where geometry records the original
    size/offset needed by blend_original_back(). Directions ≤0 are ignored.
    """
    import numpy as np
    from PIL import Image

    left, right, up, down = (max(0, int(v or 0)) for v in (left, right, up, down))
    src = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = src.size
    new_w, new_h = w + left + right, h + up + down
    geometry = {"orig_w": w, "orig_h": h, "off_x": left, "off_y": up,
                "pad_w": new_w, "pad_h": new_h}
    if (new_w, new_h) == (w, h):
        return image_bytes, geometry

    arr = np.asarray(src, dtype=np.float32)
    canvas = np.zeros((new_h, new_w, 3), dtype=np.float32)
    rng = np.random.default_rng(0)

    def _band(strip, band_h, band_w):
        fill = np.broadcast_to(strip, (band_h, band_w, 3)).copy()
        return np.clip(fill + rng.normal(0, 12, fill.shape), 0, 255)

    # Edge-average strips give the model colour/lighting continuity cues.
    if up:
        canvas[:up, left:left + w] = _band(arr[:8].mean(axis=0, keepdims=True), up, w)
    if down:
        canvas[up + h:, left:left + w] = _band(arr[-8:].mean(axis=0, keepdims=True), down, w)
    if left:
        canvas[:, :left] = _band(arr[:, :8].mean(axis=1, keepdims=True).mean(axis=0, keepdims=True), new_h, left)
    if right:
        canvas[:, left + w:] = _band(arr[:, -8:].mean(axis=1, keepdims=True).mean(axis=0, keepdims=True), new_h, right)
    canvas[up:up + h, left:left + w] = arr

    out = io.BytesIO()
    Image.fromarray(canvas.astype(np.uint8)).save(out, format="PNG")
    logger.info("Outpaint pre-pad: %dx%d -> %dx%d (L%d R%d U%d D%d)",
                w, h, new_w, new_h, left, right, up, down)
    return out.getvalue(), geometry


def build_outpaint_instruction(user_prompt: str, left: int = 0, right: int = 0,
                               up: int = 0, down: int = 0) -> str:
    """Phrase the instruction so the editor completes the band(s) instead of
    reframing. NEVER use 'extend the image' phrasing here."""
    sides = [name for name, v in (("top", up), ("bottom", down),
                                  ("left", left), ("right", right)) if v and v > 0]
    where = ", ".join(sides) if sides else "outer"
    base = (f"Keep the existing image content exactly as it is. Replace ONLY the "
            f"blurry unfinished band at the {where} edge(s) of the image with the "
            f"natural continuation of the scene, matching lighting, colours and style.")
    extra = (user_prompt or "").strip()
    return f"{base} {extra}" if extra else base


def restore_geometry_and_blend(result_bytes: bytes, source_bytes: bytes,
                               geometry: dict) -> bytes:
    """Resize the model output back to the padded canvas and blend the original
    source pixels over the original region with a feathered seam."""
    import numpy as np
    from PIL import Image

    pad_w, pad_h = geometry["pad_w"], geometry["pad_h"]
    ow, oh = geometry["orig_w"], geometry["orig_h"]
    ox, oy = geometry["off_x"], geometry["off_y"]

    result = Image.open(io.BytesIO(result_bytes)).convert("RGB")
    if result.size != (pad_w, pad_h):
        logger.info("Outpaint result %sx%s -> resizing to padded canvas %dx%d",
                    result.size[0], result.size[1], pad_w, pad_h)
        result = result.resize((pad_w, pad_h), Image.LANCZOS)

    src = Image.open(io.BytesIO(source_bytes)).convert("RGB")
    res_arr = np.asarray(result, dtype=np.float32)
    src_arr = np.asarray(src, dtype=np.float32)

    # Alpha mask: 1 inside the original region, feathering to 0 across the seam
    # toward padded bands. Only feather on sides that actually have padding.
    f = _SEAM_FEATHER_PX
    mask = np.ones((oh, ow), dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, f, dtype=np.float32)
    if oy > 0 and oh > f:                       # padded above → feather top edge
        mask[:f, :] *= ramp[:, None]
    if geometry["pad_h"] - oy - oh > 0 and oh > f:   # padded below
        mask[-f:, :] *= ramp[::-1][:, None]
    if ox > 0 and ow > f:                       # padded left
        mask[:, :f] *= ramp[None, :]
    if geometry["pad_w"] - ox - ow > 0 and ow > f:   # padded right
        mask[:, -f:] *= ramp[::-1][None, :]

    region = res_arr[oy:oy + oh, ox:ox + ow]
    blended = src_arr * mask[..., None] + region * (1.0 - mask[..., None])
    res_arr[oy:oy + oh, ox:ox + ow] = blended

    out = io.BytesIO()
    Image.fromarray(np.clip(res_arr, 0, 255).astype(np.uint8)).save(out, format="PNG")
    return out.getvalue()
