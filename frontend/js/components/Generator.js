/**
 * ArtSmoker — Generator Component
 *
 * Two-level generation:
 *   Options    — distinctly different creative concepts
 *   Variations — seed variants of the selected concept
 */
(function () {
    'use strict';

    const ASSET_TYPES = [
        { value: 'game_asset', label: 'Game Asset' },
        { value: 'marketing_banner', label: 'Marketing Banner' },
        { value: 'icon', label: 'Icon' },
        { value: 'character', label: 'Character' },
        { value: 'environment', label: 'Environment' },
    ];

    const MODELS = [
        { value: 'nova_canvas', label: 'Nova Canvas' },
        { value: 'titan_image', label: 'Titan Image v2' },
        { value: 'sd35_large', label: 'Stable Diffusion 3.5 Large' },
        { value: 'stable_image_ultra', label: 'Stable Image Ultra' },
    ];

    const SIZE_PRESETS = [
        { label: '512 x 512', w: 512, h: 512 },
        { label: '768 x 768', w: 768, h: 768 },
        { label: '1024 x 1024', w: 1024, h: 1024 },
        { label: '1024 x 576', w: 1024, h: 576 },
        { label: '576 x 1024', w: 576, h: 1024 },
        { label: '1280 x 720', w: 1280, h: 720 },
    ];

    const COUNT_OPTIONS = [1, 2, 3, 4, 5];

    window.Generator = {
        _styles: [],
        _promptEditor: null,
        _generating: false,
        _result: null,
        _selectedOption: 0,
        _selectedVariant: 0,

        render() {
            return `
                <div id="generator-view" class="view-enter">
                    <div class="flex flex-col lg:flex-row gap-6">

                        <!-- Left Sidebar -->
                        <aside class="lg:w-72 xl:w-80 flex-shrink-0 space-y-5">
                            <div class="card-static p-5 space-y-5">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
                                    </svg>
                                    Settings
                                </h2>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Art Style</label>
                                    <select id="gen-style" class="input">
                                        <option value="">None (default)</option>
                                    </select>
                                </div>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Asset Type</label>
                                    <select id="gen-asset-type" class="input">
                                        ${ASSET_TYPES.map(t => `<option value="${t.value}">${t.label}</option>`).join('')}
                                    </select>
                                </div>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Image Model</label>
                                    <select id="gen-model" class="input">
                                        ${MODELS.map(m => `<option value="${m.value}">${m.label}</option>`).join('')}
                                    </select>
                                </div>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Dimensions</label>
                                    <select id="gen-size" class="input">
                                        ${SIZE_PRESETS.map((s, i) => `<option value="${i}" ${i === 2 ? 'selected' : ''}>${s.label}</option>`).join('')}
                                    </select>
                                </div>

                                <!-- Two-level counts -->
                                <div class="grid grid-cols-2 gap-3">
                                    <div>
                                        <label class="block text-sm font-medium mb-1.5">Options</label>
                                        <select id="gen-num-options" class="input">
                                            ${COUNT_OPTIONS.map(n => `<option value="${n}" ${n === 5 ? 'selected' : ''}>${n}</option>`).join('')}
                                        </select>
                                        <p class="text-[10px] text-brand-text-muted mt-0.5">Different designs</p>
                                    </div>
                                    <div>
                                        <label class="block text-sm font-medium mb-1.5">Variations</label>
                                        <select id="gen-num-variations" class="input">
                                            ${COUNT_OPTIONS.map(n => `<option value="${n}" ${n === 5 ? 'selected' : ''}>${n}</option>`).join('')}
                                        </select>
                                        <p class="text-[10px] text-brand-text-muted mt-0.5">Per option</p>
                                    </div>
                                </div>

                            </div>

                            <!-- Prompt Pre-Check -->
                            <div class="card-static p-4">
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center gap-2">
                                        <svg class="w-4 h-4 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                                        </svg>
                                        <label class="text-sm font-medium">Prompt Pre-Check</label>
                                    </div>
                                    <label class="toggle"><input type="checkbox" id="gen-precheck"><span class="toggle-slider"></span></label>
                                </div>
                                <p class="text-[10px] text-brand-text-muted mt-1.5">Checks your prompt for moderation issues before generating. Suggests a better model if needed. Saves time and API costs on blocked prompts.</p>
                            </div>

                            <!-- Model Settings -->
                            <button id="btn-model-settings" class="w-full text-left p-3 rounded-lg bg-brand-bg/30 border border-brand-border/50 hover:border-brand-accent/30 hover:bg-brand-bg/50 transition-colors flex items-center gap-2 text-xs text-brand-text-muted">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                                Model Settings
                            </button>

                            <!-- Processing Options -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-sm font-semibold flex items-center gap-2 text-brand-text-muted uppercase tracking-wide">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343"/>
                                    </svg>
                                    <span id="gen-processing-label">Pre-Processing</span>
                                </h2>
                                <div class="space-y-3">
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Remove Background</label>
                                        <label class="toggle"><input type="checkbox" id="gen-remove-bg"><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Convert to SVG</label>
                                        <label class="toggle"><input type="checkbox" id="gen-svg" checked><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Upscale</label>
                                        <label class="toggle"><input type="checkbox" id="gen-upscale"><span class="toggle-slider"></span></label>
                                    </div>
                                </div>
                                <button id="btn-apply-postprocess" class="btn btn-secondary btn-sm w-full hidden">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                    </svg>
                                    Apply to Current Results
                                </button>
                                <p id="pp-hint" class="text-[10px] text-brand-text-muted/50 hidden">Toggle settings above, then click Apply to re-process existing images without regenerating.</p>
                            </div>
                        </aside>

                        <!-- Center: Prompt + Results -->
                        <div class="flex-1 min-w-0 space-y-5">

                            <!-- Prompt Editor -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                    </svg>
                                    Prompt
                                </h2>
                                <div id="prompt-editor-container"></div>
                            </div>

                            <!-- Generate / Reset Buttons -->
                            <div class="grid grid-cols-2 gap-3">
                                <button id="btn-generate" class="btn btn-primary btn-lg text-base">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                    </svg>
                                    Generate
                                </button>
                                <button id="btn-reset" class="btn btn-lg text-base bg-amber-600 hover:bg-amber-500 text-white">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                    </svg>
                                    Reset
                                </button>
                            </div>

                            <!-- Prompt info (original + AI-improved) -->
                            <div id="gen-prompt-info" class="hidden card-static p-4 space-y-3">
                                <div id="gen-original-prompt-section">
                                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold mb-1">Original prompt</p>
                                    <p id="gen-original-prompt-text" class="text-sm text-brand-text/80 leading-relaxed"></p>
                                </div>
                                <div id="gen-used-prompt-section">
                                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold mb-1">AI-improved prompt (sent to generator)</p>
                                    <p id="gen-used-prompt-text" class="text-sm text-brand-text/60 leading-relaxed"></p>
                                </div>
                            </div>

                            <!-- Concept prompt display -->
                            <div id="gen-concept-prompt" class="hidden card-static p-3">
                                <p class="text-xs text-brand-text-muted mb-1 font-medium">Concept prompt:</p>
                                <p id="gen-concept-prompt-text" class="text-xs text-brand-text/70 leading-relaxed"></p>
                            </div>

                            <!-- OPTIONS ROW (different concepts) -->
                            <div id="gen-options-section" class="hidden">
                                <div class="flex items-center justify-between mb-2">
                                    <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wide">
                                        Options — different designs
                                    </h3>
                                    <span id="gen-options-count" class="text-xs text-brand-text-muted"></span>
                                </div>
                                <div id="gen-options-grid" class="grid grid-cols-5 gap-3"></div>
                            </div>

                            <!-- VARIATIONS ROW (seed variants of selected option) -->
                            <div id="gen-variations-section" class="hidden">
                                <div class="flex items-center justify-between mb-2">
                                    <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wide">
                                        Variations of selected option
                                    </h3>
                                    <span id="gen-variations-count" class="text-xs text-brand-text-muted"></span>
                                </div>
                                <div id="gen-variations-grid" class="grid grid-cols-5 gap-3"></div>
                            </div>

                            <!-- Main Preview -->
                            <div class="card-static overflow-hidden">
                                <div id="gen-preview" class="preview-checkerboard min-h-[350px] lg:min-h-[450px] flex items-center justify-center p-6 relative">
                                    <div id="gen-placeholder" class="text-center">
                                        <svg class="w-16 h-16 mx-auto text-brand-text-muted/20 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                                        </svg>
                                        <p class="text-brand-text-muted/40 text-sm">Your generated images will appear here</p>
                                    </div>
                                    <div id="gen-loading" class="hidden absolute inset-0 bg-brand-bg/60 flex flex-col items-center justify-center gap-4 px-8">
                                        <div class="loading-spinner w-10 h-10 border-4 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                        <p id="gen-loading-text" class="text-sm text-brand-text-muted font-medium">Generating...</p>
                                        <p id="gen-loading-sub" class="text-xs text-brand-text-muted/60"></p>
                                        <div class="w-full max-w-xs mt-2">
                                            <div class="h-1.5 bg-brand-border rounded-full overflow-hidden">
                                                <div id="gen-progress-bar" class="h-full bg-brand-accent rounded-full transition-all duration-1000 ease-out" style="width: 0%"></div>
                                            </div>
                                            <p id="gen-loading-elapsed" class="text-[10px] text-brand-text-muted/40 text-center mt-1.5"></p>
                                        </div>
                                    </div>
                                    <img id="gen-result-img" class="hidden max-w-full max-h-[60vh] rounded-lg shadow-2xl" alt="Generated image" />
                                </div>

                                <!-- Download bar -->
                                <div id="gen-download-bar" class="hidden border-t border-brand-border p-4 flex flex-wrap items-center justify-between gap-3 bg-brand-surface">
                                    <div class="text-sm text-brand-text-muted">
                                        <span id="gen-result-info"></span>
                                    </div>
                                    <div class="flex gap-2">
                                        <a id="dl-png" href="#" download class="btn btn-secondary btn-sm">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                            </svg>
                                            PNG
                                        </a>
                                        <a id="dl-svg" href="#" download class="btn btn-secondary btn-sm hidden">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                            </svg>
                                            SVG
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        },

        /** Called when navigating back to Generator (view already cached) */
        onShow() {
            this._loadStyles();
            this._ensurePromptEditor();
        },

        _ensurePromptEditor() {
            if (this._promptEditor && this._promptEditor._textareaEl) return;
            const container = document.getElementById('prompt-editor-container');
            if (container) {
                try {
                    this._promptEditor = new PromptEditor(container, {
                        styleId: this._getStyleId(),
                        assetType: this._getAssetType(),
                    });
                } catch (err) {
                    console.error('Failed to create PromptEditor:', err);
                    if (typeof API !== 'undefined') API.log('error', 'PromptEditor init failed: ' + err.message);
                }
            }
        },

        async init() {
            await this._loadStyles();
            this._ensurePromptEditor();

            document.getElementById('gen-style')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ styleId: this._getStyleId() });
            });
            document.getElementById('gen-asset-type')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ assetType: this._getAssetType() });
            });
            document.getElementById('btn-generate')?.addEventListener('click', () => this._handleGenerate());
            document.getElementById('btn-model-settings')?.addEventListener('click', () => ModelSettings.open());
            document.getElementById('btn-apply-postprocess')?.addEventListener('click', () => this._handlePostProcess());
            document.getElementById('btn-reset')?.addEventListener('click', () => {
                if (this._result && !confirm('Reset the generator? Current results will be cleared.')) return;
                window.resetView('image-studio');
            });
        },

        async _loadStyles() {
            try {
                const data = await API.styles.list();
                this._styles = Array.isArray(data) ? data : [];
            } catch { this._styles = []; }

            const sel = document.getElementById('gen-style');
            if (!sel) return;
            const currentValue = sel.value;
            const none = sel.querySelector('option');
            sel.innerHTML = '';
            sel.appendChild(none);
            this._styles.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.name;
                sel.appendChild(opt);
            });
            // Restore previous selection if it still exists
            if (currentValue) sel.value = currentValue;
        },

        // ── Generation ──────────────────────────────────────────────

        async _handleGenerate() {
            if (this._generating) return;

            // Get the user's raw prompt (always required)
            const userPrompt = this._promptEditor ? this._promptEditor.getUserText().trim() : '';
            if (!userPrompt) {
                window.showToast?.('Enter a prompt before generating', 'warning');
                return;
            }

            // If a composed prompt exists, use it directly (skip re-refinement in backend)
            // If not, send the raw user prompt (backend will refine it)
            const hasComposed = this._promptEditor?.hasComposedPrompt();
            const prompt = hasComposed
                ? this._promptEditor.getComposedText().trim()
                : userPrompt;

            const sizeIdx = parseInt(document.getElementById('gen-size').value, 10);
            const size = SIZE_PRESETS[sizeIdx] || SIZE_PRESETS[2];
            const numOptions = parseInt(document.getElementById('gen-num-options').value, 10) || 5;
            const numVariations = parseInt(document.getElementById('gen-num-variations').value, 10) || 5;
            const total = numOptions * numVariations;

            const moderationOriginal = this._promptEditor?._moderationOriginal || null;

            const payload = {
                prompt: hasComposed ? prompt : userPrompt,
                original_prompt: userPrompt,
                pre_composed: hasComposed || false,
                moderation_original: moderationOriginal || null,
                style_id: this._getStyleId() || null,
                asset_type: this._getAssetType(),
                image_model: document.getElementById('gen-model').value,
                width: size.w,
                height: size.h,
                num_options: numOptions,
                num_variations: numVariations,
                remove_background: document.getElementById('gen-remove-bg').checked,
                generate_svg: document.getElementById('gen-svg').checked,
                upscale: document.getElementById('gen-upscale').checked,
            };

            // ── Prompt Pre-Check (if enabled) ──────────────────────
            const preCheckOn = document.getElementById('gen-precheck')?.checked;
            if (preCheckOn) {
                try {
                    window.showLoading?.('Pre-checking prompt...');
                    const screen = await API.preScreen({
                        prompt: prompt,
                        image_model: payload.image_model,
                    });
                    window.hideLoading?.();

                    if (!screen.likely_safe) {
                        this._showPreCheckDialog(prompt, screen, payload);
                        return;
                    }
                } catch (preErr) {
                    window.hideLoading?.();
                    // Pre-check failed — proceed anyway
                }
            }

            this._setGenerating(true, total, payload);
            this._moderationErrors = [];

            let moderationBlocked = false;
            let promptRefused = false;
            let refusalReason = '';

            try {
                const result = await API.generateStream(payload, (evt) => {
                    this._handleProgressEvent(evt, total);
                    // Show the composed/refined prompts in the editor
                    if (evt.type === 'prompts_ready' && this._promptEditor) {
                        const prompts = evt.prompts || [];
                        if (prompts.length > 0 && !evt.pre_composed) {
                            // Backend refined the prompt — show it in the composed area
                            this._promptEditor.setComposedText(prompts[0]);
                        }
                    }
                    // Track moderation blocks
                    if (evt.type === 'moderation_blocked') {
                        moderationBlocked = true;
                        this._moderationErrors.push(evt.error || 'Content moderation blocked');
                    }
                    // Track prompt refusals (Claude declined to refine)
                    if (evt.type === 'prompt_refused') {
                        promptRefused = true;
                        refusalReason = evt.reason || evt.message || 'The AI declined to process this prompt.';
                    }
                    if (evt.type === 'image_error' && evt.error) {
                        const errLower = (evt.error || '').toLowerCase();
                        if (errLower.includes('generation failed') || errLower.includes('moderation') || errLower.includes('blocked')) {
                            this._moderationErrors.push(evt.error);
                        }
                    }
                });

                const totalGenerated = (result.options || []).reduce((n, o) => n + (o.variants || []).length, 0);

                // Prompt refusal — Claude declined to process this prompt
                if (promptRefused) {
                    this._result = null;
                    this._showPromptRefusalDialog(prompt, refusalReason);
                }
                // Moderation block — image model rejected the prompt
                else if (moderationBlocked || (totalGenerated === 0 && this._moderationErrors.length > 0)) {
                    this._result = null;
                    this._showModerationDialog(prompt, this._moderationErrors[0] || 'Content moderation blocked this prompt', payload);
                } else if (totalGenerated === 0) {
                    window.showToast?.('All images failed to generate. Try a different prompt or model.', 'error');
                } else {
                    // Clean success — render results
                    this._result = result;
                    this._selectedOption = 0;
                    this._selectedVariant = 0;
                    this._renderResults(result);
                    window.showToast?.(`${totalGenerated} images generated across ${(result.options || []).length} options!`, 'success');
                }
            } catch (err) {
                console.error('Generation error:', err);
                // If we had any moderation errors during the stream, show the dialog
                if (this._moderationErrors.length > 0 || moderationBlocked) {
                    this._showModerationDialog(prompt, this._moderationErrors[0] || 'Generation failed', payload);
                } else {
                    window.showToast?.(err.message || 'Generation failed', 'error');
                }
            } finally {
                this._setGenerating(false);
            }
        },

        async _handlePostProcess() {
            if (!this._result) {
                window.showToast?.('Generate images first', 'warning');
                return;
            }

            // Collect all variant asset IDs from current results
            const assetIds = [];
            for (const opt of (this._result.options || [])) {
                for (const v of (opt.variants || [])) {
                    assetIds.push(v.id);
                }
            }
            if (assetIds.length === 0) {
                window.showToast?.('No images to process', 'warning');
                return;
            }

            const removeBg = document.getElementById('gen-remove-bg').checked;
            const genSvg = document.getElementById('gen-svg').checked;
            const upscale = document.getElementById('gen-upscale').checked;

            if (!removeBg && !genSvg && !upscale) {
                window.showToast?.('Enable at least one post-processing option', 'warning');
                return;
            }

            const btn = document.getElementById('btn-apply-postprocess');
            const origHTML = btn.innerHTML;
            btn.innerHTML = '<span class="spinner-sm"></span> Processing...';
            btn.disabled = true;

            try {
                const result = await API.postProcess({
                    asset_ids: assetIds,
                    remove_background: removeBg,
                    generate_svg: genSvg,
                    upscale: upscale,
                });
                const count = (result.processed || []).length;
                window.showToast?.(`Post-processing applied to ${count} image${count !== 1 ? 's' : ''}`, 'success');

                // Refresh the preview to show updated images (cache-bust)
                const img = document.getElementById('gen-result-img');
                if (img && img.src) {
                    img.src = img.src.split('?')[0] + '?t=' + Date.now();
                }
            } catch (err) {
                console.error('Post-process error:', err);
            } finally {
                btn.innerHTML = origHTML;
                btn.disabled = false;
            }
        },

        // ── Moderation Dialog ────────────────────────────────────────

        _moderationErrors: [],

        async _showModerationDialog(originalPrompt, errorMessage, payload) {
            // Remove any existing dialog
            document.getElementById('moderation-dialog')?.remove();

            // Show loading state while AI analyzes
            const dialog = document.createElement('div');
            dialog.id = 'moderation-dialog';
            dialog.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            dialog.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center gap-3 px-6 py-4 border-b border-brand-border bg-amber-950/30">
                        <svg class="w-6 h-6 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                        </svg>
                        <h2 class="text-lg font-semibold text-amber-300">Content Moderation Issue</h2>
                        <button class="mod-close ml-auto p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex-1 overflow-auto p-6" id="mod-content">
                        <div class="flex flex-col items-center justify-center py-8 gap-3 text-brand-text-muted">
                            <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                            <p>Testing your prompt on alternative models...</p>
                            <p class="text-[10px] text-brand-text-muted/50">Game art with weapons/combat often works on Stable Diffusion 3.5 even when Nova Canvas blocks it</p>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            dialog.querySelector('.mod-close').addEventListener('click', () => dialog.remove());
            dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.remove(); });

            // Call smart moderation — tries alternative models first, rewrites only as last resort
            try {
                const analysis = await API.analyzeModeration({
                    prompt: originalPrompt,
                    error_message: errorMessage,
                    image_model: payload?.image_model || 'nova_canvas',
                    width: 512,
                    height: 512,
                });

                const content = document.getElementById('mod-content');
                if (!content) return;

                const action = analysis.action || 'rewrite';
                const verified = analysis.verified;
                const workingModel = analysis.working_model;
                const workingModelLabel = analysis.working_model_label || workingModel;
                const originalModelLabel = analysis.original_model_label || analysis.original_model;

                // Store attempt history for metadata
                this._moderationAttempts = analysis.attempts || [];

                if (action === 'switch_model') {
                    // ── Model switch dialog — prompt is fine, just needs a different model ──
                    content.innerHTML = `
                        <div class="space-y-5">
                            <div class="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/20">
                                <div class="flex items-center gap-2 mb-2">
                                    <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                    </svg>
                                    <span class="text-sm font-semibold text-emerald-300">Your prompt works with ${this._escapeHtml(workingModelLabel)}</span>
                                </div>
                                <p class="text-sm text-brand-text/90 leading-relaxed">${this._escapeHtml(analysis.explanation)}</p>
                            </div>

                            <p class="text-xs text-brand-text-muted">Your prompt is preserved exactly as-is — no changes needed. This is common for game art with weapons, combat poses, and action scenes.</p>

                            <div class="flex gap-3 pt-2">
                                <button id="mod-switch-model" class="btn bg-emerald-600 hover:bg-emerald-500 text-white flex-1">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                    </svg>
                                    Generate with ${this._escapeHtml(workingModelLabel)}
                                </button>
                                <button id="mod-rewrite-instead" class="btn btn-secondary btn-sm">
                                    Rewrite for ${this._escapeHtml(originalModelLabel)}
                                </button>
                            </div>

                            <details class="text-xs">
                                <summary class="text-brand-text-muted cursor-pointer hover:text-brand-text">View ${(analysis.attempts || []).length} model tests</summary>
                                <div class="mt-2 space-y-1">
                                    ${(analysis.attempts || []).map(a => `
                                        <div class="p-1.5 rounded bg-brand-bg/40 text-[10px] flex items-center gap-2">
                                            <span class="font-mono">${a.model || '?'}</span>
                                            <span class="${a.status === 'passed' ? 'text-emerald-400' : 'text-red-400'}">${a.status}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </details>
                        </div>
                    `;

                    document.getElementById('mod-switch-model')?.addEventListener('click', () => {
                        // Switch model in the dropdown and generate
                        const modelSel = document.getElementById('gen-model');
                        if (modelSel) modelSel.value = workingModel;
                        if (this._promptEditor) this._promptEditor.setText(originalPrompt);
                        this._promptEditor._moderationOriginal = null; // No rewrite — original prompt preserved
                        dialog.remove();
                        setTimeout(() => this._handleGenerate(), 100);
                    });

                    document.getElementById('mod-rewrite-instead')?.addEventListener('click', async () => {
                        // User insists on original model — need a rewrite that passes it
                        const content = document.getElementById('mod-content');
                        if (content) {
                            content.innerHTML = `<div class="flex flex-col items-center justify-center py-8 gap-3 text-brand-text-muted">
                                <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                <p>Rewriting prompt for ${this._escapeHtml(originalModelLabel)}...</p>
                                <p class="text-[10px] text-brand-text-muted/50">Testing rewrites with canary images</p>
                            </div>`;
                        }
                        try {
                            // Force rewrite by pretending all models failed
                            const rewriteResult = await API.analyzeModeration({
                                prompt: originalPrompt,
                                error_message: 'User requested rewrite for ' + analysis.original_model,
                                image_model: analysis.original_model,
                                width: 512,
                                height: 512,
                            });
                            if (rewriteResult.rewritten_prompt && rewriteResult.verified) {
                                if (this._promptEditor) {
                                    this._promptEditor._moderationOriginal = originalPrompt;
                                    this._promptEditor.setText(rewriteResult.rewritten_prompt);
                                }
                                // Switch back to original model
                                const modelSel = document.getElementById('gen-model');
                                if (modelSel) modelSel.value = analysis.original_model;
                                dialog.remove();
                                setTimeout(() => this._handleGenerate(), 100);
                            } else {
                                dialog.remove();
                                window.showToast?.('Could not create a verified rewrite for ' + originalModelLabel + '. Try Stable Diffusion 3.5 Large instead.', 'warning');
                            }
                        } catch (err) {
                            dialog.remove();
                            window.showToast?.('Rewrite failed: ' + (err.message || ''), 'error');
                        }
                    });

                } else {
                    // ── Rewrite dialog — all models rejected, need to modify the prompt ──
                    const verifiedBadge = verified
                        ? '<span class="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">Verified — passed moderation</span>'
                        : '<span class="inline-flex items-center gap-1 text-xs font-medium text-red-400 bg-red-400/10 px-2 py-0.5 rounded-full">Not verified — may still be rejected</span>';

                    content.innerHTML = `
                        <div class="space-y-5">
                            <div>
                                <p class="text-sm text-brand-text/90 leading-relaxed">${this._escapeHtml(analysis.explanation || 'Your prompt was blocked by all available image models.')}</p>
                                <p class="text-xs text-brand-text-muted mt-1">${(analysis.attempts || []).length} attempt(s) tested internally</p>
                        </div>

                        ${(analysis.issues || []).length > 0 ? `
                        <div>
                            <h3 class="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">Issues Detected</h3>
                            <ul class="space-y-1.5">
                                ${analysis.issues.map(issue => `
                                    <li class="flex items-start gap-2 text-sm text-brand-text-muted">
                                        <svg class="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01"/>
                                        </svg>
                                        ${this._escapeHtml(issue)}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>` : ''}

                        <div>
                            <h3 class="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                Recommended Rewrite ${verifiedBadge}
                            </h3>
                            <textarea id="mod-rewritten-prompt" class="input w-full min-h-[120px] text-sm">${this._escapeHtml(analysis.rewritten_prompt || '')}</textarea>
                            <p class="text-[10px] text-brand-text-muted mt-1">${verified ? 'This rewrite has been tested and passes moderation. You can still edit it.' : 'This rewrite has NOT been verified. You may need to edit further.'}</p>
                        </div>

                        <div>
                            <details class="text-xs">
                                <summary class="text-brand-text-muted cursor-pointer hover:text-brand-text">View original prompt</summary>
                                <p class="mt-2 p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._escapeHtml(originalPrompt)}</p>
                            </details>
                        </div>

                        ${(analysis.attempts || []).length > 1 ? `
                        <div>
                            <details class="text-xs">
                                <summary class="text-brand-text-muted cursor-pointer hover:text-brand-text">View ${analysis.attempts.length} rewrite attempts</summary>
                                <div class="mt-2 space-y-2">
                                    ${(analysis.attempts || []).map((a, i) => `
                                        <div class="p-2 rounded-lg bg-brand-bg/40 border border-brand-border">
                                            <div class="flex items-center gap-2 mb-1">
                                                <span class="text-[10px] font-bold">Attempt ${a.attempt}</span>
                                                <span class="text-[10px] ${a.status === 'passed' ? 'text-emerald-400' : 'text-red-400'}">${a.status}</span>
                                            </div>
                                            <p class="text-[10px] text-brand-text-muted whitespace-pre-wrap">${this._escapeHtml(a.prompt || '').substring(0, 200)}${(a.prompt || '').length > 200 ? '...' : ''}</p>
                                        </div>
                                    `).join('')}
                                </div>
                            </details>
                        </div>` : ''}

                        <div class="flex gap-3 pt-2">
                            <button id="mod-use-rewrite" class="btn btn-primary flex-1">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                </svg>
                                ${verified ? 'Use This Prompt & Generate' : 'Use This Prompt & Try Generating'}
                            </button>
                            <button id="mod-dismiss" class="btn btn-secondary">
                                Edit Manually
                            </button>
                        </div>
                    </div>
                `;

                    // Wire up rewrite buttons (inside the else block)
                document.getElementById('mod-use-rewrite')?.addEventListener('click', () => {
                    const rewritten = document.getElementById('mod-rewritten-prompt')?.value?.trim();
                    if (rewritten && this._promptEditor) {
                        this._promptEditor._moderationOriginal = originalPrompt;
                        this._promptEditor.setText(rewritten);
                    }
                    dialog.remove();
                    // Auto-trigger generation with the rewritten prompt
                    setTimeout(() => this._handleGenerate(), 100);
                });

                document.getElementById('mod-dismiss')?.addEventListener('click', () => {
                    // Just set the prompt in the editor, let user edit manually
                    const rewritten = document.getElementById('mod-rewritten-prompt')?.value?.trim();
                    if (rewritten && this._promptEditor) {
                        this._promptEditor._moderationOriginal = originalPrompt;
                        this._promptEditor.setText(rewritten);
                    }
                    dialog.remove();
                    window.showToast?.('Prompt updated — edit and click Generate when ready', 'info');
                });

                } // end else (rewrite dialog)

            } catch (err) {
                const content = document.getElementById('mod-content');
                if (content) {
                    content.innerHTML = `
                        <div class="text-center py-8">
                            <p class="text-red-400 mb-2">Failed to analyze the prompt</p>
                            <p class="text-sm text-brand-text-muted">Try rephrasing your prompt to remove references to violence, copyrighted characters, or sensitive content.</p>
                            <button class="mod-close-btn btn btn-secondary btn-sm mt-4">Close</button>
                        </div>
                    `;
                    content.querySelector('.mod-close-btn')?.addEventListener('click', () => dialog.remove());
                }
            }
        },

        _showPromptRefusalDialog(originalPrompt, reason) {
            document.getElementById('moderation-dialog')?.remove();

            const dialog = document.createElement('div');
            dialog.id = 'moderation-dialog';
            dialog.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            dialog.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center gap-3 px-6 py-4 border-b border-brand-border bg-red-950/30">
                        <svg class="w-6 h-6 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                        </svg>
                        <h2 class="text-lg font-semibold text-red-300">Prompt Cannot Be Processed</h2>
                        <button class="mod-close ml-auto p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex-1 overflow-auto p-6 space-y-4">
                        <p class="text-sm text-brand-text/90 leading-relaxed">The AI prompt engine declined to process your request. This typically happens with prompts that ask for:</p>
                        <ul class="space-y-1 text-sm text-brand-text-muted">
                            <li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">•</span> Recognizable likenesses of real, living people</li>
                            <li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">•</span> Content that could be used for misinformation</li>
                            <li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">•</span> Explicitly harmful or unsafe content</li>
                        </ul>
                        <div class="p-3 rounded-lg bg-brand-bg/60 text-xs text-brand-text-muted">
                            <p class="font-medium mb-1">AI response:</p>
                            <p class="whitespace-pre-wrap">${this._escapeHtml(reason).substring(0, 500)}</p>
                        </div>
                        <p class="text-xs text-brand-text-muted">Note: AI image models cannot generate recognizable likenesses of specific real people. For game art, use original character descriptions instead of real-person names.</p>
                        <div class="flex gap-3 pt-2">
                            <button class="mod-close-btn btn btn-secondary flex-1">Edit Prompt</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            dialog.querySelector('.mod-close')?.addEventListener('click', () => dialog.remove());
            dialog.querySelector('.mod-close-btn')?.addEventListener('click', () => dialog.remove());
            dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.remove(); });
        },

        _showPreCheckDialog(originalPrompt, screen, payload) {
            document.getElementById('moderation-dialog')?.remove();

            const issues = screen.issues || [];
            const suggested = screen.suggested_model;
            const suggestedLabel = screen.suggested_model_label || suggested;
            const currentModel = payload.image_model;
            const modelLabels = { nova_canvas: 'Nova Canvas', titan_image: 'Titan Image v2', sd35_large: 'Stable Diffusion 3.5 Large', stable_image_ultra: 'Stable Image Ultra' };
            const currentLabel = modelLabels[currentModel] || currentModel;

            const dialog = document.createElement('div');
            dialog.id = 'moderation-dialog';
            dialog.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            dialog.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center gap-3 px-6 py-4 border-b border-brand-border bg-brand-accent/10">
                        <svg class="w-6 h-6 text-brand-accent flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                        </svg>
                        <h2 class="text-lg font-semibold">Prompt Pre-Check</h2>
                        <button class="mod-close ml-auto p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex-1 overflow-auto p-6 space-y-5">
                        <p class="text-sm text-brand-text/90">${this._escapeHtml(screen.explanation || 'This prompt may be blocked by the selected model.')}</p>

                        ${issues.length > 0 ? `
                        <div>
                            <h3 class="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">Potential Issues</h3>
                            <ul class="space-y-1">
                                ${issues.map(i => `<li class="flex items-start gap-2 text-sm text-brand-text-muted">
                                    <span class="text-amber-400 mt-0.5">•</span> ${this._escapeHtml(i)}
                                </li>`).join('')}
                            </ul>
                        </div>` : ''}

                        ${suggested ? `
                        <div class="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/20">
                            <p class="text-sm text-emerald-300 font-medium mb-1">Recommended: Switch to ${this._escapeHtml(suggestedLabel)}</p>
                            <p class="text-xs text-brand-text-muted">Your prompt will work as-is on this model. No changes needed.</p>
                        </div>` : ''}

                        <div class="flex flex-wrap gap-3 pt-2">
                            ${suggested ? `
                            <button id="precheck-switch" class="btn bg-emerald-600 hover:bg-emerald-500 text-white flex-1">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                </svg>
                                Generate with ${this._escapeHtml(suggestedLabel)}
                            </button>` : ''}
                            <button id="precheck-proceed" class="btn btn-secondary ${suggested ? '' : 'flex-1'}">
                                Try ${this._escapeHtml(currentLabel)} Anyway
                            </button>
                            <button id="precheck-cancel" class="btn btn-secondary btn-sm">
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(dialog);
            dialog.querySelector('.mod-close')?.addEventListener('click', () => dialog.remove());
            dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.remove(); });
            document.getElementById('precheck-cancel')?.addEventListener('click', () => dialog.remove());

            // Switch model and generate
            document.getElementById('precheck-switch')?.addEventListener('click', () => {
                const modelSel = document.getElementById('gen-model');
                if (modelSel && suggested) modelSel.value = suggested;
                dialog.remove();
                this._handleGenerate();
            });

            // Proceed with original model anyway (skip pre-check this time)
            document.getElementById('precheck-proceed')?.addEventListener('click', () => {
                dialog.remove();
                // Temporarily disable pre-check for this generation
                const cb = document.getElementById('gen-precheck');
                const wasChecked = cb?.checked;
                if (cb) cb.checked = false;
                this._handleGenerate();
                // Restore after a tick
                setTimeout(() => { if (cb && wasChecked) cb.checked = true; }, 500);
            });
        },

        _progressTimer: null,

        _setGenerating(on, total, payload) {
            this._generating = on;
            const btn = document.getElementById('btn-generate');
            const loadingEl = document.getElementById('gen-loading');
            const loadingText = document.getElementById('gen-loading-text');
            const loadingSub = document.getElementById('gen-loading-sub');
            const progressBar = document.getElementById('gen-progress-bar');
            const elapsed = document.getElementById('gen-loading-elapsed');
            const placeholder = document.getElementById('gen-placeholder');

            if (on) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> Generating...';
                loadingEl?.classList.remove('hidden');
                placeholder?.classList.add('hidden');
                document.getElementById('gen-result-img')?.classList.add('hidden');
                document.getElementById('gen-download-bar')?.classList.add('hidden');
                document.getElementById('gen-options-section')?.classList.add('hidden');
                document.getElementById('gen-variations-section')?.classList.add('hidden');
                document.getElementById('gen-concept-prompt')?.classList.add('hidden');
                document.getElementById('gen-prompt-info')?.classList.add('hidden');

                // Start progress simulation
                this._startProgress(total, payload);
            } else {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Generate`;
                loadingEl?.classList.add('hidden');
                this._stopProgress();
            }
        },

        _startProgress(total, payload) {
            this._stopProgress();

            const elapsedEl = document.getElementById('gen-loading-elapsed');
            const text = document.getElementById('gen-loading-text');
            const sub = document.getElementById('gen-loading-sub');
            const bar = document.getElementById('gen-progress-bar');
            const startTime = Date.now();

            if (text) text.textContent = 'Starting...';
            if (sub) sub.textContent = `${total} image${total > 1 ? 's' : ''} queued`;
            if (bar) bar.style.width = '2%';

            // Elapsed timer
            const tick = setInterval(() => {
                const secs = Math.floor((Date.now() - startTime) / 1000);
                const min = Math.floor(secs / 60);
                const sec = secs % 60;
                if (elapsedEl) elapsedEl.textContent = min > 0 ? `${min}m ${sec}s elapsed` : `${sec}s elapsed`;
            }, 1000);

            this._progressTimer = { tick };
        },

        _stopProgress() {
            if (this._progressTimer) {
                clearInterval(this._progressTimer.tick);
                this._progressTimer = null;
            }
        },

        _handleProgressEvent(evt, total) {
            const text = document.getElementById('gen-loading-text');
            const sub = document.getElementById('gen-loading-sub');
            const bar = document.getElementById('gen-progress-bar');

            switch (evt.type) {
                case 'started':
                    if (text) text.textContent = 'Starting generation...';
                    if (bar) bar.style.width = '5%';
                    break;

                case 'stage':
                    if (text) text.textContent = evt.message || evt.stage;
                    if (evt.stage === 'prompts') {
                        if (sub) sub.textContent = 'AI is creating concept prompts';
                        if (bar) bar.style.width = '10%';
                    } else if (evt.stage === 'generating') {
                        if (sub) sub.textContent = `${evt.prompts_done || ''} concept${(evt.prompts_done || 0) > 1 ? 's' : ''} ready`;
                        if (bar) bar.style.width = '20%';
                    } else if (evt.stage === 'finalizing') {
                        if (sub) sub.textContent = 'Saving assets and metadata';
                        if (bar) bar.style.width = '95%';
                    }
                    break;

                case 'image_done': {
                    const done = evt.completed || 0;
                    const tot = evt.total || total;
                    const pct = 20 + Math.round((done / tot) * 70);
                    if (text) text.textContent = `Generating images... ${done}/${tot}`;
                    if (sub) sub.textContent = `Option ${(evt.option || 0) + 1}, Variation ${(evt.variation || 0) + 1} complete`;
                    if (bar) bar.style.width = Math.min(pct, 92) + '%';
                    break;
                }

                case 'image_error': {
                    const done = evt.completed || 0;
                    const tot = evt.total || total;
                    if (sub) sub.textContent = `Option ${(evt.option || 0) + 1}, Variation ${(evt.variation || 0) + 1} failed — continuing`;
                    break;
                }

                case 'throttled': {
                    if (text) text.textContent = 'API throttled — waiting to retry...';
                    if (sub) sub.textContent = `Option ${(evt.option || 0) + 1}, Variation ${(evt.variation || 0) + 1} — waiting ${evt.delay || '?'}s`;
                    break;
                }

                case 'retry': {
                    if (text) text.textContent = `Retrying... (attempt ${evt.attempt || '?'}/${evt.max_retries || '?'})`;
                    if (sub) sub.textContent = `Option ${(evt.option || 0) + 1}, Variation ${(evt.variation || 0) + 1}`;
                    break;
                }

                case 'canary':
                    if (text) text.textContent = evt.message || 'Testing prompt...';
                    if (sub) sub.textContent = 'Verifying prompt passes content moderation';
                    if (bar) bar.style.width = '15%';
                    break;

                case 'moderation_blocked':
                    if (text) text.textContent = 'Content moderation blocked';
                    if (sub) sub.textContent = evt.message || 'Stopping generation — prompt needs revision';
                    if (bar) bar.style.width = '100%';
                    // Track for the dialog
                    this._moderationErrors.push(evt.error || 'Content moderation blocked');
                    break;

                case 'prompt_refused':
                    if (text) text.textContent = 'Prompt cannot be processed';
                    if (sub) sub.textContent = evt.message || 'The AI declined to process this prompt';
                    if (bar) bar.style.width = '100%';
                    break;

                case 'complete':
                    if (bar) bar.style.width = '100%';
                    if (text) text.textContent = 'Done!';
                    break;
            }
        },

        // ── Render Results ──────────────────────────────────────────

        _renderResults(result) {
            const options = result.options || [];

            // Switch to "Post-Processing" mode now that results exist
            const labelEl = document.getElementById('gen-processing-label');
            if (labelEl) labelEl.textContent = 'Post-Processing';
            document.getElementById('btn-apply-postprocess')?.classList.remove('hidden');
            document.getElementById('pp-hint')?.classList.remove('hidden');

            // Show original vs used prompt
            const infoSection = document.getElementById('gen-prompt-info');
            const origSection = document.getElementById('gen-original-prompt-section');
            const origText = document.getElementById('gen-original-prompt-text');
            const usedText = document.getElementById('gen-used-prompt-text');
            if (infoSection) {
                infoSection.classList.remove('hidden');
                if (result.original_prompt && result.original_prompt !== result.prompt) {
                    origSection?.classList.remove('hidden');
                    if (origText) origText.textContent = result.original_prompt;
                    if (usedText) usedText.textContent = result.prompt;
                } else {
                    // No AI improvement was used — just show the prompt
                    origSection?.classList.add('hidden');
                    if (usedText) usedText.textContent = result.prompt;
                    const usedLabel = document.querySelector('#gen-used-prompt-section > p:first-child');
                    if (usedLabel) usedLabel.textContent = 'PROMPT';
                }
            }

            // Show options row
            this._renderOptionsRow(options);

            // Select first option, first variant
            this._selectOption(0);
        },

        _renderOptionsRow(options) {
            const section = document.getElementById('gen-options-section');
            const grid = document.getElementById('gen-options-grid');
            const countEl = document.getElementById('gen-options-count');
            if (!section || !grid) return;

            if (options.length <= 1) {
                // Single option — skip the options row, go straight to variations
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');
            if (countEl) countEl.textContent = `${options.length} options`;

            // Adjust grid columns to match option count
            grid.className = `grid gap-3 grid-cols-${Math.min(options.length, 5)}`;

            grid.innerHTML = options.map((opt, i) => {
                const thumb = opt.variants?.[0];
                const thumbSrc = thumb ? thumb.png_path : '';
                return `
                    <button
                        class="option-card group relative rounded-xl overflow-hidden border-2 transition-all duration-200 cursor-pointer
                               ${i === 0 ? 'border-brand-accent ring-2 ring-brand-accent/40 shadow-lg shadow-brand-accent/20' : 'border-brand-border hover:border-brand-accent/50'}"
                        data-option-index="${i}"
                    >
                        <div class="aspect-square bg-brand-bg">
                            ${thumbSrc
                                ? `<img src="${thumbSrc}" alt="Option ${i + 1}" class="w-full h-full object-cover" loading="lazy" />`
                                : `<div class="w-full h-full flex items-center justify-center text-brand-text-muted/30 text-xs">No image</div>`
                            }
                        </div>
                        <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors"></div>
                        <div class="absolute top-1.5 left-1.5 bg-black/70 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                            Option ${i + 1}
                        </div>
                        <div class="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 to-transparent p-2 pt-6">
                            <p class="text-white text-[10px] leading-tight line-clamp-2">${this._escapeHtml(opt.refined_prompt || '').substring(0, 80)}...</p>
                        </div>
                    </button>
                `;
            }).join('');

            grid.querySelectorAll('.option-card').forEach(btn => {
                btn.addEventListener('click', () => {
                    this._selectOption(parseInt(btn.dataset.optionIndex, 10));
                });
            });
        },

        _selectOption(index) {
            const result = this._result;
            if (!result) return;
            const options = result.options || [];
            const option = options[index];
            if (!option) return;

            this._selectedOption = index;
            this._selectedVariant = 0;

            // Update option highlight
            const grid = document.getElementById('gen-options-grid');
            if (grid) {
                grid.querySelectorAll('.option-card').forEach((btn, i) => {
                    if (i === index) {
                        btn.classList.remove('border-brand-border');
                        btn.classList.add('border-brand-accent', 'ring-2', 'ring-brand-accent/40', 'shadow-lg', 'shadow-brand-accent/20');
                    } else {
                        btn.classList.remove('border-brand-accent', 'ring-2', 'ring-brand-accent/40', 'shadow-lg', 'shadow-brand-accent/20');
                        btn.classList.add('border-brand-border');
                    }
                });
            }

            // Show concept prompt
            const conceptSection = document.getElementById('gen-concept-prompt');
            const conceptText = document.getElementById('gen-concept-prompt-text');
            if (conceptSection && conceptText && option.refined_prompt) {
                conceptSection.classList.remove('hidden');
                conceptText.textContent = option.refined_prompt;
            }

            // Render variations for this option
            this._renderVariationsRow(option.variants || []);
            this._selectVariant(0);

            // Scroll down to the preview area
            document.getElementById('gen-preview')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        },

        _renderVariationsRow(variants) {
            const section = document.getElementById('gen-variations-section');
            const grid = document.getElementById('gen-variations-grid');
            const countEl = document.getElementById('gen-variations-count');
            if (!section || !grid) return;

            if (variants.length <= 1) {
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');
            if (countEl) countEl.textContent = `${variants.length} variations`;

            grid.className = `grid gap-3 grid-cols-${Math.min(variants.length, 5)}`;

            grid.innerHTML = variants.map((v, i) => `
                <button
                    class="variant-thumb group relative aspect-square rounded-lg overflow-hidden border-2 transition-all duration-200 cursor-pointer
                           ${i === 0 ? 'border-emerald-400 ring-2 ring-emerald-400/30' : 'border-brand-border hover:border-emerald-400/50'}"
                    data-variant-index="${i}"
                >
                    <img src="${v.png_path}" alt="Variation ${i + 1}" class="w-full h-full object-cover" loading="lazy" />
                    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors"></div>
                    <span class="absolute bottom-1 right-1 text-[10px] font-bold bg-black/60 text-white px-1.5 py-0.5 rounded">
                        v${i + 1}
                    </span>
                </button>
            `).join('');

            grid.querySelectorAll('.variant-thumb').forEach(btn => {
                btn.addEventListener('click', () => {
                    this._selectVariant(parseInt(btn.dataset.variantIndex, 10));
                });
            });
        },

        _selectVariant(index) {
            const result = this._result;
            if (!result) return;
            const option = (result.options || [])[this._selectedOption];
            if (!option) return;
            const variants = option.variants || [];
            const variant = variants[index];
            if (!variant) return;

            this._selectedVariant = index;

            // Update variation highlight
            const grid = document.getElementById('gen-variations-grid');
            if (grid) {
                grid.querySelectorAll('.variant-thumb').forEach((btn, i) => {
                    if (i === index) {
                        btn.classList.remove('border-brand-border');
                        btn.classList.add('border-emerald-400', 'ring-2', 'ring-emerald-400/30');
                    } else {
                        btn.classList.remove('border-emerald-400', 'ring-2', 'ring-emerald-400/30');
                        btn.classList.add('border-brand-border');
                    }
                });
            }

            // Update main preview
            const img = document.getElementById('gen-result-img');
            const placeholder = document.getElementById('gen-placeholder');
            const downloadBar = document.getElementById('gen-download-bar');

            if (img) {
                img.src = variant.png_path;
                img.classList.remove('hidden');
            }
            placeholder?.classList.add('hidden');

            if (downloadBar) {
                downloadBar.classList.remove('hidden');
                const info = document.getElementById('gen-result-info');
                if (info) {
                    // Show the filename as the label
                    info.textContent = variant.png_filename || variant.id;
                }
                const dlPng = document.getElementById('dl-png');
                const dlSvg = document.getElementById('dl-svg');
                if (dlPng) {
                    dlPng.href = variant.png_path;
                    dlPng.setAttribute('download', variant.png_filename || 'asset.png');
                }
                if (dlSvg) {
                    if (variant.svg_path) {
                        dlSvg.href = variant.svg_path;
                        dlSvg.setAttribute('download', variant.svg_filename || 'asset.svg');
                        dlSvg.classList.remove('hidden');
                    } else {
                        dlSvg.classList.add('hidden');
                    }
                }
            }
        },

        // ── Load batch from Gallery ──────────────────────────────────

        async loadBatch(batchId) {
            // Navigate to generator view first
            window.location.hash = '#image-studio';

            // Wait until the view's DOM is actually ready
            // (navigate() is async — init() loads styles from API which takes time)
            const maxWait = 5000;
            const start = Date.now();
            while (!document.getElementById('gen-preview') && (Date.now() - start) < maxWait) {
                await new Promise(r => setTimeout(r, 100));
            }

            window.showLoading?.('Loading batch...');
            try {
                const result = await API.gallery.getBatch(batchId);
                this._result = result;
                this._selectedOption = 0;
                this._selectedVariant = 0;

                // Ensure prompt editor exists, then populate
                this._ensurePromptEditor();
                if (this._promptEditor) {
                    const displayPrompt = result.prompt || '';
                    this._promptEditor.setText(displayPrompt);
                    // Store original so getOriginalText() returns the right thing
                    if (result.original_prompt) {
                        this._promptEditor._originalText = result.original_prompt;
                    }
                }

                // Set sidebar controls to match the batch settings
                const styleSel = document.getElementById('gen-style');
                if (styleSel) styleSel.value = result.style_id || '';

                const typeSel = document.getElementById('gen-asset-type');
                if (typeSel && result.asset_type) typeSel.value = result.asset_type;

                const modelSel = document.getElementById('gen-model');
                if (modelSel && result.image_model) modelSel.value = result.image_model;

                // Restore dimension preset
                const sizeSel = document.getElementById('gen-size');
                if (sizeSel && result.width && result.height) {
                    const sizeStr = `${result.width} x ${result.height}`;
                    for (let i = 0; i < sizeSel.options.length; i++) {
                        if (sizeSel.options[i].text === sizeStr) {
                            sizeSel.value = i;
                            break;
                        }
                    }
                }

                // Restore toggle switches
                const removeBg = document.getElementById('gen-remove-bg');
                if (removeBg) removeBg.checked = result.remove_background ?? false;

                const genSvg = document.getElementById('gen-svg');
                if (genSvg) genSvg.checked = result.generate_svg ?? false;

                const upscale = document.getElementById('gen-upscale');
                if (upscale) upscale.checked = result.upscale ?? false;

                // Restore options/variations counts
                const optsSel = document.getElementById('gen-num-options');
                if (optsSel && result.num_options) optsSel.value = result.num_options;

                const varsSel = document.getElementById('gen-num-variations');
                if (varsSel && result.num_variations) varsSel.value = result.num_variations;

                // Render the results
                this._renderResults(result);

                window.hideLoading?.();
                window.showToast?.(`Batch loaded: ${result.num_options} options x ${result.num_variations} variations`, 'success');
            } catch (err) {
                window.hideLoading?.();
                console.error('Failed to load batch:', err);
            }
        },

        // ── Helpers ─────────────────────────────────────────────────

        _getStyleId() {
            return document.getElementById('gen-style')?.value || '';
        },
        _getAssetType() {
            return document.getElementById('gen-asset-type')?.value || 'game_asset';
        },
        _escapeHtml(str) {
            const d = document.createElement('div');
            d.textContent = str;
            return d.innerHTML;
        },
    };
})();
