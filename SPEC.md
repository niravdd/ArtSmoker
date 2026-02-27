# ArtSmoker — AI-Powered Game Asset Generation Platform

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
    +-- Two-tier generation UI (options × variations)
    +-- Generated asset gallery with export
    |
    v
FastAPI Backend (Python)
    |
    +-- /api/styles        — CRUD for style profiles + directory/S3 import
    +-- /api/generate       — Two-level asset generation pipeline
    +-- /api/transcribe     — Voice-to-text via Nova Sonic
    +-- /api/refine-prompt  — LLM prompt improvement (preview)
    +-- /api/gallery        — Generated asset browsing + file serving
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
│   │   ├── style_analyzer.py      # Claude Opus: multi-image style analysis → profile
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
│   │   │   ├── Generator.js       # Two-tier generation UI (options + variations)
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
2. User uploads 1-10 reference images via file upload or **directory import** (bulk import from a local folder path or S3 prefix).
3. Claude Opus 4.6 (vision) analyzes all images together via `analyze_style(style_id, user_hints)`, extracting structured style attributes as JSON. The analysis is **context-aware** — Claude sees both the images AND the user's existing `generation_hints` (passed as "Artist's Guidance") so it understands the user's intent.
4. Claude Sonnet 4.6 distils the analysis into a concise `generation_hints` paragraph (max 120 words) via `generate_hints(style_id, analyzed_style, user_hints)`, also receiving the user's guidance as context.
5. Profile is cached as `profile.json` inside `data/styles/{style_id}/`.
6. User can manually edit/refine the profile.
7. Profile's `generation_hints` are incorporated into every generation prompt.
8. **Auto re-analysis**: Style analysis is automatically re-triggered when (a) reference images are uploaded via the upload endpoint, or (b) `generation_hints` are changed via PATCH and the new value differs from the previous one. Both paths use a shared `_auto_reanalyze()` helper.

**Directory/S3 import**: The `POST /api/styles/{id}/import` endpoint accepts a local directory path or S3 prefix. Body: `{ "path": "...", "auto_analyze": true }`. It scans **recursively** (using `rglob`) for all image files (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif) in all subdirectories. **Local imports use symlinks** (not copies) to avoid disk duplication. S3 imports download files to the references folder; the S3 client paginates through all objects (handles >1000 keys). Browser uploads copy files normally. Filenames from different subdirectories are **deduplicated** by prefixing with the parent directory name when collisions are detected. The total reference image count is capped at `max_reference_images` (default 10). Optionally auto-triggers Claude Opus style analysis after import.

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

**DOM caching router**: Views survive navigation. Each view's DOM is cached and shown/hidden instead of destroyed/recreated on route changes. `window.resetView(route)` destroys the cache for a specific view to force a fresh start.

**No-cache middleware**: During development, frontend static files are served with no-cache headers to ensure changes are reflected immediately.

**Client-side error logging**: All toast errors/warnings and unhandled JS errors are sent to `POST /api/log` and logged server-side with a `[CLIENT]` prefix for unified debugging.

**Style Library** — Grid of style profiles with thumbnails. Upload new styles, upload reference images, trigger AI analysis.
- **Create modal**: Includes "Import References From" section with Local and S3 browse buttons for importing reference images at creation time.
- **Detail view**: Has an "Import & Analyze" button (always auto-analyzes after import, no toggle). The analysis button is contextual: "Analyze Style" when no analysis exists, "Re-Analyze Style" when one does.
- **Server-side file browser modal**: Used for both local and S3 browsing. Single-click selects a file/folder, double-click navigates into a directory. Back button and ".." entry navigate to the parent directory.

**Generator** — The main workspace with a two-tier result display:
- **Left sidebar**: Art style selector, asset type, image model, dimensions (size presets: 512x512, 768x768, 1024x1024, 1024x576, 576x1024, 1280x720), options count (1-5, default 5), variations count (1-5, default 5), toggle switches for background removal, SVG conversion, and upscaling.
- **Center panel**: Prompt editor (text + voice input), Generate button (indigo) and Reset button (amber) at equal width. After generation, shows both the original prompt and the AI-improved prompt. `loadBatch(batchId)` method restores a previous batch from the Gallery into the Generator view.
- **Options row** (indigo/accent borders): Shows different creative concepts as thumbnail cards. Each card shows the first variation as a preview, the option number badge, and a truncated concept prompt. Click to select an option.
- **Concept prompt display**: Shows the full refined prompt for the selected option.
- **Variations row** (emerald borders): Shows seed variants of the selected option. Click to select a variation.
- **Main preview**: Large preview of the selected variant with checkerboard transparency background.
- **Download bar**: Shows the smart filename (e.g. `a-fierce-dragon_opt1_var2.png`) and provides PNG + SVG download buttons using the human-readable filenames.

If there is only one option, the options row is hidden. If there is only one variation, the variations row is hidden.

**Gallery** — Grid of all generated assets sorted newest-first. Images load immediately (no IntersectionObserver). Backend maintains an in-memory metadata cache for fast listing. Supports pagination via `limit` and `offset` query parameters. Filter by style and asset type. Click to preview/download. Auto-refreshes via `onShow()` when navigating back to the Gallery view.

**AssetViewer** — Full-size preview + download. Fetches full metadata from `GET /api/gallery/{id}` on open. Displays all available fields: original prompt, AI-improved prompt, generation prompt, style, asset type, image model (with friendly labels), dimensions, seed, batch ID, option/variation index, filename, and creation date. Includes a "Reload in Generator" button that sends the batch back to the Generator view.

### 7. Technology Choices

| Component | Technology | Reason |
|-----------|-----------|--------|
| Backend | FastAPI (Python 3.11+) | Async, fast, Pydantic models, auto-docs |
| Frontend | Vanilla JS + Tailwind CSS | No build step, fast to iterate, lightweight |
| AI Models | Bedrock (boto3) | Nova Canvas, Titan Image, SD 3.5 Large, Stable Image Ultra, Claude, Nova Sonic, Stability |
| SVG Conversion | vtracer (primary), potrace (fallback), Pillow (last resort) | Cascade of vector tracing methods |
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

Each step is independently fault-tolerant — failures are logged but do not abort the pipeline.

### 10. Storage Layer

`LocalStore` (`backend/storage/local_store.py`) provides an S3-compatible interface over the local filesystem:

**Style storage** (`data/styles/{style_id}/`):
- `profile.json` — serialized StyleProfile.
- `references/` — uploaded reference images. Local directory imports are stored as **symlinks** to avoid disk duplication; S3 downloads and browser uploads are stored as copies.

**Key methods**:
- `link_reference_image(style_id, filename, source_path)` — creates a symlink in the style's references folder pointing to the source file. Used by the local directory import path.

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
| POST | `/api/styles/{id}/references` | Upload reference images (multipart file upload). Enforces max_reference_images limit (default 10). Auto-triggers re-analysis after upload. |
| GET | `/api/styles/{id}/references/{filename}` | Serve a reference image file. |
| POST | `/api/styles/{id}/import` | Import image files from a local directory path or S3 prefix. Body: `{ "path": "/path/to/images", "auto_analyze": true }`. Scans recursively for all image files in subdirectories. Local imports use symlinks (not copies). S3 imports download files (paginates through >1000 keys). Filenames are deduplicated by prefixing with parent directory name. Optionally triggers style analysis after import. |
| POST | `/api/styles/{id}/analyze` | Trigger AI style analysis on reference images. Claude Opus analyzes images (context-aware, receives existing generation_hints as "Artist's Guidance"), Claude Sonnet generates hints. Both are persisted to the profile. |

### Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate/` | Generate assets (full two-level pipeline). Returns `GenerationResult` with options and variants. |

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
| GET | `/api/gallery/` | List generated assets. Supports query params: `style_id`, `asset_type`, `limit` (default 100, max 500), `offset` (default 0). Returns list of `GalleryItem`, sorted newest-first. Uses in-memory metadata cache. |
| GET | `/api/gallery/{id}` | Get the full metadata dictionary for a generated asset. |
| GET | `/api/gallery/{id}/png` | Download the PNG file. `Content-Disposition` header uses the smart filename (e.g. `prompt-slug_opt1_var2.png`). |
| GET | `/api/gallery/{id}/svg` | Download the SVG file. `Content-Disposition` header uses the smart filename. |
| GET | `/api/gallery/batch/{batch_id}` | Reconstruct the full options x variations structure for a batch. Used to reload a previous batch into the Generator view. |

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

Infrastructure settings live in `backend/config.py` with sensible defaults that work out of the box. Model IDs, regions, and paths are all preconfigured and rarely need overriding. If needed, any setting can be overridden via an environment variable prefixed with `ARTSMOKER_` — see `backend/config.py` for the full list. Image generation model ID settings include:
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
5. **Generate assets**:
   - Enter a prompt like "hospital building", select the style, choose asset type.
   - Set options to 3 and variations to 3 (9 total images) for a quick test.
   - Click Generate — verify the options row shows 3 distinct concept designs.
   - Click an option — verify the variations row shows 3 seed variants with emerald borders.
   - Click a variation — verify the main preview updates and the download bar shows the smart filename.
6. **Download files**: Click PNG/SVG download buttons — verify the file is named with the prompt slug (e.g. `hospital-building_opt2_var1.png`).
7. **Test voice input**: Record audio — verify transcription appears in the prompt editor.
8. **Test prompt refinement**: Type a brief prompt, click "Improve" — verify the refined prompt is more detailed.
9. **Test marketing banner**: Set asset type to "Marketing Banner" and generate — verify the result is a scenic composition, not an isolated sprite.
10. **Browse gallery**: Switch to Gallery view — verify generated assets appear with filtering by style and asset type.
11. **Verify API docs**: Visit `http://localhost:8000/docs` — verify all endpoints are documented.

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

Rough monthly costs for a small team (10 users, ~500 generation batches/month at 5×5):

| Service | Estimated Cost |
|---------|---------------|
| App Runner (1 instance, 1 vCPU, 2GB) | ~$30/month |
| S3 (50GB storage + transfers) | ~$5/month |
| Bedrock — Claude Opus (500 concept generations) | ~$15-25/month |
| Bedrock — Claude Sonnet (prompt refinement, style analysis) | ~$5-10/month |
| Bedrock — Nova Canvas (12,500 images) | ~$500-1000/month |
| Bedrock — Stability AI (background removal, upscale) | ~$250-500/month |
| **Total** | **~$800-1,600/month** |

> The dominant cost is image generation. Reducing the default from 5×5 (25 images) to 3×3 (9 images) cuts Bedrock image costs by ~64%. Post-processing (background removal, upscale) is optional and can be toggled off to save further.
