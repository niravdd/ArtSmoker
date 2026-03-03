# ArtSmoker

*Smoke-testing your artwork!*

AI-powered 2D game asset generation platform. Generate game-ready sprites, characters, icons, environments, and marketing banners from text or voice prompts — styled to match your game's visual identity. Add text overlays and generate standalone text assets with AI-designed typography.

Built on AWS Bedrock (Claude, Nova Canvas, Titan Image, SD 3.5 Large, Stable Image Ultra, Stability AI).

## What it does

1. **Upload your game's art** — import reference images from local directories (recursive scan, symlinked to avoid duplication) or S3 buckets (recursive listing with pagination, downloaded locally).
2. **AI learns your style** — AI analyzes the visual DNA (palette, perspective, rendering, mood). Analysis is context-aware: if you provide generation hints, the AI receives them as "Artist's Guidance" alongside the reference images, so the analysis understands your intent, not just what's visible.
3. **Describe what you need** — type or speak a prompt like "hospital building" or "fire mage character".
4. **Get multiple options** — the system generates up to 5 distinctly different creative concepts, each with up to 5 seed variations (25 images total). Pick the one you like.
5. **Download game-ready files** — PNG with transparent background + SVG, named descriptively (e.g. `hospital-building_opt2_var3.png`).

### Two-level generation

For each prompt, the AI creates **Options** — fundamentally different design interpretations (e.g. for "a warrior": Viking berserker, Japanese samurai, tribal fighter, cyber-soldier, Greek hoplite). For each option, the image model produces **Variations** — different random seeds giving subtle visual differences. This gives artists a broad creative palette to choose from.

### Asset type awareness

The selected **Asset Type** fundamentally changes how the AI interprets your prompt — not just the image model, but every stage of the pipeline. When you type "hospital" and select different asset types, you get completely different outputs:

| Type | Composition | Framing | Technical Approach |
|------|-------------|---------|-------------------|
| **Game Asset** | Single isolated object on transparent background. No scene, no text, no UI. | Straight-on or isometric, object fills 70-80% of frame. | Clean sharp edges for bg removal, consistent top-left lighting, no ground shadows. Designed to compose with other game assets at various scales. |
| **Character** | Full-body or 3/4-body figure, isolated on clean background. One character only. | Character fills 60-75% vertical, head-to-toe, slightly off-center. | Strong readable silhouette (identifiable from silhouette alone), expressive pose conveying personality, clear facial features and costume details. |
| **Icon** | Single bold recognizable symbol, centered with generous padding. Maximum simplicity. | Front-facing or slight 3/4 tilt, breathing room at edges. | Must read clearly at 64x64 pixels. High contrast, 3-5 colors maximum, bold shapes, no thin lines or fine detail. |
| **Marketing Banner** | Full scenic illustration with dramatic composition. Clean text-safe zone reserved on one side — no rendered text or typography. | Wide cinematic feel, camera pulled back to show a scene. | Rich saturated colors, dramatic lighting (rim light, volumetric rays), depth-of-field. The AI is explicitly instructed NOT to render text; the text-safe zone is left clean for post-production overlay in design tools (Figma, Canva, etc.). |
| **Environment** | Full landscape with foreground/midground/background depth layers, leading lines. | Wide establishing shot, horizon at upper or lower third. | Atmospheric perspective (distant objects lighter/hazier), environmental storytelling through details, mood-setting lighting. |

This matters at every stage:

- **"Improve with AI" button** — When you click Improve, the AI uses the asset type to reshape your brief into a detailed generation prompt, respecting the selected asset type and style. You can review the refined version and accept or revert.
- **Concept generation** — When generating multiple options, the AI creates N different design interpretations that all respect the asset type's structural rules. A Character option always has a readable silhouette; a Marketing Banner option always has a text-safe zone with no rendered text.
- **The result** — Two images from the same prompt but different asset types will look nothing alike. A Game Asset "warrior" is a single centered character sprite. A Marketing Banner "warrior" is an epic battle scene with a clean zone for headline overlay.

## Prerequisites

**Python 3.11+** and **AWS credentials** with Bedrock access.

Your machine needs working AWS credentials — whatever you use for other AWS work will work here. Verify with:

```bash
aws sts get-caller-identity
```

In the AWS Console, enable these models under **Amazon Bedrock > Model access**:

| Region | Models to enable |
|--------|-----------------|
| us-west-2 | Claude Sonnet 4.6, Claude Opus 4.6, SD 3.5 Large, Stable Image Ultra, Stability AI (Remove BG, Upscale) |
| us-east-1 | Nova Canvas, Titan Image v2, Nova Sonic |

Required IAM permissions: `bedrock:InvokeModel` and `bedrock:Converse` (or the managed policy `AmazonBedrockFullAccess`).

## Quick start

```bash
git clone <repo-url> && cd ArtSmoker

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run
uvicorn backend.main:app --reload
```

Open **http://localhost:8000**

### Production deployment (EC2)

Recommended: t3.small (~$15/month) for 1-2 concurrent users.

```bash
gunicorn backend.main:app -w 2 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 --timeout 300
```

Attach an IAM role with `bedrock:InvokeModel` and `bedrock:Converse` permissions.

On startup, the app validates your AWS credentials and Bedrock access. Check the console output or hit `/api/health` to see the status.

## Usage

### Workflow overview

```
                            ┌─────────────────┐
                            │   ArtSmoker      │
                            └────────┬────────┘
                                     │
                      ┌──────────────┼──────────────┐
                      │              │              │
                      ▼              ▼              ▼
              ┌──────────────┐ ┌──────────┐ ┌──────────────┐
              │Style Library │ │2D Image  │ │ Type Studio  │
              │              │ │  Studio  │ │              │
              │ Upload art   │ │ Generate │ │ Add text to  │
              │ Analyze style│ │ images   │ │ images or    │
              │ Set fonts    │ │ from     │ │ standalone   │
              │              │ │ prompts  │ │ text assets  │
              └──────┬───────┘ └────┬─────┘ └──────┬───────┘
                     │              │              │
                     │    ┌─────────┴─────────┐    │
                     │    │  Style selected?   │    │
                     │    │  (optional)        │    │
                     └───►│  Enhances output   │◄───┘
                          └─────────┬─────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    Gallery       │
                          │                 │
                          │ Browse all      │
                          │ Search/filter   │
                          │ Select & delete │
                          └────────┬────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ Download     │ │ Reload   │ │ Add Text     │
            │ PNG / SVG    │ │ in 2D    │ │ in Type      │
            │              │ │ Image    │ │ Studio       │
            │              │ │ Studio   │ │              │
            │              │ │ (refine &│ │ (overlay     │
            │              │ │  regen)  │ │  text)       │
            └──────────────┘ └──────────┘ └──────────────┘
```

**Three entry points, one gallery:**

- **Start with a style** — upload reference art in the Style Library, let AI analyze it, then generate in either studio. The style guides all output.
- **Start without a style** — jump straight into 2D Image Studio or Type Studio. AI uses its best judgement.
- **Start from the Gallery** — pick any previously generated asset and reload it in either studio for refinement, or add text to it, or download it as PNG/SVG.

All generated assets (images, text overlays, standalone text) land in the Gallery. Nothing is overwritten — each generation creates new assets.

### 2D Image Studio (generate assets)

1. Go to the **2D Image Studio** tab.
2. Type a prompt (e.g. "cute cartoon cat").
3. **Select an asset type** — this shapes everything the AI produces (see table above). A "warrior" as a Game Asset looks completely different from a "warrior" as a Marketing Banner.
4. Optionally click **"Improve with AI"** — the AI refines your brief into a detailed generation prompt, respecting the selected asset type and style. Both the original prompt and the AI-improved prompt are tracked and displayed. You can review the refined version and accept or revert.
5. Set dimensions and how many options/variations you want.
6. Configure **Pre-Processing** (applied during generation) and **Post-Processing** (applied after generation, with an "Apply" button). SVG conversion is on by default.
7. Click **Generate**.
8. Browse the **options row** (different concepts) and **variations row** (seed variants of the selected concept).
9. Click any image to preview full-size, then download PNG or SVG.
10. Use the **reset button** (amber circular arrow) to clear generated results and start fresh.

Generation progress is streamed in real time via SSE — the UI shows which image is being generated (e.g. "Generating images... 12/25"), elapsed time, and current pipeline stage. If the API is throttled, you'll see "API throttled — waiting to retry..." with the delay, then "Retrying... (attempt 2/3)" — each image retries up to 3 times with exponential backoff so large batches don't lose variants to transient throttling.

Generated results survive navigation — switching tabs and back preserves the 2D Image Studio's DOM state. Only the reset button clears it.

### Use a style profile

1. Go to the **Style Library** tab.
2. Click **Create New Style** — enter a name and optionally add generation hints. In the create modal, use the **"Import References From"** section with **Local** and **S3** browse buttons to select a source directory or bucket path. Browsing opens a server-side file/directory browser modal (single-click selects an item, double-click navigates into directories). Imported references are auto-analyzed on creation.
3. Local directory imports scan **recursively** through all subdirectories; files are **symlinked** using **relative symlinks** (no duplication, portable across machines — symlinks work as long as source art directories maintain the same relative position to the project). S3 imports list recursively with pagination and **download** files locally. Up to **50 reference images** are imported per style.
4. **Smart sampling for analysis**: When a style has more than 15 references, the analyzer selects a diverse representative subset of 15 for the AI vision call — ensuring coverage across filename groups and file-size diversity. The AI is told how many total images exist vs. how many it is seeing.
5. In the style detail view, use **"Import & Analyze"** to add more references and trigger analysis in one step. Drag-and-drop upload is also supported and **auto re-analyzes** when new images are added.
6. **"Re-Analyze Style"** appears after the initial analysis, letting you manually re-run analysis at any time.
7. **Generation hints** are part of the analysis context — the AI receives both reference images and your hints as "Artist's Guidance" when analyzing, so the style profile understands intent, not just visual appearance. Editing generation hints also triggers **automatic re-analysis**.
8. Back in the **2D Image Studio**, select your style from the dropdown — all generated assets will match its visual identity (palette, perspective, rendering style, mood).

### Type Studio

Add text to images or generate standalone text assets with AI-designed typography.

- **Two modes**: "On Image" composites text onto a gallery image; "Standalone" renders text on a transparent background.
- **Multi-line text editor** with per-line font selection and positioning controls.
- **AI-designed layouts** — the AI suggests colors, sizes, positions, and effects (shadow, outline, glow). Request 1–5 layout options for different creative directions.
- **Font picker with live preview** — style fonts listed first, then global fonts, then system fonts.
- **Pre-Processing / Post-Processing** — same workflow as 2D Image Studio, with an "Apply" button for post-processing. SVG conversion is on by default.
- Results are saved as new gallery assets (originals are never overwritten).

### Gallery

- **Search bar** for instant filtering across all assets.
- **Multi-select** with checkboxes for bulk delete.
- Images load immediately with an in-memory metadata cache. Sorted newest-first.
- Pagination support (limit/offset) for large collections.
- Gallery auto-refreshes when you navigate back to it.
- **Contextual action buttons** per asset based on type: **"2D Studio"** (indigo) to reload in the image studio, **"Add Text"** (emerald) to open in Type Studio, **"Edit in Type Studio"** (purple) for text assets.
- Click any image to open the **AssetViewer** modal with full metadata: original prompt, AI-improved prompt, generation prompt, style, asset type, image model (friendly names), dimensions, seed, batch ID, option/variation index, filename, and creation date.
- **Style snapshot**: Each asset stores a snapshot of the style used at generation time (name, description, hints, analysis). If the original style is later deleted, the asset retains the full context. Backward compatible — older assets without snapshots display normally.

### Voice input

Click the microphone button next to the prompt editor to dictate your prompt. The audio is sent to Nova Sonic for transcription.

### View state preservation

Navigation order: **Style Library → 2D Image Studio → Type Studio → Gallery**. Switching between views preserves each view's DOM state. Generated results, form inputs, and scroll positions survive navigation. The amber reset button in 2D Image Studio is the only way to clear its state.

### Image generation models

Four image models are available, each with different strengths:

| Model | Provider | Quality | Dimension handling |
|-------|----------|---------|-------------------|
| **Nova Canvas** | Amazon | Good, fast | Exact pixel dimensions (width x height) |
| **Titan Image v2** | Amazon | Good, fast | Exact pixel dimensions (width x height) |
| **SD 3.5 Large** | Stability AI | Excellent (best open model) | Aspect ratios (auto-mapped from dimensions) |
| **Stable Image Ultra** | Stability AI | Highest (premium model) | Aspect ratios (auto-mapped from dimensions) |

The Stability AI models (SD 3.5 Large, Stable Image Ultra) accept aspect ratios (1:1, 16:9, 3:2, etc.) instead of exact pixel dimensions. When you select a width and height in the UI, the backend automatically maps to the closest supported aspect ratio.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python), boto3 |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| AI | Claude Sonnet/Opus 4.6, Nova Canvas, Titan Image v2, SD 3.5 Large, Stable Image Ultra, Stability AI, Nova Sonic |
| Storage | Local filesystem (S3-ready interface) |
| Dev | No-cache middleware for static files during development; client-side error logging via `POST /api/log` |

No build step required for the frontend.

## API

Interactive docs at **http://localhost:8000/docs** (Swagger UI).

Key endpoints:

| Endpoint | Purpose |
|----------|---------|
| `POST /api/generate/` | Generate assets (options x variations) |
| `POST /api/generate/post-process` | Apply processing to existing assets |
| `POST /api/styles/` | Create a style profile |
| `POST /api/styles/{id}/import` | Bulk-import references from a local folder or S3 URI |
| `POST /api/styles/{id}/analyze` | Trigger AI style analysis |
| `POST /api/refine-prompt/` | Preview a refined prompt |
| `POST /api/transcribe/` | Voice-to-text |
| `GET /api/gallery/` | Browse generated assets (supports limit/offset pagination) |
| `DELETE /api/gallery/` | Bulk delete assets |
| `POST /api/type-studio/preview` | Render text overlay preview |
| `POST /api/type-studio/suggest` | AI layout suggestion for text |
| `GET /api/type-studio/fonts` | List available fonts |
| `GET /api/browse/local?path=~` | Browse local directory contents |
| `GET /api/browse/s3/buckets` | List available S3 buckets |
| `GET /api/browse/s3?bucket=name&prefix=path` | Browse S3 bucket contents |
| `POST /api/log` | Client-side error/warning logging (recorded as `[CLIENT]` in server console) |
| `GET /api/health` | Health check + AWS status |

## Project structure

```
ArtSmoker/
├── backend/
│   ├── main.py              # FastAPI app + startup validation
│   ├── config.py            # Settings (AWS, models, paths)
│   ├── routers/             # API endpoints
│   ├── services/            # AI pipeline (Bedrock integration)
│   ├── models/              # Pydantic request/response models
│   └── storage/             # Local filesystem (S3-compatible interface)
├── frontend/
│   ├── index.html           # SPA entry point
│   ├── css/styles.css       # Dark theme + animations
│   └── js/
│       ├── components/
│       │   ├── Generator.js     # 2D Image Studio
│       │   ├── TypeStudio.js    # Type Studio
│       │   ├── Gallery.js       # Gallery + asset viewer
│       │   ├── StyleLibrary.js  # Style management
│       │   └── ...              # PromptEditor, VoiceInput, etc.
│       ├── services/            # API client
│       └── app.js               # SPA router + navigation
├── data/
│   ├── styles/              # Style profiles + reference images
│   └── generated/           # Output assets + metadata
├── SPEC.md                  # Full technical specification (rebuild blueprint)
└── README.md                # This file
```

## Configurable limits

Two settings in `backend/config.py` control reference image handling and can be overridden via environment variables:

| Setting | Env Variable | Default | Purpose |
|---------|-------------|---------|---------|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 50 | Max images imported per style |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 15 | Max images sent to AI per analysis call |

Reducing `max_analysis_images` reduces AI vision costs per analysis. Reducing `max_reference_images` limits storage. Both can be tuned based on budget.

## AWS Bedrock Pricing & Cost Breakdown

All pricing from the official [AWS Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/) for US regions. See also [SPEC.md](SPEC.md#aws-bedrock-pricing--cost-breakdown) for monthly team projections and deployment cost estimates.

### Per-unit pricing

| Service | Model | Cost | Unit |
|---------|-------|------|------|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | $3.00 input / $15.00 output | per 1M tokens |
| **Claude Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | $5.00 input / $25.00 output | per 1M tokens |
| **Claude Opus (vision)** | same | ~$0.008 | per 1024x1024 image input |
| **Nova Canvas** | `amazon.nova-canvas-v1:0` | $0.06 | per image (1024x1024 premium) |
| **Titan Image v2** | `amazon.titan-image-generator-v2:0` | $0.01 | per image |
| **SD 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | per image |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | per image |
| **Remove Background** | Stability AI | $0.07 | per image |
| **Creative Upscale** | Stability AI | $0.60 | per image |
| **SVG Conversion** | Local (vtracer/potrace) | $0.00 | free |

### Style analysis cost (one-time per style)

~**$0.14** for a style with 20 reference images (15 sent to Claude Opus after smart sampling).

### Generation cost by batch size

Includes prompt refinement/concept generation + image generation:

| Scenario | Nova Canvas | Titan Image v2 | SD 3.5 Large | Stable Image Ultra |
|----------|------------|----------------|-------------|-------------------|
| 1 option × 1 variation | ~$0.07 | ~$0.02 | ~$0.09 | ~$0.15 |
| 1 option × 5 variations | ~$0.31 | ~$0.06 | ~$0.41 | ~$0.71 |
| 5 options × 5 variations | ~$1.55 | ~$0.30 | ~$2.05 | ~$3.55 |

### Post-processing add-ons (per image)

| Add-on | Per image | 1 image | 5 images | 25 images |
|--------|-----------|---------|----------|-----------|
| Remove Background | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convert to SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> **Creative Upscale note**: Handles Stability AI's 16MB response payload limit automatically by using JPEG output format internally, then converting back to PNG. Includes retry with exponential backoff for API throttling.

### Worked examples

| Example | Configuration | Total Cost |
|---------|-------------|-----------|
| **Cheapest** | 1×1, Titan Image, no processing | ~$0.02 |
| **Standard** | 1×5, Nova Canvas, Remove BG | ~$0.66 |
| **Full exploration** | 5×5, SD 3.5 Large, Remove BG + SVG | ~$3.80 |
| **Premium** | 5×5, Stable Image Ultra, Remove BG + Upscale + SVG | ~$20.30 |

> **Key takeaway**: Image generation itself is cheap ($0.01–$0.14/image). **Creative Upscale at $0.60/image is the dominant cost** — use it selectively on your final chosen assets, not the full batch. Remove Background at $0.07/image is reasonable. SVG conversion is free (runs locally).

## Full specification

See **[SPEC.md](SPEC.md)** for the complete technical specification — architecture, component design, model configuration, API reference, pricing, deployment roadmap, and enough detail to rebuild the project from scratch.
