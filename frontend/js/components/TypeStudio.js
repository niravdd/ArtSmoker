/**
 * ArtSmoker — Type Studio Component
 *
 * Add text to images or generate standalone text assets.
 * Uses AI for layout suggestions and renders via the backend.
 */
(function () {
    'use strict';

    const POSITIONS = [
        { value: 'top-left',       label: 'Top Left' },
        { value: 'top-center',     label: 'Top Center' },
        { value: 'top-right',      label: 'Top Right' },
        { value: 'center-left',    label: 'Center Left' },
        { value: 'center',         label: 'Center' },
        { value: 'center-right',   label: 'Center Right' },
        { value: 'bottom-left',    label: 'Bottom Left' },
        { value: 'bottom-center',  label: 'Bottom Center' },
        { value: 'bottom-right',   label: 'Bottom Right' },
        { value: 'below-previous', label: 'Below Previous' },
    ];

    // Font display helpers
    function _font_display_name(filename) {
        let name = filename.replace(/\.\w+$/, '');
        name = name.replace(/([a-z])([A-Z])/g, '$1 $2');
        name = name.replace(/[-_]+/g, ' ');
        return name.trim();
    }

    function _font_css_family(font) {
        // For system fonts, use the display name as font-family (browsers resolve it)
        // For custom fonts, we load via @font-face using the served URL
        if (font.source === 'system') {
            return font.display_name || _font_display_name(font.name);
        }
        return `custom-${font.name.replace(/\.\w+$/, '')}`;
    }

    function _filterFontOptions(dropdown, query) {
        const q = query.toLowerCase();
        dropdown.querySelectorAll('.ts-font-option').forEach(opt => {
            const name = (opt.dataset.display || opt.textContent || '').toLowerCase();
            opt.style.display = (!q || name.includes(q)) ? '' : 'none';
        });
        // Also show/hide section headers if all their options are hidden
        dropdown.querySelectorAll('.ts-font-options > div').forEach(el => {
            if (el.classList.contains('ts-font-option')) return;
            // It's a header — check if next siblings until next header have any visible
            let next = el.nextElementSibling;
            let hasVisible = false;
            while (next && !next.textContent.includes('Fonts')) {
                if (next.classList.contains('ts-font-option') && next.style.display !== 'none') {
                    hasVisible = true;
                    break;
                }
                next = next.nextElementSibling;
            }
            el.style.display = (!q || hasVisible) ? '' : 'none';
        });
    }

    // ── Client-side font detection ─────────────────────────────────
    async function _detectClientFonts() {
        const detected = [];

        // Method 1: Local Font Access API (Chrome/Edge 103+)
        if ('queryLocalFonts' in window) {
            try {
                const fonts = await window.queryLocalFonts();
                const seen = new Set();
                for (const f of fonts) {
                    const family = f.family;
                    if (!seen.has(family)) {
                        seen.add(family);
                        detected.push({
                            name: family + '.local',
                            display_name: family,
                            filename: '',
                            source: 'client',
                            path: '',  // Client fonts render directly via CSS font-family
                        });
                    }
                }
                console.log(`Detected ${detected.length} client fonts via Local Font Access API`);
                return detected;
            } catch (err) {
                // Permission denied or not supported — fall through to probing
                console.log('Local Font Access API unavailable:', err.message);
            }
        }

        // Method 2: Font probing via canvas rendering (works everywhere)
        const testFonts = [
            'Arial', 'Arial Black', 'Verdana', 'Tahoma', 'Trebuchet MS',
            'Georgia', 'Times New Roman', 'Courier New', 'Lucida Console',
            'Comic Sans MS', 'Impact', 'Palatino Linotype', 'Book Antiqua',
            'Garamond', 'Century Gothic', 'Futura', 'Helvetica', 'Helvetica Neue',
            'Gill Sans', 'Optima', 'Didot', 'American Typewriter', 'Baskerville',
            'Copperplate', 'Papyrus', 'Brush Script MT', 'Rockwell',
            'Segoe UI', 'Calibri', 'Cambria', 'Candara', 'Consolas',
        ];
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 400;
        canvas.height = 50;
        const testStr = 'mmmmmmmmmmlli';
        const baseFont = 'monospace';

        ctx.font = `20px ${baseFont}`;
        ctx.fillText(testStr, 0, 30);
        const baseWidth = ctx.measureText(testStr).width;

        for (const family of testFonts) {
            ctx.font = `20px '${family}', ${baseFont}`;
            const w = ctx.measureText(testStr).width;
            if (Math.abs(w - baseWidth) > 0.5) {
                detected.push({
                    name: family + '.local',
                    display_name: family,
                    filename: '',
                    source: 'client',
                    path: '',
                });
            }
        }
        console.log(`Detected ${detected.length} client fonts via canvas probing`);
        return detected;
    }

    // Track loaded @font-face to avoid duplicates
    const _loadedFontFaces = new Set();

    function _loadCustomFontFaces(fonts) {
        fonts.forEach(f => {
            if (f.source === 'system' || !f.path || _loadedFontFaces.has(f.name)) return;
            _loadedFontFaces.add(f.name);
            const family = _font_css_family(f);
            const style = document.createElement('style');
            style.textContent = `@font-face { font-family: '${family}'; src: url('${f.path}'); font-display: swap; }`;
            document.head.appendChild(style);
        });
    }

    window.TypeStudio = {
        _styles: [],
        _fonts: [],
        _lines: [],
        _mode: 'on-image',       // 'on-image' | 'standalone'
        _generating: false,
        _suggesting: false,
        _recentImages: [],
        _selectedImageId: '',

        // ── Render ──────────────────────────────────────────────────

        render() {
            return `
                <div id="type-studio-view" class="view-enter">
                    <div class="mb-6">
                        <h1 class="text-2xl font-bold">${t('type_studio.title')}</h1>
                        <p class="text-brand-text-muted text-sm mt-1">${t('type_studio.subtitle')}</p>
                    </div>

                    <div class="flex flex-col lg:flex-row gap-6">

                        <!-- Left Sidebar -->
                        <aside class="lg:w-72 xl:w-80 flex-shrink-0 space-y-5">
                            <div class="card-static p-5 space-y-5">

                                <!-- Mode Toggle -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('type_studio.mode')}</label>
                                    <div class="grid grid-cols-2 gap-1 p-1 bg-brand-bg rounded-lg">
                                        <button id="ts-mode-on-image" class="btn btn-sm text-xs ts-mode-btn ts-mode-active">${t('type_studio.mode_on_image')}</button>
                                        <button id="ts-mode-standalone" class="btn btn-sm text-xs ts-mode-btn">${t('type_studio.mode_standalone')}</button>
                                    </div>
                                </div>

                                <!-- Style Selector -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('type_studio.style')}</label>
                                    <select id="ts-style" class="input">
                                        <option value="">${t('type_studio.style_none')}</option>
                                    </select>
                                </div>

                                <!-- Source Image (On Image mode only) -->
                                <div id="ts-source-image-section">
                                    <label class="block text-sm font-medium mb-1.5">${t('type_studio.source_image')}</label>
                                    <div class="space-y-2">
                                        <input type="text" id="ts-image-id" class="input" placeholder="${t('type_studio.image_id_placeholder')}" />
                                        <select id="ts-recent-images" class="input">
                                            <option value="">${t('type_studio.browse_recent')}</option>
                                        </select>
                                        <div id="ts-image-preview" class="hidden rounded-lg overflow-hidden border border-brand-border bg-brand-bg">
                                            <img id="ts-image-preview-img" class="w-full h-auto" alt="Selected source image" />
                                        </div>
                                    </div>
                                </div>

                                <!-- Font List -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('type_studio.fonts')}</label>
                                    <div id="ts-font-list" class="text-xs text-brand-text-muted space-y-1">
                                        <p>${t('type_studio.fonts_loading')}</p>
                                    </div>
                                </div>

                            </div>

                            <!-- Processing Options -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-sm font-semibold flex items-center gap-2 text-brand-text-muted uppercase tracking-wide">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343"/>
                                    </svg>
                                    <span id="ts-processing-label">${t('type_studio.post_processing')}</span>
                                </h2>
                                <div class="space-y-3">
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">${t('type_studio.remove_bg')}</label>
                                        <label class="toggle"><input type="checkbox" id="ts-remove-bg"><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">${t('type_studio.convert_svg')}</label>
                                        <label class="toggle"><input type="checkbox" id="ts-svg" checked><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">${t('type_studio.upscale')}</label>
                                        <label class="toggle"><input type="checkbox" id="ts-upscale"><span class="toggle-slider"></span></label>
                                    </div>
                                </div>
                                <button id="ts-btn-apply-pp" class="btn btn-secondary btn-sm w-full hidden">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                    </svg>
                                    ${t('type_studio.pp_apply')}
                                </button>
                                <p id="ts-pp-hint" class="text-[10px] text-brand-text-muted/50 hidden">${t('type_studio.pp_hint')}</p>
                            </div>

                            <button id="ts-model-settings-btn" class="w-full text-left p-3 rounded-lg bg-brand-bg/30 border border-brand-border/50 hover:border-brand-accent/30 hover:bg-brand-bg/50 transition-colors flex items-center gap-2 text-xs text-brand-text-muted mt-3">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                                ${t('type_studio.model_settings')}
                            </button>

                            <p class="artsmoker-version text-[9px] text-brand-text-dim/30 text-center mt-4">ArtSmoker</p>
                        </aside>

                        <!-- Center: Editor + Results -->
                        <div class="flex-1 min-w-0 space-y-5">

                            <!-- Text Lines Editor -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
                                    </svg>
                                    ${t('type_studio.text_lines')}
                                </h2>
                                <div id="ts-lines-container" class="space-y-3"></div>
                                <button id="ts-add-line" class="btn btn-secondary btn-sm">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                                    </svg>
                                    ${t('type_studio.add_line')}
                                </button>
                            </div>

                            <!-- Style Note -->
                            <div class="card-static p-5">
                                <label class="block text-sm font-medium mb-1.5">${t('type_studio.style_note')}</label>
                                <textarea id="ts-style-note" class="input min-h-[60px]" rows="2"
                                    placeholder="${t('type_studio.style_note_placeholder')}"></textarea>
                            </div>

                            <!-- Layout Options + AI Model -->
                            <div class="card-static p-5 space-y-3">
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('type_studio.layout_options')}</label>
                                    <select id="ts-num-options" class="input">
                                        <option value="1">1 layout</option>
                                        <option value="2">2 layouts</option>
                                        <option value="3" selected>3 layouts</option>
                                        <option value="4">4 layouts</option>
                                        <option value="5">5 layouts</option>
                                    </select>
                                    <p class="text-[10px] text-brand-text-muted mt-1">${t('type_studio.layout_desc')}</p>
                                </div>
                                <details class="group">
                                    <summary class="text-xs font-medium text-brand-text-muted cursor-pointer hover:text-brand-text">
                                        <span class="group-open:hidden">\u25B8 ${t('type_studio.llm_model')}</span>
                                        <span class="hidden group-open:inline">\u25BE ${t('type_studio.llm_model_expanded')}</span>
                                    </summary>
                                    <div class="mt-1.5">
                                        <select id="ts-llm-complexity" class="input text-xs">
                                            <option value="complex">${t('type_studio.llm_complex')}</option>
                                            <option value="fast">${t('type_studio.llm_fast')}</option>
                                        </select>
                                        <p id="ts-llm-info" class="text-[10px] text-brand-text-dim mt-1"></p>
                                    </div>
                                </details>
                            </div>

                            <!-- Action Buttons -->
                            <div class="grid grid-cols-2 gap-3">
                                <button id="ts-btn-suggest" class="btn btn-secondary btn-lg text-base">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                                    </svg>
                                    ${t('type_studio.suggest')}
                                </button>
                                <button id="ts-btn-generate" class="btn btn-primary btn-lg text-base">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                    </svg>
                                    ${t('type_studio.generate')}
                                </button>
                            </div>

                            <!-- Layout Suggestion -->
                            <div id="ts-suggestion-section" class="hidden card-static p-5 space-y-3">
                                <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wide">
                                    ${t('type_studio.ai_suggestion')}
                                </h3>
                                <div id="ts-suggestion-content" class="text-sm text-brand-text/80 leading-relaxed space-y-2"></div>
                            </div>

                            <!-- Options Row (shown when multiple options generated) -->
                            <div id="ts-options-section" class="hidden">
                                <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wide mb-2">${t('type_studio.layout_options_click')}</h3>
                                <div id="ts-options-grid" class="grid grid-cols-5 gap-3"></div>
                            </div>

                            <!-- Preview Area -->
                            <div class="card-static overflow-hidden">
                                <div id="ts-preview" class="preview-checkerboard min-h-[350px] lg:min-h-[450px] flex items-center justify-center p-6 relative">
                                    <div id="ts-placeholder" class="text-center">
                                        <svg class="w-16 h-16 mx-auto text-brand-text-muted/20 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 6h16M4 12h8m-8 6h16"/>
                                        </svg>
                                        <p class="text-brand-text-muted/40 text-sm">${t('type_studio.preview_placeholder')}</p>
                                    </div>
                                    <div id="ts-loading" class="hidden absolute inset-0 bg-brand-bg/60 flex flex-col items-center justify-center gap-4">
                                        <div class="loading-spinner w-10 h-10 border-4 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                        <p id="ts-loading-text" class="text-sm text-brand-text-muted font-medium">${t('type_studio.processing')}</p>
                                    </div>
                                    <img id="ts-result-img" class="hidden max-w-full max-h-[60vh] rounded-lg shadow-2xl" alt="Type Studio result" />
                                </div>

                                <!-- Download Bar -->
                                <div id="ts-download-bar" class="hidden border-t border-brand-border p-4 flex flex-wrap items-center justify-between gap-3 bg-brand-surface">
                                    <div class="text-sm text-brand-text-muted">
                                        <span id="ts-result-info"></span>
                                    </div>
                                    <div class="flex gap-2">
                                        <a id="ts-dl-png" href="#" download class="btn btn-secondary btn-sm">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                            </svg>
                                            PNG
                                        </a>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
            `;
        },

        // ── Lifecycle ───────────────────────────────────────────────

        onShow() {
            this._loadStyles();
        },

        async init() {
            // Add one default text line
            this._lines = [{ text: '', font: '', position: 'center' }];

            await this._loadStyles();
            this._renderLines();
            this._loadRecentImages();
            this._loadFonts();
            this._loadLlmInfo();

            // Event listeners
            document.getElementById('ts-model-settings-btn')?.addEventListener('click', () => window.ModelSettings?.open('type-studio'));
            document.getElementById('ts-mode-on-image')?.addEventListener('click', () => this._setMode('on-image'));
            document.getElementById('ts-mode-standalone')?.addEventListener('click', () => this._setMode('standalone'));

            document.getElementById('ts-style')?.addEventListener('change', () => {
                this._loadFonts();
            });

            let imgDebounce;
            const imgInput = document.getElementById('ts-image-id');
            imgInput?.addEventListener('input', () => {
                this._selectedImageId = imgInput.value.trim();
                clearTimeout(imgDebounce);
                imgDebounce = setTimeout(() => this._updateImagePreview(), 300);
            });
            imgInput?.addEventListener('change', () => {
                this._selectedImageId = imgInput.value.trim();
                this._updateImagePreview();
            });

            document.getElementById('ts-recent-images')?.addEventListener('change', (e) => {
                const val = e.target.value;
                if (val) {
                    document.getElementById('ts-image-id').value = val;
                    this._selectedImageId = val;
                    this._updateImagePreview();
                }
            });

            document.getElementById('ts-add-line')?.addEventListener('click', () => this._addLine());
            document.getElementById('ts-btn-suggest')?.addEventListener('click', () => this._handleSuggest());
            document.getElementById('ts-btn-generate')?.addEventListener('click', () => this._handleGenerate());
            document.getElementById('ts-btn-apply-pp')?.addEventListener('click', () => this._handlePostProcess());

            // Click result image → open in AssetViewer with zoom/pan + metadata
            const resultImg = document.getElementById('ts-result-img');
            if (resultImg) {
                resultImg.style.cursor = 'pointer';
                resultImg.addEventListener('click', () => {
                    if (!this._lastResultAssetIds?.length) return;
                    const assetId = this._lastResultAssetIds[this._selectedOptionIndex || 0];
                    if (!assetId) return;
                    const item = {
                        id: assetId,
                        prompt: '',
                        png_url: `/api/gallery/${assetId}/png`,
                    };
                    if (typeof AssetViewer !== 'undefined') AssetViewer.open(item);
                });
            }
        },

        // ── Mode Toggle ─────────────────────────────────────────────

        _setMode(mode) {
            this._mode = mode;
            const onImgBtn = document.getElementById('ts-mode-on-image');
            const standaloneBtn = document.getElementById('ts-mode-standalone');
            const sourceSection = document.getElementById('ts-source-image-section');

            if (mode === 'on-image') {
                onImgBtn?.classList.add('ts-mode-active');
                standaloneBtn?.classList.remove('ts-mode-active');
                sourceSection?.classList.remove('hidden');
            } else {
                standaloneBtn?.classList.add('ts-mode-active');
                onImgBtn?.classList.remove('ts-mode-active');
                sourceSection?.classList.add('hidden');
            }
        },

        // ── Load Styles ─────────────────────────────────────────────

        async _loadLlmInfo() {
            // Show the currently configured LLM models from registry
            try {
                const reg = await API.admin.getModels();
                const infoEl = document.getElementById('ts-llm-info');
                if (infoEl && reg.categories) {
                    const complex = reg.categories.complex_llm;
                    const fast = reg.categories.fast_llm;
                    infoEl.textContent = `Complex: ${complex?.label || complex?.current || '?'} | Fast: ${fast?.label || fast?.current || '?'}`;
                }
            } catch { /* ignore */ }

            // Update info when selection changes
            document.getElementById('ts-llm-complexity')?.addEventListener('change', () => {
                const infoEl = document.getElementById('ts-llm-info');
                const val = document.getElementById('ts-llm-complexity')?.value;
                if (infoEl) infoEl.textContent = val === 'complex' ? t('type_studio.llm_quality_higher') : t('type_studio.llm_quality_faster');
            });
        },

        async _loadStyles() {
            try {
                const data = await API.styles.list();
                this._styles = Array.isArray(data) ? data : [];
            } catch { this._styles = []; }

            const sel = document.getElementById('ts-style');
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
            if (currentValue) sel.value = currentValue;
        },

        // ── Load Fonts ──────────────────────────────────────────────

        async _loadFonts() {
            const styleId = document.getElementById('ts-style')?.value || '';
            const listEl = document.getElementById('ts-font-list');

            try {
                const data = await API.typeStudio.fonts(styleId);
                this._fonts = (data && data.fonts) ? data.fonts : [];
            } catch {
                this._fonts = [];
            }

            // Detect and merge client-side fonts (browser's local fonts)
            try {
                const clientFonts = await _detectClientFonts();
                if (clientFonts.length > 0) {
                    // Add client fonts after server fonts, avoiding duplicates
                    const existing = new Set(this._fonts.map(f => f.display_name.toLowerCase()));
                    const newClientFonts = clientFonts.filter(f => !existing.has(f.display_name.toLowerCase()));
                    this._fonts = [...this._fonts, ...newClientFonts];
                }
            } catch (err) {
                console.warn('Client font detection failed:', err);
            }

            // Load @font-face for custom (non-system) fonts
            _loadCustomFontFaces(this._fonts);

            // Update sidebar font list preview
            if (listEl) {
                const styleFonts = this._fonts.filter(f => f.source === 'style');
                const otherCount = this._fonts.length - styleFonts.length;
                if (this._fonts.length === 0) {
                    listEl.innerHTML = `<p class="text-brand-text-muted/60">${t('type_studio.fonts_empty')}</p>`;
                } else {
                    let html = '';
                    if (styleFonts.length > 0) {
                        html += `<p class="text-brand-accent text-[10px] font-bold uppercase mb-1">${t('type_studio.style_fonts_count', { count: styleFonts.length })}</p>`;
                        html += styleFonts.map(f =>
                            `<div class="py-0.5" style="font-family: '${_font_css_family(f)}'">${this._escapeHtml(f.display_name || f.name)}</div>`
                        ).join('');
                    }
                    html += `<p class="text-brand-text-muted/50 text-[10px] mt-1">${otherCount} ${t('type_studio.more_fonts_suffix')}</p>`;
                    listEl.innerHTML = html;
                }
            }

            // Re-render lines to update font pickers
            this._renderLines();
        },

        // ── Load Recent Images ──────────────────────────────────────

        async _loadRecentImages() {
            const sel = document.getElementById('ts-recent-images');
            if (!sel) return;

            try {
                const data = await API.gallery.list({ limit: 20 });
                const items = Array.isArray(data) ? data : (data.items || []);
                this._recentImages = items;

                sel.innerHTML = `<option value="">${t('type_studio.browse_recent')}</option>` +
                    items.map(item => {
                        const label = item.png_filename || item.id;
                        return `<option value="${this._escapeHtml(item.id)}">${this._escapeHtml(label)}</option>`;
                    }).join('');
            } catch {
                // Leave the dropdown as-is
            }
        },

        _updateImagePreview() {
            const id = this._selectedImageId;
            const previewDiv = document.getElementById('ts-image-preview');
            const previewImg = document.getElementById('ts-image-preview-img');
            if (!previewDiv || !previewImg) return;

            if (id) {
                previewImg.src = API.gallery.pngUrl(id);
                previewImg.onerror = () => {
                    previewDiv.classList.add('hidden');
                };
                previewDiv.classList.remove('hidden');
            } else {
                previewDiv.classList.add('hidden');
            }
        },

        // ── Text Lines ──────────────────────────────────────────────

        _addLine() {
            this._lines.push({ text: '', font: '', position: 'below-previous' });
            this._renderLines();
        },

        _removeLine(index) {
            if (this._lines.length <= 1) {
                window.showToast?.(t('type_studio.line_min_required'), 'warning');
                return;
            }
            this._lines.splice(index, 1);
            this._renderLines();
        },

        _syncLinesFromDOM() {
            const container = document.getElementById('ts-lines-container');
            if (!container) return;

            container.querySelectorAll('.ts-line-row').forEach((row, i) => {
                if (this._lines[i]) {
                    this._lines[i].text = row.querySelector('.ts-line-text')?.value || '';
                    this._lines[i].font = row.querySelector('.ts-font-value')?.value || '';
                    this._lines[i].position = row.querySelector('.ts-position-select')?.value || 'center';
                }
            });
        },

        _renderLines() {
            const container = document.getElementById('ts-lines-container');
            if (!container) return;

            // Save current values before re-rendering
            this._syncLinesFromDOM();

            const positionOptions = POSITIONS.map(p =>
                `<option value="${p.value}">${p.label}</option>`
            ).join('');

            // Group fonts by source for the picker
            const styleFonts = this._fonts.filter(f => f.source === 'style');
            const globalFonts = this._fonts.filter(f => f.source === 'global');
            const systemFonts = this._fonts.filter(f => f.source === 'system');

            container.innerHTML = this._lines.map((line, i) => `
                <div class="ts-line-row p-3 bg-brand-bg rounded-lg border border-brand-border space-y-2" data-line-index="${i}">
                    <div class="flex items-center gap-2">
                        <span class="text-[10px] font-bold text-brand-text-muted/50 w-5 text-center">${i + 1}</span>
                        <input type="text" class="ts-line-text input flex-1" placeholder="${t('type_studio.text_placeholder')}"
                            value="${this._escapeAttr(line.text)}" />
                        <button class="ts-voice-btn p-1.5 rounded-lg text-brand-text-muted hover:text-brand-accent hover:bg-brand-accent/10 transition-colors"
                            data-line-index="${i}" title="${t('type_studio.voice_input')}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                            </svg>
                        </button>
                        <button class="ts-remove-line p-1.5 rounded-lg text-brand-text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
                            data-line-index="${i}" title="${t('type_studio.remove_line')}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex gap-2 pl-7">
                        <div class="ts-font-picker relative flex-[3]" data-line-index="${i}">
                            <button type="button" class="ts-font-btn input text-sm w-full text-left flex items-center justify-between">
                                <span class="ts-font-label truncate">${this._escapeHtml(line.font ? _font_display_name(line.font) : t('type_studio.default_font'))}</span>
                                <svg class="w-3 h-3 flex-shrink-0 text-brand-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                                </svg>
                            </button>
                            <input type="hidden" class="ts-font-value" value="${this._escapeAttr(line.font || '')}" />
                            <div class="ts-font-dropdown hidden absolute z-50 left-0 right-0 top-full mt-1 bg-brand-surface border border-brand-border rounded-lg shadow-xl max-h-96 overflow-y-auto">
                                <div class="p-2">
                                    <input type="text" class="ts-font-search input text-xs w-full" placeholder="${t('type_studio.search_fonts')}" />
                                </div>
                                <div class="ts-font-options">
                                    <div class="ts-font-option px-3 py-2 text-xs cursor-pointer hover:bg-white/5 rounded" data-font="">
                                        <span class="text-brand-text-muted">${t('type_studio.default_font')}</span>
                                    </div>
                                    ${styleFonts.length > 0 ? `
                                        <div class="px-3 py-1.5 text-[9px] uppercase tracking-wider font-bold text-brand-accent border-t border-brand-border mt-1 pt-2">${t('type_studio.style_fonts')}</div>
                                        ${styleFonts.map(f => `
                                            <div class="ts-font-option px-3 py-2.5 cursor-pointer hover:bg-white/5 rounded" data-font="${this._escapeAttr(f.name)}" data-display="${this._escapeAttr(f.display_name)}" data-source="style">
                                                <span style="font-family: '${_font_css_family(f)}'" class="text-lg">${this._escapeHtml(f.display_name)}</span>
                                            </div>
                                        `).join('')}
                                    ` : ''}
                                    ${globalFonts.length > 0 ? `
                                        <div class="px-3 py-1.5 text-[9px] uppercase tracking-wider font-bold text-emerald-400 border-t border-brand-border mt-1 pt-2">${t('type_studio.project_fonts')}</div>
                                        ${globalFonts.map(f => `
                                            <div class="ts-font-option px-3 py-2.5 cursor-pointer hover:bg-white/5 rounded" data-font="${this._escapeAttr(f.name)}" data-display="${this._escapeAttr(f.display_name)}" data-source="global">
                                                <span style="font-family: '${_font_css_family(f)}'" class="text-lg">${this._escapeHtml(f.display_name)}</span>
                                            </div>
                                        `).join('')}
                                    ` : ''}
                                    ${systemFonts.length > 0 ? `
                                        <div class="px-3 py-1.5 text-[9px] uppercase tracking-wider font-bold text-brand-text-muted border-t border-brand-border mt-1 pt-2">${t('type_studio.system_fonts')}</div>
                                        ${systemFonts.map(f => `
                                            <div class="ts-font-option px-3 py-2.5 cursor-pointer hover:bg-white/5 rounded" data-font="${this._escapeAttr(f.name)}" data-display="${this._escapeAttr(f.display_name)}" data-source="system">
                                                <span style="font-family: '${_font_css_family(f)}'" class="text-lg">${this._escapeHtml(f.display_name)}</span>
                                            </div>
                                        `).join('')}
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                        <select class="ts-position-select input text-xs w-36 flex-shrink-0">
                            ${positionOptions}
                        </select>
                    </div>
                </div>
            `).join('');

            // Restore position values
            container.querySelectorAll('.ts-line-row').forEach((row, i) => {
                const line = this._lines[i];
                if (!line) return;
                const posSel = row.querySelector('.ts-position-select');
                if (posSel && line.position) posSel.value = line.position;
            });

            // Attach font picker interactions
            container.querySelectorAll('.ts-font-picker').forEach(picker => {
                const btn = picker.querySelector('.ts-font-btn');
                const dropdown = picker.querySelector('.ts-font-dropdown');
                const search = picker.querySelector('.ts-font-search');
                const hiddenInput = picker.querySelector('.ts-font-value');
                const label = picker.querySelector('.ts-font-label');

                // Toggle dropdown
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    // Close other open pickers
                    document.querySelectorAll('.ts-font-dropdown').forEach(d => {
                        if (d !== dropdown) d.classList.add('hidden');
                    });
                    dropdown.classList.toggle('hidden');
                    if (!dropdown.classList.contains('hidden')) {
                        search.value = '';
                        search.focus();
                        _filterFontOptions(dropdown, '');
                    }
                });

                // Search
                search.addEventListener('input', () => {
                    _filterFontOptions(dropdown, search.value);
                });
                search.addEventListener('click', (e) => e.stopPropagation());

                // Select font
                dropdown.querySelectorAll('.ts-font-option').forEach(opt => {
                    opt.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const fontName = opt.dataset.font || '';
                        const displayName = opt.dataset.display || t('type_studio.default_font');
                        hiddenInput.value = fontName;
                        label.textContent = fontName ? displayName : t('type_studio.default_font');
                        dropdown.classList.add('hidden');
                    });
                });
            });

            // Close all font dropdowns on outside click
            document.addEventListener('click', () => {
                document.querySelectorAll('.ts-font-dropdown').forEach(d => d.classList.add('hidden'));
            });

            // Attach remove listeners
            container.querySelectorAll('.ts-remove-line').forEach(btn => {
                btn.addEventListener('click', () => {
                    this._syncLinesFromDOM();
                    this._removeLine(parseInt(btn.dataset.lineIndex, 10));
                });
            });

            // Attach voice input listeners
            container.querySelectorAll('.ts-voice-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const lineIdx = parseInt(btn.dataset.lineIndex, 10);
                    const textInput = container.querySelector(`.ts-line-row[data-line-index="${lineIdx}"] .ts-line-text`);
                    if (!textInput) return;

                    // Toggle recording
                    if (btn._recording) {
                        btn._recorder?.stop();
                        return;
                    }

                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
                        const recorder = new MediaRecorder(stream, { mimeType });
                        const chunks = [];

                        recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
                        recorder.onstop = async () => {
                            stream.getTracks().forEach(t => t.stop());
                            btn._recording = false;
                            btn.classList.remove('!text-red-400', 'recording-pulse');

                            const blob = new Blob(chunks, { type: mimeType });
                            if (blob.size < 100) return;

                            btn.innerHTML = '<span class="spinner-sm"></span>';
                            try {
                                const result = await API.transcribe(blob);
                                const text = typeof result === 'string' ? result : (result.text || result.transcript || '');
                                if (text && !text.startsWith('[Audio received')) {
                                    const sep = textInput.value && !textInput.value.endsWith(' ') ? ' ' : '';
                                    textInput.value += sep + text;
                                }
                            } catch (err) {
                                console.error('Voice transcription failed:', err);
                            }
                            btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>';
                        };

                        recorder.start();
                        btn._recording = true;
                        btn._recorder = recorder;
                        btn.classList.add('!text-red-400', 'recording-pulse');
                    } catch (err) {
                        window.showToast?.(t('type_studio.mic_denied'), 'warning');
                    }
                });
            });
        },

        // ── Build Payload ───────────────────────────────────────────

        _buildPayload() {
            this._syncLinesFromDOM();

            const lines = this._lines
                .filter(l => l.text.trim())
                .map(l => ({
                    text: l.text.trim(),
                    font: l.font || null,
                    position: l.position || 'center',
                }));

            if (lines.length === 0) {
                window.showToast?.(t('type_studio.text_required'), 'warning');
                return null;
            }

            const numOptions = parseInt(document.getElementById('ts-num-options')?.value, 10) || 3;

            const llmComplexity = document.getElementById('ts-llm-complexity')?.value || 'complex';

            const payload = {
                source_image_id: null,
                style_id: document.getElementById('ts-style')?.value || null,
                lines: lines,
                style_note: document.getElementById('ts-style-note')?.value?.trim() || null,
                num_options: numOptions,
                llm_complexity: llmComplexity,
                remove_background: document.getElementById('ts-remove-bg')?.checked || false,
                generate_svg: document.getElementById('ts-svg')?.checked || false,
                upscale: document.getElementById('ts-upscale')?.checked || false,
            };

            if (this._mode === 'on-image') {
                const imageId = this._selectedImageId || document.getElementById('ts-image-id')?.value?.trim();
                if (!imageId) {
                    window.showToast?.(t('type_studio.source_required'), 'warning');
                    return null;
                }
                payload.source_image_id = imageId;
            }

            return payload;
        },

        // ── Suggest Layout ──────────────────────────────────────────

        async _handleSuggest() {
            if (this._suggesting) return;

            const payload = this._buildPayload();
            if (!payload) return;

            this._suggesting = true;
            const btn = document.getElementById('ts-btn-suggest');
            const origHTML = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-sm"></span> ${t('type_studio.suggesting')}`;

            try {
                const result = await API.typeStudio.suggest(payload);
                this._renderSuggestion(result);
                window.showToast?.(t('type_studio.layout_ready'), 'success');
            } catch (err) {
                console.error('Suggest error:', err);
            } finally {
                this._suggesting = false;
                btn.disabled = false;
                btn.innerHTML = origHTML;
            }
        },

        _renderSuggestion(result) {
            const section = document.getElementById('ts-suggestion-section');
            const content = document.getElementById('ts-suggestion-content');
            if (!section || !content) return;

            section.classList.remove('hidden');

            let html = '';

            // Handle multiple layouts from /suggest endpoint
            const layouts = result.layouts || (result.layout_spec ? [result.layout_spec] : [result]);

            layouts.forEach((layout, li) => {
                const lines = layout.lines || [];
                if (layouts.length > 1) {
                    html += `<div class="font-semibold text-brand-accent text-xs uppercase mt-${li > 0 ? '4' : '0'} mb-1">${t('type_studio.option_label', { number: li + 1 })}</div>`;
                }
                if (lines.length > 0) {
                    html += '<div class="space-y-1">';
                    lines.forEach((line, i) => {
                        const colorSwatch = line.color ? `<span class="inline-block w-3 h-3 rounded-sm align-middle mr-1" style="background:${line.color}"></span>` : '';
                        html += `<div class="p-2 bg-brand-bg rounded-lg border border-brand-border text-xs">
                            <span class="font-semibold text-brand-text">Line ${i + 1}:</span>
                            "${this._escapeHtml(line.text || '')}"
                            ${line.font_size ? `<span class="text-brand-text-muted ml-2">Size: ${line.font_size}</span>` : ''}
                            ${line.color ? `<span class="text-brand-text-muted ml-2">${colorSwatch}${line.color}</span>` : ''}
                            ${line.anchor ? `<span class="text-brand-text-muted ml-2">Anchor: ${line.anchor}</span>` : ''}
                        </div>`;
                    });
                    html += '</div>';
                }
            });

            // Show raw spec in collapsible
            if (result.layout_spec || result.layouts) {
                const raw = result.layouts || result.layout_spec;
                html += `<details class="mt-2">
                    <summary class="text-xs text-brand-text-muted cursor-pointer hover:text-brand-text">${t('type_studio.view_raw')}</summary>
                    <pre class="mt-1 p-2 bg-brand-bg rounded-lg border border-brand-border text-[11px] text-brand-text/70 overflow-x-auto whitespace-pre-wrap">${this._escapeHtml(JSON.stringify(raw, null, 2))}</pre>
                </details>`;
            }

            // Fallback: if nothing was rendered, show the raw JSON
            if (!html) {
                html = `<pre class="p-2 bg-brand-bg rounded-lg border border-brand-border text-[11px] text-brand-text/70 overflow-x-auto whitespace-pre-wrap">${this._escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
            }

            content.innerHTML = html;
        },

        _showSuggestion(layoutSpec) {
            this._renderSuggestion({ layout_spec: layoutSpec, lines: layoutSpec.lines });
        },

        // ── Generate / Preview ──────────────────────────────────────

        async _handleGenerate() {
            if (this._generating) return;

            const payload = this._buildPayload();
            if (!payload) return;

            this._setGenerating(true);

            try {
                const result = await API.typeStudio.preview(payload);
                this._showResult(result);
                window.showToast?.(t('type_studio.generated'), 'success');
            } catch (err) {
                console.error('Generate error:', err);
            } finally {
                this._setGenerating(false);
            }
        },

        _setGenerating(on) {
            this._generating = on;
            const btn = document.getElementById('ts-btn-generate');
            const loadingEl = document.getElementById('ts-loading');
            const placeholder = document.getElementById('ts-placeholder');

            if (on) {
                btn.disabled = true;
                btn.innerHTML = `<span class="spinner-sm"></span> ${t('type_studio.generating')}`;
                loadingEl?.classList.remove('hidden');
                placeholder?.classList.add('hidden');
                document.getElementById('ts-result-img')?.classList.add('hidden');
                document.getElementById('ts-download-bar')?.classList.add('hidden');
            } else {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    ${t('type_studio.generate')}`;
                loadingEl?.classList.add('hidden');
            }
        },

        _lastResultAssetIds: [],

        _showResult(result) {
            const options = result.options || [];

            // Switch to post-processing mode
            const labelEl = document.getElementById('ts-processing-label');
            if (labelEl) labelEl.textContent = t('type_studio.post_processing_label');
            document.getElementById('ts-btn-apply-pp')?.classList.remove('hidden');
            document.getElementById('ts-pp-hint')?.classList.remove('hidden');

            // Track asset IDs for post-processing
            this._lastResultAssetIds = options.map(o => o.id);
            const optionsSection = document.getElementById('ts-options-section');
            const optionsGrid = document.getElementById('ts-options-grid');

            if (options.length > 1 && optionsSection && optionsGrid) {
                // Show options row
                optionsSection.classList.remove('hidden');
                optionsGrid.className = `grid gap-3 grid-cols-${Math.min(options.length, 5)}`;
                optionsGrid.innerHTML = options.map((opt, i) => `
                    <button class="ts-option-card group relative rounded-xl overflow-hidden border-2 transition-all duration-200 cursor-pointer
                        ${i === 0 ? 'border-brand-accent ring-2 ring-brand-accent/40' : 'border-brand-border hover:border-brand-accent/50'}"
                        data-option-index="${i}">
                        <div class="aspect-square bg-brand-bg">
                            <img src="${opt.png_url}" alt="${t('type_studio.option_label', { number: i + 1 })}" class="w-full h-full object-cover" loading="lazy" />
                        </div>
                        <div class="absolute top-1.5 left-1.5 bg-black/70 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                            ${t('type_studio.option_label', { number: i + 1 })}
                        </div>
                    </button>
                `).join('');

                optionsGrid.querySelectorAll('.ts-option-card').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const idx = parseInt(btn.dataset.optionIndex, 10);
                        // Update highlight
                        optionsGrid.querySelectorAll('.ts-option-card').forEach((b, j) => {
                            if (j === idx) {
                                b.classList.remove('border-brand-border');
                                b.classList.add('border-brand-accent', 'ring-2', 'ring-brand-accent/40');
                            } else {
                                b.classList.remove('border-brand-accent', 'ring-2', 'ring-brand-accent/40');
                                b.classList.add('border-brand-border');
                            }
                        });
                        this._selectedOptionIndex = idx;
                        this._selectOption(options[idx]);
                    });
                });

                // Show first option in preview
                this._selectOption(options[0]);
            } else if (options.length === 1) {
                optionsSection?.classList.add('hidden');
                this._selectOption(options[0]);
            } else {
                // Fallback for old single-result format
                optionsSection?.classList.add('hidden');
                this._selectOption(result);
            }
        },

        _selectOption(opt) {
            const img = document.getElementById('ts-result-img');
            const placeholder = document.getElementById('ts-placeholder');
            const downloadBar = document.getElementById('ts-download-bar');

            const pngUrl = opt.png_url || (opt.id ? API.gallery.pngUrl(opt.id) : null);

            if (img && pngUrl) {
                img.src = pngUrl;
                img.classList.remove('hidden');
            }
            placeholder?.classList.add('hidden');

            if (downloadBar && pngUrl) {
                downloadBar.classList.remove('hidden');
                const info = document.getElementById('ts-result-info');
                if (info) {
                    info.textContent = opt.png_filename || opt.id || 'type-studio-output.png';
                }
                const dlPng = document.getElementById('ts-dl-png');
                if (dlPng) {
                    dlPng.href = pngUrl;
                    dlPng.setAttribute('download', opt.png_filename || 'type-studio-output.png');
                }
            }

            if (opt.layout) {
                this._showSuggestion(opt.layout);
            }
        },

        async _handlePostProcess() {
            const ids = this._lastResultAssetIds;
            if (!ids || ids.length === 0) {
                window.showToast?.(t('type_studio.generate_first'), 'warning');
                return;
            }

            const removeBg = document.getElementById('ts-remove-bg')?.checked || false;
            const genSvg = document.getElementById('ts-svg')?.checked || false;
            const upscale = document.getElementById('ts-upscale')?.checked || false;

            if (!removeBg && !genSvg && !upscale) {
                window.showToast?.(t('type_studio.enable_pp_option'), 'warning');
                return;
            }

            const btn = document.getElementById('ts-btn-apply-pp');
            const origHTML = btn.innerHTML;
            btn.innerHTML = `<span class="spinner-sm"></span> ${t('type_studio.pp_processing')}`;
            btn.disabled = true;

            try {
                const result = await API.postProcess({
                    asset_ids: ids,
                    remove_background: removeBg,
                    generate_svg: genSvg,
                    upscale: upscale,
                });
                const count = (result.processed || []).length;
                window.showToast?.(t('type_studio.pp_applied'), 'success');

                // Refresh preview
                const img = document.getElementById('ts-result-img');
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

        // ── Helpers ─────────────────────────────────────────────────

        _escapeHtml(str) {
            const d = document.createElement('div');
            d.textContent = str;
            return d.innerHTML;
        },

        _escapeAttr(str) {
            return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        },

        /** Called from AssetViewer to pre-select a source image */
        loadSourceImage(assetId, styleId) {
            this._setMode('on-image');
            this._selectedImageId = assetId;
            const input = document.getElementById('ts-image-id');
            if (input) input.value = assetId;
            this._updateImagePreview();

            if (styleId) {
                const styleSel = document.getElementById('ts-style');
                if (styleSel) {
                    styleSel.value = styleId;
                    this._loadFonts();
                }
            }
        },

        /** Called from AssetViewer to reload a previous Type Studio asset for editing */
        loadFromMeta(meta) {
            // Set mode based on whether there's a source image
            if (meta.source_image_id) {
                this._setMode('on-image');
                this._selectedImageId = meta.source_image_id;
                const input = document.getElementById('ts-image-id');
                if (input) input.value = meta.source_image_id;
                this._updateImagePreview();
            } else {
                this._setMode('standalone');
            }

            // Set style
            if (meta.style_id) {
                const styleSel = document.getElementById('ts-style');
                if (styleSel) styleSel.value = meta.style_id;
                this._loadFonts();
            }

            // Set style note
            const noteEl = document.getElementById('ts-style-note');
            if (noteEl) noteEl.value = meta.style_note || '';

            // Restore text lines
            if (meta.lines && meta.lines.length > 0) {
                this._lines = meta.lines.map(l => ({
                    text: l.text || '',
                    font: l.font || '',
                    position: l.position || 'center',
                }));
                this._renderLines();
            }

            // Show the previous layout suggestion if available
            if (meta.layout_spec) {
                this._showSuggestion(meta.layout_spec);
            }

            window.showToast?.(t('type_studio.asset_loaded'), 'success');
        },
    };
})();
