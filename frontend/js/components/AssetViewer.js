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
        photorealistic: 'Photorealistic Image',
        type_studio: 'Type Studio',
        type_studio_composite: 'Type Studio',
    };

    const AssetViewer = {
        _overlay: null,
        _item: null,
        _meta: null,
        _list: null,   // Array of items for prev/next navigation
        _listIndex: -1, // Current index in _list

        async open(item, list, listIndex) {
            this._item = item;
            this._meta = null;
            this._list = list || null;
            this._listIndex = typeof listIndex === 'number' ? listIndex : -1;
            this._renderModal(item);
            this._attachEvents();
            document.body.style.overflow = 'hidden';

            // Fetch full metadata from the API
            try {
                const meta = await API.gallery.get(item.id);
                this._meta = meta;
                // Initialize the selected version to the asset's CURRENT version so
                // every tab (incl. 3D) resolves against what the version bar shows.
                // Without this, _currentVersion stayed null and the 3D tab fell back
                // to v1 — loading v1's GLB even when v2 was the selected version.
                this._currentVersion = meta.current_version || (meta.versions?.length || 1);
                this._updateMetadata(meta);
            } catch (err) {
                console.error('Failed to fetch metadata:', err);
            }
        },

        close() {
            this._stop3DPolling();
            this._stop3DJobsPolling();
            if (this._overlay) {
                this._overlay.remove();
                this._overlay = null;
            }
            this._meta = null;
            if (this._navKeyHandler) {
                document.removeEventListener('keydown', this._navKeyHandler);
                this._navKeyHandler = null;
            }
            document.body.style.overflow = '';
        },

        _navigateTo(item) {
            // Navigate to a different item without closing/reopening the full modal
            const list = this._list;
            const idx = this._listIndex;
            this.close();
            this.open(item, list, idx);
        },

        _renderModal(item) {
            if (this._overlay) this._overlay.remove();

            // Always cache-bust image URLs to show the latest version
            const cacheBust = `${(item.png_url || '').includes('?') ? '&' : '?'}t=${Date.now()}`;
            const pngUrl = (item.png_url || API.gallery.pngUrl(item.id)) + cacheBust;
            const svgUrl = (item.svg_url || API.gallery.svgUrl(item.id)) + cacheBust;

            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            overlay.innerHTML = `
                <div class="modal-content bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                        <h2 class="text-lg font-semibold truncate flex-1">${this._esc(item.png_filename || t('asset_viewer.generated_asset'))}</h2>
                        <div class="flex items-center gap-2 ml-4">
                            <button class="btn-reload btn btn-sm bg-indigo-600 hover:bg-indigo-500 text-white" title="${t('asset_viewer.reload_studio_title')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                </svg>
                                ${t('asset_viewer.to_studio')}
                            </button>
                            <button class="btn-add-text btn btn-sm bg-emerald-600 hover:bg-emerald-500 text-white" title="${t('asset_viewer.add_text_title')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
                                </svg>
                                ${t('asset_viewer.add_text')}
                            </button>
                            <button class="btn-reload-type hidden btn btn-sm bg-purple-600 hover:bg-purple-500 text-white" title="${t('asset_viewer.edit_type_title')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
                                </svg>
                                ${t('asset_viewer.edit_type')}
                            </button>
                            <div class="flex items-center gap-1 ml-2">
                                <button class="btn-prev p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors disabled:opacity-30" title="${t('asset_viewer.previous')}">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                                    </svg>
                                </button>
                                <button class="btn-next p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors disabled:opacity-30" title="${t('asset_viewer.next')}">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                    </svg>
                                </button>
                            </div>
                            <button class="btn-close p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors" title="${t('asset_viewer.close_title')}">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Tabs -->
                    <div class="tab-bar px-6 pt-3">
                        <button class="tab active" data-tab="png">${t('asset_viewer.png_tab')} <span id="av-tab-version-badge" class="text-[9px] opacity-60"></span></button>
                        <button class="tab" data-tab="edit">${t('asset_viewer.edit_tab')}</button>
                        <button class="tab" data-tab="svg">${t('asset_viewer.svg_tab')} <span id="av-tab-svg-version" class="text-[9px] opacity-60"></span></button>
                        <button class="tab" data-tab="meta">${t('asset_viewer.metadata_tab')} <span id="av-tab-meta-version" class="text-[9px] opacity-60"></span></button>
                        <button class="tab" data-tab="3d">${t('asset_viewer.three_d_tab')}</button>
                    </div>

                    <!-- Version bar (shared across all tabs, populated when metadata loads) -->
                    <div id="av-version-bar" class="hidden px-6 py-2 bg-brand-bg/40 border-b border-brand-border">
                        <div class="flex items-center gap-2">
                            <span class="text-[10px] text-brand-text-muted uppercase tracking-wider flex-shrink-0">${t('asset_viewer.version_label')}</span>
                            <div id="av-version-buttons" class="flex gap-1 flex-wrap"></div>
                        </div>
                        <div id="av-version-detail" class="text-[10px] text-brand-text-muted mt-1 hidden"></div>
                    </div>

                    <!-- Tab Content -->
                    <div class="flex-1 overflow-auto p-6">
                        <!-- PNG tab with zoom/pan -->
                        <div class="tab-panel" data-panel="png">
                            <div class="relative">
                                <div id="av-zoom-container" class="preview-checkerboard rounded-lg overflow-hidden" style="position:relative; height: 65vh; min-height: 300px;">
                                    <img id="av-zoom-img" src="${pngUrl}" alt="Generated PNG" loading="lazy"
                                         style="transform-origin: 0 0; transition: transform 0.1s ease-out; max-width: none;" />
                                    <!-- Measurement overlay: tracks the image's zoom/pan/fit transform,
                                         drawing a ruler + subject bounding box + per-edge margins. Hidden
                                         until toggled via the Measure button. pointer-events-none so it
                                         never blocks pan/zoom. -->
                                    <canvas id="av-zoom-measure" class="absolute inset-0 w-full h-full pointer-events-none hidden"></canvas>
                                </div>
                                <!-- Image info bar — model, style, date -->
                                <div id="av-image-info" class="flex items-center gap-3 mt-2 text-[10px] text-brand-text-muted"></div>
                                <!-- Zoom controls — floating overlay at top-right -->
                                <div class="absolute top-2 right-2 flex items-center gap-1 bg-black/60 backdrop-blur-sm rounded-lg px-2 py-1">
                                    <button id="av-zoom-out" class="p-1 rounded hover:bg-white/20 text-white/80 hover:text-white" title="${t('asset_viewer.zoom_out_title')}">
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"/></svg>
                                    </button>
                                    <span id="av-zoom-level" class="text-[10px] text-white/70 font-mono w-10 text-center">100%</span>
                                    <button id="av-zoom-in" class="p-1 rounded hover:bg-white/20 text-white/80 hover:text-white" title="${t('asset_viewer.zoom_in_title')}">
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"/></svg>
                                    </button>
                                    <button id="av-zoom-fit" class="px-1.5 py-0.5 rounded text-[10px] text-white/80 hover:bg-white/20 hover:text-white" title="${t('asset_viewer.zoom_fit_title')}">${t('asset_viewer.zoom_fit')}</button>
                                    <button id="av-zoom-actual" class="px-1.5 py-0.5 rounded text-[10px] text-white/80 hover:bg-white/20 hover:text-white" title="${t('asset_viewer.zoom_actual_title')}">${t('asset_viewer.zoom_1to1')}</button>
                                    <span class="w-px h-4 bg-white/20 mx-0.5"></span>
                                    <button id="av-zoom-measure-btn" class="px-1.5 py-0.5 rounded text-[10px] text-white/80 hover:bg-white/20 hover:text-white flex items-center gap-1" title="${t('asset_viewer.measure_title')}">
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7h16M4 7v10M4 7L2 9m18-2v10m0-10l2 2M7 7v3m5-3v5m5-5v3"/></svg>
                                        ${t('asset_viewer.measure')}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Edit tab (Inpaint / Outpaint / Erase) -->
                        <div class="tab-panel hidden" data-panel="edit">
                            <div class="space-y-3">
                                <!-- Edit mode selector -->
                                <div class="flex gap-2">
                                    <button class="av-edit-mode btn btn-sm btn-secondary active" data-mode="inpaint">${t('asset_viewer.inpaint')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="erase">${t('asset_viewer.erase')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="outpaint">${t('asset_viewer.outpaint')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="search_replace">${t('asset_viewer.replace')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="search_recolor">${t('asset_viewer.recolor')}</button>
                                </div>

                                <!-- Inpaint/Erase: Canvas + Mask -->
                                <div id="av-mask-section">
                                    <div class="flex items-center gap-3 mb-2">
                                        <label class="text-xs text-brand-text-muted">${t('asset_viewer.brush_size')}:</label>
                                        <input id="av-brush-size" type="range" min="5" max="80" value="20" class="w-24" />
                                        <span id="av-brush-size-label" class="text-xs text-brand-text-muted font-mono w-8">20px</span>
                                        <button id="av-mask-clear" class="btn btn-sm btn-secondary text-xs">${t('asset_viewer.clear_mask')}</button>
                                    </div>
                                    <p class="text-[10px] text-brand-text-dim mb-1">${t('asset_viewer.mask_hint_full')}</p>
                                    <div class="relative rounded-lg overflow-hidden border border-brand-border" style="display: inline-block;">
                                        <canvas id="av-mask-canvas" class="cursor-crosshair" style="max-width: 100%; max-height: 50vh;"></canvas>
                                    </div>
                                </div>

                                <!-- Outpaint: Direction controls -->
                                <div id="av-outpaint-section" class="hidden">
                                    <p class="text-[10px] text-brand-text-dim mb-2">${t('asset_viewer.outpaint_hint_full')}</p>
                                    <div class="grid grid-cols-4 gap-2 max-w-xs">
                                        <div><label class="text-[10px] text-brand-text-muted">${t('asset_viewer.outpaint_left')}</label><input id="av-out-left" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">${t('asset_viewer.outpaint_right')}</label><input id="av-out-right" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">${t('asset_viewer.outpaint_up')}</label><input id="av-out-up" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">${t('asset_viewer.outpaint_down')}</label><input id="av-out-down" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                    </div>
                                </div>

                                <!-- Search prompt (Replace/Recolor modes) -->
                                <div id="av-search-section" class="hidden">
                                    <label class="text-xs text-brand-text-muted mb-1 block" id="av-search-label">${t('asset_viewer.find_object')}</label>
                                    <input id="av-search-prompt" type="text" class="input text-sm w-full" placeholder="${t('asset_viewer.find_placeholder')}" />
                                </div>

                                <!-- Prompt + Model + Generate -->
                                <div>
                                    <label class="text-xs text-brand-text-muted mb-1 block" id="av-prompt-label">${t('asset_viewer.edit_prompt')}</label>
                                    <textarea id="av-edit-prompt" class="input text-sm w-full h-16" placeholder="${t('asset_viewer.edit_prompt_placeholder')}"></textarea>
                                </div>
                                <div class="flex items-end gap-2">
                                    <div class="flex-1">
                                        <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('asset_viewer.edit_model')}</label>
                                        <select id="av-edit-model" class="input text-xs"></select>
                                    </div>
                                    <button id="av-edit-generate" class="btn btn-primary btn-sm">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                                        ${t('asset_viewer.apply_edit')}
                                    </button>
                                </div>
                                <p class="text-[10px] text-brand-text-dim mt-1">${t('asset_viewer.edit_hint_full')}</p>
                                <div id="av-edit-status" class="text-xs text-brand-text-muted hidden"></div>
                            </div>
                        </div>

                        <!-- SVG tab -->
                        <div class="tab-panel hidden" data-panel="svg">
                            <div class="preview-checkerboard rounded-lg flex items-center justify-center p-4 min-h-[300px]">
                                <img src="${svgUrl}" alt="Generated SVG" class="max-w-full max-h-[60vh] rounded shadow-lg" loading="lazy"
                                     onerror="this.parentElement.innerHTML='<p class=\\'text-brand-text-muted text-sm\\'>${t('asset_viewer.svg_error_inline')}</p>'" />
                            </div>
                        </div>

                        <!-- Metadata tab (initially shows loading, updated when API responds) -->
                        <div class="tab-panel hidden" data-panel="meta">
                            <div id="asset-meta-content" class="space-y-4 text-sm">
                                <div class="flex items-center gap-2 text-brand-text-muted py-8 justify-center">
                                    <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                    ${t('asset_viewer.loading_metadata')}
                                </div>
                            </div>
                        </div>

                        <!-- 3D Model tab -->
                        <div class="tab-panel hidden" data-panel="3d">
                            <!-- In-progress strip: lists ALL parallel 3D jobs for
                                 this asset+version (independent of the main content
                                 below, so the form/viewer stays usable while jobs run). -->
                            <div id="av-3d-jobs" class="hidden mb-3"></div>
                            <div id="av-3d-content" class="space-y-4 text-sm">
                                <div class="flex items-center gap-2 text-brand-text-muted py-8 justify-center">
                                    <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                    ${t('asset_viewer.loading_metadata')}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Footer: PNG/SVG downloads — only relevant on the image tabs
                         (png/edit/svg). Hidden on the Metadata + 3D tabs, which have
                         their own actions (the 3D tab has its own Download GLB). The
                         tab handler toggles #av-image-downloads visibility. -->
                    <div id="av-image-downloads" class="flex items-center justify-end gap-3 px-6 py-4 border-t border-brand-border">
                        <a href="${pngUrl}" download="${this._esc(item.png_filename || 'asset.png')}" class="btn btn-secondary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            ${t('asset_viewer.download_png')}
                        </a>
                        <a href="${svgUrl}" download="${this._esc(item.svg_filename || 'asset.svg')}" class="btn btn-secondary btn-sm btn-dl-svg">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            ${t('asset_viewer.download_svg')}
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

            const createdAt = meta.created_at ? window.formatTimestamp(meta.created_at) : 'N/A';
            const createdDate = meta.created_at ? window.formatDate(meta.created_at) : '';
            const isTypeStudio = meta.type === 'type-studio';
            const modelLabel = meta.model_label || MODEL_LABELS[meta.image_model] || meta.image_model || '';
            const typeLabel = TYPE_LABELS[meta.asset_type] || meta.asset_type || 'N/A';
            const styleName = meta.style_snapshot?.name || meta.style_id || '';

            // Update the image info bar (below the image, above metadata panel)
            const infoBar = this._overlay?.querySelector('#av-image-info');
            if (infoBar) {
                infoBar.innerHTML = [
                    meta.imported ? `<span class="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('gallery.imported_badge')}</span>` : '',
                    modelLabel ? `<span class="px-1.5 py-0.5 rounded bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${this._esc(modelLabel)}</span>` : '',
                    styleName ? `<span class="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${this._esc(styleName)}</span>` : '',
                    typeLabel !== 'N/A' ? `<span class="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${this._esc(typeLabel)}</span>` : '',
                    meta.width && meta.height ? `<span>${meta.width}×${meta.height}</span>` : '',
                    createdDate ? `<span>${createdDate}</span>` : '',
                ].filter(Boolean).join('');
            }

            this._populateMetadata(container, meta);

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

            // Populate shared version bar if versions exist
            this._updateVersionBar(meta);

            // Populate 3D tab based on asset type
            this._update3DContent();
        },

        /**
         * Resolve the DEFAULT 3D variant entry for a 2D version, tolerating
         * every metadata shape we may encounter:
         *   • nested `three_d.v{N}` = { default_variant, variants:[…] } (current)
         *   • flat  `three_d_versions` list (kept in sync as default-per-version)
         *   • legacy single entries
         * Returns a variant-shaped object ({glb_url, size_bytes, pipeline, …}) or
         * null. One 2D version can carry MANY 3D variants; this returns the one
         * currently marked default (what the gallery/thumbnail serve).
         */
        _default3DVariant(meta, version) {
            if (!meta) return null;
            const bucket = meta.three_d?.[`v${version}`];
            if (bucket && Array.isArray(bucket.variants) && bucket.variants.length) {
                return bucket.variants.find(v => v.variant_id === bucket.default_variant)
                    || bucket.variants[bucket.variants.length - 1];
            }
            // Flat list (default-per-version) — backend keeps this in sync.
            return meta.three_d_versions?.find(v => v.version === version)
                || (version === 1 ? meta.three_d_versions?.[0] : null)
                || null;
        },

        _populateMetadata(container, meta) {
            const createdAt = meta.created_at ? window.formatTimestamp(meta.created_at) : 'N/A';
            const isTypeStudio = meta.type === 'type-studio';
            const modelLabel = meta.model_label || MODEL_LABELS[meta.image_model] || meta.image_model || '';
            const typeLabel = TYPE_LABELS[meta.asset_type] || meta.asset_type || 'N/A';
            const styleName = meta.style_snapshot?.name || meta.style_id || '';

            // Helper: copy button snippet
            const escAttr = (s) => (s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const copyBtn = (text) => `<button class="av-copy-btn ml-2 px-1.5 py-0.5 rounded text-[9px] text-brand-text-muted hover:text-brand-accent hover:bg-brand-accent/10 border border-transparent hover:border-brand-accent/20 transition-colors" data-copy="${escAttr(text)}" title="${t('asset_viewer.meta_copy')}">${t('asset_viewer.meta_copy')}</button>`;

            // Helper: collapsible section
            const section = (id, label, content, defaultOpen = false, extraClass = '') => {
                if (!content) return '';
                return `
                <div class="av-meta-section ${extraClass}">
                    <button class="av-meta-section-header flex items-center justify-between w-full text-left py-2 border-b border-brand-border/50" data-section="${id}">
                        <span class="text-xs font-semibold uppercase tracking-wider text-brand-text-muted">${label}</span>
                        <span class="av-section-arrow text-brand-text-muted text-xs transition-transform ${defaultOpen ? '' : '-rotate-90'}">▼</span>
                    </button>
                    <div class="av-meta-section-body py-3 space-y-3 ${defaultOpen ? '' : 'hidden'}" data-body="${id}">
                        ${content}
                    </div>
                </div>`;
            };

            // ── Section 1: Prompt Lineage ──────────────────────────────────
            let promptLineage = '';

            // User's Prompt (with language badge if translated)
            if (meta.original_language_prompt) {
                promptLineage += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-brand-text-muted font-medium">${t('asset_viewer.meta_user_prompt')}</label>
                            <span class="px-1.5 py-0.5 rounded text-[9px] bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${this._esc(meta.original_language || '?')}</span>
                            ${copyBtn(meta.original_language_prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-sm">${this._esc(meta.original_language_prompt)}</p>
                    </div>
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-brand-text-muted font-medium">${t('asset_viewer.meta_user_prompt')}</label>
                            <span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">EN</span>
                            ${copyBtn(meta.original_prompt || meta.prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-sm">${this._esc(meta.original_prompt || meta.prompt)}</p>
                    </div>`;
            } else if (meta.original_prompt) {
                promptLineage += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-brand-text-muted font-medium">${t('asset_viewer.meta_user_prompt')}</label>
                            ${copyBtn(meta.original_prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-sm">${this._esc(meta.original_prompt)}</p>
                    </div>`;
            }

            // Moderation Rewrite
            if (meta.moderation_original) {
                promptLineage += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-amber-400 font-medium">${t('asset_viewer.meta_moderation_rewrite')}</label>
                            ${copyBtn(meta.moderation_original)}
                        </div>
                        <p class="text-[10px] text-amber-300/70 mb-1">${t('asset_viewer.meta_moderation_note')}</p>
                        <p class="p-3 rounded-lg bg-amber-950/10 border border-amber-500/20 whitespace-pre-wrap text-sm text-amber-200/80">${this._esc(meta.moderation_original)}</p>
                    </div>`;
            }

            // AI Enhanced Prompt
            if (!isTypeStudio && meta.enhanced_prompt) {
                promptLineage += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-brand-text-muted font-medium">${t('asset_viewer.meta_enhanced_prompt')}</label>
                            ${copyBtn(meta.enhanced_prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-sm text-brand-text-muted">${this._esc(meta.enhanced_prompt)}</p>
                    </div>`;
            }

            // Final Prompt Sent (only show if different from enhanced)
            if (!isTypeStudio && meta.prompt && meta.prompt !== meta.enhanced_prompt) {
                promptLineage += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-brand-text-muted font-medium">${t('asset_viewer.meta_final_prompt')}</label>
                            ${copyBtn(meta.prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-sm">${this._esc(meta.prompt)}</p>
                    </div>`;
            } else if (isTypeStudio && meta.prompt) {
                promptLineage += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-brand-text-muted font-medium">${t('asset_viewer.meta_text_content')}</label>
                            ${copyBtn(meta.prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-sm">${this._esc(meta.prompt)}</p>
                    </div>`;
            }

            // Negative Prompt
            if (meta.negative_prompt) {
                promptLineage += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-amber-400/80 font-medium">${t('asset_viewer.meta_negative_exclusions')}</label>
                            ${copyBtn(meta.negative_prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-amber-950/20 border border-amber-900/20 whitespace-pre-wrap text-amber-300/70 italic text-sm">${this._esc(meta.negative_prompt)}</p>
                    </div>`;
            }

            // ── Section 2: Prompt Design ──────────────────────────────────
            let promptDesign = '';
            if (!isTypeStudio && meta.recomposed_prompt) {
                promptDesign += `
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <label class="text-xs text-indigo-400/80 font-medium">${t('asset_viewer.meta_recomposed')}</label>
                            ${copyBtn(meta.recomposed_prompt)}
                        </div>
                        <p class="p-3 rounded-lg bg-indigo-950/10 border border-indigo-500/20 whitespace-pre-wrap text-brand-text-muted text-sm">${this._esc(meta.recomposed_prompt)}</p>
                    </div>`;
            }
            if (meta.decomposed_data && Object.keys(meta.decomposed_data).length > 0) {
                promptDesign += `
                    <div>
                        <label class="text-xs text-amber-400/80 font-medium mb-1 block">${t('asset_viewer.meta_decomposition')}</label>
                        <div class="p-3 rounded-lg bg-amber-950/10 border border-amber-500/20 text-xs text-brand-text/70 space-y-2">
                            ${this._renderDecomposed(meta.decomposed_data)}
                        </div>
                    </div>`;
            }

            // ── Section 3: Generation Details ──────────────────────────────
            let genDetails = `<div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">`;
            if (modelLabel) {
                genDetails += `<div>
                    <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_model')}</label>
                    <p class="font-medium text-sm">${this._esc(modelLabel)}</p>
                </div>`;
            }
            genDetails += `<div>
                <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_type')}</label>
                <p class="font-medium text-sm">${typeLabel}</p>
            </div>`;
            if (styleName) {
                genDetails += `<div>
                    <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_style')}</label>
                    <p class="font-medium text-sm">${this._esc(styleName)}</p>
                </div>`;
            }
            genDetails += `<div>
                <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_dimensions')}</label>
                <p class="font-medium text-sm">${meta.width || '?'} x ${meta.height || '?'}</p>
            </div>`;
            if (meta.quality) {
                genDetails += `<div>
                    <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_quality')}</label>
                    <p class="font-medium text-sm">${this._esc(meta.quality)}</p>
                </div>`;
            }
            if (meta.region) {
                genDetails += `<div>
                    <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_region')}</label>
                    <p class="font-medium text-sm">${this._esc(meta.region)}</p>
                </div>`;
            }
            if (meta.seed != null) {
                genDetails += `<div>
                    <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_seed')}</label>
                    <p class="font-medium font-mono text-xs">${meta.seed}</p>
                </div>`;
            }
            genDetails += `<div>
                <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_created')}</label>
                <p class="font-medium text-sm">${createdAt}</p>
            </div>`;
            genDetails += `<div>
                <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_batch')}</label>
                <p class="font-mono text-[10px] text-brand-text-muted">${this._esc(meta.batch_id || meta.id)}</p>
            </div>`;
            // Option/Variation with totals
            const optDisplay = `${(meta.option_index ?? 0) + 1} / ${(meta.variant_index ?? 0) + 1}`;
            const optTotal = (meta.num_options && meta.num_variations) ? ` of ${meta.num_options} × ${meta.num_variations}` : '';
            genDetails += `<div>
                <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_options_variations')}</label>
                <p class="font-medium text-sm">${optDisplay}${optTotal}</p>
            </div>`;
            if (meta.all_models) {
                genDetails += `<div>
                    <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_all_models')}</label>
                    <p class="font-medium text-sm"><span class="px-1.5 py-0.5 rounded text-[9px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${t('asset_viewer.meta_all_models')}</span></p>
                </div>`;
            }
            if (meta.estimated_image_cost_usd != null) {
                genDetails += `<div>
                    <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_cost')}</label>
                    <p class="font-medium text-sm">~$${meta.estimated_image_cost_usd.toFixed(4)}</p>
                </div>`;
            }
            genDetails += `</div>`;

            // ── Section 4: Post-Processing ─────────────────────────────────
            let postProcessing = '';
            const hasPostProc = meta.remove_background || meta.generate_svg || meta.upscale || meta.upscaled;
            if (hasPostProc || (meta.cost_history && meta.cost_history.length > 0)) {
                let ppContent = '<div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2">';
                if (meta.remove_background) {
                    ppContent += `<div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span class="text-sm">${t('asset_viewer.meta_bg_removed')}</span>
                    </div>`;
                }
                if (meta.generate_svg) {
                    ppContent += `<div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span class="text-sm">${t('asset_viewer.meta_svg_generated')}</span>
                    </div>`;
                }
                if (meta.upscale || meta.upscaled) {
                    ppContent += `<div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span class="text-sm">${t('asset_viewer.meta_upscaled')}</span>
                    </div>`;
                }
                ppContent += '</div>';

                // Cost breakdown from cost_history — with a summed total so the
                // per-step actuals reconcile (previously there was no total).
                if (meta.cost_history && meta.cost_history.length > 0) {
                    const _histTotal = meta.cost_history.reduce((s, c) => s + (c.cost_usd || c.cost || 0), 0);
                    ppContent += `<div class="mt-3 border-t border-brand-border/30 pt-2">
                        <label class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-1 block">${t('asset_viewer.meta_cost_breakdown')}</label>
                        <div class="space-y-1">
                            ${meta.cost_history.map(c => `
                                <div class="flex justify-between text-xs text-brand-text-muted">
                                    <span>${this._esc(c.label || c.type || '?')}</span>
                                    <span class="font-mono">$${(c.cost_usd || c.cost || 0).toFixed(4)}</span>
                                </div>
                            `).join('')}
                            <div class="flex justify-between text-xs text-brand-text font-medium border-t border-brand-border/30 pt-1 mt-1">
                                <span>${t('asset_viewer.meta_cost_total')}</span>
                                <span class="font-mono">$${_histTotal.toFixed(4)}</span>
                            </div>
                        </div>
                    </div>`;
                }
                postProcessing = ppContent;
            }

            // ── Section 5: 3D Model ────────────────────────────────────────
            // The backend persists 3D provenance in `meta.three_d_versions` (a
            // list keyed by 2D version), each entry carrying a `pipeline` dict
            // (geometry model + texture backend + instance + license consent),
            // the exact deployed `model_key`, the `job_id`, params and file stats.
            // (Legacy `meta.three_d.v{N}` is still honored as a fallback.)
            let threeDContent = '';
            const currentVer = this._currentVersion || meta.current_version || (meta.versions?.length || 1);
            const threeDData = this._default3DVariant(meta, currentVer)
                || this._default3DVariant(meta, 1);
            if (threeDData) {
                const pl = threeDData.pipeline || {};
                const created3D = threeDData.created_at || threeDData.generated_at;
                threeDContent = `<div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-sm">`;
                if (created3D) {
                    threeDContent += `<div>
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_generated')}</label>
                        <p>${window.formatTimestamp(created3D)}</p>
                    </div>`;
                }
                // Geometry model (e.g. TripoSG / TRELLIS.2 full pipeline)
                if (pl.geometry_model || threeDData.model_key) {
                    threeDContent += `<div>
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_geometry')}</label>
                        <p>${this._esc(pl.geometry_model || threeDData.model_key)}</p>
                    </div>`;
                }
                // Texture backend label (Hunyuan / MV-Adapter bake / TRELLIS.2)
                if (pl.texture_label || pl.texture_backend) {
                    threeDContent += `<div>
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_texture')}</label>
                        <p>${this._esc(pl.texture_label || pl.texture_backend)}</p>
                    </div>`;
                }
                // Exact deployed endpoint that produced this asset (disambiguates
                // multiple deployments of the same model).
                if (threeDData.model_key) {
                    threeDContent += `<div class="col-span-2 sm:col-span-3">
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_endpoint')}</label>
                        <p class="font-mono text-xs">${this._esc(threeDData.model_key)}${pl.instance_type ? ` <span class="text-brand-text-muted">(${this._esc(pl.instance_type)})</span>` : ''}</p>
                    </div>`;
                } else if (pl.instance_type) {
                    threeDContent += `<div>
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_instance')}</label>
                        <p class="font-mono text-xs">${this._esc(pl.instance_type)}</p>
                    </div>`;
                }
                if (threeDData.job_id) {
                    threeDContent += `<div class="col-span-2 sm:col-span-3">
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_job_id')}</label>
                        <p class="font-mono text-xs text-brand-text-muted">${this._esc(threeDData.job_id)}${copyBtn(threeDData.job_id)}</p>
                    </div>`;
                }
                if (pl.has_pbr) {
                    threeDContent += `<div>
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_pbr')}</label>
                        <p class="text-sm"><span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">PBR</span></p>
                    </div>`;
                }
                if (threeDData.params) {
                    const p = threeDData.params;
                    const paramStr = [
                        p.steps ? `steps: ${p.steps}` : '',
                        p.guidance ? `guidance: ${p.guidance}` : '',
                        p.mesh_resolution ? `depth: ${p.mesh_resolution}` : '',
                        p.max_faces ? `faces: ${p.max_faces}` : '',
                        p.texture_resolution ? `tex: ${p.texture_resolution}` : '',
                    ].filter(Boolean).join(', ');
                    if (paramStr) {
                        threeDContent += `<div class="col-span-2 sm:col-span-3">
                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_params')}</label>
                            <p class="font-mono text-xs">${this._esc(paramStr)}</p>
                        </div>`;
                    }
                }
                if (threeDData.size_bytes || threeDData.vertices || threeDData.faces) {
                    threeDContent += `<div class="col-span-2 sm:col-span-3">
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_file')}</label>
                        <p class="text-xs">${threeDData.size_bytes ? this._formatBytes(threeDData.size_bytes) : ''}${threeDData.vertices ? ` / ${threeDData.vertices.toLocaleString()} vertices` : ''}${threeDData.faces ? ` / ${threeDData.faces.toLocaleString()} faces` : ''}</p>
                    </div>`;
                }
                // License consent provenance (the license accepted at deploy time)
                if (pl.license_name) {
                    threeDContent += `<div class="col-span-2 sm:col-span-3">
                        <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t('asset_viewer.meta_3d_license')}</label>
                        <p class="text-xs">${this._esc(pl.license_name)}${pl.commercial === true ? ` <span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('asset_viewer.meta_3d_commercial')}</span>` : ''}${pl.license_accepted_at ? ` <span class="text-brand-text-muted">— ${window.formatTimestamp(pl.license_accepted_at)}</span>` : ''}</p>
                    </div>`;
                }
                threeDContent += `</div>`;
            }

            // ── Section 6: Style ───────────────────────────────────────────
            let styleContent = '';
            if (meta.style_snapshot) {
                if (meta.style_snapshot.description) {
                    styleContent += `<p class="text-sm text-brand-text-muted">${this._esc(meta.style_snapshot.description)}</p>`;
                }
                if (meta.style_snapshot.generation_hints) {
                    styleContent += `
                        <div>
                            <label class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-1 block">${t('asset_viewer.meta_style_hints')}</label>
                            <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-xs text-brand-text-muted">${this._esc(meta.style_snapshot.generation_hints)}</p>
                        </div>`;
                }
            }

            // ── Section 7: IP Declaration ──────────────────────────────────
            let ipContent = '';
            if (meta.ip_owned || meta.ip_licensed) {
                ipContent = `<div class="p-2 rounded-lg bg-brand-accent/10 border border-brand-accent/20 text-xs">
                    <span class="font-medium">${t('asset_viewer.meta_ip_declaration')}</span>
                    ${meta.ip_owned ? ' ' + t('asset_viewer.meta_ip_owner') : ''}${meta.ip_licensed ? ' ' + t('asset_viewer.meta_ip_licensed') : ''}
                </div>`;
            }

            // ── Section 8: Edit History ────────────────────────────────────
            let editHistoryContent = '';
            if (meta.edit_history?.length) {
                editHistoryContent = `
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-2">
                        ${t('asset_viewer.meta_edit_history')} (${meta.edit_count || meta.edit_history.length} edit${meta.edit_history.length > 1 ? 's' : ''})
                    </label>
                    ${meta.original_prompt ? `
                    <p class="text-[10px] text-brand-text-dim mb-2">${t('asset_viewer.meta_original_prompt_label')} "${this._esc(meta.original_prompt)}"</p>` : ''}
                    ${meta.original_image_model ? `
                    <p class="text-[10px] text-brand-text-dim mb-2">${t('asset_viewer.meta_originally_generated')} ${this._esc(meta.original_image_model)}</p>` : ''}
                    <div class="space-y-2">
                        ${meta.edit_history.map((edit, i) => `
                        <div class="p-2 rounded bg-brand-bg/40 border-l-2 ${i === meta.edit_history.length - 1 ? 'border-emerald-400' : 'border-brand-border'}">
                            <div class="flex items-center justify-between text-[10px] text-brand-text-muted mb-1">
                                <span class="font-semibold">#${i + 1} ${this._esc(edit.edit_type || '?')}</span>
                                <span>${edit.timestamp ? window.formatTimestamp(edit.timestamp) : ''}</span>
                            </div>
                            <p class="text-xs">${this._esc(edit.model_label || edit.edit_model || '')}</p>
                            ${edit.original_language_prompts?.prompt ? `<p class="text-xs text-brand-text/70 mt-0.5"><span class="text-[9px] text-brand-accent">(${edit.original_language || '?'})</span> "${this._esc(edit.original_language_prompts.prompt)}"</p>` : ''}
                            ${edit.prompt ? `<p class="text-xs text-brand-text/70 mt-0.5">${edit.original_language_prompts?.prompt ? '<span class="text-[9px] text-emerald-400/70">(en)</span> ' : ''}"${this._esc(edit.prompt)}"</p>` : ''}
                            ${edit.negative_prompt ? `<p class="text-[10px] text-amber-300/60 italic mt-0.5">${t('asset_viewer.meta_negative_label')} ${this._esc(edit.negative_prompt)}</p>` : ''}
                            ${edit.mask_prompt ? `<p class="text-[10px] text-brand-text-dim mt-0.5">${t('asset_viewer.meta_mask_label')} "${this._esc(edit.mask_prompt)}"</p>` : ''}
                            ${edit.extra_params?.search_prompt ? `<p class="text-[10px] text-brand-text-dim mt-0.5">${t('asset_viewer.meta_find_label')} "${this._esc(edit.extra_params.search_prompt)}"</p>` : ''}
                            ${edit.extra_params?.select_prompt ? `<p class="text-[10px] text-brand-text-dim mt-0.5">${t('asset_viewer.meta_select_label')} "${this._esc(edit.extra_params.select_prompt)}"</p>` : ''}
                            ${edit.replaced_original ? '<span class="text-[9px] text-amber-400/50">' + t('asset_viewer.meta_replaced_original') + '</span>' : '<span class="text-[9px] text-emerald-400/50">' + t('asset_viewer.meta_saved_as_new') + '</span>'}
                        </div>
                        `).join('')}
                    </div>`;
            } else if (meta.edit_type) {
                editHistoryContent = `
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_edit_info')}</label>
                    <p class="text-sm"><span class="text-brand-text-muted">${t('asset_viewer.meta_type_label')}</span> ${this._esc(meta.edit_type)}</p>
                    <p class="text-sm"><span class="text-brand-text-muted">${t('asset_viewer.meta_model_label')}</span> ${this._esc(meta.model_label || meta.edit_model || '')}</p>
                    ${meta.source_image_id ? `<p class="text-sm"><span class="text-brand-text-muted">${t('asset_viewer.meta_source_label')}</span> ${this._esc(meta.source_image_id)}</p>` : ''}`;
            }

            // ── Section 9: File Info ───────────────────────────────────────
            let fileInfoContent = `<div class="space-y-1 text-sm">`;
            if (meta.png_filename) {
                fileInfoContent += `<div class="flex items-center gap-2">
                    <span class="text-brand-text-muted text-[10px] uppercase w-10">PNG</span>
                    <span class="font-mono text-xs">${this._esc(meta.png_filename)}</span>
                </div>`;
            }
            if (meta.svg_filename) {
                fileInfoContent += `<div class="flex items-center gap-2">
                    <span class="text-brand-text-muted text-[10px] uppercase w-10">SVG</span>
                    <span class="font-mono text-xs">${this._esc(meta.svg_filename)}</span>
                </div>`;
            }
            if (threeDData?.glb_file) {
                fileInfoContent += `<div class="flex items-center gap-2">
                    <span class="text-brand-text-muted text-[10px] uppercase w-10">GLB</span>
                    <span class="font-mono text-xs">${this._esc(threeDData.glb_file)}</span>
                </div>`;
            }
            fileInfoContent += `</div>`;

            // ── Type Studio section (special) ──────────────────────────────
            let typeStudioContent = '';
            if (isTypeStudio) {
                typeStudioContent = `
                    ${meta.source_image_id ? `<p class="text-sm mb-1"><span class="text-brand-text-muted">${t('asset_viewer.meta_source_image')}</span> ${this._esc(meta.source_image_id)}</p>` : '<p class="text-sm mb-1 text-brand-text-muted">' + t('asset_viewer.meta_standalone_text') + '</p>'}
                    ${meta.style_note ? `<p class="text-sm mb-1"><span class="text-brand-text-muted">${t('asset_viewer.meta_style_note')}</span> ${this._esc(meta.style_note)}</p>` : ''}
                    ${meta.lines ? `
                    <div class="mt-2 space-y-1">
                        ${meta.lines.map((l, i) => `
                            <div class="text-sm p-2 rounded bg-brand-bg/40">
                                <span class="text-brand-text-muted">${t('asset_viewer.meta_line', {num: i+1})}</span> "${this._esc(l.text)}"
                                <span class="text-brand-text-muted/60 text-xs ml-2">${l.font || t('common.default')} / ${l.position || 'center'}</span>
                            </div>
                        `).join('')}
                    </div>` : ''}`;
            }

            // ── Assemble all sections ──────────────────────────────────────
            container.innerHTML = `
                <div class="space-y-4">
                    ${promptLineage ? section('prompts', t('asset_viewer.meta_prompt_lineage'), promptLineage, true) : ''}
                    ${promptDesign ? section('design', t('asset_viewer.meta_prompt_design'), promptDesign, false) : ''}
                    <div class="av-meta-section">
                        <div class="py-2 border-b border-brand-border/50">
                            <span class="text-xs font-semibold uppercase tracking-wider text-brand-text-muted">${t('asset_viewer.meta_generation_details')}</span>
                        </div>
                        <div class="py-3">
                            ${genDetails}
                        </div>
                    </div>
                    ${postProcessing ? section('postproc', t('asset_viewer.meta_post_processing'), postProcessing, true) : ''}
                    ${threeDContent ? section('threed', t('asset_viewer.meta_three_d_section'), threeDContent, true) : ''}
                    ${styleContent ? section('style', t('asset_viewer.meta_style_section'), styleContent, false) : ''}
                    ${ipContent ? section('ip', t('asset_viewer.meta_ip_declaration'), ipContent, true) : ''}
                    ${editHistoryContent ? section('edithist', t('asset_viewer.meta_edit_history'), editHistoryContent, true) : ''}
                    ${isTypeStudio ? section('typestudio', t('asset_viewer.meta_type_studio_details'), typeStudioContent, true) : ''}
                    ${section('fileinfo', t('asset_viewer.meta_file_info'), fileInfoContent, false)}
                </div>
            `;

            // Attach section toggle handlers
            container.querySelectorAll('.av-meta-section-header').forEach(header => {
                header.addEventListener('click', () => {
                    const sectionId = header.dataset.section;
                    const body = container.querySelector(`[data-body="${sectionId}"]`);
                    const arrow = header.querySelector('.av-section-arrow');
                    if (body) {
                        body.classList.toggle('hidden');
                        if (arrow) arrow.classList.toggle('-rotate-90');
                    }
                });
            });

            // Attach copy button handlers
            container.querySelectorAll('.av-copy-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const text = btn.dataset.copy;
                    navigator.clipboard.writeText(text).then(() => {
                        const orig = btn.textContent;
                        btn.textContent = t('asset_viewer.meta_copied');
                        btn.classList.add('text-emerald-400');
                        setTimeout(() => {
                            btn.textContent = orig;
                            btn.classList.remove('text-emerald-400');
                        }, 1500);
                    });
                });
            });
        },

        /**
         * The version bar's verbose PROMPT line belongs only on the image tabs.
         * Hidden on 3D (irrelevant to the mesh) and Metadata (shown there in the
         * tab's own section — avoid duplication). Single source of truth, called
         * by the tab switcher and the version-switch handler. Resolves the active
         * tab from the DOM so it works regardless of caller.
         */
        _syncVersionDetailVisibility(activeTab) {
            const verDetail = this._overlay?.querySelector('#av-version-detail');
            if (!verDetail) return;
            const tab = activeTab
                || this._overlay?.querySelector('.tab.active')?.dataset.tab
                || 'png';
            const promptTabs = this._promptTabs || new Set(['png', 'edit', 'svg']);
            const hasContent = verDetail.innerHTML.trim().length > 0;
            verDetail.classList.toggle('hidden', !(promptTabs.has(tab) && hasContent));
        },

        _updateVersionBar(meta) {
            const bar = this._overlay?.querySelector('#av-version-bar');
            const btns = this._overlay?.querySelector('#av-version-buttons');
            const detail = this._overlay?.querySelector('#av-version-detail');
            if (!bar || !btns) return;

            const versions = meta.versions || [];
            if (versions.length < 2) {
                bar.classList.add('hidden');
                return;
            }

            bar.classList.remove('hidden');
            const currentVersion = meta.current_version || versions.length;

            btns.innerHTML = versions.map(v => `
                <button class="av-version-btn px-2 py-1 rounded text-[10px] transition-all cursor-pointer
                    ${v.version === currentVersion
                        ? 'bg-brand-accent text-white'
                        : 'bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent hover:text-brand-text'}"
                    data-version="${v.version}" data-asset="${meta.id}"
                    title="${v.type}${v.timestamp ? ' — ' + window.formatTimestamp(v.timestamp) : ''}">
                    ${v.version === 1 ? t('asset_viewer.version_original') : 'v' + v.version}
                    ${v.type !== 'original' ? '<span class="opacity-50 ml-0.5">' + v.type + '</span>' : ''}
                </button>
            `).join('');

            // Attach click handlers
            btns.querySelectorAll('.av-version-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const version = parseInt(btn.dataset.version, 10);
                    const assetId = btn.dataset.asset;
                    const v = versions.find(vv => vv.version === version);
                    const vLabel = version === 1 ? t('asset_viewer.version_original') : `v${version}`;

                    // Update PNG image
                    const img = this._overlay?.querySelector('#av-zoom-img');
                    if (img) {
                        img.src = version === currentVersion
                            ? `/api/gallery/${assetId}/png?t=${Date.now()}`
                            : `/api/gallery/${assetId}/version/${version}?t=${Date.now()}`;
                    }

                    // Update SVG image
                    const svgImg = this._overlay?.querySelector('[data-panel="svg"] img');
                    if (svgImg) {
                        svgImg.src = version === currentVersion
                            ? `/api/gallery/${assetId}/svg?t=${Date.now()}`
                            : `/api/gallery/${assetId}/version-svg/${version}?t=${Date.now()}`;
                    }

                    // Update tab version badges
                    const pngBadge = this._overlay?.querySelector('#av-tab-version-badge');
                    const svgBadge = this._overlay?.querySelector('#av-tab-svg-version');
                    const metaBadge = this._overlay?.querySelector('#av-tab-meta-version');
                    if (pngBadge) pngBadge.textContent = versions.length > 1 ? `(${vLabel})` : '';
                    if (svgBadge) svgBadge.textContent = versions.length > 1 ? `(${vLabel})` : '';
                    if (metaBadge) metaBadge.textContent = versions.length > 1 ? `(${vLabel})` : '';

                    // Refresh 3D tab state for the selected version. Switching to a
                    // different version clears any prior source approval so that
                    // version gets its own review before generating.
                    this._currentVersion = version;
                    if (this._sourceApprovedVersion !== version) this._sourceApprovedVersion = null;
                    this._update3DContent();

                    // Update metadata tab to show this version's info
                    const metaContent = this._overlay?.querySelector('#asset-meta-content');
                    if (metaContent && v) {
                        const isOriginal = v.type === 'original';
                        metaContent.innerHTML = `
                            <div class="p-3 rounded-lg bg-brand-accent/5 border border-brand-accent/20 mb-3">
                                <span class="text-xs font-semibold text-brand-accent">${t('asset_viewer.version_label')}: ${vLabel}</span>
                                <span class="text-[10px] text-brand-text-muted ml-2">${isOriginal ? t('asset_viewer.version_original') : v.type}</span>
                                ${v.timestamp ? `<span class="text-[10px] text-brand-text-dim ml-2">${window.formatTimestamp(v.timestamp)}</span>` : ''}
                            </div>
                            ${v.original_language_prompts?.prompt ? `
                            <div>
                                <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('common.prompt')} <span class="text-[9px] text-brand-accent font-normal">(${v.original_language || '?'})</span></label>
                                <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(v.original_language_prompts.prompt)}</p>
                            </div>` : ''}
                            ${v.prompt ? `
                            <div>
                                <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('common.prompt')} ${v.original_language_prompts?.prompt ? '<span class="text-[9px] text-emerald-400/70 font-normal">(English)</span>' : ''}</label>
                                <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(v.prompt)}</p>
                            </div>` : ''}
                            ${v.enhanced_prompt ? `
                            <div>
                                <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_generation_prompt')}</label>
                                <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._esc(v.enhanced_prompt)}</p>
                            </div>` : ''}
                            ${v.negative_prompt ? `
                            <div>
                                <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1 text-amber-400/80">${t('asset_viewer.meta_negative')}</label>
                                <p class="p-3 rounded-lg bg-amber-950/10 border border-amber-500/10 whitespace-pre-wrap text-amber-200/70">${this._esc(v.negative_prompt)}</p>
                            </div>` : ''}
                            ${v.mask_prompt ? `<p class="text-xs text-brand-text-muted">${t('asset_viewer.meta_mask_label')} "${this._esc(v.mask_prompt)}"</p>` : ''}
                            <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                                <p><span class="text-brand-text-muted">${t('asset_viewer.meta_model')}:</span> ${this._esc(v.model_label || v.image_model || 'N/A')}</p>
                                ${v.region ? `<p><span class="text-brand-text-muted">${t('common.region')}:</span> ${this._esc(v.region)}</p>` : ''}
                                ${v.seed != null ? `<p><span class="text-brand-text-muted">${t('asset_viewer.meta_seed')}:</span> ${v.seed}</p>` : ''}
                            </div>
                            <p class="text-[10px] text-brand-text-dim mt-2"><a href="#" class="text-brand-accent hover:underline av-back-to-full-meta">${t('asset_viewer.metadata_tab')} →</a></p>
                        `;
                        // Add click handler to go back to full metadata
                        metaContent.querySelector('.av-back-to-full-meta')?.addEventListener('click', (e) => {
                            e.preventDefault();
                            this._populateMetadata(this._overlay?.querySelector('#asset-meta-content'), meta);
                        });
                    }

                    // Highlight active button
                    btns.querySelectorAll('.av-version-btn').forEach(b => {
                        b.className = b.className
                            .replace(/bg-brand-accent text-white/g, '')
                            .replace(/bg-brand-bg border border-brand-border text-brand-text-muted/g, '');
                        if (parseInt(b.dataset.version, 10) === version) {
                            b.classList.add('bg-brand-accent', 'text-white');
                        } else {
                            b.classList.add('bg-brand-bg', 'border', 'border-brand-border', 'text-brand-text-muted');
                        }
                    });

                    // Show version detail summary (only on image tabs — the
                    // helper hides it on 3D/Metadata to avoid clutter/duplication).
                    if (detail && v) {
                        detail.innerHTML = `
                            <strong>${v.type === 'original' ? t('asset_viewer.version_original') : v.type}</strong>
                            ${v.model_label || v.image_model || ''}
                            ${v.original_language_prompts?.prompt ? ` — <span class="text-[9px] text-brand-accent">(${v.original_language || '?'})</span> "${this._esc(v.original_language_prompts.prompt)}"` : ''}
                            ${v.prompt ? ` — ${v.original_language_prompts?.prompt ? '<span class="text-[9px] text-emerald-400/70">(en)</span> ' : ''}"${this._esc(v.prompt)}"` : ''}
                            ${v.negative_prompt ? ` <span class="text-amber-300/60">[neg: ${this._esc(v.negative_prompt)}]</span>` : ''}
                            ${v.timestamp ? ` <span class="text-brand-text-dim">${window.formatTimestamp(v.timestamp)}</span>` : ''}
                        `;
                        this._syncVersionDetailVisibility();
                    }
                });
            });
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
            // PNG/SVG download footer is only meaningful on the image tabs.
            // Hide it on Metadata + 3D (the 3D tab has its own Download GLB).
            const imageTabs = new Set(['png', 'edit', 'svg']);
            const dlFooter = this._overlay.querySelector('#av-image-downloads');
            // The version bar's verbose PROMPT line is only useful on the image
            // tabs. Hide it on 3D (irrelevant to the mesh) and Metadata (the
            // Metadata tab already shows the full prompt in its own section —
            // don't show it twice). The version BUTTONS stay visible everywhere.
            const promptTabs = new Set(['png', 'edit', 'svg']);
            const verDetail = this._overlay.querySelector('#av-version-detail');
            this._promptTabs = promptTabs;  // used by _syncVersionDetailVisibility
            const syncTabChrome = (activeTab) => {
                if (dlFooter) dlFooter.classList.toggle('hidden', !imageTabs.has(activeTab));
                this._syncVersionDetailVisibility(activeTab);
            };
            syncTabChrome('png');

            this._overlay.querySelectorAll('.tab').forEach((tab) => {
                tab.addEventListener('click', () => {
                    this._overlay.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
                    tab.classList.add('active');
                    this._overlay.querySelectorAll('.tab-panel').forEach((p) => {
                        p.classList.toggle('hidden', p.dataset.panel !== tab.dataset.tab);
                    });
                    syncTabChrome(tab.dataset.tab);
                });
            });

            // ── Previous / Next navigation ────────────────────────────
            const prevBtn = this._overlay.querySelector('.btn-prev');
            const nextBtn = this._overlay.querySelector('.btn-next');

            const updateNavButtons = () => {
                if (prevBtn) prevBtn.disabled = !this._list || this._listIndex <= 0;
                if (nextBtn) nextBtn.disabled = !this._list || this._listIndex < 0 || this._listIndex >= this._list.length - 1;
            };
            updateNavButtons();

            prevBtn?.addEventListener('click', () => {
                if (this._list && this._listIndex > 0) {
                    this._listIndex--;
                    this._navigateTo(this._list[this._listIndex]);
                }
            });
            nextBtn?.addEventListener('click', () => {
                if (this._list && this._listIndex < this._list.length - 1) {
                    this._listIndex++;
                    this._navigateTo(this._list[this._listIndex]);
                }
            });

            // Arrow keys for prev/next
            this._navKeyHandler = (e) => {
                if (e.key === 'ArrowLeft' && this._list && this._listIndex > 0) {
                    this._listIndex--;
                    this._navigateTo(this._list[this._listIndex]);
                } else if (e.key === 'ArrowRight' && this._list && this._listIndex < this._list.length - 1) {
                    this._listIndex++;
                    this._navigateTo(this._list[this._listIndex]);
                }
            };
            document.addEventListener('keydown', this._navKeyHandler);

            // ── Zoom/Pan for PNG viewer ─────────────────────────────────
            this._initZoomPan();

            // ── Edit tab (Inpaint/Outpaint/Erase) ──────────────────────
            this._initEditTab();

            // ── 3D Model tab ───────────────────────────────────────────
            this._init3DTab();

            // Reload in 2D Image Studio
            this._overlay.querySelector('.btn-reload')?.addEventListener('click', async () => {
                const meta = this._meta;
                if (!meta) {
                    window.showToast?.(t('asset_viewer.metadata_not_loaded'), 'warning');
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
                    window.showToast?.(t('asset_viewer.metadata_not_loaded'), 'warning');
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

                    // Show/hide sections based on mode
                    const needsMask = editMode === 'inpaint' || editMode === 'erase';
                    const needsOutpaint = editMode === 'outpaint';
                    const needsSearch = editMode === 'search_replace' || editMode === 'search_recolor';

                    const maskSection = this._overlay.querySelector('#av-mask-section');
                    const outSection = this._overlay.querySelector('#av-outpaint-section');
                    const searchSection = this._overlay.querySelector('#av-search-section');
                    const searchLabel = this._overlay.querySelector('#av-search-label');
                    const promptLabel = this._overlay.querySelector('#av-prompt-label');

                    if (maskSection) maskSection.classList.toggle('hidden', !needsMask);
                    if (outSection) outSection.classList.toggle('hidden', !needsOutpaint);
                    if (searchSection) searchSection.classList.toggle('hidden', !needsSearch);

                    // Update labels, placeholders, and hints for each mode
                    if (searchLabel) {
                        searchLabel.textContent = editMode === 'search_recolor'
                            ? t('asset_viewer.search_recolor_label')
                            : t('asset_viewer.search_replace_label');
                    }
                    if (promptLabel) {
                        const labels = {
                            'inpaint': t('asset_viewer.edit_prompt_inpaint'),
                            'erase': t('asset_viewer.edit_prompt_erase_full'),
                            'outpaint': t('asset_viewer.edit_prompt_outpaint_full'),
                            'search_replace': t('asset_viewer.edit_prompt_replace'),
                            'search_recolor': t('asset_viewer.edit_prompt_recolor'),
                        };
                        promptLabel.textContent = labels[editMode] || t('asset_viewer.edit_prompt_default');
                    }
                    // Update placeholder per mode
                    const promptInput = this._overlay?.querySelector('#av-edit-prompt');
                    if (promptInput) {
                        const placeholders = {
                            'inpaint': t('asset_viewer.edit_prompt_placeholder_inpaint'),
                            'erase': t('asset_viewer.edit_prompt_placeholder_erase'),
                            'outpaint': t('asset_viewer.edit_prompt_placeholder_outpaint'),
                            'search_replace': t('asset_viewer.edit_prompt_placeholder_replace'),
                            'search_recolor': t('asset_viewer.edit_prompt_placeholder_recolor'),
                        };
                        promptInput.placeholder = placeholders[editMode] || t('asset_viewer.edit_prompt_placeholder');
                    }
                    // Update mode-specific hint
                    const maskHint = this._overlay?.querySelector('#av-mask-section p');
                    const editHint = this._overlay?.querySelector('#av-edit-status')?.previousElementSibling;
                    const hints = {
                        'inpaint': t('asset_viewer.edit_mode_hint_inpaint'),
                        'erase': t('asset_viewer.edit_mode_hint_erase'),
                        'outpaint': t('asset_viewer.edit_mode_hint_outpaint'),
                        'search_replace': t('asset_viewer.edit_mode_hint_replace'),
                        'search_recolor': t('asset_viewer.edit_mode_hint_recolor'),
                    };
                    if (maskHint && needsMask) {
                        maskHint.textContent = hints[editMode] || t('asset_viewer.mask_hint_full');
                    }
                    if (editHint) {
                        editHint.textContent = hints[editMode] || t('asset_viewer.edit_hint_full');
                    }
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
                    window.showToast?.(t('asset_viewer.select_edit_model'), 'warning');
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> ' + t('asset_viewer.applying');
                if (statusEl) { statusEl.textContent = t('asset_viewer.processing'); statusEl.classList.remove('hidden'); }

                try {
                    // Extract mask from canvas (only for mask-based modes)
                    let maskB64 = null;
                    const needsMask = editMode === 'inpaint' || editMode === 'erase';
                    if (needsMask) {
                        const maskResult = this._extractMask(canvas);
                        if (maskResult.isEmpty) {
                            window.showToast?.(t('asset_viewer.no_mask_full'), 'warning');
                            btn.disabled = false;
                            btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> ' + t('asset_viewer.apply_edit');
                            return;
                        }
                        maskB64 = maskResult.data;
                    }

                    const searchPrompt = this._overlay.querySelector('#av-search-prompt')?.value || '';

                    const payload = {
                        source_image_id: this._item?.id,
                        model: model,
                        prompt: prompt,
                        mask: maskB64,
                        outpaint_left: parseInt(this._overlay.querySelector('#av-out-left')?.value || '0', 10),
                        outpaint_right: parseInt(this._overlay.querySelector('#av-out-right')?.value || '0', 10),
                        outpaint_up: parseInt(this._overlay.querySelector('#av-out-up')?.value || '0', 10),
                        outpaint_down: parseInt(this._overlay.querySelector('#av-out-down')?.value || '0', 10),
                        extra_params: {},
                    };

                    // Add search/select prompts for search-based modes
                    if (editMode === 'search_replace' && searchPrompt) {
                        payload.extra_params.search_prompt = searchPrompt;
                    } else if (editMode === 'search_recolor' && searchPrompt) {
                        payload.extra_params.select_prompt = searchPrompt;
                    }

                    const result = await fetch('/api/generate/edit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    }).then(r => {
                        if (!r.ok) throw new Error(`${r.status}: ${r.statusText}`);
                        return r.json();
                    });

                    if (statusEl) { statusEl.textContent = t('asset_viewer.edit_saved', {id: result.id}); }
                    window.showToast?.(t('asset_viewer.edit_success', {model: result.model_label}), 'success');

                    // Reload the viewer with cache-busted URLs
                    const cacheBust = `?t=${Date.now()}`;
                    const newItem = {
                        id: result.id,
                        prompt: prompt,
                        png_url: `${result.png_url}${cacheBust}`,
                        png_filename: result.png_filename,
                    };
                    // Refresh Gallery thumbnails so they show the latest version
                    if (window.Gallery?.refresh) window.Gallery.refresh();
                    this.close();
                    setTimeout(() => this.open(newItem), 300);
                } catch (err) {
                    if (statusEl) { statusEl.textContent = t('asset_viewer.error_prefix', {message: err.message}); }
                    window.showToast?.(t('asset_viewer.edit_failed') + ': ' + err.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> ' + t('asset_viewer.apply_edit');
                }
            });
        },

        _loadEditModels(mode) {
            const sel = this._overlay?.querySelector('#av-edit-model');
            if (!sel) return;

            const purposeMap = {
                'inpaint': 'inpainting',
                'erase': 'erase',
                'outpaint': 'outpainting',
                'search_replace': 'search_replace',
                'search_recolor': 'search_recolor',
            };
            const purpose = purposeMap[mode] || 'inpainting';

            // Try to determine the generating model for smart default selection
            const generatingModel = this._meta?.image_model || '';

            fetch(`/api/admin/models`).then(r => r.json()).then(data => {
                sel.innerHTML = '';
                const models = data.image_models || {};
                let defaultKey = '';

                for (const [key, cfg] of Object.entries(models)) {
                    if (cfg.model_purpose === purpose && cfg.enabled) {
                        const opt = document.createElement('option');
                        opt.value = key;
                        // Only show a price when the registry actually has one —
                        // "$0.00/img" for a model with no base price is misleading.
                        const _p = cfg.base_price_usd;
                        opt.textContent = (_p != null && _p > 0)
                            ? `${cfg.label} ($${_p.toFixed(2)}/img)` : cfg.label;
                        sel.appendChild(opt);

                        // Smart default: prefer the inpaint variant of the generating model
                        if (generatingModel && key.startsWith(generatingModel)) {
                            defaultKey = key;
                        }
                    }
                }

                // Select smart default or first available
                if (defaultKey) sel.value = defaultKey;

                if (sel.options.length === 0) {
                    const opt = document.createElement('option');
                    opt.value = '';
                    opt.textContent = t('asset_viewer.no_models_for_type');
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

            const scale = canvas._imgScale || 1;
            const srcCtx = canvas.getContext('2d');
            const srcData = srcCtx.getImageData(0, 0, canvas.width, canvas.height);
            const baseData = canvas._baseImageData;

            mctx.fillStyle = 'black';
            mctx.fillRect(0, 0, w, h);
            mctx.fillStyle = 'white';

            let paintedPixels = 0;
            for (let y = 0; y < canvas.height; y++) {
                for (let x = 0; x < canvas.width; x++) {
                    const i = (y * canvas.width + x) * 4;
                    if (baseData && (
                        Math.abs(srcData.data[i] - baseData.data[i]) > 20 ||
                        Math.abs(srcData.data[i + 1] - baseData.data[i + 1]) > 20 ||
                        Math.abs(srcData.data[i + 2] - baseData.data[i + 2]) > 20
                    )) {
                        const ox = Math.round(x / scale);
                        const oy = Math.round(y / scale);
                        mctx.fillRect(ox - 2, oy - 2, 4, 4);
                        paintedPixels++;
                    }
                }
            }

            const data = maskCanvas.toDataURL('image/png').split(',')[1];
            return { data, isEmpty: paintedPixels === 0 };
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

            // Measurement overlay (Measure toggle). Tracks the SAME pan/scale as the
            // image so the ruler, subject bounding box, and per-edge margins stay
            // pinned to the image at any zoom/pan/fit. Generic: measures whatever
            // alpha silhouette exists (any subject), or ruler-only when opaque.
            const measureCanvas = this._overlay.querySelector('#av-zoom-measure');
            const measureBtn = this._overlay.querySelector('#av-zoom-measure-btn');
            let measureOn = false;
            let _bbox = null, _measured = false;   // subject bbox in image px

            const _activeClass = 'bg-white/30 text-white';
            const _clearActive = () => {
                [btnFit, btnActual, btnIn, btnOut].forEach(b => {
                    if (b) b.className = b.className.replace(/bg-brand-accent text-white/g, '').trim();
                });
            };

            const drawMeasure = () => {
                if (!measureCanvas || !measureOn) return;
                const iW = img.naturalWidth, iH = img.naturalHeight;
                if (!iW || !iH) return;
                const rect = container.getBoundingClientRect();
                const dpr = window.devicePixelRatio || 1;
                if (measureCanvas.width !== Math.round(rect.width * dpr) || measureCanvas.height !== Math.round(rect.height * dpr)) {
                    measureCanvas.width = Math.round(rect.width * dpr);
                    measureCanvas.height = Math.round(rect.height * dpr);
                }
                const ctx = measureCanvas.getContext('2d');
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.clearRect(0, 0, rect.width, rect.height);
                // Image → container space: same transform the <img> uses.
                const toX = (ix) => panX + ix * scale;
                const toY = (iy) => panY + iy * scale;
                // Image frame.
                ctx.strokeStyle = 'rgba(160,170,190,0.7)'; ctx.lineWidth = 1;
                ctx.strokeRect(toX(0) + 0.5, toY(0) + 0.5, iW * scale, iH * scale);
                // Subject bbox (if measured) + margin labels.
                if (_bbox) {
                    ctx.save();
                    ctx.strokeStyle = 'rgba(52, 211, 153, 0.9)'; ctx.setLineDash([4, 3]); ctx.lineWidth = 1.5;
                    ctx.strokeRect(toX(_bbox.x) + 0.5, toY(_bbox.y) + 0.5, _bbox.w * scale, _bbox.h * scale);
                    ctx.restore();
                    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.font = '11px ui-monospace, monospace';
                    const lbl = (txt, x, y, align) => {
                        ctx.textAlign = align || 'center'; ctx.textBaseline = 'middle';
                        const w = ctx.measureText(txt).width;
                        const px = align === 'left' ? x : align === 'right' ? x - w : x - w / 2;
                        ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillRect(px - 3, y - 8, w + 6, 16);
                        ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.fillText(txt, x, y);
                    };
                    const mUp = _bbox.y, mDown = iH - (_bbox.y + _bbox.h);
                    const mLeft = _bbox.x, mRight = iW - (_bbox.x + _bbox.w);
                    const cropTag = (v) => v <= 1 ? ' ⚠' : '';
                    lbl(`↑ ${mUp}px${cropTag(mUp)}`, toX(_bbox.x + _bbox.w / 2), toY(_bbox.y / 2));
                    lbl(`↓ ${mDown}px${cropTag(mDown)}`, toX(_bbox.x + _bbox.w / 2), toY(_bbox.y + _bbox.h + mDown / 2));
                    lbl(`← ${mLeft}px${cropTag(mLeft)}`, toX(_bbox.x / 2), toY(_bbox.y + _bbox.h / 2));
                    lbl(`${mRight}px${cropTag(mRight)} →`, toX(_bbox.x + _bbox.w + mRight / 2), toY(_bbox.y + _bbox.h / 2));
                }
                // Ruler ticks along top + left edges (true image pixels).
                ctx.fillStyle = 'rgba(210,215,230,0.85)'; ctx.strokeStyle = 'rgba(150,158,178,0.6)'; ctx.lineWidth = 1;
                ctx.font = '9px ui-monospace, monospace';
                const step = iW > 1400 ? 512 : 256;
                ctx.textAlign = 'center'; ctx.textBaseline = 'top';
                for (let px = 0; px <= iW; px += step) {
                    const x = toX(px);
                    ctx.beginPath(); ctx.moveTo(x, toY(0)); ctx.lineTo(x, toY(0) + 6); ctx.stroke();
                    ctx.fillText(String(px), x, toY(0) + 7);
                }
                ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
                for (let py = 0; py <= iH; py += step) {
                    const y = toY(py);
                    ctx.beginPath(); ctx.moveTo(toX(0), y); ctx.lineTo(toX(0) + 6, y); ctx.stroke();
                    ctx.fillText(String(py), toX(0) + 8, y);
                }
                // Size caption.
                ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.font = '10px ui-monospace, monospace';
                ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
                ctx.fillText(`${iW}×${iH}px`, 6, rect.height - 4);
            };

            const measureImage = () => {
                if (_measured) return;
                const iW = img.naturalWidth, iH = img.naturalHeight;
                if (!iW || !iH) return;
                _measured = true;
                try {
                    const s = Math.min(1, 256 / Math.max(iW, iH));
                    const sw = Math.max(1, Math.round(iW * s)), sh = Math.max(1, Math.round(iH * s));
                    const c = document.createElement('canvas'); c.width = sw; c.height = sh;
                    const cx = c.getContext('2d', { willReadFrequently: true });
                    cx.drawImage(img, 0, 0, sw, sh);
                    const px = cx.getImageData(0, 0, sw, sh).data;
                    let minX = sw, minY = sh, maxX = -1, maxY = -1, transparent = 0;
                    for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) {
                        if (px[(y * sw + x) * 4 + 3] <= 16) { transparent++; continue; }
                        if (x < minX) minX = x; if (x > maxX) maxX = x;
                        if (y < minY) minY = y; if (y > maxY) maxY = y;
                    }
                    if ((transparent / (sw * sh)) > 0.02 && maxX >= 0) {
                        _bbox = { x: Math.round(minX / s), y: Math.round(minY / s),
                            w: Math.round((maxX - minX + 1) / s), h: Math.round((maxY - minY + 1) / s) };
                    } else { _bbox = null; }  // opaque image → ruler only
                } catch { _bbox = null; }
            };

            const updateTransform = () => {
                img.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
                if (levelEl) levelEl.textContent = `${Math.round(scale * 100)}%`;
                drawMeasure();

                // Highlight the active mode button
                _clearActive();
                const pct = Math.round(scale * 100);
                if (Math.abs(scale - _fitScale) < 0.01 && btnFit) {
                    btnFit.classList.add(..._activeClass.split(' '));
                } else if (pct === 100 && btnActual) {
                    btnActual.classList.add(..._activeClass.split(' '));
                }
            };

            // Measure toggle.
            measureBtn?.addEventListener('click', () => {
                measureOn = !measureOn;
                measureCanvas?.classList.toggle('hidden', !measureOn);
                measureBtn.classList.toggle('bg-white/30', measureOn);
                measureBtn.classList.toggle('text-white', measureOn);
                if (measureOn) {
                    // Measure once the image is decoded (may be lazy-loaded).
                    if (img.complete && img.naturalWidth > 0) { measureImage(); drawMeasure(); }
                    else img.addEventListener('load', () => { measureImage(); drawMeasure(); }, { once: true });
                }
            });
            // Redraw on window resize (container size changes → recompute overlay).
            window.addEventListener('resize', () => { if (measureOn) drawMeasure(); });

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

            // Fit on load — wait for BOTH the container to have dimensions
            // AND the image to have naturalWidth (fully decoded)
            const doFit = () => {
                if (container.clientWidth > 0 && container.clientHeight > 0 && img.naturalWidth > 0) {
                    fitToView();
                } else {
                    requestAnimationFrame(doFit);
                }
            };
            // Always wait for load event to ensure naturalWidth is available
            if (img.complete && img.naturalWidth > 0) {
                requestAnimationFrame(doFit);
            } else {
                img.addEventListener('load', () => requestAnimationFrame(doFit), { once: true });
            }

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

        _init3DTab() {
            this._3dPollTimer = null;
            this._3dJobId = null;
            this._currentVersion = null;
            // Version number whose source has been reviewed+approved in the confirm
            // dialog. When it equals _currentVersion, the Generate button generates
            // directly (no re-review) — the review dialog NEVER triggers generation
            // itself; it only prepares/approves the image and returns to the form,
            // which is the single place generation is fired. null = not yet reviewed.
            this._sourceApprovedVersion = null;
            if (!window._3dActiveJobs) window._3dActiveJobs = {};
        },

        async _update3DContent() {
            const container = this._overlay?.querySelector('#av-3d-content');
            if (!container) return;

            const meta = this._meta;
            if (!meta) {
                container.innerHTML = `<p class="text-brand-text-muted text-center py-8">${t('asset_viewer.loading_metadata')}</p>`;
                return;
            }

            // Only supported for game_asset and character types
            const assetType = meta.asset_type;
            if (assetType !== 'game_asset' && assetType !== 'character') {
                container.innerHTML = `
                    <div class="text-center py-8">
                        <p class="text-brand-text-muted">${t('asset_viewer.three_d_unsupported')}</p>
                    </div>`;
                return;
            }

            // Parallel jobs: the in-progress strip (#av-3d-jobs) is driven by its
            // own poller (_start3DJobsPolling) and shows EVERY active job for this
            // asset+version. The main content below always renders the current
            // state (existing model or the generate form) so the user can fire
            // additional parallel jobs while others run — we no longer block the
            // whole tab on a single in-flight job.
            this._start3DJobsPolling();

            // Check if 3D already exists for current version — show it regardless of deployment status
            try {
                const ver = this._currentVersion || 1;
                const glbUrl = `/api/gallery/${encodeURIComponent(meta.id)}/3d/${ver}`;
                // Resolve THIS version's default 3D variant (a 2D version can hold
                // several; the switcher in _render3DComplete exposes the rest).
                const existing3D = this._default3DVariant(meta, ver);
                if (existing3D) {
                    this._render3DComplete(container, {
                        download_url: existing3D.glb_url || glbUrl,
                        file_size: existing3D.size_bytes || 0,
                        vertices: existing3D.vertices || 0,
                        faces: existing3D.faces || 0,
                        created_at: existing3D.created_at || null,
                        pipeline: existing3D.pipeline || null,
                        params: existing3D.params || null,
                    });
                    return;
                }
                // Fallback: check if GLB file exists on disk
                try {
                    const checkResp = await fetch(glbUrl, { method: 'GET', headers: { 'Range': 'bytes=0-0' } });
                    if (checkResp.ok || checkResp.status === 206) {
                        this._render3DComplete(container, {
                            download_url: glbUrl,
                            file_size: parseInt(checkResp.headers.get('content-range')?.split('/')?.pop() || '0'),
                            vertices: 0,
                            faces: 0,
                        });
                        return;
                    }
                } catch {}

                // No existing 3D model — check if generation is available (model deployed)
                const availability = await API.threeD.check();
                if (!availability || !availability.available) {
                    container.innerHTML = `
                        <div class="text-center py-8 space-y-3">
                            <p class="text-brand-text-muted">${t('asset_viewer.three_d_not_deployed')}</p>
                            <button class="btn btn-sm btn-secondary av-3d-open-settings">${t('asset_viewer.three_d_open_settings')}</button>
                        </div>`;
                    container.querySelector('.av-3d-open-settings')?.addEventListener('click', () => {
                        this.close();
                        window.ModelSettings?.open?.('custom-models');
                    });
                    return;
                }

                // Fetch deployed instances for the model chooser (best-effort —
                // the form works with an empty list, falling back to the
                // default/newest endpoint server-side).
                let instances = [];
                try {
                    const resp = await API.threeD.instances();
                    instances = (resp?.instances || []).filter(i => i.available);
                } catch {}

                // Show generation form (with instance chooser when >1 deployed)
                this._render3DForm(container, instances);
            } catch (err) {
                container.innerHTML = `<p class="text-red-400 text-center py-8">${t('asset_viewer.three_d_failed')}: ${this._esc(err.message)}</p>`;
            }
        },

        _render3DForm(container, instances = []) {
            // Model chooser — only shown when more than one TripoSG instance is
            // deployed (mirrors the Image Studio model chooser). With 0 or 1
            // instance there's nothing to choose, so the server default is used.
            const showChooser = Array.isArray(instances) && instances.length > 1;
            const chooserHtml = showChooser ? `
                    <div>
                        <label class="text-xs text-brand-text-muted mb-1 block">${t('asset_viewer.three_d_model')}</label>
                        <select id="av-3d-model" class="input text-sm w-full max-w-xs">
                            ${instances.map((inst, i) => {
                                const ptype = inst.pipeline_type === 'trellis2_full'
                                    ? t('asset_viewer.three_d_pipe_trellis2_full')
                                    : t('asset_viewer.three_d_pipe_triposg');
                                const inst_t = inst.instance_type ? ` · ${this._esc(inst.instance_type.replace('ml.', ''))}` : '';
                                const warming = inst.model_ready ? '' : ' · ' + t('asset_viewer.three_d_model_warming');
                                return `<option value="${this._esc(inst.model_key)}" ${i === 0 ? 'selected' : ''}>${this._esc(ptype)}${inst_t}${warming}</option>`;
                            }).join('')}
                        </select>
                        <p class="text-[9px] text-brand-text-dim mt-1 max-w-xs">${t('asset_viewer.three_d_model_hint')}</p>
                    </div>
            ` : '';

            // License / consent panel — shown for whichever pipeline is selected
            // (or the single deployed one). Informational: the binding acceptance
            // happened at DEPLOY time; here we surface it + confirm it's on record.
            const licensePanelHtml = `<div id="av-3d-license" class="flex-1 min-w-[16rem] rounded-lg border border-brand-border bg-brand-bg/40 p-3 text-[11px] space-y-1 hidden"></div>`;

            // Save-as choice: only when a 3D model ALREADY exists for this
            // version — i.e. this is a regeneration. Lets the user replace the
            // version's default or keep the new result as a side variant
            // (different pipeline / config) alongside it. First-ever 3D skips this.
            const ver = this._currentVersion || 1;
            const hasExisting3D = !!(this._meta?.three_d?.[`v${ver}`]?.variants?.length
                || this._meta?.three_d_versions?.some(v => v.version === ver));
            const saveAsHtml = hasExisting3D ? `
                    <div class="flex-1 min-w-[16rem] rounded-lg border border-brand-border bg-brand-bg/40 p-3">
                        <label class="text-xs text-brand-text-muted mb-2 block">${t('asset_viewer.three_d_saveas_title')}</label>
                        <label class="flex items-start gap-2 mb-1.5 cursor-pointer">
                            <input type="radio" name="av-3d-saveas" value="default" checked class="mt-0.5" />
                            <span class="text-[11px]"><span class="font-medium">${t('asset_viewer.three_d_saveas_replace')}</span><br><span class="text-brand-text-dim">${t('asset_viewer.three_d_saveas_replace_hint')}</span></span>
                        </label>
                        <label class="flex items-start gap-2 cursor-pointer">
                            <input type="radio" name="av-3d-saveas" value="variant" class="mt-0.5" />
                            <span class="text-[11px]"><span class="font-medium">${t('asset_viewer.three_d_saveas_variant')}</span><br><span class="text-brand-text-dim">${t('asset_viewer.three_d_saveas_variant_hint')}</span></span>
                        </label>
                    </div>
            ` : '';

            // The EXACT background-removed image that will go to the 3D pipeline,
            // shown on the right so the user is crystal-clear on the pipeline input
            // without opening Review. Server caches the cutout (removes BG once).
            const previewUrl = API.threeD.sourcePreviewUrl(this._item?.id, this._currentVersion || 1) + `?t=${Date.now()}`;
            const isSubject = (this._meta?.asset_type === 'character' || this._meta?.asset_type === 'game_asset');
            const previewPanelHtml = `
                <div class="w-full lg:w-64 lg:flex-shrink-0 space-y-2">
                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider">${t('asset_viewer.three_d_preview_title')}</p>
                    <div class="preview-checkerboard rounded-lg overflow-hidden border border-brand-border flex items-center justify-center" style="height: 220px;">
                        <img id="av-3d-preview-img" src="${previewUrl}" class="w-full h-full object-contain" alt="3D source" />
                    </div>
                    <p class="text-[9px] text-brand-text-dim">${t('asset_viewer.three_d_preview_note')}</p>
                    ${isSubject ? `
                    <!-- Improve the Source sits WITH the image it acts on (most intuitive
                         placement) — the sole instance; not duplicated in the button row. -->
                    <button id="av-3d-review" class="btn btn-sm bg-cyan-600 hover:bg-cyan-500 text-white w-full flex items-center justify-center gap-1.5">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"/></svg>
                        <span>${t('asset_viewer.three_d_improve_btn')}</span>
                    </button>
                    <p id="av-3d-review-status" class="text-[9px] text-brand-text-dim">${t('asset_viewer.three_d_review_hint')}</p>` : ''}
                </div>`;

            container.innerHTML = `
                <div class="flex flex-col lg:flex-row gap-5">
                  <!-- LEFT: controls -->
                  <div class="flex-1 min-w-0 space-y-4">
                    <p class="text-[10px] text-brand-text-dim">${t('asset_viewer.three_d_version_note')}</p>
                    ${chooserHtml}
                    <!-- License + save-as choice sit SIDE-BY-SIDE (wrap on narrow
                         widths) to keep the form compact instead of stacking tall. -->
                    <div class="flex flex-wrap items-stretch gap-3">
                        ${licensePanelHtml}
                        ${saveAsHtml}
                    </div>

                    <!-- Quality preset (real specs: face/vertex detail, not bogus seconds) -->
                    <div>
                        <label class="text-xs text-brand-text-muted mb-1 block">${t('asset_viewer.three_d_quality')}</label>
                        <select id="av-3d-quality" class="input text-sm w-full max-w-xs">
                            <option value="fast">${t('asset_viewer.three_d_quality_fast')}</option>
                            <option value="standard">${t('asset_viewer.three_d_quality_standard')}</option>
                            <option value="high" selected>${t('asset_viewer.three_d_quality_high')}</option>
                        </select>
                        <p id="av-3d-estimate" class="text-[10px] text-brand-text-dim mt-1.5"></p>
                    </div>

                    <!-- Advanced (collapsible) -->
                    <details class="border border-brand-border rounded-lg">
                        <summary class="px-3 py-2 text-xs text-brand-text-muted cursor-pointer hover:text-brand-text">${t('asset_viewer.three_d_advanced')}</summary>
                        <!-- Two-column grid: pairs the fields so the panel is ~half
                             the height (uses the previously-empty right side). -->
                        <div class="px-3 pb-3 pt-2 grid grid-cols-2 gap-x-4 gap-y-3">
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('asset_viewer.three_d_steps')}</label>
                                <div class="flex items-center gap-2">
                                    <input id="av-3d-steps" type="range" min="20" max="100" value="50" class="flex-1 min-w-0" />
                                    <span id="av-3d-steps-label" class="text-[10px] text-brand-text-muted w-6 text-right">50</span>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('asset_viewer.three_d_guidance')}</label>
                                <div class="flex items-center gap-2">
                                    <input id="av-3d-guidance" type="range" min="1" max="20" step="0.5" value="7.5" class="flex-1 min-w-0" />
                                    <span id="av-3d-guidance-label" class="text-[10px] text-brand-text-muted w-6 text-right">7.5</span>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('asset_viewer.three_d_faces')}</label>
                                <select id="av-3d-faces" class="input text-xs w-full">
                                    <option value="0">${t('asset_viewer.three_d_faces_unlimited')}</option>
                                    <option value="50000">50,000</option>
                                    <option value="100000" selected>100,000</option>
                                    <option value="200000">200,000</option>
                                    <option value="300000">300,000</option>
                                </select>
                                <p class="text-[9px] text-brand-text-dim mt-1">${t('asset_viewer.three_d_faces_hint')}</p>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('asset_viewer.three_d_depth')}</label>
                                <select id="av-3d-depth" class="input text-xs w-full">
                                    <option value="128">${t('asset_viewer.three_d_depth_low')}</option>
                                    <option value="256" selected>${t('asset_viewer.three_d_depth_medium')}</option>
                                    <option value="512">${t('asset_viewer.three_d_depth_high')}</option>
                                </select>
                            </div>
                            <div class="col-span-2">
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('asset_viewer.three_d_seed')}</label>
                                <input id="av-3d-seed" type="number" class="input text-xs w-full max-w-xs" placeholder="${t('asset_viewer.three_d_seed_placeholder')}" />
                                <p class="text-[9px] text-brand-text-dim mt-1">${t('asset_viewer.three_d_seed_hint')}</p>
                            </div>
                        </div>
                    </details>

                    <!-- Generate — the ONE place a 3D job is triggered. "Improve the
                         Source" lives with the preview image (right panel), so this row
                         is just the single Generate action, matching the other studios. -->
                    <div class="flex items-center gap-3 flex-wrap">
                        <button id="av-3d-generate" class="btn btn-primary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
                            </svg>
                            <span>${t('asset_viewer.three_d_generate')}</span>
                        </button>
                    </div>
                    <p class="text-[10px] text-brand-text-dim">${t('asset_viewer.three_d_async_note')}</p>
                  </div>
                  <!-- RIGHT: exact pipeline-input preview (bg-removed). -->
                  ${previewPanelHtml}
                </div>
            `;

            // Quality preset auto-fills advanced fields. Specs are REAL (face/
            // vertex targets + octree depth); the live estimate line below shows
            // accurate time + cost derived from the deployed backend/instance.
            // 0 faces = no decimation cap (full mesh, ~1M after the safety cap).
            const qualityPresets = {
                fast: { steps: 30, guidance: 5, faces: 100000, depth: 256, vtx: 50000 },
                standard: { steps: 50, guidance: 7.5, faces: 300000, depth: 256, vtx: 150000 },
                // High: full detail (octree 9, no decimation cap → ~1M faces /
                // ~500K verts after the texture-safe ceiling). Matches Hunyuan-class.
                high: { steps: 80, guidance: 12, faces: 0, depth: 512, vtx: 500000 },
            };

            const qualitySelect = container.querySelector('#av-3d-quality');
            const stepsInput = container.querySelector('#av-3d-steps');
            const stepsLabel = container.querySelector('#av-3d-steps-label');
            const guidanceInput = container.querySelector('#av-3d-guidance');
            const guidanceLabel = container.querySelector('#av-3d-guidance-label');
            const facesSelect = container.querySelector('#av-3d-faces');
            const depthSelect = container.querySelector('#av-3d-depth');
            const estimateEl = container.querySelector('#av-3d-estimate');
            const modelSelect = container.querySelector('#av-3d-model');

            // Resolve the targeted instance (chooser value, else first available)
            // to derive the live time/cost estimate from registry-backed fields.
            const _selectedInstance = () => {
                if (!Array.isArray(instances) || !instances.length) return null;
                const key = modelSelect?.value;
                return (key && instances.find(i => i.model_key === key)) || instances[0];
            };
            const _fmtTime = (s) => {
                if (!s) return '~?';
                const m = Math.round(s / 60);
                return m >= 1 ? `~${m} min` : `~${s}s`;
            };
            const updateEstimate = () => {
                if (!estimateEl) return;
                const inst = _selectedInstance();
                const facesVal = facesSelect ? parseInt(facesSelect.value || '0') : 0;
                const facesTxt = facesVal === 0
                    ? t('asset_viewer.three_d_est_fullmesh')
                    : `~${facesVal.toLocaleString()} ${t('asset_viewer.three_d_est_faces')}`;
                let tail = '';
                if (inst) {
                    // Scale runtime (and thus cost) with the chosen quality — steps
                    // drive most of the diffusion time, so latency scales ~with the
                    // step count relative to the 'standard' preset the registry's
                    // typical_latency_seconds represents. Without this, fast and high
                    // showed the same estimate despite very different runtimes.
                    const STD_STEPS = qualityPresets.standard.steps;  // 50
                    const stepsVal = parseInt(stepsInput?.value, 10) || STD_STEPS;
                    const qMult = Math.max(0.4, Math.min(2.0, stepsVal / STD_STEPS));
                    const lat = inst.typical_latency_seconds
                        ? Math.round(inst.typical_latency_seconds * qMult) : 0;
                    const cost = inst.cost_per_hour_usd;
                    const timeTxt = _fmtTime(lat);
                    let costTxt = '';
                    if (lat && cost) {
                        const jobCost = (cost * lat / 3600);
                        costTxt = ` · ~$${jobCost.toFixed(2)}`;
                    }
                    const backend = inst.texture_backend ? ` · ${inst.texture_backend}` : '';
                    tail = ` · ${timeTxt}${costTxt}${backend}`;
                }
                estimateEl.textContent = `${facesTxt}${tail}`;
            };

            const applyPreset = () => {
                const preset = qualityPresets[qualitySelect?.value];
                if (!preset) return;
                if (stepsInput) { stepsInput.value = preset.steps; stepsLabel.textContent = preset.steps; }
                if (guidanceInput) { guidanceInput.value = preset.guidance; guidanceLabel.textContent = preset.guidance; }
                if (facesSelect) facesSelect.value = String(preset.faces);
                if (depthSelect) depthSelect.value = String(preset.depth);
                updateEstimate();
            };
            // License / consent panel: reflects the selected pipeline's license,
            // commercial status, and the deploy-time acceptance on record. No new
            // checkbox — we state "accepted on <date>" (or warn if not on record).
            const licenseEl = container.querySelector('#av-3d-license');
            const updateLicensePanel = () => {
                if (!licenseEl) return;
                const inst = _selectedInstance();
                if (!inst || !inst.license_name) { licenseEl.classList.add('hidden'); return; }
                const commercialBadge = inst.commercial === true
                    ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('asset_viewer.three_d_lic_commercial')}</span>`
                    : (inst.commercial === false
                        ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${t('asset_viewer.three_d_lic_noncommercial')}</span>`
                        : '');
                const acceptedLine = inst.license_accepted
                    ? `<p class="text-emerald-400/90">✓ ${t('asset_viewer.three_d_lic_accepted')}${inst.license_accepted_at ? ' · ' + window.formatTimestamp(inst.license_accepted_at) : ''}</p>`
                    : `<p class="text-amber-400/90">⚠ ${t('asset_viewer.three_d_lic_not_recorded')}</p>`;
                const link = inst.license_url
                    ? ` <a href="${this._esc(inst.license_url)}" target="_blank" rel="noopener" class="text-brand-accent underline">${t('asset_viewer.three_d_lic_view')}</a>`
                    : '';
                licenseEl.innerHTML = `
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-brand-text-muted">${t('asset_viewer.three_d_lic_label')}</span>
                        <span class="text-brand-text font-medium">${this._esc(inst.license_name)}</span>
                        ${commercialBadge}
                    </div>
                    ${acceptedLine}
                    <p class="text-brand-text-dim">${t('asset_viewer.three_d_lic_note')}${link}</p>`;
                licenseEl.classList.remove('hidden');
            };

            qualitySelect?.addEventListener('change', applyPreset);
            facesSelect?.addEventListener('change', updateEstimate);
            modelSelect?.addEventListener('change', () => { updateEstimate(); updateLicensePanel(); });
            updateLicensePanel();

            stepsInput?.addEventListener('input', () => { if (stepsLabel) stepsLabel.textContent = stepsInput.value; updateEstimate(); });
            guidanceInput?.addEventListener('input', () => { if (guidanceLabel) guidanceLabel.textContent = guidanceInput.value; });

            applyPreset();  // sync advanced fields + estimate to the default (High)

            // Generate button — always generates directly (source review is a
            // separate, explicit step via the Review button). This is the ONLY 3D
            // trigger; nothing else fires a job.
            container.querySelector('#av-3d-generate')?.addEventListener('click', () => this._submit3DGeneration());

            // Review source button — opens the review dialog (Extend / Fill until
            // satisfied), then returns to this form. Never triggers generation.
            const reviewBtn = container.querySelector('#av-3d-review');
            reviewBtn?.addEventListener('click', () => this._reviewSource(reviewBtn));
            this._update3DReviewStatus(container);
        },

        /** Reflect whether the current version's source has been reviewed this session. */
        _update3DReviewStatus(scope) {
            const el = scope?.querySelector?.('#av-3d-review-status');
            if (!el) return;
            const done = this._sourceApprovedVersion === (this._currentVersion || 1);
            el.textContent = done
                ? '✓ ' + t('asset_viewer.three_d_review_done')
                : t('asset_viewer.three_d_review_hint');
            el.classList.toggle('text-emerald-400', done);
            el.classList.toggle('text-brand-text-dim', !done);
        },

        /**
         * Open the source-review workflow (explicit, optional). Ensures the
         * background-removed cutout exists (sidecar cache — NOT a version), runs the
         * AI completeness check, then opens the self-contained review dialog where
         * the user iterates Extend / Fill until satisfied and clicks "Use this
         * image". All work goes through /prepare-source sidecars — NO 2D versions
         * are created. NEVER triggers 3D generation (that's the form's Generate btn).
         */
        async _reviewSource(reviewBtn) {
            if (reviewBtn?.disabled) return;
            if (reviewBtn) {
                reviewBtn.disabled = true;
                reviewBtn.innerHTML = `<span class="spinner-sm"></span> ${t('asset_viewer.three_d_src_removing_bg')}`;
            }
            // Re-sync to the true current version (backend truth) before reviewing.
            try {
                this._meta = await API.gallery.get(this._item.id);
                if (this._meta?.current_version) this._currentVersion = this._meta.current_version;
            } catch {}
            const version = this._currentVersion || 1;
            // Ensure the cutout exists + get an initial completeness verdict. One call
            // (op:'cutout') removes BG once (cached) and returns the analysis. Retry
            // once on a transient failure before falling back to "review & decide".
            let analysis = null;
            for (let attempt = 0; attempt < 2 && !(analysis && analysis.analyzed); attempt++) {
                try {
                    const r = await API.threeD.prepareSource({ asset_id: this._item?.id, version, op: 'cutout' });
                    analysis = r?.analysis || null;
                } catch (e) {
                    console.warn('[3D] source prepare/analysis failed (attempt ' + (attempt + 1) + ')', e);
                }
            }
            // Self-contained review dialog — stays open through every Extend/Fill,
            // shows progress in place, resolves only on "Use this image" / "Cancel".
            const approved = await this._showSourceReview(version, analysis || { analyzed: false });
            if (approved) this._sourceApprovedVersion = version;
            // Rebuild the form (refreshes the SOURCE preview to the prepared image).
            this._update3DContent();
        },

        async _submit3DGeneration() {
            const container = this._overlay?.querySelector('#av-3d-content');
            const btn = container?.querySelector('#av-3d-generate');
            if (!btn || btn.disabled) return;

            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-sm"></span> ${t('asset_viewer.three_d_generating')}`;

            // Re-sync to the TRUE current version before generating. The backend's
            // current_version is the single source of truth — it advances on every
            // edit (outpaint/inpaint/bg-removal) and asset.png always IS the current
            // version. The local _currentVersion counter is written by many paths and
            // can lag behind, so adopt the backend value to generate from the image
            // the user actually last accepted. Source review is a SEPARATE explicit
            // step (the Review button) — generation never triggers it, and this button
            // is the ONE place a 3D job starts (visible job-strip feedback).
            try {
                this._meta = await API.gallery.get(this._item.id);
                if (this._meta?.current_version) this._currentVersion = this._meta.current_version;
            } catch {}

            const payload = {
                asset_id: this._item?.id,
                version: this._currentVersion || undefined,
                // Chosen TripoSG instance (omitted when there's no chooser → server picks newest)
                model_key: container.querySelector('#av-3d-model')?.value || undefined,
                quality: container.querySelector('#av-3d-quality')?.value || 'standard',
                seed: parseInt(container.querySelector('#av-3d-seed')?.value, 10) || undefined,
                steps: parseInt(container.querySelector('#av-3d-steps')?.value, 10) || 50,
                guidance: parseFloat(container.querySelector('#av-3d-guidance')?.value) || 7.5,
                max_faces: parseInt(container.querySelector('#av-3d-faces')?.value, 10) || 0,
                mesh_resolution: parseInt(container.querySelector('#av-3d-depth')?.value, 10) || 256,
                // Replace the version's default 3D model, or keep this as a
                // side variant. Defaults to "default" (also when the selector is
                // absent, i.e. the first-ever 3D for this version).
                save_as: container.querySelector('input[name="av-3d-saveas"]:checked')?.value || 'default',
            };

            try {
                const result = await API.threeD.generate(payload);
                window.showToast?.(t('asset_viewer.three_d_pending'), 'info');
                // Parallel-jobs model: the new job joins the in-progress strip
                // (poller picks it up); the main content re-renders to the current
                // state (existing model or a fresh form) so another job can be
                // fired immediately. No full-panel takeover.
                this._start3DJobsPolling(true);
                this._update3DContent();
            } catch (err) {
                window.showToast?.(t('asset_viewer.three_d_failed') + ': ' + err.message, 'error');
                this._reset3DGenerateBtn(btn);
            }
        },

        /** Restore the Generate-3D button to its idle state. */
        _reset3DGenerateBtn(btn) {
            if (!btn) return;
            btn.disabled = false;
            btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg> <span>${t('asset_viewer.three_d_generate')}</span>`;
        },

        /**
         * Self-contained source-review dialog. Opens ONCE and STAYS OPEN through
         * every Extend/Fill iteration — each op runs against the sidecar-based
         * /prepare-source (NO 2D versions), shows an in-progress overlay in place,
         * then refreshes the shown image + verdict without closing. Resolves only on
         * "Use this image" (true) or "Cancel" (false). Fixes the old flow where the
         * dialog closed during the op and looked like it jumped to the gallery.
         *
         * Ops (all via API.threeD.prepareSource, keyed to `version`):
         *   extend  → outpaint the CUTOUT (never compounding) → re-strip → __source
         *   inpaint → fill/replace a masked region of the current source → __source
         *   reset   → drop __source, revert to the plain cutout
         */
        _showSourceReview(version, analysis) {
            return new Promise((resolve) => {
                const id = encodeURIComponent(this._item?.id);
                const srcUrlFor = () => API.threeD.sourcePreviewUrl(this._item?.id, version) + `?t=${Date.now()}`;

                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[130] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
                backdrop.innerHTML = `
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full p-5 space-y-4 max-h-[92vh] overflow-y-auto relative">
                        <div>
                            <h3 class="text-sm font-semibold text-brand-text">${t('asset_viewer.three_d_src_pv_confirm_title')}</h3>
                            <p id="av-sr-verdict" class="text-xs mt-1"></p>
                            <p class="text-[11px] text-brand-text-dim mt-1">${t('asset_viewer.three_d_src_pv_confirm_sub')} ${t('asset_viewer.three_d_src_pv_confirm_sub2')}</p>
                        </div>
                        <div class="preview-checkerboard rounded-lg overflow-hidden border border-brand-accent/40 flex items-center justify-center relative" style="height: 300px;">
                            <img id="av-sr-img" src="${srcUrlFor()}" class="w-full h-full object-contain" alt="3D source" crossorigin="anonymous" />
                            <canvas id="av-sr-mask" class="cursor-crosshair hidden" style="max-width:100%; max-height:300px;"></canvas>
                            <canvas id="av-sr-measure" class="absolute inset-0 w-full h-full pointer-events-none hidden"></canvas>
                        </div>
                        <div id="av-sr-stats" class="text-[10px] text-brand-text-muted flex flex-wrap items-center gap-x-4 gap-y-1 px-1 hidden"></div>

                        <!-- Fill / Replace panel (mask brush) — hidden until Fill is chosen. -->
                        <div id="av-sr-fill-panel" class="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 space-y-2 hidden">
                            <div class="flex items-center justify-between">
                                <p class="text-[11px] text-amber-400">${t('asset_viewer.three_d_src_pv_fix_hint')}</p>
                                <div class="flex items-center gap-2">
                                    <label class="text-[9px] text-brand-text-muted">${t('asset_viewer.brush_size')}</label>
                                    <input id="av-sr-brush" type="range" min="8" max="80" value="28" class="w-20" />
                                    <button class="av-sr-mask-clear text-[10px] text-brand-text-muted hover:text-brand-text underline">${t('asset_viewer.clear_mask')}</button>
                                </div>
                            </div>
                            <textarea id="av-sr-fill-prompt" rows="2" class="input text-xs w-full" placeholder="${t('asset_viewer.three_d_src_fix_ph')}"></textarea>
                        </div>

                        <!-- Extend panel (directions) — hidden until Extend is chosen. -->
                        <details id="av-sr-extend-panel" class="border border-brand-border rounded-lg hidden">
                            <summary class="px-3 py-2 text-[11px] text-brand-text-muted cursor-pointer">${t('asset_viewer.three_d_src_pv_adjust')}</summary>
                            <div class="px-3 pb-3 pt-1 space-y-2">
                                <div>
                                    <label class="text-[9px] text-brand-text-muted uppercase tracking-wider">${t('asset_viewer.three_d_src_prompt_label')}</label>
                                    <textarea id="av-sr-prompt" rows="2" class="input text-xs w-full" placeholder="${t('asset_viewer.three_d_src_prompt_ph')}"></textarea>
                                </div>
                                <div class="grid grid-cols-4 gap-2">
                                    ${['left','right','up','down'].map(dd => `
                                        <div><label class="text-[9px] text-brand-text-muted">${t('asset_viewer.outpaint_' + dd)}</label>
                                        <input id="av-sr-${dd}" type="number" min="0" max="2000" value="0" class="input text-xs w-full" /></div>`).join('')}
                                </div>
                                <p class="text-[9px] text-brand-text-dim">${t('asset_viewer.three_d_src_pv_extend_note')}</p>
                            </div>
                        </details>

                        <!-- Actions: Use this image · Extend · Fill/Replace -->
                        <div class="grid grid-cols-3 gap-2">
                            <button class="av-sr-use btn btn-sm bg-brand-accent hover:bg-brand-accent-hover text-white rounded-lg py-3 text-xs font-medium leading-tight">${t('asset_viewer.three_d_src_pv_approve')}</button>
                            <button class="av-sr-extend btn btn-sm btn-secondary rounded-lg py-3 text-xs font-medium leading-tight">${t('asset_viewer.three_d_src_pv_extend_it')}</button>
                            <button class="av-sr-fill btn btn-sm btn-secondary rounded-lg py-3 text-xs font-medium leading-tight">${t('asset_viewer.three_d_src_pv_fill')}</button>
                        </div>
                        <button class="av-sr-cancel text-[11px] text-brand-text-muted hover:text-red-400 w-full text-center">${t('asset_viewer.three_d_src_pv_cancel')}</button>

                        <!-- In-progress overlay — keeps the dialog OPEN with clear feedback
                             while an Extend/Fill runs (no close, no gallery jump). -->
                        <div id="av-sr-busy" class="absolute inset-0 rounded-xl bg-brand-surface/80 backdrop-blur-sm flex-col items-center justify-center gap-3" style="display:none;">
                            <div class="loading-spinner w-8 h-8 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                            <p id="av-sr-busy-text" class="text-xs text-brand-text"></p>
                        </div>
                    </div>`;

                const $ = (sel) => backdrop.querySelector(sel);
                const imgEl = $('#av-sr-img'), maskCanvas = $('#av-sr-mask');
                const measureCanvas = $('#av-sr-measure'), statsEl = $('#av-sr-stats');
                const fillPanel = $('#av-sr-fill-panel'), extendPanel = $('#av-sr-extend-panel');
                const useBtn = $('.av-sr-use'), extendBtn = $('.av-sr-extend'), fillBtn = $('.av-sr-fill');
                const busy = $('#av-sr-busy'), busyText = $('#av-sr-busy-text');
                let fillMode = false, maskWired = false, working = false;

                const done = (v) => { this._redrawMeasurement = null; backdrop.remove(); resolve(v); };
                const setBusy = (on, text) => {
                    working = on;
                    busy.style.display = on ? 'flex' : 'none';
                    if (text) busyText.textContent = text;
                    [useBtn, extendBtn, fillBtn].forEach(b => { if (b) b.disabled = on; });
                };
                const readDirs = () => {
                    const g = (dd) => { const n = parseInt($(`#av-sr-${dd}`)?.value || '0', 10); return Number.isFinite(n) ? Math.max(0, Math.min(2000, n)) : 0; };
                    return { left: g('left'), right: g('right'), up: g('up'), down: g('down') };
                };

                // Render the current verdict line from an analysis object.
                const renderVerdict = (a) => {
                    const analyzed = !!(a && a.analyzed);
                    const defect = (analyzed && a.complete === false) ? (a.defect === 'artifact' ? 'artifact' : 'cropped') : 'none';
                    const el = $('#av-sr-verdict');
                    if (!analyzed) el.innerHTML = `<span class="text-brand-text-muted">${t('asset_viewer.three_d_src_pv_unchecked')}</span>`;
                    else if (defect === 'none') el.innerHTML = `<span class="text-emerald-400">✓ ${t('asset_viewer.three_d_src_pv_good')}</span>`;
                    else el.innerHTML = `<span class="text-amber-400">⚠ ${this._esc(a.reason || t('asset_viewer.three_d_src_still'))}</span>`;
                    return { analyzed, defect };
                };

                // Refresh the shown image + measurement after a prepare op.
                const refreshImage = () => {
                    const url = srcUrlFor();
                    imgEl.src = url;
                    // Re-measure once the new image decodes.
                    this._wireMeasurement(backdrop, url, readDirs, { img: '#av-sr-img', measure: '#av-sr-measure', stats: '#av-sr-stats' });
                };

                // Seed the extend prompt/dirs from the (initial) analysis suggestion.
                const seedFromAnalysis = (a) => {
                    const sg = (a && a.suggest_outpaint) || {};
                    ['left', 'right', 'up', 'down'].forEach(dd => { const el = $(`#av-sr-${dd}`); if (el) el.value = sg[dd] || 0; });
                    const p = $('#av-sr-prompt'); if (p && a && a.outpaint_prompt) p.value = a.outpaint_prompt;
                };

                let lastAnalysis = analysis;
                const { defect: initialDefect } = renderVerdict(analysis);
                seedFromAnalysis(analysis);
                // Wire measurement (hidden until Extend). Draw once image decodes.
                this._wireMeasurement(backdrop, srcUrlFor(), readDirs, { img: '#av-sr-img', measure: '#av-sr-measure', stats: '#av-sr-stats' });

                // ── Fill (inpaint) mode toggle ──
                const enableFillMode = () => {
                    fillMode = true;
                    fillPanel.classList.remove('hidden');
                    extendPanel.classList.add('hidden');
                    measureCanvas.classList.add('hidden'); statsEl.classList.add('hidden');
                    imgEl.classList.add('hidden');
                    maskCanvas.classList.remove('hidden');
                    fillBtn.classList.add('bg-brand-accent', 'hover:bg-brand-accent-hover', 'text-white');
                    fillBtn.classList.remove('btn-secondary');
                    if (!maskWired) { this._wirePreviewMask(maskCanvas, imgEl.src, $('#av-sr-brush')); maskWired = true; }
                };
                const disableFillMode = () => {
                    fillMode = false; maskWired = false;
                    fillPanel.classList.add('hidden');
                    maskCanvas.classList.add('hidden'); imgEl.classList.remove('hidden');
                    fillBtn.classList.remove('bg-brand-accent', 'hover:bg-brand-accent-hover', 'text-white');
                    fillBtn.classList.add('btn-secondary');
                };

                $('.av-sr-mask-clear')?.addEventListener('click', () => {
                    if (maskCanvas?._baseImageData) maskCanvas.getContext('2d').putImageData(maskCanvas._baseImageData, 0, 0);
                });

                // ── Run a prepare op (extend/inpaint) IN PLACE, dialog stays open ──
                const runOp = async (payload, busyMsg) => {
                    if (working) return;
                    setBusy(true, busyMsg);
                    try {
                        const r = await API.threeD.prepareSource({ asset_id: this._item?.id, version, ...payload });
                        lastAnalysis = r?.analysis || lastAnalysis;
                        disableFillMode();
                        refreshImage();
                        renderVerdict(lastAnalysis);
                        seedFromAnalysis(lastAnalysis);
                    } catch (e) {
                        window.showToast?.(t('asset_viewer.three_d_src_failed') + (e.message ? ': ' + e.message : ''), 'error');
                    } finally {
                        setBusy(false);
                    }
                };

                // Extend: first click reveals the panel + ruler; with an amount set, runs.
                extendBtn.addEventListener('click', () => {
                    if (working) return;
                    if (fillMode) disableFillMode();
                    const dirs = readDirs();
                    if (!Object.values(dirs).some(v => v > 0)) {
                        extendPanel.classList.remove('hidden'); extendPanel.open = true;
                        this._showMeasurement(backdrop);
                        const downInput = $('#av-sr-down');
                        if (downInput && !parseInt(downInput.value, 10)) { downInput.value = 256; downInput.focus(); }
                        this._redrawMeasurement?.();
                        return;
                    }
                    runOp({ op: 'extend', ...dirs, prompt: $('#av-sr-prompt')?.value || '' },
                        t('asset_viewer.three_d_src_completing'));
                });
                // Live measurement redraw as the user tweaks amounts.
                ['left', 'right', 'up', 'down'].forEach(dd => {
                    $(`#av-sr-${dd}`)?.addEventListener('input', () => this._redrawMeasurement?.());
                });

                // Fill: first click enters mask mode; second (with a mask) runs.
                fillBtn.addEventListener('click', () => {
                    if (working) return;
                    if (!fillMode) { enableFillMode(); return; }
                    const m = this._extractMask(maskCanvas);
                    if (m.isEmpty) { window.showToast?.(t('asset_viewer.three_d_src_nomask'), 'warning'); return; }
                    runOp({ op: 'inpaint', mask: m.data, prompt: $('#av-sr-fill-prompt')?.value || '' },
                        t('asset_viewer.three_d_src_fixing'));
                });

                useBtn.addEventListener('click', () => { if (!working) done(true); });
                const cancel = () => { if (!working) done(false); };
                $('.av-sr-cancel').addEventListener('click', cancel);
                backdrop.addEventListener('click', (e) => { if (e.target === backdrop) cancel(); });

                document.body.appendChild(backdrop);
                // If the initial verdict says cropped, reveal the extend panel + ruler.
                if (initialDefect === 'cropped') {
                    extendPanel.classList.remove('hidden'); extendPanel.open = true;
                    this._showMeasurement(backdrop);
                }
            });
        },


        /**
         * Wire an inline mask-paint canvas over an image (reuses the same red-brush
         * + base-image-diff approach as the Edit tab, so _extractMask works on it).
         */
        _wirePreviewMask(canvas, imgUrl, brushSlider) {
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            let painting = false, brushSize = 28;
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                const maxW = 380, maxH = 300;
                const scale = Math.min(maxW / img.width, maxH / img.height, 1);
                canvas.width = img.width * scale;
                canvas.height = img.height * scale;
                canvas._imgScale = scale; canvas._imgW = img.width; canvas._imgH = img.height;
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                canvas._baseImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            };
            img.src = imgUrl;
            brushSlider?.addEventListener('input', () => { brushSize = parseInt(brushSlider.value, 10) || 28; });
            const paintAt = (x, y) => {
                ctx.globalCompositeOperation = 'source-over';
                ctx.fillStyle = 'rgba(255, 100, 100, 0.5)';
                ctx.beginPath(); ctx.arc(x, y, brushSize / 2, 0, Math.PI * 2); ctx.fill();
            };
            const pos = (e) => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) * (canvas.width / r.width), (e.clientY - r.top) * (canvas.height / r.height)]; };
            canvas.addEventListener('mousedown', (e) => { painting = true; paintAt(...pos(e)); });
            canvas.addEventListener('mousemove', (e) => { if (painting) paintAt(...pos(e)); });
            window.addEventListener('mouseup', () => { painting = false; });
        },

        /**
         * Measurement overlay for the confirm dialog: reads the source image's alpha
         * silhouette to report its true pixel size, how much of the frame the subject
         * fills, and the transparent margin (px) on each edge — then draws a ruler,
         * per-edge margin callouts, and a live band previewing where the entered
         * extension will land. Fully generic: it measures whatever silhouette exists,
         * so it works for any character/object/asset, not just the test soldier.
         * `readDirs()` returns the current {left,right,up,down} extension in px.
         */
        _wireMeasurement(backdrop, imgUrl, readDirs) {
            const overlay = backdrop.querySelector('#av-sr-measure');
            const statsEl = backdrop.querySelector('#av-sr-stats');
            const wrap = overlay?.parentElement;   // the fixed-height preview box
            if (!overlay || !wrap) return;
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                const W = img.naturalWidth, H = img.naturalHeight;
                // Measure the alpha silhouette (bbox + per-edge transparent margin).
                let bbox = null, hasAlpha = false;
                try {
                    const s = Math.min(1, 256 / Math.max(W, H));  // downscale for a fast scan
                    const sw = Math.max(1, Math.round(W * s)), sh = Math.max(1, Math.round(H * s));
                    const c = document.createElement('canvas'); c.width = sw; c.height = sh;
                    const cx = c.getContext('2d', { willReadFrequently: true });
                    cx.drawImage(img, 0, 0, sw, sh);
                    const px = cx.getImageData(0, 0, sw, sh).data;
                    let minX = sw, minY = sh, maxX = -1, maxY = -1, transparent = 0, total = sw * sh;
                    for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) {
                        const a = px[(y * sw + x) * 4 + 3];
                        if (a <= 16) { transparent++; continue; }
                        if (x < minX) minX = x; if (x > maxX) maxX = x;
                        if (y < minY) minY = y; if (y > maxY) maxY = y;
                    }
                    hasAlpha = (transparent / total) > 0.02 && maxX >= 0;  // a real cutout
                    if (hasAlpha) {
                        // Scale the small-scan bbox back up to true image pixels.
                        bbox = {
                            left: Math.round(minX / s), right: Math.round(W - (maxX + 1) / s),
                            top: Math.round(minY / s), bottom: Math.round(H - (maxY + 1) / s),
                            w: Math.round((maxX - minX + 1) / s), h: Math.round((maxY - minY + 1) / s),
                        };
                    }
                } catch { /* cross-origin / decode issue → ruler only, no margins */ }
                overlay._img = { W, H, bbox, hasAlpha };

                // Stats line.
                if (statsEl) {
                    const pct = bbox
                        ? `${Math.round(100 * bbox.w / W)}% × ${Math.round(100 * bbox.h / H)}%`
                        : '—';
                    const marginChip = (edge, val) => {
                        const cropped = val <= 1;
                        const cls = cropped ? 'text-amber-400' : 'text-brand-text';
                        const tag = cropped ? ` ${t('asset_viewer.three_d_measure_cropped')}` : '';
                        return `<span class="${cls}">${t('asset_viewer.outpaint_' + edge)} ${val}px${tag}</span>`;
                    };
                    let html = `<span><span class="text-brand-text">${t('asset_viewer.three_d_measure_size')}</span> ${W}×${H}px</span>`;
                    if (bbox) {
                        html += `<span><span class="text-brand-text">${t('asset_viewer.three_d_measure_fill')}</span> ${pct}</span>`;
                        html += `<span class="flex items-center gap-2"><span class="text-brand-text">${t('asset_viewer.three_d_measure_margins')}:</span> `
                            + ['up', 'down', 'left', 'right'].map(e => marginChip(e, bbox[{ up: 'top', down: 'bottom', left: 'left', right: 'right' }[e]])).join(' · ')
                            + `</span>`;
                        html += `<span id="av-sr-newsize" class="text-brand-accent"></span>`;
                        statsEl.innerHTML = `<div class="flex flex-wrap items-center gap-x-4 gap-y-1">${html}</div>`
                            + `<div class="w-full text-brand-text-dim mt-0.5">${t('asset_viewer.three_d_measure_hint')}</div>`;
                    } else {
                        statsEl.innerHTML = `<div class="flex flex-wrap items-center gap-x-4 gap-y-1">${html}`
                            + `<span id="av-sr-newsize" class="text-brand-accent"></span></div>`
                            + `<div class="w-full text-brand-text-dim mt-0.5">${t('asset_viewer.three_d_measure_nobg')}</div>`;
                    }
                }
                // Draw only when the overlay is actually shown — it stays hidden on
                // the plain confirm view and is revealed when the user chooses Extend.
                this._redrawMeasurement = () => {
                    if (overlay.classList.contains('hidden')) return;
                    this._drawMeasurement(overlay, wrap, readDirs, backdrop);
                };
                this._redrawMeasurement();
            };
            img.src = imgUrl;
        },

        /** Reveal the measurement ruler/overlay + stats (called when the user opts to
         *  Extend, so the plain confirm view isn't cluttered by dimensions upfront). */
        _showMeasurement(backdrop) {
            backdrop.querySelector('#av-sr-measure')?.classList.remove('hidden');
            backdrop.querySelector('#av-sr-stats')?.classList.remove('hidden');
            this._redrawMeasurement?.();
        },

        /**
         * Draw the ruler + margin callouts + live extension band onto the overlay
         * canvas. Everything is laid out in the FUTURE-canvas coordinate space (the
         * current image plus the entered extension on each side), so the band shows
         * exactly where new pixels go and the ruler ticks read true pixels.
         */
        _drawMeasurement(overlay, wrap, readDirs, backdrop) {
            const meta = overlay._img;
            if (!meta) return;
            const { W, H, bbox } = meta;
            const d = readDirs();
            const rect = wrap.getBoundingClientRect();
            // The dialog may not be laid out yet (cached image → onload before the
            // dialog is in the DOM). Retry next frame until the box has a real size.
            if (rect.width < 2 || rect.height < 2) {
                requestAnimationFrame(() => this._redrawMeasurement && this._redrawMeasurement());
                return;
            }
            const dpr = window.devicePixelRatio || 1;
            overlay.width = Math.round(rect.width * dpr);
            overlay.height = Math.round(rect.height * dpr);
            const ctx = overlay.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, rect.width, rect.height);

            // The visible <img> renders the picture via HTML (reliable). We annotate
            // OVER it, matching its object-contain placement inside the box: the image
            // is centered and scaled to fit, leaving letterbox margins we draw the
            // extension bands into. imgScale = displayed px per image px.
            const imgScale = Math.min(rect.width / W, rect.height / H);
            const imgW = W * imgScale, imgH = H * imgScale;
            const imgX = (rect.width - imgW) / 2, imgY = (rect.height - imgH) / 2;
            const toX = (ix) => imgX + ix * imgScale;
            const toY = (iy) => imgY + iy * imgScale;

            // Extension bands (where NEW pixels will be generated) — drawn in the
            // letterbox space just outside the image edge, clamped to the box.
            ctx.fillStyle = 'rgba(124, 104, 238, 0.28)';
            const bandUp = Math.min(d.top * imgScale, imgY);
            const bandDown = Math.min(d.down * imgScale, rect.height - (imgY + imgH));
            const bandLeft = Math.min(d.left * imgScale, imgX);
            const bandRight = Math.min(d.right * imgScale, rect.width - (imgX + imgW));
            if (d.top > 0) ctx.fillRect(imgX, imgY - bandUp, imgW, bandUp);
            if (d.down > 0) ctx.fillRect(imgX, imgY + imgH, imgW, bandDown);
            if (d.left > 0) ctx.fillRect(imgX - bandLeft, imgY, bandLeft, imgH);
            if (d.right > 0) ctx.fillRect(imgX + imgW, imgY, bandRight, imgH);

            // Current-image frame.
            ctx.strokeStyle = 'rgba(160,170,190,0.85)'; ctx.lineWidth = 1;
            ctx.strokeRect(imgX + 0.5, imgY + 0.5, imgW, imgH);

            // Subject bbox (if a silhouette was measured) — dashed emerald box.
            if (bbox) {
                ctx.save();
                ctx.strokeStyle = 'rgba(52, 211, 153, 0.9)'; ctx.setLineDash([4, 3]); ctx.lineWidth = 1.5;
                ctx.strokeRect(toX(bbox.left) + 0.5, toY(bbox.top) + 0.5, bbox.w * imgScale, bbox.h * imgScale);
                ctx.restore();
            }

            // Ruler ticks along the top + left edges of the IMAGE (true image pixels).
            ctx.fillStyle = 'rgba(210,215,230,0.9)'; ctx.strokeStyle = 'rgba(150,158,178,0.7)';
            ctx.lineWidth = 1; ctx.font = '9px ui-monospace, monospace';
            const step = W > 1400 ? 512 : 256;
            ctx.textAlign = 'center'; ctx.textBaseline = 'top';
            for (let px = 0; px <= W; px += step) {
                const x = toX(px);
                ctx.beginPath(); ctx.moveTo(x, toY(0)); ctx.lineTo(x, toY(0) + 6); ctx.stroke();
                ctx.fillText(String(px), x, toY(0) + 7);
            }
            ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
            for (let py = 0; py <= H; py += step) {
                const y = toY(py);
                ctx.beginPath(); ctx.moveTo(toX(0), y); ctx.lineTo(toX(0) + 6, y); ctx.stroke();
                ctx.fillText(String(py), toX(0) + 8, y);
            }

            // Live "new canvas size" readout in the stats line.
            const fW = W + d.left + d.right, fH = H + d.top + d.down;
            const newSizeEl = backdrop.querySelector('#av-sr-newsize');
            if (newSizeEl) {
                newSizeEl.textContent = (d.left || d.right || d.top || d.down)
                    ? `${t('asset_viewer.three_d_measure_newsize')} ${fW}×${fH}px`
                    : '';
            }
        },


        _render3DPending(container, jobId) {
            container.innerHTML = `
                <div class="text-center py-8 space-y-4">
                    <div class="loading-spinner w-6 h-6 border-2 border-brand-accent/20 border-t-brand-accent rounded-full mx-auto"></div>
                    <div>
                        <p class="text-brand-text">${t('asset_viewer.three_d_pending_title')}</p>
                        <p class="text-[10px] text-brand-text-muted mt-1">${t('asset_viewer.three_d_pending_subtitle')}</p>
                    </div>
                    <p class="text-[9px] text-brand-text-dim font-mono">${t('asset_viewer.three_d_job_id')}: ${this._esc(jobId)}</p>
                </div>`;
        },

        /**
         * Poll ALL in-progress 3D jobs for the current asset+version and render a
         * compact in-progress strip (#av-3d-jobs). Supports multiple parallel jobs
         * (e.g. TripoSG + TRELLIS.2 at once). Single source of truth = the backend
         * /active-all route, so it survives page reloads. When the set of active
         * jobs shrinks (a job finished), it refreshes the main content + variant
         * switcher so the new model appears. Idempotent — one timer per viewer.
         */
        _start3DJobsPolling(force) {
            if (this._3dJobsTimer && !force) return;
            const tick = async () => {
                const meta = this._meta;
                const strip = this._overlay?.querySelector('#av-3d-jobs');
                if (!meta || !strip) return;
                let jobs = [];
                try {
                    const r = await API.threeD.activeJobs(meta.id, this._currentVersion || 1);
                    jobs = r?.jobs || [];
                } catch { return; }
                const prevCount = this._3dActiveCount || 0;
                this._3dActiveCount = jobs.length;
                this._render3DJobsStrip(strip, jobs);
                // A job just finished → pull fresh metadata + re-render content so
                // the new variant shows, and refresh the variant switcher.
                if (jobs.length < prevCount) {
                    try { this._meta = await API.gallery.get(meta.id); } catch {}
                    window.Gallery?.refresh?.();
                    this._update3DContent();
                }
                // No jobs left → stop polling.
                if (jobs.length === 0) this._stop3DJobsPolling();
            };
            this._stop3DJobsPolling();
            this._3dJobsTimer = setInterval(tick, 5000);
            tick();  // immediate first pass
        },

        _stop3DJobsPolling() {
            if (this._3dJobsTimer) { clearInterval(this._3dJobsTimer); this._3dJobsTimer = null; }
        },

        _render3DJobsStrip(strip, jobs) {
            if (!jobs.length) { strip.classList.add('hidden'); strip.innerHTML = ''; return; }
            strip.classList.remove('hidden');
            strip.innerHTML = `
                <div class="rounded-lg border border-brand-accent/30 bg-brand-accent/5 px-3 py-2">
                    <div class="flex items-center gap-2 mb-1.5">
                        <div class="loading-spinner w-3.5 h-3.5 border-2 border-brand-accent/30 border-t-brand-accent rounded-full"></div>
                        <span class="text-[10px] text-brand-text-muted uppercase tracking-wider">${t('asset_viewer.three_d_jobs_running')} (${jobs.length})</span>
                    </div>
                    <div class="space-y-1">
                        ${jobs.map(j => `
                            <div class="flex items-center justify-between gap-2 text-[11px]">
                                <span class="text-brand-text">${this._esc(j.label || j.model_key || '3D')}</span>
                                <span class="text-[9px] font-mono text-brand-text-dim">${this._esc(j.status)} · ${this._esc(j.job_id)}</span>
                            </div>`).join('')}
                    </div>
                </div>`;
        },

        _render3DComplete(container, data) {
            const fileSize = data.file_size ? this._formatBytes(data.file_size) : '—';
            const glbUrl = data.download_url || '#';
            const pl = data.pipeline || {};
            const prm = data.params || {};
            // Build the "models & tools used" rows from the persisted pipeline
            // block (gallery metadata). Only render rows we actually have.
            const _toolRows = [];
            if (pl.geometry_model) _toolRows.push([t('asset_viewer.three_d_geometry_model'), pl.geometry_model]);
            if (pl.texture_label || pl.texture_backend) _toolRows.push([t('asset_viewer.three_d_texture_model'), pl.texture_label || pl.texture_backend]);
            _toolRows.push([t('asset_viewer.three_d_output_type'),
                pl.has_pbr ? t('asset_viewer.three_d_pbr_textured') : t('asset_viewer.three_d_albedo_textured')]);
            if (pl.instance_type) _toolRows.push([t('asset_viewer.three_d_instance'), pl.instance_type.replace('ml.', '')]);
            if (prm.octree_depth) _toolRows.push([t('asset_viewer.three_d_mesh_detail'), `octree ${prm.octree_depth}`]);
            if (prm.steps) _toolRows.push([t('asset_viewer.three_d_diffusion_steps'), String(prm.steps)]);
            if (prm.seed !== undefined && prm.seed !== null) _toolRows.push([t('asset_viewer.three_d_seed'), String(prm.seed)]);
            // License provenance (persisted from the deploy-time acceptance).
            if (pl.license_name) {
                const commTxt = pl.commercial === true ? ` (${t('asset_viewer.three_d_lic_commercial')})`
                    : (pl.commercial === false ? ` (${t('asset_viewer.three_d_lic_noncommercial')})` : '');
                _toolRows.push([t('asset_viewer.three_d_lic_label'), pl.license_name + commTxt]);
            }
            if (pl.license_accepted_at) _toolRows.push([t('asset_viewer.three_d_lic_accepted_col'), window.formatTimestamp(pl.license_accepted_at)]);
            const toolsHtml = _toolRows.length ? `
                <div class="rounded-lg border border-brand-border/40 bg-white/[0.02] px-4 py-3">
                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-2">${t('asset_viewer.three_d_pipeline_title')}</p>
                    <div class="grid grid-cols-2 gap-x-6 gap-y-1.5">
                        ${_toolRows.map(([k, v]) => `
                            <div class="flex items-center justify-between gap-2 text-[11px]">
                                <span class="text-brand-text-muted">${k}</span>
                                <span class="font-medium text-right truncate" title="${this._esc(String(v))}">${this._esc(String(v))}</span>
                            </div>`).join('')}
                    </div>
                </div>` : '';
            // Parallel jobs: Regenerate is ALWAYS available — firing another job
            // adds it to the in-progress strip rather than blocking the view.
            const regenBtnClass = 'btn btn-sm btn-secondary';
            const regenBtnLabel = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> ${t('asset_viewer.three_d_regenerate')}`;
            container.innerHTML = `
                <div class="space-y-3">
                    <!-- Variant switcher — populated async when a version
                         has >1 3D variant (different pipeline / deployment / config). -->
                    <div id="av-3d-variants" class="hidden"></div>
                    <div class="relative rounded-lg border border-brand-border overflow-hidden bg-gradient-to-b from-gray-800 to-gray-900" style="height: 460px;">
                        <model-viewer id="av-3d-viewer"
                            src="${glbUrl}?t=${Date.now()}"
                            alt="3D Model"
                            camera-controls
                            touch-action="pan-y"
                            auto-rotate
                            shadow-intensity="0.3"
                            exposure="2"
                            environment-image="neutral"
                            tone-mapping="commerce"
                            min-camera-orbit="auto auto 0.5m"
                            max-camera-orbit="auto auto 10m"
                            interpolation-decay="100"
                            style="width: 100%; height: 100%; --poster-color: transparent; background: linear-gradient(160deg, #2a2d35 0%, #1a1d25 100%);"
                        ></model-viewer>
                        <!-- Viewer controls overlay -->
                        <div class="absolute bottom-2 right-2 flex gap-1">
                            <button id="av-3d-zoom-in" class="w-7 h-7 rounded bg-black/50 hover:bg-black/70 flex items-center justify-center text-white text-sm" title="Zoom In">+</button>
                            <button id="av-3d-zoom-out" class="w-7 h-7 rounded bg-black/50 hover:bg-black/70 flex items-center justify-center text-white text-sm" title="Zoom Out">−</button>
                            <button id="av-3d-reset" class="w-7 h-7 rounded bg-black/50 hover:bg-black/70 flex items-center justify-center text-white" title="Reset View">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
                            </button>
                            <button id="av-3d-autorotate" class="w-7 h-7 rounded bg-brand-accent/60 hover:bg-brand-accent/80 flex items-center justify-center text-white" title="Toggle Auto-Rotate">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="grid grid-cols-4 gap-3 text-center">
                        <div>
                            <p class="text-[10px] text-brand-text-muted uppercase">${t('asset_viewer.three_d_file_size')}</p>
                            <p class="font-medium">${fileSize}</p>
                        </div>
                        <div>
                            <p class="text-[10px] text-brand-text-muted uppercase">${t('asset_viewer.three_d_vertices')}</p>
                            <p class="font-medium">${data.vertices ? data.vertices.toLocaleString() : '—'}</p>
                        </div>
                        <div>
                            <p class="text-[10px] text-brand-text-muted uppercase">${t('asset_viewer.three_d_faces_count')}</p>
                            <p class="font-medium">${data.faces ? data.faces.toLocaleString() : '—'}</p>
                        </div>
                        <div>
                            <p class="text-[10px] text-brand-text-muted uppercase">${t('asset_viewer.three_d_created')}</p>
                            <p class="font-medium text-[11px]">${data.created_at ? window.formatTimestamp(data.created_at) : '—'}</p>
                        </div>
                    </div>
                    ${toolsHtml}
                    <div class="flex items-center justify-center gap-3">
                        <a id="av-3d-download" href="${glbUrl}" download class="btn btn-primary btn-sm inline-flex items-center gap-2">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            ${t('asset_viewer.three_d_download')}
                        </a>
                        <button id="av-3d-regenerate" class="${regenBtnClass} inline-flex items-center gap-1.5">
                            ${regenBtnLabel}
                        </button>
                    </div>
                    <p class="text-[9px] text-brand-text-muted text-center">${t('asset_viewer.three_d_viewer_hint')}</p>
                </div>`;

            // Viewer controls
            const viewer = container.querySelector('#av-3d-viewer');
            container.querySelector('#av-3d-zoom-in')?.addEventListener('click', () => {
                if (!viewer) return;
                const orbit = viewer.getCameraOrbit();
                orbit.radius = Math.max(0.5, orbit.radius * 0.75);
                viewer.cameraOrbit = `${orbit.theta}rad ${orbit.phi}rad ${orbit.radius}m`;
            });
            container.querySelector('#av-3d-zoom-out')?.addEventListener('click', () => {
                if (!viewer) return;
                const orbit = viewer.getCameraOrbit();
                orbit.radius = Math.min(10, orbit.radius * 1.33);
                viewer.cameraOrbit = `${orbit.theta}rad ${orbit.phi}rad ${orbit.radius}m`;
            });
            container.querySelector('#av-3d-reset')?.addEventListener('click', () => {
                if (!viewer) return;
                viewer.cameraOrbit = 'auto auto auto';
                viewer.cameraTarget = 'auto auto auto';
                viewer.fieldOfView = 'auto';
            });
            container.querySelector('#av-3d-autorotate')?.addEventListener('click', (e) => {
                if (!viewer) return;
                const isRotating = viewer.hasAttribute('auto-rotate');
                if (isRotating) {
                    viewer.removeAttribute('auto-rotate');
                    e.currentTarget.classList.remove('bg-brand-accent/60', 'hover:bg-brand-accent/80');
                    e.currentTarget.classList.add('bg-black/50', 'hover:bg-black/70');
                } else {
                    viewer.setAttribute('auto-rotate', '');
                    e.currentTarget.classList.remove('bg-black/50', 'hover:bg-black/70');
                    e.currentTarget.classList.add('bg-brand-accent/60', 'hover:bg-brand-accent/80');
                }
            });

            container.querySelector('#av-3d-regenerate')?.addEventListener('click', async () => {
                try {
                    const availability = await API.threeD.check();
                    if (!availability || !availability.available) {
                        window.showToast?.(t('asset_viewer.three_d_not_deployed'), 'warning');
                        return;
                    }
                    // Fetch deployed instances so Regenerate offers the SAME pipeline
                    // chooser as the first-time form (when >1 is deployed). Without
                    // this, regen defaulted to an empty list → no picker, so you
                    // couldn't re-run an asset through a different pipeline (e.g.
                    // A/B TripoSG vs full TRELLIS.2). Best-effort: empty list just
                    // hides the chooser and uses the server default.
                    let instances = [];
                    try {
                        const resp = await API.threeD.instances();
                        instances = (resp?.instances || []).filter(i => i.available);
                    } catch {}
                    this._render3DForm(container, instances);
                } catch (err) {
                    window.showToast?.(t('asset_viewer.three_d_not_deployed'), 'warning');
                }
            });

            // Variant switcher: show alternative 3D models for this 2D
            // version (different pipeline / deployment / config), each labelled by
            // deployment time. Best-effort, async — hidden when there's only one.
            this._populate3DVariants(container);
        },

        /**
         * Fetch + render the 3D variant switcher for the current version. A 2D
         * version can have multiple 3D variants; this lets the user view each and
         * "Set as default" (which one the gallery + thumbnail serve). Disambiguates
         * same-model multi-deploy variants by deployment time, like the 2D picker.
         */
        async _populate3DVariants(container) {
            const bar = container.querySelector('#av-3d-variants');
            const viewer = container.querySelector('#av-3d-viewer');
            if (!bar || !this._meta) return;
            const assetId = this._meta.id;
            const ver = this._currentVersion || 1;
            let data;
            try {
                data = await API.threeD.variants(assetId, ver);
            } catch { return; }
            const variants = data?.variants || [];
            if (variants.length < 2) { bar.classList.add('hidden'); return; }
            const defaultId = data.default_variant;

            const label = (v) => {
                const pl = v.pipeline || {};
                return v.instance_label
                    || pl.texture_label
                    || pl.geometry_model
                    || v.model_key || v.variant_id;
            };
            // Compact single-line pills — mirrors the 2D image version bar. Per-
            // variant detail (faces / PBR) lives in the button title tooltip so
            // the row stays short. "Set default" is a small inline button shown
            // only while previewing a non-default variant.
            const subtitle = (v) => [
                v.faces ? v.faces.toLocaleString() + ' ' + t('asset_viewer.three_d_est_faces') : '',
                v.pipeline?.has_pbr ? 'PBR' : '',
            ].filter(Boolean).join(' · ');
            bar.innerHTML = `
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-[10px] text-brand-text-muted uppercase tracking-wider flex-shrink-0">${t('asset_viewer.three_d_variants_title')}</span>
                    ${variants.map((v) => {
                        const isDefault = v.variant_id === defaultId;
                        const sub = subtitle(v);
                        return `<button class="av-3d-variant-btn px-2 py-1 rounded text-[10px] transition-all cursor-pointer ${isDefault ? 'bg-brand-accent text-white' : 'bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent hover:text-brand-text'}"
                                data-variant="${this._esc(v.variant_id)}" title="${this._esc(label(v))}${sub ? ' — ' + this._esc(sub) : ''}">
                            ${this._esc(label(v))}${isDefault ? `<span class="opacity-60 ml-1">(${t('asset_viewer.three_d_variant_default')})</span>` : ''}
                        </button>`;
                    }).join('')}
                    <button id="av-3d-set-default" class="hidden px-2 py-1 rounded text-[10px] border border-brand-accent/50 text-brand-accent hover:bg-brand-accent/10 transition-colors cursor-pointer">${t('asset_viewer.three_d_variant_set_default')}</button>
                </div>`;
            bar.classList.remove('hidden');

            // Track which variant is being previewed (starts at the default).
            let previewId = defaultId;
            const setDefaultBtn = bar.querySelector('#av-3d-set-default');
            const refreshButtons = () => {
                bar.querySelectorAll('.av-3d-variant-btn').forEach((btn) => {
                    const sel = btn.dataset.variant === previewId;
                    // Mirror the 2D version-bar pill states: accent fill when active,
                    // bordered/muted otherwise.
                    btn.classList.toggle('bg-brand-accent', sel);
                    btn.classList.toggle('text-white', sel);
                    btn.classList.toggle('bg-brand-bg', !sel);
                    btn.classList.toggle('border', !sel);
                    btn.classList.toggle('border-brand-border', !sel);
                    btn.classList.toggle('text-brand-text-muted', !sel);
                });
                // Offer "Set as default" only when previewing a non-default variant.
                if (setDefaultBtn) setDefaultBtn.classList.toggle('hidden', previewId === defaultId);
            };

            // Point both the viewer AND the Download GLB link at a variant, so
            // "Download GLB" always grabs exactly what's on screen (not the default).
            const dlLink = container.querySelector('#av-3d-download');
            const variantUrl = (vid) => `/api/gallery/${encodeURIComponent(assetId)}/3d/${ver}?variant=${encodeURIComponent(vid)}`;
            const showVariant = (vid) => {
                previewId = vid;
                if (viewer) viewer.src = `${variantUrl(vid)}&t=${Date.now()}`;
                if (dlLink) {
                    dlLink.href = variantUrl(vid);
                    dlLink.setAttribute('download', `${assetId}_${vid}.glb`);
                }
                refreshButtons();
            };
            // Initialize the download link to the default variant currently shown.
            if (dlLink && defaultId) {
                dlLink.href = variantUrl(defaultId);
                dlLink.setAttribute('download', `${assetId}_${defaultId}.glb`);
            }
            bar.querySelectorAll('.av-3d-variant-btn').forEach((btn) => {
                btn.addEventListener('click', () => showVariant(btn.dataset.variant));
            });

            setDefaultBtn?.addEventListener('click', async () => {
                try {
                    await API.threeD.setDefaultVariant(assetId, ver, previewId);
                    window.showToast?.(t('asset_viewer.three_d_variant_set_default_ok'), 'success');
                    // Refresh metadata so the gallery/thumbnail reflect the new default.
                    try { this._meta = await API.gallery.get(assetId); } catch {}
                    window.Gallery?.refresh?.();
                    this._update3DContent();
                } catch {
                    window.showToast?.(t('asset_viewer.three_d_failed'), 'error');
                }
            });
            refreshButtons();
        },

        // Legacy single-job poller removed — parallel 3D jobs are now tracked by
        // the in-progress strip (_start3DJobsPolling / #av-3d-jobs), which polls
        // the backend /active-all route and finalizes each via the server-side
        // poller. Kept as a safe no-op so existing close()/lifecycle calls work.
        _stop3DPolling() {
            if (this._3dPollTimer) {
                clearInterval(this._3dPollTimer);
                this._3dPollTimer = null;
            }
        },

        _formatBytes(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        },

        _esc(str) {
            const div = document.createElement('div');
            div.textContent = str || '';
            return div.innerHTML;
        },

        _renderDecomposed(data) {
            if (!data || typeof data !== 'object') return '';
            const sections = [];
            const _section = (label, obj) => {
                if (!obj) return;
                if (typeof obj === 'string') { sections.push(`<div><strong class="text-brand-text/80">${label}:</strong> ${this._esc(obj)}</div>`); return; }
                if (Array.isArray(obj)) {
                    const items = obj.map(item => typeof item === 'string' ? item : (item.name ? `${item.name} (${item.hex || ''})` : '')).filter(Boolean).join(', ');
                    if (items) sections.push(`<div><strong class="text-brand-text/80">${label}:</strong> ${this._esc(items)}</div>`);
                    return;
                }
                const lines = [];
                for (const [k, v] of Object.entries(obj)) {
                    if (typeof v === 'string' && v.trim()) {
                        lines.push(`<span class="text-brand-text-muted/60">${k.replace(/_/g, ' ')}:</span> ${this._esc(v)}`);
                    } else if (Array.isArray(v)) {
                        const items = v.map(item => typeof item === 'string' ? item : (item.name ? `${item.name} (${item.hex || ''})` : '')).filter(Boolean).join(', ');
                        if (items) lines.push(`<span class="text-brand-text-muted/60">${k.replace(/_/g, ' ')}:</span> ${this._esc(items)}`);
                    }
                }
                if (lines.length) sections.push(`<div><strong class="text-brand-text/80">${label}:</strong><div class="ml-3 space-y-0.5">${lines.map(l => `<div>${l}</div>`).join('')}</div></div>`);
            };
            _section('Subject', data.subject);
            _section('Scene', data.scene);
            _section('Composition', data.composition);
            _section('Lighting', data.lighting);
            _section('Style', data.style);
            return sections.join('');
        },
    };

    window.AssetViewer = AssetViewer;
})();
