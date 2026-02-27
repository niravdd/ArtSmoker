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
        { value: 'sd35_large', label: 'SD 3.5 Large' },
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

                                <!-- Toggles -->
                                <div class="space-y-3 pt-2">
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Remove Background</label>
                                        <label class="toggle"><input type="checkbox" id="gen-remove-bg"><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Convert to SVG</label>
                                        <label class="toggle"><input type="checkbox" id="gen-svg"><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Upscale</label>
                                        <label class="toggle"><input type="checkbox" id="gen-upscale"><span class="toggle-slider"></span></label>
                                    </div>
                                </div>
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
                                    <div id="gen-loading" class="hidden absolute inset-0 bg-brand-bg/60 flex flex-col items-center justify-center gap-4">
                                        <div class="loading-spinner w-10 h-10 border-4 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                        <p id="gen-loading-text" class="text-sm text-brand-text-muted font-medium">Generating...</p>
                                        <p class="text-xs text-brand-text-muted/60">This may take a moment</p>
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

        async init() {
            await this._loadStyles();

            const container = document.getElementById('prompt-editor-container');
            if (container) {
                this._promptEditor = new PromptEditor(container, {
                    styleId: this._getStyleId(),
                    assetType: this._getAssetType(),
                });
            }

            document.getElementById('gen-style')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ styleId: this._getStyleId() });
            });
            document.getElementById('gen-asset-type')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ assetType: this._getAssetType() });
            });
            document.getElementById('btn-generate')?.addEventListener('click', () => this._handleGenerate());
            document.getElementById('btn-reset')?.addEventListener('click', () => {
                if (this._result && !confirm('Reset the generator? Current results will be cleared.')) return;
                window.resetView('generator');
            });
        },

        async _loadStyles() {
            try {
                const data = await API.styles.list();
                this._styles = Array.isArray(data) ? data : [];
            } catch { this._styles = []; }

            const sel = document.getElementById('gen-style');
            if (!sel) return;
            const none = sel.querySelector('option');
            sel.innerHTML = '';
            sel.appendChild(none);
            this._styles.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.name;
                sel.appendChild(opt);
            });
        },

        // ── Generation ──────────────────────────────────────────────

        async _handleGenerate() {
            if (this._generating) return;
            const prompt = this._promptEditor ? this._promptEditor.getText().trim() : '';
            if (!prompt) {
                window.showToast?.('Enter a prompt before generating', 'warning');
                return;
            }

            const sizeIdx = parseInt(document.getElementById('gen-size').value, 10);
            const size = SIZE_PRESETS[sizeIdx] || SIZE_PRESETS[2];
            const numOptions = parseInt(document.getElementById('gen-num-options').value, 10) || 5;
            const numVariations = parseInt(document.getElementById('gen-num-variations').value, 10) || 5;
            const total = numOptions * numVariations;

            const originalPrompt = this._promptEditor ? this._promptEditor.getOriginalText().trim() : prompt;

            const payload = {
                prompt,
                original_prompt: originalPrompt !== prompt ? originalPrompt : null,
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

            this._setGenerating(true, total);

            try {
                const result = await API.generate(payload);
                this._result = result;
                this._selectedOption = 0;
                this._selectedVariant = 0;
                this._renderResults(result);
                const totalGenerated = (result.options || []).reduce((n, o) => n + (o.variants || []).length, 0);
                window.showToast?.(`${totalGenerated} images generated across ${(result.options || []).length} options!`, 'success');
            } catch (err) {
                console.error('Generation error:', err);
            } finally {
                this._setGenerating(false);
            }
        },

        _setGenerating(on, total) {
            this._generating = on;
            const btn = document.getElementById('btn-generate');
            const loadingEl = document.getElementById('gen-loading');
            const loadingText = document.getElementById('gen-loading-text');
            const placeholder = document.getElementById('gen-placeholder');

            if (on) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> Generating...';
                loadingEl?.classList.remove('hidden');
                if (loadingText) loadingText.textContent = `Generating ${total} image${total > 1 ? 's' : ''}...`;
                placeholder?.classList.add('hidden');
                document.getElementById('gen-result-img')?.classList.add('hidden');
                document.getElementById('gen-download-bar')?.classList.add('hidden');
                document.getElementById('gen-options-section')?.classList.add('hidden');
                document.getElementById('gen-variations-section')?.classList.add('hidden');
                document.getElementById('gen-concept-prompt')?.classList.add('hidden');
                document.getElementById('gen-prompt-info')?.classList.add('hidden');
            } else {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Generate`;
                loadingEl?.classList.add('hidden');
            }
        },

        // ── Render Results ──────────────────────────────────────────

        _renderResults(result) {
            const options = result.options || [];

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
            window.location.hash = '#generator';

            // Ensure the generator view is visible and initialized
            // (the DOM-caching router will show the existing view)
            await new Promise(r => setTimeout(r, 100));

            window.showLoading?.('Loading batch...');
            try {
                const result = await API.gallery.getBatch(batchId);
                this._result = result;
                this._selectedOption = 0;
                this._selectedVariant = 0;

                // Populate the prompt editor with the original or current prompt
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
                this._selectOption(0);

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
