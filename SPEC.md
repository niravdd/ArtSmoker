# ArtSmoker — AI-Powered Game Asset Generation Platform

## Context

Build a web-based platform that generates 2D game assets and marketing materials using AWS Bedrock AI models. The platform accepts text or voice prompts, learns visual styles from user-uploaded reference art, and produces game-ready assets (PNG + SVG). It is designed to be generic and scalable — any game studio can upload their art theme and generate consistent new assets.

## Architecture Overview

```
Browser (React + Tailwind)
    |
    +-- Voice input (Web Speech API → Nova Sonic for high-quality transcription)
    +-- Text input with inline LLM prompt improvement
    +-- Style library management (upload, browse, edit)
    +-- Generated asset gallery with export
    |
    v
FastAPI Backend (Python)
    |
    +-- /api/styles       — CRUD for style profiles
    +-- /api/generate      — Asset generation pipeline
    +-- /api/transcribe    — Voice-to-text via Nova Sonic
    +-- /api/refine-prompt — LLM prompt improvement
    +-- /api/gallery       — Generated asset history
    |
    v
AI Pipeline (AWS Bedrock)
    |
    +-- Claude Sonnet 4.6     — Fast tasks: prompt refinement, inline improvement, quick analysis
    +-- Claude Opus 4.6       — Complex tasks: deep style analysis, multi-image reasoning, marketing copy
    +-- Nova Canvas            — Primary image generation (text-to-image, image conditioning)
    +-- Titan Image v2         — Alternative image generation
    +-- Stability AI           — Background removal, upscaling
    +-- Nova Sonic             — Speech-to-text transcription
    |
    v
Storage (Local filesystem initially, S3-ready)
    +-- /styles/           — Style profiles + reference images
    +-- /generated/        — Output assets (PNG + SVG)
```

## Project Structure

```
ArtSmoker/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, startup
│   ├── config.py                  # AWS config, model IDs, paths
│   ├── routers/
│   │   ├── styles.py              # Style profile CRUD endpoints
│   │   ├── generate.py            # Asset generation endpoints
│   │   ├── transcribe.py          # Voice transcription endpoint
│   │   ├── refine.py              # Prompt refinement endpoint
│   │   └── gallery.py             # Generated asset browsing
│   ├── services/
│   │   ├── style_analyzer.py      # Claude Opus: deep multi-image style analysis → profile
│   │   ├── prompt_engineer.py     # Claude Sonnet: user prompt → detailed generation prompt
│   │   ├── image_generator.py     # Nova Canvas / Titan Image: generate images
│   │   ├── post_processor.py      # Stability AI: bg removal, upscale; potrace: SVG
│   │   ├── transcriber.py         # Nova Sonic: speech-to-text
│   │   └── bedrock_client.py      # Shared Bedrock client with connection pooling
│   ├── models/
│   │   ├── style_profile.py       # Pydantic models for style profiles
│   │   ├── generation_request.py  # Pydantic models for generation requests
│   │   └── generation_result.py   # Pydantic models for results
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
│   │   │   ├── Generator.js       # Main generation interface
│   │   │   ├── VoiceInput.js      # Voice recording + transcription
│   │   │   ├── PromptEditor.js    # Text input with inline LLM refinement
│   │   │   ├── Gallery.js         # Generated assets grid
│   │   │   └── AssetViewer.js     # Full-size preview + download
│   │   └── services/
│   │       └── api.js             # Backend API client
│   └── assets/                    # Static assets (icons, etc.)
├── data/
│   ├── styles/                    # User-uploaded style profiles + reference images
│   └── generated/                 # Output assets
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

**Workflow:**
1. User uploads 3-10 reference images
2. Claude Opus 4.6 (vision) analyzes all images together, extracts the style profile
3. Profile is cached as JSON for fast reuse
4. User can manually edit/refine the profile
5. Profile's `generation_hints` are prepended to every generation prompt

### 2. Asset Generation Pipeline

```
User prompt: "hospital building"
         |
         v
    [Prompt Refinement — Claude Sonnet 4.6 (fast)]
    Combines: style.generation_hints + user prompt + asset-type context
    Output: "Isometric low-poly hospital building, flat shading, white and red color
             scheme, cross symbol on roof, cheerful Kenney style, transparent background,
             centered, single object, game-ready sprite, 512x512"
         |
         v
    [Image Generation — Nova Canvas]
    Input: refined prompt + optional reference image (style conditioning)
    Output: PNG image (512x512 or 1024x1024)
         |
         v
    [Post-Processing]
    1. Background removal (Stability AI Remove Background)
    2. Upscale if needed (Stability AI Creative Upscale)
    3. SVG conversion (potrace or vtracer)
         |
         v
    Output: game-ready PNG (transparent) + SVG
```

### 3. Marketing Asset Pipeline

Same core pipeline but with different prompt engineering:

```
User prompt: "Winter Holiday Event"
         |
         v
    [Marketing Prompt — Claude Opus 4.6 (complex)]
    Combines: style profile + event theme + marketing best practices
    Output: "Wide banner, 1200x630, winter holiday theme in Kenney low-poly style,
             snowy city scene, festive decorations, warm lighting, text area on left,
             game title placeholder, event dates area"
         |
         v
    [Image Generation — SD 3.5 Large or Nova Canvas]
    Higher resolution, wider aspect ratios for banners
         |
         v
    [Post-Processing]
    Upscale, format for target platform (social media, app store, etc.)
```

### 4. Voice Input (Nova Sonic)

- Browser captures audio via MediaRecorder API
- Audio sent to backend `/api/transcribe`
- Nova Sonic transcribes speech to text
- Transcribed text displayed in prompt editor
- User can edit, then trigger LLM refinement

### 5. Frontend Design

Clean, modern UI with three main views:

**Style Library** — Grid of style profiles with thumbnails. Upload new styles. Click to view/edit.

**Generator** — The main workspace:
- Left panel: style selector + prompt input (text + voice button)
- Center: generation preview with loading states
- Right panel: output options (format, size, asset type)
- Inline prompt refinement: user types → "Improve" button → Claude Sonnet 4.6 suggests refined prompt → user accepts/edits

**Gallery** — Grid of all generated assets. Filter by style, date, type. Click to preview/download.

### 6. Technology Choices

| Component | Technology | Reason |
|-----------|-----------|--------|
| Backend | FastAPI (Python 3.11+) | Async, fast, Pydantic models, auto-docs |
| Frontend | Vanilla JS + Tailwind CSS | No build step, fast to iterate, lightweight |
| AI Models | Bedrock (boto3) | Nova Canvas, Titan Image, Claude, Nova Sonic, Stability |
| SVG Conversion | vtracer (Rust CLI) or potrace | High-quality bitmap-to-vector |
| Storage | Local filesystem | Simple start, S3-compatible interface for later |

### 7. AWS Model Configuration

**Claude Model Selection Logic:**
- **Sonnet 4.6** (fast) — prompt refinement, inline improvement suggestions, quick text tasks
- **Opus 4.6** (complex) — deep multi-image style analysis, comprehensive marketing copy, complex reasoning

The `bedrock_client.py` exposes `invoke_claude(prompt, complexity="fast"|"complex")` which routes to the appropriate model.

| Model | ID | Region | Purpose |
|-------|----|--------|---------|
| Claude Sonnet 4.6 | `anthropic.claude-sonnet-4-6-20250514-v1:0` | us-west-2 | Fast: prompt refinement, inline improvement |
| Claude Opus 4.6 | `anthropic.claude-opus-4-6-20250514-v1:0` | us-west-2 | Complex: style analysis, marketing copy |
| Nova Canvas | `amazon.nova-canvas-v1:0` | us-east-1 | Primary image generation |
| Titan Image v2 | `amazon.titan-image-generator-v2:0` | us-east-1 | Alternative image generation |
| Stability Remove BG | `stability.stable-image-remove-background-v1:0` | us-west-2 | Background removal |
| Stability Upscale | `stability.stable-creative-upscale-v1:0` | us-west-2 | Image upscaling |
| Nova Sonic | `amazon.nova-2-sonic-v1:0` | us-east-1 | Speech-to-text |

> Note: If Sonnet/Opus 4.6 model access is pending in Bedrock, the system falls back to Claude 3.5 Sonnet v2 (`anthropic.claude-3-5-sonnet-20241022-v2:0`) automatically.

## Implementation Phases

### Phase 1: Core Backend + Minimal Frontend
1. FastAPI app skeleton with config
2. Bedrock client service (shared, connection-pooled)
3. Style profile CRUD (upload images, Claude analyzes, cache profile)
4. Basic generation endpoint (prompt → Claude refine → Nova Canvas → PNG)
5. Minimal frontend: style upload + text prompt + image display

### Phase 2: Full Pipeline
6. Background removal post-processing
7. SVG conversion
8. Prompt refinement endpoint (inline improvement)
9. Gallery with generated asset history
10. Marketing asset generation (banners, different sizes)

### Phase 3: Voice + Polish
11. Nova Sonic voice transcription
12. Voice input UI component
13. Frontend polish (animations, responsive, error states)
14. Multiple image generation models (user selects Nova Canvas vs Titan vs SD)

## API Reference

### Styles
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/styles/` | Create a new style profile |
| GET | `/api/styles/` | List all style profiles |
| GET | `/api/styles/{id}` | Get a single style profile |
| PATCH | `/api/styles/{id}` | Update a style profile |
| DELETE | `/api/styles/{id}` | Delete a style profile |
| POST | `/api/styles/{id}/references` | Upload reference images |
| GET | `/api/styles/{id}/references/{filename}` | Serve a reference image |
| POST | `/api/styles/{id}/analyze` | Trigger AI style analysis |

### Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate/` | Generate an asset (full pipeline) |
| POST | `/api/refine-prompt/` | Refine a prompt with AI |

### Voice
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transcribe/` | Transcribe audio to text |

### Gallery
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gallery/` | List generated assets (filterable) |
| GET | `/api/gallery/{id}` | Get asset metadata |
| GET | `/api/gallery/{id}/png` | Download PNG file |
| GET | `/api/gallery/{id}/svg` | Download SVG file |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/docs` | Swagger UI (auto-generated) |

## Verification

1. Start backend: `cd ArtSmoker && source .venv/bin/activate && uvicorn backend.main:app --reload`
2. Open frontend: `http://localhost:8000`
3. Upload Kenney City Builder assets as a style → verify Claude analysis
4. Generate "hospital building" with that style → verify PNG + SVG output
5. Test voice input → verify transcription + prompt flow
6. Test marketing banner generation
7. Verify gallery shows all generated assets

## Configuration

All settings can be overridden via environment variables prefixed with `ARTSMOKER_`:

```bash
export ARTSMOKER_AWS_PROFILE=my-profile
export ARTSMOKER_AWS_REGION_MODELS=us-west-2
export ARTSMOKER_AWS_REGION_IMAGES=us-east-1
```

See `backend/config.py` for the full list of configurable settings.
