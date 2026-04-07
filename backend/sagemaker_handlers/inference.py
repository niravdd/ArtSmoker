"""Universal SageMaker inference handler — fully data-driven from registry.

This SINGLE handler runs inside ALL SageMaker containers for ArtSmoker.
It reads configuration entirely from environment variables (set by the
deployer from the model catalog). ZERO model-specific code — adding a
new model requires only a catalog entry.

Environment variables (set by deployer from catalog['invoke']):
  INVOKE_CONFIG:     JSON-serialized invoke config from catalog
  MODEL_KEY:         Catalog key (for logging)
  INFERENCE_LIBRARY: Which library to use (diffusers, transformers, realesrgan, codeformer)
  PREDICTOR_TYPE:    What kind of prediction (text_to_image, image_upscale, background_removal, etc.)
  LOADER_CLASS:      Python class to load (AutoPipelineForText2Image, AutoModelForImageSegmentation, etc.)
  LOADER_TASK:       Pipeline task for transformers (depth-estimation, etc.)
  TORCH_DTYPE:       Tensor dtype (float16, bfloat16)
  TRUST_REMOTE_CODE: Whether to trust remote code (true/false)
  ENABLE_CPU_OFFLOAD: Enable model CPU offload for memory optimization (true/false)
  PROCESSOR_CLASS:   Processor class for models that need one (Sam2Processor, etc.)
  LOADER_VARIANT:    Model variant (fp16, etc.)
"""

import base64
import io
import json
import logging
import os
import importlib

import torch
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_model = None
_config = {}


# ── Helpers ───────────────────────────────────────────────────────────────

def _decode_image(b64_string):
    return Image.open(io.BytesIO(base64.b64decode(b64_string)))


def _encode_image(pil_image, fmt="PNG"):
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _get_env(key, default=""):
    return os.environ.get(key, default)


def _get_env_bool(key, default=False):
    return _get_env(key, str(default)).lower() in ("true", "1", "yes")


def _get_torch_dtype():
    dtype_str = _get_env("TORCH_DTYPE", "float16")
    return {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}.get(dtype_str, torch.float16)


def _import_class(module_path, class_name):
    """Dynamically import a class from a module."""
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


# ── Loaders (by INFERENCE_LIBRARY) ────────────────────────────────────────
# Each loader reads its configuration from environment variables.
# No model-specific branching — everything is parameterized.

def _load_diffusers(model_dir):
    """Load any diffusers pipeline — the specific class comes from LOADER_CLASS env."""
    loader_class_name = _get_env("LOADER_CLASS", "AutoPipelineForText2Image")
    variant = _get_env("LOADER_VARIANT") or None

    PipelineClass = _import_class("diffusers", loader_class_name)

    kwargs = {"torch_dtype": _get_torch_dtype()}
    if variant:
        kwargs["variant"] = variant

    try:
        pipe = PipelineClass.from_pretrained(model_dir, **kwargs)
    except Exception:
        # Fallback: try without variant
        pipe = PipelineClass.from_pretrained(model_dir, torch_dtype=_get_torch_dtype())

    pipe.to("cuda")

    if _get_env_bool("ENABLE_CPU_OFFLOAD"):
        try:
            pipe.enable_model_cpu_offload()
        except Exception:
            pass

    return {"library": "diffusers", "pipe": pipe}


def _load_transformers(model_dir):
    """Load any transformers model — class/task from env vars."""
    loader_class = _get_env("LOADER_CLASS", "pipeline")
    loader_task = _get_env("LOADER_TASK", "")
    trust_remote = _get_env_bool("TRUST_REMOTE_CODE")
    processor_class = _get_env("PROCESSOR_CLASS", "")

    if loader_class == "pipeline":
        from transformers import pipeline
        kwargs = {"model": model_dir, "device": "cuda"}
        if loader_task:
            kwargs["task"] = loader_task
        pipe = pipeline(**kwargs)
        return {"library": "transformers", "predictor": "pipeline", "pipe": pipe}

    else:
        # Load specific model class
        ModelClass = _import_class("transformers", loader_class)
        kwargs = {}
        if trust_remote:
            kwargs["trust_remote_code"] = True
        model = ModelClass.from_pretrained(model_dir, **kwargs)
        model.to("cuda").eval()

        result = {"library": "transformers", "predictor": "model", "model": model}

        # Load processor if specified
        if processor_class:
            ProcessorClass = _import_class("transformers", processor_class)
            processor = ProcessorClass.from_pretrained(model_dir)
            result["processor"] = processor

        return result


def _load_realesrgan(model_dir):
    """Load Real-ESRGAN — finds .pth file in model_dir."""
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    model_path = None
    for f in os.listdir(model_dir):
        if f.endswith(".pth"):
            model_path = os.path.join(model_dir, f)
            break
    if not model_path:
        raise FileNotFoundError(f"No .pth file found in {model_dir}")

    rrdb = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    upsampler = RealESRGANer(scale=4, model_path=model_path, model=rrdb, half=True)
    return {"library": "realesrgan", "model": upsampler}


def _load_codeformer(model_dir):
    """Load CodeFormer face restoration."""
    return {"library": "codeformer", "model_dir": model_dir}


_LOADERS = {
    "diffusers": _load_diffusers,
    "transformers": _load_transformers,
    "realesrgan": _load_realesrgan,
    "codeformer": _load_codeformer,
}


# ── Predictors (by PREDICTOR_TYPE) ────────────────────────────────────────
# Each predictor handles a category of inference. The specific behavior
# is parameterized by the input_fields from the catalog.

def _predict_text_to_image(input_data, model_dict):
    """Generate an image from a text prompt (diffusers pipeline)."""
    pipe = model_dict["pipe"]
    seed = input_data.get("seed")
    generator = torch.Generator("cuda").manual_seed(seed) if seed is not None else None

    # Build kwargs from input_data — only pass fields the pipeline accepts
    kwargs = {"generator": generator}
    for key in ("prompt", "width", "height", "num_inference_steps", "guidance_scale",
                "negative_prompt", "num_frames", "fps", "motion_bucket_id"):
        if key in input_data and input_data[key] is not None:
            kwargs[key] = input_data[key]

    result = pipe(**kwargs)
    return _encode_image(result.images[0])


def _predict_image_to_video(input_data, model_dict):
    """Generate video frames from a conditioning image (diffusers pipeline)."""
    pipe = model_dict["pipe"]
    img = _decode_image(input_data["image"])

    kwargs = {"image": img}
    for key in ("num_frames", "fps", "motion_bucket_id", "noise_aug_strength"):
        if key in input_data:
            kwargs[key] = input_data[key]

    frames = pipe(**kwargs).frames[0]

    # Encode frames as base64 PNGs
    encoded_frames = [_encode_image(f) for f in frames]
    return json.dumps({"frames": encoded_frames, "fps": input_data.get("fps", 7)})


def _predict_image_upscale(input_data, model_dict):
    """Upscale an image (Real-ESRGAN)."""
    import cv2

    img_bytes = base64.b64decode(input_data["image"])
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

    scale = input_data.get("scale", 4)
    output, _ = model_dict["model"].enhance(img, outscale=scale)

    _, buffer = cv2.imencode(".png", output)
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def _predict_background_removal(input_data, model_dict):
    """Remove background from image (transformers segmentation model)."""
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


def _predict_depth_estimation(input_data, model_dict):
    """Generate depth map (transformers pipeline)."""
    img = _decode_image(input_data["image"])
    result = model_dict["pipe"](img)
    return _encode_image(result["depth"].convert("L"))


def _predict_segmentation(input_data, model_dict):
    """Segment objects in image (SAM-style model with processor)."""
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


def _predict_face_restoration(input_data, model_dict):
    """Restore faces in image (CodeFormer)."""
    # CodeFormer has complex dependencies — simplified placeholder
    return _encode_image(_decode_image(input_data["image"]))


_PREDICTORS = {
    "text_to_image": _predict_text_to_image,
    "image_to_video": _predict_image_to_video,
    "image_upscale": _predict_image_upscale,
    "background_removal": _predict_background_removal,
    "depth_estimation": _predict_depth_estimation,
    "segmentation": _predict_segmentation,
    "face_restoration": _predict_face_restoration,
}


# ── SageMaker Entry Points ────────────────────────────────────────────────

def model_fn(model_dir):
    """Load model — called once when endpoint starts.

    Reads INFERENCE_LIBRARY from env to pick the right loader.
    The loader reads its specific params (LOADER_CLASS, TORCH_DTYPE, etc.) from env.
    """
    global _model, _config
    library = _get_env("INFERENCE_LIBRARY", "diffusers")
    model_key = _get_env("MODEL_KEY", "unknown")

    # Load invoke config if provided as JSON
    config_json = _get_env("INVOKE_CONFIG")
    if config_json:
        try:
            _config = json.loads(config_json)
        except Exception:
            _config = {}

    loader = _LOADERS.get(library)
    if not loader:
        raise ValueError(f"Unsupported INFERENCE_LIBRARY: {library}. Available: {list(_LOADERS.keys())}")

    logger.info("Loading %s with library=%s", model_key, library)
    _model = loader(model_dir)
    logger.info("Model %s loaded (library=%s)", model_key, library)
    return _model


def input_fn(request_body, content_type="application/json"):
    """Parse input — supports JSON only."""
    if content_type == "application/json":
        return json.loads(request_body)
    raise ValueError(f"Unsupported content type: {content_type}")


def predict_fn(input_data, model_dict):
    """Run inference — routes to predictor by PREDICTOR_TYPE env var."""
    predictor_type = _get_env("PREDICTOR_TYPE", "text_to_image")
    predictor = _PREDICTORS.get(predictor_type)
    if not predictor:
        raise ValueError(f"Unknown PREDICTOR_TYPE: {predictor_type}. Available: {list(_PREDICTORS.keys())}")

    return predictor(input_data, model_dict)


def output_fn(prediction, accept="application/json"):
    """Format output as JSON."""
    if isinstance(prediction, str) and prediction.startswith("{"):
        return prediction  # Already JSON (e.g., video frames)
    return json.dumps({"image": prediction, "format": "base64_png"})
