#!/usr/bin/env node
/**
 * ArtSmoker Image Generation — Node.js API Sample
 * =================================================
 *
 * Demonstrates the full ArtSmoker image generation pipeline:
 *   1. List available models          GET  /api/admin/models/image-options
 *   2. Classify asset type            POST /api/refine-prompt/classify-asset-type
 *   3. Decompose the prompt           POST /api/refine-prompt/decompose
 *   4. Generate images via SSE        POST /api/generate/stream
 *   5. Poll for async job completion   GET  /api/generate/async-jobs
 *   6. Download completed images      GET  /api/gallery/{asset_id}/png
 *
 * Prerequisites:
 *   - Node.js 18+ (uses built-in fetch and streams)
 *   - ArtSmoker server running at http://localhost:8000
 *
 * Setup (run once in the api-samples/ directory):
 *   npm init -y && npm pkg set type=module && npm install eventsource-parser
 *
 * How to run:
 *   node imageGen_node.js
 *   node imageGen_node.js --prompt "a medieval castle on a cliff" --model nova_canvas
 *   node imageGen_node.js --prompt "a cyberpunk warrior" --width 1024 --height 1024 --options 2 --variations 2
 *
 * Full API docs:     http://localhost:8000/docs
 * Detailed spec:     See SPEC.md in the project root
 *
 * Environment:
 *   ARTSMOKER_URL — base URL (default: http://localhost:8000)
 */

import { createParser } from 'eventsource-parser';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { parseArgs } from 'util';

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
        option_complete: C.green,
        async_submitted: C.cyan,
        done:            C.green,
        complete:        C.green,
        error:           C.red,
        image_error:     C.red,
    };
    const color = colorMap[type] || C.dim;
    console.log(`  ${color}[${type}]${C.reset} ${message}`);
}


// ── HTTP helpers ────────────────────────────────────────────────────────────

/** POST JSON and return parsed response. */
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

/** GET JSON and return parsed response. */
async function getJson(path, timeoutMs = 10000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const resp = await fetch(`${BASE_URL}${path}`, {
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


// ── Step 1: List available models ───────────────────────────────────────────

async function listModels() {
    /**
     * Fetch available image generation models from the server.
     *
     * GET /api/admin/models/image-options returns the list of enabled
     * text-to-image models with their metadata (label, region, pricing).
     */
    printStep(1, 'Fetching available image models...');
    const models = await getJson('/api/admin/models/image-options');
    console.log(`  Found ${colored(String(models.length), C.green)} available models:`);
    for (const m of models) {
        const key = m.key || '';
        const label = m.label || key;
        const region = m.region || '';
        const price = m.base_price_usd || 0;
        console.log(`    ${C.dim}-${C.reset} ${colored(key, C.bold)} (${label}) [${region}] ~$${price.toFixed(4)}/image`);
    }
    return models;
}


// ── Step 2: Classify asset type ─────────────────────────────────────────────

async function classifyAssetType(prompt, currentType = 'photorealistic') {
    /**
     * Auto-classify the ideal asset type for the given prompt.
     *
     * POST /api/refine-prompt/classify-asset-type
     * The server uses an LLM to determine whether the prompt better matches
     * a different asset type (e.g., 'character' instead of 'game_asset').
     */
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
    } else {
        console.log(`  Asset type '${colored(currentType, C.green)}' is appropriate for this prompt.`);
        return currentType;
    }
}


// ── Step 3: Decompose prompt ────────────────────────────────────────────────

async function decomposePrompt(prompt, assetType, model = '') {
    /**
     * Decompose the user prompt into structured visual components.
     *
     * POST /api/refine-prompt/decompose
     * Returns a JSON structure with editable fields: subject, scene,
     * composition, lighting, style (including color palette with hex values).
     */
    printStep(3, 'Decomposing prompt into visual components...');
    const result = await postJson('/api/refine-prompt/decompose', {
        prompt,
        asset_type: assetType,
        image_model: model,
    }, 60000);

    // Display the decomposed components
    for (const [sectionName, sectionData] of Object.entries(result)) {
        if (sectionName.startsWith('_')) continue;  // Skip metadata
        if (typeof sectionData !== 'object' || Array.isArray(sectionData)) continue;
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


// ── Step 4: Generate images via SSE ─────────────────────────────────────────

async function generateImages(prompt, model, assetType, width = 1024, height = 1024, numOptions = 2, numVariations = 2) {
    /**
     * Generate images using the SSE streaming endpoint.
     *
     * POST /api/generate/stream
     * The server sends Server-Sent Events with real-time progress:
     *   - started:          Generation batch has begun
     *   - stage:            Pipeline stage update (prompts, generating, etc.)
     *   - prompts_ready:    Enhanced prompts are ready
     *   - image_done:       A single image variant completed (Bedrock models)
     *   - async_submitted:  Job submitted to SageMaker (custom models)
     *   - complete:         All images done, includes full result
     *   - error:            Something went wrong
     */
    printStep(4, 'Generating images via SSE stream...');

    // Build the generation request payload
    const payload = {
        prompt,
        image_model: model,
        asset_type: assetType,
        width,
        height,
        num_options: numOptions,
        num_variations: numVariations,
        // Reasonable defaults for API usage
        remove_background: false,
        generate_svg: false,
        upscale: false,
    };

    console.log(`  Payload: ${colored(JSON.stringify(payload, null, 2), C.dim)}`);

    // Open the SSE connection.
    // The /api/generate/stream endpoint returns text/event-stream.
    const resp = await fetch(`${BASE_URL}/api/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Generation failed: HTTP ${resp.status}: ${text.slice(0, 200)}`);
    }

    let resultData = null;
    const asyncJobs = [];
    let batchId = null;

    console.log(`\n  ${C.bold}--- SSE Events ---${C.reset}`);

    // Parse the SSE stream using eventsource-parser.
    // Node.js fetch returns a ReadableStream (Web Streams API).
    const parser = createParser({
        onEvent(event) {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch {
                return;  // Skip malformed data
            }

            const eventType = data.type || 'unknown';

            // Handle each event type
            switch (eventType) {
                case 'started': {
                    batchId = data.batch_id || '';
                    const total = data.total || 0;
                    printEvent(eventType, `Batch ${batchId.slice(0, 8)}... - generating ${total} images`);
                    break;
                }
                case 'stage': {
                    const stage = data.stage || '';
                    const message = data.message || '';
                    printEvent(eventType, `[${stage}] ${message}`);
                    break;
                }
                case 'prompts_ready': {
                    const prompts = data.prompts || [];
                    const negative = data.negative_prompt || '';
                    printEvent(eventType, `${prompts.length} enhanced prompt(s) ready`);
                    prompts.forEach((p, i) => {
                        const display = p.length > 120 ? p.slice(0, 120) + '...' : p;
                        console.log(`    ${C.dim}Prompt ${i + 1}: ${display}${C.reset}`);
                    });
                    if (negative) {
                        console.log(`    ${C.dim}Negative: ${negative.slice(0, 100)}${C.reset}`);
                    }
                    break;
                }
                case 'image_done': {
                    const opt = (data.option || 0) + 1;
                    const vari = (data.variation || 0) + 1;
                    const done = data.completed || 0;
                    const total = data.total || 0;
                    printEvent(eventType, `Option ${opt}, Variation ${vari} (${done}/${total} complete)`);
                    break;
                }
                case 'async_submitted': {
                    const jobId = data.job_id || '';
                    const modelLabel = data.model_label || '';
                    asyncJobs.push(jobId);
                    printEvent(eventType, `Async job ${jobId.slice(0, 12)}... (${modelLabel}) - will poll for completion`);
                    break;
                }
                case 'complete': {
                    resultData = data.result || data;
                    const summary = data.all_models_summary;
                    if (summary) {
                        printEvent(eventType, `All models: ${summary.summary || ''}`);
                    } else {
                        const options = resultData.options || [];
                        const totalImages = options.reduce((sum, o) => sum + (o.variants || []).length, 0);
                        printEvent(eventType, `Done! ${totalImages} images generated`);
                    }
                    break;
                }
                case 'error':
                case 'image_error': {
                    const error = data.detail || data.error || 'Unknown error';
                    printEvent(eventType, colored(error, C.red));
                    break;
                }
                case 'moderation_blocked': {
                    const msg = data.message || 'Content moderation blocked this prompt';
                    printEvent(eventType, colored(msg, C.red));
                    break;
                }
                case 'prompt_refused': {
                    const reason = data.reason || 'Prompt refused by the AI';
                    printEvent(eventType, colored(reason, C.red));
                    break;
                }
                default: {
                    printEvent(eventType, JSON.stringify(data).slice(0, 200));
                }
            }
        }
    });

    // Read the response body as a stream and feed it to the SSE parser.
    // Node.js 18+ fetch returns a ReadableStream (Web Streams API).
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        // Decode the chunk and feed to the parser
        const chunk = decoder.decode(value, { stream: true });
        parser.feed(chunk);
    }

    console.log(`  ${C.bold}--- End SSE ---${C.reset}\n`);

    return { result: resultData, asyncJobs, batchId };
}


// ── Step 5: Poll for async job completion ───────────────────────────────────

async function pollAsyncJobs(jobIds, timeoutMs = 600000) {
    /**
     * Poll for async job completion (SageMaker custom models).
     *
     * GET /api/generate/async-jobs
     * Returns all active and recent jobs with their statuses:
     *   - pending:    Job submitted, waiting for result
     *   - generating: Model is actively processing
     *   - complete:   Image is ready in the gallery
     *   - failed:     Job failed with an error
     *
     * Polls every 5 seconds until all jobs complete or timeout.
     */
    if (jobIds.length === 0) return [];

    printStep(5, `Polling ${jobIds.length} async job(s)...`);
    const start = Date.now();
    const completedJobs = [];
    const completedIds = new Set();

    while (Date.now() - start < timeoutMs) {
        const data = await getJson('/api/generate/async-jobs');
        const jobs = data.jobs || [];

        let pending = 0;
        for (const jid of jobIds) {
            const job = jobs.find(j => j.job_id === jid);
            if (!job) continue;

            if (job.status === 'complete' && !completedIds.has(jid)) {
                completedIds.add(jid);
                completedJobs.push(job);
                console.log(`  ${C.green}Job ${jid.slice(0, 12)}... completed! Asset: ${job.asset_id || ''}${C.reset}`);
            } else if (job.status === 'failed') {
                if (!completedIds.has(jid)) {
                    completedIds.add(jid);
                    completedJobs.push(job);
                    console.log(`  ${C.red}Job ${jid.slice(0, 12)}... failed: ${job.error || 'Unknown'}${C.reset}`);
                }
            } else {
                pending++;
                const elapsed = Math.round((Date.now() - start) / 1000);
                console.log(`  ${C.dim}Job ${jid.slice(0, 12)}... status: ${job.status} (${elapsed}s elapsed)${C.reset}`);
            }
        }

        if (pending === 0) break;

        // Wait 5 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 5000));
    }

    return completedJobs;
}


// ── Step 6: Download completed images ───────────────────────────────────────

async function downloadImages(result, outputDir = 'output') {
    /**
     * Download generated images from the gallery.
     *
     * GET /api/gallery/{asset_id}/png
     * Saves each image to the output directory with a descriptive filename.
     */
    if (!result) {
        console.log(`  ${C.yellow}No result data to download.${C.reset}`);
        return [];
    }

    printStep(6, 'Downloading generated images...');
    if (!existsSync(outputDir)) {
        mkdirSync(outputDir, { recursive: true });
    }

    const options = result.options || [];
    const downloaded = [];

    for (const option of options) {
        const optIdx = option.option_index || 0;
        const variants = option.variants || [];

        for (const variant of variants) {
            const assetId = variant.id || '';
            const pngPath = variant.png_path || '';
            const varIdx = variant.variant_index || 0;

            // Skip async jobs that haven't completed yet
            if (variant.async_job && !pngPath) {
                console.log(`  ${C.dim}Skipping opt${optIdx + 1}_var${varIdx + 1} (async pending)${C.reset}`);
                continue;
            }

            if (!assetId || !pngPath) continue;

            // Download the PNG
            const url = `${BASE_URL}${pngPath}`;
            try {
                const resp = await fetch(url);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

                const buffer = Buffer.from(await resp.arrayBuffer());
                const filename = `opt${optIdx + 1}_var${varIdx + 1}_${assetId}.png`;
                const filepath = join(outputDir, filename);
                writeFileSync(filepath, buffer);
                const sizeKb = (buffer.length / 1024).toFixed(1);
                downloaded.push(filepath);
                console.log(`  ${C.green}Saved:${C.reset} ${filepath} (${sizeKb} KB)`);
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

    if (!result) {
        console.log(`  ${C.red}No results produced.${C.reset}`);
        return;
    }

    const batchId = result.id || '';
    const prompt = result.prompt || '';
    const model = result.image_model || '';
    const options = result.options || [];
    const totalImages = options.reduce((sum, o) => sum + (o.variants || []).length, 0);
    const cost = result.total_cost_usd || 0;
    const elapsed = (elapsedMs / 1000).toFixed(1);

    console.log(`  Batch ID:    ${colored(batchId.slice(0, 16) + '...', C.cyan)}`);
    console.log(`  Prompt:      ${prompt.slice(0, 80)}${prompt.length > 80 ? '...' : ''}`);
    console.log(`  Model:       ${colored(model, C.bold)}`);
    console.log(`  Dimensions:  ${result.width || '?'}x${result.height || '?'}`);
    console.log(`  Options:     ${options.length}`);
    console.log(`  Total imgs:  ${colored(String(totalImages), C.green)}`);
    console.log(`  Downloaded:  ${downloaded.length} file(s)`);
    if (asyncJobs.length > 0) {
        console.log(`  Async jobs:  ${asyncJobs.length}`);
    }
    if (cost) {
        console.log(`  Est. cost:   ${colored(`~$${cost.toFixed(4)}`, C.yellow)}`);
    }
    console.log(`  Elapsed:     ${elapsed}s`);

    if (downloaded.length > 0) {
        console.log(`\n  ${C.bold}Output files:${C.reset}`);
        for (const fp of downloaded) {
            console.log(`    ${C.dim}${fp}${C.reset}`);
        }
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
  --options N             Number of concept options 1-5 (default: 2)
  --variations N          Number of seed variations 1-5 (default: 2)
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

    return {
        prompt:         values.prompt || null,
        model:          values.model || null,
        assetType:      values['asset-type'] || 'photorealistic',
        width:          parseInt(values.width) || 1024,
        height:         parseInt(values.height) || 1024,
        numOptions:     parseInt(values.options) || 2,
        numVariations:  parseInt(values.variations) || 2,
        outputDir:      values.output || 'output',
        skipClassify:   values['skip-classify'] || false,
        skipDecompose:  values['skip-decompose'] || false,
    };
}


// ── Interactive prompt (stdin) ──────────────────────────────────────────────

function readLine(question) {
    return new Promise(resolve => {
        process.stdout.write(question);
        let input = '';
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

    // Check server connectivity
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

    // Step 1: List models and select one
    const models = await listModels();
    if (models.length === 0) {
        console.log(`  ${C.red}No models available. Check your ArtSmoker configuration.${C.reset}`);
        process.exit(1);
    }

    // Select model
    let modelKey = args.model;
    if (!modelKey) {
        if (!args.prompt) {
            // Interactive model selection
            const defaultKey = models[0]?.key || 'nova_canvas';
            const input = await readLine(`\n  Enter model key (or press Enter for '${defaultKey}'):\n  ${C.cyan}>${C.reset} `);
            modelKey = input || defaultKey;
        } else {
            modelKey = models[0]?.key || 'nova_canvas';
        }
    }

    // Validate model key
    const validKeys = models.map(m => m.key || '');
    if (!validKeys.includes(modelKey)) {
        console.log(`\n  ${C.red}Unknown model: '${modelKey}'${C.reset}`);
        console.log(`  Available: ${validKeys.join(', ')}`);
        process.exit(1);
    }

    console.log(`\n  Using model: ${colored(modelKey, C.green)}`);

    // Get prompt
    let prompt = args.prompt;
    if (!prompt) {
        prompt = await readLine(`\n  Enter your image prompt:\n  ${C.cyan}>${C.reset} `);
        if (!prompt) {
            console.log(`  ${C.red}Prompt cannot be empty.${C.reset}`);
            process.exit(1);
        }
    }

    let assetType = args.assetType;

    // Step 2: Classify asset type (optional)
    if (!args.skipClassify) {
        try {
            assetType = await classifyAssetType(prompt, assetType);
        } catch (e) {
            console.log(`  ${C.yellow}Classification skipped: ${e.message}${C.reset}`);
        }
    }

    // Step 3: Decompose prompt (optional)
    if (!args.skipDecompose) {
        try {
            await decomposePrompt(prompt, assetType, modelKey);
        } catch (e) {
            console.log(`  ${C.yellow}Decomposition skipped: ${e.message}${C.reset}`);
        }
    }

    // Step 4: Generate images
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

    // Step 5: Poll async jobs if any (custom/SageMaker models)
    if (asyncJobs.length > 0) {
        const completed = await pollAsyncJobs(asyncJobs, 600000);
        // Update result with completed async job asset IDs
        if (completed.length > 0 && resultData) {
            for (const option of (resultData.options || [])) {
                for (const variant of (option.variants || [])) {
                    if (variant.async_job) {
                        const jobId = variant.async_job.job_id || '';
                        const comp = completed.find(
                            j => j.job_id === jobId && j.status === 'complete'
                        );
                        if (comp) {
                            variant.id = comp.asset_id || '';
                            variant.png_path = `/api/gallery/${variant.id}/png`;
                        }
                    }
                }
            }
        }
    }

    // Step 6: Download images
    const downloaded = resultData
        ? await downloadImages(resultData, args.outputDir)
        : [];

    // Summary
    const elapsed = Date.now() - startTime;
    printSummary(resultData || {}, downloaded, asyncJobs, elapsed);
}

main().catch(e => {
    console.error(`${C.red}Fatal error: ${e.message}${C.reset}`);
    process.exit(1);
});
