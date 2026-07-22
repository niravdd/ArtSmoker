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
_model_dir = None  # Set in model_fn — needed by dev hot-reload to locate code/

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


# ── Dev hot-reload (generic code overlay) ──────────────────────────────────
# On a dev box, the deployer sets ARTSMOKER_DEV_HOTRELOAD=1 and points
# ARTSMOKER_HOTRELOAD_KEY at an S3 overlay archive (overlay.tar.gz, rooted at
# "code/"). Before each inference, predict_fn checks that object's ETag. If it
# changed, we:
#   1. extract the overlay over <model_dir>/code/ (the real inference.py +
#      bundled packages like mvadapter/ triposg/),
#   2. drop the bundled top-level packages from sys.modules so the next
#      function-level import picks up the new source,
#   3. re-exec the new inference.py's predictor functions into THIS module's
#      globals, so the updated _predict_* logic is what runs.
# The reloaded predictor then runs against the already-loaded (warm) model_dict
# — no scale-in, no weight reload. Fully model-agnostic: it reloads whatever
# code/ contains and dispatches by PREDICTOR_TYPE. Prod is unaffected (flag
# absent). The loader (model_fn) is intentionally NOT re-run — weights stay warm.
_hotreload_state = {"etag": None}

# Writable overlay root. SageMaker mounts /opt/ml/model (the baked code/) as
# READ-ONLY, so we CANNOT extract there. Instead we extract to /tmp and prepend
# it to sys.path so its packages shadow the baked ones, and re-exec the overlaid
# inference.py from here. This is what makes hot-reload actually work on SM.
_HOTRELOAD_DIR = "/tmp/artsmoker_hotreload/code"

# Names re-bound into this module's globals when inference.py is overlaid.
# Limited to the predictor surface (functions + their module-level constants
# are re-exec'd wholesale, but we only swap callables/dicts, never touch live
# model state, env, or the cache globals).
_HOTRELOAD_PROTECTED_GLOBALS = {
    "_model", "_config", "_model_dir", "_loaded_from_cache",
    "_all_preserved_from_cache", "_cache_info", "_hotreload_state",
    "os", "sys", "json", "torch", "np", "Image", "logger", "logging",
    "importlib", "io", "base64",
}


def _bundled_top_level_packages():
    """Top-level package names present in the overlay or baked code/ (e.g. mvadapter)."""
    pkgs = set()
    dirs = [_HOTRELOAD_DIR]
    if _model_dir:
        dirs.append(os.path.join(_model_dir, "code"))
    for code_dir in dirs:
        try:
            for name in os.listdir(code_dir):
                p = os.path.join(code_dir, name)
                if os.path.isdir(p) and os.path.exists(os.path.join(p, "__init__.py")):
                    pkgs.add(name)
        except Exception:
            pass
    return sorted(pkgs)


def _apply_code_overlay(tar_bytes):
    """Extract an overlay tar (rooted at code/) into a WRITABLE /tmp dir.

    SageMaker mounts the baked code dir (/opt/ml/model/code) read-only, so we
    extract to _HOTRELOAD_DIR instead and prepend it to sys.path (front) so its
    modules shadow the baked ones. Strips any leading "code/" arc prefix.
    Afterwards removes __pycache__, bumps mtimes, and invalidates import caches
    so Python doesn't reuse stale bytecode.
    """
    import tarfile
    import importlib as _il
    import shutil as _sh
    import sys as _sys
    code_dir = _HOTRELOAD_DIR
    # Fresh dir each apply so removed files don't linger.
    _sh.rmtree(code_dir, ignore_errors=True)
    os.makedirs(code_dir, exist_ok=True)
    extracted = []
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if name.startswith("code/"):
                name = name[len("code/"):]
            if not name or name.startswith("/") or ".." in name.split("/"):
                continue  # path-traversal guard
            member.name = name
            tar.extract(member, path=code_dir)
            extracted.append(os.path.join(code_dir, name))
    # Prepend overlay dir to sys.path so its packages take import precedence.
    if code_dir in _sys.path:
        _sys.path.remove(code_dir)
    _sys.path.insert(0, code_dir)
    # Invalidate any cached bytecode for the overlaid files.
    import time as _time
    now = _time.time()
    for root, dirs, files in os.walk(code_dir):
        if "__pycache__" in dirs:
            _sh.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)
            dirs.remove("__pycache__")
    for path in extracted:
        try:
            if os.path.isfile(path):
                os.utime(path, (now, now))
        except Exception:
            pass
    _il.invalidate_caches()
    return True


def _reload_handler_predictors():
    """Re-exec the overlaid inference.py and rebind predictor globals.

    Runs the new inference.py (from the writable overlay dir) in a scratch
    namespace, then copies its _predict_* functions, helper functions, module
    constants, and the _PREDICTORS dict into THIS live module's globals —
    except protected runtime state (model, config, caches, stdlib handles).
    """
    code_path = os.path.join(_HOTRELOAD_DIR, "inference.py")
    if not os.path.exists(code_path):
        return False
    with open(code_path, "r") as f:
        src = f.read()
    g = globals()
    scratch = {"__name__": g.get("__name__", "inference"), "__file__": code_path}
    # Seed protected runtime objects so the new code's module-level statements
    # (if any run at import) see consistent state. We exec defs/consts only —
    # the new file's top-level executable code is the same shape as the running
    # one, so this is safe in practice for our handler.
    exec(compile(src, code_path, "exec"), scratch)  # noqa: S102 — dev only
    swapped = 0
    for k, v in scratch.items():
        if k.startswith("__"):
            continue
        if k in _HOTRELOAD_PROTECTED_GLOBALS:
            continue
        # Only swap functions, the predictor/loader dicts, and constants.
        if callable(v) or isinstance(v, (dict, int, float, str, list, tuple, bool)):
            g[k] = v
            swapped += 1
    logger.info("Hot-reload: re-bound %d symbols from overlaid inference.py", swapped)
    return True


def _maybe_apply_hotreload():
    """If a changed dev overlay is staged in S3, apply it. Best-effort.

    Returns True if an overlay was (re)applied this call. Never raises into
    the inference path.
    """
    if _get_env("ARTSMOKER_DEV_HOTRELOAD") != "1" or not _model_dir:
        return False
    bucket = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET")
    key = _get_env("ARTSMOKER_HOTRELOAD_KEY")
    if not bucket or not key:
        return False
    try:
        import boto3
        s3 = boto3.client("s3")
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
        except Exception:
            return False  # no overlay staged
        etag = head.get("ETag")
        if etag == _hotreload_state["etag"]:
            return False  # unchanged since last apply
        logger.info("Hot-reload: new code overlay detected (etag=%s) — applying", etag)
        tar_bytes = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        _apply_code_overlay(tar_bytes)
        # Drop bundled top-level packages so the next import is fresh.
        import sys as _sys
        for pkg in _bundled_top_level_packages():
            for mod_name in [m for m in list(_sys.modules) if m == pkg or m.startswith(pkg + ".")]:
                _sys.modules.pop(mod_name, None)
            logger.info("Hot-reload: purged package '%s' from sys.modules", pkg)
        _reload_handler_predictors()
        _hotreload_state["etag"] = etag
        logger.info("Hot-reload: overlay applied — warm model reused, predictors refreshed")
        return True
    except Exception as e:
        logger.warning("Hot-reload: overlay apply failed (%s) — using current code", e)
        return False


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


def _load_trellis2_image_to_3d(model_dir):
    """Load the STANDALONE full TRELLIS.2 image→3D pipeline (no TripoSG).

    Distinct from _load_image_to_3d (TripoSG + texture-backend): this generates
    BOTH geometry and texture from TRELLIS.2 alone. At LOAD time we only need to
    (a) build the TRELLIS.2 CUDA-ext stack + python deps (the heavy part — must
    happen before MMS's 120s inference watchdog), and (b) load the lightweight
    BiRefNet (MIT) background-remover for the RGBA cutout. The 8-checkpoint
    pipeline itself loads lazily on the first inference (_load_trellis2_full_pipe),
    so model_fn returns fast and the endpoint reports InService promptly.
    """
    code_dir = os.path.join(model_dir, "code")
    hf_token = _get_env("HUGGING_FACE_HUB_TOKEN") or None

    # Build the TRELLIS.2 stack (clone + o_voxel/cumesh/flex_gemm/nvdiffrast +
    # transformers>=4.56 + xformers) at LOAD time, then S3-cache. Mirrors the
    # `trellis2` texture-backend load branch. On failure, retry in background.
    trellis2_ready = False
    try:
        _ensure_trellis2(blocking=True)
        _trellis2_ops_bg["state"] = 1
        trellis2_ready = True
        logger.info("TRELLIS.2 full-pipeline stack ready (built/cached at load)")
    except Exception as e:
        logger.warning("TRELLIS.2 stack not ready at load (%s) — will retry in background on first job", e)
        _ensure_trellis2_background()

    # Background remover for the RGBA cutout (BiRefNet/MIT default; RMBG opt-in).
    rmbg_model = None
    try:
        secondary_sources = _config.get("secondary_sources", {})
        bg_choice = (_get_env("ARTSMOKER_BG_MODEL", "birefnet") or "birefnet").lower().strip()
        if bg_choice == "rmbg":
            bg_repo = secondary_sources.get("rmbg", {}).get("repo_id") or "briaai/RMBG-1.4"
        else:
            bg_repo = secondary_sources.get("birefnet", {}).get("repo_id") or "ZhengPeng7/BiRefNet"
        logger.info("Downloading background-removal model (%s) from %s...", bg_choice, bg_repo)
        from transformers import AutoModelForImageSegmentation
        rmbg_model = AutoModelForImageSegmentation.from_pretrained(
            bg_repo, trust_remote_code=True, token=hf_token,
        )
        rmbg_model.to("cuda").eval()
        try:
            rmbg_model._artsmoker_bg_backend = "rmbg" if bg_choice == "rmbg" else "birefnet"
        except Exception:
            pass
        logger.info("Background-removal model loaded on GPU (%s)", bg_choice)
    except Exception as e:
        logger.warning("Background-removal model load failed (will skip bg removal): %s", e)

    vram_gb = 0
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        vram_gb = (getattr(props, 'total_memory', 0) or getattr(props, 'total_mem', 0)) / (1024**3)

    return {
        "library": "trellis2_image_to_3d",
        "pipe": None,                 # full pipeline loads lazily in the predictor
        "rmbg_model": rmbg_model,
        "texture_available": trellis2_ready,
        "vram_gb": vram_gb,
        "code_dir": code_dir,
        "hf_token": hf_token,
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

    # Load the background-removal model for preprocessing. The mask model is
    # SELECTABLE so we can use a commercially-licensed one without deleting the
    # old path: BiRefNet (ZhengPeng7/BiRefNet, MIT code+weights) is the default;
    # RMBG (briaai/RMBG-1.4, CC-BY-NC / non-commercial) stays available behind
    # ARTSMOKER_BG_MODEL=rmbg, so if BRIA's terms change we just flip the flag.
    # Both load identically (AutoModelForImageSegmentation + trust_remote_code)
    # and produce a foreground mask; the per-model differences (input
    # normalization, output indexing) are handled in _foreground_mask_np().
    rmbg_model = None
    try:
        secondary_sources = _config.get("secondary_sources", {})
        bg_choice = (_get_env("ARTSMOKER_BG_MODEL", "birefnet") or "birefnet").lower().strip()
        if bg_choice == "rmbg":
            bg_repo = secondary_sources.get("rmbg", {}).get("repo_id") or "briaai/RMBG-1.4"
        else:
            bg_repo = secondary_sources.get("birefnet", {}).get("repo_id") or "ZhengPeng7/BiRefNet"

        logger.info("Downloading background-removal model (%s) from %s...", bg_choice, bg_repo)
        from transformers import AutoModelForImageSegmentation
        rmbg_model = AutoModelForImageSegmentation.from_pretrained(
            bg_repo, trust_remote_code=True, token=hf_token,
        )
        rmbg_model.to("cuda").eval()
        # Tag the model so the mask helper knows which convention to use.
        try:
            rmbg_model._artsmoker_bg_backend = "rmbg" if bg_choice == "rmbg" else "birefnet"
        except Exception:
            pass
        logger.info("Background-removal model loaded on GPU (%s)", bg_choice)
    except Exception as e:
        logger.warning("Background-removal model load failed (will skip bg removal): %s", e)

    # Detect VRAM for adaptive loading strategy
    vram_gb = 0
    high_vram = False
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        vram_gb = (getattr(props, 'total_memory', 0) or getattr(props, 'total_mem', 0)) / (1024**3)
        high_vram = vram_gb >= 40  # g6e (48GB) vs g5 (24GB)
    logger.info("VRAM: %.1f GB — texture pipeline strategy: %s",
                vram_gb, "preloaded" if high_vram else "on-demand")

    # Texture backend: "mvadapter" (default, original 6-view+TexturePipeline) or
    # "hunyuan" (Hunyuan3D-Paint). Both are retained; the server default is set
    # via ARTSMOKER_TEXTURE_BACKEND. The native ops each backend needs are built
    # HERE at load time (model_fn — no MMS response watchdog), then cached to S3,
    # exactly like the nvdiffrast pattern, so the first inference never trips the
    # 120s watchdog compiling.
    mv_pipe = None
    texture_pipe = None
    paint_pipe = None
    texture_available = False
    backend = _texture_backend()
    logger.info("Texture backend (server default): %s", backend)

    if backend == "hunyuan":
        # Build custom_rasterizer + mesh_inpaint_processor at load time.
        try:
            import hy3dpaint  # noqa: F401  (package presence check; vendored)
        except Exception:
            pass  # the dir is on disk; textureGenPipeline imports happen in _load_hunyuan_paint
        try:
            _ensure_hunyuan_ops(code_dir, blocking=True)
            _hunyuan_ops_bg["state"] = 1
            logger.info("Hunyuan native ops ready (built/cached at load)")
            texture_available = True
        except Exception as e:
            logger.warning("Hunyuan ops not ready at load (%s) — will retry in background on first job", e)
        # Preload the paint pipe on high-VRAM. Paint (~21 GB) + TripoSG (~16 GB)
        # ~= 37 GB at idle, fits the 44.5 GB L40S; the proven meta-eviction frees
        # TripoSG's VRAM during texturing regardless.
        if high_vram and texture_available:
            try:
                paint_pipe = _load_hunyuan_paint(code_dir, hf_token)
                logger.info("Hunyuan3D-Paint preloaded (high VRAM mode)")
            except Exception as e:
                logger.warning("Hunyuan paint preload failed (will load on-demand): %s", e)
    elif backend == "trellis2":
        # ── TRELLIS.2 backend (MIT, commercial-clean) ──
        # The `trellis2` package + 3 CUDA extensions (o_voxel/cumesh/flex_gemm) +
        # nvdiffrast are git-cloned and built HERE at load (the build far exceeds
        # MMS's 120s response watchdog), then S3-cached so later cold starts are
        # fast. The texturing checkpoints + DINOv3 are pulled lazily on first job.
        try:
            _ensure_trellis2(blocking=True)
            _trellis2_ops_bg["state"] = 1
            texture_available = True
            logger.info("TRELLIS.2 stack ready (built/cached at load)")
        except Exception as e:
            logger.warning("TRELLIS.2 not ready at load (%s) — will retry in background on first job", e)
            _ensure_trellis2_background()
    else:
        # ── MV-Adapter backend (default, UNCHANGED behavior) ──
        if high_vram:
            try:
                mv_pipe, texture_pipe = _load_texture_models(code_dir, hf_token)
                texture_available = True
                logger.info("MV-Adapter + TexturePipeline preloaded (high VRAM mode)")
            except Exception as e:
                logger.warning("Texture pipeline preload failed (will try on-demand): %s", e)
        else:
            # Low-VRAM path: don't preload MV-Adapter weights, but compile
            # nvdiffrast at LOAD time (lazy compile inside predict_fn would block
            # past MMS's 120s response watchdog → worker reboot mid-job).
            try:
                import mvadapter  # noqa: F401
                texture_available = True
                logger.info("MV-Adapter package available — texture models load on-demand per inference")
                try:
                    _ensure_rasterizer()  # install kaolin (or compile nvdiffrast) at LOAD time
                    if _rasterizer_choice() == "nvdiffrast":
                        _nvdiffrast_bg["state"] = 1
                    logger.info("Rasterizer ready at load (%s) — texture phases enabled", _rasterizer_choice())
                except Exception as e:
                    logger.warning("Rasterizer not ready at load (%s) — will retry in background on first texture job", e)
            except ImportError:
                logger.info("MV-Adapter package not available — will produce untextured meshes")

    return {
        "library": "image_to_3d",
        "pipe": pipe,
        "rmbg_model": rmbg_model,
        "mv_pipe": mv_pipe,
        "texture_pipe": texture_pipe,
        "paint_pipe": paint_pipe,
        "texture_backend": backend,
        "texture_available": texture_available,
        "high_vram": high_vram,
        "vram_gb": vram_gb,
        "code_dir": code_dir,
        "hf_token": hf_token,
        # Local HF snapshot dir — lets us rebuild TripoSG cheaply (no re-download)
        # if we EVICT it (rather than CPU-park) to survive low host RAM before
        # the texture phases. See _reload_triposg / the park-or-evict logic.
        "triposg_local_path": local_path,
        "_triposg_evicted": False,
    }


# S3 prefix for cached texture-pipeline dependencies (nvdiffrast wheel,
# RealESRGAN upscaler, LaMa inpainter). The nvdiffrast wheel lives under a
# /nvdiffrast/ subfolder of this.
_TEXTURE_DEPS_PREFIX = "artsmoker/custom-models/texture-deps"
_NVDIFFRAST_WHEEL_PREFIX = f"{_TEXTURE_DEPS_PREFIX}/nvdiffrast/"
# Cached native ops for the Hunyuan3D-Paint backend (built at load, like
# nvdiffrast): the custom_rasterizer CUDA extension wheel and the
# mesh_inpaint_processor pybind .so.
_HUNYUAN_DEPS_PREFIX = f"{_TEXTURE_DEPS_PREFIX}/hunyuan"
_HUNYUAN_INPAINT_SO_PREFIX = f"{_HUNYUAN_DEPS_PREFIX}/mesh_inpaint_processor/"


def _gpu_arch_tag() -> str:
    """Compute-capability tag of the current GPU, e.g. 'sm_89' (L40S) or
    'sm_86' (A10G). CUDA-compiled artifacts (wheels/.so) are NOT portable across
    architectures, so this tags both the build flags and the S3 wheel cache so a
    wheel built on one GPU family is never loaded on another. Falls back to
    'sm_89' (the original hardcoded L40S target) if the device can't be probed,
    preserving prior behavior on the validated g6e path."""
    try:
        import torch
        if torch.cuda.is_available():
            major, minor = torch.cuda.get_device_capability()
            return f"sm_{major}{minor}"
    except Exception:
        pass
    return "sm_89"


def _torch_arch_list() -> str:
    """TORCH_CUDA_ARCH_LIST value for the current GPU, e.g. '8.9' or '8.6'."""
    tag = _gpu_arch_tag()[3:]  # strip 'sm_'
    return f"{tag[0]}.{tag[1:]}" if len(tag) >= 2 else "8.9"


# CUDA-compiled wheel caches are namespaced by GPU arch so an L40S (sm_89) wheel
# is never pulled onto an A10G (sm_86) and vice-versa. Each is a property-style
# helper so the arch is resolved at call time (after CUDA is up), not import.
def _hunyuan_rasterizer_wheel_prefix() -> str:
    return f"{_HUNYUAN_DEPS_PREFIX}/custom_rasterizer/{_gpu_arch_tag()}/"

_hunyuan_ops_bg = {"state": -1, "error": ""}
_hunyuan_ops_bg_lock = None

# ── TRELLIS.2 (Microsoft, MIT) texturing backend ─────────────────────────────
# Commercial-clean Hunyuan-grade texturer. The `trellis2` package + its 3 CUDA
# extensions (o_voxel, cumesh, flex_gemm) are NOT pip-installable from an index;
# we git-clone + build at LOAD time (like nvdiffrast) and S3-cache the wheels.
# nvdiffrast is shared with the existing _ensure_nvdiffrast path. LICENSE NOTE:
# nvdiffrast is under the NVIDIA Source Code License (1-Way Commercial) —
# NON-commercial for general users, NOT MIT. o_voxel/postprocess.py (the to_glb
# bake) hard-imports it at module load, so the full TRELLIS.2 pipeline currently
# carries a non-commercial rasterizer dependency. This is disclosed in the
# catalog license_agreement.dependencies for trellis2_image_to_3d (and SPEC §12).
# (The separate MV-Adapter texture path defaults to Kaolin/Apache-2.0 instead —
# see _rasterizer_choice — but o_voxel's internal import cannot be swapped without
# patching upstream microsoft/TRELLIS.2.)
# The DINOv3 image encoder (gated, commercial-OK) is pulled at runtime via HF
# token — requires a "Built with DINOv3" attribution in the product UI.
_TRELLIS2_REPO = "https://github.com/microsoft/TRELLIS.2.git"
_TRELLIS2_RUN_DIR = "/tmp/trellis2_run"          # writable clone (package on sys.path)
_TRELLIS2_DEPS_PREFIX = f"{_TEXTURE_DEPS_PREFIX}/trellis2"
# cached o_voxel/cumesh/flex_gemm wheels — arch-namespaced (sm_89 L40S, sm_86 A10G,
# …) since CUDA-compiled wheels are NOT portable across GPU architectures.
def _trellis2_wheel_prefix() -> str:
    return f"{_TRELLIS2_DEPS_PREFIX}/wheels/{_gpu_arch_tag()}/"
_TRELLIS2_REPO_REF = "main"                      # pin if upstream churns
# o_voxel ships in-repo; cumesh + flexgemm are external git (per setup.sh).
# CRITICAL: these MUST be cloned --recursive — CuMesh compiles its submodules
# (cubvh, xatlas, eigen), and `pip install git+...` clones NON-recursively, so the
# submodule sources are missing → a silently broken simplify/remesh that SHREDS
# the mesh into thousands of fragments. TRELLIS.2's setup.sh clones --recursive
# precisely for this. We clone to a local dir recursively, then pip-install the dir.
_TRELLIS2_EXT_GIT = {
    "cumesh": "https://github.com/JeffreyXiang/CuMesh.git",
    "flex_gemm": "https://github.com/JeffreyXiang/FlexGEMM.git",
}
# NOTE: nvdiffrast is built by the SHARED _ensure_nvdiffrast (also used by the
# working Hunyuan/MVPainter texturers) at HEAD. We deliberately do NOT pin it here
# — changing the shared builder would disturb those validated paths. nvdiffrast is
# JIT-compiled at runtime (arch auto-handled) and a low-probability contributor;
# revisit pinning to v0.4.0 ONLY if the cumesh-submodule fix doesn't fully resolve.
_trellis2_ops_bg = {"state": -1, "error": ""}
_trellis2_ops_bg_lock = None
# HF model repo (texturing checkpoints ~6.8 GB pulled at from_pretrained). The
# texturing config selects only the 4 texturing checkpoints out of the 16.2 GB
# repo. ATTN_BACKEND=xformers: the SLAT sparse transformer has NO sdpa fallback
# (only xformers/flash_attn) — xformers ships prebuilt cu124 wheels, so we avoid
# the flash-attn source compile entirely.
_TRELLIS2_HF_REPO = "microsoft/TRELLIS.2-4B"
_TRELLIS2_TEX_CONFIG = "texturing_pipeline.json"   # texturer (BYO mesh): 4 ckpts
_TRELLIS2_FULL_CONFIG = "pipeline.json"            # full image→3D: 8 ckpts (~16 GB)
_trellis2_texture_pipe = None  # cached per worker, reused across jobs
_trellis2_full_pipe = None     # cached full image→3D pipeline (per worker)

# Background nvdiffrast-compile state (for the inference-time guard). When a
# compile is kicked off on a worker thread, predict_fn fails the current job
# FAST (under MMS's 120s response watchdog) rather than blocking; subsequent
# jobs find nvdiffrast ready. -1=not started, 0=compiling, 1=done, 2=failed.
_nvdiffrast_bg = {"state": -1, "error": ""}
_nvdiffrast_bg_lock = None  # lazily created threading.Lock


def _ensure_nvdiffrast(blocking: bool = True) -> bool:
    """Make nvdiffrast importable. Returns True if available now.

    Resolution order (works for ANY end user, no pre-upload required):
      1. Already importable (warm worker, or installed at load).
      2. Download a pre-compiled wheel from the user's OWN S3 cache (fast).
      3. Compile from source (~60-120s) and cache the wheel to that S3 for all
         future cold starts.

    CRITICAL: compiling takes longer than MMS's 120s inference response timeout.
    So this MUST run at LOAD time (model_fn — generous load timeout, no response
    watchdog), NOT inside predict_fn. When called with blocking=False (the
    inference-time guard), it returns immediately if a compile is needed so the
    caller can avoid tripping the watchdog.

    The compiled wheel keeps its REAL basename in S3 (pip requires a 5-part
    wheel filename: name-version-pytag-abitag-platform).
    """
    try:
        import nvdiffrast  # noqa: F401
        return True
    except ImportError:
        pass

    if not blocking:
        return False  # caller must not block under the response watchdog

    import subprocess
    import boto3 as _boto3
    from botocore.exceptions import ClientError as _BotoClientError

    s3 = _boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
    bucket = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET") or ""

    # Step 2: pre-compiled wheel from the user's S3 cache.
    if bucket:
        try:
            logger.info("Checking S3 for pre-compiled nvdiffrast wheel (s3://%s/%s)...", bucket, _NVDIFFRAST_WHEEL_PREFIX)
            listing = s3.list_objects_v2(Bucket=bucket, Prefix=_NVDIFFRAST_WHEEL_PREFIX)
            wheel_objs = [o["Key"] for o in listing.get("Contents", []) if o["Key"].endswith(".whl")]
            if wheel_objs:
                wheel_key = wheel_objs[0]
                wheel_basename = os.path.basename(wheel_key)  # real 5-part name
                wheel_path = os.path.join("/tmp", wheel_basename)
                s3.download_file(bucket, wheel_key, wheel_path)
                subprocess.check_call(["pip", "install", "--quiet", "--no-deps", "--force-reinstall", wheel_path], timeout=120)
                import nvdiffrast  # noqa: F401
                logger.info("nvdiffrast installed from S3 cache (%s)", wheel_basename)
                return True
            logger.info("No cached nvdiffrast wheel in S3 — will compile from source")
        except _BotoClientError:
            logger.info("No cached nvdiffrast wheel in S3 — will compile from source")
        except Exception as e:
            logger.info("S3 cache load failed (%s) — will compile from source", e)

    # Step 3: compile from source, then cache the wheel to S3.
    logger.info("Compiling nvdiffrast from source (requires CUDA toolkit, ~60-120s)...")
    try:
        subprocess.check_call(["pip", "install", "--quiet", "setuptools", "wheel", "ninja"], timeout=120)
        if not os.environ.get("CUDA_HOME"):
            for p in ["/usr/local/cuda", "/opt/conda", "/usr/local/cuda-12.4", "/usr/local/cuda-12"]:
                if os.path.isfile(os.path.join(p, "bin", "nvcc")):
                    os.environ["CUDA_HOME"] = p
                    logger.info("Set CUDA_HOME=%s", p)
                    break
        subprocess.check_call(
            ["pip", "install", "--no-build-isolation", "--no-deps",
             "git+https://github.com/NVlabs/nvdiffrast.git"],
            timeout=600, env={**os.environ},
        )
        import nvdiffrast  # noqa: F401
        logger.info("nvdiffrast compiled and installed successfully")

        if bucket:
            try:
                import glob
                pip_cache_wheels = glob.glob("/tmp/pip-ephem-wheel-cache-*/wheels/**/nvdiffrast*.whl", recursive=True)
                wheel_src = pip_cache_wheels[0] if pip_cache_wheels else None
                if not wheel_src:
                    wheel_dir = "/tmp/nvdiffrast_wheel_export"
                    os.makedirs(wheel_dir, exist_ok=True)
                    subprocess.check_call(
                        ["pip", "wheel", "--no-build-isolation", "--no-deps",
                         "--wheel-dir", wheel_dir, "git+https://github.com/NVlabs/nvdiffrast.git"],
                        timeout=600, env={**os.environ},
                    )
                    found = glob.glob(os.path.join(wheel_dir, "nvdiffrast*.whl"))
                    wheel_src = found[0] if found else None
                if wheel_src:
                    wkey = _NVDIFFRAST_WHEEL_PREFIX + os.path.basename(wheel_src)
                    s3.upload_file(wheel_src, bucket, wkey)
                    logger.info("Cached nvdiffrast wheel to S3: s3://%s/%s", bucket, wkey)
            except Exception as cache_err:
                logger.warning("Failed to cache nvdiffrast wheel to S3: %s", cache_err)
        return True
    except Exception as e:
        logger.error("nvdiffrast compilation failed: %s", e)
        raise ImportError(f"nvdiffrast unavailable — texture generation requires CUDA compilation: {e}")


def _pip_install_build_cached(pkg_name, build_spec, s3_glob, blocking=True, verify_import=True):
    """Generic: make a source-built package importable, S3-caching its wheel.

    Mirrors _ensure_nvdiffrast for any --no-build-isolation git/dir package:
      1. already importable → True
      2. cached wheel in S3 (arch-namespaced, _trellis2_wheel_prefix()) → pip install it
      3. build from `build_spec` (a pip-installable path/URL), then cache the
         wheel to S3 for future cold starts.
    `pkg_name` is the python import name; `s3_glob` is the wheel-name prefix to
    match in S3 (e.g. 'o_voxel'). Returns True on success. blocking=False bails
    immediately if a build would be needed (inference-watchdog guard).

    verify_import=False skips the import checks (the fast-path AND the post-build
    verify) and decides "already installed" by distribution metadata instead. Use
    it for packages with cross-dependencies that can't import until a sibling is
    present (e.g. o_voxel imports flex_gemm at module load): the caller builds the
    whole set in dependency order, then imports once at the end."""
    import importlib
    if verify_import:
        try:
            importlib.import_module(pkg_name)
            return True
        except Exception:
            pass
    else:
        # Can't import yet (siblings may be missing) — check install metadata.
        try:
            import importlib.metadata as _md
            _md.distribution(pkg_name)
            return True
        except Exception:
            pass
    if not blocking:
        return False
    import subprocess, glob as _glob
    import boto3 as _boto3
    s3 = _boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
    bucket = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET") or ""
    # 1. CUDA_HOME for nvcc
    if not os.environ.get("CUDA_HOME"):
        for p in ["/usr/local/cuda", "/usr/local/cuda-12.4", "/usr/local/cuda-12", "/opt/conda"]:
            if os.path.isfile(os.path.join(p, "bin", "nvcc")):
                os.environ["CUDA_HOME"] = p
                break
    # Pin the CUDA-ext compile (cumesh/flex_gemm/o_voxel) to THIS GPU's arch so
    # binaries match the hardware (L40S=8.9, A10G=8.6) rather than guessing.
    os.environ["TORCH_CUDA_ARCH_LIST"] = _torch_arch_list()
    # 2. S3 cached wheel
    if bucket:
        try:
            listing = s3.list_objects_v2(Bucket=bucket, Prefix=_trellis2_wheel_prefix())
            for o in listing.get("Contents", []):
                k = o["Key"]
                if k.endswith(".whl") and os.path.basename(k).startswith(s3_glob):
                    wp = os.path.join("/tmp", os.path.basename(k))
                    s3.download_file(bucket, k, wp)
                    subprocess.check_call(["pip", "install", "--quiet", "--no-deps",
                                           "--force-reinstall", wp], timeout=180)
                    if verify_import:
                        importlib.import_module(pkg_name)
                    logger.info("%s installed from S3 cache (%s)", pkg_name, os.path.basename(k))
                    return True
        except Exception as e:
            logger.info("%s S3 cache miss/failed (%s) — building from source", pkg_name, e)
    # 3. build from source + cache the wheel
    logger.info("Building %s from source (nvcc, may take minutes)...", pkg_name)
    subprocess.check_call(["pip", "install", "--quiet", "setuptools", "wheel", "ninja", "pybind11"], timeout=180)
    subprocess.check_call(["pip", "install", "--no-build-isolation", "--no-deps", build_spec],
                          timeout=1800, env={**os.environ})
    if verify_import:
        importlib.import_module(pkg_name)
    logger.info("%s built + installed", pkg_name)
    if bucket:
        try:
            wdir = f"/tmp/{pkg_name}_wheel_export"
            os.makedirs(wdir, exist_ok=True)
            subprocess.check_call(["pip", "wheel", "--no-build-isolation", "--no-deps",
                                   "--wheel-dir", wdir, build_spec], timeout=1800, env={**os.environ})
            found = _glob.glob(os.path.join(wdir, f"{s3_glob}*.whl"))
            if found:
                wkey = _trellis2_wheel_prefix() + os.path.basename(found[0])
                s3.upload_file(found[0], bucket, wkey)
                logger.info("Cached %s wheel to S3: %s", pkg_name, wkey)
        except Exception as ce:
            logger.warning("Failed to cache %s wheel: %s", pkg_name, ce)
    return True


def _ensure_trellis2(blocking: bool = True) -> bool:
    """Make the TRELLIS.2 texturing stack importable. Returns True if ready.

    Clones the MIT repo (for the `trellis2` package + the in-repo o-voxel source)
    onto sys.path, then ensures the 4 CUDA extensions: nvdiffrast (shared
    helper), o_voxel (in-repo), cumesh + flex_gemm (external git). Each ext's
    wheel is S3-cached so cold starts after the first are fast. MUST run at LOAD
    time (builds exceed MMS's 120s response watchdog); blocking=False is the
    inference-time guard that bails so the caller can defer.
    """
    import sys as _sys
    # Fast path: package + all ext already importable.
    try:
        if os.path.join(_TRELLIS2_RUN_DIR) not in _sys.path:
            _sys.path.insert(0, _TRELLIS2_RUN_DIR)
        import trellis2  # noqa: F401
        import o_voxel, cumesh, flex_gemm  # noqa: F401
        import nvdiffrast  # noqa: F401
        return True
    except Exception:
        pass
    if not blocking:
        return False
    import subprocess
    # 1. Clone the repo (package source + o-voxel). Shallow, no LFS weights.
    if not os.path.isdir(os.path.join(_TRELLIS2_RUN_DIR, "trellis2")):
        os.makedirs(os.path.dirname(_TRELLIS2_RUN_DIR), exist_ok=True)
        env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"}
        subprocess.check_call(["git", "clone", "--depth", "1", "--branch", _TRELLIS2_REPO_REF,
                               "--recursive", _TRELLIS2_REPO, _TRELLIS2_RUN_DIR],
                              timeout=600, env=env)
        logger.info("Cloned TRELLIS.2 repo to %s", _TRELLIS2_RUN_DIR)
    if _TRELLIS2_RUN_DIR not in _sys.path:
        _sys.path.insert(0, _TRELLIS2_RUN_DIR)
    # The fast-path above probed `import trellis2` while _TRELLIS2_RUN_DIR did NOT
    # yet exist on disk — Python's FileFinder NEGATIVELY caches a missing path and
    # (unlike a present dir, which refreshes on mtime) does NOT auto-invalidate it.
    # Without this, the final `import trellis2` still misses even though the clone
    # just populated the dir. The CUDA exts import fine (they land in site-packages,
    # which is mtime-refreshed) — only the sys.path package source needs this.
    import importlib as _il
    _il.invalidate_caches()
    # 2. TRELLIS.2-specific Python deps (NOT in the shared container reqs — we
    # install them only on the trellis2 endpoint so the Hunyuan/MVPainter/MV-
    # Adapter endpoints keep their pinned transformers). Two hard requirements:
    #   • transformers>=4.56 — DINOv3ViTModel (the image encoder) is imported at
    #     module load; the shared container caps transformers<4.52, which lacks it.
    #   • xformers — the SLAT *sparse* attention has NO sdpa fallback (only
    #     xformers/flash_attn). xformers has prebuilt cu124 wheels → no compile.
    # spconv/torchsparse are deliberately omitted: SPARSE_CONV_BACKEND=flex_gemm.
    # CRITICAL ordering/pinning: an UNPINNED xformers pulls its latest build,
    # which depends on a newer torch and SILENTLY upgrades the container's
    # torch 2.6.0+cu124 → 2.12 — which then breaks EVERY CUDA-ext compile
    # (nvdiffrast/o_voxel/cumesh/flex_gemm fail their torch/CUDA setup check with
    # a mismatched ABI). xformers 0.0.29.post3 is the build matched to torch
    # 2.6.0+cu124; --no-deps keeps it from touching torch (its only runtime dep,
    # already present). Install it separately, FIRST.
    subprocess.check_call(["pip", "install", "--quiet", "--no-deps", "xformers==0.0.29.post3"],
                          timeout=600, env={**os.environ})
    _py_deps = [
        "plyfile", "easydict", "pandas", "lpips", "kornia", "timm", "zstandard",
        "git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8",
    ]
    logger.info("Installing TRELLIS.2 Python deps (utils3d, plyfile, lpips, ...)")
    # Pin torch/torchvision in the SAME resolve so no transitive dep can upgrade
    # them (pip treats 2.6.0+cu124 as satisfying ==2.6.0). If a dep genuinely
    # needs a newer torch, this surfaces a LOUD conflict instead of a silent,
    # build-breaking upgrade.
    subprocess.check_call(["pip", "install", "--quiet",
                           "torch==2.6.0", "torchvision==0.21.0", *_py_deps],
                          timeout=1200, env={**os.environ})
    # transformers MUST be >=4.56 for DINOv3ViTModel (the TRELLIS.2 image encoder,
    # imported at module load). The SageMaker HuggingFace DLC ships a pip CONSTRAINT
    # file (PIP_CONSTRAINT=/etc/.../constraint.txt) pinning transformers/diffusers/
    # accelerate to the image's tested versions. pip silently honors an inherited
    # `-c constraint` on EVERY install — even `--no-deps --upgrade` — which is why a
    # prior attempt left transformers at 4.51.3 (DINOv3ViTModel absent → untextured
    # fallback) while torch/xformers/the CUDA exts (NOT in the constraint file)
    # upgraded fine. Neutralize the constraint for THIS install by clearing
    # PIP_CONSTRAINT in the subprocess env. --no-deps keeps transformers' runtime
    # deps (numpy/pyyaml/regex/safetensors/huggingface-hub/tqdm — already present)
    # untouched; non-quiet so the resolved version is visible in the build log.
    # Version CEILING matters: DINOv3 landed in transformers 4.56.0 with
    # `DINOv3ViTModel` as a TOP-LEVEL class. transformers 5.x restructured the
    # package and that top-level import path no longer resolves (an unpinned
    # >=4.56 grabbed 5.12.1 → the same DINOv3ViTModel ImportError). Pin to the
    # 4.56–4.57 line; tokenizers<0.23 to match (5.x pulls 0.23).
    _env_nocon = {**os.environ}
    _env_nocon.pop("PIP_CONSTRAINT", None)
    subprocess.check_call(["pip", "install", "--no-cache-dir", "--no-deps", "--upgrade",
                           "transformers>=4.56,<4.58", "tokenizers>=0.22,<0.23"],
                          timeout=600, env=_env_nocon)
    # CRITICAL: the handler process ALREADY imported transformers 4.51.3 during
    # TripoSG load (model_fn), so sys.modules['transformers'] is the stale 4.51.3
    # module — the pip upgrade above only changed DISK. A later
    # `from transformers import DINOv3ViTModel` would hit the cached 4.51.3 module
    # (no DINOv3ViTModel → ImportError → untextured fallback), even though 4.57.6
    # is now installed. Purge every transformers* entry from sys.modules so the
    # next import reloads 4.57.6 from disk. Safe: TripoSG already built its
    # objects (they keep their class refs alive); the TRELLIS.2 texturer is a
    # separate pipeline that imports transformers fresh at texture time.
    for _mod in [m for m in _sys.modules if m == "transformers" or m.startswith("transformers.")]:
        del _sys.modules[_mod]
    import importlib as _il_tfm
    _il_tfm.invalidate_caches()
    # 3. nvdiffrast (shared) + the 3 TRELLIS.2-specific CUDA extensions.
    # BUILD ORDER MATTERS: o_voxel/postprocess.py imports flex_gemm, cumesh AND
    # nvdiffrast at module load, so o_voxel must be built LAST. We also can't
    # eagerly import each package right after its own build (verify_import=False)
    # — a package's wheel can build fine yet not import until its siblings exist
    # (o_voxel can't import without flex_gemm). Build all in dependency order, then
    # verify the whole stack imports once at the end.
    _ensure_nvdiffrast(blocking=True)
    # cumesh + flex_gemm: clone --recursive to a local dir (NOT `git+`, which skips
    # submodules → broken simplify → shredded mesh), then build from that dir.
    def _recursive_clone(name, url):
        dest = os.path.join("/tmp", f"trellis2_ext_{name}")
        if not os.path.isdir(os.path.join(dest, ".git")):
            import shutil as _sh
            if os.path.isdir(dest):
                _sh.rmtree(dest, ignore_errors=True)
            subprocess.check_call(["git", "clone", "--recursive", "--depth", "1", url, dest], timeout=600)
            logger.info("Cloned %s --recursive to %s", name, dest)
        return dest
    _flex_dir = _recursive_clone("flex_gemm", _TRELLIS2_EXT_GIT["flex_gemm"])
    _cumesh_dir = _recursive_clone("cumesh", _TRELLIS2_EXT_GIT["cumesh"])
    _pip_install_build_cached("flex_gemm", _flex_dir, "flex_gemm", verify_import=False)
    _pip_install_build_cached("cumesh", _cumesh_dir, "cumesh", verify_import=False)
    _pip_install_build_cached("o_voxel", os.path.join(_TRELLIS2_RUN_DIR, "o-voxel"), "o_voxel", verify_import=False)
    # Verify the full stack now that every extension is present.
    import importlib
    for _m in ("flex_gemm", "cumesh", "o_voxel", "nvdiffrast", "trellis2"):
        importlib.import_module(_m)
    # DINOv3ViTModel (the image encoder) is the canary for the transformers>=4.56
    # upgrade. Verify it imports HERE, at load — if it's missing, fail loudly so the
    # build is marked not-ready, rather than discovering it at inference time and
    # silently shipping an untextured mesh (the 4.51.3-revert bug).
    from transformers import DINOv3ViTModel  # noqa: F401
    import transformers as _tfm
    logger.info("TRELLIS.2 stack ready (package + o_voxel + cumesh + flex_gemm + nvdiffrast; transformers=%s)",
                getattr(_tfm, "__version__", "?"))
    return True


def _ensure_trellis2_background():
    """Kick TRELLIS.2 build on a daemon thread (idempotent), like nvdiffrast."""
    import threading
    global _trellis2_ops_bg_lock
    if _trellis2_ops_bg_lock is None:
        _trellis2_ops_bg_lock = threading.Lock()
    with _trellis2_ops_bg_lock:
        if _trellis2_ops_bg["state"] in (0, 1):
            return
        _trellis2_ops_bg["state"] = 0
    def _work():
        try:
            _ensure_trellis2(blocking=True)
            _trellis2_ops_bg["state"] = 1
            logger.info("Background TRELLIS.2 build complete — texturing available")
        except Exception as e:
            _trellis2_ops_bg["state"] = 2
            _trellis2_ops_bg["error"] = str(e)
            logger.error("Background TRELLIS.2 build failed: %s", e)
    threading.Thread(target=_work, daemon=True, name="trellis2-build").start()


def _rasterizer_choice():
    """Which texture-bake rasterizer to use: 'kaolin' (Apache-2.0, default,
    commercial-safe) or 'nvdiffrast' (NVIDIA non-commercial, retained fallback).
    Mirrors make_raster_context()'s ARTSMOKER_RASTERIZER flag."""
    return (_get_env("ARTSMOKER_RASTERIZER", "kaolin") or "kaolin").lower().strip()


def _ensure_kaolin(blocking: bool = True) -> bool:
    """Make kaolin importable (Apache-2.0 rasterizer for the texture bake).

    Kaolin ships PREBUILT wheels keyed by torch+CUDA (no source compile), so this
    is lighter than _ensure_nvdiffrast — just pip-install the matching wheel from
    NVIDIA's wheel index, derived at runtime from the installed torch/CUDA (never
    hard-coded). Like nvdiffrast it runs at LOAD time (no inference watchdog).
    """
    try:
        import kaolin  # noqa: F401
        return True
    except Exception:
        pass
    if not blocking:
        return False
    import subprocess, sys as _sys
    try:
        import torch
        tv = torch.__version__.split("+")[0]              # e.g. 2.6.0
        cu = (torch.version.cuda or "").replace(".", "")  # e.g. 124
        index = f"https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-{tv}_cu{cu}.html" if cu else None
    except Exception:
        index = None
    cmd = [_sys.executable, "-m", "pip", "install", "kaolin"]
    if index:
        cmd += ["-f", index]
    logger.info("Installing kaolin (Apache-2.0 rasterizer): %s", " ".join(cmd[2:]))
    try:
        subprocess.check_call(cmd)
        import kaolin  # noqa: F401
        logger.info("kaolin installed (index=%s)", index or "pip-default")
        return True
    except Exception as e:
        logger.error("kaolin install failed: %s", e)
        raise ImportError(f"kaolin unavailable — Apache-2.0 rasterizer needs it: {e}")


def _ensure_rasterizer(blocking: bool = True) -> bool:
    """Ensure the SELECTED bake rasterizer is importable. Default kaolin
    (commercial-safe); nvdiffrast when ARTSMOKER_RASTERIZER=nvdiffrast. Single
    gate the texture path calls so we install the right one at load time."""
    if _rasterizer_choice() == "nvdiffrast":
        return _ensure_nvdiffrast(blocking=blocking)
    return _ensure_kaolin(blocking=blocking)


def _ensure_nvdiffrast_background():
    """Kick off nvdiffrast compile on a daemon thread (idempotent).

    Used by the inference-time guard so the worker isn't blocked past MMS's
    120s response watchdog. Updates _nvdiffrast_bg so predict_fn can report
    'preparing, retry shortly' instead of crashing the worker.
    """
    import threading
    global _nvdiffrast_bg_lock
    if _nvdiffrast_bg_lock is None:
        _nvdiffrast_bg_lock = threading.Lock()
    with _nvdiffrast_bg_lock:
        if _nvdiffrast_bg["state"] in (0, 1):
            return  # already compiling or done
        _nvdiffrast_bg["state"] = 0

    def _work():
        try:
            _ensure_nvdiffrast(blocking=True)
            _nvdiffrast_bg["state"] = 1
            logger.info("Background nvdiffrast compile complete — texture phases now available")
        except Exception as e:
            _nvdiffrast_bg["state"] = 2
            _nvdiffrast_bg["error"] = str(e)
            logger.error("Background nvdiffrast compile failed: %s", e)

    t = threading.Thread(target=_work, daemon=True, name="nvdiffrast-compile")
    t.start()


_HUNYUAN_RUN_DIR = "/tmp/hy3dpaint_run"  # writable copy of the vendored package


def _hunyuan_writable_dir(code_dir):
    """Return a WRITABLE copy of the vendored hy3dpaint package.

    The bundled source lives under /opt/ml/model/code/ which SageMaker mounts
    READ-ONLY. We need to write into the tree (the custom_rasterizer build dir,
    and the compiled mesh_inpaint_processor .so which must sit next to
    MeshRender.py for its relative import). So copy hy3dpaint to /tmp once and
    use that everywhere (build + import). Idempotent: copies only if absent.
    """
    import shutil as _sh
    dst = os.path.join(_HUNYUAN_RUN_DIR, "hy3dpaint")
    src = os.path.join(code_dir, "hy3dpaint")
    if not os.path.isdir(dst):
        try:
            os.makedirs(_HUNYUAN_RUN_DIR, exist_ok=True)
            _sh.copytree(src, dst)
            logger.info("Copied hy3dpaint to writable %s", dst)
        except Exception as e:
            logger.warning("Could not copy hy3dpaint to /tmp (%s) — using read-only src", e)
            return src
    return dst


def _hunyuan_inpaint_so_dir(code_dir):
    """Directory where mesh_inpaint_processor.*.so must live for the relative
    import `from .mesh_inpaint_processor import meshVerticeInpaint` in
    hy3dpaint/DifferentiableRenderer/MeshRender.py to resolve. Uses the WRITABLE
    /tmp copy (the read-only model dir can't be written to)."""
    return os.path.join(_hunyuan_writable_dir(code_dir), "DifferentiableRenderer")


def _ensure_hunyuan_ops(code_dir, blocking: bool = True) -> bool:
    """Make the two Hunyuan3D-Paint native ops importable. Returns True if ready.

    Two builds (mirrors the proven _ensure_nvdiffrast pattern — import → S3
    cache → build-from-source → cache-to-S3):
      1. custom_rasterizer — a CUDA extension (module `custom_rasterizer_kernel`,
         package `custom_rasterizer`). Imported as `import custom_rasterizer` by
         MeshRender (raster_mode="cr"). Built via `pip install` of the vendored
         hy3dpaint/custom_rasterizer/ (CUDAExtension). Cached as a wheel to S3.
      2. mesh_inpaint_processor — a CPU pybind11 .so built by c++ from
         hy3dpaint/DifferentiableRenderer/mesh_inpaint_processor.cpp. Must be
         placed INSIDE that dir (relative import `.mesh_inpaint_processor`).
         Cached as a raw .so to S3 (keyed by python tag for ABI safety).

    CRITICAL: the CUDA build exceeds MMS's 120s response watchdog, so this runs
    at LOAD time (model_fn). blocking=False returns immediately when a build is
    still needed (the inference-time guard) so predict_fn never trips the watchdog.
    """
    import subprocess
    import glob as _glob

    rasterizer_ok = False
    inpaint_so_dir = _hunyuan_inpaint_so_dir(code_dir)

    # ---- 0. Already importable? ----
    try:
        import custom_rasterizer  # noqa: F401
        rasterizer_ok = True
    except Exception:
        rasterizer_ok = False
    inpaint_ok = bool(_glob.glob(os.path.join(inpaint_so_dir, "mesh_inpaint_processor*.so")))
    if rasterizer_ok and inpaint_ok:
        return True

    if not blocking:
        return False  # don't block under the response watchdog

    import boto3 as _boto3
    s3 = _boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
    bucket = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET") or ""

    # Ensure CUDA_HOME for the CUDA build (same autodetect as nvdiffrast).
    if not os.environ.get("CUDA_HOME"):
        for p in ["/usr/local/cuda", "/opt/conda", "/usr/local/cuda-12.4", "/usr/local/cuda-12"]:
            if os.path.isfile(os.path.join(p, "bin", "nvcc")):
                os.environ["CUDA_HOME"] = p
                logger.info("Set CUDA_HOME=%s", p)
                break
    # Pin the build to THIS GPU's arch (L40S=8.9, A10G=8.6, …) so the compile
    # doesn't probe/guess and the artifact matches the hardware it runs on.
    os.environ["TORCH_CUDA_ARCH_LIST"] = _torch_arch_list()

    # Build from the WRITABLE /tmp copy of hy3dpaint (the read-only model dir
    # can't host setup.py's build/ dir → "Read-only file system" error).
    _writable = _hunyuan_writable_dir(code_dir)
    rasterizer_src = os.path.join(_writable, "custom_rasterizer")

    # ---- 1. custom_rasterizer ----
    if not rasterizer_ok:
        # 1a. S3 cached wheel.
        if bucket:
            try:
                listing = s3.list_objects_v2(Bucket=bucket, Prefix=_hunyuan_rasterizer_wheel_prefix())
                wheels = [o["Key"] for o in listing.get("Contents", []) if o["Key"].endswith(".whl")]
                if wheels:
                    wkey = wheels[0]
                    wpath = os.path.join("/tmp", os.path.basename(wkey))
                    s3.download_file(bucket, wkey, wpath)
                    subprocess.check_call(["pip", "install", "--quiet", "--no-deps",
                                           "--force-reinstall", wpath], timeout=180)
                    import custom_rasterizer  # noqa: F401
                    rasterizer_ok = True
                    logger.info("custom_rasterizer installed from S3 cache (%s)", os.path.basename(wkey))
            except Exception as e:
                logger.info("custom_rasterizer S3 cache miss/failed (%s) — building from source", e)
        # 1b. Build from the vendored source, then cache the wheel.
        if not rasterizer_ok:
            logger.info("Building custom_rasterizer CUDA extension from source (~2-5 min)...")
            try:
                subprocess.check_call(["pip", "install", "--quiet", "setuptools", "wheel", "ninja", "pybind11"], timeout=180)
                wheel_dir = "/tmp/custom_rasterizer_wheel"
                os.makedirs(wheel_dir, exist_ok=True)
                subprocess.check_call(
                    ["pip", "wheel", "--no-build-isolation", "--no-deps",
                     "--wheel-dir", wheel_dir, rasterizer_src],
                    timeout=900, env={**os.environ},
                )
                built = _glob.glob(os.path.join(wheel_dir, "custom_rasterizer*.whl"))
                if not built:
                    raise RuntimeError("custom_rasterizer wheel not produced")
                subprocess.check_call(["pip", "install", "--quiet", "--no-deps",
                                       "--force-reinstall", built[0]], timeout=180)
                import custom_rasterizer  # noqa: F401
                rasterizer_ok = True
                logger.info("custom_rasterizer built + installed (%s)", os.path.basename(built[0]))
                if bucket:
                    try:
                        s3.upload_file(built[0], bucket,
                                       _hunyuan_rasterizer_wheel_prefix() + os.path.basename(built[0]))
                        logger.info("Cached custom_rasterizer wheel to S3")
                    except Exception as ce:
                        logger.warning("Failed to cache custom_rasterizer wheel: %s", ce)
            except Exception as e:
                logger.error("custom_rasterizer build failed: %s", e)
                raise ImportError(f"custom_rasterizer unavailable — Hunyuan paint needs it: {e}")

    # ---- 2. mesh_inpaint_processor (.so placed inside DifferentiableRenderer/) ----
    if not inpaint_ok:
        import sysconfig
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
        so_name = "mesh_inpaint_processor" + ext_suffix
        so_dst = os.path.join(inpaint_so_dir, so_name)
        # 2a. S3 cache (keyed by ext suffix for ABI match).
        cached = False
        if bucket:
            try:
                skey = _HUNYUAN_INPAINT_SO_PREFIX + so_name
                s3.download_file(bucket, skey, so_dst)
                cached = True
                logger.info("mesh_inpaint_processor .so loaded from S3 cache")
            except Exception:
                cached = False
        # 2b. Compile from source.
        if not cached:
            logger.info("Compiling mesh_inpaint_processor (pybind11 .so)...")
            try:
                subprocess.check_call(["pip", "install", "--quiet", "pybind11"], timeout=120)
                import pybind11
                includes = subprocess.check_output(["python", "-m", "pybind11", "--includes"]).decode().split()
                cpp_src = os.path.join(inpaint_so_dir, "mesh_inpaint_processor.cpp")
                cmd = ["c++", "-O3", "-Wall", "-shared", "-std=c++11", "-fPIC",
                       *includes, cpp_src, "-o", so_dst]
                subprocess.check_call(cmd, timeout=300, env={**os.environ})
                logger.info("mesh_inpaint_processor compiled -> %s", so_name)
                if bucket:
                    try:
                        s3.upload_file(so_dst, bucket, _HUNYUAN_INPAINT_SO_PREFIX + so_name)
                        logger.info("Cached mesh_inpaint_processor .so to S3")
                    except Exception as ce:
                        logger.warning("Failed to cache mesh_inpaint_processor .so: %s", ce)
            except Exception as e:
                # Non-fatal: MeshRender wraps this import in try/except. Texture
                # still bakes; only the vertex-inpaint refinement is skipped.
                logger.warning("mesh_inpaint_processor compile failed (inpaint refinement disabled): %s", e)

    return rasterizer_ok


def _ensure_hunyuan_ops_background(code_dir):
    """Kick off the Hunyuan native-ops build on a daemon thread (idempotent),
    so the worker isn't blocked past MMS's 120s response watchdog."""
    import threading
    global _hunyuan_ops_bg_lock
    if _hunyuan_ops_bg_lock is None:
        _hunyuan_ops_bg_lock = threading.Lock()
    with _hunyuan_ops_bg_lock:
        if _hunyuan_ops_bg["state"] in (0, 1):
            return
        _hunyuan_ops_bg["state"] = 0

    def _work():
        try:
            _ensure_hunyuan_ops(code_dir, blocking=True)
            _hunyuan_ops_bg["state"] = 1
            logger.info("Background Hunyuan ops build complete — paint backend now available")
        except Exception as e:
            _hunyuan_ops_bg["state"] = 2
            _hunyuan_ops_bg["error"] = str(e)
            logger.error("Background Hunyuan ops build failed: %s", e)

    t = threading.Thread(target=_work, daemon=True, name="hunyuan-ops-build")
    t.start()


# Texture backend selector. "mvadapter" (default, original) or "hunyuan"
# (Hunyuan3D-Paint). Per-request override via input_data["texture_backend"];
# server default via ARTSMOKER_TEXTURE_BACKEND. Both backends are retained.
def _texture_backend(input_data=None):
    if input_data and input_data.get("texture_backend"):
        return str(input_data["texture_backend"]).lower().strip()
    return (_get_env("ARTSMOKER_TEXTURE_BACKEND", "mvadapter") or "mvadapter").lower().strip()


def _load_hunyuan_paint(code_dir, hf_token):
    """Load the Hunyuan3D-Paint pipeline (second texturing backend).

    Returns a Hunyuan3DPaintPipeline. Weights (tencent/Hunyuan3D-2.1 paint
    subfolder + facebook/dinov2-giant) are pulled from HF at construction
    (needs HF auth for the Tencent-licensed repo). Native ops (custom_rasterizer
    + mesh_inpaint_processor) must already be built — call _ensure_hunyuan_ops
    at load time first.
    """
    import sys as _sys
    import time as _time

    # The vendored package's internal imports are top-level (e.g.
    # `from DifferentiableRenderer.MeshRender import MeshRender`,
    # `from utils...`, `from textureGenPipeline import ...`), so hy3dpaint/
    # ITSELF must be on sys.path (not just code/). Use the WRITABLE /tmp copy so
    # the compiled mesh_inpaint_processor .so (written next to MeshRender.py) is
    # importable via its relative import, and the cfg/ paths resolve there too.
    hy_dir = _hunyuan_writable_dir(code_dir)
    if hy_dir not in _sys.path:
        _sys.path.insert(0, hy_dir)
    # Ensure HF auth for the gated Tencent repo.
    if hf_token:
        os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", hf_token)
        os.environ.setdefault("HF_TOKEN", hf_token)

    # Compatibility shim: basicsr (via realesrgan/imageSuperNet) imports
    # torchvision.transforms.functional_tensor, removed in torchvision 0.17+.
    # Apply BEFORE constructing the pipeline (which loads imageSuperNet).
    try:
        from utils.torchvision_shim import apply as _apply_tv_shim
        _apply_tv_shim()
    except Exception as _shim_e:
        logger.warning("torchvision shim not applied (%s) — realesrgan import may fail", _shim_e)

    from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig

    # max_num_view=6 keeps VRAM/time bounded; resolution 512 is the per-view gen
    # size (the pipeline upscales + bakes to texture_size=4096 internally).
    conf = Hunyuan3DPaintConfig(max_num_view=6, resolution=512)
    # The vendored config hardcodes RELATIVE paths assuming CWD=repo root. On the
    # container the code is under code/hy3dpaint/, so rewrite to ABSOLUTE paths
    # (no os.chdir — that would race in a shared worker).
    conf.multiview_cfg_path = os.path.join(hy_dir, "cfgs", "hunyuan-paint-pbr.yaml")
    conf.realesrgan_ckpt_path = _hunyuan_realesrgan_path()
    conf.multiview_pretrained_path = "tencent/Hunyuan3D-2.1"
    conf.dino_ckpt_path = "facebook/dinov2-giant"

    t0 = _time.time()
    logger.info("Loading Hunyuan3D-Paint pipeline (paint backend)...")
    paint_pipe = Hunyuan3DPaintPipeline(conf)
    logger.info("Hunyuan3D-Paint loaded in %.0fs", _time.time() - t0)
    return paint_pipe


def _hunyuan_realesrgan_path():
    """Ensure RealESRGAN_x4plus.pth (Hunyuan's super-res ckpt — x4, distinct from
    MV-Adapter's x2) is on disk, S3-cache-first. Returns the local path."""
    import boto3 as _boto3
    import urllib.request as _urlreq
    _s3 = _boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
    _bucket = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET") or ""
    local = "/tmp/RealESRGAN_x4plus.pth"
    s3key = f"{_TEXTURE_DEPS_PREFIX}/RealESRGAN_x4plus.pth"
    url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
    if not os.path.exists(local):
        if _bucket:
            try:
                _s3.download_file(_bucket, s3key, local)
                logger.info("RealESRGAN x4 loaded from S3 cache")
                return local
            except Exception:
                pass
        try:
            logger.info("Downloading RealESRGAN x4 from GitHub...")
            _urlreq.urlretrieve(url, local)
            if _bucket:
                try:
                    _s3.upload_file(local, _bucket, s3key)
                    logger.info("Cached RealESRGAN x4 to S3")
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Failed to download RealESRGAN x4: %s", e)
    return local


def _ensure_texture_quality_models():
    """Download the bake quality models (RealESRGAN x2 upscaler + LaMa inpainter),
    S3-cached. Returns (upscaler_path_or_None, inpaint_path_or_None).

    Reusable by both the MV-Adapter load path and the MVPainter bake — the latter
    previously built a bare TexturePipeline with NO upscaler/inpainter, which is
    why MVPainter textures came out soft (512² views projected to 4096² with no
    super-res) and fragmented (no inpaint refine). Idempotent: skips files already
    on local disk.
    """
    import urllib.request as _urlreq
    import boto3 as _boto3
    _s3 = _boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
    _bucket = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET") or ""
    _upscaler_path = "/tmp/RealESRGAN_x2plus.pth"
    _inpaint_path = "/tmp/big-lama.pt"
    specs = [
        (_upscaler_path, f"{_TEXTURE_DEPS_PREFIX}/RealESRGAN_x2plus.pth",
         "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth", "RealESRGAN x2"),
        (_inpaint_path, f"{_TEXTURE_DEPS_PREFIX}/big-lama.pt",
         "https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt", "LaMa inpainter"),
    ]
    for _local, _s3k, _url, _name in specs:
        if os.path.exists(_local):
            continue
        if _bucket:
            try:
                _s3.download_file(_bucket, _s3k, _local)
                logger.info("%s loaded from S3 cache", _name)
                continue
            except Exception:
                pass
        try:
            logger.info("Downloading %s from GitHub...", _name)
            _urlreq.urlretrieve(_url, _local)
            logger.info("%s downloaded (%.1f MB)", _name, os.path.getsize(_local) / (1024 * 1024))
            if _bucket:
                try:
                    _s3.upload_file(_local, _bucket, _s3k)
                    logger.info("Cached %s to S3", _name)
                except Exception:
                    pass
        except Exception as _e:
            logger.warning("Failed to fetch %s: %s", _name, _e)
    return (_upscaler_path if os.path.exists(_upscaler_path) else None,
            _inpaint_path if os.path.exists(_inpaint_path) else None)


def _load_texture_models(code_dir, hf_token):
    """Load MV-Adapter (multi-view generation) and TexturePipeline models.

    Called either at startup (high VRAM) or on-demand during prediction (low VRAM).
    Returns (mv_pipe, texture_pipe) tuple.
    Raises ImportError if critical dependencies (nvdiffrast) are unavailable.
    """
    import time as _time
    import subprocess

    # Ensure the bake rasterizer is importable (kaolin by default; nvdiffrast via
    # ARTSMOKER_RASTERIZER). Prepared at LOAD time in model_fn so this is normally
    # a no-op here.
    _ensure_rasterizer()

    # Load SDXL + MV-Adapter for multi-view generation
    t0 = _time.time()
    logger.info("Loading MV-Adapter (SDXL + adapter weights)...")
    from diffusers import AutoencoderKL
    from mvadapter.pipelines.pipeline_mvadapter_i2mv_sdxl import MVAdapterI2MVSDXLPipeline

    # Use the standard SDXL VAE in fp32 for the decode to avoid fp16 color drift.
    # The fp16-fix VAE only guarantees no-NaN, not color fidelity — and color
    # bias compounds when 6 views are blended into one texture atlas.
    _vae = AutoencoderKL.from_pretrained(
        "madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16
    )
    mv_pipe = MVAdapterI2MVSDXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        vae=_vae,
        torch_dtype=torch.float16,
    )
    mv_pipe.init_custom_adapter(num_views=6)
    mv_pipe.load_custom_adapter(
        "huanngzh/mv-adapter",
        weight_name="mvadapter_i2mv_sdxl.safetensors",
    )
    mv_pipe.to(device="cuda", dtype=torch.float16)
    # cond_encoder is not a registered pipeline component — cast explicitly
    mv_pipe.cond_encoder.to(device="cuda", dtype=torch.float16)
    # Force fp32 VAE decode for accurate colors (latents upcast around decode)
    mv_pipe.vae.to(torch.float32)
    mv_pipe.vae.config.force_upcast = True
    # VAE slicing + tiling: decode the 6-view batch in chunks/tiles instead of
    # all at once. The fp32 6-view decode is a major contributor to the Phase 2
    # VRAM peak (~43.6 GB observed); slicing/tiling cuts that peak substantially
    # with NO quality loss (same output, just chunked). Lets the 1M-face render
    # fit on the L40S without lowering face count.
    try:
        mv_pipe.enable_vae_slicing()
        mv_pipe.enable_vae_tiling()
        logger.info("MV-Adapter VAE slicing + tiling enabled (lower Phase 2 peak)")
    except Exception as _vae_e:
        logger.warning("Could not enable VAE slicing/tiling: %s", _vae_e)
    mv_time = _time.time() - t0
    logger.info("MV-Adapter loaded in %.0fs (fp32 VAE decode)", mv_time)

    # Download quality models (RealESRGAN upscaler + LaMa inpainter).
    # S3 client + bucket: re-established here (they previously lived in the
    # inline nvdiffrast block that was extracted into _ensure_nvdiffrast()).
    import boto3 as _boto3
    _s3 = _boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
    _bucket = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET") or ""

    _upscaler_url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"
    _inpaint_url = "https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt"
    _upscaler_s3_key = f"{_TEXTURE_DEPS_PREFIX}/RealESRGAN_x2plus.pth"
    _inpaint_s3_key = f"{_TEXTURE_DEPS_PREFIX}/big-lama.pt"
    _upscaler_path = "/tmp/RealESRGAN_x2plus.pth"
    _inpaint_path = "/tmp/big-lama.pt"

    import urllib.request as _urlreq

    for _local, _s3k, _url, _name in [
        (_upscaler_path, _upscaler_s3_key, _upscaler_url, "RealESRGAN x2"),
        (_inpaint_path, _inpaint_s3_key, _inpaint_url, "LaMa inpainter"),
    ]:
        if not os.path.exists(_local):
            # Try S3 cache first
            if _bucket:
                try:
                    _s3.download_file(_bucket, _s3k, _local)
                    logger.info("%s loaded from S3 cache", _name)
                    continue
                except Exception:
                    pass
            # Download from GitHub
            logger.info("Downloading %s from GitHub...", _name)
            try:
                _urlreq.urlretrieve(_url, _local)
                logger.info("%s downloaded (%.1f MB)", _name, os.path.getsize(_local) / (1024*1024))
                # Cache to S3
                if _bucket:
                    try:
                        _s3.upload_file(_local, _bucket, _s3k)
                        logger.info("Cached %s to S3", _name)
                    except Exception:
                        pass
            except Exception as _dl_err:
                logger.warning("Failed to download %s: %s", _name, _dl_err)
                _local = None

    # Load TexturePipeline with upscaler + inpainter for maximum quality
    t0 = _time.time()
    logger.info("Loading TexturePipeline (with RealESRGAN upscaler + LaMa inpainter)...")
    from mvadapter.pipelines.pipeline_texture import TexturePipeline
    texture_pipe = TexturePipeline(
        upscaler_ckpt_path=_upscaler_path if os.path.exists(_upscaler_path) else None,
        inpaint_ckpt_path=_inpaint_path if os.path.exists(_inpaint_path) else None,
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
    "trellis2_image_to_3d": _load_trellis2_image_to_3d,  # full pipeline: builds CUDA stack + RMBG cutout at load; 8-ckpt pipe loads lazily in the predictor
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

    # Build kwargs from input_data — only pass fields the pipeline accepts.
    # true_cfg_scale is Qwen-Image's real CFG knob (guidance_scale is a no-op
    # placeholder there); include it so the generator's CFG isn't silently dropped.
    kwargs = {"generator": generator}
    for key in ("prompt", "width", "height", "num_inference_steps", "guidance_scale",
                "true_cfg_scale", "negative_prompt", "num_frames", "fps", "motion_bucket_id"):
        if key in input_data and input_data[key] is not None:
            kwargs[key] = input_data[key]

    # Append the model's "positive_magic" quality suffix if configured (e.g.
    # Qwen-Image's ", Ultra HD, 4K, cinematic composition." — the official
    # pipeline always appends it; omitting it noticeably degrades quality).
    positive_magic = _config.get("positive_magic", "")
    if positive_magic and kwargs.get("prompt"):
        kwargs["prompt"] = f"{kwargs['prompt'].rstrip()}{positive_magic}"

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


def _predict_image_edit(input_data, model_dict):
    """Reference-guided image edit (e.g. Qwen-Image-Edit / QwenImageEditPlusPipeline).

    Takes 1–3 reference images + an instruction prompt and produces a new image
    that preserves the referenced subject/product/character while applying the
    requested changes. Serves BOTH the Image Studio reference-guided tab and the
    basic Edit tab (a single reference image + mask-free instruction).
    """
    pipe = model_dict["pipe"]
    seed = input_data.get("seed")
    generator = torch.Generator("cuda").manual_seed(seed) if seed is not None else None

    # Reference images: accept a list ("reference_images"), or a single "image".
    refs = input_data.get("reference_images")
    if not refs:
        single = input_data.get("image")
        refs = [single] if single else []
    if not refs:
        raise ValueError("image_edit requires at least one reference image")
    images = [_decode_image(r).convert("RGB") for r in refs[:3]]
    logger.info("image_edit: %d reference image(s), sizes=%s, prompt=%d chars, seed=%s",
                len(images), [im.size for im in images],
                len(input_data.get("prompt") or ""), seed)
    # QwenImageEditPlusPipeline takes a list; single-image pipelines take one image.
    image_arg = images if len(images) > 1 else images[0]

    kwargs = {"image": image_arg, "generator": generator}
    if input_data.get("prompt"):
        kwargs["prompt"] = input_data["prompt"]
    # CFG for Qwen edit: true_cfg_scale>1 + a (non-empty) negative_prompt enables it.
    # Per the official Qwen-Image-Edit-2511 example, BOTH true_cfg_scale=4.0 AND
    # guidance_scale=1.0 are set — guidance_scale must be forwarded (not left to a
    # wrong pipeline default) or edit quality degrades.
    neg = input_data.get("negative_prompt")
    kwargs["negative_prompt"] = neg if neg else " "
    for key in ("num_inference_steps", "true_cfg_scale", "guidance_scale"):
        if input_data.get(key) is not None:
            kwargs[key] = input_data[key]

    total_steps = kwargs.get("num_inference_steps", 40)
    import time as _t
    _step_start = _t.time()

    def _log_progress(pipe, step, timestep, callback_kwargs):
        elapsed = _t.time() - _step_start
        if step == 0 or (step + 1) % 5 == 0 or step + 1 == total_steps:
            logger.info("Edit step %d/%d (%d%%) — %.1fs elapsed",
                        step + 1, total_steps, int((step + 1) / total_steps * 100), elapsed)
        return callback_kwargs

    try:
        kwargs["callback_on_step_end"] = _log_progress
        result = pipe(**kwargs)
    except TypeError:
        kwargs.pop("callback_on_step_end", None)
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


def _log_gpu_mem(label):
    """Log current CUDA allocated/reserved/free so phase transitions are visible."""
    if not torch.cuda.is_available():
        return
    try:
        alloc = torch.cuda.memory_allocated(0) / (1024 ** 3)
        reserved = torch.cuda.memory_reserved(0) / (1024 ** 3)
        free_b, total_b = torch.cuda.mem_get_info(0)
        free_gb = free_b / (1024 ** 3)
        total_gb = total_b / (1024 ** 3)
        logger.info("GPU mem [%s]: alloc=%.2f GB reserved=%.2f GB | driver-free=%.2f GB of %.1f GB",
                    label, alloc, reserved, free_gb, total_gb)
    except Exception:
        pass


def _reclaim_cuda_memory(tag=""):
    """Force the CUDA caching allocator to release cached-but-unused blocks.

    PyTorch's caching allocator keeps freed GPU blocks in a per-process pool
    (so driver-free stays low even after tensors are released). empty_cache()
    returns those cached blocks to the driver, making them available for the
    NEXT large allocation (e.g. SDXL's multi-view UNet forward). gc.collect()
    first drops any lingering Python references (autograd graphs, cycles) so the
    allocator actually sees the blocks as free. ipc_collect() reclaims any
    cross-process handles. Order matters: collect refs → empty cache.

    This is the crux of the high-VRAM OOM fix: Phase 1's dense octree SDF
    volume leaves ~25+ GB reserved; without this, Phase 2 only sees ~1 GB free.
    """
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        try:
            torch.cuda.ipc_collect()
        except Exception:
            pass
    if tag:
        _log_gpu_mem(tag)


def _move_module_to(module, device):
    """Move a pipeline or model (and known sub-modules) to a device, best-effort.

    Diffusers pipelines expose .to(device); plain nn.Modules too. Returns True
    if a move was attempted. Used to park TripoSG/RMBG on CPU between phases on
    the high-VRAM path (they aren't needed during MV-Adapter/TexturePipeline).
    """
    if module is None:
        return False
    try:
        module.to(device)
        return True
    except Exception as e:
        logger.warning("Could not move module to %s: %s", device, e)
        return False


def _evict_module_to_meta(module, submodule_attrs=None, label="module"):
    """GENERIC eviction: free a pipeline/model's storage with ZERO host-RAM copy.

    Moving to the `meta` device releases CUDA (and host) tensor storage
    IMMEDIATELY without allocating a host-RAM copy (meta tensors have no backing
    storage) — unlike .to("cpu"), which copies weights into host RAM and can
    OOM-kill the worker when RAM is the scarce resource (e.g. a CPU/host-RAM-
    bound bake like Open3D UVAtlas on a high-poly mesh).

    Model-agnostic — any backend (TripoSG, MVPainter, Hunyuan, future models)
    can call this to fit a baseline instance. The caller is responsible for
    dropping its Python refs and reloading from source/snapshot when next needed.
    `submodule_attrs` is the fallback list of sub-module names to evict
    individually if a whole-pipeline .to("meta") isn't supported. Returns True if
    an eviction was attempted. Best-effort: never raises.
    """
    if module is None:
        return False
    try:
        module.to("meta")
        return True
    except Exception:
        moved = False
        for _attr in (submodule_attrs or ("vae", "unet", "transformer", "text_encoder",
                                          "image_encoder", "vision_encoder", "vision_encoder_2")):
            _m = getattr(module, _attr, None)
            if _m is not None and hasattr(_m, "to"):
                try:
                    _m.to("meta"); moved = True
                except Exception:
                    pass
        if not moved:
            logger.warning("Could not evict %s to meta (no movable submodules)", label)
        return moved


def _host_ram_available_gb():
    """Return available host (system) RAM in GB, or None if it can't be read.

    Used to decide whether parking the fp32 TripoSG pipeline (~8-10 GB) from GPU
    into host RAM is safe. On g6e.xlarge (only 32 GiB RAM) the box is already
    ~20 GB full with all models loaded, so moving TripoSG to CPU pushed it over
    the limit → the Linux OOM-killer SIGKILL'd the worker the instant we parked
    (no Python traceback, abrupt worker disconnect). On g6e.2xlarge (64 GiB)
    there's ample headroom. This lets the handler pick park-vs-evict at runtime
    so the SAME code is safe on either instance.
    """
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        try:
            # Fallback: parse /proc/meminfo (MemAvailable in kB).
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) / (1024 ** 2)
        except Exception:
            pass
        return None


def _host_ram_total_gb():
    """Return total host RAM in GB, or None. Used to pick the MV-Adapter
    resolution tier: the multi-view fp32 VAE decode of 6 views is bounded by
    HOST RAM, not VRAM (1536² spiked a 32 GiB box to 99.9% → OOM). A bigger
    instance (g6e.2xlarge = 64 GiB, 4xlarge = 128 GiB) can run higher res."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / (1024 ** 2)
        except Exception:
            pass
        return None


def _log_mem(label):
    """GENERIC phase memory probe — logs BOTH host RAM (used/total) and GPU VRAM
    at a named checkpoint. Reusable by any backend to find the real peak that
    dictates the instance baseline. Host RAM is often the hidden ceiling (CPU
    unwrap / fp32 decode), so we surface used-of-total, not just free."""
    try:
        avail = _host_ram_available_gb()
        total = _host_ram_total_gb()
        used = (total - avail) if (avail is not None and total is not None) else None
        ram = ("RAM %.1f/%.1f GB used (%.1f free)" % (used, total, avail)) if used is not None else "RAM ?"
        gpu = ""
        import torch as _t
        if _t.cuda.is_available():
            gpu = " | VRAM %.1f GB alloc, %.1f reserved" % (
                _t.cuda.memory_allocated() / 1024**3, _t.cuda.memory_reserved() / 1024**3)
        logger.info("MEM [%s]: %s%s", label, ram, gpu)
    except Exception:
        pass


def _choose_mv_resolution():
    """Pick the MV-Adapter render+generation resolution.

    Subject-agnostic tradeoff (humans, animals, vehicles, props alike):
    MV-Adapter is SDXL-based and SDXL is trained at 1024². Generating ABOVE
    1024² can trigger SDXL's high-resolution failure mode — feature DUPLICATION
    / "melting". We DO render at 1280² for the extra texture/face detail, but we
    counter the duplication with GEOMETRY-DOMINANT conditioning
    (control_conditioning_scale raised to 1.6 in Phase 2): a tightly-enforced
    geometry control leaves SDXL little freedom to hallucinate duplicates, so
    1280² + strong control is far cleaner than 1280² was with weak control.
    1024² remains the guaranteed-clean fallback via ARTSMOKER_MV_RES=1024 if any
    duplication shows in the 03_raw_views debug artifact — no redeploy needed.

    1280² uses fp16 VAE decode to stay under the host-RAM ceiling (the fp32
    6-view decode at 1280² risks the 32 GiB OOM; fp16 halves that footprint and
    was proven RAM-safe at 1280² previously).

    Returns (resolution:int, use_fp16_vae:bool).
    """
    override = _get_env("ARTSMOKER_MV_RES", "")
    if override:
        try:
            r = int(override)
            fp16 = _get_env("ARTSMOKER_MV_FP16_VAE", "") == "1"
            logger.info("MV resolution override: %d (fp16_vae=%s)", r, fp16)
            return r, fp16
        except ValueError:
            pass
    # 1280² for higher detail; fp16 VAE decode for host-RAM safety. SDXL
    # duplication is held in check by the strong geometry control in Phase 2.
    return 1280, True


def _reload_triposg(model_dict):
    """Reload the TripoSG pipeline onto GPU after it was EVICTED (not parked).

    On low-host-RAM instances we free TripoSG entirely before the texture phases
    (delete the object + reclaim VRAM) instead of parking it on CPU, because the
    CPU copy would OOM the host. The next inference needs it back on CUDA, so we
    rebuild it from the locally-cached HF snapshot (already on disk from the
    initial load — no re-download). ~20s, paid only on low-RAM instances.
    """
    local_path = model_dict.get("triposg_local_path")
    if not local_path:
        # The model_dict may predate the triposg_local_path key (e.g. it was
        # built by the baked handler at container start, then a hot-reload
        # overlay swapped in this newer code but reused the existing dict). The
        # snapshot is still on disk — re-derive its path from the HF repo. This
        # is a local cache hit (no network), so it's safe and cheap. CRITICAL:
        # without this fallback an evicted TripoSG can never be reloaded and the
        # endpoint is bricked for all subsequent jobs ('NoneType' is not callable
        # at pipe()).
        try:
            from huggingface_hub import snapshot_download
            hf_repo = _get_env("ARTSMOKER_HF_REPO")
            hf_token = model_dict.get("hf_token") or _get_env("HUGGING_FACE_HUB_TOKEN") or None
            if hf_repo:
                local_path = snapshot_download(repo_id=hf_repo, token=hf_token)
                model_dict["triposg_local_path"] = local_path
                logger.info("Re-derived TripoSG snapshot path from HF repo %s", hf_repo)
        except Exception as _e:
            logger.warning("Could not re-derive TripoSG snapshot path: %s", _e)
    if not local_path:
        logger.warning("Cannot reload TripoSG — no cached local path recorded")
        return False
    try:
        import time as _time
        t0 = _time.time()
        from triposg import TripoSGPipeline
        pipe = TripoSGPipeline.from_pretrained(local_path)
        if torch.cuda.is_available():
            pipe.to("cuda")
        model_dict["pipe"] = pipe
        model_dict["_triposg_evicted"] = False
        logger.info("Reloaded evicted TripoSG to GPU in %.0fs", _time.time() - t0)
        return True
    except Exception as e:
        logger.warning("Failed to reload evicted TripoSG: %s", e)
        return False


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

    # Self-heal: if a prior job EVICTED TripoSG (low host-RAM path) and the
    # reload didn't restore it, pipe is None here → pipe() would raise
    # 'NoneType is not callable' and brick the endpoint for every job. Rebuild
    # it before use. (_reload_triposg re-derives the snapshot path from the HF
    # repo if model_dict lacks it — e.g. a hot-reload overlay reused an older
    # model_dict.)
    pipe = model_dict.get("pipe")
    if pipe is None:
        logger.warning("TripoSG pipe is None at predict entry — reloading (evicted and not restored)...")
        if _reload_triposg(model_dict):
            pipe = model_dict.get("pipe")
    if pipe is None:
        raise RuntimeError("TripoSG pipeline unavailable (evict/reload failed) — cannot run Phase 1")
    rmbg_model = model_dict.get("rmbg_model")
    high_vram = model_dict.get("high_vram", False)
    texture_available = model_dict.get("texture_available", False)

    # 1. Decode input image
    img = _decode_image(input_data["image"]).convert("RGB")
    logger.info("Input image: %dx%d", img.width, img.height)
    # NOTE: source_image (the MV-Adapter reference) is captured LATER, AFTER the
    # subject-fill crop, so the reference framing matches the geometry that
    # TripoSG builds from the SAME cropped image. Capturing it here (pre-crop)
    # fed MV-Adapter an uncropped reference while the geometry control images
    # were full-frame (cropped) → conflicting scale → the projected texture
    # smeared and the face drifted. See the crop block below.
    source_image = None

    # 2. Remove background if a bg-removal model is available
    if rmbg_model is not None:
        logger.info("Removing background (%s)...", getattr(rmbg_model, "_artsmoker_bg_backend", "birefnet"))
        orig_size = img.size  # (W, H)

        # Compute the foreground mask via the shared helper (handles RMBG vs
        # BiRefNet conventions). Same uint8 H×W mask either way.
        mask_np = _foreground_mask_np(rmbg_model, img)
        logger.info("Foreground mask: shape=%s, range=[%d, %d]", mask_np.shape, mask_np.min(), mask_np.max())

        # 3. Composite onto white background
        pil_mask = Image.fromarray(mask_np)
        img_rgba = img.copy()
        img_rgba.putalpha(pil_mask)
        white_bg = Image.new("RGBA", orig_size, (255, 255, 255, 255))
        white_bg.paste(img_rgba, mask=img_rgba.split()[3])
        img = white_bg.convert("RGB")
        logger.info("Background removed, composited on white")

        # 4. SUBJECT-FILL CROP — the single highest-impact geometry lever.
        # TripoSG encodes the whole image into a fixed-capacity latent (2048/
        # 4096 tokens). If the subject only fills part of the frame, the face
        # gets a tiny share of tokens → smooth/flat facial geometry (no eye
        # sockets/nose relief), no matter the octree depth. Cropping to the
        # subject's bounding box (from the RMBG mask) + a small margin, then
        # recentering on a square, makes the figure fill the frame so far more
        # latent capacity lands on it. This is the research-backed primary fix
        # for flat faces on full-body subjects.
        try:
            ys, xs = np.where(mask_np > 16)  # foreground pixels
            if xs.size > 0 and ys.size > 0:
                x0, x1 = int(xs.min()), int(xs.max())
                y0, y1 = int(ys.min()), int(ys.max())
                bw, bh = x1 - x0, y1 - y0
                # square side = longer bbox dim + 8% margin each side
                side = int(max(bw, bh) * 1.16)
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                sx0 = cx - side // 2
                sy0 = cy - side // 2
                # paste the (possibly out-of-bounds) square region onto a white
                # square canvas so the subject is centered and fills it
                canvas = Image.new("RGB", (side, side), (255, 255, 255))
                src_x0, src_y0 = max(0, sx0), max(0, sy0)
                src_x1, src_y1 = min(img.width, sx0 + side), min(img.height, sy0 + side)
                region = img.crop((src_x0, src_y0, src_x1, src_y1))
                canvas.paste(region, (src_x0 - sx0, src_y0 - sy0))
                _frac_before = (bw * bh) / float(img.width * img.height)
                img = canvas
                logger.info(
                    "Subject-fill crop: bbox=%dx%d (%.0f%% of frame) -> %dx%d square (subject now fills frame)",
                    bw, bh, _frac_before * 100, side, side,
                )
            else:
                logger.info("Subject-fill crop skipped: empty mask")
        except Exception as _crop_e:
            logger.warning("Subject-fill crop failed (using uncropped): %s", _crop_e)
    else:
        logger.info("No RMBG model — using input image as-is")

    # Capture the MV-Adapter reference from the FINAL framed image (post-crop),
    # so the reference and the TripoSG geometry share the same framing/scale.
    # _preprocess_mv_reference re-runs RMBG + gray-composite on this; using the
    # cropped img here keeps the reference's subject scale aligned with the
    # geometry control images → clean projection (no smear/drift).
    source_image = img.copy()

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 1: TripoSG geometry generation
    # ═══════════════════════════════════════════════════════════════════════
    steps = input_data.get("num_inference_steps", 50)
    guidance = input_data.get("guidance_scale", 7.0)
    seed = input_data.get("seed")
    generator = torch.Generator("cuda").manual_seed(seed) if seed is not None else None

    logger.info("Phase 1: TripoSG geometry — steps=%d, guidance=%.1f, seed=%s", steps, guidance, seed)

    # Octree depth controls geometry resolution. Higher = finer detail (e.g.
    # facial structure), at the cost of slower marching cubes. The frontend's
    # quality preset sends mesh_resolution; we map it to octree depth. Default
    # 8/9 (was 7/8) for noticeably sharper geometry on heads/faces.
    _dense_depth = int(input_data.get("dense_octree_depth", 8))
    _hier_depth = int(input_data.get("hierarchical_octree_depth", _dense_depth + 1))
    # Latent token count = TripoSG's shape-capacity ceiling. The VAE is
    # position-encoding-free, so it can decode at a HIGHER token count than the
    # 2048 default with NO fine-tuning (per the TripoSG paper's 4096 extrapolation).
    # 2048->4096 raises the actual detail ceiling the face is hitting — the only
    # in-model lever that adds capacity (octree depth just samples an
    # already-smooth field more densely). Cost is in Phase-1 VRAM/compute, which
    # has headroom (TripoSG is evicted before the texture phases). Override via
    # ARTSMOKER_TRIPOSG_TOKENS or request 'num_tokens'.
    _num_tokens = int(input_data.get("num_tokens", _get_env("ARTSMOKER_TRIPOSG_TOKENS", "4096")))
    logger.info("Phase 1: octree depth dense=%d hierarchical=%d, num_tokens=%d",
                _dense_depth, _hier_depth, _num_tokens)

    t0 = _t.time()
    output = pipe(
        image=img,
        num_inference_steps=steps,
        num_tokens=_num_tokens,
        guidance_scale=guidance,
        generator=generator,
        # Use hierarchical decoder (not flash) — flash requires diso CUDA package.
        use_flash_decoder=False,
        dense_octree_depth=_dense_depth,
        hierarchical_octree_depth=_hier_depth,
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

    # Release Phase 1's GPU working set BEFORE texture phases. TripoSG's dense
    # octree marching-cubes leaves a large transient SDF volume cached by the
    # allocator (~25+ GB reserved at octree depth 9/10). The extracted mesh is
    # CPU-side (numpy/trimesh), so we can drop the pipeline output and reclaim
    # that cache now. Without this, Phase 2's SDXL multi-view forward OOMs even
    # on a 44.5 GB GPU (observed: only 1.18 GB driver-free → 3 GB alloc fails).
    _log_gpu_mem("after Phase 1 (before reclaim)")
    try:
        del output
    except Exception:
        pass
    _reclaim_cuda_memory("after Phase 1 reclaim")

    # Orientation fix: TripoSG emits the mesh with its FRONT facing the +Y / azimuth-180
    # camera, but MV-Adapter expects the front to align with the reference image at the
    # azimuth-0 camera. Diagnostic renders confirmed the front was 180° off (face landed
    # on the back/side). Rotate 180° about the up (Y) axis so the front faces azimuth 0.
    try:
        import trimesh as _tm
        _rot = _tm.transformations.rotation_matrix(np.pi, [0, 1, 0])
        mesh.apply_transform(_rot)
        logger.info("Applied 180° Y-axis rotation to align mesh front with reference")
    except Exception as _rot_err:
        logger.warning("Mesh orientation rotation failed: %s", _rot_err)

    # 4b. OPTIONAL Phase-1 mesh cleanup: drop disconnected floaters + degenerate
    # faces from the raw octree mesh BEFORE decimation, so the texture pipeline
    # never wastes UV space (or projects onto) stray junk. Conservative by
    # default — only removes components far smaller than the main body (tiny
    # specks), never legitimate separate parts. Off unless mesh_cleanup is truthy
    # (default on); tune the floater threshold via mesh_cleanup_min_ratio
    # (fraction of the largest component's face count; default 1%).
    def _as_bool_in(v, d):
        if v is None:
            return d
        return str(v).lower() in ("1", "true", "yes", "on")
    if _as_bool_in(input_data.get("mesh_cleanup"), True):
        try:
            import numpy as _np
            faces_before = len(mesh.faces)
            # Drop degenerate (zero-area) + duplicate faces first.
            try:
                mesh.update_faces(mesh.nondegenerate_faces())
                mesh.update_faces(mesh.unique_faces())
                mesh.remove_unreferenced_vertices()
            except Exception as _de:
                logger.debug("degenerate/duplicate face cull skipped: %s", _de)
            # Drop tiny disconnected floaters: keep components whose face count is
            # >= min_ratio × the largest component's. Default 1% — kills specks,
            # keeps real multi-part geometry (e.g. a separate weapon/accessory).
            try:
                min_ratio = float(input_data.get("mesh_cleanup_min_ratio", 0.01) or 0.01)
            except (TypeError, ValueError):
                min_ratio = 0.01
            try:
                comps = mesh.split(only_watertight=False)
                if comps is not None and len(comps) > 1:
                    sizes = [len(c.faces) for c in comps]
                    biggest = max(sizes)
                    thresh = max(1, int(biggest * min_ratio))
                    kept = [c for c, s in zip(comps, sizes) if s >= thresh]
                    if kept and len(kept) < len(comps):
                        import trimesh as _tm2
                        mesh = _tm2.util.concatenate(kept)
                        logger.info("Mesh cleanup: kept %d/%d components (dropped %d floaters < %d faces)",
                                    len(kept), len(comps), len(comps) - len(kept), thresh)
            except Exception as _se:
                logger.debug("floater split/cull skipped: %s", _se)
            if len(mesh.faces) != faces_before:
                logger.info("Phase-1 cleanup: %d -> %d faces", faces_before, len(mesh.faces))
        except Exception as _ce:
            logger.warning("Phase-1 mesh cleanup skipped (keeping raw mesh): %s", _ce)

    # 5. Decimate to target face count. 0 = "maximum quality", but we still
    # enforce a hard ceiling: the texture pipeline (UV unwrap + projection +
    # Poisson) crashes the worker on extreme densities (8.6M raw octree-9 faces
    # crashed it). Cap at 1M to keep fine geometry while staying texture-safe.
    _TEXTURE_SAFE_MAX_FACES = 1000000
    target_faces = input_data.get("faces", 500000)
    if target_faces <= 0 or target_faces > _TEXTURE_SAFE_MAX_FACES:
        if len(mesh.faces) > _TEXTURE_SAFE_MAX_FACES:
            logger.info("Capping faces to texture-safe max %d (was %d, requested %s)",
                        _TEXTURE_SAFE_MAX_FACES, len(mesh.faces), target_faces or "unlimited")
        target_faces = _TEXTURE_SAFE_MAX_FACES
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
    # For the hunyuan/mvpainter backends, attempt texturing even if
    # texture_available was set False at LOAD time (e.g. a dep install failed at
    # load, or a hot-reload overlay reused a stale model_dict). They load their
    # pipe + deps on-demand with their own watchdog guards, so a stale load-time
    # flag must not permanently block the texture path.
    _backend_now = model_dict.get("texture_backend") or _texture_backend(input_data)
    if input_data.get("texture_backend"):
        _backend_now = str(input_data["texture_backend"]).lower().strip()
    _attempt_texture = texture_available or (_backend_now in ("hunyuan", "trellis2"))
    textured_glb_data = None
    if _attempt_texture:
        try:
            textured_glb_data = _generate_texture(
                mesh, source_image, model_dict, input_data
            )
        except Exception as tex_err:
            logger.warning("Phase 2/3 texture generation failed — falling back to untextured: %s", tex_err)
            import traceback
            # Log the full traceback at WARNING (not DEBUG) — a texture failure is
            # operationally important and the stack pinpoints the failing line for
            # diagnosis without a redeploy-to-raise-log-level cycle.
            logger.warning("Texture error traceback:\n%s", traceback.format_exc())
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
    # Report which texture backend actually ran + whether the GLB carries PBR maps,
    # so the gallery metadata (read by generate_3d.py → AssetViewer) is accurate
    # rather than defaulting to the deployed backend's label. PBR backends:
    # hunyuan/trellis2 emit base-color + metallic-roughness; mvpainter emits
    # base-color (+ optional normal map). _textured reflects success vs the
    # untextured fallback.
    _textured = textured_glb_data is not None
    _has_pbr = _textured and (_backend_now in ("hunyuan", "trellis2"))
    return json.dumps({
        "mesh": b64_glb,
        "format": "base64_glb",
        "vertices": vertex_count,
        "faces": face_count,
        "textured": _textured,
        "texture_backend": _backend_now if _textured else None,
        "has_pbr": _has_pbr,
        "rasterizer": _rasterizer_choice() if _textured else "",
    })


def _generate_texture_hunyuan(mesh_path, source_image, model_dict, input_data, temp_dir):
    """Texture an existing mesh with Hunyuan3D-Paint → PBR GLB bytes.

    Called from _generate_texture's backend branch AFTER TripoSG has been
    parked/evicted (so VRAM is free). Single call: mesh path + reference image →
    OBJ + sibling PBR GLB (albedo + metallic-roughness). Returns GLB bytes.

    Hunyuan3D-Paint's architecture (per-view normal+coordinate-map conditioning +
    cross-view attention + random-azimuth training) is what avoids the multi-view
    duplication/Janus that MV-Adapter hit on complex poses — see project notes.

    Raises on failure so the caller falls back to the untextured GLB.
    """
    import time as _t
    code_dir = model_dict.get("code_dir", "")
    hf_token = model_dict.get("hf_token")
    t0 = _t.time()
    logger.info("Texturing with Hunyuan3D-Paint backend...")

    # Watchdog guard: the native ops compile (~2-5 min) exceeds MMS's 120s
    # response timeout. They are built at LOAD time normally; if NOT ready here
    # (warm worker from before this fix, or a failed load build), do NOT build
    # inline — kick off the background build and fail fast (caller → untextured).
    if not _ensure_hunyuan_ops(code_dir, blocking=False):
        _ensure_hunyuan_ops_background(code_dir)
        st = _hunyuan_ops_bg["state"]
        msg = ("Hunyuan paint native ops are being prepared in the background "
               "(one-time CUDA compile, ~2-5 min). Texture skipped this run — resubmit shortly.")
        if st == 2:
            msg = f"Hunyuan paint native ops preparation failed: {_hunyuan_ops_bg['error']}"
        logger.warning("Hunyuan texture deferred: %s", msg)
        raise RuntimeError(msg)

    # Get (or on-demand load) the paint pipeline.
    paint_pipe = model_dict.get("paint_pipe")
    on_demand = paint_pipe is None
    if on_demand:
        logger.info("Loading Hunyuan3D-Paint on-demand...")
        paint_pipe = _load_hunyuan_paint(code_dir, hf_token)
        if model_dict.get("high_vram"):
            model_dict["paint_pipe"] = paint_pipe  # cache for reuse on high-VRAM

    # Reference image: background-removed, composited on neutral gray (the paint
    # pipeline re-handles RGBA→white internally, but feeding a clean subject is
    # best). Reuse the same preprocessing as MV-Adapter for consistency.
    ref_image = _preprocess_mv_reference(source_image, model_dict.get("rmbg_model"))
    _save_debug_artifact(ref_image, "01_reference")

    out_dir = os.path.join(temp_dir, "paint_out")
    os.makedirs(out_dir, exist_ok=True)
    out_obj = os.path.join(out_dir, "textured_mesh.obj")

    _log_gpu_mem("before Hunyuan paint call")
    # use_remesh=FALSE: the pipeline's remesh step (utils/simplify_mesh_utils.py)
    # uses pymeshlab's save_current_mesh, whose save plugins fail on this headless
    # container (missing libOpenGL — same issue that broke pymeshlab in the
    # MV-Adapter path) → "Unknown format for save: obj". Skip it: our Phase-1 mesh
    # is already clean (decimated to 1M faces, fixed normals), and Hunyuan's
    # mesh_uv_wrap does the UV unwrap regardless. save_glb=False: the pipeline's
    # own OBJ→GLB step uses Blender (bpy, not installed); it writes OBJ+MTL+PBR
    # maps via save_obj_mesh (manual file I/O, no pymeshlab/bpy), and we assemble
    # the PBR GLB from those with trimesh.
    returned = paint_pipe(
        mesh_path=mesh_path,
        image_path=ref_image,
        output_mesh_path=out_obj,
        use_remesh=False,
        save_glb=False,
    )
    logger.info("Hunyuan paint call complete in %.1fs (returned %s)", _t.time() - t0, returned)
    _log_gpu_mem("after Hunyuan paint call")

    # On-demand (low-VRAM): release the paint pipe now.
    if on_demand and not model_dict.get("high_vram"):
        try:
            del paint_pipe
            model_dict["paint_pipe"] = None
        except Exception:
            pass
        _reclaim_cuda_memory("after on-demand Hunyuan paint unload")

    # Assemble a self-contained PBR GLB from the OBJ + maps the pipeline wrote.
    glb_path = _assemble_pbr_glb(out_obj, out_dir)
    if not glb_path or not os.path.exists(glb_path):
        raise RuntimeError(f"Hunyuan paint produced no GLB (obj={out_obj})")

    with open(glb_path, "rb") as f:
        glb_data = f.read()
    logger.info("Hunyuan3D-Paint textured GLB: %.1f KB from %s", len(glb_data) / 1024, glb_path)

    # Debug: extract the baked albedo + MR atlases for inspection.
    if _get_env("ARTSMOKER_TEXTURE_DEBUG", "") == "1":
        try:
            import trimesh as _tm
            _m = _tm.load(glb_path, process=False)
            _g = list(_m.geometry.values())[0] if hasattr(_m, "geometry") and _m.geometry else _m
            _mat = getattr(getattr(_g, "visual", None), "material", None)
            _alb = getattr(_mat, "baseColorTexture", None)
            if _alb is not None:
                _save_debug_artifact(_alb, "02_albedo_atlas")
            _mr = getattr(_mat, "metallicRoughnessTexture", None)
            if _mr is not None:
                _save_debug_artifact(_mr.convert("RGB"), "03_mr_atlas")
        except Exception as _de:
            logger.warning("Hunyuan debug atlas extract failed: %s", _de)

    return glb_data


# ── TRELLIS.2 backend (Microsoft, MIT — commercial-clean Hunyuan-grade) ───────
def _trellis2_runtime_setup(model_dict):
    """Shared runtime prep for BOTH TRELLIS.2 pipelines (texturer + full image→3D).

    Sets HF auth + the SLAT backend env vars (sparse attention has NO sdpa
    fallback → xformers; conv → flex_gemm), and monkeypatches TRELLIS.2's BiRefNet
    rembg wrapper to the MIT ZhengPeng7/BiRefNet repo so the bundled, GATED,
    non-commercial briaai/RMBG-2.0 is never DOWNLOADED at from_pretrained (it would
    never RUN — we always feed a pre-cut RGBA image, which preprocess_image's
    has_alpha branch passes straight through — but from_pretrained constructs it
    regardless). Operator can opt back into RMBG via ARTSMOKER_TRELLIS2_REMBG=rmbg
    (disclosed, requires accepting Bria's license on HF). Idempotent.
    """
    hf_token = model_dict.get("hf_token")
    if hf_token:
        os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", hf_token)
        os.environ.setdefault("HF_TOKEN", hf_token)
    os.environ.setdefault("ATTN_BACKEND", "xformers")
    os.environ.setdefault("SPARSE_CONV_BACKEND", "flex_gemm")
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    _rembg_choice = (_get_env("ARTSMOKER_TRELLIS2_REMBG", "birefnet") or "birefnet").lower().strip()
    if _rembg_choice != "rmbg":
        try:
            from trellis2.pipelines.rembg import BiRefNet as _T2BiRefNet
            if not getattr(_T2BiRefNet, "_artsmoker_patched", False):
                _orig_init = _T2BiRefNet.__init__
                def _mit_init(self, model_name="ZhengPeng7/BiRefNet", *a, **kw):
                    return _orig_init(self, model_name="ZhengPeng7/BiRefNet", *a, **kw)
                _T2BiRefNet.__init__ = _mit_init
                _T2BiRefNet._artsmoker_patched = True
                logger.info("TRELLIS.2 rembg forced to MIT BiRefNet (gated RMBG-2.0 download avoided)")
        except Exception as _pe:
            logger.warning("Could not patch TRELLIS.2 rembg to BiRefNet (%s) — "
                           "may attempt the bundled (gated) RMBG download", _pe)
    else:
        logger.info("TRELLIS.2 rembg: operator opted into RMBG (non-commercial) — using bundled repo")


def _load_trellis2_texture_pipe(model_dict):
    """Load (and cache per worker) the TRELLIS.2 texturing pipeline.

    Requires the TRELLIS.2 stack importable (_ensure_trellis2 at LOAD time). The
    4 texturing checkpoints (~6.8 GB) + the gated DINOv3 encoder are pulled from
    HF at from_pretrained — needs HF auth. low_vram=True (the repo default) keeps
    each model on CPU and pages it to GPU per step, which fits the 44.5 GB L40S
    alongside TripoSG (we evict TripoSG before texturing regardless).
    """
    global _trellis2_texture_pipe
    if _trellis2_texture_pipe is not None:
        return _trellis2_texture_pipe
    import time as _t
    _trellis2_runtime_setup(model_dict)
    from trellis2.pipelines import Trellis2TexturingPipeline
    t0 = _t.time()
    logger.info("Loading TRELLIS.2 texturing pipeline (%s / %s)...",
                _TRELLIS2_HF_REPO, _TRELLIS2_TEX_CONFIG)
    pipe = Trellis2TexturingPipeline.from_pretrained(
        _TRELLIS2_HF_REPO, config_file=_TRELLIS2_TEX_CONFIG
    )
    # We feed RGBA → TRELLIS.2's rembg never runs; drop the handle so it can't
    # page onto GPU. (Belt-and-suspenders with the MIT patch above.)
    try:
        pipe.rembg_model = None
    except Exception:
        pass
    pipe.cuda()  # low_vram=True → this only moves the lightweight bits; models page per step
    logger.info("TRELLIS.2 texturing pipeline loaded in %.0fs", _t.time() - t0)
    _trellis2_texture_pipe = pipe
    return pipe


def _generate_texture_trellis2(mesh_path, source_image, model_dict, input_data, temp_dir):
    """Texture an existing mesh with TRELLIS.2 → PBR GLB bytes.

    Called from _generate_texture's backend branch AFTER TripoSG has been
    evicted/parked (VRAM free). TRELLIS.2's SLAT/SparseTensor texture model is the
    commercial-clean (MIT) analogue of Hunyuan3D-Paint: image-conditioned (DINOv3)
    texture-voxel generation baked onto the mesh's own UVs. run() returns a fully
    PBR-textured trimesh (base_color + metallic-roughness + alpha).

    NOTE: TRELLIS.2's postprocess bake uses nvdiffrast (NVIDIA non-commercial). We
    run it here for the quality A/B vs Hunyuan FIRST; the nvdiffrast→Kaolin swap is
    a separate (licensing-only) variable to validate independently, so quality and
    rasterizer-license are never confounded in one change.

    Raises on failure so the caller falls back to the untextured GLB.
    """
    import time as _t
    t0 = _t.time()
    logger.info("Texturing with TRELLIS.2 backend...")

    # Watchdog guard: the CUDA-ext build (~5-10 min) far exceeds MMS's 120s
    # response timeout. Built at LOAD time normally; if NOT ready on this warm
    # worker, do NOT build inline — kick the background build and fail fast so the
    # caller returns the untextured mesh (resubmit once the build lands).
    if not _ensure_trellis2(blocking=False):
        _ensure_trellis2_background()
        st = _trellis2_ops_bg["state"]
        msg = ("TRELLIS.2 native ops are being prepared in the background "
               "(one-time CUDA build, ~5-10 min). Texture skipped this run — resubmit shortly.")
        if st == 2:
            msg = f"TRELLIS.2 native ops preparation failed: {_trellis2_ops_bg['error']}"
        logger.warning("TRELLIS.2 texture deferred: %s", msg)
        raise RuntimeError(msg)

    import trimesh as _trimesh
    pipe = _load_trellis2_texture_pipe(model_dict)

    # Quality knobs (per-request tunable for live A/B without redeploy):
    #  • texture_size — PBR atlas resolution. TRELLIS.2's run() default is 2048,
    #    but it supports 4096 (Hunyuan parity). 2048 reads as soft/hazy; 4096 is
    #    noticeably sharper. Default 4096 here.
    #  • tex_resolution — the SLAT voxel resolution (1024 is the model's max).
    #  • ref_lift — shadow-lift on the reference. Default 0 for TRELLIS.2 (the
    #    0.7 MVPainter lift washes out contrast → dull look). Override per-request.
    def _as_int(v, d):
        try: return int(v)
        except (TypeError, ValueError): return d
    def _as_float(v, d):
        try: return float(v)
        except (TypeError, ValueError): return d
    texture_size = _as_int(input_data.get("texture_size"), 4096)
    tex_resolution = _as_int(input_data.get("tex_resolution"), 1024)
    ref_lift = _as_float(input_data.get("ref_lift"), 0.0)
    seed = _as_int(input_data.get("seed"), 42)
    logger.info("TRELLIS.2 params: texture_size=%d resolution=%d ref_lift=%.2f seed=%d",
                texture_size, tex_resolution, ref_lift, seed)

    # Reference image: RGBA cutout (subject opaque, bg transparent). TRELLIS.2's
    # preprocess_image uses the alpha channel directly when present (else runs its
    # own BiRefNet) — same contract MVPainter wants, so reuse that helper. Pass
    # ref_lift (default 0) so we don't inherit MVPainter's contrast-washing lift.
    ref_rgba = _preprocess_mvpainter_reference(source_image, model_dict.get("rmbg_model"),
                                               lift_override=ref_lift)
    _save_debug_artifact(ref_rgba.convert("RGB"), "01_reference")

    mesh = _trimesh.load(mesh_path, process=False, force="mesh")
    _log_gpu_mem("before TRELLIS.2 run")
    out_mesh = pipe.run(mesh, ref_rgba, seed=seed,
                        resolution=tex_resolution, texture_size=texture_size)
    logger.info("TRELLIS.2 run complete in %.1fs", _t.time() - t0)
    _log_gpu_mem("after TRELLIS.2 run")

    glb_path = os.path.join(temp_dir, "trellis2_textured.glb")
    out_mesh.export(glb_path)  # PBR material baked into the GLB
    if not os.path.exists(glb_path) or os.path.getsize(glb_path) == 0:
        raise RuntimeError("TRELLIS.2 produced no GLB")
    with open(glb_path, "rb") as f:
        glb_data = f.read()
    logger.info("TRELLIS.2 textured GLB: %.1f KB from %s", len(glb_data) / 1024, glb_path)
    return glb_data


# ── TRELLIS.2 FULL image→3D pipeline (standalone, no TripoSG) ─────────────────
def _load_trellis2_full_pipe(model_dict):
    """Load (and cache per worker) the full TRELLIS.2 image→3D pipeline.

    Unlike the texturer (BYO mesh), this GENERATES geometry AND texture from a
    single image. Loads the full `pipeline.json` config = 8 checkpoints (sparse-
    structure + shape-SLAT + tex-SLAT flow models & decoders, ~16 GB) + the gated
    DINOv3 encoder, from microsoft/TRELLIS.2-4B. Shares the CUDA-ext stack
    (_ensure_trellis2), HF auth, SLAT backend env, and the MIT-rembg patch with
    the texturer via _trellis2_runtime_setup. low_vram=True pages models per step
    (fits the 44.5 GB L40S).
    """
    global _trellis2_full_pipe
    if _trellis2_full_pipe is not None:
        return _trellis2_full_pipe
    import time as _t
    _trellis2_runtime_setup(model_dict)
    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    t0 = _t.time()
    logger.info("Loading TRELLIS.2 FULL image→3D pipeline (%s / %s)...",
                _TRELLIS2_HF_REPO, _TRELLIS2_FULL_CONFIG)
    pipe = Trellis2ImageTo3DPipeline.from_pretrained(
        _TRELLIS2_HF_REPO, config_file=_TRELLIS2_FULL_CONFIG
    )
    try:
        pipe.rembg_model = None  # we pre-cut to RGBA; rembg never runs
    except Exception:
        pass
    pipe.cuda()
    logger.info("TRELLIS.2 FULL pipeline loaded in %.0fs", _t.time() - t0)
    _trellis2_full_pipe = pipe
    return pipe


def _predict_trellis2_full(input_data, model_dict):
    """Full image→3D via TRELLIS.2: image → textured PBR GLB (no TripoSG).

    Mirrors _predict_image_to_3d's JSON contract (base64_glb + verts/faces/...),
    so the frontend 3D flow + gallery are unchanged. Steps: decode image → RGBA
    cutout (BiRefNet) → pipe.run(image)[0] (generates geometry + texture) →
    simplify to the nvdiffrast cap → o_voxel.postprocess.to_glb (decimate 1M,
    4096² PBR atlas, remesh) → base64.
    """
    import base64 as _b64
    import tempfile as _tf
    import time as _t
    t0 = _t.time()

    # Watchdog guard: the CUDA-ext build (~5-10 min) exceeds MMS's 120s response
    # timeout. Built at LOAD time normally; if NOT ready on this warm worker, kick
    # the background build and fail fast (the job is retryable once it lands).
    if not _ensure_trellis2(blocking=False):
        _ensure_trellis2_background()
        st = _trellis2_ops_bg["state"]
        msg = ("TRELLIS.2 native ops are being prepared in the background "
               "(one-time CUDA build, ~5-10 min). Resubmit shortly.")
        if st == 2:
            msg = f"TRELLIS.2 native ops preparation failed: {_trellis2_ops_bg['error']}"
        raise RuntimeError(msg)

    # Decode the input image.
    img_b64 = input_data.get("image")
    if not img_b64:
        raise ValueError("No input image provided for TRELLIS.2 full pipeline")
    from PIL import Image as _PImg
    import io as _io
    src = _PImg.open(_io.BytesIO(_b64.b64decode(img_b64)))

    # RGBA cutout (BiRefNet/MIT) — TRELLIS.2's preprocess_image takes the has_alpha
    # branch and skips its own (gated) rembg. ref_lift=0: no MVPainter shadow-lift.
    ref_rgba = _preprocess_mvpainter_reference(src, model_dict.get("rmbg_model"), lift_override=0.0)
    _save_debug_artifact(ref_rgba.convert("RGB"), "01_reference")

    pipe = _load_trellis2_full_pipe(model_dict)

    def _as_int(v, d):
        try: return int(v)
        except (TypeError, ValueError): return d
    seed = _as_int(input_data.get("seed"), 42)
    # Quality default: 1M faces (the TRELLIS.2 slider MAX), matching TripoSG's
    # high-quality output so users don't perceive TRELLIS.2 as lower-fidelity.
    # This is also what the catalog input_fields declare (faces=1000000). The
    # A10G/L40S have ample VRAM headroom for it (measured ~5 GB peak of 24 GB).
    # Texture atlas stays at 2048 (the app's standard) unless overridden to 4096.
    # Both overridable per-request via faces / texture_size.
    texture_size = _as_int(input_data.get("texture_size"), 2048)
    decimation_target = _as_int(input_data.get("faces"), 1000000) or 1000000
    # pipeline_type: the app ALWAYS sets one (512 / 1024_cascade / 1536_cascade);
    # the bare run() default is not what the app uses. '1024_cascade' is the app's
    # standard-quality choice. Overridable per-request via resolution.
    _res = str(input_data.get("resolution", "1024"))
    pipeline_type = {"512": "512", "1024": "1024_cascade", "1536": "1536_cascade"}.get(_res, "1024_cascade")
    # to_glb postprocess knobs — per-request tunable for live A/B (the geometry was
    # coming out shredded; isolating which postprocess param is responsible without
    # a redeploy per trial). remesh=False uses o_voxel's branch WITH the topology
    # cleanup (remove_small_connected_components / repair_non_manifold /
    # fill_holes / unify_orientations); remesh=True skips that cleanup.
    def _as_float(v, d):
        try: return float(v)
        except (TypeError, ValueError): return d
    def _as_bool(v, d):
        if v is None: return d
        return str(v).lower() in ("1", "true", "yes", "on")
    remesh = _as_bool(input_data.get("remesh"), False)        # default → cleanup branch
    remesh_project = _as_float(input_data.get("remesh_project"), 0.9)  # to_glb's own default

    _log_gpu_mem("before TRELLIS.2 full run")
    # preprocess_image=True (TRELLIS.2 resizes/recenters/premultiplies; RGBA-safe,
    # skips its own rembg) + pipeline_type set like the official app (1024_cascade).
    # This made generation rich (12M-face raw mesh on the stock image) but the GLB
    # postprocess still shredded it — the remaining variable is the to_glb remesh/
    # cleanup path (knobs above), under A/B.
    out = pipe.run(ref_rgba, seed=seed, preprocess_image=True, pipeline_type=pipeline_type)
    mesh = out[0]
    logger.info("TRELLIS.2 full run complete in %.1fs", _t.time() - t0)
    _log_gpu_mem("after TRELLIS.2 full run")

    # nvdiffrast hard cap on triangle count before GLB postprocess.
    try:
        mesh.simplify(16777216)
    except Exception as _se:
        logger.info("mesh.simplify skipped (%s)", _se)

    import o_voxel
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices,
        faces=mesh.faces,
        attr_volume=mesh.attrs,
        coords=mesh.coords,
        attr_layout=mesh.layout,
        voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=decimation_target,
        texture_size=texture_size,
        remesh=remesh,
        remesh_band=1,
        remesh_project=remesh_project,
        verbose=True,
    )
    logger.info("TRELLIS.2 to_glb: remesh=%s remesh_project=%s decimation_target=%d texture_size=%d",
                remesh, remesh_project, decimation_target, texture_size)
    # Resource-baseline telemetry (right-sizing the instance). Logs
    # PEAK GPU VRAM + current host RAM so we can tell if g6e.xlarge (or smaller) is
    # sufficient vs the 2xlarge we first tested on. The bake's UV-unwrap/remesh is
    # host-RAM-bound; the SLAT decode is the VRAM peak.
    try:
        if torch.cuda.is_available():
            _peak_vram = torch.cuda.max_memory_allocated() / (1024**3)
            _resv_vram = torch.cuda.max_memory_reserved() / (1024**3)
            logger.info("TRELLIS.2 RESOURCE PEAK: VRAM alloc=%.1f GB reserved=%.1f GB | host RAM avail=%.1f GB / total=%.1f GB",
                        _peak_vram, _resv_vram,
                        _host_ram_available_gb() or -1.0, _host_ram_total_gb() or -1.0)
    except Exception as _re:
        logger.info("resource-peak logging skipped (%s)", _re)
    temp_dir = _tf.mkdtemp(prefix="artsmoker_trellis2_full_")
    glb_path = os.path.join(temp_dir, "trellis2_full.glb")
    # extension_webp=True: encode the 4096² PBR atlas as WebP, not raw PNG. A 1M-
    # face mesh with an uncompressed atlas is ~80 MB → base64 ~107 MB, which blows
    # past the SageMaker async response limit (the inlined result never lands in
    # S3 → 'Frontend disconnected' / 500). WebP cuts the texture payload ~5-10×,
    # bringing the GLB well under the limit. This is exactly what TRELLIS.2's own
    # example.py does. (The texturer path's trimesh export stays PNG — its ~17 MB
    # output is already under the limit.)
    glb.export(glb_path, extension_webp=True)
    if not os.path.exists(glb_path) or os.path.getsize(glb_path) == 0:
        raise RuntimeError("TRELLIS.2 full pipeline produced no GLB")
    with open(glb_path, "rb") as f:
        glb_data = f.read()

    # Vertex/face counts for the response (post-decimation, from the exported GLB).
    vtx = fac = 0
    try:
        import trimesh as _tm
        _m = _tm.load(glb_path, process=False, force="mesh")
        vtx, fac = len(_m.vertices), len(_m.faces)
    except Exception:
        pass
    logger.info("TRELLIS.2 full GLB: %.1f KB, %d verts, %d faces", len(glb_data) / 1024, vtx, fac)

    b64_glb = _b64.b64encode(glb_data).decode("utf-8")
    return json.dumps({
        "mesh": b64_glb,
        "format": "base64_glb",
        "vertices": vtx,
        "faces": fac,
        "textured": True,
        "texture_backend": "trellis2_full",
        "has_pbr": True,
        "geometry_model": "TRELLIS.2",
    })


# ── MVPainter backend: REMOVED 2026-06-25 ──────────────────────────────────
# MVPainter was dropped entirely: research found its weights are fine-tuned
# from a Tencent Hunyuan3D checkpoint (NOT the claimed Apache-2.0 commercial-
# safe), and its texture quality was the lowest of the three backends. It is
# strictly dominated by Hunyuan (quality) and TRELLIS.2 (commercial-clean +
# native PBR). The shared _preprocess_mvpainter_reference() helper is RETAINED
# (TRELLIS.2 + Hunyuan reuse it for the RGBA cutout).

def _assemble_pbr_glb(obj_path, out_dir, albedo_path=None):
    """Build a self-contained textured GLB from an OBJ (+ UVs) + an albedo PNG.

    Generic OBJ+albedo → textured GLB assembler (used by texture backends that
    emit an OBJ/MTL + albedo PNG rather than a ready GLB). trimesh's native
    OBJ+MTL load is unreliable at picking up map_Kd (observed: it produced a
    703 KB GLB with NO texture/UV from an OBJ+MTL+albedo set). So we load
    geometry+UVs, then EXPLICITLY attach the albedo as a PBR baseColorTexture via
    TextureVisuals — guaranteeing the texture embeds in the GLB binary buffer.
    Falls back to a plain load if anything is missing.
    """
    import trimesh as _tm
    from PIL import Image as _PImg
    glb_path = os.path.join(out_dir, "textured_mesh_assembled.glb")
    # Locate the albedo if not given (a sibling albedo.png next to the OBJ).
    if albedo_path is None:
        cand = os.path.join(os.path.dirname(obj_path), "albedo.png")
        albedo_path = cand if os.path.exists(cand) else None
    try:
        loaded = _tm.load(obj_path, process=False)
        # If it's a Scene, concat to a single mesh.
        if isinstance(loaded, _tm.Scene):
            geoms = list(loaded.geometry.values())
            mesh = geoms[0] if len(geoms) == 1 else _tm.util.concatenate(geoms)
        else:
            mesh = loaded
        uv = getattr(getattr(mesh, "visual", None), "uv", None)
        has_tex = getattr(getattr(getattr(mesh, "visual", None), "material", None),
                          "baseColorTexture", None) is not None
        # When we have an EXPLICIT albedo, it must ALWAYS win — even if trimesh
        # already auto-loaded a texture from the OBJ's MTL. An OBJ whose MTL
        # points at a sibling/coarse albedo makes trimesh set has_tex=True; if we
        # only attached on (not has_tex) we'd silently ship that auto-loaded
        # texture instead of the refined albedo we were handed. So gate the
        # explicit attach on having a PNG + UVs, NOT on has_tex.
        if albedo_path and uv is not None and len(uv) > 0:
            img = _PImg.open(albedo_path).convert("RGB")
            mat = _tm.visual.material.PBRMaterial(baseColorTexture=img,
                                                  metallicFactor=0.0, roughnessFactor=0.9)
            mesh.visual = _tm.visual.TextureVisuals(uv=uv, material=mat)
            logger.info("Assembled GLB: attached %s as baseColorTexture (%s)",
                        os.path.basename(albedo_path), img.size)
        elif not albedo_path:
            logger.warning("Assembled GLB: no albedo found near %s — GLB will be untextured", obj_path)
        elif uv is None or len(uv) == 0:
            logger.warning("Assembled GLB: mesh has no UVs — cannot attach albedo, GLB untextured")
        mesh.export(glb_path, file_type="glb")
        return glb_path
    except Exception as e:
        logger.warning("PBR GLB assembly failed (%s) — trying plain export", e)
        try:
            _tm.load(obj_path, process=False).export(glb_path, file_type="glb")
            return glb_path
        except Exception as e2:
            logger.warning("Plain GLB export also failed: %s", e2)
            return None


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

        # Park TripoSG on CPU before the texture phases — on BOTH VRAM tiers.
        # TripoSG (~8 GB) is not used again until the next inference, so moving
        # it off-GPU frees headroom for SDXL's multi-view forward (Phase 2) and
        # the 4096² UV / render framebuffers (Phase 3). On the high-VRAM (g6e)
        # path this is the key change: previously TripoSG stayed resident and,
        # combined with Phase 1's reserved octree cache, left too little free
        # VRAM for SDXL (3 GB alloc OOM'd with only 1.18 GB free).
        # NOTE: RMBG stays on GPU — Phase 2 uses it to clean the multi-view
        # images. (The old low-VRAM code parked RMBG too, which would have
        # caused a device mismatch when RMBG ran on CUDA tensors in Phase 2.)
        # PARK-OR-EVICT: moving the fp32 TripoSG pipeline (~8-10 GB) to CPU needs
        # that much FREE host RAM. On g6e.xlarge (32 GiB RAM) the box is already
        # ~20 GB full with all models loaded, so an unconditional CPU-park pushes
        # it past the limit and the Linux OOM-killer SIGKILLs the worker the
        # instant we park (observed: abrupt disconnect + 500, NO Python traceback,
        # right after this log line). On g6e.2xlarge (64 GiB) there's ample room.
        # So: park to CPU only when host RAM clearly allows it; otherwise EVICT
        # TripoSG entirely (free GPU + RAM) and reload it from the local snapshot
        # before the next job. Either way Phase 2 gets its freed VRAM.
        # Determine the texture backend NOW (before park/evict) — it dictates the
        # right memory strategy. Only the MV-Adapter (default) bake reaches here —
        # the hunyuan / trellis2 backends early-return above with their own memory
        # handling. The MV-Adapter bake is GPU-bound, so PARKING TripoSG on CPU
        # (~10 GB) is sufficient; no force-evict needed.
        _force_evict = False

        _PARK_RAM_HEADROOM_GB = 14.0  # ~10 GB fp32 pipe + transfer buffers + margin
        triposg_pipe = model_dict.get("pipe")
        if triposg_pipe is not None:
            _avail_gb = _host_ram_available_gb()
            if _force_evict or (_avail_gb is not None and _avail_gb < _PARK_RAM_HEADROOM_GB):
                logger.info(
                    "EVICTING TripoSG from GPU (will reload before next job) — %s "
                    "(host RAM %.1f GB free)...",
                    "mvpainter host-RAM-bound bake" if _force_evict else "host RAM low",
                    _avail_gb if _avail_gb is not None else -1.0,
                )
                # Free TripoSG's VRAM WITHOUT a host-RAM copy. Two wrong ways we
                # already hit: (1) .to("cpu") copies ~8-10 GB fp32 into the
                # nearly-full host RAM → host OOM-kill; (2) just dropping the
                # Python ref does NOT reliably free the GPU storage in time —
                # TripoSG stayed resident (~16 GB) and MV-Adapter then CUDA-OOM'd
                # at Phase 2 (37.87 GB). The correct tool is the `meta` device:
                # moving the modules to meta releases their CUDA storage IMMEDIATELY
                # with ZERO host allocation (meta tensors have no backing storage).
                # We reload TripoSG fresh from the local snapshot next job anyway,
                # so discarding these weights is fine. Generic zero-copy eviction.
                _evict_module_to_meta(
                    triposg_pipe,
                    submodule_attrs=("vae", "transformer", "scheduler",
                                     "image_encoder", "feature_extractor"),
                    label="TripoSG",
                )
                model_dict["pipe"] = None
                model_dict["_triposg_evicted"] = True
                triposg_pipe = None
                del triposg_pipe
                # Force the VRAM release NOW, before MV-Adapter allocates, so
                # Phase 2 sees the freed headroom (not a deferred reclaim).
                _reclaim_cuda_memory("after evicting TripoSG (meta) — before texture parking")
            else:
                logger.info(
                    "Parking TripoSG on CPU for texture phases (%.1f GB host RAM free)...",
                    _avail_gb if _avail_gb is not None else -1.0,
                )
                _move_module_to(triposg_pipe, "cpu")

        # Park the TexturePipeline's upscaler (RealESRGAN) + inpainter (LaMa) on
        # CPU during Phase 2. They are ONLY used in Phase 3, but on the preloaded
        # high-VRAM path they sit resident on GPU, stealing headroom from Phase
        # 2's peak (MV-Adapter SDXL forward + nvdiffrast render of a 1M-face
        # mesh spiked to ~43.6 GB and OOM'd on the 44.5 GB L40S). We move them
        # back to GPU just before Phase 3. Safe: they aren't referenced in
        # Phase 2.
        _parked_tex_models = []
        if texture_pipe is not None:
            for _attr in ("upscaler", "inpainter"):
                _m = getattr(texture_pipe, _attr, None)
                if _m is not None and hasattr(_m, "to"):
                    try:
                        _m.to("cpu")
                        _parked_tex_models.append(_attr)
                    except Exception as _e:
                        logger.warning("Could not park texture_pipe.%s: %s", _attr, _e)
            if _parked_tex_models:
                logger.info("Parked texture models on CPU for Phase 2: %s", _parked_tex_models)

        _reclaim_cuda_memory("after parking TripoSG + texture models (before Phase 2)")

        # ═══════════════════════════════════════════════════════════════════
        # TEXTURE BACKEND DISPATCH — which texturer paints the TripoSG mesh.
        # ───────────────────────────────────────────────────────────────────
        # Active, user-selectable backends (registry texture_backends.options):
        #   • "trellis2" — TRELLIS.2 (MIT + commercial DINOv3). DEFAULT. Native
        #     PBR; self-contained bake via o_voxel.postprocess.to_glb (does NOT
        #     use the mvadapter TexturePipeline below).
        #   • "hunyuan"  — Hunyuan3D-Paint (best quality, Tencent NON-commercial).
        #     Bakes via the vendored `mvadapter` TexturePipeline + mesh_utils.
        #
        # ON MV-ADAPTER (the `else` branch below): the `mvadapter` package plays
        # TWO roles. (1) As a GENERATOR backend (_generate_texture / its own SDXL
        # multi-view pipeline) it is RETIRED — it failed the Janus/duplicated-face
        # test, is NOT offered in the registry options, and is reached only as a
        # fallback if `backend` is empty/unknown. (2) As a BAKE LIBRARY
        # (mvadapter.pipelines.pipeline_texture.TexturePipeline + utils.mesh_utils)
        # it is STILL REQUIRED — Hunyuan's Phase-3 bake imports it. So the vendored
        # `bundled_packages/mvadapter` MUST stay even though the MV-Adapter texturer
        # itself is no longer a user choice. Do not delete the package.
        #
        # MVPAINTER was removed entirely 2026-06-25 (commit after 81eaed5): its
        # weights are fine-tuned from a Tencent Hunyuan3D checkpoint (NOT the
        # claimed Apache-2.0 commercial-safe) and its quality was the lowest of the
        # three. Strictly dominated by Hunyuan (quality) + TRELLIS.2 (commercial-
        # clean). Only the shared _preprocess_mvpainter_reference() helper survives
        # (TRELLIS.2 + Hunyuan reuse it for the RGBA cutout — name kept for git
        # blame continuity; it's just "RGBA cutout prep", nothing MVPainter-specific).
        # ═══════════════════════════════════════════════════════════════════
        backend = model_dict.get("texture_backend") or _texture_backend(input_data)
        if input_data.get("texture_backend"):  # per-request override wins
            backend = str(input_data["texture_backend"]).lower().strip()
        if backend == "hunyuan":
            glb_data = _generate_texture_hunyuan(
                mesh_path, source_image, model_dict, input_data, temp_dir
            )
            return glb_data
        if backend == "trellis2":
            glb_data = _generate_texture_trellis2(
                mesh_path, source_image, model_dict, input_data, temp_dir
            )
            return glb_data

        # ═══════════════════════════════════════════════════════════════════
        # Phase 2: MV-Adapter multi-view generation  (default backend)
        # ═══════════════════════════════════════════════════════════════════
        t0 = _t.time()
        logger.info("Phase 2: MV-Adapter multi-view generation...")

        # Watchdog guard: nvdiffrast compile (~2-3 min) exceeds MMS's 120s
        # inference response timeout. It should already be compiled at load
        # (model_fn). If it's somehow NOT ready here (e.g. a warm worker that
        # loaded before this fix, or a load-time compile that failed), DO NOT
        # compile inline — that would block past the watchdog and reboot the
        # worker mid-job. Instead kick off a background compile and fail this
        # job fast with a clear, retryable message (the mesh still returns
        # untextured via the caller's fallback).
        if not _ensure_rasterizer(blocking=False):
            _ensure_nvdiffrast_background()  # only kicks if nvdiffrast is the choice; harmless otherwise
            msg = (f"Bake rasterizer ({_rasterizer_choice()}) is being prepared in "
                   "the background. Texture skipped this run — resubmit shortly.")
            logger.warning("Texture phase deferred: %s", msg)
            raise RuntimeError(msg)

        # Load MV-Adapter on-demand if not preloaded (low VRAM path)
        if mv_pipe is None:
            logger.info("Loading MV-Adapter on-demand...")
            mv_pipe, texture_pipe = _load_texture_models(code_dir, hf_token)

        from mvadapter.utils.mesh_utils import (
            get_orthogonal_camera, load_mesh, render, make_raster_context
        )

        # Set up cameras for 6 orthogonal views — MUST match the official
        # MV-Adapter convention exactly or the back view gets a front-face
        # (Janus problem). Base azimuth list [0,90,180,270,180,180]; the
        # geometry render applies the -90 "−y as front" offset, and the same
        # un-offset base list is passed to TexturePipeline (which re-applies -90).
        _MV_BASE_AZIMUTH = [0, 90, 180, 270, 180, 180]
        _MV_ELEVATION = [0, 0, 0, 0, 89.99, -89.99]
        cameras = get_orthogonal_camera(
            elevation_deg=_MV_ELEVATION,
            distance=[1.8] * 6,
            left=-0.55, right=0.55, bottom=-0.55, top=0.55,
            azimuth_deg=[x - 90 for x in _MV_BASE_AZIMUTH],
            device="cuda",
        )

        # Render mesh normals/positions as control signals for MV-Adapter.
        # CRITICAL: front_x_to_y=True must match TexturePipeline's front_x=True
        # default. Otherwise Phase 2 (geometry render) and Phase 3 (texture
        # projection) disagree by 90° about which mesh axis is "front", and the
        # face lands on the side of the head (Janus problem).
        # MV-Adapter render+generation resolution — chosen ADAPTIVELY per
        # instance to maximize face/texture detail without OOM. The binding
        # constraint is HOST RAM (the fp32 6-view VAE decode), not VRAM: 1536²
        # fp32 spiked a 32 GiB box to 99.9% → OOM. _choose_mv_resolution() reads
        # total host RAM and returns the highest safe tier (g6e.xlarge 32GiB →
        # 1280 w/ fp16 decode; 2xlarge 64GiB → 1536 w/ fp16; 4xlarge 128GiB →
        # 1536 fp32). Render and generation res MUST match so the geometry
        # control images align with the diffused views.
        _MV_RES, _MV_FP16_VAE = _choose_mv_resolution()
        logger.info("MV-Adapter resolution: %d² (fp16_vae_decode=%s, host RAM %.0f GiB)",
                    _MV_RES, _MV_FP16_VAE, _host_ram_total_gb() or -1)
        # If a higher tier needs the lighter fp16 VAE decode to fit host RAM,
        # switch the VAE off the fp32-forced path for this run. fp16 decode has a
        # small color-drift risk (the reason we default to fp32), but it halves
        # the host-RAM footprint of the 6-view decode — the trade that lets a
        # 32 GiB box exceed 1024². Below 1024 stays fp32 (no need).
        try:
            if _MV_FP16_VAE and mv_pipe is not None and hasattr(mv_pipe, "vae"):
                mv_pipe.vae.to(torch.float16)
                mv_pipe.vae.config.force_upcast = False
                logger.info("VAE set to fp16 decode for this resolution tier")
            elif mv_pipe is not None and hasattr(mv_pipe, "vae"):
                mv_pipe.vae.to(torch.float32)
                mv_pipe.vae.config.force_upcast = True
        except Exception as _vae_sw:
            logger.warning("Could not switch VAE decode dtype: %s", _vae_sw)
        ctx = make_raster_context(device="cuda")  # Kaolin default; nvdiffrast via ARTSMOKER_RASTERIZER
        mesh_obj = load_mesh(mesh_path, rescale=True, front_x_to_y=True, device="cuda")
        render_out = render(
            ctx, mesh_obj, cameras,
            height=_MV_RES, width=_MV_RES,
            render_attr=False,
            normal_background=0.0,
        )

        # Concatenate position + normal maps as control image (6 views, 6 channels)
        control_images = torch.cat([
            (render_out.pos + 0.5).clamp(0, 1),
            (render_out.normal / 2 + 0.5).clamp(0, 1),
        ], dim=-1).permute(0, 3, 1, 2)  # (6, 6, H, W)

        # DEBUG: save the geometry normal render per view (shows orientation)
        if _get_env("ARTSMOKER_TEXTURE_DEBUG", "") == "1":
            try:
                _nrm = (render_out.normal / 2 + 0.5).clamp(0, 1)  # (6, H, W, 3)
                _nrm_np = (_nrm.cpu().numpy() * 255).astype(np.uint8)
                _grid = _make_mv_grid([Image.fromarray(_nrm_np[i]) for i in range(_nrm_np.shape[0])])
                _save_debug_artifact(_grid, "01_geometry_normals")
            except Exception as _e:
                logger.warning("Debug normal render save failed: %s", _e)

        # Preprocess reference image to match MV-Adapter's training distribution:
        # background removed + composited on neutral gray (0.5). Passing a raw
        # image with an arbitrary background pushes the model off-distribution and
        # causes color casts (cyan/teal). This mirrors the official preprocess_image.
        ref_image = _preprocess_mv_reference(source_image, model_dict.get("rmbg_model"))
        _save_debug_artifact(ref_image, "02_reference")

        # Generate multi-view images conditioned on geometry + reference image.
        # GEOMETRY-DOMINANT CONDITIONING (subject-agnostic — applies to humans,
        # animals, vehicles, props alike). The control_image is the 3D geometry
        # render per view: it is the ONLY signal that knows which way each view
        # actually faces. The reference_image is a single 2D picture in ONE pose.
        # When reference is weighted too high, MV-Adapter follows the 2D
        # reference's orientation instead of the per-view geometry — e.g. it drew
        # the head TURNED to match the reference's slightly-turned face even on
        # the straight-on front camera, so the face projected onto the wrong side
        # of the head. The fix is to let the geometry control dominate placement
        # and use the reference only for appearance/colour:
        #   - control_conditioning_scale 1.2 -> 1.6: geometry firmly dictates
        #     WHERE features sit and which way each view faces.
        #   - reference_conditioning_scale 1.0 -> 0.7: reference informs look, not
        #     orientation — stops it overriding the geometry's facing.
        # This is generic: stronger geometry adherence keeps ANY object's 6 views
        # mutually consistent and correctly oriented, which is the precondition
        # for clean projection regardless of subject type. The strong control
        # also suppresses SDXL's 1280² duplication tendency (see
        # _choose_mv_resolution), letting us keep 1280² for detail.
        mv_result = mv_pipe(
            "best quality, crisp textures, vivid colors, detailed surface materials, game asset",
            height=_MV_RES, width=_MV_RES,
            num_inference_steps=50,
            guidance_scale=3.0,
            num_images_per_prompt=6,
            control_image=control_images,
            control_conditioning_scale=1.6,
            reference_image=ref_image,
            reference_conditioning_scale=0.7,
            negative_prompt="watermark, ugly, deformed, noisy, blurry, low quality, inconsistent, duplicated, extra limbs, distorted",
        )
        mv_images = mv_result.images
        elapsed_p2 = _t.time() - t0
        logger.info("Phase 2 complete in %.1fs — generated %d multi-view images", elapsed_p2, len(mv_images))

        # DEBUG: save the raw MV-Adapter views (before RMBG) — the source of truth
        if _get_env("ARTSMOKER_TEXTURE_DEBUG", "") == "1":
            try:
                _save_debug_artifact(_make_mv_grid(mv_images), "03_raw_views")
            except Exception as _e:
                logger.warning("Debug raw views save failed: %s", _e)

        # Remove background from multi-view images using RMBG
        # This ensures no background color bleeds into the texture projection
        rmbg_model = model_dict.get("rmbg_model")
        mask_images = []
        if rmbg_model is not None:
            cleaned_images = []
            for mv_img in mv_images:
                # Per-view foreground mask via the shared helper (RMBG/BiRefNet-agnostic).
                mask_np = _foreground_mask_np(rmbg_model, mv_img)
                mask_images.append(Image.fromarray(mask_np, mode='L'))
                # Composite on neutral gray (127) — matches MV-Adapter's training
                # background and avoids white edge halos bleeding into the atlas.
                # The mask is passed to projection so background is excluded anyway,
                # but gray keeps any soft-edge bleed neutral instead of bright.
                mv_np = np.array(mv_img)
                mask_3c = np.stack([mask_np] * 3, axis=-1) / 255.0
                gray_bg = np.ones_like(mv_np) * 127
                composited = (mv_np * mask_3c + gray_bg * (1 - mask_3c)).astype(np.uint8)
                cleaned_images.append(Image.fromarray(composited))
            mv_images = cleaned_images
            logger.info("Background removed from %d multi-view images", len(mv_images))

        # Save multi-view images as a packed grid (6 images side by side)
        mv_grid = _make_mv_grid(mv_images)
        mv_grid_path = os.path.join(temp_dir, "mv_grid.png")
        mv_grid.save(mv_grid_path)
        logger.info("Saved multi-view grid: %dx%d", mv_grid.width, mv_grid.height)
        _save_debug_artifact(mv_grid, "04_cleaned_views")

        # Save foreground masks for TexturePipeline projection
        mv_masks_path = None
        if mask_images:
            mv_masks_grid = _make_mv_grid_masks(mask_images)
            mv_masks_path = os.path.join(temp_dir, "mv_masks.png")
            mv_masks_grid.save(mv_masks_path)
            _save_debug_artifact(mv_masks_grid.convert("RGB"), "05_masks")


        # On low VRAM: unload MV-Adapter before Phase 3 (it must be re-loaded
        # on the next inference). On high VRAM we keep MV-Adapter resident
        # (preloaded), but still reclaim the allocator cache so Phase 3's
        # rasterization framebuffers and 4096² UV buffers have room.
        if not high_vram:
            logger.info("Low VRAM mode: unloading MV-Adapter for Phase 3...")
            del mv_pipe
            mv_pipe = None
            model_dict["mv_pipe"] = None
        else:
            # Drop references to the large Phase 2 tensors before reclaiming.
            try:
                del mv_result, control_images, render_out, mesh_obj, ctx
            except Exception:
                pass
        _reclaim_cuda_memory("after Phase 2 (before Phase 3)")

        # NOTE: We do NOT move MV-Adapter to CPU here. It's an fp16 diffusers
        # pipeline, and fp16 ops can't run on CPU — diffusers raises, which
        # previously crashed the worker right after Phase 2. It's also
        # unnecessary: parking the upscaler/inpainter during Phase 2 already
        # leaves ~35 GB free, and Phase 3's TexturePipeline loads fine alongside
        # the resident MV-Adapter on the 44.5 GB L40S.
        if texture_pipe is not None and _parked_tex_models:
            for _attr in _parked_tex_models:
                _m = getattr(texture_pipe, _attr, None)
                if _m is not None and hasattr(_m, "to"):
                    try:
                        _m.to("cuda")
                    except Exception as _e:
                        logger.warning("Could not restore texture_pipe.%s to GPU: %s", _attr, _e)
            logger.info("Restored texture models to GPU for Phase 3: %s", _parked_tex_models)
        _reclaim_cuda_memory("after restoring texture models (before Phase 3 bake)")

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

        # Maximum quality config: upscale views 2x + view-based inpainting for occlusions
        _has_upscaler = hasattr(texture_pipe, 'upscaler') and texture_pipe.upscaler is not None
        _has_inpainter = hasattr(texture_pipe, 'inpainter') and texture_pipe.inpainter is not None
        _rgb_config = ModProcessConfig(
            view_upscale=_has_upscaler,
            view_upscale_factor=2,
            inpaint_mode="view" if _has_inpainter else "uv",
        )
        logger.info("Phase 3 config: upscale=%s, inpaint=%s", _has_upscaler, _rgb_config.inpaint_mode)

        tex_output = texture_pipe(
            mesh_path=mesh_path,
            save_dir=temp_dir,
            save_name="textured",
            uv_unwarp=True,
            preprocess_mesh=True,
            uv_size=4096,
            rgb_path=mv_grid_path,
            rgb_process_config=_rgb_config,
            view_masks_path=mv_masks_path,
            view_inpaint_include_occlusion_boundary=True,
            poisson_reprojection=True,
            camera_azimuth_deg=_MV_BASE_AZIMUTH,
            camera_elevation_deg=_MV_ELEVATION,
            camera_distance=1.8,
            camera_ortho_scale=1.1,
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

        return glb_data

    finally:
        # Always restore TripoSG to GPU for the next inference (we parked it on
        # CPU before Phase 2 on BOTH VRAM tiers). RMBG was never parked, so it
        # stays on GPU. This runs whether texture generation succeeded or fell
        # back to untextured — the next job's Phase 1 expects TripoSG on CUDA.
        # Idempotent: .to("cuda") on an already-CUDA module is a no-op.
        if torch.cuda.is_available():
            try:
                if model_dict.get("_triposg_evicted"):
                    # Low host-RAM path: TripoSG was freed entirely. Rebuild it
                    # from the local snapshot (no re-download) so the next job's
                    # Phase 1 finds it on CUDA.
                    logger.info("Reloading evicted TripoSG to GPU for next inference...")
                    _reload_triposg(model_dict)
                else:
                    triposg_pipe = model_dict.get("pipe")
                    if triposg_pipe is not None:
                        logger.info("Restoring TripoSG to GPU for next inference...")
                        _move_module_to(triposg_pipe, "cuda")
            except Exception as _restore_err:
                logger.warning("Failed to restore TripoSG to GPU: %s", _restore_err)
            # On the preloaded high-VRAM path, the texture models (upscaler/
            # inpainter) are reused across jobs and rest on GPU. We park them on
            # CPU during Phase 2 — restore them so the next job finds them where
            # it expects. (MV-Adapter is NOT parked — fp16 can't go to CPU.)
            # Idempotent; covers success AND fallback paths.
            if high_vram:
                try:
                    _tp = model_dict.get("texture_pipe")
                    if _tp is not None:
                        for _attr in ("upscaler", "inpainter"):
                            _m = getattr(_tp, _attr, None)
                            if _m is not None and hasattr(_m, "to"):
                                _m.to("cuda")
                    logger.info("Restored MV-Adapter + texture models to GPU for next inference")
                except Exception as _re:
                    logger.warning("Failed to restore texture models to GPU: %s", _re)
            # Reclaim any texture-phase cache so the next job starts clean.
            _reclaim_cuda_memory("after texture phases (cleanup)")
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def _save_debug_artifact(pil_image, name):
    """Upload a diagnostic image to S3 under texture-debug/ for inspection.

    Controlled by ARTSMOKER_TEXTURE_DEBUG env var. Cleaned up after analysis.
    """
    if _get_env("ARTSMOKER_TEXTURE_DEBUG", "") != "1":
        return
    try:
        import io as _io, boto3 as _b3
        _bkt = _get_env("ARTSMOKER_CACHE_BUCKET") or _get_env("ARTSMOKER_S3_BUCKET") or ""
        if not _bkt:
            return
        buf = _io.BytesIO()
        pil_image.save(buf, format="PNG")
        buf.seek(0)
        _s3c = _b3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
        _s3c.upload_fileobj(buf, _bkt, f"artsmoker/custom-models/texture-debug/{name}.png")
        logger.info("Saved debug artifact: %s", name)
    except Exception as e:
        logger.warning("Debug artifact save failed (%s): %s", name, e)


def _foreground_mask_np(rmbg_model, pil_image):
    """Run the background-removal model on a PIL image → uint8 foreground mask
    (H×W, 0..255), resized back to the original image size.

    Centralizes the per-model differences so RMBG and BiRefNet are interchangeable
    (the model carries `_artsmoker_bg_backend`; default treated as birefnet):
      - RMBG-1.4:  input normalized /255 then ([0.5]*3,[1]*3); output at [0][0],
                   min/max-normalized.
      - BiRefNet:  input ImageNet-normalized ([0.485,0.456,0.406],[0.229,0.224,
                   0.225]); output at [-1].sigmoid().
    Returns None if rmbg_model is None.
    """
    if rmbg_model is None:
        return None
    backend = getattr(rmbg_model, "_artsmoker_bg_backend", "birefnet")
    orig_size = pil_image.size  # (W, H)
    orig_np = np.array(pil_image.convert("RGB"))
    from torchvision.transforms.functional import normalize as _tv_normalize
    x = torch.tensor(orig_np, dtype=torch.float32).permute(2, 0, 1)
    x = torch.nn.functional.interpolate(x.unsqueeze(0), size=[1024, 1024], mode="bilinear")
    x = torch.divide(x, 255.0)
    if backend == "rmbg":
        x = _tv_normalize(x, [0.5, 0.5, 0.5], [1.0, 1.0, 1.0])
    else:  # birefnet — ImageNet normalization
        x = _tv_normalize(x, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    # Match the model's dtype (BiRefNet card uses .half()); fall back to float.
    try:
        x = x.to("cuda").to(next(rmbg_model.parameters()).dtype)
    except Exception:
        x = x.to("cuda")
    with torch.no_grad():
        out = rmbg_model(x)
    if backend == "rmbg":
        result = out[0][0]
    else:
        result = out[-1].sigmoid()
    result = torch.squeeze(torch.nn.functional.interpolate(
        result, size=[orig_size[1], orig_size[0]], mode="bilinear"), 0)
    ma, mi = torch.max(result), torch.min(result)
    if ma > mi:
        result = (result - mi) / (ma - mi)
    mask_np = (result * 255).permute(1, 2, 0).float().cpu().numpy().astype(np.uint8)
    return np.squeeze(mask_np)


def _preprocess_mv_reference(pil_image, rmbg_model):
    """Prepare reference image for MV-Adapter: remove background, composite on gray.

    MV-Adapter is trained with subjects on a neutral gray (0.5) background.
    Passing a raw image with an arbitrary background causes color casts.
    Returns a square RGB PIL image on gray (127) background.
    """
    img = pil_image.convert("RGB")
    if rmbg_model is None:
        return img
    try:
        orig_np = np.array(img)
        mask = _foreground_mask_np(rmbg_model, img)  # (H, W) uint8, RMBG/BiRefNet-agnostic
        mask_3c = np.stack([mask] * 3, axis=-1) / 255.0
        gray_bg = np.ones_like(orig_np) * 127
        composited = (orig_np * mask_3c + gray_bg * (1 - mask_3c)).astype(np.uint8)
        return Image.fromarray(composited)
    except Exception as e:
        logger.warning("Reference preprocess failed (%s) — using raw image", e)
        return img


def _shadow_lift(pil_rgb, strength=1.0):
    """Lift crushed shadows on an RGB image so the baked texture isn't dark.

    The reference soldier (and similar assets) are dramatically-lit studio renders
    with deep shadows on a dark uniform; MVPainter reproduces that darkness and we
    bake it as albedo → a near-black texture. This applies a shadow/midtone LIFT
    (not a flat brighten, which washes highlights): a per-pixel gamma<1 weighted by
    how dark the pixel is, so shadows open up while highlights stay put. Operates on
    luminance-preserving ratios to avoid hue shift. strength in ~[0,1.5]; 0 = no-op.
    Gated by ARTSMOKER_REF_LIFT (default "0.7") / per-request "ref_lift".
    """
    import numpy as _np
    try:
        s = float(strength)
    except (TypeError, ValueError):
        s = 0.0
    if s <= 0:
        return pil_rgb
    arr = _np.asarray(pil_rgb.convert("RGB"), dtype=_np.float32) / 255.0
    lum = arr @ _np.array([0.2126, 0.7152, 0.0722], dtype=_np.float32)  # (H,W)
    # Shadow weight: 1 in blacks → 0 in highlights (smooth). Lift = gamma applied
    # proportionally to that weight, so only dark regions open up.
    w = (1.0 - lum) ** 2.0                       # emphasize the darkest pixels
    gamma = 1.0 - 0.5 * s * w                    # γ<1 brightens; scaled by darkness
    gamma = _np.clip(gamma, 0.35, 1.0)[..., None]
    lifted = _np.clip(arr, 1e-4, 1.0) ** gamma   # per-channel → preserves hue ratios
    # Gentle black-point raise so true 0 isn't pinned (adds a little base fill).
    lifted = lifted * (1.0 - 0.06 * s) + 0.06 * s
    out = _np.clip(lifted * 255.0, 0, 255).astype(_np.uint8)
    from PIL import Image as _PImg
    return _PImg.fromarray(out, "RGB")


def _preprocess_mvpainter_reference(pil_image, rmbg_model, lift_override=None):
    """Prepare the reference image as an RGBA cutout (bg-removed + optional shadow-lift).

    SHARED helper — despite the legacy name, this is NOT MVPainter-specific (MVPainter
    was removed 2026-06-25). It's the common RGBA-cutout prep reused by BOTH active
    texturers: TRELLIS.2 (`_generate_texture_trellis2`) and Hunyuan
    (`_generate_texture_hunyuan`), plus the full TRELLIS.2 image-to-3D predictor. Name
    retained for git-blame continuity; safe to rename to _preprocess_rgba_reference if
    ever desired (update the 3 call sites). Do NOT delete.

    Background: a texturer pipeline that runs its OWN preprocessing (recenter_img/white_out_
    background read the ALPHA channel to find the subject, then to_rgb_image
    composites the cutout onto a white background (its training distribution).
    So we must hand it a background-removed image WITH an alpha channel — not the
    gray-composited RGB that _preprocess_mv_reference produces for MV-Adapter
    (which crashed MVPainter's `for r,g,b,a in data` on a 3-channel image).
    Returns an RGBA PIL image (subject opaque, background transparent). Falls
    back to opaque RGBA if RMBG is unavailable.

    lift_override: when not None, use this shadow-lift strength instead of the
    ARTSMOKER_REF_LIFT env default. The TRELLIS.2 texturer passes 0 — the lift was
    tuned for MVPainter's crushed-dark albedo, but on TRELLIS.2 it washes out
    contrast (dull/hazy look), and TRELLIS.2 wants a clean cutout.
    """
    img = pil_image.convert("RGB")
    # Shadow-lift the reference BEFORE MVPainter so the generated views (and the
    # baked albedo) aren't crushed-dark. Default on at moderate strength; the dark
    # navy soldier reference is a heavily-lit render with deep shadows.
    _lift = str(lift_override) if lift_override is not None else _get_env("ARTSMOKER_REF_LIFT", "0.7")
    try:
        img_lifted = _shadow_lift(img, float(_lift))
        if float(_lift) > 0:
            logger.info("Reference shadow-lift applied (strength=%s)", _lift)
    except Exception as _le:
        logger.warning("Shadow-lift failed (%s) — using original reference", _le)
        img_lifted = img
    if rmbg_model is None:
        return img_lifted.convert("RGBA")
    try:
        orig_np = np.array(img_lifted)
        alpha = _foreground_mask_np(rmbg_model, img)  # mask from ORIGINAL (lift doesn't change silhouette)
        rgba = np.dstack([orig_np, alpha]).astype(np.uint8)  # (H, W, 4)
        return Image.fromarray(rgba, "RGBA")
    except Exception as e:
        logger.warning("MVPainter reference preprocess failed (%s) — using opaque RGBA", e)
        return img_lifted.convert("RGBA")


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


def _make_mv_grid_masks(mask_images):
    """Create a horizontal grid of grayscale mask images (packed side by side)."""
    if not mask_images:
        raise ValueError("No masks to grid")
    widths = [img.width for img in mask_images]
    height = mask_images[0].height
    total_width = sum(widths)
    grid = Image.new("L", (total_width, height))
    x_offset = 0
    for img in mask_images:
        grid.paste(img, (x_offset, 0))
        x_offset += img.width
    return grid


_PREDICTORS = {
    "text_to_image": _predict_text_to_image,
    "image_edit": _predict_image_edit,
    "autoregressive_image": _predict_autoregressive_image,
    "image_to_video": _predict_image_to_video,
    "image_to_3d": _predict_image_to_3d,
    "trellis2_image_to_3d": _predict_trellis2_full,
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
    global _model, _config, _model_dir
    _model_dir = model_dir
    library = _get_env("INFERENCE_LIBRARY", "diffusers")

    # DIAGNOSTIC: dump the MMS config so we can see the ACTUAL effective
    # default_response_timeout (the HF DLC writes /etc/sagemaker-mms.properties;
    # env-var overrides may or may not land there). Reveals the true request
    # timeout that governs long image_to_3d inferences.
    try:
        for _cfgp in ("/etc/sagemaker-mms.properties", "/etc/default-mms.properties"):
            if os.path.exists(_cfgp):
                with open(_cfgp) as _cf:
                    _content = _cf.read()
                logger.info("=== MMS CONFIG %s ===\n%s\n=== END %s ===", _cfgp, _content, _cfgp)
    except Exception as _ce:
        logger.warning("Could not read MMS config: %s", _ce)

    # Install system libraries needed by pymeshlab (OpenGL) on headless containers
    if library in ("image_to_3d", "trellis2_image_to_3d"):
        import subprocess as _sp
        _opengl_installed = False
        # Try apt-get first (Debian-based DLC)
        try:
            _sp.run(["apt-get", "update", "-qq"], timeout=60, capture_output=True)
            result = _sp.run(["apt-get", "install", "-y", "-qq", "libopengl0", "libgl1-mesa-glx", "libglib2.0-0"], timeout=120, capture_output=True)
            if result.returncode == 0:
                logger.info("Installed OpenGL libs via apt-get")
                _opengl_installed = True
            else:
                logger.info("apt-get failed (rc=%d), trying conda...", result.returncode)
        except Exception as _e:
            logger.info("apt-get unavailable (%s), trying conda...", _e)
        # Fallback: try conda (conda-based DLC)
        if not _opengl_installed:
            try:
                result = _sp.run(["conda", "install", "-y", "-q", "-c", "conda-forge", "mesalib", "libgl-cos7-x86_64"],
                                 timeout=120, capture_output=True)
                if result.returncode == 0:
                    logger.info("Installed OpenGL libs via conda")
                    _opengl_installed = True
                else:
                    logger.warning("conda install also failed — pymeshlab plugins will be limited (trimesh fallback active)")
            except Exception as _e2:
                logger.warning("conda unavailable — pymeshlab plugins will be limited: %s", _e2)
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
        logger.info("Input: prompt=%d chars, size=%sx%s, steps=%s, guidance=%s, seed=%s",
                     prompt_len, data.get("width", "?"), data.get("height", "?"),
                     data.get("num_inference_steps", "?"), data.get("guidance_scale", "?"),
                     data.get("seed", "?"))
        return data
    raise ValueError(f"Unsupported content type: {content_type}")


def _run_with_heartbeat(predictor, input_data, model_dict, predictor_type):
    """Run a long predictor on a daemon thread; main thread waits + heartbeats.

    Why: a multi-minute CPU-bound predictor (e.g. image_to_3d octree marching
    cubes, single-threaded ~10 min) blocks the MMS worker so it can't service
    SageMaker's /ping health checks → SageMaker marks the container Unhealthy
    and kills the instance mid-job (confirmed root cause). By running the work
    on a background thread and waiting via Thread.join(interval) in a loop, the
    main worker thread stays in a normal interruptible wait (the interpreter can
    service health/IPC), and we emit a heartbeat log so progress is visible.

    Also surfaces the real failure: the worker thread's exception is captured
    and re-raised here (instead of the worker silently dying), so any hidden
    error finally shows a traceback.
    """
    import threading
    import time as _time

    box = {}

    def _work():
        try:
            box["result"] = predictor(input_data, model_dict)
        except BaseException as e:  # noqa: BLE001 — capture everything to re-raise
            box["error"] = e

    th = threading.Thread(target=_work, name=f"predict-{predictor_type}", daemon=True)
    t0 = _time.time()
    th.start()
    # Wait in short slices so the main thread never blocks uninterruptibly.
    while th.is_alive():
        th.join(timeout=15.0)
        if th.is_alive():
            logger.info("…still working (%s): %.0fs elapsed", predictor_type, _time.time() - t0)
    if "error" in box:
        raise box["error"]
    return box.get("result")


def predict_fn(input_data, model_dict):
    """Run inference — routes to predictor by PREDICTOR_TYPE env var."""
    import time as _time
    t0 = _time.time()

    # Dev hot-reload: if a changed code overlay is staged in S3, apply it
    # (overwrites code/, purges bundled packages, re-binds predictors) before
    # dispatch — so updated _predict_* logic AND bundled-package edits run
    # against the already-warm model. No-op in prod (flag absent).
    _maybe_apply_hotreload()

    # Resolve the predictor AFTER any reload so we pick up the refreshed dict.
    predictor_type = _get_env("PREDICTOR_TYPE", "text_to_image")
    predictor = _PREDICTORS.get(predictor_type)
    if not predictor:
        raise ValueError(f"Unknown PREDICTOR_TYPE: {predictor_type}. Available: {list(_PREDICTORS.keys())}")

    # Log GPU memory before inference
    if torch.cuda.is_available():
        alloc = torch.cuda.memory_allocated(0) / (1024**3)
        reserved = torch.cuda.memory_reserved(0) / (1024**3)
        free_gb = (torch.cuda.mem_get_info(0)[0] / (1024**3)) if hasattr(torch.cuda, "mem_get_info") else 0
        logger.info("GPU memory before inference: %.2f GB allocated, %.2f GB reserved (%.1f GB free)",
                     alloc, reserved, free_gb)

    try:
        # Long-running predictors (image_to_3d: ~10 min single-threaded octree
        # marching cubes) block the worker so hard that the container can't
        # answer SageMaker's /ping health checks → SageMaker marks it Unhealthy
        # and kills the instance mid-job. Run such predictors on a background
        # thread and have THIS thread wait with a periodic heartbeat, so the
        # worker process stays in a normal Python wait (responsive) instead of
        # buried in a non-yielding native call. Fast predictors run inline.
        _LONG_RUNNING = {"image_to_3d", "trellis2_image_to_3d"}
        if predictor_type in _LONG_RUNNING:
            result = _run_with_heartbeat(predictor, input_data, model_dict, predictor_type)
        else:
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
