# ArtSmoker

AI-powered 2D game asset generation platform. Generate game-ready sprites, characters, icons, environments, and marketing banners from text or voice prompts — styled to match your game's visual identity.

Built on AWS Bedrock (Claude, Nova Canvas, Titan Image, Stability AI).

## What it does

1. **Upload your game's art** — drop in reference images from your existing assets.
2. **AI learns your style** — Claude Opus analyzes the visual DNA (palette, perspective, rendering, mood).
3. **Describe what you need** — type or speak a prompt like "hospital building" or "fire mage character".
4. **Get multiple options** — the system generates up to 5 distinctly different creative concepts, each with up to 5 seed variations (25 images total). Pick the one you like.
5. **Download game-ready files** — PNG with transparent background + SVG, named descriptively (e.g. `hospital-building_opt2_var3.png`).

### Two-level generation

For each prompt, Claude Opus creates **Options** — fundamentally different design interpretations (e.g. for "a warrior": Viking berserker, Japanese samurai, tribal fighter, cyber-soldier, Greek hoplite). For each option, the image model produces **Variations** — different random seeds giving subtle visual differences. This gives artists a broad creative palette to choose from.

### Asset type awareness

The same prompt produces structurally different images depending on the selected asset type:

| Type | What you get |
|------|-------------|
| Game Asset | Single isolated object, centered, transparent background, clean edges |
| Character | Full-body design, expressive pose, readable silhouette |
| Icon | Bold single symbol, high contrast, reads at 64px |
| Marketing Banner | Full scenic illustration, text-safe zone, cinematic composition |
| Environment | Layered landscape with depth, atmosphere, and mood |

## Prerequisites

**Python 3.11+** and **AWS credentials** with Bedrock access.

Your machine needs working AWS credentials — whatever you use for other AWS work will work here. Verify with:

```bash
aws sts get-caller-identity
```

In the AWS Console, enable these models under **Amazon Bedrock > Model access**:

| Region | Models to enable |
|--------|-----------------|
| us-west-2 | Claude Sonnet 4.6, Claude Opus 4.6, Stability AI (Remove BG, Upscale) |
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
3. Pick an asset type, dimensions, and how many options/variations you want.
4. Click **Generate**.
5. Browse the options row (different concepts) and variations row (seed variants).
6. Click any image to preview full-size, then download PNG or SVG.

### Use a style profile

1. Go to the **Style Library** tab.
2. Create a style and upload reference images from your game (or use directory import via the API).
3. Click **Analyze** — Claude extracts the visual style.
4. Back in Generator, select your style from the dropdown — all generated assets will match it.

### Voice input

Click the microphone button next to the prompt editor to dictate your prompt. The audio is sent to Nova Sonic for transcription.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python), boto3 |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| AI | Claude Sonnet/Opus 4.6, Nova Canvas, Titan Image v2, Stability AI, Nova Sonic |
| Storage | Local filesystem (S3-ready interface) |

No build step required for the frontend.

## API

Interactive docs at **http://localhost:8000/docs** (Swagger UI).

Key endpoints:

| Endpoint | Purpose |
|----------|---------|
| `POST /api/generate/` | Generate assets (options x variations) |
| `POST /api/styles/` | Create a style profile |
| `POST /api/styles/{id}/import-directory` | Bulk-import reference images from a local folder |
| `POST /api/styles/{id}/analyze` | Trigger AI style analysis |
| `POST /api/refine-prompt/` | Preview a refined prompt |
| `POST /api/transcribe/` | Voice-to-text |
| `GET /api/gallery/` | Browse generated assets |
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
