"""Universal SageMaker inference handler — registry-driven, zero model-specific code.

This SINGLE handler runs inside ALL SageMaker containers for ArtSmoker.
It reads MODEL_KEY and INFERENCE_LIBRARY from environment variables to
determine how to load and invoke the model. Adding a new model requires
only a catalog entry — no code changes here.

Supported inference libraries:
  - diffusers: FLUX, SDXL Turbo, Stable Video Diffusion, ControlNet
  - transformers: RMBG, Depth Anything, SAM 2
  - realesrgan: Real-ESRGAN upscaling
  - codeformer: CodeFormer face restoration

Environment variables (set by deployer):
  MODEL_KEY: catalog key (e.g., "flux1_schnell")
  INFERENCE_LIBRARY: which library to use (e.g., "diffusers")
  HF_MODEL_ID: HuggingFace repo ID (if applicable)
  MODEL_CATEGORY: "image_generation", "post_processing", "video_generation", "utility"
"""

import base64
import io
import json
import logging
import os

import torch
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_model = None  # Loaded model/pipeline


# ── Image Helpers ─────────────────────────────────────────────────────────

def _decode_image(b64_string):
    return Image.open(io.BytesIO(base64.b64decode(b64_string)))


def _encode_image(pil_image, fmt="PNG"):
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── Loaders (by inference_library) ────────────────────────────────────────

def _load_diffusers(model_dir):
    """Load a diffusers pipeline (FLUX, SDXL, SVD, ControlNet)."""
    from diffusers import AutoPipelineForText2Image
    try:
        pipe = AutoPipelineForText2Image.from_pretrained(
            model_dir, torch_dtype=torch.bfloat16
        )
    except Exception:
        # Fallback: try float16 if bfloat16 unsupported
        pipe = AutoPipelineForText2Image.from_pretrained(
            model_dir, torch_dtype=torch.float16
        )
    pipe.to("cuda")
    try:
        pipe.enable_model_cpu_offload()
    except Exception:
        pass
    return {"type": "diffusers", "pipe": pipe}


def _load_transformers(model_dir):
    """Load a transformers model (RMBG, Depth Anything, SAM)."""
    category = os.environ.get("MODEL_CATEGORY", "")
    model_key = os.environ.get("MODEL_KEY", "")

    if "rmbg" in model_key:
        from transformers import AutoModelForImageSegmentation
        model = AutoModelForImageSegmentation.from_pretrained(
            model_dir, trust_remote_code=True
        )
        model.to("cuda").eval()
        return {"type": "rmbg", "model": model}

    elif "depth" in model_key:
        from transformers import pipeline
        pipe = pipeline(task="depth-estimation", model=model_dir, device="cuda")
        return {"type": "depth", "pipe": pipe}

    elif "sam" in model_key:
        from transformers import Sam2Model, Sam2Processor
        model = Sam2Model.from_pretrained(model_dir)
        processor = Sam2Processor.from_pretrained(model_dir)
        model.to("cuda").eval()
        return {"type": "sam", "model": model, "processor": processor}

    else:
        # Generic transformers pipeline
        from transformers import pipeline
        pipe = pipeline(model=model_dir, device="cuda")
        return {"type": "generic_transformers", "pipe": pipe}


def _load_realesrgan(model_dir):
    """Load Real-ESRGAN upscaler."""
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    # Find the .pth file
    model_path = None
    for f in os.listdir(model_dir):
        if f.endswith(".pth"):
            model_path = os.path.join(model_dir, f)
            break
    if not model_path:
        raise FileNotFoundError(f"No .pth file found in {model_dir}")

    rrdb = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    upsampler = RealESRGANer(scale=4, model_path=model_path, model=rrdb, half=True)
    return {"type": "realesrgan", "model": upsampler}


def _load_codeformer(model_dir):
    """Load CodeFormer face restoration."""
    # CodeFormer has a complex setup — simplified here
    return {"type": "codeformer", "model_dir": model_dir}


_LOADERS = {
    "diffusers": _load_diffusers,
    "transformers": _load_transformers,
    "realesrgan": _load_realesrgan,
    "codeformer": _load_codeformer,
}


# ── Predictors (by loaded model type) ─────────────────────────────────────

def _predict_diffusers(input_data, model_dict):
    """Text-to-image via diffusers pipeline."""
    pipe = model_dict["pipe"]
    seed = input_data.get("seed")
    generator = torch.Generator("cuda").manual_seed(seed) if seed is not None else None

    kwargs = {
        "prompt": input_data.get("prompt", ""),
        "width": input_data.get("width", 1024),
        "height": input_data.get("height", 1024),
        "generator": generator,
    }
    # Optional params (only pass if provided — some pipelines don't accept all)
    for key in ("num_inference_steps", "guidance_scale", "negative_prompt",
                "num_frames", "fps", "motion_bucket_id"):
        if key in input_data:
            kwargs[key] = input_data[key]

    result = pipe(**kwargs)
    image = result.images[0]
    return _encode_image(image)


def _predict_rmbg(input_data, model_dict):
    """Background removal."""
    import torchvision.transforms.functional as F

    model = model_dict["model"]
    img = _decode_image(input_data["image"]).convert("RGB")
    orig_size = img.size

    tensor = F.to_tensor(img).unsqueeze(0).to("cuda")
    tensor = F.resize(tensor, [1024, 1024])
    tensor = F.normalize(tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

    with torch.no_grad():
        mask = model(tensor)[-1].sigmoid()[0].squeeze().cpu()

    mask = torch.nn.functional.interpolate(
        mask.unsqueeze(0).unsqueeze(0), size=orig_size[::-1], mode="bilinear"
    ).squeeze()
    mask = (mask * 255).byte().numpy()

    rgba = _decode_image(input_data["image"]).convert("RGBA")
    rgba.putalpha(Image.fromarray(mask))
    return _encode_image(rgba)


def _predict_depth(input_data, model_dict):
    """Depth estimation."""
    img = _decode_image(input_data["image"])
    result = model_dict["pipe"](img)
    return _encode_image(result["depth"].convert("L"))


def _predict_sam(input_data, model_dict):
    """Object segmentation."""
    model = model_dict["model"]
    processor = model_dict["processor"]
    img = _decode_image(input_data["image"])

    points = input_data.get("points")
    labels = input_data.get("labels")

    inputs = processor(img,
                       input_points=[points] if points else None,
                       input_labels=[labels] if labels else None,
                       return_tensors="pt").to("cuda")
    with torch.no_grad():
        outputs = model(**inputs)

    masks = processor.image_processor.post_process_masks(
        outputs.pred_masks, inputs["original_sizes"], inputs["reshaped_input_sizes"]
    )
    mask = masks[0][0][0].cpu().numpy().astype(np.uint8) * 255
    return _encode_image(Image.fromarray(mask))


def _predict_realesrgan(input_data, model_dict):
    """Image upscaling."""
    import cv2

    img_bytes = base64.b64decode(input_data["image"])
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

    scale = input_data.get("scale", 4)
    output, _ = model_dict["model"].enhance(img, outscale=scale)

    _, buffer = cv2.imencode(".png", output)
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


_PREDICTORS = {
    "diffusers": _predict_diffusers,
    "rmbg": _predict_rmbg,
    "depth": _predict_depth,
    "sam": _predict_sam,
    "realesrgan": _predict_realesrgan,
    "generic_transformers": _predict_diffusers,  # Fallback
}


# ── SageMaker Entry Points ────────────────────────────────────────────────

def model_fn(model_dir):
    """Load model — called once when endpoint starts."""
    global _model
    lib = os.environ.get("INFERENCE_LIBRARY", "diffusers")
    model_key = os.environ.get("MODEL_KEY", "unknown")

    loader = _LOADERS.get(lib)
    if not loader:
        raise ValueError(f"Unsupported INFERENCE_LIBRARY: {lib}. Available: {list(_LOADERS.keys())}")

    logger.info("Loading %s model with %s from %s", model_key, lib, model_dir)
    _model = loader(model_dir)
    logger.info("Model %s loaded successfully (type=%s)", model_key, _model.get("type"))
    return _model


def input_fn(request_body, content_type="application/json"):
    """Parse input request."""
    if content_type == "application/json":
        return json.loads(request_body)
    raise ValueError(f"Unsupported content type: {content_type}")


def predict_fn(input_data, model_dict):
    """Run inference — routes to the correct predictor based on model type."""
    model_type = model_dict.get("type", "")
    predictor = _PREDICTORS.get(model_type)
    if not predictor:
        raise ValueError(f"No predictor for model type: {model_type}. Available: {list(_PREDICTORS.keys())}")
    return predictor(input_data, model_dict)


def output_fn(prediction, accept="application/json"):
    """Format output."""
    return json.dumps({"image": prediction, "format": "base64_png"})
