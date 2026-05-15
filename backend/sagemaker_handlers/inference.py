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

import os

import base64
import io
import json
import logging
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


# ── Block Offload Manager ────────────────────────────────────────────────
# Generic GPU↔CPU block offloading with CUDA stream prefetching.
# Standard PyTorch primitives: forward hooks, CUDA streams, non-blocking transfers.
# Works with any model that has sequential transformer blocks (nn.ModuleList).

class BlockOffloadManager:
    """Sliding-window block offloading with async CUDA stream prefetching.

    CPU-first strategy: model loaded to CPU, components placed selectively.
    Uses a sliding window to keep offloaded blocks on GPU as long as possible,
    only evicting the oldest when space is needed for the next incoming block.
    This avoids the costly move-back-after-every-forward pattern.

    Window size controls how many offloaded blocks can be on GPU simultaneously.
    With window=2 and prefetch=2, at most 4 offloaded blocks are on GPU at once
    (2 in window + 2 being prefetched). This uses ~9.6 GB extra VRAM for 2.4 GB
    blocks, well within the ~32 GB headroom on 96 GB.
    """

    def __init__(self, layers, blocks_to_offload, prefetch_ahead=2,
                 window_size=2, target_device="cuda"):
        self.layers = layers
        self.num_blocks = len(layers)
        self.blocks_to_offload = min(blocks_to_offload, self.num_blocks)
        self.prefetch_ahead = prefetch_ahead
        self.window_size = window_size
        self.target_device = target_device
        self.offload_start = self.num_blocks - self.blocks_to_offload
        self._hooks = []
        self._enabled = False
        self._prefetch_stream = None
        self._prefetch_events = {}
        self._block_devices = {}
        self._gpu_queue = []  # Track offloaded blocks currently on GPU (FIFO)

    def setup(self):
        if self.blocks_to_offload <= 0:
            return

        self._prefetch_stream = torch.cuda.Stream(device=self.target_device)

        for i in range(self.offload_start):
            self.layers[i].to(self.target_device)
            self._fix_bnb_state(self.layers[i])
            self._block_devices[i] = self.target_device

        for i in range(self.offload_start, self.num_blocks):
            self._pin_block(self.layers[i])
            self._block_devices[i] = "cpu"

        for i, block in enumerate(self.layers):
            pre = block.register_forward_pre_hook(
                lambda mod, inp, idx=i: self._pre_forward(idx, mod, inp)
            )
            post = block.register_forward_hook(
                lambda mod, inp, out, idx=i: self._post_forward(idx, mod, inp, out)
            )
            self._hooks.extend([pre, post])

        self._enabled = True

        block_size = self._estimate_block_size()
        max_gpu = self.window_size + self.prefetch_ahead
        logger.info("Block offload (sliding window): %d/%d blocks offloaded (%.1f GB each), "
                     "window=%d, prefetch=%d (max %d on GPU = ~%.1f GB extra)",
                     self.blocks_to_offload, self.num_blocks, block_size,
                     self.window_size, self.prefetch_ahead, max_gpu,
                     max_gpu * block_size)

    def _pin_block(self, block):
        for param in block.parameters():
            try:
                if not param.data.is_pinned():
                    param.data = param.data.pin_memory()
            except Exception:
                pass

    def _estimate_block_size(self):
        if self.offload_start < self.num_blocks:
            block = self.layers[self.offload_start]
            total = sum(p.numel() * p.element_size() for p in block.parameters())
            return total / (1024**3)
        return 0

    def _evict_oldest(self):
        """Evict the oldest offloaded block from GPU back to CPU."""
        while len(self._gpu_queue) > self.window_size:
            victim = self._gpu_queue.pop(0)
            if self._block_devices.get(victim) == self.target_device:
                self.layers[victim].to("cpu")
                self._block_devices[victim] = "cpu"

    def _pre_forward(self, block_idx, module, input):
        if not self._enabled:
            return

        if block_idx in self._prefetch_events:
            self._prefetch_events[block_idx].synchronize()
            del self._prefetch_events[block_idx]
            self._fix_bnb_state(module)
            self._block_devices[block_idx] = self.target_device

        if self._block_devices.get(block_idx) == "cpu":
            module.to(self.target_device)
            self._fix_bnb_state(module)
            self._block_devices[block_idx] = self.target_device

        # Track this offloaded block in the GPU window queue
        if block_idx >= self.offload_start:
            if block_idx in self._gpu_queue:
                self._gpu_queue.remove(block_idx)
            self._gpu_queue.append(block_idx)
            self._evict_oldest()

        # Prefetch upcoming offloaded blocks
        for offset in range(1, self.prefetch_ahead + 1):
            prefetch_idx = block_idx + offset
            if (prefetch_idx < self.num_blocks and
                prefetch_idx >= self.offload_start and
                self._block_devices.get(prefetch_idx) == "cpu" and
                prefetch_idx not in self._prefetch_events):
                with torch.cuda.stream(self._prefetch_stream):
                    self.layers[prefetch_idx].to(self.target_device, non_blocking=True)
                    event = torch.cuda.Event()
                    event.record(self._prefetch_stream)
                    self._prefetch_events[prefetch_idx] = event

    def _post_forward(self, block_idx, module, input, output):
        # Sliding window: do NOT evict here. Eviction happens in _pre_forward
        # when the window overflows. This keeps blocks on GPU across steps.
        pass

    def _fix_bnb_state(self, module):
        """Fix BnB INT8 CB/SCB after CPU→GPU move only."""
        try:
            import bitsandbytes as bnb
            for child in module.modules():
                if isinstance(child, bnb.nn.Linear8bitLt):
                    w = child.weight
                    if hasattr(w, 'CB') and w.CB is not None:
                        if w.CB.device != w.data.device:
                            w.CB = w.data
                    if hasattr(w, 'SCB') and w.SCB is not None:
                        if w.SCB.device != w.data.device:
                            w.SCB = w.SCB.to(w.data.device)
        except ImportError:
            pass
        except Exception as e:
            logger.debug("BnB state fix: %s", e)

    def enable(self):
        self._enabled = True
        self._gpu_queue.clear()

    def disable(self):
        self._enabled = False
        self._prefetch_events.clear()
        self._gpu_queue.clear()
        for i in range(self.offload_start, self.num_blocks):
            if self._block_devices.get(i) != "cpu":
                try:
                    self.layers[i].to("cpu")
                    self._block_devices[i] = "cpu"
                except Exception:
                    pass
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def cleanup(self):
        for h in self._hooks:
            h.remove()
        self._hooks.clear()
        self._enabled = False


# ── Helpers ───────────────────────────────────────────────────────────────

def _cleanup_before_fallback(comp_name: str, pre_loaded: dict):
    """Free GPU memory and references from a failed component load before retrying.

    Aggressively clears GPU: removes reference from pre_loaded, runs garbage
    collection, and empties CUDA cache. Called before every HuggingFace fallback.
    """
    if comp_name in pre_loaded:
        try:
            obj = pre_loaded.pop(comp_name)
            del obj
        except Exception:
            pass
    try:
        import torch, gc
        gc.collect()
        gc.collect()  # Second pass catches ref cycles
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            allocated = torch.cuda.memory_allocated() / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            logger.info("GPU after cleanup: %.1f GB allocated, %.1f GB reserved", allocated, reserved)
    except Exception:
        pass


def _load_from_hf(comp_name, comp_subfolder, CompClass, load_kwargs, hf_token, pre_loaded):
    """Single attempt to load a component from HuggingFace with quantization.

    This is the final fallback — called once, never retried. If this fails,
    the component is skipped (logged as error). The GPU placement logic
    downstream handles missing components via model_cpu_offload.
    """
    hf_repo = _get_env("ARTSMOKER_HF_REPO")
    if not hf_repo:
        logger.error("No ARTSMOKER_HF_REPO set — cannot fall back to HuggingFace for %s", comp_name)
        return
    try:
        pre_loaded[comp_name] = CompClass.from_pretrained(
            hf_repo, subfolder=comp_subfolder, **load_kwargs,
        )
        logger.info("Loaded %s from HuggingFace (fallback)", comp_name)
    except Exception as hf_err:
        logger.error("HuggingFace load failed for %s: %s — component will be unquantized", comp_name, hf_err)


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
        # Preserve early-saved quantized components (written during quantization loop).
        # Only clean non-component files (stale model_index.json etc), not component dirs.
        quant_comp_names = {
            c.get("name") for c in _config.get("quantization_components", [])
            if isinstance(c, dict)
        }
        if os.path.exists(save_dir):
            for item in os.listdir(save_dir):
                item_path = os.path.join(save_dir, item)
                if item in quant_comp_names and os.path.isdir(item_path):
                    continue  # Keep early-saved quantized component directories
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
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

        # If no components have quantization_config.json, the cache still contains
        # valid weights (likely NF4 packed, just missing metadata due to diffusers bug).
        # Save anyway — the workaround above should fix this, but if not, bf16 cache
        # can still be re-quantized on load.
        if quantized_components and not any(c["preserved"] for c in quantized_components):
            logger.warning("No quantization_config.json found — cache will need re-quantization on load")

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
                        try:
                            logger.info("Loading %s from cache: NF4 preserved, direct load", comp_name)
                            preserved_kwargs = {"torch_dtype": _get_torch_dtype()}
                            if hf_token:
                                preserved_kwargs["token"] = hf_token
                            pre_loaded[comp_name] = CompClass.from_pretrained(comp_path, **preserved_kwargs)
                        except Exception as cache_err:
                            logger.warning("Preserved load failed for %s: %s — retrying with re-quantization", comp_name, cache_err)
                            _cleanup_before_fallback(comp_name, pre_loaded)
                            _clean_stale_quant_artifacts(comp_path)
                            try:
                                pre_loaded[comp_name] = CompClass.from_pretrained(comp_path, **load_kwargs)
                                logger.info("Re-quantized %s from cache (fallback)", comp_name)
                            except Exception as requant_err:
                                logger.warning("Cache re-quantize failed for %s: %s — falling back to HuggingFace", comp_name, requant_err)
                                _cleanup_before_fallback(comp_name, pre_loaded)
                                _load_from_hf(comp_name, comp_subfolder, CompClass, load_kwargs, hf_token, pre_loaded)
                    else:
                        _clean_stale_quant_artifacts(comp_path)
                        logger.info("Loading %s from cache: re-quantizing to %s (not preserved)", comp_name, comp_quant)
                        try:
                            pre_loaded[comp_name] = CompClass.from_pretrained(comp_path, **load_kwargs)
                        except Exception as requant_err:
                            logger.warning("Cache re-quantize failed for %s: %s — falling back to HuggingFace", comp_name, requant_err)
                            _cleanup_before_fallback(comp_name, pre_loaded)
                            _load_from_hf(comp_name, comp_subfolder, CompClass, load_kwargs, hf_token, pre_loaded)
                else:
                    logger.warning("Cache missing component %s — loading from HuggingFace", comp_name)
                    _load_from_hf(comp_name, comp_subfolder, CompClass, load_kwargs, hf_token, pre_loaded)
            else:
                pre_loaded[comp_name] = CompClass.from_pretrained(
                    model_source, subfolder=comp_subfolder, **load_kwargs,
                )

            logger.info("Loaded %s with %s quantization (from_cache=%s)", comp_name, comp_quant, _loaded_from_cache)

            # Save component IMMEDIATELY after quantization, before pipeline assembly.
            # Diffusers models (Flux2Transformer2DModel) write real NF4 packed weights
            # with BnB quant_state in safetensors. Transformers models (Mistral3) do NOT —
            # they save bf16 without quant_state. We verify by checking safetensors for
            # bitsandbytes__* keys before writing quantization_config.json.
            if not _loaded_from_cache and _get_env("ARTSMOKER_CACHE_BUCKET"):
                _early_save_dir = "/tmp/model-save"
                comp_save_dir = os.path.join(_early_save_dir, comp_name)
                try:
                    os.makedirs(comp_save_dir, exist_ok=True)
                    pre_loaded[comp_name].save_pretrained(comp_save_dir)

                    # Check if safetensors actually contain BnB quant_state metadata.
                    # Only write quantization_config.json if they do — otherwise the
                    # loader will try to load bf16 weights as pre-quantized NF4 and fail.
                    qconfig_path = os.path.join(comp_save_dir, "quantization_config.json")
                    has_real_nf4 = False
                    if not os.path.exists(qconfig_path):
                        for fname in os.listdir(comp_save_dir):
                            if fname.endswith(".safetensors"):
                                try:
                                    from safetensors import safe_open
                                    with safe_open(os.path.join(comp_save_dir, fname), framework="pt") as sf:
                                        keys = sf.keys()
                                        if any("bitsandbytes" in k for k in keys):
                                            has_real_nf4 = True
                                            break
                                except Exception:
                                    pass

                        if has_real_nf4:
                            qconfig_data = {
                                "load_in_4bit": comp_quant in ("int4", "4bit", "nf4"),
                                "load_in_8bit": comp_quant in ("int8", "8bit"),
                                "bnb_4bit_quant_type": "nf4" if comp_quant in ("int4", "4bit", "nf4") else None,
                                "bnb_4bit_compute_dtype": "bfloat16",
                                "bnb_4bit_use_double_quant": False,
                                "bnb_4bit_quant_storage": "uint8",
                                "quant_method": "bitsandbytes",
                            }
                            with open(qconfig_path, "w") as _f:
                                json.dump(qconfig_data, _f, indent=2)
                            config_path = os.path.join(comp_save_dir, "config.json")
                            if os.path.exists(config_path):
                                with open(config_path, "r") as _f:
                                    cfg = json.load(_f)
                                cfg["quantization_config"] = qconfig_data
                                with open(config_path, "w") as _f:
                                    json.dump(cfg, _f, indent=2)
                            logger.info("Verified NF4 quant_state in safetensors — wrote quantization_config.json")
                        else:
                            logger.info("No BnB quant_state in safetensors — saved as bf16 (will re-quantize on load)")

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
            logger.warning("Component load failed for %s (%s): %s — trying HuggingFace", comp_name, comp_quant, e)
            _cleanup_before_fallback(comp_name, pre_loaded)
            _load_from_hf(comp_name, comp_subfolder, CompClass, load_kwargs, hf_token, pre_loaded)

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

    # GPU placement strategy:
    # - All NF4 quantized (fresh or cached) → pipe.to("cuda") = fast path (30-60s/image)
    #   NF4 components are already on GPU from quantization. ~15 GB total fits easily.
    # - Fallback from failed quantization (full bf16) → model_cpu_offload (prevents OOM)
    has_quantized = bool(pre_loaded)
    all_quantized = has_quantized and len(pre_loaded) == len([
        c for c in _config.get("quantization_components", []) if isinstance(c, dict)
    ])
    expects_quantization = bool(_config.get("quantization_components"))

    if device_map:
        logger.info("Skipping .to(cuda)/offload — model placed by device_map")
    elif all_quantized:
        # All expected components are NF4 quantized (on GPU). Total ~15 GB fits on 44.5+ GB.
        logger.info("All components NF4 quantized — moving pipeline to GPU (fast inference)")
        pipe.to("cuda")
    elif has_quantized:
        # Partial quantization — some components on GPU, some not. Use offload for safety.
        logger.info("Partial quantization — using model_cpu_offload")
        pipe.enable_model_cpu_offload()
    elif expects_quantization and not has_quantized:
        logger.warning("Quantization expected but none succeeded — using model_cpu_offload (bf16 too large for GPU)")
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


def _load_autoregressive(model_dir):
    """Load an autoregressive image model (e.g., HunyuanImage 3.0).

    Three GPU placement strategies (chosen by config):
      1. device_map="auto" — multi-GPU: Accelerate splits layers across GPUs.
         No block offloading. Used on g7e.12xlarge+ (2+ GPUs, 192+ GB).
      2. Block offload (CPU-first) — single GPU with limited VRAM.
         Load to CPU, selectively place. Sliding window keeps offloaded blocks
         on GPU as long as possible, evicting oldest when window overflows.
      3. Single GPU, no offload — model fits entirely (NF4, or large GPU).
    """
    from transformers import AutoModelForCausalLM

    model_source = _resolve_model_source(model_dir)
    hf_token = _get_env("HUGGING_FACE_HUB_TOKEN") or None

    trust_remote = _config.get("trust_remote_code", False)
    attn_impl = _config.get("attn_implementation", "sdpa")
    moe_impl = _config.get("moe_impl", "eager")
    moe_drop = _config.get("moe_drop_tokens", True)
    torch_dtype = _config.get("torch_dtype", "auto")
    block_swap_blocks = _config.get("block_swap_blocks", 0)

    # Auto-detect GPU placement strategy based on hardware
    num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
    use_multi_gpu = num_gpus >= 2
    use_block_offload = block_swap_blocks > 0 and not use_multi_gpu

    logger.info("Loading autoregressive model from %s (trust_remote=%s, attn=%s, moe=%s, "
                "gpus=%d, strategy=%s)",
                model_source, trust_remote, attn_impl, moe_impl, num_gpus,
                "multi-gpu" if use_multi_gpu else "block-offload" if use_block_offload else "single-gpu")

    load_kwargs = {
        "torch_dtype": torch_dtype,
        "attn_implementation": attn_impl,
    }
    if trust_remote:
        load_kwargs["trust_remote_code"] = True
    if moe_impl:
        load_kwargs["moe_impl"] = moe_impl
    if moe_drop is not None:
        load_kwargs["moe_drop_tokens"] = moe_drop
    if hf_token:
        load_kwargs["token"] = hf_token

    if use_multi_gpu:
        load_kwargs["device_map"] = "auto"
        logger.info("Multi-GPU: device_map='auto' — Accelerate dispatches across %d GPUs", num_gpus)
    elif use_block_offload:
        load_kwargs["device_map"] = "cpu"
        logger.info("CPU-first load: block offload with sliding window (%d blocks)", block_swap_blocks)

    model = AutoModelForCausalLM.from_pretrained(model_source, **load_kwargs)

    if hasattr(model, "load_tokenizer"):
        logger.info("Loading custom tokenizer from %s", model_source)
        model.load_tokenizer(model_source)
    else:
        logger.info("No custom tokenizer loader — using standard tokenizer")
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_source, trust_remote_code=trust_remote, token=hf_token
        )
        model._tokenizer = tokenizer

    block_offload = None
    prefetch_ahead = _config.get("block_swap_prefetch", 2)
    window_size = _config.get("block_swap_window", 2)

    if use_multi_gpu:
        model.eval()
        if hasattr(model, 'hf_device_map'):
            devices = set(str(v) for v in model.hf_device_map.values())
            logger.info("Multi-GPU placement: %d devices — %s", len(devices), dict(model.hf_device_map))
        gpu_alloc = sum(
            torch.cuda.memory_allocated(i) / (1024**3)
            for i in range(torch.cuda.device_count())
        ) if torch.cuda.is_available() else 0
        logger.info("Multi-GPU total allocation: %.1f GB across %d GPUs", gpu_alloc, torch.cuda.device_count())

    elif use_block_offload and hasattr(model, "model") and hasattr(model.model, "layers"):
        if not (hasattr(model, "model") and hasattr(model.model, "layers")):
            logger.warning("block_swap_blocks=%d but model has no model.model.layers — disabled", block_swap_blocks)

        model.eval()

        inner = model.model
        moved_components = []
        for name, child in inner.named_children():
            if name == "layers":
                continue
            try:
                child.to("cuda")
                moved_components.append(name)
            except Exception as e:
                logger.warning("Could not move %s to GPU: %s", name, e)

        for name, child in model.named_children():
            if name == "model":
                continue
            try:
                child.to("cuda")
                moved_components.append(name)
            except Exception as e:
                logger.warning("Could not move %s to GPU: %s", name, e)

        logger.info("Moved non-block components to GPU: %s", moved_components)

        block_offload = BlockOffloadManager(
            inner.layers, block_swap_blocks,
            prefetch_ahead=prefetch_ahead, window_size=window_size,
            target_device="cuda"
        )
        block_offload.setup()

        gpu_alloc = torch.cuda.memory_allocated(0) / (1024**3) if torch.cuda.is_available() else 0
        logger.info("After block offload setup: %.1f GB GPU allocated", gpu_alloc)
    else:
        try:
            model.to("cuda")
            logger.info("Model moved to GPU (no block offload)")
        except (ValueError, RuntimeError) as move_err:
            if "8-bit" in str(move_err) or "not supported" in str(move_err):
                logger.info("Model already on correct device (pre-quantized)")
            else:
                raise
        model.eval()

    gpu_alloc = torch.cuda.memory_allocated(0) / (1024**3) if torch.cuda.is_available() else 0
    logger.info("Autoregressive model loaded: %.1f GB GPU allocated", gpu_alloc)

    return {
        "library": "autoregressive",
        "model": model,
        "block_offload": block_offload,
        "generate_method": _config.get("generate_method", "generate_image"),
        "bot_task": _config.get("bot_task", "image"),
    }


def _load_image_to_3d(model_dir):
    """Load an image-to-3D mesh generation pipeline.

    Supports any diffusers-compatible 3D pipeline that takes an image and
    produces a mesh. Currently loads from bundled code packages shipped
    alongside inference.py in the model.tar.gz.

    Also loads a background removal model (RMBG) as preprocessing —
    the 3D model expects clean foreground objects on white background.

    VRAM-adaptive loading strategy:
      - High VRAM (>=40 GB, e.g. g6e): Load ALL models simultaneously
        (TripoSG + SDXL/MV-Adapter + TexturePipeline) for fastest throughput.
      - Low VRAM (<40 GB, e.g. g5 24GB): Load only TripoSG + RMBG at startup.
        MV-Adapter and TexturePipeline are loaded on-demand during prediction,
        with memory freed between phases.
    """
    import sys

    # Add bundled packages to path (shipped inside model.tar.gz as code/triposg/)
    code_dir = os.path.join(model_dir, "code")
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)

    hf_repo = _get_env("ARTSMOKER_HF_REPO")
    hf_token = _get_env("HUGGING_FACE_HUB_TOKEN") or None
    dtype = _get_torch_dtype()

    # Download model weights to local directory, then load pipeline from there.
    # Uses custom pipeline code (bundled in model.tar.gz) — loading from a local
    # path with the package on sys.path avoids diffusers' remote code validation.
    import time as _time
    t0 = _time.time()
    logger.info("Downloading image-to-3D model weights from %s ...", hf_repo)
    from huggingface_hub import snapshot_download
    local_path = snapshot_download(repo_id=hf_repo, token=hf_token)
    dl_time = _time.time() - t0
    logger.info("Model weights downloaded in %.0fs to %s", dl_time, local_path)

    t0 = _time.time()
    # Load in fp32 — the VAE mesh extraction uses fp32 linear layers internally
    # and mixing fp16/fp32 causes dtype mismatches. Model is ~8GB in fp32,
    # well within the 44GB L40S VRAM.
    logger.info("Loading image-to-3D pipeline to GPU (fp32 — VAE requires full precision)...")
    from triposg import TripoSGPipeline
    pipe = TripoSGPipeline.from_pretrained(local_path)
    pipe.to("cuda")
    load_time = _time.time() - t0
    logger.info("Image-to-3D pipeline loaded on GPU in %.0fs", load_time)

    # Load RMBG (background removal) for preprocessing
    rmbg_model = None
    try:
        secondary_sources = _config.get("secondary_sources", {})
        rmbg_repo = secondary_sources.get("rmbg", {}).get("repo_id", "briaai/RMBG-1.4")
        if not rmbg_repo:
            rmbg_repo = "briaai/RMBG-1.4"

        logger.info("Downloading RMBG model from %s...", rmbg_repo)
        from transformers import AutoModelForImageSegmentation
        rmbg_model = AutoModelForImageSegmentation.from_pretrained(
            rmbg_repo, trust_remote_code=True, token=hf_token,
        )
        rmbg_model.to("cuda").eval()
        logger.info("RMBG background removal model loaded on GPU")
    except Exception as e:
        logger.warning("RMBG load failed (will skip background removal): %s", e)

    # Detect VRAM for adaptive loading strategy
    vram_gb = 0
    high_vram = False
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        vram_gb = (getattr(props, 'total_memory', 0) or getattr(props, 'total_mem', 0)) / (1024**3)
        high_vram = vram_gb >= 40  # g6e (48GB) vs g5 (24GB)
    logger.info("VRAM: %.1f GB — texture pipeline strategy: %s",
                vram_gb, "preloaded" if high_vram else "on-demand")

    # Attempt to load MV-Adapter + TexturePipeline on high-VRAM instances
    mv_pipe = None
    texture_pipe = None
    texture_available = False

    if high_vram:
        try:
            mv_pipe, texture_pipe = _load_texture_models(code_dir, hf_token)
            texture_available = True
            logger.info("MV-Adapter + TexturePipeline preloaded (high VRAM mode)")
        except Exception as e:
            logger.warning("Texture pipeline preload failed (will try on-demand): %s", e)
    else:
        # Check if mvadapter package is available (installed) without loading models
        try:
            import mvadapter  # noqa: F401
            texture_available = True
            logger.info("MV-Adapter package available — texture will be loaded on-demand per inference")
        except ImportError:
            logger.info("MV-Adapter package not available — will produce untextured meshes")

    return {
        "library": "image_to_3d",
        "pipe": pipe,
        "rmbg_model": rmbg_model,
        "mv_pipe": mv_pipe,
        "texture_pipe": texture_pipe,
        "texture_available": texture_available,
        "high_vram": high_vram,
        "vram_gb": vram_gb,
        "code_dir": code_dir,
        "hf_token": hf_token,
    }


def _load_texture_models(code_dir, hf_token):
    """Load MV-Adapter (multi-view generation) and TexturePipeline models.

    Called either at startup (high VRAM) or on-demand during prediction (low VRAM).
    Returns (mv_pipe, texture_pipe) tuple.
    Raises ImportError if critical dependencies (nvdiffrast) are unavailable.
    """
    import time as _time
    import subprocess

    # nvdiffrast needs CUDA compilation via torch.utils.cpp_extension.
    # It's not pip-installable in isolated builds (needs PyTorch in the build env).
    # We compile at runtime with --no-build-isolation so it finds torch + CUDA.
    try:
        import nvdiffrast
    except ImportError:
        logger.info("nvdiffrast not installed — compiling with CUDA (this takes ~60s)...")
        try:
            # Ensure build tools are present
            subprocess.check_call(
                ["pip", "install", "--quiet", "setuptools", "wheel"],
                timeout=30,
            )
            # Set CUDA_HOME if not set (needed for torch CUDAExtension)
            if not os.environ.get("CUDA_HOME"):
                for cuda_path in ["/usr/local/cuda", "/opt/conda/pkgs/cuda-toolkit"]:
                    if os.path.isdir(cuda_path):
                        os.environ["CUDA_HOME"] = cuda_path
                        break
            # Compile nvdiffrast using PyTorch's CUDAExtension (no build isolation)
            subprocess.check_call(
                ["pip", "install", "--no-build-isolation", "--no-deps",
                 "git+https://github.com/NVlabs/nvdiffrast.git"],
                timeout=300,
            )
            import nvdiffrast
            logger.info("nvdiffrast compiled and installed successfully")
        except Exception as e:
            logger.warning("nvdiffrast compilation failed: %s — texture generation unavailable", e)
            raise ImportError(f"nvdiffrast unavailable: {e}")

    # Load SDXL + MV-Adapter for multi-view generation
    t0 = _time.time()
    logger.info("Loading MV-Adapter (SDXL + adapter weights)...")
    from mvadapter.pipelines.pipeline_mvadapter import prepare_pipeline
    mv_pipe = prepare_pipeline(
        base_model="stabilityai/stable-diffusion-xl-base-1.0",
        vae_model="madebyollin/sdxl-vae-fp16-fix",
        adapter_path="huanngzh/mv-adapter",
        num_views=6,
        device="cuda",
        dtype=torch.float16,
    )
    mv_time = _time.time() - t0
    logger.info("MV-Adapter loaded in %.0fs", mv_time)

    # Load TexturePipeline (projection + blending, no heavy model weights)
    t0 = _time.time()
    logger.info("Loading TexturePipeline...")
    from mvadapter.pipelines.pipeline_texture import TexturePipeline
    texture_pipe = TexturePipeline(
        upscaler_ckpt_path=None,  # Skip upscaling for now (saves VRAM)
        inpaint_ckpt_path=None,   # Use basic inpainting
        device="cuda",
    )
    tex_time = _time.time() - t0
    logger.info("TexturePipeline loaded in %.0fs", tex_time)

    return mv_pipe, texture_pipe


_LOADERS = {
    "diffusers": _load_diffusers,
    "transformers": _load_transformers,
    "autoregressive": _load_autoregressive,
    "image_to_3d": _load_image_to_3d,
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

    # Progress logging for diffusers pipelines
    total_steps = kwargs.get("num_inference_steps", 50)
    import time as _t
    _step_start = _t.time()

    def _log_progress(pipe, step, timestep, callback_kwargs):
        elapsed = _t.time() - _step_start
        pct = int((step + 1) / total_steps * 100)
        if step == 0 or (step + 1) % 5 == 0 or step + 1 == total_steps:
            logger.info("Diffusion step %d/%d (%d%%) — %.1fs elapsed", step + 1, total_steps, pct, elapsed)
        return callback_kwargs

    try:
        kwargs["callback_on_step_end"] = _log_progress
        result = pipe(**kwargs)
    except TypeError:
        del kwargs["callback_on_step_end"]
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


def _predict_autoregressive_image(input_data, model_dict):
    """Generate an image from an autoregressive model (e.g., HunyuanImage 3.0).

    The model uses generate_image() (or whatever generate_method is configured)
    instead of a diffusers pipeline __call__. Returns a PIL.Image which we
    convert to base64 PNG.
    """
    model = model_dict["model"]
    generate_method = model_dict.get("generate_method", "generate_image")
    bot_task = model_dict.get("bot_task", "image")

    prompt = input_data.get("prompt", "")
    width = input_data.get("width", 1024)
    height = input_data.get("height", 1024)
    steps = input_data.get("num_inference_steps", _config.get("input_fields", {}).get("num_inference_steps", {}).get("default", 50))
    guidance = input_data.get("guidance_scale", _config.get("input_fields", {}).get("guidance_scale", {}).get("default", 5.0))
    seed = input_data.get("seed")

    # HunyuanImage expects "HxW" format (height first), not "WxH"
    image_size_format = _config.get("image_size_format", "HxW")
    if image_size_format == "WxH":
        image_size = f"{width}x{height}"
    else:
        image_size = f"{height}x{width}"

    gen_fn = getattr(model, generate_method, None)
    if not gen_fn:
        raise ValueError(f"Model has no '{generate_method}' method. Available: {[m for m in dir(model) if 'generat' in m.lower()]}")

    logger.info("Autoregressive generation: size=%s, steps=%d, guidance=%.1f, seed=%s, bot_task=%s",
                image_size, steps, guidance, seed, bot_task)

    import time as _t, threading

    # Background progress logger — since autoregressive models don't emit step callbacks,
    # log elapsed time periodically so CloudWatch shows the job is alive.
    _gen_done = threading.Event()
    _gen_start = _t.time()

    def _progress_logger():
        while not _gen_done.is_set():
            _gen_done.wait(30)  # Log every 30 seconds
            if not _gen_done.is_set():
                elapsed = _t.time() - _gen_start
                logger.info("Autoregressive generation in progress — %.0fs elapsed (%s, %d steps)",
                            elapsed, image_size, steps)

    progress_thread = threading.Thread(target=_progress_logger, daemon=True)
    progress_thread.start()

    gen_kwargs = {
        "prompt": prompt,
        "image_size": image_size,
        "diff_infer_steps": steps,
        "bot_task": bot_task,
        "guidance_scale": guidance,
    }
    if seed is not None:
        gen_kwargs["seed"] = seed

    # Enable block offload hooks during generation (if configured)
    block_offload = model_dict.get("block_offload")
    if block_offload:
        block_offload.enable()
        logger.info("Block offload enabled for inference")

    try:
        result = gen_fn(**gen_kwargs)
    finally:
        if block_offload:
            block_offload.disable()
        _gen_done.set()
        elapsed = _t.time() - _gen_start
        logger.info("Autoregressive generation finished — %.1fs total", elapsed)

    # Result format varies by model. HunyuanImage returns (cot_text, [PIL.Image, ...])
    if isinstance(result, tuple) and len(result) == 2:
        cot_text, samples = result
        if cot_text:
            logger.info("CoT reasoning: %s", cot_text[:200])
        image = samples[0] if samples else None
    elif isinstance(result, list):
        image = result[0] if result else None
    else:
        image = result

    if image is None:
        raise RuntimeError("Model returned no image")

    if hasattr(image, "save"):
        return _encode_image(image)
    elif isinstance(image, str):
        return image
    else:
        raise RuntimeError(f"Unexpected output type: {type(image)}")


def _predict_image_to_3d(input_data, model_dict):
    """Generate a textured 3D mesh (GLB) from an input image.

    Pipeline (3 phases):
      Phase 1: TripoSG geometry generation
        1. Decode base64 input image
        2. Remove background using RMBG (produces alpha mask)
        3. Composite foreground onto white background
        4. Run TripoSG → untextured mesh
        5. Optionally decimate mesh to target face count

      Phase 2: MV-Adapter multi-view generation
        6. Render mesh normals/positions as control signals
        7. Generate 6 multi-view images via SDXL + MV-Adapter

      Phase 3: TexturePipeline texture baking
        8. Project multi-view images onto mesh UV
        9. Export as textured GLB

    Fallback: If Phase 2 or 3 fails (missing models, OOM, any error),
    returns the untextured GLB from Phase 1 (which already works).

    VRAM management on low-VRAM instances (g5, 24GB):
      - Phase 1: TripoSG (8GB) + RMBG (0.5GB) on GPU. Unload after.
      - Phase 2: Load SDXL + MV-Adapter (9GB fp16). Generate views. Unload.
      - Phase 3: Load nvdiffrast + texture pipeline. Bake. Export.
    """
    import trimesh
    import tempfile
    import time as _t

    pipe = model_dict["pipe"]
    rmbg_model = model_dict.get("rmbg_model")
    high_vram = model_dict.get("high_vram", False)
    texture_available = model_dict.get("texture_available", False)

    # 1. Decode input image
    img = _decode_image(input_data["image"]).convert("RGB")
    source_image = img.copy()  # Keep original for MV-Adapter reference
    logger.info("Input image: %dx%d", img.width, img.height)

    # 2. Remove background if RMBG is available
    if rmbg_model is not None:
        logger.info("Removing background with RMBG...")
        orig_size = img.size  # (W, H)
        orig_np = np.array(img)

        # Preprocess: resize to 1024x1024, normalize with RMBG-specific values
        input_tensor = torch.tensor(orig_np, dtype=torch.float32).permute(2, 0, 1)
        input_tensor = torch.nn.functional.interpolate(
            input_tensor.unsqueeze(0), size=[1024, 1024], mode="bilinear"
        )
        input_tensor = torch.divide(input_tensor, 255.0)
        from torchvision.transforms.functional import normalize as tv_normalize
        input_tensor = tv_normalize(input_tensor, [0.5, 0.5, 0.5], [1.0, 1.0, 1.0])
        input_tensor = input_tensor.to("cuda")

        with torch.no_grad():
            output = rmbg_model(input_tensor)

        # Extract mask: RMBG returns nested structure, mask is at [0][0]
        result = output[0][0]
        # Resize mask back to original image size
        result = torch.squeeze(torch.nn.functional.interpolate(
            result, size=[orig_size[1], orig_size[0]], mode="bilinear"
        ), 0)
        # Normalize to 0-255
        ma, mi = torch.max(result), torch.min(result)
        result = (result - mi) / (ma - mi)
        mask_np = (result * 255).permute(1, 2, 0).cpu().numpy().astype(np.uint8)
        mask_np = np.squeeze(mask_np)
        logger.info("RMBG mask: shape=%s, range=[%d, %d]", mask_np.shape, mask_np.min(), mask_np.max())

        # 3. Composite onto white background
        pil_mask = Image.fromarray(mask_np)
        img_rgba = img.copy()
        img_rgba.putalpha(pil_mask)
        white_bg = Image.new("RGBA", orig_size, (255, 255, 255, 255))
        white_bg.paste(img_rgba, mask=img_rgba.split()[3])
        img = white_bg.convert("RGB")
        logger.info("Background removed, composited on white")
    else:
        logger.info("No RMBG model — using input image as-is")

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 1: TripoSG geometry generation
    # ═══════════════════════════════════════════════════════════════════════
    steps = input_data.get("num_inference_steps", 50)
    guidance = input_data.get("guidance_scale", 7.0)
    seed = input_data.get("seed")
    generator = torch.Generator("cuda").manual_seed(seed) if seed is not None else None

    logger.info("Phase 1: TripoSG geometry — steps=%d, guidance=%.1f, seed=%s", steps, guidance, seed)

    t0 = _t.time()
    output = pipe(
        image=img,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
        # Use hierarchical decoder (not flash) — flash requires diso CUDA package.
        # Hierarchical with depth 7 uses 128^3 grid -> fast CPU marching cubes.
        use_flash_decoder=False,
        dense_octree_depth=7,
        hierarchical_octree_depth=8,
    )
    elapsed = _t.time() - t0
    logger.info("Phase 1 complete in %.1fs", elapsed)

    # Extract mesh from output
    if hasattr(output, "meshes") and output.meshes:
        mesh = output.meshes[0]
    elif isinstance(output, tuple) and len(output) >= 2:
        mesh = output[1][0] if output[1] else None
    else:
        raise RuntimeError("Pipeline returned no mesh")

    if mesh is None or (hasattr(mesh, "vertices") and len(mesh.vertices) == 0):
        raise RuntimeError("Pipeline returned an empty mesh")

    logger.info("Mesh: %d vertices, %d faces", len(mesh.vertices), len(mesh.faces))

    # 5. Optionally decimate to target face count
    target_faces = input_data.get("faces", 200000)
    if target_faces > 0 and len(mesh.faces) > target_faces:
        logger.info("Decimating mesh from %d to %d faces", len(mesh.faces), target_faces)
        try:
            mesh = mesh.simplify_quadric_decimation(face_count=target_faces)
            logger.info("Decimated to %d faces", len(mesh.faces))
        except TypeError:
            try:
                ratio = target_faces / len(mesh.faces)
                mesh = mesh.simplify_quadric_decimation(ratio)
                logger.info("Decimated to %d faces (ratio mode)", len(mesh.faces))
            except Exception as e:
                logger.warning("Decimation failed (keeping original): %s", e)
        except Exception as e:
            logger.warning("Decimation failed (keeping original): %s", e)

    # Fix normals early — needed for both untextured and textured paths
    try:
        mesh.fix_normals()
    except Exception:
        pass

    vertex_count = len(mesh.vertices)
    face_count = len(mesh.faces)
    logger.info("Phase 1 mesh: %d vertices, %d faces", vertex_count, face_count)

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 2 + 3: Texture generation (MV-Adapter + TexturePipeline)
    # Falls back to untextured GLB if anything fails.
    # ═══════════════════════════════════════════════════════════════════════
    textured_glb_data = None
    if texture_available:
        try:
            textured_glb_data = _generate_texture(
                mesh, source_image, model_dict, input_data
            )
        except Exception as tex_err:
            logger.warning("Phase 2/3 texture generation failed — falling back to untextured: %s", tex_err)
            import traceback
            logger.debug("Texture error traceback:\n%s", traceback.format_exc())
            textured_glb_data = None
            # Ensure GPU memory is freed after texture failure
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    # ═══════════════════════════════════════════════════════════════════════
    # Export final GLB
    # ═══════════════════════════════════════════════════════════════════════
    if textured_glb_data is not None:
        # Textured GLB from Phase 3
        glb_data = textured_glb_data
        logger.info("Exporting TEXTURED GLB: %.1f KB", len(glb_data) / 1024)
    else:
        # Fallback: untextured GLB with neutral PBR material
        from trimesh.visual.material import PBRMaterial
        mesh.visual = trimesh.visual.TextureVisuals(
            material=PBRMaterial(
                baseColorFactor=[200, 200, 200, 255],
                metallicFactor=0.1,
                roughnessFactor=0.7,
                doubleSided=True,
            )
        )
        glb_data = mesh.export(file_type="glb", include_normals=True)
        logger.info("Exporting UNTEXTURED GLB (fallback): %.1f KB", len(glb_data) / 1024)

    b64_glb = base64.b64encode(glb_data).decode("utf-8")
    return json.dumps({"mesh": b64_glb, "format": "base64_glb", "vertices": vertex_count, "faces": face_count})


def _generate_texture(mesh, source_image, model_dict, input_data):
    """Run Phase 2 (MV-Adapter) + Phase 3 (TexturePipeline) to produce textured GLB.

    This function encapsulates the entire texture generation process so that
    any failure is caught cleanly by the caller and falls back to untextured.

    Args:
        mesh: trimesh.Trimesh from Phase 1
        source_image: Original input PIL Image (for MV-Adapter reference)
        model_dict: Model dictionary from _load_image_to_3d
        input_data: Original request input data

    Returns:
        bytes: GLB file data with baked texture, or raises on failure.
    """
    import tempfile
    import time as _t

    high_vram = model_dict.get("high_vram", False)
    mv_pipe = model_dict.get("mv_pipe")
    texture_pipe = model_dict.get("texture_pipe")
    code_dir = model_dict.get("code_dir", "")
    hf_token = model_dict.get("hf_token")

    temp_dir = tempfile.mkdtemp(prefix="artsmoker_texture_")

    try:
        # Save mesh to temp file for the texture pipeline
        import trimesh as _trimesh
        mesh_path = os.path.join(temp_dir, "geometry.glb")
        mesh.export(mesh_path, file_type="glb", include_normals=True)
        logger.info("Phase 2: Saved geometry to %s", mesh_path)

        # On low VRAM: unload TripoSG + RMBG before loading MV-Adapter
        if not high_vram:
            logger.info("Low VRAM mode: unloading TripoSG + RMBG for Phase 2...")
            triposg_pipe = model_dict.get("pipe")
            rmbg = model_dict.get("rmbg_model")
            if triposg_pipe is not None:
                triposg_pipe.to("cpu")
            if rmbg is not None:
                rmbg.to("cpu")
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            if torch.cuda.is_available():
                freed = torch.cuda.memory_reserved(0) / (1024**3)
                logger.info("Freed GPU memory: reserved=%.1f GB", freed)

        # ═══════════════════════════════════════════════════════════════════
        # Phase 2: MV-Adapter multi-view generation
        # ═══════════════════════════════════════════════════════════════════
        t0 = _t.time()
        logger.info("Phase 2: MV-Adapter multi-view generation...")

        # Load MV-Adapter on-demand if not preloaded (low VRAM path)
        if mv_pipe is None:
            logger.info("Loading MV-Adapter on-demand...")
            mv_pipe, texture_pipe = _load_texture_models(code_dir, hf_token)

        from mvadapter.utils.mesh_utils import (
            get_orthogonal_camera, load_mesh, render, NVDiffRastContextWrapper
        )

        # Set up cameras for 6 orthogonal views
        cameras = get_orthogonal_camera(
            elevation_deg=[0, 0, 0, 0, 89.99, -89.99],
            distance=[1.8] * 6,
            left=-0.55, right=0.55, bottom=-0.55, top=0.55,
            azimuth_deg=[-90, 0, 90, 180, 90, 90],
            device="cuda",
        )

        # Render mesh normals/positions as control signals for MV-Adapter
        ctx = NVDiffRastContextWrapper(device="cuda", context_type="cuda")
        mesh_obj = load_mesh(mesh_path, rescale=True, device="cuda")
        render_out = render(
            ctx, mesh_obj, cameras,
            height=768, width=768,
            render_attr=False,
            normal_background=0.0,
        )

        # Concatenate position + normal maps as control image (6 views, 6 channels)
        control_images = torch.cat([
            (render_out.pos + 0.5).clamp(0, 1),
            (render_out.normal / 2 + 0.5).clamp(0, 1),
        ], dim=-1).permute(0, 3, 1, 2)  # (6, 6, H, W)

        # Generate multi-view images conditioned on geometry + reference image
        mv_result = mv_pipe(
            "high quality",
            height=768, width=768,
            num_inference_steps=15,
            guidance_scale=3.0,
            num_images_per_prompt=6,
            control_image=control_images,
            control_conditioning_scale=1.0,
            reference_image=source_image,
            reference_conditioning_scale=1.0,
            negative_prompt="watermark, ugly, deformed, noisy, blurry",
        )
        mv_images = mv_result.images
        elapsed_p2 = _t.time() - t0
        logger.info("Phase 2 complete in %.1fs — generated %d multi-view images", elapsed_p2, len(mv_images))

        # Save multi-view images as a packed grid (6 images side by side)
        mv_grid = _make_mv_grid(mv_images)
        mv_grid_path = os.path.join(temp_dir, "mv_grid.png")
        mv_grid.save(mv_grid_path)
        logger.info("Saved multi-view grid: %dx%d", mv_grid.width, mv_grid.height)

        # On low VRAM: unload MV-Adapter before Phase 3
        if not high_vram:
            logger.info("Low VRAM mode: unloading MV-Adapter for Phase 3...")
            del mv_pipe
            model_dict["mv_pipe"] = None
            import gc
            gc.collect()
            torch.cuda.empty_cache()

        # ═══════════════════════════════════════════════════════════════════
        # Phase 3: TexturePipeline texture baking
        # ═══════════════════════════════════════════════════════════════════
        t0 = _t.time()
        logger.info("Phase 3: Texture baking...")

        from mvadapter.pipelines.pipeline_texture import TexturePipeline, ModProcessConfig

        # Use existing texture_pipe if preloaded, otherwise it was loaded in Phase 2
        if texture_pipe is None:
            texture_pipe = TexturePipeline(
                upscaler_ckpt_path=None,
                inpaint_ckpt_path=None,
                device="cuda",
            )

        tex_output = texture_pipe(
            mesh_path=mesh_path,
            save_dir=temp_dir,
            save_name="textured",
            uv_unwarp=True,
            uv_size=2048,  # 2K texture (4K too large for response)
            rgb_path=mv_grid_path,
            camera_azimuth_deg=[0, 90, 180, 270, 180, 180],
            camera_elevation_deg=[0, 0, 0, 0, 89.99, -89.99],
        )
        elapsed_p3 = _t.time() - t0
        logger.info("Phase 3 complete in %.1fs", elapsed_p3)

        # Read the textured GLB output
        textured_path = tex_output.shaded_model_save_path
        if textured_path and os.path.exists(textured_path):
            with open(textured_path, "rb") as f:
                glb_data = f.read()
            logger.info("Textured GLB: %.1f KB from %s", len(glb_data) / 1024, textured_path)
        else:
            raise RuntimeError(f"TexturePipeline did not produce output (path={textured_path})")

        # On low VRAM: reload TripoSG + RMBG back to GPU for next inference
        if not high_vram:
            logger.info("Low VRAM mode: reloading TripoSG + RMBG to GPU...")
            triposg_pipe = model_dict.get("pipe")
            rmbg = model_dict.get("rmbg_model")
            if triposg_pipe is not None:
                triposg_pipe.to("cuda")
            if rmbg is not None:
                rmbg.to("cuda")

        return glb_data

    finally:
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def _make_mv_grid(images):
    """Create a horizontal grid of PIL images (packed side by side).

    The TexturePipeline expects a single image with 6 views concatenated
    horizontally (N*W, H). This is the standard MV-Adapter output format.
    """
    if not images:
        raise ValueError("No images to grid")
    widths = [img.width for img in images]
    height = images[0].height
    total_width = sum(widths)
    grid = Image.new("RGB", (total_width, height))
    x_offset = 0
    for img in images:
        grid.paste(img, (x_offset, 0))
        x_offset += img.width
    return grid


_PREDICTORS = {
    "text_to_image": _predict_text_to_image,
    "autoregressive_image": _predict_autoregressive_image,
    "image_to_video": _predict_image_to_video,
    "image_to_3d": _predict_image_to_3d,
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
        return prediction  # Already JSON (e.g., 3D mesh with stats, video frames)
    return json.dumps({"image": prediction, "format": "base64_png"})
