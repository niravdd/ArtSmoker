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
  - [5.3 Prompt Refinement & Prompt Designer](#53-prompt-refinement--prompt-designer)
  - [5.4 Voice Transcription](#54-voice-transcription)
  - [5.5 Gallery](#55-gallery)
  - [5.6 Type Studio](#56-type-studio)
  - [5.7 Video](#57-video)
  - [5.8 Chat Studio](#58-chat-studio)
  - [5.9 Browse](#59-browse)
  - [5.10 Custom Models (Self-Hosted)](#510-custom-models-self-hosted-on-amazon-sagemaker)
  - [5.11 Async Jobs](#511-async-jobs-self-hosted-model-generation)
  - [5.12 Admin (Model Management)](#512-admin-model-management)
  - [5.13 System](#513-system)
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
    +-- Chat Studio: multi-model LLM chat with streaming, sessions, vision
    +-- Type Studio: text overlay system (on-image + standalone)
    +-- i18n: 9 languages (EN, JA, ZH, KO, FR, ES, HI, RU, DE) with language switcher
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
    +-- /api/gallery        — Generated asset browsing + file serving + bulk delete + image import
    +-- /api/video          — Video generation (async), job polling, MP4/thumbnail serving
    +-- /api/browse         — Server-side file browser (local + S3) + bucket creation
    +-- /api/admin          — Model registry management + Bedrock discovery + video settings
    +-- /api/log            — Client-side error logging
    |
    v
AI Pipeline (Amazon Bedrock)
    |
    +-- Claude Sonnet          — Fast tasks: prompt refinement, generation hints, cohesion check (Phase 1), chat
    +-- Claude Opus            — Complex tasks: style analysis (Phase 2), concept generation, marketing copy, chat
    +-- 80+ LLMs              — Chat Studio: Claude, Nova, Llama, Mistral, Cohere, Qwen, DeepSeek, etc.
    +-- Stable Diffusion 3.5 Large — Primary image generation (text-to-image)
    +-- Stable Image Ultra      — Image generation (Stability AI premium)
    +-- Stable Image Core       — Image generation (Stability AI fast)
    +-- Stability AI            — Background removal, upscaling, inpainting, style transfer
    +-- Nova Reel v1.0/v1.1    — Video generation (text-to-video, image-to-video, multi-shot)
    +-- Luma AI Ray v2.0       — Video generation (text-to-video, flexible aspect ratios)
    +-- Nova Sonic              — Speech-to-text transcription (bidirectional streaming)
    |
    v
Self-Hosted (Amazon SageMaker)
    |
    +-- HunyuanImage 3.0 (BF16) — 80B MoE text-to-image (g7e.12xlarge, FlashInfer)
    +-- HunyuanImage 3.0 (NF4)  — Quantized variant (g7e.2xlarge)
    +-- FLUX.2 dev (NF4)        — Image generation (g6e.4xlarge)
    |
    v
Storage (Local filesystem + S3)
    +-- /data/styles/       — Style profiles + reference images
    +-- /data/generated/    — Output image assets (PNG + SVG) + metadata + versions
    +-- /data/video/        — Video assets (MP4 + thumbnails + job metadata)
    +-- /data/chat/         — Chat sessions (JSON per session)
    +-- S3 bucket           — Video generation output (required for async Bedrock invoke)
```

## 3. Project Structure

```
ArtSmoker/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, lifespan, static mount
│   ├── config.py                  # AWS config, model IDs, paths, defaults
│   ├── model_registry.json        # Persisted model configuration (LLMs, image models, post-processing)
│   ├── prompt_templates.json      # Persisted editable LLM directive prompts (28 templates)
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
│   │   ├── custom_deploy.py       # Custom model deploy/teardown/status/redeploy API (SageMaker)
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
│   │   ├── prompt_translator.py   # Auto-detect language (Unicode heuristic + LLM fallback), translate to English
│   │   ├── prompt_templates.py    # Editable LLM directive prompts: load, save, validate variables, reset, enhance
│   │   ├── pulseboard.py          # Zero-dependency PulseBoard client SDK (copied from PulseBoard project)
│   │   ├── bedrock_client.py      # Shared Bedrock client: invoke_llm (with system prompt), invoke_image_model (generic)
│   │   ├── sagemaker_deployer.py  # SageMaker endpoint lifecycle: create, teardown, readiness, auto-scaling
│   │   ├── sagemaker_invoker.py   # SageMaker inference: invoke_endpoint_async/realtime, S3 input upload
│   │   ├── async_jobs.py          # Async job tracker: S3 poller, resubmission, persistence, lifecycle
│   │   ├── custom_models.py       # Custom model catalog: reads custom_model_catalog from registry
│   │   ├── model_detector.py      # HuggingFace model auto-detection: infers library, loader, config from repo
│   │   └── auto_update.py         # Version-gated git pull, registry self-healing on startup
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update models
│   │   ├── generation_request.py  # GenerationRequest, AssetType, ImageModel enums
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult, GalleryItem
│   ├── sagemaker_handlers/
│   │   └── inference.py           # Universal SageMaker handler (packaged in model.tar.gz for endpoints)
│   ├── storage/
│   │   └── local_store.py         # Local filesystem storage (S3-compatible interface)
│   └── requirements.txt
├── frontend/
│   ├── index.html                 # Single-page app entry
│   ├── css/
│   │   └── styles.css             # Tailwind + custom styles
│   ├── js/
│   │   ├── app.js                 # Main app logic, routing, showConfirm(), language switcher
│   │   ├── i18n/
│   │   │   ├── i18n.js            # Core: t() function, language switching, reverse lookup, translateView()
│   │   │   ├── en.json            # English (base) — 817+ translation keys
│   │   │   ├── ja.json            # Japanese
│   │   │   ├── zh.json            # Simplified Chinese
│   │   │   ├── ko.json            # Korean
│   │   │   ├── fr.json            # French
│   │   │   ├── es.json            # Spanish
│   │   │   ├── hi.json            # Hindi
│   │   │   └── ru.json            # Russian
│   │   ├── components/
│   │   │   ├── StyleLibrary.js    # Style profile browser + uploader
│   │   │   ├── ImageStudio.js     # 2D Image Studio: two-tier generation UI (options + variations)
│   │   │   ├── VideoStudio.js     # Video Studio: text-to-video generation, job polling, video player
│   │   │   ├── ChatStudio.js      # Chat Studio: multi-model LLM chat with streaming, sessions, vision
│   │   │   ├── TypeStudio.js      # Type Studio: text overlay system (on-image + standalone)
│   │   │   ├── VoiceInput.js      # Voice recording + transcription
│   │   │   ├── PromptEditor.js    # Text input with inline LLM refinement
│   │   │   ├── PromptDesigner.js  # Visual decomposition editor with Lock/Vary toggles per field
│   │   │   ├── Gallery.js         # Unified gallery: images + videos, media filter, type filter
│   │   │   ├── AssetViewer.js     # Full-size image preview + zoom/pan + edit + versioning
│   │   │   └── ModelSettings.js   # Model registry admin UI: 7 tabs (Image/Video/Chat/Type/Shared Studio, Templates, JSON)
│   │   └── services/
│   │       └── api.js             # Backend API client
│   └── (no build step — served as static files by FastAPI)
├── data/
│   ├── styles/                    # User-uploaded style profiles + reference images
│   ├── generated/                 # Output image assets (PNG + SVG + metadata + versions)
│   ├── video/                     # Video assets (MP4 + thumbnails + job metadata)
│   └── chat/                      # Chat sessions (JSON per session)
├── api-samples/                   # Standalone API client examples (Python, Node.js, Go, Rust)
│   ├── imageGen_python.py         # Full-featured Python client with style management + generation
│   ├── imageGen_node.js           # Node.js equivalent
│   ├── imageGen_go.go             # Go equivalent
│   ├── imageGen_rust.rs           # Rust equivalent
│   └── skill.md                   # AI IDE integration guide (references SPEC.md + /docs)
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
   - **Phase 2 — Full analysis (Claude Opus, vision)**: The cohesion assessment from Phase 1 is fed to Claude Opus alongside the (sampled) reference images, guiding it to analyze appropriately for the collection type. This means diverse collections get useful hints about production patterns, not a diluted "colorful game art" generic description. Image format is detected from magic bytes (JPEG/PNG/GIF/WebP) rather than hardcoded, ensuring correct MIME types in Bedrock Converse API calls. The `palette` field is coerced from dict to list when the LLM returns a dict instead of the expected hex-string list.
   - The analysis prompt is specifically designed for game assets on transparent backgrounds — it asks for material-specific rendering details (how stone, wood, metal are rendered), proportion system, and shadow/lighting specifics. The analysis is **context-aware** — Claude sees both the images AND the user's existing `generation_hints` (passed as "Artist's Guidance") so it understands the user's intent.
   - The cohesion check adds ~$0.01 per analysis (Sonnet with 8 images is very cheap).
5. Claude Sonnet distils the analysis into a concise `generation_hints` paragraph (max 200 words) via `generate_hints(style_id, analyzed_style, user_hints)`, also receiving the user's guidance as context. The hints cover 8 dimensions: perspective, rendering with material specifics, color palette by material, proportions, edge treatment, shadow/lighting, detail level, and background — specific enough that generated assets should visually blend with existing reference images.
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

**Multi-model mode** (`all_models: true`): Generates with multiple models instead of a single model. The frontend sends `selected_models: ["sd35_large", "stable_image_ultra", ...]` — a list of specific model keys chosen via the checkbox dropdown. If `selected_models` is not provided (backward compat), all enabled models are used. Each model becomes an "option" with configurable variations. Models run independently — no shared canary, no cooperative cancellation. Moderation blocks on one model don't affect others. The pipeline is handled by `_run_all_models_generation()` in `generate.py`.

- Models are ordered by moderation strictness (least strict first: SD 3.5 Large → Stable Image Ultra → Stable Image Core) for optimal throughput.
- **Same prompt mode** (default): One prompt refined once, sent to all models for direct comparison.
- **Model-optimized mode** (`model_optimized_prompts: true`): Prompt is refined separately per model (e.g., SD 3.5 Large gets quality boosters, Qwen-Image gets text-rendering cues).
- Per-model results include `status` ("success", "moderation_blocked", "error"), `status_detail` (error message), and the specific `image_model`/`model_label` used.
- SSE events include `model_status` (per-model as each completes) and `all_models_summary` (in the `complete` event).
- Per-variant `metadata.json` stores the actual model used (`image_model`, `model_label`, `all_models: true`).

```
User prompt: "hospital building"
         |
         v
    [Decomposition — Claude Sonnet/Opus]
    Always runs (even when user skips Prompt Designer). Produces structured
    `decomposed_data` with {value, source} tagged fields per attribute.
    Source is "user" (sacred/locked — preserved exactly) or "inferred"
    (variable — may be freely varied across concepts). Style guidance is
    baked into decomposition, not re-injected later.
         |
         v
    [Prompt Designer — optional interactive step]
    Visual editor with Lock/Vary toggles (locked/fixed or randomise)
    per decomposed field. Asset Type + Style selectors sync with main
    page and trigger re-decompose on change.
         |
         v
    [Concept Generation — Claude Opus (complex)]
    Uses locked/variable sections instead of flat recomposed text.
    Locked fields are preserved verbatim; variable fields are creatively
    varied across concepts. `optimal_prompt_words` per model controls
    target length (30-80 words for HunyuanImage,
    120 for SD 3.5 Large). If num_options > 1: generate_concept_prompts()
    produces N distinctly different enhanced prompts as a JSON array.
    If num_options == 1: refine_prompt() (Claude Sonnet, fast) produces
    a single enhanced prompt. Marketing banners use refine_marketing_prompt()
    (Claude Opus, complex).
    Claude extracts exclusions to a separate "NEGATIVE:" line during enhancement.
         |
         v
    [Model-Specific Prompt Enhancement]
    Prompt is restructured as a descriptive CAPTION (not a command) per target model,
    with model-specific guidance applied during the enhancement step:
    - SD 3.5 Large: quality boosters (masterpiece, best quality), style tokens, 2000 chars
    - Stable Image Ultra: photorealistic quality boosters, 2000 chars
    - Stable Image Core: quality boosters, fast tier, 2000 chars
    - HunyuanImage: concise descriptive prompts (30-80 words), CoT reasoning model
    Negative prompt parsed by _parse_negative_prompt() and passed through pipeline.
         |
         v
    For each enhanced prompt, generate num_variations images in parallel:
         |
         v
    [Image Generation — Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core, or a self-hosted model]
    Input: enhanced prompt + negative prompt + random seed per variation
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
| Stable Diffusion 3.5 Large | 2000 |
| Stable Image Ultra | 2000 |
| Stable Image Core | 2000 |

The active limit is passed to all prompt refinement functions (`refine_prompt()`, `refine_marketing_prompt()`, `generate_concept_prompts()`) and adjusts automatically when the user switches models. Stable Diffusion 3.5 Large and Stable Image Ultra get 2x richer prompts with more room for detail, composition, and quality directives. A hard truncation fallback (breaking on word boundaries) still applies per model.

**Model-optimized prompt engineering**: Prompts are written as descriptive **captions**, not imperative commands, following the structure recommended by [AWS Nova Canvas documentation](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html): Subject, Environment, Pose/Action, Lighting, Camera angle, Style. Negation words ("no", "not", "without", "DO NOT") are removed from the main prompt — exclusions are separated into a dedicated negative prompt instead. Model-specific instructions are injected per target model:

| Model | Prompt Style | Key Optimizations |
|-------|-------------|-------------------|
| Stable Diffusion 3.5 Large | Rich caption with boosters | Quality boosters (masterpiece, best quality), style tokens (concept art, artstation), 2000 char limit |
| Stable Image Ultra | Photorealistic caption | Photorealistic quality boosters, cinematic lighting descriptors, 2000 char limit |
| Stable Image Core | Concise caption with boosters | Quality boosters, fast tier, 2000 char limit |
| HunyuanImage 3.0 | Concise descriptive | Short prompts (30-80 words) for CoT reasoning model, no quality boosters needed |

**Negative prompt support**: All Stability image models receive a negative prompt parameter alongside the main prompt. Negative prompts are extracted through multiple mechanisms:

1. **Single-option refinement**: `refine_prompt()` instructs Claude to output a `NEGATIVE:` line, parsed by `_parse_negative_prompt()`.
2. **Multi-option concept generation**: `generate_concept_prompts()` applies two extraction layers:
   - Checks if the AI returned a `NEGATIVE:` entry as the last item in the JSON array.
   - Post-processes each concept prompt with `_strip_negation_phrases()` — a regex-based extractor that finds embedded negation patterns ("No X", "not Y", "without Z", "DO NOT include W") and strips them from the main prompt, collecting the negated terms into a shared negative prompt. Terms are deduplicated via `_deduplicate_negative()`.
3. **Pre-composed prompts**: When the user clicks "Preview Enhanced Prompt" first, the `/api/refine-prompt` endpoint returns `negative_prompt` in its response. The frontend sends this back in the `GenerationRequest.negative_prompt` field so it survives the pre-composed path (which skips backend refinement).

The negative prompt is stored in per-variant `metadata.json`, included in SSE events (`prompts_ready` and `complete`), and displayed in the ImageStudio (red-labeled "Negative prompt — exclusions sent to model" section) and AssetViewer (metadata tab). Per AWS documentation, negation words should not appear in negative prompts either — only the terms to exclude (e.g. "blurry, text, watermark" not "no blurry, no text").

| Model | Negative Prompt Parameter |
|-------|--------------------------|
| Stable Diffusion 3.5 Large | `negative_prompt` field |
| Stable Image Ultra | `negative_prompt` field |
| Stable Image Core | `negative_prompt` field |

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
| `photorealistic` | **OUTPUT**: Photorealistic image (default asset type). **COMPOSITION**: Natural, photograph-like framing — subject fills frame with contextually appropriate background. **FRAMING**: Real-world camera perspective (eye-level, shallow DoF for portraits, wide for landscapes). **TECHNICAL**: Photorealistic lighting, natural skin tones, realistic materials and textures, lens-appropriate bokeh. **DO NOT**: Stylize, cartoonify, or add illustrated/painted aesthetics. Avoid obvious AI artifacts (extra fingers, impossible geometry). |
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
│   ├── enhanced_prompt: str     # The model-specific enhanced prompt for this option
│   └── variants: list[VariantResult]
│       ├── id: str              # "{batch_id}_o{opt}_v{var}"
│       ├── variant_index: int
│       ├── png_path: str        # API URL: /api/gallery/{id}/png
│       ├── svg_path: str | None # API URL: /api/gallery/{id}/svg
│       ├── png_filename: str    # Smart name: "prompt-slug_opt1_var2.png"
│       └── svg_filename: str | None
└── created_at: datetime
```

Each variant is stored in its own directory under `data/generated/{asset_id}/` with `asset.png`, optionally `asset.svg`, and `metadata.json`. The metadata per variant stores: `original_prompt`, `moderation_original` (pre-rewrite prompt when applicable), `negative_prompt` (extracted exclusion terms), `num_options` and `num_variations` (generation-time batch dimensions — used for partial batch tracking after deletions), IP declaration fields (`ip_owned`, `ip_licensed`), and all other generation parameters. Full prompt lineage is: `original_prompt` (user's raw input) → `decomposed_data` (structured JSON from Prompt Designer) → `recomposed_prompt` (flat text from components) → `enhanced_prompt` (model-specific AI-enhanced prompt) → `moderation_original` (if rewritten to pass moderation) → `prompt` (final prompt sent to the image model) + `negative_prompt` (exclusion terms sent separately).

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
- id, prompt, style_id, asset_type, png_url, svg_url, created_at, has_3d (bool — true when a generated `.glb` exists for the asset; drives the "3D" badge and the "3D Models" media filter).

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

**No-cache middleware**: During development, frontend static files are served with no-cache headers to ensure changes are reflected immediately. Gallery images use versioned cache-busting (`?v=N`) to force browser re-fetch after in-place edits (inpaint, erase, etc.).

**Client-side error logging**: All toast errors/warnings and unhandled JS errors are sent to `POST /api/log` and logged server-side with a `[CLIENT]` prefix for unified debugging.

**Style Library** — Grid of style profiles with thumbnails. Upload new styles, upload reference images, trigger AI analysis.
- **Create modal**: Includes "Import References From" section with Local and S3 browse buttons for importing reference images at creation time.
- **Detail view**: Has an "Import & Analyze" button (always auto-analyzes after import, no toggle). The analysis button is contextual: "Analyze Style" when no analysis exists, "Re-Analyze Style" when one does.
- **Server-side file browser modal**: Used for both local and S3 browsing. Single-click selects a file/folder, double-click navigates into a directory. Back button and ".." entry navigate to the parent directory.

**2D Image Studio** (`#image-studio`) — The main image generation workspace with a two-tier result display.

**Prompt mode selector** (segmented control at the top of the prompt area) — two ways to drive generation:
- **Prompt-guided** (default): the standard text-to-image flow described below.
- **Reference-guided**: generate from 1–3 uploaded reference images plus a mandatory user instruction. Two sub-modes:
  - **"Match the reference"** — preserves the subject/product/character from the reference while applying the instruction (theme, background, wardrobe, lighting). Powered by a deployed instruction editor (Qwen-Image-Edit). This mode is **deploy-gated**: it is only offered when `GET /api/generate/reference-available` reports a reference-capable editor is live; otherwise the UI routes the user to deploy it from Custom Models (the `deploy_catalog_key`), mirroring the 3D-pipeline gating pattern.
  - **"Inspired by the reference"** — vision-analyzes the reference(s) + instruction into an enhanced prompt (`POST /api/generate/analyze-reference`), then generates with the user's normal text-to-image models. **Always available** — needs no custom deployment. The derived prompt is previewed so the user sees exactly what the model will receive.

- **Left sidebar** (progressive disclosure layout):
  - **Art Style** selector, **Asset Type** selector.
  - **Image Model** multi-select checkbox dropdown — populated dynamically from the registry (`GET /api/admin/models/image-options`), not hardcoded. Checkboxes allow selecting any combination of models; "All Available Models" toggle at the bottom selects/deselects all. Minimum 1 model required — auto-selects first model on close if empty. Below the dropdown, a smart **summary line** shows the active configuration: `us-east-1 · Premium · $0.06/img` for single model, or `3 models × 2 options × 2 variations = 12 images (~$2.40)` for multi-model. Cost estimate updates live as models are checked/unchecked.
  - **Dimensions** (size presets: 512×512, 768×768, 1024×1024, 1024×576, 576×1024, 1280×720).
  - **Advanced** (collapsible `<details>` section): **Quality** dropdown — shows quality tiers when the model supports them (no current model exposes tiers, so this shows "Default"; the mechanism remains for any future model with `quality_options`). **Region** dropdown — shows the model's available regions sorted cheapest-first, with per-image pricing. "Auto" selects the cheapest. Quality and region changes update the summary line and pricing.
  - **Cost estimate**: `Est. cost: ~$1.50 (25 images × $0.06)` — updates dynamically based on model, quality, region, options, and variations.
  - **Options** count (1-5), **Variations** count (1-5).
  - When **multiple models** are selected: a "Model-optimized prompts" toggle appears, and info text shows the model count, total images, and estimated cost.
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
- **Options row** (indigo/accent borders): Shows different creative concepts as thumbnail cards. Each card shows the first variation as a preview, the option number badge (or model name in "All Models" mode), and a truncated concept prompt. In "All Models" mode, the header changes to "Models — comparison across image models", and blocked/failed models show a semi-transparent overlay badge ("Blocked — moderation" or "Failed"). Click to select an option — the **"Generated prompt — Option N"** (or **"Generated prompt — Stable Diffusion 3.5 Large"**) section updates with the exact prompt and negative prompt used for that option.
- **Concept prompt display**: Shows the full enhanced prompt for the selected option.
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
  - When checked with a strict model selected: shows a recommendation to switch to SD 3.5 Large with a "Switch now" quick-action link.
  - **Pre-Check toggle disabled** when IP is declared — the user asserts they have rights, so pre-screening is unnecessary.
  - IP declaration stored in per-variant `metadata.json` (`ip_owned`, `ip_licensed`) for audit trail.
  - Shown in AssetViewer metadata display.
  - In moderation dialog: acknowledges the IP claim and explains platform limitation.
  - Note: Stability model moderation is platform-enforced by AWS and cannot be bypassed regardless of IP ownership.

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

**Gallery** (`#gallery`) — Unified **masonry** layout (CSS multi-column, variable height) of all generated images and videos sorted newest-first, with each asset shown at its true aspect ratio. Features a **Media filter** (All / 2D Artwork / 3D Models / Video — "3D Models" lists assets that have a generated 3D model), style filter, asset type filter, and search. Assets that have a generated 3D model show a **"3D" badge**. Images load immediately; videos display thumbnails with play overlay, VIDEO badge, and duration indicator. Click a video to open the player modal. Backend always reads metadata fresh from disk. Supports pagination via `limit` and `offset` query parameters. Auto-refreshes via `onShow()` when navigating back, and after image edits or video generation completes.
- **Search bar**: Instant filtering across prompts, style names, and asset types as the user types.
- **Multi-select**: Checkboxes on each asset card for bulk selection. A **"Delete Selected"** button triggers `DELETE /api/gallery/` with `{ids: [...]}` for bulk deletion.
- **Import Image**: An **"Import Image"** button (Gallery header) opens a modal (drag-drop or click-to-browse) that uploads an existing image via `POST /api/gallery/import` (multipart). The user must pick an **asset type** (required — no default; Character/Game Asset enable image-to-3D). Optional title and IP-declaration checkboxes. The backend normalizes the upload to PNG (via Pillow, any input format; EXIF stripped; alpha preserved), then writes the SAME on-disk structure as a generated asset (`data/generated/import_{uuid}/` with `asset.png` + `metadata.json`) so all downstream features (edit, versioning, image-to-3D, source review) work identically. The metadata carries `imported: true`, `image_model: "imported"`, `model_label: "Imported image"`, an empty `prompt` (the optional title doubles as the display prompt), captured `width`/`height`, and no `async_status` (treated as a complete/sync asset). No AI is invoked. Imported assets show an emerald **"Imported"** badge on the gallery card and in the AssetViewer info bar. The gallery refreshes and opens the new asset on success.
- Click any asset to open the AssetViewer.

**AssetViewer** — Full-size preview with zoom/pan and image editing. Fetches full metadata from `GET /api/gallery/{id}` on open. Four tabs:

- **PNG tab** — zoom/pan viewer: mouse wheel to zoom (centered on cursor), click-drag to pan, Fit/1:1/+/- buttons. Active mode (Fit or 1:1) highlighted. Image starts at fit-to-view.
- **Edit tab** — five editing modes:
  - **Inpaint**: Canvas brush mask painter (adjustable brush size). Paint the area to edit → enter a prompt → select an inpainting model from the registry → Apply. Mask extracted as black/white image (white = edit area).
  - **Erase**: Same mask UI, no prompt needed — removes objects and fills background.
  - **Outpaint**: Directional pixel controls (left/right/up/down) + optional prompt. Extends the image. A **live growing-frame preview** renders the image inside an outside gutter with **pixel rulers**, auto-resizing as the extend dimensions change; negative values are blocked. This preview shares a single renderer with the 3D "Improve this Image" (source-completion) dialog.
  - **Replace**: Search & Replace — enter what to find and what to replace it with. Uses `stability_search_replace` format family.
  - **Recolor**: Search & Recolor — select an object and specify the target color. Uses `stability_search_recolor` format family.
  - Models populated dynamically from registry filtered by `model_purpose` (inpainting, erase, outpainting, search_replace, or search_recolor). Shows price per model. **Instruction editors** (`model_purpose: image_edit`, e.g. Qwen-Image-Edit) appear across all five modes via their `capabilities` map and need no mask.
  - **Mask gate**: for mask-requiring model+mode combos, **Apply Edit is disabled until a mask is painted** — the persistent status line explains why ("Paint a mask on the image to enable Apply Edit"). Clearing the mask or switching to a mask-requiring model re-arms the gate; switching to a mask-free editor lifts it. Prevents silent no-op submits.
  - **Instruction-editor outpaint (pre-pad + blend-back)**: mask-free editors regenerate the whole frame at the input's size — they cannot grow a canvas, and a naive "extend the image" instruction makes them *reframe* (pan/crop) and lose content. For Extend/Outpaint on an `image_edit` model, the backend **pre-pads** the source canvas by the requested pixels (new bands filled with edge-average colour + noise), instructs the model to *"replace ONLY the blurry unfinished band"*, resizes the (resolution-bucketed) result back to the padded canvas, and **blends the original pixels back over the original region** with a feathered seam — so the existing image is preserved pixel-exact and only the new band is generated (`backend/services/instruction_outpaint.py`; applied on both the sync and async completion paths).
  - **AI "Generate Prompt" button** (per-mode, model-aware): reads the current image + its original generation prompt and suggests an edit instruction for the active mode via `POST /api/generate/suggest-edit-prompt`. The suggestion is tailored to the selected editor — a **descriptive caption** for Stability edit models and an **imperative instruction** for a Qwen-Image-Edit instruction editor (model-awareness is derived from the registry, not hardcoded). It can also flag `suggest_outpaint` for Extend/Outpaint mode.
  - **Replace original** checkbox (default: checked) — replaces the source image in-place. Uncheck to save as a new gallery asset instead. Metadata records the `source_image_id` and `edit_type` for provenance.
- **Export & Cutouts tab** — per-version export artefacts: a background-removed transparent **PNG cutout**, a **no-background SVG** (vector trace of the cutout), and a **with-background SVG**. Background removal method is user-selectable per run: `local` (free, on-device rembg/u2net — Apache-2.0 weights, one-time download, CPU) or `bedrock` (paid Amazon Bedrock SD remover). One bg-removal produces the cutout; the no-bg SVG is a free local vtracer trace of it. Artefacts are cached per version and method (`asset__nobg_v{N}.png/.svg`); regenerating with a different method replaces them. API: `GET /{id}/export-status`, `POST /{id}/export-variants` (`{method, version}`), `GET /{id}/cutout-png/{v}`, `GET /{id}/cutout-svg/{v}`. The method + cost are recorded in `meta["cutouts"]`. (vtracer runs in a **crash-isolated subprocess** — a known cp314 wheel segfault on tuned params falls back to default params, then to the CLI.)
- **Metadata tab** — full prompt lineage: original prompt → AI-improved prompt → generation prompt → negative prompt (amber-styled). Plus style (from `style_snapshot` fallback), asset type, image model (reads `model_label` from metadata), dimensions, seed, batch ID, option/variation, IP status, filename, created date. Adapts for Type Studio assets. For edit versions, the record distinguishes the **user's typed prompt** (`prompt`) from the **machine-built instruction actually sent** (`edit_prompt_sent` — set when search-folding, removal-transform, or the outpaint instruction builder rewrote it).
- **Info bar model tags (per-version provenance)** — the tag under the image always names the **original generator**; when the *viewed* version is an edit made by a different model, a second tag names that editor ("· this edit"). Tags re-render on every version-bar switch, tracking the viewed version — not the asset's latest.
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
| AI Models | Bedrock (boto3) | Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core, Claude, Nova Sonic, Stability |
| SVG Conversion | vtracer (primary), potrace (fallback), Pillow (last resort) | Cascade of vector tracing methods |
| Text Rendering | Pillow (Python Imaging Library) | Text overlay composition with shadow, outline, glow effects |
| Storage | Local filesystem | Simple start, S3-compatible interface for later migration |

### 4.8 AWS Configuration

**Default AWS Profile**: None — uses the standard AWS credential chain (configurable via `ARTSMOKER_AWS_PROFILE`).

**Two-region architecture**:
- `us-west-2` (`aws_region_models`): Claude models, Stability AI models (including Stable Diffusion 3.5 Large, Stable Image Ultra).
- `us-east-1` (`aws_region_images`): Nova Sonic, Nova Reel.

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

**Inference-param gating** (`_model_supports_temperature` / `_build_inference_config`): Newer Claude tiers (e.g. Opus 4.8) reject the `temperature` Converse param. The gate is **registry-driven** — it reads `supports_temperature` (or `temperature` in `deprecated_params[]`) off the model's `chat_models` entry and omits the param accordingly, with a minimal built-in heuristic only as a last resort when the registry is silent. No hardcoded model lists; new models that deprecate a param work with zero code change once Sync records the capability.

**Auto-roll on Sync** (`_auto_roll_llm_categories`): On every AWS Sync the `fast_llm` and `complex_llm` categories are smartly re-pointed to the newest available Claude — newest **Sonnet** → fast, newest **Opus** → complex (version parsed from the model ID, preferring `us.` cross-region inference profiles, ACTIVE over LEGACY, keeping the category's region when the model is offered there). `fallback_llm` rolls to the **second-newest Sonnet** (one version behind `fast_llm`) so the AccessDenied safety net is a genuinely different yet still-current model rather than a clone of the primary; it degrades to the newest Sonnet if only one version exists. This keeps non-technical users off deprecated models automatically (auto-switch + a logged notice). A manual category pick in Model Settings sets `pinned: true`, which the auto-roll respects — it then only *notifies* that a newer model exists rather than overriding the choice. The roll also probes the chosen model once and records its `supports_temperature` so the param gate above stays self-correcting.

#### Two inference endpoints: `bedrock-runtime` (Converse) and `bedrock-mantle`

Amazon Bedrock exposes **two** inference endpoints, and a model may be reachable on one, the other, or both — via *different* APIs:

| Endpoint | APIs | boto3? | Auth | ArtSmoker client |
|----------|------|--------|------|------------------|
| `bedrock-runtime.{region}.amazonaws.com` | InvokeModel, **Converse**/ConverseStream | ✅ yes | AWS SigV4 (existing creds) | `bedrock_client.py` |
| `bedrock-mantle.{region}.api.aws` | **Chat Completions**, **Responses** (OpenAI-compatible), **Messages** (Anthropic) | ❌ no — HTTP/OpenAI SDK | **Bedrock bearer token** | `mantle_client.py` |

Why both matter: the newest **frontier models are Mantle-only** — OpenAI **GPT-5.x** are Responses-API-only; some new Claude variants (e.g. Mythos) are Messages-only — so they cannot be reached via Converse at all. Conversely, Converse keeps capabilities Mantle lacks (Guardrails, `us.` cross-region inference profiles, structured outputs) and needs no extra token.

**Routing policy — Converse-first, Mantle only when required.** Each `chat_models` entry carries (stamped by Sync, see §4.11): `endpoints[]` (which endpoints list the model), `apis[]` (which APIs it supports), and a resolved **`invoke_endpoint`** + **`invoke_api`** chosen by priority **`converse` > `chat_completions` > `responses` > `messages`** (`mantle_client.resolve_invoke_path`). So Claude/most models stay on the rock-solid boto3 Converse path; Mantle is used only for models Converse can't reach. `invoke_llm` and the Chat Studio stream both branch on the resolved `invoke_endpoint`: runtime → existing boto3 path (unchanged); mantle → `mantle_client` (`_invoke_llm_mantle` / `_chat_stream_mantle`). The startup probe (§7.5) honors the same resolution.

**Mantle auth** (`mantle_client.get_bedrock_token`): Mantle uses a **Bedrock bearer token**, not SigV4. By default a **short-term token** (≤12h, inherits the caller's IAM permissions) is derived from the active AWS credentials via `aws-bedrock-token-generator` — **nothing is stored**, and it's cached per-region + refreshed in-process (8h TTL, inside the ≤12h lifetime). An explicit `AWS_BEARER_TOKEN_BEDROCK` env var takes precedence if set (an operator-owned override). Token values are never logged. If neither the SDK nor a token is available, Mantle is cleanly reported unavailable and the Converse path is unaffected. Mantle is not offered in every region; `mantle_region_for` maps an arbitrary region to the nearest supported one (default fallback `us-west-2`).

**Self-healing on auth failure** (`_mantle_call`): every Mantle invoker runs through a wrapper that, on a `401`/`403`/expired-token error, discards the cached/env token, **force-derives** a fresh short-term token from the AWS credentials, and retries the call **once**. This recovers automatically from a stale `AWS_BEARER_TOKEN_BEDROCK` (e.g. an operator-set short-term token that lapsed) without ever mutating `os.environ` — the operator's value stays as they set it, and the retry simply uses an in-memory derived token. Applies to all three Mantle APIs (Chat Completions, Responses, Messages).

| Model | ID | Region | Purpose |
|-------|----|--------|---------|
| Claude Sonnet | newest Sonnet on Sync | us-west-2 | Fast: prompt refinement, generation hints |
| Claude Opus | newest Opus on Sync | us-west-2 | Complex: style analysis, concept generation, marketing copy |
| Claude 3.5 Sonnet v2 (fallback) | `anthropic.claude-3-5-sonnet-20241022-v2:0` | us-west-2 | Fallback on access denied |
| Stability Remove BG | `us.stability.stable-image-remove-background-v1:0` | us-west-2 | Background removal |
| Stability Upscale | `us.stability.stable-creative-upscale-v1:0` | us-west-2 | Image upscaling |
| Stable Diffusion 3.5 Large | `stability.sd3-5-large-v1:0` | us-west-2 | Primary image generation |
| Stable Image Core 1.0 | `stability.stable-image-core-v1:1` | us-west-2 | Image generation (Stability AI fast) |
| Stable Image Ultra | `stability.stable-image-ultra-v1:1` | us-west-2 | Image generation (Stability AI premium) |
| Nova Reel v1.1 | `amazon.nova-reel-v1:1` | us-east-1 | Video generation (Amazon) |
| Luma Ray v2.0 | `luma.ray-v2:0` | us-west-2 | Video generation (Luma AI) |
| Nova Sonic | `amazon.nova-2-sonic-v1:0` | us-east-1 | Speech-to-text |

> Note: Claude and Stability AI post-processing model IDs use **US inference profiles** (e.g. `us.anthropic.claude-*` for the current Sonnet/Opus, `us.stability.stable-image-remove-background-v1:0`, `us.stability.stable-creative-upscale-v1:0`) rather than full versioned model IDs. The Claude tiers auto-roll to the newest Sonnet/Opus on Sync, so the concrete IDs change over time. Stable Diffusion 3.5 Large and Stable Image Ultra use **direct model IDs** (not inference profiles).

> Note: Stability AI generation models (Stable Diffusion 3.5 Large, Stable Image Ultra) use **aspect ratios** instead of exact pixel dimensions. The backend provides a `_dimensions_to_aspect_ratio()` helper that maps width×height to the closest supported ratio: 1:1, 16:9, 9:16, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21.

### 4.9 Post-Processing Pipeline

The post-processing pipeline (`backend/services/post_processor.py`) applies three optional steps in sequence:

1. **Background removal** — Stability AI Remove Background model. If it fails, the pipeline continues with the original image.
2. **Upscaling** — Stability AI Creative Upscale model. Takes the enhanced prompt as a quality guide. If it fails, the pipeline continues with the current image.
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
- `metadata.json` — full generation metadata (prompt, enhanced_prompt, recomposed_prompt, decomposed_data, style_id, asset_type, seed, filenames, etc.).

Asset IDs follow the pattern `{batch_uuid}_o{option_index}_v{variant_index}` for generated assets, and `import_{uuid}` for images brought in via the Gallery's Import Image feature (see §4.6). Imported assets share the identical directory structure (`asset.png` + `metadata.json`) and are flagged `imported: true` in metadata, so every downstream feature treats them exactly like generated assets.

### 4.11 Model Registry

The model registry (`backend/model_registry.json` v2) is the **single source of truth** for all AI model configuration. No model data is hardcoded in application code — everything is read from this file at runtime. The registry is managed through the admin API and auto-discovery; it should never be edited manually.

**Registry structure** (v2):

1. **Format families** (`format_families`): Define request/response templates by provider. Each family specifies: `prompt_path`, `negative_prompt_path`, `seed_path`, `dimensions_mode` ("pixels" or "aspect_ratio"), `dimensions_paths`, `response_image_path`, and `body_template`. Currently 15 families covering all image services (`amazon_text_to_image`, `stability_text_to_image`, `amazon_inpainting`, `amazon_outpainting`, `stability_inpaint`, `stability_outpaint`, `stability_erase`, `stability_search_replace`, `stability_search_recolor`, `stability_control`, `stability_style_transfer`, `stability_remove_bg`, `stability_upscale`) and video generation (`nova_reel`, `luma_ray`). Adding a new provider or service means adding a format family — no code changes needed.

2. **Bedrock regions** (`bedrock_regions`): Cached list of all AWS regions supporting Bedrock (currently 33). Discovered dynamically during refresh-all via `boto3.Session().get_available_regions("bedrock")`. Read from cache for all other operations — zero AWS calls.

3. **Image pricing** (`image_pricing`): Per-model, per-region, per-quality pricing data from the AWS Pricing API. Fetched during refresh-all only. Keyed by `model_name|region|quality|size`. Used to display cost estimates in the UI and sort regions by cheapest-first.

4. **LLM categories** (`categories`): Named model slots for different purposes:
   - `fast_llm` — newest Claude Sonnet (prompt refinement, hints, pre-check, cohesion check)
   - `complex_llm` — newest Claude Opus (style analysis, concept generation, marketing copy, Type Studio layout)
   - `fallback_llm` — Fallback model on AccessDeniedException
   - `voice` — Nova Sonic (speech-to-text)

   Each category stores: `current` (the model ID), `region`, `provider`, `api_type`, `label`, `description`, and optionally `pinned` (bool). `fast_llm`/`complex_llm` are **auto-rolled to the newest Sonnet/Opus on every Sync** (see §4.8 *Auto-roll on Sync*); setting `pinned: true` — which happens automatically when a user manually picks a model in Model Settings — opts a category out of auto-roll (it's then only notified of newer models, never overridden).

5. **Chat models** (`chat_models`): Discovered LLM models available for Chat Studio. Keyed by internal name (e.g. `claude_sonnet_4_6`, `llama_3_3_70b`, `gpt_5_4`). Each entry stores: `label`, `model_id`, `provider`, `available_regions`, `context_window`, `supports_vision`, `supports_streaming`, `input_price_per_1k`, `output_price_per_1k`, `model_source` (`foundation`, `custom`, `imported`), and optionally `supports_temperature` (recorded by the Sync auto-roll's one-time probe — drives the inference-param gate in §4.8). It also carries the **endpoint/API routing** fields (§4.8): `endpoints[]` (`bedrock-runtime` and/or `bedrock-mantle`), `apis[]` (`converse`/`invoke`/`chat_completions`/`responses`/`messages`), and the resolved `invoke_endpoint` + `invoke_api` the app actually uses (Converse-first). All of these are user-overridable in `.user.json`. Custom and imported models inherit `format_family` from their base model.

6. **Image models** (`image_models`): Keyed by internal name (e.g. `sd35_large`, `stable_image_ultra`). Each entry stores:
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
   - `extra_body` — model-specific body overrides deep-merged into the format family template (e.g. a Stability model `{"output_format": "png"}`)

7. **Post-processing** (`post_processing`): Keyed by operation name (`remove_background`, `upscale`). Each stores: `label`, `model_id`, `region`, `provider`, `enabled`.

**Generic invoker** (`backend/services/bedrock_client.py: invoke_image_model()`): Reads the model's format family from the registry, constructs the request body dynamically using dot-path helpers (`_set_nested`, `_get_nested`, `_deep_merge`), applies quality overrides, gets the Bedrock client for the model's region (with `region_override` support), invokes, and parses the response. No per-model invoke functions needed — any model with a registered format family works.

**Auto-discovery** (`POST /api/admin/discover/refresh-all`):
1. Discovers all Bedrock-supported regions from AWS
2. Fetches per-image pricing from the AWS Pricing API
3. Resets all `available_regions` to empty (prunes stale data)
4. Scans each region — registers new text-to-image, video, and chat models, updates `available_regions` for existing models
5. Discovers custom models via `ListCustomModels`, `ListImportedModels`, `ListCustomModelDeployments`, and `ListProvisionedModelThroughputs` — custom models inherit format family from their base model
6. Disables models no longer found in any region
7. Backfills Bedrock metadata (input/output modalities, lifecycle, ARN, streaming support)
8. **Reconciles the `bedrock-mantle` catalog** (`_reconcile_mantle_models`): queries the Mantle `models.list`, marks discovered runtime models that are *also* on Mantle, and adds **Mantle-only** models (OpenAI GPT-5.x, Claude Mythos, GLM/Grok, …) as new `chat_models` entries — stamping `endpoints[]`/`apis[]`/`invoke_endpoint`/`invoke_api` on every entry (derived from provider/family heuristics grounded in the AWS API-compatibility matrix; dated aliases like `gpt-5.4-2026-03-05` are de-duped against their undated base). Skipped cleanly if Mantle is unavailable.
9. **Auto-rolls** `fast_llm`/`complex_llm` to the newest discovered Sonnet/Opus (respecting `pinned` categories), recording each rolled model's `supports_temperature` (see §4.8 *Auto-roll on Sync*)

This is the **only** operation that calls AWS discovery/pricing APIs. All other operations read from the cached registry file.

**Model validation**: The `GenerationRequest.image_model` field is a plain string validated against registry keys at runtime — not limited to a fixed enum. Dynamically added models are accepted without code changes.

**Frontend**: Model dropdowns are populated from the API on page load — `GET /api/admin/models/image-options` for Image Studio, `GET /api/admin/models/video-options` for Video Studio, and `GET /api/chat/models` for Chat Studio. LLM categories and post-processing use dropdown model pickers (not text fields) populated from discovered models. No hardcoded model lists in JavaScript.

**Model Settings UI** (`ModelSettings.js`): A modal with 7 tabs organized by studio:
- **Image Studio** — image models, regions, quality tiers, prompt limits, moderation strictness. Models are grouped into **five collapsible sections** — Image Generation, Image Editing, Upscaling, Control & Style, Background — with each model carrying a small **role tag** (e.g. Inpaint, Outpaint, Instruction) so a section can hold several roles without one-model-per-section clutter. The mapping is data-driven (an unknown/future `model_purpose` falls back to its own trailing section — never hidden). A multi-mode instruction editor (e.g. Qwen-Image-Edit) is listed **once** with an **"Also covers"** line derived from its `capabilities` map, showing every edit mode it can serve. Deployed custom models surface here automatically (Sync/deploy copies `model_purpose` + `capabilities` from the catalog), each with its own enable/disable toggle. Entries within each section are sorted alphabetically.
- **Video Studio** — video models, S3 bucket settings, regions, pricing
- **Chat Studio** — discovered chat/LLM models with context window, vision support, pricing per 1K tokens
- **Type Studio** — LLM model used for text layout generation
- **Shared Studio** — cross-studio LLM categories (Fast/Complex/Fallback LLM, Voice), post-processing models
- **Prompt Templates** — 28 editable LLM directive prompts organized by studio with two-level navigation
- **Registry JSON** — raw JSON editor for the full model registry

All sections are collapsible with Show All / Hide All toggles. Clicking "Model Settings" in any studio opens the modal to the relevant tab. The modal is 72rem wide.

**Searchable model dropdowns:** All model selection dropdowns (Image Studio, Chat Studio, LLM categories) support type-to-filter search. Models are grouped by provider with section headers. Typing narrows the list in real-time; clearing the search restores the full grouped list. All dropdowns expand to dynamic width when open (content-driven, not fixed). The Chat Studio model dropdown uses a custom scrollable container with max-height (replacing the native `<select>` which showed all models at once).

**Custom Models tab:** Uses a two-level hierarchy — models are organized by Studio (Image, Video, Post-processing) and then by Category within each studio. Each model card shows deployment status, instance type, warm-up state, and action buttons (Deploy/Teardown/Redeploy).

**Pending Jobs button:** Shown in the Image Studio toolbar when async jobs exist. Badge shows count of active jobs. Opens a slide-out panel with per-job details.

**HF Token management button:** In the Custom Models tab header. Shows current token status (stored/not stored). Click to add, update, or delete the shared HuggingFace token. Token is stored encrypted in AWS Secrets Manager (`artsmoker/hf-token`).

**15-minute warm-up display:** Custom model status cards show a warm-up progress bar after deployment reaches `InService`. The bar tracks elapsed time since `InService` was reported, with a 15-minute expected window. Status transitions: Creating → InService (warming up) → Ready.

**Layered configuration (defaults + user overrides)**:

Both the model registry and prompt templates use a two-file layered system that separates system data from user preferences:

```
model_registry.json          (git-tracked, source of truth)
├── format_families          ← code defaults (15 families)
├── image_models             ← discovered by Sync from AWS
├── video_models             ← discovered by Sync from AWS
├── chat_models              ← discovered by Sync from AWS
├── categories               ← default LLM selections
├── post_processing          ← discovered by Sync from AWS
├── bedrock_regions          ← discovered by Sync from AWS
└── image_pricing            ← fetched by Sync from AWS

model_registry.user.json     (gitignored, user preferences only)
├── image_models.X.enabled   ← user disabled this model
├── categories.fast_llm      ← user's LLM category choice
└── video_models.Y.enabled   ← user disabled this model

prompt_templates.json        (git-tracked, runtime source of truth)
└── 28 default templates     ← code _DEFAULTS backfills any missing on load

prompt_templates.user.json   (gitignored, user edits only)
├── chat_title_generate.text ← user customized this template
└── translate_to_english.system_prompt ← user customized system prompt
```

**Load order** (every server start): main file → overlay `.user.json` on top. User preferences always win. Deep merge semantics: dict sections (e.g., individual model entries within `image_models`) are merged at the model level; non-dict sections (e.g., `bedrock_regions` array) are replaced wholesale. `_meta` keys are preserved across save/load cycles.

**Runtime immutability**: `model_registry.json` is **read-only at runtime**. All user actions (enable/disable models, change categories, adjust settings) write exclusively to `model_registry.user.json`. The main file is only written by: (a) Sync from AWS, (b) git pull / auto-update. `prompt_templates.json` is the **runtime source of truth**. The code `_DEFAULTS` dict is a regeneration/backfill **seed** only — on load, templates missing from the JSON are written into it (fresh clone / newly added templates self-heal), but existing JSON entries are never overwritten. User edits overlay via `prompt_templates.user.json`.

**Sync from AWS**: Writes discovered models, pricing, and regions to `model_registry.json`. Sync data (discovered models, pricing, regions) goes to the main file. User preferences in `.user.json` are preserved — a user who disabled a model keeps it disabled even after Sync re-discovers it.

**Git pull / auto-update**: Version-gated — only pulls when remote `APP_VERSION` > local. Compares semantic versions from `config.py`. Dev mode (`ARTSMOKER_DEV_MODE=true`) disables all auto-updates. On successful pull, triggers self-restart via `os.execv` to reload updated code. An `atexit` handler provides runtime restart capability (e.g., after admin-triggered update). Frontend monitor checks `/api/update-status` once on page load and every 24 hours — shows a restart banner when an update is available. Updates `model_registry.json` (format families, code defaults) and `prompt_templates.json` (the git-tracked template file; code `_DEFAULTS` only backfills templates missing from it). User `.user.json` files are gitignored and untouched.

**Deleting `.user.json`**: Restores all settings to defaults. No user preferences leak into the main files.

**First deployment auto-Sync**: On startup, the system checks for an `aws_account_discovered` timestamp in `model_registry.user.json` (gitignored). If missing (fresh deployment — models have never been discovered from this AWS account), a full Sync from AWS runs automatically after credential validation. This discovers all available models, pricing, and regions. Subsequent starts find the timestamp and skip auto-Sync. Since the timestamp is in the gitignored `.user.json`, fresh clones always trigger auto-Sync. Users can always Sync manually from Model Settings at any time.

**Code defaults for self-healing**: If `model_registry.json` is deleted, the system regenerates it from code-defined defaults on startup: 3 base image models (SD 3.5 Large, Stable Image Ultra, Stable Image Core), 4 LLM categories, 15 format families, and 2 post-processing models. The auto-Sync then discovers and adds all remaining models from AWS.

**Prompt templates**: `prompt_templates.json` (git-tracked) is the runtime source of truth. `_load()` reads it first; the code `_DEFAULTS` dict is a backfill/regeneration seed that only fills in templates **missing** from the JSON (never overwrites existing entries), so a fresh clone or a newly added template self-heals. User edits are stored in `prompt_templates.user.json` (gitignored) with only the changed `text` and/or `system_prompt` fields and are overlaid on top; reset restores the JSON default.

**Startup sequence**:
1. Auto-update: compare local `APP_VERSION` against remote, pull if remote is newer (skipped if `ARTSMOKER_DEV_MODE=true`), self-restart via `os.execv` if code changed
2. Check config freshness: prompt templates loaded from `prompt_templates.json` (code seed backfills any missing), registry checked for `aws_account_discovered` field
3. Ensure data directories
4. Validate AWS credentials + Bedrock access
5. If registry never synced + credentials valid → auto-Sync from AWS (30-60 seconds, first deployment only)
6. Initialize telemetry, start server

**Registry as single source of truth**: The application code contains **zero hardcoded model IDs, API parameters, or invocation templates**. Everything the system needs to invoke any Bedrock service — model IDs, regions, request body structures, prompt paths, negative prompt paths, mask paths, seed ranges, quality tiers, dimension modes, response parsing, pricing, and parameter constraints — is stored in `model_registry.json` and read at runtime. The format families define the complete API contract for each provider/service type, including a `parameters` spec with types, ranges, defaults, and descriptions for every configurable field. This means:

- Adding a new image model requires zero code changes — just register it via auto-discovery or the admin API
- Adding a new image service (e.g., a new Stability AI feature) requires adding a format family definition in `_DEFAULT_FORMAT_FAMILIES` in `model_registry.py` — the invoker and UI adapt automatically
- The LLM models used for prompt refinement, style analysis, and Type Studio layout are all configurable via `categories.fast_llm` and `categories.complex_llm` — the user can switch to any Converse-compatible model
- All pricing, regions, quality tiers, and model availability come from the registry — populated by auto-discovery and the AWS Pricing API during refresh-all

**Backward compatibility**: Generated assets reference model keys (e.g. `sd35_large`), not raw Bedrock model IDs. Changing a model ID in the registry does not break old asset metadata.

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
| POST | `/api/generate/edit` | Image editing services. Accepts `source_image_id`, `source_version` (int, honors 2D versioning), `model` (registry key), `prompt`, `negative_prompt`, `mask` (base64, white = edit area), `mask_prompt` (natural-language mask target), `outpaint_left/right/up/down`, `extra_params`. **Two editor classes:** (1) **mask-based** (Stability inpaint/outpaint/erase/search-replace/recolor, `model_purpose` = the specific mode) — require a painted mask or mask prompt; (2) **mask-free instruction editors** (`model_purpose: image_edit`, e.g. Qwen-Image-Edit) — edit from a text instruction alone across all five modes via their `capabilities` map, no mask needed. Result saved as a new gallery asset with metadata linking to the source. |
| POST | `/api/generate/suggest-edit-prompt` | Suggest an edit instruction for the AssetViewer Edit tab. Body: `{asset_id, version, mode, model}`. Reads the image + its original generation prompt and returns `{prompt, search_prompt, reasoning, suggest_outpaint}`. The suggested `prompt` is a **descriptive caption** for Stability edit models and an **imperative instruction** for a Qwen-Image-Edit instruction editor — model-aware, derived from the registry (not hardcoded). Powers the Edit tab's per-mode "Generate Prompt" button. |
| POST | `/api/generate/analyze-moderation` | Analyze a moderation-blocked prompt. Accepts `force_rewrite` (bool) — when false (default): Phase 1 tries alternative models, Phase 2 rewrites if all reject. When true: skips model switching, rewrites directly for the target model and tests against it. Returns `action`, `working_model`, `issues`, `explanation`, `rewritten_prompt`, `verified`, and `attempts` (log). |
| GET | `/api/generate/reference-available` | Whether a reference-capable editor (e.g. Qwen-Image-Edit) is deployed. Gates the "Match the reference" mode in the Image Studio. Returns `{available, model_key, endpoint_name, deploy_catalog_key}` — when unavailable, `deploy_catalog_key` tells the UI which catalog model to route the user to in the Custom Models deploy flow (mirrors the 3D gating pattern). "Inspired by the reference" mode needs no custom model and is always available. |
| POST | `/api/generate/analyze-reference` | Vision-analyze 1–3 reference images + a mandatory user instruction → an enhanced prompt, for the "Inspired by the reference" preview (so the user sees the prompt the model will receive). Body (`AnalyzeReferenceRequest`): `images` (1–3 base64 PNGs), `prompt` (required — what to do with the reference), `asset_type`, `ui_lang` (soft translation hint). Returns the enhanced prompt + accumulated cost. |

**Pre-screen request body** (`PreScreenRequest`):
```json
{
  "prompt": "a warrior with a sword",
  "image_model": "sd35_large"
}
```

**Pre-screen response**:
```json
{
  "likely_safe": false,
  "issues": ["weapon/combat language may trigger the selected model's moderation"],
  "explanation": "The selected model is strict about weapons and combat...",
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
  "image_model": "stable_image_core",
  "width": 512,
  "height": 512
}
```

**Moderation analysis response** — multi-phase, returns different actions:
```json
{
  "action": "switch_model",
  "working_model": "sd35_large",
  "original_model": "stable_image_core",
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
  "attempts": [{"model": "sd35_large", "result": "blocked"}, {"model": "stable_image_ultra", "result": "blocked"}]
}
```

**Request body** (`GenerationRequest`):
```json
{
  "prompt": "hospital building",
  "original_prompt": "hospital",
  "style_id": "city-builder-iso",
  "asset_type": "game_asset",
  "image_model": "sd35_large",
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
- `image_model` (default `sd35_large`): Any valid key from the model registry (e.g. `sd35_large`, `stable_image_ultra`, `stable_image_core`). Validated against the registry at runtime — not limited to a fixed enum. New models added via auto-discovery are accepted without code changes.
- `quality` (optional, `str | None`): Quality tier override (e.g. `"standard"`, `"premium"`). If null, uses the model's `default_quality` from the registry. Only relevant for models with `quality_options`.
- `region` (optional, `str | None`): Region override for the model. If null, uses the model's default `region` from the registry. Must be one of the model's `available_regions`.
- `width` / `height` (default 1024): Output dimensions in pixels.
- `num_options` (default 5, range 1-5): Number of distinct concept designs.
- `num_variations` (default 5, range 1-5): Number of seed variants per option.
- `remove_background` (default true): Run Stability AI background removal.
- `generate_svg` (default true): Convert to SVG.
- `upscale` (default false): Run Stability AI upscaling.
- `negative_prompt` (default ""): Negative prompt carried from the Compose step.
- `all_models` (default false): When true, generates with multiple models (one option per model). Dispatches to `_run_all_models_generation()`.
- `selected_models` (default null): List of specific model keys for multi-model generation. When provided with `all_models=true`, only those models are used. When null, all enabled models run.
- `model_optimized_prompts` (default false): Only used when `all_models` is true. When true, refines the prompt separately per model for tailored output. When false, all models receive the same prompt for direct comparison. When `pre_composed` is true and refinement is skipped, the backend uses this value instead of extracting from refinement.
- `ip_owned` (default false): User asserts IP ownership over the content.
- `ip_licensed` (default false): User asserts licensing rights. Both IP fields are stored in per-variant metadata for audit trail.

### 5.3 Prompt Refinement & Prompt Designer

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/refine-prompt/` | Quick Enhance — auto-refine a prompt into a detailed image caption. |
| POST | `/api/refine-prompt/decompose` | Prompt Designer — decompose a user prompt into structured visual components (subject, scene, composition, lighting, style with color palette). |
| POST | `/api/refine-prompt/recompose` | Reassemble structured components into a flat recomposed prompt. |
| POST | `/api/refine-prompt/classify-asset-type` | LLM-powered asset type classification — detects if the selected asset type matches the prompt (e.g., scene described as Game Asset → suggests Environment). |
| POST | `/api/refine-prompt/translate-preview` | Lightweight language detection + translation preview. |

**Prompt pipeline terminology:**

The image generation pipeline transforms the user's idea through four stages:

1. **User Prompt** — the user's raw text input (Step 1 textarea). Always preserved, never overwritten by the system.
2. **Decomposed Data** — structured JSON with `subject`, `scene`, `composition`, `lighting`, `style` (including color palette). Each field is a `{value, source}` tagged object where `source` is `"user"` (sacred/locked — preserved exactly across concepts) or `"inferred"` (variable — may be freely varied). Style guidance is baked into decomposition, not re-injected later. This is the intermediate representation produced by `/api/refine-prompt/decompose` and edited in the Prompt Designer (Step 2). Stored in metadata as `decomposed_data`. Decomposition always runs (even when the user skips Prompt Designer), providing structured data for concept generation.
3. **Recomposed Prompt** — flat text rebuilt from the decomposed components by `/api/refine-prompt/recompose`, now split into locked (user-sourced) and variable (inferred) sections for concept generation. Stored in metadata as `recomposed_prompt`. Model-specific prompt guidance is **not** applied at this stage.
4. **Enhanced AI Prompt** — model-specific optimized prompt generated by the LLM from the locked/variable sections + model guidance. Target length controlled by `optimal_prompt_words` per model (30-80 for HunyuanImage, 120 for SD 3.5 Large). This is what actually gets sent to the image model. Stored in metadata as `enhanced_prompt`. Each option gets its own enhanced prompt (via `generate_concept_prompts` for N×M mode).

All three derived levels (`decomposed_data`, `recomposed_prompt`, `enhanced_prompt`) are persisted to `metadata.json` alongside the original `prompt`.

**Generation flows:**

- **1×1 (single option, single variation)**: decompose → recompose (locked/variable) → enhance (1 enhanced prompt) → 1 image
- **N×M (multiple options/variations)**: decompose → recompose (locked/variable) → enhance (N enhanced prompts via `generate_concept_prompts`, locked sections preserved, variable sections varied) → N options × M variations (different seeds per variation)
- **Skip Steps 2/3**: Generate auto-enhances the user prompt server-side (decompose + recompose + enhance happen internally — decompose always runs even when Prompt Designer is skipped)

**Prompt Designer flow:**

The 2D Image Studio uses a guided 3-step workflow:

1. **Step 1 — Describe** (User Prompt): User types a prompt. The textarea placeholder adapts to the selected asset type (e.g., "A young female warrior..." for Character, "A misty Japanese garden..." for Environment).

2. **Step 2 — Prompt Designer** *(optional)* (Decomposed Data → Recomposed Prompt): Clicking the Prompt Designer button:
   - Runs LLM asset type classification first — if mismatch detected (e.g., scene prompt + Game Asset), a dialog suggests switching
   - Sends prompt to `/api/refine-prompt/decompose` — LLM decomposes into structured JSON with `{value, source}` tagged fields:
     ```json
     {
       "subject": {
         "description": {"value": "young female warrior", "source": "user"},
         "clothing": {"value": "leather armor with silver trim", "source": "inferred"},
         ...
       },
       "scene": { "setting": {"value": "...", "source": "..."}, ... },
       "composition": { "camera_angle": {"value": "...", "source": "..."}, ... },
       "lighting": { "key_light": {"value": "...", "source": "..."}, ... },
       "style": { "art_style": {"value": "...", "source": "..."}, "color_palette": [...] }
     }
     ```
   - Displayed in a tabbed modal (Subject | Scene | Composition | Lighting | Style & Colors) with **Asset Type** and **Style** selectors at the top that sync with the main page and trigger re-decompose on change
   - Each field is editable with **Lock/Vary toggles** (locked/fixed or randomise) per field. Locked fields (`source: "user"`) are preserved verbatim across concepts; variable fields (`source: "inferred"`) are freely varied. Default is Randomise for inferred fields; editing a field does not auto-lock it
   - Color palette shown as named swatches with hex values and usage descriptions
   - Style Library hints are incorporated if a style is selected — baked into decomposition
   - Info footer explains the lock/vary behavior below the action buttons
   - "Generate Enhanced Prompt" → sends edited components to `/api/refine-prompt/recompose` → recomposed prompt (with locked/variable sections) shown in Step 2, then enhanced with model guidance → Enhanced AI Prompt appears in Step 3

3. **Step 3 — Enhanced Prompt Preview** *(optional)* (Enhanced AI Prompt): Shows the model-specific enhanced prompt that the image model will receive. Generated from the recomposed prompt + model guidance. Editable before generating.

**Generate** works at any point — Steps 2 and 3 are optional. If skipped, Generate auto-enhances the prompt server-side.

**Model-specific prompt handling:**
- Each model can have `prompt_guidance` in its registry invoke config — LLM instructions for writing prompts optimized for that model's architecture
- Models declare `supports_negative_prompt: true/false` — templates conditionally include/skip NEGATIVE: line. FLUX models skip negative prompts entirely; the LLM focuses all effort on the positive caption
- FLUX.2 guidance targets 60-100 word concise prompts (not verbose 300+ word descriptions that dilute signal)
- HunyuanImage 3.0 guidance targets 30-80 word concise prompts — the model has internal CoT reasoning, so shorter prompts with clear intent outperform verbose descriptions
- The `image_refine_single` and `prompt_recompose` templates pass `{model_specific_instructions}` so the LLM adapts per model

**Asset type classification** (`/api/refine-prompt/classify-asset-type`):

Runs exactly once per prompt session — whichever button the user clicks first (Prompt Designer, Generate Enhanced Prompt, or Generate) triggers the check. The `_assetTypeConfirmed` flag prevents re-checking on subsequent buttons. Editing the prompt text resets the flag.

Uses an LLM to determine the best asset type for a prompt. Key distinction: a person mentioned IN a scene (e.g., "woman piloting a train shown from outside with a village backdrop") is classified as Environment (scene is the subject), not Character. Only prompts where the person IS the primary focal point are classified as Character.

**Refine request body** (`PromptRefineRequest`):
```json
{
  "prompt": "hospital building",
  "style_id": "city-builder-iso",
  "asset_type": "game_asset",
  "image_model": "sd35_large"
}
```

**Refine response**:
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
| GET | `/api/gallery/{id}/version-svg/{version}` | Download the SVG for a specific version (falls back to `asset.svg` for the current version). |
| GET | `/api/gallery/{id}/export-status?version=N` | Export & Cutouts: which artefacts (cutout PNG / no-bg SVG / with-bg SVG) exist for the version, plus the method used. |
| POST | `/api/gallery/{id}/export-variants` | Create the export artefacts for a version. Body: `{method: "local"\|"bedrock", version}`. Idempotent per method (re-running with the same method reuses); switching method regenerates. Local = free (rembg); bedrock cost is recorded in `meta["cutouts"]` + cost history. |
| GET | `/api/gallery/{id}/cutout-png/{version}` | Download the background-removed transparent PNG cutout for a version. |
| GET | `/api/gallery/{id}/cutout-svg/{version}` | Download the no-background SVG (vector trace of the cutout) for a version. |

**Async status indicators:** Gallery items from self-hosted model generation display status badges — pending (amber pulse), complete (green), or failed (red with error tooltip). Pending items show a placeholder thumbnail that live-replaces with the actual image on completion.

**Model label auto-backfill:** When loading gallery items, the model key is resolved to a human-readable label from the registry. If the model key no longer exists in the registry (e.g., model was removed), the raw key is displayed as fallback.

**Date format:** All gallery timestamps show the full date + time + timezone (e.g., "07 Apr 2026, 14:32 PDT"), consistent across all studios and the gallery grid.

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

**Prompt enhancement:** When "Enhance prompt" is enabled, the `video_enhance_prompt` template adds camera movements, lighting, and temporal cues. The template receives `{model_guidance}` from the video model's `prompt_guidance` field in the registry (or a sensible default: "Richly descriptive, up to 5000 characters" for Luma Ray, "Concise descriptive caption, 512 character limit" for Nova Reel). `{optimal_length}` comes from the model's `optimal_prompt_words` field. Video models have no negative prompt support — avoidance terms are woven into positive descriptions naturally.

### 5.8 Chat Studio

A full-featured LLM chat interface running on the user's own AWS account. 80+ models from 16 providers, all discovered automatically via Sync from AWS.

**Frontend features** (`ChatStudio.js`):
- **Streaming responses** — real-time token-by-token rendering via Bedrock ConverseStream SSE
- **Markdown rendering** — headings, bold/italic, lists, tables, blockquotes, horizontal rules (via marked.js)
- **Code blocks** — syntax highlighting (highlight.js) with language badge and one-click copy button
- **Per-message metrics** — input/output tokens, latency, estimated cost, model used
- **Context window bar** — visual fill indicator (green/amber/red) with used/max token count
- **Region switching** — each model shows all available regions; pick the closest or cheapest
- **Session management** — sidebar with session list, inline rename, duplicate, delete, search/filter
- **System prompt templates** — 6 built-in: General Assistant, Coding Expert, Creative Writer, Game Designer, Data Analyst, Technical Writer
- **Vision/multimodal** — drag-drop, file picker, or Ctrl+V paste images for vision-capable models
- **Context compaction** — AI summarizes older messages to free context window space (summary injected as user message to maintain alternation)
- **Regenerate** — re-run any AI response with the same prompt
- **Edit & resend** — modify any user message and replay from that point
- **Fork** — branch a conversation from any message into a new session
- **Export** — download conversation as Markdown with full metadata
- **Search** — search within session messages, returns matching snippets with context
- **Auto-title** — AI generates a 3-8 word session title from the first exchange
- **Pricing info** — model picker shows cost per 1K tokens; pricing bar shows estimated cost for 10K/100K token conversations
- **PulseBoard telemetry** — session summary events (one per session interaction, not per message)

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
| GET | `/api/chat/sessions/{id}/export` | Export session as Markdown file download. Includes session metadata, model info, and all messages with timestamps. |
| GET | `/api/chat/sessions/{id}/search?q=` | Search within a session's messages. Case-insensitive substring search. Returns matching snippets with surrounding context. |
| POST | `/api/chat/compact` | Compact older messages via LLM summarization. Keeps last N messages verbatim, replaces older with a summary message (role: user to maintain strict alternation). |
| POST | `/api/chat/telemetry` | Receive session summary event from frontend (one event per session interaction, not per message). |

### 5.9 Browse

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/browse/local?path=~` | Browse local filesystem directories. Returns list of files and subdirectories at the given path. Recognizes all supported asset formats: images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) and 3D models (.glb, .gltf). Used by the Style Library file browser modal. |
| GET | `/api/browse/s3/buckets` | List available S3 buckets. |
| GET | `/api/browse/s3?bucket=name&prefix=path` | Browse objects in an S3 bucket at the given prefix. |
| POST | `/api/browse/s3/create-bucket` | Create a new S3 bucket. Payload: `name`, `region`. Validates bucket name format. Returns created bucket info. |

### 5.10 Custom Models (Self-Hosted on Amazon SageMaker)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/custom-models/catalog` | List all available custom models with deployment status. Checks Amazon SageMaker endpoint status for each. |
| GET | `/api/custom-models/catalog/{key}` | Get detailed info for a specific model from the catalog. |
| POST | `/api/custom-models/deploy` | Deploy a model. For HuggingFace: uploads handler to S3 → creates Amazon SageMaker endpoint (container pulls from HF). For others: download → S3 → endpoint. Body: `{model_key, endpoint_type ("async"/"realtime"), instance_type (optional)}`. |
| GET | `/api/custom-models/status/{key}` | Check Amazon SageMaker endpoint deployment status (Creating, InService, Failed, etc.). Includes 15-minute warm-up awareness — InService does not mean ready (model download may still be in progress). |
| DELETE | `/api/custom-models/teardown/{key}` | Full cleanup: deletes endpoint, endpoint config, model, auto-scaling policies + scalable target, CloudWatch alarms, registry entries, in-memory async jobs, and S3-persisted async jobs (`artsmoker/async-jobs/*.json`). Optional `?delete_s3=true` to also remove S3 model artifacts. |
| POST | `/api/custom-models/redeploy/{key}` | Tear down and redeploy. For updates/patches. |
| GET | `/api/custom-models/hf-token-status` | Check whether a HuggingFace token is stored in Secrets Manager. Returns `{has_token, secret_name}`. |
| POST | `/api/custom-models/hf-token` | Store or update the HuggingFace token. Encrypted in AWS Secrets Manager (`artsmoker/hf-token`). Shared across all gated models. Body: `{token}`. |
| DELETE | `/api/custom-models/hf-token` | Delete the stored HuggingFace token from Secrets Manager. |
| GET | `/api/custom-models/gated-access/{key}` | Pre-check whether the stored HF token can access **every** repo this model pulls — its `source` repo plus any HuggingFace `dependencies[]`. Probes each via `huggingface_hub.auth_check`, returning per-repo `{repo_id, gated, accessible, status, action, license_url}` plus `all_clear` / `blocking[]`. Drives the deploy dialog's per-repo ✓/✗ + guided next-step UX. Never returns the token. |

**Architecture:**

```
Catalog (custom_models.py)
  ↓ (source URLs, invoke config)
Deployer (sagemaker_deployer.py)
  ↓ HuggingFace models: handler to S3 → endpoint (container pulls from HF)
  ↓ Other models:       download → S3 → endpoint
Registry (model_registry.json)
  ↓ (model_source=custom_hosted, invoke config, endpoint info)
Invoker (sagemaker_invoker.py)
  ↓ (routes to Amazon SageMaker instead of Bedrock)
Studios (Image, Video, Post-processing)
```

**Registry-driven design:** All model behavior is defined by data in the catalog `invoke` section — no model-specific code paths anywhere. Adding a new model = adding a catalog entry. The universal inference handler (`sagemaker_handlers/inference.py`) reads configuration from environment variables set by the deployer from the catalog.

**Catalog invoke config** (drives everything):
```json
{
  "invoke": {
    "library": "diffusers",
    "loader_class": "AutoPipelineForText2Image",
    "torch_dtype": "bfloat16",
    "enable_cpu_offload": true,
    "enable_sequential_cpu_offload": false,
    "enable_vae_slicing": true,
    "enable_vae_tiling": false,
    "predictor_type": "text_to_image",
    "input_fields": {
      "prompt": {"type": "string", "required": true},
      "width": {"type": "int", "default": 1024},
      "num_inference_steps": {"type": "int", "default": 4},
      "guidance_scale": {"type": "float", "default": 0.0},
      "seed": {"type": "int", "required": false}
    },
    "output_type": "base64_png",
    "max_prompt_length": 2048
  }
}
```

**GPU auto-detection:** The inference handler detects GPU count at runtime and selects the optimal strategy:
- **2+ GPUs** → `device_map="auto"` (naive pipeline parallelism — more memory, not more speed)
- **1 GPU + `block_swap_blocks > 0`** → CPU-first sliding window offload (block swap)
- **1 GPU + no swap** → direct `.to("cuda")`

The same catalog entry works on any instance type — no per-instance configuration needed.

**FlashInfer support (Blackwell SM 12.0):** On g7e instances (NVIDIA Blackwell B200), FlashInfer fused MoE kernels dramatically reduce inference time. Requirements: `torch+cu129`, pre-compiled `flashinfer-jit-cache` wheels (no nvcc/JIT needed), `FLASHINFER_CUDA_ARCH_LIST=12.0f` for SM120 cache lookup, `FLASHINFER_DISABLE_JIT=1` to prevent fallback to nvcc. BF16 + FlashInfer on g7e.12xlarge: **68s/image** (vs 19 min for INT8 with BnB dequantization overhead). Speed comes from FlashInfer fused kernels, not from extra GPUs.

**NVMe instance families:** Instances with local NVMe storage (g7e, p5, p5e, p6) reject the `VolumeSizeInGB` parameter — SageMaker auto-mounts their NVMe. The deployer skips this parameter for these families.

**Memory optimizations** (catalog-driven per model): The invoke config controls four memory strategies applied at model load time:
- `enable_model_cpu_offload` — offloads inactive pipeline stages to CPU (recommended default)
- `enable_sequential_cpu_offload` — aggressive per-layer offloading for very large models
- `enable_vae_slicing` — processes VAE decoding in slices to reduce VRAM peak
- `enable_vae_tiling` — tiles VAE decoding for high-resolution outputs

Each model's catalog entry specifies which optimizations to enable. The inference handler applies them automatically — no per-model code.

**HuggingFace model loading:** The container uses `ARTSMOKER_HF_REPO` (not `HF_MODEL_ID`) so our inference handler controls loading with CPU offloading strategies from the catalog. The deployer sets `ARTSMOKER_HF_REPO` to the HuggingFace repo ID and `INVOKE_CONFIG` with the full invoke JSON. The inference handler reads these, downloads the model, and applies memory optimizations before serving. For gated models, the HF token is stored encrypted in **AWS Secrets Manager** (`artsmoker/hf-token`) — a single shared token for all gated models, managed via the UI button. The token is also passed as `HUGGING_FACE_HUB_TOKEN` env var to the container (read-only, visible only in the user's own AWS account via `sagemaker:DescribeModel`).

**Model bundles:** Lightweight models that share similar architectures (e.g., multiple LoRA adapters on the same base) can be deployed as a bundle on a single Amazon SageMaker endpoint. The inference handler loads the base model once and swaps adapters per request, reducing instance count and cost.

**Non-HuggingFace models** (GitHub releases like Real-ESRGAN, CodeFormer): downloaded to the server, uploaded to S3 with the inference handler, then the endpoint loads from S3.

**Deployment types:**
- **Async** (scale-to-zero): `AsyncInferenceConfig` with S3 output. Scales to zero instances when idle ($0 cost). Cold start from zero: 5-15 minutes (includes HF model download on first start). Input uploaded to S3, output polled from S3.
- **Realtime** (always-on): Standard endpoint with `InitialInstanceCount=1`. Instant inference. Costs ~$1.21/hr continuously (ml.g5.xlarge). Instance pricing: g5.2xlarge $1.51/hr, g6e.4xlarge $3.76/hr, g7e.12xlarge $10.36/hr.

**Auto-scaling** (async endpoints): Dual scaling policy for true scale-to-zero:
- **TargetTracking** — scales in to zero instances when no requests arrive (zero-cost idle)
- **StepScaling** with `HasBacklogWithoutCapacity` CloudWatch alarm — scales out from zero when the first request lands in the backlog

This combination solves the cold-start-from-zero problem: TargetTracking alone cannot scale from 0→1 (no instances = no metric data). The StepScaling alarm triggers on backlog presence regardless of instance count.

**15-minute warm-up window:** Amazon SageMaker reports `InService` as soon as the container starts, but the model is not ready until weights are downloaded from HuggingFace and loaded into GPU memory. For large models (e.g., 23-70GB), this takes 5-15 minutes after `InService`. The status endpoint tracks this window and the frontend displays a warm-up progress indicator.

**NF4 quantization:** BnB NF4 quantization requires CUDA and loads layer-by-layer to GPU. No `device_map` override on quantization components (setting `device_map="cpu"` prevents quantization from firing — weights stay bf16). Peak GPU usage during quantization: ~13 GB for FLUX.2 transformer (7 shards). After quantization, NF4 transformer (~10 GB) + text encoder (~5 GB) = ~15 GB on 44.5 GB L40S with 29 GB headroom.

**S3 model cache:** After a successful model load, the handler saves pipeline components to S3 (`artsmoker/custom-models/{model_key}/model-cache/`) for faster cold starts. Cache behavior per component:
- `.cache-info.json` — version fingerprint + per-component `preserved` flag. Fingerprint changes when model key, HF repo, catalog version, or quantization config changes → automatic cache invalidation.
- **preserved=true** — NF4 packed uint8 weights with quantization metadata. Diffusers models (e.g., `Flux2Transformer2DModel`) write proper NF4 via `save_pretrained()`. Transformers models (e.g., `Mistral3ForConditionalGeneration`) may not preserve quant_state — handler verifies by inspecting safetensors for `bitsandbytes__*` keys before marking preserved. Workaround writes `quantization_config.json` manually (diffusers FrozenDict name-mangling bug). Fast path: loads directly to GPU, `pipe.to("cuda")`, ~30-60s/image inference.
- **preserved=false** — bf16 weights without BnB metadata. Handler cleans stale quantization artifacts, re-quantizes to NF4 on GPU from local disk (~3 min per component vs ~3 min from HuggingFace).
- Cache save runs in a background thread after `model_fn()` completes (does not block inference). Aborts if saved weights are corrupt (no BnB quant_state and not valid bf16).

**Resilient cache load fallback chain** (per component, each step tried once):
1. `preserved=true` → direct NF4 load (fastest)
2. If fails → cleanup GPU → re-quantize from cached bf16 weights
3. If fails → cleanup GPU → download from HuggingFace with quantization
4. If fails → log error, component skipped → `model_cpu_offload` prevents OOM

**Auto-scaling:** Registered after model readiness confirmed (not at endpoint InService — model may still be loading). Checks AWS for existing policies on startup to avoid redundant API calls. Configuration:
- Scale-to-zero: TargetTracking on `ApproximateBacklogSizePerInstance`, cooldown derived from `typical_latency_seconds` in the catalog (`max(600, typical * 2)`) — prevents instances from being killed mid-inference. The catalog key lookup strips the hash suffix from endpoint names (e.g., `_620a`) via prefix match.
- Scale-from-zero: StepScaling on `HasBacklogWithoutCapacity` alarm, 60s cooldown for fast response
- Instance recommendations: `allowed_instances` field in catalog requirements filters instance dropdown (e.g., FLUX.2 limited to g6e.4xlarge+, HunyuanImage limited to g7e.2xlarge+)

**Multi-instance deployment (Deploy Another):** A single catalog model can be deployed on multiple instances simultaneously. Each deployment gets a unique endpoint name with a different hash suffix (e.g., `flux2-dev-nf4_620a`, `flux2-dev-nf4_b3f1`). This enables running the same model on different instance types for cost/performance comparison, or running multiple copies for higher throughput.

- **API:** The catalog response includes a `deployed_instances[]` array per model (1:many mapping). Each entry contains `deployed_key`, `endpoint_name`, `instance_type`, `label`, `status`, `warming_up`, `warmup_detail`, `instance_count`, `deploy_progress`, and `deploy_stage`. Top-level `deployment_status` and `endpoint_name` use the first instance for backward compatibility.
- **Deploy:** POST `/api/custom-models/deploy` with the same `model_key` creates a new endpoint with a fresh hash suffix. The deployer generates the unique suffix from `uuid4().hex[:4]` and registers the new instance in `model_registry.user.json` under `image_models.{catalog_key}_{hash}`.
- **Teardown:** DELETE `/api/custom-models/teardown/{deployed_key}` targets a specific deployed instance by its `deployed_key` (e.g., `flux2-dev-nf4_620a`). Each instance is torn down independently — removing one does not affect others.
- **Redeploy:** POST `/api/custom-models/redeploy/{deployed_key}` tears down and redeploys a specific instance.
- **Image Models dropdown:** Each deployment appears as a separate entry in the model selector with its instance type and deploy timestamp, so users can target a specific deployment for inference.
- **UI:** The Custom Models dialog shows a "Deploy Another" button (visible when at least one instance is already deployed). Deployed instances are listed in an expandable section within each catalog model card, with per-instance status indicator, Remove button, and Redeploy button. Instance rows use fixed-width columns for visual alignment.
- **License:** License acceptance is required once per catalog model (not per instance). The acceptance is recorded in `model_registry.user.json` under `license_acceptances` with the model key and timestamp.

**Model dropdown visibility (image-options / video-options):** Custom-hosted models appear in the Image Studio and Video Studio dropdowns based on a `model_ready` flag persisted in the user registry. This flag means "validated at least once" — set to `True` after the first successful model load, cleared only on teardown or redeploy. Dropdown behavior by state:

| State | Listed in dropdown | Accepts jobs |
|---|---|---|
| First deploy (never loaded) | No — hidden until model loads successfully | No |
| Warm & active (instances running) | Yes | Yes — immediate inference |
| Scaled to zero (idle, 0 instances) | Yes | Yes — SageMaker queues in backlog, backlog alarm triggers scale-out |
| Scaling out (provisioning) | Yes | Yes — jobs continue queuing |
| Teardown / redeploy | No — `model_ready` cleared | No |

This ensures users can always submit async jobs to models they've previously validated, even when instances are idle. The `HasBacklogWithoutCapacity` CloudWatch alarm automatically scales from zero when jobs land in the backlog.

**Cold start times** (FLUX.2 dev on g6e.4xlarge):
- Fresh build (no cache): ~6 min (HF download + NF4 quantize on GPU)
- From S3 cache (preserved=true): ~4 min (S3 download + direct NF4 load for transformer, HF fallback for text encoder)
- Inference: ~80s/image at 1024x1024, 40 steps on GPU fast path

**Cold start times** (HunyuanImage 3.0 BF16 on g7e.12xlarge):
- Fresh build: ~10 min (80B model download from HuggingFace)
- Inference: ~68s/image with FlashInfer fused MoE kernels (vs ~19 min with INT8 BnB dequantization)

**Amazon SageMaker IAM requirements:**
```
sagemaker:CreateModel, sagemaker:CreateEndpointConfig, sagemaker:CreateEndpoint
sagemaker:DeleteModel, sagemaker:DeleteEndpointConfig, sagemaker:DeleteEndpoint
sagemaker:DescribeEndpoint, sagemaker:InvokeEndpoint, sagemaker:InvokeEndpointAsync
iam:PassRole (to pass Amazon SageMaker execution role)
secretsmanager:CreateSecret, secretsmanager:UpdateSecret, secretsmanager:GetSecretValue, secretsmanager:DeleteSecret
```

**Role discovery** (fully automatic — no environment variable needed):
1. Running on EC2/ECS → auto-discovers the instance role, adds sagemaker.amazonaws.com trust if missing
2. Finds existing `ArtSmokerSageMakerRole` or `ArtSmokerEC2Role` in the account
3. Auto-creates `ArtSmokerSageMakerRole` with Amazon SageMaker + S3 permissions if none found

For EC2 deployments: add `AmazonSageMakerFullAccess` to the same `ArtSmokerEC2Role` used for Bedrock. ArtSmoker auto-discovers it. For local development: ArtSmoker auto-creates `ArtSmokerSageMakerRole` on first deploy (requires `iam:CreateRole` permission).

**S3 storage layout** (all under the same bucket configured in Video Settings):
```
s3://your-bucket/
├── artsmoker/video/{job_id}/         ← Video generation output (MP4, thumbnails)
├── artsmoker/custom-models/{key}/    ← Handler code (HF models) or weights + handler (non-HF)
│   └── code/inference.py             ← Universal inference handler (bundled)
├── artsmoker/custom-models/
│   ├── inference-input/{endpoint}/   ← Async inference input payloads
│   └── inference-output/{key}/       ← Async inference results
└── artsmoker/async-jobs/*.json       ← Persisted async job state (1-day S3 lifecycle expiry)
```

### 5.10.1 Image-to-3D: Two Pipelines, Texture Backends & Dependency Licensing

ArtSmoker offers **two image-to-3D pipelines**, each a separate Custom Models catalog entry under the **3D Generation** category. The user picks which to deploy (and, when more than one is live, which to use per generation) — both are offered with their own cost and licensing; it is the user's choice.

| Pipeline | Catalog key | How it works | Texture |
|----------|-------------|--------------|---------|
| **TripoSG + texture backend** | `triposg` | TripoSG generates untextured geometry; a chosen **texture backend** paints it | Selectable backend (below) |
| **TRELLIS.2 (Full)** | `trellis2_image_to_3d` | A single TRELLIS.2 model generates **both geometry and PBR texture** (SLAT), no separate texturing step | Integrated (MIT + DINOv3) |

Both take a single image and produce a GLB; the handler routes the job to whichever deployed instance the user selected (`library`/`predictor_type` = `image_to_3d` for TripoSG, `trellis2_image_to_3d` for the full pipeline). The full pipeline shares the runtime-built CUDA-ext stack (o_voxel/cumesh/flex_gemm/nvdiffrast) and the DINOv3/BiRefNet gated-repo handling with the texturer.

> **⚠️ nvdiffrast license (full TRELLIS.2 pipeline).** The mesh/PBR bake (`o_voxel.postprocess.to_glb`) **hard-imports `nvdiffrast`**, which is under the **NVIDIA Source Code License (1-Way Commercial) — non-commercial for general users**, *not* MIT. It is an internal dependency of upstream `o_voxel` and cannot be swapped without patching microsoft/TRELLIS.2, so the full image-to-3D pipeline currently carries a non-commercial rasterizer dependency — surfaced in the deploy dialog (`license_agreement.dependencies` + `warnings`). **Review before commercial use.** The separate **TripoSG + texture-backend** path is unaffected: its bake defaults to **Kaolin (Apache-2.0)** via `ARTSMOKER_RASTERIZER`.

**Full-pipeline resourcing (measured).** The standalone TRELLIS.2 pipeline's baseline is **`ml.g6e.xlarge`** (`recommended_instance`; `allowed_instances` also offers 2xlarge/4xlarge as RAM-headroom upsells). A live run measured peak **~6.5 GB VRAM** (of the L40S's 48 GB — hugely over-provisioned) and **~22 GB host RAM** during the `to_glb` UV-unwrap/bake. Host RAM, not VRAM, is the real constraint: xlarge's 32 GiB holds it with ~9 GB headroom, so `min_ram_gb: 28` is enforced and the handler logs a per-run `TRELLIS.2 RESOURCE PEAK` line (VRAM alloc/reserved + host RAM avail/total) to keep the baseline observable. SageMaker async-inference rates: g6e.xlarge **$2.61/hr**, 2xlarge **$2.80/hr**, 4xlarge **$3.76/hr** (all carry the same single L40S, so the per-hour gap is small).

**Texture backends (TripoSG pipeline only).** The backend is chosen **per-deployment** (baked into the endpoint as `ARTSMOKER_TEXTURE_BACKEND`) from the catalog's `texture_backends.options`. Two are offered, each with a distinct license profile that is **disclosed in the deploy dialog and must be explicitly accepted** (`attestation_required`) before deployment proceeds.

| Backend | License | Commercial | Key model dependencies | Gated repos |
|---------|---------|------------|------------------------|-------------|
| **TRELLIS.2** (default for new deploys) | MIT | ✅ Yes (with attribution) | `microsoft/TRELLIS.2-4B` (MIT), `facebook/dinov3-vitl16-pretrain-lvd1689m` (commercial-OK, **"Built with DINOv3" attribution required**), `ZhengPeng7/BiRefNet` (MIT, the actual background cutout) | `facebook/dinov3-…` |
| **Hunyuan3D-Paint** | Tencent Hunyuan 3D 2.0 Community | ❌ Non-commercial | `tencent/Hunyuan3D-2.1` (Tencent, non-commercial), `facebook/dinov2-giant` (**CC-BY-NC-4.0, also non-commercial**), RealESRGAN x4 (MIT) | `tencent/Hunyuan3D-2.1` |

**Licensing is surfaced, not buried.** Each `texture_backends.options.<key>.license` block carries `name`, `url`, `commercial`, `attestation_required`, `key_terms[]`, `warnings[]`, and a structured `dependencies[]` array (each: `name`, `license`, `url`, `gated`, `commercial`, `role`). The deploy dialog (`ModelSettings.js`) renders the `dependencies[]` as a per-model table with commercial/gated badges and HuggingFace links, so the operator sees **exactly which models are pulled and under what terms** before agreeing. Gated repos additionally require accepting that model's license on HuggingFace (the stored HF token must belong to an account that has done so).

**Gated-repo access pre-check (deploy dialog).** Rather than a vague "gated · accept on HF" badge, the deploy dialog calls `GET /api/custom-models/gated-access/{key}` (see §5.10), which probes **every** repo the deploy will pull (model source + dependencies) with the stored token via `huggingface_hub.auth_check`. It renders a per-repo ✓/✗ with the exact next step (accept this specific gate on HF, or add a token) and **blocks deploy** while a required repo is inaccessible — so a missing gate acceptance fails fast in the dialog instead of 10 minutes into a cold start. In practice this pinpoints the one genuinely-gated repo (e.g. `facebook/dinov3-…`) even when the model is broadly flagged `requires_hf_auth` but its other repos are public.

**DINOv2 ≠ DINOv3** (a common confusion, called out explicitly): Hunyuan's image encoder is **DINOv2-giant (CC-BY-NC-4.0, non-commercial)**; TRELLIS.2's is **DINOv3 (commercial-OK, attribution required)**. They are different models with different licenses.

**Background-removal model (the cutout that actually runs).** ArtSmoker pre-cuts the input to an RGBA image before texturing; this cutout is produced by a **selectable** background remover, defaulting to the commercially-clean MIT option:

| Env flag | Default | Options | Notes |
|----------|---------|---------|-------|
| `ARTSMOKER_BG_MODEL` | `birefnet` | `birefnet` (`ZhengPeng7/BiRefNet`, MIT) · `rmbg` (`briaai/RMBG-1.4`, CC-BY-NC / non-commercial) | The handler's preprocessing cutout for all texture backends. |
| `ARTSMOKER_TRELLIS2_REMBG` | `birefnet` | `birefnet` (MIT) · `rmbg` (bundled `briaai/RMBG-2.0`, non-commercial, gated) | TRELLIS.2 ships a config that points its *internal* rembg at the gated Bria RMBG-2.0. Since we always feed a pre-cut RGBA image, TRELLIS.2's rembg **never executes** — but `from_pretrained` would still *download* it. By default the handler monkeypatches TRELLIS.2's BiRefNet wrapper to the MIT repo so the gated Bria model is never pulled, keeping TRELLIS.2 fully MIT. Set to `rmbg` to opt back into the bundled Bria model (requires accepting its license on HuggingFace). |

Because BiRefNet (MIT) does the real cutout at equal/better quality, **RMBG is not required** for any backend; it remains available as a disclosed opt-in. Both flags default to the commercial-clean MIT path.

**Pipeline selection & license consent at generate time (AssetViewer 3D tab).** `GET /api/generate/3d/instances` returns every deployed image-to-3D instance (both pipelines) enriched with `pipeline_type` (`triposg` | `trellis2_full`), the active license summary (`license_name`, `license_url`, `commercial`), the **deploy-time acceptance on record** (`license_accepted`, `license_accepted_at`), and `est_cost_usd` (= instance hourly rate × typical latency). The AssetViewer shows a **pipeline chooser only when more than one generator is deployed** (with exactly one, it's auto-selected); each option displays its est. cost + time and a license panel. Consent is **not re-prompted** at generate time — the binding attestation happens at deploy (see below); the panel instead states *"License accepted at deploy on `<date>`"* (or warns if no acceptance is on record). The chosen pipeline + the accepted license are persisted into the asset's metadata (`three_d_versions[].pipeline`: `pipeline_type`, `license_name`, `commercial`, `license_accepted_at`) for full provenance, shown back in the 3D tab's "Models & Tools Used".

**Deploy-time acceptance (authoritative).** The Custom Models deploy dialog is where the user reads and accepts. For TripoSG it's the texture-backend `attestation_required` checkbox + dependency table; for the full TRELLIS.2 pipeline it's the model's `license_agreement` modal — which now also renders the structured `dependencies[]` table (same per-model name/license/commercial/gated/role breakdown). Acceptances are recorded in the user registry (`license_acceptances`, keyed by model/backend with a timestamp); the generate-time UI reads this to show the "accepted on `<date>`" status.

> **GLB texture format note.** Generated GLBs encode their PBR atlas as **WebP** (`EXT_texture_webp`) to keep files compact (and within the SageMaker async response limit). This renders correctly in the in-app viewer (`model-viewer`), Blender 4.x, three.js, and modern Unity/Unreal glTF importers. macOS Preview/QuickLook converts GLB→USDZ and does **not** support WebP textures, so it renders the model black — a viewer limitation, not an asset defect. We intentionally keep WebP rather than degrade to PNG.
>
> **Timestamps** are written timezone-aware (`datetime.now(timezone.utc)` → `…+00:00`) so the frontend renders local time correctly. (A prior naive `utcnow().isoformat()` had no zone suffix and displayed the wrong time.)

### 5.10.2 Source Completion (Character/Asset → 3D)

Image-to-3D can only build geometry for what is **visible** in the source image: a character cropped at the waist yields a legless mesh. Rather than force the user to frame the image precisely, ArtSmoker detects an incomplete source on 3D submit and **offers** to complete it via outpainting — turning a framing problem into an opt-in quality step.

**Flow (AssetViewer 3D tab, `character` / `game_asset` only):**
1. **Analyze** — `POST /api/generate/3d/analyze-source` sends the current 2D version's PNG to a vision LLM (the editable `three_d_source_analysis` steering template). It returns strict JSON: `{complete, subject, crop_edges[], missing[], suggest_outpaint{down/up/left/right px}, outpaint_prompt, reason}`. **Conservative by design** — defaults to `complete:true` on any uncertainty or parse/transport error, so a well-framed image is never blocked.
2. **Offer** — if incomplete, a non-blocking dialog explains what's cropped and offers **Complete it first** / **Generate as-is** (clear secondary) / cancel. The dialog shows the LLM-**suggested completion prompt** in an **editable** field (e.g. *"the soldier's legs and combat boots, matching the armor"*); the user can edit or clear it (blank = the outpaint model just continues the subject).
3. **Outpaint** — reuses the existing `POST /api/generate/edit` outpaint route (`model=stable_outpaint_v1`, directions from the analysis, the user's prompt), which creates a **new 2D version**. Provenance is recorded in that version's record under `edit_context` (trigger `3d_source_completion`, source version, directions, prompt) via a reserved `extra_params._meta` key that is stripped before the model call.
4. **Preview & re-review** — after each outpaint, a **before→after preview popup** (layered above the 3D dialog) shows the source vs the result plus a **fresh re-review verdict** (re-runs `analyze-source` on the new version — the outpaint amount was an LLM *estimate*, not a measurement, so quality is verified before proceeding). The user picks: **Use this for 3D** (primary when the re-review passes), **Extend again** (primary when still cropped — re-outpaint with tweakable directions + editable prompt; **unlimited rounds**, each a new version + re-review + re-preview), or **Discard & keep original** (**soft discard** — reverts the 3D source to the pre-outpaint version; the outpainted version remains in history).
5. **Generate** — the 3D job is submitted against whichever version the user accepted.

The whole pre-check is skipped on retry and is purely a pre-submit gate — the happy path for a complete image is unchanged.

**Sidecar preparation (`POST /api/generate/3d/prepare-source`)** — prepares a version's 3D source **in place** via sidecar files (`asset_v{N}__cutout.png`, `asset_v{N}__source.png`), never creating 2D versions. Ops: `cutout` (ensure the background-removed cutout exists — idempotent cache), `extend` (outpaint the cutout, re-strip, save as the prepared source), `inpaint` (mask-based fill on the prepared source), `reset`. The request's `bg_method` selects the background-removal method for the cutout/re-strip: `local` (default — free rembg; the 3D mesher only needs the background gone, not a feathered edge) or `bedrock` (paid). The 3D panel offers this as a dropdown. For `extend`, an optional `edit_model` may name an instruction editor (`model_purpose: image_edit`, e.g. Qwen-Image-Edit) — the extend then runs the same pre-pad + complete-the-band + blend-back recipe as the Edit tab, synchronously (`invoke_instruction_edit_sync` waits on the async endpoint and cleans up its S3 artifacts); the default remains the first enabled Bedrock outpainting model.

### 5.11 Async Jobs (Self-Hosted Model Generation)

Non-blocking generation for self-hosted models on Amazon SageMaker async endpoints. When a user generates with a custom model, the request is submitted to S3 and returns immediately — the UI tracks progress without blocking.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/generate/async-jobs` | List all active and recent async jobs. Returns job ID, model key, status (pending/complete/failed), submission time, prompt, and full generation metadata. |
| POST | `/api/generate/async-jobs/clear` | Clear completed/failed jobs from the tracking list. Active jobs are preserved. |

**S3 persistence:** Jobs are persisted to `artsmoker/async-jobs/` in the S3 bucket. Job state survives server restarts — on startup, the system reloads active jobs from S3 and resumes polling. An S3 lifecycle rule (1-day expiry) is set lazily on first persist to auto-cleanup stale job files.

**Background poller:** A background thread checks S3 every 10 seconds (while jobs are active) for completed inference outputs. When output appears, it downloads the result, decodes the image, and writes it to the local gallery. Frontend polls at 5-second intervals for fast UI updates.

**Gallery integration:** Full metadata (prompt, model, style snapshot, options/variations structure) is saved at submission time. The gallery entry is created immediately with a `pending` status. On completion, the PNG and SVG are written in-place and status flips to `complete`. On failure, status flips to `failed` with an error message.

**Invocation timeout:** `InvocationTimeoutSeconds` is set per-request as `min(3600, max(900, typical_latency_seconds × 2))` from the catalog. The 3600-second cap is a SageMaker hard limit for async invocations. Models with `typical_latency_seconds > 300` get an extended timeout; others use SageMaker's default.

**Cost tracking:** Compute cost is calculated as `(duration_seconds / 3600) × hourly_rate`, where `hourly_rate` comes from the instance type pricing in the catalog. Duration is capped at the model's invocation timeout. This cost is added to the request's cost accumulator alongside any LLM prompt-enhancement costs.

**Frontend (Pending Jobs button):** A button in Image Studio shows the count of active async jobs. Clicking opens a panel listing each job with model name, prompt excerpt, elapsed time, and status. The dialog shows a cleanup info header explaining 24-hour auto-cleanup of stale jobs. Smart polling: the frontend polls `/api/generate/async-jobs` only when at least one job is active — stops polling when all jobs resolve. On completion, the gallery thumbnail live-replaces the pending placeholder.

**Job resubmission:** SageMaker async endpoints silently drop queued jobs when instances scale to zero. The poller detects stale jobs (pending >15 min with no S3 output and endpoint at 0 instances) and resubmits them using the original S3 input file. The resubmission call itself triggers the `HasBacklogWithoutCapacity` CloudWatch alarm, forcing scale-from-zero. Max 3 resubmission attempts per job with 60-second cooldown between attempts. `endpoint_name` is stored per job and resolved via registry on resubmission (handles endpoint redeployment). All resubmission state persists to S3 (survives server restart). **Capacity-aware:** when the endpoint's `DesiredInstanceCount` > `CurrentInstanceCount` (scale-out requested but blocked — e.g. `InsufficientInstanceCapacity`), the job is treated as *progressing* and retries are NOT consumed — resubmitting cannot help until an instance actually lands.

**Fast failure detection (`S3FailurePath`):** async endpoint configs set an `S3FailurePath` (`…/inference-failures/{model_key}/`); SageMaker writes the model's error body there when an inference fails, and the invoke response's `FailureLocation` is stored per job. The poller checks the failure artifact (plus the legacy `{output}.failure` convention) before the success output — a crashing job **fails in seconds with the model's real error** instead of sitting "generating" until the 15-minute stale timeout.

**Per-asset write locks (`asset_locks.py`):** the sync `/edit` versioned save and the async edit completion both read-modify-write the same asset's `metadata.json`. Both writers serialize on a shared per-asset `threading.Lock`, so simultaneous completions can never compute the same version number and clobber each other's records.

**Edit breadcrumbs:** every `/api/generate/edit` request logs a lifecycle trail under one short trace ID — `EDIT-START` (model, purpose, source, version, mask?) → `EDIT-DONE` (new version + cost) or `EDIT-FAIL` (error) or `EDIT-ASYNC` (handed to job N) — so "did my edit run, and what happened?" is a single grep.

**Cross-region endpoints:** a deployment may carry an explicit `deployment.region` (and optional `deployment.s3_bucket`) in the registry — set automatically by the deployer on every new deploy. The invoker (realtime + async submit + async input upload) and the job poller resolve their AWS clients per-endpoint from these fields, falling back to the home region (`aws_region_models`) when absent. Async jobs carry their `region`, so polling, downloads, and resubmission all hit the correct regional S3/SageMaker even when an endpoint lives outside the home region (e.g. deployed to us-east-2 during a us-west-2 capacity drought).

**Readiness detection:** Two-pass CloudWatch log scan: (1) `filter_log_events` with "loaded in" pattern scans entire log history server-side (catches model load even after hours of pings), (2) `get_log_events` tail for progress/error detection. Readiness is persisted to the registry (`deployment.model_ready=True`) so it survives server restarts without re-scanning logs.

### 5.12 Admin (Model Management)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/models` | Get the full model registry (categories, image models, video models, post-processing, format families). |
| GET | `/api/admin/models/image-options` | Enabled text-to-image models for the Image Studio dropdown. Returns per-model metadata including region_pricing and quality_options. |
| GET | `/api/admin/models/video-options` | Enabled video models for the Video Studio dropdown. Returns per-model metadata including parameters, task_types, and pricing. |
| GET | `/api/admin/regions` | Cached list of Bedrock-supported AWS regions from the registry. |
| GET | `/api/admin/video/settings` | Current video storage settings (S3 bucket, prefix, storage mode). |
| PUT | `/api/admin/video/settings` | Update video settings. Validates S3 bucket access (head_bucket + put/delete test) before saving. |
| PATCH | `/api/admin/models/category/{name}` | Update an LLM category (e.g. `fast_llm`, `complex_llm`). A manual `current` change sets `pinned: true`, opting the category out of the Sync auto-roll. |
| PATCH | `/api/admin/models/image/{key}` | Update an image model. |
| PATCH | `/api/admin/models/video/{key}` | Update a video model (enable/disable, region, prompt limit). |
| POST | `/api/admin/models/image` | Add a new image model to the registry. |
| PUT | `/api/admin/models` | Replace the entire model registry JSON. Validates required top-level keys. Used by the raw JSON editor. |
| PATCH | `/api/admin/models/postprocess/{key}` | Update a post-processing model (model_id, region, enabled). |
| POST | `/api/admin/models/reload` | Reload the model registry from disk (e.g. after external edit). |
| POST | `/api/admin/discover/refresh-all` | Full registry refresh: discovers regions, fetches pricing, scans all regions for foundation + custom + imported models, backfills Bedrock metadata (input/output modalities, lifecycle, ARN, streaming, customizations), and auto-rolls `fast_llm`/`complex_llm` to the newest Sonnet/Opus (respecting pinned categories). Live progress is available via the `/api/sync-progress` SSE stream. |
| POST | `/api/admin/discover/{region}/auto-register` | Scan a single region for foundation image + video models. Classifies by output modality (IMAGE → image registry, VIDEO → video registry). Custom/imported models are discovered separately during refresh-all. |
| GET | `/api/admin/discover/{region}` | Raw model listing: image generators, video generators, text/LLM, vision models. |
| GET | `/api/admin/templates` | Get all 28 prompt templates with metadata (description, variables, modified flag, group). |
| PATCH | `/api/admin/templates/{key}` | Update a template's content. Validates required variables are present — returns missing vars if not. |
| POST | `/api/admin/templates/{key}/reset` | Reset a template to its default content. |
| POST | `/api/admin/templates/reset-all` | Reset all templates to their defaults. |
| POST | `/api/admin/templates/{key}/enhance` | Enhance a template using an LLM. Accepts model_id, region, optional instructions. Returns suggested improved content for review. |

### 5.13 System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check — returns `{status, version, aws: {credentials, identity, bedrock_models, bedrock_images, errors}}`. |
| GET | `/api/sync-progress` | SSE stream of live AWS-Sync progress (per-region log lines + running model counts, final `done` event). Powers the first-run "Setting Up" modal and the Custom Models "Sync with AWS" overlay. |
| GET | `/api/update-status` | Check for available updates. Returns `{update_available, local_version, remote_version, dev_mode}`. Used by frontend monitor. |
| POST | `/api/ping` | Frontend telemetry ping. Accepts `{event, properties}` and forwards to PulseBoard if telemetry is enabled. |
| POST | `/api/log` | Receive client-side log entries. Body: `{ "level": "error", "message": "...", "context": {} }`. Logged server-side with `[CLIENT]` prefix. |
| GET | `/docs` | Swagger UI (auto-generated by FastAPI). |

## 6. LLM Directive Prompts (Prompt Templates)

ArtSmoker uses 28 directive prompts to guide LLM behavior across different features. All prompts are stored in `backend/prompt_templates.json` and are fully editable via the Model Settings UI (Prompt Templates tab) or the raw JSON editor.

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

### 7.4a Image-Editing Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `edit_prompt_suggestion` | `generate.py` | Edit Prompt Suggestion (per-mode, model-aware) — reads the image + its original generation prompt and suggests an edit instruction for the active edit mode. Produces a descriptive caption for Stability edit models or an imperative instruction for a Qwen-Image-Edit instruction editor. Used by the AssetViewer Edit-tab "Generate Prompt" button (endpoint `generate.suggest_edit_prompt`). | `{original_prompt}`, `{mode}`, `{model_label}` + image | Sonnet (vision) |

### 7.5 Video Generation Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `video_enhance_prompt` | `video.py` | Enhance a user prompt with camera movements, lighting, temporal cues, and avoidance language (since video models have no negative prompt). | `{prompt}`, `{prompt_limit}`, `{model_guidance}`, `{optimal_length}` | Sonnet |

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
| `translate_detect_language` | `prompt_translator.py` | Detect language when Unicode heuristics are ambiguous (e.g. French vs Spanish). Returns 2-letter code. | `{text}` | Sonnet |
| `translate_to_english` | `prompt_translator.py` | Translate non-English text to English, preserving meaning and technical terms. | `{text}`, `{lang_name}` | Sonnet |

### 7.9 Prompt Designer Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `prompt_decompose` | `refine.py` | Decompose a user prompt into structured visual components (subject, scene, composition, lighting, style with color palette). | `{user_prompt}`, `{style_section}`, `{asset_context}` | Sonnet |
| `prompt_recompose` | `refine.py` | Reassemble decomposed structured components into a flat recomposed prompt. Model-specific guidance is applied later during enhancement, not here. | `{structured_json}`, `{model_name}`, `{max_chars}` | Sonnet |
| `asset_type_classify` | `refine.py` | Classify a prompt into the best asset type. Distinguishes character-focused vs scene-focused prompts even when both mention people. | `{user_prompt}` | Sonnet |

### 7.10 Admin Templates

| Template | File | Purpose | Variables | Model Used |
|----------|------|---------|-----------|------------|
| `admin_template_enhance` | `admin.py` | Improve a prompt template via AI. | `{template_label}`, `{template_description}`, `{template_used_by}`, `{variable_list}`, `{user_instructions}`, `{current_text}` | User-selected |
| `admin_template_fix_variables` | `admin.py` | Auto-insert missing variables into a user-edited template. | `{missing_variables}`, `{template_text}` | Sonnet |

### 7.11 Editing Templates

Users can edit any template via **Model Settings → Prompt Templates** tab.

**Two-level navigation:**
1. **"View All / Hide All"** toggles group sections (2D Image Studio, Style Library, Content Safety, Video Studio, Type Studio, Chat Studio, Translation)
2. **"Expand editors / Collapse editors"** inside each group toggles the individual template text boxes

Each template shows:
- Friendly description of what it controls (e.g., "Creative Options — how multiple distinct concepts are generated from one idea") plus a **"used by"** note of which feature consumes it
- Available `{variables}` that must be preserved
- Editable **prompt body** and, where the template has one, an editable **system prompt** (the steering channel sent separately from the user message) — both persisted per-template in `prompt_templates.user.json`
- **Save** — validates variables, blocks save if any are missing (offers "Fix & Save" to auto-insert)
- **Enhance with AI** — select any LLM model to improve the template
- **Reset to Default** — restore the original

A **"Reset All"** action (`POST /api/admin/templates/reset-all`) restores every template to its code default at once. Templates are organized into groups covering all studios plus Content Safety, Translation, Prompt Designer, Reference/Editing, and Admin, with an "Other" catch-all so a newly added template always appears.

### 6.10 AI-Assisted Template Refinement

Users can ask an LLM to improve any template:

1. Select a refinement model from the dropdown (all chat-capable models available)
2. Optionally type specific instructions (e.g., "optimize for pixel art", "make moderation less strict")
3. Click "Enhance with AI" — the LLM receives the current template + its metadata + instructions
4. A purple suggestion panel shows the improved version
5. If the AI's suggestion is missing required `{variables}`, a warning is displayed
6. Click "Accept" to copy into the editor (then "Save" to persist), or "Dismiss" to discard

**API**: `POST /api/admin/templates/{name}/enhance` with `{model_id, region, instructions}`.

### 6.11 Variable Validation & Auto-Fix

Templates use `{curly_brace}` variables that are substituted at runtime (e.g., `{user_prompt}` becomes the user's actual text). Removing a variable breaks the feature that uses the template.

**Validation on save** (`PATCH /api/admin/templates/{name}`):
1. Backend checks all required `{variables}` are present in the edited text
2. If variables are missing, returns HTTP 400 with the list of missing variables
3. Frontend shows a dialog explaining which variables are missing and why they matter
4. User clicks **"Fix & Save"** — sends `{fix_variables: true}` to the API
5. Backend calls the fast LLM (Claude Sonnet) to intelligently insert the missing variables in the right positions within the user's edited text
6. Backend validates the LLM's fix actually restored all variables
7. If fix succeeds → saves. If fix fails → returns error with manual instructions.

**Self-healing**: If `prompt_templates.json` is deleted, corrupted, or has missing templates, the service regenerates from code defaults on next load. User edits for existing templates are preserved; missing templates are added from defaults.

**Storage**: `backend/prompt_templates.json` is the runtime source of truth. The `_DEFAULTS` dict in `backend/services/prompt_templates.py` is a backfill seed only — it fills in templates missing from the JSON on load but never overwrites existing entries. User edits are stored in `prompt_templates.user.json` and marked with `"modified": true`.

> [!WARNING]
> Editing directive prompts changes how the AI behaves across the entire application. Test changes carefully. The variable validation prevents accidental breakage, but semantic changes to the instructions can still affect output quality.

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
| `bedrock:CreateInference` *(or `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** inference — required for models reachable ONLY via the `bedrock-mantle` endpoint (OpenAI GPT-5.x, Claude Mythos, GLM/Grok/Qwen/Gemma, etc.). Without it those models fail with a clear "Mantle access denied" message; Converse-served models (Claude tiers) are unaffected. See §4.8. |
| `account:ListRegions` | List the account's **enabled** regions so Sync scans only those (skips opt-in/disabled regions instead of erroring on them). Optional — without it, Sync falls back to scanning all Bedrock regions (slower, with skips logged). |
| `account:GetRegionOptStatus` | Read per-region opt-in status (companion to `account:ListRegions`). Optional. |
| `s3:CreateBucket` | Create S3 bucket for video storage (optional, via UI) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | Video output storage and retrieval |
| `aws-marketplace:Subscribe` | Auto-subscription on first use of third-party models (incl. Mantle-hosted third-party models) |
| `aws-marketplace:ViewSubscriptions` | Check existing model subscriptions |
| `sts:GetCallerIdentity` | Startup credential validation; also underpins the locally-signed Mantle bearer token |
| `pricing:GetProducts` | Fetch model pricing during Sync from AWS (optional) |

> **Amazon Bedrock Mantle (frontier models):** The `bedrock-mantle` endpoint authenticates with a short-term **bearer token** that ArtSmoker derives locally from these same credentials (nothing stored) — so no extra *token* setup is needed, but the identity must hold **Mantle inference permission**. The simplest grant is the AWS managed policy **`AmazonBedrockMantleInferenceAccess`** (read + `CreateInference` + bearer-token calls) or **`AmazonBedrockMantleFullAccess`**. Third-party Mantle models additionally rely on the `aws-marketplace:*` permissions above. If this is missing, only Mantle-only models are affected — everything on the Converse endpoint keeps working.

**Quickest setup**: Attach **`AmazonBedrockFullAccess`** (covers all `bedrock:*` including `CreateInference`) **plus** **`AmazonBedrockMantleInferenceAccess`** for the Mantle endpoint. You may additionally need `aws-marketplace:Subscribe` / `aws-marketplace:ViewSubscriptions` for first-time third-party model access, and `account:ListRegions` for the fast region-filtered Sync.

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
        "bedrock:ListCustomModelDeployments",
        "bedrock:CreateInference"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Sid": "AmazonBedrockMantleInference",
      "Action": [
        "bedrock:GetInferenceProfile",
        "bedrock:CreateInference",
        "bedrock:GetInference",
        "bedrock:ListInferences"
      ],
      "Resource": "*",
      "Comment": "Or simply attach the managed policy AmazonBedrockMantleInferenceAccess"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aws-marketplace:Subscribe",
        "aws-marketplace:ViewSubscriptions"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["account:ListRegions", "account:GetRegionOptStatus"],
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
> Note: `Comment` is illustrative only — strip it before applying (IAM rejects unknown keys). The dedicated Mantle statement mirrors the managed policy `AmazonBedrockMantleInferenceAccess`; attaching that managed policy instead is simpler and AWS keeps it current.
>
> This is the **core** policy (Bedrock + Mantle + S3 + discovery). **Self-hosted Custom Models on Amazon SageMaker** need an additional set of permissions (`sagemaker:*` for endpoints, `iam:PassRole`/`CreateRole`/`AttachRolePolicy`, `secretsmanager:*` for the gated-model HF token) — see the **Amazon SageMaker IAM requirements** under §5.10. Skip those if you won't deploy Custom Models.

**Apply the policy via CLI:**

```bash
# Option A: Quickest — attach managed policies to your IAM user
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
# Mantle endpoint (frontier models — OpenAI GPT-5.x, Claude Mythos, GLM, etc.)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess
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

On launch, ArtSmoker runs a lightweight **sanity check** (`validate_aws_credentials()` in `bedrock_client.py`) — not an exhaustive audit. It confirms the configured IAM role can actually reach Amazon Bedrock by probing a **representative sample** of the models the app may use, all read from the registry (no hardcoded model IDs):
1. AWS credentials resolve (`sts:GetCallerIdentity`).
2. **Fast LLM** (`categories.fast_llm`) — a 1-token `Converse` call.
3. **Complex LLM** (`categories.complex_llm`) — a 1-token `Converse` call. Probing both tiers matters because they are usually different models with different access (and the complex tier is often a newer model that deprecates inference params — see below).
4. **Image model** — a lightweight `InvokeModel` against the first enabled image model in the registry; a `ValidationException` still counts as success (the model was reached, only the dummy body was rejected).

Each LLM probe builds its `inferenceConfig` through the same registry-driven gate used at runtime (`_build_inference_config` → `_model_supports_temperature`), so a model that deprecates `temperature` (e.g. Claude Opus 4.8) does **not** fail the probe. `_model_supports_temperature` reads `supports_temperature` / `deprecated_params` off the model's `chat_models` entry; only when the registry is silent does it fall back to a minimal built-in heuristic. Each probe also honors the model's **resolved invoke path** (§4.8): a Converse-routed model is probed with a 1-token `Converse` call on `bedrock-runtime`; a Mantle-only model (e.g. a `fast_llm`/`complex_llm` pointed at GPT-5.x) is probed with a 1-token call on its `bedrock-mantle` API — so the sanity check exercises exactly the path the app will use.

The result records a `probes` list (`role`, `model_id`, `region`, `ok`). On success the console logs a concise multi-line message — *"Amazon Bedrock access verified — the IAM role can reach a representative sample of N model(s)…"* — followed by one `✓ <role> — <model_id> (<region>)` line per probe (kept short so it never overflows a typical console width). Results are also available at `GET /api/health`. If credentials are missing, a prominent error box explains what to configure. If some checks fail but credentials exist, a warning lists the failures — the app still starts (some features may be degraded).

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
   - On startup: create data directories (`data/`, `data/styles/`, `data/generated/`, `data/video/`, `data/chat/`) via `mkdir(parents=True, exist_ok=True)`.
   - On startup: call `validate_aws_credentials()` from `bedrock_client.py` — stores result in a module-level `_aws_status` dict.
   - On startup: initialize PulseBoard telemetry (`telemetry_init()`, `track_server_start()`) — fire-and-forget.
   - Log a prominent error box if credentials are missing, a warning if some Bedrock checks fail, or an info message if all checks pass.
3. **Colored console logging** — custom `_ColorFormatter` using ANSI 256-color codes. Each log level gets a distinct color (cyan for INFO, yellow for WARNING, red for ERROR). Timestamps are included. The formatter overrides uvicorn's default logger for consistent output.
4. **NoCacheStaticMiddleware** — custom `BaseHTTPMiddleware` that adds `Cache-Control: no-cache, no-store, must-revalidate` and `Pragma: no-cache` headers to all responses where the request path does NOT start with `/api/`. This ensures frontend static files are never cached during development.
5. **CORS middleware** — `CORSMiddleware` with `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`. Development-mode open CORS.
6. **Include all routers**: styles, generate, refine, transcribe, gallery, browse, typestudio, video, chat, admin — in that order.
7. **Health check endpoint** (`GET /api/health`) — defined inline on `app`, returns `{status: "ok"|"degraded", aws: {credentials, identity, bedrock_models, bedrock_images, errors}}`.
8. **Client log endpoint** (`POST /api/log`) — defined inline on `app`, receives `{level, message, context}`, logs as `[CLIENT] {message} | {context}` at the appropriate Python log level.
   - **Sync progress stream** (`GET /api/sync-progress`) — an SSE stream of live AWS-Sync progress, used by both the first-run "Setting Up" modal and the Custom Models "Sync with AWS" overlay. It tails `_server_state["sync_log"]`, emitting a `data:` event per new log line (with running model counts) and a final `done` event. Because the manual Sync button opens the stream a beat *before* its `refresh-all` POST flips `sync_in_progress` on, the generator first waits up to ~10s for the sync to start before concluding nothing is running — without this grace period the overlay would close immediately and show no live updates.
9. **Static files mount** — `app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True))` mounted LAST so `/api/*` routes take priority. `FRONTEND_DIR` is `Path(__file__).resolve().parent.parent / "frontend"`. The `html=True` flag enables serving `index.html` for directory requests.

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
huggingface_hub>=0.23          # Custom-model weight downloads from HuggingFace
openai>=1.50                   # Amazon Bedrock Mantle endpoint (OpenAI-compatible Chat Completions + Responses)
aws-bedrock-token-generator>=1.0  # Short-term Bedrock bearer token for Mantle (derived from AWS creds)
requests>=2.31                 # Anthropic Messages API over the Mantle endpoint
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
- `showConfirm({ title, message, confirmText, cancelText, variant })` — styled confirmation dialog replacing all browser `confirm()` calls. Returns a Promise resolving to `true`/`false`. Variant options: `danger` (red confirm button), `warning` (amber), default (indigo). Used for destructive actions: Sync from AWS, delete sessions, reset templates, etc.
- `showLoading(text)` / `hideLoading()` — fullscreen loading overlay with spinner.
- `resetView(route)` — destroys the DOM cache for a specific view, forcing fresh render on next visit.
- `t(key, params)` — global translation function (see [Section 15: i18n](#15-internationalization-i18n)).

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
10. **Test prompt enhancement**: Type a brief prompt, click "Preview Enhanced Prompt" — verify the enhanced prompt respects user intent over style defaults.
11. **Test marketing banner**: Set asset type to "Marketing Banner" and generate — verify the result is a scenic composition, not an isolated sprite.
12. **Test Type Studio**: Navigate to Type Studio, enter text lines, select fonts, request AI layout suggestions. Verify 1-5 layout options are returned. Select a layout and render — verify the result is saved to the gallery.
13. **Test Video Studio**: Navigate to Video Studio, configure S3 bucket in Video Settings, select a video model (Nova Reel or Luma Ray), enter a prompt, and generate. Verify the job appears in Active Jobs, polling updates the status, and on completion the video plays and thumbnail appears. Verify the video also appears in the Gallery with a VIDEO badge.
14. **Browse gallery**: Switch to Gallery view — verify generated images and videos appear with the Media filter (All / 2D Artwork / 3D Models / Video), style filter, and search. Test multi-select and bulk delete (both image and video assets).
15. **Test AssetViewer buttons**: Open an image asset — verify "2D Studio" and "Add Text" buttons appear. Open a type-studio asset — verify "Edit in Type Studio" button appears. Click a video card — verify the video player modal opens with metadata.
16. **Test style_snapshot**: Delete a style, then view an asset that was generated with it — verify the style name still displays from the snapshot.
17. **Test Model Settings**: Click "Model Settings" in any studio sidebar — verify it opens to the relevant tab. Tabs: Image Studio, Video Studio, Chat Studio, Type Studio, Shared Studio, Prompt Templates, Registry JSON. All sections should be collapsible with Show All / Hide All toggles. LLM categories and post-processing should show dropdown model pickers (not raw text fields). Try Sync from AWS — verify image, video, and chat models are discovered.
17. **Test content moderation**: Generate with a prompt that triggers moderation — verify the system tries alternative models first (emerald dialog) before suggesting a rewrite (amber dialog). Test the rewrite option in each dialog — verify the rewritten prompt appears in the enhanced prompt area (not the original textarea) with the amber disclaimer. Verify the original prompt is preserved. Enable "Prompt Pre-Check" and test with a borderline prompt — verify the indigo pre-check dialog appears with specific issues, model switch, and rewrite options.
18. **Test Chat Studio**: Navigate to Chat Studio, select a model and region, type a message. Verify streaming response with markdown rendering and code highlighting. Test: create/rename/delete sessions, vision (paste an image), context compaction (fill context then compact), export as Markdown, fork from a message, regenerate a response.
19. **Test i18n**: Click a language button (JA, ZH, KO, FR, ES, HI, RU, DE) in the nav bar. Language buttons show native script (日, 中, 한, हिं, РУ, DE) with bilingual tooltips. Verify all UI text switches to the selected language. Switch back to EN. Verify prompts in non-English languages show the bilingual preview (Original/English tabs) in Image Studio and Video Studio.
20. **Test prompt templates**: Open Model Settings → Prompt Templates. Verify two-level navigation: "View All" opens groups, "Expand editors" opens text boxes. Edit a template, remove a required variable — verify "Fix & Save" offers to auto-insert it. Test "Enhance with AI" and "Reset to Default".
21. **Test custom confirmation dialogs**: Click "Sync from AWS" — verify a styled modal appears (not a browser confirm popup). Same for delete operations.
22. **Verify API docs**: Visit `http://localhost:8000/docs` — verify all endpoints are documented (including `/api/admin/*`, `/api/chat/*`, `/api/video/*`).

<a id="13-aws-bedrock-pricing--cost-breakdown"></a>

<a id="14-aws-bedrock-pricing--cost-breakdown"></a>

<a id="14-amazon-bedrock-pricing--cost-breakdown"></a>

## 14. Amazon Bedrock Pricing & Cost Breakdown

> [!NOTE]
> **All in-app costs are estimates only.** Every cost ArtSmoker shows or reports (per-image/video/token, 3D compute, keep-warm, deployment, session/asset totals, and PulseBoard telemetry) is a **guidance estimate** computed from AWS published pricing × expected usage — **not a bill and not a guarantee** of actual charges. Actual cost depends on account pricing, region, discounts, taxes, data transfer, endpoint uptime (incl. idle/warm SageMaker instances), and auto-scaling. **Users are solely responsible for monitoring their own AWS spend** (Billing Console, Cost Explorer, Budgets/alarms). See the README [Disclaimer](README.md#disclaimer).
>
> The tables below are **reference pricing for deployment planning**. The application shows **live pricing** in the UI, all fetched from the AWS Pricing API during registry refresh-all and stored in `model_registry.json`:
> - **Image/video per-unit** — `_fetch_image_pricing` → `image_pricing` (per model|region|quality|size).
> - **SageMaker instance hourly rates** — `_fetch_sagemaker_pricing` (`ServiceCode=AmazonSageMaker`, `component=Hosting`) → `sagemaker_pricing` (per instance|region); resolved by `custom_models.get_instance_hourly_rate(instance, catalog_key, region)` (synced per-region → any synced region → catalog seed), driving all compute-cost math (3D, async 2D, keep-warm).
> - **LLM per-token** — `_fetch_llm_pricing` (Bedrock `1K/1M tokens` rows, split input/output by usagetype) → `_apply_llm_pricing` stamps `input_price_per_1k`/`output_price_per_1k` onto each matched `chat_models` entry (per-model, Option A). `cost_tracker.compute_llm_cost` reads these registry prices FIRST (via `_registry_llm_price`), falling back to a small static seed then a Sonnet-priced default only when a model isn't matched.
>
> Model prices' `base_price_usd` / per-region `quality_prices` are displayed in the Image/Video Studio selectors and estimates. Pricing is cached in the registry and only updated when an admin runs refresh-all.

Model lineups and prices change frequently (deprecations, launches, revisions), so **any dollar figure written into this doc is an illustrative snapshot, not authoritative**. The application is the source of truth: it reads live, per-region pricing from the AWS Pricing API into `model_registry.json` (per-model `base_price_usd` / `quality_prices`) on each Sync and displays the cost for your actual configured region. Confirm current pricing in-app or on the official [Amazon Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/). The app's default regions are `us-west-2` (Claude, Stability AI) and `us-east-1` (Nova Sonic, Nova Reel).

### 14.1 Per-Unit Pricing

What incurs cost and its billing unit — the current per-unit price is fetched live and shown in-app (figures here are illustrative order-of-magnitude only):

| Service | Model | Billed by | Notes |
|---------|-------|-----------|-------|
| **LLM prompt engineering & chat** | Claude Sonnet / Opus (newest on Sync) | input & output tokens | Prices stamped per-model onto `chat_models` by `_apply_llm_pricing`; Opus ≫ Sonnet |
| **Bedrock image generation** | SD 3.5 Large, Stable Image Ultra, Stable Image Core | per image | Ultra ≫ SD 3.5 ≫ Core; per-model `base_price_usd`/`quality_prices` in registry |
| **Self-hosted image / 3D** | FLUX, HunyuanImage, Qwen-Image, TripoSG, TRELLIS.2 | SageMaker GPU-seconds | Not per-image; scale-to-zero = $0 idle. Rate via `get_instance_hourly_rate` |
| **Remove Background / Creative Upscale** | Stability AI services | per image | Creative Upscale is the most expensive post-processing step |
| **SVG Conversion** | vtracer / potrace / Pillow (local) | — | free, runs locally |

> [!NOTE]
> Prices from the official [Amazon Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/) as of March 2026. Prices may change — always verify against the official source.

> [!NOTE]
> **Vision token formula**: Claude charges image inputs as tokens: `tokens = (width × height) / 750`. A 1024×1024 image ≈ 1,398 tokens. At Opus $5.00/MTok input = ~$0.007 per image.

### 14.2 Additional LLM Costs (Per Use)

These Claude calls are part of the system's workflow but not included in the per-batch cost tables below:

| Call | Model | When triggered | Approx. Cost |
|------|-------|----------------|-------------|
| Prompt Pre-Check | Claude Sonnet | Before each generation (if toggle enabled) | ~$0.005 |
| Moderation Analysis + Rewrite | Claude Sonnet | Only when all image models reject a prompt | ~$0.005 |
| Type Studio Layout Suggestion | Claude Opus | Each AI layout request in Type Studio | ~$0.02–$0.05 |

Pre-check and moderation rewrite are a fraction of a cent each. Type Studio layout costs vary with the number of text lines and whether a base image is analyzed (vision input adds ~$0.007 per image).

### 14.3 Style Analysis Cost (One-Time per Style)

For a style with **100 reference images** (20 sent to Claude Opus after smart sampling, 8 sent to Claude Sonnet for cohesion check):

| Step | Model | Calculation | Cost |
|------|-------|-------------|------|
| Cohesion check (Phase 1) | Claude Sonnet (vision) | 8 images (game sprites, smaller than 1024×1024) + ~500 prompt tokens; ~500 output tokens | ~$0.01 |
| Analyze images (Phase 2) | Claude Opus (vision) | 20 images (game sprites) + ~500 prompt tokens; ~1,500 output tokens | ~$0.12 |
| Generate hints | Claude Sonnet | ~800 input + ~200 output tokens | ~$0.005 |
| **Total per style analysis** | | | **~$0.14** |

### 14.4 Generation Cost Scenarios

The generation cost depends on the image model chosen and the options×variations count. Prompt refinement cost is constant per batch.

**Base cost per batch** (prompt refinement/concept generation):

| Options | Prompt Step | Model | Approx. Cost |
|---------|-----------|-------|-------------|
| 1 option | Single prompt refinement | Claude Sonnet | ~$0.005 |
| 5 options | Concept generation (5 prompts) | Claude Opus | ~$0.05 |

**Image generation cost per batch** (the dominant cost):

| Scenario | Images | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|--------|-------------------|--------------|-------------------|
| 1 option × 1 variation | 1 | $0.04 | $0.08 | $0.14 |
| 1 option × 5 variations | 5 | $0.20 | $0.40 | $0.70 |
| 5 options × 1 variation | 5 | $0.20 | $0.40 | $0.70 |
| 5 options × 5 variations | 25 | $1.00 | $2.00 | $3.50 |

**Post-processing add-ons** (per image, optional):

| Add-on | Per Image | 1 image | 5 images | 25 images |
|--------|-----------|---------|----------|-----------|
| Remove Background | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convert to SVG | $0.00 | $0.00 | $0.00 | $0.00 |

### 14.5 Full Cost Examples

**Example 1: Quick single asset (cheapest)**
1 option × 1 variation, Stable Image Core, no post-processing:

| Step | Cost |
|------|------|
| Prompt refinement (Sonnet) | $0.005 |
| 1 image (Stable Image Core) | $0.04 |
| **Total** | **~$0.05** |

**Example 2: Standard workflow (5 variations to choose from)**
1 option × 5 variations, Stable Diffusion 3.5 Large, Remove BG on:

| Step | Cost |
|------|------|
| Prompt refinement (Sonnet) | $0.005 |
| 5 images (Stable Diffusion 3.5 Large) | $0.40 |
| 5× Remove Background | $0.35 |
| **Total** | **~$0.76** |

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
> **Key takeaway**: Image generation is cheap ($0.04–$0.14/image). **Creative Upscale is the big cost driver at $0.60/image** — use it selectively on your final chosen assets, not on the full batch. Remove Background at $0.07/image is reasonable. SVG conversion is free.

## 15. Internationalization (i18n)

ArtSmoker supports 9 languages: English (base), Japanese, Simplified Chinese, Korean, French, Spanish, Hindi, Russian, and German.

### 15.1 Architecture

```
frontend/js/i18n/
├── i18n.js          # Core: t() function, JSON loader, DOM updater, reverse lookup
├── en.json          # English (base) — 817+ keys, source of truth
├── ja.json          # Japanese — 817+ keys
├── zh.json          # Simplified Chinese — 817+ keys
├── ko.json          # Korean — 817+ keys
├── fr.json          # French — 817+ keys
├── es.json          # Spanish — 817+ keys
├── hi.json          # Hindi — 817+ keys
├── ru.json          # Russian — 817+ keys
└── de.json          # German — 817+ keys
```

**Key design decisions:**
- `t('key')` is a global function available in all JS — returns the translated string for the active language
- `t('key', {count: 5})` supports `{{variable}}` placeholder substitution
- Language files are flat JSON loaded on demand (not bundled)
- `I18n.updateDOM()` translates static HTML elements via `data-i18n` attributes
- `I18n.translateView(container)` post-renders component HTML using a reverse lookup (English text → key → translated text)
- Language selection persisted in `localStorage` (`artsmoker_lang` key)
- On language change: all cached views cleared and re-rendered in the new language
- CJK/Devanagari/Cyrillic font support: Noto Sans JP/SC/KR/Devanagari loaded via Google Fonts CDN

### 15.2 Prompt Translation Pipeline

Non-English prompts are auto-detected and translated to English before processing. The translation uses the fast LLM (Claude Sonnet) at ~$0.001 per call.

```
User types prompt (any language)
    ↓
detect_language(text, ui_lang) —
   • If the UI language is English, detection is SKIPPED entirely (no translation).
   • If a non-English UI language is selected, that language is checked/confirmed FIRST.
   • Otherwise: Unicode heuristic (CJK/Hangul/Devanagari/Cyrillic/Latin+accents+function words),
     with function-word matching done WORD-BOUNDARY aware (fixes English being mislabeled as German).
    ↓ (if ambiguous)
LLM fallback detection
    ↓
translate_to_english() via Claude Sonnet
    ↓
Returns: { original, translated, source_lang, was_translated }
```

**UI-language hint (`ui_lang`):** The frontend passes the user's selected UI language as a *soft prior* for detection. It only breaks genuine ties — unambiguous content signals (script, umlauts, matched function words) always take precedence, so a user who deliberately writes in a different language than their UI setting is still detected from the text itself. The hint is used in three places: (1) accented Latin text that matches no word list, (2) accent-free Latin text where the hinted language's own function words appear, and (3) as the fallback when the LLM detector returns an unsupported/empty code — replacing a coin-flip or a blind `en` default. `source_lang`, by contrast, is an authoritative override that skips detection entirely.

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
- `enhanced_prompt`: AI-enhanced English prompt (model-specific)
- `negative_prompt`: Extracted negative concepts

**File names:** `_slugify_prompt()` translates non-ASCII prompts to English before slugifying, so Japanese "病院の建物" becomes `hospital-building_opt1_var1.png` (not `asset.png`).

### 15.3 Bilingual Prompt Preview

When a user types a non-English prompt, a translation preview bar appears with:
- Language badge (e.g., "日本語 → English")
- Two tabs: **Original** (shows user's text) and **English** (shows what the model will receive)
- Translation fetched via debounced API call (`POST /api/refine-prompt/translate-preview`)
- Available in Image Studio (PromptEditor) and Video Studio prompt areas

### 15.4 UI String Translation

- 800+ translation keys across 16 categories (nav, common, image_studio, video_studio, etc.)
- Components use `t('key')` in template literals: `${t('image_studio.title')}`
- Confirm dialogs, toast messages, tooltips, placeholders all translated
- Technical terms stay in English: AI, LLM, SVG, PNG, S3, AWS, Bedrock, API
- Product names stay in English: ArtSmoker, Stable Diffusion

### 15.5 Adding a New Language

1. Copy `frontend/js/i18n/en.json` to `frontend/js/i18n/{code}.json`
2. Translate all values (keep keys identical)
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
│   └── Each iteration: image model → post-process → save to S3
├── State 3: Assemble metadata, write batch result to S3
└── State 4: Mark job complete (DynamoDB or S3 marker)
```

**Changes required**:

1. **Separate frontend hosting**: Upload `frontend/` to an S3 bucket with static website hosting. CloudFront distribution with two origins: S3 for `/*` and App Runner for `/api/*`. This eliminates frontend load from the API tier and gives global CDN caching.

2. **Async generation with Step Functions**:
   - `POST /api/generate/` no longer blocks. It validates the request, writes a job record (DynamoDB or S3), starts a Step Functions execution, and returns `{"job_id": "...", "status": "pending"}`.
   - The Step Functions state machine orchestrates the pipeline:
     - **ConceptGeneration** task: Lambda (or inline) calls Claude Opus for concept prompts. This is fast (5-15s) and fits Lambda's model.
     - **GenerateImages** Map state: Fans out to N×M parallel Lambda invocations, each generating one image (Stable Diffusion 3.5 Large + post-processing). Each Lambda runs for 30-60s — well within limits.
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

4. **Billing integration** (optional): Stripe or AWS Marketplace for paid tiers. Generation costs are roughly: Claude Opus concept generation (~$0.02-0.05 per batch) + Stability image generation (~$0.04-0.14 per image) + Stability AI post-processing (~$0.02-0.04 per image). A 5×5 batch costs approximately $1.50-3.50 in Bedrock API fees.

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

| Service | 5×5 SD 3.5 Large (no upscale) | 3×3 Stable Image Core (no upscale) |
|---------|-------------------------------|------------------------------------|
| App Runner (1 instance) | ~$30/month | ~$30/month |
| S3 (50GB) | ~$5/month | ~$5/month |
| Claude (prompts + concepts) | ~$27/month | ~$5/month |
| Image generation | ~$1,000/month | ~$180/month |
| Remove Background | ~$875/month | ~$315/month |
| **Total** | **~$1,937/month** | **~$535/month** |

> [!TIP]
> **Biggest cost levers**: Image model choice (Stable Image Core at $0.04 vs Ultra at $0.14 = 3.5× difference), batch size (3×3 = 9 images vs 5×5 = 25 = 2.8× difference), and Creative Upscale ($0.60/image — only use on final selected assets).

## 17. Disclaimer

**Generated Content Quality**: All images, videos, and other assets generated by ArtSmoker are produced by AI models available through Amazon Bedrock, including both first-party AWS models and third-party models. The quality, accuracy, and appropriateness of generated content depend entirely on the prompts provided, the models selected, and the style references uploaded by the user. The authors and contributors of ArtSmoker make no guarantees regarding the quality, suitability, or fitness for purpose of any generated content.

**Intellectual Property**: Users are solely responsible for ensuring that their prompts, reference images, and generated outputs do not infringe on any third-party intellectual property rights, including but not limited to copyrights, trademarks, and personality rights. ArtSmoker is a tool — it does not filter, validate, or assess the IP status of inputs or outputs. The tool authors and contributors bear no responsibility for any IP infringement arising from the use of this software.

**AI Model and Service Terms**: Generated content is subject to the terms of service and acceptable use policies of the underlying AI model providers accessible through Amazon Bedrock. Users should review the [AWS Service Terms](https://aws.amazon.com/service-terms/), the [Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/), and the individual model provider terms before using generated assets in production or commercial contexts.

**No Warranty**: This software is provided "as is" without warranty of any kind. See [LICENSE](LICENSE) for full terms.
