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
                <div class="modal-content bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
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
                    </div>

                    <!-- Footer -->
                    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-brand-border">
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
                    modelLabel ? `<span class="px-1.5 py-0.5 rounded bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${this._esc(modelLabel)}</span>` : '',
                    styleName ? `<span class="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${this._esc(styleName)}</span>` : '',
                    typeLabel !== 'N/A' ? `<span class="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${this._esc(typeLabel)}</span>` : '',
                    meta.width && meta.height ? `<span>${meta.width}×${meta.height}</span>` : '',
                    createdDate ? `<span>${createdDate}</span>` : '',
                ].filter(Boolean).join('');
            }

            container.innerHTML = `
                ${meta.original_language_prompt ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_original_prompt')} <span class="text-[9px] text-brand-accent font-normal">(${this._esc(meta.original_language || '?')})</span></label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.original_language_prompt)}</p>
                </div>
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_original_prompt')} <span class="text-[9px] text-emerald-400/70 font-normal">(English)</span></label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.original_prompt || meta.prompt)}</p>
                </div>` : meta.original_prompt ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_original_prompt')}</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.original_prompt)}</p>
                </div>` : ''}
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${isTypeStudio ? t('asset_viewer.meta_text_content') : (meta.original_prompt ? t('asset_viewer.meta_enhanced') : t('common.prompt'))}</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.prompt || 'N/A')}</p>
                </div>
                ${!isTypeStudio && meta.refined_prompt ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_generation_prompt')}</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._esc(meta.refined_prompt)}</p>
                </div>` : ''}
                ${meta.negative_prompt ? `
                <div>
                    <label class="block text-xs text-amber-400/80 uppercase tracking-wider mb-1">${t('asset_viewer.meta_negative_exclusions')}</label>
                    <p class="p-3 rounded-lg bg-amber-950/20 border border-amber-900/20 whitespace-pre-wrap text-amber-300/70 italic text-sm">${this._esc(meta.negative_prompt)}</p>
                </div>` : ''}
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_style')}</label>
                        <p class="font-medium">${this._esc(meta.style_snapshot?.name || meta.style_id || t('common.none'))}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_type')}</label>
                        <p class="font-medium">${typeLabel}</p>
                    </div>
                    ${modelLabel ? `<div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_model')}</label>
                        <p class="font-medium">${modelLabel}</p>
                    </div>` : ''}
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_dimensions')}</label>
                        <p class="font-medium">${meta.width || '?'} x ${meta.height || '?'}</p>
                    </div>
                    ${meta.seed != null ? `<div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_seed')}</label>
                        <p class="font-medium font-mono text-xs">${meta.seed}</p>
                    </div>` : ''}
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_created')}</label>
                        <p class="font-medium">${createdAt}</p>
                    </div>
                </div>
                ${(meta.ip_owned || meta.ip_licensed) ? `
                <div class="p-2 rounded-lg bg-brand-accent/10 border border-brand-accent/20 text-xs">
                    <span class="font-medium">${t('asset_viewer.meta_ip_declaration')}</span>
                    ${meta.ip_owned ? ' ' + t('asset_viewer.meta_ip_owner') : ''}${meta.ip_licensed ? ' ' + t('asset_viewer.meta_ip_licensed') : ''}
                </div>` : ''}
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_batch')}</label>
                        <p class="font-mono text-xs text-brand-text-muted">${this._esc(meta.batch_id || meta.id)}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_option_var')}</label>
                        <p class="font-medium">${(meta.option_index ?? 0) + 1} / ${(meta.variant_index ?? 0) + 1}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_filename')}</label>
                        <p class="font-mono text-xs">${this._esc(meta.png_filename || 'N/A')}</p>
                    </div>
                </div>
                ${meta.style_snapshot?.generation_hints ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_style_hints')}</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-xs text-brand-text-muted">${this._esc(meta.style_snapshot.generation_hints)}</p>
                </div>` : ''}
                ${meta.type === 'type-studio' ? `
                <div class="border-t border-brand-border pt-4 mt-2">
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-2">${t('asset_viewer.meta_type_studio_details')}</label>
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
                    </div>` : ''}
                </div>` : ''}
                ${meta.edit_history?.length ? `
                <div class="border-t border-brand-border pt-4 mt-2">
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
                    </div>
                </div>` : ''}
                ${meta.edit_type && !meta.edit_history?.length ? `
                <div class="border-t border-brand-border pt-4 mt-2">
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_edit_info')}</label>
                    <p class="text-sm"><span class="text-brand-text-muted">${t('asset_viewer.meta_type_label')}</span> ${this._esc(meta.edit_type)}</p>
                    <p class="text-sm"><span class="text-brand-text-muted">${t('asset_viewer.meta_model_label')}</span> ${this._esc(meta.model_label || meta.edit_model || '')}</p>
                    ${meta.source_image_id ? `<p class="text-sm"><span class="text-brand-text-muted">${t('asset_viewer.meta_source_label')}</span> ${this._esc(meta.source_image_id)}</p>` : ''}
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

            // Populate shared version bar if versions exist
            this._updateVersionBar(meta);
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
                            ${v.refined_prompt ? `
                            <div>
                                <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${t('asset_viewer.meta_generation_prompt')}</label>
                                <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._esc(v.refined_prompt)}</p>
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

                    // Show version detail summary
                    if (detail && v) {
                        detail.classList.remove('hidden');
                        detail.innerHTML = `
                            <strong>${v.type === 'original' ? t('asset_viewer.version_original') : v.type}</strong>
                            ${v.model_label || v.image_model || ''}
                            ${v.original_language_prompts?.prompt ? ` — <span class="text-[9px] text-brand-accent">(${v.original_language || '?'})</span> "${this._esc(v.original_language_prompts.prompt)}"` : ''}
                            ${v.prompt ? ` — ${v.original_language_prompts?.prompt ? '<span class="text-[9px] text-emerald-400/70">(en)</span> ' : ''}"${this._esc(v.prompt)}"` : ''}
                            ${v.negative_prompt ? ` <span class="text-amber-300/60">[neg: ${this._esc(v.negative_prompt)}]</span>` : ''}
                            ${v.timestamp ? ` <span class="text-brand-text-dim">${window.formatTimestamp(v.timestamp)}</span>` : ''}
                        `;
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
            this._overlay.querySelectorAll('.tab').forEach((tab) => {
                tab.addEventListener('click', () => {
                    this._overlay.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
                    tab.classList.add('active');
                    this._overlay.querySelectorAll('.tab-panel').forEach((p) => {
                        p.classList.toggle('hidden', p.dataset.panel !== tab.dataset.tab);
                    });
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
                        opt.textContent = `${cfg.label} ($${(cfg.base_price_usd || 0).toFixed(2)}/img)`;
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

            const _activeClass = 'bg-white/30 text-white';
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

        _esc(str) {
            const div = document.createElement('div');
            div.textContent = str || '';
            return div.innerHTML;
        },
    };

    window.AssetViewer = AssetViewer;
})();
