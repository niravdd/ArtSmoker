#!/usr/bin/env node
/**
 * ArtSmoker Image Generation — Node.js API Sample
 * =================================================
 *
 * A self-contained client that drives the ArtSmoker image-generation API
 * end-to-end: list models → (optional) classify + decompose the prompt →
 * generate over an SSE stream → poll any async (self-hosted) jobs → download
 * the finished PNGs to disk.
 *
 * Pipeline & endpoints
 *   1. List available models          GET  /api/admin/models/image-options
 *   2. Classify asset type            POST /api/refine-prompt/classify-asset-type
 *   3. Decompose the prompt           POST /api/refine-prompt/decompose
 *   4. Generate images (SSE)          POST /api/generate/stream
 *   5. Poll async jobs (self-hosted)  GET  /api/generate/async-jobs
 *   6. Download images                GET  /api/gallery/{asset_id}/png
 *
 * Prerequisites
 *   - Node.js 18+  (uses the built-in global `fetch`, `AbortController`,
 *                   `TextDecoder`, and `node:util`'s `parseArgs`)
 *   - NO dependencies and NO build step — this is a plain CommonJS file.
 *     Just run it. SSE is parsed by hand (see readSseStream) so there is
 *     nothing to `npm install`.
 *   - An ArtSmoker server running at http://localhost:8000 with at least one
 *     image model enabled (Bedrock models work with AWS credentials; custom
 *     SageMaker models must be deployed first).
 *
 * How to run
 *   node imageGen_node.js
 *   node imageGen_node.js --prompt "a medieval castle on a cliff" --model nova_canvas
 *   node imageGen_node.js --prompt "a cyberpunk warrior" --width 1024 --height 1024 --options 2 --variations 2
 *
 * Cost note — the sample deliberately keeps a run small and cheap:
 *   - num_options × num_variations default to 5 × 5 = 25 images SERVER-SIDE.
 *     This sample uses 2 × 2 = 4 for a quick, inexpensive run.
 *   - remove_background and generate_svg default to TRUE server-side (extra
 *     post-processing + cost). This sample sends them as FALSE to get the raw
 *     generated image only. See the payload in generateImages().
 *
 * Reference
 *   Interactive API docs (source of truth):  http://localhost:8000/docs
 *   Architecture / data model:                SPEC.md in the project root
 *   API contract for AI assistants:            api-samples/skill.md
 *
 * Environment
 *   ARTSMOKER_URL — base URL (default: http://localhost:8000)
 */

'use strict';

const { writeFileSync, mkdirSync, existsSync } = require('node:fs');
const { join } = require('node:path');
const { parseArgs } = require('node:util');

// ── Configuration ───────────────────────────────────────────────────────────

const BASE_URL = process.env.ARTSMOKER_URL || 'http://localhost:8000';

// ANSI color codes for terminal output
const C = {
    reset:   '\x1b[0m',
    bold:    '\x1b[1m',
    dim:     '\x1b[2m',
    red:     '\x1b[91m',
    green:   '\x1b[92m',
    yellow:  '\x1b[93m',
    blue:    '\x1b[94m',
    magenta: '\x1b[95m',
    cyan:    '\x1b[96m',
};

function colored(text, color) {
    return `${color}${text}${C.reset}`;
}

function printHeader(title) {
    const width = 60;
    console.log(`\n${C.cyan}${'='.repeat(width)}`);
    console.log(`  ${title}`);
    console.log(`${'='.repeat(width)}${C.reset}\n`);
}

function printStep(step, description) {
    console.log(`${C.bold}${C.blue}[Step ${step}]${C.reset} ${description}`);
}

function printEvent(type, message) {
    const colorMap = {
        started:         C.green,
        stage:           C.yellow,
        prompts_ready:   C.magenta,
        image_done:      C.green,
        option_complete: C.green,   // doc alias for image_done
        async_submitted: C.cyan,
        model_status:    C.dim,
        complete:        C.green,
        done:            C.green,   // doc alias for complete
        error:           C.red,
        image_error:     C.red,
        moderation_blocked: C.red,
        prompt_refused:  C.red,
    };
    const color = colorMap[type] || C.dim;
    console.log(`  ${color}[${type}]${C.reset} ${message}`);
}


// ── HTTP helpers ────────────────────────────────────────────────────────────

/** POST JSON and return the parsed response. */
async function postJson(path, body, timeoutMs = 60000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const resp = await fetch(`${BASE_URL}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: controller.signal,
        });
        if (!resp.ok) {
            const text = await resp.text();
            throw new Error(`HTTP ${resp.status}: ${text.slice(0, 200)}`);
        }
        return await resp.json();
    } finally {
        clearTimeout(timer);
    }
}

/** GET JSON and return the parsed response. */
async function getJson(path, timeoutMs = 10000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const resp = await fetch(`${BASE_URL}${path}`, { signal: controller.signal });
        if (!resp.ok) {
            const text = await resp.text();
            throw new Error(`HTTP ${resp.status}: ${text.slice(0, 200)}`);
        }
        return await resp.json();
    } finally {
        clearTimeout(timer);
    }
}


// ── Minimal SSE stream reader (no dependencies) ───────────────────────────────

/**
 * Read a `text/event-stream` response body and invoke `onEvent(dataObject)`
 * for every event whose `data:` payload parses as JSON.
 *
 * ArtSmoker frames each event as one or more `data: <json>` lines followed by a
 * blank line, and sends `: keepalive` comment lines between events. We buffer
 * raw bytes, split on the blank-line delimiter, concatenate the `data:` lines
 * of each block, and JSON-parse the result. Comment lines (starting with `:`)
 * are ignored per the SSE spec.
 */
async function readSseStream(resp, onEvent) {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const flushBlocks = () => {
        let idx;
        // Events are separated by a blank line ("\n\n"); tolerate CRLF too.
        while ((idx = buffer.search(/\r?\n\r?\n/)) !== -1) {
            const match = buffer.slice(idx).match(/^\r?\n\r?\n/);
            const block = buffer.slice(0, idx);
            buffer = buffer.slice(idx + match[0].length);

            const dataLines = [];
            for (const line of block.split(/\r?\n/)) {
                if (line.startsWith(':')) continue;          // comment / keepalive
                if (line.startsWith('data:')) {
                    dataLines.push(line.slice(5).replace(/^ /, ''));
                }
            }
            if (dataLines.length === 0) continue;
            const payload = dataLines.join('\n');
            let parsed;
            try {
                parsed = JSON.parse(payload);
            } catch {
                continue;  // skip non-JSON frames
            }
            onEvent(parsed);
        }
    };

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        flushBlocks();
    }
    // Final decode + flush for any trailing bytes/block.
    buffer += decoder.decode();
    if (buffer && !/\r?\n\r?\n$/.test(buffer)) buffer += '\n\n';
    flushBlocks();
}


// ── Step 1: List available models ─────────────────────────────────────────────

/**
 * Fetch available text-to-image models.
 *
 * GET /api/admin/models/image-options
 * Response shape: { models: [ {key, label, provider, region, base_price_usd,
 *                   region_pricing:[{region, price_usd, quality_prices}],
 *                   model_source, supported_sizes, capabilities, ...} ],
 *                   available_regions: [...] }
 * NOTE: the payload is an OBJECT with a `models` array — not a bare array.
 */
async function listModels() {
    printStep(1, 'Fetching available image models...');
    const data = await getJson('/api/admin/models/image-options');
    const models = data.models || [];
    console.log(`  Found ${colored(String(models.length), C.green)} available model(s):`);
    for (const m of models) {
        const key = m.key || '';
        const label = m.label || key;
        const region = m.region || '';
        // base_price_usd may be null; fall back to the default region price.
        const price = m.base_price_usd ?? m.region_pricing?.[0]?.price_usd ?? null;
        const priceStr = price != null ? `~$${price.toFixed(4)}/image` : 'price n/a';
        const source = m.model_source && m.model_source !== 'foundation' ? ` {${m.model_source}}` : '';
        console.log(`    ${C.dim}-${C.reset} ${colored(key, C.bold)} (${label}) [${region}] ${priceStr}${source}`);
    }
    return models;
}


// ── Step 2: Classify asset type ───────────────────────────────────────────────

/**
 * Auto-classify the ideal asset type for the prompt.
 *
 * POST /api/refine-prompt/classify-asset-type   body: {prompt, asset_type}
 * Response (mismatch): {current, suggested, reason, confidence, mismatch:true}
 * Response (ok):       {current, suggested, mismatch:false}
 */
async function classifyAssetType(prompt, currentType = 'photorealistic') {
    printStep(2, 'Classifying asset type...');
    const result = await postJson('/api/refine-prompt/classify-asset-type', {
        prompt,
        asset_type: currentType,
    }, 30000);

    if (result.mismatch) {
        const suggested = result.suggested;
        const reason = result.reason || '';
        console.log(`  ${C.yellow}Suggestion:${C.reset} Switch from '${currentType}' to '${colored(suggested, C.green)}'`);
        console.log(`  ${C.dim}Reason: ${reason}${C.reset}`);
        return suggested;
    }
    console.log(`  Asset type '${colored(currentType, C.green)}' is appropriate for this prompt.`);
    return currentType;
}


// ── Step 3: Decompose prompt ──────────────────────────────────────────────────

/**
 * Decompose the prompt into structured visual components.
 *
 * POST /api/refine-prompt/decompose   body: {prompt, asset_type, image_model}
 * Response: sections (subject, scene, composition, lighting, style) whose
 * fields are {value, source} where source is "user" or "inferred", plus a
 * `_meta` block. This is provenance only — the default path does NOT feed it
 * back into generation (see the optional `decomposed_data` field below).
 */
async function decomposePrompt(prompt, assetType, model = '') {
    printStep(3, 'Decomposing prompt into visual components...');
    const result = await postJson('/api/refine-prompt/decompose', {
        prompt,
        asset_type: assetType,
        image_model: model,
    }, 60000);

    for (const [sectionName, sectionData] of Object.entries(result)) {
        if (sectionName.startsWith('_')) continue;  // Skip _meta
        if (typeof sectionData !== 'object' || sectionData === null || Array.isArray(sectionData)) continue;
        console.log(`  ${colored(sectionName.toUpperCase(), C.magenta)}:`);
        for (const [fieldName, fieldData] of Object.entries(sectionData)) {
            if (typeof fieldData === 'object' && fieldData !== null && 'value' in fieldData) {
                const source = fieldData.source ? ` [${fieldData.source}]` : '';
                console.log(`    ${fieldName}: ${C.dim}${fieldData.value}${source}${C.reset}`);
            } else if (Array.isArray(fieldData)) {
                console.log(`    ${fieldName}: [${fieldData.length} entries]`);
            } else if (typeof fieldData === 'string') {
                console.log(`    ${fieldName}: ${C.dim}${fieldData}${C.reset}`);
            }
        }
    }
    return result;
}


// ── Step 4: Generate images via SSE ────────────────────────────────────────────

/**
 * Generate images using the SSE streaming endpoint.
 *
 * POST /api/generate/stream  (returns text/event-stream)
 *
 * Event types actually emitted by the server (see backend/routers/generate.py):
 *   - asset_type_suggestion : optional first event hinting a better asset_type
 *   - started               : {batch_id, total, num_options, num_variations}
 *   - stage                 : {stage, message}   (prompts, canary, generating, finalizing)
 *   - prompts_ready         : {prompts:[...], negative_prompt, recomposed_prompt}
 *   - image_done            : {option, variation, completed, total}  (a Bedrock image finished)
 *   - async_submitted       : {option, variation, job_id, model_label}  (self-hosted job queued)
 *   - image_error           : {option, variation, error}
 *   - moderation_blocked     : {message, error}
 *   - prompt_refused         : {reason, message}
 *   - model_status           : per-task status (all-models runs only)
 *   - complete               : {result: GenerationResult, all_models_summary?}  ← terminal
 *   - error                  : {detail}  (fatal server error)
 *
 * (The doc names "option_complete"/"done" are aliases; we handle both.)
 */
async function generateImages(prompt, model, assetType, width = 1024, height = 1024, numOptions = 2, numVariations = 2) {
    printStep(4, 'Generating images via SSE stream...');

    // Build the generation request payload.
    const payload = {
        prompt,
        image_model: model,
        asset_type: assetType,
        width,
        height,
        // Server default is 5 × 5 = 25 images. Keep it small for a quick sample run.
        num_options: numOptions,
        num_variations: numVariations,
        // These two POST-PROCESSING flags default to TRUE server-side. Send them
        // explicitly as FALSE so we get the raw generated PNG only (no background
        // removal, no SVG vectorization) — faster and cheaper for a sample.
        remove_background: false,
        generate_svg: false,
        // Creative upscale is off by default (extra cost); shown here for clarity.
        upscale: false,

        // ── Optional newer fields (left at defaults for the simple path) ──
        // region: null,                 // override the model's AWS region
        // quality: '',                  // model-specific tier, e.g. "standard"/"premium"
        // seed: null,                   // base seed for reproducible batches
        // style_id: null,               // a saved style profile (GET /api/styles/)
        // all_models: false,            // generate with EVERY enabled model
        // selected_models: null,        // ["nova_canvas", "sd35_large", ...]
        // model_optimized_prompts: false, // per-model prompt tailoring (multi-model only)
        // decomposed_data: null,        // feed Step-3's structured breakdown back in
        // Reference-guided generation (Reference Studio):
        // reference_images: null,       // 1–3 base64-encoded PNG references
        // reference_mode: 'inspired',   // 'match' (keep subject, needs an edit model) or
        //                               // 'inspired' (vision-LLM composition guidance)
    };

    console.log(`  Payload: ${colored(JSON.stringify(payload, null, 2), C.dim)}`);

    const resp = await fetch(`${BASE_URL}/api/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify(payload),
    });

    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Generation failed: HTTP ${resp.status}: ${text.slice(0, 200)}`);
    }
    if (!resp.body) {
        throw new Error('Generation stream returned no body.');
    }

    let resultData = null;
    let batchId = null;
    let fatalError = null;
    const asyncJobs = [];

    console.log(`\n  ${C.bold}--- SSE Events ---${C.reset}`);

    await readSseStream(resp, (data) => {
        const eventType = data.type || 'unknown';
        switch (eventType) {
            case 'asset_type_suggestion': {
                printEvent(eventType, `Consider asset type '${data.suggested || ''}' — ${data.reason || ''}`);
                break;
            }
            case 'started': {
                batchId = data.batch_id || '';
                printEvent(eventType, `Batch ${batchId.slice(0, 8)}... - generating ${data.total || 0} image(s)`);
                break;
            }
            case 'stage': {
                printEvent(eventType, `[${data.stage || ''}] ${data.message || ''}`);
                break;
            }
            case 'prompts_ready': {
                const prompts = data.prompts || [];
                printEvent(eventType, `${prompts.length} enhanced prompt(s) ready`);
                prompts.forEach((p, i) => {
                    const display = p.length > 120 ? p.slice(0, 120) + '...' : p;
                    console.log(`    ${C.dim}Prompt ${i + 1}: ${display}${C.reset}`);
                });
                if (data.negative_prompt) {
                    console.log(`    ${C.dim}Negative: ${String(data.negative_prompt).slice(0, 100)}${C.reset}`);
                }
                break;
            }
            case 'image_done':
            case 'option_complete': {
                const opt = (data.option ?? data.option_index ?? 0) + 1;
                const vari = (data.variation ?? data.variant_index ?? 0) + 1;
                printEvent('image_done', `Option ${opt}, Variation ${vari} (${data.completed || 0}/${data.total || 0} complete)`);
                break;
            }
            case 'async_submitted': {
                const jobId = data.job_id || '';
                if (jobId) asyncJobs.push(jobId);
                printEvent(eventType, `Async job ${jobId.slice(0, 12)}... (${data.model_label || ''}) - will poll for completion`);
                break;
            }
            case 'model_status': {
                // Per-task status in all-models runs; keep it quiet unless it failed.
                if (data.status && data.status !== 'success') {
                    printEvent(eventType, `${data.model_label || data.model || ''}: ${data.status}`);
                }
                break;
            }
            case 'complete':
            case 'done': {
                resultData = data.result || data;
                if (data.all_models_summary) {
                    printEvent('complete', `All models: ${data.all_models_summary.summary || ''}`);
                } else {
                    const options = (resultData && resultData.options) || [];
                    const totalImages = options.reduce((sum, o) => sum + (o.variants || []).length, 0);
                    printEvent('complete', `Done! ${totalImages} image(s) generated`);
                }
                break;
            }
            case 'error':
            case 'image_error': {
                const err = data.detail || data.error || 'Unknown error';
                printEvent(eventType, colored(err, C.red));
                if (eventType === 'error') fatalError = String(err);
                break;
            }
            case 'moderation_blocked': {
                printEvent(eventType, colored(data.message || 'Content moderation blocked this generation', C.red));
                break;
            }
            case 'prompt_refused': {
                printEvent(eventType, colored(data.reason || 'Prompt refused by the AI', C.red));
                break;
            }
            default: {
                // Forward-compat: unknown event types (e.g. LLM retry notices) print raw.
                printEvent(eventType, JSON.stringify(data).slice(0, 200));
            }
        }
    });

    console.log(`  ${C.bold}--- End SSE ---${C.reset}\n`);

    if (fatalError) throw new Error(fatalError);
    return { result: resultData, asyncJobs, batchId };
}


// ── Step 5: Poll for async job completion ──────────────────────────────────────

/**
 * Poll for async (self-hosted SageMaker) job completion.
 *
 * GET /api/generate/async-jobs → {jobs:[{job_id, status, asset_id, image_path,
 *                                 model_label, error, queue_position, ...}],
 *                                 pending_count, has_active}
 * status is one of: "pending" | "generating" | "complete" | "failed".
 * Polls every 10s until all tracked jobs finish or `timeoutMs` elapses.
 */
async function pollAsyncJobs(jobIds, timeoutMs = 900000) {
    if (jobIds.length === 0) return [];

    printStep(5, `Polling ${jobIds.length} async job(s)...`);
    const start = Date.now();
    const completedJobs = [];
    const settled = new Set();

    while (Date.now() - start < timeoutMs) {
        let jobs = [];
        try {
            const data = await getJson('/api/generate/async-jobs');
            jobs = data.jobs || [];
        } catch (e) {
            console.log(`  ${C.yellow}Poll error (will retry): ${e.message}${C.reset}`);
        }

        for (const jid of jobIds) {
            if (settled.has(jid)) continue;
            const job = jobs.find(j => j.job_id === jid);
            if (!job) continue;

            if (job.status === 'complete') {
                settled.add(jid);
                completedJobs.push(job);
                console.log(`  ${C.green}Job ${jid.slice(0, 12)}... completed! Asset: ${job.asset_id || ''}${C.reset}`);
            } else if (job.status === 'failed') {
                settled.add(jid);
                completedJobs.push(job);
                console.log(`  ${C.red}Job ${jid.slice(0, 12)}... failed: ${job.error || 'Unknown'}${C.reset}`);
            } else {
                const elapsed = Math.round((Date.now() - start) / 1000);
                const pos = job.queue_position ? ` queue #${job.queue_position}` : '';
                console.log(`  ${C.dim}Job ${jid.slice(0, 12)}... status: ${job.status}${pos} (${elapsed}s elapsed)${C.reset}`);
            }
        }

        if (settled.size >= jobIds.length) break;
        await new Promise(resolve => setTimeout(resolve, 10000));
    }

    return completedJobs;
}


// ── Step 6: Download completed images ──────────────────────────────────────────

/**
 * Download generated images from the gallery.
 *
 * GET /api/gallery/{asset_id}/png → PNG bytes.
 * Saves each image under `outputDir` with a descriptive, sanitized filename.
 */
async function downloadImages(result, outputDir = 'output') {
    if (!result) {
        console.log(`  ${C.yellow}No result data to download.${C.reset}`);
        return [];
    }

    printStep(6, 'Downloading generated images...');
    // nosemgrep -- outputDir is a fixed local config constant, not user-controlled
    if (!existsSync(outputDir)) {
        // nosemgrep -- outputDir is a fixed local config constant, not user-controlled
        mkdirSync(outputDir, { recursive: true });
    }

    const options = result.options || [];
    const downloaded = [];

    for (const option of options) {
        const optIdx = option.option_index || 0;
        for (const variant of (option.variants || [])) {
            const assetId = variant.id || '';
            const pngPath = variant.png_path || '';
            const varIdx = variant.variant_index || 0;

            // Async job that hasn't produced a file yet (should have been resolved
            // by polling in main(); skip defensively).
            if (variant.async_job && !pngPath) {
                console.log(`  ${C.dim}Skipping opt${optIdx + 1}_var${varIdx + 1} (async pending)${C.reset}`);
                continue;
            }
            if (!assetId || !pngPath) continue;

            const url = pngPath.startsWith('http') ? pngPath : `${BASE_URL}${pngPath}`;
            try {
                const resp = await fetch(url);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const buffer = Buffer.from(await resp.arrayBuffer());
                // Sanitize the server-provided asset id so it can't traverse outside outputDir.
                const safeAssetId = String(assetId).replace(/[^a-zA-Z0-9_-]/g, '_');
                const filename = `opt${optIdx + 1}_var${varIdx + 1}_${safeAssetId}.png`;
                // nosemgrep -- filename is sanitized (alnum/_/- only) and joined under the fixed outputDir
                const filepath = join(outputDir, filename);
                // nosemgrep -- writing a downloaded image to the sanitized path under outputDir
                writeFileSync(filepath, buffer);
                downloaded.push(filepath);
                console.log(`  ${C.green}Saved:${C.reset} ${filepath} (${(buffer.length / 1024).toFixed(1)} KB)`);
            } catch (e) {
                console.log(`  ${C.red}Failed to download ${assetId}: ${e.message}${C.reset}`);
            }
        }
    }

    return downloaded;
}


// ── Results summary ─────────────────────────────────────────────────────────

function printSummary(result, downloaded, asyncJobs, elapsedMs) {
    printHeader('Generation Summary');

    if (!result || !result.id) {
        console.log(`  ${C.red}No results produced.${C.reset}`);
        return;
    }

    const options = result.options || [];
    const totalImages = options.reduce((sum, o) => sum + (o.variants || []).length, 0);
    const cost = result.total_cost_usd || 0;

    console.log(`  Batch ID:    ${colored((result.id || '').slice(0, 16) + '...', C.cyan)}`);
    console.log(`  Prompt:      ${(result.prompt || '').slice(0, 80)}${(result.prompt || '').length > 80 ? '...' : ''}`);
    console.log(`  Model:       ${colored(result.image_model || '', C.bold)}`);
    console.log(`  Dimensions:  ${result.width || '?'}x${result.height || '?'}`);
    console.log(`  Options:     ${options.length}`);
    console.log(`  Total imgs:  ${colored(String(totalImages), C.green)}`);
    console.log(`  Downloaded:  ${downloaded.length} file(s)`);
    if (asyncJobs.length > 0) console.log(`  Async jobs:  ${asyncJobs.length}`);
    if (cost) console.log(`  Est. cost:   ${colored(`~$${cost.toFixed(4)}`, C.yellow)}`);
    console.log(`  Elapsed:     ${(elapsedMs / 1000).toFixed(1)}s`);

    if (downloaded.length > 0) {
        console.log(`\n  ${C.bold}Output files:${C.reset}`);
        for (const fp of downloaded) console.log(`    ${C.dim}${fp}${C.reset}`);
    }
}


// ── CLI argument parsing ────────────────────────────────────────────────────

function parseCli() {
    const { values } = parseArgs({
        options: {
            prompt:          { type: 'string' },
            model:           { type: 'string' },
            'asset-type':    { type: 'string', default: 'photorealistic' },
            width:           { type: 'string', default: '1024' },
            height:          { type: 'string', default: '1024' },
            options:         { type: 'string', default: '2' },
            variations:      { type: 'string', default: '2' },
            output:          { type: 'string', default: 'output' },
            'skip-classify': { type: 'boolean', default: false },
            'skip-decompose':{ type: 'boolean', default: false },
            help:            { type: 'boolean', short: 'h', default: false },
        },
        strict: false,
    });

    if (values.help) {
        console.log(`
ArtSmoker Image Generation - Node.js API Sample

Usage:
  node imageGen_node.js [options]

Options:
  --prompt TEXT           Image generation prompt (interactive if not provided)
  --model KEY             Model key (e.g. nova_canvas, sd35_large)
  --asset-type TYPE       photorealistic|game_asset|character|environment|icon|marketing_banner
  --width N               Image width (default: 1024)
  --height N              Image height (default: 1024)
  --options N             Number of concept options 1-5 (default: 2; server default is 5)
  --variations N          Number of seed variations 1-5 (default: 2; server default is 5)
  --output DIR            Output directory (default: output)
  --skip-classify         Skip asset type classification
  --skip-decompose        Skip prompt decomposition
  --help, -h              Show this help message

Examples:
  node imageGen_node.js --prompt "a medieval castle on a cliff"
  node imageGen_node.js --prompt "cyberpunk warrior" --model sd35_large --options 3
`);
        process.exit(0);
    }

    const clamp = (n, lo, hi, dflt) => {
        const v = parseInt(n, 10);
        if (Number.isNaN(v)) return dflt;
        return Math.min(hi, Math.max(lo, v));
    };

    return {
        prompt:         values.prompt || null,
        model:          values.model || null,
        assetType:      values['asset-type'] || 'photorealistic',
        width:          parseInt(values.width, 10) || 1024,
        height:         parseInt(values.height, 10) || 1024,
        numOptions:     clamp(values.options, 1, 5, 2),
        numVariations:  clamp(values.variations, 1, 5, 2),
        outputDir:      values.output || 'output',
        skipClassify:   values['skip-classify'] || false,
        skipDecompose:  values['skip-decompose'] || false,
    };
}


// ── Interactive prompt (stdin) ──────────────────────────────────────────────

function readLine(question) {
    return new Promise(resolve => {
        process.stdout.write(question);
        process.stdin.setEncoding('utf8');
        process.stdin.resume();
        process.stdin.once('data', data => {
            process.stdin.pause();
            resolve(data.toString().trim());
        });
    });
}


// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
    const args = parseCli();

    printHeader('ArtSmoker Image Generation');
    console.log(`  Server: ${colored(BASE_URL, C.cyan)}`);

    // Check server connectivity.
    try {
        await getJson('/api/admin/models/image-options');
    } catch (e) {
        console.log(`\n  ${C.red}Cannot connect to ArtSmoker at ${BASE_URL}`);
        console.log(`  Make sure the server is running:${C.reset}`);
        console.log(`  ${C.dim}  cd /path/to/ArtSmoker`);
        console.log(`    source .venv/bin/activate`);
        console.log(`    uvicorn backend.main:app --reload${C.reset}`);
        process.exit(1);
    }

    const startTime = Date.now();

    // Step 1: List models.
    const models = await listModels();
    if (models.length === 0) {
        console.log(`  ${C.red}No models available. Check your ArtSmoker configuration.${C.reset}`);
        process.exit(1);
    }

    // Select model.
    let modelKey = args.model;
    if (!modelKey) {
        const defaultKey = models[0]?.key || 'nova_canvas';
        if (!args.prompt) {
            const input = await readLine(`\n  Enter model key (or press Enter for '${defaultKey}'):\n  ${C.cyan}>${C.reset} `);
            modelKey = input || defaultKey;
        } else {
            modelKey = defaultKey;
        }
    }

    const validKeys = models.map(m => m.key || '');
    if (!validKeys.includes(modelKey)) {
        console.log(`\n  ${C.red}Unknown model: '${modelKey}'${C.reset}`);
        console.log(`  Available: ${validKeys.join(', ')}`);
        process.exit(1);
    }
    console.log(`\n  Using model: ${colored(modelKey, C.green)}`);

    // Get prompt.
    let prompt = args.prompt;
    if (!prompt) {
        prompt = await readLine(`\n  Enter your image prompt:\n  ${C.cyan}>${C.reset} `);
        if (!prompt) {
            console.log(`  ${C.red}Prompt cannot be empty.${C.reset}`);
            process.exit(1);
        }
    }

    let assetType = args.assetType;

    // Step 2: Classify asset type (optional).
    if (!args.skipClassify) {
        try {
            assetType = await classifyAssetType(prompt, assetType);
        } catch (e) {
            console.log(`  ${C.yellow}Classification skipped: ${e.message}${C.reset}`);
        }
    }

    // Step 3: Decompose prompt (optional — provenance/preview only).
    if (!args.skipDecompose) {
        try {
            await decomposePrompt(prompt, assetType, modelKey);
        } catch (e) {
            console.log(`  ${C.yellow}Decomposition skipped: ${e.message}${C.reset}`);
        }
    }

    // Step 4: Generate images.
    let genResult;
    try {
        genResult = await generateImages(
            prompt, modelKey, assetType,
            args.width, args.height,
            args.numOptions, args.numVariations,
        );
    } catch (e) {
        console.log(`\n  ${C.red}Generation failed: ${e.message}${C.reset}`);
        process.exit(1);
    }

    const resultData = genResult.result;
    const asyncJobs = genResult.asyncJobs;

    // Step 5: Poll async jobs if any (self-hosted / SageMaker models).
    if (asyncJobs.length > 0) {
        const completed = await pollAsyncJobs(asyncJobs);
        // Resolve each completed job's asset back onto its variant so it downloads.
        if (completed.length > 0 && resultData) {
            for (const option of (resultData.options || [])) {
                for (const variant of (option.variants || [])) {
                    const jobId = variant.async_job?.job_id;
                    if (!jobId) continue;
                    const comp = completed.find(j => j.job_id === jobId && j.status === 'complete');
                    if (comp) {
                        variant.id = comp.asset_id || variant.id;
                        variant.png_path = comp.image_path || `/api/gallery/${variant.id}/png`;
                    }
                }
            }
        }
    }

    // Step 6: Download images.
    const downloaded = resultData ? await downloadImages(resultData, args.outputDir) : [];

    // Summary.
    printSummary(resultData || {}, downloaded, asyncJobs, Date.now() - startTime);
}

main().catch(e => {
    console.error(`${C.red}Fatal error: ${e.message}${C.reset}`);
    process.exit(1);
});
