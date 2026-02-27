# ArtSmoker

AI-powered 2D game asset generation platform. Generate game-ready sprites, characters, icons, environments, and marketing banners from text or voice prompts — styled to match your game's visual identity.

Built on AWS Bedrock (Claude, Nova Canvas, Titan Image, SD 3.5 Large, Stable Image Ultra, Stability AI).

## What it does

1. **Upload your game's art** — import reference images from local directories (recursive scan, symlinked to avoid duplication) or S3 buckets (recursive listing with pagination, downloaded locally).
2. **AI learns your style** — Claude Opus analyzes the visual DNA (palette, perspective, rendering, mood). Analysis is context-aware: if you provide generation hints, Claude receives them as "Artist's Guidance" alongside the reference images, so the analysis understands your intent, not just what's visible.
3. **Describe what you need** — type or speak a prompt like "hospital building" or "fire mage character".
4. **Get multiple options** — the system generates up to 5 distinctly different creative concepts, each with up to 5 seed variations (25 images total). Pick the one you like.
5. **Download game-ready files** — PNG with transparent background + SVG, named descriptively (e.g. `hospital-building_opt2_var3.png`).

### Two-level generation

For each prompt, Claude Opus creates **Options** — fundamentally different design interpretations (e.g. for "a warrior": Viking berserker, Japanese samurai, tribal fighter, cyber-soldier, Greek hoplite). For each option, the image model produces **Variations** — different random seeds giving subtle visual differences. This gives artists a broad creative palette to choose from.

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

- **"Improve with AI" button** — When you click Improve, Claude uses the asset type to reshape your brief into a detailed generation prompt, respecting the selected asset type and style. You can review the refined version and accept or revert.
- **Concept generation** — When generating multiple options, Claude Opus creates N different design interpretations that all respect the asset type's structural rules. A Character option always has a readable silhouette; a Marketing Banner option always has a text-safe zone with no rendered text.
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

On startup, the app validates your AWS credentials and Bedrock access. Check the console output or hit `/api/health` to see the status.

## Usage

### Generate assets (no style)

1. Go to the **Generator** tab.
2. Type a prompt (e.g. "cute cartoon cat").
3. **Select an asset type** — this shapes everything the AI produces (see table above). A "warrior" as a Game Asset looks completely different from a "warrior" as a Marketing Banner.
4. Optionally click **"Improve with AI"** — Claude refines your brief into a detailed generation prompt, respecting the selected asset type and style. Both the original prompt and the AI-improved prompt are tracked and displayed. You can review the refined version and accept or revert.
5. Set dimensions and how many options/variations you want.
6. Click **Generate**.
7. Browse the **options row** (different concepts) and **variations row** (seed variants of the selected concept).
8. Click any image to preview full-size, then download PNG or SVG.
9. Use the **reset button** (amber circular arrow) to clear generated results and start fresh.

Generated results survive navigation — switching to Gallery or Style Library and back preserves the Generator's DOM state. Only the reset button clears it.

### Use a style profile

1. Go to the **Style Library** tab.
2. Click **Create New Style** — enter a name and optionally add generation hints. In the create modal, use the **"Import References From"** section with **Local** and **S3** browse buttons to select a source directory or bucket path. Browsing opens a server-side file/directory browser modal (single-click selects an item, double-click navigates into directories). Imported references are auto-analyzed on creation.
3. Local directory imports scan **recursively** through all subdirectories; files are **symlinked** (no duplication). S3 imports list recursively with pagination and **download** files locally.
4. In the style detail view, use **"Import & Analyze"** to add more references and trigger analysis in one step. Drag-and-drop upload is also supported and **auto re-analyzes** when new images are added.
5. **"Re-Analyze Style"** appears after the initial analysis, letting you manually re-run analysis at any time.
6. **Generation hints** are part of the analysis context — Claude Opus receives both reference images and your hints as "Artist's Guidance" when analyzing, so the style profile understands intent, not just visual appearance. Editing generation hints also triggers **automatic re-analysis**.
7. Back in Generator, select your style from the dropdown — all generated assets will match its visual identity (palette, perspective, rendering style, mood).

### Gallery

- Images load immediately with an in-memory metadata cache. Sorted newest-first.
- Pagination support (limit/offset) for large collections.
- Gallery auto-refreshes when you navigate back to it.
- Click any image to open the **AssetViewer** modal with full metadata: original prompt, AI-improved prompt, generation prompt, style, asset type, image model (friendly names), dimensions, seed, batch ID, option/variation index, filename, and creation date.
- Click **"Reload in Generator"** in the AssetViewer to restore the entire batch — all options, variations, prompts, and settings — for refinement and re-generation.

### Voice input

Click the microphone button next to the prompt editor to dictate your prompt. The audio is sent to Nova Sonic for transcription.

### View state preservation

Switching between Generator, Gallery, and Style Library preserves each view's DOM state. Generated results, form inputs, and scroll positions survive navigation. The amber reset button in Generator is the only way to clear its state.

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
| `POST /api/styles/` | Create a style profile |
| `POST /api/styles/{id}/import` | Bulk-import references from a local folder or S3 URI |
| `POST /api/styles/{id}/analyze` | Trigger AI style analysis |
| `POST /api/refine-prompt/` | Preview a refined prompt |
| `POST /api/transcribe/` | Voice-to-text |
| `GET /api/gallery/` | Browse generated assets (supports limit/offset pagination) |
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
│   └── js/                  # Components + API client
├── data/
│   ├── styles/              # Style profiles + reference images
│   └── generated/           # Output assets + metadata
├── SPEC.md                  # Full technical specification (rebuild blueprint)
└── README.md                # This file
```

## Full specification

See **[SPEC.md](SPEC.md)** for the complete technical specification — architecture, component design, model configuration, API reference, and enough detail to rebuild the project from scratch.
