"""Custom Model Catalog — registry of self-hosted 3rd-party models.

The catalog defines everything needed to download, deploy, and invoke
each model. It follows the same pattern as the Bedrock model registry:
all behavior is driven by data/parameters, not by model-specific code.

Adding a new model = adding a catalog entry here. Zero code changes elsewhere.

The catalog is stored as code defaults (like prompt_templates._DEFAULTS),
with the deployed state tracked in model_registry.json under 'custom_models'.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Deployment Bundles ────────────────────────────────────────────────────
#
# Lightweight models can share a single Amazon SageMaker instance to save costs.
# Heavy models (>12GB VRAM) get their own dedicated instance.
#
# Bundle key → list of model keys that can share one endpoint.

BUNDLES = {
    "enhancement": {
        "label": "Enhancement Bundle",
        "description": "Lightweight post-processing models sharing one GPU instance. Includes upscaling, background removal, and face restoration.",
        "models": ["real_esrgan", "rmbg_2", "codeformer"],
        "recommended_instance": "ml.g5.xlarge",
        "total_vram_gb": 6,  # Combined VRAM of all models
    },
    "utility": {
        "label": "Utility Bundle",
        "description": "Depth estimation and segmentation models sharing one GPU instance.",
        "models": ["depth_anything_v2", "sam2"],
        "recommended_instance": "ml.g5.xlarge",
        "total_vram_gb": 10,
    },
}

# Models that need their own dedicated instance (>12GB VRAM)
DEDICATED_MODELS = {"flux1_schnell", "flux1_dev", "sdxl_turbo", "stable_video_diffusion"}


# ── Catalog: Data-driven model definitions ────────────────────────────────
#
# Each entry contains EVERYTHING needed to:
#   - Download the model (source URLs, auth requirements)
#   - Deploy it (instance type, container, env vars)
#   - Invoke it (input/output format, library, loader class, predictor type)
#   - Display it (label, description, pricing, studio assignment)
#
# The 'invoke' section is passed as environment variables to the Amazon SageMaker
# container, so the universal inference handler knows how to load and run
# the model WITHOUT any model-specific code.

MODEL_CATALOG = {
    # ── Image Generation ──────────────────────────────────────────────

    "flux1_schnell": {
        "label": "FLUX.1 [schnell]",
        "description": "Fast text-to-image by Black Forest Labs. 1-4 step generation, Apache 2.0 licensed.",
        "category": "image_generation",
        "studio": "image",
        "provider": "Black Forest Labs",
        "license": "Apache 2.0",
        "requires_hf_auth": True,
        "hf_license_url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell",
        "source": {
            "type": "huggingface",
            "repo_id": "black-forest-labs/FLUX.1-schnell",
        },
        "requirements": {
            "min_vram_gb": 12,
            "recommended_instance": "ml.g5.2xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 25,
        },
        "invoke": {
            "library": "diffusers",
            "loader_class": "FluxPipeline",
            "torch_dtype": "bfloat16",
            "enable_model_cpu_offload": True,
            "enable_vae_slicing": True,
            "enable_vae_tiling": True,
            "predictor_type": "text_to_image",
            "input_fields": {
                "prompt": {"type": "string", "required": True},
                "width": {"type": "int", "default": 1024},
                "height": {"type": "int", "default": 1024},
                "num_inference_steps": {"type": "int", "default": 4},
                "guidance_scale": {"type": "float", "default": 0.0},
                "seed": {"type": "int", "required": False},
            },
            "output_type": "base64_png",
            "supports_negative_prompt": False,
            "max_prompt_length": 2048,
            "typical_latency_seconds": 5,
        },
        "pricing": {
            "estimated_cost_per_image": 0.02,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41, "ml.g5.2xlarge": 2.82},
        },
        "version": "1.0",
        "last_updated": "2024-08-01",
    },

    "flux1_dev": {
        "label": "FLUX.1 [dev]",
        "description": "High-quality text-to-image by Black Forest Labs. Non-commercial license.",
        "category": "image_generation",
        "studio": "image",
        "provider": "Black Forest Labs",
        "license": "FLUX.1 [dev] Non-Commercial License",
        "requires_hf_auth": True,
        "hf_license_url": "https://huggingface.co/black-forest-labs/FLUX.1-dev",
        "source": {
            "type": "huggingface",
            "repo_id": "black-forest-labs/FLUX.1-dev",
        },
        "requirements": {
            "min_vram_gb": 24,
            "recommended_instance": "ml.g5.2xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 35,
        },
        "invoke": {
            "library": "diffusers",
            "loader_class": "FluxPipeline",
            "torch_dtype": "bfloat16",
            "enable_model_cpu_offload": True,
            "enable_vae_slicing": True,
            "enable_vae_tiling": True,
            "predictor_type": "text_to_image",
            "input_fields": {
                "prompt": {"type": "string", "required": True},
                "width": {"type": "int", "default": 1024},
                "height": {"type": "int", "default": 1024},
                "num_inference_steps": {"type": "int", "default": 28},
                "guidance_scale": {"type": "float", "default": 3.5},
                "seed": {"type": "int", "required": False},
            },
            "output_type": "base64_png",
            "supports_negative_prompt": False,
            "max_prompt_length": 2048,
            "typical_latency_seconds": 15,
        },
        "pricing": {
            "estimated_cost_per_image": 0.06,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41, "ml.g5.2xlarge": 1.52},
        },
        "version": "1.0",
        "last_updated": "2024-08-01",
    },

    "sdxl_turbo": {
        "label": "SDXL Turbo",
        "description": "Ultra-fast 1-step image generation by Stability AI.",
        "category": "image_generation",
        "studio": "image",
        "provider": "Stability AI",
        "license": "Stability AI Non-Commercial Community License",
        "requires_hf_auth": False,
        "source": {
            "type": "huggingface",
            "repo_id": "stabilityai/sdxl-turbo",
        },
        "requirements": {
            "min_vram_gb": 8,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 15,
        },
        "invoke": {
            "library": "diffusers",
            "loader_class": "AutoPipelineForText2Image",
            "torch_dtype": "float16",
            "loader_variant": "fp16",
            "predictor_type": "text_to_image",
            "input_fields": {
                "prompt": {"type": "string", "required": True},
                "width": {"type": "int", "default": 512},
                "height": {"type": "int", "default": 512},
                "num_inference_steps": {"type": "int", "default": 1},
                "guidance_scale": {"type": "float", "default": 0.0},
                "seed": {"type": "int", "required": False},
            },
            "output_type": "base64_png",
            "supports_negative_prompt": False,
            "max_prompt_length": 2048,
            "typical_latency_seconds": 2,
        },
        "pricing": {
            "estimated_cost_per_image": 0.01,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41},
        },
        "version": "1.0",
        "last_updated": "2023-11-28",
    },

    # ── Image Enhancement ─────────────────────────────────────────────

    "real_esrgan": {
        "label": "Real-ESRGAN (4x Upscale)",
        "description": "AI super-resolution upscaling. Free alternative to Stability AI Creative Upscale ($0.60/img).",
        "category": "post_processing",
        "studio": "image",
        "provider": "Xinntao",
        "license": "BSD-3-Clause",
        "requires_hf_auth": False,
        "source": {
            "type": "github_release",
            "repo": "xinntao/Real-ESRGAN",
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        },
        "requirements": {
            "min_vram_gb": 2,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 1,
        },
        "invoke": {
            "library": "realesrgan",
            "predictor_type": "image_upscale",
            "input_fields": {
                "image": {"type": "base64_png", "required": True},
                "scale": {"type": "int", "default": 4},
            },
            "output_type": "base64_png",
            "typical_latency_seconds": 3,
        },
        "pricing": {
            "estimated_cost_per_image": 0.01,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41},
        },
        "version": "0.1.0",
        "last_updated": "2021-07-20",
    },

    "rmbg_2": {
        "label": "RMBG-2.0 (Background Removal)",
        "description": "AI background removal by BRIA. Free alternative to Stability AI Remove BG ($0.07/img).",
        "category": "post_processing",
        "studio": "image",
        "provider": "BRIA AI",
        "license": "CC-BY-NC-4.0",
        "requires_hf_auth": True,
        "hf_license_url": "https://huggingface.co/briaai/RMBG-2.0",
        "source": {
            "type": "huggingface",
            "repo_id": "briaai/RMBG-2.0",
        },
        "requirements": {
            "min_vram_gb": 2,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 2,
        },
        "invoke": {
            "library": "transformers",
            "loader_class": "AutoModelForImageSegmentation",
            "trust_remote_code": True,
            "predictor_type": "background_removal",
            "input_fields": {
                "image": {"type": "base64_png", "required": True},
            },
            "output_type": "base64_png_rgba",
            "typical_latency_seconds": 2,
        },
        "pricing": {
            "estimated_cost_per_image": 0.005,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41},
        },
        "version": "2.0",
        "last_updated": "2024-06-15",
    },

    "codeformer": {
        "label": "CodeFormer (Face Restoration)",
        "description": "AI face restoration — fixes AI-generated face artifacts.",
        "category": "post_processing",
        "studio": "image",
        "provider": "Shangchen Zhou et al.",
        "license": "NTU S-Lab License 1.0 (research)",
        "requires_hf_auth": False,
        "source": {
            "type": "github_release",
            "repo": "sczhou/CodeFormer",
            "url": "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth",
        },
        "requirements": {
            "min_vram_gb": 2,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 1,
        },
        "invoke": {
            "library": "codeformer",
            "predictor_type": "face_restoration",
            "input_fields": {
                "image": {"type": "base64_png", "required": True},
                "fidelity": {"type": "float", "default": 0.7},
            },
            "output_type": "base64_png",
            "typical_latency_seconds": 3,
        },
        "pricing": {
            "estimated_cost_per_image": 0.01,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41},
        },
        "version": "0.1.0",
        "last_updated": "2022-12-15",
    },

    # ── Utility / Composition ─────────────────────────────────────────

    "depth_anything_v2": {
        "label": "Depth Anything v2",
        "description": "Monocular depth estimation — generates depth maps for 3D effects.",
        "category": "utility",
        "studio": "image",
        "provider": "DepthAnything Team",
        "license": "CC-BY-NC-4.0",
        "requires_hf_auth": False,
        "source": {
            "type": "huggingface",
            "repo_id": "depth-anything/Depth-Anything-V2-Large",
        },
        "requirements": {
            "min_vram_gb": 4,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 3,
        },
        "invoke": {
            "library": "transformers",
            "loader_class": "pipeline",
            "loader_task": "depth-estimation",
            "predictor_type": "depth_estimation",
            "input_fields": {
                "image": {"type": "base64_png", "required": True},
            },
            "output_type": "base64_png_grayscale",
            "typical_latency_seconds": 2,
        },
        "pricing": {
            "estimated_cost_per_image": 0.005,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41},
        },
        "version": "2.0",
        "last_updated": "2024-06-13",
    },

    "sam2": {
        "label": "Segment Anything 2 (SAM 2)",
        "description": "Smart object segmentation by Meta — click to select objects precisely.",
        "category": "utility",
        "studio": "image",
        "provider": "Meta AI",
        "license": "Apache 2.0",
        "requires_hf_auth": False,
        "source": {
            "type": "huggingface",
            "repo_id": "facebook/sam2-hiera-large",
        },
        "requirements": {
            "min_vram_gb": 6,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 5,
        },
        "invoke": {
            "library": "transformers",
            "loader_class": "Sam2Model",
            "processor_class": "Sam2Processor",
            "predictor_type": "segmentation",
            "input_fields": {
                "image": {"type": "base64_png", "required": True},
                "points": {"type": "list", "required": False, "description": "[[x,y], ...] coordinates"},
                "labels": {"type": "list", "required": False, "description": "[1,0,...] foreground/background"},
            },
            "output_type": "base64_png_mask",
            "typical_latency_seconds": 2,
        },
        "pricing": {
            "estimated_cost_per_image": 0.005,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41},
        },
        "version": "2.0",
        "last_updated": "2024-07-29",
    },

    # ── Video Generation ──────────────────────────────────────────────

    "stable_video_diffusion": {
        "label": "Stable Video Diffusion (SVD-XT)",
        "description": "Image-to-video by Stability AI — 25 frames from a single image.",
        "category": "video_generation",
        "studio": "video",
        "provider": "Stability AI",
        "license": "Stability AI Community License",
        "requires_hf_auth": False,
        "source": {
            "type": "huggingface",
            "repo_id": "stabilityai/stable-video-diffusion-img2vid-xt",
        },
        "requirements": {
            "min_vram_gb": 16,
            "recommended_instance": "ml.g5.2xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 20,
        },
        "invoke": {
            "library": "diffusers",
            "loader_class": "StableVideoDiffusionPipeline",
            "torch_dtype": "float16",
            "predictor_type": "image_to_video",
            "input_fields": {
                "image": {"type": "base64_png", "required": True, "description": "Conditioning image"},
                "num_frames": {"type": "int", "default": 14},
                "fps": {"type": "int", "default": 7},
                "motion_bucket_id": {"type": "int", "default": 127},
                "noise_aug_strength": {"type": "float", "default": 0.02},
            },
            "output_type": "base64_mp4",
            "typical_latency_seconds": 60,
        },
        "pricing": {
            "estimated_cost_per_video": 0.25,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41, "ml.g5.2xlarge": 2.82},
        },
        "version": "1.1",
        "last_updated": "2023-11-21",
    },
}


# ── Public API ────────────────────────────────────────────────────────────

def get_catalog() -> dict:
    """Return the full model catalog."""
    return MODEL_CATALOG


def get_catalog_model(model_key: str) -> dict | None:
    """Return a single model from the catalog."""
    return MODEL_CATALOG.get(model_key)


def get_catalog_by_category(category: str) -> dict:
    """Return models filtered by category."""
    return {k: v for k, v in MODEL_CATALOG.items() if v.get("category") == category}


def get_catalog_by_studio(studio: str) -> dict:
    """Return models filtered by studio (image, video)."""
    return {k: v for k, v in MODEL_CATALOG.items() if v.get("studio") == studio}


def get_bundle_for_model(model_key: str) -> str | None:
    """Return the bundle key for a model, or None if it needs a dedicated instance."""
    for bundle_key, bundle in BUNDLES.items():
        if model_key in bundle["models"]:
            return bundle_key
    return None


def get_bundle(bundle_key: str) -> dict | None:
    """Return a bundle definition."""
    return BUNDLES.get(bundle_key)


def get_all_bundles() -> dict:
    """Return all bundle definitions."""
    return BUNDLES


def is_dedicated(model_key: str) -> bool:
    """Check if a model needs its own dedicated instance."""
    return model_key in DEDICATED_MODELS
