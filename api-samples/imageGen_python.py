#!/usr/bin/env python3
"""
ArtSmoker Image Generation — Python API Sample
================================================

Demonstrates the full ArtSmoker image generation pipeline:
  1. List available models          GET  /api/admin/models/image-options
  2. Classify asset type            POST /api/refine-prompt/classify-asset-type
  3. Decompose the prompt           POST /api/refine-prompt/decompose
  4. Generate images via SSE        POST /api/generate/stream
  5. Poll for async job completion   GET  /api/generate/async-jobs
  6. Download completed images      GET  /api/gallery/{asset_id}/png

Prerequisites:
  - Python 3.10+
  - pip install requests sseclient-py
  - ArtSmoker server running at http://localhost:8000

How to run:
  python imageGen_python.py
  python imageGen_python.py --prompt "a medieval castle on a cliff" --model nova_canvas
  python imageGen_python.py --prompt "a cyberpunk warrior" --width 1024 --height 1024 --options 2 --variations 2

Full API docs:     http://localhost:8000/docs
Detailed spec:     See SPEC.md in the project root

Environment:
  ARTSMOKER_URL  — base URL (default: http://localhost:8000)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("\033[91mError: 'requests' is not installed. Run: pip install requests\033[0m")
    sys.exit(1)

try:
    import sseclient
except ImportError:
    print("\033[91mError: 'sseclient-py' is not installed. Run: pip install sseclient-py\033[0m")
    sys.exit(1)


# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("ARTSMOKER_URL", "http://localhost:8000")

# ANSI color codes for terminal output
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"


def colored(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{Color.RESET}"


def print_header(title: str):
    """Print a styled section header."""
    width = 60
    print(f"\n{Color.CYAN}{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}{Color.RESET}\n")


def print_step(step: int, description: str):
    """Print a numbered step indicator."""
    print(f"{Color.BOLD}{Color.BLUE}[Step {step}]{Color.RESET} {description}")


def print_event(event_type: str, message: str):
    """Print an SSE event with color coding."""
    color_map = {
        "started":          Color.GREEN,
        "stage":            Color.YELLOW,
        "prompts_ready":    Color.MAGENTA,
        "image_done":       Color.GREEN,
        "option_complete":  Color.GREEN,
        "async_submitted":  Color.CYAN,
        "done":             Color.GREEN,
        "complete":         Color.GREEN,
        "error":            Color.RED,
        "image_error":      Color.RED,
    }
    color = color_map.get(event_type, Color.DIM)
    print(f"  {color}[{event_type}]{Color.RESET} {message}")


# ── Step 1: List available models ────────────────────────────────────────────

def list_models() -> list[dict]:
    """Fetch available image generation models from the server.

    GET /api/admin/models/image-options returns the list of enabled
    text-to-image models with their metadata (label, region, pricing).
    """
    print_step(1, "Fetching available image models...")
    url = f"{BASE_URL}/api/admin/models/image-options"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    models = resp.json()
    print(f"  Found {colored(str(len(models)), Color.GREEN)} available models:")
    for m in models:
        key = m.get("key", "")
        label = m.get("label", key)
        region = m.get("region", "")
        price = m.get("base_price_usd", 0)
        print(f"    {Color.DIM}-{Color.RESET} {colored(key, Color.BOLD)} ({label}) "
              f"[{region}] ~${price:.4f}/image")
    return models


# ── Step 2: Classify asset type ──────────────────────────────────────────────

def classify_asset_type(prompt: str, current_type: str = "photorealistic") -> str:
    """Auto-classify the ideal asset type for the given prompt.

    POST /api/refine-prompt/classify-asset-type
    The server uses an LLM to determine whether the prompt better matches
    a different asset type (e.g., 'character' instead of 'game_asset').
    """
    print_step(2, "Classifying asset type...")
    url = f"{BASE_URL}/api/refine-prompt/classify-asset-type"
    payload = {
        "prompt": prompt,
        "asset_type": current_type,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("mismatch"):
        suggested = result["suggested"]
        reason = result.get("reason", "")
        print(f"  {Color.YELLOW}Suggestion:{Color.RESET} Switch from "
              f"'{current_type}' to '{colored(suggested, Color.GREEN)}'")
        print(f"  {Color.DIM}Reason: {reason}{Color.RESET}")
        return suggested
    else:
        print(f"  Asset type '{colored(current_type, Color.GREEN)}' is appropriate for this prompt.")
        return current_type


# ── Step 3: Decompose prompt ─────────────────────────────────────────────────

def decompose_prompt(prompt: str, asset_type: str, model: str = "") -> dict:
    """Decompose the user prompt into structured visual components.

    POST /api/refine-prompt/decompose
    Returns a JSON structure with editable fields: subject, scene,
    composition, lighting, style (including color palette with hex values).
    """
    print_step(3, "Decomposing prompt into visual components...")
    url = f"{BASE_URL}/api/refine-prompt/decompose"
    payload = {
        "prompt": prompt,
        "asset_type": asset_type,
        "image_model": model,
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    result = resp.json()

    # Display the decomposed components
    for section_name, section_data in result.items():
        if section_name.startswith("_"):
            continue  # Skip metadata
        if not isinstance(section_data, dict):
            continue
        print(f"  {colored(section_name.upper(), Color.MAGENTA)}:")
        for field_name, field_data in section_data.items():
            if isinstance(field_data, dict) and "value" in field_data:
                value = field_data["value"]
                source = field_data.get("source", "")
                source_label = f" [{source}]" if source else ""
                print(f"    {field_name}: {Color.DIM}{value}{source_label}{Color.RESET}")
            elif isinstance(field_data, list):
                # Color palette is a list
                print(f"    {field_name}: [{len(field_data)} entries]")
            elif isinstance(field_data, str):
                print(f"    {field_name}: {Color.DIM}{field_data}{Color.RESET}")

    return result


# ── Step 4: Generate images via SSE ──────────────────────────────────────────

def generate_images(
    prompt: str,
    model: str,
    asset_type: str,
    width: int = 1024,
    height: int = 1024,
    num_options: int = 2,
    num_variations: int = 2,
) -> dict:
    """Generate images using the SSE streaming endpoint.

    POST /api/generate/stream
    The server sends Server-Sent Events with real-time progress:
      - started:          Generation batch has begun
      - stage:            Pipeline stage update (prompts, generating, etc.)
      - prompts_ready:    Enhanced prompts are ready
      - image_done:       A single image variant completed (Bedrock models)
      - option_complete:  An option with all variants completed
      - async_submitted:  Job submitted to SageMaker (custom models)
      - complete:         All images done, includes full result
      - error:            Something went wrong
    """
    print_step(4, "Generating images via SSE stream...")
    url = f"{BASE_URL}/api/generate/stream"

    # Build the generation request payload
    payload = {
        "prompt": prompt,
        "image_model": model,
        "asset_type": asset_type,
        "width": width,
        "height": height,
        "num_options": num_options,
        "num_variations": num_variations,
        # Reasonable defaults for API usage
        "remove_background": False,
        "generate_svg": False,
        "upscale": False,
    }

    print(f"  Payload: {colored(json.dumps(payload, indent=2), Color.DIM)}")

    # Open an SSE connection using sseclient-py.
    # The /api/generate/stream endpoint returns text/event-stream.
    resp = requests.post(url, json=payload, stream=True, timeout=300)
    resp.raise_for_status()
    client = sseclient.SSEClient(resp)

    result_data = None
    async_jobs = []
    batch_id = None

    print(f"\n  {Color.BOLD}--- SSE Events ---{Color.RESET}")

    for event in client.events():
        # Each SSE event has event.data as a JSON string
        try:
            data = json.loads(event.data)
        except json.JSONDecodeError:
            continue  # Skip keepalive comments or malformed data

        event_type = data.get("type", "unknown")

        # Handle each event type
        if event_type == "started":
            batch_id = data.get("batch_id", "")
            total = data.get("total", 0)
            print_event(event_type,
                        f"Batch {batch_id[:8]}... — generating {total} images")

        elif event_type == "stage":
            stage = data.get("stage", "")
            message = data.get("message", "")
            print_event(event_type, f"[{stage}] {message}")

        elif event_type == "prompts_ready":
            prompts = data.get("prompts", [])
            negative = data.get("negative_prompt", "")
            recomposed = data.get("recomposed_prompt", "")
            print_event(event_type,
                        f"{len(prompts)} enhanced prompt(s) ready")
            for i, p in enumerate(prompts):
                print(f"    {Color.DIM}Prompt {i+1}: {p[:120]}...{Color.RESET}"
                      if len(p) > 120 else
                      f"    {Color.DIM}Prompt {i+1}: {p}{Color.RESET}")
            if negative:
                print(f"    {Color.DIM}Negative: {negative[:100]}{Color.RESET}")

        elif event_type == "image_done":
            opt = data.get("option", 0)
            var = data.get("variation", 0)
            done = data.get("completed", 0)
            total = data.get("total", 0)
            print_event(event_type,
                        f"Option {opt+1}, Variation {var+1} "
                        f"({done}/{total} complete)")

        elif event_type == "option_complete":
            opt = data.get("option_index", 0)
            print_event(event_type, f"Option {opt+1} finished")

        elif event_type == "async_submitted":
            # Custom/SageMaker model — job submitted for async processing
            job_id = data.get("job_id", "")
            model_label = data.get("model_label", "")
            async_jobs.append(job_id)
            print_event(event_type,
                        f"Async job {job_id[:12]}... ({model_label}) — "
                        f"will poll for completion")

        elif event_type == "complete":
            result_data = data.get("result", data)
            summary = data.get("all_models_summary", {})
            if summary:
                print_event(event_type, f"All models: {summary.get('summary', '')}")
            else:
                options = result_data.get("options", [])
                total_images = sum(len(o.get("variants", [])) for o in options)
                print_event(event_type,
                            f"Done! {total_images} images generated")

        elif event_type in ("error", "image_error"):
            error = data.get("detail", data.get("error", "Unknown error"))
            print_event(event_type, colored(error, Color.RED))

        elif event_type == "moderation_blocked":
            msg = data.get("message", "Content moderation blocked this prompt")
            print_event(event_type, colored(msg, Color.RED))

        elif event_type == "prompt_refused":
            reason = data.get("reason", "Prompt refused by the AI")
            print_event(event_type, colored(reason, Color.RED))

        else:
            # Catch-all for any other event types
            print_event(event_type, json.dumps(data)[:200])

    print(f"  {Color.BOLD}--- End SSE ---{Color.RESET}\n")

    return {
        "result": result_data,
        "async_jobs": async_jobs,
        "batch_id": batch_id,
    }


# ── Step 5: Poll for async job completion ────────────────────────────────────

def poll_async_jobs(job_ids: list[str], timeout: int = 600) -> list[dict]:
    """Poll for async job completion (SageMaker custom models).

    GET /api/generate/async-jobs
    Returns all active and recent jobs with their statuses:
      - pending:    Job submitted, waiting for result
      - generating: Model is actively processing
      - complete:   Image is ready in the gallery
      - failed:     Job failed with an error

    Polls every 5 seconds until all jobs complete or timeout.
    """
    if not job_ids:
        return []

    print_step(5, f"Polling {len(job_ids)} async job(s)...")
    url = f"{BASE_URL}/api/generate/async-jobs"
    start = time.time()
    completed_jobs = []

    while time.time() - start < timeout:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])

        # Check status of our specific jobs
        pending = 0
        for jid in job_ids:
            job = next((j for j in jobs if j.get("job_id") == jid), None)
            if not job:
                continue
            status = job.get("status", "unknown")
            if status == "complete":
                if jid not in [cj.get("job_id") for cj in completed_jobs]:
                    completed_jobs.append(job)
                    asset_id = job.get("asset_id", "")
                    print(f"  {Color.GREEN}Job {jid[:12]}... completed! "
                          f"Asset: {asset_id}{Color.RESET}")
            elif status == "failed":
                error = job.get("error", "Unknown error")
                print(f"  {Color.RED}Job {jid[:12]}... failed: {error}{Color.RESET}")
                completed_jobs.append(job)
            else:
                pending += 1
                elapsed = int(time.time() - start)
                print(f"  {Color.DIM}Job {jid[:12]}... status: {status} "
                      f"({elapsed}s elapsed){Color.RESET}")

        if pending == 0:
            break

        # Wait before next poll
        time.sleep(5)  # nosemgrep: python.lang.best-practice.sleep.arbitrary-sleep -- deliberate poll interval (sample script)

    if pending > 0:
        print(f"  {Color.YELLOW}Warning: {pending} job(s) still pending "
              f"after {timeout}s timeout{Color.RESET}")

    return completed_jobs


# ── Step 6: Download completed images ────────────────────────────────────────

def download_images(result: dict, output_dir: str = "output") -> list[str]:
    """Download generated images from the gallery.

    GET /api/gallery/{asset_id}/png
    Saves each image to the output directory with a descriptive filename.
    """
    if not result:
        print(f"  {Color.YELLOW}No result data to download.{Color.RESET}")
        return []

    print_step(6, "Downloading generated images...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    options = result.get("options", [])
    downloaded = []

    for option in options:
        opt_idx = option.get("option_index", 0)
        variants = option.get("variants", [])

        for variant in variants:
            asset_id = variant.get("id", "")
            png_path = variant.get("png_path", "")
            var_idx = variant.get("variant_index", 0)

            # Skip async jobs that haven't completed yet
            if variant.get("async_job") and not png_path:
                print(f"  {Color.DIM}Skipping opt{opt_idx+1}_var{var_idx+1} "
                      f"(async pending){Color.RESET}")
                continue

            if not asset_id or not png_path:
                continue

            # Download the PNG
            url = f"{BASE_URL}{png_path}"
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()

                filename = f"opt{opt_idx+1}_var{var_idx+1}_{asset_id}.png"
                filepath = Path(output_dir) / filename
                filepath.write_bytes(resp.content)
                size_kb = len(resp.content) / 1024
                downloaded.append(str(filepath))
                print(f"  {Color.GREEN}Saved:{Color.RESET} {filepath} "
                      f"({size_kb:.1f} KB)")
            except requests.RequestException as e:
                print(f"  {Color.RED}Failed to download {asset_id}: {e}{Color.RESET}")

    return downloaded


# ── Results summary ──────────────────────────────────────────────────────────

def print_summary(
    result: dict,
    downloaded: list[str],
    async_jobs: list[str],
    elapsed: float,
):
    """Print a formatted summary of the generation results."""
    print_header("Generation Summary")

    if not result:
        print(f"  {Color.RED}No results produced.{Color.RESET}")
        return

    batch_id = result.get("id", "")
    prompt = result.get("prompt", "")
    model = result.get("image_model", "")
    options = result.get("options", [])
    total_images = sum(len(o.get("variants", [])) for o in options)
    cost = result.get("total_cost_usd", 0)

    print(f"  Batch ID:    {colored(batch_id[:16] + '...', Color.CYAN)}")
    print(f"  Prompt:      {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"  Model:       {colored(model, Color.BOLD)}")
    print(f"  Dimensions:  {result.get('width', '?')}x{result.get('height', '?')}")
    print(f"  Options:     {len(options)}")
    print(f"  Total imgs:  {colored(str(total_images), Color.GREEN)}")
    print(f"  Downloaded:  {len(downloaded)} file(s)")
    if async_jobs:
        print(f"  Async jobs:  {len(async_jobs)}")
    if cost:
        print(f"  Est. cost:   {colored(f'~${cost:.4f}', Color.YELLOW)}")
    print(f"  Elapsed:     {elapsed:.1f}s")

    if downloaded:
        print(f"\n  {Color.BOLD}Output files:{Color.RESET}")
        for fp in downloaded:
            print(f"    {Color.DIM}{fp}{Color.RESET}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ArtSmoker Image Generation — Python API Sample",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --prompt "a medieval castle on a cliff"
  %(prog)s --prompt "cyberpunk warrior" --model sd35_large --options 3
  %(prog)s --prompt "cute pixel art cat" --asset-type icon --width 512 --height 512
        """,
    )
    parser.add_argument("--prompt", type=str, default=None,
                        help="Image generation prompt (interactive if not provided)")
    parser.add_argument("--model", type=str, default=None,
                        help="Model key (e.g. nova_canvas, sd35_large)")
    parser.add_argument("--asset-type", type=str, default="photorealistic",
                        help="Asset type: photorealistic, game_asset, character, "
                             "environment, icon, marketing_banner (default: photorealistic)")
    parser.add_argument("--width", type=int, default=1024,
                        help="Image width (default: 1024)")
    parser.add_argument("--height", type=int, default=1024,
                        help="Image height (default: 1024)")
    parser.add_argument("--options", type=int, default=2,
                        help="Number of concept options 1-5 (default: 2)")
    parser.add_argument("--variations", type=int, default=2,
                        help="Number of seed variations 1-5 (default: 2)")
    parser.add_argument("--output", type=str, default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--skip-classify", action="store_true",
                        help="Skip asset type classification")
    parser.add_argument("--skip-decompose", action="store_true",
                        help="Skip prompt decomposition")
    args = parser.parse_args()

    print_header("ArtSmoker Image Generation")
    print(f"  Server: {colored(BASE_URL, Color.CYAN)}")

    # Check server connectivity
    try:
        resp = requests.get(f"{BASE_URL}/api/admin/models/image-options", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        print(f"\n  {Color.RED}Cannot connect to ArtSmoker at {BASE_URL}")
        print(f"  Make sure the server is running:{Color.RESET}")
        print(f"  {Color.DIM}  cd /path/to/ArtSmoker")
        print(f"    source .venv/bin/activate")
        print(f"    uvicorn backend.main:app --reload{Color.RESET}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"\n  {Color.RED}Server error: {e}{Color.RESET}")
        sys.exit(1)

    start_time = time.time()

    # Step 1: List models and select one
    models = list_models()
    if not models:
        print(f"  {Color.RED}No models available. Check your ArtSmoker configuration.{Color.RESET}")
        sys.exit(1)

    # Select model — from CLI arg, or interactive, or first available
    model_key = args.model
    if model_key is None:
        # Interactive model selection if not provided via CLI
        if args.prompt is None:
            print(f"\n  Enter model key (or press Enter for '{models[0].get('key', '')}'):")
            user_model = input(f"  {Color.CYAN}>{Color.RESET} ").strip()
            model_key = user_model if user_model else models[0].get("key", "nova_canvas")
        else:
            model_key = models[0].get("key", "nova_canvas")

    # Validate model key
    valid_keys = [m.get("key", "") for m in models]
    if model_key not in valid_keys:
        print(f"\n  {Color.RED}Unknown model: '{model_key}'{Color.RESET}")
        print(f"  Available: {', '.join(valid_keys)}")
        sys.exit(1)

    print(f"\n  Using model: {colored(model_key, Color.GREEN)}")

    # Get prompt — from CLI arg or interactive
    prompt = args.prompt
    if prompt is None:
        print(f"\n  Enter your image prompt:")
        prompt = input(f"  {Color.CYAN}>{Color.RESET} ").strip()
        if not prompt:
            print(f"  {Color.RED}Prompt cannot be empty.{Color.RESET}")
            sys.exit(1)

    asset_type = args.asset_type

    # Step 2: Classify asset type (optional)
    if not args.skip_classify:
        try:
            asset_type = classify_asset_type(prompt, asset_type)
        except requests.RequestException as e:
            print(f"  {Color.YELLOW}Classification skipped: {e}{Color.RESET}")

    # Step 3: Decompose prompt (optional)
    if not args.skip_decompose:
        try:
            decomposed = decompose_prompt(prompt, asset_type, model_key)
        except requests.RequestException as e:
            print(f"  {Color.YELLOW}Decomposition skipped: {e}{Color.RESET}")

    # Step 4: Generate images
    try:
        gen_result = generate_images(
            prompt=prompt,
            model=model_key,
            asset_type=asset_type,
            width=args.width,
            height=args.height,
            num_options=args.options,
            num_variations=args.variations,
        )
    except requests.RequestException as e:
        print(f"\n  {Color.RED}Generation failed: {e}{Color.RESET}")
        sys.exit(1)

    result_data = gen_result.get("result")
    async_jobs = gen_result.get("async_jobs", [])

    # Step 5: Poll async jobs if any (custom/SageMaker models)
    if async_jobs:
        completed = poll_async_jobs(async_jobs, timeout=600)
        # Update result with completed async job asset IDs
        if completed and result_data:
            for option in result_data.get("options", []):
                for variant in option.get("variants", []):
                    if variant.get("async_job"):
                        job_id = variant["async_job"].get("job_id", "")
                        comp = next(
                            (j for j in completed
                             if j.get("job_id") == job_id and j.get("status") == "complete"),
                            None,
                        )
                        if comp:
                            asset_id = comp.get("asset_id", "")
                            variant["id"] = asset_id
                            variant["png_path"] = f"/api/gallery/{asset_id}/png"

    # Step 6: Download images
    downloaded = download_images(result_data, args.output) if result_data else []

    # Summary
    elapsed = time.time() - start_time
    print_summary(result_data or {}, downloaded, async_jobs, elapsed)


if __name__ == "__main__":
    main()
