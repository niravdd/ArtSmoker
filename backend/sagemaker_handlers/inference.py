"""Universal Amazon SageMaker inference handler — fully data-driven from registry.

This SINGLE handler runs inside ALL Amazon SageMaker containers for ArtSmoker.
It reads configuration entirely from environment variables (set by the
deployer from the model catalog). ZERO model-specific code — adding a
new model requires only a catalog entry.

Supports two model loading modes:
  1. HuggingFace models: Our handler downloads from ARTSMOKER_HF_REPO using
     from_pretrained(repo_id). We do NOT use HF_MODEL_ID (the DLC container
     intercepts that and bypasses our optimizations like CPU offloading).
  2. Pre-uploaded weights: Model weights are in model_dir (uploaded to S3 as tar.gz).
     The handler loads from the local path.

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
  ARTSMOKER_HF_REPO: HuggingFace repo ID (our handler downloads, NOT the DLC container)
  HUGGING_FACE_HUB_TOKEN: Auth token for gated HuggingFace models (read-only)
  ENABLE_MODEL_CPU_OFFLOAD: Keep only active component on GPU (fits large models in 24GB)
  ENABLE_SEQUENTIAL_CPU_OFFLOAD: Layer-by-layer offload (slowest, least VRAM)
  ENABLE_VAE_SLICING: Process VAE in slices (saves VRAM on batch generation)
  ENABLE_VAE_TILING: Process VAE in tiles (saves VRAM on large images)
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

# ── S3 Model Cache ───────────────────────────────────────────────────────
_CACHE_LOCAL_DIR = "/tmp/model-cache"
_CACHE_INFO_FILE = ".cache-info.json"
_loaded_from_cache = False       # Set True when loading from S3 cache
_all_preserved_from_cache = False # Set True ONLY when all NF4 components preserved in cache
_cache_info = {}                 # Loaded from .cache-info.json during cache download


def _is_component_preserved(comp_name: str) -> bool:
    """Check if a cached component has NF4 weights preserved (with BnB metadata).

    Reads from .cache-info.json's quantized_components array. If the component
    has "preserved": true, its weights are in BnB NF4 format and can be loaded
    directly with quantization_config. If false, weights are bf16 and need
    re-quantization on the fly.
    """
    for comp in _cache_info.get("quantized_components", []):
        if comp.get("name") == comp_name:
            return comp.get("preserved", False)
    return False


def _clean_stale_quant_artifacts(comp_path: str):
    """Remove ALL stale BnB quantization artifacts from a cached component directory.

    When save_pretrained() saves bf16 weights but leaves partial quantization
    metadata (in separate files AND inside config.json), BnB gets confused on
    reload — it finds conflicting signals about the weight format.
    Cleaning these artifacts lets BnB treat it as a fresh bf16→NF4 quantization.
    """
    # 1. Remove standalone quantization config files
    stale_files = ["quantization_config.json", "quantize_config.json"]
    for fname in stale_files:
        fpath = os.path.join(comp_path, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            logger.info("Removed stale quantization file: %s", fpath)

    # 2. Remove quantization_config from inside config.json (embedded metadata)
    config_path = os.path.join(comp_path, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            if "quantization_config" in config:
                del config["quantization_config"]
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                logger.info("Removed embedded quantization_config from %s/config.json", comp_path.split("/")[-1])
        except Exception as e:
            logger.warning("Failed to clean config.json in %s: %s", comp_path, e)


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


# ── S3 Model Cache Functions ──────────────────────────────────────────────

def _get_cache_s3_path():
    """Return (bucket, prefix) for the S3 model cache, or (None, None) if not configured."""
    bucket = _get_env("ARTSMOKER_CACHE_BUCKET")
    prefix = _get_env("ARTSMOKER_CACHE_PREFIX")
    if not bucket or not prefix:
        return None, None
    return bucket, prefix


def _get_cache_version_key():
    """Compute a fingerprint for cache invalidation.

    Changes to model key, HF repo, catalog version, or quantization config
    will produce a different key, causing cache miss → fresh download.
    """
    model_key = _get_env("MODEL_KEY", "unknown")
    hf_repo = _get_env("ARTSMOKER_HF_REPO", "")
    cache_version = _get_env("ARTSMOKER_CACHE_VERSION", "1.0")
    quant_summary = ""
    for comp in _config.get("quantization_components", []):
        if isinstance(comp, dict):
            quant_summary += f"{comp.get('name', '')}-{comp.get('quantization', '')}-"
    return f"{model_key}:{hf_repo}:{cache_version}:{quant_summary}"


def _check_s3_cache():
    """Check S3 for cached model weights. Download if found and valid.

    Returns local path to cached model, or None.
    """
    global _loaded_from_cache, _cache_info, _all_preserved_from_cache
    bucket, prefix = _get_cache_s3_path()
    if not bucket:
        return None

    try:
        import boto3, time as _time, shutil
        s3 = boto3.client("s3")
        info_key = f"{prefix}/{_CACHE_INFO_FILE}"

        # Check if cache exists and read metadata
        try:
            resp = s3.get_object(Bucket=bucket, Key=info_key)
            cache_info = json.loads(resp["Body"].read().decode())
        except Exception:
            logger.info("No S3 cache found at s3://%s/%s", bucket, prefix)
            return None

        # Validate version fingerprint
        expected = _get_cache_version_key()
        cached_version = cache_info.get("version_key", "")
        if cached_version != expected:
            logger.info("Cache version mismatch: cached=%s, expected=%s — will rebuild",
                        cached_version, expected)
            return None

        # Download cached files
        logger.info("Found valid S3 cache (saved %s) — downloading...",
                     cache_info.get("saved_at", "?"))
        t0 = _time.time()

        if os.path.exists(_CACHE_LOCAL_DIR):
            shutil.rmtree(_CACHE_LOCAL_DIR)
        os.makedirs(_CACHE_LOCAL_DIR, exist_ok=True)

        paginator = s3.get_paginator("list_objects_v2")
        total_bytes = 0
        file_count = 0
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                s3_key = obj["Key"]
                relative = s3_key[len(prefix):].lstrip("/")
                if not relative:
                    continue
                local_path = os.path.join(_CACHE_LOCAL_DIR, relative)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                s3.download_file(bucket, s3_key, local_path)
                total_bytes += obj.get("Size", 0)
                file_count += 1

        elapsed = _time.time() - t0
        logger.info("Downloaded %d files (%.1f GB) from S3 cache in %.1fs",
                     file_count, total_bytes / (1024**3), elapsed)

        # Validate cache has actual model weights (not just config/scheduler/tokenizer).
        # Sequential CPU offload models can't save weights (meta tensors) — their cache
        # contains only metadata files. Reject such caches early so we fall through to HF.
        has_weights = False
        for root, dirs, files in os.walk(_CACHE_LOCAL_DIR):
            for f in files:
                if f.endswith((".safetensors", ".bin", ".pth", ".pt")):
                    has_weights = True
                    break
            if has_weights:
                break
        if not has_weights:
            logger.warning("S3 cache has no model weights (only config/metadata) — ignoring cache, will download from source")
            import shutil as _shutil
            _shutil.rmtree(_CACHE_LOCAL_DIR, ignore_errors=True)
            return None

        _loaded_from_cache = True
        _cache_info = cache_info  # Preserve for _is_component_preserved() lookups

        # Check if ALL quantized components have preserved NF4
        quant_comps = cache_info.get("quantized_components", [])
        if quant_comps and all(c.get("preserved", False) for c in quant_comps):
            _all_preserved_from_cache = True
            logger.info("All quantized components have preserved NF4 — fast GPU load path available")
        else:
            not_preserved = [c["name"] for c in quant_comps if not c.get("preserved", False)]
            logger.info("Components without preserved NF4 (will re-quantize from bf16): %s", not_preserved)

        return _CACHE_LOCAL_DIR

    except Exception as e:
        logger.warning("S3 cache download failed (will load from source): %s", e)
        return None


def _save_to_s3_cache_sync(model_dict):
    """Save loaded model to S3 cache SYNCHRONOUSLY (blocks until complete).

    Used in build mode where the instance will be torn down after caching.
    Must complete before model_fn returns, or auto-scaling could kill the
    instance mid-upload.
    """
    logger.info("Synchronous S3 cache save starting...")
    _do_s3_cache_save(model_dict)


def _save_to_s3_cache(model_dict):
    """Save loaded model to S3 cache in a background thread.

    Runs after predict_fn() succeeds. Failures are non-fatal — they log
    a warning but never block inference.
    """
    import threading
    threading.Thread(target=lambda: _do_s3_cache_save(model_dict), daemon=True, name="s3-cache-save").start()
    logger.info("Started background S3 cache save")


def _do_s3_cache_save(model_dict):
    """Core cache save logic — component-level save preserving NF4 quantization.

    CRITICAL: We save each pipeline component individually using
    component.save_pretrained(), NOT pipe.save_pretrained(). This properly
    preserves BitsAndBytes NF4 quantization (including quantization_config.json).
    pipe.save_pretrained() silently expands NF4 weights to fp32 for some components.

    The cache structure mirrors the HuggingFace model layout:
      model-cache/
        transformer/        ← NF4 quantized (~10 GB, not 38 GB)
        text_encoder_2/     ← NF4 quantized (~6 GB, not 22 GB)
        text_encoder/       ← bf16 (small, ~2 GB)
        vae/                ← bf16 (~0.5 GB)
        scheduler/
        tokenizer/
        tokenizer_2/
        model_index.json    ← pipeline config
        .cache-info.json    ← version fingerprint (uploaded LAST as commit marker)
    """
    bucket, prefix = _get_cache_s3_path()
    if not bucket:
        return

    try:
        import boto3, time as _time, shutil
        s3 = boto3.client("s3")

        # Check if cache already exists (another instance may have saved)
        info_key = f"{prefix}/{_CACHE_INFO_FILE}"
        try:
            resp = s3.get_object(Bucket=bucket, Key=info_key)
            cache_info = json.loads(resp["Body"].read().decode())
            if cache_info.get("version_key") == _get_cache_version_key():
                logger.info("S3 cache already exists and is current — skipping save")
                return
        except Exception:
            pass  # No cache yet — proceed

        save_dir = "/tmp/model-save"
        if os.path.exists(save_dir):
            shutil.rmtree(save_dir)
        os.makedirs(save_dir, exist_ok=True)

        t0 = _time.time()
        library = model_dict.get("library", "")

        if library == "diffusers" and "pipe" in model_dict:
            pipe = model_dict["pipe"]
            # Save pipeline config (model_index.json)
            pipe.save_config(save_dir)
            logger.info("Saved pipeline config (model_index.json)")

            # Quantized components were early-saved BEFORE pipeline assembly
            # (in the quantization loop) to preserve BnB metadata.
            # Non-quantized components are saved here from the pipeline.
            quant_names = {
                c.get("name") for c in _config.get("quantization_components", [])
                if isinstance(c, dict)
            }

            components_saved = 0
            for attr_name in ["transformer", "text_encoder", "text_encoder_2",
                              "vae", "scheduler", "tokenizer", "tokenizer_2"]:
                comp_dir = os.path.join(save_dir, attr_name)

                # Check if early-saved version exists (quantized components)
                if attr_name in quant_names and os.path.isdir(comp_dir):
                    comp_size = sum(
                        os.path.getsize(os.path.join(r, f))
                        for r, _, files in os.walk(comp_dir) for f in files
                    ) / (1024**3)
                    logger.info("Using early-saved %s: %.2f GB (NF4 preserved)", attr_name, comp_size)
                    components_saved += 1
                    continue

                # Non-quantized component — save from pipeline
                component = getattr(pipe, attr_name, None)
                if component is None:
                    continue
                os.makedirs(comp_dir, exist_ok=True)
                try:
                    if hasattr(component, "save_pretrained"):
                        component.save_pretrained(comp_dir)
                    elif hasattr(component, "save_config"):
                        component.save_config(comp_dir)
                    comp_size = sum(
                        os.path.getsize(os.path.join(r, f))
                        for r, _, files in os.walk(comp_dir) for f in files
                    ) / (1024**3)
                    logger.info("Saved %s: %.2f GB", attr_name, comp_size)
                    components_saved += 1
                except Exception as e:
                    logger.warning("Failed to save component %s: %s", attr_name, e)

            logger.info("Saved %d pipeline components", components_saved)

        elif library == "transformers":
            if "model" in model_dict:
                model_dict["model"].save_pretrained(save_dir)
            if "processor" in model_dict:
                model_dict["processor"].save_pretrained(save_dir)
            if "pipe" in model_dict and hasattr(model_dict["pipe"], "save_pretrained"):
                model_dict["pipe"].save_pretrained(save_dir)
        else:
            logger.info("Cache save not supported for library=%s — skipping", library)
            return

        save_elapsed = _time.time() - t0
        logger.info("Model saved to local disk in %.1fs", save_elapsed)

        # Upload all model files to S3 FIRST, then write cache-info LAST as commit marker.
        t0 = _time.time()
        total_bytes = 0
        file_count = 0
        info_path = os.path.join(save_dir, _CACHE_INFO_FILE)

        # Collect quantization info from saved components for cache metadata
        quantized_components = []
        for comp in _config.get("quantization_components", []):
            if isinstance(comp, dict):
                comp_dir = os.path.join(save_dir, comp.get("name", ""))
                qconfig_path = os.path.join(comp_dir, "quantization_config.json")
                has_qconfig = os.path.exists(qconfig_path)
                quantized_components.append({
                    "name": comp.get("name"),
                    "quantization": comp.get("quantization"),
                    "preserved": has_qconfig,
                })
                if has_qconfig:
                    logger.info("✓ %s: quantization_config.json present (NF4 preserved)", comp.get("name"))
                else:
                    logger.warning("✗ %s: NO quantization_config.json — will need re-quantization on load", comp.get("name"))

        cache_info = {
            "version_key": _get_cache_version_key(),
            "model_key": _get_env("MODEL_KEY", "unknown"),
            "hf_repo": _get_env("ARTSMOKER_HF_REPO", ""),
            "cache_version": _get_env("ARTSMOKER_CACHE_VERSION", "1.0"),
            "saved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "library": library,
            "torch_version": torch.__version__,
            "save_method": "component_level",
            "quantized_components": quantized_components,
        }
        with open(info_path, "w") as f:
            json.dump(cache_info, f, indent=2)

        # Upload model files (not cache-info yet)
        for root, dirs, files in os.walk(save_dir):
            for fname in files:
                if fname == _CACHE_INFO_FILE:
                    continue  # Upload last
                local_path = os.path.join(root, fname)
                relative = os.path.relpath(local_path, save_dir)
                s3_key = f"{prefix}/{relative}"
                file_size = os.path.getsize(local_path)
                s3.upload_file(local_path, bucket, s3_key)
                total_bytes += file_size
                file_count += 1
                if file_count % 5 == 0:
                    logger.info("Cache upload progress: %d files, %.1f GB...", file_count, total_bytes / (1024**3))

        # Upload cache-info LAST (commit marker)
        s3.upload_file(info_path, bucket, f"{prefix}/{_CACHE_INFO_FILE}")
        file_count += 1

        upload_elapsed = _time.time() - t0
        logger.info("Uploaded %d files (%.1f GB) to S3 cache in %.1fs — s3://%s/%s",
                     file_count, total_bytes / (1024**3), upload_elapsed, bucket, prefix)

        # Cleanup local save directory
        shutil.rmtree(save_dir, ignore_errors=True)

    except Exception as e:
        logger.warning("S3 cache save failed (non-fatal): %s", e)
        import traceback
        logger.debug("Cache save traceback:\n%s", traceback.format_exc())


# ── Loaders (by INFERENCE_LIBRARY) ────────────────────────────────────────
# Each loader reads its configuration from environment variables.
# No model-specific branching — everything is parameterized.
#
# Model source resolution:
#   1. S3 model cache (quantized weights from previous successful load)
#   2. Local weights in model_dir (non-HF models bundled in tar.gz)
#   3. HuggingFace repo download (first-time load)
#   - We do NOT use HF_MODEL_ID (the DLC container intercepts that and
#     uses its own handler, bypassing our optimizations)

def _resolve_model_source(model_dir):
    """Determine model source: S3 cache → local weights → HuggingFace repo.

    Returns the model identifier to pass to from_pretrained():
    either a local directory path or a HuggingFace repo ID.
    """
    # Priority 1: S3 model cache (quantized weights from previous successful load)
    cached_path = _check_s3_cache()
    if cached_path:
        logger.info("Loading model from S3 cache: %s", cached_path)
        return cached_path

    # Priority 2: Local weights in model_dir (non-HF models bundled in tar.gz)
    hf_repo = _get_env("ARTSMOKER_HF_REPO")
    has_weights = False
    if os.path.isdir(model_dir):
        for item in os.listdir(model_dir):
            if item == "code":
                continue
            if item.endswith((".bin", ".safetensors", ".pth", ".pt", ".onnx")) or \
               item in ("config.json", "model_index.json", "tokenizer.json"):
                has_weights = True
                break

    if has_weights:
        logger.info("Loading model from local path: %s", model_dir)
        return model_dir

    # Priority 3: HuggingFace repo (first-time load)
    if hf_repo:
        logger.info("Downloading model from HuggingFace: %s", hf_repo)
        return hf_repo

    logger.warning("No model weights and no ARTSMOKER_HF_REPO — attempting local: %s", model_dir)
    return model_dir


def _load_diffusers(model_dir):
    """Load any diffusers pipeline with memory optimizations from env vars.

    Downloads from HuggingFace if no local weights. Applies optimizations
    (CPU offloading, VAE slicing/tiling) based on catalog-driven env vars.
    """
    loader_class_name = _get_env("LOADER_CLASS", "AutoPipelineForText2Image")
    variant = _get_env("LOADER_VARIANT") or None

    PipelineClass = _import_class("diffusers", loader_class_name)

    model_source = _resolve_model_source(model_dir)
    hf_token = _get_env("HUGGING_FACE_HUB_TOKEN") or None

    kwargs = {"torch_dtype": _get_torch_dtype()}
    if variant:
        kwargs["variant"] = variant
    if hf_token:
        kwargs["token"] = hf_token

    # Quantization: pre-load specific components with reduced precision.
    # When loading from S3 cache, we still need to tell from_pretrained to
    # use BnB quantization config — the saved weights are in NF4 format but
    # the loader needs the quantization_config to interpret them correctly.
    # The difference: cache loads from local disk (fast), fresh loads from HF (slow).
    quant_components = _config.get("quantization_components", [])
    pre_loaded = {}

    if _loaded_from_cache:
        logger.info("Loading from S3 cache — components saved individually with quantization preserved")
        # Still load quantized components with BnB config, but from the local cache path
        # (not from HuggingFace). This ensures NF4 weights are loaded as NF4, not expanded to bf16.

    # Support legacy format: list of strings + separate quantization field
    if quant_components and isinstance(quant_components[0], str):
        legacy_quant = _config.get("quantization", "")
        legacy_class = _config.get("quantization_loader_class", "")
        if legacy_quant and legacy_class:
            quant_components = [{
                "name": quant_components[0],
                "class": legacy_class,
                "module": "diffusers",
                "subfolder": quant_components[0],
                "quantization": legacy_quant,
            }]
        else:
            quant_components = []

    for comp in quant_components:
        if not isinstance(comp, dict):
            continue
        comp_name = comp.get("name", "")
        comp_class = comp.get("class", "")
        comp_module = comp.get("module", "diffusers")
        comp_subfolder = comp.get("subfolder", comp_name)
        comp_quant = comp.get("quantization", "")

        if not comp_name or not comp_class or not comp_quant:
            continue

        action = "Loading cached" if _loaded_from_cache else "Quantizing"
        logger.info("%s %s: class=%s, type=%s", action, comp_name, comp_class, comp_quant)
        try:
            # Build quantization config — needed for BOTH fresh quantization AND cache loading.
            # For cache: tells from_pretrained to interpret saved weights as NF4 (not expand to bf16).
            # For fresh: tells from_pretrained to quantize from full-precision HF weights.
            if comp_module == "diffusers":
                from diffusers import BitsAndBytesConfig as BnbConfig
            else:
                from transformers import BitsAndBytesConfig as BnbConfig

            if comp_quant in ("int8", "8bit"):
                qconfig = BnbConfig(load_in_8bit=True)
            elif comp_quant in ("int4", "4bit", "nf4"):
                qconfig = BnbConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")
            else:
                logger.warning("Unknown quantization type '%s' for %s — skipping", comp_quant, comp_name)
                continue

            CompClass = _import_class(comp_module, comp_class)
            load_kwargs = {
                "quantization_config": qconfig,
                "torch_dtype": _get_torch_dtype(),
            }
            if hf_token:
                load_kwargs["token"] = hf_token

            # Device map for quantization: "cpu" keeps large models in RAM during quantization
            # to avoid GPU OOM. Needed for both fresh loads AND cache re-quantization.
            comp_device_map = comp.get("device_map")
            if comp_device_map:
                load_kwargs["device_map"] = comp_device_map
                logger.info("Loading %s to device_map='%s'", comp_name, comp_device_map)

            # Source path resolution:
            # - Cache: component saved as subfolder of cache dir. Try both comp_name
            #   and comp_subfolder (pipeline may save under different names).
            # - Fresh: subfolder of HuggingFace repo.
            if _loaded_from_cache:
                # Try multiple possible directory names
                comp_path = None
                for candidate in [comp_name, comp_subfolder]:
                    candidate_path = os.path.join(model_source, candidate)
                    if os.path.isdir(candidate_path):
                        comp_path = candidate_path
                        break

                if comp_path:
                    preserved = _is_component_preserved(comp_name)
                    if preserved:
                        # NF4 weights with BnB metadata preserved — load directly (fast)
                        logger.info("Loading %s from cache: NF4 preserved, direct load", comp_name)
                        pre_loaded[comp_name] = CompClass.from_pretrained(comp_path, **load_kwargs)
                    else:
                        # bf16 weights — clean stale BnB artifacts and re-quantize on the fly.
                        # BnB will treat these as fresh bf16 weights and quantize to NF4,
                        # same as a fresh HF download but from local disk (faster).
                        _clean_stale_quant_artifacts(comp_path)
                        logger.info("Loading %s from cache: bf16 → re-quantizing to %s (NF4 not preserved)", comp_name, comp_quant)
                        pre_loaded[comp_name] = CompClass.from_pretrained(comp_path, **load_kwargs)
                else:
                    logger.warning("Cache missing component %s — will load from pipeline (UNQUANTIZED)", comp_name)
                    continue
            else:
                pre_loaded[comp_name] = CompClass.from_pretrained(
                    model_source, subfolder=comp_subfolder, **load_kwargs,
                )

            logger.info("Loaded %s with %s quantization (from_cache=%s)", comp_name, comp_quant, _loaded_from_cache)

            # CRITICAL: Save quantized component IMMEDIATELY, before pipeline assembly
            # or model_cpu_offload can strip BnB metadata. save_pretrained() on a freshly
            # quantized component writes quantization_config.json. After pipeline assembly
            # + offloading, this metadata is lost and save reverts to full precision.
            if not _loaded_from_cache and _get_env("ARTSMOKER_CACHE_BUCKET"):
                _early_save_dir = "/tmp/model-save"
                comp_save_dir = os.path.join(_early_save_dir, comp_name)
                try:
                    os.makedirs(comp_save_dir, exist_ok=True)
                    pre_loaded[comp_name].save_pretrained(comp_save_dir)
                    qconfig_path = os.path.join(comp_save_dir, "quantization_config.json")
                    has_qc = os.path.exists(qconfig_path)
                    comp_size = sum(
                        os.path.getsize(os.path.join(r, f))
                        for r, _, files in os.walk(comp_save_dir) for f in files
                    ) / (1024**3)
                    logger.info("Early-saved %s: %.2f GB, quantization_config.json=%s",
                                comp_name, comp_size, "✓" if has_qc else "✗")
                except Exception as save_err:
                    logger.warning("Early save failed for %s: %s", comp_name, save_err)

        except Exception as e:
            logger.warning("Quantization failed for %s (%s), falling back to full precision: %s",
                          comp_name, comp_quant, e)

    # Multi-GPU: load transformer with device_map to split across GPUs
    device_map = _config.get("device_map", "")
    if device_map and not pre_loaded:
        # Load the transformer separately with device_map for multi-GPU distribution
        transformer_class = _config.get("transformer_class", "")
        if transformer_class:
            logger.info("Loading transformer with device_map='%s' across multiple GPUs", device_map)
            try:
                TransformerClass = _import_class("diffusers", transformer_class)
                pre_loaded["transformer"] = TransformerClass.from_pretrained(
                    model_source, subfolder="transformer",
                    device_map=device_map,
                    torch_dtype=_get_torch_dtype(),
                    token=hf_token,
                )
                num_devices = len(set(str(v) for v in pre_loaded["transformer"].hf_device_map.values()))
                logger.info("Transformer distributed across %d devices (device_map=%s)", num_devices, device_map)
            except Exception as e:
                logger.warning("Multi-GPU transformer load failed: %s — falling back to single GPU", e)

    has_quant = "yes" if pre_loaded else "none"
    logger.info("Loading %s with %s (dtype=%s, quantization=%s, device_map=%s)",
                model_source, loader_class_name, _get_env("TORCH_DTYPE", "float16"),
                has_quant, device_map or "none")

    if pre_loaded:
        kwargs.update(pre_loaded)

    try:
        pipe = PipelineClass.from_pretrained(model_source, **kwargs)
    except Exception as load_err:
        # If loading from cache failed, fall back to HuggingFace repo (not same broken path).
        # This handles corrupt/incomplete caches gracefully.
        hf_repo = _get_env("ARTSMOKER_HF_REPO")
        fallback_source = hf_repo if (hf_repo and _loaded_from_cache) else model_source
        if fallback_source != model_source:
            logger.warning("Cache load failed (%s) — falling back to HuggingFace: %s", load_err, fallback_source)
        else:
            logger.warning("Pipeline load failed (%s) — retrying with minimal kwargs", load_err)

        fallback_kwargs = {"torch_dtype": _get_torch_dtype()}
        if hf_token:
            fallback_kwargs["token"] = hf_token
        if pre_loaded:
            fallback_kwargs.update(pre_loaded)
        pipe = PipelineClass.from_pretrained(fallback_source, **fallback_kwargs)

    # GPU placement strategy for quantized models:
    # device_map="balanced" causes CUDA illegal memory access when text encoder is on CPU
    # and transformer is on GPU (cross-device tensor operations fail).
    # model_cpu_offload is the correct approach: moves ONE component at a time to GPU,
    # runs its forward pass, then moves it back. Each component gets full GPU access.
    # With bf16 text encoder (~22 GB) + NF4 transformer (~10 GB), each fits on 44.5 GB L40S.
    # Speed: text encoding once (~15s) + 28 denoising steps (~3-4 min) = ~3.5 min total.
    has_quantized = bool(pre_loaded)
    all_quantized = has_quantized and len(pre_loaded) == len([
        c for c in _config.get("quantization_components", []) if isinstance(c, dict)
    ])

    if device_map:
        logger.info("Skipping .to(cuda)/offload — model placed by device_map")
    elif all_quantized and _all_preserved_from_cache:
        # All components have PRESERVED NF4 weights loaded from cache — already compact,
        # loaded directly to GPU (no device_map="cpu" needed for preserved NF4).
        # Total ~16 GB NF4 fits easily on 44.5+ GB L40S GPU.
        # This is the fast path: ~30-60s/image instead of ~5 min with model_cpu_offload.
        logger.info("All components NF4 preserved from cache — moving pipeline to GPU (fast inference)")
        pipe.to("cuda")
    elif has_quantized:
        # Quantized components loaded to CPU (fresh build OR cache re-quantization).
        # Use model_cpu_offload to move one at a time — slower but safe.
        logger.info("Quantized components on CPU — using model_cpu_offload")
        pipe.enable_model_cpu_offload()
    elif _get_env_bool("ENABLE_MODEL_CPU_OFFLOAD"):
        logger.info("Enabling model CPU offload (keeps only active component on GPU)")
        pipe.enable_model_cpu_offload()
    elif _get_env_bool("ENABLE_SEQUENTIAL_CPU_OFFLOAD"):
        logger.info("Enabling sequential CPU offload (layer-by-layer, slowest but least VRAM)")
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.to("cuda")

    # Log device placement summary — critical for debugging OOM/spill issues
    if has_quantized and getattr(pipe, 'hf_device_map', None):
        logger.info("Device placement:")
        for comp_name, device in pipe.hf_device_map.items():
            logger.info("  %s → %s", comp_name, device)
    elif has_quantized:
        # Check individual component devices
        for attr_name in ["transformer", "text_encoder", "text_encoder_2", "vae"]:
            comp = getattr(pipe, attr_name, None)
            if comp is not None:
                try:
                    device = next(comp.parameters()).device
                    logger.info("  %s → %s", attr_name, device)
                except StopIteration:
                    pass

    if _get_env_bool("ENABLE_VAE_SLICING"):
        logger.info("Enabling VAE slicing")
        try:
            pipe.enable_vae_slicing()
        except Exception:
            pass

    if _get_env_bool("ENABLE_VAE_TILING"):
        logger.info("Enabling VAE tiling")
        try:
            pipe.enable_vae_tiling()
        except Exception:
            pass

    return {"library": "diffusers", "pipe": pipe}


def _load_transformers(model_dir):
    """Load any transformers model — class/task from env vars.

    Downloads from HuggingFace via ARTSMOKER_HF_REPO if no local weights.
    """
    loader_class = _get_env("LOADER_CLASS", "pipeline")
    loader_task = _get_env("LOADER_TASK", "")
    trust_remote = _get_env_bool("TRUST_REMOTE_CODE")
    processor_class = _get_env("PROCESSOR_CLASS", "")

    model_source = _resolve_model_source(model_dir)
    hf_token = _get_env("HUGGING_FACE_HUB_TOKEN") or None

    if loader_class == "pipeline":
        from transformers import pipeline
        kwargs = {"model": model_source, "device": "cuda"}
        if loader_task:
            kwargs["task"] = loader_task
        if hf_token:
            kwargs["token"] = hf_token
        pipe = pipeline(**kwargs)
        return {"library": "transformers", "predictor": "pipeline", "pipe": pipe}

    else:
        # Load specific model class
        ModelClass = _import_class("transformers", loader_class)
        kwargs = {}
        if trust_remote:
            kwargs["trust_remote_code"] = True
        if hf_token:
            kwargs["token"] = hf_token
        model = ModelClass.from_pretrained(model_source, **kwargs)
        model.to("cuda").eval()

        result = {"library": "transformers", "predictor": "model", "model": model}

        # Load processor if specified
        if processor_class:
            ProcessorClass = _import_class("transformers", processor_class)
            proc_kwargs = {}
            if hf_token:
                proc_kwargs["token"] = hf_token
            processor = ProcessorClass.from_pretrained(model_source, **proc_kwargs)
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


# ── Amazon SageMaker Entry Points ─────────────────────────────────────────

def model_fn(model_dir):
    """Load model — called once when endpoint starts.

    Reads INFERENCE_LIBRARY from env to pick the right loader.
    The loader reads its specific params (LOADER_CLASS, TORCH_DTYPE, etc.) from env.

    For HuggingFace direct pull: fetches auth token from Secrets Manager first,
    then the loader downloads weights from HuggingFace using from_pretrained().
    """
    global _model, _config
    library = _get_env("INFERENCE_LIBRARY", "diffusers")
    model_key = _get_env("MODEL_KEY", "unknown")

    # Log environment and versions for diagnostics
    try:
        import diffusers as _d, transformers as _t, accelerate as _a
        logger.info("=== ArtSmoker Inference Handler ===")
        logger.info("Model: %s, Library: %s", model_key, library)
        logger.info("Versions: diffusers=%s, transformers=%s, accelerate=%s, torch=%s",
                     _d.__version__, _t.__version__, _a.__version__, torch.__version__)
        logger.info("CUDA available: %s, device count: %d", torch.cuda.is_available(),
                     torch.cuda.device_count() if torch.cuda.is_available() else 0)
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram = getattr(props, 'total_memory', 0) or getattr(props, 'total_mem', 0)
            logger.info("GPU: %s, VRAM: %.1f GB", torch.cuda.get_device_name(0), vram / (1024**3))
        try:
            import peft as _p
            logger.info("peft=%s", _p.__version__)
        except ImportError:
            logger.info("peft: not installed")
    except Exception as e:
        logger.warning("Version logging failed: %s", e)

    # Load invoke config — prefer file (no truncation risk), fall back to env var
    config_file = os.path.join(model_dir, "code", "invoke_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file) as f:
                _config = json.load(f)
            logger.info("invoke_config.json loaded from model.tar.gz (%d keys)", len(_config))
        except Exception as e:
            logger.warning("Failed to load invoke_config.json: %s", e)
            _config = {}
    else:
        config_json = _get_env("INVOKE_CONFIG")
        if config_json:
            try:
                _config = json.loads(config_json)
                logger.info("INVOKE_CONFIG loaded from env var (%d keys)", len(_config))
            except Exception:
                _config = {}

    loader = _LOADERS.get(library)
    if not loader:
        raise ValueError(f"Unsupported INFERENCE_LIBRARY: {library}. Available: {list(_LOADERS.keys())}")

    logger.info("Loading %s with library=%s ...", model_key, library)
    import time as _time
    t0 = _time.time()
    _model = loader(model_dir)
    elapsed = _time.time() - t0
    logger.info("Model %s loaded in %.1fs (library=%s)", model_key, elapsed, library)

    # Log VRAM usage after loading
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / (1024**3)
        reserved = torch.cuda.memory_reserved(0) / (1024**3)
        logger.info("GPU memory after load: %.2f GB allocated, %.2f GB reserved", allocated, reserved)

    # S3 cache save strategy:
    # - Build mode (ARTSMOKER_BUILD_ONLY=true): save SYNCHRONOUSLY — must block
    #   until upload completes, or auto-scaling could kill the instance mid-upload.
    # - Normal mode: save in BACKGROUND thread — don't delay model readiness.
    #   We save immediately after model_fn (not after first inference) because
    #   the instance may scale down before any inference arrives.
    if _get_env("ARTSMOKER_CACHE_BUCKET") and not _loaded_from_cache:
        if _get_env_bool("ARTSMOKER_BUILD_ONLY"):
            logger.info("Build mode — saving cache synchronously after model load")
            _save_to_s3_cache_sync(_model)
        else:
            logger.info("Normal mode — saving cache in background after model load")
            _save_to_s3_cache(_model)

    return _model


def input_fn(request_body, content_type="application/json"):
    """Parse input — supports JSON only."""
    if content_type == "application/json":
        data = json.loads(request_body)
        # Log input summary (not the full prompt — could be long)
        prompt_len = len(data.get("prompt", ""))
        logger.info("Input: prompt=%d chars, size=%dx%d, steps=%s, guidance=%s, seed=%s",
                     prompt_len, data.get("width", "?"), data.get("height", "?"),
                     data.get("num_inference_steps", "?"), data.get("guidance_scale", "?"),
                     data.get("seed", "?"))
        return data
    raise ValueError(f"Unsupported content type: {content_type}")


def predict_fn(input_data, model_dict):
    """Run inference — routes to predictor by PREDICTOR_TYPE env var."""
    predictor_type = _get_env("PREDICTOR_TYPE", "text_to_image")
    predictor = _PREDICTORS.get(predictor_type)
    if not predictor:
        raise ValueError(f"Unknown PREDICTOR_TYPE: {predictor_type}. Available: {list(_PREDICTORS.keys())}")

    import time as _time
    t0 = _time.time()

    # Log GPU memory before inference
    if torch.cuda.is_available():
        alloc = torch.cuda.memory_allocated(0) / (1024**3)
        reserved = torch.cuda.memory_reserved(0) / (1024**3)
        logger.info("GPU memory before inference: %.2f GB allocated, %.2f GB reserved (%.1f GB free of 44.5 GB)",
                     alloc, reserved, 44.5 - reserved)

    try:
        result = predictor(input_data, model_dict)
        elapsed = _time.time() - t0

        # Log GPU memory after inference (peak is during, but this shows post-inference state)
        if torch.cuda.is_available():
            peak = torch.cuda.max_memory_allocated(0) / (1024**3)
            alloc = torch.cuda.memory_allocated(0) / (1024**3)
            logger.info("GPU memory after inference: %.2f GB peak, %.2f GB current", peak, alloc)
            torch.cuda.reset_peak_memory_stats(0)

        logger.info("Inference complete in %.1fs (predictor=%s, output=%d chars)",
                     elapsed, predictor_type, len(result) if isinstance(result, str) else 0)

        # Cache save now happens in model_fn() (background thread in normal mode,
        # synchronous in build mode). No longer deferred to first inference.

        return result
    except Exception as exc:
        elapsed = _time.time() - t0
        logger.error("Inference FAILED after %.1fs (predictor=%s): %s", elapsed, predictor_type, exc)
        import traceback
        logger.error("Traceback:\n%s", traceback.format_exc())
        raise


def output_fn(prediction, accept="application/json"):
    """Format output as JSON."""
    if isinstance(prediction, str) and prediction.startswith("{"):
        return prediction  # Already JSON (e.g., video frames)
    return json.dumps({"image": prediction, "format": "base64_png"})
