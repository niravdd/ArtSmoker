# ArtSmoker — AI-Powered Game Asset Generation Platform

## Table of Contents

- [Context](#context)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Detailed Component Design](#detailed-component-design)
  - [1. Style Profile System](#1-style-profile-system)
  - [2. Two-Level Asset Generation Pipeline](#2-two-level-asset-generation-pipeline)
  - [3. Strong Asset-Type Differentiation](#3-strong-asset-type-differentiation)
  - [4. Result Model Structure](#4-result-model-structure)
  - [5. Voice Input (Nova Sonic)](#5-voice-input-nova-sonic)
  - [6. Frontend Design](#6-frontend-design)
  - [7. Technology Choices](#7-technology-choices)
  - [8. AWS Configuration](#8-aws-configuration)
  - [9. Post-Processing Pipeline](#9-post-processing-pipeline)
  - [10. Storage Layer](#10-storage-layer)
- [API Reference](#api-reference)
  - [Styles](#styles)
  - [Generation](#generation)
  - [Prompt Refinement](#prompt-refinement)
  - [Voice Transcription](#voice-transcription)
  - [Gallery](#gallery)
  - [Type Studio](#type-studio)
  - [Browse](#browse)
  - [System](#system)
- [Prerequisites: AWS Setup](#prerequisites-aws-setup)
- [Configuration](#configuration)
- [Verification](#verification)
- [AWS Bedrock Pricing & Cost Breakdown](#aws-bedrock-pricing--cost-breakdown)
  - [Per-Unit Pricing](#per-unit-pricing)
  - [Style Analysis Cost](#style-analysis-cost-one-time-per-style)
  - [Generation Cost Scenarios](#generation-cost-scenarios)
  - [Full Cost Examples](#full-cost-examples)
- [Deployment & Scaling Roadmap](#deployment--scaling-roadmap)
  - [Phase 1: Local Development](#phase-1-current--local-development-done)
  - [Phase 2: App Runner + S3](#phase-2-containerized-deployment--app-runner--s3)
  - [Phase 3: CloudFront + Async](#phase-3-optimized-delivery--cloudfront--async-generation)
  - [Phase 4: Multi-Tenant](#phase-4-multi-tenant-platform)

---

## Context

A web-based platform that generates 2D game assets and marketing materials using AWS Bedrock AI models. The platform accepts text or voice prompts, learns visual styles from user-uploaded reference art, and produces game-ready assets (PNG + SVG). It is designed to be generic and scalable — any game studio can upload their art theme and generate consistent new assets.

The system uses a **two-level generation model**: for each user prompt, Claude Opus generates multiple distinctly different creative *options* (concept designs), and for each option the image generator produces multiple seed *variations*. This gives the user a broad creative palette to choose from.

## Architecture Overview

```
Browser (Vanilla JS + Tailwind CSS)
    |
    +-- Voice input (MediaRecorder → Nova Sonic for transcription)
    +-- Text input with inline LLM prompt refinement
    +-- Style library management (upload, browse, edit, directory import)
    +-- 2D Image Studio: two-tier generation UI (options × variations)
    +-- Type Studio: text overlay system (on-image + standalone)
    +-- Generated asset gallery with export
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
    +-- /api/browse         — Server-side file browser (local + S3)
    +-- /api/log            — Client-side error logging
    |
    v
AI Pipeline (AWS Bedrock)
    |
    +-- Claude Sonnet 4.6      — Fast tasks: prompt refinement, generation hints
    +-- Claude Opus 4.6        — Complex tasks: style analysis, concept generation, marketing copy
    +-- Nova Canvas             — Primary image generation (text-to-image)
    +-- Titan Image v2          — Alternative image generation
    +-- SD 3.5 Large            — Image generation (Stability AI)
    +-- Stable Image Ultra      — Image generation (Stability AI premium)
    +-- Stability AI            — Background removal, upscaling
    +-- Nova Sonic              — Speech-to-text transcription (bidirectional streaming)
    |
    v
Storage (Local filesystem, S3-ready interface)
    +-- /data/styles/       — Style profiles + reference images
    +-- /data/generated/    — Output assets (PNG + SVG) + metadata
```

## Project Structure

```
ArtSmoker/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, lifespan, static mount
│   ├── config.py                  # AWS config, model IDs, paths, defaults
│   ├── routers/
│   │   ├── styles.py              # Style profile CRUD + directory import + analysis
│   │   ├── generate.py            # Two-level asset generation (options × variations)
│   │   ├── transcribe.py          # Voice transcription endpoint
│   │   ├── refine.py              # Prompt refinement preview endpoint
│   │   └── gallery.py             # Generated asset browsing + file serving
│   ├── services/
│   │   ├── style_analyzer.py      # Claude Opus: multi-image style analysis → profile (includes _smart_sample())
│   │   ├── prompt_engineer.py     # Claude Sonnet/Opus: prompt refinement + concept generation
│   │   ├── image_generator.py     # Nova Canvas / Titan Image / SD 3.5 Large / Stable Image Ultra: generate images
│   │   ├── post_processor.py      # Stability AI: bg removal, upscale; vtracer/potrace: SVG
│   │   ├── transcriber.py         # Nova Sonic: bidirectional streaming speech-to-text
│   │   └── bedrock_client.py      # Shared Bedrock client with connection pooling
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
│   │   │   ├── TypeStudio.js      # Type Studio: text overlay system (on-image + standalone)
│   │   │   ├── VoiceInput.js      # Voice recording + transcription
│   │   │   ├── PromptEditor.js    # Text input with inline LLM refinement
│   │   │   ├── Gallery.js         # Generated assets grid
│   │   │   └── AssetViewer.js     # Full-size preview + download
│   │   └── services/
│   │       └── api.js             # Backend API client
│   └── assets/                    # Static assets (icons, etc.)
├── data/
│   ├── styles/                    # User-uploaded style profiles + reference images
│   └── generated/                 # Output assets (PNG + SVG + metadata)
├── SPEC.md                        # This file — full project specification
└── README.md                      # Quick-start guide
```

## Detailed Component Design

### 1. Style Profile System

A style profile captures the visual DNA of a game's art:

```json
{
  "id": "city-builder-kenney",
  "name": "Kenney City Builder",
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
    "background": "transparent"
  },
  "generation_hints": "Isometric low-poly game asset, flat shading, cheerful colors, transparent background, single object centered, no shadows, Kenney style"
}
```

**Pydantic models** (`backend/models/style_profile.py`):
- `AnalyzedStyle` — structured fields: perspective, palette (list of hex strings), rendering, line_weight, mood, scale, background.
- `StyleProfile` — full profile with id, name, description, created_at, reference_images, analyzed_style, generation_hints.
- `StyleProfileCreate` — name + description + optional `generation_hints` for creation.
- `StyleProfileUpdate` — optional name, description, analyzed_style, generation_hints for partial updates.

**Workflow:**
1. User creates a style profile (name + description + optional `generation_hints`).
2. User uploads 1-50 reference images via file upload or **directory import** (bulk import from a local folder path or S3 prefix). The cap is configurable via `max_reference_images` (default 50, env: `ARTSMOKER_MAX_REFERENCE_IMAGES`).
3. **Smart sampling for analysis**: When a style has more than `max_analysis_images` (default 15, env: `ARTSMOKER_MAX_ANALYSIS_IMAGES`) reference images, the `_smart_sample()` function in `style_analyzer.py` selects a diverse representative subset for the Claude Opus vision call. Sampling strategy:
   - Always includes the first and last image (alphabetically).
   - Groups images by filename prefix (subdirectory origin) and picks at least one from each group.
   - Fills remaining slots by file-size diversity (evenly-spaced intervals across the size range, since different sizes suggest different content/complexity).
   - Claude is told how many total images exist vs. how many it is seeing (e.g. "You are seeing 15 representative images sampled from a collection of 50 total reference images").
   When the image count is at or below `max_analysis_images`, all images are sent directly.
4. Claude Opus 4.6 (vision) analyzes the (sampled) images via `analyze_style(style_id, user_hints)`, extracting structured style attributes as JSON. The analysis is **context-aware** — Claude sees both the images AND the user's existing `generation_hints` (passed as "Artist's Guidance") so it understands the user's intent.
5. Claude Sonnet 4.6 distils the analysis into a concise `generation_hints` paragraph (max 120 words) via `generate_hints(style_id, analyzed_style, user_hints)`, also receiving the user's guidance as context.
6. Profile is cached as `profile.json` inside `data/styles/{style_id}/`.
7. User can manually edit/refine the profile.
8. Profile's `generation_hints` are incorporated into every generation prompt.
9. **Auto re-analysis**: Style analysis is automatically re-triggered when (a) reference images are uploaded via the upload endpoint, or (b) `generation_hints` are changed via PATCH and the new value differs from the previous one. Both paths use a shared `_auto_reanalyze()` helper.

**Directory/S3 import**: The `POST /api/styles/{id}/import` endpoint accepts a local directory path or S3 prefix. Body: `{ "path": "...", "auto_analyze": true }`. It scans **recursively** (using `rglob`) for all image files (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif) in all subdirectories. **Local imports use symlinks** (not copies) to avoid disk duplication. S3 imports download files to the references folder; the S3 client paginates through all objects (handles >1000 keys). Browser uploads copy files normally. Filenames from different subdirectories are **deduplicated** by prefixing with the parent directory name when collisions are detected. The total reference image count is capped at `max_reference_images` (default 50, env: `ARTSMOKER_MAX_REFERENCE_IMAGES`). Optionally auto-triggers Claude Opus style analysis after import.

### 2. Two-Level Asset Generation Pipeline

The generation system produces images across two dimensions:

- **Options** (1-5, default 5): Distinctly different creative concepts generated by Claude Opus. Each option has a completely different design prompt — different visual approaches, moods, silhouettes, and aesthetics.
- **Variations** (1-5, default 5): Seed variations of each option. Same prompt, different random seeds passed to the image generator.
- **Total images** = `num_options` x `num_variations` (up to 25 images per batch).

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
         |
         v
    For each concept prompt, generate num_variations images in parallel:
         |
         v
    [Image Generation — Nova Canvas, Titan Image, SD 3.5 Large, or Stable Image Ultra]
    Input: refined prompt + random seed per variation
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

**Parallel execution**: All option-variation combinations are dispatched to a `ThreadPoolExecutor` with `max_workers=min(total, 5)` to limit Bedrock API throttling.

**Real-time progress via SSE**: The `/stream` endpoint uses Server-Sent Events (SSE) for real-time progress updates during generation. Event types: `started` (generation kicked off), `stage` (pipeline phase — `prompts`/`generating`/`finalizing`), `image_done` (per-image with `completed`/`total` count), `image_error` (per-image failure), and `complete` (final result).

**Smart filenames**: Each generated image gets a human-readable filename derived from the user's prompt slug plus the option/variation indices: `a-fierce-dragon_opt1_var2.png`. These filenames are stored in per-asset `metadata.json` and served via `Content-Disposition` headers on the gallery file endpoints.

**Prompt length limit**: Amazon Nova Canvas enforces a 1024-character prompt limit. The prompt engineer instructs Claude to keep outputs under **900 characters**, and there is a hard truncation fallback at 1024 characters (breaking on word boundaries) in `refine_prompt()`, `refine_marketing_prompt()`, and `generate_concept_prompts()`.

### 3. Strong Asset-Type Differentiation

Each `AssetType` has detailed structural directives in `prompt_engineer.py` covering five dimensions. These are injected into the prompt template with instructions to follow them **precisely**. The same user prompt produces fundamentally different images depending on the asset type.

| Asset Type | Key Directives |
|---|---|
| `game_asset` | **OUTPUT**: In-game sprite/tile/object. **COMPOSITION**: Single object, centered, isolated on transparent background. **FRAMING**: Straight-on or style's canonical perspective, fill 70-80% of frame. **TECHNICAL**: Clean sharp edges, consistent lighting (top-left default), no ground shadows. **DO NOT**: Include text, UI, multiple objects, or scene backgrounds. |
| `marketing_banner` | **OUTPUT**: Promotional banner. **COMPOSITION**: Full-scene illustration, reserve left/right third as text-safe zone (must be empty for post-production overlay), strong focal point opposite. **FRAMING**: Wide/cinematic feel, camera pulled back. **TECHNICAL**: Rich saturated colors, dramatic lighting, depth-of-field. **NO TEXT** — do not render any text, letters, words, or typography; the text-safe zone must remain empty. **DO NOT**: Make it sparse or icon-like. Marketing prompt template also strips text requests from the user prompt and instructs Claude to ignore title/text mentions. |
| `icon` | **OUTPUT**: App/UI/button icon. **COMPOSITION**: Single bold recognizable symbol, centered with 15% padding. **FRAMING**: Front-facing or slight 3/4 tilt. **TECHNICAL**: Must read at 64x64, high contrast, 3-5 colors, bold shapes. **DO NOT**: Add complexity, fine detail, or scene context. |
| `character` | **OUTPUT**: Character design/portrait. **COMPOSITION**: Full/3/4-body, slightly off-center, facing viewer or 3/4 view. Isolated on clean background. **FRAMING**: Fill 60-75% vertical, head-to-toe or head-to-knee. **TECHNICAL**: Strong readable silhouette, expressive pose, consistent lighting. **DO NOT**: Crop limbs awkwardly, add backgrounds, include multiple characters. |
| `environment` | **OUTPUT**: Environment/background/landscape. **COMPOSITION**: Full scenic illustration with foreground/midground/background depth layers, leading lines. **FRAMING**: Wide establishing shot, horizon at upper/lower third. **TECHNICAL**: Atmospheric perspective, environmental storytelling, mood-setting lighting. **DO NOT**: Make it flat or icon-like. |

### 4. Result Model Structure

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

Each variant is stored in its own directory under `data/generated/{asset_id}/` with `asset.png`, optionally `asset.svg`, and `metadata.json`. The metadata per variant also stores `original_prompt` alongside the other generation fields.

**Style snapshot in metadata**: Each generated asset (from both 2D Image Studio and Type Studio) stores a `style_snapshot` object capturing the style's state at generation time:
```json
{
  "style_snapshot": {
    "name": "Kenney City Builder",
    "description": "Low-poly isometric city buildings",
    "generation_hints": "Isometric low-poly game asset, flat shading...",
    "analyzed_style": { "perspective": "...", "palette": [...], ... }
  }
}
```
This ensures that if the original style profile is later deleted or modified, the asset retains the full style context that was used during its creation. The AssetViewer shows the style name from `style_snapshot` as a fallback when the original style no longer exists. The gallery batch endpoint (`GET /api/gallery/batch/{batch_id}`) includes the `style_snapshot` in each variant's metadata.

**GalleryItem** — a flat summary model for the gallery listing endpoint:
- id, prompt, style_id, asset_type, png_url, svg_url, created_at.

### 5. Voice Input (Nova Sonic)

- Browser captures audio via `MediaRecorder` API (WebM/Opus format).
- Audio file sent to backend `POST /api/transcribe/` as a multipart upload.
- Backend attempts Nova Sonic bidirectional streaming transcription (`invoke_model_with_bidirectional_stream`).
- If streaming API is unavailable or access is denied, returns a placeholder message indicating the audio was received but full transcription requires streaming setup.
- Transcribed text displayed in prompt editor for user review/editing.

### 6. Frontend Design

Clean, modern single-page application served as static files mounted at `/` by FastAPI.

**Navigation**: The top nav shows the ArtSmoker logo with the tagline "Smoke-testing your artwork!" followed by four views in order: **Style Library** (`#styles`) → **2D Image Studio** (`#image-studio`) → **Type Studio** (`#type-studio`) → **Gallery** (`#gallery`).

**No Claude branding in frontend**: All user-facing UI references use "AI" generically — never "Claude". For example, buttons say "AI Improve" not "Claude Improve", and labels say "AI-improved prompt" not "Claude-improved prompt".

**DOM caching router**: Views survive navigation. Each view's DOM is cached and shown/hidden instead of destroyed/recreated on route changes. `window.resetView(route)` destroys the cache for a specific view to force a fresh start.

**No-cache middleware**: During development, frontend static files are served with no-cache headers to ensure changes are reflected immediately.

**Client-side error logging**: All toast errors/warnings and unhandled JS errors are sent to `POST /api/log` and logged server-side with a `[CLIENT]` prefix for unified debugging.

**Style Library** — Grid of style profiles with thumbnails. Upload new styles, upload reference images, trigger AI analysis.
- **Create modal**: Includes "Import References From" section with Local and S3 browse buttons for importing reference images at creation time.
- **Detail view**: Has an "Import & Analyze" button (always auto-analyzes after import, no toggle). The analysis button is contextual: "Analyze Style" when no analysis exists, "Re-Analyze Style" when one does.
- **Server-side file browser modal**: Used for both local and S3 browsing. Single-click selects a file/folder, double-click navigates into a directory. Back button and ".." entry navigate to the parent directory.

**2D Image Studio** (`#image-studio`) — The main image generation workspace with a two-tier result display:
- **Left sidebar**: Art style selector, asset type, image model, dimensions (size presets: 512x512, 768x768, 1024x1024, 1024x576, 576x1024, 1280x720), options count (1-5, default 5), variations count (1-5, default 5), processing toggle switches (see below).
- **Processing options**: Toggle switches for Remove Background, SVG Conversion (on by default), and Upscale. Before generation these are labeled **"Pre-Processing"** (applied during generation). After generation completes, the label switches to **"Post-Processing"** and an **"Apply to Current Results"** button appears, allowing users to re-apply processing to the existing generated images without re-generating (calls `POST /api/generate/post-process`).
- **Center panel**: Prompt editor (text + voice input), Generate button (indigo) and Reset button (amber) at equal width. After generation, shows both the original prompt and the AI-improved prompt. `loadBatch(batchId)` method restores a previous batch from the Gallery into the 2D Image Studio view.
- **Options row** (indigo/accent borders): Shows different creative concepts as thumbnail cards. Each card shows the first variation as a preview, the option number badge, and a truncated concept prompt. Click to select an option.
- **Concept prompt display**: Shows the full refined prompt for the selected option.
- **Variations row** (emerald borders): Shows seed variants of the selected option. Click to select a variation.
- **Main preview**: Large preview of the selected variant with checkerboard transparency background.
- **Download bar**: Shows the smart filename (e.g. `a-fierce-dragon_opt1_var2.png`) and provides PNG + SVG download buttons using the human-readable filenames.

If there is only one option, the options row is hidden. If there is only one variation, the variations row is hidden.

**Type Studio** (`#type-studio`) — Full text overlay system for creating titled/branded versions of gallery images or standalone text compositions.

- **Two modes**:
  - **"On Image"** — Composites text onto a selected gallery image. User picks a base image from the gallery as the background.
  - **"Standalone"** — Renders text on a transparent background (no base image).

- **Multi-line text editor**: Users enter one or more lines of text. Each line supports:
  - Individual **font selection** from the font picker.
  - **Position hints** (e.g. top-center, bottom-left) to guide AI layout placement.

- **AI layout suggestion**: The backend (`POST /api/type-studio/suggest`) uses AI to suggest text layout parameters including position, size, color, and effects for each line. Returns **1-5 layout options** representing different creative directions (e.g. bold centered vs. subtle corner placement). The user selects their preferred layout option before rendering.

- **Pillow rendering**: The backend (`POST /api/type-studio/preview`) renders the final composition using Pillow with support for **shadow**, **outline**, and **glow** text effects. The rendered result is saved as a new gallery asset.

- **Font picker**: Shows fonts in priority order:
  1. **Style-specific fonts** — fonts associated with the selected style profile (shown first).
  2. **Global fonts** — project-wide custom fonts.
  3. **System fonts** — detected from the host OS.
  All fonts show a **live preview** of the selected text in the picker dropdown. Fonts are served via `GET /api/type-studio/font-file/{source}/{filename}`.

- **Processing options**: Same toggle switches as 2D Image Studio (Remove BG, SVG Conversion on by default, Upscale) with the same Pre-Processing → Post-Processing label behavior and "Apply to Current Results" button.

- **Gallery integration**: Results are saved as new gallery assets with full metadata (including `source: "type-studio"`, base image reference if applicable, text content, font choices, layout parameters, and `style_snapshot`). Assets created in Type Studio can be loaded back from the Gallery via an **"Edit in Type Studio"** button in the AssetViewer.

**Gallery** (`#gallery`) — Grid of all generated assets sorted newest-first. Images load immediately (no IntersectionObserver). Backend always reads metadata fresh from disk (no cache-first strategy — ensures consistency after post-processing updates). Supports pagination via `limit` and `offset` query parameters. Filter by style and asset type. Auto-refreshes via `onShow()` when navigating back to the Gallery view.
- **Search bar**: Instant filtering across prompts, style names, and asset types as the user types.
- **Multi-select**: Checkboxes on each asset card for bulk selection. A **"Delete Selected"** button triggers `DELETE /api/gallery/` with `{ids: [...]}` for bulk deletion.
- Click any asset to open the AssetViewer.

**AssetViewer** — Full-size preview + download. Fetches full metadata from `GET /api/gallery/{id}` on open. Displays all available fields: original prompt, AI-improved prompt, generation prompt, style (from `style_snapshot` as fallback if the original style was deleted), asset type, image model (with friendly labels), dimensions, seed, batch ID, option/variation index, filename, and creation date. The **SVG tab/button is hidden** when no SVG file exists for the asset. Metadata display adapts for Type Studio assets (shows text content, font choices, layout parameters instead of generation prompts).
- **Contextual action buttons**:
  - **"2D Studio"** (indigo) — visible for image-type assets only. Sends the batch back to the 2D Image Studio view.
  - **"Add Text"** (emerald) — visible for image-type assets only. Opens Type Studio in "On Image" mode with this asset as the base image.
  - **"Edit in Type Studio"** (purple) — visible for type-studio assets only. Loads the asset back into Type Studio for re-editing.

### 7. Technology Choices

| Component | Technology | Reason |
|-----------|-----------|--------|
| Backend | FastAPI (Python 3.11+) | Async, fast, Pydantic models, auto-docs |
| Frontend | Vanilla JS + Tailwind CSS | No build step, fast to iterate, lightweight |
| AI Models | Bedrock (boto3) | Nova Canvas, Titan Image, SD 3.5 Large, Stable Image Ultra, Claude, Nova Sonic, Stability |
| SVG Conversion | vtracer (primary), potrace (fallback), Pillow (last resort) | Cascade of vector tracing methods |
| Text Rendering | Pillow (Python Imaging Library) | Text overlay composition with shadow, outline, glow effects |
| Storage | Local filesystem | Simple start, S3-compatible interface for later migration |

### 8. AWS Configuration

**Default AWS Profile**: None — uses the standard AWS credential chain (configurable via `ARTSMOKER_AWS_PROFILE`).

**Two-region architecture**:
- `us-west-2` (`aws_region_models`): Claude models, Stability AI models (including SD 3.5 Large, Stable Image Ultra).
- `us-east-1` (`aws_region_images`): Nova Canvas, Titan Image, Nova Sonic.

**Bedrock client** (`backend/services/bedrock_client.py`):
- Lazy-initialized boto3 clients keyed by region with connection pooling (10 max pool connections).
- Adaptive retry configuration (3 max attempts).
- `invoke_claude(prompt, complexity, images, max_tokens, temperature)` — routes to Sonnet or Opus based on complexity parameter.
- `invoke_sd35_large(prompt, seed, width, height)` — generates images via SD 3.5 Large.
- `invoke_stable_image_ultra(prompt, seed, width, height)` — generates images via Stable Image Ultra.
- `_dimensions_to_aspect_ratio(width, height)` — maps pixel dimensions to the closest Stability AI supported aspect ratio (1:1, 16:9, 9:16, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21). Used by both Stability generation methods.
- Uses the Bedrock **Converse API** for Claude invocations (supports text + vision inputs).

**Claude Model Selection Logic:**
- `invoke_claude(complexity="fast")` routes to Sonnet.
- `invoke_claude(complexity="complex")` routes to Opus.

**Model fallback**: On `AccessDeniedException` from the primary Claude model, the system automatically falls back to Claude 3.5 Sonnet v2.

| Model | ID | Region | Purpose |
|-------|----|--------|---------|
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` | us-west-2 | Fast: prompt refinement, generation hints |
| Claude Opus 4.6 | `us.anthropic.claude-opus-4-6-v1` | us-west-2 | Complex: style analysis, concept generation, marketing copy |
| Claude 3.5 Sonnet v2 (fallback) | `anthropic.claude-3-5-sonnet-20241022-v2:0` | us-west-2 | Fallback on access denied |
| Nova Canvas | `amazon.nova-canvas-v1:0` | us-east-1 | Primary image generation |
| Titan Image v2 | `amazon.titan-image-generator-v2:0` | us-east-1 | Alternative image generation |
| Stability Remove BG | `us.stability.stable-image-remove-background-v1:0` | us-west-2 | Background removal |
| Stability Upscale | `us.stability.stable-creative-upscale-v1:0` | us-west-2 | Image upscaling |
| SD 3.5 Large | `stability.sd3-5-large-v1:0` | us-west-2 | Image generation (Stability AI) |
| Stable Image Ultra | `stability.stable-image-ultra-v1:1` | us-west-2 | Image generation (Stability AI premium) |
| Nova Sonic | `amazon.nova-2-sonic-v1:0` | us-east-1 | Speech-to-text |

> Note: Claude and Stability AI post-processing model IDs use **US inference profiles** (`us.anthropic.claude-sonnet-4-6`, `us.anthropic.claude-opus-4-6-v1`, `us.stability.stable-image-remove-background-v1:0`, `us.stability.stable-creative-upscale-v1:0`) rather than full versioned model IDs. SD 3.5 Large and Stable Image Ultra use **direct model IDs** (not inference profiles).

> Note: Stability AI generation models (SD 3.5 Large, Stable Image Ultra) use **aspect ratios** instead of exact pixel dimensions. The backend provides a `_dimensions_to_aspect_ratio()` helper that maps width×height to the closest supported ratio: 1:1, 16:9, 9:16, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21.

### 9. Post-Processing Pipeline

The post-processing pipeline (`backend/services/post_processor.py`) applies three optional steps in sequence:

1. **Background removal** — Stability AI Remove Background model. If it fails, the pipeline continues with the original image.
2. **Upscaling** — Stability AI Creative Upscale model. Takes the refined prompt as a quality guide. If it fails, the pipeline continues with the current image.
3. **SVG conversion** — Cascading approach:
   - **vtracer** (preferred): High-quality color vector tracing with configurable parameters (color precision 6, layer difference 16, speckle filter 4, etc.).
   - **potrace** (fallback): Monochrome bitmap tracing. Converts PNG to BMP via Pillow first.
   - **Pillow embedded raster** (last resort): Wraps the PNG as a base64 data URI inside an SVG element. Not a true vector but ensures SVG output is always available.

**Creative Upscale details**: Uses JPEG output format to avoid Stability AI's 16MB response payload limit, then converts back to PNG. Includes retry with exponential backoff (up to 5 attempts) for API throttling. Thread pool concurrency is reduced to 3 workers when upscale is enabled to avoid rate limits.

Each step is independently fault-tolerant — failures are logged but do not abort the pipeline.

### 10. Storage Layer

`LocalStore` (`backend/storage/local_store.py`) provides an S3-compatible interface over the local filesystem:

**Style storage** (`data/styles/{style_id}/`):
- `profile.json` — serialized StyleProfile.
- `references/` — uploaded reference images. Local directory imports are stored as **symlinks** to avoid disk duplication; S3 downloads and browser uploads are stored as copies.

**Key methods**:
- `link_reference_image(style_id, filename, source_path)` — creates a **relative symlink** (via `os.path.relpath()`) in the style's references folder pointing to the source file. Used by the local directory import path. Relative symlinks survive directory moves and work across machines (unlike absolute symlinks). S3 and browser uploads still copy files.

**Generated asset storage** (`data/generated/{asset_id}/`):
- `asset.png` — final processed PNG.
- `asset.svg` — optional SVG conversion.
- `metadata.json` — full generation metadata (prompt, refined_prompt, style_id, asset_type, seed, filenames, etc.).

Asset IDs follow the pattern `{batch_uuid}_o{option_index}_v{variant_index}`.

## API Reference

### Styles

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/styles/` | Create a new style profile (name + description + optional generation_hints). ID is auto-generated as a slug. Returns 409 on duplicate. |
| GET | `/api/styles/` | List all style profiles. |
| GET | `/api/styles/{id}` | Get a single style profile by identifier. |
| PATCH | `/api/styles/{id}` | Partially update a style profile (name, description, analyzed_style, generation_hints). Auto-triggers re-analysis when `generation_hints` change (new value differs from previous). |
| DELETE | `/api/styles/{id}` | Delete a style profile and all its associated data (references, profile.json). |
| POST | `/api/styles/{id}/references` | Upload reference images (multipart file upload). Enforces max_reference_images limit (default 50). Auto-triggers re-analysis after upload. |
| GET | `/api/styles/{id}/references/{filename}` | Serve a reference image file. |
| POST | `/api/styles/{id}/import` | Import image files from a local directory path or S3 prefix. Body: `{ "path": "/path/to/images", "auto_analyze": true }`. Scans recursively for all image files in subdirectories. Local imports use symlinks (not copies). S3 imports download files (paginates through >1000 keys). Filenames are deduplicated by prefixing with parent directory name. Optionally triggers style analysis after import. |
| POST | `/api/styles/{id}/analyze` | Trigger AI style analysis on reference images. If the style has more than `max_analysis_images` (default 15) references, smart sampling selects a diverse subset. Claude Opus analyzes images (context-aware, receives existing generation_hints as "Artist's Guidance"), Claude Sonnet generates hints. Both are persisted to the profile. |

### Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate/` | Generate assets (full two-level pipeline). Returns `GenerationResult` with options and variants. |
| POST | `/api/generate/post-process` | Apply post-processing to existing generated assets. Accepts asset IDs and processing flags (remove_background, generate_svg, upscale). Updates the assets in-place and refreshes their metadata on disk. Used by the "Apply to Current Results" button in both studios. |

**Request body** (`GenerationRequest`):
```json
{
  "prompt": "hospital building",
  "original_prompt": "hospital",
  "style_id": "city-builder-kenney",
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
- `style_id` (optional): Style profile to apply.
- `asset_type` (default `game_asset`): One of `game_asset`, `marketing_banner`, `icon`, `character`, `environment`.
- `image_model` (default `nova_canvas`): One of `nova_canvas`, `titan_image`, `sd35_large`, `stable_image_ultra`. Defined by the `ImageModel` enum: `NOVA_CANVAS = "nova_canvas"`, `TITAN_IMAGE = "titan_image"`, `SD35_LARGE = "sd35_large"`, `STABLE_IMAGE_ULTRA = "stable_image_ultra"`.
- `width` / `height` (default 1024): Output dimensions in pixels.
- `num_options` (default 5, range 1-5): Number of distinct concept designs.
- `num_variations` (default 5, range 1-5): Number of seed variants per option.
- `remove_background` (default true): Run Stability AI background removal.
- `generate_svg` (default true): Convert to SVG.
- `upscale` (default false): Run Stability AI upscaling.

### Prompt Refinement

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/refine-prompt/` | Preview a refined prompt without generating images. |

**Request body** (`PromptRefineRequest`):
```json
{
  "prompt": "hospital building",
  "style_id": "city-builder-kenney",
  "asset_type": "game_asset"
}
```

**Response**:
```json
{
  "original": "hospital building",
  "refined": "Isometric low-poly hospital building, flat shading, white and red..."
}
```

### Voice Transcription

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transcribe/` | Transcribe an uploaded audio file to text (multipart form upload, field name `file`). |

**Response**:
```json
{
  "text": "hospital building with a red cross on the roof"
}
```

### Gallery

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gallery/` | List generated assets. Supports query params: `style_id`, `asset_type`, `limit` (default 100, max 500), `offset` (default 0). Returns list of `GalleryItem`, sorted newest-first. Always reads metadata fresh from disk (no cache-first strategy). |
| GET | `/api/gallery/{id}` | Get the full metadata dictionary for a generated asset (includes `style_snapshot`). |
| GET | `/api/gallery/{id}/png` | Download the PNG file. `Content-Disposition` header uses the smart filename (e.g. `prompt-slug_opt1_var2.png`). |
| GET | `/api/gallery/{id}/svg` | Download the SVG file. `Content-Disposition` header uses the smart filename. |
| DELETE | `/api/gallery/` | Bulk delete assets. Request body: `{ "ids": ["asset_id_1", "asset_id_2", ...] }`. Deletes the asset directories and their contents from disk. Returns count of deleted assets. |
| GET | `/api/gallery/batch/{batch_id}` | Reconstruct the full options x variations structure for a batch (includes `style_snapshot` per variant). Used to reload a previous batch into the 2D Image Studio view. |

### Type Studio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/type-studio/fonts` | List available fonts grouped by source. Returns style-specific fonts (for the given `style_id` query param), global project fonts, and detected system fonts. Each entry includes font name, filename, source, and a preview URL. |
| GET | `/api/type-studio/font-file/{source}/{filename}` | Serve a font file (TTF/OTF/WOFF2) for rendering or live preview. `source` is one of `style`, `global`, or `system`. |
| POST | `/api/type-studio/suggest` | AI layout suggestion. Accepts text lines, font choices, position hints, mode ("on_image" or "standalone"), optional base image ID, and style_id. Returns 1-5 layout options, each with per-line position (x, y), font size, color, and effects (shadow, outline, glow) representing different creative directions. |
| POST | `/api/type-studio/preview` | Render and save the text overlay. Accepts text lines, selected layout option, font choices, mode, optional base image ID, style_id, and processing flags. Pillow renders the composition with the specified effects. Saves the result as a new gallery asset with full metadata (including `style_snapshot`) and returns the new asset ID and URLs. |

### Browse

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/browse/local?path=~` | Browse local filesystem directories. Returns list of files and subdirectories at the given path. Used by the Style Library file browser modal. |
| GET | `/api/browse/s3/buckets` | List available S3 buckets. |
| GET | `/api/browse/s3?bucket=name&prefix=path` | Browse objects in an S3 bucket at the given prefix. Returns list of objects and common prefixes. |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check — returns status + AWS credential/Bedrock validation results. |
| POST | `/api/log` | Receive client-side log entries. Body: `{ "level": "error", "message": "...", "context": {} }`. Logged server-side with `[CLIENT]` prefix. |
| GET | `/docs` | Swagger UI (auto-generated by FastAPI). |

## Prerequisites: AWS Setup

ArtSmoker uses AWS Bedrock and requires working AWS credentials on the host machine **before launching**. No AWS configuration is needed inside the app itself — it uses the standard AWS credential chain.

### AWS Credentials

The app uses boto3's standard credential resolution order:
1. **Environment variables**: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (+ optional `AWS_SESSION_TOKEN`)
2. **Shared credentials file**: `~/.aws/credentials` (default profile, or set `AWS_PROFILE` for a named profile)
3. **AWS SSO**: If configured via `aws configure sso`
4. **Instance role**: Automatic on EC2, Lambda, ECS, etc.

Whatever method you use for other AWS work on your machine will work here. If `aws sts get-caller-identity` succeeds in your terminal, ArtSmoker will pick up the same credentials.

### Required IAM Permissions

The IAM principal (user, role, or SSO session) needs the following:

```
bedrock:InvokeModel          — for all image models (Nova Canvas, Titan Image, Stability AI)
bedrock:Converse             — for Claude models (Sonnet, Opus)
```

These translate to the AWS managed policy `AmazonBedrockFullAccess`, or a scoped policy on `bedrock:InvokeModel` and `bedrock:Converse` for the specific model ARNs.

### Bedrock Model Access

In the AWS Console, go to **Amazon Bedrock → Model access** and ensure the following models are **enabled** in their respective regions:

| Model | Region | Model Access Page |
|-------|--------|-------------------|
| Claude Sonnet 4.6, Claude Opus 4.6 | us-west-2 | Anthropic models |
| Nova Canvas, Titan Image v2, Nova Sonic | us-east-1 | Amazon models |
| Stability AI (Remove BG, Upscale, SD 3.5 Large, Stable Image Ultra) | us-west-2 | Stability AI models |

> Model access is regional. You need to enable models in **both** us-west-2 and us-east-1.

### Startup Validation

On launch, ArtSmoker automatically validates:
1. AWS credentials resolve (STS GetCallerIdentity)
2. Bedrock Claude access works in us-west-2
3. Bedrock Nova Canvas access works in us-east-1

Results are logged to the console and available at `GET /api/health`. If credentials are missing, a clear error message shows what to configure.

## Configuration

All per-generation settings (style, asset type, image model, dimensions, options/variations counts, post-processing toggles) are controlled through the **frontend UI**.

Infrastructure settings live in `backend/config.py` with sensible defaults that work out of the box. Model IDs, regions, and paths are all preconfigured and rarely need overriding. If needed, any setting can be overridden via an environment variable prefixed with `ARTSMOKER_` — see `backend/config.py` for the full list.

**Reference image and analysis limits** (for cost management):
- `max_reference_images: int = 50` (env: `ARTSMOKER_MAX_REFERENCE_IMAGES`) — max images imported per style. Limits storage.
- `max_analysis_images: int = 15` (env: `ARTSMOKER_MAX_ANALYSIS_IMAGES`) — max images sent to Claude Opus per analysis call. When a style exceeds this count, `_smart_sample()` selects a diverse subset. Reducing this value reduces Claude Opus vision costs per analysis.

**Image generation model ID settings**:
- `sd35_large_model_id: str = "stability.sd3-5-large-v1:0"`
- `stable_image_ultra_model_id: str = "stability.stable-image-ultra-v1:1"`

## Verification

1. **Start backend**:
   ```bash
   cd ArtSmoker && source .venv/bin/activate && uvicorn backend.main:app --reload
   ```
2. **Open frontend**: Navigate to `http://localhost:8000` — the frontend is served as static files by FastAPI.
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
9. **Test prompt refinement**: Type a brief prompt, click "Improve" — verify the refined prompt is more detailed.
10. **Test marketing banner**: Set asset type to "Marketing Banner" and generate — verify the result is a scenic composition, not an isolated sprite.
11. **Test Type Studio**: Navigate to Type Studio, enter text lines, select fonts, request AI layout suggestions. Verify 1-5 layout options are returned. Select a layout and render — verify the result is saved to the gallery.
12. **Browse gallery**: Switch to Gallery view — verify generated assets appear with filtering by style and asset type. Test the search bar for instant filtering. Test multi-select and bulk delete.
13. **Test AssetViewer buttons**: Open an image asset — verify "2D Studio" and "Add Text" buttons appear. Open a type-studio asset — verify "Edit in Type Studio" button appears.
14. **Test style_snapshot**: Delete a style, then view an asset that was generated with it — verify the style name still displays from the snapshot.
15. **Verify API docs**: Visit `http://localhost:8000/docs` — verify all endpoints are documented.

## AWS Bedrock Pricing & Cost Breakdown

All prices below are from the official [AWS Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/) for US regions (us-west-2, us-east-1). Prices are on-demand, per-request.

### Per-Unit Pricing

| Service | Model | Per-Unit Cost | Unit |
|---------|-------|--------------|------|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | $3.00 input / $15.00 output | per 1M tokens |
| **Claude Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | $5.00 input / $25.00 output | per 1M tokens |
| **Claude Opus 4.6 (vision)** | same | ~$0.008 | per 1024×1024 image input |
| **Nova Canvas** | `amazon.nova-canvas-v1:0` | $0.06 | per image (1024×1024, premium) |
| **Titan Image v2** | `amazon.titan-image-generator-v2:0` | $0.01 | per image (1024×1024) |
| **SD 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | per image |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | per image |
| **Remove Background** | `stability.stable-image-remove-background-v1:0` | $0.07 | per image |
| **Creative Upscale** | `stability.stable-creative-upscale-v1:0` | $0.60 | per image |
| **SVG Conversion** | vtracer / potrace / Pillow (local) | $0.00 | free — runs locally |

> **Vision token formula**: Claude charges image inputs as tokens: `tokens = (width × height) / 750`. A 1024×1024 image ≈ 1,398 tokens. At Opus $5.00/MTok input = ~$0.007 per image.

### Style Analysis Cost (one-time per style)

For a style with **20 reference images** (15 sent to Claude after smart sampling):

| Step | Model | Calculation | Cost |
|------|-------|-------------|------|
| Analyze images | Claude Opus 4.6 (vision) | 15 images × ~1,398 tokens + ~500 prompt tokens = ~21,470 input tokens; ~1,000 output tokens | ~$0.13 |
| Generate hints | Claude Sonnet 4.6 | ~800 input + ~200 output tokens | ~$0.005 |
| **Total per style analysis** | | | **~$0.14** |

### Generation Cost Scenarios

The generation cost depends on the image model chosen and the options×variations count. Prompt refinement cost is constant per batch.

**Base cost per batch** (prompt refinement/concept generation):

| Options | Prompt Step | Model | Approx. Cost |
|---------|-----------|-------|-------------|
| 1 option | Single prompt refinement | Claude Sonnet 4.6 | ~$0.005 |
| 5 options | Concept generation (5 prompts) | Claude Opus 4.6 | ~$0.05 |

**Image generation cost per batch** (the dominant cost):

| Scenario | Images | Nova Canvas | Titan Image v2 | SD 3.5 Large | Stable Image Ultra |
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

### Full Cost Examples

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
5 options × 5 variations, SD 3.5 Large, Remove BG + SVG:

| Step | Cost |
|------|------|
| Concept generation (Opus) | $0.05 |
| 25 images (SD 3.5 Large) | $2.00 |
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

> **Key takeaway**: Image generation is cheap ($0.01–$0.14/image). **Creative Upscale is the big cost driver at $0.60/image** — use it selectively on your final chosen assets, not on the full batch. Remove Background at $0.07/image is reasonable. SVG conversion is free.

## Deployment & Scaling Roadmap

The current architecture runs as a single local process (uvicorn + local filesystem). This section documents the phased plan for production deployment and scaling.

### Why not Lambda

AWS Lambda is not suitable as the primary compute for this application:

- **Timeout risk**: Lambda's 15-minute maximum is tight for batch generation. A 5×5 batch involves Claude Opus concept generation (5-15s) + 25 parallel image generations (8-15s each, throttled to 5 concurrent) + post-processing per image. Total wall-clock time can reach 2-5 minutes under normal conditions, but Bedrock throttling or retries push it dangerously close to the limit.
- **Cold starts**: The dependency payload (boto3, Pillow, FastAPI, Pydantic) causes 3-5 second cold starts. For an interactive tool where an artist is waiting, this adds unacceptable latency to every request after idle periods.
- **Stateless filesystem**: Lambda has no persistent local filesystem. The current `LocalStore` writes style profiles, reference images, and generated assets to disk. Lambda would require a full S3 rewrite before it could even run.
- **Synchronous payload limit**: Lambda's 6MB response limit is fine for the JSON response (image URLs, not bytes), but constrains future evolution (e.g. returning thumbnails inline, batch ZIP downloads).
- **Concurrency model mismatch**: The generation pipeline uses `ThreadPoolExecutor` internally to parallelize image generation. Lambda's single-request-per-invocation model means each Lambda would serialize its own internal threads, negating the concurrency benefit unless the architecture is decomposed into separate Lambdas per image.

Lambda _could_ work for lightweight endpoints (styles CRUD, gallery listing, health check), but mixing Lambda and non-Lambda compute for the same API adds routing complexity without meaningful benefit at this stage.

### Phase 1: Current — Local Development (Done)

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

#### EC2 Quick Start

For a lightweight production deployment (1-2 concurrent users), an EC2 instance is the simplest path:

- **Recommended instance**: t3.small (2 vCPU, 2 GB RAM, ~$15/month).
- **Run with gunicorn** for production:
  ```bash
  gunicorn backend.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 300
  ```
- **IAM role**: Attach an IAM role with `bedrock:InvokeModel` + `bedrock:Converse` permissions — no access keys needed on the instance.
- **No race conditions for concurrent users** — each generation uses unique UUIDs, file writes don't overlap.
- **Migrating style data**: Style references use relative symlinks, so they work across machines as long as the source art directories maintain the same relative position to the ArtSmoker project.

### Phase 2: Containerized Deployment — App Runner + S3

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

### Phase 3: Optimized Delivery — CloudFront + Async Generation

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

### Phase 4: Multi-Tenant Platform

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

### Infrastructure Summary

| Phase | Compute | Storage | Frontend | Auth | Scale |
|-------|---------|---------|----------|------|-------|
| 1 (Current) | Local uvicorn | Local filesystem | Served by FastAPI | None | Single user |
| 2 (Deploy) | App Runner | S3 bucket | Bundled in container | None (or basic) | Team |
| 3 (Optimize) | App Runner + Step Functions + Lambda | S3 + DynamoDB | S3 + CloudFront | Optional | Heavy usage |
| 4 (Multi-tenant) | Same as Phase 3 | S3 (tenant-prefixed) + DynamoDB | S3 + CloudFront | Cognito | Multiple teams |

### Cost Estimates (Phase 2)

Rough monthly costs for a small team (10 users, ~500 generation batches/month). See the **AWS Bedrock Pricing & Cost Breakdown** section above for detailed per-operation costs.

| Service | 5×5 Nova Canvas (no upscale) | 3×3 Titan (no upscale) |
|---------|------------------------------|------------------------|
| App Runner (1 instance) | ~$30/month | ~$30/month |
| S3 (50GB) | ~$5/month | ~$5/month |
| Claude (prompts + concepts) | ~$27/month | ~$5/month |
| Image generation | ~$750/month | ~$45/month |
| Remove Background | ~$875/month | ~$315/month |
| **Total** | **~$1,687/month** | **~$400/month** |

> **Biggest cost levers**: Image model choice (Titan at $0.01 vs Ultra at $0.14 = 14× difference), batch size (3×3 = 9 images vs 5×5 = 25 = 2.8× difference), and Creative Upscale ($0.60/image — only use on final selected assets).
