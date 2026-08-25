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
            // nosemgrep
            overlay.innerHTML = html`
                <div class="modal-content bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                        <h2 class="text-lg font-semibold truncate flex-1">${item.png_filename || t('artsmoker.ui.asset_viewer.generated_asset')}</h2>
                        <div class="flex items-center gap-2 ml-4">
                            <button class="btn-reload btn btn-sm bg-indigo-600 hover:bg-indigo-500 text-white" title="${t('artsmoker.ui.asset_viewer.reload_studio_title')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                </svg>
                                ${t('artsmoker.ui.asset_viewer.to_studio')}
                            </button>
                            <button class="btn-add-text btn btn-sm bg-emerald-600 hover:bg-emerald-500 text-white" title="${t('artsmoker.ui.asset_viewer.add_text_title')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
                                </svg>
                                ${t('artsmoker.ui.asset_viewer.add_text')}
                            </button>
                            <button class="btn-reload-type hidden btn btn-sm bg-purple-600 hover:bg-purple-500 text-white" title="${t('artsmoker.ui.asset_viewer.edit_type_title')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
                                </svg>
                                ${t('artsmoker.ui.asset_viewer.edit_type')}
                            </button>
                            <div class="flex items-center gap-1 ml-2">
                                <button class="btn-prev p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors disabled:opacity-30" title="${t('artsmoker.ui.asset_viewer.previous')}">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                                    </svg>
                                </button>
                                <button class="btn-next p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors disabled:opacity-30" title="${t('artsmoker.ui.asset_viewer.next')}">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                    </svg>
                                </button>
                            </div>
                            <button class="btn-close p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors" title="${t('artsmoker.ui.asset_viewer.close_title')}">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Tabs -->
                    <div class="tab-bar px-6 pt-3">
                        <button class="tab active" data-tab="png">${t('artsmoker.ui.asset_viewer.png_tab')} <span id="av-tab-version-badge" class="text-[9px] opacity-60"></span></button>
                        <button class="tab" data-tab="edit">${t('artsmoker.ui.asset_viewer.edit_tab')}</button>
                        <button class="tab" data-tab="svg">${t('artsmoker.ui.asset_viewer.export_tab')} <span id="av-tab-svg-version" class="text-[9px] opacity-60"></span></button>
                        <button class="tab" data-tab="meta">${t('artsmoker.ui.asset_viewer.metadata_tab')} <span id="av-tab-meta-version" class="text-[9px] opacity-60"></span></button>
                        <button class="tab" data-tab="3d">${t('artsmoker.ui.asset_viewer.three_d_tab')}</button>
                    </div>

                    <!-- Version bar (shared across all tabs, populated when metadata loads) -->
                    <div id="av-version-bar" class="hidden px-6 py-2 bg-brand-bg/40 border-b border-brand-border">
                        <div class="flex items-center gap-2">
                            <span class="text-[10px] text-brand-text-muted uppercase tracking-wider flex-shrink-0">${t('artsmoker.ui.asset_viewer.version_label')}</span>
                            <div id="av-version-buttons" class="flex gap-1 flex-wrap"></div>
                            <button id="av-version-delete" class="ml-auto flex-shrink-0 px-2 py-1 rounded text-[10px] text-red-400/80 border border-red-500/20 hover:bg-red-500/10 hover:text-red-400 transition-all cursor-pointer" title="${t('artsmoker.ui.asset_viewer.version_delete_title')}">
                                <svg class="w-3 h-3 inline -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                                <span id="av-version-delete-label">${t('artsmoker.ui.asset_viewer.version_delete_btn')}</span>
                            </button>
                        </div>
                        <div id="av-version-detail" class="text-[10px] text-brand-text-muted mt-1 hidden"></div>
                    </div>

                    <!-- Tab Content -->
                    <div class="flex-1 overflow-auto p-6">
                        <!-- PNG tab with zoom/pan -->
                        <div class="tab-panel" data-panel="png">
                            <div class="relative">
                                <div id="av-zoom-container" class="preview-checkerboard rounded-lg overflow-hidden" style="position:relative; height: 65vh; min-height: 300px;">
                                    <img id="av-zoom-img" src="${pngUrl}" alt="${t('artsmoker.ui.asset_viewer.alt_generated_png')}" loading="lazy"
                                         style="transform-origin: 0 0; transition: transform 0.1s ease-out; max-width: none;" />
                                    <!-- Version-switch loading overlay: shown while the newly
                                         selected version's PNG downloads. Without it the PREVIOUS
                                         version keeps showing (browsers hold the old pixels until
                                         the new src finishes) and users mistake it for the new one. -->
                                    <div id="av-zoom-loading" class="hidden absolute inset-0 z-10 flex items-center justify-center bg-brand-bg/60 backdrop-blur-[2px]">
                                        <div class="flex flex-col items-center gap-2">
                                            <div class="loading-spinner w-8 h-8 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                            <span class="text-xs text-brand-text-muted">${t('artsmoker.ui.asset_viewer.version_loading')}</span>
                                        </div>
                                    </div>
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
                                    <button id="av-zoom-out" class="p-1 rounded hover:bg-white/20 text-white/80 hover:text-white" title="${t('artsmoker.ui.asset_viewer.zoom_out_title')}">
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"/></svg>
                                    </button>
                                    <span id="av-zoom-level" class="text-[10px] text-white/70 font-mono w-10 text-center">100%</span>
                                    <button id="av-zoom-in" class="p-1 rounded hover:bg-white/20 text-white/80 hover:text-white" title="${t('artsmoker.ui.asset_viewer.zoom_in_title')}">
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"/></svg>
                                    </button>
                                    <button id="av-zoom-fit" class="px-1.5 py-0.5 rounded text-[10px] text-white/80 hover:bg-white/20 hover:text-white" title="${t('artsmoker.ui.asset_viewer.zoom_fit_title')}">${t('artsmoker.ui.asset_viewer.zoom_fit')}</button>
                                    <button id="av-zoom-actual" class="px-1.5 py-0.5 rounded text-[10px] text-white/80 hover:bg-white/20 hover:text-white" title="${t('artsmoker.ui.asset_viewer.zoom_actual_title')}">${t('artsmoker.ui.asset_viewer.zoom_1to1')}</button>
                                    <span class="w-px h-4 bg-white/20 mx-0.5"></span>
                                    <button id="av-zoom-measure-btn" class="px-1.5 py-0.5 rounded text-[10px] text-white/80 hover:bg-white/20 hover:text-white flex items-center gap-1" title="${t('artsmoker.ui.asset_viewer.measure_title')}">
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7h16M4 7v10M4 7L2 9m18-2v10m0-10l2 2M7 7v3m5-3v5m5-5v3"/></svg>
                                        ${t('artsmoker.ui.asset_viewer.measure')}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Edit tab (Inpaint / Outpaint / Erase) -->
                        <div class="tab-panel hidden" data-panel="edit">
                            <div class="space-y-3">
                                <!-- Edit mode selector -->
                                <div class="flex gap-2">
                                    <button class="av-edit-mode btn btn-sm btn-secondary active" data-mode="inpaint">${t('artsmoker.ui.asset_viewer.inpaint')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="erase">${t('artsmoker.ui.asset_viewer.erase')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="outpaint">${t('artsmoker.ui.asset_viewer.outpaint')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="search_replace">${t('artsmoker.ui.asset_viewer.replace')}</button>
                                    <button class="av-edit-mode btn btn-sm btn-secondary" data-mode="search_recolor">${t('artsmoker.ui.asset_viewer.recolor')}</button>
                                </div>

                                <!-- Inpaint/Erase: Canvas + Mask -->
                                <div id="av-mask-section">
                                    <!-- Mask-paint controls (hidden for mask-free editors like Qwen) -->
                                    <div id="av-mask-controls">
                                        <div class="flex items-center gap-3 mb-2">
                                            <label class="text-xs text-brand-text-muted">${t('artsmoker.ui.asset_viewer.brush_size')}:</label>
                                            <input id="av-brush-size" type="range" min="5" max="80" value="20" class="w-24" />
                                            <span id="av-brush-size-label" class="text-xs text-brand-text-muted font-mono w-8">20px</span>
                                            <button id="av-mask-clear" class="btn btn-sm btn-secondary text-xs">${t('artsmoker.ui.asset_viewer.clear_mask')}</button>
                                        </div>
                                        <p class="text-[10px] text-brand-text-dim mb-1">${t('artsmoker.ui.asset_viewer.mask_hint_full')}</p>
                                    </div>
                                    <!-- Source image canvas — ALWAYS shown; it's the image the edit works on -->
                                    <div class="relative rounded-lg overflow-hidden border border-brand-border" style="display: inline-block;">
                                        <canvas id="av-mask-canvas" class="cursor-crosshair" style="max-width: 100%; max-height: 50vh;"></canvas>
                                    </div>
                                </div>

                                <!-- Outpaint: live preview (shared renderer) + direction controls -->
                                <div id="av-outpaint-section" class="hidden space-y-2">
                                    <p class="text-[10px] text-brand-text-dim">${t('artsmoker.ui.asset_viewer.outpaint_hint_full')}</p>
                                    <!-- Preview box: HTML <img> (object-contain) + measurement overlay,
                                         same structure as the 3D source-review dialog so the shared
                                         _wireMeasurement renderer draws rulers + extension bands here. -->
                                    <div class="relative w-full bg-brand-bg rounded-lg overflow-hidden border border-brand-border" style="height: 380px;">
                                        <img id="av-out-img" class="w-full h-full object-contain" alt="${t('artsmoker.ui.asset_viewer.alt_extend_preview')}" crossorigin="anonymous" />
                                        <canvas id="av-out-measure" class="absolute inset-0 w-full h-full pointer-events-none"></canvas>
                                    </div>
                                    <div id="av-out-stats" class="text-[10px] text-brand-text-muted flex flex-wrap items-center gap-x-4 gap-y-1 px-1"></div>
                                    <div class="grid grid-cols-4 gap-2 max-w-xs">
                                        <div><label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.asset_viewer.outpaint_left')}</label><input id="av-out-left" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.asset_viewer.outpaint_right')}</label><input id="av-out-right" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.asset_viewer.outpaint_up')}</label><input id="av-out-up" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                        <div><label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.asset_viewer.outpaint_down')}</label><input id="av-out-down" type="number" value="0" min="0" max="2000" class="input text-xs w-full" /></div>
                                    </div>
                                </div>

                                <!-- Search prompt (Replace/Recolor modes) -->
                                <div id="av-search-section" class="hidden">
                                    <label class="text-xs text-brand-text-muted mb-1 block" id="av-search-label">${t('artsmoker.ui.asset_viewer.find_object')}</label>
                                    <input id="av-search-prompt" type="text" class="input text-sm w-full" placeholder="${t('artsmoker.ui.asset_viewer.find_placeholder')}" />
                                </div>

                                <!-- Prompt + Model + Generate -->
                                <div>
                                    <div class="flex items-center justify-between mb-1">
                                        <label class="text-xs text-brand-text-muted" id="av-prompt-label">${t('artsmoker.ui.asset_viewer.edit_prompt')}</label>
                                        <button id="av-suggest-prompt" type="button" class="text-[10px] text-violet-300 hover:text-violet-200 flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-violet-500/10 transition-colors" title="${t('artsmoker.ui.asset_viewer.suggest_prompt_title')}">
                                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>
                                            <span>${t('artsmoker.ui.asset_viewer.suggest_prompt')}</span>
                                        </button>
                                    </div>
                                    <textarea id="av-edit-prompt" class="input text-sm w-full h-16" placeholder="${t('artsmoker.ui.asset_viewer.edit_prompt_placeholder')}"></textarea>
                                    <p id="av-suggest-reasoning" class="text-[10px] text-violet-300/70 mt-1 hidden"></p>
                                </div>
                                <div class="flex items-end gap-2">
                                    <div class="flex-1">
                                        <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('artsmoker.ui.asset_viewer.edit_model')}</label>
                                        <select id="av-edit-model" class="input text-xs"></select>
                                    </div>
                                    <button id="av-edit-generate" class="btn btn-primary btn-sm">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                                        ${t('artsmoker.ui.asset_viewer.apply_edit')}
                                    </button>
                                </div>
                                <p class="text-[10px] text-brand-text-dim mt-1">${t('artsmoker.ui.asset_viewer.edit_hint_full')}</p>
                                <div id="av-edit-status" class="text-xs text-brand-text-muted hidden"></div>
                            </div>
                        </div>

                        <!-- Export & Cutouts tab — vector SVG + background-removed variants -->
                        <div class="tab-panel hidden" data-panel="svg">
                            <div class="space-y-3">
                                <div class="flex items-start justify-between gap-3 flex-wrap">
                                    <p class="text-[11px] text-brand-text-muted max-w-md">${t('artsmoker.ui.asset_viewer.export_intro')}</p>
                                    <!-- Background-removal method + generate control.
                                         whitespace-nowrap on the label and button keeps
                                         each from wrapping mid-text; the row itself never
                                         wraps (flex-nowrap) — the intro paragraph shrinks
                                         instead. -->
                                    <div class="flex items-center gap-2 flex-shrink-0 flex-nowrap">
                                        <label class="text-[10px] text-brand-text-muted uppercase tracking-wider whitespace-nowrap">${t('artsmoker.ui.asset_viewer.export_bg_method')}</label>
                                        <select id="av-export-method" class="input text-xs py-1">
                                            <option value="local">${t('artsmoker.ui.asset_viewer.export_method_local')}</option>
                                            <option value="bedrock">${t('artsmoker.ui.asset_viewer.export_method_bedrock')}</option>
                                        </select>
                                        <button id="av-export-generate" class="btn btn-primary btn-sm whitespace-nowrap flex-shrink-0">
                                            <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"/></svg>
                                            ${t('artsmoker.ui.asset_viewer.export_generate_cutouts')}
                                        </button>
                                    </div>
                                </div>
                                <p id="av-export-method-hint" class="text-[10px] text-brand-text-dim -mt-1"></p>
                                <div id="av-export-status" class="text-xs text-brand-text-muted hidden"></div>
                                <!-- Three-variant grid, populated by _renderExportPanel -->
                                <div id="av-export-grid" class="grid grid-cols-1 sm:grid-cols-3 gap-3"></div>
                            </div>
                        </div>

                        <!-- Metadata tab (initially shows loading, updated when API responds) -->
                        <div class="tab-panel hidden" data-panel="meta">
                            <div id="asset-meta-content" class="space-y-4 text-sm">
                                <div class="flex items-center gap-2 text-brand-text-muted py-8 justify-center">
                                    <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                    ${t('artsmoker.ui.asset_viewer.loading_metadata')}
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
                                    ${t('artsmoker.ui.asset_viewer.loading_metadata')}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Footer: PNG/SVG downloads — only relevant on the image tabs
                         (png/edit/svg). Hidden on the Metadata + 3D tabs, which have
                         their own actions (the 3D tab has its own Download GLB). The
                         tab handler toggles #av-image-downloads visibility. -->
                    <div id="av-image-downloads" class="flex items-center justify-end gap-3 px-6 py-4 border-t border-brand-border">
                        <a id="av-download-png" href="${pngUrl}" download="${item.png_filename || 'asset.png'}" class="btn btn-secondary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            ${t('artsmoker.ui.asset_viewer.download_png')}
                        </a>
                        <a id="av-download-svg" href="${svgUrl}" download="${item.svg_filename || 'asset.svg'}" class="btn btn-secondary btn-sm btn-dl-svg">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            ${t('artsmoker.ui.asset_viewer.download_svg')}
                        </a>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);
            this._overlay = overlay;
        },

        /** Render the info bar under the image. The model tags are per-VERSION:
         *  the base tag is always the ORIGINAL generator; a second tag names the
         *  editor model of the version being VIEWED (this._currentVersion),
         *  shown only for edit versions whose model differs from the original.
         *  Called on load and re-called by the version bar on every switch. */
        _renderInfoBar(meta) {
            const infoBar = this._overlay?.querySelector('#av-image-info');
            if (!infoBar) return;
            const createdDate = meta.created_at ? window.formatDate(meta.created_at) : '';
            const modelLabel = meta.model_label || MODEL_LABELS[meta.image_model] || meta.image_model || '';
            const typeLabel = TYPE_LABELS[meta.asset_type] || meta.asset_type || 'N/A';
            const styleName = meta.style_snapshot?.name || meta.style_id || '';
            let versionModelLabel = '';
            try {
                const viewedV = this._currentVersion || meta.current_version || (meta.versions?.length || 1);
                const vrec = (meta.versions || []).find(v => v.version === viewedV);
                const vm = vrec && vrec.type !== 'original'
                    ? (vrec.model_label || vrec.image_model || '') : '';
                if (vm && vm !== modelLabel) versionModelLabel = vm;
            } catch {}
            // nosemgrep
            infoBar.innerHTML = [
                meta.imported ? html`<span class="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('artsmoker.ui.gallery.imported_badge')}</span>` : '',
                modelLabel ? html`<span class="px-1.5 py-0.5 rounded bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${modelLabel}${versionModelLabel ? html` <span class="opacity-60">· ${t('artsmoker.ui.asset_viewer.version_original')}</span>` : ''}</span>` : '',
                versionModelLabel ? html`<span class="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">${versionModelLabel} <span class="opacity-60">· ${t('artsmoker.ui.asset_viewer.version_this_edit')}</span></span>` : '',
                styleName ? html`<span class="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${styleName}</span>` : '',
                typeLabel !== 'N/A' ? html`<span class="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${typeLabel}</span>` : '',
                meta.width && meta.height ? html`<span>${meta.width}×${meta.height}</span>` : '',
                createdDate ? html`<span>${createdDate}</span>` : '',
            ].filter(Boolean).join('');
        },

        _updateMetadata(meta) {
            const container = this._overlay?.querySelector('#asset-meta-content');
            if (!container) return;

            // Now that metadata (versions, prompt slug, timestamps) is loaded, set
            // the initial PNG/SVG download filenames for the current version — the
            // static render couldn't (no meta yet). Version switches update these too.
            try {
                const curV = meta.current_version || (meta.versions?.length || 1);
                const vrec = (meta.versions || []).find(v => v.version === curV);
                const dlPng = this._overlay?.querySelector('#av-download-png');
                const dlSvg = this._overlay?.querySelector('#av-download-svg');
                if (dlPng) dlPng.setAttribute('download', this._versionDownloadName('png', curV, vrec));
                if (dlSvg) dlSvg.setAttribute('download', this._versionDownloadName('svg', curV, vrec));
            } catch {}

            const createdAt = meta.created_at ? window.formatTimestamp(meta.created_at) : 'N/A';
            const createdDate = meta.created_at ? window.formatDate(meta.created_at) : '';
            const isTypeStudio = meta.type === 'type-studio';
            const modelLabel = meta.model_label || MODEL_LABELS[meta.image_model] || meta.image_model || '';
            const typeLabel = TYPE_LABELS[meta.asset_type] || meta.asset_type || 'N/A';
            const styleName = meta.style_snapshot?.name || meta.style_id || '';

            // Update the image info bar (below the image, above metadata panel).
            // Extracted to a method: the version bar re-renders it on switch so
            // the "this edit" tag always reflects the VIEWED version, not the
            // asset's latest.
            this._renderInfoBar(meta);

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

            // Show/hide the footer SVG download button based on whether a with-bg
            // SVG exists. The Export & Cutouts tab itself is ALWAYS visible now —
            // it offers on-demand generation of the vector + background-removed
            // variants even when no SVG was produced at generation time.
            const hasSvg = !!(meta.svg_path);
            const svgDlBtn = this._overlay?.querySelector('.btn-dl-svg');
            if (svgDlBtn) svgDlBtn.classList.toggle('hidden', !hasSvg);
            const svgTab = this._overlay?.querySelector('[data-tab="svg"]');
            if (svgTab) svgTab.classList.remove('hidden');
            // Reset export-panel cache (asset/version may have changed) and refresh.
            this._exportStatus = null;
            this._renderExportPanel();

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
            // EXACT-version match only: a version that never had a 3D model must
            // resolve to null (→ "Generate Now"), never borrow another version's
            // model. (The old `version===1 → three_d_versions[0]` fallback made a
            // cropped Original show the full-body model generated from a later
            // outpainted version.)
            return meta.three_d_versions?.find(v => v.version === version) || null;
        },

        /** Render ONE 3D variant's metadata fields. When `multi` (the version has
         *  several 3D sub-variants), each is wrapped in a titled sub-card with a
         *  "Default" badge on the served one; a single variant renders bare. */
        _render3DVariantMeta(v, isDefault, multi, copyBtn) {
            const pl = v.pipeline || {};
            const created = v.created_at || v.generated_at;
            const field = (labelKey, html) =>
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                `<div><label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t(labelKey)}</label><p>${html}</p></div>`;
            const wide = (labelKey, html) =>
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                `<div class="col-span-2 sm:col-span-3"><label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${t(labelKey)}</label><p>${html}</p></div>`;
            let g = `<div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-sm">`;
            if (created) g += field('asset_viewer.meta_3d_generated', window.formatTimestamp(created));
            if (pl.geometry_model || v.model_key)
                g += field('asset_viewer.meta_3d_geometry', this._esc(pl.geometry_model || v.model_key));
            if (pl.texture_label || pl.texture_backend)
                g += field('asset_viewer.meta_3d_texture', this._esc(pl.texture_label || pl.texture_backend));
            if (v.model_key)
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                g += wide('asset_viewer.meta_3d_endpoint', `<span class="font-mono text-xs">${this._esc(v.model_key)}${pl.instance_type ? ` <span class="text-brand-text-muted">(${this._esc(pl.instance_type)})</span>` : ''}</span>`);
            else if (pl.instance_type)
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                g += field('asset_viewer.meta_3d_instance', `<span class="font-mono text-xs">${this._esc(pl.instance_type)}</span>`);
            if (v.job_id)
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                g += wide('asset_viewer.meta_3d_job_id', `<span class="font-mono text-xs text-brand-text-muted">${this._esc(v.job_id)}${copyBtn(v.job_id)}</span>`);
            if (pl.has_pbr)
                g += field('asset_viewer.meta_3d_pbr', `<span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">PBR</span>`);
            let _attrib = Array.isArray(pl.attributions) ? pl.attributions.slice() : [];
            const _usedDino = pl.pipeline_type === 'trellis2_full' || pl.texture_backend === 'trellis2';
            if (_usedDino && pl.textured !== false && !_attrib.includes('Built with DINOv3')) _attrib.push('Built with DINOv3');
            if (_attrib.length)
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                g += wide('asset_viewer.meta_3d_attribution', _attrib.map(a => `<span class="px-1.5 py-0.5 rounded text-[9px] bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${this._esc(a)}</span>`).join(' '));
            if (v.params) {
                const p = v.params;
                const paramStr = [
                    p.steps ? `steps: ${p.steps}` : '',
                    p.guidance ? `guidance: ${p.guidance}` : '',
                    p.mesh_resolution ? `depth: ${p.mesh_resolution}` : '',
                    p.max_faces ? `faces: ${p.max_faces}` : '',
                    p.texture_resolution ? `tex: ${p.texture_resolution}` : '',
                ].filter(Boolean).join(', ');
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                if (paramStr) g += wide('asset_viewer.meta_3d_params', `<span class="font-mono text-xs">${this._esc(paramStr)}</span>`);
            }
            if (v.size_bytes || v.vertices || v.faces)
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                g += wide('asset_viewer.meta_3d_file', `<span class="text-xs">${v.size_bytes ? this._formatBytes(v.size_bytes) : ''}${v.vertices ? ` / ${v.vertices.toLocaleString()} vertices` : ''}${v.faces ? ` / ${v.faces.toLocaleString()} faces` : ''}</span>`);
            if (pl.license_name)
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                g += wide('asset_viewer.meta_3d_license', `<span class="text-xs">${this._esc(pl.license_name)}${pl.commercial === true ? ` <span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('artsmoker.ui.asset_viewer.meta_3d_commercial')}</span>` : ''}${pl.license_accepted_at ? ` <span class="text-brand-text-muted">— ${window.formatTimestamp(pl.license_accepted_at)}</span>` : ''}</span>`);
            g += `</div>`;
            if (!multi) return g;
            // Multi-variant: wrap in a titled sub-card, default badged.
            const title = this._esc(pl.geometry_model || v.model_key || t('artsmoker.ui.asset_viewer.meta_3d_variant'))
                + (pl.texture_label ? ` · ${this._esc(pl.texture_label)}` : '');
            const badge = isDefault
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                ? ` <span class="px-1.5 py-0.5 rounded text-[9px] bg-brand-accent/15 text-brand-accent border border-brand-accent/25">${t('artsmoker.ui.asset_viewer.meta_3d_default')}</span>` : '';
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            return `<div class="border border-brand-border rounded-lg p-3 mb-2">
                <div class="text-xs font-medium text-brand-text mb-2">${title}${badge}</div>${g}</div>`;
        },

        _populateMetadata(container, meta) {
            const createdAt = meta.created_at ? window.formatTimestamp(meta.created_at) : 'N/A';
            const isTypeStudio = meta.type === 'type-studio';
            const modelLabel = meta.model_label || MODEL_LABELS[meta.image_model] || meta.image_model || '';
            const typeLabel = TYPE_LABELS[meta.asset_type] || meta.asset_type || 'N/A';
            const styleName = meta.style_snapshot?.name || meta.style_id || '';

            // Helper: copy button snippet
            const escAttr = (s) => (s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            const copyBtn = (text) => `<button class="av-copy-btn ml-2 px-1.5 py-0.5 rounded text-[9px] text-brand-text-muted hover:text-brand-accent hover:bg-brand-accent/10 border border-transparent hover:border-brand-accent/20 transition-colors" data-copy="${escAttr(text)}" title="${t('artsmoker.ui.asset_viewer.meta_copy')}">${t('artsmoker.ui.asset_viewer.meta_copy')}</button>`;

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

            // ── Shared design-system helpers (ONE consistent visual language) ──
            // fact(): a label-over-value cell for the left "facts" rail. `mono`
            // renders the value in monospace (IDs, seeds, paths); `full` lets a
            // value span/wrap (paths). Uniform label + value typography for every
            // fact — no more per-field font drift.
            const fact = (label, value, { mono = false, wrap = false } = {}) => {
                if (value == null || value === '') return '';
                const valClass = [
                    'text-sm text-brand-text break-words',
                    mono ? 'font-mono text-xs' : 'font-medium',
                    wrap ? 'whitespace-pre-wrap' : '',
                ].join(' ');
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                return `
                    <div class="av-fact">
                        <div class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-0.5">${label}</div>
                        <div class="${valClass}">${value}</div>
                    </div>`;
            };
            // promptBlock(): a labeled prompt card — one card treatment for ALL
            // prompts (user/enhanced/final/negative/recomposed). `tone` picks an
            // accent (neutral / amber / indigo / emerald) but keeps identical
            // padding, radius, font-size and label style across every card.
            const TONE = {
                neutral: 'bg-brand-bg/60 border-brand-border/40 text-brand-text',
                muted: 'bg-brand-bg/60 border-brand-border/40 text-brand-text-muted',
                amber: 'bg-amber-950/15 border-amber-500/20 text-amber-200/80',
                indigo: 'bg-indigo-950/15 border-indigo-500/20 text-brand-text/80',
            };
            const LABEL_TONE = {
                neutral: 'text-brand-text-muted', muted: 'text-brand-text-muted',
                amber: 'text-amber-400/80', indigo: 'text-indigo-400/80',
            };
            // Smaller text + a capped, scrollable box (user scrolls to read long
            // prompts rather than the card growing tall). `sub` renders a small
            // caption above the value (e.g. "sent to the model", "none").
            const promptBlock = (label, value, { tone = 'neutral', badge = '', copy = true, italic = false, note = '', sub = '', muted = false } = {}) => {
                if (!value) return '';
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                return `
                    <div class="av-prompt-block">
                        <div class="flex items-center gap-2 mb-0.5">
                            <span class="text-[11px] font-medium ${LABEL_TONE[tone] || LABEL_TONE.neutral}">${label}</span>
                            ${badge}
                            ${copy ? copyBtn(value) : ''}
                        </div>
                        ${note ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<p class="text-[9px] text-brand-text-muted mb-0.5">${note}</p>` : ''}
                        <p class="p-2 rounded-lg border ${TONE[tone] || TONE.neutral} whitespace-pre-wrap text-[11px] leading-snug max-h-28 overflow-y-auto ${italic ? 'italic' : ''} ${muted ? 'text-brand-text-muted' : ''}">${this._esc(value)}${sub ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<span class="block mt-1 text-[9px] text-brand-text-muted/70 not-italic">${sub}</span>` : ''}</p>
                    </div>`;
            };

            // ── Prompt Lineage — IN ORDER for the SELECTED version ─────────
            // 1. User's prompt  →  2. Prompt Designer (decomposed + recomposed,
            // if used)  →  3. Refined prompt actually sent (with +/- prompting
            // folded in)  →  4. For an edited version: what was sent to the editor
            // (instruction, mask, outpaint/extend canvas-growth spec).
            const ver = meta._version || null;                 // selected version record (null = base/v1)
            const isEdit = !!(ver && ver.type && ver.type !== 'original');
            const enBadge = `<span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">EN</span>`;
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            const langBadge = `<span class="px-1.5 py-0.5 rounded text-[9px] bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${this._esc(meta.original_language || '?')}</span>`;
            let promptLineage = '';

            // 1. USER PROMPT (original language + EN twin if translated)
            if (meta.original_language_prompt) {
                promptLineage += promptBlock(t('artsmoker.ui.asset_viewer.meta_user_prompt'), meta.original_language_prompt, { badge: langBadge });
                promptLineage += promptBlock(t('artsmoker.ui.asset_viewer.meta_user_prompt'), meta.original_prompt || meta.prompt, { badge: enBadge });
            } else if (meta.original_prompt) {
                promptLineage += promptBlock(t('artsmoker.ui.asset_viewer.meta_user_prompt'), meta.original_prompt);
            }
            if (meta.moderation_original) {
                promptLineage += promptBlock(t('artsmoker.ui.asset_viewer.meta_moderation_rewrite'), meta.moderation_original,
                    { tone: 'amber', note: t('artsmoker.ui.asset_viewer.meta_moderation_note') });
            }

            // 2. PROMPT DESIGNER (optional) — decomposed fields + concatenated
            //    (recomposed) text. Only for non-edit views (a base generation).
            if (!isTypeStudio && !isEdit) {
                if (meta.decomposed_data && Object.keys(meta.decomposed_data).length > 0) {
                    promptLineage += `
                        <div class="av-prompt-block">
                            <div class="text-[11px] font-medium ${LABEL_TONE.amber} mb-0.5">${t('artsmoker.ui.asset_viewer.meta_decomposition')}</div>
                            <div class="p-2 rounded-lg border ${TONE.amber} text-[11px] leading-snug max-h-28 overflow-y-auto space-y-1">
                                ${this._renderDecomposed(meta.decomposed_data)}
                            </div>
                        </div>`;
                }
                if (meta.recomposed_prompt) {
                    promptLineage += promptBlock(t('artsmoker.ui.asset_viewer.meta_recomposed'), meta.recomposed_prompt,
                        { tone: 'indigo', note: t('artsmoker.ui.asset_viewer.meta_recomposed_note') });
                } else if ('recomposed_prompt' in meta) {
                    promptLineage += promptBlock(t('artsmoker.ui.asset_viewer.meta_recomposed'), t('artsmoker.ui.asset_viewer.meta_designer_unused'),
                        { tone: 'muted', italic: true, copy: false });
                }
            }

            // 3. REFINED PROMPT actually sent to the model — with the positive
            //    suffix (positive_magic) + negative prompt folded in TOGETHER.
            if (!isTypeStudio && !isEdit) {
                const refined = meta.enhanced_prompt || meta.prompt || '';
                if (refined) {
                    const posMagic = meta.positive_magic ? this._esc(meta.positive_magic) : '';
                    const negTxt = meta.negative_prompt ? this._esc(meta.negative_prompt) : t('artsmoker.ui.asset_viewer.meta_none');
                    // Copy button carries ONLY the refined prompt (via data-copy).
                    // The positive/negative add-ons render in a SEPARATE element
                    // OUTSIDE the copyable <p>, so "copy" never grabs them.
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    promptLineage += `
                        <div class="av-prompt-block">
                            <div class="flex items-center gap-2 mb-0.5">
                                <span class="text-[11px] font-medium ${LABEL_TONE.neutral}">${t('artsmoker.ui.asset_viewer.meta_refined_prompt')}</span>
                                ${copyBtn(refined)}
                            </div>
                            <p class="p-2 rounded-t-lg border border-b-0 ${TONE.neutral} whitespace-pre-wrap text-[11px] leading-snug max-h-32 overflow-y-auto">${this._esc(refined)}</p>
                            <div class="p-2 rounded-b-lg border ${TONE.neutral} text-[9px] text-brand-text-muted/80 space-y-0.5">
                                <div>${t('artsmoker.ui.asset_viewer.meta_positive_add')}: ${posMagic || t('artsmoker.ui.asset_viewer.meta_none')}</div>
                                <div>${t('artsmoker.ui.asset_viewer.meta_negative_add')}: ${negTxt}</div>
                            </div>
                        </div>`;
                }
            } else if (isTypeStudio && meta.prompt) {
                promptLineage += promptBlock(t('artsmoker.ui.asset_viewer.meta_text_content'), meta.prompt);
            }

            // 4. EDITED VERSION — what was sent to the EDITOR to act upon.
            if (isEdit) {
                promptLineage += this._renderEditLineage(ver, promptBlock, TONE, LABEL_TONE, meta);
            }

            let promptDesign = '';  // (folded into promptLineage above; kept for assembly compat)

            // ── Section 3: Generation Details (left "facts" rail) ──────────
            // Uniform label-over-value facts, one column, consistent typography.
            const optDisplay = `${(meta.option_index ?? 0) + 1} / ${(meta.variant_index ?? 0) + 1}`;
            const optTotal = (meta.num_options && meta.num_variations) ? ` of ${meta.num_options} × ${meta.num_variations}` : '';
            const allModelsChip = meta.all_models
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                ? `<span class="px-1.5 py-0.5 rounded text-[9px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${t('artsmoker.ui.asset_viewer.meta_all_models')}</span>` : '';
            let genDetails = `<div class="space-y-3">`;
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_model'), modelLabel ? this._esc(modelLabel) : '');
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_type'), this._esc(typeLabel));
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_style'), styleName ? this._esc(styleName) : '');
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_dimensions'), `${meta.width || '?'} × ${meta.height || '?'}`);
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_quality'), meta.quality ? this._esc(meta.quality) : '');
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_region'), meta.region ? this._esc(meta.region) : '');
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_seed'), meta.seed != null ? String(meta.seed) : '', { mono: true });
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_cost'), meta.estimated_image_cost_usd != null ? `~$${meta.estimated_image_cost_usd.toFixed(4)}` : '');
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_options_variations'), `${optDisplay}${optTotal}`);
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_created'), createdAt);
            genDetails += fact(t('artsmoker.ui.asset_viewer.meta_batch'), this._esc(meta.batch_id || meta.id), { mono: true });
            if (allModelsChip) genDetails += fact(t('artsmoker.ui.asset_viewer.meta_all_models'), allModelsChip);
            genDetails += `</div>`;

            // ── Section 4: Post-Processing ─────────────────────────────────
            let postProcessing = '';
            const hasPostProc = meta.remove_background || meta.generate_svg || meta.upscale || meta.upscaled;
            if (hasPostProc || (meta.cost_history && meta.cost_history.length > 0)) {
                let ppContent = '<div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2">';
                if (meta.remove_background) {
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    ppContent += `<div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span class="text-sm">${t('artsmoker.ui.asset_viewer.meta_bg_removed')}</span>
                    </div>`;
                }
                if (meta.generate_svg) {
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    ppContent += `<div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span class="text-sm">${t('artsmoker.ui.asset_viewer.meta_svg_generated')}</span>
                    </div>`;
                }
                if (meta.upscale || meta.upscaled) {
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    ppContent += `<div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span class="text-sm">${t('artsmoker.ui.asset_viewer.meta_upscaled')}</span>
                    </div>`;
                }
                ppContent += '</div>';

                // Cost breakdown from cost_history — with a summed total so the
                // per-step actuals reconcile (previously there was no total).
                if (meta.cost_history && meta.cost_history.length > 0) {
                    const _histTotal = meta.cost_history.reduce((s, c) => s + (c.cost_usd || c.cost || 0), 0);
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    ppContent += `<div class="mt-3 border-t border-brand-border/30 pt-2">
                        <label class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-1 block">${t('artsmoker.ui.asset_viewer.meta_cost_breakdown')}</label>
                        <div class="space-y-1">
                            ${meta.cost_history.map(c => /* nosemgrep -- _esc/escAttr-escaped raw template */ `
                                <div class="flex justify-between text-xs text-brand-text-muted">
                                    <span>${this._esc(c.label || c.type || '?')}</span>
                                    <span class="font-mono">$${(c.cost_usd || c.cost || 0).toFixed(4)}</span>
                                </div>
                            `).join('')}
                            <div class="flex justify-between text-xs text-brand-text font-medium border-t border-brand-border/30 pt-1 mt-1">
                                <span>${t('artsmoker.ui.asset_viewer.meta_cost_total')}</span>
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
            // The 3D section reflects the VIEWED version ONLY. A 2D version can hold
            // MULTIPLE 3D sub-variants (e.g. TripoSG + TRELLIS.2) — show them ALL,
            // default first + badged, with a count header so the user isn't misled
            // into thinking "3/3" (2D versions) equals the number of 3D models.
            const bucket3d = meta.three_d?.[`v${currentVer}`];
            let variants3d = Array.isArray(bucket3d?.variants) ? bucket3d.variants.slice() : [];
            if (!variants3d.length) {   // legacy flat fallback → single entry
                const single = this._default3DVariant(meta, currentVer);
                if (single) variants3d = [single];
            }
            if (variants3d.length) {
                const defaultId = bucket3d?.default_variant;
                const multi = variants3d.length > 1;
                // Default variant first.
                variants3d.sort((a, b) =>
                    (b.variant_id === defaultId ? 1 : 0) - (a.variant_id === defaultId ? 1 : 0));
                const header = multi
                    // nosemgrep -- { count: … } is a t() params object, not a template string
                    ? `<div class="text-[11px] text-brand-text-muted mb-2">${t('artsmoker.ui.asset_viewer.meta_3d_variant_count', { count: variants3d.length })}</div>`
                    : '';
                threeDContent = header + variants3d
                    .map(v => this._render3DVariantMeta(v, v.variant_id === defaultId, multi, copyBtn))
                    .join('');
            }

            // ── Section 6: Style ───────────────────────────────────────────
            let styleContent = '';
            if (meta.style_snapshot) {
                if (meta.style_snapshot.description) {
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    styleContent += `<p class="text-sm text-brand-text-muted">${this._esc(meta.style_snapshot.description)}</p>`;
                }
                if (meta.style_snapshot.generation_hints) {
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    styleContent += `
                        <div>
                            <label class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-1 block">${t('artsmoker.ui.asset_viewer.meta_style_hints')}</label>
                            <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-xs text-brand-text-muted">${this._esc(meta.style_snapshot.generation_hints)}</p>
                        </div>`;
                }
            }

            // ── Section 7: IP Declaration ──────────────────────────────────
            let ipContent = '';
            if (meta.ip_owned || meta.ip_licensed) {
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                ipContent = `<div class="p-2 rounded-lg bg-brand-accent/10 border border-brand-accent/20 text-xs">
                    <span class="font-medium">${t('artsmoker.ui.asset_viewer.meta_ip_declaration')}</span>
                    ${meta.ip_owned ? ' ' + t('artsmoker.ui.asset_viewer.meta_ip_owner') : ''}${meta.ip_licensed ? ' ' + t('artsmoker.ui.asset_viewer.meta_ip_licensed') : ''}
                </div>`;
            }

            // ── Version History — driven off the REAL versions[] data ──────
            // (The old edit_history[] block was dead — the backend never wrote
            // that key; version records live in meta.versions[] with different
            // field names.) Compact timeline of all versions; the selected one
            // is highlighted. Full per-version detail shows in Prompt Lineage.
            let editHistoryContent = '';
            const allVersions = Array.isArray(meta.versions) ? meta.versions : [];
            if (allVersions.length > 1) {
                const selVer = this._currentVersion || meta.current_version || allVersions.length;
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                editHistoryContent = `<div class="space-y-1.5">
                    ${allVersions.map(vr => {
                        const isSel = vr.version === selVer;
                        const kind = (vr.type || 'edit').replace(/_/g, ' ');
                        const when = vr.timestamp ? window.formatTimestamp(vr.timestamp) : '';
                        const model = this._esc(vr.model_label || vr.image_model || '');
                        // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                        return `<div class="p-2 rounded border-l-2 ${isSel ? 'border-emerald-400 bg-emerald-400/5' : 'border-brand-border bg-brand-bg/40'}">
                            <div class="flex items-center justify-between text-[10px]">
                                <span class="font-semibold text-brand-text">v${vr.version} · ${this._esc(kind)}${isSel ? /* nosemgrep -- _esc/escAttr-escaped raw template */ ` <span class="text-emerald-400/80">(${t('artsmoker.ui.asset_viewer.meta_current_version')})</span>` : ''}</span>
                                <span class="text-brand-text-muted">${when}</span>
                            </div>
                            ${model ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<p class="text-[10px] text-brand-text-muted mt-0.5">${model}</p>` : ''}
                        </div>`;
                    }).join('')}
                </div>`;
            }

            // ── Section 9: File & Version ──────────────────────────────────
            // Shows the EXACT on-disk path for the CURRENTLY-SELECTED version.
            // Convention (backend): current version = <dir>/asset.png; older
            // versions = <dir>/asset_v{N}.png. storage_dir is the absolute dir
            // provided by the /api/gallery/{id} endpoint.
            const versions = Array.isArray(meta.versions) ? meta.versions : [];
            const totalVers = versions.length || 1;
            const curVer = this._currentVersion || meta.current_version || totalVers;
            const isCurrent = curVer === (meta.current_version || totalVers);
            const dir = meta.storage_dir || '';
            const pngFile = isCurrent ? 'asset.png' : `asset_v${curVer}.png`;
            const fullPath = dir ? `${dir}/${pngFile}` : pngFile;
            let fileInfoContent = `<div class="space-y-3">`;
            if (totalVers > 1) {
                fileInfoContent += fact(t('artsmoker.ui.asset_viewer.meta_version'),
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    `${curVer} / ${totalVers}${isCurrent ? ` <span class="text-emerald-400/80 text-[10px]">(${t('artsmoker.ui.asset_viewer.meta_current_version')})</span>` : ''}`);
            }
            fileInfoContent += fact(t('artsmoker.ui.asset_viewer.meta_full_path'),
                `${this._esc(fullPath)}${copyBtn(fullPath)}`, { mono: true, wrap: true });
            if (meta.svg_filename) {
                const svgFile = isCurrent ? (meta.svg_filename) : `asset_v${curVer}.svg`;
                fileInfoContent += fact('SVG', `${this._esc(dir ? dir + '/' + svgFile : svgFile)}`, { mono: true, wrap: true });
            }
            // 3D model file path for the VIEWED version's DEFAULT variant (only
            // when that version actually has a model — version-exact, no fallback).
            // The variant record's field is `glb_filename` (older shapes used
            // `glb_file`); tolerate both so the path always renders when present.
            const _def3d = this._default3DVariant(meta, curVer);
            const glbFile = _def3d?.glb_filename || _def3d?.glb_file;
            if (glbFile) {
                const glbPath = dir ? `${dir}/${glbFile}` : glbFile;
                fileInfoContent += fact('GLB', `${this._esc(glbPath)}${copyBtn(glbPath)}`, { mono: true, wrap: true });
            }
            fileInfoContent += `</div>`;

            // ── Type Studio section (special) ──────────────────────────────
            let typeStudioContent = '';
            if (isTypeStudio) {
                typeStudioContent = `
                    ${meta.source_image_id ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<p class="text-sm mb-1"><span class="text-brand-text-muted">${t('artsmoker.ui.asset_viewer.meta_source_image')}</span> ${this._esc(meta.source_image_id)}</p>` : '<p class="text-sm mb-1 text-brand-text-muted">' + t('artsmoker.ui.asset_viewer.meta_standalone_text') + '</p>'}
                    ${meta.style_note ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<p class="text-sm mb-1"><span class="text-brand-text-muted">${t('artsmoker.ui.asset_viewer.meta_style_note')}</span> ${this._esc(meta.style_note)}</p>` : ''}
                    ${meta.lines ? `
                    <div class="mt-2 space-y-1">
                        ${meta.lines.map((l, i) => /* nosemgrep -- _esc/escAttr-escaped raw template */ `
                            <div class="text-sm p-2 rounded bg-brand-bg/40">
                                <span class="text-brand-text-muted">${t('artsmoker.ui.asset_viewer.meta_line', {num: i+1})}</span> "${this._esc(l.text)}"
                                <span class="text-brand-text-muted/60 text-xs ml-2">${this._esc(l.font || t('artsmoker.ui.common.default'))} / ${this._esc(l.position || 'center')}</span>
                            </div>
                        `).join('')}
                    </div>` : ''}`;
            }

            // ── Assemble: two-column layout ────────────────────────────────
            // LEFT rail = compact facts (always-open, non-collapsible): generation
            // details + file/version. RIGHT = prompt lineage + prompt design (the
            // scrolling narrative). Bulky/optional sections (post-proc, 3D, style,
            // IP, edit history, type studio) span FULL WIDTH below both columns.
            // Matches the right-column section() header padding (py-2) so the
            // "Generation Details" and "Prompt Lineage" labels align on the same
            // baseline across the two columns.
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            const railHeader = (label) => `<div class="text-xs font-semibold uppercase tracking-wider text-brand-text-muted py-2 mb-1 border-b border-brand-border/50">${label}</div>`;
            const promptsCol = promptLineage
                ? section('prompts', t('artsmoker.ui.asset_viewer.meta_prompt_lineage'), promptLineage, true)
                : '';
            // Left facts rail: generation details (incl. 3D for THIS version) +
            // post-processing + version history + file/version. Everything
            // valuable for the selected version, one consistent column.
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            const factsRail = `
                <div class="space-y-5">
                    <div>${railHeader(t('artsmoker.ui.asset_viewer.meta_generation_details'))}${genDetails}</div>
                    ${threeDContent ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<div>${railHeader(t('artsmoker.ui.asset_viewer.meta_three_d_section'))}${threeDContent}</div>` : ''}
                    ${postProcessing ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<div>${railHeader(t('artsmoker.ui.asset_viewer.meta_post_processing'))}${postProcessing}</div>` : ''}
                    ${editHistoryContent ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<div>${railHeader(t('artsmoker.ui.asset_viewer.meta_version_history'))}${editHistoryContent}</div>` : ''}
                    ${styleContent ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<div>${railHeader(t('artsmoker.ui.asset_viewer.meta_style_section'))}${styleContent}</div>` : ''}
                    ${ipContent ? /* nosemgrep -- _esc/escAttr-escaped raw template */ `<div>${railHeader(t('artsmoker.ui.asset_viewer.meta_ip_declaration'))}${ipContent}</div>` : ''}
                    <div>${railHeader(t('artsmoker.ui.asset_viewer.meta_file_info'))}${fileInfoContent}</div>
                </div>`;
            // nosemgrep
            container.innerHTML = html`
                <div class="grid grid-cols-1 md:grid-cols-[minmax(0,240px)_minmax(0,1fr)] gap-6">
                    <aside class="av-facts-rail">${raw(factsRail)}</aside>
                    <div class="av-prompts-col min-w-0 space-y-4">
                        ${promptsCol ? raw(promptsCol) : html`<p class="text-sm text-brand-text-muted italic">${t('artsmoker.ui.asset_viewer.meta_no_prompts')}</p>`}
                        ${isTypeStudio && typeStudioContent ? raw(section('typestudio', t('artsmoker.ui.asset_viewer.meta_type_studio_details'), typeStudioContent, true)) : ''}
                    </div>
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
                        btn.textContent = t('artsmoker.ui.asset_viewer.meta_copied');
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

        // ── Export & Cutouts panel ────────────────────────────────────────
        //
        // Three artefacts per version: (1) with-bg vector SVG, (2) background-
        // removed transparent PNG, (3) background-removed vector SVG. (2)+(3) are
        // produced on demand from a SINGLE background removal (the SVG is a free
        // local trace of the cutout PNG), via local rembg (free) or paid Bedrock.

        _exportCard({ titleKey, descKey, url, isSvg, filename, exists, checker }) {
            const bg = checker ? 'preview-checkerboard' : 'bg-brand-bg/40';
            const inner = exists
                ? html`<img src="${url}?t=${Date.now()}" alt="" class="max-w-full max-h-[34vh] object-contain rounded" loading="lazy" />`
                : html`<div class="flex flex-col items-center gap-1 text-brand-text-dim text-[11px] py-10">
                        <svg class="w-6 h-6 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                        <span>${t('artsmoker.ui.asset_viewer.export_not_generated')}</span>
                   </div>`;
            const dl = exists
                ? html`<a href="${url}" download="${filename}" class="btn btn-secondary btn-sm w-full justify-center">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>
                        ${isSvg ? t('artsmoker.ui.asset_viewer.export_dl_svg') : t('artsmoker.ui.asset_viewer.export_dl_png')}
                   </a>`
                : html`<button class="btn btn-secondary btn-sm w-full justify-center opacity-40 cursor-not-allowed" disabled>${isSvg ? t('artsmoker.ui.asset_viewer.export_dl_svg') : t('artsmoker.ui.asset_viewer.export_dl_png')}</button>`;
            return html`
                <div class="border border-brand-border rounded-lg overflow-hidden flex flex-col">
                    <div class="px-3 py-2 border-b border-brand-border">
                        <div class="text-xs font-medium text-brand-text">${t(titleKey)}</div>
                        <div class="text-[10px] text-brand-text-muted">${t(descKey)}</div>
                    </div>
                    <div class="${bg} flex-1 flex items-center justify-center p-3 min-h-[180px]">${inner}</div>
                    <div class="p-2">${dl}</div>
                </div>`;
        },

        /** Render the three export cards from cached status (fetches if absent). */
        async _renderExportPanel() {
            const grid = this._overlay?.querySelector('#av-export-grid');
            if (!grid || !this._item) return;
            const assetId = this._item.id;
            const version = this._currentVersion || this._meta?.current_version
                || (this._meta?.versions?.length || 1);

            // Update the method hint (cost implication) whenever we render.
            this._updateExportMethodHint();

            if (!this._exportStatus) {
                try {
                    this._exportStatus = await API.gallery.exportStatus(assetId, version);
                } catch {
                    this._exportStatus = null;
                }
            }
            const s = this._exportStatus || {};
            const withbgUrl = s.withbg_svg?.url || API.gallery.versionSvgUrl(assetId, version);
            const withbgExists = !!s.withbg_svg?.exists;
            const pngExists = !!s.nobg_png?.exists;
            const svgExists = !!s.nobg_svg?.exists;

            // nosemgrep
            grid.innerHTML = [
                this._exportCard({
                    titleKey: 'asset_viewer.export_card_withbg_title',
                    descKey: 'asset_viewer.export_card_withbg_desc',
                    url: withbgUrl, isSvg: true, checker: false,
                    filename: `${assetId}_v${version}.svg`, exists: withbgExists,
                }),
                this._exportCard({
                    titleKey: 'asset_viewer.export_card_nobg_png_title',
                    descKey: 'asset_viewer.export_card_nobg_png_desc',
                    url: API.gallery.cutoutPngUrl(assetId, version), isSvg: false, checker: true,
                    filename: `${assetId}_v${version}_nobg.png`, exists: pngExists,
                }),
                this._exportCard({
                    titleKey: 'asset_viewer.export_card_nobg_svg_title',
                    descKey: 'asset_viewer.export_card_nobg_svg_desc',
                    url: API.gallery.cutoutSvgUrl(assetId, version), isSvg: true, checker: true,
                    filename: `${assetId}_v${version}_nobg.svg`, exists: svgExists,
                }),
            ].join('');

            // Reflect whichever method last produced the cutouts (if any).
            const methodSel = this._overlay?.querySelector('#av-export-method');
            if (methodSel && s.method) methodSel.value = s.method;

            // If cutouts already exist, soften the CTA label to "Regenerate".
            const genBtnLabel = this._overlay?.querySelector('#av-export-generate');
            if (genBtnLabel) {
                const span = genBtnLabel.childNodes[genBtnLabel.childNodes.length - 1];
                const label = (pngExists && svgExists)
                    ? t('artsmoker.ui.asset_viewer.export_regenerate_cutouts')
                    : t('artsmoker.ui.asset_viewer.export_generate_cutouts');
                if (span && span.nodeType === Node.TEXT_NODE) span.textContent = ' ' + label;
            }
        },

        _updateExportMethodHint() {
            const sel = this._overlay?.querySelector('#av-export-method');
            const hint = this._overlay?.querySelector('#av-export-method-hint');
            if (!sel || !hint) return;
            hint.textContent = sel.value === 'bedrock'
                ? t('artsmoker.ui.asset_viewer.export_method_bedrock_hint')
                : t('artsmoker.ui.asset_viewer.export_method_local_hint');
        },

        /** Trigger on-demand generation of the bg-removed cutout PNG + SVG. */
        async _generateExportCutouts() {
            const btn = this._overlay?.querySelector('#av-export-generate');
            const statusEl = this._overlay?.querySelector('#av-export-status');
            const methodSel = this._overlay?.querySelector('#av-export-method');
            if (!btn || !this._item) return;
            const method = methodSel?.value || 'local';
            const version = this._currentVersion || this._meta?.current_version
                || (this._meta?.versions?.length || 1);

            // Decide whether to regenerate. Reuse the freshest status we have.
            let s = this._exportStatus;
            if (!s || s.version !== version) {
                try { s = await API.gallery.exportStatus(this._item.id, version); } catch { s = null; }
            }
            const pngExists = !!s?.nobg_png?.exists;
            const svgExists = !!s?.nobg_svg?.exists;
            let force = false;
            if (pngExists && svgExists) {
                // Both already exist — don't silently overwrite; ask first.
                const ok = await window.showConfirm?.(
                    t('artsmoker.ui.asset_viewer.export_regen_confirm'),
                    { title: t('artsmoker.ui.asset_viewer.export_regen_title'),
                      confirmLabel: t('artsmoker.ui.asset_viewer.export_regen_yes'), danger: true });
                if (!ok) return;   // keep the existing cutouts untouched
                force = true;
            }
            // else: PNG-without-SVG (just trace the SVG from the existing PNG) or
            // neither (generate) — both handled by force=false server-side.

            btn.disabled = true;
            if (statusEl) {
                statusEl.classList.remove('hidden', 'text-red-400');
                statusEl.textContent = t('artsmoker.ui.asset_viewer.export_working');
            }
            try {
                const res = await API.gallery.createExportVariants(this._item.id, { method, version, force });
                this._exportStatus = res;
                await this._renderExportPanel();
                if (statusEl) {
                    const cost = res.cost_incurred_usd || 0;
                    statusEl.textContent = cost > 0
                        ? t('artsmoker.ui.asset_viewer.export_done_cost', { cost: cost.toFixed(2) })
                        : t('artsmoker.ui.asset_viewer.export_done_free');
                }
            } catch (err) {
                console.error('Export variants failed:', err);
                if (statusEl) {
                    statusEl.classList.add('text-red-400');
                    statusEl.textContent = t('artsmoker.ui.asset_viewer.export_error');
                }
            } finally {
                btn.disabled = false;
            }
        },

        _updateVersionBar(meta) {
            const bar = this._overlay?.querySelector('#av-version-bar');
            const btns = this._overlay?.querySelector('#av-version-buttons');
            const detail = this._overlay?.querySelector('#av-version-detail');
            if (!bar || !btns) return;

            // Tombstoned (deleted) versions are metadata records only — never
            // rendered as pills. Numbering is sparse by design (never reused).
            const versions = (meta.versions || []).filter(v => !v.deleted);

            // The bar is ALWAYS shown (it hosts the per-version Delete button,
            // which must be available even for a single/un-versioned asset —
            // deleting the only version deletes the whole asset). With fewer
            // than 2 versions there's nothing to switch between, so the pills
            // are skipped and only the label + Delete button render.
            bar.classList.remove('hidden');
            const currentVersion = meta.current_version || versions.length;
            if (versions.length < 2) {
                // Same term + pill styling as the multi-version bar uses for v1
                // ("Original") — a single/un-versioned asset IS its original.
                // nosemgrep
                btns.innerHTML = html`<span class="px-2 py-1 rounded text-[10px] bg-brand-accent text-white">${t('artsmoker.ui.asset_viewer.version_original')}</span>`;
                if (detail) detail.classList.add('hidden');
                return;
            }

            // nosemgrep
            btns.innerHTML = versions.map(v => html`
                <button class="av-version-btn px-2 py-1 rounded text-[10px] transition-all cursor-pointer
                    ${v.version === currentVersion
                        ? 'bg-brand-accent text-white'
                        : 'bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent hover:text-brand-text'}"
                    data-version="${v.version}" data-asset="${meta.id}"
                    title="${v.type}${v.timestamp ? ' — ' + window.formatTimestamp(v.timestamp) : ''}">
                    ${v.version === 1 ? t('artsmoker.ui.asset_viewer.version_original') : 'v' + v.version}
                    ${v.type !== 'original' ? html`<span class="opacity-50 ml-0.5">${v.type}</span>` : ''}
                </button>
            `).join('');

            // Attach click handlers
            btns.querySelectorAll('.av-version-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const version = parseInt(btn.dataset.version, 10);
                    const assetId = btn.dataset.asset;
                    const v = versions.find(vv => vv.version === version);
                    const vLabel = version === 1 ? t('artsmoker.ui.asset_viewer.version_original') : `v${version}`;

                    // Keep _currentVersion in sync FIRST so the Edit tab + 3D tab
                    // resolve against the chosen version (used below and by Edit).
                    this._currentVersion = version;

                    // Re-render the info bar so the model tags track the VIEWED
                    // version (the "this edit" tag must not stick to the latest).
                    this._renderInfoBar(this._meta || meta || {});

                    // Update PNG image, then re-fit the zoom viewer to the new image
                    // (a taller extended version would otherwise overflow / sit
                    // off-centre with the previous version's scale & pan).
                    // While the new PNG downloads, dim the stale image and show the
                    // loading overlay — otherwise the browser keeps rendering the
                    // PREVIOUS version's pixels and slow loads read as "switched".
                    const img = this._overlay?.querySelector('#av-zoom-img');
                    if (img) {
                        const loadingEl = this._overlay?.querySelector('#av-zoom-loading');
                        const settle = () => {
                            loadingEl?.classList.add('hidden');
                            img.style.opacity = '';
                        };
                        loadingEl?.classList.remove('hidden');
                        img.style.opacity = '0.25';
                        img.addEventListener('load', settle, { once: true });
                        img.addEventListener('error', () => {
                            settle();
                            window.showToast?.(t('artsmoker.ui.asset_viewer.version_load_failed'), 'error');
                        }, { once: true });
                        img.src = version === currentVersion
                            ? `/api/gallery/${assetId}/png?t=${Date.now()}`
                            : `/api/gallery/${assetId}/version/${version}?t=${Date.now()}`;
                        // Cached/instant loads may complete synchronously on src set.
                        if (img.complete && img.naturalWidth > 0) settle();
                        this._refitZoomOnLoad?.();
                    }

                    // Refresh the Export & Cutouts panel for the selected version
                    // (variants are cached per version, so re-fetch the status).
                    this._exportStatus = null;
                    this._renderExportPanel();

                    // Update the Edit tab's mask canvas AND the shared Extend preview
                    // to the selected version so edits act on what the user sees (both
                    // were stuck on the first-loaded version). Clears any in-progress
                    // mask; re-points the outpaint preview at the new version's image.
                    this._loadEditCanvasImage?.();
                    this._wireOutpaintPreview?.();

                    // Point the PNG/SVG download links at the SELECTED version — they
                    // were frozen at the current version (asset.png/svg) and ignored
                    // the version bar, so downloading "Original" gave the latest.
                    const dlPng = this._overlay?.querySelector('#av-download-png');
                    const dlSvg = this._overlay?.querySelector('#av-download-svg');
                    if (dlPng) {
                        dlPng.href = version === currentVersion
                            ? `/api/gallery/${assetId}/png?t=${Date.now()}`
                            : `/api/gallery/${assetId}/version/${version}?t=${Date.now()}`;
                        dlPng.setAttribute('download', this._versionDownloadName('png', version, v));
                    }
                    if (dlSvg) {
                        dlSvg.href = version === currentVersion
                            ? `/api/gallery/${assetId}/svg?t=${Date.now()}`
                            : `/api/gallery/${assetId}/version-svg/${version}?t=${Date.now()}`;
                        dlSvg.setAttribute('download', this._versionDownloadName('svg', version, v));
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
                    // version gets its own review before generating. (_currentVersion
                    // was already set above so Edit/3D resolve the right version.)
                    if (this._sourceApprovedVersion !== version) this._sourceApprovedVersion = null;
                    this._update3DContent();

                    // Re-render the FULL metadata panel for the selected version
                    // using the SAME _populateMetadata layout (consistent UX) — no
                    // separate/divergent per-version view. We overlay the version's
                    // own prompt/model/seed fields onto the base metadata so the
                    // panel reflects THIS version, and _populateMetadata reads
                    // this._currentVersion (already set above) for the exact file
                    // path. `_versioned` flags it so the panel can badge the version.
                    const metaContent = this._overlay?.querySelector('#asset-meta-content');
                    if (metaContent) {
                        // Overlay the selected version's own fields onto the base
                        // meta so the whole Metadata panel reflects THIS version
                        // (the version bar governs Metadata too). Pass the full
                        // version record as _version so _populateMetadata can show
                        // per-version edit specs (mask, outpaint dims, what was
                        // sent to the editor) and the right 3D variant.
                        const versionMeta = { ...meta, _version: v || null };
                        if (v) {
                            if (v.prompt != null) versionMeta.prompt = v.prompt;
                            if (v.enhanced_prompt != null) versionMeta.enhanced_prompt = v.enhanced_prompt;
                            if (v.negative_prompt != null) versionMeta.negative_prompt = v.negative_prompt;
                            if (v.model_label != null) versionMeta.model_label = v.model_label;
                            if (v.image_model != null) versionMeta.image_model = v.image_model;
                            if (v.region != null) versionMeta.region = v.region;
                            if (v.seed != null) versionMeta.seed = v.seed;
                            // A version's result_dims are its true canvas size.
                            if (v.result_dims?.width) { versionMeta.width = v.result_dims.width; versionMeta.height = v.result_dims.height; }
                            if (v.original_language_prompts?.prompt) {
                                versionMeta.original_language_prompt = v.original_language_prompts.prompt;
                                versionMeta.original_language = v.original_language || versionMeta.original_language;
                            }
                            versionMeta._versionType = v.type;
                            versionMeta._versionTimestamp = v.timestamp;
                        }
                        this._populateMetadata(metaContent, versionMeta);
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
                        // nosemgrep
                        detail.innerHTML = html`
                            <strong>${v.type === 'original' ? t('artsmoker.ui.asset_viewer.version_original') : v.type}</strong>
                            ${v.model_label || v.image_model || ''}
                            ${v.original_language_prompts?.prompt ? html` — <span class="text-[9px] text-brand-accent">(${v.original_language || '?'})</span> "${v.original_language_prompts.prompt}"` : ''}
                            ${v.prompt ? html` — ${v.original_language_prompts?.prompt ? html`<span class="text-[9px] text-emerald-400/70">(en)</span> ` : ''}"${v.prompt}"` : ''}
                            ${v.negative_prompt ? html` <span class="text-amber-300/60">[neg: ${v.negative_prompt}]</span>` : ''}
                            ${v.timestamp ? html` <span class="text-brand-text-dim">${window.formatTimestamp(v.timestamp)}</span>` : ''}
                        `;
                        this._syncVersionDetailVisibility();
                    }
                });
            });
        },

        _attachEvents() {
            if (!this._overlay) return;

            this._overlay.querySelector('.btn-close').addEventListener('click', () => this.close());

            // Per-version delete (version bar). Deletes ONLY the selected
            // version (tombstone + files); the whole-asset delete stays in the
            // Gallery. On success: switch to the promoted/previous version, or —
            // if that was the last version — the asset itself is gone: navigate
            // to the next/previous item in the list, else close the viewer.
            this._overlay.querySelector('#av-version-delete')?.addEventListener('click', async () => {
                const delBtn = this._overlay.querySelector('#av-version-delete');
                const meta = this._meta || {};
                const live = (meta.versions || []).filter(v => !v.deleted);
                const viewedV = this._currentVersion || meta.current_version || (live.length || 1);
                const isLast = live.length <= 1;
                const q = isLast
                    ? t('artsmoker.ui.asset_viewer.version_delete_last_confirm')
                    : t('artsmoker.ui.asset_viewer.version_delete_confirm', { version: viewedV });
                const ok = await window.showConfirm(q, {
                    title: t('artsmoker.ui.asset_viewer.version_delete_title'),
                    detail: t('artsmoker.ui.asset_viewer.version_delete_detail'),
                    confirmLabel: t('artsmoker.ui.asset_viewer.version_delete_btn'),
                    danger: true,
                });
                if (!ok) return;
                delBtn.disabled = true;
                try {
                    const resp = await fetch(
                        `/api/gallery/${encodeURIComponent(this._item?.id || '')}/version/${viewedV}`,
                        { method: 'DELETE' });
                    const d = await resp.json().catch(() => ({}));
                    if (!resp.ok) throw new Error(d.detail || `${resp.status}`);
                    if (d.file_errors && d.file_errors.length) {
                        // Metadata is consistent; some files remained (orphans, not
                        // corruption) — tell the user honestly.
                        window.showToast?.(t('artsmoker.ui.asset_viewer.version_delete_partial',
                            { count: d.file_errors.length }), 'warning');
                    }
                    if (window.Gallery?.refresh) window.Gallery.refresh();
                    if (d.asset_deleted) {
                        // Whole asset gone — go to a neighbour or close.
                        window.showToast?.(t('artsmoker.ui.asset_viewer.version_delete_asset_gone'), 'success');
                        const list = this._list, idx = this._listIndex;
                        if (list && list.length > 1 && idx >= 0) {
                            list.splice(idx, 1);
                            const nextIdx = Math.min(idx, list.length - 1);
                            this.close();
                            this.open(list[nextIdx], list, nextIdx);
                        } else {
                            this.close();
                        }
                        return;
                    }
                    window.showToast?.(t('artsmoker.ui.asset_viewer.version_deleted',
                        { version: viewedV, current: d.current_version }), 'success');
                    // Reopen the SAME asset fresh — metadata, version bar, image,
                    // edit canvas, export panel all re-resolve to the new current.
                    const list = this._list, idx = this._listIndex;
                    const item = this._item;
                    this.close();
                    this.open(item, list, idx);
                } catch (err) {
                    window.showToast?.(t('artsmoker.ui.asset_viewer.version_delete_failed') + ': ' + err.message, 'error');
                } finally {
                    delBtn.disabled = false;
                }
            });

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

            // Export & Cutouts: generate button + method-hint refresh.
            this._overlay.querySelector('#av-export-generate')
                ?.addEventListener('click', () => this._generateExportCutouts());
            this._overlay.querySelector('#av-export-method')
                ?.addEventListener('change', () => this._updateExportMethodHint());

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

            // Arrow keys for prev/next (gallery navigation). Guard against two cases
            // where arrows must NOT navigate the underlying image:
            //  1. Focus is in an editable field (text/number input, textarea,
            //     contenteditable) — arrows move the caret / adjust the value there.
            //  2. A layered dialog is open above the viewer (e.g. the source-review
            //     popup at z-[130]) — its own inputs own the keystrokes.
            this._navKeyHandler = (e) => {
                if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
                const el = document.activeElement;
                const tag = (el?.tagName || '').toLowerCase();
                if (tag === 'input' || tag === 'textarea' || tag === 'select' || el?.isContentEditable) return;
                // Any modal layered above the viewer (z >= 130) → let it handle keys.
                if (document.querySelector('.fixed.z-\\[130\\], .fixed.z-\\[140\\]')) return;
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
                    window.showToast?.(t('artsmoker.ui.asset_viewer.metadata_not_loaded'), 'warning');
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
                    window.showToast?.(t('artsmoker.ui.asset_viewer.metadata_not_loaded'), 'warning');
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

            // Track whether the user has painted anything since the last canvas
            // (re)load/clear. Drives the Apply-Edit gate for mask-requiring
            // model+mode combos — a submit without a mask used to fail with only
            // a transient toast the user could easily miss ("SD job never ran").
            canvas._maskPainted = false;
            this._updateApplyEditGate = () => {
                const btn = this._overlay?.querySelector('#av-edit-generate');
                const statusEl = this._overlay?.querySelector('#av-edit-status');
                if (!btn) return;
                const needsMask = (editMode === 'inpaint' || editMode === 'erase')
                    && !this._selectedEditModelIsMaskFree();
                const blocked = needsMask && !canvas._maskPainted;
                btn.disabled = blocked;
                btn.classList.toggle('opacity-50', blocked);
                btn.classList.toggle('cursor-not-allowed', blocked);
                if (statusEl) {
                    if (blocked) {
                        statusEl.textContent = t('artsmoker.ui.asset_viewer.mask_required_hint');
                        statusEl.classList.remove('hidden');
                    } else if (statusEl.textContent === t('artsmoker.ui.asset_viewer.mask_required_hint')) {
                        statusEl.textContent = '';
                    }
                }
            };

            // Load the SELECTED version's image onto the mask canvas. Re-callable so
            // the Edit tab always shows/edits the version chosen in the version bar
            // (not whatever was loaded first). Clears any painted mask on reload.
            this._loadEditCanvasImage = () => {
                const ver = this._currentVersion || (this._meta?.current_version) || 1;
                const cur = (this._meta?.current_version) || (this._meta?.versions?.length || 1);
                const id = encodeURIComponent(this._item?.id || '');
                const url = (ver === cur)
                    ? `/api/gallery/${id}/png?t=${Date.now()}`
                    : `/api/gallery/${id}/version/${ver}?t=${Date.now()}`;
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
                    canvas._maskPainted = false;   // fresh canvas = no mask yet
                    this._updateApplyEditGate?.();
                };
                img.src = url;
            };

            // Extend/Outpaint preview uses the SHARED measurement renderer
            // (_wireMeasurement) — the same one the 3D "Improve this Image" dialog
            // uses — so rulers, extension bands, subject bbox, and the live
            // new-size readout are identical across both surfaces. readDirs() maps
            // the #av-out-* direction inputs; _wireMeasurement handles the rest.
            this._outpaintReadDirs = () => {
                // Clamp to a non-negative range — extension can't be negative, and a
                // sane upper bound guards against pasted/typo values.
                const q = (sel) => { const n = parseInt(this._overlay?.querySelector(sel)?.value || '0', 10); return Number.isFinite(n) ? Math.max(0, Math.min(2000, n)) : 0; };
                return { up: q('#av-out-up'), down: q('#av-out-down'), left: q('#av-out-left'), right: q('#av-out-right') };
            };
            // (Re)wire the preview to the SELECTED version's image. Called on open,
            // on version switch, and when Extend mode is entered. The overlay stays
            // visible in the Edit tab (unlike the 3D dialog where it's toggled).
            this._wireOutpaintPreview = () => {
                const ver = this._currentVersion || (this._meta?.current_version) || 1;
                const cur = (this._meta?.current_version) || (this._meta?.versions?.length || 1);
                const id = encodeURIComponent(this._item?.id || '');
                const url = (ver === cur)
                    ? `/api/gallery/${id}/png?t=${Date.now()}`
                    : `/api/gallery/${id}/version/${ver}?t=${Date.now()}`;
                this._wireMeasurement(this._overlay, url, this._outpaintReadDirs,
                    { img: '#av-out-img', measure: '#av-out-measure', stats: '#av-out-stats' });
            };
            // Back-compat shim: other code paths call _drawOutpaintPreview() to
            // refresh the extend view (e.g. after Generate-Prompt seeds directions).
            this._drawOutpaintPreview = () => this._redrawMeasurement?.();

            this._loadEditCanvasImage();

            // Live-redraw the extend preview as the user changes any direction.
            // Also sanitize the field: extension can't be negative, so snap any
            // negative entry back to 0 before redrawing.
            ['#av-out-left', '#av-out-right', '#av-out-up', '#av-out-down'].forEach(sel => {
                this._overlay.querySelector(sel)?.addEventListener('input', (e) => {
                    const el = e.target;
                    if (el && parseInt(el.value, 10) < 0) el.value = '0';
                    if (editMode === 'outpaint') this._redrawMeasurement?.();
                });
            });

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
                if (editMode !== 'inpaint' && editMode !== 'erase') return;  // no mask in outpaint
                painting = true;
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                paintAt((e.clientX - rect.left) * scaleX, (e.clientY - rect.top) * scaleY);
                if (!canvas._maskPainted) { canvas._maskPainted = true; this._updateApplyEditGate?.(); }
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
                canvas._maskPainted = false;
                this._updateApplyEditGate?.();
            });

            // Edit mode switching
            this._overlay.querySelectorAll('.av-edit-mode').forEach(btn => {
                btn.addEventListener('click', () => {
                    editMode = btn.dataset.mode;
                    this._overlay.querySelectorAll('.av-edit-mode').forEach(b => b.classList.remove('active', 'bg-brand-accent', 'text-white'));
                    btn.classList.add('active', 'bg-brand-accent', 'text-white');

                    // The mask SECTION holds the paint canvas — inpaint/erase only.
                    // Outpaint has its OWN preview box (#av-outpaint-section) using the
                    // shared measurement renderer (image + rulers + extension bands),
                    // matching the 3D "Improve this Image" dialog.
                    const needsOutpaint = editMode === 'outpaint';
                    const paintModes = editMode === 'inpaint' || editMode === 'erase';
                    const maskFree = this._selectedEditModelIsMaskFree();
                    const needsSearch = editMode === 'search_replace' || editMode === 'search_recolor';

                    const maskSection = this._overlay.querySelector('#av-mask-section');
                    const maskControls = this._overlay.querySelector('#av-mask-controls');
                    const outSection = this._overlay.querySelector('#av-outpaint-section');
                    const searchSection = this._overlay.querySelector('#av-search-section');
                    const searchLabel = this._overlay.querySelector('#av-search-label');
                    const promptLabel = this._overlay.querySelector('#av-prompt-label');

                    if (maskSection) maskSection.classList.toggle('hidden', !paintModes);
                    if (maskControls) maskControls.classList.toggle('hidden', maskFree || !paintModes);
                    if (outSection) outSection.classList.toggle('hidden', !needsOutpaint);
                    if (searchSection) searchSection.classList.toggle('hidden', !needsSearch);

                    // Entering outpaint: (re)load the shared preview with the selected
                    // version's image. Entering a paint mode: reload the mask canvas at
                    // its own size (the paint canvas is separate from the outpaint box).
                    if (needsOutpaint) {
                        this._wireOutpaintPreview?.();
                    } else if (paintModes) {
                        this._loadEditCanvasImage?.();
                    }

                    // Update labels, placeholders, and hints for each mode
                    if (searchLabel) {
                        searchLabel.textContent = editMode === 'search_recolor'
                            ? t('artsmoker.ui.asset_viewer.search_recolor_label')
                            : t('artsmoker.ui.asset_viewer.search_replace_label');
                    }
                    if (promptLabel) {
                        const labels = {
                            'inpaint': t('artsmoker.ui.asset_viewer.edit_prompt_inpaint'),
                            'erase': t('artsmoker.ui.asset_viewer.edit_prompt_erase_full'),
                            'outpaint': t('artsmoker.ui.asset_viewer.edit_prompt_outpaint_full'),
                            'search_replace': t('artsmoker.ui.asset_viewer.edit_prompt_replace'),
                            'search_recolor': t('artsmoker.ui.asset_viewer.edit_prompt_recolor'),
                        };
                        promptLabel.textContent = labels[editMode] || t('artsmoker.ui.asset_viewer.edit_prompt_default');
                    }
                    // Update placeholder per mode
                    const promptInput = this._overlay?.querySelector('#av-edit-prompt');
                    if (promptInput) {
                        const placeholders = {
                            'inpaint': t('artsmoker.ui.asset_viewer.edit_prompt_placeholder_inpaint'),
                            'erase': t('artsmoker.ui.asset_viewer.edit_prompt_placeholder_erase'),
                            'outpaint': t('artsmoker.ui.asset_viewer.edit_prompt_placeholder_outpaint'),
                            'search_replace': t('artsmoker.ui.asset_viewer.edit_prompt_placeholder_replace'),
                            'search_recolor': t('artsmoker.ui.asset_viewer.edit_prompt_placeholder_recolor'),
                        };
                        promptInput.placeholder = placeholders[editMode] || t('artsmoker.ui.asset_viewer.edit_prompt_placeholder');
                    }
                    // Update mode-specific hint
                    const maskHint = this._overlay?.querySelector('#av-mask-section p');
                    const editHint = this._overlay?.querySelector('#av-edit-status')?.previousElementSibling;
                    const hints = {
                        'inpaint': t('artsmoker.ui.asset_viewer.edit_mode_hint_inpaint'),
                        'erase': t('artsmoker.ui.asset_viewer.edit_mode_hint_erase'),
                        'outpaint': t('artsmoker.ui.asset_viewer.edit_mode_hint_outpaint'),
                        'search_replace': t('artsmoker.ui.asset_viewer.edit_mode_hint_replace'),
                        'search_recolor': t('artsmoker.ui.asset_viewer.edit_mode_hint_recolor'),
                    };
                    if (maskHint && paintModes && !maskFree) {
                        maskHint.textContent = hints[editMode] || t('artsmoker.ui.asset_viewer.mask_hint_full');
                    }
                    if (editHint) {
                        editHint.textContent = hints[editMode] || t('artsmoker.ui.asset_viewer.edit_hint_full');
                    }

                    // Mode changed — re-evaluate whether Apply needs a mask.
                    this._updateApplyEditGate?.();
                });
            });

            // Populate edit model dropdown from registry
            this._loadEditModels(editMode);
            this._overlay.querySelectorAll('.av-edit-mode').forEach(btn => {
                btn.addEventListener('click', () => this._loadEditModels(btn.dataset.mode));
            });
            // When the model changes, toggle only the mask-PAINT controls: a
            // mask-free editor (Qwen) hides brush/clear/hint, but the source image
            // canvas (in #av-mask-section) stays visible — it's the edit input.
            this._overlay.querySelector('#av-edit-model')?.addEventListener('change', () => {
                const maskControls = this._overlay.querySelector('#av-mask-controls');
                if (maskControls) maskControls.classList.toggle('hidden', this._selectedEditModelIsMaskFree());
                // A mask-free model lifts the gate; a mask-requiring one restores it.
                this._updateApplyEditGate?.();
            });

            // ✨ Generate Prompt — vision LLM reads the image + original prompt and
            // proposes a ready-to-use edit prompt TAILORED to the active mode AND the
            // selected edit model's expected style (caption vs instruction). Replaces
            // any existing text (per the requested behaviour). For replace/recolor it
            // also fills the "find object" field; for extend it seeds the directions.
            this._overlay.querySelector('#av-suggest-prompt')?.addEventListener('click', async () => {
                const sbtn = this._overlay.querySelector('#av-suggest-prompt');
                const promptEl = this._overlay.querySelector('#av-edit-prompt');
                const reasonEl = this._overlay.querySelector('#av-suggest-reasoning');
                const model = this._overlay.querySelector('#av-edit-model')?.value || '';
                const label = sbtn?.querySelector('span');
                const origLabel = label?.textContent;
                if (sbtn) sbtn.disabled = true;
                if (label) label.textContent = t('artsmoker.ui.asset_viewer.suggest_prompt_working');
                if (reasonEl) reasonEl.classList.add('hidden');
                try {
                    const resp = await fetch('/api/generate/suggest-edit-prompt', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        // nosemgrep -- serialized HTTP request body; key ordering is irrelevant (not used as an object/map key)
                        body: JSON.stringify({
                            asset_id: this._item?.id,
                            version: this._currentVersion || undefined,
                            mode: editMode,
                            model,
                        }),
                    });
                    if (!resp.ok) throw new Error(String(resp.status));
                    const d = await resp.json();
                    // Fill the prompt box (replace existing text, as requested).
                    if (promptEl && d.prompt) promptEl.value = d.prompt;
                    // Replace/recolor: also fill the "find object" field.
                    if (d.search_prompt) {
                        const sp = this._overlay.querySelector('#av-search-prompt');
                        if (sp) sp.value = d.search_prompt;
                    }
                    // Extend: seed the direction inputs from the suggestion, then
                    // refresh the live preview so the user sees the new canvas.
                    if (editMode === 'outpaint' && d.suggest_outpaint) {
                        const map = { left: '#av-out-left', right: '#av-out-right', up: '#av-out-up', down: '#av-out-down' };
                        for (const [k, sel] of Object.entries(map)) {
                            const inp = this._overlay.querySelector(sel);
                            if (inp && d.suggest_outpaint[k] != null) inp.value = d.suggest_outpaint[k];  // nosemgrep -- fixed key from a left/right/up/down map, not JSON-derived object keys
                        }
                        this._drawOutpaintPreview?.();
                    }
                    // Show the LLM's one-line reasoning under the box.
                    if (reasonEl && d.reasoning) { reasonEl.textContent = d.reasoning; reasonEl.classList.remove('hidden'); }
                } catch (e) {
                    window.showToast?.(t('artsmoker.ui.asset_viewer.suggest_prompt_failed'), 'error');
                } finally {
                    if (sbtn) sbtn.disabled = false;
                    if (label) label.textContent = origLabel;
                }
            });

            // Generate / Apply Edit
            this._overlay.querySelector('#av-edit-generate')?.addEventListener('click', async () => {
                const statusEl = this._overlay.querySelector('#av-edit-status');
                const btn = this._overlay.querySelector('#av-edit-generate');
                const model = this._overlay.querySelector('#av-edit-model')?.value;
                const prompt = this._overlay.querySelector('#av-edit-prompt')?.value || '';

                if (!model) {
                    window.showToast?.(t('artsmoker.ui.asset_viewer.select_edit_model'), 'warning');
                    return;
                }

                btn.disabled = true;
                // nosemgrep
                btn.innerHTML = html`<span class="spinner-sm"></span> ${t('artsmoker.ui.asset_viewer.applying')}`;
                if (statusEl) { statusEl.textContent = t('artsmoker.ui.asset_viewer.processing'); statusEl.classList.remove('hidden'); }

                try {
                    // Extract mask from canvas (only for mask-based modes with a
                    // mask-requiring model — Qwen instruction edits need no mask).
                    let maskB64 = null;
                    const needsMask = (editMode === 'inpaint' || editMode === 'erase')
                        && !this._selectedEditModelIsMaskFree();
                    if (needsMask) {
                        const maskResult = this._extractMask(canvas);
                        if (maskResult.isEmpty) {
                            // Belt-and-braces: the Apply gate should prevent this,
                            // but if it's ever reached, block in BOTH the toast AND
                            // the persistent status line (a toast alone was missed
                            // and read as "job submitted").
                            window.showToast?.(t('artsmoker.ui.asset_viewer.no_mask_full'), 'warning');
                            if (statusEl) { statusEl.textContent = t('artsmoker.ui.asset_viewer.no_mask_full'); statusEl.classList.remove('hidden'); }
                            btn.disabled = false;
                            // nosemgrep
                            btn.innerHTML = html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> ${t('artsmoker.ui.asset_viewer.apply_edit')}`;
                            return;
                        }
                        maskB64 = maskResult.data;
                    }

                    const searchPrompt = this._overlay.querySelector('#av-search-prompt')?.value || '';

                    const payload = {
                        source_image_id: this._item?.id,
                        // Edit the VERSION the user selected in the version bar, not
                        // always the latest. The backend honors source_version and
                        // archives correctly; omitting it defaulted every edit to the
                        // current version (asset.png) regardless of the tab selection.
                        source_version: this._currentVersion || undefined,
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
                        // nosemgrep -- serialized HTTP request body; key ordering is irrelevant (not used as an object/map key)
                        body: JSON.stringify(payload),
                    }).then(r => {
                        if (!r.ok) throw new Error(`${r.status}: ${r.statusText}`);
                        return r.json();
                    });

                    // Async edit (e.g. Qwen-Image-Edit on a scale-to-zero endpoint):
                    // the edit runs in the background; the poller saves the new
                    // version when ready. Inform the user and stop — don't reload.
                    if (result.async) {
                        // Match the 3D async UI: surface the job id + submit time so
                        // the user can correlate with the async-jobs strip / logs.
                        const jobInfo = result.async_job_id
                            ? ' ' + t('artsmoker.ui.asset_viewer.edit_async_job_info', {
                                  id: result.async_job_id,
                                  time: new Date().toLocaleTimeString(),
                              })
                            : '';
                        if (statusEl) { statusEl.textContent = t('artsmoker.ui.asset_viewer.edit_async_queued') + jobInfo; }
                        window.showToast?.(t('artsmoker.ui.asset_viewer.edit_async_queued') + jobInfo, 'info');
                        if (window.Gallery?.refresh) window.Gallery.refresh();
                        return;  // finally{} re-enables the button
                    }

                    if (statusEl) { statusEl.textContent = t('artsmoker.ui.asset_viewer.edit_saved', {id: result.id}); }
                    window.showToast?.(t('artsmoker.ui.asset_viewer.edit_success', {model: result.model_label}), 'success');

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
                    if (statusEl) { statusEl.textContent = t('artsmoker.ui.asset_viewer.error_prefix', {message: err.message}); }
                    window.showToast?.(t('artsmoker.ui.asset_viewer.edit_failed') + ': ' + err.message, 'error');
                } finally {
                    btn.disabled = false;
                    // nosemgrep
                    btn.innerHTML = html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> ${t('artsmoker.ui.asset_viewer.apply_edit')}`;
                }
            });
        },

        /** Is the currently-selected edit model a mask-free instruction editor
         *  (e.g. Qwen-Image-Edit)? Such models edit from a text instruction and
         *  do NOT need a painted mask, unlike Stability inpaint/erase. */
        _selectedEditModelIsMaskFree() {
            const key = this._overlay?.querySelector('#av-edit-model')?.value || '';
            return !!(this._maskFreeEditModels && this._maskFreeEditModels[key]);
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
                // Track which edit models are mask-free instruction editors
                // (e.g. Qwen-Image-Edit, model_purpose 'image_edit'). Used to make
                // the mask requirement + UI model-aware: Stability inpaint/erase
                // need a painted mask; Qwen edits from a text instruction alone.
                this._maskFreeEditModels = this._maskFreeEditModels || {};

                for (const [key, cfg] of Object.entries(models)) {
                    // A model qualifies if its purpose matches exactly (Stability
                    // inpaint/outpaint), OR it's a general image-edit model that
                    // declares this capability (e.g. Qwen-Image-Edit — offered
                    // alongside the Stability models when deployed).
                    const capMatch = cfg.model_purpose === 'image_edit'
                        && cfg.capabilities && cfg.capabilities[purpose];
                    if ((cfg.model_purpose === purpose || capMatch) && cfg.enabled) {
                        this._maskFreeEditModels[key] = cfg.model_purpose === 'image_edit';
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
                    opt.textContent = t('artsmoker.ui.asset_viewer.no_models_for_type');
                    sel.appendChild(opt);
                }

                // Apply mask-paint-control visibility for the now-selected model,
                // so the initial state is correct on open (a mask-free default like
                // Qwen hides brush/clear/hint immediately) — not only after a click.
                const maskControls = this._overlay?.querySelector('#av-mask-controls');
                if (maskControls) maskControls.classList.toggle('hidden', this._selectedEditModelIsMaskFree());
                // Re-evaluate the Apply gate now that the model list (and thus
                // mask-free knowledge) is loaded — the canvas-load evaluation may
                // have run before this fetch resolved.
                this._updateApplyEditGate?.();
            }).catch(() => {});
        },

        /**
         * Populate the 3D "Improve the Source" → Extend edit-model selector.
         * The backend's `edit_model` override for op=extend only takes an alternate
         * (instruction-outpaint) path for general image-edit models that declare an
         * outpainting capability (e.g. Qwen-Image-Edit); a plain Stability outpaint
         * key resolves to the same default Bedrock model as "Auto". So we list only
         * those instruction editors plus an Auto default, and hide the row entirely
         * when none is deployed (no meaningful choice to make).
         */
        _load3DExtendModels(root) {
            const sel = root?.querySelector('#av-sr-edit-model');
            const row = root?.querySelector('#av-sr-edit-model-row');
            if (!sel) return;
            fetch(`/api/admin/models`).then(r => r.json()).then(data => {
                const models = data.image_models || {};
                sel.innerHTML = '';
                // "Auto" (value="") → backend resolves the first enabled Bedrock
                // outpainting model, i.e. today's default behaviour.
                const auto = document.createElement('option');
                auto.value = '';
                auto.textContent = t('artsmoker.ui.asset_viewer.edit_model_auto');
                sel.appendChild(auto);
                for (const [key, cfg] of Object.entries(models)) {
                    if (cfg.enabled && cfg.model_purpose === 'image_edit' && cfg.capabilities?.outpainting) {
                        const opt = document.createElement('option');
                        opt.value = key;
                        const _p = cfg.base_price_usd;
                        opt.textContent = (_p != null && _p > 0)
                            ? `${cfg.label} ($${_p.toFixed(2)}/img)` : cfg.label;
                        sel.appendChild(opt);
                    }
                }
                // Only reveal the selector when there's a real alternative to Auto.
                if (row) row.classList.toggle('hidden', sel.options.length <= 1);
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

            // Re-fit when the image SOURCE changes (e.g. switching to a taller
            // extended version) — without this the viewer kept the prior version's
            // scale/pan and the new image overflowed or sat off-centre. Callable
            // from the version switcher; waits for the new image to decode.
            this._refitZoomOnLoad = () => {
                const run = () => requestAnimationFrame(doFit);
                if (img.complete && img.naturalWidth > 0) run();
                else img.addEventListener('load', run, { once: true });
            };

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
            // Per-version flag: the background-removed cutout already exists (cached
            // server-side), so re-opening review won't re-remove BG — used only to
            // pick an accurate button label ("Reviewing…" vs "Removing background…").
            this._sourceCutoutReady = {};
            if (!window._3dActiveJobs) window._3dActiveJobs = {};
        },

        async _update3DContent() {
            const container = this._overlay?.querySelector('#av-3d-content');
            if (!container) return;

            const meta = this._meta;
            if (!meta) {
                // nosemgrep
                container.innerHTML = html`<p class="text-brand-text-muted text-center py-8">${t('artsmoker.ui.asset_viewer.loading_metadata')}</p>`;
                return;
            }

            // Only supported for game_asset and character types
            const assetType = meta.asset_type;
            if (assetType !== 'game_asset' && assetType !== 'character') {
                // nosemgrep
                container.innerHTML = html`
                    <div class="text-center py-8">
                        <p class="text-brand-text-muted">${t('artsmoker.ui.asset_viewer.three_d_unsupported')}</p>
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
                // NO disk-probe fallback here. Whether a version "has" a 3D model
                // is decided SOLELY by its metadata record (above) — probing
                // GET /3d/{ver} would let the serve route's legacy bare-GLB
                // fallback (asset_3d.glb → v1) surface a model under a version
                // that never generated one (e.g. a cropped Original showing the
                // full-body model made from a later outpainted version). With no
                // record for this version, fall through to "Generate Now".

                // No existing 3D model — check if generation is available (model deployed)
                const availability = await API.threeD.check();
                if (!availability || !availability.available) {
                    // nosemgrep
                    container.innerHTML = html`
                        <div class="text-center py-8 space-y-3">
                            <p class="text-brand-text-muted">${t('artsmoker.ui.asset_viewer.three_d_not_deployed')}</p>
                            <button class="btn btn-sm btn-secondary av-3d-open-settings">${t('artsmoker.ui.asset_viewer.three_d_open_settings')}</button>
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
                // nosemgrep
                container.innerHTML = html`<p class="text-red-400 text-center py-8">${t('artsmoker.ui.asset_viewer.three_d_failed')}: ${err.message}</p>`;
            }
        },

        _render3DForm(container, instances = []) {
            // Model chooser — only shown when more than one TripoSG instance is
            // deployed (mirrors the Image Studio model chooser). With 0 or 1
            // instance there's nothing to choose, so the server default is used.
            const showChooser = Array.isArray(instances) && instances.length > 1;
            const chooserHtml = showChooser ? html`
                    <div>
                        <label class="text-xs text-brand-text-muted mb-1 block">${t('artsmoker.ui.asset_viewer.three_d_model')}</label>
                        <select id="av-3d-model" class="input text-sm w-full max-w-xs">
                            ${instances.map((inst, i) => {
                                const ptype = inst.pipeline_type === 'trellis2_full'
                                    ? t('artsmoker.ui.asset_viewer.three_d_pipe_trellis2_full')
                                    : t('artsmoker.ui.asset_viewer.three_d_pipe_triposg');
                                const inst_t = inst.instance_type ? ' · ' + inst.instance_type.replace('ml.', '') : '';
                                const warming = inst.model_ready ? '' : ' · ' + t('artsmoker.ui.asset_viewer.three_d_model_warming');
                                return html`<option value="${inst.model_key}" ${i === 0 ? 'selected' : ''}>${ptype}${inst_t}${warming}</option>`;
                            })}
                        </select>
                        <p class="text-[9px] text-brand-text-dim mt-1 max-w-xs">${t('artsmoker.ui.asset_viewer.three_d_model_hint')}</p>
                    </div>
            ` : '';

            // License / consent panel — shown for whichever pipeline is selected
            // (or the single deployed one). Informational: the binding acceptance
            // happened at DEPLOY time; here we surface it + confirm it's on record.
            const licensePanelHtml = html`<div id="av-3d-license" class="flex-1 min-w-[16rem] rounded-lg border border-brand-border bg-brand-bg/40 p-3 text-[11px] space-y-1 hidden"></div>`;

            // Save-as choice: only when a 3D model ALREADY exists for this
            // version — i.e. this is a regeneration. Lets the user replace the
            // version's default or keep the new result as a side variant
            // (different pipeline / config) alongside it. First-ever 3D skips this.
            const ver = this._currentVersion || 1;
            const hasExisting3D = !!(this._meta?.three_d?.[`v${ver}`]?.variants?.length
                || this._meta?.three_d_versions?.some(v => v.version === ver));
            const saveAsHtml = hasExisting3D ? html`
                    <div class="flex-1 min-w-[16rem] rounded-lg border border-brand-border bg-brand-bg/40 p-3">
                        <label class="text-xs text-brand-text-muted mb-2 block">${t('artsmoker.ui.asset_viewer.three_d_saveas_title')}</label>
                        <label class="flex items-start gap-2 mb-1.5 cursor-pointer">
                            <input type="radio" name="av-3d-saveas" value="default" checked class="mt-0.5" />
                            <span class="text-[11px]"><span class="font-medium">${t('artsmoker.ui.asset_viewer.three_d_saveas_replace')}</span><br><span class="text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_saveas_replace_hint')}</span></span>
                        </label>
                        <label class="flex items-start gap-2 cursor-pointer">
                            <input type="radio" name="av-3d-saveas" value="variant" class="mt-0.5" />
                            <span class="text-[11px]"><span class="font-medium">${t('artsmoker.ui.asset_viewer.three_d_saveas_variant')}</span><br><span class="text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_saveas_variant_hint')}</span></span>
                        </label>
                    </div>
            ` : '';

            // The EXACT background-removed image that will go to the 3D pipeline,
            // shown on the right so the user is crystal-clear on the pipeline input
            // without opening Review. Server caches the cutout (removes BG once).
            // Form "SOURCE FOR 3D" = the version CUTOUT (matches Export + generation).
            const previewUrl = API.threeD.sourcePreviewUrl(this._item?.id, this._currentVersion || 1) + `&t=${Date.now()}`;
            const isSubject = (this._meta?.asset_type === 'character' || this._meta?.asset_type === 'game_asset');
            const previewPanelHtml = html`
                <div class="w-full lg:w-64 lg:flex-shrink-0 space-y-2">
                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider">${t('artsmoker.ui.asset_viewer.three_d_preview_title')}</p>
                    <div class="preview-checkerboard rounded-lg overflow-hidden border border-brand-border flex items-center justify-center" style="height: 220px;">
                        <img id="av-3d-preview-img" src="${previewUrl}" class="w-full h-full object-contain" alt="3D source" />
                    </div>
                    <p class="text-[9px] text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_preview_note')}</p>
                    <!-- Background-removal method for the 3D cutout. Local (free,
                         on-device) is the default; Bedrock (paid, softer edge) is
                         offered explicitly. Threaded into every prepare-source call. -->
                    <div class="flex items-center gap-2">
                        <label class="text-[9px] text-brand-text-muted uppercase tracking-wider flex-shrink-0">${t('artsmoker.ui.asset_viewer.three_d_bg_method')}</label>
                        <select id="av-3d-bg-method" class="input text-[10px] py-0.5 flex-1">
                            <option value="local">${t('artsmoker.ui.asset_viewer.export_method_local')}</option>
                            <option value="bedrock">${t('artsmoker.ui.asset_viewer.export_method_bedrock')}</option>
                        </select>
                    </div>
                    <p id="av-3d-bg-method-hint" class="text-[9px] text-brand-text-dim"></p>
                    ${isSubject ? html`
                    <!-- Improve the Source sits WITH the image it acts on (most intuitive
                         placement) — the sole instance; not duplicated in the button row. -->
                    <button id="av-3d-review" class="btn btn-sm bg-cyan-600 hover:bg-cyan-500 text-white w-full flex items-center justify-center gap-1.5">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"/></svg>
                        <span>${t('artsmoker.ui.asset_viewer.three_d_improve_btn')}</span>
                    </button>
                    <p id="av-3d-review-status" class="text-[9px] text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_review_hint')}</p>` : ''}
                </div>`;

            // nosemgrep
            container.innerHTML = html`
                <div class="flex flex-col lg:flex-row gap-5">
                  <!-- LEFT: controls -->
                  <div class="flex-1 min-w-0 space-y-4">
                    <p class="text-[10px] text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_version_note')}</p>
                    ${chooserHtml}
                    <!-- License + save-as choice sit SIDE-BY-SIDE (wrap on narrow
                         widths) to keep the form compact instead of stacking tall. -->
                    <div class="flex flex-wrap items-stretch gap-3">
                        ${licensePanelHtml}
                        ${saveAsHtml}
                    </div>

                    <!-- Quality preset (real specs: face/vertex detail, not bogus seconds) -->
                    <div>
                        <label class="text-xs text-brand-text-muted mb-1 block">${t('artsmoker.ui.asset_viewer.three_d_quality')}</label>
                        <select id="av-3d-quality" class="input text-sm w-full max-w-xs">
                            <option value="fast">${t('artsmoker.ui.asset_viewer.three_d_quality_fast')}</option>
                            <option value="standard">${t('artsmoker.ui.asset_viewer.three_d_quality_standard')}</option>
                            <option value="high" selected>${t('artsmoker.ui.asset_viewer.three_d_quality_high')}</option>
                        </select>
                        <p id="av-3d-estimate" class="text-[10px] text-brand-text-dim mt-1.5"></p>
                    </div>

                    <!-- Advanced (collapsible) -->
                    <details class="border border-brand-border rounded-lg">
                        <summary class="px-3 py-2 text-xs text-brand-text-muted cursor-pointer hover:text-brand-text">${t('artsmoker.ui.asset_viewer.three_d_advanced')}</summary>
                        <!-- Two-column grid: pairs the fields so the panel is ~half
                             the height (uses the previously-empty right side). -->
                        <div class="px-3 pb-3 pt-2 grid grid-cols-2 gap-x-4 gap-y-3">
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('artsmoker.ui.asset_viewer.three_d_steps')}</label>
                                <div class="flex items-center gap-2">
                                    <input id="av-3d-steps" type="range" min="20" max="100" value="50" class="flex-1 min-w-0" />
                                    <span id="av-3d-steps-label" class="text-[10px] text-brand-text-muted w-6 text-right">50</span>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('artsmoker.ui.asset_viewer.three_d_guidance')}</label>
                                <div class="flex items-center gap-2">
                                    <input id="av-3d-guidance" type="range" min="1" max="20" step="0.5" value="7.5" class="flex-1 min-w-0" />
                                    <span id="av-3d-guidance-label" class="text-[10px] text-brand-text-muted w-6 text-right">7.5</span>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('artsmoker.ui.asset_viewer.three_d_faces')}</label>
                                <select id="av-3d-faces" class="input text-xs w-full">
                                    <option value="0">${t('artsmoker.ui.asset_viewer.three_d_faces_unlimited')}</option>
                                    <option value="50000">50,000</option>
                                    <option value="100000" selected>100,000</option>
                                    <option value="200000">200,000</option>
                                    <option value="300000">300,000</option>
                                </select>
                                <p class="text-[9px] text-brand-text-dim mt-1">${t('artsmoker.ui.asset_viewer.three_d_faces_hint')}</p>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('artsmoker.ui.asset_viewer.three_d_depth')}</label>
                                <select id="av-3d-depth" class="input text-xs w-full">
                                    <option value="128">${t('artsmoker.ui.asset_viewer.three_d_depth_low')}</option>
                                    <option value="256" selected>${t('artsmoker.ui.asset_viewer.three_d_depth_medium')}</option>
                                    <option value="512">${t('artsmoker.ui.asset_viewer.three_d_depth_high')}</option>
                                </select>
                            </div>
                            <div class="col-span-2">
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${t('artsmoker.ui.asset_viewer.three_d_seed')}</label>
                                <input id="av-3d-seed" type="number" class="input text-xs w-full max-w-xs" placeholder="${t('artsmoker.ui.asset_viewer.three_d_seed_placeholder')}" />
                                <p class="text-[9px] text-brand-text-dim mt-1">${t('artsmoker.ui.asset_viewer.three_d_seed_hint')}</p>
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
                            <span>${t('artsmoker.ui.asset_viewer.three_d_generate')}</span>
                        </button>
                    </div>
                    <p class="text-[10px] text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_async_note')}</p>
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
                    ? t('artsmoker.ui.asset_viewer.three_d_est_fullmesh')
                    : `~${facesVal.toLocaleString()} ${t('artsmoker.ui.asset_viewer.three_d_est_faces')}`;
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
                    ? html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('artsmoker.ui.asset_viewer.three_d_lic_commercial')}</span>`
                    : (inst.commercial === false
                        ? html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${t('artsmoker.ui.asset_viewer.three_d_lic_noncommercial')}</span>`
                        : '');
                const acceptedLine = inst.license_accepted
                    ? html`<p class="text-emerald-400/90">✓ ${t('artsmoker.ui.asset_viewer.three_d_lic_accepted')}${inst.license_accepted_at ? ' · ' + window.formatTimestamp(inst.license_accepted_at) : ''}</p>`
                    : html`<p class="text-amber-400/90">⚠ ${t('artsmoker.ui.asset_viewer.three_d_lic_not_recorded')}</p>`;
                const link = inst.license_url
                    ? html` <a href="${inst.license_url}" target="_blank" rel="noopener" class="text-brand-accent underline">${t('artsmoker.ui.asset_viewer.three_d_lic_view')}</a>`
                    : '';
                // nosemgrep
                licenseEl.innerHTML = html`
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-brand-text-muted">${t('artsmoker.ui.asset_viewer.three_d_lic_label')}</span>
                        <span class="text-brand-text font-medium">${inst.license_name}</span>
                        ${commercialBadge}
                    </div>
                    ${acceptedLine}
                    <p class="text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_lic_note')}${link}</p>`;
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

            // Background-removal method selector: keep the cost hint in sync.
            const bgSel = container.querySelector('#av-3d-bg-method');
            bgSel?.addEventListener('change', () => this._update3DBgMethodHint(container));
            this._update3DBgMethodHint(container);
        },

        /** Cost hint for the 3D background-removal method selector. */
        _update3DBgMethodHint(scope) {
            const sel = scope?.querySelector?.('#av-3d-bg-method');
            const hint = scope?.querySelector?.('#av-3d-bg-method-hint');
            if (!sel || !hint) return;
            hint.textContent = sel.value === 'bedrock'
                ? t('artsmoker.ui.asset_viewer.export_method_bedrock_hint')
                : t('artsmoker.ui.asset_viewer.export_method_local_hint');
        },

        /** The 3D cutout background-removal method the user selected (default local). */
        _bg3DMethod() {
            return this._overlay?.querySelector('#av-3d-bg-method')?.value || 'local';
        },

        /** Reflect whether the current version's source has been reviewed this session. */
        _update3DReviewStatus(scope) {
            const el = scope?.querySelector?.('#av-3d-review-status');
            if (!el) return;
            const done = this._sourceApprovedVersion === (this._currentVersion || 1);
            el.textContent = done
                ? '✓ ' + t('artsmoker.ui.asset_viewer.three_d_review_done')
                : t('artsmoker.ui.asset_viewer.three_d_review_hint');
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
            // Re-sync to the true current version (backend truth) before reviewing.
            try {
                this._meta = await API.gallery.get(this._item.id);
                if (this._meta?.current_version) this._currentVersion = this._meta.current_version;
            } catch {}
            const version = this._currentVersion || 1;
            // Label the button for what's ACTUALLY about to happen. BG removal is a
            // cached, at-most-once step (server reuses the __cutout sidecar and skips
            // it entirely when the version is already background-free) — so only show
            // "Removing background…" the FIRST time, when no cutout exists yet.
            // Otherwise this is just a re-analysis, so show "Reviewing…".
            if (reviewBtn) {
                reviewBtn.disabled = true;
                // No removal needed if we've already prepared the cutout this session
                // OR the current version is itself a background-removed edit (the
                // server serves it directly, skipping removal). Check the version's
                // recorded type/op — mirrors the backend's _version_is_bg_free.
                const vrec = (this._meta?.versions || []).find(v => v.version === version);
                const alreadyBgFree = vrec && (vrec.type === 'remove_background'
                    || (vrec.edit_context && vrec.edit_context.op === 'remove_background'));
                const needsBgRemoval = !this._sourceCutoutReady?.[version] && !alreadyBgFree;
                // nosemgrep
                reviewBtn.innerHTML = html`<span class="spinner-sm"></span> ${needsBgRemoval
                    ? t('artsmoker.ui.asset_viewer.three_d_src_removing_bg')
                    : t('artsmoker.ui.asset_viewer.three_d_src_reviewing')}`;
            }
            // Start each improve session from the CLEAN cutout: drop any stale or
            // uncommitted prepared source (__source) from a prior session. With
            // commit-time versioning, uncommitted improve work isn't persisted —
            // and this also clears legacy pre-versioning __source sidecars so the
            // dialog never shows an old full-body source under a cropped Original.
            try {
                await API.threeD.prepareSource({ asset_id: this._item?.id, version, op: 'reset', bg_method: this._bg3DMethod() });
            } catch (e) { /* best-effort */ }
            // Ensure the cutout exists + get an initial completeness verdict. One call
            // (op:'cutout') removes BG once (cached) and returns the analysis. Retry
            // once on a transient failure before falling back to "review & decide".
            let analysis = null;
            for (let attempt = 0; attempt < 2 && !(analysis && analysis.analyzed); attempt++) {
                try {
                    const r = await API.threeD.prepareSource({ asset_id: this._item?.id, version, op: 'cutout', bg_method: this._bg3DMethod() });
                    analysis = r?.analysis || null;
                    // The cutout now exists (cached server-side) — future reviews of
                    // this version won't re-remove the background, so label them
                    // "Reviewing…" rather than "Removing background…".
                    (this._sourceCutoutReady = this._sourceCutoutReady || {})[version] = true;
                } catch (e) {
                    console.warn('[3D] source prepare/analysis failed, attempt', attempt + 1, e);
                }
            }
            // The cutout now exists server-side (the SAME canonical file the Export &
            // Cutouts tab renders). Refresh that tab's cached status + grid so it
            // reflects the new cutout in this session — previously the export status
            // was cached at first view (no cutout) and never re-fetched, so the PNG
            // cutout stayed blank until the dialog was closed and reopened.
            if (this._sourceCutoutReady?.[version]) {
                this._exportStatus = null;
                this._renderExportPanel?.();
            }
            // Self-contained review dialog — stays open through every Extend/Fill,
            // shows progress in place, resolves only on "Use this image" / "Cancel".
            const result = await this._showSourceReview(version, analysis || { analyzed: false });
            if (result && result.approved) {
                this._sourceApprovedVersion = version;
                // Commit-time versioning (Option A): if the user actually improved
                // the source (ran Extend/Fill), materialize the prepared image as a
                // NEW 2D version and switch to it — so any 3D generated now attributes
                // to the improved version, and the untouched Original stays clean.
                // If nothing was changed, no version is created (generate from Original
                // as-is, as before).
                if (Array.isArray(result.ops) && result.ops.length) {
                    try {
                        const c = await API.threeD.commitSource(this._item?.id, version, result.ops, result.prompt || '');
                        if (c && c.committed) {
                            this._meta = await API.gallery.get(this._item.id);
                            this._currentVersion = c.version;
                            this._sourceApprovedVersion = c.version;
                            if (window.Gallery?.refresh) window.Gallery.refresh();
                            window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_src_committed', { version: c.version }), 'success');
                        }
                    } catch (e) {
                        window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_src_commit_failed') + (e.message ? ': ' + e.message : ''), 'error');
                    }
                }
            }
            // Rebuild the form (refreshes the SOURCE preview to the prepared image).
            this._update3DContent();
        },

        async _submit3DGeneration() {
            const container = this._overlay?.querySelector('#av-3d-content');
            const btn = container?.querySelector('#av-3d-generate');
            if (!btn || btn.disabled) return;

            btn.disabled = true;
            // nosemgrep
            btn.innerHTML = html`<span class="spinner-sm"></span> ${t('artsmoker.ui.asset_viewer.three_d_generating')}`;

            // S3 bucket preflight — 3D generation runs on a custom (self-hosted)
            // endpoint that needs the deployment bucket for its async input/output.
            // Catch a missing bucket here with a clear pointer instead of a failed
            // job. (A deployed 3D endpoint usually implies a bucket was set, but the
            // bucket can be cleared later — so we still guard.)
            try {
                const st = await (await fetch('/api/custom-models/s3-bucket-status')).json();
                if (!st.ok) {
                    this._reset3DGenerateBtn(btn);
                    const go = await window.showConfirm?.(
                        st.message || t('artsmoker.ui.custom_models.bucket_required_desc'),
                        {
                            title: t('artsmoker.ui.custom_models.bucket_required_title'),
                            detail: t('artsmoker.ui.custom_models.s3_set_in_settings'),
                            confirmLabel: t('artsmoker.ui.custom_models.open_model_settings'),
                            cancelLabel: t('artsmoker.ui.common.cancel'),
                        },
                    );
                    if (go) window.ModelSettings?.open?.('custom-models');
                    return;
                }
            } catch { /* status endpoint unreachable — let backend guard handle it */ }

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
                window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_pending'), 'info');
                // Parallel-jobs model: the new job joins the in-progress strip
                // (poller picks it up); the main content re-renders to the current
                // state (existing model or a fresh form) so another job can be
                // fired immediately. No full-panel takeover.
                this._start3DJobsPolling(true);
                this._update3DContent();
            } catch (err) {
                window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_failed') + ': ' + err.message, 'error');
                this._reset3DGenerateBtn(btn);
            }
        },

        /** Restore the Generate-3D button to its idle state. */
        _reset3DGenerateBtn(btn) {
            if (!btn) return;
            btn.disabled = false;
            // nosemgrep
            btn.innerHTML = html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg> <span>${t('artsmoker.ui.asset_viewer.three_d_generate')}</span>`;
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
                // Review dialog shows the LIVE working source (prepared=true) so
                // each Extend/Fill round is visible during the session.
                const srcUrlFor = () => API.threeD.sourcePreviewUrl(this._item?.id, version, true) + `&t=${Date.now()}`;

                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[130] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
                // nosemgrep
                backdrop.innerHTML = html`
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full p-5 space-y-4 max-h-[92vh] overflow-y-auto relative">
                        <div>
                            <h3 class="text-sm font-semibold text-brand-text">${t('artsmoker.ui.asset_viewer.three_d_src_pv_confirm_title')}</h3>
                            <p id="av-sr-verdict" class="text-xs mt-1"></p>
                            <p class="text-[11px] text-brand-text-dim mt-1">${t('artsmoker.ui.asset_viewer.three_d_src_pv_confirm_sub')} ${t('artsmoker.ui.asset_viewer.three_d_src_pv_confirm_sub2')}</p>
                        </div>
                        <div class="preview-checkerboard rounded-lg overflow-hidden border border-brand-accent/40 flex items-center justify-center relative" style="height: 360px;">
                            <img id="av-sr-img" src="${srcUrlFor()}" class="w-full h-full object-contain" alt="3D source" crossorigin="anonymous" />
                            <canvas id="av-sr-mask" class="cursor-crosshair hidden" style="max-width:100%; max-height:360px;"></canvas>
                            <canvas id="av-sr-measure" class="absolute inset-0 w-full h-full pointer-events-none hidden"></canvas>
                        </div>
                        <div id="av-sr-stats" class="text-[10px] text-brand-text-muted flex flex-wrap items-center gap-x-4 gap-y-1 px-1 hidden"></div>

                        <!-- Fill / Replace panel (mask brush) — hidden until Fill is chosen. -->
                        <div id="av-sr-fill-panel" class="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 space-y-2 hidden">
                            <div class="flex items-center justify-between">
                                <p class="text-[11px] text-amber-400">${t('artsmoker.ui.asset_viewer.three_d_src_pv_fix_hint')}</p>
                                <div class="flex items-center gap-2">
                                    <label class="text-[9px] text-brand-text-muted">${t('artsmoker.ui.asset_viewer.brush_size')}</label>
                                    <input id="av-sr-brush" type="range" min="8" max="80" value="28" class="w-20" />
                                    <button class="av-sr-mask-clear text-[10px] text-brand-text-muted hover:text-brand-text underline">${t('artsmoker.ui.asset_viewer.clear_mask')}</button>
                                </div>
                            </div>
                            <textarea id="av-sr-fill-prompt" rows="2" class="input text-xs w-full" placeholder="${t('artsmoker.ui.asset_viewer.three_d_src_fix_ph')}"></textarea>
                        </div>

                        <!-- Extend panel (directions) — hidden until Extend is chosen. -->
                        <details id="av-sr-extend-panel" class="border border-brand-border rounded-lg hidden">
                            <summary class="px-3 py-2 text-[11px] text-brand-text-muted cursor-pointer">${t('artsmoker.ui.asset_viewer.three_d_src_pv_adjust')}</summary>
                            <div class="px-3 pb-3 pt-1 space-y-2">
                                <div>
                                    <label class="text-[9px] text-brand-text-muted uppercase tracking-wider">${t('artsmoker.ui.asset_viewer.three_d_src_prompt_label')}</label>
                                    <textarea id="av-sr-prompt" rows="2" class="input text-xs w-full" placeholder="${t('artsmoker.ui.asset_viewer.three_d_src_prompt_ph')}"></textarea>
                                </div>
                                <!-- Optional edit-model override — shown only when an instruction editor is deployed. -->
                                <div id="av-sr-edit-model-row" class="hidden">
                                    <label class="text-[9px] text-brand-text-muted uppercase tracking-wider">${t('artsmoker.ui.asset_viewer.edit_model')}</label>
                                    <select id="av-sr-edit-model" class="input text-xs w-full"></select>
                                </div>
                                <div class="grid grid-cols-4 gap-2">
                                    ${['left','right','up','down'].map(dd => html`
                                        <div><label class="text-[9px] text-brand-text-muted">${t('artsmoker.ui.asset_viewer.outpaint_' + dd)}</label>
                                        <input id="av-sr-${dd}" type="number" min="0" max="2000" value="0" class="input text-xs w-full" /></div>`)}
                                </div>
                                <p class="text-[9px] text-brand-text-dim">${t('artsmoker.ui.asset_viewer.three_d_src_pv_extend_note')}</p>
                            </div>
                        </details>

                        <!-- Actions: Use this image · Extend · Fill/Replace -->
                        <div class="grid grid-cols-3 gap-2">
                            <button class="av-sr-use btn btn-sm bg-brand-accent hover:bg-brand-accent-hover text-white rounded-lg py-3 text-xs font-medium leading-tight">${t('artsmoker.ui.asset_viewer.three_d_src_pv_approve')}</button>
                            <button class="av-sr-extend btn btn-sm btn-secondary rounded-lg py-3 text-xs font-medium leading-tight">${t('artsmoker.ui.asset_viewer.three_d_src_pv_extend_it')}</button>
                            <button class="av-sr-fill btn btn-sm btn-secondary rounded-lg py-3 text-xs font-medium leading-tight">${t('artsmoker.ui.asset_viewer.three_d_src_pv_fill')}</button>
                        </div>
                        <button class="av-sr-cancel text-[11px] text-brand-text-muted hover:text-red-400 w-full text-center">${t('artsmoker.ui.asset_viewer.three_d_src_pv_cancel')}</button>

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
                // Track which improve ops actually ran + the last prompt used, so
                // the commit-time versioning (on "Use this for 3D") can create a
                // truthfully-typed new 2D version only when a change was made.
                const opsRun = new Set();
                let lastImprovePrompt = '';

                const done = (v) => {
                    this._redrawMeasurement = null;
                    backdrop.remove();
                    resolve(v ? { approved: true, ops: [...opsRun], prompt: lastImprovePrompt }
                              : { approved: false });
                };
                const setBusy = (on, text) => {
                    working = on;
                    busy.style.display = on ? 'flex' : 'none';
                    if (text) busyText.textContent = text;
                    [useBtn, extendBtn, fillBtn].forEach(b => { if (b) b.disabled = on; });
                };
                const readDirs = () => {
                    // nosemgrep -- $ is a local backdrop.querySelector shim (not jQuery); dd is a fixed left/right/up/down set, never user data
                    const g = (dd) => { const n = parseInt($(`#av-sr-${dd}`)?.value || '0', 10); return Number.isFinite(n) ? Math.max(0, Math.min(2000, n)) : 0; };
                    return { left: g('left'), right: g('right'), up: g('up'), down: g('down') };
                };

                // Render the current verdict line from an analysis object.
                const renderVerdict = (a) => {
                    const analyzed = !!(a && a.analyzed);
                    const defect = (analyzed && a.complete === false) ? (a.defect === 'artifact' ? 'artifact' : 'cropped') : 'none';
                    const el = $('#av-sr-verdict');
                    // nosemgrep
                    if (!analyzed) el.innerHTML = html`<span class="text-brand-text-muted">${t('artsmoker.ui.asset_viewer.three_d_src_pv_unchecked')}</span>`;
                    // nosemgrep
                    else if (defect === 'none') el.innerHTML = html`<span class="text-emerald-400">✓ ${t('artsmoker.ui.asset_viewer.three_d_src_pv_good')}</span>`;
                    // nosemgrep
                    else el.innerHTML = html`<span class="text-amber-400">⚠ ${a.reason || t('artsmoker.ui.asset_viewer.three_d_src_still')}</span>`;
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
                    // nosemgrep -- $ is a local backdrop.querySelector shim (not jQuery); dd is a fixed left/right/up/down set, never user data
                    ['left', 'right', 'up', 'down'].forEach(dd => { const el = $(`#av-sr-${dd}`); if (el) el.value = sg[dd] || 0; });
                    const p = $('#av-sr-prompt'); if (p && a && a.outpaint_prompt) p.value = a.outpaint_prompt;
                };

                let lastAnalysis = analysis;
                const { defect: initialDefect } = renderVerdict(analysis);
                seedFromAnalysis(analysis);
                // Populate the (optional) Extend edit-model selector. Instruction
                // editors like Qwen-Image-Edit run an alternate outpaint recipe; the
                // row stays hidden when none is deployed (default Bedrock outpaint).
                this._load3DExtendModels(backdrop);
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
                        const r = await API.threeD.prepareSource({ asset_id: this._item?.id, version, bg_method: this._bg3DMethod(), ...payload });
                        // Record the improvement so commit-time versioning knows a
                        // change was made (and its type/prompt) — extend/inpaint only.
                        if (payload.op === 'extend' || payload.op === 'inpaint') {
                            opsRun.add(payload.op);
                            if (payload.prompt) lastImprovePrompt = payload.prompt;
                        }
                        lastAnalysis = r?.analysis || lastAnalysis;
                        disableFillMode();
                        refreshImage();
                        renderVerdict(lastAnalysis);
                        seedFromAnalysis(lastAnalysis);
                    } catch (e) {
                        window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_src_failed') + (e.message ? ': ' + e.message : ''), 'error');
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
                    runOp({ op: 'extend', ...dirs, prompt: $('#av-sr-prompt')?.value || '', edit_model: $('#av-sr-edit-model')?.value || '' },
                        t('artsmoker.ui.asset_viewer.three_d_src_completing'));
                });
                // Live measurement redraw as the user tweaks amounts. Snap any
                // negative entry back to 0 — extension can't be negative.
                ['left', 'right', 'up', 'down'].forEach(dd => {
                    // nosemgrep -- $ is a local backdrop.querySelector shim (not jQuery); dd is a fixed left/right/up/down set, never user data
                    $(`#av-sr-${dd}`)?.addEventListener('input', (e) => {
                        if (e.target && parseInt(e.target.value, 10) < 0) e.target.value = '0';
                        this._redrawMeasurement?.();
                    });
                });

                // Fill: first click enters mask mode; second (with a mask) runs.
                fillBtn.addEventListener('click', () => {
                    if (working) return;
                    if (!fillMode) { enableFillMode(); return; }
                    const m = this._extractMask(maskCanvas);
                    if (m.isEmpty) { window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_src_nomask'), 'warning'); return; }
                    runOp({ op: 'inpaint', mask: m.data, prompt: $('#av-sr-fill-prompt')?.value || '' },
                        t('artsmoker.ui.asset_viewer.three_d_src_fixing'));
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
        _wireMeasurement(backdrop, imgUrl, readDirs, sel) {
            // sel = {img, measure, stats} element selectors. Defaults to the 3D
            // source-review dialog's ids; the Edit tab passes its own (#av-out-*)
            // so ONE renderer serves both surfaces. `dirKeys` maps the readDirs()
            // shape: the 3D dialog returns {top,...} while the Edit tab returns
            // {up,...} — normalized in _drawMeasurement.
            sel = sel || { img: '#av-sr-img', measure: '#av-sr-measure', stats: '#av-sr-stats' };
            const overlay = backdrop.querySelector(sel.measure);
            const statsEl = backdrop.querySelector(sel.stats);
            const wrap = overlay?.parentElement;   // the fixed-height preview box
            if (!overlay || !wrap) return;
            // Point the VISIBLE <img> at this URL so it actually displays the picture
            // (the Edit tab leaves it blank in markup; the 3D dialog pre-fills it, but
            // re-pointing it on a version switch is correct there too). We annotate the
            // overlay canvas over it. cache-bust is already in imgUrl.
            const visibleImg = backdrop.querySelector(sel.img);
            if (visibleImg && visibleImg.getAttribute('src') !== imgUrl) visibleImg.src = imgUrl;
            // Remember the selectors + stats target on the overlay so _drawMeasurement
            // (called via _redrawMeasurement) resolves the right elements.
            overlay._sel = sel;
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
                        const tag = cropped ? ` ${t('artsmoker.ui.asset_viewer.three_d_measure_cropped')}` : '';
                        // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                        return `<span class="${cls}">${t('artsmoker.ui.asset_viewer.outpaint_' + edge)} ${val}px${tag}</span>`;
                    };
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    let statsHtml = `<span><span class="text-brand-text">${t('artsmoker.ui.asset_viewer.three_d_measure_size')}</span> ${W}×${H}px</span>`;
                    if (bbox) {
                        // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                        statsHtml += `<span><span class="text-brand-text">${t('artsmoker.ui.asset_viewer.three_d_measure_fill')}</span> ${pct}</span>`;
                        // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                        statsHtml += `<span class="flex items-center gap-2"><span class="text-brand-text">${t('artsmoker.ui.asset_viewer.three_d_measure_margins')}:</span> `
                            + ['up', 'down', 'left', 'right'].map(e => marginChip(e, bbox[{ up: 'top', down: 'bottom', left: 'left', right: 'right' }[e]])).join(' · ')
                            + `</span>`;
                        statsHtml += `<span id="av-sr-newsize" class="text-brand-accent"></span>`;
                        // nosemgrep
                        statsEl.innerHTML = html`<div class="flex flex-wrap items-center gap-x-4 gap-y-1">${raw(statsHtml)}</div>`
                            + html`<div class="w-full text-brand-text-dim mt-0.5">${t('artsmoker.ui.asset_viewer.three_d_measure_hint')}</div>`;
                    } else {
                        // nosemgrep
                        statsEl.innerHTML = html`<div class="flex flex-wrap items-center gap-x-4 gap-y-1">${raw(statsHtml)}`
                            + html`<span id="av-sr-newsize" class="text-brand-accent"></span></div>`
                            + html`<div class="w-full text-brand-text-dim mt-0.5">${t('artsmoker.ui.asset_viewer.three_d_measure_nobg')}</div>`;
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
            // Normalize the directions: 3D dialog returns {top,down,left,right};
            // the Edit tab returns {up,down,left,right}. Accept either.
            const raw = readDirs() || {};
            const d = { top: raw.top ?? raw.up ?? 0, down: raw.down ?? 0, left: raw.left ?? 0, right: raw.right ?? 0 };
            const rect = wrap.getBoundingClientRect();
            // The dialog may not be laid out yet (cached image → onload before the
            // dialog is in the DOM). Retry next frame until the box has a real size.
            // If the preview box isn't laid out yet, retry next frame — BUT only if
            // it's actually on-screen. offsetParent is null when an ancestor is
            // display:none (e.g. the Edit tab's outpaint section while another mode
            // is active), which would otherwise spin an infinite rAF loop.
            if (rect.width < 2 || rect.height < 2) {
                if (wrap.offsetParent !== null) {
                    requestAnimationFrame(() => this._redrawMeasurement && this._redrawMeasurement());
                }
                return;
            }
            const dpr = window.devicePixelRatio || 1;
            overlay.width = Math.round(rect.width * dpr);
            overlay.height = Math.round(rect.height * dpr);
            const ctx = overlay.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, rect.width, rect.height);

            // A ruler GUTTER is reserved along the top + left edges — the ruler is
            // drawn there, OUTSIDE the image, never overlapping it (a proper
            // editor-style ruler). The extended frame is laid out in the remaining
            // content region (box minus the gutter).
            const GUT = 22;  // gutter thickness in CSS px (top + left)
            const contentW = Math.max(2, rect.width - GUT);
            const contentH = Math.max(2, rect.height - GUT);

            // GROWING-FRAME layout: we lay out the FULL extended canvas (original +
            // all margins) and scale THAT to fit the CONTENT region. As the user adds
            // margins, totalW/H grow, the scale shrinks, and the original image visibly
            // shrinks inside the growing frame — so you can see how much bigger the
            // image gets with each dimension change. The image is inset by the top/left
            // margins; extension bands fill the rest.
            const totalW = W + d.left + d.right;
            const totalH = H + d.top + d.down;
            const scale = Math.min(contentW / totalW, contentH / totalH);
            const frameW = totalW * scale, frameH = totalH * scale;
            // Centre the extended frame within the content region (offset past gutter).
            const frameX = GUT + (contentW - frameW) / 2, frameY = GUT + (contentH - frameH) / 2;
            // Original image position within the frame (offset by top/left margins).
            const imgX = frameX + d.left * scale, imgY = frameY + d.top * scale;
            const imgW = W * scale, imgH = H * scale;
            // Coordinates in TRUE image pixels → canvas (relative to the image origin).
            const toX = (ix) => imgX + ix * scale;
            const toY = (iy) => imgY + iy * scale;

            // Position the VISIBLE <img> to exactly the inset image rect so it shrinks
            // and repositions in lockstep with the growing frame (the canvas overlay
            // draws bands/rulers around it). Switch it from object-contain fill to an
            // absolutely-placed element matching imgX/imgY/imgW/imgH.
            const visImg = backdrop.querySelector((overlay._sel || {}).img || '#av-sr-img');
            if (visImg) {
                visImg.style.position = 'absolute';
                visImg.style.left = imgX + 'px';
                visImg.style.top = imgY + 'px';
                visImg.style.width = imgW + 'px';
                visImg.style.height = imgH + 'px';
                visImg.style.objectFit = 'fill';  // rect already matches aspect
            }

            // Extension zone: wash over the WHOLE extended frame, then the opaque
            // original image is represented by the visible <img> beneath — so we cut
            // a "hole" by only washing the margin areas. Simpler: wash the full frame
            // lightly; the image sits on top via the HTML <img> (object-contain), but
            // since the frame no longer matches the <img> placement, we instead draw
            // the wash only in the margin bands around the inset image.
            ctx.fillStyle = 'rgba(124, 104, 238, 0.28)';
            if (d.top > 0)   ctx.fillRect(frameX, frameY, frameW, imgY - frameY);
            if (d.down > 0)  ctx.fillRect(frameX, imgY + imgH, frameW, (frameY + frameH) - (imgY + imgH));
            if (d.left > 0)  ctx.fillRect(frameX, imgY, imgX - frameX, imgH);
            if (d.right > 0) ctx.fillRect(imgX + imgW, imgY, (frameX + frameW) - (imgX + imgW), imgH);

            // Outer frame = the FINAL extended bounds (dashed indigo).
            ctx.save();
            ctx.setLineDash([6, 4]);
            ctx.strokeStyle = 'rgba(129,140,248,0.9)'; ctx.lineWidth = 1.5;
            ctx.strokeRect(frameX + 0.5, frameY + 0.5, frameW - 1, frameH - 1);
            ctx.restore();

            // Original-image frame (solid).
            ctx.strokeStyle = 'rgba(220,225,235,0.9)'; ctx.lineWidth = 1.5;
            ctx.strokeRect(imgX + 0.5, imgY + 0.5, imgW, imgH);

            // Subject bbox (if a silhouette was measured) — dashed emerald box.
            if (bbox) {
                ctx.save();
                ctx.strokeStyle = 'rgba(52, 211, 153, 0.9)'; ctx.setLineDash([4, 3]); ctx.lineWidth = 1.5;
                ctx.strokeRect(toX(bbox.left) + 0.5, toY(bbox.top) + 0.5, bbox.w * scale, bbox.h * scale);
                ctx.restore();
            }

            // Rulers in the GUTTER (outside the frame): the top ruler measures the
            // final width (0 → totalW), the left ruler the final height (0 → totalH),
            // aligned to the extended frame's edges. Ticks + labels live entirely in
            // the gutter so they never overlap the image.
            ctx.save();
            // Gutter backgrounds.
            ctx.fillStyle = 'rgba(15,18,28,0.55)';
            ctx.fillRect(0, 0, rect.width, GUT);   // top gutter
            ctx.fillRect(0, 0, GUT, rect.height);  // left gutter
            ctx.fillStyle = 'rgba(210,215,230,0.95)';
            ctx.strokeStyle = 'rgba(150,158,178,0.8)';
            ctx.lineWidth = 1; ctx.font = '9px ui-monospace, monospace';
            const step = Math.max(totalW, totalH) > 1400 ? 512 : 256;
            const fToX = (px) => frameX + px * scale;   // frame-pixel → canvas x
            const fToY = (py) => frameY + py * scale;   // frame-pixel → canvas y
            // Top ruler (X: 0..totalW). 0 and the endpoint are always labelled.
            const xs = new Set([0, totalW]);
            for (let px = 0; px <= totalW; px += step) xs.add(px);
            ctx.textBaseline = 'bottom';
            xs.forEach(px => {
                const x = fToX(px);
                if (x < GUT - 1 || x > rect.width + 1) return;
                const end = (px === 0 || px === totalW);
                ctx.beginPath(); ctx.moveTo(x, GUT); ctx.lineTo(x, GUT - (end ? 7 : 4)); ctx.stroke();
                ctx.textAlign = px === 0 ? 'left' : px === totalW ? 'right' : 'center';
                ctx.fillText(String(px), Math.min(Math.max(x, GUT), rect.width - 1), GUT - 8);
            });
            // Left ruler (Y: 0..totalH) — labels rotated to read vertically.
            const ys = new Set([0, totalH]);
            for (let py = 0; py <= totalH; py += step) ys.add(py);
            ys.forEach(py => {
                const y = fToY(py);
                if (y < GUT - 1 || y > rect.height + 1) return;
                const end = (py === 0 || py === totalH);
                ctx.beginPath(); ctx.moveTo(GUT, y); ctx.lineTo(GUT - (end ? 7 : 4), y); ctx.stroke();
                ctx.save();
                ctx.translate(GUT - 9, Math.min(Math.max(y, GUT), rect.height - 1));
                ctx.rotate(-Math.PI / 2);
                ctx.textAlign = py === 0 ? 'right' : py === totalH ? 'left' : 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillText(String(py), 0, 0);
                ctx.restore();
            });
            ctx.restore();

            // Live "new canvas size" readout in the stats line. The newsize span is
            // injected inside the stats element (id 'av-sr-newsize'), which exists
            // once per surface — scope the lookup to this surface's stats element so
            // the 3D dialog and the Edit tab don't collide.
            const fW = W + d.left + d.right, fH = H + d.top + d.down;
            const statsEl = backdrop.querySelector((overlay._sel || {}).stats || '#av-sr-stats');
            const newSizeEl = statsEl?.querySelector('#av-sr-newsize') || backdrop.querySelector('#av-sr-newsize');
            if (newSizeEl) {
                newSizeEl.textContent = (d.left || d.right || d.top || d.down)
                    ? `${t('artsmoker.ui.asset_viewer.three_d_measure_newsize')} ${fW}×${fH}px`
                    : '';
            }
        },


        _render3DPending(container, jobId) {
            // nosemgrep
            container.innerHTML = html`
                <div class="text-center py-8 space-y-4">
                    <div class="loading-spinner w-6 h-6 border-2 border-brand-accent/20 border-t-brand-accent rounded-full mx-auto"></div>
                    <div>
                        <p class="text-brand-text">${t('artsmoker.ui.asset_viewer.three_d_pending_title')}</p>
                        <p class="text-[10px] text-brand-text-muted mt-1">${t('artsmoker.ui.asset_viewer.three_d_pending_subtitle')}</p>
                    </div>
                    <p class="text-[9px] text-brand-text-dim font-mono">${t('artsmoker.ui.asset_viewer.three_d_job_id')}: ${jobId}</p>
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
            // nosemgrep
            strip.innerHTML = html`
                <div class="rounded-lg border border-brand-accent/30 bg-brand-accent/5 px-3 py-2">
                    <div class="flex items-center gap-2 mb-1.5">
                        <div class="loading-spinner w-3.5 h-3.5 border-2 border-brand-accent/30 border-t-brand-accent rounded-full"></div>
                        <span class="text-[10px] text-brand-text-muted uppercase tracking-wider">${t('artsmoker.ui.asset_viewer.three_d_jobs_running')} (${jobs.length})</span>
                    </div>
                    <div class="space-y-1">
                        ${jobs.map(j => html`
                            <div class="flex items-center justify-between gap-2 text-[11px]">
                                <span class="text-brand-text">${j.label || j.model_key || '3D'}</span>
                                <span class="text-[9px] font-mono text-brand-text-dim">${j.status} · ${j.job_id}</span>
                            </div>`)}
                    </div>
                </div>`;
        },

        /** Build an engine-export URL for the current 3D asset/version/variant,
         *  including the user's prep-op picks (packing/LODs/collision/UV2 — only
         *  what was explicitly chosen). fmt ∈ glb|fbx|usd; GLB ignores all of it. */
        _exportUrl(fmt, target) {
            const id = encodeURIComponent(this._meta?.id || this._item?.id || '');
            const ver = this._currentVersion || 1;
            const q = new URLSearchParams({ target: target || 'generic' });
            if (this._current3DVariant) q.set('variant', this._current3DVariant);
            const opt = (sel) => document.getElementById(sel)?.value || 'none';
            const pack = opt('av-3d-opt-pack'), lods = opt('av-3d-opt-lods'),
                  collision = opt('av-3d-opt-collision'), uv2 = opt('av-3d-opt-uv2');
            if (pack !== 'none') q.set('pack', pack);
            if (lods !== 'none') q.set('lods', lods);
            if (collision !== 'none') q.set('collision', collision);
            if (uv2 !== 'none') q.set('uv2', uv2);
            return `/api/gallery/${id}/3d/${ver}/export/${fmt}?${q.toString()}`;
        },

        /** Descriptive download filename for an engine export ({slug}_vN_{ts}_{target}.{ext}). */
        _exportDownloadName(ext, target) {
            const ver = this._currentVersion || 1;
            const vrec = (this._meta?.versions || []).find(v => v.version === ver);
            const base = this._versionDownloadName(ext, ver, vrec);   // {slug}_vN_{ts}.{ext}
            return base.replace(new RegExp(`\\.${ext}$`, 'i'), `_${target}.${ext}`);
        },

        /** Render the "Ready to download" chip row: one compact chip per export
         *  already generated for the CURRENT version (recorded in metadata's
         *  three_d_exports). Click = instant download of that exact file; tooltip
         *  carries the full option labels + size. Hidden when none exist. */
        _renderReadyExports() {
            const row = document.getElementById('av-3d-ready-exports');
            if (!row) return;
            const ver = this._currentVersion || 1;
            const all = this._meta?.three_d_exports || {};
            const items = Object.entries(all).filter(([, r]) => (r.version || 1) === ver);
            if (!items.length) { row.classList.remove('flex'); row.classList.add('hidden'); return; }
            const targetLabel = (key) => {
                const hit = (this._exportTargets || []).find(tt => tt.key === key);
                return hit ? hit.label : key;
            };
            const optLabel = (v) => t(`artsmoker.ui.asset_viewer.three_d_optval_${v}`) || v;
            const fmtMB = (b) => b ? `${(b / 1048576).toFixed(1)} MB` : '';
            // nosemgrep
            row.innerHTML = html`
                <span class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.asset_viewer.three_d_ready_exports')}</span>
                ${items.map(([fname, r]) => {
                    const ops = Object.values(r.ops || {});
                    const opsShort = ops.length ? ` · ${ops.join('+')}` : '';
                    const tip = [targetLabel(r.target), ...ops.map(optLabel), fmtMB(r.size_bytes)]
                        .filter(Boolean).join(' · ');
                    return html`<button class="av-3d-ready-chip px-2 py-0.5 rounded-full text-[10px] border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 transition-colors cursor-pointer"
                        data-fname="${fname}" title="${tip}">
                        ⬇ ${(r.format || '').toUpperCase()}${r.zip ? '+tex' : ''} · ${targetLabel(r.target)}${opsShort}
                    </button>`;
                })}`;
            row.classList.remove('hidden');
            row.classList.add('flex');
            row.querySelectorAll('.av-3d-ready-chip').forEach(btn => {
                btn.addEventListener('click', () => {
                    const r = (this._meta?.three_d_exports || {})[btn.dataset.fname];
                    if (r) this._downloadReadyExport(r);
                });
            });
        },

        /** Download an already-generated export directly from its metadata record
         *  (instant — the file is cached server-side; no regeneration). */
        async _downloadReadyExport(r) {
            const id = encodeURIComponent(this._meta?.id || this._item?.id || '');
            const q = new URLSearchParams({ target: r.target || 'generic' });
            if (r.variant) q.set('variant', r.variant);
            for (const [k, v] of Object.entries(r.ops || {})) q.set(k, v);
            const url = `/api/gallery/${id}/3d/${r.version || 1}/export/${r.format}?${q.toString()}`;
            try {
                const resp = await fetch(url);
                if (!resp.ok) {
                    let detail = '';
                    try { detail = (await resp.json()).detail || ''; } catch { /* non-JSON */ }
                    window.showToast?.((t('artsmoker.ui.asset_viewer.three_d_export_failed') || 'Export failed')
                        + (detail ? `: ${detail}` : ''), 'error');
                    return;
                }
                const blob = await resp.blob();
                const cd = resp.headers.get('Content-Disposition') || '';
                const m = cd.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
                const name = m ? decodeURIComponent(m[1].replace(/"/g, '')) : `asset.${r.format}`;
                const u = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = u; a.download = name;
                document.body.appendChild(a); a.click(); a.remove();
                setTimeout(() => URL.revokeObjectURL(u), 5000);
            } catch (e) {
                window.showToast?.((t('artsmoker.ui.asset_viewer.three_d_export_failed') || 'Export failed')
                    + (e?.message ? `: ${e.message}` : ''), 'error');
            }
        },

        /** Probe (debounced) whether the CURRENT picks are already generated and
         *  cached server-side, and drive the two-step button state: not cached →
         *  "Generate FBX/USD"; cached → "Download FBX/USD" + ✓ (instant).
         *  Cached exports are never regenerated. */
        _refreshExportReady() {
            clearTimeout(this._exportReadyTimer);
            this._exportReadyTimer = setTimeout(async () => {
                const hint = t('artsmoker.ui.asset_viewer.three_d_export_ready_badge')
                    || 'Already generated — instant download';
                this._exportCached = this._exportCached || {};
                // Processed-GLB button: only meaningful when an op that APPLIES to
                // GLB is selected (packing doesn't — glTF has its own material spec);
                // hidden otherwise, since it would just duplicate the original GLB.
                const opVal = (id) => document.getElementById(id)?.value || 'none';
                const glbOps = ['av-3d-opt-lods', 'av-3d-opt-collision', 'av-3d-opt-uv2']
                    .some(id => opVal(id) !== 'none');
                document.getElementById('av-3d-download-pglb')?.classList.toggle('hidden', !glbOps);
                for (const fmt of ['fbx', 'usd', ...(glbOps ? ['glb'] : [])]) {
                    const badge = document.getElementById(`av-3d-${fmt}-ready`);
                    const label = document.getElementById(`av-3d-${fmt}-label`);
                    if (!badge || !label) continue;
                    try {
                        const target = document.getElementById('av-3d-target')?.value || 'generic';
                        const r = await fetch(this._exportUrl(fmt, target) + '&check=1');
                        const d = r.ok ? await r.json() : { cached: false };
                        this._exportCached[fmt] = !!d.cached;
                        badge.classList.toggle('hidden', !d.cached);
                        badge.title = d.cached ? hint : '';
                        label.textContent = d.cached
                            ? t(`artsmoker.ui.asset_viewer.three_d_download_${fmt}`)
                            : t(`artsmoker.ui.asset_viewer.three_d_generate_${fmt}`);
                    } catch {
                        this._exportCached[fmt] = false;
                        badge.classList.add('hidden');
                    }
                }
            }, 250);
        },

        /** Download an FBX/USD export: fetch (converting server-side on first use),
         *  show preparing/success/failure toasts, then save the blob. Fetch-based so
         *  a failure (Blender missing / conversion error → HTTP 503) surfaces a clear
         *  message instead of the browser silently saving an error page. */
        async _downloadExport(fmt) {
            const target = document.getElementById('av-3d-target')?.value || 'generic';
            const targetLabel = document.getElementById('av-3d-target')?.selectedOptions?.[0]?.textContent || target;
            // Disable BOTH export buttons for the duration — a second heavy Blender
            // run in parallel helps no one; the visual state + live status line below
            // keep an impatient user informed instead of re-clicking.
            const fbxBtn = document.getElementById('av-3d-download-fbx');
            const usdBtn = document.getElementById('av-3d-download-usd');
            const pglbBtn = document.getElementById('av-3d-download-pglb');
            [fbxBtn, usdBtn, pglbBtn].forEach(b => { if (b) b.disabled = true; });
            const btn = fmt === 'usd' ? usdBtn : (fmt === 'glb' ? pglbBtn : fbxBtn);
            const statusEl = document.getElementById('av-3d-export-status');
            if (statusEl && !this._exportCached?.[fmt]) {   // spinner only for the Generate step
                const base = (t('artsmoker.ui.asset_viewer.three_d_export_status') || 'Preparing {{fmt}} for {{target}}…')
                    .replace('{{fmt}}', fmt.toUpperCase()).replace('{{target}}', targetLabel);
                const hint = t('artsmoker.ui.asset_viewer.three_d_export_status_hint')
                    || 'large models with LODs/collision can take a few minutes';
                // A spinner, not a timer/ETA: "alive and working" is the only claim we
                // can make reliably (durations vary by mesh/ops/machine — see notes).
                // nosemgrep
                statusEl.innerHTML = html`<span class="spinner-sm"></span> ${base} — ${hint}`;
                statusEl.classList.remove('hidden');
                statusEl.classList.add('flex');
            }
            // Two-step UX: when the current combination is NOT cached yet, this click
            // GENERATES it (convert + cache server-side, no save dialog); the button
            // then flips to "Download …" ✓ for the instant second step. When cached,
            // this click downloads immediately.
            const isGenerate = !this._exportCached?.[fmt];
            if (isGenerate) window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_export_preparing'), 'info');
            try {
                if (isGenerate) {
                    const prep = await fetch(this._exportUrl(fmt, target) + '&prepare=1');
                    if (!prep.ok) {
                        let detail = '';
                        try { detail = (await prep.json()).detail || ''; } catch { /* non-JSON */ }
                        window.showToast?.((t('artsmoker.ui.asset_viewer.three_d_export_failed') || 'Export failed')
                            + (detail ? `: ${detail}` : ''), 'error');
                        return;
                    }
                    window.showToast?.((t('artsmoker.ui.asset_viewer.three_d_export_ready') || '{{fmt}} ready to download')
                        .replace('{{fmt}}', fmt.toUpperCase()), 'success');
                    // Refresh metadata so the new export appears in the ready-chips row.
                    try {
                        this._meta = await API.gallery.get(this._meta?.id || this._item?.id);
                        this._renderReadyExports();
                    } catch { /* chips refresh is best-effort */ }
                    return;   // step 1 done — the user downloads via the flipped button
                }
                const resp = await fetch(this._exportUrl(fmt, target));
                if (!resp.ok) {
                    let detail = '';
                    try { detail = (await resp.json()).detail || ''; } catch { /* non-JSON */ }
                    window.showToast?.((t('artsmoker.ui.asset_viewer.three_d_export_failed') || 'Export failed')
                        + (detail ? `: ${detail}` : ''), 'error');
                    return;
                }
                const blob = await resp.blob();
                // Prefer the server's filename (it encodes the chosen ops + .zip when
                // texture packing adds files); fall back to the slug-based name.
                const cd = resp.headers.get('Content-Disposition') || '';
                const m = cd.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
                let name = m ? decodeURIComponent(m[1].replace(/"/g, '')) : '';
                if (!name) name = this._exportDownloadName(fmt === 'usd' ? 'usdz' : (fmt === 'glb' ? 'glb' : 'fbx'), target);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = name;
                document.body.appendChild(a); a.click(); a.remove();
                setTimeout(() => URL.revokeObjectURL(url), 5000);
                window.showToast?.((t('artsmoker.ui.asset_viewer.three_d_export_ready') || '{{fmt}} ready')
                    .replace('{{fmt}}', fmt.toUpperCase()), 'success');
            } catch (e) {
                window.showToast?.((t('artsmoker.ui.asset_viewer.three_d_export_failed') || 'Export failed')
                    + (e?.message ? `: ${e.message}` : ''), 'error');
            } finally {
                statusEl?.classList.remove('flex');
                statusEl?.classList.add('hidden');
                [fbxBtn, usdBtn, pglbBtn].forEach(b => { if (b) b.disabled = false; });
                this._refreshExportReady();   // a fresh export is now cached → show ✓
            }
        },

        /** Build the "stats grid + Models & Tools Used" HTML for a 3D variant's data
         *  ({file_size, vertices, faces, created_at, pipeline, params}). Reused for
         *  the initial render AND re-rendered per variant on switch, so the panel
         *  always reflects the SELECTED variant's actual pipeline (not the default). */
        _render3DMetaHtml(d) {
            d = d || {};
            const fileSize = d.file_size ? this._formatBytes(d.file_size) : '—';
            const pl = d.pipeline || {};
            const prm = d.params || {};
            const rows = [];
            if (pl.geometry_model) rows.push([t('artsmoker.ui.asset_viewer.three_d_geometry_model'), pl.geometry_model]);
            if (pl.texture_label || pl.texture_backend) rows.push([t('artsmoker.ui.asset_viewer.three_d_texture_model'), pl.texture_label || pl.texture_backend]);
            rows.push([t('artsmoker.ui.asset_viewer.three_d_output_type'),
                pl.has_pbr ? t('artsmoker.ui.asset_viewer.three_d_pbr_textured') : t('artsmoker.ui.asset_viewer.three_d_albedo_textured')]);
            if (pl.instance_type) rows.push([t('artsmoker.ui.asset_viewer.three_d_instance'), pl.instance_type.replace('ml.', '')]);
            if (prm.octree_depth) rows.push([t('artsmoker.ui.asset_viewer.three_d_mesh_detail'), `octree ${prm.octree_depth}`]);
            if (prm.steps) rows.push([t('artsmoker.ui.asset_viewer.three_d_diffusion_steps'), String(prm.steps)]);
            if (prm.seed !== undefined && prm.seed !== null) rows.push([t('artsmoker.ui.asset_viewer.three_d_seed'), String(prm.seed)]);
            if (pl.license_name) {
                const commTxt = pl.commercial === true ? ` (${t('artsmoker.ui.asset_viewer.three_d_lic_commercial')})`
                    : (pl.commercial === false ? ` (${t('artsmoker.ui.asset_viewer.three_d_lic_noncommercial')})` : '');
                rows.push([t('artsmoker.ui.asset_viewer.three_d_lic_label'), pl.license_name + commTxt]);
            }
            if (pl.license_accepted_at) rows.push([t('artsmoker.ui.asset_viewer.three_d_lic_accepted_col'), window.formatTimestamp(pl.license_accepted_at)]);
            const toolsHtml = rows.length ? html`
                <div class="rounded-lg border border-brand-border/40 bg-white/[0.02] px-4 py-3">
                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-2">${t('artsmoker.ui.asset_viewer.three_d_pipeline_title')}</p>
                    <div class="grid grid-cols-2 gap-x-6 gap-y-1.5">
                        ${rows.map(([k, v]) => html`
                            <div class="flex items-center justify-between gap-2 text-[11px]">
                                <span class="text-brand-text-muted">${k}</span>
                                <span class="font-medium text-right truncate" title="${String(v)}">${String(v)}</span>
                            </div>`)}
                    </div>
                </div>` : '';
            return html`
                <div class="grid grid-cols-4 gap-3 text-center">
                    <div>
                        <p class="text-[10px] text-brand-text-muted uppercase">${t('artsmoker.ui.asset_viewer.three_d_file_size')}</p>
                        <p class="font-medium">${fileSize}</p>
                    </div>
                    <div>
                        <p class="text-[10px] text-brand-text-muted uppercase">${t('artsmoker.ui.asset_viewer.three_d_vertices')}</p>
                        <p class="font-medium">${d.vertices ? d.vertices.toLocaleString() : '—'}</p>
                    </div>
                    <div>
                        <p class="text-[10px] text-brand-text-muted uppercase">${t('artsmoker.ui.asset_viewer.three_d_faces_count')}</p>
                        <p class="font-medium">${d.faces ? d.faces.toLocaleString() : '—'}</p>
                    </div>
                    <div>
                        <p class="text-[10px] text-brand-text-muted uppercase">${t('artsmoker.ui.asset_viewer.three_d_created')}</p>
                        <p class="font-medium text-[11px]">${d.created_at ? window.formatTimestamp(d.created_at) : '—'}</p>
                    </div>
                </div>
                ${toolsHtml}`;
        },

        _render3DComplete(container, data) {
            const glbUrl = data.download_url || '#';
            this._current3DVariant = null;   // set when the variant switcher loads (≥2 variants)
            // Parallel jobs: Regenerate is ALWAYS available — firing another job
            // adds it to the in-progress strip rather than blocking the view.
            const regenBtnClass = 'btn btn-sm btn-secondary';
            const regenBtnLabel = html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> ${t('artsmoker.ui.asset_viewer.three_d_regenerate')}`;
            // Untextured-fallback notice: the texture bake failed and the pipeline
            // shipped a usable but plain (untextured) mesh instead. We DON'T fail the
            // job (the user still gets geometry, no wasted time/cost) — we clearly
            // tell them what happened and that regenerating may fix it. Only when the
            // record explicitly says textured===false (older/missing → assume fine).
            const _untextured = data.pipeline && data.pipeline.textured === false;
            const untexturedNotice = _untextured ? html`
                <div class="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 flex items-start gap-2">
                    <svg class="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                    <p class="text-[11px] text-amber-300/90">${t('artsmoker.ui.asset_viewer.three_d_untextured_notice')}</p>
                </div>` : '';
            // nosemgrep
            container.innerHTML = html`
                <div class="space-y-3">
                    ${untexturedNotice}
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
                            <button id="av-3d-zoom-in" class="w-7 h-7 rounded bg-black/50 hover:bg-black/70 flex items-center justify-center text-white text-sm" title="${t('artsmoker.ui.asset_viewer.zoom_in')}">+</button>
                            <button id="av-3d-zoom-out" class="w-7 h-7 rounded bg-black/50 hover:bg-black/70 flex items-center justify-center text-white text-sm" title="${t('artsmoker.ui.asset_viewer.zoom_out')}">−</button>
                            <button id="av-3d-reset" class="w-7 h-7 rounded bg-black/50 hover:bg-black/70 flex items-center justify-center text-white" title="${t('artsmoker.ui.asset_viewer.reset_view')}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
                            </button>
                            <button id="av-3d-autorotate" class="w-7 h-7 rounded bg-brand-accent/60 hover:bg-brand-accent/80 flex items-center justify-center text-white" title="${t('artsmoker.ui.asset_viewer.toggle_autorotate')}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                            </button>
                        </div>
                    </div>
                    <!-- Stats + Models&Tools panel — re-rendered per variant on switch. -->
                    <div id="av-3d-meta" class="space-y-3">${this._render3DMetaHtml(data)}</div>
                    <div class="flex flex-col items-center gap-2">
                        <div class="flex items-center justify-center gap-x-4 gap-y-1.5 flex-wrap">
                            <div class="flex items-center gap-1.5">
                                <label class="text-[10px] text-brand-text-muted whitespace-nowrap">${t('artsmoker.ui.asset_viewer.three_d_target_engine')}</label>
                                <select id="av-3d-target" class="input text-[10px] py-0.5"></select>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <label class="text-[10px] text-brand-text-muted whitespace-nowrap">${t('artsmoker.ui.asset_viewer.three_d_opt_packing')}</label>
                                <select id="av-3d-opt-pack" class="input text-[10px] py-0.5"></select>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <label class="text-[10px] text-brand-text-muted whitespace-nowrap">${t('artsmoker.ui.asset_viewer.three_d_opt_lods')}</label>
                                <select id="av-3d-opt-lods" class="input text-[10px] py-0.5"></select>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <label class="text-[10px] text-brand-text-muted whitespace-nowrap">${t('artsmoker.ui.asset_viewer.three_d_opt_collision')}</label>
                                <select id="av-3d-opt-collision" class="input text-[10px] py-0.5"></select>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <label class="text-[10px] text-brand-text-muted whitespace-nowrap">${t('artsmoker.ui.asset_viewer.three_d_opt_uv2')}</label>
                                <select id="av-3d-opt-uv2" class="input text-[10px] py-0.5"></select>
                            </div>
                        </div>
                        <div class="flex items-center justify-center gap-2 flex-wrap">
                            <a id="av-3d-download" href="${glbUrl}" download class="btn btn-primary btn-sm inline-flex items-center gap-2">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                </svg>
                                ${t('artsmoker.ui.asset_viewer.three_d_download')}
                            </a>
                            <button id="av-3d-download-fbx" class="btn btn-secondary btn-sm inline-flex items-center gap-2" title="${t('artsmoker.ui.asset_viewer.three_d_fidelity_note')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                </svg>
                                <span id="av-3d-fbx-label">${t('artsmoker.ui.asset_viewer.three_d_generate_fbx')}</span>
                                <span id="av-3d-fbx-ready" class="hidden text-emerald-300 font-bold">✓</span>
                            </button>
                            <button id="av-3d-download-usd" class="btn btn-secondary btn-sm inline-flex items-center gap-2" title="${t('artsmoker.ui.asset_viewer.three_d_fidelity_note')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                </svg>
                                <span id="av-3d-usd-label">${t('artsmoker.ui.asset_viewer.three_d_generate_usd')}</span>
                                <span id="av-3d-usd-ready" class="hidden text-emerald-300 font-bold">✓</span>
                            </button>
                            <!-- Processed GLB (LODs/collision/UV2 baked; separately named, original
                                 untouched). Shown only when an applicable op is selected. -->
                            <button id="av-3d-download-pglb" class="hidden btn btn-secondary btn-sm inline-flex items-center gap-2" title="${t('artsmoker.ui.asset_viewer.three_d_pglb_hint')}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                </svg>
                                <span id="av-3d-glb-label">${t('artsmoker.ui.asset_viewer.three_d_generate_glb')}</span>
                                <span id="av-3d-glb-ready" class="hidden text-emerald-300 font-bold">✓</span>
                            </button>
                            <button id="av-3d-regenerate" class="${regenBtnClass} inline-flex items-center gap-1.5">
                                ${regenBtnLabel}
                            </button>
                        </div>
                        <!-- Live export status (spinner) — shown while Blender runs. -->
                        <p id="av-3d-export-status" class="hidden text-[10px] text-cyan-400/90 text-center items-center justify-center gap-1.5"></p>
                        <!-- Already-generated exports for this version: one chip per
                             combination, click = instant download. Answers "what did I
                             already generate?" after the dialog was closed and reopened. -->
                        <div id="av-3d-ready-exports" class="hidden items-center justify-center gap-1.5 flex-wrap"></div>
                    </div>
                    <p class="text-[9px] text-brand-text-muted text-center">${t('artsmoker.ui.asset_viewer.three_d_viewer_hint')}</p>
                    <p class="text-[9px] text-brand-text-muted/70 text-center">${t('artsmoker.ui.asset_viewer.three_d_fidelity_note')}</p>
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
                        window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_not_deployed'), 'warning');
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
                    window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_not_deployed'), 'warning');
                }
            });

            // Default GLB download name (single-variant case, where the variant bar
            // stays hidden and never sets it). Aligned with PNG/SVG/multi-variant:
            // {slug}_v{N}_{ts}.glb. _populate3DVariants overrides this with a
            // variant-specific name when more than one variant exists.
            const glbDl = container.querySelector('#av-3d-download');
            if (glbDl) {
                const ver = this._currentVersion || 1;
                const vrec = (this._meta?.versions || []).find(v => v.version === ver);
                glbDl.setAttribute('download', this._versionDownloadName('glb', ver, vrec));
            }
            // Engine-export: FBX/USD buttons fetch-download (converting server-side on
            // first use, processing EXACTLY the ops the user picked), with preparing/
            // success/failure toasts. Dropdowns are config-driven from the backend;
            // the packing list refreshes per engine (Unity can't use UE-style ORM).
            container.querySelector('#av-3d-download-fbx')?.addEventListener('click', () => this._downloadExport('fbx'));
            container.querySelector('#av-3d-download-usd')?.addEventListener('click', () => this._downloadExport('usd'));
            container.querySelector('#av-3d-download-pglb')?.addEventListener('click', () => this._downloadExport('glb'));
            const targetSel = container.querySelector('#av-3d-target');
            const optSelects = {
                pack: container.querySelector('#av-3d-opt-pack'),
                lods: container.querySelector('#av-3d-opt-lods'),
                collision: container.querySelector('#av-3d-opt-collision'),
                uv2: container.querySelector('#av-3d-opt-uv2'),
            };
            const optLabel = (v) => t(`artsmoker.ui.asset_viewer.three_d_optval_${v}`) || v;
            const fillOptions = () => {
                const opts = this._exportOptions?.[targetSel?.value] || null;
                if (!opts) return;
                const lists = { pack: opts.packing, lods: opts.lods, collision: opts.collision, uv2: opts.uv2 };
                for (const [k, sel] of Object.entries(optSelects)) {
                    if (!sel) continue;
                    const keep = sel.value;   // preserve the pick when still offered
                    // nosemgrep
                    sel.innerHTML = (lists[k] || ['none'])
                        .map(v => html`<option value="${v}">${optLabel(v)}</option>`).join('');
                    sel.value = (lists[k] || []).includes(keep) ? keep : 'none';
                }
                this._refreshExportReady();
            };
            // Any op change re-probes whether that combination is already cached.
            Object.values(optSelects).forEach(sel => sel?.addEventListener('change', () => this._refreshExportReady()));
            if (targetSel) {
                targetSel.addEventListener('change', fillOptions);
                (async () => {
                    try {
                        const data = await API.admin.exportTargets();
                        // nosemgrep
                        targetSel.innerHTML = (data.targets || [])
                            .map(tt => html`<option value="${tt.key}">${tt.label}</option>`).join('');
                        targetSel.value = data.default || 'generic';
                        this._exportOptions = data.options || null;
                        this._exportTargets = data.targets || [];
                    } catch { /* leave empty → generic default + no ops in the URL */ }
                    fillOptions();
                    this._renderReadyExports();   // needs target labels → after fetch
                })();
            }

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
                v.faces ? v.faces.toLocaleString() + ' ' + t('artsmoker.ui.asset_viewer.three_d_est_faces') : '',
                v.pipeline?.has_pbr ? 'PBR' : '',
            ].filter(Boolean).join(' · ');
            // nosemgrep
            bar.innerHTML = html`
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-[10px] text-brand-text-muted uppercase tracking-wider flex-shrink-0">${t('artsmoker.ui.asset_viewer.three_d_variants_title')}</span>
                    ${variants.map((v) => {
                        const isDefault = v.variant_id === defaultId;
                        const sub = subtitle(v);
                        return html`<button class="av-3d-variant-btn px-2 py-1 rounded text-[10px] transition-all cursor-pointer ${isDefault ? 'bg-brand-accent text-white' : 'bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent hover:text-brand-text'}"
                                data-variant="${v.variant_id}" title="${label(v)}${sub ? ' — ' + sub : ''}">
                            ${label(v)}${isDefault ? html`<span class="opacity-60 ml-1">(${t('artsmoker.ui.asset_viewer.three_d_variant_default')})</span>` : ''}
                        </button>`;
                    })}
                    <button id="av-3d-set-default" class="hidden px-2 py-1 rounded text-[10px] border border-brand-accent/50 text-brand-accent hover:bg-brand-accent/10 transition-colors cursor-pointer">${t('artsmoker.ui.asset_viewer.three_d_variant_set_default')}</button>
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
            // GLB download name aligned with PNG/SVG: {slug}_v{N}_{variant}_{ts}.glb,
            // using the VARIANT's own created_at (falls back to the 2D version's
            // timestamp, then created_at). Keeps naming consistent across all downloads.
            const glbName = (vid) => {
                const vrec = (this._meta?.versions || []).find(v => v.version === ver);
                const variant = variants.find(x => x.variant_id === vid) || {};
                const base = this._versionDownloadName('glb', ver, vrec);   // {slug}_vN_{ts}.glb
                const tsRaw = variant.created_at || '';
                // Insert the variant id before the extension; prefer the variant's
                // own timestamp when present (rebuild via a synthetic record).
                if (tsRaw) {
                    const synth = { timestamp: tsRaw };
                    const withVarTs = this._versionDownloadName('glb', ver, synth);
                    return withVarTs.replace(/\.glb$/i, `_${vid}.glb`).replace(/[^\w.\-]+/g, '-');
                }
                return base.replace(/\.glb$/i, `_${vid}.glb`).replace(/[^\w.\-]+/g, '-');
            };
            // Re-render the stats + "Models & Tools Used" panel for THIS variant, so
            // switching variants shows that variant's real pipeline (not the default).
            const refreshMetaPanel = (vid) => {
                const metaEl = container.querySelector('#av-3d-meta');
                const v = variants.find(x => x.variant_id === vid);
                if (metaEl && v) {
                    // nosemgrep
                    metaEl.innerHTML = this._render3DMetaHtml({
                        file_size: v.size_bytes, vertices: v.vertices, faces: v.faces,
                        created_at: v.created_at, pipeline: v.pipeline, params: v.params,
                    });
                }
            };
            const showVariant = (vid) => {
                previewId = vid;
                if (viewer) viewer.src = `${variantUrl(vid)}&t=${Date.now()}`;
                if (dlLink) {
                    dlLink.href = variantUrl(vid);
                    dlLink.setAttribute('download', glbName(vid));
                }
                // FBX/USD read this at click time (+ the target dropdown).
                this._current3DVariant = vid;
                refreshMetaPanel(vid);
                this._refreshExportReady();
                refreshButtons();
            };
            // Initialize the download link + meta panel to the default variant shown.
            if (dlLink && defaultId) {
                dlLink.href = variantUrl(defaultId);
                dlLink.setAttribute('download', glbName(defaultId));
            }
            if (defaultId) {
                this._current3DVariant = defaultId;
                refreshMetaPanel(defaultId);
            }
            bar.querySelectorAll('.av-3d-variant-btn').forEach((btn) => {
                btn.addEventListener('click', () => showVariant(btn.dataset.variant));
            });

            setDefaultBtn?.addEventListener('click', async () => {
                try {
                    await API.threeD.setDefaultVariant(assetId, ver, previewId);
                    window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_variant_set_default_ok'), 'success');
                    // Refresh metadata so the gallery/thumbnail reflect the new default.
                    try { this._meta = await API.gallery.get(assetId); } catch {}
                    window.Gallery?.refresh?.();
                    this._update3DContent();
                } catch {
                    window.showToast?.(t('artsmoker.ui.asset_viewer.three_d_failed'), 'error');
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

        /** Build a download filename for a specific version: a readable prompt slug
         *  (from png_filename, minus its opt/var suffix + extension) + version label
         *  + the version's own timestamp, e.g.
         *  "a-young-athletic-male-soldier_v3_20260706-042211.png". Falls back to the
         *  asset id when no slug is available. Filesystem-safe. */
        _versionDownloadName(ext, version, vrec) {
            const meta = this._meta || {};
            // Base slug from png_filename ("slug_opt1_var2.png") → "slug", else id.
            // The backend already caps the slug at 40 chars; cap defensively here too
            // (e.g. imported assets) so the final name stays well under FS limits.
            let slug = (meta.png_filename || '').replace(/\.[a-z0-9]+$/i, '')
                .replace(/_opt\d+_var\d+$/i, '').trim();
            if (!slug) slug = (this._item?.id || 'asset');
            if (slug.length > 40) slug = slug.slice(0, 40).replace(/-+$/, '');
            const vLabel = version === 1 ? 'original' : `v${version}`;
            // Compact timestamp from the version's own timestamp (fallback: created_at).
            let ts = '';
            const raw = (vrec && vrec.timestamp) || meta.created_at || '';
            if (raw) {
                const d = new Date(raw);
                if (!isNaN(d)) {
                    const p = (n) => String(n).padStart(2, '0');
                    ts = `_${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
                }
            }
            const safe = `${slug}_${vLabel}${ts}.${ext}`.replace(/[^\w.\-]+/g, '-').replace(/-+/g, '-');
            return safe;
        },

        /**
         * Render the "what was sent to the editor" lineage for an edited version.
         * Shows: the edit instruction actually sent (post-transform), positive/
         * negative prompting, mask (prompt + a thumbnail of the drawn mask if
         * persisted), and the outpaint/extend canvas-growth spec (old→new dims +
         * per-edge pixels). Driven entirely off the version record `v`.
         */
        _renderEditLineage(v, promptBlock, TONE, LABEL_TONE, meta) {
            if (!v) return '';
            let html = '';
            const editLabel = (v.type || 'edit').replace(/_/g, ' ');

            // The instruction actually sent to the editor (post-transform if any).
            const sent = v.edit_prompt_sent || v.enhanced_prompt || v.prompt || '';
            if (sent) {
                const neg = v.negative_prompt ? this._esc(v.negative_prompt) : t('artsmoker.ui.asset_viewer.meta_none');
                // Copy carries ONLY `sent`; the negative renders in a separate
                // element outside the copyable <p>.
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                html += `
                    <div class="av-prompt-block">
                        <div class="flex items-center gap-2 mb-0.5">
                            <span class="text-[11px] font-medium ${LABEL_TONE.indigo}">${t('artsmoker.ui.asset_viewer.meta_sent_to_editor')}</span>
                            <span class="px-1.5 py-0.5 rounded text-[9px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${this._esc(editLabel)}</span>
                            ${this._copyBtnFor ? this._copyBtnFor(sent) : ''}
                        </div>
                        <p class="p-2 rounded-t-lg border border-b-0 ${TONE.indigo} whitespace-pre-wrap text-[11px] leading-snug max-h-32 overflow-y-auto">${this._esc(sent)}</p>
                        <div class="p-2 rounded-b-lg border ${TONE.indigo} text-[9px] text-brand-text-muted/80">${t('artsmoker.ui.asset_viewer.meta_negative_add')}: ${neg}</div>
                    </div>`;
            }
            if (v.prompt && v.edit_prompt_sent && v.prompt !== v.edit_prompt_sent) {
                html += promptBlock(t('artsmoker.ui.asset_viewer.meta_your_instruction'), v.prompt, { tone: 'muted', muted: true });
            }

            // Mask (natural-language and/or the drawn mask thumbnail).
            if (v.mask_prompt) {
                html += promptBlock(t('artsmoker.ui.asset_viewer.meta_mask_area'), v.mask_prompt, { tone: 'amber' });
            }
            if (v.mask_file && meta?.id) {
                html += `
                    <div class="av-prompt-block">
                        <div class="text-[11px] font-medium ${LABEL_TONE.amber} mb-0.5">${t('artsmoker.ui.asset_viewer.meta_mask_drawn')}</div>
                        <img src="/api/gallery/${encodeURIComponent(meta.id)}/mask/${encodeURIComponent(v.mask_file)}"
                             class="max-h-32 rounded-lg border border-brand-border/40 bg-[repeating-conic-gradient(#0000_0deg_90deg,#ffffff10_90deg_180deg)]" alt="mask" />
                    </div>`;
            }

            // Outpaint / extend canvas-growth spec: old → new dims + per-edge px.
            const sd = v.source_dims, rd = v.result_dims, op = v.outpaint_px;
            if (op || (sd?.width && rd?.width && (sd.width !== rd.width || sd.height !== rd.height))) {
                const edges = op ? Object.entries(op).filter(([, px]) => px > 0)
                    .map(([e, px]) => `${e} +${px}px`).join(', ') : '';
                const dims = (sd?.width && rd?.width)
                    ? `${sd.width}×${sd.height} → ${rd.width}×${rd.height}` : '';
                const body = [dims, edges].filter(Boolean).join('  ·  ') || t('artsmoker.ui.asset_viewer.meta_none');
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                html += `
                    <div class="av-prompt-block">
                        <div class="text-[11px] font-medium ${LABEL_TONE.neutral} mb-0.5">${t('artsmoker.ui.asset_viewer.meta_canvas_change')}</div>
                        <p class="p-2 rounded-lg border ${TONE.neutral} text-[11px] font-mono">${this._esc(body)}</p>
                    </div>`;
            }
            return html;
        },

        _copyBtnFor(text) {
            const escAttr = (s) => (s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            return `<button class="av-copy-btn ml-2 px-1.5 py-0.5 rounded text-[9px] text-brand-text-muted hover:text-brand-accent hover:bg-brand-accent/10 border border-transparent hover:border-brand-accent/20 transition-colors" data-copy="${escAttr(text)}" title="${t('artsmoker.ui.asset_viewer.meta_copy')}">${t('artsmoker.ui.asset_viewer.meta_copy')}</button>`;
        },

        _renderDecomposed(data) {
            if (!data || typeof data !== 'object') return '';

            // Extract a field's display text. Prompt Designer fields are
            // {value, source} objects (the actual schema); older data may be a
            // bare string or an array of strings / {name,hex} color entries.
            const fieldText = (v) => {
                if (v == null) return '';
                if (typeof v === 'string') return v.trim();
                if (Array.isArray(v)) {
                    return v.map(it => typeof it === 'string' ? it
                        : (it && it.name ? `${it.name}${it.hex ? ` (${it.hex})` : ''}` : ''))
                        .filter(Boolean).join(', ');
                }
                if (typeof v === 'object') {
                    // {value, source} field object.
                    if ('value' in v) return typeof v.value === 'string' ? v.value.trim() : fieldText(v.value);
                    // some sections may nest arrays under a key (e.g. colors)
                    return '';
                }
                return String(v);
            };
            const humanize = (k) => k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

            const sections = [];
            // Iterate EVERY section + EVERY field (no hardcoded key list) so all
            // decomposed items are shown, not just five. Handles nested
            // {value,source} fields and marks user-stated vs inferred.
            for (const [sectionKey, sectionVal] of Object.entries(data)) {
                if (sectionKey.startsWith('_')) continue;  // skip provenance (_meta etc.)
                if (!sectionVal || typeof sectionVal !== 'object' || Array.isArray(sectionVal)) {
                    const txt = fieldText(sectionVal);
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    if (txt) sections.push(`<div><strong class="text-brand-text/80">${this._esc(humanize(sectionKey))}:</strong> ${this._esc(txt)}</div>`);
                    continue;
                }
                const lines = [];
                for (const [fieldKey, fieldVal] of Object.entries(sectionVal)) {
                    const txt = fieldText(fieldVal);
                    if (!txt) continue;
                    // Show the source tag (user-stated vs inferred) when present.
                    const src = (fieldVal && typeof fieldVal === 'object' && fieldVal.source) ? fieldVal.source : '';
                    const srcTag = src === 'user'
                        // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                        ? ` <span class="text-emerald-400/60 text-[9px]">(${t('artsmoker.ui.asset_viewer.meta_src_user')})</span>`
                        // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                        : (src === 'inferred' ? ` <span class="text-brand-text-muted/40 text-[9px]">(${t('artsmoker.ui.asset_viewer.meta_src_inferred')})</span>` : '');
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    lines.push(`<div><span class="text-brand-text-muted/60">${this._esc(humanize(fieldKey))}:</span> ${this._esc(txt)}${srcTag}</div>`);
                }
                if (lines.length) {
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    sections.push(`<div><strong class="text-brand-text/80">${this._esc(humanize(sectionKey))}:</strong><div class="ml-3 space-y-0.5">${lines.join('')}</div></div>`);
                }
            }
            return sections.join('');
        },
    };

    window.AssetViewer = AssetViewer;
})();
