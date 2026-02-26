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

The selected **Asset Type** fundamentally changes how the AI interprets your prompt — not just the image model, but every stage of the pipeline. When you type "hospital" and select different asset types, you get completely different outputs:

| Type | Composition | Framing | Technical Approach |
|------|-------------|---------|-------------------|
| **Game Asset** | Single isolated object on transparent background. No scene, no text, no UI. | Straight-on or isometric, object fills 70-80% of frame. | Clean sharp edges for bg removal, consistent top-left lighting, no ground shadows. Designed to compose with other game assets at various scales. |
| **Character** | Full-body or 3/4-body figure, isolated on clean background. One character only. | Character fills 60-75% vertical, head-to-toe, slightly off-center. | Strong readable silhouette (identifiable from silhouette alone), expressive pose conveying personality, clear facial features and costume details. |
| **Icon** | Single bold recognizable symbol, centered with generous padding. Maximum simplicity. | Front-facing or slight 3/4 tilt, breathing room at edges. | Must read clearly at 64x64 pixels. High contrast, 3-5 colors maximum, bold shapes, no thin lines or fine detail. |
| **Marketing Banner** | Full scenic illustration with dramatic composition. Text-safe zone reserved on one side. | Wide cinematic feel, camera pulled back to show a scene. | Rich saturated colors, dramatic lighting (rim light, volumetric rays), depth-of-field for visual hierarchy. Publication-ready quality. |
| **Environment** | Full landscape with foreground/midground/background depth layers, leading lines. | Wide establishing shot, horizon at upper or lower third. | Atmospheric perspective (distant objects lighter/hazier), environmental storytelling through details, mood-setting lighting. |

This matters at every stage:

- **"Improve with AI" button** — When you click Improve, Claude uses the asset type to reshape your brief into a detailed generation prompt. The same input "hospital" becomes an isolated sprite prompt for Game Asset, but a cinematic scene prompt for Marketing Banner.
- **Concept generation** — When generating multiple options, Claude Opus creates N different design interpretations that all respect the asset type's structural rules. A Character option always has a readable silhouette; a Marketing Banner option always has a text-safe zone.
- **The result** — Two images from the same prompt but different asset types will look nothing alike. A Game Asset "warrior" is a single centered character sprite. A Marketing Banner "warrior" is an epic battle scene with space for a headline.

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
3. **Select an asset type** — this shapes everything the AI produces (see table above). A "warrior" as a Game Asset looks completely different from a "warrior" as a Marketing Banner.
4. Optionally click **"Improve with AI"** — Claude refines your brief into a detailed generation prompt, respecting the selected asset type and style. You can review the refined version and accept or revert.
5. Set dimensions and how many options/variations you want.
6. Click **Generate**.
7. Browse the **options row** (different concepts) and **variations row** (seed variants of the selected concept).
8. Click any image to preview full-size, then download PNG or SVG.
9. Use the **reset button** (circular arrow) to clear results and start fresh.

### Use a style profile

1. Go to the **Style Library** tab.
2. Click **Create New Style** — enter a name and paste a local directory path or S3 URI (`s3://bucket/prefix`) in the "Import References From" field. The system imports all images and auto-analyzes with Claude Opus.
3. Alternatively, create a style first, then open it and use the drag-and-drop upload zone or the import field to add references, then click **Analyze**.
4. Back in Generator, select your style from the dropdown — all generated assets will match its visual identity (palette, perspective, rendering style, mood).

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
| `POST /api/styles/{id}/import` | Bulk-import references from a local folder or S3 URI |
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
