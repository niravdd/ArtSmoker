// ArtSmoker Image Generation — Go API Sample
// =============================================
//
// A self-contained, end-to-end client for the ArtSmoker image-generation API.
// It drives the full pipeline and saves the finished PNGs to disk:
//
//   1. List available models          GET  /api/admin/models/image-options
//   2. Classify asset type (optional) POST /api/refine-prompt/classify-asset-type
//   3. Decompose the prompt (optional) POST /api/refine-prompt/decompose
//   4. Generate images via SSE        POST /api/generate/stream
//   5. Poll for async job completion   GET  /api/generate/async-jobs
//   6. Download completed images      GET  /api/gallery/{asset_id}/png
//
// Sync vs async: Amazon Bedrock models return images inline over the SSE
// stream (event "image_done"). Self-hosted SageMaker models return
// "async_submitted" and finish in the background — this sample then polls
// /api/generate/async-jobs until each job is "complete" or "failed" before
// downloading.
//
// Prerequisites:
//   - Go 1.21+ (uses the built-in min())
//   - No external dependencies — Go standard library only
//   - A running ArtSmoker server (default: http://localhost:8000) with at
//     least one image model enabled. Bedrock models work out of the box with
//     valid AWS credentials; custom SageMaker models must be deployed first.
//
// How to run:
//   go run imageGen_go.go
//   go run imageGen_go.go -prompt "a medieval castle on a cliff" -model nova_canvas
//   go run imageGen_go.go -prompt "a cyberpunk warrior" -width 1024 -height 1024 -options 2 -variations 2
//
// Cost note: num_options × num_variations = the number of images per model, and
// each image is a billed model call. The server DEFAULTS both to 5 (25 images).
// This sample defaults to 2 × 2 = 4 images so a test run stays quick and cheap.
//
// Post-processing note: the server DEFAULTS remove_background AND generate_svg to
// TRUE. This sample sends both as false to keep the raw generated image (see the
// GenerationRequest struct — the booleans are deliberately NOT `omitempty`, so a
// false value is actually transmitted rather than silently dropped).
//
// Full API docs:     http://localhost:8000/docs   (live Swagger — source of truth)
// Detailed spec:     SPEC.md in the project root
// Skill / contract:  api-samples/skill.md
//
// Environment:
//   ARTSMOKER_URL — base URL (default: http://localhost:8000)

package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// ── Configuration ───────────────────────────────────────────────────────────

// nosemgrep -- documented default for the local sample; overridden by ARTSMOKER_URL below
var baseURL = "http://localhost:8000"

func init() {
	if env := os.Getenv("ARTSMOKER_URL"); env != "" {
		baseURL = env
	}
}

// ANSI color codes for terminal output
const (
	colorReset   = "\033[0m"
	colorBold    = "\033[1m"
	colorDim     = "\033[2m"
	colorRed     = "\033[91m"
	colorGreen   = "\033[92m"
	colorYellow  = "\033[93m"
	colorBlue    = "\033[94m"
	colorMagenta = "\033[95m"
	colorCyan    = "\033[96m"
)

func colored(text, color string) string {
	return color + text + colorReset
}

func printHeader(title string) {
	width := 60
	fmt.Printf("\n%s%s\n", colorCyan, strings.Repeat("=", width))
	fmt.Printf("  %s\n", title)
	fmt.Printf("%s%s\n\n", strings.Repeat("=", width), colorReset)
}

func printStep(step int, description string) {
	fmt.Printf("%s%s[Step %d]%s %s\n", colorBold, colorBlue, step, colorReset, description)
}

func printEvent(eventType, message string) {
	colorMap := map[string]string{
		"started":               colorGreen,
		"stage":                 colorYellow,
		"prompts_ready":         colorMagenta,
		"image_done":            colorGreen,
		"model_status":          colorGreen,
		"async_submitted":       colorCyan,
		"asset_type_suggestion": colorYellow,
		"complete":              colorGreen,
		"error":                 colorRed,
		"image_error":           colorRed,
		"moderation_blocked":    colorRed,
		"prompt_refused":        colorRed,
	}
	color, ok := colorMap[eventType]
	if !ok {
		color = colorDim
	}
	fmt.Printf("  %s[%s]%s %s\n", color, eventType, colorReset, message)
}

// truncate shortens a string for display (rune-safe enough for logging).
func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

// ── HTTP helpers ────────────────────────────────────────────────────────────

var httpClient = &http.Client{Timeout: 60 * time.Second}

// postJSON sends a POST request with a JSON body and decodes the response.
func postJSON(path string, body, result interface{}) error {
	payload, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}
	resp, err := httpClient.Post(baseURL+path, "application/json", bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("POST %s: %w", path, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodyBytes[:min(len(bodyBytes), 400)]))
	}
	return json.NewDecoder(resp.Body).Decode(result)
}

// getJSON sends a GET request and decodes the JSON response.
func getJSON(path string, result interface{}) error {
	resp, err := httpClient.Get(baseURL + path)
	if err != nil {
		return fmt.Errorf("GET %s: %w", path, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodyBytes[:min(len(bodyBytes), 400)]))
	}
	return json.NewDecoder(resp.Body).Decode(result)
}

// ── Step 1: List available models ───────────────────────────────────────────

// Model is one entry from /api/admin/models/image-options → "models".
type Model struct {
	Key         string `json:"key"`
	Label       string `json:"label"`
	Provider    string `json:"provider"`
	Region      string `json:"region"` // default (cheapest known) region
	ModelSource string `json:"model_source"`
	// base_price_usd may be null in the registry ("pricing unavailable"), so it
	// is a pointer — nil means no price is known (never assume $0).
	BasePriceUSD *float64 `json:"base_price_usd"`
}

// imageOptionsResponse is the ACTUAL envelope returned by the endpoint.
// NOTE: the endpoint returns an object {"models": [...], "available_regions": [...]},
// NOT a bare JSON array — decode into this wrapper, not into []Model directly.
type imageOptionsResponse struct {
	Models           []Model  `json:"models"`
	AvailableRegions []string `json:"available_regions"`
}

func fetchModels() ([]Model, error) {
	var resp imageOptionsResponse
	if err := getJSON("/api/admin/models/image-options", &resp); err != nil {
		return nil, err
	}
	return resp.Models, nil
}

func listModels() ([]Model, error) {
	printStep(1, "Fetching available image models...")
	models, err := fetchModels()
	if err != nil {
		return nil, err
	}
	fmt.Printf("  Found %s available models:\n", colored(fmt.Sprintf("%d", len(models)), colorGreen))
	for _, m := range models {
		label := m.Label
		if label == "" {
			label = m.Key
		}
		price := "price n/a"
		if m.BasePriceUSD != nil {
			price = fmt.Sprintf("~$%.4f/image", *m.BasePriceUSD)
		}
		source := m.ModelSource
		if source == "" {
			source = "foundation"
		}
		fmt.Printf("    %s-%s %s (%s) [%s | %s] %s\n",
			colorDim, colorReset, colored(m.Key, colorBold), label, m.Region, source, price)
	}
	return models, nil
}

// ── Step 2: Classify asset type ─────────────────────────────────────────────

func classifyAssetType(prompt, currentType string) (string, error) {
	// POST /api/refine-prompt/classify-asset-type (body: PromptRefineRequest).
	// An LLM decides whether the prompt better matches a different asset type.
	// Response when it disagrees:
	//   {"current","suggested","reason","confidence","mismatch": true}
	// Response when the current type is fine:
	//   {"current","suggested","mismatch": false}
	printStep(2, "Classifying asset type...")
	reqBody := map[string]string{
		"prompt":     prompt,
		"asset_type": currentType,
	}
	var result struct {
		Current   string `json:"current"`
		Suggested string `json:"suggested"`
		Reason    string `json:"reason"`
		Mismatch  bool   `json:"mismatch"`
	}
	if err := postJSON("/api/refine-prompt/classify-asset-type", reqBody, &result); err != nil {
		return currentType, err
	}

	if result.Mismatch && result.Suggested != "" {
		fmt.Printf("  %sSuggestion:%s Switch from '%s' to '%s'\n",
			colorYellow, colorReset, currentType, colored(result.Suggested, colorGreen))
		if result.Reason != "" {
			fmt.Printf("  %sReason: %s%s\n", colorDim, result.Reason, colorReset)
		}
		return result.Suggested, nil
	}
	fmt.Printf("  Asset type '%s' is appropriate for this prompt.\n", colored(currentType, colorGreen))
	return currentType, nil
}

// ── Step 3: Decompose prompt ────────────────────────────────────────────────

func decomposePrompt(prompt, assetType, model string) (map[string]interface{}, error) {
	// POST /api/refine-prompt/decompose (body: prompt, asset_type, image_model,
	// style_id). Returns structured sections (subject, scene, composition,
	// lighting, style) plus a "_meta" translation block. Each field is
	// {value, source} where source is "user" or "inferred".
	printStep(3, "Decomposing prompt into visual components...")
	reqBody := map[string]string{
		"prompt":      prompt,
		"asset_type":  assetType,
		"image_model": model,
	}
	var result map[string]interface{}
	if err := postJSON("/api/refine-prompt/decompose", reqBody, &result); err != nil {
		return nil, err
	}

	// Display the decomposed components (skip "_meta" and other underscore keys).
	for sectionName, sectionRaw := range result {
		if strings.HasPrefix(sectionName, "_") {
			continue
		}
		sectionData, ok := sectionRaw.(map[string]interface{})
		if !ok {
			continue
		}
		fmt.Printf("  %s:\n", colored(strings.ToUpper(sectionName), colorMagenta))
		for fieldName, fieldRaw := range sectionData {
			switch field := fieldRaw.(type) {
			case map[string]interface{}:
				if val, ok := field["value"]; ok {
					source := ""
					if s, ok := field["source"]; ok {
						source = fmt.Sprintf(" [%v]", s)
					}
					fmt.Printf("    %s: %s%v%s%s\n", fieldName, colorDim, val, source, colorReset)
				}
			case []interface{}:
				fmt.Printf("    %s: [%d entries]\n", fieldName, len(field))
			case string:
				fmt.Printf("    %s: %s%s%s\n", fieldName, colorDim, field, colorReset)
			}
		}
	}
	return result, nil
}

// ── Step 4: Generate images via SSE ─────────────────────────────────────────

// GenerationRequest mirrors backend/models/generation_request.py.
//
// Struct-tag discipline (READ THIS before adding fields):
//   - Booleans the server defaults to TRUE (remove_background, generate_svg)
//     must NOT use `omitempty` — otherwise a false value is dropped from the
//     JSON and the server silently re-enables the default. They are sent
//     unconditionally here.
//   - Truly optional fields use pointers + `omitempty` so they are sent ONLY
//     when set, letting the server apply its own defaults otherwise.
type GenerationRequest struct {
	Prompt        string `json:"prompt"`
	ImageModel    string `json:"image_model"`
	AssetType     string `json:"asset_type"`
	Width         int    `json:"width"`
	Height        int    `json:"height"`
	NumOptions    int    `json:"num_options"`    // 1–5; server default 5
	NumVariations int    `json:"num_variations"` // 1–5; server default 5

	// Post-processing — sent explicitly (no omitempty) so `false` is transmitted.
	RemoveBackground bool `json:"remove_background"` // server default TRUE
	GenerateSVG      bool `json:"generate_svg"`      // server default TRUE
	Upscale          bool `json:"upscale"`           // server default false (extra cost)

	// Optional — only encoded when set.
	Seed    *int64  `json:"seed,omitempty"`    // base seed 0…2^31-1 (nil = server-random)
	Quality *string `json:"quality,omitempty"` // model-specific tier, e.g. "standard"
	Region  *string `json:"region,omitempty"`  // override the model's AWS region

	// Multi-model generation (leave zero/nil for the simple single-model path).
	// Set AllModels=true to fan out across every enabled model, or list specific
	// keys in SelectedModels. ModelOptimizedPrompts tailors the enhanced prompt
	// per model — only meaningful with AllModels/SelectedModels.
	AllModels             bool     `json:"all_models,omitempty"`
	SelectedModels        []string `json:"selected_models,omitempty"`
	ModelOptimizedPrompts bool     `json:"model_optimized_prompts,omitempty"`

	// Reference-guided generation (advanced — omitted on the default path). To
	// use it, supply 1–3 base64-encoded PNGs in ReferenceImages and set
	// ReferenceMode to "inspired" (vision-LLM writes a prompt, any text-to-image
	// model renders), "match" (pixel-faithful edit via a deployed edit model), or
	// "remix" (Stability image-to-image at a strength ladder).
	ReferenceImages []string `json:"reference_images,omitempty"`
	ReferenceMode   string   `json:"reference_mode,omitempty"`
}

// GenerationResult mirrors backend/models/generation_result.py (the payload of
// the SSE "complete" event, under "result").
type GenerationResult struct {
	ID           string         `json:"id"` // batch_id
	Prompt       string         `json:"prompt"`
	ImageModel   string         `json:"image_model"` // "all_models" in multi-model mode
	AssetType    string         `json:"asset_type"`
	Width        int            `json:"width"`
	Height       int            `json:"height"`
	AllModels    bool           `json:"all_models"`
	Options      []OptionResult `json:"options"`
	BlockedCount int            `json:"blocked_count"`
	TotalCostUSD float64        `json:"total_cost_usd"`
}

// OptionResult holds a single concept option with its variants.
type OptionResult struct {
	OptionIndex    int             `json:"option_index"`
	EnhancedPrompt string          `json:"enhanced_prompt"`
	ImageModel     string          `json:"image_model"`
	ModelLabel     string          `json:"model_label"`
	Status         string          `json:"status"` // "success" | "moderation_blocked" | "error"
	Variants       []VariantResult `json:"variants"`
}

// VariantResult holds a single image variant.
type VariantResult struct {
	ID           string                 `json:"id"`
	VariantIndex int                    `json:"variant_index"`
	PNGPath      string                 `json:"png_path"` // "" while an async job is pending
	AsyncJob     map[string]interface{} `json:"async_job"`
}

// GenOutput is the return value from generateImages.
type GenOutput struct {
	Result    *GenerationResult
	AsyncJobs []string
	BatchID   string
}

func generateImages(req GenerationRequest) (*GenOutput, error) {
	// POST /api/generate/stream returns text/event-stream. The Go standard
	// library has no SSE client, so we parse the stream by hand below.
	printStep(4, "Generating images via SSE stream...")

	payloadBytes, _ := json.MarshalIndent(req, "  ", "  ")
	fmt.Printf("  Payload: %s%s%s\n", colorDim, string(payloadBytes), colorReset)

	// Long timeout — a full batch can take minutes (especially cold custom models).
	sseClient := &http.Client{Timeout: 15 * time.Minute}
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}
	resp, err := sseClient.Post(baseURL+"/api/generate/stream", "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("SSE connect: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodyBytes[:min(len(bodyBytes), 400)]))
	}

	output := &GenOutput{}
	fmt.Printf("\n  %s--- SSE Events ---%s\n", colorBold, colorReset)

	// SSE framing: an event is a run of lines terminated by a blank line. A
	// line beginning ":" is a comment/keepalive. We accumulate consecutive
	// "data:" lines (per spec they are joined with "\n") and dispatch on blank.
	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 0, 256*1024), 4*1024*1024) // large buffer for big result payloads

	var dataBuf []string
	flush := func() {
		if len(dataBuf) == 0 {
			return
		}
		handleSSEEvent(strings.Join(dataBuf, "\n"), output)
		dataBuf = dataBuf[:0]
	}

	for scanner.Scan() {
		line := strings.TrimRight(scanner.Text(), "\r")
		if line == "" {
			flush() // end of one event
			continue
		}
		if strings.HasPrefix(line, ":") {
			continue // comment / keepalive
		}
		if strings.HasPrefix(line, "data:") {
			dataBuf = append(dataBuf, strings.TrimPrefix(strings.TrimPrefix(line, "data:"), " "))
		}
		// Other SSE fields (event:, id:, retry:) are unused by this API.
	}
	flush() // dispatch a trailing event with no terminating blank line

	if err := scanner.Err(); err != nil {
		fmt.Printf("  %sSSE read error: %s%s\n", colorRed, err, colorReset)
	}

	fmt.Printf("  %s--- End SSE ---%s\n\n", colorBold, colorReset)
	return output, nil
}

// handleSSEEvent parses one SSE data payload and updates output. The event
// names match what backend/routers/generate.py actually emits — note the skill
// flow-diagram aliases: the code emits "image_done" (not "option_complete") and
// "complete" (not "done").
func handleSSEEvent(jsonStr string, output *GenOutput) {
	var data map[string]interface{}
	if err := json.Unmarshal([]byte(jsonStr), &data); err != nil {
		return // skip malformed / partial data
	}
	eventType, _ := data["type"].(string)

	switch eventType {
	case "asset_type_suggestion":
		suggested, _ := data["suggested"].(string)
		printEvent(eventType, fmt.Sprintf("Consider asset type '%s' for this prompt", suggested))

	case "started":
		batchID, _ := data["batch_id"].(string)
		total, _ := data["total"].(float64)
		output.BatchID = batchID
		printEvent(eventType, fmt.Sprintf("Batch %s — generating %.0f image(s)", truncate(batchID, 8), total))

	case "stage":
		stage, _ := data["stage"].(string)
		message, _ := data["message"].(string)
		printEvent(eventType, fmt.Sprintf("[%s] %s", stage, message))

	case "prompts_ready":
		prompts, _ := data["prompts"].([]interface{})
		negative, _ := data["negative_prompt"].(string)
		printEvent(eventType, fmt.Sprintf("%d enhanced prompt(s) ready", len(prompts)))
		for i, p := range prompts {
			ps, _ := p.(string)
			fmt.Printf("    %sPrompt %d: %s%s\n", colorDim, i+1, truncate(ps, 120), colorReset)
		}
		if negative != "" {
			fmt.Printf("    %sNegative: %s%s\n", colorDim, truncate(negative, 100), colorReset)
		}

	case "image_done": // single-model: one image finished (Bedrock, inline)
		opt, _ := data["option"].(float64)
		vari, _ := data["variation"].(float64)
		done, _ := data["completed"].(float64)
		total, _ := data["total"].(float64)
		printEvent(eventType, fmt.Sprintf("Option %.0f, Variation %.0f (%.0f/%.0f complete)",
			opt+1, vari+1, done, total))

	case "model_status": // all-models mode: per (model, concept, variation) result
		label, _ := data["model_label"].(string)
		status, _ := data["status"].(string)
		done, _ := data["completed"].(float64)
		total, _ := data["total"].(float64)
		printEvent(eventType, fmt.Sprintf("%s → %s (%.0f/%.0f)", label, status, done, total))

	case "async_submitted": // self-hosted SageMaker model queued a background job
		jobID, _ := data["job_id"].(string)
		modelLabel, _ := data["model_label"].(string)
		if jobID != "" {
			output.AsyncJobs = append(output.AsyncJobs, jobID)
		}
		printEvent(eventType, fmt.Sprintf("Async job %s (%s) — will poll for completion",
			truncate(jobID, 12), modelLabel))

	case "complete": // terminal success event — carries the full GenerationResult
		resultRaw, ok := data["result"]
		if !ok {
			resultRaw = data
		}
		resultBytes, _ := json.Marshal(resultRaw)
		var result GenerationResult
		if err := json.Unmarshal(resultBytes, &result); err == nil {
			output.Result = &result
		}
		totalImages := 0
		for _, opt := range result.Options {
			totalImages += len(opt.Variants)
		}
		printEvent(eventType, fmt.Sprintf("Done! %d image(s) in result", totalImages))

	case "image_error":
		detail, _ := data["error"].(string)
		if detail == "" {
			detail = "Unknown error"
		}
		printEvent(eventType, colored(detail, colorRed))

	case "error": // terminal failure from the streaming endpoint
		detail, _ := data["detail"].(string)
		if detail == "" {
			detail, _ = data["error"].(string)
		}
		if detail == "" {
			detail = "Unknown error"
		}
		printEvent(eventType, colored(detail, colorRed))

	case "moderation_blocked":
		msg, _ := data["message"].(string)
		if msg == "" {
			msg = "Content moderation blocked this generation"
		}
		printEvent(eventType, colored(msg, colorRed))

	case "prompt_refused":
		reason, _ := data["reason"].(string)
		if reason == "" {
			reason = "Prompt refused by the AI"
		}
		printEvent(eventType, colored(reason, colorRed))

	default:
		printEvent(eventType, truncate(jsonStr, 200))
	}
}

// ── Step 5: Poll for async job completion ───────────────────────────────────

func pollAsyncJobs(jobIDs []string, timeout time.Duration) []map[string]interface{} {
	// GET /api/generate/async-jobs → {"jobs": [...], "pending_count", "has_active"}.
	// Each job has: job_id, status ("pending"|"generating"|"complete"|"failed"),
	// asset_id, model_label, image_path, error, queue_position, queue_total.
	// Poll every ~10s until all our jobs are complete/failed or we time out.
	if len(jobIDs) == 0 {
		return nil
	}

	printStep(5, fmt.Sprintf("Polling %d async job(s)...", len(jobIDs)))
	start := time.Now()
	completedJobs := make([]map[string]interface{}, 0)
	completedIDs := make(map[string]bool)

	for time.Since(start) < timeout {
		var data struct {
			Jobs []map[string]interface{} `json:"jobs"`
		}
		if err := getJSON("/api/generate/async-jobs", &data); err != nil {
			fmt.Printf("  %sPoll error: %s%s\n", colorRed, err, colorReset)
			time.Sleep(10 * time.Second)
			continue
		}

		pending := 0
		for _, jid := range jobIDs {
			var job map[string]interface{}
			for _, j := range data.Jobs {
				if id, _ := j["job_id"].(string); id == jid {
					job = j
					break
				}
			}
			if job == nil {
				continue
			}

			status, _ := job["status"].(string)
			switch status {
			case "complete":
				if !completedIDs[jid] {
					completedIDs[jid] = true
					completedJobs = append(completedJobs, job)
					assetID, _ := job["asset_id"].(string)
					fmt.Printf("  %sJob %s completed! Asset: %s%s\n",
						colorGreen, truncate(jid, 12), assetID, colorReset)
				}
			case "failed":
				if !completedIDs[jid] {
					completedIDs[jid] = true
					completedJobs = append(completedJobs, job)
					errMsg, _ := job["error"].(string)
					fmt.Printf("  %sJob %s failed: %s%s\n",
						colorRed, truncate(jid, 12), errMsg, colorReset)
				}
			default: // "pending" | "generating"
				pending++
				elapsed := int(time.Since(start).Seconds())
				pos := ""
				if p, ok := job["queue_position"].(float64); ok {
					pos = fmt.Sprintf(", queue #%.0f", p)
				}
				fmt.Printf("  %sJob %s status: %s (%ds elapsed%s)%s\n",
					colorDim, truncate(jid, 12), status, elapsed, pos, colorReset)
			}
		}

		if pending == 0 {
			break
		}
		time.Sleep(10 * time.Second)
	}

	return completedJobs
}

// ── Step 6: Download completed images ───────────────────────────────────────

func downloadImages(result *GenerationResult, outputDir string) []string {
	// GET /api/gallery/{asset_id}/png returns the PNG bytes. We build the URL
	// from each variant's asset id, saving to a descriptive filename.
	if result == nil {
		fmt.Printf("  %sNo result data to download.%s\n", colorYellow, colorReset)
		return nil
	}

	printStep(6, "Downloading generated images...")
	// nosemgrep -- 0o700 is least-privilege for a directory (owner needs execute to traverse); 0o600 would be unusable
	if err := os.MkdirAll(outputDir, 0o700); err != nil {
		fmt.Printf("  %sFailed to create output dir: %s%s\n", colorRed, err, colorReset)
		return nil
	}

	var downloaded []string

	for _, option := range result.Options {
		optIdx := option.OptionIndex
		for _, variant := range option.Variants {
			assetID := variant.ID

			// Skip async jobs that haven't completed yet (no PNG path resolved).
			if variant.PNGPath == "" {
				fmt.Printf("  %sSkipping opt%d_var%d (async pending or no image)%s\n",
					colorDim, optIdx+1, variant.VariantIndex+1, colorReset)
				continue
			}
			if assetID == "" {
				continue
			}

			// Download via the canonical gallery route (never trust a relative
			// path blindly — build it from the asset id we know).
			url := baseURL + fmt.Sprintf("/api/gallery/%s/png", assetID)
			resp, err := httpClient.Get(url)
			if err != nil {
				fmt.Printf("  %sFailed to download %s: %s%s\n", colorRed, assetID, err, colorReset)
				continue
			}
			imgBytes, readErr := io.ReadAll(resp.Body)
			status := resp.StatusCode
			resp.Body.Close()
			if readErr != nil || status >= 400 {
				fmt.Printf("  %sFailed to download %s: HTTP %d%s\n", colorRed, assetID, status, colorReset)
				continue
			}

			filename := fmt.Sprintf("opt%d_var%d_%s.png", optIdx+1, variant.VariantIndex+1, assetID)
			outPath := filepath.Join(outputDir, filename)
			if err := os.WriteFile(outPath, imgBytes, 0o644); err != nil {
				fmt.Printf("  %sFailed to write %s: %s%s\n", colorRed, outPath, err, colorReset)
				continue
			}

			downloaded = append(downloaded, outPath)
			fmt.Printf("  %sSaved:%s %s (%.1f KB)\n", colorGreen, colorReset, outPath, float64(len(imgBytes))/1024)
		}
	}

	return downloaded
}

// ── Results summary ─────────────────────────────────────────────────────────

func printSummary(result *GenerationResult, downloaded, asyncJobs []string, elapsed time.Duration) {
	printHeader("Generation Summary")

	if result == nil {
		fmt.Printf("  %sNo results produced.%s\n", colorRed, colorReset)
		return
	}

	totalImages := 0
	for _, opt := range result.Options {
		totalImages += len(opt.Variants)
	}

	fmt.Printf("  Batch ID:    %s\n", colored(truncate(result.ID, 16), colorCyan))
	fmt.Printf("  Prompt:      %s\n", truncate(result.Prompt, 80))
	fmt.Printf("  Model:       %s\n", colored(result.ImageModel, colorBold))
	fmt.Printf("  Dimensions:  %dx%d\n", result.Width, result.Height)
	fmt.Printf("  Options:     %d\n", len(result.Options))
	fmt.Printf("  Total imgs:  %s\n", colored(fmt.Sprintf("%d", totalImages), colorGreen))
	fmt.Printf("  Downloaded:  %d file(s)\n", len(downloaded))
	if len(asyncJobs) > 0 {
		fmt.Printf("  Async jobs:  %d\n", len(asyncJobs))
	}
	if result.BlockedCount > 0 {
		fmt.Printf("  Blocked:     %d (content moderation on specific seeds)\n", result.BlockedCount)
	}
	if result.TotalCostUSD > 0 {
		fmt.Printf("  Est. cost:   %s\n", colored(fmt.Sprintf("~$%.4f", result.TotalCostUSD), colorYellow))
	}
	fmt.Printf("  Elapsed:     %.1fs\n", elapsed.Seconds())

	if len(downloaded) > 0 {
		fmt.Printf("\n  %sOutput files:%s\n", colorBold, colorReset)
		for _, fp := range downloaded {
			fmt.Printf("    %s%s%s\n", colorDim, fp, colorReset)
		}
	}
}

// ── Interactive stdin reader ────────────────────────────────────────────────

func readLine(prompt string) string {
	fmt.Print(prompt)
	scanner := bufio.NewScanner(os.Stdin)
	if scanner.Scan() {
		return strings.TrimSpace(scanner.Text())
	}
	return ""
}

// ── Main ────────────────────────────────────────────────────────────────────

func main() {
	promptFlag := flag.String("prompt", "", "Image generation prompt (interactive if not provided)")
	modelFlag := flag.String("model", "", "Model key (e.g. nova_canvas, sd35_large)")
	assetTypeFlag := flag.String("asset-type", "photorealistic", "Asset type: photorealistic, game_asset, character, environment, icon, marketing_banner")
	widthFlag := flag.Int("width", 1024, "Image width")
	heightFlag := flag.Int("height", 1024, "Image height")
	optionsFlag := flag.Int("options", 2, "Number of concept options 1-5 (server default is 5)")
	variationsFlag := flag.Int("variations", 2, "Number of seed variations 1-5 (server default is 5)")
	regionFlag := flag.String("region", "", "Override the model's AWS region (empty = model default)")
	outputFlag := flag.String("output", "output", "Output directory")
	skipClassify := flag.Bool("skip-classify", false, "Skip asset type classification")
	skipDecompose := flag.Bool("skip-decompose", false, "Skip prompt decomposition")
	flag.Parse()

	printHeader("ArtSmoker Image Generation")
	fmt.Printf("  Server: %s\n", colored(baseURL, colorCyan))

	startTime := time.Now()

	// Step 1: List models (also serves as the connectivity check).
	models, err := listModels()
	if err != nil {
		fmt.Printf("\n  %sCannot reach ArtSmoker at %s: %s\n", colorRed, baseURL, err)
		fmt.Printf("  Make sure the server is running:%s\n", colorReset)
		fmt.Printf("  %s  cd /path/to/ArtSmoker\n", colorDim)
		fmt.Printf("    source .venv/bin/activate\n")
		fmt.Printf("    uvicorn backend.main:app --reload%s\n", colorReset)
		os.Exit(1)
	}
	if len(models) == 0 {
		fmt.Printf("  %sNo image models are enabled. Check your ArtSmoker configuration.%s\n", colorRed, colorReset)
		os.Exit(1)
	}

	// Select model — from CLI flag, or interactive, or first available.
	modelKey := *modelFlag
	if modelKey == "" {
		if *promptFlag == "" {
			defaultKey := models[0].Key
			input := readLine(fmt.Sprintf("\n  Enter model key (or press Enter for '%s'):\n  %s>%s ", defaultKey, colorCyan, colorReset))
			if input != "" {
				modelKey = input
			} else {
				modelKey = defaultKey
			}
		} else {
			modelKey = models[0].Key
		}
	}

	// Validate the model key against the live list.
	valid := false
	for _, m := range models {
		if m.Key == modelKey {
			valid = true
			break
		}
	}
	if !valid {
		fmt.Printf("\n  %sUnknown model: '%s'%s\n", colorRed, modelKey, colorReset)
		validKeys := make([]string, len(models))
		for i, m := range models {
			validKeys[i] = m.Key
		}
		fmt.Printf("  Available: %s\n", strings.Join(validKeys, ", "))
		os.Exit(1)
	}

	fmt.Printf("\n  Using model: %s\n", colored(modelKey, colorGreen))

	// Get the prompt — from CLI flag or interactively.
	prompt := *promptFlag
	if prompt == "" {
		prompt = readLine(fmt.Sprintf("\n  Enter your image prompt:\n  %s>%s ", colorCyan, colorReset))
		if prompt == "" {
			fmt.Printf("  %sPrompt cannot be empty.%s\n", colorRed, colorReset)
			os.Exit(1)
		}
	}

	assetType := *assetTypeFlag

	// Step 2: Classify asset type (optional).
	if !*skipClassify {
		suggested, err := classifyAssetType(prompt, assetType)
		if err != nil {
			fmt.Printf("  %sClassification skipped: %s%s\n", colorYellow, err, colorReset)
		} else {
			assetType = suggested
		}
	}

	// Step 3: Decompose prompt (optional, display only in this sample).
	if !*skipDecompose {
		if _, err := decomposePrompt(prompt, assetType, modelKey); err != nil {
			fmt.Printf("  %sDecomposition skipped: %s%s\n", colorYellow, err, colorReset)
		}
	}

	// Step 4: Build the request and generate.
	req := GenerationRequest{
		Prompt:        prompt,
		ImageModel:    modelKey,
		AssetType:     assetType,
		Width:         *widthFlag,
		Height:        *heightFlag,
		NumOptions:    *optionsFlag,
		NumVariations: *variationsFlag,
		// Keep the raw generated image: the server defaults these to TRUE, so we
		// must send them as false explicitly (see the struct's tag notes).
		RemoveBackground: false,
		GenerateSVG:      false,
		Upscale:          false,
	}
	if *regionFlag != "" {
		req.Region = regionFlag
	}

	genResult, err := generateImages(req)
	if err != nil {
		fmt.Printf("\n  %sGeneration failed: %s%s\n", colorRed, err, colorReset)
		os.Exit(1)
	}

	// Step 5: Poll async jobs if any (self-hosted SageMaker models).
	if len(genResult.AsyncJobs) > 0 {
		completed := pollAsyncJobs(genResult.AsyncJobs, 15*time.Minute)
		// Resolve completed async jobs into downloadable variants.
		if len(completed) > 0 && genResult.Result != nil {
			for i := range genResult.Result.Options {
				for j := range genResult.Result.Options[i].Variants {
					v := &genResult.Result.Options[i].Variants[j]
					if v.AsyncJob == nil {
						continue
					}
					jobID, _ := v.AsyncJob["job_id"].(string)
					for _, c := range completed {
						cID, _ := c["job_id"].(string)
						cStatus, _ := c["status"].(string)
						if cID == jobID && cStatus == "complete" {
							if assetID, _ := c["asset_id"].(string); assetID != "" {
								v.ID = assetID
								v.PNGPath = fmt.Sprintf("/api/gallery/%s/png", assetID)
							}
						}
					}
				}
			}
		}
	}

	// Step 6: Download images.
	var downloaded []string
	if genResult.Result != nil {
		downloaded = downloadImages(genResult.Result, *outputFlag)
	}

	printSummary(genResult.Result, downloaded, genResult.AsyncJobs, time.Since(startTime))
}
