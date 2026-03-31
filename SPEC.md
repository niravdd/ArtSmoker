# ArtSmoker — AI-Powered Game Asset Generation Platform

## How to Use This Specification

> **This document is a complete rebuild blueprint.** An LLM or developer reading this spec should be able to reconstruct the entire project — backend, frontend, and infrastructure — without access to the original codebase.

**Reading order for a rebuild:**

1. **Context + Architecture** — understand what this project does and how it's structured.
2. **Project Structure** — create the file/directory skeleton first.
3. **Application Bootstrap** — set up `main.py`, config, dependencies before writing features.
4. **Detailed Component Design** — implement each subsystem. Start with storage, then models, then services, then routers, then frontend.
5. **API Reference** — use as the contract between backend and frontend. Every endpoint, request body, and response shape is documented here.
6. **Frontend Design System** — CSS theme, component patterns, and conventions.
7. **Verification** — test checklist to validate the build.

**Coding conventions:**
- **Backend**: Python 3.11+, FastAPI with Pydantic v2 models, type hints everywhere, `async def` for route handlers. Services are plain synchronous functions (Bedrock calls are blocking). Use `logging.getLogger(__name__)` in every module.
- **Frontend**: Vanilla JS (no framework, no build step), Tailwind CSS via CDN, IIFE pattern for components (`(function() { 'use strict'; window.ComponentName = { render(), init(), onShow(), destroy() }; })();`). Components expose themselves on `window` and are wired up by `app.js`.
- **Naming**: Backend uses `snake_case` for everything. Frontend uses `camelCase` for JS, `kebab-case` for CSS classes and HTML IDs. API field names are `snake_case` (matching Python models).
- **Error handling**: Backend returns `HTTPException` with status codes (400, 404, 409, 502). Frontend shows errors via `window.showToast(message, 'error')`. All client-side errors are also sent to `POST /api/log` for server-side recording.
- **No Claude branding in frontend**: All user-facing UI references use "AI" generically — never "Claude" or any specific model name in labels/buttons. Image model names use full display names ("Stable Diffusion 3.5 Large", not "SD 3.5").

## Table of Contents

- [1. Context](#1-context)
- [2. Architecture Overview](#2-architecture-overview)
- [3. Project Structure](#3-project-structure)
- [4. Detailed Component Design](#4-detailed-component-design)
  - [4.1 Style Profile System](#41-style-profile-system)
  - [4.2 Two-Level Asset Generation Pipeline](#42-two-level-asset-generation-pipeline)
  - [4.3 Strong Asset-Type Differentiation](#43-strong-asset-type-differentiation)
  - [4.4 Result Model Structure](#44-result-model-structure)
  - [4.5 Voice Input (Nova Sonic)](#45-voice-input-nova-sonic)
  - [4.6 Frontend Design](#46-frontend-design)
  - [4.7 Technology Choices](#47-technology-choices)
  - [4.8 AWS Configuration](#48-aws-configuration)
  - [4.9 Post-Processing Pipeline](#49-post-processing-pipeline)
  - [4.10 Storage Layer](#410-storage-layer)
  - [4.11 Model Registry](#411-model-registry)
- [5. API Reference](#5-api-reference)
  - [5.1 Styles](#51-styles)
  - [5.2 Generation](#52-generation)
  - [5.3 Prompt Refinement](#53-prompt-refinement)
  - [5.4 Voice Transcription](#54-voice-transcription)
  - [5.5 Gallery](#55-gallery)
  - [5.6 Type Studio](#56-type-studio)
  - [5.7 Video](#57-video)
  - [5.8 Chat Studio](#58-chat-studio)
  - [5.9 Browse](#59-browse)
  - [5.10 Admin (Model Management)](#510-admin-model-management)
  - [5.11 System](#511-system)
- [6. LLM Directive Prompts (Prompt Templates)](#6-llm-directive-prompts-prompt-templates)
- [7. Prerequisites: AWS Setup](#7-prerequisites-aws-setup)
  - [7.1 AWS Credentials](#71-aws-credentials)
  - [7.2 Required IAM Permissions](#72-required-iam-permissions)
  - [7.3 Bedrock Model Availability](#73-bedrock-model-availability)
  - [7.4 Verifying Access](#74-verifying-access)
  - [7.5 Startup Validation](#75-startup-validation)
- [8. Security Model](#8-security-model)
- [9. Application Bootstrap (main.py)](#9-application-bootstrap-mainpy)
- [10. Dependencies (requirements.txt)](#10-dependencies-requirementstxt)
- [11. Frontend Design System](#11-frontend-design-system)
- [12. Configuration](#12-configuration)
- [13. Verification](#13-verification)
- [14. Amazon Bedrock Pricing & Cost Breakdown](#14-aws-bedrock-pricing--cost-breakdown)
  - [14.1 Per-Unit Pricing](#141-per-unit-pricing)
  - [14.2 Additional LLM Costs](#142-additional-llm-costs-per-use)
  - [14.3 Style Analysis Cost](#143-style-analysis-cost-one-time-per-style)
  - [14.4 Generation Cost Scenarios](#144-generation-cost-scenarios)
  - [14.5 Full Cost Examples](#145-full-cost-examples)
- [15. Internationalization (i18n)](#15-internationalization-i18n)
- [16. Deployment & Scaling Roadmap](#16-deployment--scaling-roadmap)
  - [16.1 Why Not Lambda](#161-why-not-lambda)
  - [16.2 Phase 1: Local Development](#162-phase-1-current--local-development-done)
  - [16.3 Phase 2: App Runner + S3](#163-phase-2-containerized-deployment--app-runner--s3)
  - [16.4 Phase 3: CloudFront + Async](#164-phase-3-optimized-delivery--cloudfront--async-generation)
  - [16.5 Phase 4: Multi-Tenant](#165-phase-4-multi-tenant-platform)

---

## 1. Context

ArtSmoker is a self-hosted web application that gives creative teams and game studios a simple, artist-friendly interface for Amazon Bedrock's image and video generation models — without needing to learn the Bedrock API, CLI, or prompt engineering.

**Problem**: Creative teams want to use AI for asset generation but face real barriers. They don't build or train their own models — and shouldn't need to. Amazon Bedrock offers a wide range of models, but the Bedrock console and API are built for developers, not artists. Composing effective prompts (with negative prompts, style directives, and model-specific formatting) takes expertise most artists don't have. Image editing operations like inpainting, outpainting, and style transfer are even more inaccessible.

**Solution**: ArtSmoker wraps Bedrock in a clean creative interface — purpose-built for game asset production. Artists describe what they need in plain language. ArtSmoker handles prompt composition, negative prompt extraction, style application, model-specific formatting, and multi-model comparison behind the scenes. Upload existing art, and ArtSmoker's vision models learn the visual identity — every generated asset matches the game's look and feel.

The platform supports all text-to-image models, video models, and image editing services available on Amazon Bedrock, across all regions. Fully configurable, dynamically discovered, self-deployed, and self-billed — no shared endpoints, no third-party data access.

**Two operating modes**:
- **Standalone** — no art style or theme setup required. Open any studio, describe what you need, and generate. The AI handles prompt enhancement, negative prompt extraction, and model-specific formatting automatically.
- **Style-guided** — upload your game's existing art. ArtSmoker's vision models analyze the visual identity (colour palettes, line weights, lighting, composition) and produce a style profile. Every subsequent generation is automatically enhanced with your style's directives, ensuring consistent visual identity across all assets.

Both modes use the same **two-level generation model**: for each user prompt, the LLM generates multiple distinctly different creative *options* (concept designs), and for each option the image generator produces multiple seed *variations*. This gives the user a broad creative palette to choose from.

## 2. Architecture Overview

```
Browser (Vanilla JS + Tailwind CSS)
    |
    +-- Voice input (MediaRecorder → Nova Sonic for transcription)
    +-- Text input with inline LLM prompt refinement
    +-- Style library management (upload, browse, edit, directory import)
    +-- 2D Image Studio: two-tier generation UI (options × variations)
    +-- Video Studio: text-to-video generation (async, S3-backed)
    +-- Type Studio: text overlay system (on-image + standalone)
    +-- Unified gallery: images + videos with filtering and export
    |
    v
FastAPI Backend (Python)
    |
    +-- /api/styles        — CRUD for style profiles + directory/S3 import
    +-- /api/generate       — Two-level asset generation pipeline + post-processing
    +-- /api/type-studio    — Text overlay: font listing, AI layout, preview/render
    +-- /api/transcribe     — Voice-to-text via Nova Sonic
    +-- /api/refine-prompt  — LLM prompt improvement (preview)
    +-- /api/gallery        — Generated asset browsing + file serving + bulk delete
    +-- /api/video          — Video generation (async), job polling, MP4/thumbnail serving
    +-- /api/browse         — Server-side file browser (local + S3) + bucket creation
    +-- /api/admin          — Model registry management + Bedrock discovery + video settings
    +-- /api/log            — Client-side error logging
    |
    v
AI Pipeline (Amazon Bedrock)
    |
    +-- Claude Sonnet 4.6      — Fast tasks: prompt refinement, generation hints, cohesion check (Phase 1)
    +-- Claude Opus 4.6        — Complex tasks: style analysis (Phase 2), concept generation, marketing copy
    +-- Nova Canvas             — Primary image generation (text-to-image)
    +-- Titan Image v2          — Alternative image generation
    +-- Stable Diffusion 3.5 Large            — Image generation (Stability AI)
    +-- Stable Image Ultra      — Image generation (Stability AI premium)
    +-- Stability AI            — Background removal, upscaling, inpainting, style transfer
    +-- Nova Reel v1.0/v1.1    — Video generation (text-to-video, image-to-video, multi-shot)
    +-- Luma AI Ray v2.0       — Video generation (text-to-video, flexible aspect ratios)
    +-- Nova Sonic              — Speech-to-text transcription (bidirectional streaming)
    |
    v
Storage (Local filesystem + S3)
    +-- /data/styles/       — Style profiles + reference images
    +-- /data/generated/    — Output image assets (PNG + SVG) + metadata + versions
    +-- /data/video/        — Video assets (MP4 + thumbnails + job metadata)
    +-- S3 bucket           — Video generation output (required for async Bedrock invoke)
```

## 3. Project Structure

```
ArtSmoker/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, lifespan, static mount
│   ├── config.py                  # AWS config, model IDs, paths, defaults
│   ├── model_registry.json        # Persisted model configuration (LLMs, image models, post-processing)
│   ├── routers/
│   │   ├── styles.py              # Style profile CRUD + directory import + analysis
│   │   ├── generate.py            # Two-level asset generation (options × variations) + image editing
│   │   ├── video.py               # Video generation (async), job polling, MP4/thumbnail serving, revisions
│   │   ├── transcribe.py          # Voice transcription endpoint
│   │   ├── refine.py              # Prompt refinement preview endpoint
│   │   ├── gallery.py             # Generated asset browsing + file serving + versioned assets
│   │   ├── browse.py              # Server-side file/S3 browser + S3 bucket creation
│   │   ├── typestudio.py          # Type Studio: text overlay, font serving, AI layout
│   │   ├── chat.py                # Chat Studio: LLM chat streaming, sessions, export, context compaction
│   │   └── admin.py               # Model registry admin API + Bedrock discovery (image + video + chat) + video settings
│   ├── services/
│   │   ├── model_registry.py      # Model registry manager: loads/saves model_registry.json, provides config to system
│   │   ├── video_generator.py     # Video generation: async Bedrock invoke, S3 download, ffmpeg thumbnails
│   │   ├── style_analyzer.py      # Two-phase style analysis: Sonnet cohesion check → Opus full analysis (includes _smart_sample())
│   │   ├── prompt_engineer.py     # Claude Sonnet/Opus: prompt refinement + concept generation
│   │   ├── image_generator.py     # Generic image invoker via registry format families
│   │   ├── post_processor.py      # Registry-driven: bg removal, upscale (by model purpose); vtracer/potrace: SVG
│   │   ├── transcriber.py         # Nova Sonic: bidirectional streaming speech-to-text
│   │   ├── texture_extractor.py   # glTF/GLB texture extraction (base64, binary chunks, external refs)
│   │   ├── import_dedup.py        # Smart deduplication for directory imports (rotation variants, animation frames, folder priority)
│   │   ├── cost_tracker.py        # Request-scoped cost accumulator: tracks LLM tokens + image model prices
│   │   ├── telemetry.py           # PulseBoard SDK wrapper: tracks server events (startup, generation, errors)
│   │   ├── pulseboard.py          # Zero-dependency PulseBoard client SDK (copied from PulseBoard project)
│   │   └── bedrock_client.py      # Shared Bedrock client: invoke_llm (with system prompt), invoke_image_model (generic)
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update models
│   │   ├── generation_request.py  # GenerationRequest, AssetType, ImageModel enums
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult, GalleryItem
│   ├── storage/
│   │   └── local_store.py         # Local filesystem storage (S3-compatible interface)
│   └── requirements.txt
├── frontend/
│   ├── index.html                 # Single-page app entry
│   ├── css/
│   │   └── styles.css             # Tailwind + custom styles
│   ├── js/
│   │   ├── app.js                 # Main app logic, routing
│   │   ├── components/
│   │   │   ├── StyleLibrary.js    # Style profile browser + uploader
│   │   │   ├── ImageStudio.js     # 2D Image Studio: two-tier generation UI (options + variations)
│   │   │   ├── VideoStudio.js     # Video Studio: text-to-video generation, job polling, video player
│   │   │   ├── ChatStudio.js      # Chat Studio: multi-model LLM chat with streaming, sessions, vision
│   │   │   ├── TypeStudio.js      # Type Studio: text overlay system (on-image + standalone)
│   │   │   ├── VoiceInput.js      # Voice recording + transcription
│   │   │   ├── PromptEditor.js    # Text input with inline LLM refinement
│   │   │   ├── Gallery.js         # Unified gallery: images + videos, media filter, type filter
│   │   │   ├── AssetViewer.js     # Full-size image preview + zoom/pan + edit + versioning
│   │   │   └── ModelSettings.js   # Model registry admin UI: image models, video models, LLM, JSON editor
│   │   └── services/
│   │       └── api.js             # Backend API client
│   └── (no build step — served as static files by FastAPI)
├── data/
│   ├── styles/                    # User-uploaded style profiles + reference images
│   ├── generated/                 # Output image assets (PNG + SVG + metadata + versions)
│   └── video/                     # Video assets (MP4 + thumbnails + job metadata)
├── .gitattributes                 # Marks generated SVGs as binary (secret scanner false-positive prevention)
├── .github/
│   └── secret_scanning.yml        # Excludes data/ and *.svg from GitHub secret scanning
├── SPEC.md                        # This file — full project specification
└── README.md                      # Quick-start guide
```

## 4. Detailed Component Design

### 4.1 Style Profile System

A style profile captures the visual DNA of a game's art:

```json
{
  "id": "city-builder-iso",
  "name": "Isometric City Builder",
  "description": "Low-poly isometric city buildings",
  "created_at": "2026-02-24T...",
  "reference_images": ["ref1.png", "ref2.png", "..."],
  "analyzed_style": {
    "perspective": "isometric, 45-degree top-down",
    "palette": ["#4a90d9", "#f5a623", "#7ed321", "#d0021b"],
    "rendering": "flat-shaded low-poly, no textures, solid colors",
    "line_weight": "no outlines, form defined by color planes",
    "mood": "cheerful, clean, toylike",
    "scale": "1-unit grid tiles, buildings 1-3 units tall",
    "background": "transparent",
    "materials": "stone rendered as uniform flat gray planes, wood as warm brown blocks, metal as light blue-gray surfaces — no textures or gradients",
    "detail_level": "minimal surface detail, no visible grain or weathering, forms defined entirely by color planes and sharp edges"
  },
  "generation_hints": "Isometric low-poly game asset, flat shading, cheerful colors, transparent background, single object centered, no shadows"
}
```

**Pydantic models** (`backend/models/style_profile.py`):
- `AnalyzedStyle` — 9 structured fields: perspective, palette (list of hex strings), rendering, line_weight, mood, scale, background, materials (how stone, wood, metal are rendered), detail_level (what surface details are visible vs simplified).
- `StyleProfile` — full profile with id, name, description, created_at, reference_images, analyzed_style, generation_hints.
- `StyleProfileCreate` — name + description + optional `generation_hints` for creation.
- `StyleProfileUpdate` — optional name, description, analyzed_style, generation_hints for partial updates.

**Workflow:**
1. User creates a style profile (name + description + optional `generation_hints`).
2. User uploads 1-100 reference images via file upload or **directory import** (bulk import from a local folder path or S3 prefix). The cap is configurable via `max_reference_images` (default 100, env: `ARTSMOKER_MAX_REFERENCE_IMAGES`).
3. **Smart sampling for analysis**: When a style has more than `max_analysis_images` (default 20, env: `ARTSMOKER_MAX_ANALYSIS_IMAGES`) reference images, the `_smart_sample()` function in `style_analyzer.py` selects a diverse representative subset for the Claude Opus vision call. Sampling strategy:
   - Always includes the first and last image (alphabetically).
   - Groups images by filename prefix (subdirectory origin) and picks at least one from each group.
   - Fills remaining slots by file-size diversity (evenly-spaced intervals across the size range, since different sizes suggest different content/complexity).
   - Claude is told how many total images exist vs. how many it is seeing (e.g. "You are seeing 20 representative images sampled from a collection of 80 total reference images").
   When the image count is at or below `max_analysis_images`, all images are sent directly.
4. **Two-phase cohesion-aware analysis** via `analyze_style(style_id, user_hints)`:
   - **Phase 1 — Cohesion check (Claude Sonnet, cheap)**: Sends 8 representative images to Claude Sonnet to determine collection cohesion level (high/medium/low):
     - **High cohesion**: All images share the same style — the Phase 2 prompt extracts a unified style profile.
     - **Medium cohesion**: Structural patterns are shared but themes differ — the Phase 2 prompt extracts design language and production standards.
     - **Low cohesion**: Diverse styles — the Phase 2 prompt focuses on what IS consistent (quality standards, sizing conventions, composition patterns).
   - **Phase 2 — Full analysis (Claude Opus, vision)**: The cohesion assessment from Phase 1 is fed to Claude Opus alongside the (sampled) reference images, guiding it to analyze appropriately for the collection type. This means diverse collections get useful hints about production patterns, not a diluted "colorful game art" generic description.
   - The analysis prompt is specifically designed for game assets on transparent backgrounds — it asks for material-specific rendering details (how stone, wood, metal are rendered), proportion system, and shadow/lighting specifics. The analysis is **context-aware** — Claude sees both the images AND the user's existing `generation_hints` (passed as "Artist's Guidance") so it understands the user's intent.
   - The cohesion check adds ~$0.01 per analysis (Sonnet with 8 images is very cheap).
5. Claude Sonnet 4.6 distils the analysis into a concise `generation_hints` paragraph (max 200 words) via `generate_hints(style_id, analyzed_style, user_hints)`, also receiving the user's guidance as context. The hints cover 8 dimensions: perspective, rendering with material specifics, color palette by material, proportions, edge treatment, shadow/lighting, detail level, and background — specific enough that generated assets should visually blend with existing reference images.
6. Profile is cached as `profile.json` inside `data/styles/{style_id}/`.
7. User can manually edit/refine the profile.
8. Profile's `generation_hints` are incorporated into every generation prompt.
9. **Auto re-analysis**: Style analysis is automatically re-triggered when (a) reference images are uploaded via the upload endpoint, or (b) `generation_hints` are changed via PATCH and the new value differs from the previous one. Both paths use a shared `_auto_reanalyze()` helper.

**Directory/S3 import**: The `POST /api/styles/{id}/import` endpoint accepts a local directory path or S3 prefix. Body: `{ "path": "...", "auto_analyze": true }`. It scans **recursively** (using `rglob`) for all supported asset files in all subdirectories.

**Smart deduplication on import** (`backend/services/import_dedup.py`): Deduplication always runs on every import regardless of file count — even small sets can have cross-folder duplicates. The system deduplicates rotation variants and animation frames before importing, ensuring Claude sees the full vocabulary of unique objects rather than 15 copies of the same barrel from different angles.
- **Rotation variants**: Files like `barrel_N.png`, `barrel_E.png`, `barrel_S.png`, `barrel_W.png` are recognized as rotations of the same object — only the south-facing variant (`barrel_S.png`) is kept.
- **Animation frames**: Files like `Male_0_Idle0.png` through `Male_0_Idle8.png` are recognized as frames of the same animation — only the base frame (`Idle`) is kept.
- **Folder prioritization**: When the same object appears in multiple subdirectories (e.g. rendered at different angles), folders are scored by priority: `Samples`/`Screenshots` (highest) > `Isometric`/`rendered` > `Characters` > `Angle` (lowest, skipped entirely if an `Isometric` variant exists).
- **Implementation**: `deduplicate_imports()` calls `_get_canonical_key()` per file to compute a normalized key, then selects the best representative per key using folder priority scoring.
- **Impact**: For example, a 747-file isometric asset pack deduplicates to ~99 unique objects — a 7× reduction that keeps the full object vocabulary within the reference image budget.

**Supported import formats** (centralized in `config.py`):
- **Image formats** (`IMAGE_EXTENSIONS`): .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga (Targa), .ico, .svg
- **3D model texture extraction** (`MODEL_EXTENSIONS_WITH_TEXTURES`): .glb (binary glTF), .gltf (JSON glTF) — embedded textures (base64 data URIs, binary buffer chunks) and external texture references are extracted automatically via `backend/services/texture_extractor.py`

**How 3D model extraction works**: During directory import, after scanning for image files, the system also scans for .glb/.gltf files and extracts embedded textures. The `texture_extractor.py` service parses glTF JSON (base64 data URIs, external file references) and GLB binary containers (buffer view chunks). Extracted textures are saved as **copies** (not symlinked, since they come from binary data). Filenames are prefixed with the model name to avoid collisions (e.g. `castle_texture0.png`).

**Local imports use symlinks** (not copies) to avoid disk duplication for standard image files. S3 imports download files to the references folder; the S3 client paginates through all objects (handles >1000 keys). Browser uploads copy files normally. Filenames from different subdirectories are **deduplicated** by prefixing with the parent directory name when collisions are detected. The total reference image count is capped at `max_reference_images` (default 100, env: `ARTSMOKER_MAX_REFERENCE_IMAGES`). Optionally auto-triggers Claude Opus style analysis after import.

### 4.2 Two-Level Asset Generation Pipeline

The generation system produces images across two dimensions:

- **Options** (1-5, default 5): Distinctly different creative concepts generated by Claude Opus. Each option has a completely different design prompt — different visual approaches, moods, silhouettes, and aesthetics.
- **Variations** (1-5, default 5): Seed variations of each option. Same prompt, different random seeds passed to the image generator.
- **Total images** = `num_options` x `num_variations` (up to 25 images per batch).

**"All Available Models" mode** (`all_models: true`): Generates with every enabled image model instead of a single model. Each model becomes an "option" with 1 variation. Models run independently — no shared canary, no cooperative cancellation. Moderation blocks on one model don't affect others. The pipeline is handled by `_run_all_models_generation()` in `generate.py`.

- Models are ordered by moderation strictness (least strict first: SD 3.5 Large → Stable Image Ultra → Titan Image → Nova Canvas) for optimal throughput.
- **Same prompt mode** (default): One prompt refined once, sent to all models for direct comparison.
- **Model-optimized mode** (`model_optimized_prompts: true`): Prompt is refined separately per model (e.g., SD 3.5 Large gets quality boosters, Nova Canvas gets structured captions).
- Per-model results include `status` ("success", "moderation_blocked", "error"), `status_detail` (error message), and the specific `image_model`/`model_label` used.
- SSE events include `model_status` (per-model as each completes) and `all_models_summary` (in the `complete` event).
- Per-variant `metadata.json` stores the actual model used (`image_model`, `model_label`, `all_models: true`).

```
User prompt: "hospital building"
         |
         v
    [Concept Generation — Claude Opus 4.6 (complex)]
    If num_options > 1: generate_concept_prompts() produces N distinctly
    different design interpretations as a JSON array of prompt strings.
    If num_options == 1: refine_prompt() (Claude Sonnet, fast) produces
    a single refined prompt. Marketing banners use refine_marketing_prompt()
    (Claude Opus, complex).
    Claude extracts exclusions to a separate "NEGATIVE:" line during refinement.
         |
         v
    [Model-Optimized Prompt Engineering]
    Prompt is restructured as a descriptive CAPTION (not a command) per target model:
    - Nova Canvas: caption style, Subject→Environment→Pose→Lighting→Camera→Style, 900 chars
    - Titan Image v2: concise captions, 480 chars
    - SD 3.5 Large: quality boosters (masterpiece, best quality), style tokens, 2000 chars
    - Stable Image Ultra: photorealistic quality boosters, 2000 chars
    Negative prompt parsed by _parse_negative_prompt() and passed through pipeline.
         |
         v
    For each concept prompt, generate num_variations images in parallel:
         |
         v
    [Image Generation — Nova Canvas, Titan Image, Stable Diffusion 3.5 Large, or Stable Image Ultra]
    Input: refined prompt + negative prompt + random seed per variation
    Output: PNG image (default 1024x1024)
         |
         v
    [Post-Processing Pipeline]
    1. Background removal (Stability AI Remove Background) — optional
    2. Upscale (Stability AI Creative Upscale) — optional
    3. SVG conversion (vtracer → potrace → Pillow fallback) — optional
         |
         v
    Output per variant: PNG (transparent) + SVG, stored with smart filenames
```

**Parallel execution**: All option-variation combinations are dispatched to a `ThreadPoolExecutor` with `max_workers=min(total, 5)` (reduced to 3 when upscale is enabled) to limit Bedrock API throttling.

**Image generation retry**: Each image generation call retries up to 3 times with exponential backoff (2s, 5s, 9s + jitter) on throttling, rate-limit, service-unavailable, and connection errors. This ensures that large batches (e.g. 5×5 = 25 images) don't lose variants to transient API throttling. Retry status is streamed to the frontend in real-time.

**Real-time progress via SSE**: The `POST /api/generate/stream` endpoint uses Server-Sent Events (SSE) for real-time progress updates during generation. The response is `text/event-stream` with JSON payloads on `data:` lines. A `": keepalive"` comment is sent periodically to prevent connection timeout. Complete event types:

| Event type | Payload | When emitted |
|------------|---------|--------------|
| `started` | `{batch_id}` | Generation begins |
| `stage` | `{stage: "prompts"\|"canary"\|"generating"\|"finalizing", message}` | Pipeline phase transitions |
| `prompts_ready` | `{prompts: [...], pre_composed: bool}` | Concept prompts generated — frontend displays in composed area |
| `canary` | `{message}` | Canary test starting |
| `image_done` | `{completed, total, option_index, variant_index}` | One image finished |
| `image_error` | `{option_index, variant_index, error}` | One image failed |
| `throttled` | `{delay, message}` | API throttled — waiting before retry |
| `retry` | `{attempt, max_attempts, message}` | Retrying after throttle |
| `moderation_blocked` | `{error, option_index, variant_index}` | Moderation rejected an image |
| `prompt_refused` | `{reason, original_response, message}` | Claude declined to refine prompt |
| `complete` | `{result: GenerationResult, prompt_refused?: bool}` | Pipeline finished |
| `model_status` | `{model, model_label, option_index, status, status_detail, completed, total}` | Per-model result in "All Models" mode |
| `error` | `{detail}` | Unrecoverable error |

**Smart filenames**: Each generated image gets a human-readable filename derived from the user's prompt slug plus the option/variation indices: `a-fierce-dragon_opt1_var2.png`. These filenames are stored in per-asset `metadata.json` and served via `Content-Disposition` headers on the gallery file endpoints.

**Dynamic prompt length limits by model**: Each image model has a different prompt capacity, stored in the model registry (`prompt_limit` field per model):

| Model | Prompt Limit (chars) |
|-------|---------------------|
| Nova Canvas | 900 |
| Titan Image v2 | 480 |
| Stable Diffusion 3.5 Large | 2000 |
| Stable Image Ultra | 2000 |

The active limit is passed to all prompt refinement functions (`refine_prompt()`, `refine_marketing_prompt()`, `generate_concept_prompts()`) and adjusts automatically when the user switches models. Stable Diffusion 3.5 Large and Stable Image Ultra get 2x richer prompts with more room for detail, composition, and quality directives. A hard truncation fallback (breaking on word boundaries) still applies per model.

**Model-optimized prompt engineering**: Prompts are written as descriptive **captions**, not imperative commands, following the structure recommended by [AWS Nova Canvas documentation](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html): Subject, Environment, Pose/Action, Lighting, Camera angle, Style. Negation words ("no", "not", "without", "DO NOT") are removed from the main prompt — exclusions are separated into a dedicated negative prompt instead. Model-specific instructions are injected per target model:

| Model | Prompt Style | Key Optimizations |
|-------|-------------|-------------------|
| Nova Canvas | Structured caption | Subject→Environment→Pose→Lighting→Camera→Style order, quality markers, 900 char limit |
| Titan Image v2 | Concise caption | Shorter descriptive phrases, 480 char limit |
| Stable Diffusion 3.5 Large | Rich caption with boosters | Quality boosters (masterpiece, best quality), style tokens (concept art, artstation), 2000 char limit |
| Stable Image Ultra | Photorealistic caption | Photorealistic quality boosters, cinematic lighting descriptors, 2000 char limit |

**Negative prompt support**: All four image models receive a negative prompt parameter alongside the main prompt. Negative prompts are extracted through multiple mechanisms:

1. **Single-option refinement**: `refine_prompt()` instructs Claude to output a `NEGATIVE:` line, parsed by `_parse_negative_prompt()`.
2. **Multi-option concept generation**: `generate_concept_prompts()` applies two extraction layers:
   - Checks if the AI returned a `NEGATIVE:` entry as the last item in the JSON array.
   - Post-processes each concept prompt with `_strip_negation_phrases()` — a regex-based extractor that finds embedded negation patterns ("No X", "not Y", "without Z", "DO NOT include W") and strips them from the main prompt, collecting the negated terms into a shared negative prompt. Terms are deduplicated via `_deduplicate_negative()`.
3. **Pre-composed prompts**: When the user clicks "Preview Enhanced Prompt" first, the `/api/refine-prompt` endpoint returns `negative_prompt` in its response. The frontend sends this back in the `GenerationRequest.negative_prompt` field so it survives the pre-composed path (which skips backend refinement).

The negative prompt is stored in per-variant `metadata.json`, included in SSE events (`prompts_ready` and `complete`), and displayed in the ImageStudio (red-labeled "Negative prompt — exclusions sent to model" section) and AssetViewer (metadata tab). Per AWS documentation, negation words should not appear in negative prompts either — only the terms to exclude (e.g. "blurry, text, watermark" not "no blurry, no text").

| Model | Negative Prompt Parameter |
|-------|--------------------------|
| Nova Canvas | `negativeText` in `textToImageParams` |
| Titan Image v2 | `negativeText` in `textToImageParams` |
| Stable Diffusion 3.5 Large | `negative_prompt` field |
| Stable Image Ultra | `negative_prompt` field |

Negative prompts are stored in per-variant `metadata.json` as `negative_prompt`.

**Content moderation handling — smart model switching**: When an image generation call fails due to the model's built-in content moderation filters, the system uses a tiered recovery strategy:

1. **Try alternative models FIRST** (preserving the prompt): When the selected model blocks a prompt, the system tries other image models that may have more relaxed moderation. The prompt stays unchanged — only the model switches. If an alternative model accepts the prompt, a **model switch dialog** (emerald-themed) informs the user and offers one-click switching. A "Rewrite for [original model]" option is also available.
2. **Rewrite as LAST RESORT**: Only when ALL available models reject the prompt does the system invoke `POST /api/generate/analyze-moderation` to analyze and rewrite. A **rewrite dialog** (amber-themed) presents the suggested safe rewrite in an editable textarea with specific issues listed, a verified/unverified badge, attempt log, and the original prompt in a disclosure.
3. **Pre-check toggle** ("Prompt Pre-Check"): Enabled by default. Pre-screens prompts via the fast LLM before any image generation. A **pre-check dialog** (indigo-themed) proactively warns the user about likely moderation issues with specific concerns listed. Options: switch to a recommended model, **rewrite for the current model**, proceed anyway, or cancel. Auto-disabled when IP ownership/licensing is declared. Internally skipped (one-shot `_skipPreCheck` flag) when the user has already reviewed and accepted a model switch or rewrite — the flag resets after one generation so subsequent requests are pre-checked normally.
4. **Prompt refusal detection**: Catches LLM refusal responses during prompt refinement and shows a **prompt refusal dialog** (red-themed) with the actual AI response (up to 500 chars) and a clear explanation instead of sending garbage to the image model.

**Prompt rewrite implementation**: The `POST /api/generate/analyze-moderation` endpoint supports two modes controlled by the `force_rewrite` flag:

- **`force_rewrite: false`** (default) — Two-phase approach: Phase 1 tries the same prompt on alternative models ordered by permissiveness. If one accepts, returns `action: "switch_model"` with the working model. Only if ALL models reject does Phase 2 (rewrite) run.
- **`force_rewrite: true`** — Skips Phase 1 entirely. Goes straight to rewrite and tests the rewrite against the **target model specifically** (not the most permissive model). Used when the user explicitly chooses "Rewrite for [model]" from any dialog.

**Issue-driven rewrite**: The rewrite LLM prompt is composed from the specific issues identified by the pre-check or the model rejection — not from hardcoded rules. The detected issues (e.g. "copyrighted IP references", "explicit violence", "adult content") are passed directly to the LLM with generic handling rules:
1. Address each specific issue identified — do not ignore any
2. For copyrighted IP: replace with original descriptions that capture the same visual energy
3. For copyrighted character traits/abilities: replace with generic equivalents
4. For violence/aggression: reframe as dynamic action poses and combat stances
5. For adult/inappropriate content: remove or replace with tasteful alternatives
6. Preserve all visual style directives, composition, and quality parameters
7. Rewrite must be substantially different — not minor word changes
8. Keep under 900 characters

The rewrite is tested via canary image generation (up to 3 attempts with iterative refinement). If the canary passes, `verified: true` is returned. If all attempts fail, the best rewrite is returned with `verified: false`.

**Rewrite presentation**: The rewrite result is shown **inside the dialog** (not auto-closed) with:
- Editable textarea containing the rewritten prompt
- Verified/not-verified badge
- Amber best-effort disclaimer: *"This is an automated attempt to make your prompt compatible with [model]'s moderation policy. It is not guaranteed to be accepted — the model performs its own independent assessment that may still reject the prompt."*
- "View original prompt" disclosure
- "Use This Rewrite & Review" button to accept

**Rewrite never overwrites the user's original prompt.** The rewritten text is placed in the **enhanced/composed prompt area** via `PromptEditor.setComposedText()`, leaving the original prompt textarea untouched. A persistent amber disclaimer (`#gen-rewrite-disclaimer`) appears in the prompt info section. The disclaimer clears when a new generation starts. The user must review the enhanced prompt and click Generate themselves — no auto-generation after rewrite.

All prompts are stored in metadata: `original_prompt` (what the user typed), `prompt` (what was sent to the image model), `negative_prompt`, and `moderation_original` (pre-rewrite prompt when a rewrite was accepted). This provides full audit trail for every generated asset.

Non-retriable errors (content moderation, policy blocks) are detected and skip the retry loop entirely. The generic image model invoker (`invoke_image_model`) returns the actual error message from the model instead of crashing with a `KeyError` on missing image data.

**Canary request and batch cancellation**: Before dispatching the full parallel batch, the system generates a single "canary" image first using the first option's prompt. The canary counts as option 0, variation 0 (`o0_v0`) — if it passes, it becomes the first variant in the results (not wasted). If the canary is blocked by content moderation, the entire batch stops immediately — costing only 1 wasted API call instead of N×M×3 (options × variations × retry attempts). If the canary passes, the remaining tasks dispatch in parallel with a shared `threading.Event` cancel flag. If any task in the parallel batch encounters a non-retriable moderation error, it sets the cancel flag and all remaining tasks skip their API calls. When a batch is partially completed then blocked, **already-generated variants are cleaned up** (deleted from disk) so the user doesn't see orphaned partial results. This two-phase approach (canary + cooperative cancellation) minimizes wasted API spend on prompts that will be rejected across the board.

**Error classification**: The system classifies image generation errors by string-matching the error message to determine if an error is a non-retriable moderation block (contains terms like "moderation", "blocked", "content policy", "not allowed") vs. a transient error (throttling, timeout, connection) that should be retried. Non-retriable errors skip the retry loop entirely and trigger the moderation recovery flow.

### 4.3 Strong Asset-Type Differentiation

Each `AssetType` has detailed structural directives in `prompt_engineer.py` covering five dimensions. These are injected into the prompt template with instructions to follow them as **guides**, not rigid templates. The same user prompt produces fundamentally different images depending on the asset type.

**Smart prompt refinement — "USER INTENT IS KING"**: The prompt refinement pipeline treats the user's explicit words as the highest-priority signal, overriding style guide defaults and asset type templates when they conflict:

- **User overrides style**: If the user says "real-world like" but the style guide says "toylike", the user's intent wins. The style guide informs the general aesthetic, but explicit user directives take precedence.
- **User overrides asset type**: If the user describes something that doesn't match the rigid asset type template (e.g. a tileable pattern selected under "game_asset"), the AI intelligently interprets what the user is actually describing — isolated object vs tileable panel vs scene vs texture — rather than forcing the template structure.
- **Asset type is a GUIDE**: The structural directives (composition, framing, technical approach) are starting points that the AI adapts based on the user's description, not a rigid mold.
- **Prompt refusal detection**: The system catches Claude "I'm sorry" / refusal responses during refinement and surfaces a clear dialog to the user instead of silently sending the refusal text as an image prompt.

| Asset Type | Key Directives |
|---|---|
| `game_asset` | **OUTPUT**: In-game sprite/tile/object. **COMPOSITION**: Single object, centered, isolated on transparent background. **FRAMING**: Straight-on or style's canonical perspective, fill 70-80% of frame. **TECHNICAL**: Clean sharp edges, consistent lighting (top-left default), no ground shadows. **DO NOT**: Include text, UI, multiple objects, or scene backgrounds. |
| `marketing_banner` | **OUTPUT**: Promotional banner. **COMPOSITION**: Full-scene illustration, reserve left/right third as text-safe zone (must be empty for post-production overlay), strong focal point opposite. **FRAMING**: Wide/cinematic feel, camera pulled back. **TECHNICAL**: Rich saturated colors, dramatic lighting, depth-of-field. **NO TEXT** — do not render any text, letters, words, or typography; the text-safe zone must remain empty. **DO NOT**: Make it sparse or icon-like. Marketing prompt template also strips text requests from the user prompt and instructs Claude to ignore title/text mentions. |
| `icon` | **OUTPUT**: App/UI/button icon. **COMPOSITION**: Single bold recognizable symbol, centered with 15% padding. **FRAMING**: Front-facing or slight 3/4 tilt. **TECHNICAL**: Must read at 64x64, high contrast, 3-5 colors, bold shapes. **DO NOT**: Add complexity, fine detail, or scene context. |
| `character` | **OUTPUT**: Character design/portrait. **COMPOSITION**: Full/3/4-body, slightly off-center, facing viewer or 3/4 view. Isolated on clean background. **FRAMING**: Fill 60-75% vertical, head-to-toe or head-to-knee. **TECHNICAL**: Strong readable silhouette, expressive pose, consistent lighting. **DO NOT**: Crop limbs awkwardly, add backgrounds, include multiple characters. |
| `environment` | **OUTPUT**: Environment/background/landscape. **COMPOSITION**: Full scenic illustration with foreground/midground/background depth layers, leading lines. **FRAMING**: Wide establishing shot, horizon at upper/lower third. **TECHNICAL**: Atmospheric perspective, environmental storytelling, mood-setting lighting. **DO NOT**: Make it flat or icon-like. |

### 4.4 Result Model Structure

**Pydantic models** (`backend/models/generation_result.py`):

```
GenerationResult
├── id: str                      # Batch UUID
├── prompt: str                  # Original user prompt
├── original_prompt: str | None  # Pre-AI-improvement prompt
├── style_id: str | None
├── asset_type: str
├── image_model: str
├── width: int
├── height: int
├── num_options: int
├── num_variations: int
├── options: list[OptionResult]
│   ├── option_index: int
│   ├── refined_prompt: str      # The concept-specific prompt
│   └── variants: list[VariantResult]
│       ├── id: str              # "{batch_id}_o{opt}_v{var}"
│       ├── variant_index: int
│       ├── png_path: str        # API URL: /api/gallery/{id}/png
│       ├── svg_path: str | None # API URL: /api/gallery/{id}/svg
│       ├── png_filename: str    # Smart name: "prompt-slug_opt1_var2.png"
│       └── svg_filename: str | None
└── created_at: datetime
```

Each variant is stored in its own directory under `data/generated/{asset_id}/` with `asset.png`, optionally `asset.svg`, and `metadata.json`. The metadata per variant stores: `original_prompt`, `moderation_original` (pre-rewrite prompt when applicable), `negative_prompt` (extracted exclusion terms), `num_options` and `num_variations` (generation-time batch dimensions — used for partial batch tracking after deletions), IP declaration fields (`ip_owned`, `ip_licensed`), and all other generation parameters. Full prompt lineage is: `original_prompt` (user's raw input) → AI-improved prompt → `moderation_original` (if rewritten to pass moderation) → `prompt` (final prompt sent to the image model) + `negative_prompt` (exclusion terms sent separately).

**Style snapshot in metadata**: Each generated asset (from 2D Image Studio, Video Studio, and Type Studio) stores a `style_snapshot` object capturing the style's state at generation time:
```json
{
  "style_snapshot": {
    "name": "Isometric City Builder",
    "description": "Low-poly isometric city buildings",
    "generation_hints": "Isometric low-poly game asset, flat shading...",
    "analyzed_style": { "perspective": "...", "palette": [...], ... }
  }
}
```
This ensures that if the original style profile is later deleted or modified, the asset retains the full style context that was used during its creation. The AssetViewer shows the style name from `style_snapshot` as a fallback when the original style no longer exists. The gallery batch endpoint (`GET /api/gallery/batch/{batch_id}`) includes the `style_snapshot` in each variant's metadata.

**GalleryItem** — a flat summary model for the gallery listing endpoint:
- id, prompt, style_id, asset_type, png_url, svg_url, created_at.

### 4.5 Voice Input (Nova Sonic)

- Browser captures audio via `MediaRecorder` API (WebM/Opus format).
- Audio file sent to backend `POST /api/transcribe/` as a multipart upload.
- Backend attempts Nova Sonic bidirectional streaming transcription (`invoke_model_with_bidirectional_stream`).
- **Current limitation**: Nova Sonic requires the bidirectional streaming API, which depends on a compatible boto3 version. If the streaming API is unavailable, access is denied, or the API call fails, the service returns a placeholder message indicating audio was received but transcription requires streaming setup. Full transcription works when Nova Sonic streaming is properly configured in the us-east-1 region.
- Transcribed text displayed in prompt editor for user review/editing.

### 4.6 Frontend Design

Clean, modern single-page application served as static files mounted at `/` by FastAPI.

**Navigation**: The top nav shows the ArtSmoker logo with the tagline "Smoke-testing your artwork!" followed by five views in order: **Style Library** (`#styles`) → **2D Image Studio** (`#image-studio`) → **Type Studio** (`#type-studio`) → **Video Studio** (`#video-studio`) → **Gallery** (`#gallery`).

**No Claude branding in frontend**: All user-facing UI references use "AI" generically — never "Claude". For example, buttons say "AI Improve" not "Claude Improve", and labels say "AI-improved prompt" not "Claude-improved prompt". Image model names use their full display names: "Stable Diffusion 3.5 Large" (not "SD 3.5 Large").

**DOM caching router**: Views survive navigation. Each view's DOM is cached and shown/hidden instead of destroyed/recreated on route changes. `window.resetView(route)` destroys the cache for a specific view to force a fresh start.

**No-cache middleware**: During development, frontend static files are served with no-cache headers to ensure changes are reflected immediately.

**Client-side error logging**: All toast errors/warnings and unhandled JS errors are sent to `POST /api/log` and logged server-side with a `[CLIENT]` prefix for unified debugging.

**Style Library** — Grid of style profiles with thumbnails. Upload new styles, upload reference images, trigger AI analysis.
- **Create modal**: Includes "Import References From" section with Local and S3 browse buttons for importing reference images at creation time.
- **Detail view**: Has an "Import & Analyze" button (always auto-analyzes after import, no toggle). The analysis button is contextual: "Analyze Style" when no analysis exists, "Re-Analyze Style" when one does.
- **Server-side file browser modal**: Used for both local and S3 browsing. Single-click selects a file/folder, double-click navigates into a directory. Back button and ".." entry navigate to the parent directory.

**2D Image Studio** (`#image-studio`) — The main image generation workspace with a two-tier result display:
- **Left sidebar** (progressive disclosure layout):
  - **Art Style** selector, **Asset Type** selector.
  - **Image Model** dropdown — populated dynamically from the registry (`GET /api/admin/models/image-options`), not hardcoded. Includes "All Available Models" at the bottom. Below the dropdown, a smart **summary line** shows the active configuration: `us-east-1 · Premium · $0.06/img` — updates on any change.
  - **Dimensions** (size presets: 512×512, 768×768, 1024×1024, 1024×576, 576×1024, 1280×720).
  - **Advanced** (collapsible `<details>` section): **Quality** dropdown — shows quality tiers when the model supports them (e.g. Standard/Premium for Nova Canvas, "Default" for models without tiers). **Region** dropdown — shows the model's available regions sorted cheapest-first, with per-image pricing. "Auto" selects the cheapest. Quality and region changes update the summary line and pricing.
  - **Cost estimate**: `Est. cost: ~$1.50 (25 images × $0.06)` — updates dynamically based on model, quality, region, options, and variations.
  - **Options** count (1-5), **Variations** count (1-5).
  - When **"All Available Models"** is selected: options/variations are disabled (fixed at 1 per model), a "Model-optimized prompts" toggle appears, and info text shows the model count.
  - **"Model Settings"** button opens the Model Registry admin UI (see [4.11 Model Registry](#411-model-registry)).
- **Processing options**: Toggle switches for Remove Background, SVG Conversion (on by default), Upscale, and **Prompt Pre-Check** (pre-screens prompts via Claude Sonnet before image generation). Options row is placed **below** the prompt areas (images grouped together). Before generation these are labeled **"Pre-Processing"** (applied during generation). After generation completes, the label switches to **"Post-Processing"** and an **"Apply to Current Results"** button appears, allowing users to re-apply processing to the existing generated images without re-generating (calls `POST /api/generate/post-process`).
- **Two-area prompt editor** (center panel): The prompt editor uses a two-textarea design:
  - **Top textarea** (user input): Where the user writes their prompt. This area is **never overwritten** by the system — it always contains the user's original words.
  - **"Preview Enhanced Prompt" button**: Optional pre-generation preview. Creates an AI-enhanced version in a second area below, combining user prompt + style guidelines + asset type directives + AI-enhanced details. **Model-aware**: optimized for the selected image model. Changing the model clears the composed prompt.
  - **Auto-enhancement on Generate**: If the user clicks Generate without previewing, the backend **automatically enhances** the prompt and shows the result in the composed area via SSE (`prompts_ready` event). The button is for pre-review only — generation always works without it.
  - **Composed prompt area** (green-tinted, below): Displays the AI-composed generation prompt. This is what gets sent to the image model.
  - **Flow**: If a composed prompt exists, it is sent directly (no double-refinement). If not, the backend auto-refines during generation. Editing the original prompt clears the composed area.
  - **Prompt Editor DOM fix**: `document.contains()` check ensures the textarea is in the live DOM after view reset, preventing stale references.
  - **Prompt info section**: After generation, shows: original prompt, AI-improved prompt, **negative prompt** (red-labeled "exclusions sent to model", hidden when empty), and concept prompts for full lineage visibility.
  - Voice input and `loadBatch(batchId)` restore a previous batch from the Gallery into the 2D Image Studio view. `ensurePromptEditor()` is called on show/loadBatch for robust initialization. The loadBatch navigation uses a yield-then-poll pattern: sets the hash, yields to let the `hashchange` event fire, polls for a DOM element (up to 10s), then adds a 200ms settling delay to let `init()`/`onShow()` finish before writing batch data into the DOM. For partial batches (where some variants were deleted from Gallery), the toast shows "X of Y images remaining (Z deleted)" instead of the normal batch summary.
- **Options row** (indigo/accent borders): Shows different creative concepts as thumbnail cards. Each card shows the first variation as a preview, the option number badge (or model name in "All Models" mode), and a truncated concept prompt. In "All Models" mode, the header changes to "Models — comparison across image models", and blocked/failed models show a semi-transparent overlay badge ("Blocked — moderation" or "Failed"). Click to select an option — the **"Generated prompt — Option N"** (or **"Generated prompt — Nova Canvas"**) section updates with the exact prompt and negative prompt used for that option.
- **Concept prompt display**: Shows the full refined prompt for the selected option.
- **Variations row** (emerald borders): Shows seed variants of the selected option. Click to select a variation.
- **Main preview**: Large preview of the selected variant with checkerboard transparency background.
- **Download bar**: Shows the smart filename (e.g. `a-fierce-dragon_opt1_var2.png`) and provides PNG + SVG download buttons using the human-readable filenames.

If there is only one option, the options row is hidden. If there is only one variation, the variations row is hidden.

- **Content moderation dialogs** — four distinct themed modals handle different moderation scenarios:
  - **Pre-check dialog** (indigo): Proactive warning before generating, shown when "Prompt Pre-Check" is enabled and the LLM detects likely moderation issues. Lists specific concerns. Options: switch to recommended model, **rewrite for current model**, proceed anyway, or cancel.
  - **Model switch dialog** (emerald): Appears when the prompt was blocked by the selected model but works with an alternative. Shows which model works and why, with a full attempt log ("View N model tests"). Also offers "Rewrite for [original model]" as an alternative.
  - **Rewrite dialog** (amber): Appears only when ALL models reject the prompt (last resort). Displays AI-analyzed issues, a friendly explanation, an editable rewritten prompt (via `POST /api/generate/analyze-moderation`), verified/unverified badge, collapsible original prompt, and rewrite attempt log. The **"Review Rewritten Prompt"** button places the rewrite in the enhanced prompt area (not the original textarea) with a persistent disclaimer.
  - **Prompt refusal dialog** (red): Appears when the LLM declines to refine a prompt (e.g. requests involving real people). Shows the actual AI response text (up to 500 chars) and common trigger categories.
  - **All rewrite paths**: The rewritten prompt is placed in the composed/enhanced area via `setComposedText()`, never overwriting the original. A persistent amber disclaimer (`#gen-rewrite-disclaimer`) warns that the rewrite is still subject to the model's own moderation. The user must review and click Generate — no auto-generation after rewrite. The disclaimer clears when a new generation starts.
  All dialogs are non-destructive — they recommend actions and the user decides whether to accept, edit, or dismiss.

- **IP Declaration** — "Intellectual Property (IP) Declaration" section in the Image Studio sidebar:
  - Two checkboxes: "I/We own this IP" and "I/We have a license for this IP".
  - When checked with a strict model selected (Nova Canvas or Titan Image): shows a recommendation to switch to SD 3.5 Large with a "Switch now" quick-action link.
  - **Pre-Check toggle disabled** when IP is declared — the user asserts they have rights, so pre-screening is unnecessary.
  - IP declaration stored in per-variant `metadata.json` (`ip_owned`, `ip_licensed`) for audit trail.
  - Shown in AssetViewer metadata display.
  - In moderation dialog: acknowledges the IP claim and explains platform limitation.
  - Note: Nova Canvas moderation is platform-enforced by AWS and cannot be bypassed regardless of IP ownership.

**Type Studio** (`#type-studio`) — Full text overlay system for creating titled/branded versions of gallery images or standalone text compositions.

- **Two modes**:
  - **"On Image"** — Composites text onto a selected gallery image. User picks a base image from the gallery as the background.
  - **"Standalone"** — Renders text on a transparent background (no base image).

- **Multi-line text editor**: Users enter one or more lines of text. Each line supports:
  - Individual **font selection** from the font picker.
  - **Position hints** (e.g. top-center, bottom-left) to guide AI layout placement.
  - **Voice input** — mic button per line. Click to record, click again to stop. Audio transcribed via the voice model configured in the registry (`categories.voice`). Transcribed text appended to the line.

- **AI layout suggestion**: The backend (`POST /api/type-studio/suggest`) uses the configured LLM to suggest text layout parameters including position, size, color, and effects for each line. Returns **1-5 layout options** representing different creative directions. The **LLM model** used is configurable via a collapsible "AI Model for layout" dropdown — "Complex LLM" (default, highest quality) or "Fast LLM" (cheaper). Both read from the registry (`categories.complex_llm` and `categories.fast_llm`). The `llm_complexity` field in the request controls which is used.

- **Pillow rendering**: The backend (`POST /api/type-studio/preview`) renders the final composition using Pillow with support for **shadow**, **outline**, and **glow** text effects. The rendered result is saved as a new gallery asset.

- **Click to zoom**: Clicking the result preview opens the AssetViewer with full zoom/pan, metadata, download buttons, and the Edit tab (inpaint/outpaint/erase/replace/recolor).

- **Font picker**: Shows fonts in priority order:
  1. **Style-specific fonts** — fonts associated with the selected style profile.
  2. **Bundled fonts** — 8 OFL-licensed Google Fonts shipped in `data/fonts/`: Roboto, Open Sans, Lato, Montserrat, Playfair Display, Oswald, Raleway, Source Code Pro.
  3. **System fonts** — detected from the host OS (macOS: `/System/Library/Fonts`, `/Library/Fonts`, `~/Library/Fonts`; Linux: `/usr/share/fonts`, `/usr/local/share/fonts`, `~/.fonts`).
  4. **Client-side fonts** — detected from the user's browser via the Local Font Access API (`queryLocalFonts()`, Chrome/Edge) with a canvas-probing fallback for 30+ common font families. Client fonts are merged with server fonts, deduplicated by display name. This ensures artists see their local machine's fonts even when the server runs on a minimal EC2 instance.
  All fonts show a **live preview** in the picker dropdown. Served via `GET /api/type-studio/font-file/{source}/{filename}`.

**Type Studio Pydantic models** (defined inline in `backend/routers/typestudio.py`):
- `TextLine` — `text: str`, `font: str | None`, `position: str | None` (e.g. "top-center", "bottom-left")
- `TypeStudioRequest` — `source_image_id: str | None`, `style_id: str | None`, `lines: list[TextLine]`, `style_note: str | None`, `num_options: int = 1`, `llm_complexity: str = "complex"`, `remove_background: bool`, `generate_svg: bool`, `upscale: bool`
- `LayoutEffect` — `shadow: dict | None`, `outline: dict | None`, `glow: dict | None`
- `LayoutLine` — `text: str`, `x: int`, `y: int`, `font_size: int`, `color: str`, `font: str | None`, `anchor: str` (Pillow text anchor), `effects: LayoutEffect`
- `LayoutSpec` — `lines: list[LayoutLine]`, `canvas_width: int`, `canvas_height: int`
- `FontInfo` — `name: str`, `display_name: str`, `filename: str`, `source: str`, `path: str`, `preview_url: str`
- `FontListResponse` — `fonts: list[FontInfo]`

- **Processing options**: Same toggle switches as 2D Image Studio (Remove BG, SVG Conversion on by default, Upscale) with the same Pre-Processing → Post-Processing label behavior and "Apply to Current Results" button.

- **Gallery integration**: Results are saved as new gallery assets with full metadata (including `source: "type-studio"`, base image reference if applicable, text content, font choices, layout parameters, and `style_snapshot`). Assets created in Type Studio can be loaded back from the Gallery via an **"Edit in Type Studio"** button in the AssetViewer.

**Gallery** (`#gallery`) — Unified grid of all generated images and videos sorted newest-first. Features a **Media filter** (All / 2D Artwork / Video), style filter, asset type filter, and search. Images load immediately; videos display thumbnails with play overlay, VIDEO badge, and duration indicator. Click a video to open the player modal. Backend always reads metadata fresh from disk. Supports pagination via `limit` and `offset` query parameters. Auto-refreshes via `onShow()` when navigating back, and after image edits or video generation completes.
- **Search bar**: Instant filtering across prompts, style names, and asset types as the user types.
- **Multi-select**: Checkboxes on each asset card for bulk selection. A **"Delete Selected"** button triggers `DELETE /api/gallery/` with `{ids: [...]}` for bulk deletion.
- Click any asset to open the AssetViewer.

**AssetViewer** — Full-size preview with zoom/pan and image editing. Fetches full metadata from `GET /api/gallery/{id}` on open. Four tabs:

- **PNG tab** — zoom/pan viewer: mouse wheel to zoom (centered on cursor), click-drag to pan, Fit/1:1/+/- buttons. Active mode (Fit or 1:1) highlighted. Image starts at fit-to-view.
- **Edit tab** — five editing modes:
  - **Inpaint**: Canvas brush mask painter (adjustable brush size). Paint the area to edit → enter a prompt → select an inpainting model from the registry → Apply. Mask extracted as black/white image (white = edit area).
  - **Erase**: Same mask UI, no prompt needed — removes objects and fills background.
  - **Outpaint**: Directional pixel controls (left/right/up/down) + optional prompt. Extends the image.
  - **Replace**: Search & Replace — enter what to find and what to replace it with. Uses `stability_search_replace` format family.
  - **Recolor**: Search & Recolor — select an object and specify the target color. Uses `stability_search_recolor` format family.
  - Models populated dynamically from registry filtered by `model_purpose` (inpainting, erase, outpainting, search_replace, or search_recolor). Shows price per model.
  - **Replace original** checkbox (default: checked) — replaces the source image in-place. Uncheck to save as a new gallery asset instead. Metadata records the `source_image_id` and `edit_type` for provenance.
- **SVG tab** — SVG preview (hidden when no SVG exists).
- **Metadata tab** — full prompt lineage: original prompt → AI-improved prompt → generation prompt → negative prompt (amber-styled). Plus style (from `style_snapshot` fallback), asset type, image model (reads `model_label` from metadata), dimensions, seed, batch ID, option/variation, IP status, filename, created date. Adapts for Type Studio assets.
- **Previous / Next navigation** — arrow buttons and keyboard left/right arrows to navigate through the list of images (Gallery items, or ImageStudio options/variations). Context-aware: the list comes from wherever the viewer was opened (Gallery grid, ImageStudio batch, or TypeStudio results).
- **Contextual action buttons**:
  - **"2D Studio"** (indigo) — visible for image-type assets only. Sends the batch back to the 2D Image Studio view.
  - **"Add Text"** (emerald) — visible for image-type assets only. Opens Type Studio in "On Image" mode with this asset as the base image.
  - **"Edit in Type Studio"** (purple) — visible for type-studio assets only. Loads the asset back into Type Studio for re-editing.

### 4.7 Technology Choices

| Component | Technology | Reason |
|-----------|-----------|--------|
| Backend | FastAPI (Python 3.11+) | Async, fast, Pydantic models, auto-docs |
| Frontend | Vanilla JS + Tailwind CSS | No build step, fast to iterate, lightweight |
| AI Models | Bedrock (boto3) | Nova Canvas, Titan Image, Stable Diffusion 3.5 Large, Stable Image Ultra, Claude, Nova Sonic, Stability |
| SVG Conversion | vtracer (primary), potrace (fallback), Pillow (last resort) | Cascade of vector tracing methods |
| Text Rendering | Pillow (Python Imaging Library) | Text overlay composition with shadow, outline, glow effects |
| Storage | Local filesystem | Simple start, S3-compatible interface for later migration |

### 4.8 AWS Configuration

**Default AWS Profile**: None — uses the standard AWS credential chain (configurable via `ARTSMOKER_AWS_PROFILE`).

**Two-region architecture**:
- `us-west-2` (`aws_region_models`): Claude models, Stability AI models (including Stable Diffusion 3.5 Large, Stable Image Ultra).
- `us-east-1` (`aws_region_images`): Nova Canvas, Titan Image, Nova Sonic.

**Bedrock client** (`backend/services/bedrock_client.py`):
- Lazy-initialized boto3 clients keyed by region with connection pooling (10 max pool connections).
- Adaptive retry configuration (3 max attempts).
- `invoke_llm(prompt, system, complexity, images, max_tokens, temperature)` — routes to Sonnet or Opus based on complexity parameter. Uses the Bedrock **Converse API** (supports text + vision inputs).
- `invoke_image_model(model_key, prompt, ...)` — generic image model invoker. Reads format family from the registry to build the request body dynamically. Handles all image services: text-to-image, inpainting, outpainting, erase, search & replace, recolor, style transfer, upscale, and remove background — with zero model-specific code.
- `_dimensions_to_aspect_ratio(width, height)` — maps pixel dimensions to the closest Stability AI supported aspect ratio.
- `_set_nested(obj, path, value)` / `_get_nested(obj, path)` — dot-notation helpers for building/reading nested request/response bodies.

**LLM Model Selection Logic:**
- `invoke_llm(complexity="fast")` routes to Sonnet (or whichever model is configured in the `fast_llm` registry category).
- `invoke_llm(complexity="complex")` routes to Opus (or whichever model is configured in the `complex_llm` registry category).

**Model fallback**: On `AccessDeniedException` from the primary LLM model, the system automatically falls back to the `fallback_llm` category model.

| Model | ID | Region | Purpose |
|-------|----|--------|---------|
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` | us-west-2 | Fast: prompt refinement, generation hints |
| Claude Opus 4.6 | `us.anthropic.claude-opus-4-6-v1` | us-west-2 | Complex: style analysis, concept generation, marketing copy |
| Claude 3.5 Sonnet v2 (fallback) | `anthropic.claude-3-5-sonnet-20241022-v2:0` | us-west-2 | Fallback on access denied |
| Nova Canvas | `amazon.nova-canvas-v1:0` | us-east-1 | Primary image generation |
| Titan Image v2 | `amazon.titan-image-generator-v2:0` | us-east-1 | Alternative image generation |
| Stability Remove BG | `us.stability.stable-image-remove-background-v1:0` | us-west-2 | Background removal |
| Stability Upscale | `us.stability.stable-creative-upscale-v1:0` | us-west-2 | Image upscaling |
| Stable Diffusion 3.5 Large | `stability.sd3-5-large-v1:0` | us-west-2 | Image generation (Stability AI) |
| Stable Image Ultra | `stability.stable-image-ultra-v1:1` | us-west-2 | Image generation (Stability AI premium) |
| Nova Sonic | `amazon.nova-2-sonic-v1:0` | us-east-1 | Speech-to-text |

> Note: Claude and Stability AI post-processing model IDs use **US inference profiles** (`us.anthropic.claude-sonnet-4-6`, `us.anthropic.claude-opus-4-6-v1`, `us.stability.stable-image-remove-background-v1:0`, `us.stability.stable-creative-upscale-v1:0`) rather than full versioned model IDs. Stable Diffusion 3.5 Large and Stable Image Ultra use **direct model IDs** (not inference profiles).

> Note: Stability AI generation models (Stable Diffusion 3.5 Large, Stable Image Ultra) use **aspect ratios** instead of exact pixel dimensions. The backend provides a `_dimensions_to_aspect_ratio()` helper that maps width×height to the closest supported ratio: 1:1, 16:9, 9:16, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21.

### 4.9 Post-Processing Pipeline

The post-processing pipeline (`backend/services/post_processor.py`) applies three optional steps in sequence:

1. **Background removal** — Stability AI Remove Background model. If it fails, the pipeline continues with the original image.
2. **Upscaling** — Stability AI Creative Upscale model. Takes the refined prompt as a quality guide. If it fails, the pipeline continues with the current image.
3. **SVG conversion** — Cascading approach:
   - **vtracer** (preferred): High-quality color vector tracing with configurable parameters (color precision 6, layer difference 16, speckle filter 4, etc.).
   - **potrace** (fallback): Monochrome bitmap tracing. Converts PNG to BMP via Pillow first.
   - **Pillow embedded raster** (last resort): Wraps the PNG as a base64 data URI inside an SVG element. Not a true vector but ensures SVG output is always available.

**Creative Upscale details**: Uses JPEG output format to avoid Stability AI's 16MB response payload limit, then converts back to PNG via Pillow. Includes retry with exponential backoff (up to **5 attempts** — more than image generation's 3 attempts, because upscale is more throttle-prone) for API throttling. Thread pool concurrency is reduced to 3 workers when upscale is enabled to avoid rate limits.

Each step is independently fault-tolerant — failures are logged but do not abort the pipeline.

### 4.10 Storage Layer

`LocalStore` (`backend/storage/local_store.py`) provides an S3-compatible interface over the local filesystem:

**Style storage** (`data/styles/{style_id}/`):
- `profile.json` — serialized StyleProfile.
- `references/` — uploaded reference images. Local directory imports are stored as **symlinks** to avoid disk duplication; S3 downloads and browser uploads are stored as copies. Textures extracted from 3D models (.glb/.gltf) are stored as **copies** (not symlinked, since they originate from binary data) with filenames prefixed by the source model name (e.g. `castle_texture0.png`).

**Key methods**:
- `link_reference_image(style_id, filename, source_path)` — creates a **relative symlink** (via `os.path.relpath()`) in the style's references folder pointing to the source file. Used by the local directory import path. Relative symlinks survive directory moves and work across machines (unlike absolute symlinks). S3 and browser uploads still copy files.

**Generated asset storage** (`data/generated/{asset_id}/`):
- `asset.png` — final processed PNG.
- `asset.svg` — optional SVG conversion.
- `metadata.json` — full generation metadata (prompt, refined_prompt, style_id, asset_type, seed, filenames, etc.).

Asset IDs follow the pattern `{batch_uuid}_o{option_index}_v{variant_index}`.

### 4.11 Model Registry

The model registry (`backend/model_registry.json` v2) is the **single source of truth** for all AI model configuration. No model data is hardcoded in application code — everything is read from this file at runtime. The registry is managed through the admin API and auto-discovery; it should never be edited manually.

**Registry structure** (v2):

1. **Format families** (`format_families`): Define request/response templates by provider. Each family specifies: `prompt_path`, `negative_prompt_path`, `seed_path`, `dimensions_mode` ("pixels" or "aspect_ratio"), `dimensions_paths`, `response_image_path`, and `body_template`. Currently 15 families covering all image services (`amazon_text_to_image`, `stability_text_to_image`, `amazon_inpainting`, `amazon_outpainting`, `stability_inpaint`, `stability_outpaint`, `stability_erase`, `stability_search_replace`, `stability_search_recolor`, `stability_control`, `stability_style_transfer`, `stability_remove_bg`, `stability_upscale`) and video generation (`nova_reel`, `luma_ray`). Adding a new provider or service means adding a format family — no code changes needed.

2. **Bedrock regions** (`bedrock_regions`): Cached list of all AWS regions supporting Bedrock (currently 33). Discovered dynamically during refresh-all via `boto3.Session().get_available_regions("bedrock")`. Read from cache for all other operations — zero AWS calls.

3. **Image pricing** (`image_pricing`): Per-model, per-region, per-quality pricing data from the AWS Pricing API. Fetched during refresh-all only. Keyed by `model_name|region|quality|size`. Used to display cost estimates in the UI and sort regions by cheapest-first.

4. **LLM categories** (`categories`): Named model slots for different purposes:
   - `fast_llm` — Claude Sonnet 4.6 (prompt refinement, hints, pre-check, cohesion check)
   - `complex_llm` — Claude Opus 4.6 (style analysis, concept generation, marketing copy, Type Studio layout)
   - `fallback_llm` — Fallback model on AccessDeniedException
   - `voice` — Nova Sonic (speech-to-text)

   Each category stores: `current` (the model ID), `region`, `provider`, `api_type`, `label`, `description`.

5. **Image models** (`image_models`): Keyed by internal name (e.g. `nova_canvas`, `sd35_large`). Each entry stores:
   - `label` — human-readable display name
   - `model_id` — Bedrock model identifier
   - `region` — default AWS region for invocation
   - `available_regions` — all regions where this model is available (populated by auto-discovery)
   - `provider` — e.g. "Amazon", "Stability AI"
   - `enabled` — whether the model is available for selection in the UI
   - `model_purpose` — `"text_to_image"` for generation models (filters out manipulation models like upscale, inpaint)
   - `format_family` — reference to a format family (e.g. `"amazon_text_to_image"`)
   - `prompt_limit` — maximum prompt characters (drives dynamic prompt sizing and truncation)
   - `moderation_strictness` — one of `very_strict`, `strict`, `moderate` (drives model ordering in All Models mode and smart model switching)
   - `quality_options` — array of `{value, label, body_override}` for models with quality tiers (e.g. Standard/Premium). Empty for models without tiers.
   - `default_quality` — the default quality tier value
   - `base_price_usd` — fallback per-image price when the Pricing API has no data
   - `extra_body` — model-specific body overrides deep-merged into the format family template (e.g. Nova Canvas `{"imageGenerationConfig": {"quality": "premium"}}`)

6. **Post-processing** (`post_processing`): Keyed by operation name (`remove_background`, `upscale`). Each stores: `label`, `model_id`, `region`, `provider`, `enabled`.

**Generic invoker** (`backend/services/bedrock_client.py: invoke_image_model()`): Reads the model's format family from the registry, constructs the request body dynamically using dot-path helpers (`_set_nested`, `_get_nested`, `_deep_merge`), applies quality overrides, gets the Bedrock client for the model's region (with `region_override` support), invokes, and parses the response. No per-model invoke functions needed — any model with a registered format family works.

**Auto-discovery** (`POST /api/admin/discover/refresh-all`):
1. Discovers all Bedrock-supported regions from AWS
2. Fetches per-image pricing from the AWS Pricing API
3. Resets all `available_regions` to empty (prunes stale data)
4. Scans each region — registers new text-to-image models (enabled=false), updates `available_regions` for existing models
5. Disables models no longer found in any region

This is the **only** operation that calls AWS discovery/pricing APIs. All other operations read from the cached registry file.

**Model validation**: The `GenerationRequest.image_model` field is a plain string validated against registry keys at runtime — not limited to a fixed enum. Dynamically added models are accepted without code changes.

**Frontend**: The model dropdowns in Image Studio and Video Studio are populated from `GET /api/admin/models/image-options` and `GET /api/admin/models/video-options` respectively on page load. No hardcoded model lists in JavaScript.

**Registry as single source of truth**: The application code contains **zero hardcoded model IDs, API parameters, or invocation templates**. Everything the system needs to invoke any Bedrock service — model IDs, regions, request body structures, prompt paths, negative prompt paths, mask paths, seed ranges, quality tiers, dimension modes, response parsing, pricing, and parameter constraints — is stored in `model_registry.json` and read at runtime. The format families define the complete API contract for each provider/service type, including a `parameters` spec with types, ranges, defaults, and descriptions for every configurable field. This means:

- Adding a new image model requires zero code changes — just register it via auto-discovery or the admin API
- Adding a new image service (e.g., a new Stability AI feature) requires adding a format family definition in `_DEFAULT_FORMAT_FAMILIES` in `model_registry.py` — the invoker and UI adapt automatically
- The LLM models used for prompt refinement, style analysis, and Type Studio layout are all configurable via `categories.fast_llm` and `categories.complex_llm` — the user can switch to any Converse-compatible model
- All pricing, regions, quality tiers, and model availability come from the registry — populated by auto-discovery and the AWS Pricing API during refresh-all

**Backward compatibility**: Generated assets reference model keys (e.g. `nova_canvas`), not raw Bedrock model IDs. Changing a model ID in the registry does not break old asset metadata.

## 5. API Reference

### 5.1 Styles

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/styles/` | Create a new style profile (name + description + optional generation_hints). ID is auto-generated as a slug. Returns 409 on duplicate. |
| GET | `/api/styles/` | List all style profiles. |
| GET | `/api/styles/{id}` | Get a single style profile by identifier. |
| PATCH | `/api/styles/{id}` | Partially update a style profile (name, description, analyzed_style, generation_hints). Auto-triggers re-analysis when `generation_hints` change (new value differs from previous). |
| DELETE | `/api/styles/{id}` | Delete a style profile and all its associated data (references, profile.json). |
| POST | `/api/styles/{id}/references` | Upload reference images (multipart file upload). Enforces max_reference_images limit (default 100). Auto-triggers re-analysis after upload. |
| GET | `/api/styles/{id}/references/{filename}` | Serve a reference image file. |
| POST | `/api/styles/{id}/import` | Import asset files from a local directory path or S3 prefix. Body: `{ "path": "/path/to/images", "auto_analyze": true }`. Scans recursively for image files (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) and 3D models (.glb, .gltf) with automatic texture extraction. Local image imports use symlinks (not copies); extracted textures are saved as copies. S3 imports download files (paginates through >1000 keys). Filenames are deduplicated by prefixing with parent/model name. Optionally triggers style analysis after import. |
| POST | `/api/styles/{id}/analyze` | Trigger AI style analysis on reference images. If the style has more than `max_analysis_images` (default 20) references, smart sampling selects a diverse subset. Two-phase analysis: Claude Sonnet cohesion check (8 images), then Claude Opus full analysis guided by cohesion level. Claude Sonnet generates hints. All persisted to the profile. |

### 5.2 Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate/` | Generate assets (full two-level pipeline). Returns `GenerationResult` with options and variants. Also available as `/api/generate/stream` for SSE streaming. |
| POST | `/api/generate/stream` | SSE streaming variant of generate — same pipeline, but streams real-time progress events. This is the primary endpoint used by the frontend. |
| POST | `/api/generate/post-process` | Apply post-processing to existing generated assets. Accepts asset IDs and processing flags (remove_background, generate_svg, upscale). Updates the assets in-place and refreshes their metadata on disk. Used by the "Apply to Current Results" button in the 2D Image Studio and Type Studio. |
| POST | `/api/generate/pre-screen` | Pre-screen a prompt for likely moderation issues before generation. Uses Claude Sonnet (fast, cheap). Returns whether the prompt is likely safe, specific issues, and a suggested alternative model if the prompt would work with a less strict model. |
| POST | `/api/generate/edit` | Image editing services: inpaint, outpaint, erase, search-replace, etc. Accepts `source_image_id`, `model` (registry key), `prompt`, `mask` (base64), `mask_prompt` (natural language, Nova Canvas), outpaint directions. Uses the generic invoker with the model's format family. Result saved as a new gallery asset with metadata linking to the source. |
| POST | `/api/generate/analyze-moderation` | Analyze a moderation-blocked prompt. Accepts `force_rewrite` (bool) — when false (default): Phase 1 tries alternative models, Phase 2 rewrites if all reject. When true: skips model switching, rewrites directly for the target model and tests against it. Returns `action`, `working_model`, `issues`, `explanation`, `rewritten_prompt`, `verified`, and `attempts` (log). |

**Pre-screen request body** (`PreScreenRequest`):
```json
{
  "prompt": "a warrior with a sword",
  "image_model": "nova_canvas"
}
```

**Pre-screen response**:
```json
{
  "likely_safe": false,
  "issues": ["weapon/combat language may trigger Nova Canvas moderation"],
  "explanation": "Nova Canvas is very strict about weapons and combat...",
  "suggested_model": "sd35_large",
  "suggested_model_label": "Stable Diffusion 3.5 Large"
}
```

On failure, pre-screen returns `{likely_safe: true}` as a safe default (don't block generation if pre-screening itself fails).

**Moderation analysis request body** (`ModerationRequest`):
```json
{
  "prompt": "the flagged prompt text",
  "error_message": "the error message returned by the image model",
  "image_model": "nova_canvas",
  "width": 512,
  "height": 512
}
```

**Moderation analysis response** — multi-phase, returns different actions:
```json
{
  "action": "switch_model",
  "working_model": "sd35_large",
  "original_model": "nova_canvas",
  "issues": ["weapon reference"],
  "explanation": "Your prompt works with a different model...",
  "rewritten_prompt": null,
  "verified": true,
  "attempts": [{"model": "sd35_large", "result": "success"}, {"model": "stable_image_ultra", "result": "skipped"}]
}
```
Or when all models reject (rewrite fallback):
```json
{
  "action": "rewrite",
  "working_model": null,
  "issues": ["copyrighted character name", "explicit violence"],
  "explanation": "The prompt was flagged because...",
  "rewritten_prompt": "An armored fantasy warrior with a glowing sword...",
  "verified": true,
  "attempts": [{"model": "sd35_large", "result": "blocked"}, {"model": "nova_canvas", "result": "blocked"}]
}
```

**Request body** (`GenerationRequest`):
```json
{
  "prompt": "hospital building",
  "original_prompt": "hospital",
  "style_id": "city-builder-iso",
  "asset_type": "game_asset",
  "image_model": "nova_canvas",
  "width": 1024,
  "height": 1024,
  "num_options": 5,
  "num_variations": 5,
  "remove_background": true,
  "generate_svg": true,
  "upscale": false
}
```

Fields:
- `prompt` (required): User's description of the desired asset.
- `original_prompt` (optional, `str | None`): The user's pre-AI-improvement prompt, tracked for provenance.
- `pre_composed` (default false): If true, the prompt was already AI-composed via the "Preview Enhanced Prompt" button — the backend skips refinement and uses the prompt as-is.
- `moderation_original` (optional, `str | None`): Stores the pre-moderation-rewrite prompt when the user accepted a moderation rewrite. Preserved in metadata for audit trail.
- `style_id` (optional): Style profile to apply.
- `asset_type` (default `game_asset`): One of `game_asset`, `marketing_banner`, `icon`, `character`, `environment`. Defined by the `AssetType` enum.
- `image_model` (default `nova_canvas`): Any valid key from the model registry (e.g. `nova_canvas`, `titan_image`, `sd35_large`, `stable_image_ultra`, `stable_image_core_v1`). Validated against the registry at runtime — not limited to a fixed enum. New models added via auto-discovery are accepted without code changes.
- `quality` (optional, `str | None`): Quality tier override (e.g. `"standard"`, `"premium"`). If null, uses the model's `default_quality` from the registry. Only relevant for models with `quality_options`.
- `region` (optional, `str | None`): Region override for the model. If null, uses the model's default `region` from the registry. Must be one of the model's `available_regions`.
- `width` / `height` (default 1024): Output dimensions in pixels.
- `num_options` (default 5, range 1-5): Number of distinct concept designs.
- `num_variations` (default 5, range 1-5): Number of seed variants per option.
- `remove_background` (default true): Run Stability AI background removal.
- `generate_svg` (default true): Convert to SVG.
- `upscale` (default false): Run Stability AI upscaling.
- `negative_prompt` (default ""): Negative prompt carried from the Compose step.
- `all_models` (default false): When true, generates with every enabled image model (one option per model, 1 variation each). Overrides `num_options` and `num_variations`. Dispatches to `_run_all_models_generation()`.
- `model_optimized_prompts` (default false): Only used when `all_models` is true. When true, refines the prompt separately per model for tailored output. When false, all models receive the same prompt for direct comparison. When `pre_composed` is true and refinement is skipped, the backend uses this value instead of extracting from refinement.
- `ip_owned` (default false): User asserts IP ownership over the content.
- `ip_licensed` (default false): User asserts licensing rights. Both IP fields are stored in per-variant metadata for audit trail.

### 5.3 Prompt Refinement

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/refine-prompt/` | Preview a refined prompt without generating images. |

**Request body** (`PromptRefineRequest`):
```json
{
  "prompt": "hospital building",
  "style_id": "city-builder-iso",
  "asset_type": "game_asset",
  "image_model": "nova_canvas"
}
```

- `image_model` (optional): Target image model for model-optimized prompt engineering. When provided, the refinement produces prompts structured for the specific model (e.g. caption-style for Nova Canvas, quality-boosted for SD 3.5 Large). The PromptEditor passes the currently selected model automatically.

**Response**:
```json
{
  "original": "hospital building",
  "refined": "Isometric low-poly hospital building, flat shading, white and red...",
  "negative_prompt": "text, watermark, blurry"
}
```

### 5.4 Voice Transcription

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transcribe/` | Transcribe an uploaded audio file to text (multipart form upload, field name `file`). |

**Response**:
```json
{
  "text": "hospital building with a red cross on the roof"
}
```

### 5.5 Gallery

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gallery/` | List generated assets. Supports query params: `style_id`, `asset_type`, `limit` (default 100, max 500), `offset` (default 0). Returns list of `GalleryItem`, sorted newest-first. Always reads metadata fresh from disk (no cache-first strategy). |
| GET | `/api/gallery/{id}` | Get the full metadata dictionary for a generated asset (includes `style_snapshot`). |
| GET | `/api/gallery/{id}/png` | Download the PNG file. `Content-Disposition` header uses the smart filename (e.g. `prompt-slug_opt1_var2.png`). |
| GET | `/api/gallery/{id}/svg` | Download the SVG file. `Content-Disposition` header uses the smart filename. |
| DELETE | `/api/gallery/` | Bulk delete assets. Request body: `{ "ids": ["asset_id_1", "asset_id_2", ...] }`. Deletes the asset directories and their contents from disk. Returns `{deleted, not_found}`. **Batch-aware**: when deleting batch assets, updates surviving siblings' metadata with `batch_deleted_count`, `original_num_options`, and `original_num_variations` so the system can report partial batch context on reload. |
| GET | `/api/gallery/batch/{batch_id}` | Reconstruct the full options × variations structure for a batch (includes `style_snapshot` and `negative_prompt` per variant). Returns enriched batch context: `batch_surviving_count`, `batch_original_total`, `batch_deleted_count`, `original_num_options`, `original_num_variations` — so the frontend can display "4 of 25 images remaining (21 deleted)" when loading a partial batch. |
| GET | `/api/gallery/{id}/version/{version}` | Download a specific version of an asset (e.g. `v1` = original, `v2` = after edit). |
| GET | `/api/gallery/{id}/version-svg/{version}` | Download the SVG for a specific version. |

### 5.6 Type Studio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/type-studio/fonts` | List available fonts grouped by source. Returns style-specific fonts (for the given `style_id` query param), global project fonts, and detected system fonts. Each entry includes font name, filename, source, and a preview URL. |
| GET | `/api/type-studio/font-file/{source}/{filename}` | Serve a font file (TTF/OTF/WOFF2) for rendering or live preview. `source` is one of `style`, `global`, or `system`. |
| POST | `/api/type-studio/suggest` | AI layout suggestion. Accepts text lines, font choices, position hints, mode ("on_image" or "standalone"), optional base image ID, and style_id. Returns 1-5 layout options, each with per-line position (x, y), font size, color, and effects (shadow, outline, glow) representing different creative directions. |
| POST | `/api/type-studio/preview` | Render and save the text overlay. Accepts text lines, selected layout option, font choices, mode, optional base image ID, style_id, and processing flags. Pillow renders the composition with the specified effects. Saves the result as a new gallery asset with full metadata (including `style_snapshot`) and returns the new asset ID and URLs. |

### 5.7 Video

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/video/generate` | Start a video generation job. Returns `job_id` and `invocation_arn`. Payload: `model_key`, `prompt`, `task_type`, `duration`, `aspect_ratio`, `resolution`, `loop`, `seed`, `source_image` (base64), `enhance_prompt`. Requires S3 bucket configured in video settings. |
| GET | `/api/video/status/{job_id}` | Poll job status. Returns `InProgress`, `Completed`, or `Failed`. On completion, triggers thumbnail extraction (ffmpeg) and metadata save. |
| GET | `/api/video/jobs?status=&limit=` | List video jobs (active + completed from disk). Sorted by start time, descending. |
| GET | `/api/video/{video_id}/mp4` | Serve video MP4. If stored locally, serves file. If S3-only, redirects to presigned URL. |
| GET | `/api/video/{video_id}/thumbnail` | Serve JPEG thumbnail (first frame, extracted via ffmpeg). |
| GET | `/api/video/{video_id}/metadata` | Full job metadata including original_prompt, enhanced_prompt, negative_concepts, model info, video specs. |
| POST | `/api/video/revise` | Re-generate with modified prompt, linked to original video in metadata. Inherits settings from the original job. |
| DELETE | `/api/video/{video_id}` | Delete video (local files). |

### 5.8 Chat Studio

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/stream` | Send messages to an LLM and stream the response via SSE (Bedrock ConverseStream). Returns events: delta (text chunks), metadata (tokens, cost, latency), stop, error. |
| GET | `/api/chat/models` | List all available LLM models for chat. Aggregates from discovered chat_models, LLM categories, and custom/imported models. Includes per-model pricing, regions, context window, vision capability. |
| POST | `/api/chat/sessions` | Create a new chat session. |
| GET | `/api/chat/sessions` | List chat sessions, sorted by last activity. |
| GET | `/api/chat/sessions/{id}` | Load a full session (all messages + metadata). |
| PUT | `/api/chat/sessions/{id}` | Update session (title, messages, model, temperature, etc.). |
| DELETE | `/api/chat/sessions/{id}` | Delete a session. |
| POST | `/api/chat/sessions/{id}/duplicate` | Duplicate a session with a new ID. |
| GET | `/api/chat/sessions/{id}/export` | Export session as Markdown file download. |
| GET | `/api/chat/sessions/{id}/search?q=` | Search within a session's messages. Returns matching snippets with context. |
| POST | `/api/chat/compact` | Compact older messages via LLM summarization. Keeps last N messages verbatim, replaces older with summary. |
| POST | `/api/chat/telemetry` | Receive session summary event from frontend (one event per session interaction, not per message). |

### 5.9 Browse

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/browse/local?path=~` | Browse local filesystem directories. Returns list of files and subdirectories at the given path. Recognizes all supported asset formats: images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) and 3D models (.glb, .gltf). Used by the Style Library file browser modal. |
| GET | `/api/browse/s3/buckets` | List available S3 buckets. |
| GET | `/api/browse/s3?bucket=name&prefix=path` | Browse objects in an S3 bucket at the given prefix. |
| POST | `/api/browse/s3/create-bucket` | Create a new S3 bucket. Payload: `name`, `region`. Validates bucket name format. Returns created bucket info. |

### 5.10 Admin (Model Management)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/models` | Get the full model registry (categories, image models, video models, post-processing, format families). |
| GET | `/api/admin/models/image-options` | Enabled text-to-image models for the Image Studio dropdown. Returns per-model metadata including region_pricing and quality_options. |
| GET | `/api/admin/models/video-options` | Enabled video models for the Video Studio dropdown. Returns per-model metadata including parameters, task_types, and pricing. |
| GET | `/api/admin/regions` | Cached list of Bedrock-supported AWS regions from the registry. |
| GET | `/api/admin/video/settings` | Current video storage settings (S3 bucket, prefix, storage mode). |
| PUT | `/api/admin/video/settings` | Update video settings. Validates S3 bucket access (head_bucket + put/delete test) before saving. |
| PATCH | `/api/admin/models/category/{name}` | Update an LLM category (e.g. `fast_llm`, `complex_llm`). |
| PATCH | `/api/admin/models/image/{key}` | Update an image model. |
| PATCH | `/api/admin/models/video/{key}` | Update a video model (enable/disable, region, prompt limit). |
| POST | `/api/admin/models/image` | Add a new image model to the registry. |
| PUT | `/api/admin/models` | Replace the entire model registry JSON. Validates required top-level keys. Used by the raw JSON editor. |
| PATCH | `/api/admin/models/postprocess/{key}` | Update a post-processing model (model_id, region, enabled). |
| POST | `/api/admin/models/reload` | Reload the model registry from disk (e.g. after external edit). |
| POST | `/api/admin/discover/refresh-all` | Full registry refresh: discovers regions, fetches pricing, scans all regions for foundation + custom + imported models, backfills Bedrock metadata (input/output modalities, lifecycle, ARN, streaming, customizations). |
| POST | `/api/admin/discover/{region}/auto-register` | Scan a single region for foundation image + video models. Classifies by output modality (IMAGE → image registry, VIDEO → video registry). Custom/imported models are discovered separately during refresh-all. |
| GET | `/api/admin/discover/{region}` | Raw model listing: image generators, video generators, text/LLM, vision models. |

### 5.11 System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check — returns `{status, version, aws: {credentials, identity, bedrock_models, bedrock_images, errors}}`. |
| POST | `/api/ping` | Frontend telemetry ping. Accepts `{event, properties}` and forwards to PulseBoard if telemetry is enabled. |
| POST | `/api/log` | Receive client-side log entries. Body: `{ "level": "error", "message": "...", "context": {} }`. Logged server-side with `[CLIENT]` prefix. |
| GET | `/docs` | Swagger UI (auto-generated by FastAPI). |

## 6. LLM Directive Prompts (Prompt Templates)

ArtSmoker uses 13 directive prompts to guide LLM behavior across different features. All prompts are stored in `backend/prompt_templates.json` and are fully editable via the Model Settings UI (Prompt Templates tab) or the raw JSON editor.

### 7.1 How Templates Work

Each template is a named prompt with placeholder variables that get filled at runtime. The system loads the template, substitutes variables like `{user_prompt}`, `{model_name}`, `{style_section}`, and sends the result to the LLM.

Templates are organized by the feature they serve:

### 7.2 Image Generation Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `image_refine_single` | `prompt_engineer.py` | Refine a single user prompt into a detailed image caption. Respects priority order: user intent > asset type > style. | `{user_prompt}`, `{model_name}`, `{model_specific_instructions}`, `{asset_context}`, `{style_section}`, `{max_chars}` | Opus or Sonnet |
| `image_refine_marketing` | `prompt_engineer.py` | Marketing-banner-specific refinement with text-safe zones and cinematic composition. | `{user_prompt}`, `{style_section}`, `{max_chars}` | Opus |
| `image_concepts_multi` | `prompt_engineer.py` | Generate 2-5 visually distinct creative concepts from one prompt. Returns JSON array. | `{user_prompt}`, `{num_options}`, `{asset_context}`, `{style_section}`, `{max_chars}` | Opus |

**Key design principle:** User intent is king — the prompt explicitly instructs the LLM to prioritize the user's words over asset type defaults and style guidelines.

### 7.3 Style Analysis Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `style_analysis_full` | `style_analyzer.py` | Analyze reference images for visual attributes: perspective, palette, rendering, lighting, composition, line work. | `{user_guidance_section}` + reference images | Opus (vision) |
| `style_hints_generation` | `style_analyzer.py` | Distill an analyzed style into a concise generation directive paragraph (max 200 words). | `{style_json}`, `{user_guidance_section}` | Sonnet |
| `style_cohesion_check` | `style_analyzer.py` | Quick check: do reference images represent a single cohesive style or a diverse collection? Returns JSON with cohesion level. | Reference images | Sonnet (vision) |

### 7.4 Content Moderation Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `moderation_prescreen` | `generate.py` | Predict if a prompt will be blocked by the target model. Suggests alternative models if needed. Returns JSON. | `{prompt_for_screen}`, `{model_label}` | Sonnet |
| `moderation_rewrite` | `generate.py` | Rewrite a blocked prompt to pass moderation while preserving creative intent. Handles IP references, violence, aggression. | `{original_prompt}`, issues list | Sonnet |

### 7.5 Video Generation Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `video_enhance_prompt` | `video.py` | Enhance a user prompt with camera movements, lighting, temporal cues, and avoidance language (since video models have no negative prompt). | `{prompt}`, `{prompt_limit}` | Sonnet |

### 7.6 Type Studio Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `typestudio_layout` | `typestudio.py` | Design text layout with positions, fonts, sizes, colors, and effects for image overlay. Returns JSON array of layout options. | `{canvas_width}`, `{canvas_height}`, `{image_context}`, `{style_section}`, `{lines_desc}` | Opus or Sonnet |

### 7.7 Chat Studio Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `chat_context_compact` | `chat.py` | Summarize older messages to free context window space. Preserves key facts, decisions, and context. | `{convo_text}` | Sonnet |
| `chat_title_generate` | `chat.py` | Auto-generate a 3-8 word session title from the first exchange. | `{user_message}`, `{assistant_snippet}` | Sonnet |

### 7.8 Translation Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `translate_detect_language` | `prompt_translator.py` | Detect language when Unicode heuristics are ambiguous (French vs Spanish). Returns 2-letter code. | `{text}` | Sonnet |
| `translate_to_english` | `prompt_translator.py` | Translate non-English text to English, preserving meaning and technical terms. | `{text}`, `{lang_name}` | Sonnet |

### 7.9 Editing Templates

Users can edit any template via **Model Settings → Prompt Templates** tab. Each template shows:
- Template name and description
- Where it's used in the pipeline
- Available variables (must be preserved when editing)
- A "Reset to Default" button to restore the original
- An **"Enhance with AI"** button that uses any available LLM to refine the template

### 6.10 AI-Assisted Template Refinement

Users can ask an LLM to improve any template:

1. Select a refinement model from the dropdown (all chat-capable models available)
2. Optionally type specific instructions (e.g., "optimize for pixel art", "make moderation less strict")
3. Click "Enhance with AI" — the LLM receives the current template + its metadata + instructions
4. A purple suggestion panel shows the improved version
5. If the AI's suggestion is missing required `{variables}`, a warning is displayed
6. Click "Accept" to copy into the editor (then "Save" to persist), or "Dismiss" to discard

**API**: `POST /api/admin/templates/{name}/enhance` with `{model_id, region, instructions}`.

**Storage**: All templates stored in `backend/prompt_templates.json`. Code defaults are baked into `backend/services/prompt_templates.py` (source of truth for resets). User edits are marked with `"modified": true`.

> [!WARNING]
> Editing directive prompts changes how the AI behaves across the entire application. Test changes carefully. Removing required variables (e.g., `{user_prompt}`) will break the feature that uses the template. The AI enhancement validates variable preservation and warns if any are missing.

## 7. Prerequisites: AWS Setup

ArtSmoker uses Amazon Bedrock and requires working AWS credentials on the host machine **before launching**. No AWS configuration is needed inside the app itself — it uses the standard AWS credential chain.

### 7.1 AWS Credentials

The app uses [boto3's standard credential resolution](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials):

1. **Environment variables**: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (+ optional `AWS_SESSION_TOKEN`)
2. **Shared credentials file**: `~/.aws/credentials` (default profile, or set `AWS_PROFILE`/`ARTSMOKER_AWS_PROFILE` for a named profile)
3. **AWS SSO**: If configured via `aws configure sso`
4. **IAM Instance Profile**: Automatic on EC2 — attach a role with the required permissions, no credentials needed on the machine. See [Instance Profiles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html).
5. **ECS Task Role / App Runner Instance Role**: Automatic in containerized environments.

Whatever method you use for other AWS work on your machine will work here. On EC2 and other AWS compute, using an Instance Profile or Task Role is recommended over storing access keys.

### 7.2 Required IAM Permissions

The IAM principal (user, role, or SSO session) needs the following permissions:

| Permission | Purpose |
|------------|---------|
| `bedrock:InvokeModel` | Image generation, image editing, post-processing (all image models) |
| `bedrock:Converse` | LLM calls — prompt refinement, style analysis, concept generation |
| `bedrock:InvokeModelWithBidirectionalStream` | Voice transcription (optional — app works without it) |
| `bedrock:StartAsyncInvoke` | Video generation (async invocation) |
| `bedrock:GetAsyncInvoke` | Poll video generation job status |
| `bedrock:ListAsyncInvokes` | List video generation jobs |
| `bedrock:ListFoundationModels` | Foundation model discovery (Sync from AWS) |
| `bedrock:ListCustomModels` | Discover fine-tuned custom models in your account |
| `bedrock:ListImportedModels` | Discover imported models in your account |
| `bedrock:GetCustomModel` | Read custom model details (base model, status) |
| `bedrock:GetImportedModel` | Read imported model details (architecture, status) |
| `bedrock:ListProvisionedModelThroughputs` | Find invocable custom models with provisioned throughput |
| `bedrock:ListCustomModelDeployments` | Find custom models with on-demand deployments |
| `s3:CreateBucket` | Create S3 bucket for video storage (optional, via UI) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | Video output storage and retrieval |
| `aws-marketplace:Subscribe` | Auto-subscription on first use of third-party models |
| `aws-marketplace:ViewSubscriptions` | Check existing model subscriptions |
| `sts:GetCallerIdentity` | Startup credential validation |
| `pricing:GetProducts` | Fetch model pricing during Sync from AWS (optional) |

**Quickest setup**: Attach the AWS managed policy **`AmazonBedrockFullAccess`**. This covers all `bedrock:*` actions. You may additionally need `aws-marketplace:Subscribe` and `aws-marketplace:ViewSubscriptions` for first-time third-party model access.

For a scoped IAM policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Converse",
        "bedrock:InvokeModelWithBidirectionalStream",
        "bedrock:StartAsyncInvoke",
        "bedrock:GetAsyncInvoke",
        "bedrock:ListAsyncInvokes",
        "bedrock:ListFoundationModels",
        "bedrock:ListCustomModels",
        "bedrock:ListImportedModels",
        "bedrock:GetCustomModel",
        "bedrock:GetImportedModel",
        "bedrock:ListProvisionedModelThroughputs",
        "bedrock:ListCustomModelDeployments"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aws-marketplace:Subscribe",
        "aws-marketplace:Unsubscribe",
        "aws-marketplace:ViewSubscriptions"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:CreateBucket", "s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket", "s3:HeadBucket"],
      "Resource": ["arn:aws:s3:::artsmoker-*", "arn:aws:s3:::artsmoker-*/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity", "pricing:GetProducts"],
      "Resource": "*"
    }
  ]
}
```

**Apply the policy via CLI:**

```bash
# Option A: Quickest — attach managed policies to your IAM user
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Option B: Scoped — create and attach the policy above
aws iam create-policy --policy-name ArtSmokerAccess \
  --policy-document file://artsmoker-policy.json
# Then attach to your user or role:
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess

# Option C: EC2 role — create a role for EC2 instance profiles
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

### 7.3 Bedrock Model Availability

Bedrock models are **available by default** in all commercial AWS regions — no manual enablement step is needed. On first invocation of a third-party model (Anthropic, Stability AI), AWS automatically initiates a marketplace subscription in the background (requires the `aws-marketplace` permissions above).

> [!NOTE]
> **Anthropic models**: Require a one-time [First Time Use form](https://console.aws.amazon.com/bedrock/home#/modelaccess) completion before first invocation.

ArtSmoker discovers available models and regions dynamically via the **Sync from AWS** feature in the admin UI. Models and regions are not hardcoded — the system reads from Amazon Bedrock's `ListFoundationModels`, `ListCustomModels`, and `ListImportedModels` APIs and stores the results in the model registry. Custom (fine-tuned) models inherit their format family from their base model dynamically — no hardcoded model mappings. Imported models are registered as LLM alternatives. Each model is configured with its optimal region, and users can override the region per request.

### 7.4 Verifying Access

Confirming credentials work (`sts:GetCallerIdentity`) only verifies identity — it does **not** confirm Bedrock permissions. ArtSmoker uses multiple Bedrock APIs (`InvokeModel`, `Converse`, `StartAsyncInvoke`, `ListFoundationModels`), so a model listing test alone is not sufficient.

```bash
# 1. Confirm credentials resolve
aws sts get-caller-identity

# 2. Can you list models? (bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[0].modelId" --output text

# 3. Can you invoke a model? (bedrock:InvokeModel)
aws bedrock-runtime invoke-model --region us-east-1 \
  --model-id amazon.titan-image-generator-v2:0 \
  --content-type application/json --accept application/json \
  --body '{"textToImageParams":{"text":"test"},"imageGenerationConfig":{"numberOfImages":1,"width":512,"height":512}}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# 4. Can you list custom models? (bedrock:ListCustomModels — needed for custom model discovery)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

If steps 1-3 pass, your core permissions are set. Step 4 is only needed for custom model discovery. If step 2 passes but step 3 fails, your IAM policy allows listing but not invoking — update it using the scoped policy above or attach `AmazonBedrockFullAccess`.

### 7.5 Startup Validation

On launch, ArtSmoker automatically validates:
1. AWS credentials resolve (`sts:GetCallerIdentity`)
2. Bedrock Claude access works in us-west-2 (attempts a lightweight `Converse` call)
3. Bedrock Nova Canvas access works in us-east-1 (attempts a lightweight `InvokeModel` call)

Results are logged to the console and available at `GET /api/health`. If credentials are missing, a prominent error box explains what to configure. If some checks fail but credentials exist, a warning is shown — the app still starts (some features may be degraded).

## 8. Security Model

ArtSmoker is designed as a **local/trusted-network development tool** — it runs on the developer's own machine or a private EC2 instance. The security model reflects this:

- **No authentication**: There is no login system. All API endpoints are open. This is appropriate for Phase 1 (local development) and Phase 2 (private team deployment). Phase 4 adds Cognito authentication.
- **Filesystem browser**: The `GET /api/browse/local` endpoint allows browsing any directory the server process can access. This is intentional — the user is browsing their own machine to select reference art. **Do not expose this endpoint to untrusted networks** without adding authentication and path restrictions.
- **Font file serving**: The `GET /api/type-studio/font-file/{source}/{filename}` endpoint validates that path components do not contain traversal characters (`..`, `/`, `\`), and verifies the resolved path stays within expected directories.
- **S3 access**: S3 browsing and imports use the server's AWS credentials. The user can access any S3 bucket their IAM role permits.
- **Client-side logging**: The `POST /api/log` endpoint accepts arbitrary log messages. In a multi-user deployment, this should be rate-limited.

> [!IMPORTANT]
> For production deployments beyond a trusted team, add authentication (see Phase 4 roadmap), restrict the browse endpoint to allowed directories, and place the service behind a reverse proxy with TLS.

## 9. Application Bootstrap (main.py)

`backend/main.py` assembles the FastAPI application. Build it in this exact order:

1. **FastAPI app** with `title="ArtSmoker"`, `description="AI-Powered Game Asset Generation"`, and a `lifespan` handler.
2. **Lifespan handler** (async context manager):
   - On startup: create data directories (`data/`, `data/styles/`, `data/generated/`, `data/video/`) via `mkdir(parents=True, exist_ok=True)`.
   - On startup: call `validate_aws_credentials()` from `bedrock_client.py` — stores result in a module-level `_aws_status` dict.
   - On startup: initialize PulseBoard telemetry (`telemetry_init()`, `track_server_start()`) — fire-and-forget.
   - Log a prominent error box if credentials are missing, a warning if some Bedrock checks fail, or an info message if all checks pass.
3. **NoCacheStaticMiddleware** — custom `BaseHTTPMiddleware` that adds `Cache-Control: no-cache, no-store, must-revalidate` and `Pragma: no-cache` headers to all responses where the request path does NOT start with `/api/`. This ensures frontend static files are never cached during development.
4. **CORS middleware** — `CORSMiddleware` with `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`. Development-mode open CORS.
5. **Include all routers**: styles, generate, refine, transcribe, gallery, browse, typestudio, video, chat, admin — in that order.
6. **Health check endpoint** (`GET /api/health`) — defined inline on `app`, returns `{status: "ok"|"degraded", aws: {credentials, identity, bedrock_models, bedrock_images, errors}}`.
7. **Client log endpoint** (`POST /api/log`) — defined inline on `app`, receives `{level, message, context}`, logs as `[CLIENT] {message} | {context}` at the appropriate Python log level.
8. **Static files mount** — `app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True))` mounted LAST so `/api/*` routes take priority. `FRONTEND_DIR` is `Path(__file__).resolve().parent.parent / "frontend"`. The `html=True` flag enables serving `index.html` for directory requests.

## 10. Dependencies (requirements.txt)

**Python packages** (installed via pip):

```
fastapi>=0.115
uvicorn[standard]>=0.34
boto3>=1.36
python-multipart>=0.0.20
pydantic>=2.10
pydantic-settings>=2.7
Pillow>=11.1
aiofiles>=24.1
```

For multi-user, shared test, or production deployments, also install `gunicorn` (Linux/macOS only):
```
pip install gunicorn
```
Use `gunicorn` whenever more than one person will access the app concurrently — not just in production. Solo development with `uvicorn --reload` is fine for a single developer.

**External CLI tools** (optional, not Python packages — improve SVG quality):

| Tool | Purpose | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| vtracer | Primary SVG conversion (color vector tracing) | `pip install vtracer` or `cargo install vtracer` | `pip install vtracer` or `cargo install vtracer` | `pip install vtracer` or `cargo install vtracer` or [pre-built binaries](https://github.com/visioncortex/vtracer/releases) |
| potrace | Fallback SVG conversion (monochrome tracing) | `brew install potrace` | `sudo apt install potrace` | Download from [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading) |
| ffmpeg | Video thumbnail extraction + metadata (duration, resolution, FPS) | `brew install ffmpeg` | `sudo apt install ffmpeg` | [ffmpeg.org/download](https://ffmpeg.org/download.html) or `winget install ffmpeg` |

If neither vtracer nor potrace is installed, SVG conversion falls back to Pillow's embedded-raster approach (base64 PNG wrapped inside an SVG element). This is functional but not true vector output — the file size is roughly the same as the PNG.

If ffmpeg is not installed, Video Studio still generates and plays videos (streamed from S3 or downloaded as MP4), but thumbnails will be missing (black placeholder in Gallery and Video Studio) and video metadata (duration, resolution) won't be extracted. `ffprobe` (included with ffmpeg) is used for metadata. Verify installation with `ffmpeg -version`.

**System requirements by platform**:

| Requirement | macOS | Linux (Debian/Ubuntu) | Windows |
|-------------|-------|-----------------------|---------|
| Python 3.11+ | `brew install python@3.12` or [python.org](https://www.python.org/downloads/) | `sudo apt install python3 python3-pip python3-venv` | [python.org](https://www.python.org/downloads/) (check "Add to PATH") |
| AWS CLI | `brew install awscli` or [AWS installer](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | `sudo apt install awscli` or [AWS installer](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | [AWS MSI installer](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| Python command | `python3` / `pip3` | `python3` / `pip3` | `python` / `pip` |
| ffmpeg (optional) | `brew install ffmpeg` | `sudo apt install ffmpeg` | [ffmpeg.org/download](https://ffmpeg.org/download.html) or `winget install ffmpeg` |
| Venv activation | `source .venv/bin/activate` | `source .venv/bin/activate` | `.venv\Scripts\activate` |
| Multi-user server | gunicorn (pip install) | gunicorn (pip install) | uvicorn with `--workers` flag (gunicorn not supported on Windows) |
| System fonts (Type Studio) | Detected from `/System/Library/Fonts`, `/Library/Fonts`, `~/Library/Fonts` | Detected from `/usr/share/fonts`, `/usr/local/share/fonts`, `~/.fonts`, `~/.local/share/fonts` | Not auto-detected — use global or style-specific custom fonts |

**Installation without venv** (all platforms):

```bash
# macOS / Linux
pip3 install --user -r backend/requirements.txt

# Windows
pip install -r backend\requirements.txt
```

> Note: On modern Linux distros (PEP 668), `pip install` outside a venv may require `--user` or `--break-system-packages`. Using a venv is recommended to avoid system conflicts.

## 11. Frontend Design System

The frontend uses a dark theme with CSS custom properties. These values define the entire visual identity and must be replicated exactly for visual consistency.

**CSS Custom Properties** (`:root` in `styles.css`):
```css
--bg: #0f172a;              /* Page background (slate-900) */
--surface: #1e293b;         /* Card/panel background (slate-800) */
--surface-hover: #253347;   /* Hovered surface */
--accent: #6366f1;          /* Primary accent — indigo-500 */
--accent-hover: #818cf8;    /* Hovered accent — indigo-400 */
--accent-muted: #4f46e5;    /* Muted accent — indigo-600 */
--text: #e2e8f0;            /* Primary text — slate-200 */
--text-muted: #94a3b8;      /* Secondary text — slate-400 */
--text-dim: #64748b;        /* Tertiary text — slate-500 */
--border: #334155;          /* Border color — slate-700 */
--danger: #ef4444;          /* Error/delete — red-500 */
--success: #22c55e;         /* Success — green-500 */
--warning: #f59e0b;         /* Warning — amber-500 */
--radius: 0.75rem;          /* Default border radius */
--shadow: 0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -2px rgba(0,0,0,0.2);
--shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.4), 0 4px 6px -4px rgba(0,0,0,0.3);
```

**Tailwind CSS** is loaded via CDN (`<script src="https://cdn.tailwindcss.com"></script>`) with an inline config that extends the default theme with `brand-*` color aliases mapping to the same hex values above (e.g. `brand-bg: '#0f172a'`). This allows using both `bg-brand-bg` (Tailwind) and `var(--bg)` (CSS) interchangeably.

**Key CSS component classes** (defined in `styles.css`):
- `.card` / `.card-static` — surface-colored panels with border and radius
- `.btn-primary` / `.btn-secondary` / `.btn-danger` / `.btn-sm` / `.btn-lg` — button variants
- `.modal-overlay` / `.modal-content` — modal system with backdrop blur and slide-in animation
- `.toast` / `.toast-exit` — notification toasts with slide-in/out animations
- `.toggle` / `.toggle-slider` — custom toggle switch (checkbox replacement)
- `.loading-spinner` / `.spinner-sm` — CSS-only spinning indicators
- `.recording-pulse` / `.recording-dot` — voice recording animations
- `.upload-zone` / `.drag-over` — drag-and-drop upload area
- `.preview-checkerboard` — transparency checkerboard pattern for image previews
- `.gallery-grid` — responsive auto-fill grid (`repeat(auto-fill, minmax(280px, 1fr))`, 200px on mobile)
- `.skeleton` — shimmer loading placeholders
- `.badge` / `.badge-indigo` / `.badge-green` — tag badges
- `.tab-bar` / `.tab` / `.active` — tab navigation
- `.prompt-compare` — two-column grid for prompt editor
- `.ts-mode-btn` / `.ts-mode-active` — Type Studio mode toggle buttons
- `.img-hover-zoom` — scale-up on hover
- `.view-enter` / `.view-exit` — route transition animations
- `.fade-in` — utility fade animation
- Custom scrollbar styling (thin, accent-colored)

**Global JavaScript utilities** (exposed by `app.js` on `window`):
- `showToast(message, type, duration)` — types: `success`, `error`, `warning`, `info`. Auto-dismisses. Pauses on hover. Error/warning toasts are also sent to `POST /api/log`.
- `showLoading(text)` / `hideLoading()` — fullscreen loading overlay with spinner.
- `resetView(route)` — destroys the DOM cache for a specific view, forcing fresh render on next visit.

**Frontend component pattern** — every component is an IIFE that attaches to `window`:
```javascript
(function () {
    'use strict';
    window.ComponentName = {
        render() { return '<div>...</div>'; },  // Returns HTML string
        init() { /* Called once on first visit — bind events */ },
        onShow() { /* Called on every visit (including cached) — refresh data */ },
        destroy() { /* Cleanup — called by resetView() */ },
    };
})();
```
`app.js` manages a DOM-caching router: each view is rendered once, then hidden/shown on route changes (not destroyed/recreated). The `_viewCache` object stores the live DOM element for each route.

## 12. Configuration

All per-generation settings (style, asset type, image model, dimensions, options/variations counts, post-processing toggles) are controlled through the **frontend UI**.

Infrastructure settings live in `backend/config.py` with sensible defaults that work out of the box. Static paths and environment overrides are in config.py; model IDs, regions, prompt limits, and moderation strictness are in the **model registry** (`backend/model_registry.json`), editable via the Admin API or the frontend Model Settings UI. If needed, any config.py setting can be overridden via an environment variable prefixed with `ARTSMOKER_` — see `backend/config.py` for the full list.

**Model registry** (`backend/model_registry.json`):
- All model IDs, regions, prompt limits, and capabilities are centralized here. See [4.11 Model Registry](#411-model-registry) for the full structure.
- Editable at runtime via the Admin API (`/api/admin/models`) or the frontend Model Settings modal.
- Lives alongside backend code (not in `data/`) — it is system configuration, not user data.

**Reference image and analysis limits** (for cost management):
- `max_reference_images: int = 100` (env: `ARTSMOKER_MAX_REFERENCE_IMAGES`) — max images imported per style. Limits storage.
- `max_analysis_images: int = 20` (env: `ARTSMOKER_MAX_ANALYSIS_IMAGES`) — max images sent to Claude Opus per analysis call. When a style exceeds this count, `_smart_sample()` selects a diverse subset. Reducing this value reduces Claude Opus vision costs per analysis.

## 13. Verification

1. **Start backend**:
   ```bash
   # macOS / Linux (with venv)
   cd ArtSmoker && source .venv/bin/activate && uvicorn backend.main:app --reload

   # macOS / Linux (without venv)
   cd ArtSmoker && python3 -m uvicorn backend.main:app --reload

   # Windows (with venv)
   cd ArtSmoker && .venv\Scripts\activate && uvicorn backend.main:app --reload

   # Windows (without venv)
   cd ArtSmoker && python -m uvicorn backend.main:app --reload
   ```
2. **Check startup output**: The console should show "All AWS checks passed" or a warning about specific Bedrock regions. If credentials are missing, a prominent error box explains what to configure.
3. **Open frontend**: Navigate to `http://localhost:8000` — the frontend is served as static files by FastAPI. No separate web server needed.
3. **Create a style profile**: Use the Style Library view to create a profile and upload reference images (or use directory import).
4. **Trigger style analysis**: Click analyze — verify Claude extracts structured style attributes and generation hints.
5. **Generate assets in 2D Image Studio**:
   - Enter a prompt like "hospital building", select the style, choose asset type.
   - Set options to 3 and variations to 3 (9 total images) for a quick test.
   - Click Generate — verify the options row shows 3 distinct concept designs.
   - Click an option — verify the variations row shows 3 seed variants with emerald borders.
   - Click a variation — verify the main preview updates and the download bar shows the smart filename.
6. **Test post-processing**: After generation, verify the label switches to "Post-Processing". Toggle a processing option and click "Apply to Current Results" — verify assets are updated without re-generating.
7. **Download files**: Click PNG/SVG download buttons — verify the file is named with the prompt slug (e.g. `hospital-building_opt2_var1.png`).
8. **Test voice input**: Record audio — verify transcription appears in the prompt editor.
9. **Test two-area prompt editor**: Type a prompt, click "Preview Enhanced Prompt" — verify the composed prompt appears in the green-tinted area below. Verify the note under the button reflects whether a style is selected. Edit the original prompt — verify the composed area clears. Click Generate without composing — verify the backend auto-refines and populates the composed area via SSE.
10. **Test prompt refinement**: Type a brief prompt, click "Preview Enhanced Prompt" — verify the refined prompt respects user intent over style defaults.
11. **Test marketing banner**: Set asset type to "Marketing Banner" and generate — verify the result is a scenic composition, not an isolated sprite.
12. **Test Type Studio**: Navigate to Type Studio, enter text lines, select fonts, request AI layout suggestions. Verify 1-5 layout options are returned. Select a layout and render — verify the result is saved to the gallery.
13. **Test Video Studio**: Navigate to Video Studio, configure S3 bucket in Video Settings, select a video model (Nova Reel or Luma Ray), enter a prompt, and generate. Verify the job appears in Active Jobs, polling updates the status, and on completion the video plays and thumbnail appears. Verify the video also appears in the Gallery with a VIDEO badge.
14. **Browse gallery**: Switch to Gallery view — verify generated images and videos appear with the Media filter (All / 2D Artwork / Video), style filter, and search. Test multi-select and bulk delete (both image and video assets).
15. **Test AssetViewer buttons**: Open an image asset — verify "2D Studio" and "Add Text" buttons appear. Open a type-studio asset — verify "Edit in Type Studio" button appears. Click a video card — verify the video player modal opens with metadata.
16. **Test style_snapshot**: Delete a style, then view an asset that was generated with it — verify the style name still displays from the snapshot.
17. **Test Model Settings**: Click "Model Settings" in the sidebar — verify the modal shows Image Models, Video Models, LLM & Post-Processing tabs, and Registry JSON. Verify video models show regions and pricing. Try Sync from AWS — verify both image and video models are discovered.
17. **Test content moderation**: Generate with a prompt that triggers moderation — verify the system tries alternative models first (emerald dialog) before suggesting a rewrite (amber dialog). Test the rewrite option in each dialog — verify the rewritten prompt appears in the enhanced prompt area (not the original textarea) with the amber disclaimer. Verify the original prompt is preserved. Enable "Prompt Pre-Check" and test with a borderline prompt — verify the indigo pre-check dialog appears with specific issues, model switch, and rewrite options.
18. **Verify API docs**: Visit `http://localhost:8000/docs` — verify all endpoints are documented (including `/api/admin/*`).

<a id="13-aws-bedrock-pricing--cost-breakdown"></a>

<a id="14-aws-bedrock-pricing--cost-breakdown"></a>

## 14. Amazon Bedrock Pricing & Cost Breakdown

> [!NOTE]
> The tables below are **reference pricing for deployment planning**. The application shows **live pricing** in the UI — fetched from the AWS Pricing API during registry refresh-all and stored in `model_registry.json`. Each model's `base_price_usd` and per-region `quality_prices` are displayed in the Image Studio and Video Studio model/region selectors and cost estimates. The pricing data is cached in the registry and only updated when an admin explicitly runs refresh-all.

All prices below are from the official [Amazon Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/) for US regions (us-west-2, us-east-1). Prices are on-demand, per-request.

### 14.1 Per-Unit Pricing

| Service | Model | Per-Unit Cost | Unit |
|---------|-------|--------------|------|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | $3.00 input / $15.00 output | per 1M tokens |
| **Claude Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | $5.00 input / $25.00 output | per 1M tokens |
| **Claude Opus 4.6 (vision)** | same | ~$0.008 | per 1024×1024 image input |
| **Nova Canvas** | `amazon.nova-canvas-v1:0` | $0.06 | per image (1024×1024, premium) |
| **Titan Image v2** | `amazon.titan-image-generator-v2:0` | $0.01 | per image (1024×1024) |
| **Stable Diffusion 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | per image |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | per image |
| **Remove Background** | `us.stability.stable-image-remove-background-v1:0` | $0.07 | per image |
| **Creative Upscale** | `stability.stable-creative-upscale-v1:0` | $0.60 | per image |
| **SVG Conversion** | vtracer / potrace / Pillow (local) | $0.00 | free — runs locally |

> [!NOTE]
> Prices from the official [Amazon Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/) as of March 2026. Prices may change — always verify against the official source.

> [!NOTE]
> **Vision token formula**: Claude charges image inputs as tokens: `tokens = (width × height) / 750`. A 1024×1024 image ≈ 1,398 tokens. At Opus $5.00/MTok input = ~$0.007 per image.

### 14.2 Additional LLM Costs (Per Use)

These Claude calls are part of the system's workflow but not included in the per-batch cost tables below:

| Call | Model | When triggered | Approx. Cost |
|------|-------|----------------|-------------|
| Prompt Pre-Check | Claude Sonnet 4.6 | Before each generation (if toggle enabled) | ~$0.005 |
| Moderation Analysis + Rewrite | Claude Sonnet 4.6 | Only when all image models reject a prompt | ~$0.005 |
| Type Studio Layout Suggestion | Claude Opus 4.6 | Each AI layout request in Type Studio | ~$0.02–$0.05 |

Pre-check and moderation rewrite are a fraction of a cent each. Type Studio layout costs vary with the number of text lines and whether a base image is analyzed (vision input adds ~$0.007 per image).

### 14.3 Style Analysis Cost (One-Time per Style)

For a style with **100 reference images** (20 sent to Claude Opus after smart sampling, 8 sent to Claude Sonnet for cohesion check):

| Step | Model | Calculation | Cost |
|------|-------|-------------|------|
| Cohesion check (Phase 1) | Claude Sonnet 4.6 (vision) | 8 images (game sprites, smaller than 1024×1024) + ~500 prompt tokens; ~500 output tokens | ~$0.01 |
| Analyze images (Phase 2) | Claude Opus 4.6 (vision) | 20 images (game sprites) + ~500 prompt tokens; ~1,500 output tokens | ~$0.12 |
| Generate hints | Claude Sonnet 4.6 | ~800 input + ~200 output tokens | ~$0.005 |
| **Total per style analysis** | | | **~$0.14** |

### 14.4 Generation Cost Scenarios

The generation cost depends on the image model chosen and the options×variations count. Prompt refinement cost is constant per batch.

**Base cost per batch** (prompt refinement/concept generation):

| Options | Prompt Step | Model | Approx. Cost |
|---------|-----------|-------|-------------|
| 1 option | Single prompt refinement | Claude Sonnet 4.6 | ~$0.005 |
| 5 options | Concept generation (5 prompts) | Claude Opus 4.6 | ~$0.05 |

**Image generation cost per batch** (the dominant cost):

| Scenario | Images | Nova Canvas | Titan Image v2 | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|--------|-------------|----------------|--------------|-------------------|
| 1 option × 1 variation | 1 | $0.06 | $0.01 | $0.08 | $0.14 |
| 1 option × 5 variations | 5 | $0.30 | $0.05 | $0.40 | $0.70 |
| 5 options × 1 variation | 5 | $0.30 | $0.05 | $0.40 | $0.70 |
| 5 options × 5 variations | 25 | $1.50 | $0.25 | $2.00 | $3.50 |

**Post-processing add-ons** (per image, optional):

| Add-on | Per Image | 1 image | 5 images | 25 images |
|--------|-----------|---------|----------|-----------|
| Remove Background | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convert to SVG | $0.00 | $0.00 | $0.00 | $0.00 |

### 14.5 Full Cost Examples

**Example 1: Quick single asset (cheapest)**
1 option × 1 variation, Titan Image v2, no post-processing:

| Step | Cost |
|------|------|
| Prompt refinement (Sonnet) | $0.005 |
| 1 image (Titan) | $0.01 |
| **Total** | **~$0.02** |

**Example 2: Standard workflow (5 variations to choose from)**
1 option × 5 variations, Nova Canvas, Remove BG on:

| Step | Cost |
|------|------|
| Prompt refinement (Sonnet) | $0.005 |
| 5 images (Nova Canvas) | $0.30 |
| 5× Remove Background | $0.35 |
| **Total** | **~$0.66** |

**Example 3: Full creative exploration (5 concepts × 5 variations)**
5 options × 5 variations, Stable Diffusion 3.5 Large, Remove BG + SVG:

| Step | Cost |
|------|------|
| Concept generation (Opus) | $0.05 |
| 25 images (Stable Diffusion 3.5 Large) | $2.00 |
| 25× Remove Background | $1.75 |
| 25× SVG Conversion | $0.00 |
| **Total** | **~$3.80** |

**Example 4: Premium with upscale (most expensive)**
5 options × 5 variations, Stable Image Ultra, Remove BG + Upscale + SVG:

| Step | Cost |
|------|------|
| Concept generation (Opus) | $0.05 |
| 25 images (Ultra) | $3.50 |
| 25× Remove Background | $1.75 |
| 25× Creative Upscale | $15.00 |
| 25× SVG Conversion | $0.00 |
| **Total** | **~$20.30** |

> [!TIP]
> **Key takeaway**: Image generation is cheap ($0.01–$0.14/image). **Creative Upscale is the big cost driver at $0.60/image** — use it selectively on your final chosen assets, not on the full batch. Remove Background at $0.07/image is reasonable. SVG conversion is free.

## 15. Internationalization (i18n)

ArtSmoker supports 6 languages: English (base), Japanese, Simplified Chinese, Korean, French, and Spanish.

### 15.1 Architecture

```
frontend/js/i18n/
├── i18n.js          # Core: t() function, JSON loader, DOM updater, reverse lookup
├── en.json          # English (base) — 775 keys, source of truth
├── ja.json          # Japanese — 775 keys
├── zh.json          # Simplified Chinese — 775 keys
├── ko.json          # Korean — 775 keys
├── fr.json          # French — 775 keys
└── es.json          # Spanish — 775 keys
```

**Key design decisions:**
- `t('key')` is a global function available in all JS — returns the translated string for the active language
- `t('key', {count: 5})` supports `{{variable}}` placeholder substitution
- Language files are flat JSON loaded on demand (not bundled)
- `I18n.updateDOM()` translates static HTML elements via `data-i18n` attributes
- `I18n.translateView(container)` post-renders component HTML using a reverse lookup (English text → key → translated text)
- Language selection persisted in `localStorage` (`artsmoker_lang` key)
- On language change: all cached views cleared and re-rendered in the new language
- CJK font support: Noto Sans JP/SC/KR loaded via Google Fonts CDN

### 15.2 Prompt Translation Pipeline

Non-English prompts are auto-detected and translated to English before processing. The translation uses the fast LLM (Claude Sonnet) at ~$0.001 per call.

```
User types prompt (any language)
    ↓
detect_language() — Unicode heuristic (CJK/Hangul/Latin+accents)
    ↓ (if ambiguous)
LLM fallback detection
    ↓
translate_to_english() via Claude Sonnet
    ↓
Returns: { original, translated, source_lang, was_translated }
```

**Where translation is applied:**

| Path | Translates? | Why |
|------|------------|-----|
| Image Studio — single model | Yes | Image models work best with English |
| Image Studio — all models | Yes | Same |
| Image editing (inpaint/outpaint/erase/replace/recolor) | Yes | Edit models expect English |
| Video Studio | Yes | Video models expect English |
| Prompt refinement preview | Yes | LLM refinement assumes English |
| Pre-screen moderation | Yes | Consistent moderation results |
| Chat Studio | No | LLMs are natively multilingual |
| Type Studio text lines | No | Text rendered on image in user's language |

**Metadata stored per asset:**
- `original_language`: Detected language code (e.g., "ja", "fr")
- `original_language_prompt`: The user's original text (only if translated)
- `prompt`: The English translation (sent to the model)
- `refined_prompt`: AI-enhanced English prompt
- `negative_prompt`: Extracted negative concepts

**File names:** `_slugify_prompt()` translates non-ASCII prompts to English before slugifying, so Japanese "病院の建物" becomes `hospital-building_opt1_var1.png` (not `asset.png`).

### 15.3 Bilingual Prompt Preview

When a user types a non-English prompt, a translation preview bar appears with:
- Language badge (e.g., "日本語 → English")
- Two tabs: **Original** (shows user's text) and **English** (shows what the model will receive)
- Translation fetched via debounced API call (`POST /api/refine-prompt/translate-preview`)
- Available in Image Studio (PromptEditor) and Video Studio prompt areas

### 15.4 UI String Translation

- 775 translation keys across 16 categories (nav, common, image_studio, video_studio, etc.)
- Components use `t('key')` in template literals: `${t('image_studio.title')}`
- Confirm dialogs, toast messages, tooltips, placeholders all translated
- Technical terms stay in English: AI, LLM, SVG, PNG, S3, AWS, Bedrock, API
- Product names stay in English: ArtSmoker, Nova Canvas, Stable Diffusion

### 15.5 Adding a New Language

1. Copy `frontend/js/i18n/en.json` to `frontend/js/i18n/{code}.json`
2. Translate all 775 values (keep keys identical)
3. Add the language to `SUPPORTED_LANGS` in `frontend/js/i18n/i18n.js`
4. Add the language code to `SUPPORTED_LANGS` in `backend/services/prompt_translator.py`
5. Add CJK font if needed in `frontend/index.html` (Google Fonts link)

<a id="15-deployment--scaling-roadmap"></a>

<a id="16-deployment--scaling-roadmap"></a>

## 16. Deployment & Scaling Roadmap

The current architecture runs as a single local process (uvicorn + local filesystem). This section documents the phased plan for production deployment and scaling.

### 16.1 Why Not Lambda

AWS Lambda is not suitable as the primary compute for this application:

- **Timeout risk**: Lambda's 15-minute maximum is tight for batch generation. A 5×5 batch involves Claude Opus concept generation (5-15s) + 25 parallel image generations (8-15s each, throttled to 5 concurrent) + post-processing per image. Total wall-clock time can reach 2-5 minutes under normal conditions, but Bedrock throttling or retries push it dangerously close to the limit.
- **Cold starts**: The dependency payload (boto3, Pillow, FastAPI, Pydantic) causes 3-5 second cold starts. For an interactive tool where an artist is waiting, this adds unacceptable latency to every request after idle periods.
- **Stateless filesystem**: Lambda has no persistent local filesystem. The current `LocalStore` writes style profiles, reference images, and generated assets to disk. Lambda would require a full S3 rewrite before it could even run.
- **Synchronous payload limit**: Lambda's 6MB response limit is fine for the JSON response (image URLs, not bytes), but constrains future evolution (e.g. returning thumbnails inline, batch ZIP downloads).
- **Concurrency model mismatch**: The generation pipeline uses `ThreadPoolExecutor` internally to parallelize image generation. Lambda's single-request-per-invocation model means each Lambda would serialize its own internal threads, negating the concurrency benefit unless the architecture is decomposed into separate Lambdas per image.

Lambda _could_ work for lightweight endpoints (styles CRUD, gallery listing, health check), but mixing Lambda and non-Lambda compute for the same API adds routing complexity without meaningful benefit at this stage.





<a id="162-phase-1-current--local-development-done"></a>

### 16.2 Phase 1: Current — Local Development (Done)

```
Developer machine
├── uvicorn (FastAPI)
├── Local filesystem (data/styles/, data/generated/)
└── Direct Bedrock API calls
```

- Single process, `uvicorn --reload` for development.
- Frontend served as static files by FastAPI's `StaticFiles` mount.
- Storage: local filesystem under `data/`.
- No authentication, single user.

#### 14.2.1 EC2 Quick Start

For a lightweight production deployment (1-2 concurrent users), an EC2 instance is the simplest path:

- **Recommended instance**: t3.small (2 vCPU, 2 GB RAM, ~$15/month), Amazon Linux 2023 or Ubuntu 22.04+.
- **Setup**:
  ```bash
  # Amazon Linux 2023
  sudo dnf install python3.11 python3.11-pip git
  # Ubuntu 22.04+
  sudo apt update && sudo apt install python3 python3-pip python3-venv git

  # Optional: SVG tools
  sudo apt install potrace                     # Ubuntu
  pip install vtracer                       # or: cargo install vtracer (needs Rust)

  git clone <repo-url> && cd ArtSmoker
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r backend/requirements.txt
  pip install gunicorn
  ```
- **Run with gunicorn** for production:
  ```bash
  gunicorn backend.main:app -w 2 -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 --timeout 300
  ```
  The `--timeout 300` (5 minutes) accommodates large batch generations with retries.
- **IAM role**: Create and attach an IAM role (no access keys needed on the instance):
  ```bash
  # Create role + instance profile (run from your local machine, one-time)
  aws iam create-role --role-name ArtSmokerEC2Role \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }'
  aws iam attach-role-policy --role-name ArtSmokerEC2Role \
    --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
  aws iam attach-role-policy --role-name ArtSmokerEC2Role \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
  aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
  aws iam add-role-to-instance-profile \
    --instance-profile-name ArtSmokerEC2Profile --role-name ArtSmokerEC2Role

  # Attach to your instance
  aws ec2 associate-iam-instance-profile \
    --instance-id i-YOUR_INSTANCE_ID \
    --iam-instance-profile Name=ArtSmokerEC2Profile
  ```
- **Persistent operation**: Create a systemd service:
  ```bash
  # Create the service file
  sudo tee /etc/systemd/system/artsmoker.service > /dev/null << 'UNIT'
  [Unit]
  Description=ArtSmoker
  After=network.target

  [Service]
  WorkingDirectory=/home/ec2-user/ArtSmoker
  ExecStart=/home/ec2-user/ArtSmoker/.venv/bin/gunicorn backend.main:app \
    -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 300
  Restart=always
  User=ec2-user

  [Install]
  WantedBy=multi-user.target
  UNIT

  # Enable, start, and verify
  sudo systemctl daemon-reload
  sudo systemctl enable artsmoker
  sudo systemctl start artsmoker
  sudo systemctl status artsmoker
  ```
- **No race conditions for concurrent users** — each generation uses unique UUIDs, file writes don't overlap.
- **Migrating style data**: Style references use relative symlinks, so they work across machines as long as the source art directories maintain the same relative position to the ArtSmoker project.





<a id="163-phase-2-containerized-deployment--app-runner--s3"></a>

### 16.3 Phase 2: Containerized Deployment — App Runner + S3

**Goal**: Production URL accessible by the whole team, persistent storage, no server management.

**Architecture**:
```
CloudFront (optional, for custom domain + caching)
    |
    v
AWS App Runner
    ├── FastAPI container (all endpoints)
    ├── Bedrock API calls (same as Phase 1)
    └── S3 for storage (replaces local filesystem)
         ├── s3://artsmoker-data/styles/{id}/profile.json
         ├── s3://artsmoker-data/styles/{id}/references/*.png
         └── s3://artsmoker-data/generated/{id}/asset.png, asset.svg, metadata.json
```

**Changes required**:

1. **Dockerfile**: Containerize the FastAPI app. Multi-stage build: Python 3.11+ slim base, install requirements, copy backend + frontend, expose port 8000. Install `vtracer` binary for SVG conversion.

2. **S3 storage backend**: Implement `S3Store` with the same interface as `LocalStore`. The `LocalStore` was designed with this migration in mind — same method signatures, just swap `Path.read_bytes()` for `s3.get_object()` and `Path.write_bytes()` for `s3.put_object()`. Add `ARTSMOKER_STORAGE_BACKEND=s3` and `ARTSMOKER_S3_BUCKET=artsmoker-data` to config.

3. **App Runner setup**:
   - Create an ECR repository, push the Docker image.
   - Create an App Runner service pointing at the ECR image.
   - Attach an IAM instance role with `bedrock:InvokeModel`, `bedrock:Converse`, `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `s3:DeleteObject`.
   - Configure auto-scaling: min 1 instance, max based on expected load (each instance handles ~10 concurrent generation requests via the thread pool).
   - App Runner handles HTTPS termination, health checks (`/api/health`), and rolling deployments.

4. **Frontend as static assets**: For Phase 2, the frontend can stay bundled in the container (served by FastAPI). Moving it to S3 + CloudFront is a Phase 3 optimization.

5. **Environment variables**: All config passes through environment variables (already supported via `ARTSMOKER_` prefix). App Runner environment configuration maps directly.

**Estimated effort**: 1-2 days. The S3 storage swap is the main work; Dockerfile and App Runner setup are straightforward.





<a id="164-phase-3-optimized-delivery--cloudfront--async-generation"></a>

### 16.4 Phase 3: Optimized Delivery — CloudFront + Async Generation

**Goal**: Fast global frontend delivery, resilient generation pipeline that handles heavy usage without timeouts.

**Architecture**:
```
CloudFront CDN
├── /                → S3 bucket (frontend static files)
├── /api/*           → App Runner origin (FastAPI)
└── /api/gallery/*/png, /api/gallery/*/svg
                     → S3 bucket (generated assets, served directly)

App Runner (FastAPI)
├── Lightweight endpoints (styles CRUD, gallery listing, health)
├── POST /api/generate/ → submits job, returns job ID immediately
└── GET /api/jobs/{id}  → poll for completion

Step Functions (generation pipeline)
├── State 1: Concept generation (Claude Opus → N prompt strings)
├── State 2: Map state — parallel image generation (N options × M variations)
│   └── Each iteration: Nova Canvas → post-process → save to S3
├── State 3: Assemble metadata, write batch result to S3
└── State 4: Mark job complete (DynamoDB or S3 marker)
```

**Changes required**:

1. **Separate frontend hosting**: Upload `frontend/` to an S3 bucket with static website hosting. CloudFront distribution with two origins: S3 for `/*` and App Runner for `/api/*`. This eliminates frontend load from the API tier and gives global CDN caching.

2. **Async generation with Step Functions**:
   - `POST /api/generate/` no longer blocks. It validates the request, writes a job record (DynamoDB or S3), starts a Step Functions execution, and returns `{"job_id": "...", "status": "pending"}`.
   - The Step Functions state machine orchestrates the pipeline:
     - **ConceptGeneration** task: Lambda (or inline) calls Claude Opus for concept prompts. This is fast (5-15s) and fits Lambda's model.
     - **GenerateImages** Map state: Fans out to N×M parallel Lambda invocations, each generating one image (Nova Canvas + post-processing). Each Lambda runs for 30-60s — well within limits.
     - **Assemble** task: Collects results, writes final metadata to S3/DynamoDB.
   - Step Functions handles retries, timeouts, error states, and parallelism natively.
   - Frontend polls `GET /api/jobs/{id}` (or uses WebSocket/SSE for push notification).

3. **Direct S3 serving for assets**: CloudFront serves generated PNGs and SVGs directly from S3 (no need to proxy through FastAPI). The gallery endpoints return S3 URLs or CloudFront URLs instead of `/api/gallery/{id}/png` paths. This offloads bandwidth from the API tier entirely.

4. **DynamoDB for metadata** (optional but recommended): Replace the per-asset `metadata.json` files with a DynamoDB table. Enables fast filtered queries (by style, asset type, date range) without scanning the filesystem. Schema: `PK=asset_id`, GSI on `style_id`, GSI on `created_at`.

**Estimated effort**: 3-5 days. Step Functions state machine + Lambda decomposition is the main work. CloudFront setup is well-documented.

### 16.5 Phase 4: Multi-Tenant Platform

**Goal**: Multiple studios/users, each with their own styles and generated assets, with authentication and access control.

**Architecture additions**:
```
Amazon Cognito
├── User pools (email/password or SSO)
├── JWT tokens in API requests
└── Per-user/team scoping

S3 bucket structure
├── s3://artsmoker-data/{tenant_id}/styles/...
└── s3://artsmoker-data/{tenant_id}/generated/...

DynamoDB
├── Partition key: tenant_id#asset_id
└── GSI: tenant_id + created_at (per-tenant gallery queries)
```

**Changes required**:

1. **Authentication**: Add Cognito user pool. FastAPI dependency that validates JWT from the `Authorization` header on every `/api/*` request. Extract `tenant_id` from the token claims.

2. **Tenant-scoped storage**: All S3 paths and DynamoDB queries are prefixed/partitioned by `tenant_id`. Users only see their own styles and generated assets.

3. **Usage tracking and quotas**: Track Bedrock API calls per tenant. Enforce generation quotas (e.g. 100 images/day on free tier, unlimited on paid). DynamoDB counter or CloudWatch metrics.

4. **Billing integration** (optional): Stripe or AWS Marketplace for paid tiers. Generation costs are roughly: Claude Opus concept generation (~$0.02-0.05 per batch) + Nova Canvas images (~$0.04-0.08 per image) + Stability AI post-processing (~$0.02-0.04 per image). A 5×5 batch costs approximately $1.50-3.00 in Bedrock API fees.

5. **Admin dashboard**: Usage analytics, tenant management, model cost tracking.

**Estimated effort**: 1-2 weeks depending on auth requirements and billing complexity.

### 16.6 Infrastructure Summary

| Phase | Compute | Storage | Frontend | Auth | Scale |
|-------|---------|---------|----------|------|-------|
| 1 (Current) | Local uvicorn | Local filesystem | Served by FastAPI | None | Single user |
| 2 (Deploy) | App Runner | S3 bucket | Bundled in container | None (or basic) | Team |
| 3 (Optimize) | App Runner + Step Functions + Lambda | S3 + DynamoDB | S3 + CloudFront | Optional | Heavy usage |
| 4 (Multi-tenant) | Same as Phase 3 | S3 (tenant-prefixed) + DynamoDB | S3 + CloudFront | Cognito | Multiple teams |

### 16.7 Cost Estimates (Phase 2)

Rough monthly costs for a small team (10 users, ~500 generation batches/month). See the **Amazon Bedrock Pricing & Cost Breakdown** section above for detailed per-operation costs.

| Service | 5×5 Nova Canvas (no upscale) | 3×3 Titan (no upscale) |
|---------|------------------------------|------------------------|
| App Runner (1 instance) | ~$30/month | ~$30/month |
| S3 (50GB) | ~$5/month | ~$5/month |
| Claude (prompts + concepts) | ~$27/month | ~$5/month |
| Image generation | ~$750/month | ~$45/month |
| Remove Background | ~$875/month | ~$315/month |
| **Total** | **~$1,687/month** | **~$400/month** |

> [!TIP]
> **Biggest cost levers**: Image model choice (Titan at $0.01 vs Ultra at $0.14 = 14× difference), batch size (3×3 = 9 images vs 5×5 = 25 = 2.8× difference), and Creative Upscale ($0.60/image — only use on final selected assets).

## 17. Disclaimer

**Generated Content Quality**: All images, videos, and other assets generated by ArtSmoker are produced by AI models available through Amazon Bedrock, including both first-party AWS models and third-party models. The quality, accuracy, and appropriateness of generated content depend entirely on the prompts provided, the models selected, and the style references uploaded by the user. The authors and contributors of ArtSmoker make no guarantees regarding the quality, suitability, or fitness for purpose of any generated content.

**Intellectual Property**: Users are solely responsible for ensuring that their prompts, reference images, and generated outputs do not infringe on any third-party intellectual property rights, including but not limited to copyrights, trademarks, and personality rights. ArtSmoker is a tool — it does not filter, validate, or assess the IP status of inputs or outputs. The tool authors and contributors bear no responsibility for any IP infringement arising from the use of this software.

**AI Model and Service Terms**: Generated content is subject to the terms of service and acceptable use policies of the underlying AI model providers accessible through Amazon Bedrock. Users should review the [AWS Service Terms](https://aws.amazon.com/service-terms/), the [Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/), and the individual model provider terms before using generated assets in production or commercial contexts.

**No Warranty**: This software is provided "as is" without warranty of any kind. See [LICENSE](LICENSE) for full terms.
