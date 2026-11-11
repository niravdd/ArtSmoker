# 3D Parts — Split Characters & Assets into Separate Models (Design)

> **Status:** design, researched 2026-11-11 on branch `feature-3D-Parts`. Nothing is built yet.
> The code references point at `main` @ `5f09f84` (v1.9-20261111_01).
> The licence findings come from primary files (LICENSE, NOTICE, file headers, HF model cards), read 2026-11-11.
> They are a reading of licence text, **not legal advice**. Items marked ⚖️ need a counsel decision.

---

## 1. Problem and goals

Today an image becomes **one fused, fully dressed mesh** (TripoSG or TRELLIS.2). Real production works differently:

- A character is a **base body** plus **separate, swappable accessories**: boots, gun, jacket, hair, hat.
  - A gun may be held, holstered, or left out of a scene.
  - Cf. a ZBrush subtool stack (body / eyes / teeth / brows), or a bald base body with a grid of hats, hair, outfits and boots.
- Map props are separate assets too, and some props are themselves made of parts:
  - tree = trunk + canopy;
  - chair = seat / back / legs.

Goals:

| # | Goal | Priority |
|---|------|----------|
| G1 | **Split an EXISTING generated 3D model into parts.** Parts are shown assembled in the viewer and exported as a per-part package | **Must-have** (user, 2026-11-11) |
| G2 | **Character Kit**: generate the base body and each accessory individually from the 2D image, so the base is clean and the accessories are complete | High |
| G3 | **Style variants** of the same character/asset | High |
| G4 | Expression variants on the same head topology | Later; see §8.3 |

It is **opt-in everywhere**: single-model generation stays exactly as it is.

---

## 2. Research findings

### 2.1 What our code does today

The facts below were surveyed 2026-11-11. Re-verify the line numbers before editing.

- **One image per 3D job.**
  - `ThreeDGenerateRequest` is defined at `generate_3d.py:289`.
  - The payload carries a single `image` (`:792-811`).
  - Neither 3D predictor accepts more than one image (`inference.py` `_predict_image_to_3d:3623`, `_predict_trellis2_full:4292`).
- **Outputs are re-framed.**
  - The source is cropped to a square around the subject (`inference.py:3701-3738`).
  - TripoSG output is rotated 180° about Y (`:3824-3833`).
  - TRELLIS.2 output is normalised to the `[-0.5, 0.5]³` box (`:4389`).
  - A floater cleanup drops components under 1% (`:3835+`), which can delete thin accessories.
  - **Consequence: a part generated on its own loses its placement on the body.**
- **Variant identity.** `_variant_id(ptype, tex_backend, model_key)` is built only from the pipeline and the deployment. A second result from the same pipeline **replaces** the first (`generate_3d.py:2290-2296`).
- **Throughput.**
  - Each 3D endpoint runs `MaxConcurrentInvocationsPerInstance=1` with `MaxCapacity=1` (`sagemaker_deployer.py:706-718`, `:2160-2166`).
  - Typical latency is 600 s (TRELLIS.2) and 900 s (TripoSG).
  - So K jobs take about K × 10–15 min, run serially.
- **Viewer.** It uses `<model-viewer>` with a single `src` (`AssetViewer.js:165-182`, shared with `CollectionAssetViewer.js`). There is no per-node visibility.
- **Export assumptions.**
  - `build_3d_export` (`gallery.py:1185`) handles one GLB.
  - `pack_textures` and `assert_packable` read only the first material (`mesh_export.py:628`, `:657`).
  - `build_collision_glb` concatenates all geometry (`:718-745`).
  - The Blender `convert.py` already loops over all MESH objects for UV2 and LOD.
- **Reusable building blocks:**
  - **Texture a GIVEN mesh from an image**: `_generate_texture_trellis2` (`inference.py:~4173`, MIT TRELLIS.2 texturer).
  - SAM-style segmentation predictor: `_predict_segmentation` (`:3255`), with catalog `sam2` (Apache-2.0).
  - Vision-LLM judge pattern: `_analyze_source_bytes` (`generate_3d.py:1636`).
  - Source sidecars: `prepare-source` and `_sidecar_name`.
  - Purpose lookup: `_find_model_key_by_purpose`.
  - The Collection fan-out pattern: `generate_collection_3d` + `three_d_requests` + `/3d-status` + the zip in `download_collection_3d`.
  - Every 3D variant keeps its source cutout (`asset_v{N}__cutout.png`). **This is our 2D guide for splitting existing models.**

### 2.2 How reliable part splitting is in practice

Sources: GitHub issues, HF Spaces, vendor docs and a community arena, read 2026-11-11. Reddit and X could not be fetched.

- **Every open model is young and fragile.** Recurring complaints:
  - over- and under-segmentation (one character split into 11,052 parts; a staircase whose railings were never assigned to any part);
  - broken UVs and textures after a split;
  - install pain;
  - out-of-memory errors.
- **Completion (filling the surface hidden by a cut) is not production-ready on a 48 GB GPU with textures:**
  - HoloPart crashes on thin parts such as boards and doors (issue #11; open, no maintainer reply).
  - X-Part runs out of memory even on 96 GB until its batch and point counts are edited.
  - Both output **untextured** geometry.
- **Commercial tools split first, then let the artist correct.** Their docs confirm this flow:
  - **Meshy Auto Split** works well on "humanoid figures and characters", props and game-style models. It does badly with "windows", "chains, hair, or mesh-like surfaces". It "automatically seals every cut into a closed, solid part", keeps textures in GLB/OBJ/FBX, and takes 40–60 s.
  - **Tripo segmentation v2** has `simple/balanced/detailed` granularity, an optional reference image, and a separate completion API (AI or quick cap). Its Studio offers paint/merge correction.
- **By asset class:**
  - **Furniture, weapons and hard-surface props:** the split works (clean creases). Every cut still opens a hole that must be capped.
  - **Characters:** hat, gun and boots separate well. Clothes and hair are shells fused onto the body, and **the body under them does not exist in the mesh**: it must be invented and then re-textured.
  - **Trees and plants:** trunk vs canopy guided by a 2D mask is plausible. Individual branches or leaves are not. Generating trunk and foliage separately (G2) is safer.

**Design consequence.** The must-have (G1) is built as **face-labelling on the original mesh**, which keeps its UVs and textures:

1. split automatically, guided by a 2D mask;
2. let the user correct the split by click/brush;
3. seal each cut;
4. optionally re-texture.

Completion is an **optional experimental** step and never a dependency.

### 2.3 Licence audit

Read from primary files on 2026-11-11.

How licences are handled: every self-hosted model's licence, dependencies and warnings are shown in the deploy dialog. Deploy refuses without acceptance (`custom_deploy.py:782-785`) and records it (`_record_license_acceptance`). Optional components with extra terms use an attestation, like the Hunyuan texture backend (`texture_backends.options.hunyuan.license.attestation_required`). **So the requirement is accurate, complete disclosure, plus swapping out non-commercial dependencies where we can.**

| Component | Code / weights | Notable dependencies | Outputs | Verdict and what to disclose |
|---|---|---|---|---|
| **SAM 2.1** | Apache-2.0 / Apache-2.0 | — | Yes | ✅ Already in catalog (`sam2`) |
| **SAM 3 / 3.1** | SAM License (2025-11-19) / same, **HF-gated (manual)** | none third-party | Yes ("you are and will be the owner") | ✅ Disclose:<br>• the trade-controls clause ("activities subject to ITAR or end uses prohibited by Trade Controls, including … the development or use of guns or illegal weapons"). This is about **real-world** export-controlled and weapons uses. It is **not** a bar on fictional game/media art;<br>• ship a copy of the licence;<br>• HF access request |
| **GeoSAM2** | Apache-2.0 / Apache-2.0 | SAM 2.1 (Apache); Blender run as `blender -b -P` subprocess (GPL; separate program per GNU FAQ, same as our exporter) | Yes | ✅ Clean |
| **SegviGen** | MIT (+ TRELLIS.2 MIT) / MIT | **RMBG-2.0 hard-coded** (CC BY-NC); DINOv3 (gated, attribution, as TRELLIS.2); **`bpy` imported in-process** (GPL) | Not as shipped | ⚠️ Usable only after:<br>• swapping in BiRefNet (MIT; same interface, as we already do for TRELLIS.2);<br>• moving bpy rendering into a Blender subprocess |
| **HoloPart** | MIT + **HunyuanDiT-derived transformer** + `holopart/LICENSE` = **FlashVDM** licence / MIT | needs a pre-segmented mesh | Yes, in Territory | ⚠️ Same Tencent terms as TripoSG (below) |
| **PartCrafter** | MIT + HunyuanDiT-derived (no NOTICE) / MIT | RMBG-1.4 (NC; download only, skip it); optional Gemini flags (leave off) | Yes, in Territory | ⚠️ Tencent HunyuanDiT licence (EU excluded) |
| **FlexPart** | MIT + HunyuanDiT `dit_block` / **Apache-2.0** (+TripoSG VAE, MIT) | RMBG-1.4 optional | Yes, in Territory | ⚠️ As PartCrafter. Very new (Oct 2026) |
| **SAM 3D Objects** | SAM License / gated; **≥32 GB VRAM** | nvdiffrast (NVIDIA NC) by default → swap to `pytorch3d`; **Inria NC** Gaussian rasteriser vendored, default `backend="inria"` → swap to gsplat; `requirements.txt` pins `smplx` (NC) and `bpy`, but nothing imports them → drop both | Yes, after the swaps | ⚠️ Usable only with that patched build |
| **SAM 3D Body** + **MHR** | SAM License (gated) + MHR Apache-2.0 (code and `assets/`) | Detectron2 ViTDet weights **CC BY-SA 3.0**; MoGe-2 MIT; DINOv3 code; **no SMPL/SMPL-X needed** | Yes | ✅ Disclose:<br>• SAM License;<br>• CC BY-SA 3.0 attribution for the detector.<br>Gives a pose-matched, **rigged** base body |
| **Qwen-Image-Edit-2511 / Qwen-Image-Layered** | Apache-2.0 (card tag + GitHub LICENSE; HF repos have no LICENSE file) | Qwen2.5-VL (Apache-2.0) | Yes | ✅ |
| **Anny** | Apache-2.0 / CC0 MakeHuman assets | `smpl`/`smplx` topologies download a **non-commercial** zip | Yes, with the `anny`/`makehuman` topologies | ✅ Only if the SMPL topologies are disabled |
| Hunyuan3D-Part (P3-SAM + X-Part) | Tencent 3D-Part CLA (EU/UK/KR excluded; 1M MAU) | **`facebook/sonata` weights = CC-BY-NC 4.0** (README: "Sonata weight is released under the CC-BY-NC 4.0 license"), embedded in X-Part | No | ❌ Can't be fixed by patching. An attestation doesn't cure inherited NC weights |
| OmniPart | MIT, but the CLI downloads `partfield_encoder.ckpt` (`inference_omnipart.py`) | PartField = NVIDIA NC; GLB export imports nvdiffrast (NC); Inria rasteriser | No | ❌ |
| PartPacker, PartField, PartSAM, SAMesh (no licence file), pix2gestalt, GALA (SMPL-X), Sapiens v1, AutoPartGen, Qwen-Image-2.1 (research licence) | — | — | — | ❌ Non-commercial or unlicensed |

#### ⚖️ Existing exposure: the TripoSG catalog entry under-discloses

The `custom_model_catalog.models.triposg` entry shows only "MIT License". The primary files say:

- **`triposg/models/transformers/triposg_transformer.py`** is "based on Tencent HunyuanDiT … Portions of this code are copied or adapted". It embeds the **Tencent Hunyuan Community License (HunyuanDiT, 14 May 2024)**:
  - Territory: "worldwide … excluding the territory of the European Union";
  - a separate licence above **100M MAU**.
- **`triposg/LICENSE`** is the **Tencent Hunyuan FlashVDM Community License (19 Mar 2025)**:
  - Territory excludes the **EU, UK and South Korea**;
  - a separate licence above **1M MAU**.
  - Our handler sets `use_flash_decoder=False` (`inference.py:3784`), so the FlashVDM decoder never runs, but the code ships in the package.
- **Shared terms of both licences:**
  - "Tencent claims no rights in Outputs" (commercial use is fine inside the Territory);
  - no use or display of the Works **or Output** outside the Territory;
  - no using Output to improve other AI models;
  - an **AUP requiring machine-generated content to be identified as such** when placed in a public context;
  - a NOTICE is required on distribution;
  - "Powered by Tencent Hunyuan" is encouraged, not required.
- **Background removal:** TripoSG's own scripts download RMBG-1.4 (NC). Our handler defaults to BiRefNet (`ARTSMOKER_BG_MODEL=birefnet`), so that part is already clean.
- ⚖️ **Counsel question:** do the MIT-tagged TripoSG *weights* count as Hunyuan "Model Derivatives"?

**Done (commit `4f36099`).** The `triposg` catalog `license_agreement` now carries the Tencent terms (key_terms, dependencies, warnings).
- The code only renders and combines what the registry says (`_pipeline_info` / `_summarize_licenses`).
- An acceptance counts only for the licence name it was given to. When the terms change, the 3D tab offers **Review terms** (`POST /api/generate/3d/license-accept`), and generation returns 409 until the user accepts.
- New catalog entries that reuse TripoSG code (HoloPart, PartCrafter, FlexPart) carry the same disclosure.

### 2.4 SAM 3D family and rigging

Verified against the code and docs on 2026-11-11.

**SAM 3D Objects**
- **Input and calls:** one image + one mask per call (`Inference.__call__(image, mask)`), with no batch API.
- **Output:** amodal: it completes hidden geometry. Each object comes with its **layout in the camera frame** (`rotation` quaternion, `translation`, isotropic `scale`), and `make_scene()` composes the objects into one scene.
- **Detail limits:**
  - The coarse grid is 64³, and the paper notes "loss of details" on thin structures, hands and faces.
  - The public wrapper defaults to `with_texture_baking=False, use_vertex_color=True`, so it outputs vertex colours.
  - Baking gives a 1024² **base-colour-only** texture (no PBR).
- **Resources:** ≥ 32 GB VRAM (official), about 8–12 s per object on an H100 (community report).
- **Quality evidence:** human-preference wins of ≥ 5:1 over TRELLIS v1, HY3D-2.1 and TripoSG, but on **real photos**. There is **no comparison with TRELLIS.2** and no evidence on game art.
- **Role for us:** the **layout + amodal proxy** for each part, not the hero mesh.

**SAM 3D Body**
- **Output:** image → **MHR** body in the camera frame (127 joints; LOD1 = 18,439 vertices). Covers body, hands and feet, and handles several people per image.
- **No face or jaw expressions:** face expressions and the jaw are explicitly zeroed (`mhr_head.py`: `pred_face = … * 0`, `pred_pose_euler[:, -3:] = 0`).
- **Training data:** real and photorealistic only. Stylised or chibi proportions are untested and likely weak.

**MHR** (Apache-2.0)
- 204 articulation parameters, 45 identity parameters and **72 FACS expression blendshapes**.
- Artist-authored LBS skin weights and neural pose correctives.
- 7 LODs (73,639 → 595 vertices), shipped as rigged FBX with identity and expression blendshapes.
- No official engine integrations.

**Auto-rigging**
- Nothing in SAM 3D rigs an arbitrary mesh.
- The established route is **fit a body, then transfer its skinning** (e.g. ECON's `avatarizer` transfers LBS weights by kNN, with a dress trick for skirts), plus Robust Skin Weights Transfer (MIT).
- **Failure modes:** skirts and robes, long hair, capes, held props, and non-human or chibi characters.
- **General commercial-safe rigger:** SkinTokens (MIT; uses Michelangelo GPL/LGPL, so isolate it). The alternatives are worse:
  - **Puppeteer:** bundles PartField, which is non-commercial.
  - **RigAnything:** non-commercial.
  - **MagicArticulate:** releases only the skeleton part.

---

## 3. Architecture overview

```
                   ┌──────────────── G1  Split an existing model (must-have) ───────────────┐
 existing 3D  ──►  │ propose parts ─► 2D masks ─► label mesh faces ─► user correction ─►    │
 variant + its     │ (vision LLM)    (SAM 3/2.1)  (projection; GeoSAM2  (click/brush in     │
 source cutout     │                              optional)             3D viewer)          │
                   │ ─► split by labels (keeps UVs) ─► seal cuts ─► [optional completion /  │
                   │                                                 re-texture]            │
                   └──────────────────────────────────┬─────────────────────────────────────┘
                                                      ▼
                       PART SET  (meta.three_d.v{N}.part_sets[])  ──► assembled GLB + manifest
                                                      ▲                 ──► package zip
                   ┌──────────────── G2  Character Kit (generate parts) ┴──────────────────┐
 2D version   ──►  │ propose parts ─► masks ─► per-part in-place images (Qwen-Edit-2511)    │
                   │ + clean base (Qwen-Edit "bodysuit" or SAM 3D Body → MHR) ─► one 3D     │
                   │ job per part ─► register each to the dressed reference mesh ─► fit pass│
                   └────────────────────────────────────────────────────────────────────────┘
```

Both flows produce the same **Part Set**. The viewer, the package and the style variants are shared.

---

## 4. G1: Split an existing model (must-have, build first)

### 4.1 Steps

1. **Propose parts.**
   - A Bedrock vision LLM looks at the source cutout plus the asset prompt and asset type. It returns `[{label, category, slot, attach_type, bbox}]`.
   - This uses a new prompt template, `three_d_part_proposal`, following the `_analyze_source_bytes` pattern.
   - Categories:
     - characters: `body`, `hair`, `headwear`, `eyewear`, `top`, `bottom`, `footwear`, `handwear`, `held_prop`, `worn_prop`, `other`;
     - props: free labels (`trunk`, `canopy`, `seat`, `leg`, …).
2. **2D masks** on the source cutout, one per part.
   - **SAM 3**: text prompts ("boots") are the best fit. It is gated on HF, and its licence is disclosed in the deploy dialog.
   - **SAM 2.1**: prompted with the LLM's boxes. Already in the catalog; Apache-2.0.
   - Both run through the existing segmentation predictor path. The user can edit the parts list and masks before anything else is spent, the same way the 3D source review works.
3. **Label mesh faces.** This is deterministic: no model, and no licence beyond our own code.
   - First recover the camera that relates the mesh to the cutout:
     - undo the pipeline's known frame (TripoSG's 180° Y rotation; TRELLIS.2's unit box);
     - fit a scale and translation so the front-view mesh silhouette matches the cutout alpha (maximise IoU).
   - Ray-cast each mask pixel to its first visible face, so each visible face gets the label with the most votes.
   - Spread labels to hidden or back faces with a graph-cut over mesh adjacency. Its data term is the visible votes; its smoothness term follows dihedral angle and UV-island boundaries, so cuts land on creases and seams.
   - **Optional model-based labelling:** GeoSAM2 (Apache-2.0), which takes a 2D mask on rendered views and returns per-face labels. It needs a GPU endpoint, so it is offered as the "accurate" mode and used when the projection leaves too many faces unassigned.
4. **User correction** in the parts viewer (§6): pick a part, click or brush faces to reassign, merge or split parts. The edited per-face label array is posted back. This is what practitioners actually use.
5. **Split while keeping UVs and materials.**
   - Extract one sub-mesh per label with the original UVs and material, so the texture is unchanged.
   - Do it in headless Blender (`mesh_export` subprocess pattern) or with trimesh.
6. **Seal cuts** (default), the Meshy-style "closed, solid part":
   - fill the boundary loops (Blender `fill_holes` / grid fill);
   - unwrap the cap faces into a small new UV island;
   - colour them from boundary texels (dilate).
7. **Optional, opt-in (each costs a GPU job and is marked experimental):**
   - **Re-texture a part** from the source image with the TRELLIS.2 texturer (`_generate_texture_trellis2`, MIT) for parts whose hidden surfaces matter.
   - **Completion** with HoloPart (Tencent-lineage disclosure; known crash on thin parts). It runs on geometry only and is then re-textured. It is never on by default.

### 4.2 Characters vs props

- **Characters:** accessories (hat, gun, boots, glasses) come out cleanly. Removing clothes and hair leaves the body as a shell with holes, not a clean base. G2 or a body template (SAM 3D Body → MHR) gives a proper base.
- **Hard-surface props** (furniture, weapons, vehicles): the best case. Crease-aligned cuts plus sealing is enough.
- **Trees and plants:** support coarse splits only (trunk / canopy / base). The UI suggests "generate separately" (G2) for finer splits.

---

## 5. G2: Character Kit (generate parts individually)

1. Parts proposal and masks, as in G1 steps 1–2.
2. **In-place part images.** Qwen-Image-Edit-2511 (Apache-2.0) works on the **full original canvas, with no crop**: "only the {item}, same position and scale, plain background, complete hidden parts".
   - Then remove the background (BiRefNet or Bedrock remove-background).
   - Validate: the alpha must contain ≥ ~90% of the original mask, and the bbox drift must be ≤ a few %. Otherwise retry, or fall back to Qwen-Image-Layered.
3. **Clean base body: both routes run** (user decision 2026-11-11: maximum quality, no compromises). The result is kept per asset, or both are offered as variants.
   - (a) **Qwen-Edit bodysuit + TRELLIS.2:** "same person, same pose, bald, fitted neutral bodysuit", then TRELLIS.2 for full detail and PBR. This route matches the art style. Validate that its silhouette sits inside the dressed one and that keypoints are stable.
   - (b) **SAM 3D Body → MHR:** a pose-matched, **rigged** Apache-2.0 body with 72 FACS expression blendshapes on fixed topology. This is the best rig and expression base for realistic proportions; for stylised or chibi characters it is untested and likely weak.
   - The Unity Asset Store requires coverage, so the base is a mannequin or bodysuit, never nude.
   - **Max-quality hybrid (P0 candidate):** wrap the MHR rig onto the TRELLIS.2 bodysuit mesh. Fit (b) to (a), then transfer the skeleton, skin weights and expression shapes. That combines (a)'s fidelity with (b)'s rig.
4. **One normal 3D job per part.** Each job gets `part_set_id` and `part_id`. The existing poller and finalize handle them; finalize writes to the part set, not to the variants list.
5. **Register** each part to the **dressed reference mesh** (the existing variant, or one generated first):
   - fit scale and translation by silhouette (same canvas = same camera);
   - refine with ICP against the matching labelled region of the reference (from G1 step 3);
   - run an anti-penetration pass: push garments outward along normals or shrink the body under them (Blender Shrinkwrap "Outside Surface" + offset).
6. **Layout and occlusion via SAM 3D Objects** (max-quality path):
   - SAM 3 masks go to SAM 3D Objects, which returns an amodal proxy per part with its camera-frame layout (R, t, s).
   - Each part's hero mesh comes from TRELLIS.2 (PBR, high resolution). It is registered to its proxy by a similarity transform plus ICP, so every part shares one frame without depending on silhouette fitting.
   - The proxies also guide the in-place images for parts that are heavily occluded.
7. Alternative for props: **FlexPart** (mask-prompted parts in one frame; geometry only, then re-textured) as a P0 bake-off candidate.

Cost: K parts take about K × 10–15 min, serially per endpoint. Example: 6 parts on g5.2xlarge ($1.52/hr in the catalog) take about 1–1.5 h and cost about $2. The estimate is shown before submitting (`threeDEstimate`).

---

## 6. Data model, jobs and viewer

### 6.1 Metadata

This sits beside the existing variants and never replaces them. All writes use `asset_write_lock`, with the lock order `_3d_finalize_lock → asset_write_lock` (SPEC §17).

```jsonc
meta.three_d["v{N}"].part_sets = [{
  "set_id": "ps_<short>",            // unique per split / kit
  "kind": "split" | "kit",
  "source_variant": "<variant_id>",  // the dressed mesh it came from / registers to
  "created_at": "...",
  "status": "proposing|masking|labelling|review|splitting|generating|assembling|ready|failed",
  "labels_file": "asset_3d_v{N}__{set}__labels.npy",   // G1 per-face labels (editable)
  "parts": [{
    "part_id": "boots", "label": "Leather boots", "category": "footwear",
    "slot": "feet", "attach": {"type": "fitted" | "socket", "socket": {"unreal": "foot_l", "unity": "LeftFoot", "mixamo": "mixamorig:LeftFoot"}, "pivot": [x, y, z]},
    "hides_body_regions": ["feet", "calves"],
    "mask_file": "...png", "source_image": "...png",     // kit: in-place part image
    "glb_filename": "asset_3d_v{N}__{set}__boots.glb",
    "job_id": "...", "status": "...", "transform": [16 floats],   // kit: registration result
    "faces": 0, "sealed": true, "retextured": false, "completed": false,
    "pipeline": { /* same licence/provenance record as variants */ }
  }],
  "assembled_glb": "asset_3d_v{N}__{set}__assembled.glb",
  "manifest_file": "asset_3d_v{N}__{set}__manifest.json",
  "styles": [{"style_id": "toon", "source_image": "...", "texture_set": "..."}]
}]
```

Places that must learn about part sets:
- version delete (`gallery.py:616-624`);
- `has_3d` (`*.glb` glob);
- the `resolve_3d_glb` candidate names (part files must never match them);
- `_saved_variant_for_job` / `_adopt_peer_finalized` (job → part lookup);
- Collections `refresh_if_member`.

### 6.2 Jobs

- Part jobs reuse the 3D job dict plus `part_set_id` and `part_id`. G1 GPU steps (masks, GeoSAM2, re-texture, completion) are separate job types on their own endpoints.
- A set-level coordinator is a server-side state machine. It mirrors the Collection fan-out pattern (`generate_collection_3d` / `three_d_requests` / `/3d-status`) and keeps asset IDs unchanged.
- Terminology: a part set belongs to one asset version. Each GPU invocation is a **Job**. No new tier word in the UI (CLAUDE.md terminology).

### 6.3 Viewer

- A new **parts view** uses **three.js + GLTFLoader** (CDN ES module, no build step). It provides:
  - per-part visibility toggles;
  - isolate / solo;
  - exploded view;
  - picking faces for correction (brush with BVH ray-cast);
  - style switching (KHR_materials_variants).
- `<model-viewer>` stays the viewer for ordinary single variants.
- All markup goes through `html\`\``.

---

## 7. Package (export / download)

Built by looping the existing `build_3d_export` per part (the `download_collection_3d` pattern), plus the assembled file:

```
{asset}_v{N}_parts/
  manifest.json                     # parts, categories, slots, attach (fitted|socket + per-engine socket names),
                                    # pivots, hides_body_regions, styles, tris/LODs, licences/attributions
  assembled/{asset}_assembled.glb   # every part as a named node (+ KHR_materials_variants for styles)
  assembled/{asset}_assembled.fbx   # (+ USD) via the Blender converter, engine preset applied
  parts/{slot}/{asset}_{part}.glb|fbx
  textures/…                        # when a packing preset is chosen
  styles/{style_id}/…               # per-style texture sets (FBX has no material variants)
  previews/{part}.png
  LICENSES/                         # NOTICE / licence texts the parts' pipelines require
```

- **Origins:** fitted parts (clothes, boots, hair) share the character's world origin, with the feet at (0,0,0), so they align when imported together. Socket props (gun, hat) get a pivot at the grip or contact point; the manifest stores the offset that places them in the assembled pose.
- **Engine naming:** collision `UCX_` (Unreal) / `-col` (Godot), applied per part as today. `pack_textures` and `build_collision_glb` gain per-mesh loops; today they assume one material and one mesh.
- **Caching:** the export cache token and `three_d_exports` keys gain a part/set dimension.

---

## 8. Style variants

### 8.1 Same mesh, new look (v1)

1. Restyle the 2D source: Qwen-Image-Edit-2511, or the Stability style-transfer / style-guide / control-structure services on Amazon Bedrock.
2. **Re-texture the same meshes** with `_generate_texture_trellis2`.

The geometry is identical, so every part still fits. Ship it as KHR_materials_variants in the assembled GLB plus `styles/{id}/` texture sets.

### 8.2 Full restyle

For example, chibi or low-poly stylisation. This is a new 2D version through the existing pipeline, so the geometry is new and parts don't carry over. Offered as a one-click "restyle into a new version".

### 8.3 Expressions on the same topology

**Not automatable commercial-safely today.**
- glTF morph targets require identical vertex counts.
- No commercial-safe tool generates expression blendshapes from a static AI head. RigAnyFace has no code; OmniFaceRig is non-commercial; Polywink is a manual €499 service.

**With an MHR base this becomes possible.** MHR ships **72 FACS expression blendshapes** on a fixed topology (Apache-2.0).
- If the base body is MHR, or the MHR rig is wrapped onto our base mesh (§5 step 3 hybrid), its expressions transfer with it. The result is true morph-target expression variants on the same head topology, as in the user's reference.
- SAM 3D Body does not *estimate* the expression in the image (it is zeroed), so expressions are authored from MHR's named controls (`jawDrop`, `eyesClosed_L`, …), not copied from the picture.
- **Without MHR** (non-humanoid, or a style MHR can't fit), v1 makes each expression a separate static head mesh via a 2D expression edit.

## 8a. Rigging (the user's long-standing ask)

Nothing generates a rig for an arbitrary mesh directly. The plan has three parts:
1. **Humanoids with realistic or tight-fitting builds:** SAM 3D Body → MHR fitted to the same image → register to our mesh → transfer MHR's skeleton and LBS weights (and expression shapes) in headless Blender. This is ECON-style kNN / Robust Skin Weights Transfer. Socket props (gun, hat) are bound to hand/head bones instead of skinned.
2. **Everything else** (stylised or chibi, skirts and robes, creatures): SkinTokens (MIT; Michelangelo isolated), as in the existing rigging research.
3. **Garments from G1/G2:** weights transferred from the rigged body (Data Transfer, nearest face interpolated).

The output is a rigged FBX/GLB package with standard bone-name maps per engine in the manifest.

---

## 8b. Endpoints: new only, existing ones untouched

User decision, 2026-11-11. The live endpoints were checked read-only that day: TripoSG, TRELLIS.2, Qwen-Image BF16, HunyuanImage 3.0 BF16/NF4, FLUX.2 dev and FLUX.1 dev.
- Each container serves exactly one predictor (`PREDICTOR_TYPE`).
- Segmentation, SAM 3D, mesh-input re-texturing and part labelling are new input types. Adding them to an existing endpoint would mean changing its handler and redeploying it.
- So:
  - **New catalog entry "3D Parts"** with its own predictor type and its own scale-to-zero async endpoint. It holds SAM 3 / 3.1, SAM 3D Objects, SAM 3D Body, GeoSAM2 and a TRELLIS.2 *mesh-input* texturer, loaded on demand and parked in host RAM between stages.
    - Sized on a single L40S 48 GB (SAM 3D Objects needs ≥ 32 GB).
    - It needs large host RAM for parking, so a `g6e.4xlarge` or above (exact choice in P0).
    - New code path, so the existing handlers stay unchanged.
  - **A fresh Qwen-Image-Edit-2511 BF16 deployment** (existing catalog entry) for the Character Kit images.
  - The existing TRELLIS.2 / TripoSG endpoints are used only for their existing purpose: image → 3D per part.

## 9. Phases

| Phase | Scope | Verify |
|---|---|---|
| **P0** | Bake-off **with the user** (planned SageMaker spend, never ad-hoc). About 3 assets (character, chair or table, tree): G1 projection vs GeoSAM2; HoloPart on/off; G2 Qwen-Edit parts; FlexPart. Tripo/Meshy as a manual quality bar only (external, non-AWS) | Side-by-side renders and per-part review |
| **P1** | G1 backend: parts proposal template, masks, projection labelling, split + seal, part-set metadata, package zip, TripoSG licence disclosure fix | Fixture tests; sanity-harness stage; semgrep/bandit |
| **P2** | three.js parts viewer + correction brush; Collections parity | Browser E2E; user QA |
| **P3** | G2 Character Kit (in-place parts, base body, registration, fit pass) | P0 assets re-run |
| **P4** | Styles (re-texture + materials variants) | — |
| **P5** | Rigging (§8a): MHR fit-and-transfer for humanoids, SkinTokens otherwise; MHR expression variants (§8.3) | Rig deforms cleanly in Blender plus one engine |

## 10. Decisions

- ✅ TripoSG licence disclosure: done (§2.3). ⚖️ The weights question is still for counsel.
- ✅ New endpoints only; existing deployments are untouched (§8b).
- ✅ Base body: both routes, plus the MHR-onto-TRELLIS.2 hybrid; maximum quality (§5).
- ⏳ P0: which assets to test (suggested: character, chair/table, tree), and when to deploy the new "3D Parts" + Qwen-Edit endpoints. SageMaker spend is planned with the user.
