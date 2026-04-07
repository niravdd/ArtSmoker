"""Custom Model Deployment — manages self-hosted 3rd-party models on SageMaker.

Handles the full lifecycle: catalog → download → deploy → invoke → manage.
Models run on SageMaker Async or Real-time endpoints in the user's AWS account.

Architecture:
  1. Model Catalog: known models with source URLs, requirements, invocation specs
  2. Download: pulls weights from original sources (GitHub/HuggingFace) to user's S3
  3. Deploy: creates SageMaker endpoint from CloudFormation template
  4. Invoke: sends inference requests, polls for async results
  5. Manage: status, redeploy, update, teardown

HuggingFace tokens (for gated models) are used transiently during download
and NEVER stored — passed once to pull weights, then discarded.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Model Catalog ─────────────────────────────────────────────────────────
#
# Each entry defines everything ArtSmoker needs to download, deploy, and
# invoke a model. Source URLs point to the ORIGINAL hosting location
# (GitHub releases, HuggingFace repos) — we never re-host weights.

MODEL_CATALOG = {
    # ── Image Generation ──────────────────────────────────────────────

    "flux1_schnell": {
        "label": "FLUX.1 [schnell]",
        "description": "Fast text-to-image by Black Forest Labs. High quality, Apache 2.0 licensed.",
        "category": "image_generation",
        "studio": "image",
        "provider": "Black Forest Labs",
        "license": "Apache 2.0",
        "requires_hf_auth": False,
        "source": {
            "type": "huggingface",
            "repo_id": "black-forest-labs/FLUX.1-schnell",
            "files": ["flux1-schnell.safetensors"],  # or full repo clone
        },
        "requirements": {
            "min_vram_gb": 12,
            "recommended_instance": "ml.g5.2xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 25,
            "inference_library": "diffusers",
        },
        "invocation": {
            "input_format": {
                "prompt": "string",
                "width": "int (default 1024)",
                "height": "int (default 1024)",
                "num_inference_steps": "int (default 4)",
                "guidance_scale": "float (default 0.0)",
                "seed": "int (optional)",
            },
            "output_format": "base64 PNG image",
            "typical_latency_seconds": 5,
            "supports_negative_prompt": False,
            "max_prompt_length": 2048,
        },
        "pricing": {
            "estimated_cost_per_image": 0.02,  # Based on ~5s on g5.xlarge at $1.41/hr
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41, "ml.g5.2xlarge": 2.82},
        },
        "version": "1.0",
        "last_updated": "2024-08-01",
    },

    "flux1_dev": {
        "label": "FLUX.1 [dev]",
        "description": "High-quality text-to-image by Black Forest Labs. Better than schnell but non-commercial license. Requires HuggingFace license acceptance.",
        "category": "image_generation",
        "studio": "image",
        "provider": "Black Forest Labs",
        "license": "FLUX.1 [dev] Non-Commercial License",
        "requires_hf_auth": True,
        "hf_license_url": "https://huggingface.co/black-forest-labs/FLUX.1-dev",
        "source": {
            "type": "huggingface",
            "repo_id": "black-forest-labs/FLUX.1-dev",
            "files": ["flux1-dev.safetensors"],
        },
        "requirements": {
            "min_vram_gb": 24,
            "recommended_instance": "ml.g5.2xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 35,
            "inference_library": "diffusers",
        },
        "invocation": {
            "input_format": {
                "prompt": "string",
                "width": "int (default 1024)",
                "height": "int (default 1024)",
                "num_inference_steps": "int (default 28)",
                "guidance_scale": "float (default 3.5)",
                "seed": "int (optional)",
            },
            "output_format": "base64 PNG image",
            "typical_latency_seconds": 15,
            "supports_negative_prompt": False,
            "max_prompt_length": 2048,
        },
        "pricing": {
            "estimated_cost_per_image": 0.06,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41, "ml.g5.2xlarge": 2.82},
        },
        "version": "1.0",
        "last_updated": "2024-08-01",
    },

    "sdxl_turbo": {
        "label": "SDXL Turbo",
        "description": "Ultra-fast image generation by Stability AI. 1-4 step generation.",
        "category": "image_generation",
        "studio": "image",
        "provider": "Stability AI",
        "license": "Stability AI Community License",
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
            "inference_library": "diffusers",
        },
        "invocation": {
            "input_format": {
                "prompt": "string",
                "width": "int (default 512)",
                "height": "int (default 512)",
                "num_inference_steps": "int (default 1)",
                "guidance_scale": "float (default 0.0)",
            },
            "output_format": "base64 PNG image",
            "typical_latency_seconds": 2,
            "supports_negative_prompt": False,
            "max_prompt_length": 2048,
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
        "label": "Real-ESRGAN",
        "description": "AI upscaling — 2x/4x super-resolution. Free alternative to Stability AI Creative Upscale.",
        "category": "post_processing",
        "studio": "image",
        "provider": "Xinntao",
        "license": "BSD-3-Clause",
        "requires_hf_auth": False,
        "source": {
            "type": "github_release",
            "repo": "xinntao/Real-ESRGAN",
            "asset_pattern": "RealESRGAN_x4plus.pth",
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        },
        "requirements": {
            "min_vram_gb": 2,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 1,
            "inference_library": "realesrgan",
        },
        "invocation": {
            "input_format": {
                "image": "base64 PNG",
                "scale": "int (2 or 4, default 4)",
            },
            "output_format": "base64 PNG image",
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
        "description": "AI background removal by BRIA. Free alternative to Stability AI Remove Background.",
        "category": "post_processing",
        "studio": "image",
        "provider": "BRIA AI",
        "license": "Apache 2.0",
        "requires_hf_auth": False,
        "source": {
            "type": "huggingface",
            "repo_id": "briaai/RMBG-2.0",
        },
        "requirements": {
            "min_vram_gb": 2,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 2,
            "inference_library": "transformers",
        },
        "invocation": {
            "input_format": {"image": "base64 PNG"},
            "output_format": "base64 PNG image (transparent background)",
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
        "description": "AI face restoration and enhancement. Fixes AI-generated face artifacts.",
        "category": "post_processing",
        "studio": "image",
        "provider": "Shangchen Zhou et al.",
        "license": "Non-Commercial Research",
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
            "inference_library": "codeformer",
        },
        "invocation": {
            "input_format": {
                "image": "base64 PNG",
                "fidelity": "float (0.0-1.0, default 0.7)",
            },
            "output_format": "base64 PNG image",
            "typical_latency_seconds": 3,
        },
        "pricing": {
            "estimated_cost_per_image": 0.01,
            "instance_cost_per_hour": {"ml.g5.xlarge": 1.41},
        },
        "version": "0.1.0",
        "last_updated": "2022-12-15",
    },

    # ── Composition / Control ─────────────────────────────────────────

    "depth_anything_v2": {
        "label": "Depth Anything v2",
        "description": "Monocular depth estimation. Generates depth maps for ControlNet or 3D effects.",
        "category": "utility",
        "studio": "image",
        "provider": "DepthAnything Team",
        "license": "Apache 2.0",
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
            "inference_library": "transformers",
        },
        "invocation": {
            "input_format": {"image": "base64 PNG"},
            "output_format": "base64 PNG depth map (grayscale)",
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
        "description": "Smart object segmentation by Meta. Click or prompt to select objects precisely.",
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
            "min_vram_gb": 8,
            "recommended_instance": "ml.g5.xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 5,
            "inference_library": "transformers",
        },
        "invocation": {
            "input_format": {
                "image": "base64 PNG",
                "points": "list of [x, y] coordinates (optional)",
                "labels": "list of 0/1 (foreground/background) per point",
                "text_prompt": "string (optional)",
            },
            "output_format": "base64 PNG mask",
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
        "label": "Stable Video Diffusion (SVD)",
        "description": "Image-to-video generation by Stability AI. 14-25 frames from a single image.",
        "category": "video_generation",
        "studio": "video",
        "provider": "Stability AI",
        "license": "Stability AI Community License",
        "requires_hf_auth": True,
        "hf_license_url": "https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt",
        "source": {
            "type": "huggingface",
            "repo_id": "stabilityai/stable-video-diffusion-img2vid-xt",
        },
        "requirements": {
            "min_vram_gb": 16,
            "recommended_instance": "ml.g5.2xlarge",
            "min_instance": "ml.g5.xlarge",
            "disk_gb": 20,
            "inference_library": "diffusers",
        },
        "invocation": {
            "input_format": {
                "image": "base64 PNG (conditioning image)",
                "num_frames": "int (14 or 25, default 14)",
                "fps": "int (default 7)",
                "motion_bucket_id": "int (default 127)",
                "noise_aug_strength": "float (default 0.02)",
            },
            "output_format": "base64 MP4 video or list of base64 PNG frames",
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


# ── Deployment Status ─────────────────────────────────────────────────────

class DeploymentStatus:
    NOT_DEPLOYED = "not_deployed"
    DOWNLOADING = "downloading"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    IDLE = "idle"         # Async endpoint scaled to zero
    STOPPING = "stopping"
    FAILED = "failed"


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
    """Return models filtered by studio (image, video, chat)."""
    return {k: v for k, v in MODEL_CATALOG.items() if v.get("studio") == studio}
