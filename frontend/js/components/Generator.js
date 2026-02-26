/**
 * ArtSmoker — Generator Component
 *
 * The main workspace for generating AI art assets.
 * Left sidebar with controls, center with prompt editor and preview.
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
        { value: 'titan_image', label: 'Titan Image' },
    ];

    const SIZE_PRESETS = [
        { label: '512 x 512', w: 512, h: 512 },
        { label: '768 x 768', w: 768, h: 768 },
        { label: '1024 x 1024', w: 1024, h: 1024 },
        { label: '1024 x 576', w: 1024, h: 576 },
        { label: '576 x 1024', w: 576, h: 1024 },
        { label: '1280 x 720', w: 1280, h: 720 },
    ];

    window.Generator = {
        _styles: [],
        _promptEditor: null,
        _generating: false,
        _result: null,

        render() {
            return `
                <div id="generator-view" class="view-enter">
                    <div class="flex flex-col lg:flex-row gap-6">

                        <!-- Left Sidebar: Controls -->
                        <aside class="lg:w-72 xl:w-80 flex-shrink-0 space-y-5">
                            <div class="card-static p-5 space-y-5">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
                                    </svg>
                                    Settings
                                </h2>

                                <!-- Style Selector -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Art Style</label>
                                    <select id="gen-style" class="input">
                                        <option value="">None (default)</option>
                                    </select>
                                </div>

                                <!-- Asset Type -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Asset Type</label>
                                    <select id="gen-asset-type" class="input">
                                        ${ASSET_TYPES.map((t) => `<option value="${t.value}">${t.label}</option>`).join('')}
                                    </select>
                                </div>

                                <!-- Image Model -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Image Model</label>
                                    <select id="gen-model" class="input">
                                        ${MODELS.map((m) => `<option value="${m.value}">${m.label}</option>`).join('')}
                                    </select>
                                </div>

                                <!-- Size Preset -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Dimensions</label>
                                    <select id="gen-size" class="input">
                                        ${SIZE_PRESETS.map((s, i) => `<option value="${i}" ${i === 2 ? 'selected' : ''}>${s.label}</option>`).join('')}
                                    </select>
                                </div>

                                <!-- Toggles -->
                                <div class="space-y-3 pt-2">
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Remove Background</label>
                                        <label class="toggle">
                                            <input type="checkbox" id="gen-remove-bg">
                                            <span class="toggle-slider"></span>
                                        </label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Convert to SVG</label>
                                        <label class="toggle">
                                            <input type="checkbox" id="gen-svg">
                                            <span class="toggle-slider"></span>
                                        </label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">Upscale</label>
                                        <label class="toggle">
                                            <input type="checkbox" id="gen-upscale">
                                            <span class="toggle-slider"></span>
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </aside>

                        <!-- Center: Prompt + Preview -->
                        <div class="flex-1 min-w-0 space-y-5">
                            <!-- Prompt Editor Area -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                    </svg>
                                    Prompt
                                </h2>
                                <div id="prompt-editor-container"></div>
                            </div>

                            <!-- Generate Button -->
                            <button id="btn-generate" class="btn btn-primary btn-lg w-full text-base">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                </svg>
                                Generate Image
                            </button>

                            <!-- Preview Area -->
                            <div class="card-static overflow-hidden">
                                <div id="gen-preview" class="preview-checkerboard min-h-[350px] lg:min-h-[450px] flex items-center justify-center p-6 relative">
                                    <!-- Placeholder -->
                                    <div id="gen-placeholder" class="text-center">
                                        <svg class="w-16 h-16 mx-auto text-brand-text-muted/20 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                                        </svg>
                                        <p class="text-brand-text-muted/40 text-sm">Your generated image will appear here</p>
                                    </div>

                                    <!-- Loading state (hidden) -->
                                    <div id="gen-loading" class="hidden absolute inset-0 bg-brand-bg/60 flex flex-col items-center justify-center gap-4">
                                        <div class="loading-spinner w-10 h-10 border-4 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                        <p class="text-sm text-brand-text-muted font-medium">Generating your image...</p>
                                        <p class="text-xs text-brand-text-muted/60">This may take a moment</p>
                                    </div>

                                    <!-- Result image (hidden) -->
                                    <img id="gen-result-img" class="hidden max-w-full max-h-[60vh] rounded-lg shadow-2xl" alt="Generated image" />
                                </div>

                                <!-- Download bar (hidden) -->
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
                                        <a id="dl-svg" href="#" download class="btn btn-secondary btn-sm">
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
            // Load styles into dropdown
            await this._loadStyles();

            // Initialize prompt editor
            const container = document.getElementById('prompt-editor-container');
            if (container) {
                this._promptEditor = new PromptEditor(container, {
                    styleId: this._getStyleId(),
                    assetType: this._getAssetType(),
                });
            }

            // Style/type change -> update prompt editor context
            document.getElementById('gen-style')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ styleId: this._getStyleId() });
            });
            document.getElementById('gen-asset-type')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ assetType: this._getAssetType() });
            });

            // Generate button
            document.getElementById('btn-generate')?.addEventListener('click', () => this._handleGenerate());
        },

        // --------------------------------------------------------
        //  Data
        // --------------------------------------------------------

        async _loadStyles() {
            try {
                const data = await API.styles.list();
                this._styles = Array.isArray(data) ? data : (data.styles || data.items || []);
            } catch (err) {
                this._styles = [];
            }

            const sel = document.getElementById('gen-style');
            if (!sel) return;
            // keep first "None" option
            const none = sel.querySelector('option');
            sel.innerHTML = '';
            sel.appendChild(none);
            this._styles.forEach((s) => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.name;
                sel.appendChild(opt);
            });
        },

        // --------------------------------------------------------
        //  Generation
        // --------------------------------------------------------

        async _handleGenerate() {
            if (this._generating) return;
            const prompt = this._promptEditor ? this._promptEditor.getText().trim() : '';
            if (!prompt) {
                window.showToast && window.showToast('Enter a prompt before generating', 'warning');
                return;
            }

            const sizeIdx = parseInt(document.getElementById('gen-size').value, 10);
            const size = SIZE_PRESETS[sizeIdx] || SIZE_PRESETS[2];

            const payload = {
                prompt,
                style_id: this._getStyleId() || undefined,
                asset_type: this._getAssetType(),
                model: document.getElementById('gen-model').value,
                width: size.w,
                height: size.h,
                remove_background: document.getElementById('gen-remove-bg').checked,
                convert_to_svg: document.getElementById('gen-svg').checked,
                upscale: document.getElementById('gen-upscale').checked,
            };

            this._setGenerating(true);

            try {
                const result = await API.generate(payload);
                this._result = result;
                this._showResult(result);
                window.showToast && window.showToast('Image generated successfully!', 'success');
            } catch (err) {
                console.error('Generation error:', err);
            } finally {
                this._setGenerating(false);
            }
        },

        _setGenerating(on) {
            this._generating = on;
            const btn = document.getElementById('btn-generate');
            const loadingEl = document.getElementById('gen-loading');
            const placeholder = document.getElementById('gen-placeholder');

            if (on) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> Generating...';
                loadingEl?.classList.remove('hidden');
                placeholder?.classList.add('hidden');
                document.getElementById('gen-result-img')?.classList.add('hidden');
                document.getElementById('gen-download-bar')?.classList.add('hidden');
            } else {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Generate Image`;
                loadingEl?.classList.add('hidden');
            }
        },

        _showResult(result) {
            const img = document.getElementById('gen-result-img');
            const placeholder = document.getElementById('gen-placeholder');
            const downloadBar = document.getElementById('gen-download-bar');

            // The result should contain a gallery item or at least an id
            const galleryId = result.gallery_id || result.id;
            if (!galleryId) {
                window.showToast && window.showToast('Generation returned no image ID', 'error');
                return;
            }

            const pngUrl = API.gallery.pngUrl(galleryId);
            const svgUrl = API.gallery.svgUrl(galleryId);

            if (img) {
                img.src = pngUrl;
                img.classList.remove('hidden');
                img.classList.add('fade-in');
            }
            placeholder?.classList.add('hidden');

            // Download bar
            if (downloadBar) {
                downloadBar.classList.remove('hidden');
                const info = document.getElementById('gen-result-info');
                if (info) {
                    info.textContent = `ID: ${galleryId}`;
                }
                const dlPng = document.getElementById('dl-png');
                const dlSvg = document.getElementById('dl-svg');
                if (dlPng) dlPng.href = pngUrl;
                if (dlSvg) dlSvg.href = svgUrl;
            }
        },

        // --------------------------------------------------------
        //  Helpers
        // --------------------------------------------------------

        _getStyleId() {
            return document.getElementById('gen-style')?.value || '';
        },

        _getAssetType() {
            return document.getElementById('gen-asset-type')?.value || 'game_asset';
        },
    };
})();
