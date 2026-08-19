"""Model Detector — auto-detect model configuration from HuggingFace repos.

Given a HuggingFace repo URL, inspects the repository metadata (without
downloading the full model) to determine:
  - Library (diffusers, transformers)
  - Loader class (AutoPipelineForText2Image, AutoModelForImageSegmentation, etc.)
  - Predictor type (text_to_image, image_upscale, background_removal, etc.)
  - License
  - VRAM requirements (estimated from model size)
  - Whether authentication is required (gated repo)

This enables the "Add Custom Model" wizard — users provide a repo URL,
the system auto-fills the catalog entry, user reviews and confirms.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def detect_from_hf_repo(repo_id: str, hf_token: str | None = None) -> dict:
    """Inspect a HuggingFace repo and return a pre-filled catalog entry.

    Does NOT download the model weights — only fetches lightweight metadata
    (config.json, model_index.json, README, repo info).

    Args:
        repo_id: HuggingFace repo ID (e.g., "black-forest-labs/FLUX.1-schnell")
        hf_token: Optional token for gated repos (used for this API call only)

    Returns:
        dict with a pre-filled catalog entry ready for user review
    """
    try:
        from huggingface_hub import HfApi, hf_hub_download, model_info
    except ImportError:
        raise RuntimeError("huggingface_hub is required. Install with: pip install huggingface_hub")

    api = HfApi()

    # Fetch repo metadata
    try:
        info = api.model_info(repo_id, token=hf_token)
    except Exception as e:
        if "401" in str(e) or "403" in str(e):
            raise ValueError(
                f"Repository '{repo_id}' requires authentication. "
                f"Provide a HuggingFace token to access this model."
            )
        raise ValueError(f"Could not access repository '{repo_id}': {e}")

    # Extract basic info
    label = info.modelId.split("/")[-1].replace("-", " ").title()
    provider = info.modelId.split("/")[0] if "/" in info.modelId else "Unknown"
    license_info = _extract_license(info)
    is_gated = info.gated if hasattr(info, "gated") else False
    tags = info.tags or []
    pipeline_tag = info.pipeline_tag or ""
    library_name = info.library_name or ""

    # Determine library + loader + predictor from metadata
    invoke_config = _detect_invoke_config(
        repo_id, info, tags, pipeline_tag, library_name, hf_token
    )

    # Estimate VRAM from model size
    vram_gb = _estimate_vram(info)

    # Determine category and studio
    category, studio = _detect_category(pipeline_tag, invoke_config.get("predictor_type", ""))

    # Determine offload strategy based on VRAM
    if vram_gb >= 24:
        invoke_config["enable_model_cpu_offload"] = True
        invoke_config.pop("enable_cpu_offload", None)
    elif vram_gb >= 12:
        invoke_config["enable_model_cpu_offload"] = True
        invoke_config.pop("enable_cpu_offload", None)
    else:
        invoke_config.pop("enable_cpu_offload", None)

    # Concurrency: large diffusion models = 1, lightweight = 4
    if invoke_config.get("library") == "diffusers" and vram_gb >= 8:
        invoke_config["max_concurrent_invocations"] = 1
    elif vram_gb >= 12:
        invoke_config["max_concurrent_invocations"] = 1
    else:
        invoke_config["max_concurrent_invocations"] = 4

    # Typical latency estimate
    if invoke_config.get("library") == "diffusers":
        steps = invoke_config.get("input_fields", {}).get("num_inference_steps", {}).get("default", 20)
        # Rough: ~1-5s per step depending on model size
        sec_per_step = max(1, vram_gb / 6)
        invoke_config["typical_latency_seconds"] = int(steps * sec_per_step)
    else:
        invoke_config["typical_latency_seconds"] = max(3, vram_gb)

    # Instance recommendation — match VRAM to GPU capacity
    # Single GPU: g5.xlarge (24GB A10G), g6e.xlarge (48GB L40S)
    # Multi-GPU: g6e.12xlarge (4×48=192GB), g6e.48xlarge (8×48=384GB)
    if vram_gb > 192:
        recommended = "ml.g6e.48xlarge"
        instance_costs = {"ml.g6e.48xlarge": 125.28}
        invoke_config["enable_model_cpu_offload"] = True
    elif vram_gb > 48:
        recommended = "ml.g6e.12xlarge"
        instance_costs = {"ml.g6e.12xlarge": 31.32}
        invoke_config["enable_model_cpu_offload"] = True
    elif vram_gb > 24:
        recommended = "ml.g6e.xlarge"
        instance_costs = {"ml.g6e.xlarge": 2.61}
        invoke_config["enable_model_cpu_offload"] = True
    elif vram_gb > 12:
        recommended = "ml.g5.2xlarge"
        instance_costs = {"ml.g5.xlarge": 1.41, "ml.g5.2xlarge": 2.82}
        invoke_config["enable_model_cpu_offload"] = True
    else:
        recommended = "ml.g5.xlarge"
        instance_costs = {"ml.g5.xlarge": 1.41}

    # Python requirements from registry templates (not hardcoded)
    try:
        from backend.services.model_registry import get_registry
        templates = get_registry().get("custom_model_catalog", {}).get("requirement_templates", {})
    except Exception:
        templates = {}

    base_reqs = list(templates.get("base", []))
    lib = invoke_config.get("library", "")
    if lib == "diffusers" and "flux" in repo_id.lower():
        model_reqs = list(templates.get("diffusers_flux", templates.get("diffusers", [])))
    elif lib == "diffusers":
        model_reqs = list(templates.get("diffusers", []))
    elif lib == "transformers":
        model_reqs = list(templates.get("transformers", []))
    elif lib == "realesrgan":
        model_reqs = list(templates.get("realesrgan", []))
    else:
        model_reqs = list(templates.get("transformers", []))  # safe fallback

    # Build the catalog entry
    entry = {
        "label": label,
        "description": f"Auto-detected from {repo_id}. Please review and edit.",
        "category": category,
        "studio": studio,
        "provider": provider,
        "license": license_info,
        "requires_hf_auth": bool(is_gated),
        "hf_license_url": f"https://huggingface.co/{repo_id}" if is_gated else None,
        "source": {
            "type": "huggingface",
            "repo_id": repo_id,
        },
        "requirements": {
            "min_vram_gb": vram_gb,
            "recommended_instance": recommended,
            "min_instance": "ml.g5.xlarge",
            "disk_gb": max(1, int(vram_gb * 1.5)),
        },
        "invoke": invoke_config,
        "pricing": {
            "estimated_cost_per_image": round(0.02 * (vram_gb / 12), 3),
            "instance_cost_per_hour": instance_costs,
        },
        "python_requirements": {
            "base": base_reqs,
            "model": model_reqs,
        },
        "version": "auto-detected",
        "last_updated": "",
        "_detection_metadata": {
            "pipeline_tag": pipeline_tag,
            "library_name": library_name,
            "tags": tags[:20],
            "model_size_gb": round(vram_gb, 1),
        },
    }

    return entry


def _detect_invoke_config(repo_id, info, tags, pipeline_tag, library_name, token=None) -> dict:
    """Determine the invoke configuration from repo metadata."""

    # Check for diffusers model (has model_index.json)
    if library_name == "diffusers" or "diffusers" in tags:
        loader_class = _detect_diffusers_class(repo_id, token)
        predictor = _pipeline_tag_to_predictor(pipeline_tag, "diffusers")
        return {
            "library": "diffusers",
            "loader_class": loader_class,
            "torch_dtype": "bfloat16" if "flux" in repo_id.lower() else "float16",
            "enable_cpu_offload": True,
            "predictor_type": predictor,
            "input_fields": _default_input_fields(predictor),
            "output_type": "base64_png" if "video" not in predictor else "base64_mp4",
            "supports_negative_prompt": "stable-diffusion" in repo_id.lower(),
            "max_prompt_length": 2048,
            "typical_latency_seconds": 15,
        }

    # Check for transformers model (has config.json)
    if library_name == "transformers" or "transformers" in tags:
        loader_class, task = _detect_transformers_class(repo_id, pipeline_tag, token)
        predictor = _pipeline_tag_to_predictor(pipeline_tag, "transformers")
        config = {
            "library": "transformers",
            "predictor_type": predictor,
            "input_fields": _default_input_fields(predictor),
            "output_type": "base64_png",
            "typical_latency_seconds": 3,
        }
        if task:
            config["loader_class"] = "pipeline"
            config["loader_task"] = task
        else:
            config["loader_class"] = loader_class
        return config

    # Fallback: try diffusers if pipeline_tag suggests image generation
    if pipeline_tag in ("text-to-image", "image-to-image"):
        return {
            "library": "diffusers",
            "loader_class": "AutoPipelineForText2Image",
            "torch_dtype": "float16",
            "predictor_type": "text_to_image",
            "input_fields": _default_input_fields("text_to_image"),
            "output_type": "base64_png",
            "max_prompt_length": 2048,
            "typical_latency_seconds": 10,
        }

    # Unknown — return best guess
    return {
        "library": "diffusers",
        "loader_class": "AutoPipelineForText2Image",
        "torch_dtype": "float16",
        "predictor_type": "text_to_image",
        "input_fields": _default_input_fields("text_to_image"),
        "output_type": "base64_png",
        "typical_latency_seconds": 10,
        "_warning": "Could not auto-detect model type. Please verify the invoke configuration.",
    }


def _detect_diffusers_class(repo_id, token=None) -> str:
    """Detect the diffusers pipeline class from model_index.json."""
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(repo_id, "model_index.json", token=token)  # nosec B615 -- inspects a user-supplied repo to detect its type; pinning a revision would defeat detection
        with open(path, encoding="utf-8") as f:
            index = json.load(f)
        class_name = index.get("_class_name", "")
        if class_name:
            return class_name
    except Exception:
        pass
    return "AutoPipelineForText2Image"


def _detect_transformers_class(repo_id, pipeline_tag, token=None) -> tuple[str, str]:
    """Detect the transformers model class and task."""
    # Map pipeline_tag to transformers task
    task_map = {
        "depth-estimation": ("pipeline", "depth-estimation"),
        "image-segmentation": ("AutoModelForImageSegmentation", ""),
        "image-classification": ("pipeline", "image-classification"),
        "object-detection": ("pipeline", "object-detection"),
        "text-to-image": ("pipeline", "text-to-image"),
    }
    if pipeline_tag in task_map:
        return task_map[pipeline_tag]

    # Try reading config.json for model_type
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(repo_id, "config.json", token=token)  # nosec B615 -- inspects a user-supplied repo to detect its type; pinning a revision would defeat detection
        with open(path, encoding="utf-8") as f:
            config = json.load(f)
        architectures = config.get("architectures", [])
        if architectures:
            return (architectures[0], "")
    except Exception:
        pass

    return ("AutoModel", "")


def _pipeline_tag_to_predictor(pipeline_tag: str, library: str) -> str:
    """Map HuggingFace pipeline_tag to our predictor_type."""
    mapping = {
        "text-to-image": "text_to_image",
        "image-to-image": "text_to_image",
        "text-to-video": "image_to_video",
        "image-to-video": "image_to_video",
        "depth-estimation": "depth_estimation",
        "image-segmentation": "background_removal",
        "image-classification": "utility",
        "object-detection": "segmentation",
        "image-feature-extraction": "utility",
    }
    return mapping.get(pipeline_tag, "text_to_image")


def _default_input_fields(predictor_type: str) -> dict:
    """Return default input fields for a predictor type."""
    if predictor_type == "text_to_image":
        return {
            "prompt": {"type": "string", "required": True},
            "width": {"type": "int", "default": 1024},
            "height": {"type": "int", "default": 1024},
            "num_inference_steps": {"type": "int", "default": 20},
            "guidance_scale": {"type": "float", "default": 7.5},
            "seed": {"type": "int", "required": False},
        }
    elif predictor_type in ("image_upscale", "background_removal", "depth_estimation", "face_restoration"):
        return {
            "image": {"type": "base64_png", "required": True},
        }
    elif predictor_type == "segmentation":
        return {
            "image": {"type": "base64_png", "required": True},
            "points": {"type": "list", "required": False},
            "labels": {"type": "list", "required": False},
        }
    elif predictor_type == "image_to_video":
        return {
            "image": {"type": "base64_png", "required": True},
            "num_frames": {"type": "int", "default": 14},
            "fps": {"type": "int", "default": 7},
        }
    return {"prompt": {"type": "string", "required": True}}


def _extract_license(info) -> str:
    """Extract license from model info."""
    if hasattr(info, "card_data") and info.card_data and hasattr(info.card_data, "license"):
        return info.card_data.license or "Unknown"
    # Check tags for license
    for tag in (info.tags or []):
        if tag.startswith("license:"):
            return tag.replace("license:", "")
    return "Unknown"


def _estimate_vram(info) -> int:
    """Estimate VRAM requirement from model size."""
    # Try safetensors metadata for parameter count
    if hasattr(info, "safetensors") and info.safetensors:
        total = info.safetensors.get("total", 0)
        if total > 0:
            # fp16: ~2 bytes per parameter
            gb = (total * 2) / (1024 ** 3)
            return max(2, int(gb + 2))  # Add 2GB overhead

    # Fallback: estimate from siblings (file sizes)
    try:
        total_size = sum(
            s.size for s in (info.siblings or [])
            if s.rfilename.endswith(('.safetensors', '.bin', '.pth', '.pt'))
        )
        if total_size > 0:
            gb = total_size / (1024 ** 3)
            return max(2, int(gb + 2))
    except Exception:
        pass

    return 8  # Safe default


def _detect_category(pipeline_tag: str, predictor_type: str) -> tuple[str, str]:
    """Determine the category and studio from pipeline_tag."""
    if pipeline_tag in ("text-to-image", "image-to-image"):
        return "image_generation", "image"
    if pipeline_tag in ("text-to-video", "image-to-video"):
        return "video_generation", "video"
    if pipeline_tag == "image-segmentation":
        return "post_processing", "image"
    if pipeline_tag == "depth-estimation":
        return "utility", "image"
    if predictor_type in ("image_upscale", "background_removal", "face_restoration"):
        return "post_processing", "image"
    return "image_generation", "image"  # Default
