"""Shared Amazon Bedrock client with connection pooling and model routing."""

import base64
import json
import logging

import boto3
from botocore.config import Config as BotoConfig

from backend.config import settings

logger = logging.getLogger(__name__)

_boto_config = BotoConfig(
    retries={"max_attempts": 3, "mode": "adaptive"},
    max_pool_connections=10,
)

# Lazy-initialised clients keyed by region
_clients: dict[str, boto3.client] = {}


def _get_client(region: str):
    if region not in _clients:
        session_kwargs = {}
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile
        session = boto3.Session(region_name=region, **session_kwargs)
        _clients[region] = session.client(
            "bedrock-runtime", config=_boto_config
        )
    return _clients[region]


def get_models_client():
    """Client for Claude / Stability models (us-west-2)."""
    return _get_client(settings.aws_region_models)


def get_images_client():
    """Client for Nova Canvas / Titan Image / Nova Sonic (us-east-1)."""
    return _get_client(settings.aws_region_images)


# ── Startup validation ────────────────────────────────────────────────────

def validate_aws_credentials() -> dict:
    """Validate AWS credentials and Bedrock model access on startup.

    Returns a dict with check results:
        {
            "credentials": True/False,
            "identity": "arn:aws:...",
            "models_region": True/False,
            "images_region": True/False,
            "errors": ["..."]
        }
    """
    result = {
        "credentials": False,
        "identity": None,
        "models_region": False,
        "images_region": False,
        "errors": [],
    }

    # 1. Check credentials resolve (STS GetCallerIdentity)
    try:
        session_kwargs = {}
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile
        session = boto3.Session(**session_kwargs)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        result["credentials"] = True
        result["identity"] = identity.get("Arn", "unknown")
        logger.info("AWS credentials valid: %s", result["identity"])
    except Exception as exc:
        msg = f"AWS credentials not configured or invalid: {exc}"
        result["errors"].append(msg)
        logger.error(msg)
        return result

    # 2. Probe the registry-configured LLMs — BOTH tiers (fast_llm + complex_llm),
    # since they're typically different models with different access/params. Each
    # is a cheap 1-token Converse call. inferenceConfig is built via the SAME
    # registry-driven gate as runtime (_build_inference_config) so a model that
    # deprecates `temperature` (e.g. Opus 4.8) doesn't make this probe fail.
    # result["probes"] records each for an honest, representative summary line.
    result.setdefault("probes", [])
    _llm_ok = True
    for _tier, _label in (("fast", "Fast LLM"), ("complex", "Complex LLM")):
        _id, _region = "?", "?"
        try:
            _id, _region = _pick_llm_model(_tier)
            if not _id:
                continue
            # Probe via the model's RESOLVED path: Converse models use the boto3
            # 1-token call (registry-driven param gate); Mantle-only models
            # (e.g. GPT-5.x) use a 1-token call on the right Mantle API.
            _endpoint, _api = _resolve_invoke_path(_id)
            if _endpoint == "bedrock-mantle":
                _invoke_llm_mantle(_id, _api, "hi", max_tokens=1, region=_region)
                _probe_endpoint = "bedrock-mantle"
            else:
                _client = _get_client(_region)
                _client.converse(
                    modelId=_id,
                    messages=[{"role": "user", "content": [{"text": "hi"}]}],
                    inferenceConfig=_build_inference_config(_id, 1, 0.0),
                )
                _probe_endpoint = "bedrock-runtime"
            result["probes"].append({"role": _label, "model_id": _id, "region": _region,
                                     "endpoint": _probe_endpoint, "ok": True})
        except Exception as exc:
            _llm_ok = False
            result["probes"].append({"role": _label, "model_id": _id, "region": _region, "ok": False})
            result["errors"].append(f"Amazon Bedrock {_label} check failed: {exc}")
    result["models_region"] = _llm_ok

    # 3. Check Bedrock access for first enabled image model from registry
    img_model_id, img_region = "?", "?"
    try:
        from backend.services.model_registry import get_enabled_image_model_keys_sorted, get_image_model
        img_keys = get_enabled_image_model_keys_sorted()
        if img_keys:
            img_cfg = get_image_model(img_keys[0])
            img_region = img_cfg.get("region", "us-east-1")
            img_model_id = img_cfg.get("model_id", "")
            client = _get_client(img_region)
            # Light check — just confirm we can reach the model endpoint
            client.invoke_model(
                modelId=img_model_id,
                contentType="application/json",
                accept="application/json",
                body='{"prompt":"test","output_format":"png","aspect_ratio":"1:1"}',
            )
            result["images_region"] = True
            result["probes"].append({"role": "Image model", "model_id": img_model_id,
                                     "region": img_region, "ok": True})
        else:
            result["images_region"] = False
            result["errors"].append("No enabled image models in registry.")
    except client.exceptions.ValidationException:
        # ValidationException means we reached the model — access works
        result["images_region"] = True
        result["probes"].append({"role": "Image model", "model_id": img_model_id,
                                 "region": img_region, "ok": True})
    except Exception as exc:
        result["probes"].append({"role": "Image model", "model_id": img_model_id,
                                 "region": img_region, "ok": False})
        result["errors"].append(f"Amazon Bedrock image model check failed: {exc}")

    return result


# ── Claude helpers ────────────────────────────────────────────────────────

def _pick_llm_model(complexity: str) -> tuple[str, str]:
    """Pick the LLM model ID and region for the given complexity level.

    Reads from the model registry (categories.fast_llm / complex_llm).
    The actual model can be Claude, Llama, Mistral, or any Bedrock-compatible
    LLM — configured by the user via the registry.
    Returns (model_id, region).
    """
    from backend.services.model_registry import get_category
    if complexity == "complex":
        cat = get_category("complex_llm")
    else:
        cat = get_category("fast_llm")
    model_id = cat.get("current", "")
    region = cat.get("region", settings.aws_region_models)
    if not model_id:
        # No model configured — check code defaults in registry before giving up
        from backend.services.model_registry import get_registry
        reg = get_registry()
        cat_name = "complex_llm" if complexity == "complex" else "fast_llm"
        default_cat = reg.get("categories", {}).get(cat_name, {})
        model_id = default_cat.get("current", "")
        region = default_cat.get("region", settings.aws_region_models)
        if not model_id:
            logger.warning("No %s model configured — run Sync from AWS in Model Settings", cat_name)
    return (model_id, region)


def _resolve_invoke_path(model_id: str) -> tuple[str, str]:
    """Resolve (invoke_endpoint, invoke_api) for a model from the registry.

    Reads the per-model ``invoke_endpoint``/``invoke_api`` that Sync stamped on
    the ``chat_models`` entry (matched by model_id, with/without the ``us.``
    profile prefix). Defaults to ("bedrock-runtime", "converse") when the model
    isn't found or carries no routing — i.e. the Converse path stays the default
    for everything not explicitly marked otherwise (Converse-first policy).
    """
    try:
        from backend.services.model_registry import get_registry
        mid = model_id or ""
        bare = mid[3:] if mid.startswith("us.") else mid
        for cfg in (get_registry().get("chat_models", {}) or {}).values():
            cmid = cfg.get("model_id", "")
            cbare = cmid[3:] if cmid.startswith("us.") else cmid
            if cmid == mid or cbare == bare:
                ep = cfg.get("invoke_endpoint")
                api = cfg.get("invoke_api")
                if ep and api:
                    return ep, api
                break
    except Exception:
        pass
    return "bedrock-runtime", "converse"


def _get_fallback_llm() -> tuple[str, str]:
    """Get the fallback LLM model ID and region from the registry."""
    from backend.services.model_registry import get_category
    cat = get_category("fallback_llm")
    model_id = cat.get("current", "")
    region = cat.get("region", settings.aws_region_models)
    if not model_id:
        # Try fast_llm as fallback-of-fallback
        fast = get_category("fast_llm")
        model_id = fast.get("current", "")
        region = fast.get("region", settings.aws_region_models)
    return (model_id, region)


def _model_supports_temperature(model_id: str) -> bool:
    """Whether a model accepts the Converse `temperature` inferenceConfig param.

    REGISTRY-DRIVEN (not a hardcoded model list): looks the model up in
    chat_models by model_id/model_arn and reads its declared capability —
    `supports_temperature: false` or `temperature` in `deprecated_params[]` →
    omit it. The AWS sync captures these per-model so new models that deprecate
    params work with NO code change. Only when the registry is silent do we fall
    back to a minimal built-in heuristic (newer Claude tiers deprecate it), so the
    behaviour is safe today and self-correcting once sync populates the field.
    """
    try:
        from backend.services.model_registry import get_registry
        mid = model_id or ""
        for cfg in (get_registry().get("chat_models", {}) or {}).values():
            if cfg.get("model_id") == mid or cfg.get("model_arn", "").endswith(mid):
                if cfg.get("supports_temperature") is False:
                    return False
                if "temperature" in (cfg.get("deprecated_params") or []):
                    return False
                if cfg.get("supports_temperature") is True:
                    return True
                break  # found the model but it declares nothing → use heuristic
    except Exception:
        pass
    # Heuristic fallback (registry silent): Claude Opus 4.8+ deprecate temperature.
    _no_temperature = ("claude-opus-4-8",)
    return not any(tok in (model_id or "") for tok in _no_temperature)


def _build_inference_config(model_id: str, max_tokens: int, temperature: float) -> dict:
    """Build the Converse inferenceConfig, omitting params the model rejects
    (registry-driven via _model_supports_temperature)."""
    cfg = {"maxTokens": max_tokens}
    if _model_supports_temperature(model_id):
        cfg["temperature"] = temperature
    return cfg


def _img_mime(img_bytes: bytes) -> str:
    """Sniff an image's MIME type from its magic bytes (for Mantle payloads)."""
    if img_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if img_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if img_bytes[:4] == b"GIF8":
        return "image/gif"
    if img_bytes[:4] == b"RIFF" and img_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _invoke_llm_mantle(
    model_id: str,
    invoke_api: str,
    prompt: str,
    *,
    system: str = "",
    images: list[bytes] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    region: str = "",
) -> str:
    """Invoke an LLM over the bedrock-mantle endpoint (Chat Completions /
    Responses / Messages), converting our prompt+images to the right shape.

    Isolated from the Converse path; reached only when a model's resolved
    invoke_endpoint is bedrock-mantle. Cost tracking mirrors the Converse path
    where usage is available.
    """
    from backend.services import mantle_client as mc

    # Capture token usage so Mantle-routed model inference (GPT-5.x, Mythos, …) is
    # cost-tracked exactly like the Converse path — previously the usage object was
    # discarded and all Mantle spend was silently recorded as $0.
    usage: dict = {}

    # Build the user content. OpenAI (chat/responses) and Anthropic (messages)
    # use different content shapes for images.
    if invoke_api == "messages":
        content: list[dict] = []
        for img in (images or []):
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": _img_mime(img),
                           "data": base64.b64encode(img).decode()},
            })
        content.append({"type": "text", "text": prompt})
        text = mc.invoke_messages(
            model_id, [{"role": "user", "content": content}],
            region=region, system=system, max_tokens=max_tokens,
            temperature=temperature, usage_out=usage,
        )
    else:
        # OpenAI-style content parts (chat_completions + responses).
        parts: list[dict] = []
        for img in (images or []):
            b64 = base64.b64encode(img).decode()
            parts.append({"type": "image_url",
                          "image_url": {"url": f"data:{_img_mime(img)};base64,{b64}"}})
        parts.append({"type": "text", "text": prompt})
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": parts if images else prompt})
        if invoke_api == "responses":
            text = mc.invoke_responses(
                model_id, messages, region=region, max_output_tokens=max_tokens,
                usage_out=usage,
            )
        else:  # chat_completions
            text = mc.invoke_chat_completions(
                model_id, messages, region=region, max_tokens=max_tokens,
                temperature=temperature, usage_out=usage,
            )

    # Record cost from captured usage (mirrors the Converse path).
    try:
        in_tok = int(usage.get("input_tokens", 0) or 0)
        out_tok = int(usage.get("output_tokens", 0) or 0)
        if in_tok or out_tok:
            from backend.services.cost_tracker import add_cost, compute_llm_cost
            cost = compute_llm_cost(model_id, in_tok, out_tok)
            if cost > 0:
                add_cost("llm", cost, f"{model_id} (mantle): {in_tok} in, {out_tok} out")
    except Exception as e:
        logger.debug("Mantle cost tracking failed for %s: %s", model_id, e)

    return text


def invoke_llm(
    prompt: str,
    *,
    system: str = "",
    complexity: str = "fast",
    images: list[bytes] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Invoke an LLM via Bedrock Converse API.

    The model used is determined by the registry (categories.fast_llm or
    complex_llm). Can be Claude, Llama, Mistral, or any Converse-compatible
    model — the user configures this via Model Settings.

    Args:
        prompt: The text prompt.
        system: Optional system prompt to guide behavior.
        complexity: "fast" → fast_llm category, "complex" → complex_llm category.
        images: Optional list of PNG image bytes to include as vision input.
        max_tokens: Max response tokens.
        temperature: Sampling temperature.

    Returns:
        The text response from the LLM.
    """
    model_id, region = _pick_llm_model(complexity)

    # Route by the model's resolved invoke path (Converse-first; Mantle only for
    # models Converse can't reach — e.g. OpenAI GPT-5.x via Responses, Claude
    # Mythos via Messages). The boto3 Converse path below is unchanged and stays
    # the default for everything that supports it.
    invoke_endpoint, invoke_api = _resolve_invoke_path(model_id)
    if invoke_endpoint == "bedrock-mantle":
        return _invoke_llm_mantle(
            model_id, invoke_api, prompt,
            system=system, images=images, max_tokens=max_tokens,
            temperature=temperature, region=region,
        )

    client = _get_client(region)

    content_blocks: list[dict] = []
    if images:
        for img_bytes in images:
            if img_bytes[:3] == b'\xff\xd8\xff':
                fmt = "jpeg"
            elif img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                fmt = "png"
            elif img_bytes[:4] == b'GIF8':
                fmt = "gif"
            elif img_bytes[:4] == b'RIFF' and img_bytes[8:12] == b'WEBP':
                fmt = "webp"
            else:
                fmt = "png"
            content_blocks.append({
                "image": {
                    "format": fmt,
                    "source": {"bytes": img_bytes},
                }
            })
    content_blocks.append({"text": prompt})

    messages = [{"role": "user", "content": content_blocks}]

    converse_kwargs = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": _build_inference_config(model_id, max_tokens, temperature),
    }
    if system:
        converse_kwargs["system"] = [{"text": system}]

    try:
        response = client.converse(**converse_kwargs)
        text = response["output"]["message"]["content"][0]["text"]
        # Track LLM cost
        usage = response.get("usage", {})
        in_tok = usage.get("inputTokens", 0)
        out_tok = usage.get("outputTokens", 0)
        if in_tok or out_tok:
            from backend.services.cost_tracker import add_cost, compute_llm_cost
            llm_cost = compute_llm_cost(model_id, in_tok, out_tok)
            add_cost("llm", llm_cost, f"{model_id}: {in_tok} in, {out_tok} out")
        return text
    except client.exceptions.AccessDeniedException:
        fallback_id, fallback_region = _get_fallback_llm()
        logger.warning(
            "Access denied for %s, falling back to %s in %s",
            model_id, fallback_id, fallback_region,
        )
        fallback_client = _get_client(fallback_region)
        fallback_kwargs = {
            "modelId": fallback_id,
            "messages": messages,
            "inferenceConfig": _build_inference_config(fallback_id, max_tokens, temperature),
        }
        if system:
            fallback_kwargs["system"] = [{"text": system}]
        response = fallback_client.converse(**fallback_kwargs)
        text = response["output"]["message"]["content"][0]["text"]
        usage = response.get("usage", {})
        in_tok = usage.get("inputTokens", 0)
        out_tok = usage.get("outputTokens", 0)
        if in_tok or out_tok:
            from backend.services.cost_tracker import add_cost, compute_llm_cost
            llm_cost = compute_llm_cost(fallback_id, in_tok, out_tok)
            add_cost("llm", llm_cost, f"{fallback_id} (fallback): {in_tok} in, {out_tok} out")
        return text


# ── Generic image generation (registry-driven) ──────────────────────────

def _set_nested(obj: dict, path: str, value):
    """Set a value at a dot-path in a nested dict. E.g. 'a.b.c' sets obj['a']['b']['c']."""
    keys = path.split(".")
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = value


def _get_nested(obj: dict, path: str):
    """Get a value from a dot-path, supporting array indexing like 'images[0]'."""
    import re as _re
    for part in path.split("."):
        m = _re.match(r"(\w+)\[(\d+)\]", part)
        if m:
            obj = obj[m.group(1)][int(m.group(2))]
        else:
            obj = obj[part]
    return obj


def invoke_image_model(
    model_key: str,
    prompt: str = "",
    *,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    quality: str | None = None,
    region_override: str | None = None,
    source_image: bytes | None = None,
    mask_image: bytes | None = None,
    mask_prompt: str | None = None,
    extra_params: dict | None = None,
) -> bytes:
    """Generic image model invoker — handles Bedrock and custom Amazon SageMaker models.

    For custom models (model_source=custom_hosted), routes to Amazon SageMaker.
    For Bedrock models, uses the format family to construct the request.

    Works for text-to-image, inpainting, outpainting, erase, style transfer,
    and all other image services defined in the registry. The format family
    determines which fields are used.

    Args:
        model_key: Registry key (e.g. 'nova_canvas', 'stability_inpaint')
        prompt: Text prompt (optional for erase/remove-bg services)
        negative_prompt: Exclusion terms
        width/height: Output dimensions (for text-to-image models)
        seed: Random seed
        quality: Quality tier override
        region_override: AWS region override
        source_image: Input image as PNG bytes (for inpaint/outpaint/edit services)
        mask_image: Mask image as PNG bytes (white = area to edit)
        mask_prompt: Natural language mask description (Nova Canvas alternative to mask_image)
        extra_params: Additional parameters (e.g. outpaint directions, control_strength)

    Returns PNG image bytes.
    """
    from backend.services.model_registry import get_image_model, get_registry
    import copy

    model_config = get_image_model(model_key)
    if not model_config:
        raise ValueError(f"Unknown image model: {model_key}")

    # Route custom Amazon SageMaker models to the invoker
    if model_config.get("model_source") == "custom_hosted":
        from backend.services.sagemaker_invoker import invoke_custom_image_model
        return invoke_custom_image_model(
            model_key, prompt, width=width, height=height, seed=seed,
            negative_prompt=negative_prompt,
        )

    model_id = model_config["model_id"]
    region = region_override or model_config["region"]
    family_name = model_config.get("format_family", "")

    registry = get_registry()
    family = registry.get("format_families", {}).get(family_name)
    if not family:
        raise ValueError(f"Unknown format family '{family_name}' for model '{model_key}'")

    # Start with the family body template and merge model-specific overrides
    body = copy.deepcopy(family["body_template"])
    extra = model_config.get("extra_body", {})
    _deep_merge(body, extra)

    # Apply quality tier override if specified
    if quality:
        quality_options = model_config.get("quality_options", [])
        for qopt in quality_options:
            if qopt.get("value") == quality and qopt.get("body_override"):
                _deep_merge(body, qopt["body_override"])
                break

    # Set prompt (if the family has a prompt path and we have a prompt)
    if prompt and family.get("prompt_path"):
        _set_nested(body, family["prompt_path"], prompt)

    # Set negative prompt
    if negative_prompt and family.get("negative_prompt_path"):
        _set_nested(body, family["negative_prompt_path"], negative_prompt)

    # Set source image (for inpaint, outpaint, erase, style services)
    if source_image and family.get("image_path"):
        _set_nested(body, family["image_path"], base64.b64encode(source_image).decode("ascii"))

    # Set mask image (for inpaint, erase services)
    if mask_image and family.get("mask_path"):
        _set_nested(body, family["mask_path"], base64.b64encode(mask_image).decode("ascii"))
    elif mask_image and family.get("mask_image_path"):
        _set_nested(body, family["mask_image_path"], base64.b64encode(mask_image).decode("ascii"))

    # Set mask prompt (Nova Canvas alternative to mask image)
    if mask_prompt and family.get("mask_prompt_path"):
        _set_nested(body, family["mask_prompt_path"], mask_prompt)

    # Set dimensions or aspect ratio (only for text-to-image families)
    dims_mode = family.get("dimensions_mode")
    if dims_mode == "aspect_ratio":
        body["aspect_ratio"] = _dimensions_to_aspect_ratio(width, height)
    elif dims_mode == "pixels":
        dim_paths = family.get("dimensions_paths", {})
        if dim_paths.get("width"):
            _set_nested(body, dim_paths["width"], width)
        if dim_paths.get("height"):
            _set_nested(body, dim_paths["height"], height)

    # Set seed
    if seed is not None and family.get("seed_path"):
        _set_nested(body, family["seed_path"], seed)

    # Set extra parameters (outpaint directions, control_strength, etc.)
    if extra_params:
        for k, v in extra_params.items():
            body[k] = v

    # Invoke
    client = _get_client(region)
    label = model_config.get("label", model_key)
    logger.info("Invoking %s (%s) in %s: prompt=%d chars, seed=%s",
                label, model_id, region, len(prompt), seed)

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())

    # Track image model cost
    purpose = model_config.get("model_purpose", "text_to_image")
    image_cost = model_config.get("base_price_usd", 0) or 0
    if image_cost > 0:
        from backend.services.cost_tracker import add_cost
        component = "image_generation" if purpose == "text_to_image" else f"image_{purpose}"
        add_cost(component, image_cost, f"{label} × 1")

    # Extract image from response
    try:
        image_data = _get_nested(result, family["response_image_path"])
    except (KeyError, IndexError, TypeError):
        error_msg = result.get("error", result.get("message", str(result)))
        logger.error("%s returned no image: %s", label, error_msg)
        raise RuntimeError(f"{label} generation failed: {error_msg}")

    return base64.b64decode(image_data)


def _deep_merge(base: dict, override: dict):
    """Recursively merge override into base (mutates base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# Backward-compatible alias — existing imports of invoke_claude still work
invoke_claude = invoke_llm

def _dimensions_to_aspect_ratio(width: int, height: int) -> str:
    """Convert pixel dimensions to the nearest Stability AI aspect ratio string."""
    ratio = width / height
    # Stability supports: 1:1, 16:9, 9:16, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21
    aspect_ratios = [
        (1.0, "1:1"), (16/9, "16:9"), (9/16, "9:16"),
        (3/2, "3:2"), (2/3, "2:3"), (4/5, "4:5"), (5/4, "5:4"),
        (21/9, "21:9"), (9/21, "9:21"),
    ]
    closest = min(aspect_ratios, key=lambda x: abs(x[0] - ratio))
    return closest[1]


