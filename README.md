# ArtSmoker
> *Smoke-testing your artwork!*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

## 📌 0. Overview

A simple, artist-friendly interface for Amazon Bedrock's image and video generation models. ArtSmoker helps creative teams use Bedrock efficiently — without needing to learn the API, CLI, or prompt engineering.

### 📝 The Problem

Creative teams and game studios want to use AI for asset generation, but face real barriers:

- **No simple interface** — artists shouldn't need to log into the Bedrock console or write API calls to generate images
- **Prompt engineering is hard** — composing effective prompts with proper negative prompts, style directives, and model-specific formatting takes expertise most artists don't have
- **Teams don't build/train their own models** — they need access to the many models already available on Bedrock, through something they can actually use
- **Image editing is inaccessible** — inpainting, outpainting, search & replace, and style transfer all require API knowledge
- **2D-to-3D is a separate pipeline** — getting from a 2D concept to a game-engine-ready textured 3D model normally requires manual modeling, UV unwrapping, and texture painting — or expensive third-party tools

### 📝 The Solution

ArtSmoker is a self-hosted web application that wraps Amazon Bedrock in a clean creative interface — purpose-built for game asset production, with applicability across other creative industries such as advertising, e-commerce, publishing, and digital media where AI-generated visual content is valuable.

- **Artists describe what they need** in plain language — ArtSmoker handles prompt decomposition, enhancement, model-specific optimisation, and style application behind the scenes. A guided Prompt Designer lets users fine-tune individual visual elements (subject, scene, lighting, colours) with lock/vary controls for genuinely distinct creative options
- **Style-aware generation** — upload your game's existing art, and ArtSmoker's vision models learn your visual identity. Every generated asset matches your game's look and feel
- **All Bedrock models, all regions** — fully configurable. Choose your text-to-image models, video models, and regions. The system discovers available models dynamically via the Bedrock API
- **Self-hosted open-source models — 1-click deploy** — browse a curated catalog of pre-tested models (Qwen-Image, HunyuanImage 3.0, FLUX.2, and more), pick a GPU instance, and deploy to Amazon SageMaker with one click. Everything is handled: inference packaging, quantisation, CUDA configuration, auto-scaling, and job tracking. Every catalog model is validated end-to-end before shipping
- **Image-to-3D in one click** — generate a textured 3D model (GLB) directly from any 2D game asset or character image. Multi-view synthesis and texture baking produce game-engine-ready meshes that import directly into Unity, Unreal, or Blender — no manual modeling required
- **Your AWS account, your IP** — everything runs in your own private AWS account. All artwork, prompts, styles, and generated assets stay within your isolated environment — no data leaves to third-party services. You retain full ownership and control of your creative IP

**Amazon Bedrock models**: Claude Sonnet/Opus (prompt engineering & chat), Nova Canvas, Titan Image, Stable Diffusion 3.5 Large, Stable Image Ultra, Stability AI services (image editing), Nova Reel, Luma AI Ray (video generation), and 80+ LLMs from 16 providers for Chat Studio. **Self-hosted models**: Qwen-Image (text-to-image) & Qwen-Image-Edit (reference-guided + instruction editing, Apache-2.0), HunyuanImage 3.0 (BF16/NF4), FLUX.2, FLUX.1, TripoSG & TRELLIS.2 (image-to-3D), and more via Amazon SageMaker — with an extensible catalog for adding new models.

**[Get started now — jump to Prerequisites & Installation ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker supports 8 languages. Switch the UI language using the language buttons in the top navigation bar (EN | 日 | 中 | 한 | हिं | РУ | FR | ES). Your selection is saved automatically.

| Language | README |
|----------|--------|
| English | This document |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | [README.ko.md](README.ko.md) |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français (French) | [README.fr.md](README.fr.md) |
| Español (Spanish) | [README.es.md](README.es.md) |
| Deutsch (German) | [README.de.md](README.de.md) |

**Multi-lingual prompt support:**
- Non-English prompts are automatically detected (Japanese, Chinese, Korean, Hindi, Russian, French, Spanish, and more) and translated to English before generation
- A bilingual preview appears in the prompt area: toggle between your original text and the English translation to see exactly what the model will receive
- The original prompt, detected language, and English translation are all preserved in the asset metadata
- File names are generated from the translated English prompt (so "病院の建物" → `hospital-building_opt1_var1.png`)
- Chat Studio passes prompts directly to the LLM (no translation) since models like Claude are natively multilingual
- Type Studio text stays in your language (it's rendered on the image as-is)
- All moderation pre-checks and content screening work on the translated English prompt for consistency

## 📌 1. What It Does

ArtSmoker works in two modes — **standalone** (no art style or theme setup needed, just describe and generate) and **style-guided** (upload your existing art, and every generation matches your visual identity). Both modes use the same studios and generation pipeline.

### 📝 Standalone Mode (Quick Start)

No style or theme setup needed — open the 2D Image Studio, Video Studio, or Type Studio and start creating immediately.

1. **Describe what you need** — type a prompt like "hospital building" or "fire mage character", or use voice input. The AI decomposes your idea into visual components, enhances it with model-specific optimisations, and respects your creative intent through smart lock/vary controls. Write in any language — non-English prompts are auto-translated.
2. **Choose your models and settings** — multi-select from all available text-to-image models (Amazon Bedrock + self-hosted on SageMaker), pick dimensions, quality tier, and region. Check multiple models for side-by-side comparison, or select one for focused generation. Cost estimate updates live.
3. **Get genuinely different options** — the system generates up to 5 distinctly different creative concepts (varying outfit, mood, lighting, composition — not just camera angle), each with up to 5 seed variations (25 images total). User-specified details are locked; AI-inferred details are varied boldly.
4. **Edit and refine** — use inpainting, outpainting, erase, search & replace, or recolor directly in the Asset Viewer. Each edit creates a new version — the original is always preserved.
5. **Download game-ready files** — PNG with transparent background + SVG, named descriptively (e.g. `hospital-building_opt2_var3.png`). Videos export as MP4.

### 📝 Style-Guided Mode (Match Your Art Style & Theme)

For teams that want every generated asset to match an existing art style — upload reference images and let the AI learn your visual identity first.

1. **Upload your game's art** — import reference images from local directories (recursive scan, symlinked to avoid duplication) or S3 buckets (recursive listing with pagination). **Smart deduplication** runs automatically — removes rotation variants (barrel_N/E/S/W.png keeps only barrel_S.png) and animation frames (Idle0-Idle8 keeps only Idle). For example, a 747-file isometric asset pack deduplicates to ~99 unique objects. Supports: .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg, plus automatic texture extraction from 3D models (.glb, .gltf).
2. **AI learns your style** — two-phase cohesion-aware analysis: first, a quick check determines whether your collection is unified, structurally consistent, or diverse. Then a deep analysis of the full reference set produces a metadata-rich style profile — colour palettes, line weights, lighting patterns, composition rules, and production conventions. If you provide generation hints, the AI receives them as "Artist's Guidance" so the analysis understands your intent, not just what's visible.
3. **Generate with style applied** — when you select a style in the Image Studio, every prompt is automatically enhanced with your style's visual directives. A prompt like "hospital building" becomes a detailed generation instruction that includes your game's colour palette, perspective conventions, and rendering style.
4. **Everything from Standalone mode applies** — multiple options, model comparison, editing, versioning, and game-ready downloads all work the same way, now guided by your art style.

> [!NOTE]
> All generated content is produced by AI models and depends on the prompts and references you provide. Please review the [Disclaimer](#disclaimer) regarding content quality, intellectual property, and applicable service terms before using generated assets in production.

### 📝 1.1 Features at a Glance

- 🎨 **Style Library** — Upload art, AI learns your visual identity
- 🖼️ **2D Image Studio** — Generate images with options x variations, guided 3-step prompt workflow
- 🎨 **Prompt Designer** — AI decomposes your prompt into editable visual components (subject, scene, lighting, colours) with lock/vary toggles per field, style integration, and smart asset type classification. Photorealistic, Character, Environment, and more
- 🎬 **Video Studio** — Text-to-video with model-specific prompt guidance (Nova Reel camera controls, Luma Ray natural language), multi-shot, image-to-video
- ✍️ **Type Studio** — AI-designed text overlays with font picker
- 💬 **Chat Studio** — Multi-model LLM chat with streaming, markdown, code highlighting, vision, sessions, context compaction
- 📁 **Unified Gallery** — Browse images + videos, media filter, search, download, delete
- 📥 **Import Image** — Bring an existing image (any format) into the Gallery as a first-class asset. Auto-converted to PNG, tagged with an asset type you choose, and immediately editable and 3D-ready — everything (versioning, editing, image-to-3D) works exactly as it does for a generated image
- ✏️ **Image Editing** — Inpainting, outpainting, erase, search & replace, recolor (in AssetViewer)
- 🔄 **Real-time progress** — SSE streaming with retry/throttle visibility
- 🛡️ **Smart moderation** — Canary testing, auto model switching, AI-assisted rewriting
- ⚙️ **Model Registry** — Admin UI organized by studio (Image, Video, Chat, Type, Shared), Bedrock discovery, custom model support
- 📝 **Prompt Templates** — 27 editable LLM directive prompts, AI-assisted refinement, variable validation with auto-fix
- 📦 **Asset Versioning** — Edit-in-place with version history (v1, v2, ...) and version navigation
- 💰 **Cost Tracking** — Estimated AWS spend per request, per session, per asset — sent to PulseBoard telemetry
- 🌐 **8-Language i18n** — Full UI translation (EN, JA, ZH, KO, HI, RU, FR, ES), auto-detect non-English prompts, bilingual preview
- 🔍 **Custom Model Support** — Discover fine-tuned, imported, and deployed custom Bedrock models automatically
- 🔧 **Self-Hosted Models — 1-Click Deploy** — Browse a curated catalog of pre-tested open-source models (Qwen-Image, Qwen-Image-Edit, HunyuanImage 3.0, FLUX.2, FLUX.1, TripoSG, TRELLIS.2, and more), pick a GPU instance, and click Deploy. ArtSmoker handles everything: packaging the inference handler, configuring quantisation, selecting the right CUDA toolkit, setting up auto-scaling, registering CloudWatch alarms, and wiring async job tracking. Every model in the catalog has been validated end-to-end — from cold start through generation to gallery delivery — so you don't have to debug GPU drivers, memory overflows, or container compatibility. Supports BF16 + FlashInfer for best quality, NF4 for cost efficiency, multi-GPU auto-detection, auto-scales to zero ($0 idle), and the same model runs on different instance types without reconfiguration
- 🧊 **Image-to-3D Generation** — Convert any Game Asset or Character image into a textured 3D mesh (GLB) with one click. Multi-view synthesis + texture baking produces game-engine-ready assets. Interactive 3D viewer with orbit/zoom/pan
- 🩹 **Smart source completion for 3D** — image-to-3D can only build what's visible, so a cropped character (legs cut off) becomes a legless mesh. Before generating, ArtSmoker vision-checks the source and, if it's cropped, **offers** to complete it via outpainting (an AI-suggested, fully editable prompt) — previews the before/after, re-reviews the result, lets you extend again or discard, and saves it as a new image version. Opt-in and non-blocking; well-framed images generate straight through
- 🔄 **Auto-Update** — Version-gated git pull on startup, self-restart on update, 24h periodic check (`ARTSMOKER_AUTO_UPDATE=false` to disable)

### 📝 1.2 Screenshots

**2D Image Studio** — Settings on the left with multi-select model dropdown, asset type, dimensions, and post-processing options. 3-step prompt workflow on the right with Prompt Designer and Generate Enhanced Prompt buttons. IP declaration and cost estimate at the bottom.

![2D Image Studio — Settings, prompt workflow, and generation controls](docs/images/image-studio-top.png)

**2D Image Studio — Generation Results** — Enhanced prompt shown above, multi-model comparison results below. Each model generates independently with per-model prompt optimization. Results display model name, dimensions, and generation cost.

![2D Image Studio — Enhanced prompt and generation results](docs/images/image-studio-results.png)

**2D Image Studio — Model Comparison** — Side-by-side comparison grid across all selected models (7 models shown). Variations of the selected option displayed below. Post-processing toggles (Remove Background, Convert to SVG, Upscale) on the left.

![2D Image Studio — Multi-model comparison grid with variations](docs/images/image-studio-comparison.png)

**Prompt Designer** — AI decomposes your prompt into editable visual components (Subject, Scene, Composition, Lighting, Style & Colors). Each field can be individually edited with lock/vary controls for genuinely distinct creative options.

![Prompt Designer — Structured visual decomposition with editable fields](docs/images/prompt-designer-top.png)

**Prompt Designer — Color Palette** — Named color palettes with hex swatches, style keywords, and quality level controls. The AI learns your visual identity and applies it consistently across all generations.

![Prompt Designer — Color palette, style keywords, and quality controls](docs/images/prompt-designer-bottom.png)

**Style Library** — Upload your game's existing art, AI analyzes the visual style and produces a metadata-rich prompt guide. Reference images are displayed with the full AI analysis and JSON style profile.

![Style Library — AI style analysis with reference images](docs/images/style-library-top.png)

![Style Library — Reference images, import options, and analysis data](docs/images/style-library-bottom.png)

**Gallery** — Unified view of all generated images and videos with media type filter, style filter, search, and sorting. Click any asset to open the full viewer. The **Import Image** button brings an existing image into the gallery — pick an asset type (Character/Game Asset enable 3D), and it's converted to PNG and made instantly editable and 3D-ready.

![Gallery — Generated assets grid with filters](docs/images/gallery.png)

**Asset Viewer** — Full-size preview with tabbed interface (PNG, Edit, SVG, Metadata, 3D Model). Download PNG and SVG directly. Transparent background compositing shown with checkerboard pattern.

![Asset Viewer — Full-size preview with download options](docs/images/asset-viewer.png)

**Asset Viewer — Image Editing** — Edit tab with inpainting: paint a mask over the area to change, describe what you want, select an editing model, and apply. Version history preserved — originals are never overwritten.

![Asset Viewer — Inpainting with mask and prompt](docs/images/asset-viewer-edit.png)

**3D Model Generation** — Convert any Game Asset or Character image into a textured 3D mesh (GLB). Configure marching cubes resolution, foreground ratio, and generation parameters directly in the Asset Viewer's 3D Model tab.

![3D Model Generation — Settings and generation in the Asset Viewer](docs/images/3d-model-generation.png)

**Video Studio** — Settings on the left (model, generation mode, duration, region, cost estimate), prompt on the right. Supports Nova Reel (single shot, multi-shot auto/manual up to 2 minutes) and Luma AI Ray (aspect ratios, looping).

![Video Studio — Settings and prompt](docs/images/video-studio.png)

![Video Studio — Generation in progress with AI-enhanced prompt](docs/images/video-studio-generating.png)

![Video Studio — Completed video with thumbnail and recent videos](docs/images/video-studio-completed.png)

**Video Player** — Click a video to play it inline with full metadata (original prompt, AI-enhanced prompt, model, duration, region).

![Video Player — Playing a generated video with metadata](docs/images/video-player.png)

### 📝 1.3 Two-Level Generation

For each prompt, the AI creates **Options** — fundamentally different design interpretations (e.g. for "a warrior": Viking berserker, Japanese samurai, tribal fighter, cyber-soldier, Greek hoplite). For each option, the image model produces **Variations** — different random seeds giving subtle visual differences. This gives artists a broad creative palette to choose from.

### 📝 1.4 Multi-Model Selection

The model dropdown supports **checkbox-based multi-select** — pick any combination of models for a single generation run:

- **Single model** — check one model for focused generation (fastest, cheapest)
- **Multiple models** — check 2-3 specific models for targeted comparison (e.g. SD 3.5 + FLUX.2 only)
- **All Available Models** — toggle at the bottom selects/deselects all enabled models for a full side-by-side comparison

Each model runs independently: if stricter models block the prompt, you still get results from models that accepted it, with clear status labels (success, blocked by moderation, or failed) on each option card. The cost estimate updates live as you check/uncheck models.

An optional **"Model-optimized prompts"** toggle tailors the prompt to each model's strengths — prompts are rewritten per model (e.g. quality boosters for SD 3.5, natural language for FLUX.2, concise captions for Nova Canvas).

### 📝 1.5 Reference-Guided Generation

Beyond writing a prompt from scratch, you can generate **from 1–3 reference images plus an instruction** — pick the mode with the segmented control at the top of the Image Studio prompt area:

- **Match the reference** — keep the subject, product, or character from your reference and change the rest (theme, background, wardrobe, lighting) exactly as your instruction says. Ideal for consistent characters or product shots across scenes. This mode runs on a self-hosted instruction editor (Qwen-Image-Edit) and appears **once it's deployed** — if it isn't, ArtSmoker points you straight to deploy it from Custom Models (one click, same flow as the 3D pipelines). Commercial-safe (Apache-2.0).
- **Inspired by the reference** — ArtSmoker's vision AI reads your reference(s) and instruction, writes an enhanced prompt (shown to you first), then generates with your normal text-to-image models. **Always available** — no deployment needed. Great for borrowing a look, palette, or composition without copying the subject.

Both modes require an instruction so you stay in control of what the reference is *for*. Reference-guided generation is separate from the Style Library (which analyzes many images into a reusable style profile) — use it for one-off, image-driven generations.

### 📝 1.6 Video Studio

Generate AI-powered videos and animations from text prompts. Supports **Amazon Nova Reel** (v1.0, v1.1) and **Luma AI Ray** (v2.0).

| Feature | Nova Reel | Luma Ray v2 |
|---------|-----------|-------------|
| **Max duration** | 120s (2 minutes) | 9 seconds |
| **Resolution** | 1280x720 | 720p / 540p |
| **Aspect ratios** | 16:9 only | 7 options (1:1, 16:9, 9:16, etc.) |
| **Image-to-video** | Yes (start frame) | Yes (start + end frame) |
| **Looping video** | No | Yes |
| **Multi-shot control** | Yes (auto + manual) | No |
| **Price** | ~$0.08/sec | ~$1.50/sec |

**How it works:**
1. Select a video model and configure duration, aspect ratio, region
2. Enter a prompt — AI enhances it with cinematic vocabulary, camera movements, and temporal coherence cues
3. Click Generate — the job runs asynchronously via `StartAsyncInvoke`, output goes to your configured S3 bucket
4. Poll status every 5 seconds — on completion, thumbnail is extracted (via ffmpeg) and MP4 is downloaded locally (or streamed from S3)
5. Videos appear in both the Video Studio's "Recent Videos" section and the unified Gallery

**S3 bucket required**: Video generation outputs to S3. You can configure via Video Settings in the UI (browse existing buckets or create new), or create one via CLI:

```bash
# Create an S3 bucket for video storage (replace REGION and YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# For regions other than us-east-1, add the LocationConstraint:
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

Storage mode: download locally (default) or stream from S3 on demand.

**Video prompt enhancement**: The LLM adds camera movements (pan, zoom, dolly, tracking), lighting details, and temporal cues. Since video models don't support negative prompts, avoidance concepts are woven into the positive prompt naturally.

### 📝 1.7 Chat Studio

A full-featured LLM chat interface — like a self-hosted conversational AI, running on your own AWS account with no third-party data access.

**80+ models from 16 providers** — Claude (Sonnet, Opus, Haiku), Amazon Nova, Meta Llama, Mistral, Cohere, Qwen, DeepSeek, Google Gemma, NVIDIA Nemotron, and more. Plus any custom/imported models in your account. All discovered automatically via Sync from AWS.

**Core features:**
- **Streaming responses** — real-time token-by-token rendering via Bedrock ConverseStream
- **Markdown rendering** — headings, bold/italic, lists, tables, blockquotes, horizontal rules
- **Code blocks** — syntax highlighting (highlight.js) with language badge + copy button
- **Per-message metrics** — input/output tokens, latency, estimated cost, model used
- **Context window bar** — visual fill indicator (green/amber/red) with used/max token count
- **Region switching** — each model shows all available regions, pick the closest or cheapest

**Session management:**
- Multiple concurrent sessions with auto-save
- Inline rename, duplicate, delete, search/filter in sidebar
- Export conversations as Markdown
- Session totals: token count, estimated cost, message count

**Advanced features:**
- **System prompt templates** — General Assistant, Coding Expert, Creative Writer, Game Designer, Data Analyst, Technical Writer
- **Vision/multimodal** — drag-drop, file picker, or Ctrl+V paste images for vision-capable models
- **Context compaction** — AI summarizes older messages to free context window space
- **Regenerate** — re-run any AI response with the same prompt
- **Edit & resend** — modify any user message and replay from that point
- **Fork** — branch a conversation from any message into a new session

**Pricing transparency:** model picker shows cost per 1K tokens, pricing info bar shows estimated cost for 10K and 100K token conversations.

### 📝 1.8 Asset Type Awareness

The selected **Asset Type** fundamentally changes how the AI interprets your prompt — not just the image model, but every stage of the pipeline. When you type "hospital" and select different asset types, you get completely different outputs:

| Type | Composition | Framing | Technical Approach |
|------|-------------|---------|-------------------|
| **Game Asset** | Single isolated object on transparent background. No scene, no text, no UI. | Straight-on or isometric, object fills 70-80% of frame. | Clean sharp edges for bg removal, consistent top-left lighting, no ground shadows. Designed to compose with other game assets at various scales. |
| **Character** | Full-body or 3/4-body figure, isolated on clean background. One character only. | Character fills 60-75% vertical, head-to-toe, slightly off-center. | Strong readable silhouette (identifiable from silhouette alone), expressive pose conveying personality, clear facial features and costume details. |
| **Icon** | Single bold recognizable symbol, centered with generous padding. Maximum simplicity. | Front-facing or slight 3/4 tilt, breathing room at edges. | Must read clearly at 64x64 pixels. High contrast, 3-5 colors maximum, bold shapes, no thin lines or fine detail. |
| **Marketing Banner** | Full scenic illustration with dramatic composition. Clean text-safe zone reserved on one side — no rendered text or typography. | Wide cinematic feel, camera pulled back to show a scene. | Rich saturated colors, dramatic lighting (rim light, volumetric rays), depth-of-field. The AI is explicitly instructed NOT to render text; the text-safe zone is left clean for post-production overlay in design tools (Figma, Canva, etc.). |
| **Environment** | Full landscape with foreground/midground/background depth layers, leading lines. | Wide establishing shot, horizon at upper or lower third. | Atmospheric perspective (distant objects lighter/hazier), environmental storytelling through details, mood-setting lighting. |

This matters at every stage:

- **"Preview Enhanced Prompt" button** — When you click Compose, the AI uses the asset type to reshape your brief into a detailed generation prompt, combining your words with style guidelines and asset type directives. Your explicit intent always overrides style defaults. You can review the composed version before generating.
- **Concept generation** — When generating multiple options, the AI creates N different design interpretations that all respect the asset type's structural rules. A Character option always has a readable silhouette; a Marketing Banner option always has a text-safe zone with no rendered text.
- **The result** — Two images from the same prompt but different asset types will look nothing alike. A Game Asset "warrior" is a single centered character sprite. A Marketing Banner "warrior" is an epic battle scene with a clean zone for headline overlay.

### 📝 1.9 3D Model Generation (Image-to-3D)

Generate production-ready, fully-textured 3D meshes from any 2D image — directly in the Asset Viewer. Select a **Game Asset** or **Character** image, open the **3D Model** tab, and click Generate. The result is a game-engine-ready GLB you can orbit, zoom, and download — with no manual modeling, UV unwrapping, or texture painting.

**The generated model — orbit, inspect, download:**

![3D Model Generation — the generated soldier mesh viewed from multiple angles in the interactive 3D viewer](docs/images/3d-model-result.png)

A single 2D character image (left, in the PNG tab) becomes a fully-textured 3D mesh you can rotate freely in-browser. The **3D Model** tab now also lists the exact **models & tools** used to produce each asset (geometry model, texturing backend, output type, instance, and generation parameters) — persisted to the asset's metadata for full provenance.

**Two pipelines — your choice.** ArtSmoker offers two ways to turn an image into a textured 3D model. Deploy either (or both) from Custom Models; when both are live, you pick per generation in the Asset Viewer — each shows its est. cost, time, and licence so you decide informed:

| Pipeline | How it works | Licence | Commercial use | Best for |
|----------|--------------|---------|----------------|----------|
| **TripoSG + texture backend** | TripoSG builds the mesh; a chosen texture backend (TRELLIS.2 / Hunyuan3D-Paint) paints it | per backend (below) | per backend | Mixing geometry + a specific texturer |
| **TRELLIS.2 (Full)** | One model generates **both** geometry and PBR texture (SLAT) | MIT | ✅ Yes — "Built with DINOv3" attribution | Production, commercial assets, simplest path |

**How the TripoSG pipeline works:**

1. **Geometry extraction** — a rectified flow transformer (TripoSG, 1.5B parameters, MIT-licensed) converts a single 2D image into a high-fidelity 3D mesh using a signed distance field (SDF) representation. Mesh density scales with the quality preset (up to ~1M faces at the highest octree resolution) for crisp detail on faces and gear.
2. **Texturing** — the mesh is painted by a **texture backend you choose at deploy time** (default **TRELLIS.2**, Microsoft, MIT — a SLAT/voxel-conditioned texturer producing full PBR materials at a 4096² atlas).
3. **PBR output** — exported as a GLB with embedded PBR maps, ready for physically-based rendering in any modern engine.

The **TRELLIS.2 (Full)** pipeline does the same end-to-end in a single model — no separate texturing step.

**Licence in plain sight — at deploy AND at generate.** Each deployable option shows its **full licence and dependency breakdown** in the deploy dialog — every model it pulls, that model's licence, and whether it's commercial-OK or gated — and you read and accept before deploying. At generate time, the Asset Viewer surfaces the licence again and confirms *"accepted at deploy on `<date>`"* (no second click needed):

| Texture backend | Licence | Commercial use | Best for |
|---------|---------|----------------|----------|
| **TRELLIS.2** *(default)* | MIT | ✅ Yes — requires a "Built with DINOv3" attribution in your product | Production, commercial assets, highest quality |
| **Hunyuan3D-Paint** | Tencent Community | ❌ Non-commercial | Research / non-commercial, exceptional faces |

Background removal (the cutout step) uses **BiRefNet (MIT)** by default — fully commercial-clean — with a non-commercial alternative (RMBG) available as a disclosed opt-in. ArtSmoker never silently pulls a restricted dependency: anything gated or non-commercial is named, badged, and gated behind an explicit acceptance.

**Output:** Standard GLB with embedded PBR textures — imports directly into Unity, Unreal Engine, Blender, and other game engines. The interactive 3D viewer supports orbit, zoom, and pan for immediate inspection, and the **3D Model** tab lists the exact models & tools used (geometry model, texturing backend, dependencies, instance, parameters) for full provenance.

**Infrastructure:** Both pipelines deploy via the same 1-click Custom Models flow, with the deploy-time picker showing each option's licence, dependency table, instance baseline, and est. cost/time. The full TRELLIS.2 pipeline's right-sized baseline is **`ml.g6e.xlarge`** (~$2.61/hr; measured peak ~6.5 GB VRAM + ~22 GB host RAM — host RAM is the binding constraint, not the GPU). Larger `g6e` sizes are offered as RAM-headroom upsells. Endpoints scale to zero when idle — $0 cost between jobs. First cold start builds the CUDA extensions once (then S3-cached for fast restarts). Before deploying a gated model, the dialog **pre-checks HuggingFace access for every repo it pulls** and shows a ✓/✗ per repo with the exact next step — so you never discover a missing licence acceptance minutes into a cold start.

> **Viewing the GLB:** textures are encoded as WebP (`EXT_texture_webp`) to keep files compact — renders perfectly in the in-app viewer, Blender 4.x, three.js, and modern Unity/Unreal importers. macOS Preview/QuickLook doesn't support WebP-in-glTF and will show the model black; use the in-app viewer or any modern glTF tool.

| Metric | Value |
|--------|-------|
| Mesh quality | Up to ~1M faces, full vertex normals |
| Texture resolution | 4096² PBR atlas (base color + metallic-roughness + alpha) |
| Licensing | Commercially-safe by default (TRELLIS.2 MIT + BiRefNet MIT); non-commercial backends offered with full disclosure |
| Supported asset types | Game Asset, Character |

<a id="get-started"></a>

## 📌 2. Prerequisites

- **Python 3.11+** (3.12, 3.13, 3.14 all work)
- **AWS CLI** configured with working credentials
- **IAM permissions** for Bedrock access (see below)

### 📝 2.1 AWS Credentials

ArtSmoker uses [boto3's standard credential resolution](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials), so any of the following methods work:

| Method | Best for | How |
|--------|----------|-----|
| **Environment variables** | CI/CD, containers | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **Shared credentials file** | Local development | `~/.aws/credentials` via `aws configure` |
| **Named profile** | Multiple accounts | Set `ARTSMOKER_AWS_PROFILE=myprofile` or `AWS_PROFILE` |
| **AWS SSO** | Enterprise SSO | `aws configure sso` |
| **IAM Instance Profile** | EC2, ECS, App Runner | Attach an IAM role to the instance — no credentials needed on the machine |
| **ECS Task Role** | ECS/Fargate containers | Assign a task execution role with the required permissions |

Quick check that credentials are working:

```bash
aws sts get-caller-identity
```

> [!NOTE]
> On EC2 and other AWS compute services, you don't need to configure explicit credentials. Attach an [IAM Instance Profile](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html) with the required permissions, and boto3 picks it up automatically via the instance metadata service.

### 📝 2.1.1 Verify Bedrock Access

Confirming credentials work (`sts:GetCallerIdentity`) only verifies identity — it does not confirm you have Bedrock permissions. ArtSmoker uses multiple Bedrock APIs, so a quick listing test alone is not sufficient. The most reliable check:

```bash
# Test 1: Can you list models? (requires bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# Test 2: Can you invoke a model? (requires bedrock:InvokeModel)
aws bedrock-runtime invoke-model --region us-east-1 \
  --model-id amazon.titan-image-generator-v2:0 \
  --content-type application/json --accept application/json \
  --body '{"textToImageParams":{"text":"test"},"imageGenerationConfig":{"numberOfImages":1,"width":512,"height":512}}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# Test 3: Can you use the Converse API? (requires bedrock:Converse)
aws bedrock-runtime converse --region us-east-1 \
  --model-id amazon.titan-text-lite-v1 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# Test 4: Can you list custom models? (requires bedrock:ListCustomModels)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

If Tests 1-3 pass, your core permissions are set. Test 4 is needed only for custom model discovery. If Test 1 passes but Tests 2-3 fail, your IAM policy allows listing but not invoking — update it using the permissions table below.

### 📝 2.2 IAM Permissions

Your IAM user, role, or instance profile needs these permissions:

| Permission | Used for |
|------------|----------|
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
| `bedrock:CreateInference` *(or policy `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** — frontier models reachable only via the Mantle endpoint (OpenAI GPT‑5.x, Claude Mythos, GLM, Grok, Qwen, Gemma…). Missing it affects only those models; Claude via Converse keeps working. |
| `account:ListRegions` | Scan only your account's **enabled** regions during Sync (fast, no errors on opt‑in regions). Optional — falls back to scanning all regions. |
| `account:GetRegionOptStatus` | Read per‑region opt‑in status (companion to `account:ListRegions`). Optional. |
| `s3:CreateBucket` | Create S3 bucket for video storage (optional, via UI) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | Video output storage and retrieval |
| `aws-marketplace:Subscribe` | Auto-subscription on first use of third-party models (incl. third-party Mantle models) |
| `aws-marketplace:ViewSubscriptions` | Check existing model subscriptions |
| `sts:GetCallerIdentity` | Startup credential validation; also underpins the locally-signed Mantle bearer token |
| `pricing:GetProducts` | Fetch model pricing during Sync from AWS (optional) |
| `sagemaker:*` | Self-hosted custom models on Amazon SageMaker (optional — only if using Custom Models) |
| `iam:PassRole` | Allow Amazon SageMaker to use your role (optional — only for Custom Models) |
| `iam:CreateRole` / `iam:AttachRolePolicy` | Auto-create Amazon SageMaker execution role on first deploy (optional — only for Custom Models) |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | Auto-configure existing role for Amazon SageMaker trust (optional) |
| `secretsmanager:CreateSecret` / `secretsmanager:GetSecretValue` / `secretsmanager:DeleteSecret` | Encrypted storage for HuggingFace tokens on gated models (optional — auto-cleaned on teardown) |

**Quickest setup** (managed policies — broadest access):

```bash
# Option A: Attach managed policies to your IAM user (simplest for local development)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Amazon Bedrock Mantle endpoint — needed for frontier models (OpenAI GPT-5.x,
# Claude Mythos, GLM, Grok, etc.). Skip only if you won't use Mantle-only models.
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

# Add S3 access for video storage
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**Scoped setup** (tighter permissions — recommended for production):

```bash
# Create a scoped IAM policy with only the permissions ArtSmoker needs
aws iam create-policy --policy-name ArtSmokerAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Bedrock",
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
      "Sid": "BedrockMantleInference",
      "Effect": "Allow",
      "Action": ["bedrock:CreateInference", "bedrock:GetInference", "bedrock:ListInferences", "bedrock:GetInferenceProfile"],
      "Resource": "*"
    },
    {
      "Sid": "EnabledRegions",
      "Effect": "Allow",
      "Action": ["account:ListRegions", "account:GetRegionOptStatus"],
      "Resource": "*"
    },
    {
      "Sid": "S3VideoStorage",
      "Effect": "Allow",
      "Action": ["s3:CreateBucket", "s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject", "s3:HeadBucket"],
      "Resource": ["arn:aws:s3:::artsmoker-*", "arn:aws:s3:::artsmoker-*/*"]
    },
    {
      "Sid": "Marketplace",
      "Effect": "Allow",
      "Action": ["aws-marketplace:Subscribe", "aws-marketplace:ViewSubscriptions"],
      "Resource": "*"
    },
    {
      "Sid": "Utility",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity", "pricing:GetProducts"],
      "Resource": "*"
    },
    {
      "Sid": "SageMakerCustomModels",
      "Effect": "Allow",
      "Action": [
        "sagemaker:CreateModel", "sagemaker:CreateEndpointConfig", "sagemaker:CreateEndpoint",
        "sagemaker:DeleteModel", "sagemaker:DeleteEndpointConfig", "sagemaker:DeleteEndpoint",
        "sagemaker:DescribeEndpoint", "sagemaker:InvokeEndpoint", "sagemaker:InvokeEndpointAsync"
      ],
      "Resource": "arn:aws:sagemaker:*:*:*artsmoker*"
    },
    {
      "Sid": "SageMakerRoleManagement",
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:AttachRolePolicy", "iam:GetRole", "iam:UpdateAssumeRolePolicy", "iam:PassRole"],
      "Resource": ["arn:aws:iam::*:role/ArtSmoker*"]
    },
    {
      "Sid": "SecretsManagerHFTokens",
      "Effect": "Allow",
      "Action": ["secretsmanager:CreateSecret", "secretsmanager:UpdateSecret", "secretsmanager:GetSecretValue", "secretsmanager:DeleteSecret"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:artsmoker/*"
    }
  ]
}'

# Attach to your IAM user (replace YOUR_ACCOUNT_ID and YOUR_USERNAME)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!TIP]
> **For EC2/ECS/App Runner** — create an IAM role instead of attaching to a user. See the [EC2 Deployment](#43-ec2--cloud-deployment) section for the complete role creation commands. No access keys needed — boto3 auto-discovers the role from the instance metadata service.

> [!NOTE]
> Bedrock models are available by default in all commercial AWS regions — no manual enablement step is needed. On first invocation of a third-party model (Anthropic, Stability AI), AWS automatically initiates a marketplace subscription in the background (requires the `aws-marketplace` permissions above). Anthropic models require a one-time [First Time Use form](https://console.aws.amazon.com/bedrock/home#/modelaccess) completion.

### 📝 2.3 Optional: SVG Conversion Tools

SVG conversion uses external CLI tools (not Python packages). Without them, SVG output falls back to a Pillow-based raster-in-SVG wrapper — functional but not true vector output.

| Tool | Purpose | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **vtracer** | Primary SVG (color vector tracing) | `pip install vtracer` or `cargo install vtracer` | `pip install vtracer` or `cargo install vtracer` | `pip install vtracer` or `cargo install vtracer` or [pre-built binaries](https://github.com/visioncortex/vtracer/releases) |
| **potrace** | Fallback SVG (monochrome tracing) | `brew install potrace` | `sudo apt install potrace` | Download from [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading) |

Verify installation:

```bash
# Check SVG conversion tools
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 Optional: Video Thumbnail & Metadata Tools

Video Studio generates MP4 videos via Amazon Nova Reel and Luma AI Ray. To extract thumbnails (first frame as JPEG) and video metadata (duration, resolution, FPS), **ffmpeg** and **ffprobe** must be installed on the machine running the ArtSmoker backend.

Without ffmpeg:
- Videos still generate and play correctly (streamed from S3 or downloaded as MP4)
- Thumbnails will be missing — the Gallery and Video Studio show a black placeholder instead of a preview image
- Video metadata (duration, resolution) won't be displayed

| Tool | Purpose | macOS | Linux (Debian/Ubuntu) | Windows |
|------|---------|-------|-----------------------|---------|
| **ffmpeg** | Thumbnail extraction + video metadata | `brew install ffmpeg` | `sudo apt install ffmpeg` | Download from [ffmpeg.org/download](https://ffmpeg.org/download.html) or `winget install ffmpeg` |

> [!NOTE]
> `ffprobe` is included with ffmpeg — no separate install needed. ArtSmoker checks for ffmpeg at runtime and falls back gracefully if it's not found — video generation works either way, you just won't get thumbnails.

Verify installation:

```bash
ffmpeg -version 2>&1 | head -1 && echo "ffmpeg: OK" || echo "ffmpeg: not installed (optional)"
ffprobe -version 2>&1 | head -1 && echo "ffprobe: OK" || echo "ffprobe: not installed (optional)"
```

## 📌 3. Installation

### 📝 3.1 macOS

```bash
git clone <repo-url> && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment (system-wide install)
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> On macOS, `python3` and `pip3` are available via Homebrew (`brew install python`) or the Xcode command-line tools. If you see "command not found", install Python from [python.org](https://www.python.org/downloads/) or via `brew install python@3.12`.

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# Install Python if needed
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone <repo-url> && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> On some Linux distros, `pip install` outside a venv requires the `--user` flag or `--break-system-packages` (PEP 668). Using a venv avoids this entirely.

### 📝 3.3 Windows

```powershell
git clone <repo-url>
cd ArtSmoker

# Option A: With virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Option B: Without virtual environment
pip install -r backend\requirements.txt
```

> [!NOTE]
> On Windows, use `python` (not `python3`). Install Python from [python.org](https://www.python.org/downloads/) — check "Add to PATH" during installation. The Type Studio font picker detects fonts from `C:\Windows\Fonts` (system font detection is currently macOS/Linux only — Windows users can use global or style-specific custom fonts).

## 📌 4. Running

### 📝 4.1 Solo Development (All Platforms)

Single-process with auto-reload on file changes — ideal for one developer working locally:

```bash
# With venv (activate first)
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

uvicorn backend.main:app --reload
```

```bash
# Without venv (if installed system-wide)
uvicorn backend.main:app --reload

# Or if uvicorn isn't on PATH
python3 -m uvicorn backend.main:app --reload     # macOS / Linux
python -m uvicorn backend.main:app --reload       # Windows
```

Open **http://localhost:8000** — the frontend is served by FastAPI, no separate web server needed.

On startup, the console shows AWS credential validation results. If something's wrong, you'll see a clear error box. You can also check `http://localhost:8000/api/health` for the status.

### 📝 4.2 Multi-User / Shared Test Box / Production (macOS / Linux)

For any environment with more than one concurrent user — whether a shared dev/test box, staging, or production — use **gunicorn** with multiple workers:

```bash
# Install gunicorn (one-time, in addition to requirements.txt)
pip install gunicorn

# Run with gunicorn (multi-worker, handles concurrent users)
gunicorn backend.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

| Flag | Purpose |
|------|---------|
| `-w 2` | 2 worker processes (increase for heavier load) |
| `-k uvicorn.workers.UvicornWorker` | Use uvicorn's async worker class |
| `--bind 0.0.0.0:8000` | Listen on all interfaces (not just localhost) |
| `--timeout 300` | 5-minute timeout for large batch generations with retries |

> [!TIP]
> **gunicorn** is Linux/macOS only. On Windows, use `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2` for multi-worker serving.

<a id="43-ec2--cloud-deployment"></a>

### 📝 4.3 EC2 / Cloud Deployment

Recommended: **t3.small** (~$15/month) for 1-2 concurrent users.

**Step 1: Create an IAM role for the EC2 instance** (run from your local machine):

```bash
# Create the IAM role with EC2 trust policy
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach the ArtSmoker policy (use the scoped policy from section 2.2, or the managed policy)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create an instance profile and attach the role
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

**Step 2: Launch an EC2 instance** (or attach the profile to an existing one):

```bash
# Attach to an existing running instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**Step 3: Install and run on the instance** (SSH into the instance):

```bash
# Install (one-time)
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone <repo-url> && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# Optional: install ffmpeg for video thumbnails
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**Step 4: Run as a systemd service** (persistent, auto-restarts):

```bash
# Create the service file
sudo tee /etc/systemd/system/artsmoker.service > /dev/null << 'EOF'
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
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable artsmoker
sudo systemctl start artsmoker

# Verify it's running
sudo systemctl status artsmoker

# View logs
sudo journalctl -u artsmoker -f
```

Open **http://YOUR_INSTANCE_IP:8000** — ensure your EC2 security group allows inbound TCP 8000.

### 📝 4.4 First Steps After Setup

After ArtSmoker is running, complete these steps to get the best results:

**1. Sync models from AWS** — Open **Model Settings** (gear icon in any studio) → click **Sync from AWS**. This discovers all available image, video, and chat models across all Bedrock regions. Takes 30-60 seconds. Only needed once, or when AWS adds new models.

**2. Review and customize prompt templates** — This is the most impactful configuration you can do. Open **Model Settings → Prompt Templates** tab. ArtSmoker uses 27 editable directive prompts that control how the AI behaves:

| Template | What it controls |
|----------|-----------------|
| Image Prompt Refinement | How your text descriptions are turned into detailed image generation prompts |
| Multi-Concept Generation | How multiple creative options are generated from a single idea |
| Style Analysis | How reference images are analyzed to learn your art style |
| Content Moderation | How strict the pre-check and rewrite system is |
| Video Enhancement | How video prompts are enriched with camera movements and lighting |
| Text Layout | How Type Studio designs text positioning on images |

Each template can be:
- **Edited directly** — modify the instructions to match your team's needs
- **Enhanced with AI** — select any LLM model, optionally add instructions (e.g., "optimize for pixel art"), and click "Enhance with AI". Review the suggestion, then Accept or Dismiss
- **Reset to default** — restore the original at any time

Templates are organized by studio (Image Studio, Style Library, Content Safety, Video Studio, Type Studio, Chat Studio, Translation) with friendly descriptions of what each one controls.

**Variable safety:** Templates use `{curly_brace}` variables (e.g., `{user_prompt}`, `{model_name}`) that are substituted at runtime. If you accidentally remove a required variable, ArtSmoker will:
1. Block the save and show which variables are missing
2. Offer **"Fix & Save"** — an LLM automatically inserts the missing variables back into your edited text in the right places
3. Verify the fix before saving

All templates are stored in `backend/prompt_templates.json` and self-heal from code defaults if the file is deleted or corrupted.

> [!TIP]
> Start by reviewing the **Image Prompt Refinement** and **Creative Options** templates. These have the biggest impact on output quality. If your team specializes in a particular art style (e.g., pixel art, watercolor, isometric), add those preferences directly into the templates so every generation benefits.

**3. Set up a style profile** (optional) — Go to **Style Library**, create a new style, upload reference images, and click **Analyze**. This teaches ArtSmoker your visual identity.

**4. Choose your language** — Click a language button in the nav bar (EN | JA | ZH | KO | FR | ES) if you prefer a non-English interface.

## 📌 5. Architecture

```
┌─────────────────────────────────────────────┐
│  Browser (SPA)                              │
│  Vanilla JS + Tailwind CSS                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────┐
│  FastAPI Backend (Python)                   │
│                                             │
│  /api/styles      Style CRUD + import       │
│  /api/generate    Two-level generation      │
│  /api/type-studio Text overlay + fonts      │
│  /api/video       Video generation + jobs   │
│  /api/chat        LLM chat + sessions       │
│  /api/gallery     Asset browsing + export   │
│  /api/browse      File/S3 browser           │
│  /api/admin       Model registry + templates│
│  /api/refine-prompt  Prompt + translate      │
│  /api/transcribe  Voice-to-text             │
└────────────┬────────────────────┬───────────┘
             │                    │
             ▼                    ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  us-west-2           │  │  us-east-1               │
│                      │  │                          │
│  Claude Sonnet 4.6   │  │  Nova Canvas             │
│  Claude Opus 4.6     │  │  Titan Image v2          │
│  SD 3.5 Large        │  │  Nova Sonic              │
│  Stable Image Ultra  │  │                          │
│  Stability AI (post) │  │                          │
└──────────────────────┘  └──────────────────────────┘ ... (other regions)
             │
             ▼
┌──────────────────────┐
│  Local Storage        │
│  data/styles/         │
│  data/generated/      │
│  data/video/          │
│  data/chat/           │
└──────────────────────┘
```

## 📌 6. Usage

### 📝 6.1 Workflow Overview

```
                            ┌─────────────────┐
                            │   ArtSmoker     │
                            └────────┬────────┘
                                     │
       ┌───────────┼───────────┼───────────┼───────────┐
       │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼
  ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐
  │  Style   │ │  2D    │ │ Video  │ │   Type   │ │  Chat  │
  │ Library  │ │ Image  │ │ Studio │ │  Studio  │ │ Studio │
  │          │ │ Studio │ │        │ │          │ │        │
  │ Upload   │ │Generate│ │Generate│ │ Add text │ │ Multi- │
  │ Analyze  │ │ images │ │ videos │ │ to imgs  │ │ model  │
  │ Set fonts│ │        │ │        │ │          │ │ LLM    │
  │          │ │        │ │        │ │          │ │ chat   │
  └────┬─────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────────┘
             │              │            │               │
             │    ┌─────────┴────────────┴─────────┐     │
             │    │  Style selected? (optional)    │     │
             └───►│  Enhances output               │◄────┘
                  └─────────┬──────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    Gallery      │
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

**Three entry points, one unified gallery:**

- **Start with a style** — upload reference art in the Style Library, let AI analyze it, then generate in any studio. The style guides all output.
- **Start without a style** — jump straight into 2D Image Studio, Video Studio, or Type Studio. AI uses its best judgement.
- **Start from the Gallery** — pick any previously generated asset and reload it in the appropriate studio for refinement, add text to it, play a video, or download as PNG/SVG/MP4.

All generated assets (images, videos, text overlays, standalone text) land in the unified Gallery. Nothing is overwritten — each generation creates new assets.

### 📝 6.2 Generation Pipeline

```
User prompt: "hospital building"
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Prompt Composition            Claude Sonnet (1 opt) │
│    (optional "Compose" button)   or Opus (2-5 options) │
│    + style + asset type                                │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Canary Test                                         │
│    Single image tests moderation                       │
│    Pass? ──► Full batch    Fail? ──► Model switch      │
│                                  or rewrite suggestion │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Parallel Image Generation                           │
│    Up to 5 options × 5 variations = 25 images          │
│    ThreadPool (3-5 workers)                            │
│    Retry with exponential backoff (3 attempts)         │
│    SSE progress streaming to browser                   │
│    Cooperative cancellation on moderation block        │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Post-Processing (per image, optional)               │
│    Remove Background ──► Stability AI ($0.07/img)      │
│    Upscale ──► Stability AI Creative Upscale ($0.60)   │
│    SVG ──► vtracer / potrace / Pillow (free, local)    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Storage                                             │
│    data/generated/{asset_id}/                          │
│    ├── asset.png (transparent background)              │
│    ├── asset.svg (optional)                            │
│    └── metadata.json (full prompt lineage)             │
│    Smart filenames: prompt-slug_opt1_var2.png          │
└────────────────────────────────────────────────────────┘
```

### 📝 6.3 Content Moderation Flow

```
User clicks Generate
         │
         ▼
┌──────────────────────┐
│ Pre-Check enabled?   │
│ (Prompt Pre-Check    │
│  toggle, on by       │
│  default)            │
└───┬────────────┬─────┘
  Yes            No
    │            │
    ▼            │
┌──────────┐     │
│ Claude   │     │
│ Sonnet   │     │
│ screens  │     │
│ prompt   │     │
└───┬────┬─┘     │
 Issues? No      │
    │    └──────►│
    ▼            │
┌──────────────┐  │
│ Indigo       │  │
│ dialog:      │  │
│ • Switch     │  │
│ • Rewrite    │  │
│ • Proceed    │  │
│ • Cancel     │  │
└──┬───────────┘  │
   │◄────────────┘
   ▼
┌──────────────────────┐
│ Canary test          │
│ (1 image to model)   │
└───┬────────────┬─────┘
 Blocked        Pass
    │            │
    ▼            ▼
┌──────────┐  ┌──────────┐
│ Try alt  │  │ Full     │
│ models   │  │ batch    │
└───┬────┬─┘  │ runs     │
 Works?  No   └──────────┘
    │    │
    ▼    ▼
Emerald    Amber
dialog     dialog
(switch    (rewrite →
 or         enhanced
 rewrite)   prompt area)
```

### 📝 6.4 2D Image Studio (Generate Assets)

The 2D Image Studio uses a guided 3-step workflow:

**Step 1 — Describe your idea**: Type a prompt in the textarea. The placeholder shows a realistic example that changes based on your selected Asset Type (e.g., "A young female warrior in ornate silver armor..." for Character, or "A misty Japanese garden at dawn..." for Environment). Use voice input (mic button) to dictate instead of typing.

**Step 2 — Prompt Designer** *(optional)*: Click **🎨 Prompt Designer** to decompose your prompt into structured visual components. The AI analyzes your prompt and breaks it into editable sections:

- **Subject** — character description, clothing, accessories, pose, expression
- **Scene** — setting, background, props, time of day
- **Composition** — camera angle, framing, depth of field
- **Lighting** — key light, fill/rim light, mood
- **Style & Colors** — art style, quality level, and a named color palette with hex swatches

Each field can be individually edited. **Generate Enhanced Prompt** recomposes your edits into a flat recomposed prompt (shown read-only in Step 2) and then automatically generates the Enhanced AI Prompt for Step 3.

Before the Prompt Designer opens, an **AI asset type classification** runs — if your prompt describes a scene but you selected "Game Asset", a dialog suggests switching to "Environment" or "Character". This ensures the Prompt Designer decomposes with the correct context.

**Step 3 — Enhanced prompt preview** *(optional)*: Click **Generate Enhanced Prompt** to see the model-optimized prompt before generating. The AI takes the recomposed prompt from Step 2 and enhances it with model-specific guidance (anatomy, materials, lighting, prompt structure). You can edit the enhanced prompt before generating. If you used the Prompt Designer in Step 2, this is auto-populated.

**Prompt pipeline**: User Prompt → Decompose → Recompose (`recomposed_prompt`) → Enhance with model guidance (`enhanced_prompt`) → Image Model. For multiple options, the enhancement step generates N distinct interpretations from the same recomposed base. All three levels are stored in metadata.

**Generate**: Click Generate at any point — Steps 2 and 3 are optional. If you skip them, Generate auto-decomposes, recomposes, and enhances your prompt before proceeding. **Prompt Pre-Check** (on by default) screens the prompt for moderation issues before generation.

**Additional controls:**
- **Asset Type** — select in the sidebar. Changes the prompt placeholder and affects how the AI interprets your prompt. The system suggests switching if it detects a mismatch.
- **Art Style** — select a style profile to guide generation with your visual identity.
- **Dimensions, Options, Variations** — configure output size and how many creative concepts to generate.
- **Post-Processing** — Remove Background, Upscale, SVG conversion (applied after generation).
- **IP Declaration** — assert ownership or licensing for strict model compatibility.
- **Model Settings** — view/edit model configuration, discover available Amazon Bedrock models.

Generation progress is streamed in real time via SSE — the UI shows which image is being generated (e.g. "Generating images... 12/25"), elapsed time, and current pipeline stage. If the API is throttled, you'll see "API throttled — waiting to retry..." with the delay, then "Retrying... (attempt 2/3)" — each image retries up to 3 times with exponential backoff so large batches don't lose variants to transient throttling.

Generated results survive navigation — switching tabs and back preserves the 2D Image Studio's DOM state. Only the reset button clears it.

**Smart content moderation**: When your prompt is blocked by a model's content moderation filters, ArtSmoker handles it progressively through three colour-coded dialogs:

- **Indigo (Pre-Check)** — before generation, an AI pre-screens your prompt against the selected model's known sensitivity. If issues are detected, you see the specific concerns and can: switch to a recommended model, **rewrite the prompt** for the current model, proceed anyway, or cancel.
- **Emerald (Model Switch)** — after a generation block, if an alternative model accepts your prompt as-is, ArtSmoker shows which model works and why. One-click to switch. Full attempt log available ("View N model tests").
- **Amber (Rewrite)** — when all models reject, an AI-generated rewrite is offered in an editable textarea with specific issues listed. A verified/unverified badge indicates whether the rewrite passed canary testing.

**Prompt rewrite behaviour**: In all three dialogs, choosing "Rewrite" never overwrites your original prompt. The rewritten version appears in the **enhanced prompt area** below your original text, with a persistent amber disclaimer: *"This rewrite is an attempt to make the prompt compatible — it is still subject to the model's own moderation assessment and may be rejected."* You review and edit the enhanced prompt, then click Generate when satisfied. Your original prompt is always preserved in history and metadata.

Common triggers include copyrighted IP names and character references, violence/weapon language, and adult content references. Tip: the **"Preview Enhanced Prompt"** button often produces prompts that pass moderation naturally, since the AI rephrases in descriptive terms.

**Smart canary testing**: Before generating the full batch, ArtSmoker sends a single "canary" image request to test the prompt against the model's moderation filters. If the canary is blocked, the batch stops immediately (1 wasted API call instead of N×M×3). If the canary passes, remaining tasks run in parallel with cooperative cancellation — if any task hits a moderation block, the rest skip their API calls automatically.

### 📝 6.5 Use a Style Profile

1. Go to the **Style Library** tab.
2. Click **Create New Style** — enter a name and optionally add generation hints. In the create modal, use the **"Import References From"** section with **Local** and **S3** browse buttons to select a source directory or bucket path. Browsing opens a server-side file/directory browser modal (single-click selects an item, double-click navigates into directories). Imported references are auto-analyzed on creation.
3. Local directory imports scan **recursively** through all subdirectories for images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg) and 3D models (.glb, .gltf). Image files are **symlinked** using **relative symlinks** (no duplication, portable across machines). 3D model files (.glb/.gltf) have their embedded textures **automatically extracted** — base64 data URIs, binary buffer chunks, and external texture references are all handled. Extracted textures are saved as copies (prefixed with the model name to avoid collisions). S3 imports list recursively with pagination and **download** files locally. Up to **100 reference images** are imported per style. Supported extensions are centralized in `backend/config.py` (`IMAGE_EXTENSIONS` and `MODEL_EXTENSIONS_WITH_TEXTURES`).
4. **Two-phase cohesion-aware analysis**: Phase 1 sends 8 images to Claude Sonnet to determine cohesion level (high/medium/low) — high means unified style, medium means shared structure with different themes, low means diverse styles. Phase 2 feeds the cohesion assessment to Claude Opus alongside the reference images, guiding it to analyze appropriately for the collection type. When a style has more than 20 references, the analyzer selects a diverse representative subset of 20 for the Opus vision call — ensuring coverage across filename groups and file-size diversity. The AI is told how many total images exist vs. how many it is seeing. The analysis prompt is specifically designed for game assets on transparent backgrounds — asks for material-specific rendering details, proportion system, and shadow/lighting specifics. Extracts 9 style attributes including `materials` (how stone, wood, metal are rendered) and `detail_level` (what surface details are visible vs simplified). Generation hints are expanded to 200 words covering 8 dimensions: perspective, rendering, materials, color palette, proportions, edge treatment, shadow/lighting, detail level, and background — specific enough that generated assets visually blend with existing references.
5. In the style detail view, use **"Import & Analyze"** to add more references and trigger analysis in one step. Drag-and-drop upload is also supported and **auto re-analyzes** when new images are added.
6. **"Re-Analyze Style"** appears after the initial analysis, letting you manually re-run analysis at any time.
7. **Generation hints** are part of the analysis context — the AI receives both reference images and your hints as "Artist's Guidance" when analyzing, so the style profile understands intent, not just visual appearance. Editing generation hints also triggers **automatic re-analysis**.
8. Back in the **2D Image Studio**, select your style from the dropdown — all generated assets will match its visual identity (palette, perspective, rendering style, mood).

### 📝 6.6 Style Analysis Flow

```
┌──────────────────────────────────────────┐
│ Create / Import style                    │
│ (reference images uploaded or imported)  │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 1: Cohesion Check                  │
│ Claude Sonnet — 8 images — ~$0.01        │
│ Determines: high / medium / low          │
│   high   = unified style                 │
│   medium = shared structure, diff themes │
│   low    = diverse collection            │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 2: Full Analysis                   │
│ Claude Opus — up to 20 images            │
│ Guided by cohesion level                 │
│ + Artist's Guidance (user hints)         │
│ Extracts 9 style attributes              │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 3: Hint Generation                 │
│ Claude Sonnet — 200-word hints           │
│ 8 dimensions: perspective, rendering,    │
│ materials, palette, proportions, edges,  │
│ shadow/lighting, detail level            │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Stored in profile.json                   │
│ ~$0.14 total per style analysis          │
│ Used in all future generation            │
└──────────────────────────────────────────┘
```

### 📝 6.7 Type Studio

Add text to images or generate standalone text assets with AI-designed typography.

- **Two modes**: "On Image" composites text onto a gallery image; "Standalone" renders text on a transparent background.
- **Multi-line text editor** with per-line font selection, positioning controls, and **voice input** (mic button per line — dictate text via Nova Sonic transcription).
- **AI-designed layouts** — the AI suggests colors, sizes, positions, and effects (shadow, outline, glow). Request 1–5 layout options for different creative directions. The **LLM model** used for layout is configurable (Complex LLM for best quality, Fast LLM for cheaper) — reads from the registry categories.
- **Font picker with live preview** — style fonts, 8 bundled fonts (Roboto, Open Sans, Lato, Montserrat, Playfair Display, Oswald, Raleway, Source Code Pro), system fonts, and **client-side detected fonts** (via Local Font Access API or canvas probing).
- **Pre-Processing / Post-Processing** — same workflow as 2D Image Studio, with an "Apply" button for post-processing. SVG conversion is on by default.
- **Click to zoom** — clicking the result preview opens the AssetViewer with full zoom/pan, metadata, download, and image editing tools.
- Results are saved as new gallery assets (originals are never overwritten).

### 📝 6.8 Gallery

- **Unified view** of all generated images and videos with a **Media filter** (All / 2D Artwork / Video).
- **Search bar** for instant filtering across all assets (prompts, styles, models).
- **Multi-select** with checkboxes for bulk delete (handles both image and video assets). Deletions are **batch-aware** — surviving siblings track how many variants were removed, so reloading a partial batch in the Image Studio shows "X of Y images remaining (Z deleted)".
- Assets load immediately with an in-memory metadata cache. Sorted newest-first.
- Pagination support (limit/offset) for large collections.
- Gallery auto-refreshes when you navigate back to it, and after any edit or video generation completes.
- **Video cards** display a thumbnail with a play overlay, VIDEO badge, and duration indicator. Click to open the video player modal.
- **Contextual action buttons** per asset based on type: **"2D Studio"** (indigo) to reload in the image studio, **"Add Text"** (emerald) to open in Type Studio, **"Edit in Type Studio"** (purple) for text assets.
- Click any image to open the **AssetViewer** modal with:
  - **Zoom/pan** — mouse wheel to zoom, drag to pan, Fit/1:1 buttons with active mode highlighting.
  - **Edit tab** — inpaint, erase, outpaint, search & replace, or recolor the image directly. Two kinds of editor are offered per mode: **mask-based** (Stability) — paint a mask with the brush tool, enter a prompt, and apply; and **mask-free instruction editors** (Qwen-Image-Edit, when deployed) — just describe the change in words, no mask needed. The brush controls hide automatically for a mask-free model. Choose the editing model, apply; default replaces the original image, uncheck "Replace original" to save as a new asset (every edit preserves version history).
  - **Previous / Next** — arrow buttons and keyboard left/right to navigate through the list without closing the viewer.
  - **Full metadata**: original prompt, AI-improved prompt, generation prompt, negative prompt, style, asset type, image model (friendly names), dimensions, seed, batch ID, option/variation index, IP declaration status, filename, and creation date.
- **Style snapshot**: Each asset stores a snapshot of the style used at generation time (name, description, hints, analysis). If the original style is later deleted, the asset retains the full context. Backward compatible — older assets without snapshots display normally.

### 📝 6.9 Voice Input

Click the microphone button next to the prompt editor to dictate your prompt. The audio is sent to Nova Sonic for transcription.

> [!NOTE]
> Voice transcription requires Nova Sonic's bidirectional streaming API, which depends on a compatible boto3 version and model access enabled in us-east-1. If the streaming API is not available, the service returns a placeholder acknowledgment. Full real-time transcription works when Nova Sonic streaming is properly configured.

### 📝 6.10 View State Preservation

Navigation order: **Style Library → 2D Image Studio → Type Studio → Video Studio → Gallery**. Switching between views preserves each view's DOM state. Generated results, form inputs, and scroll positions survive navigation. The amber reset button in 2D Image Studio and Video Studio is the only way to clear their state.

### 📝 6.11 Model Management

All AI model configuration is centralized in `backend/model_registry.json` — the single source of truth. Models, regions, pricing, quality tiers, and format templates are all stored here and managed through the UI or API:

- Click **"Model Settings"** in the sidebar of any studio to open the admin modal — it opens to the relevant tab for that studio.
- **7 tabs** organized by studio:
  - **Image Studio** — Image generation models (Nova Canvas, Titan, SD 3.5, Ultra), regions, quality tiers, prompt limits, moderation strictness
  - **Video Studio** — Video models (Nova Reel, Luma Ray), S3 bucket settings, regions, pricing
  - **Chat Studio** — Discovered chat/LLM models (80+ from 16 providers), context windows, vision capability, pricing per 1K tokens
  - **Type Studio** — LLM model for text layout generation (Complex or Fast LLM)
  - **Shared Studio** — Cross-studio LLM categories (Fast LLM, Complex LLM, Fallback LLM, Voice), post-processing models (Remove Background, Upscale)
  - **Prompt Templates** — 27 editable LLM directive prompts organized by studio (see section 4.4)
  - **Registry JSON** — Raw JSON editor for the full model registry
- All sections are **collapsible** with **Show All / Hide All** toggles for quick navigation.
- LLM categories and post-processing use **dropdown model pickers** (populated from discovered models) — not raw text fields.
- **Sync from AWS**: Scans all Bedrock-supported AWS regions (discovered dynamically), auto-registers new image, video, and **chat models**, updates regional availability, fetches per-model pricing from the AWS Pricing API, and disables models no longer available. A **live progress overlay** streams each region as it's scanned. This is the **only** action that calls AWS discovery APIs — all other operations read from the cached registry.
- **Always on the newest Claude**: Each Sync automatically rolls your **Fast LLM** to the newest Claude Sonnet and **Complex LLM** to the newest Claude Opus available in your account, so you're never stranded on a deprecated model — no manual config needed. If you manually pick a specific model for a category, it's **pinned** and the auto-roll leaves it alone (it just notifies you when a newer one appears).
- **Custom model discovery**: Sync also discovers **fine-tuned custom models** (`ListCustomModels`), **imported models** (`ListImportedModels`), and models with **on-demand deployments** (`ListCustomModelDeployments`) or **provisioned throughput** (`ListProvisionedModelThroughputs`). Custom models inherit their format family from the base model automatically.
- **Auto-discovery**: New foundation models are registered with `enabled=true` — the admin can disable them. Existing models get their `available_regions` and Bedrock metadata (modalities, lifecycle, ARN) updated automatically.
- **Styled confirmation dialogs**: All destructive actions (Sync, delete, reset) use custom styled modals — no browser `confirm()` popups.
- Changes are persisted immediately to `model_registry.json` via the Admin API.
- The registry is backward compatible — existing assets reference model keys (e.g. `nova_canvas`), not raw Bedrock model IDs.

### 📝 6.12 Self-Hosted Models (Custom Models on Amazon SageMaker)

ArtSmoker can deploy open-source AI models on **Amazon SageMaker** in your own AWS account, extending your capabilities beyond what Amazon Bedrock offers. These run alongside Bedrock models and appear in the same studio dropdowns.

**Extensible model catalog:** Ships with a built-in catalog of open-source models spanning image generation, upscaling, background removal, depth estimation, segmentation, and video. Adding a new model requires only a catalog entry — no code changes. You can also add custom models via the UI (+ Add Model). The catalog and available models evolve over time.

**Deployment options:**
- **Async (scale-to-zero)** — pay only when generating. Scales to zero when idle ($0 cost), scales up automatically on new request. Cold start ~5-10 min.
- **Always-On** — instant responses, ~$1.41/hr (ml.g5.xlarge)

**How to deploy:** Model Settings → Custom Models tab → click Deploy. The SageMaker container pulls model weights directly from HuggingFace at startup — no multi-GB local download required.

**CPU offloading:** Large diffusion models use intelligent CPU offloading to fit on smaller GPU instances. Each model's catalog entry specifies the strategy — `model_cpu_offload` (keeps active layers on GPU) or `sequential_cpu_offload` (aggressive per-layer offload for very large models). Applied automatically by the inference handler.

**Async generation with Pending Jobs:** Self-hosted models generate asynchronously. A **Pending Jobs** panel appears in the 2D Image Studio showing active jobs with progress indicators. Completed images arrive in the Gallery automatically — no polling or page refresh needed.

**HuggingFace token management:** Gated models require a Read-only HuggingFace token. The token is stored encrypted in **AWS Secrets Manager** in your account, managed via the UI (set/update/delete), and shared across all models that need it. Tokens are automatically cleaned up when you tear down all models.

**Gated-access pre-check:** Before a gated deploy, the dialog probes **every** HuggingFace repo the model pulls (its own weights plus any dependencies) using your stored token, and shows a ✓/✗ per repo with the exact next step — accept *this* repo's licence on HuggingFace, or add a token. Deploy stays blocked until every required repo is reachable, so a forgotten licence acceptance fails fast in the dialog instead of minutes into a cold start.

**Setup:** Add Amazon SageMaker and Secrets Manager permissions to the **same IAM role** you already use for Bedrock — no separate role or environment variable needed. ArtSmoker auto-discovers your role on EC2/ECS, or auto-creates an `ArtSmokerSageMakerRole` if needed.

```bash
# Add Amazon SageMaker permissions to your existing ArtSmoker role (one command)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Python dependency:** `huggingface_hub>=0.23` (install with `pip install huggingface_hub`)

### 📝 6.13 Image & Video Generation Models

All models are **discovered dynamically** from the registry — not hardcoded. The Image Studio dropdown is populated from `GET /api/admin/models/image-options` and the Video Studio dropdown from `GET /api/admin/models/video-options` on page load. Any model registered and enabled in the registry appears automatically.

The **Image Model** dropdown is the primary selection. Below it, a smart summary line shows the active region, quality tier, and per-image cost. An expandable **Advanced** section lets you override:

- **Quality** — models that support quality tiers (e.g. Nova Canvas: Standard $0.04/img vs Premium $0.06/img) show a dropdown. Models without tiers show "Default".
- **Region** — shows regions where the selected model is available, sorted cheapest-first with pricing. "Auto" selects the cheapest region.

A **cost estimate** updates dynamically based on all selections (model × quality × region × options × variations).

**Format families**: Models are invoked through a generic invoker (`invoke_image_model`) that reads request templates from the registry (`format_families`). Currently 15 families covering image generation (2), image editing (8), post-processing (2), and video generation (2):
- **Image generation**: `amazon_text_to_image` (Nova Canvas, Titan Image), `stability_text_to_image` (SD 3.5 Large, Stable Image Ultra)
- **Image editing**: `amazon_inpainting`, `amazon_outpainting`, `stability_inpaint`, `stability_outpaint`, `stability_erase`, `stability_search_replace`, `stability_search_recolor`, `stability_control`, `stability_style_transfer`
- **Post-processing**: `stability_remove_bg`, `stability_upscale`
- **Video**: `nova_reel`, `luma_ray`

Adding a new Bedrock image model requires zero code changes — just register it via the admin API or auto-discovery with the correct format family.

**Model-optimized prompt engineering**: Prompts are automatically structured as descriptive captions (not commands) following [AWS documentation](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html). Negation words are removed from the main prompt and exclusion terms are sent as a separate **negative prompt**. The prompt is truncated to each model's specific `prompt_limit` from the registry.

> [!NOTE]
> **Moderation sensitivity varies by model** and is tracked in the registry (`moderation_strictness`). Nova Canvas is the strictest — it rejects prompts with copyrighted names, weapons, and combat language more aggressively. Stable Diffusion 3.5 Large is more relaxed for action/combat themes. ArtSmoker handles this automatically — when a prompt is blocked, the system tries alternative models ordered by strictness before suggesting a rewrite.

## 📌 7. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+), boto3, Pydantic |
| Frontend | Vanilla JS, Tailwind CSS (CDN) |
| AI (LLM) | Claude Sonnet 4.6 (fast tasks), Claude Opus 4.6 (complex tasks) |
| AI (Image) | Nova Canvas, Titan Image v2, Stable Diffusion 3.5 Large, Stable Image Ultra |
| AI (Post-processing) | Stability AI (Remove Background, Creative Upscale) |
| AI (Chat) | 80+ LLMs from 16 providers via Bedrock ConverseStream (Claude, Nova, Llama, Mistral, etc.) |
| AI (Video) | Nova Reel v1.0/v1.1 (up to 2min), Luma AI Ray v2 (up to 9s) |
| AI (Voice) | Nova Sonic (speech-to-text via bidirectional streaming) |
| i18n | Custom t() function, 817 keys × 6 languages, reverse-lookup DOM translation |
| SVG Conversion | vtracer (primary), potrace (fallback), Pillow (last resort) |
| Text Rendering | Pillow (shadow, outline, glow effects) |
| Storage | Local filesystem (S3-ready interface) |
| Dev | No-cache middleware for static files; client-side error logging via `POST /api/log` |

No build step required for the frontend.

## 📌 8. Security Model

ArtSmoker is designed as a **local/trusted-network development tool** — it runs on the developer's own machine or a private EC2 instance. The security model reflects this:

- **No authentication** — all API endpoints are open. Appropriate for local development and private team deployments.
- **Filesystem browser** — the `GET /api/browse/local` endpoint allows browsing any directory the server process can access. This is intentional for importing reference art from your machine.
- **Font serving** — path traversal protection validates that font file requests stay within expected directories.
- **S3 access** — S3 browsing and imports use the server's AWS credentials. The user can access any S3 bucket their IAM role permits.

> [!WARNING]
> Do not expose ArtSmoker to untrusted networks without adding authentication and path restrictions. See the [Deployment Roadmap in SPEC.md](SPEC.md#16-deployment--scaling-roadmap) for production hardening guidance (Phase 4 adds Cognito authentication).

## 📌 9. API

Interactive docs at **http://localhost:8000/docs** (Swagger UI).

Key endpoints:

| Endpoint | Purpose |
|----------|---------|
| **Generation** | |
| `POST /api/generate/` | Generate assets (options × variations) with SSE streaming |
| `POST /api/generate/post-process` | Apply processing to existing assets |
| `POST /api/generate/edit` | Image editing: inpaint, outpaint, erase, search-replace, etc. Accepts source image, mask, prompt, model. |
| `POST /api/generate/analyze-moderation` | Analyze a moderation-blocked prompt and suggest a safe rewrite |
| **Styles** | |
| `POST /api/styles/` | Create a style profile |
| `POST /api/styles/{id}/import` | Bulk-import references from a local folder or S3 URI |
| `POST /api/styles/{id}/analyze` | Trigger AI style analysis |
| **Prompt** | |
| `POST /api/refine-prompt/` | Preview a refined prompt |
| `POST /api/transcribe/` | Voice-to-text (Nova Sonic) |
| **Gallery** | |
| `GET /api/gallery/` | Browse generated assets (supports limit/offset pagination) |
| `GET /api/gallery/batch/{batch_id}` | Reconstruct full options × variations structure for a batch |
| `DELETE /api/gallery/` | Bulk delete assets |
| **Type Studio** | |
| `POST /api/type-studio/preview` | Render text overlay preview |
| `POST /api/type-studio/suggest` | AI layout suggestion for text |
| `GET /api/type-studio/fonts` | List available fonts |
| **Browse** | |
| `GET /api/browse/local?path=~` | Browse local directory contents |
| `GET /api/browse/s3/buckets` | List available S3 buckets |
| `GET /api/browse/s3?bucket=name&prefix=path` | Browse S3 bucket contents |
| **Chat** | |
| `POST /api/chat/stream` | Stream LLM response via SSE (Bedrock ConverseStream) |
| `GET /api/chat/models` | List all available chat models (foundation + custom + imported) |
| `POST /api/chat/sessions` | Create a new chat session |
| `GET /api/chat/sessions` | List chat sessions |
| `GET /api/chat/sessions/{id}` | Load a full session (messages + metadata) |
| `PUT /api/chat/sessions/{id}` | Update session (title, messages, model, temperature) |
| `DELETE /api/chat/sessions/{id}` | Delete a session |
| `POST /api/chat/sessions/{id}/duplicate` | Duplicate a session |
| `GET /api/chat/sessions/{id}/export` | Export session as Markdown |
| `GET /api/chat/sessions/{id}/search?q=` | Search within a session's messages |
| `POST /api/chat/compact` | Compact older messages via LLM summarization |
| `POST /api/chat/generate-title` | Auto-generate a session title from first exchange |
| **Video** | |
| `POST /api/video/generate` | Start async video generation job |
| `GET /api/video/status/{job_id}` | Poll video generation job status |
| `GET /api/video/jobs` | List all video generation jobs |
| `GET /api/video/{id}/mp4` | Serve video MP4 file |
| `GET /api/video/{id}/thumbnail` | Serve video thumbnail |
| `DELETE /api/video/{id}` | Delete a video |
| **Admin** | |
| `GET /api/admin/models` | Get full model registry (LLMs, image models, post-processing) |
| `GET /api/admin/models/image-options` | Enabled text-to-image models for the dropdown (with pricing, quality tiers, regions). Accepts `?region=` filter. |
| `GET /api/admin/regions` | Cached list of Bedrock-supported AWS regions (no AWS calls) |
| `PATCH /api/admin/models/category/{name}` | Update an LLM category config |
| `PATCH /api/admin/models/image/{key}` | Update an image model config |
| `POST /api/admin/models/image` | Add a new image model |
| `POST /api/admin/discover/refresh-all` | Full refresh: discover regions + scan models + fetch pricing + prune stale data. The ONLY endpoint that calls AWS discovery APIs. |
| `POST /api/admin/discover/{region}/auto-register` | Scan a single region for models, register new ones, update regions for existing |
| `GET /api/admin/discover/{region}` | Discover available Bedrock models in a region (raw listing) |
| `GET /api/admin/templates` | Get all 27 editable prompt templates |
| `PATCH /api/admin/templates/{name}` | Update a template (validates required variables) |
| `POST /api/admin/templates/{name}/reset` | Reset a template to default |
| `POST /api/admin/templates/{name}/enhance` | Enhance a template with AI |
| **System** | |
| `POST /api/log` | Client-side error/warning logging (recorded as `[CLIENT]` in server console) |
| `GET /api/health` | Health check + AWS credential/Bedrock validation |

## 📌 10. Project Structure

```
ArtSmoker/
├── backend/
│   ├── main.py              # FastAPI app, startup validation, static mount
│   ├── config.py            # Settings (AWS regions, model IDs, paths, limits)
│   ├── model_registry.json  # Single source of truth: models, regions, pricing, format families, quality tiers
│   ├── requirements.txt
│   ├── prompt_templates.json # Persisted editable LLM directive prompts (27 templates)
│   ├── routers/
│   │   ├── generate.py      # Two-level asset generation + SSE streaming
│   │   ├── styles.py        # Style profile CRUD + directory/S3 import + analysis
│   │   ├── gallery.py       # Asset browsing + file serving + bulk delete
│   │   ├── typestudio.py    # Type Studio: text overlay, font serving, AI layout
│   │   ├── video.py         # Video generation (async), job polling, MP4/thumbnail serving
│   │   ├── chat.py          # Chat Studio: LLM streaming, sessions, export, context compaction
│   │   ├── browse.py        # Server-side file/S3 browser for reference import
│   │   ├── refine.py        # Prompt refinement preview + translation preview
│   │   ├── transcribe.py    # Voice transcription
│   │   └── admin.py         # Model registry management + Bedrock discovery + prompt templates
│   ├── services/
│   │   ├── bedrock_client.py     # Shared Bedrock client with connection pooling
│   │   ├── model_registry.py     # Model registry: loads/saves model_registry.json
│   │   ├── prompt_engineer.py    # Claude: prompt refinement + concept generation
│   │   ├── image_generator.py    # Nova Canvas / Titan / SD 3.5 / Ultra: image gen
│   │   ├── style_analyzer.py     # Two-phase style analysis (cohesion + full)
│   │   ├── post_processor.py     # Stability AI: bg removal, upscale; vtracer: SVG
│   │   ├── transcriber.py        # Nova Sonic: streaming speech-to-text
│   │   ├── import_dedup.py       # Smart deduplication (rotations, animations, folders)
│   │   ├── texture_extractor.py  # glTF/GLB texture extraction
│   │   ├── prompt_translator.py  # Auto-detect language + translate to English
│   │   ├── prompt_templates.py   # Editable LLM directive prompts (load/save/validate)
│   │   ├── video_generator.py   # Video: async Bedrock invoke, S3 download, ffmpeg thumbnails
│   │   ├── cost_tracker.py      # Request-scoped cost accumulator
│   │   ├── telemetry.py         # PulseBoard SDK wrapper: tracks server events
│   │   ├── custom_models.py    # Self-hosted model catalog (extensible)
│   │   ├── async_jobs.py       # Async generation job queue (Pending Jobs panel)
│   │   ├── sagemaker_deployer.py # Amazon SageMaker endpoint management (direct HF pull for HF models)
│   │   └── sagemaker_invoker.py  # Routes inference to Amazon SageMaker endpoints
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update
│   │   ├── generation_request.py  # GenerationRequest, AssetType, ImageModel enums
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult
│   └── storage/
│       └── local_store.py         # Local filesystem (S3-compatible interface)
├── frontend/
│   ├── index.html           # SPA entry point
│   ├── css/styles.css       # Dark theme + animations
│   └── js/
│       ├── app.js               # SPA router + DOM caching + navigation + showConfirm()
│       ├── i18n/
│       │   ├── i18n.js          # Core: t() function, language switching, reverse lookup
│       │   ├── en.json          # English (base) — 817 keys
│       │   ├── ja.json          # Japanese
│       │   ├── zh.json          # Simplified Chinese
│       │   ├── ko.json          # Korean
│       │   ├── fr.json          # French
│       │   └── es.json          # Spanish
│       ├── services/api.js      # Backend API client
│       └── components/
│           ├── ImageStudio.js   # 2D Image Studio (options × variations)
│           ├── TypeStudio.js    # Type Studio (text overlay)
│           ├── VideoStudio.js   # Video Studio (text-to-video generation)
│           ├── ChatStudio.js    # Chat Studio (multi-model LLM chat)
│           ├── Gallery.js       # Gallery grid + search + bulk ops
│           ├── StyleLibrary.js  # Style management + file browser
│           ├── AssetViewer.js   # Full-size preview + metadata + download
│           ├── ModelSettings.js # Model registry admin UI (modal)
│           ├── PromptEditor.js  # Two-area prompt editor + compose
│           └── VoiceInput.js    # MediaRecorder + transcription
├── data/
│   ├── styles/              # Style profiles + reference images (symlinked)
│   ├── generated/           # Output assets (PNG + SVG + metadata.json)
│   ├── video/               # Video assets (MP4 + thumbnails + job metadata)
│   └── chat/                # Chat sessions (JSON per session)
├── SPEC.md                  # Full technical specification (rebuild blueprint)
└── README.md                # This file
```

## 📌 11. Configurable Limits

Settings in `backend/config.py` can be overridden via environment variables (prefix `ARTSMOKER_`):

| Setting | Env Variable | Default | Purpose |
|---------|-------------|---------|---------|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | Max images imported per style |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | Max images sent to AI per analysis call |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Region for Claude + Stability AI models |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Region for Nova Canvas + Titan + Nova Sonic |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | AWS profile name (uses default chain if unset) |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | Git pull on startup + 24h periodic check, self-restart on update |

Reducing `max_analysis_images` reduces AI vision costs per analysis. Reducing `max_reference_images` limits storage. Both can be tuned based on budget.

## 📌 12. Amazon Bedrock Pricing & Cost Breakdown

> [!NOTE]
> The tables below are **reference pricing for planning purposes**. The app itself shows **live per-model pricing** in the Image Studio sidebar — fetched from the AWS Pricing API during registry refresh and stored in `model_registry.json`. The in-app cost estimate updates dynamically based on selected model, quality tier, region, and batch size.

Reference prices are taken from the official [Amazon Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/) for the app's **default regions** — `us-west-2` (Claude, Stability AI) and `us-east-1` (Amazon Nova Canvas, Titan Image, Nova Sonic). Prices can differ in other AWS Regions; the app always shows **live pricing for your actual configured region** in the Image Studio sidebar (fetched from the AWS Pricing API). See also [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown) for monthly team projections and deployment cost estimates.

### 📝 12.1 Per-Unit Pricing

| Service | Model | Cost | Unit |
|---------|-------|------|------|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | $3.00 input / $15.00 output | per 1M tokens |
| **Claude Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | $5.00 input / $25.00 output | per 1M tokens |
| **Claude Opus (vision)** | same | ~$0.008 | per 1024×1024 image input |
| **Nova Canvas** | `amazon.nova-canvas-v1:0` | $0.06 | per image (1024×1024 premium) |
| **Titan Image v2** | `amazon.titan-image-generator-v2:0` | $0.01 | per image |
| **Stable Diffusion 3.5 Large** | `stability.sd3-5-large-v1:0` | $0.08 | per image |
| **Stable Image Ultra** | `stability.stable-image-ultra-v1:1` | $0.14 | per image |
| **Remove Background** | Stability AI | $0.07 | per image |
| **Creative Upscale** | Stability AI | $0.60 | per image |
| **SVG Conversion** | Local (vtracer/potrace) | $0.00 | free |

> [!NOTE]
> Prices from the official [Amazon Bedrock Pricing page](https://aws.amazon.com/bedrock/pricing/) as of March 2026. Prices may change — always verify against the official source before budgeting.

### 📝 12.2 Additional LLM Costs (Per Use)

These LLM calls are included in the generation workflow but not separately itemized in the batch cost tables below:

| Call | Model | When | Approx. Cost |
|------|-------|------|-------------|
| **Prompt Pre-Check** | Claude Sonnet 4.6 | Before generation (if toggle enabled) | ~$0.005 |
| **Moderation Rewrite** | Claude Sonnet 4.6 | Only when all models reject a prompt | ~$0.005 |
| **Type Studio Layout** | Claude Opus 4.6 | Each AI layout suggestion request | ~$0.02–$0.05 |

These are small — pre-check and moderation rewrite are a fraction of a cent each. Type Studio layout is comparable to a single-option prompt refinement.

### 📝 12.3 Style Analysis Cost (One-Time per Style)

~**$0.14** per style (20 images sent to Claude Opus + 8 images cohesion check at Claude Sonnet). The cohesion check adds ~$0.01 (Sonnet with 8 images is very cheap).

### 📝 12.4 Generation Cost by Batch Size

Includes prompt refinement/concept generation + image generation:

| Scenario | Nova Canvas | Titan Image v2 | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|------------|----------------|-------------|-------------------|
| 1 option × 1 variation | ~$0.07 | ~$0.02 | ~$0.09 | ~$0.15 |
| 1 option × 5 variations | ~$0.31 | ~$0.06 | ~$0.41 | ~$0.71 |
| 5 options × 5 variations | ~$1.55 | ~$0.30 | ~$2.05 | ~$3.55 |

### 📝 12.5 Post-Processing Add-Ons (Per Image)

| Add-on | Per image | 1 image | 5 images | 25 images |
|--------|-----------|---------|----------|-----------|
| Remove Background | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convert to SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Creative Upscale note**: Handles Stability AI's 16MB response payload limit automatically by using JPEG output format internally, then converting back to PNG. Includes retry with exponential backoff for API throttling.

### 📝 12.6 Worked Examples

| Example | Configuration | Total Cost |
|---------|-------------|-----------|
| **Cheapest** | 1×1, Titan Image, no processing | ~$0.02 |
| **Standard** | 1×5, Nova Canvas, Remove BG | ~$0.66 |
| **Full exploration** | 5×5, Stable Diffusion 3.5 Large, Remove BG + SVG | ~$3.80 |
| **Premium** | 5×5, Stable Image Ultra, Remove BG + Upscale + SVG | ~$20.30 |

> [!TIP]
> **Key takeaway**: Image generation itself is cheap ($0.01–$0.14/image). **Creative Upscale at $0.60/image is the dominant cost** — use it selectively on your final chosen assets, not the full batch. Remove Background at $0.07/image is reasonable. SVG conversion is free (runs locally).

<a id="disclaimer"></a>

## 📌 13. Disclaimer

> [!IMPORTANT]
> **Generated Content Quality**: All images, videos, and other assets generated by ArtSmoker are produced by AI models available through Amazon Bedrock, including both first-party AWS models and third-party models. The quality, accuracy, and appropriateness of generated content depend entirely on the prompts provided, the models selected, and the style references uploaded by the user. The authors and contributors of ArtSmoker make no guarantees regarding the quality, suitability, or fitness for purpose of any generated content.
>
> **Intellectual Property**: Users are solely responsible for ensuring that their prompts, reference images, and generated outputs do not infringe on any third-party intellectual property rights, including but not limited to copyrights, trademarks, and personality rights. ArtSmoker is a tool — it does not filter, validate, or assess the IP status of inputs or outputs. The tool authors and contributors bear no responsibility for any IP infringement arising from the use of this software.
>
> **AI Model and Service Terms**: Generated content is subject to the terms of service and acceptable use policies of the underlying AI model providers accessible through Amazon Bedrock. Users should review the [AWS Service Terms](https://aws.amazon.com/service-terms/), the [Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/), and the individual model provider terms before using generated assets in production or commercial contexts.
>
> **Cost Estimates Only — Monitor Your Own Spend**: All costs shown in ArtSmoker (per-image, per-video, per-token, 3D compute, deployment, and session/asset totals) are **estimates for guidance only**, computed from AWS published pricing and expected usage. They are **not a bill and not a guarantee** of your actual charges. Real costs depend on your AWS account pricing, region, discounts, taxes, data transfer, endpoint uptime (including idle/warm SageMaker instances), auto-scaling behaviour, and factors outside this tool. **You are solely responsible for monitoring and controlling your own AWS spend** — use the [AWS Billing Console](https://console.aws.amazon.com/billing/), [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/), and [Budgets/billing alarms](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) to track and cap actual charges. Self-hosted SageMaker endpoints in particular continue to bill for as long as they are deployed or kept warm, even when idle — remember to tear them down when finished. The authors and contributors bear no responsibility for any AWS charges incurred through the use of this software.
>
> **No Warranty**: This software is provided "as is" without warranty of any kind. See [LICENSE](LICENSE) for full terms.

## 📌 14. Full Specification

See **[SPEC.md](SPEC.md)** for the complete technical specification — architecture, component design, model configuration, API reference, security model, pricing, deployment roadmap, and enough detail to rebuild the project from scratch.
