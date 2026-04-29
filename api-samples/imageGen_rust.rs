// ArtSmoker Image Generation — Rust API Sample
// ===============================================
//
// Demonstrates the full ArtSmoker image generation pipeline:
//   1. List available models          GET  /api/admin/models/image-options
//   2. Classify asset type            POST /api/refine-prompt/classify-asset-type
//   3. Decompose the prompt           POST /api/refine-prompt/decompose
//   4. Generate images via SSE        POST /api/generate/stream
//   5. Poll for async job completion   GET  /api/generate/async-jobs
//   6. Download completed images      GET  /api/gallery/{asset_id}/png
//
// Prerequisites:
//   - Rust 1.70+ with Cargo
//   - ArtSmoker server running at http://localhost:8000
//
// Dependencies — add to Cargo.toml:
//   ```toml
//   [package]
//   name = "artsmoker-sample"
//   version = "0.1.0"
//   edition = "2021"
//
//   [dependencies]
//   reqwest = { version = "0.12", features = ["json", "stream"] }
//   tokio = { version = "1", features = ["full"] }
//   serde = { version = "1", features = ["derive"] }
//   serde_json = "1"
//   futures-util = "0.3"
//   clap = { version = "4", features = ["derive"] }
//   ```
//
// How to run:
//   # Create a new project and copy this file as src/main.rs
//   cargo new artsmoker-sample && cp imageGen_rust.rs artsmoker-sample/src/main.rs
//   cd artsmoker-sample
//   # Add the dependencies above to Cargo.toml, then:
//   cargo run -- --prompt "a medieval castle on a cliff" --model nova_canvas
//   cargo run -- --prompt "a cyberpunk warrior" --width 1024 --height 1024 --options 2 --variations 2
//
// Full API docs:     http://localhost:8000/docs
// Detailed spec:     See SPEC.md in the project root
//
// Environment:
//   ARTSMOKER_URL — base URL (default: http://localhost:8000)

use clap::Parser;
use futures_util::StreamExt;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashSet;
use std::path::PathBuf;
use std::time::{Duration, Instant};

// ── Configuration ───────────────────────────────────────────────────────────

fn base_url() -> String {
    std::env::var("ARTSMOKER_URL").unwrap_or_else(|_| "http://localhost:8000".to_string())
}

// ANSI color codes for terminal output
mod color {
    pub const RESET: &str = "\x1b[0m";
    pub const BOLD: &str = "\x1b[1m";
    pub const DIM: &str = "\x1b[2m";
    pub const RED: &str = "\x1b[91m";
    pub const GREEN: &str = "\x1b[92m";
    pub const YELLOW: &str = "\x1b[93m";
    pub const BLUE: &str = "\x1b[94m";
    pub const MAGENTA: &str = "\x1b[95m";
    pub const CYAN: &str = "\x1b[96m";
}

fn print_header(title: &str) {
    let width = 60;
    println!("\n{}{}", color::CYAN, "=".repeat(width));
    println!("  {}", title);
    println!("{}{}\n", "=".repeat(width), color::RESET);
}

fn print_step(step: u32, description: &str) {
    println!(
        "{}{}[Step {}]{} {}",
        color::BOLD,
        color::BLUE,
        step,
        color::RESET,
        description
    );
}

fn print_event(event_type: &str, message: &str) {
    let c = match event_type {
        "started" | "image_done" | "option_complete" | "done" | "complete" => color::GREEN,
        "stage" => color::YELLOW,
        "prompts_ready" => color::MAGENTA,
        "async_submitted" => color::CYAN,
        "error" | "image_error" => color::RED,
        _ => color::DIM,
    };
    println!("  {}[{}]{} {}", c, event_type, color::RESET, message);
}

// ── Data types ──────────────────────────────────────────────────────────────

/// A model entry from /api/admin/models/image-options.
#[derive(Debug, Deserialize)]
struct ModelOption {
    key: Option<String>,
    label: Option<String>,
    region: Option<String>,
    base_price_usd: Option<f64>,
}

/// The full generation result from the SSE complete event.
#[derive(Debug, Deserialize)]
struct GenerationResult {
    id: Option<String>,
    prompt: Option<String>,
    image_model: Option<String>,
    width: Option<u32>,
    height: Option<u32>,
    options: Option<Vec<OptionResult>>,
    total_cost_usd: Option<f64>,
}

/// A single concept option with its variants.
#[derive(Debug, Deserialize)]
struct OptionResult {
    option_index: Option<u32>,
    enhanced_prompt: Option<String>,
    variants: Option<Vec<VariantResult>>,
}

/// A single image variant.
#[derive(Debug, Deserialize, Clone)]
struct VariantResult {
    id: Option<String>,
    variant_index: Option<u32>,
    png_path: Option<String>,
    async_job: Option<Value>,
}

/// Output from the generate step.
struct GenOutput {
    result: Option<GenerationResult>,
    async_jobs: Vec<String>,
    batch_id: String,
}

/// CLI arguments.
#[derive(Parser, Debug)]
#[command(
    name = "artsmoker-sample",
    about = "ArtSmoker Image Generation - Rust API Sample"
)]
struct Args {
    /// Image generation prompt (interactive if not provided)
    #[arg(long)]
    prompt: Option<String>,

    /// Model key (e.g. nova_canvas, sd35_large)
    #[arg(long)]
    model: Option<String>,

    /// Asset type: photorealistic, game_asset, character, environment, icon, marketing_banner
    #[arg(long, default_value = "photorealistic")]
    asset_type: String,

    /// Image width
    #[arg(long, default_value = "1024")]
    width: u32,

    /// Image height
    #[arg(long, default_value = "1024")]
    height: u32,

    /// Number of concept options (1-5)
    #[arg(long, default_value = "2")]
    options: u32,

    /// Number of seed variations (1-5)
    #[arg(long, default_value = "2")]
    variations: u32,

    /// Output directory
    #[arg(long, default_value = "output")]
    output: String,

    /// Skip asset type classification
    #[arg(long)]
    skip_classify: bool,

    /// Skip prompt decomposition
    #[arg(long)]
    skip_decompose: bool,
}

// ── Step 1: List available models ───────────────────────────────────────────

async fn list_models(client: &Client) -> Result<Vec<ModelOption>, Box<dyn std::error::Error>> {
    /// Fetch available image generation models from the server.
    ///
    /// GET /api/admin/models/image-options returns the list of enabled
    /// text-to-image models with their metadata (label, region, pricing).
    print_step(1, "Fetching available image models...");
    let url = format!("{}/api/admin/models/image-options", base_url());
    let models: Vec<ModelOption> = client.get(&url).send().await?.json().await?;
    println!(
        "  Found {}{}{} available models:",
        color::GREEN,
        models.len(),
        color::RESET
    );
    for m in &models {
        let key = m.key.as_deref().unwrap_or("");
        let label = m.label.as_deref().unwrap_or(key);
        let region = m.region.as_deref().unwrap_or("");
        let price = m.base_price_usd.unwrap_or(0.0);
        println!(
            "    {}- {}{}{} ({}) [{}] ~${:.4}/image",
            color::DIM,
            color::RESET,
            key,
            color::RESET,
            label,
            region,
            price
        );
    }
    Ok(models)
}

// ── Step 2: Classify asset type ─────────────────────────────────────────────

async fn classify_asset_type(
    client: &Client,
    prompt: &str,
    current_type: &str,
) -> Result<String, Box<dyn std::error::Error>> {
    /// Auto-classify the ideal asset type for the given prompt.
    ///
    /// POST /api/refine-prompt/classify-asset-type
    /// The server uses an LLM to determine whether the prompt better matches
    /// a different asset type (e.g., 'character' instead of 'game_asset').
    print_step(2, "Classifying asset type...");
    let url = format!("{}/api/refine-prompt/classify-asset-type", base_url());
    let body = serde_json::json!({
        "prompt": prompt,
        "asset_type": current_type,
    });
    let result: Value = client.post(&url).json(&body).send().await?.json().await?;

    if result["mismatch"].as_bool().unwrap_or(false) {
        let suggested = result["suggested"].as_str().unwrap_or(current_type);
        let reason = result["reason"].as_str().unwrap_or("");
        println!(
            "  {}Suggestion:{} Switch from '{}' to '{}{}{}'",
            color::YELLOW,
            color::RESET,
            current_type,
            color::GREEN,
            suggested,
            color::RESET
        );
        println!("  {}Reason: {}{}", color::DIM, reason, color::RESET);
        Ok(suggested.to_string())
    } else {
        println!(
            "  Asset type '{}{}{}' is appropriate for this prompt.",
            color::GREEN, current_type, color::RESET
        );
        Ok(current_type.to_string())
    }
}

// ── Step 3: Decompose prompt ────────────────────────────────────────────────

async fn decompose_prompt(
    client: &Client,
    prompt: &str,
    asset_type: &str,
    model: &str,
) -> Result<Value, Box<dyn std::error::Error>> {
    /// Decompose the user prompt into structured visual components.
    ///
    /// POST /api/refine-prompt/decompose
    /// Returns a JSON structure with editable fields: subject, scene,
    /// composition, lighting, style (including color palette with hex values).
    print_step(3, "Decomposing prompt into visual components...");
    let url = format!("{}/api/refine-prompt/decompose", base_url());
    let body = serde_json::json!({
        "prompt": prompt,
        "asset_type": asset_type,
        "image_model": model,
    });
    let result: Value = client.post(&url).json(&body).send().await?.json().await?;

    // Display the decomposed components
    if let Some(obj) = result.as_object() {
        for (section_name, section_data) in obj {
            if section_name.starts_with('_') {
                continue; // Skip metadata
            }
            if let Some(section_obj) = section_data.as_object() {
                println!(
                    "  {}{}{}:",
                    color::MAGENTA,
                    section_name.to_uppercase(),
                    color::RESET
                );
                for (field_name, field_data) in section_obj {
                    if let Some(field_obj) = field_data.as_object() {
                        if let Some(value) = field_obj.get("value") {
                            let source = field_obj
                                .get("source")
                                .and_then(|s| s.as_str())
                                .map(|s| format!(" [{}]", s))
                                .unwrap_or_default();
                            println!(
                                "    {}: {}{}{}{}",
                                field_name,
                                color::DIM,
                                value.as_str().unwrap_or(""),
                                source,
                                color::RESET
                            );
                        }
                    } else if let Some(arr) = field_data.as_array() {
                        println!("    {}: [{} entries]", field_name, arr.len());
                    } else if let Some(s) = field_data.as_str() {
                        println!("    {}: {}{}{}", field_name, color::DIM, s, color::RESET);
                    }
                }
            }
        }
    }
    Ok(result)
}

// ── Step 4: Generate images via SSE ─────────────────────────────────────────

async fn generate_images(
    client: &Client,
    prompt: &str,
    model: &str,
    asset_type: &str,
    width: u32,
    height: u32,
    num_options: u32,
    num_variations: u32,
) -> Result<GenOutput, Box<dyn std::error::Error>> {
    /// Generate images using the SSE streaming endpoint.
    ///
    /// POST /api/generate/stream
    /// The server sends Server-Sent Events with real-time progress:
    ///   - started:          Generation batch has begun
    ///   - stage:            Pipeline stage update (prompts, generating, etc.)
    ///   - prompts_ready:    Enhanced prompts are ready
    ///   - image_done:       A single image variant completed (Bedrock models)
    ///   - async_submitted:  Job submitted to SageMaker (custom models)
    ///   - complete:         All images done, includes full result
    ///   - error:            Something went wrong
    print_step(4, "Generating images via SSE stream...");

    // Build the generation request payload
    let payload = serde_json::json!({
        "prompt": prompt,
        "image_model": model,
        "asset_type": asset_type,
        "width": width,
        "height": height,
        "num_options": num_options,
        "num_variations": num_variations,
        "remove_background": false,
        "generate_svg": false,
        "upscale": false,
    });

    println!(
        "  Payload: {}{}{}",
        color::DIM,
        serde_json::to_string_pretty(&payload)?,
        color::RESET
    );

    // Open the SSE connection.
    // The /api/generate/stream endpoint returns text/event-stream.
    let url = format!("{}/api/generate/stream", base_url());
    let resp = client
        .post(&url)
        .json(&payload)
        .timeout(Duration::from_secs(300))
        .send()
        .await?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await?;
        return Err(format!("HTTP {}: {}", status, &body[..body.len().min(200)]).into());
    }

    let mut output = GenOutput {
        result: None,
        async_jobs: Vec::new(),
        batch_id: String::new(),
    };

    println!(
        "\n  {}--- SSE Events ---{}",
        color::BOLD,
        color::RESET
    );

    // Parse the SSE stream manually.
    // SSE format: "data: {json}\n\n" with optional ":" comment lines for keepalive.
    let mut stream = resp.bytes_stream();
    let mut buffer = String::new();

    while let Some(chunk) = stream.next().await {
        let chunk = chunk?;
        let text = String::from_utf8_lossy(&chunk);
        buffer.push_str(&text);

        // Process complete lines in the buffer
        while let Some(newline_pos) = buffer.find('\n') {
            let line = buffer[..newline_pos].trim_end().to_string();
            buffer = buffer[newline_pos + 1..].to_string();

            // Skip empty lines and keepalive comments
            if line.is_empty() || line.starts_with(':') {
                continue;
            }

            // SSE data lines start with "data: "
            if !line.starts_with("data: ") {
                continue;
            }

            let json_str = &line[6..]; // Strip "data: " prefix
            let data: Value = match serde_json::from_str(json_str) {
                Ok(v) => v,
                Err(_) => continue, // Skip malformed data
            };

            let event_type = data["type"].as_str().unwrap_or("unknown");

            // Handle each event type
            match event_type {
                "started" => {
                    let batch_id = data["batch_id"].as_str().unwrap_or("");
                    let total = data["total"].as_u64().unwrap_or(0);
                    output.batch_id = batch_id.to_string();
                    let display_id = &batch_id[..batch_id.len().min(8)];
                    print_event(
                        event_type,
                        &format!("Batch {}... - generating {} images", display_id, total),
                    );
                }
                "stage" => {
                    let stage = data["stage"].as_str().unwrap_or("");
                    let message = data["message"].as_str().unwrap_or("");
                    print_event(event_type, &format!("[{}] {}", stage, message));
                }
                "prompts_ready" => {
                    let prompts = data["prompts"].as_array();
                    let negative = data["negative_prompt"].as_str().unwrap_or("");
                    let count = prompts.map_or(0, |p| p.len());
                    print_event(
                        event_type,
                        &format!("{} enhanced prompt(s) ready", count),
                    );
                    if let Some(prompts) = prompts {
                        for (i, p) in prompts.iter().enumerate() {
                            let ps = p.as_str().unwrap_or("");
                            let display = if ps.len() > 120 {
                                format!("{}...", &ps[..120])
                            } else {
                                ps.to_string()
                            };
                            println!(
                                "    {}Prompt {}: {}{}",
                                color::DIM,
                                i + 1,
                                display,
                                color::RESET
                            );
                        }
                    }
                    if !negative.is_empty() {
                        let display = &negative[..negative.len().min(100)];
                        println!(
                            "    {}Negative: {}{}",
                            color::DIM, display, color::RESET
                        );
                    }
                }
                "image_done" => {
                    let opt = data["option"].as_u64().unwrap_or(0);
                    let var = data["variation"].as_u64().unwrap_or(0);
                    let done = data["completed"].as_u64().unwrap_or(0);
                    let total = data["total"].as_u64().unwrap_or(0);
                    print_event(
                        event_type,
                        &format!(
                            "Option {}, Variation {} ({}/{} complete)",
                            opt + 1,
                            var + 1,
                            done,
                            total
                        ),
                    );
                }
                "async_submitted" => {
                    let job_id = data["job_id"].as_str().unwrap_or("");
                    let model_label = data["model_label"].as_str().unwrap_or("");
                    output.async_jobs.push(job_id.to_string());
                    let display_id = &job_id[..job_id.len().min(12)];
                    print_event(
                        event_type,
                        &format!(
                            "Async job {}... ({}) - will poll for completion",
                            display_id, model_label
                        ),
                    );
                }
                "complete" => {
                    // Parse the full result from the complete event
                    let result_value = data.get("result").unwrap_or(&data);
                    if let Ok(result) =
                        serde_json::from_value::<GenerationResult>(result_value.clone())
                    {
                        let total_images: usize = result
                            .options
                            .as_ref()
                            .map_or(0, |opts| {
                                opts.iter()
                                    .map(|o| o.variants.as_ref().map_or(0, |v| v.len()))
                                    .sum()
                            });
                        print_event(
                            event_type,
                            &format!("Done! {} images generated", total_images),
                        );
                        output.result = Some(result);
                    }
                }
                "error" | "image_error" => {
                    let error = data["detail"]
                        .as_str()
                        .or_else(|| data["error"].as_str())
                        .unwrap_or("Unknown error");
                    print_event(
                        event_type,
                        &format!("{}{}{}", color::RED, error, color::RESET),
                    );
                }
                "moderation_blocked" => {
                    let msg = data["message"]
                        .as_str()
                        .unwrap_or("Content moderation blocked this prompt");
                    print_event(
                        event_type,
                        &format!("{}{}{}", color::RED, msg, color::RESET),
                    );
                }
                "prompt_refused" => {
                    let reason = data["reason"]
                        .as_str()
                        .unwrap_or("Prompt refused by the AI");
                    print_event(
                        event_type,
                        &format!("{}{}{}", color::RED, reason, color::RESET),
                    );
                }
                _ => {
                    let s = serde_json::to_string(&data).unwrap_or_default();
                    let display = &s[..s.len().min(200)];
                    print_event(event_type, display);
                }
            }
        }
    }

    println!(
        "  {}--- End SSE ---{}",
        color::BOLD,
        color::RESET
    );
    println!();

    Ok(output)
}

// ── Step 5: Poll for async job completion ───────────────────────────────────

async fn poll_async_jobs(
    client: &Client,
    job_ids: &[String],
    timeout: Duration,
) -> Vec<Value> {
    /// Poll for async job completion (SageMaker custom models).
    ///
    /// GET /api/generate/async-jobs
    /// Returns all active and recent jobs with their statuses.
    /// Polls every 5 seconds until all jobs complete or timeout.
    if job_ids.is_empty() {
        return Vec::new();
    }

    print_step(5, &format!("Polling {} async job(s)...", job_ids.len()));
    let start = Instant::now();
    let mut completed_jobs: Vec<Value> = Vec::new();
    let mut completed_ids: HashSet<String> = HashSet::new();

    while start.elapsed() < timeout {
        let url = format!("{}/api/generate/async-jobs", base_url());
        let data: Value = match client.get(&url).send().await {
            Ok(resp) => match resp.json().await {
                Ok(v) => v,
                Err(_) => {
                    tokio::time::sleep(Duration::from_secs(5)).await;
                    continue;
                }
            },
            Err(_) => {
                tokio::time::sleep(Duration::from_secs(5)).await;
                continue;
            }
        };

        let jobs = data["jobs"].as_array();
        let mut pending = 0;

        for jid in job_ids {
            // Find this job in the response
            let job = jobs.and_then(|js| {
                js.iter().find(|j| j["job_id"].as_str() == Some(jid.as_str()))
            });
            let Some(job) = job else { continue };

            let status = job["status"].as_str().unwrap_or("unknown");
            match status {
                "complete" => {
                    if !completed_ids.contains(jid) {
                        completed_ids.insert(jid.clone());
                        completed_jobs.push(job.clone());
                        let asset_id = job["asset_id"].as_str().unwrap_or("");
                        println!(
                            "  {}Job {}... completed! Asset: {}{}",
                            color::GREEN,
                            &jid[..jid.len().min(12)],
                            asset_id,
                            color::RESET
                        );
                    }
                }
                "failed" => {
                    if !completed_ids.contains(jid) {
                        completed_ids.insert(jid.clone());
                        completed_jobs.push(job.clone());
                        let err = job["error"].as_str().unwrap_or("Unknown");
                        println!(
                            "  {}Job {}... failed: {}{}",
                            color::RED,
                            &jid[..jid.len().min(12)],
                            err,
                            color::RESET
                        );
                    }
                }
                _ => {
                    pending += 1;
                    let elapsed = start.elapsed().as_secs();
                    println!(
                        "  {}Job {}... status: {} ({}s elapsed){}",
                        color::DIM,
                        &jid[..jid.len().min(12)],
                        status,
                        elapsed,
                        color::RESET
                    );
                }
            }
        }

        if pending == 0 {
            break;
        }

        // Wait 5 seconds before next poll
        tokio::time::sleep(Duration::from_secs(5)).await;
    }

    completed_jobs
}

// ── Step 6: Download completed images ───────────────────────────────────────

async fn download_images(
    client: &Client,
    result: &GenerationResult,
    output_dir: &str,
) -> Vec<String> {
    /// Download generated images from the gallery.
    ///
    /// GET /api/gallery/{asset_id}/png
    /// Saves each image to the output directory with a descriptive filename.
    print_step(6, "Downloading generated images...");
    let dir = PathBuf::from(output_dir);
    if let Err(e) = std::fs::create_dir_all(&dir) {
        println!(
            "  {}Failed to create output dir: {}{}",
            color::RED, e, color::RESET
        );
        return Vec::new();
    }

    let mut downloaded = Vec::new();

    let options = match &result.options {
        Some(opts) => opts,
        None => return downloaded,
    };

    for option in options {
        let opt_idx = option.option_index.unwrap_or(0);
        let variants = match &option.variants {
            Some(v) => v,
            None => continue,
        };

        for variant in variants {
            let asset_id = variant.id.as_deref().unwrap_or("");
            let png_path = variant.png_path.as_deref().unwrap_or("");
            let var_idx = variant.variant_index.unwrap_or(0);

            // Skip async jobs that haven't completed yet
            if variant.async_job.is_some() && png_path.is_empty() {
                println!(
                    "  {}Skipping opt{}_var{} (async pending){}",
                    color::DIM,
                    opt_idx + 1,
                    var_idx + 1,
                    color::RESET
                );
                continue;
            }

            if asset_id.is_empty() || png_path.is_empty() {
                continue;
            }

            // Download the PNG
            let url = format!("{}{}", base_url(), png_path);
            match client.get(&url).send().await {
                Ok(resp) => {
                    if !resp.status().is_success() {
                        println!(
                            "  {}Failed to download {}: HTTP {}{}",
                            color::RED,
                            asset_id,
                            resp.status(),
                            color::RESET
                        );
                        continue;
                    }
                    match resp.bytes().await {
                        Ok(bytes) => {
                            let filename =
                                format!("opt{}_var{}_{}.png", opt_idx + 1, var_idx + 1, asset_id);
                            let filepath = dir.join(&filename);
                            if let Err(e) = std::fs::write(&filepath, &bytes) {
                                println!(
                                    "  {}Failed to write {}: {}{}",
                                    color::RED,
                                    filepath.display(),
                                    e,
                                    color::RESET
                                );
                                continue;
                            }
                            let size_kb = bytes.len() as f64 / 1024.0;
                            let path_str = filepath.to_string_lossy().to_string();
                            println!(
                                "  {}Saved:{} {} ({:.1} KB)",
                                color::GREEN,
                                color::RESET,
                                path_str,
                                size_kb
                            );
                            downloaded.push(path_str);
                        }
                        Err(e) => {
                            println!(
                                "  {}Failed to read body for {}: {}{}",
                                color::RED, asset_id, e, color::RESET
                            );
                        }
                    }
                }
                Err(e) => {
                    println!(
                        "  {}Failed to download {}: {}{}",
                        color::RED, asset_id, e, color::RESET
                    );
                }
            }
        }
    }

    downloaded
}

// ── Results summary ─────────────────────────────────────────────────────────

fn print_summary(
    result: &Option<GenerationResult>,
    downloaded: &[String],
    async_jobs: &[String],
    elapsed: Duration,
) {
    print_header("Generation Summary");

    let result = match result {
        Some(r) => r,
        None => {
            println!("  {}No results produced.{}", color::RED, color::RESET);
            return;
        }
    };

    let total_images: usize = result.options.as_ref().map_or(0, |opts| {
        opts.iter()
            .map(|o| o.variants.as_ref().map_or(0, |v| v.len()))
            .sum()
    });

    let batch_id = result.id.as_deref().unwrap_or("");
    let display_id = if batch_id.len() > 16 {
        format!("{}...", &batch_id[..16])
    } else {
        batch_id.to_string()
    };

    let prompt = result.prompt.as_deref().unwrap_or("");
    let display_prompt = if prompt.len() > 80 {
        format!("{}...", &prompt[..80])
    } else {
        prompt.to_string()
    };

    let model = result.image_model.as_deref().unwrap_or("?");
    let num_options = result.options.as_ref().map_or(0, |o| o.len());

    println!(
        "  Batch ID:    {}{}{}",
        color::CYAN, display_id, color::RESET
    );
    println!("  Prompt:      {}", display_prompt);
    println!(
        "  Model:       {}{}{}",
        color::BOLD, model, color::RESET
    );
    println!(
        "  Dimensions:  {}x{}",
        result.width.unwrap_or(0),
        result.height.unwrap_or(0)
    );
    println!("  Options:     {}", num_options);
    println!(
        "  Total imgs:  {}{}{}",
        color::GREEN, total_images, color::RESET
    );
    println!("  Downloaded:  {} file(s)", downloaded.len());
    if !async_jobs.is_empty() {
        println!("  Async jobs:  {}", async_jobs.len());
    }
    if let Some(cost) = result.total_cost_usd {
        if cost > 0.0 {
            println!(
                "  Est. cost:   {}~${:.4}{}",
                color::YELLOW, cost, color::RESET
            );
        }
    }
    println!("  Elapsed:     {:.1}s", elapsed.as_secs_f64());

    if !downloaded.is_empty() {
        println!(
            "\n  {}Output files:{}",
            color::BOLD, color::RESET
        );
        for fp in downloaded {
            println!("    {}{}{}", color::DIM, fp, color::RESET);
        }
    }
}

// ── Interactive stdin reader ────────────────────────────────────────────────

fn read_line(prompt_text: &str) -> String {
    eprint!("{}", prompt_text);
    let mut input = String::new();
    std::io::stdin()
        .read_line(&mut input)
        .expect("Failed to read input");
    input.trim().to_string()
}

// ── Main ────────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let client = Client::builder()
        .timeout(Duration::from_secs(60))
        .build()?;

    print_header("ArtSmoker Image Generation");
    println!(
        "  Server: {}{}{}",
        color::CYAN,
        base_url(),
        color::RESET
    );

    // Check server connectivity
    let test_url = format!("{}/api/admin/models/image-options", base_url());
    if client.get(&test_url).send().await.is_err() {
        println!(
            "\n  {}Cannot connect to ArtSmoker at {}",
            color::RED,
            base_url()
        );
        println!("  Make sure the server is running:{}", color::RESET);
        println!("  {}  cd /path/to/ArtSmoker", color::DIM);
        println!("    source .venv/bin/activate");
        println!(
            "    uvicorn backend.main:app --reload{}",
            color::RESET
        );
        std::process::exit(1);
    }

    let start_time = Instant::now();

    // Step 1: List models and select one
    let models = list_models(&client)?;
    if models.is_empty() {
        println!(
            "  {}No models available. Check your ArtSmoker configuration.{}",
            color::RED, color::RESET
        );
        std::process::exit(1);
    }

    // Select model — from CLI arg, or interactive, or first available
    let model_key = if let Some(ref m) = args.model {
        m.clone()
    } else if args.prompt.is_none() {
        // Interactive model selection
        let default_key = models[0].key.as_deref().unwrap_or("nova_canvas");
        let input = read_line(&format!(
            "\n  Enter model key (or press Enter for '{}'):\n  {}>{} ",
            default_key, color::CYAN, color::RESET
        ));
        if input.is_empty() {
            default_key.to_string()
        } else {
            input
        }
    } else {
        models[0]
            .key
            .as_deref()
            .unwrap_or("nova_canvas")
            .to_string()
    };

    // Validate model key
    let valid_keys: Vec<&str> = models
        .iter()
        .filter_map(|m| m.key.as_deref())
        .collect();
    if !valid_keys.contains(&model_key.as_str()) {
        println!(
            "\n  {}Unknown model: '{}'{}",
            color::RED, model_key, color::RESET
        );
        println!("  Available: {}", valid_keys.join(", "));
        std::process::exit(1);
    }

    println!(
        "\n  Using model: {}{}{}",
        color::GREEN, model_key, color::RESET
    );

    // Get prompt — from CLI arg or interactive
    let prompt = if let Some(ref p) = args.prompt {
        p.clone()
    } else {
        let input = read_line(&format!(
            "\n  Enter your image prompt:\n  {}>{} ",
            color::CYAN, color::RESET
        ));
        if input.is_empty() {
            println!("  {}Prompt cannot be empty.{}", color::RED, color::RESET);
            std::process::exit(1);
        }
        input
    };

    let mut asset_type = args.asset_type.clone();

    // Step 2: Classify asset type (optional)
    if !args.skip_classify {
        match classify_asset_type(&client, &prompt, &asset_type).await {
            Ok(suggested) => asset_type = suggested,
            Err(e) => println!(
                "  {}Classification skipped: {}{}",
                color::YELLOW, e, color::RESET
            ),
        }
    }

    // Step 3: Decompose prompt (optional)
    if !args.skip_decompose {
        match decompose_prompt(&client, &prompt, &asset_type, &model_key).await {
            Ok(_) => {}
            Err(e) => println!(
                "  {}Decomposition skipped: {}{}",
                color::YELLOW, e, color::RESET
            ),
        }
    }

    // Step 4: Generate images
    let gen_result = generate_images(
        &client,
        &prompt,
        &model_key,
        &asset_type,
        args.width,
        args.height,
        args.options,
        args.variations,
    )
    .await?;

    // Step 5: Poll async jobs if any (custom/SageMaker models)
    let mut result = gen_result.result;
    if !gen_result.async_jobs.is_empty() {
        let completed =
            poll_async_jobs(&client, &gen_result.async_jobs, Duration::from_secs(600)).await;
        // Update result with completed async job asset IDs
        if !completed.is_empty() {
            if let Some(ref mut res) = result {
                if let Some(ref mut options) = res.options {
                    for option in options.iter_mut() {
                        if let Some(ref mut variants) = option.variants {
                            for variant in variants.iter_mut() {
                                if variant.async_job.is_some() {
                                    if let Some(job_id) = variant
                                        .async_job
                                        .as_ref()
                                        .and_then(|j| j["job_id"].as_str())
                                    {
                                        for c in &completed {
                                            if c["job_id"].as_str() == Some(job_id)
                                                && c["status"].as_str() == Some("complete")
                                            {
                                                if let Some(aid) = c["asset_id"].as_str() {
                                                    variant.id = Some(aid.to_string());
                                                    variant.png_path = Some(format!(
                                                        "/api/gallery/{}/png",
                                                        aid
                                                    ));
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Step 6: Download images
    let downloaded = if let Some(ref res) = result {
        download_images(&client, res, &args.output).await
    } else {
        Vec::new()
    };

    // Summary
    let elapsed = start_time.elapsed();
    print_summary(&result, &downloaded, &gen_result.async_jobs, elapsed);

    Ok(())
}
