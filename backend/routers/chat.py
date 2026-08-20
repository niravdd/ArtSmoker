"""Chat Studio router — multi-model LLM chat with streaming, sessions, and cost tracking."""

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from backend.config import settings
from backend.services.prompt_templates import get_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

CHAT_DIR = settings.data_dir / "chat"


# ── Request models ────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    model_id: str
    region: str | None = None
    messages: list[dict]  # [{role, content}]
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float | None = None


class SessionCreate(BaseModel):
    title: str = "New Chat"
    model_id: str = ""
    system_prompt: str = ""


class SessionUpdate(BaseModel):
    title: str | None = None
    model_id: str | None = None
    region_override: str | None = None
    system_prompt: str | None = None
    messages: list[dict] | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_cost_usd: float | None = None


class CompactRequest(BaseModel):
    session_id: str
    keep_recent: int = 6  # Keep last N messages verbatim


# ── Mantle streaming (OpenAI-compatible endpoint) ───────────────────────────

def _chat_stream_mantle(req: "ChatMessageRequest", model_id: str, region: str, invoke_api: str):
    """Stream a chat response from a bedrock-mantle model via the OpenAI SDK.

    Emits the SAME SSE event shapes as the Converse path (delta / metadata /
    stop / error) so the frontend needs no changes. Used only for mantle-only
    models (resolved invoke_endpoint == bedrock-mantle). Chat Completions and
    Responses stream natively; the Anthropic Messages API path streams via its
    own SSE — for simplicity we use non-streaming Messages and emit one delta.
    """
    from backend.services.cost_tracker import compute_llm_cost, reset_costs, add_cost
    reset_costs()

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    # Normalize messages to OpenAI shape (role/content strings; structured
    # content is passed through). System prompt becomes a system message.
    msgs = []
    if req.system_prompt and invoke_api != "messages":
        msgs.append({"role": "system", "content": req.system_prompt})
    for m in req.messages:
        msgs.append({"role": m.get("role", "user"), "content": m.get("content", "")})

    def generate():
        start = time.time()
        full = ""
        in_tok = 0
        out_tok = 0
        try:
            from backend.services import mantle_client as mc
            client = mc._get_openai_client(region)
            if invoke_api == "responses":
                # include_usage → the terminal event carries token counts.
                stream = client.responses.create(
                    model=model_id, input=msgs,
                    max_output_tokens=req.max_tokens, store=False, stream=True)
                for event in stream:
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str) and delta:
                        full += delta
                        yield sse({"type": "delta", "text": delta})
                    # Final "response.completed" event exposes cumulative usage.
                    ev_resp = getattr(event, "response", None)
                    ev_usage = getattr(ev_resp, "usage", None) if ev_resp else None
                    if ev_usage is not None:
                        in_tok = getattr(ev_usage, "input_tokens", 0) or 0
                        out_tok = getattr(ev_usage, "output_tokens", 0) or 0
            elif invoke_api == "messages":
                # Non-streaming Messages → single delta (keeps deps minimal).
                _u = {}
                text = mc.invoke_messages(
                    model_id, [{"role": m["role"], "content": m["content"]} for m in msgs],
                    region=region, system=req.system_prompt or "",
                    max_tokens=req.max_tokens, temperature=req.temperature, usage_out=_u)
                full = text
                in_tok = _u.get("input_tokens", 0)
                out_tok = _u.get("output_tokens", 0)
                if text:
                    yield sse({"type": "delta", "text": text})
            else:  # chat_completions
                kwargs = {"model": model_id, "messages": msgs,
                          "max_completion_tokens": req.max_tokens, "stream": True,
                          "stream_options": {"include_usage": True}}
                if req.temperature is not None:
                    kwargs["temperature"] = req.temperature
                stream = client.chat.completions.create(**kwargs)
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        piece = chunk.choices[0].delta.content
                        full += piece
                        yield sse({"type": "delta", "text": piece})
                    # The usage-only final chunk (no choices) carries token counts.
                    cu = getattr(chunk, "usage", None)
                    if cu is not None:
                        in_tok = getattr(cu, "prompt_tokens", 0) or 0
                        out_tok = getattr(cu, "completion_tokens", 0) or 0

            latency_ms = round((time.time() - start) * 1000)
            # Real cost from captured usage (was hardcoded to 0 tokens → $0).
            cost = compute_llm_cost(model_id, in_tok, out_tok)
            try:
                if cost > 0:
                    from backend.services.cost_tracker import add_cost
                    add_cost("chat_llm", cost, f"{model_id} (mantle): {in_tok} in, {out_tok} out")
            except Exception:
                pass
            yield sse({"type": "metadata", "input_tokens": in_tok, "output_tokens": out_tok,
                       "latency_ms": latency_ms, "cost_usd": cost,
                       "model_id": model_id, "region": region,
                       "endpoint": "bedrock-mantle", "api": invoke_api})
            yield sse({"type": "stop", "stop_reason": "end_turn"})
        except Exception as exc:
            logger.error("Mantle chat stream error (%s/%s): %s", model_id, invoke_api, exc)
            yield sse({"type": "error", "detail": f"Mantle error: {str(exc)[:300]}"})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Streaming chat ────────────────────────────────────────────────────────

@router.post("/stream")
async def chat_stream(req: ChatMessageRequest):
    """Send messages to an LLM and stream the response via SSE.

    Uses Bedrock ConverseStream for real-time token streaming.
    Returns SSE events: delta (text chunks), metadata (tokens, cost, latency), error.
    """
    from backend.services.bedrock_client import _get_client
    from backend.services.cost_tracker import compute_llm_cost, reset_costs, add_cost
    reset_costs()

    if not req.messages:
        raise HTTPException(400, detail="Messages are required")

    model_id = req.model_id
    region = req.region or _resolve_chat_region(model_id)

    # Route by the model's resolved invoke path. Mantle-only models (e.g. OpenAI
    # GPT-5.x via Responses, GLM/Grok via Chat Completions, Claude Mythos via
    # Messages) can't use ConverseStream — stream them via the Mantle endpoint.
    # Everything Converse-capable keeps the unchanged boto3 path below.
    from backend.services.bedrock_client import _resolve_invoke_path
    _invoke_endpoint, _invoke_api = _resolve_invoke_path(model_id)
    if _invoke_endpoint == "bedrock-mantle":
        return _chat_stream_mantle(req, model_id, region, _invoke_api)

    client = _get_client(region)

    # Build Converse messages
    converse_messages = []
    for msg in req.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, str):
            converse_messages.append({"role": role, "content": [{"text": content}]})
        elif isinstance(content, list):
            # Already structured (e.g., with images)
            converse_messages.append({"role": role, "content": content})

    converse_kwargs = {
        "modelId": model_id,
        "messages": converse_messages,
        "inferenceConfig": {
            "maxTokens": req.max_tokens,
            "temperature": req.temperature,
        },
    }
    if req.top_p is not None:
        converse_kwargs["inferenceConfig"]["topP"] = req.top_p
    if req.system_prompt:
        converse_kwargs["system"] = [{"text": req.system_prompt}]

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    # Content safety guidance shown to users when content is blocked
    _BLOCKED_GUIDANCE = (
        "\n\n**What you can try:**\n"
        "- Rephrase your request to focus on the specific information you need\n"
        "- Remove explicit, violent, or otherwise sensitive language\n"
        "- Break complex requests into smaller, more specific questions\n"
        "- Try a different model — safety thresholds vary between providers"
    )

    def generate():
        start_time = time.time()
        full_text = ""

        try:
            response = client.converse_stream(**converse_kwargs)
            stream = response.get("stream", [])

            for event in stream:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        full_text += text
                        yield sse({"type": "delta", "text": text})

                elif "metadata" in event:
                    usage = event["metadata"].get("usage", {})
                    in_tok = usage.get("inputTokens", 0)
                    out_tok = usage.get("outputTokens", 0)
                    latency_ms = round((time.time() - start_time) * 1000)
                    cost = compute_llm_cost(model_id, in_tok, out_tok)
                    add_cost("chat_llm", cost, f"{model_id}: {in_tok} in, {out_tok} out")

                    yield sse({
                        "type": "metadata",
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "latency_ms": latency_ms,
                        "cost_usd": cost,
                        "model_id": model_id,
                        "region": region,
                    })

                elif "messageStop" in event:
                    stop_reason = event["messageStop"].get("stopReason", "")
                    yield sse({"type": "stop", "stop_reason": stop_reason})

                    # Handle content-filtered stop reasons
                    if stop_reason in ("guardrail", "content_filtered", "content-filtered"):
                        yield sse({
                            "type": "content_blocked",
                            "reason": stop_reason,
                            "message": (
                                "This response was blocked by the model's content safety filters."
                                + _BLOCKED_GUIDANCE
                            ),
                        })

                elif "guardrail" in event:
                    # Bedrock Guardrails interception (if guardrails are configured)
                    guard = event["guardrail"]
                    action = guard.get("action", "NONE")
                    if action == "BLOCKED":
                        # Extract which filter triggered
                        assessments = guard.get("assessments", [])
                        triggers = []
                        for a in assessments:
                            for filter_type in ("contentPolicy", "wordPolicy", "topicPolicy", "sensitiveInformationPolicy"):
                                policy = a.get(filter_type)
                                if policy:
                                    for f in policy.get("filters", policy.get("topics", policy.get("piiEntities", []))):
                                        name = f.get("type", f.get("name", filter_type))
                                        triggers.append(name)
                        trigger_str = ", ".join(triggers[:3]) if triggers else "content policy"
                        yield sse({
                            "type": "content_blocked",
                            "reason": f"guardrail:{trigger_str}",
                            "message": (
                                f"This request was blocked by content safety filters ({trigger_str})."
                                + _BLOCKED_GUIDANCE
                            ),
                        })

                elif "modelStreamErrorException" in event:
                    err = event["modelStreamErrorException"]
                    err_msg = err.get("message", "Unknown model error")
                    if "content" in err_msg.lower() or "safety" in err_msg.lower() or "policy" in err_msg.lower():
                        yield sse({
                            "type": "content_blocked",
                            "reason": "model_error",
                            "message": (
                                "The model stopped generating due to its content safety policy."
                                + _BLOCKED_GUIDANCE
                            ),
                        })
                    else:
                        yield sse({"type": "error", "detail": f"Model error: {err_msg}"})

        except client.exceptions.ThrottlingException as exc:
            yield sse({"type": "error", "detail": "Rate limited — try again in a moment."})
        except client.exceptions.ValidationException as exc:
            err_msg = str(exc)
            if "content" in err_msg.lower() or "safety" in err_msg.lower() or "policy" in err_msg.lower() or "harmful" in err_msg.lower():
                yield sse({
                    "type": "content_blocked",
                    "reason": "validation",
                    "message": (
                        "This request was rejected by the model's content safety checks before processing."
                        + _BLOCKED_GUIDANCE
                    ),
                })
            else:
                yield sse({"type": "error", "detail": f"Validation error: {err_msg}"})
        except client.exceptions.AccessDeniedException as exc:
            yield sse({"type": "error", "detail": f"Access denied for model {model_id}. Check IAM permissions or model access."})
        except Exception as exc:
            logger.error("Chat stream error: %s", exc)
            err_msg = str(exc)
            if "content" in err_msg.lower() or "safety" in err_msg.lower() or "blocked" in err_msg.lower():
                yield sse({
                    "type": "content_blocked",
                    "reason": "exception",
                    "message": (
                        "The model's content safety system prevented this request from being processed."
                        + _BLOCKED_GUIDANCE
                    ),
                })
            else:
                yield sse({"type": "error", "detail": err_msg})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Chat models ───────────────────────────────────────────────────────────

@router.get("/models")
async def list_chat_models():
    """List all available LLM models for Chat Studio.

    Aggregates from: chat_models registry section (discovered text LLMs),
    LLM categories (fast/complex/fallback), and custom_llms.
    Includes per-model pricing (cost per 1K input/output tokens).
    """
    from backend.services.model_registry import get_registry
    from backend.services.cost_tracker import LLM_PRICING
    registry = get_registry()

    def _get_pricing(model_id: str, chat_model_entry: dict | None = None) -> dict:
        """Get pricing per 1K tokens for a model.

        Tries: 1) chat_model registry entry pricing, 2) hardcoded LLM_PRICING, 3) empty.
        """
        # Try chat_models registry entry first (populated by discovery)
        if chat_model_entry:
            in_p = chat_model_entry.get("input_price_per_1k", 0)
            out_p = chat_model_entry.get("output_price_per_1k", 0)
            if in_p or out_p:
                return {"input_per_1k": round(in_p, 4), "output_per_1k": round(out_p, 4)}

        # Fall back to hardcoded pricing
        pricing = LLM_PRICING.get(model_id)
        if not pricing:
            for key, p in LLM_PRICING.items():
                if key in model_id or model_id in key:
                    pricing = p
                    break
        if pricing:
            return {
                "input_per_1k": round(pricing["input_per_mtok"] / 1000, 4),
                "output_per_1k": round(pricing["output_per_mtok"] / 1000, 4),
            }
        return {}

    models = []
    seen_labels = set()  # Deduplicate by normalized label to avoid "Claude Sonnet 4" appearing twice

    # Collect active category model IDs (so we can tag them as "active" in the list)
    active_cat_ids = set()
    for cat_name in ["fast_llm", "complex_llm", "fallback_llm"]:
        mid = registry.get("categories", {}).get(cat_name, {}).get("current", "")
        if mid:
            active_cat_ids.add(mid)

    # 1. chat_models (discovered text LLMs — the comprehensive source)
    from backend.services.model_registry import _lifecycle_usable
    for key, cfg in registry.get("chat_models", {}).items():
        if not cfg.get("enabled", True) or not _lifecycle_usable(cfg):
            continue
        mid = cfg.get("model_id", "")
        label = cfg.get("label", key)
        norm_label = label.lower().strip()
        if norm_label in seen_labels:
            continue
        seen_labels.add(norm_label)

        # Check if this model is also an active category model (by partial ID match)
        is_active = mid in active_cat_ids or any(mid in cid or cid in mid for cid in active_cat_ids)
        # Use the inference profile ID if this model matches a category
        effective_id = mid
        for cid in active_cat_ids:
            if mid in cid or cid.replace("us.", "") in mid:
                effective_id = cid  # Use the category's inference profile ID
                break

        models.append({
            "key": key,
            "label": label,
            "model_id": effective_id,
            "provider": cfg.get("provider", ""),
            "region": cfg.get("region", ""),
            "available_regions": cfg.get("available_regions", []),
            "has_vision": cfg.get("has_vision", False),
            "streaming_supported": cfg.get("streaming_supported", True),
            "max_context_tokens": cfg.get("max_context_tokens", 128000),
            "model_source": cfg.get("model_source", "foundation"),
            "is_active_llm": is_active,
            "pricing": _get_pricing(effective_id, cfg) or _get_pricing(mid, cfg),
        })

    # 2. LLM categories — only add if not already covered by chat_models discovery
    for cat_name in ["fast_llm", "complex_llm", "fallback_llm"]:
        cat = registry.get("categories", {}).get(cat_name, {})
        mid = cat.get("current", "")
        if not mid:
            continue
        # Check if any discovered model already covers this
        already_covered = any(m["model_id"] == mid for m in models)
        if already_covered:
            continue
        norm = (cat.get("label", cat_name)).lower().strip()
        if norm in seen_labels:
            continue
        seen_labels.add(norm)

        # Try to find this model's regions from chat_models by model family match.
        # Category IDs like "us.anthropic.claude-sonnet-4-6" should match discovered
        # "us.anthropic.claude-sonnet-4-5-20250929-v1:0" (same family, different version).
        import re as _re
        cat_regions = [cat.get("region", "us-west-2")]
        cat_vision = False
        cat_ctx = 200000
        # Extract family: "claude-sonnet" from "us.anthropic.claude-sonnet-4-6-v1"
        mid_clean = mid.replace("us.", "").split(":")[0]
        mid_parts = mid_clean.split(".")[-1]  # "claude-sonnet-4-6-v1" or "claude-opus-4-6-v1"
        mid_family = _re.sub(r"-\d.*", "", mid_parts)  # "claude-sonnet" or "claude-opus"
        for _, cm in registry.get("chat_models", {}).items():
            cm_id = cm.get("model_id", "").replace("us.", "").split(":")[0]
            cm_parts = cm_id.split(".")[-1]
            cm_family = _re.sub(r"-\d.*", "", cm_parts)
            if mid_family and cm_family == mid_family:
                cat_regions = cm.get("available_regions", cat_regions)
                cat_vision = cm.get("has_vision", False)
                cat_ctx = cm.get("max_context_tokens", cat_ctx)
                break

        models.append({
            "key": f"cat_{cat_name}",
            "label": cat.get("label", cat_name),
            "model_id": mid,
            "provider": cat.get("provider", ""),
            "region": cat.get("region", "us-west-2"),
            "available_regions": cat_regions,
            "has_vision": cat_vision,
            "streaming_supported": True,
            "max_context_tokens": cat_ctx,
            "model_source": "foundation",
            "is_active_llm": True,
            "pricing": _get_pricing(mid),
        })

    # 3. Custom LLMs
    custom = registry.get("categories", {}).get("custom_llms", {}).get("models", {})
    for key, cfg in custom.items():
        mid = cfg.get("model_id", "")
        if not mid or not cfg.get("enabled", False):
            continue
        norm = (cfg.get("label", key)).lower().strip()
        if norm in seen_labels:
            continue
        seen_labels.add(norm)
        models.append({
            "key": key,
            "label": cfg.get("label", key),
            "model_id": mid,
            "provider": "Custom",
            "region": cfg.get("region", ""),
            "available_regions": [cfg.get("region", "")],
            "has_vision": False,
            "streaming_supported": cfg.get("instruct_supported", True),
            "max_context_tokens": 128000,
            "model_source": cfg.get("model_source", "custom"),
            "is_active_llm": False,
            "pricing": _get_pricing(mid),
        })

    # Sort: active LLMs first, then by provider + label
    models.sort(key=lambda m: (0 if m.get("is_active_llm") else 1, m.get("provider", ""), m.get("label", "")))

    return {"models": models}


# ── Sessions ──────────────────────────────────────────────────────────────

@router.post("/sessions")
async def create_session(body: SessionCreate):
    """Create a new chat session."""
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    session = {
        "session_id": session_id,
        "title": body.title,
        "model_id": body.model_id,
        "system_prompt": body.system_prompt,
        "temperature": 0.7,
        "max_tokens": 4096,
        "messages": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost_usd": 0.0,
        "created_at": now,
        "updated_at": now,
    }

    _save_session(session_id, session)
    return session


@router.get("/sessions")
async def list_sessions():
    """List chat sessions, sorted by last activity."""
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []

    for f in sorted(CHAT_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            sessions.append({
                "session_id": data.get("session_id", f.stem),
                "title": data.get("title", "Untitled"),
                "model_id": data.get("model_id", ""),
                "message_count": len(data.get("messages", [])),
                "total_cost_usd": data.get("total_cost_usd", 0),
                "updated_at": data.get("updated_at", ""),
                "created_at": data.get("created_at", ""),
            })
        except Exception:
            pass

    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Load a full chat session."""
    session = _load_session(session_id)
    if not session:
        raise HTTPException(404, detail=f"Session {session_id} not found")
    return session


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, body: SessionUpdate):
    """Update a chat session (title, messages, model, etc.)."""
    session = _load_session(session_id)
    if not session:
        raise HTTPException(404, detail=f"Session {session_id} not found")

    updates = body.model_dump(exclude_unset=True)
    session.update(updates)
    session["updated_at"] = datetime.utcnow().isoformat()
    _save_session(session_id, session)
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    path = CHAT_DIR / f"{session_id}.json"
    if path.exists():
        path.unlink()
        return {"deleted": session_id}
    raise HTTPException(404, detail=f"Session {session_id} not found")


@router.post("/sessions/{session_id}/duplicate")
async def duplicate_session(session_id: str):
    """Duplicate a chat session with a new ID."""
    session = _load_session(session_id)
    if not session:
        raise HTTPException(404, detail=f"Session {session_id} not found")

    new_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    new_session = {**session, "session_id": new_id, "title": f"{session['title']} (copy)", "created_at": now, "updated_at": now}
    _save_session(new_id, new_session)
    return new_session


@router.get("/sessions/{session_id}/export")
async def export_session(session_id: str):
    """Export a chat session as Markdown."""
    session = _load_session(session_id)
    if not session:
        raise HTTPException(404, detail=f"Session {session_id} not found")

    lines = [f"# {session.get('title', 'Chat')}", ""]
    if session.get("system_prompt"):
        lines += [f"> **System prompt:** {session['system_prompt']}", ""]
    lines.append(f"**Model:** {session.get('model_id', '?')} | **Tokens:** {session.get('total_input_tokens', 0) + session.get('total_output_tokens', 0):,} | **Cost:** ${session.get('total_cost_usd', 0):.4f}")
    lines.append("")

    for msg in session.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        ts = msg.get("timestamp", "")
        if role == "user":
            lines += [f"## User{f' ({ts[:16]})' if ts else ''}", "", content, ""]
        else:
            tokens = ""
            if msg.get("input_tokens") or msg.get("output_tokens"):
                tokens = f" | {msg.get('input_tokens', 0)} in / {msg.get('output_tokens', 0)} out"
                if msg.get("cost_usd"):
                    tokens += f" | ${msg['cost_usd']:.4f}"
            lines += [f"## Assistant{f' ({ts[:16]})' if ts else ''}{tokens}", "", content, ""]

    from starlette.responses import Response
    md = "\n".join(lines)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in session.get("title", "chat")).strip().replace(" ", "_")
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}_{session_id}.md"'},
    )


@router.post("/compact")
async def compact_context(body: CompactRequest):
    """Compact older messages in a session by summarizing them via LLM.

    Keeps the last `keep_recent` messages verbatim. Older messages are
    replaced by a single summary message, freeing context window space.
    """
    from backend.services.bedrock_client import invoke_llm

    session = _load_session(body.session_id)
    if not session:
        raise HTTPException(404, detail=f"Session {body.session_id} not found")

    messages = session.get("messages", [])
    if len(messages) <= body.keep_recent:
        return {"compacted": False, "reason": "Not enough messages to compact"}

    # Split: older messages to summarize, recent to keep
    to_summarize = messages[:-body.keep_recent]
    to_keep = messages[-body.keep_recent:]

    # Build summary prompt
    convo_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m.get('content', '')[:500]}"
        for m in to_summarize
    )

    try:
        from backend.services.prompt_templates import get_system_prompt
        summary = invoke_llm(
            prompt=get_template('chat_context_compact').format(convo_text=convo_text),
            system=get_system_prompt('chat_context_compact'),
            max_tokens=1000,
            temperature=0.3,
        )
    except Exception as exc:
        raise HTTPException(502, detail=f"Summarization failed: {exc}")

    # Replace old messages with summary.
    # Use role "user" to avoid consecutive assistant messages (Converse API
    # requires strict user/assistant alternation). The compacted marker in
    # the content makes it clear this is a system-generated summary.
    summary_msg = {
        "role": "user",
        "content": f"*[Context summary — {len(to_summarize)} earlier messages compacted]*\n\n{summary}",
        "timestamp": datetime.utcnow().isoformat(),
        "compacted": True,
        "compacted_count": len(to_summarize),
    }

    session["messages"] = [summary_msg] + to_keep
    session["updated_at"] = datetime.utcnow().isoformat()
    _save_session(body.session_id, session)

    return {
        "compacted": True,
        "messages_removed": len(to_summarize),
        "messages_remaining": len(session["messages"]),
        "summary_length": len(summary),
    }


@router.get("/sessions/{session_id}/search")
async def search_session(session_id: str, q: str = ""):
    """Search within a session's messages."""
    session = _load_session(session_id)
    if not session:
        raise HTTPException(404, detail=f"Session {session_id} not found")
    if not q:
        return {"matches": []}

    query = q.lower()
    matches = []
    for i, msg in enumerate(session.get("messages", [])):
        content = msg.get("content", "")
        if query in content.lower():
            # Find the matching snippet with context
            pos = content.lower().index(query)
            start = max(0, pos - 50)
            end = min(len(content), pos + len(query) + 50)
            snippet = content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet += "..."
            matches.append({"index": i, "role": msg["role"], "snippet": snippet})

    return {"matches": matches, "query": q}


# ── Smart title generation ─────────────────────────────────────────────────

class TitleRequest(BaseModel):
    user_message: str
    assistant_snippet: str = ""


@router.post("/generate-title")
async def generate_title(body: TitleRequest):
    """Generate a concise chat session title from the first exchange.

    Uses the fast LLM with minimal tokens — costs ~$0.0003 per call.
    Returns a 3-8 word title summarizing the conversation topic.
    """
    from backend.services.bedrock_client import invoke_llm

    try:
        prompt = get_template('chat_title_generate').format(
            user_message=body.user_message[:300],
            assistant_snippet=body.assistant_snippet[:200] if body.assistant_snippet else "(none)",
        )

        from backend.services.prompt_templates import get_system_prompt
        title = invoke_llm(
            prompt=prompt,
            system=get_system_prompt('chat_title_generate'),
            max_tokens=30,
            temperature=0.3,
            complexity="fast",
        ).strip().strip('"\'').split('\n')[0]

        # Truncate if too long
        if len(title) > 60:
            title = title[:57] + "..."

        return {"title": title}
    except Exception as exc:
        logger.debug("Title generation failed: %s", exc)
        raise HTTPException(502, detail="Title generation failed")


# ── Telemetry ─────────────────────────────────────────────────────────────

class ChatTelemetryEvent(BaseModel):
    session_id: str
    model_id: str = ""
    messages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0
    duration_seconds: int = 0
    has_vision: bool = False
    compacted: bool = False


@router.post("/telemetry")
async def chat_telemetry(body: ChatTelemetryEvent):
    """Receive a session summary event from the frontend.

    Called once when the user navigates away from a session — captures the
    full session's usage in a single PulseBoard event.
    """
    from backend.services.telemetry import track_chat_session, track_chat_cost
    track_chat_session(
        model=body.model_id,
        messages=body.messages,
        input_tokens=body.input_tokens,
        output_tokens=body.output_tokens,
        duration_seconds=body.duration_seconds,
        has_vision=body.has_vision,
        compacted=body.compacted,
    )
    if body.cost_usd > 0:
        track_chat_cost(cost_usd=body.cost_usd, model=body.model_id)
    return {"ok": True}


# ── Helpers ───────────────────────────────────────────────────────────────

def _save_session(session_id: str, data: dict):
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    (CHAT_DIR / f"{session_id}.json").write_text(json.dumps(data, indent=2, default=str))


def _load_session(session_id: str) -> dict | None:
    path = CHAT_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _resolve_chat_region(model_id: str) -> str:
    """Find the best region for a chat model from the registry."""
    from backend.services.model_registry import get_registry
    registry = get_registry()

    # Check chat_models
    for key, cfg in registry.get("chat_models", {}).items():
        if cfg.get("model_id") == model_id:
            return cfg.get("region", "us-west-2")

    # Check categories
    for cat_name in ["fast_llm", "complex_llm", "fallback_llm"]:
        cat = registry.get("categories", {}).get(cat_name, {})
        if cat.get("current") == model_id:
            return cat.get("region", "us-west-2")

    return "us-west-2"
