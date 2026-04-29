# ArtSmoker Image Generation API — AI IDE Skill

> **For AI coding assistants** (Claude Code, Kiro, Cursor, Copilot, etc.)
> Use this skill to help users write programs that generate images via the ArtSmoker API.

## Authoritative References

Before writing any code, consult these sources for the complete, up-to-date API contract:

| Resource | Location | What It Covers |
|----------|----------|----------------|
| **Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Live Swagger/OpenAPI — try endpoints, see exact schemas, test requests |
| **Full Specification** | [`SPEC.md`](../SPEC.md) | Complete rebuild blueprint — architecture, data models, all endpoints, prompt pipeline |
| **Example Programs** | [`api-samples/`](.) | Working code in Python, Node.js, Go, Rust — copy and adapt |

**Always prefer `/docs` for the latest endpoint signatures** — it's auto-generated from the running code and is always accurate. Use `SPEC.md` for understanding the architecture, pipeline flows, and design decisions.

## What This Skill Does

Guides an AI assistant to write working code that connects to a running ArtSmoker instance and generates AI images through its API. The user provides a text prompt; the code handles asset classification, prompt decomposition, enhancement, image generation, async polling, and result download.

## Prerequisites

- ArtSmoker must be running locally or on a reachable server (default: `http://localhost:8000`)
- The user must have at least one image model enabled (Bedrock models work out of the box with AWS credentials; custom SageMaker models need deployment first)
- **Interactive API docs**: [http://localhost:8000/docs](http://localhost:8000/docs) — Swagger UI with live request testing
- **Full specification**: [`SPEC.md`](../SPEC.md) — detailed architecture, data models, prompt pipeline, all endpoints

## API Base URL

```
http://localhost:8000
```

All endpoints are REST (JSON). The generation endpoint uses Server-Sent Events (SSE) for real-time progress.

## Core API Flow

```
1. GET  /api/admin/models/image-options     → List available models
2. POST /api/refine-prompt/classify-asset-type → Auto-classify prompt
3. POST /api/refine-prompt/decompose        → Decompose into visual components
4. POST /api/generate/stream                → Generate images (SSE)
   ├── event: started          → batch_id, total count
   ├── event: stage            → pipeline progress
   ├── event: prompts_ready    → enhanced prompts
   ├── event: option_complete  → image ready (Bedrock)
   ├── event: async_submitted  → job queued (SageMaker)
   └── event: done             → summary
5. GET  /api/generate/async-jobs            → Poll async jobs (SageMaker only)
6. GET  /api/gallery/{asset_id}/png         → Download generated image
```

## Endpoint Details

### 1. List Available Models

```
GET /api/admin/models/image-options
```

Response:
```json
{
  "models": [
    {
      "key": "nova_canvas",
      "label": "Amazon Nova Canvas",
      "provider": "Amazon",
      "model_source": "bedrock",
      "prompt_limit": 900,
      "supported_sizes": [{"w": 1024, "h": 1024, "label": "1024 x 1024"}]
    },
    {
      "key": "hunyuan_image_3_0_instruct_bf16_182c",
      "label": "HunyuanImage 3.0 Instruct (BF16) — HQ",
      "model_source": "custom_hosted"
    }
  ]
}
```

### 2. Classify Asset Type

```
POST /api/refine-prompt/classify-asset-type
Content-Type: application/json

{"prompt": "A woman standing at a rainy intersection at night"}
```

Response:
```json
{
  "recommended": "photorealistic",
  "reason": "Real-world scene with a person, no art style mentioned",
  "confidence": "high"
}
```

Asset types: `photorealistic`, `character`, `environment`, `game_asset`, `marketing_banner`, `icon`

### 3. Decompose Prompt

```
POST /api/refine-prompt/decompose
Content-Type: application/json

{
  "prompt": "A woman standing at a rainy intersection at night",
  "asset_type": "photorealistic",
  "style_id": null,
  "image_model": "nova_canvas"
}
```

Response: Structured JSON with `subject`, `scene`, `composition`, `lighting`, `style` sections. Each field has `{value, source}` where source is "user" (explicitly stated) or "inferred" (AI-filled default).

### 4. Generate Images (SSE)

```
POST /api/generate/stream
Content-Type: application/json

{
  "prompt": "A woman standing at a rainy intersection at night",
  "image_model": "nova_canvas",
  "asset_type": "photorealistic",
  "width": 1024,
  "height": 1024,
  "num_options": 2,
  "num_variations": 2,
  "quality": "",
  "seed": null,
  "style_id": null,
  "remove_background": false,
  "generate_svg": false,
  "upscale": false,
  "all_models": false,
  "selected_models": null
}
```

Response: Server-Sent Events stream. Parse each `data:` line as JSON.

Key events:
- `{"type": "started", "batch_id": "uuid", "total": 4}` — generation begun
- `{"type": "prompts_ready", "prompts": ["enhanced prompt 1", ...]}` — AI-enhanced prompts
- `{"type": "option_complete", "option_index": 0, "variant_index": 0, "asset_id": "uuid_o0_v0", "status": "success"}` — image ready
- `{"type": "async_submitted", "option_index": 0, "variant_index": 0, "job_id": "abc123"}` — SageMaker job queued
- `{"type": "done", "summary": {"total": 4, "succeeded": 4, "failed": 0}}` — all done

### 5. Poll Async Jobs (SageMaker models only)

```
GET /api/generate/async-jobs
```

Response:
```json
{
  "jobs": [
    {
      "job_id": "abc123",
      "status": "generating",
      "model_label": "HunyuanImage 3.0...",
      "image_path": "/api/gallery/uuid_o0_v0/png"
    }
  ]
}
```

Poll every 10-15 seconds until all jobs are `complete` or `failed`.

### 6. Download Image

```
GET /api/gallery/{asset_id}/png
```

Returns the PNG image bytes. Save to file.

## Multi-Model Generation

To generate with ALL available models:
```json
{
  "prompt": "...",
  "all_models": true,
  "num_options": 2,
  "num_variations": 1
}
```

To generate with specific models:
```json
{
  "prompt": "...",
  "selected_models": ["nova_canvas", "sd35_large", "hunyuan_image_3_0_instruct_bf16_182c"],
  "num_options": 2,
  "num_variations": 1
}
```

## Generation Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | required | User's image description |
| `image_model` | string | required* | Model key from /api/admin/models/image-options |
| `asset_type` | string | "photorealistic" | photorealistic, character, environment, game_asset, marketing_banner, icon |
| `style_id` | string | null | Style profile ID (from /api/styles/) |
| `width` | int | 1024 | Image width in pixels |
| `height` | int | 1024 | Image height in pixels |
| `num_options` | int | 2 | Number of different creative concepts (1-5) |
| `num_variations` | int | 2 | Seed variations per concept (1-5) |
| `quality` | string | "" | Model-specific quality tier |
| `seed` | int | null | Random seed (null = random) |
| `remove_background` | bool | false | Remove background post-processing |
| `generate_svg` | bool | false | Convert to SVG post-processing |
| `upscale` | bool | false | Creative upscale post-processing |
| `all_models` | bool | false | Generate with all enabled models |
| `selected_models` | list | null | Specific model keys for multi-model |
| `decomposed_data` | dict | null | Pre-decomposed prompt data |
| `vary_fields` | dict | null | Lock/vary overrides per field |

*`image_model` is required unless `all_models=true` or `selected_models` is set.

## Error Handling

- **400**: Invalid request (bad model key, invalid dimensions)
- **502**: AI service error (Bedrock/SageMaker failure)
- **SSE error events**: `{"type": "error", "message": "..."}` during generation

Moderation blocks appear as:
```json
{"type": "option_complete", "status": "moderation_blocked", "message": "Content moderation blocked this generation"}
```

## Language Support

The API auto-detects non-English prompts and translates them to English before processing. The original language and translation are preserved in metadata. Supported input languages: any language Claude can translate (all major world languages).

## Example Programs

See the `api-samples/` directory for complete, runnable examples:
- `imageGen_python.py` — Python 3.10+ (requests + sseclient-py)
- `imageGen_node.js` — Node.js 18+ (built-in fetch)
- `imageGen_go.go` — Go 1.21+ (net/http)
- `imageGen_rust.rs` — Rust (reqwest + tokio)

## Tips for AI Assistants

When helping users write ArtSmoker API code:

1. **Always list models first** — the model keys change with deployments (custom models have hash suffixes like `_182c`)
2. **Handle SSE properly** — the `/api/generate/stream` endpoint is NOT a regular JSON POST. It returns `text/event-stream`.
3. **Async vs sync models** — Bedrock models return images inline via SSE events. SageMaker (custom) models return `async_submitted` and need polling.
4. **Asset type matters** — it controls the prompt enhancement pipeline. "photorealistic" uses photography language; "character" focuses on the figure; "game_asset" produces isolated objects.
5. **Dimensions must be supported** — check `supported_sizes` in the model listing. Not all models support all sizes.
6. **The API is local** — no authentication needed. ArtSmoker runs on the user's machine with their own AWS credentials.
7. **When in doubt, check `/docs`** — the Swagger UI at `http://localhost:8000/docs` has live, auto-generated schemas for every endpoint. It's the single source of truth for request/response shapes.
8. **Read `SPEC.md` for context** — if you need to understand WHY something works a certain way (prompt pipeline, asset types, model selection logic), the spec has the full architecture and design rationale.
