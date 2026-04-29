// ArtSmoker Image Generation — Go API Sample
// =============================================
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
//   - Go 1.21+
//   - No external dependencies (uses stdlib only)
//   - ArtSmoker server running at http://localhost:8000
//
// How to run:
//   go run imageGen_go.go
//   go run imageGen_go.go -prompt "a medieval castle on a cliff" -model nova_canvas
//   go run imageGen_go.go -prompt "a cyberpunk warrior" -width 1024 -height 1024 -options 2 -variations 2
//
// Full API docs:     http://localhost:8000/docs
// Detailed spec:     See SPEC.md in the project root
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
		"started":         colorGreen,
		"stage":           colorYellow,
		"prompts_ready":   colorMagenta,
		"image_done":      colorGreen,
		"option_complete": colorGreen,
		"async_submitted": colorCyan,
		"done":            colorGreen,
		"complete":        colorGreen,
		"error":           colorRed,
		"image_error":     colorRed,
	}
	color, ok := colorMap[eventType]
	if !ok {
		color = colorDim
	}
	fmt.Printf("  %s[%s]%s %s\n", color, eventType, colorReset, message)
}

// ── HTTP helpers ────────────────────────────────────────────────────────────

var httpClient = &http.Client{Timeout: 60 * time.Second}

// postJSON sends a POST request with a JSON body and decodes the response.
func postJSON(path string, body interface{}, result interface{}) error {
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
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodyBytes[:min(len(bodyBytes), 200)]))
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
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodyBytes[:min(len(bodyBytes), 200)]))
	}
	return json.NewDecoder(resp.Body).Decode(result)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ── Step 1: List available models ───────────────────────────────────────────

// Model represents a model entry from /api/admin/models/image-options.
type Model struct {
	Key          string  `json:"key"`
	Label        string  `json:"label"`
	Region       string  `json:"region"`
	BasePriceUSD float64 `json:"base_price_usd"`
}

func listModels() ([]Model, error) {
	// GET /api/admin/models/image-options returns the list of enabled
	// text-to-image models with their metadata (label, region, pricing).
	printStep(1, "Fetching available image models...")
	var models []Model
	if err := getJSON("/api/admin/models/image-options", &models); err != nil {
		return nil, err
	}
	fmt.Printf("  Found %s available models:\n", colored(fmt.Sprintf("%d", len(models)), colorGreen))
	for _, m := range models {
		key := m.Key
		label := m.Label
		if label == "" {
			label = key
		}
		fmt.Printf("    %s- %s%s (%s) [%s] ~$%.4f/image\n",
			colorDim, colorReset, colored(key, colorBold), label, m.Region, m.BasePriceUSD)
	}
	return models, nil
}

// ── Step 2: Classify asset type ─────────────────────────────────────────────

func classifyAssetType(prompt, currentType string) (string, error) {
	// POST /api/refine-prompt/classify-asset-type
	// The server uses an LLM to determine whether the prompt better matches
	// a different asset type (e.g., 'character' instead of 'game_asset').
	printStep(2, "Classifying asset type...")
	reqBody := map[string]string{
		"prompt":     prompt,
		"asset_type": currentType,
	}
	var result map[string]interface{}
	if err := postJSON("/api/refine-prompt/classify-asset-type", reqBody, &result); err != nil {
		return currentType, err
	}

	if mismatch, ok := result["mismatch"].(bool); ok && mismatch {
		suggested := fmt.Sprintf("%v", result["suggested"])
		reason := fmt.Sprintf("%v", result["reason"])
		fmt.Printf("  %sSuggestion:%s Switch from '%s' to '%s'\n",
			colorYellow, colorReset, currentType, colored(suggested, colorGreen))
		fmt.Printf("  %sReason: %s%s\n", colorDim, reason, colorReset)
		return suggested, nil
	}
	fmt.Printf("  Asset type '%s' is appropriate for this prompt.\n", colored(currentType, colorGreen))
	return currentType, nil
}

// ── Step 3: Decompose prompt ────────────────────────────────────────────────

func decomposePrompt(prompt, assetType, model string) (map[string]interface{}, error) {
	// POST /api/refine-prompt/decompose
	// Returns a JSON structure with editable fields: subject, scene,
	// composition, lighting, style (including color palette with hex values).
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

	// Display the decomposed components
	for sectionName, sectionRaw := range result {
		if strings.HasPrefix(sectionName, "_") {
			continue // Skip metadata
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

// GenerationResult holds the full result from the generation pipeline.
type GenerationResult struct {
	ID           string                   `json:"id"`
	Prompt       string                   `json:"prompt"`
	ImageModel   string                   `json:"image_model"`
	Width        int                      `json:"width"`
	Height       int                      `json:"height"`
	Options      []OptionResult           `json:"options"`
	TotalCostUSD float64                  `json:"total_cost_usd"`
}

// OptionResult holds a single concept option with its variants.
type OptionResult struct {
	OptionIndex    int             `json:"option_index"`
	EnhancedPrompt string          `json:"enhanced_prompt"`
	Variants       []VariantResult `json:"variants"`
}

// VariantResult holds a single image variant.
type VariantResult struct {
	ID           string                 `json:"id"`
	VariantIndex int                    `json:"variant_index"`
	PNGPath      string                 `json:"png_path"`
	AsyncJob     map[string]interface{} `json:"async_job"`
}

// GenOutput is the return value from generateImages.
type GenOutput struct {
	Result    *GenerationResult
	AsyncJobs []string
	BatchID   string
}

func generateImages(prompt, model, assetType string, width, height, numOptions, numVariations int) (*GenOutput, error) {
	// POST /api/generate/stream
	// The server sends Server-Sent Events with real-time progress.
	// We parse the SSE stream manually since Go stdlib doesn't include an SSE client.
	printStep(4, "Generating images via SSE stream...")

	// Build the generation request payload
	payload := map[string]interface{}{
		"prompt":            prompt,
		"image_model":       model,
		"asset_type":        assetType,
		"width":             width,
		"height":            height,
		"num_options":       numOptions,
		"num_variations":    numVariations,
		"remove_background": false,
		"generate_svg":      false,
		"upscale":           false,
	}

	payloadBytes, _ := json.MarshalIndent(payload, "  ", "  ")
	fmt.Printf("  Payload: %s%s%s\n", colorDim, string(payloadBytes), colorReset)

	// Open the SSE connection.
	// We need a long timeout since generation can take minutes.
	sseClient := &http.Client{Timeout: 5 * time.Minute}
	body, _ := json.Marshal(payload)
	resp, err := sseClient.Post(baseURL+"/api/generate/stream", "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("SSE connect: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodyBytes[:min(len(bodyBytes), 200)]))
	}

	output := &GenOutput{}

	fmt.Printf("\n  %s--- SSE Events ---%s\n", colorBold, colorReset)

	// Parse SSE stream manually.
	// SSE format: "data: {json}\n\n" with optional ":" comment lines for keepalive.
	scanner := bufio.NewScanner(resp.Body)
	// Increase buffer size for potentially large SSE payloads
	scanner.Buffer(make([]byte, 0, 256*1024), 256*1024)

	for scanner.Scan() {
		line := scanner.Text()

		// Skip empty lines (SSE event delimiter) and keepalive comments
		if line == "" || strings.HasPrefix(line, ":") {
			continue
		}

		// SSE data lines start with "data: "
		if !strings.HasPrefix(line, "data: ") {
			continue
		}

		jsonStr := strings.TrimPrefix(line, "data: ")
		var data map[string]interface{}
		if err := json.Unmarshal([]byte(jsonStr), &data); err != nil {
			continue // Skip malformed data
		}

		eventType, _ := data["type"].(string)

		// Handle each event type
		switch eventType {
		case "started":
			batchID, _ := data["batch_id"].(string)
			total, _ := data["total"].(float64)
			output.BatchID = batchID
			printEvent(eventType, fmt.Sprintf("Batch %s... - generating %.0f images", batchID[:min(8, len(batchID))], total))

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
				if len(ps) > 120 {
					ps = ps[:120] + "..."
				}
				fmt.Printf("    %sPrompt %d: %s%s\n", colorDim, i+1, ps, colorReset)
			}
			if negative != "" {
				if len(negative) > 100 {
					negative = negative[:100]
				}
				fmt.Printf("    %sNegative: %s%s\n", colorDim, negative, colorReset)
			}

		case "image_done":
			opt, _ := data["option"].(float64)
			vari, _ := data["variation"].(float64)
			done, _ := data["completed"].(float64)
			total, _ := data["total"].(float64)
			printEvent(eventType, fmt.Sprintf("Option %.0f, Variation %.0f (%.0f/%.0f complete)",
				opt+1, vari+1, done, total))

		case "async_submitted":
			jobID, _ := data["job_id"].(string)
			modelLabel, _ := data["model_label"].(string)
			output.AsyncJobs = append(output.AsyncJobs, jobID)
			printEvent(eventType, fmt.Sprintf("Async job %s... (%s) - will poll for completion",
				jobID[:min(12, len(jobID))], modelLabel))

		case "complete":
			// Parse the full result from the complete event
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
			printEvent(eventType, fmt.Sprintf("Done! %d images generated", totalImages))

		case "error", "image_error":
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
				msg = "Content moderation blocked this prompt"
			}
			printEvent(eventType, colored(msg, colorRed))

		case "prompt_refused":
			reason, _ := data["reason"].(string)
			if reason == "" {
				reason = "Prompt refused by the AI"
			}
			printEvent(eventType, colored(reason, colorRed))

		default:
			truncated, _ := json.Marshal(data)
			s := string(truncated)
			if len(s) > 200 {
				s = s[:200]
			}
			printEvent(eventType, s)
		}
	}

	fmt.Printf("  %s--- End SSE ---%s\n\n", colorBold, colorReset)

	return output, nil
}

// ── Step 5: Poll for async job completion ───────────────────────────────────

func pollAsyncJobs(jobIDs []string, timeout time.Duration) []map[string]interface{} {
	// GET /api/generate/async-jobs
	// Returns all active and recent jobs with their statuses.
	// Polls every 5 seconds until all jobs complete or timeout.
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
			time.Sleep(5 * time.Second)
			continue
		}

		pending := 0
		for _, jid := range jobIDs {
			// Find this job in the response
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
					fmt.Printf("  %sJob %s... completed! Asset: %s%s\n",
						colorGreen, jid[:min(12, len(jid))], assetID, colorReset)
				}
			case "failed":
				if !completedIDs[jid] {
					completedIDs[jid] = true
					completedJobs = append(completedJobs, job)
					errMsg, _ := job["error"].(string)
					fmt.Printf("  %sJob %s... failed: %s%s\n",
						colorRed, jid[:min(12, len(jid))], errMsg, colorReset)
				}
			default:
				pending++
				elapsed := int(time.Since(start).Seconds())
				fmt.Printf("  %sJob %s... status: %s (%ds elapsed)%s\n",
					colorDim, jid[:min(12, len(jid))], status, elapsed, colorReset)
			}
		}

		if pending == 0 {
			break
		}

		// Wait 5 seconds before next poll
		time.Sleep(5 * time.Second)
	}

	return completedJobs
}

// ── Step 6: Download completed images ───────────────────────────────────────

func downloadImages(result *GenerationResult, outputDir string) []string {
	// GET /api/gallery/{asset_id}/png
	// Saves each image to the output directory with a descriptive filename.
	if result == nil {
		fmt.Printf("  %sNo result data to download.%s\n", colorYellow, colorReset)
		return nil
	}

	printStep(6, "Downloading generated images...")
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		fmt.Printf("  %sFailed to create output dir: %s%s\n", colorRed, err, colorReset)
		return nil
	}

	var downloaded []string

	for _, option := range result.Options {
		optIdx := option.OptionIndex
		for _, variant := range option.Variants {
			assetID := variant.ID
			pngPath := variant.PNGPath
			varIdx := variant.VariantIndex

			// Skip async jobs that haven't completed yet
			if variant.AsyncJob != nil && pngPath == "" {
				fmt.Printf("  %sSkipping opt%d_var%d (async pending)%s\n",
					colorDim, optIdx+1, varIdx+1, colorReset)
				continue
			}

			if assetID == "" || pngPath == "" {
				continue
			}

			// Download the PNG
			url := baseURL + pngPath
			resp, err := httpClient.Get(url)
			if err != nil {
				fmt.Printf("  %sFailed to download %s: %s%s\n", colorRed, assetID, err, colorReset)
				continue
			}
			imgBytes, err := io.ReadAll(resp.Body)
			resp.Body.Close()
			if err != nil || resp.StatusCode >= 400 {
				fmt.Printf("  %sFailed to download %s: HTTP %d%s\n", colorRed, assetID, resp.StatusCode, colorReset)
				continue
			}

			filename := fmt.Sprintf("opt%d_var%d_%s.png", optIdx+1, varIdx+1, assetID)
			filepath_ := filepath.Join(outputDir, filename)
			if err := os.WriteFile(filepath_, imgBytes, 0644); err != nil {
				fmt.Printf("  %sFailed to write %s: %s%s\n", colorRed, filepath_, err, colorReset)
				continue
			}

			sizeKB := float64(len(imgBytes)) / 1024
			downloaded = append(downloaded, filepath_)
			fmt.Printf("  %sSaved:%s %s (%.1f KB)\n", colorGreen, colorReset, filepath_, sizeKB)
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

	prompt := result.Prompt
	if len(prompt) > 80 {
		prompt = prompt[:80] + "..."
	}
	batchID := result.ID
	if len(batchID) > 16 {
		batchID = batchID[:16] + "..."
	}

	fmt.Printf("  Batch ID:    %s\n", colored(batchID, colorCyan))
	fmt.Printf("  Prompt:      %s\n", prompt)
	fmt.Printf("  Model:       %s\n", colored(result.ImageModel, colorBold))
	fmt.Printf("  Dimensions:  %dx%d\n", result.Width, result.Height)
	fmt.Printf("  Options:     %d\n", len(result.Options))
	fmt.Printf("  Total imgs:  %s\n", colored(fmt.Sprintf("%d", totalImages), colorGreen))
	fmt.Printf("  Downloaded:  %d file(s)\n", len(downloaded))
	if len(asyncJobs) > 0 {
		fmt.Printf("  Async jobs:  %d\n", len(asyncJobs))
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
	// Parse command-line flags
	promptFlag := flag.String("prompt", "", "Image generation prompt (interactive if not provided)")
	modelFlag := flag.String("model", "", "Model key (e.g. nova_canvas, sd35_large)")
	assetTypeFlag := flag.String("asset-type", "photorealistic", "Asset type: photorealistic, game_asset, character, environment, icon, marketing_banner")
	widthFlag := flag.Int("width", 1024, "Image width")
	heightFlag := flag.Int("height", 1024, "Image height")
	optionsFlag := flag.Int("options", 2, "Number of concept options 1-5")
	variationsFlag := flag.Int("variations", 2, "Number of seed variations 1-5")
	outputFlag := flag.String("output", "output", "Output directory")
	skipClassify := flag.Bool("skip-classify", false, "Skip asset type classification")
	skipDecompose := flag.Bool("skip-decompose", false, "Skip prompt decomposition")
	flag.Parse()

	printHeader("ArtSmoker Image Generation")
	fmt.Printf("  Server: %s\n", colored(baseURL, colorCyan))

	// Check server connectivity
	var testModels []Model
	if err := getJSON("/api/admin/models/image-options", &testModels); err != nil {
		fmt.Printf("\n  %sCannot connect to ArtSmoker at %s\n", colorRed, baseURL)
		fmt.Printf("  Make sure the server is running:%s\n", colorReset)
		fmt.Printf("  %s  cd /path/to/ArtSmoker\n", colorDim)
		fmt.Printf("    source .venv/bin/activate\n")
		fmt.Printf("    uvicorn backend.main:app --reload%s\n", colorReset)
		os.Exit(1)
	}

	startTime := time.Now()

	// Step 1: List models and select one
	models, err := listModels()
	if err != nil {
		fmt.Printf("  %sFailed to list models: %s%s\n", colorRed, err, colorReset)
		os.Exit(1)
	}
	if len(models) == 0 {
		fmt.Printf("  %sNo models available. Check your ArtSmoker configuration.%s\n", colorRed, colorReset)
		os.Exit(1)
	}

	// Select model — from CLI flag, or interactive, or first available
	modelKey := *modelFlag
	if modelKey == "" {
		if *promptFlag == "" {
			// Interactive model selection
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

	// Validate model key
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

	// Get prompt — from CLI flag or interactive
	prompt := *promptFlag
	if prompt == "" {
		prompt = readLine(fmt.Sprintf("\n  Enter your image prompt:\n  %s>%s ", colorCyan, colorReset))
		if prompt == "" {
			fmt.Printf("  %sPrompt cannot be empty.%s\n", colorRed, colorReset)
			os.Exit(1)
		}
	}

	assetType := *assetTypeFlag

	// Step 2: Classify asset type (optional)
	if !*skipClassify {
		suggested, err := classifyAssetType(prompt, assetType)
		if err != nil {
			fmt.Printf("  %sClassification skipped: %s%s\n", colorYellow, err, colorReset)
		} else {
			assetType = suggested
		}
	}

	// Step 3: Decompose prompt (optional)
	if !*skipDecompose {
		_, err := decomposePrompt(prompt, assetType, modelKey)
		if err != nil {
			fmt.Printf("  %sDecomposition skipped: %s%s\n", colorYellow, err, colorReset)
		}
	}

	// Step 4: Generate images
	genResult, err := generateImages(prompt, modelKey, assetType,
		*widthFlag, *heightFlag, *optionsFlag, *variationsFlag)
	if err != nil {
		fmt.Printf("\n  %sGeneration failed: %s%s\n", colorRed, err, colorReset)
		os.Exit(1)
	}

	// Step 5: Poll async jobs if any (custom/SageMaker models)
	if len(genResult.AsyncJobs) > 0 {
		completed := pollAsyncJobs(genResult.AsyncJobs, 10*time.Minute)
		// Update result with completed async job asset IDs
		if len(completed) > 0 && genResult.Result != nil {
			for i := range genResult.Result.Options {
				for j := range genResult.Result.Options[i].Variants {
					v := &genResult.Result.Options[i].Variants[j]
					if v.AsyncJob != nil {
						jobID, _ := v.AsyncJob["job_id"].(string)
						for _, c := range completed {
							cID, _ := c["job_id"].(string)
							cStatus, _ := c["status"].(string)
							if cID == jobID && cStatus == "complete" {
								assetID, _ := c["asset_id"].(string)
								v.ID = assetID
								v.PNGPath = fmt.Sprintf("/api/gallery/%s/png", assetID)
							}
						}
					}
				}
			}
		}
	}

	// Step 6: Download images
	var downloaded []string
	if genResult.Result != nil {
		downloaded = downloadImages(genResult.Result, *outputFlag)
	}

	// Summary
	elapsed := time.Since(startTime)
	printSummary(genResult.Result, downloaded, genResult.AsyncJobs, elapsed)
}
