/**
 * ArtSmoker — AssetViewer Component
 *
 * Modal overlay showing full-size image, complete metadata,
 * and a "Reload in 2D Image Studio" button.
 *
 * Usage:
 *   AssetViewer.open(galleryItem)   // opens modal, fetches full metadata
 *   AssetViewer.close()
 */
(function () {
    'use strict';

    // Fallback labels for older assets without model_label in metadata.
    // New assets store model_label directly — this map is only for backward compatibility.
    const MODEL_LABELS = {
        nova_canvas: 'Amazon Nova Canvas',
        titan_image: 'Amazon Titan Image v2',
        sd35_large: 'Stable Diffusion 3.5 Large',
        stable_image_ultra: 'Stable Image Ultra',
    };

    const TYPE_LABELS = {
        game_asset: 'Game Asset',
        marketing_banner: 'Marketing Banner',
        icon: 'Icon',
        character: 'Character',
        environment: 'Environment',
        type_studio: 'Type Studio',
        type_studio_composite: 'Type Studio',
    };

    const AssetViewer = {
        _overlay: null,
        _item: null,
        _meta: null,

        async open(item) {
            this._item = item;
            this._meta = null;
            this._renderModal(item);
            this._attachEvents();
            document.body.style.overflow = 'hidden';

            // Fetch full metadata from the API
            try {
                const meta = await API.gallery.get(item.id);
                this._meta = meta;
                this._updateMetadata(meta);
            } catch (err) {
                console.error('Failed to fetch metadata:', err);
            }
        },

        close() {
            if (this._overlay) {
                this._overlay.remove();
                this._overlay = null;
            }
            this._meta = null;
            document.body.style.overflow = '';
        },

        _renderModal(item) {
            if (this._overlay) this._overlay.remove();

            const pngUrl = item.png_url || API.gallery.pngUrl(item.id);
            const svgUrl = item.svg_url || API.gallery.svgUrl(item.id);

            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            overlay.innerHTML = `
                <div class="modal-content bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                        <h2 class="text-lg font-semibold truncate flex-1">${this._esc(item.png_filename || 'Generated Asset')}</h2>
                        <div class="flex items-center gap-2 ml-4">
                            <button class="btn-reload btn btn-sm bg-indigo-600 hover:bg-indigo-500 text-white" title="Reload this batch in 2D Image Studio">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                </svg>
                                2D Studio
                            </button>
                            <button class="btn-add-text btn btn-sm bg-emerald-600 hover:bg-emerald-500 text-white" title="Add text to this image in Type Studio">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
                                </svg>
                                Add Text
                            </button>
                            <button class="btn-reload-type hidden btn btn-sm bg-purple-600 hover:bg-purple-500 text-white" title="Reload in Type Studio with original settings">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
                                </svg>
                                Edit in Type Studio
                            </button>
                            <button class="btn-close p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors" title="Close">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Tabs -->
                    <div class="tab-bar px-6 pt-3">
                        <button class="tab active" data-tab="png">PNG</button>
                        <button class="tab" data-tab="edit">Edit</button>
                        <button class="tab" data-tab="svg">SVG</button>
                        <button class="tab" data-tab="meta">Metadata</button>
                    </div>

                    <!-- Tab Content -->
                    <div class="flex-1 overflow-auto p-6">
                        <!-- PNG tab with zoom/pan -->
                        <div class="tab-panel" data-panel="png">
                            <div class="relative">
                                <div id="av-zoom-container" class="preview-checkerboard rounded-lg overflow-hidden min-h-[300px] max-h-[70vh] cursor-grab active:cursor-grabbing" style="position:relative;">
                                    <img id="av-zoom-img" src="${pngUrl}" alt="Generated PNG" class="rounded shadow-lg" loading="lazy"
                                         style="transform-origin: 0 0; transition: transform 0.1s ease-out; max-width: none;" />
                                </div>
                                <div class="flex items-center gap-2 mt-2 justify-center">
                                    <button id="av-zoom-out" class="btn btn-sm btn-secondary px-2 py-1" title="Zoom out">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"/></svg>
                                    </button>
                                    <span id="av-zoom-level" class="text-xs text-brand-text-muted font-mono w-12 text-center">100%</span>
                                    <button id="av-zoom-in" class="btn btn-sm btn-secondary px-2 py-1" title="Zoom in">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"/></svg>
                                    </button>
                                    <button id="av-zoom-fit" class="btn btn-sm btn-secondary px-2 py-1 text-xs" title="Fit to view">Fit</button>
                                    <button id="av-zoom-actual" class="btn btn-sm btn-secondary px-2 py-1 text-xs" title="Actual size (100%)">1:1</button>
                                </div>
                            </div>
                        </div>

                        <!-- Edit tab (Inpaint / Outpaint / Erase) -->
                        <div class="tab-panel hidden" data-panel="edit">
                            <div class="space-y-3">
                                <!-- Edit mode selector -->
                                <div class="flex gap-2">
                                    <button class="av-edit-mode btn btn-sm btn-secondary active" data-mode="inpaint">Inpaint</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="erase">Erase</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="outpaint">Outpaint</button>
                                </div>

                                <!-- Inpaint/Erase: Canvas + Mask -->
                                <div id="av-mask-section">
                                    <div class="flex items-center gap-3 mb-2">
                                        <label class="text-xs text-brand-text-muted">Brush:</label>
                                        <input id="av-brush-size" type="range" min="5" max="80" value="20" class="w-24" />
                                        <span id="av-brush-size-label" class="text-xs text-brand-text-muted font-mono w-8">20px</span>
                                        <button id="av-mask-clear" class="btn btn-sm btn-secondary text-xs">Clear mask</button>
                                    </div>
                                    <p class="text-[10px] text-brand-text-dim mb-1">Paint white over the area you want to edit. The rest of the image will be preserved.</p>
                                    <div class="relative rounded-lg overflow-hidden border border-brand-border" style="display: inline-block;">
                                        <canvas id="av-mask-canvas" class="cursor-crosshair" style="max-width: 100%; max-height: 50vh;"></canvas>
                                    </div>
                                </div>

                                <!-- Outpaint: Direction controls -->
                                <div id="av-outpaint-section" class="hidden">
                                    <p class="text-[10px] text-brand-text-dim mb-2">Extend the image in any direction (pixels to add):</p>
                                    <div class="grid grid-cols-4 gap-2 max-w-xs">
                                        <div><label class="text-[10px] text-brand-text-muted">Left</label><input id="av-out-left" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">Right</label><input id="av-out-right" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">Up</label><input id="av-out-up" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">Down</label><input id="av-out-down" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                    </div>
                                </div>

                                <!-- Prompt + Model + Generate -->
                                <div>
                                    <label class="text-xs text-brand-text-muted mb-1 block">Prompt (describe what to generate in the edited area)</label>
                                    <textarea id="av-edit-prompt" class="input text-sm w-full h-16" placeholder="e.g. a treasure chest, a wooden door, blue sky..."></textarea>
                                </div>
                                <div class="flex items-end gap-2">
                                    <div class="flex-1">
                                        <label class="text-[10px] text-brand-text-muted mb-0.5 block">Model</label>
                                        <select id="av-edit-model" class="input text-xs"></select>
                                    </div>
                                    <button id="av-edit-generate" class="btn btn-primary btn-sm">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                                        Apply Edit
                                    </button>
                                </div>
                                <div id="av-edit-status" class="text-xs text-brand-text-muted hidden"></div>
                            </div>
                        </div>

                        <!-- SVG tab -->
                        <div class="tab-panel hidden" data-panel="svg">
                            <div class="preview-checkerboard rounded-lg flex items-center justify-center p-4 min-h-[300px]">
                                <img src="${svgUrl}" alt="Generated SVG" class="max-w-full max-h-[60vh] rounded shadow-lg" loading="lazy"
                                     onerror="this.parentElement.innerHTML='<p class=\\'text-brand-text-muted text-sm\\'>SVG not available for this asset.</p>'" />
                            </div>
                        </div>

                        <!-- Metadata tab (initially shows loading, updated when API responds) -->
                        <div class="tab-panel hidden" data-panel="meta">
                            <div id="asset-meta-content" class="space-y-4 text-sm">
                                <div class="flex items-center gap-2 text-brand-text-muted py-8 justify-center">
                                    <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                    Loading metadata...
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-brand-border">
                        <a href="${pngUrl}" download="${this._esc(item.png_filename || 'asset.png')}" class="btn btn-secondary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            Download PNG
                        </a>
                        <a href="${svgUrl}" download="${this._esc(item.svg_filename || 'asset.svg')}" class="btn btn-secondary btn-sm btn-dl-svg">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            Download SVG
                        </a>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);
            this._overlay = overlay;
        },

        _updateMetadata(meta) {
            const container = this._overlay?.querySelector('#asset-meta-content');
            if (!container) return;

            const createdAt = meta.created_at ? new Date(meta.created_at).toLocaleString() : 'N/A';
            const isTypeStudio = meta.type === 'type-studio';
            const modelLabel = meta.model_label || MODEL_LABELS[meta.image_model] || meta.image_model || '';
            const typeLabel = TYPE_LABELS[meta.asset_type] || meta.asset_type || 'N/A';

            container.innerHTML = `
                ${meta.original_prompt ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Original Prompt</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.original_prompt)}</p>
                </div>` : ''}
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${isTypeStudio ? 'Text Content' : (meta.original_prompt ? 'AI-Improved Prompt' : 'Prompt')}</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.prompt || 'N/A')}</p>
                </div>
                ${!isTypeStudio && meta.refined_prompt ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Generation Prompt (sent to image model)</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._esc(meta.refined_prompt)}</p>
                </div>` : ''}
                ${meta.negative_prompt ? `
                <div>
                    <label class="block text-xs text-amber-400/80 uppercase tracking-wider mb-1">Negative Prompt (exclusions sent to model)</label>
                    <p class="p-3 rounded-lg bg-amber-950/20 border border-amber-900/20 whitespace-pre-wrap text-amber-300/70 italic text-sm">${this._esc(meta.negative_prompt)}</p>
                </div>` : ''}
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Style</label>
                        <p class="font-medium">${this._esc(meta.style_snapshot?.name || meta.style_id || 'None')}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Asset Type</label>
                        <p class="font-medium">${typeLabel}</p>
                    </div>
                    ${modelLabel ? `<div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Image Model</label>
                        <p class="font-medium">${modelLabel}</p>
                    </div>` : ''}
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Dimensions</label>
                        <p class="font-medium">${meta.width || '?'} x ${meta.height || '?'}</p>
                    </div>
                    ${meta.seed != null ? `<div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Seed</label>
                        <p class="font-medium font-mono text-xs">${meta.seed}</p>
                    </div>` : ''}
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Created</label>
                        <p class="font-medium">${createdAt}</p>
                    </div>
                </div>
                ${(meta.ip_owned || meta.ip_licensed) ? `
                <div class="p-2 rounded-lg bg-brand-accent/10 border border-brand-accent/20 text-xs">
                    <span class="font-medium">IP Declaration:</span>
                    ${meta.ip_owned ? ' Owner' : ''}${meta.ip_licensed ? ' Licensed' : ''}
                </div>` : ''}
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Batch ID</label>
                        <p class="font-mono text-xs text-brand-text-muted">${this._esc(meta.batch_id || meta.id)}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Option / Variation</label>
                        <p class="font-medium">${(meta.option_index ?? 0) + 1} / ${(meta.variant_index ?? 0) + 1}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Filename</label>
                        <p class="font-mono text-xs">${this._esc(meta.png_filename || 'N/A')}</p>
                    </div>
                </div>
                ${meta.style_snapshot?.generation_hints ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Style Hints (at generation time)</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-xs text-brand-text-muted">${this._esc(meta.style_snapshot.generation_hints)}</p>
                </div>` : ''}
                ${meta.type === 'type-studio' ? `
                <div class="border-t border-brand-border pt-4 mt-2">
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-2">Type Studio Details</label>
                    ${meta.source_image_id ? `<p class="text-sm mb-1"><span class="text-brand-text-muted">Source image:</span> ${this._esc(meta.source_image_id)}</p>` : '<p class="text-sm mb-1 text-brand-text-muted">Standalone text (no source image)</p>'}
                    ${meta.style_note ? `<p class="text-sm mb-1"><span class="text-brand-text-muted">Style note:</span> ${this._esc(meta.style_note)}</p>` : ''}
                    ${meta.lines ? `
                    <div class="mt-2 space-y-1">
                        ${meta.lines.map((l, i) => `
                            <div class="text-sm p-2 rounded bg-brand-bg/40">
                                <span class="text-brand-text-muted">Line ${i+1}:</span> "${this._esc(l.text)}"
                                <span class="text-brand-text-muted/60 text-xs ml-2">${l.font || 'default'} / ${l.position || 'center'}</span>
                            </div>
                        `).join('')}
                    </div>` : ''}
                </div>` : ''}
            `;

            // Show/hide contextual buttons based on asset type
            const isTS = meta.type === 'type-studio';
            const reloadBtn = this._overlay?.querySelector('.btn-reload');
            const addTextBtn = this._overlay?.querySelector('.btn-add-text');
            const reloadTypeBtn = this._overlay?.querySelector('.btn-reload-type');

            // 2D Studio: show for image assets, hide for Type Studio assets
            if (reloadBtn) reloadBtn.classList.toggle('hidden', isTS);
            // Add Text: show for image assets, hide for Type Studio assets (use Edit instead)
            if (addTextBtn) addTextBtn.classList.toggle('hidden', isTS);
            // Edit in Type Studio: show for Type Studio assets only
            if (reloadTypeBtn) reloadTypeBtn.classList.toggle('hidden', !isTS);

            // Show/hide SVG download button and tab based on whether SVG exists
            const hasSvg = !!(meta.svg_path);
            const svgDlBtn = this._overlay?.querySelector('.btn-dl-svg');
            if (svgDlBtn) svgDlBtn.classList.toggle('hidden', !hasSvg);
            const svgTab = this._overlay?.querySelector('[data-tab="svg"]');
            if (svgTab) svgTab.classList.toggle('hidden', !hasSvg);
        },

        _attachEvents() {
            if (!this._overlay) return;

            this._overlay.querySelector('.btn-close').addEventListener('click', () => this.close());

            this._overlay.addEventListener('click', (e) => {
                if (e.target === this._overlay) this.close();
            });

            this._escHandler = (e) => {
                if (e.key === 'Escape') {
                    this.close();
                    document.removeEventListener('keydown', this._escHandler);
                }
            };
            document.addEventListener('keydown', this._escHandler);

            // Tab switching
            this._overlay.querySelectorAll('.tab').forEach((tab) => {
                tab.addEventListener('click', () => {
                    this._overlay.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
                    tab.classList.add('active');
                    this._overlay.querySelectorAll('.tab-panel').forEach((p) => {
                        p.classList.toggle('hidden', p.dataset.panel !== tab.dataset.tab);
                    });
                });
            });

            // ── Zoom/Pan for PNG viewer ─────────────────────────────────
            this._initZoomPan();

            // ── Edit tab (Inpaint/Outpaint/Erase) ──────────────────────
            this._initEditTab();

            // Reload in 2D Image Studio
            this._overlay.querySelector('.btn-reload')?.addEventListener('click', async () => {
                const meta = this._meta;
                if (!meta) {
                    window.showToast?.('Metadata not loaded yet', 'warning');
                    return;
                }
                const batchId = meta.batch_id || meta.id;
                this.close();
                await ImageStudio.loadBatch(batchId);
            });

            // Add Text in Type Studio
            this._overlay.querySelector('.btn-add-text')?.addEventListener('click', async () => {
                const item = this._item;
                if (!item) return;
                this.close();
                window.location.hash = '#type-studio';
                await new Promise(r => setTimeout(r, 0)); // yield for hashchange
                const start = Date.now();
                while (!document.getElementById('ts-style') && (Date.now() - start) < 10000) {
                    await new Promise(r => setTimeout(r, 100));
                }
                await new Promise(r => setTimeout(r, 200)); // let init/onShow finish
                if (window.TypeStudio?.loadSourceImage) {
                    window.TypeStudio.loadSourceImage(item.id, item.style_id);
                }
            });

            // Edit in Type Studio (reload previous Type Studio work)
            this._overlay.querySelector('.btn-reload-type')?.addEventListener('click', async () => {
                const meta = this._meta;
                if (!meta) {
                    window.showToast?.('Metadata not loaded yet', 'warning');
                    return;
                }
                this.close();
                window.location.hash = '#type-studio';
                await new Promise(r => setTimeout(r, 0)); // yield for hashchange
                const start = Date.now();
                while (!document.getElementById('ts-style') && (Date.now() - start) < 10000) {
                    await new Promise(r => setTimeout(r, 100));
                }
                await new Promise(r => setTimeout(r, 200)); // let init/onShow finish
                if (window.TypeStudio?.loadFromMeta) {
                    window.TypeStudio.loadFromMeta(meta);
                }
            });
        },

        _initEditTab() {
            if (!this._overlay) return;
            const canvas = this._overlay.querySelector('#av-mask-canvas');
            const brushSlider = this._overlay.querySelector('#av-brush-size');
            const brushLabel = this._overlay.querySelector('#av-brush-size-label');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            let painting = false;
            let brushSize = 20;
            let editMode = 'inpaint';

            // Load source image onto canvas
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                // Scale canvas to fit while maintaining aspect ratio
                const maxW = 600, maxH = 400;
                const scale = Math.min(maxW / img.width, maxH / img.height, 1);
                canvas.width = img.width * scale;
                canvas.height = img.height * scale;
                canvas._imgScale = scale;
                canvas._imgW = img.width;
                canvas._imgH = img.height;
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                canvas._baseImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            };
            img.src = this._item?.png_url || '';

            // Brush size
            brushSlider?.addEventListener('input', () => {
                brushSize = parseInt(brushSlider.value, 10);
                if (brushLabel) brushLabel.textContent = `${brushSize}px`;
            });

            // Paint mask (white semi-transparent overlay)
            const paintAt = (x, y) => {
                ctx.globalCompositeOperation = 'source-over';
                ctx.fillStyle = 'rgba(255, 100, 100, 0.5)';
                ctx.beginPath();
                ctx.arc(x, y, brushSize / 2, 0, Math.PI * 2);
                ctx.fill();
            };

            canvas.addEventListener('mousedown', (e) => {
                painting = true;
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                paintAt((e.clientX - rect.left) * scaleX, (e.clientY - rect.top) * scaleY);
            });
            canvas.addEventListener('mousemove', (e) => {
                if (!painting) return;
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                paintAt((e.clientX - rect.left) * scaleX, (e.clientY - rect.top) * scaleY);
            });
            window.addEventListener('mouseup', () => { painting = false; });

            // Clear mask
            this._overlay.querySelector('#av-mask-clear')?.addEventListener('click', () => {
                if (canvas._baseImageData) {
                    ctx.putImageData(canvas._baseImageData, 0, 0);
                }
            });

            // Edit mode switching
            this._overlay.querySelectorAll('.av-edit-mode').forEach(btn => {
                btn.addEventListener('click', () => {
                    editMode = btn.dataset.mode;
                    this._overlay.querySelectorAll('.av-edit-mode').forEach(b => b.classList.remove('active', 'bg-brand-accent', 'text-white'));
                    btn.classList.add('active', 'bg-brand-accent', 'text-white');
                    // Show/hide sections
                    const maskSection = this._overlay.querySelector('#av-mask-section');
                    const outSection = this._overlay.querySelector('#av-outpaint-section');
                    if (maskSection) maskSection.classList.toggle('hidden', editMode === 'outpaint');
                    if (outSection) outSection.classList.toggle('hidden', editMode !== 'outpaint');
                });
            });

            // Populate edit model dropdown from registry
            this._loadEditModels(editMode);
            this._overlay.querySelectorAll('.av-edit-mode').forEach(btn => {
                btn.addEventListener('click', () => this._loadEditModels(btn.dataset.mode));
            });

            // Generate / Apply Edit
            this._overlay.querySelector('#av-edit-generate')?.addEventListener('click', async () => {
                const statusEl = this._overlay.querySelector('#av-edit-status');
                const btn = this._overlay.querySelector('#av-edit-generate');
                const model = this._overlay.querySelector('#av-edit-model')?.value;
                const prompt = this._overlay.querySelector('#av-edit-prompt')?.value || '';

                if (!model) {
                    window.showToast?.('Select an editing model', 'warning');
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> Applying...';
                if (statusEl) { statusEl.textContent = 'Processing...'; statusEl.classList.remove('hidden'); }

                try {
                    // Extract mask from canvas (convert painted areas to white mask)
                    let maskB64 = null;
                    if (editMode !== 'outpaint') {
                        maskB64 = this._extractMask(canvas);
                    }

                    const payload = {
                        source_image_id: this._item?.id,
                        model: model,
                        prompt: prompt,
                        mask: maskB64,
                        outpaint_left: parseInt(this._overlay.querySelector('#av-out-left')?.value || '0', 10),
                        outpaint_right: parseInt(this._overlay.querySelector('#av-out-right')?.value || '0', 10),
                        outpaint_up: parseInt(this._overlay.querySelector('#av-out-up')?.value || '0', 10),
                        outpaint_down: parseInt(this._overlay.querySelector('#av-out-down')?.value || '0', 10),
                    };

                    const result = await fetch('/api/generate/edit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    }).then(r => {
                        if (!r.ok) throw new Error(`${r.status}: ${r.statusText}`);
                        return r.json();
                    });

                    if (statusEl) { statusEl.textContent = `Done! Saved as ${result.id}`; }
                    window.showToast?.(`Image edited with ${result.model_label}. Saved to Gallery.`, 'success');

                    // Reload the viewer with the new asset
                    const newItem = {
                        id: result.id,
                        prompt: prompt,
                        png_url: result.png_url,
                        png_filename: result.png_filename,
                    };
                    this.close();
                    setTimeout(() => this.open(newItem), 300);
                } catch (err) {
                    if (statusEl) { statusEl.textContent = `Error: ${err.message}`; }
                    window.showToast?.('Edit failed: ' + err.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Apply Edit';
                }
            });
        },

        _loadEditModels(mode) {
            const sel = this._overlay?.querySelector('#av-edit-model');
            if (!sel) return;

            // Map edit mode to model_purpose
            const purposeMap = {
                'inpaint': 'inpainting',
                'erase': 'erase',
                'outpaint': 'outpainting',
            };
            const purpose = purposeMap[mode] || 'inpainting';

            // Fetch models from API filtered by purpose
            fetch(`/api/admin/models`).then(r => r.json()).then(data => {
                sel.innerHTML = '';
                const models = data.image_models || {};
                for (const [key, cfg] of Object.entries(models)) {
                    if (cfg.model_purpose === purpose && cfg.enabled) {
                        const opt = document.createElement('option');
                        opt.value = key;
                        opt.textContent = `${cfg.label} ($${(cfg.base_price_usd || 0).toFixed(2)}/img)`;
                        sel.appendChild(opt);
                    }
                }
                if (sel.options.length === 0) {
                    const opt = document.createElement('option');
                    opt.value = '';
                    opt.textContent = 'No models enabled — use Model Settings to enable';
                    sel.appendChild(opt);
                }
            }).catch(() => {});
        },

        _extractMask(canvas) {
            // Create a mask image: white where user painted (red overlay), black elsewhere
            const w = canvas._imgW || canvas.width;
            const h = canvas._imgH || canvas.height;
            const maskCanvas = document.createElement('canvas');
            maskCanvas.width = w;
            maskCanvas.height = h;
            const mctx = maskCanvas.getContext('2d');

            // Scale from display canvas to original image size
            const scale = canvas._imgScale || 1;

            // Get the painted canvas data
            const srcCtx = canvas.getContext('2d');
            const srcData = srcCtx.getImageData(0, 0, canvas.width, canvas.height);
            const baseData = canvas._baseImageData;

            // Compare: where pixels differ from base = painted (mask = white)
            mctx.fillStyle = 'black';
            mctx.fillRect(0, 0, w, h);
            mctx.fillStyle = 'white';

            for (let y = 0; y < canvas.height; y++) {
                for (let x = 0; x < canvas.width; x++) {
                    const i = (y * canvas.width + x) * 4;
                    // Check if pixel was painted (differs from base)
                    if (baseData && (
                        Math.abs(srcData.data[i] - baseData.data[i]) > 20 ||
                        Math.abs(srcData.data[i + 1] - baseData.data[i + 1]) > 20 ||
                        Math.abs(srcData.data[i + 2] - baseData.data[i + 2]) > 20
                    )) {
                        const ox = Math.round(x / scale);
                        const oy = Math.round(y / scale);
                        mctx.fillRect(ox - 2, oy - 2, 4, 4);
                    }
                }
            }

            // Convert to base64 PNG
            return maskCanvas.toDataURL('image/png').split(',')[1];
        },

        _initZoomPan() {
            const container = this._overlay?.querySelector('#av-zoom-container');
            const img = this._overlay?.querySelector('#av-zoom-img');
            const levelEl = this._overlay?.querySelector('#av-zoom-level');
            if (!container || !img) return;

            let scale = 1;
            let panX = 0, panY = 0;
            let isDragging = false;
            let dragStartX = 0, dragStartY = 0;
            let panStartX = 0, panStartY = 0;

            const btnFit = this._overlay.querySelector('#av-zoom-fit');
            const btnActual = this._overlay.querySelector('#av-zoom-actual');
            const btnIn = this._overlay.querySelector('#av-zoom-in');
            const btnOut = this._overlay.querySelector('#av-zoom-out');
            let _fitScale = 1; // Track what "fit" scale is

            const _activeClass = 'bg-brand-accent text-white';
            const _clearActive = () => {
                [btnFit, btnActual, btnIn, btnOut].forEach(b => {
                    if (b) b.className = b.className.replace(/bg-brand-accent text-white/g, '').trim();
                });
            };

            const updateTransform = () => {
                img.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
                if (levelEl) levelEl.textContent = `${Math.round(scale * 100)}%`;

                // Highlight the active mode button
                _clearActive();
                const pct = Math.round(scale * 100);
                if (Math.abs(scale - _fitScale) < 0.01 && btnFit) {
                    btnFit.classList.add(..._activeClass.split(' '));
                } else if (pct === 100 && btnActual) {
                    btnActual.classList.add(..._activeClass.split(' '));
                }
            };

            const fitToView = () => {
                const cW = container.clientWidth;
                const cH = container.clientHeight || 500;
                const iW = img.naturalWidth || img.width || cW;
                const iH = img.naturalHeight || img.height || cH;
                scale = Math.min(cW / iW, cH / iH, 1);
                _fitScale = scale; // Remember what "fit" means for this image
                panX = (cW - iW * scale) / 2;
                panY = (cH - iH * scale) / 2;
                updateTransform();
            };

            // Fit on load
            if (img.complete) fitToView();
            else img.addEventListener('load', fitToView, { once: true });

            // Mouse wheel zoom (centered on cursor)
            container.addEventListener('wheel', (e) => {
                e.preventDefault();
                const rect = container.getBoundingClientRect();
                const mx = e.clientX - rect.left;
                const my = e.clientY - rect.top;

                const oldScale = scale;
                const delta = e.deltaY > 0 ? 0.9 : 1.1;
                scale = Math.min(Math.max(scale * delta, 0.1), 10);

                // Adjust pan to zoom toward cursor
                panX = mx - (mx - panX) * (scale / oldScale);
                panY = my - (my - panY) * (scale / oldScale);
                updateTransform();
            }, { passive: false });

            // Pan via drag
            container.addEventListener('mousedown', (e) => {
                if (e.button !== 0) return;
                isDragging = true;
                dragStartX = e.clientX;
                dragStartY = e.clientY;
                panStartX = panX;
                panStartY = panY;
                e.preventDefault();
            });
            window.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                panX = panStartX + (e.clientX - dragStartX);
                panY = panStartY + (e.clientY - dragStartY);
                updateTransform();
            });
            window.addEventListener('mouseup', () => { isDragging = false; });

            // Zoom buttons
            this._overlay.querySelector('#av-zoom-in')?.addEventListener('click', () => {
                scale = Math.min(scale * 1.25, 10);
                updateTransform();
            });
            this._overlay.querySelector('#av-zoom-out')?.addEventListener('click', () => {
                scale = Math.max(scale * 0.8, 0.1);
                updateTransform();
            });
            this._overlay.querySelector('#av-zoom-fit')?.addEventListener('click', fitToView);
            this._overlay.querySelector('#av-zoom-actual')?.addEventListener('click', () => {
                const cW = container.clientWidth;
                const cH = container.clientHeight || 500;
                const iW = img.naturalWidth || img.width || cW;
                const iH = img.naturalHeight || img.height || cH;
                scale = 1;
                panX = (cW - iW) / 2;
                panY = Math.max((cH - iH) / 2, 0);
                updateTransform();
            });
        },

        _esc(str) {
            const div = document.createElement('div');
            div.textContent = str || '';
            return div.innerHTML;
        },
    };

    window.AssetViewer = AssetViewer;
})();
