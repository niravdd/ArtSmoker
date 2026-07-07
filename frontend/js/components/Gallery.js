/**
 * ArtSmoker — Gallery Component
 *
 * Grid of generated asset thumbnails with filtering, sorting,
 * lazy loading, and click-to-open AssetViewer.
 */
(function () {
    'use strict';

    const PAGE_SIZE = 100;

    window.Gallery = {
        _items: [],
        _styles: [],
        _loading: false,
        _lastLoadTime: 0,
        _offset: 0,
        _hasMore: false,
        _selected: new Set(),
        _cacheKey: '0',

        render() {
            return `
                <div id="gallery-view" class="space-y-6 view-enter">
                    <!-- Header -->
                    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 class="text-2xl font-bold">${t('gallery.title')}</h1>
                            <p class="text-sm text-brand-text-muted mt-1">${t('gallery.subtitle')}</p>
                        </div>
                        <div class="flex items-center gap-2">
                            <button id="gal-import-btn" class="btn btn-secondary btn-sm">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                                </svg>
                                ${t('gallery.import_image')}
                            </button>
                            <a href="#image-studio" class="btn btn-primary btn-sm">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                                </svg>
                                ${t('gallery.generate_new')}
                            </a>
                        </div>
                    </div>

                    <!-- Selection bar (hidden until items are selected) -->
                    <div id="gal-selection-bar" class="hidden card-static p-3 bg-red-950/30 border-red-500/30 flex items-center justify-between gap-4">
                        <div class="flex items-center gap-3">
                            <button id="gal-select-all" class="btn btn-secondary btn-sm text-xs">${t('gallery.select_all')}</button>
                            <button id="gal-deselect-all" class="btn btn-secondary btn-sm text-xs">${t('gallery.deselect_all')}</button>
                            <span id="gal-selected-count" class="text-sm text-red-300 font-medium"></span>
                        </div>
                        <div class="flex items-center gap-3">
                            <span class="text-[10px] text-red-400/70">${t('gallery.delete_warning')}</span>
                            <button id="gal-delete-btn" class="btn btn-sm bg-red-600 hover:bg-red-500 text-white">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                                </svg>
                                ${t('gallery.delete_selected')}
                            </button>
                        </div>
                    </div>

                    <!-- Search + Filter Bar -->
                    <div class="card-static p-4 space-y-3">
                        <!-- Search -->
                        <div class="relative">
                            <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-muted/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                            </svg>
                            <input type="text" id="gal-search" class="input w-full pl-10" placeholder="${t('gallery.search_placeholder')}">
                        </div>
                        <!-- Filters -->
                        <div class="flex flex-wrap items-center gap-3">
                            <div class="flex-1 min-w-[120px]">
                                <label class="block text-xs text-brand-text-muted mb-1">${t('gallery.filter_media')}</label>
                                <select id="gal-filter-media" class="input">
                                    <option value="">${t('gallery.filter_all_media')}</option>
                                    <option value="image">${t('gallery.filter_images')}</option>
                                    <option value="video">${t('gallery.filter_videos')}</option>
                                </select>
                            </div>
                            <div class="flex-1 min-w-[160px]">
                                <label class="block text-xs text-brand-text-muted mb-1">${t('gallery.filter_style')}</label>
                                <select id="gal-filter-style" class="input">
                                    <option value="">${t('gallery.filter_all_styles')}</option>
                                </select>
                            </div>
                            <div class="flex-1 min-w-[160px]">
                                <label class="block text-xs text-brand-text-muted mb-1">${t('gallery.filter_type')}</label>
                                <select id="gal-filter-type" class="input">
                                    <option value="">${t('gallery.filter_all_types')}</option>
                                    <option value="game_asset">${t('gallery.filter_game_asset')}</option>
                                    <option value="marketing_banner">${t('gallery.filter_marketing_banner')}</option>
                                    <option value="icon">${t('gallery.filter_icon')}</option>
                                    <option value="character">${t('gallery.filter_character')}</option>
                                    <option value="environment">${t('gallery.filter_environment')}</option>
                                    <option value="video">${t('gallery.filter_video')}</option>
                                </select>
                            </div>
                            <div class="flex-1 min-w-[160px]">
                                <label class="block text-xs text-brand-text-muted mb-1">${t('gallery.sort')}</label>
                                <select id="gal-sort" class="input">
                                    <option value="newest">${t('gallery.sort_newest')}</option>
                                    <option value="oldest">${t('gallery.sort_oldest')}</option>
                                </select>
                            </div>
                            <div class="flex items-end">
                                <button id="gal-apply-filter" class="btn btn-secondary btn-sm mt-4">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/>
                                    </svg>
                                    ${t('common.apply')}
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Item count -->
                    <div id="gal-count" class="text-xs text-brand-text-muted hidden"></div>

                    <!-- Gallery Grid -->
                    <div id="gallery-grid" class="gallery-grid">
                        ${this._skeletons(8)}
                    </div>

                    <!-- Load More -->
                    <div id="gal-load-more" class="hidden text-center py-4">
                        <button id="btn-load-more" class="btn btn-secondary btn-sm">${t('gallery.load_more')}</button>
                    </div>
                    <p class="artsmoker-version text-[9px] text-brand-text-dim/30 text-center mt-6">ArtSmoker</p>
                </div>
            `;
        },

        async init() {
            // Load styles for filter dropdown
            this._loadStylesFilter();

            // Filter apply button
            document.getElementById('gal-apply-filter')?.addEventListener('click', () => this._loadItems(true));

            // Also apply on dropdown change
            ['gal-filter-media', 'gal-filter-style', 'gal-filter-type', 'gal-sort'].forEach((id) => {
                document.getElementById(id)?.addEventListener('change', () => this._loadItems(true));
            });

            // Search with debounce
            let searchTimer;
            document.getElementById('gal-search')?.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(() => this._applySearch(), 300);
            });

            // Load More button
            document.getElementById('btn-load-more')?.addEventListener('click', () => this._loadMore());

            // Selection / Delete
            document.getElementById('gal-select-all')?.addEventListener('click', () => {
                this._selected.clear();  // Start fresh — only select currently visible items
                const items = this._filteredItems !== null ? this._filteredItems : this._items;
                items.forEach(i => this._selected.add(i.id));
                this._updateSelectionUI();
            });
            document.getElementById('gal-deselect-all')?.addEventListener('click', () => {
                this._selected.clear();
                this._updateSelectionUI();
            });
            document.getElementById('gal-delete-btn')?.addEventListener('click', () => this._handleDelete());

            // Import an existing image into the gallery
            document.getElementById('gal-import-btn')?.addEventListener('click', () => this._openImportModal());

            // Load items
            await this._loadItems(true);
        },

        /** Import-image modal: upload a file + set its asset type, then it becomes a
         *  first-class gallery asset (editable, 3D-capable) exactly like a generated one. */
        _openImportModal() {
            // Asset types offered — reuse the gallery filter labels. Character/game
            // asset enable 3D (noted in the hint below).
            const TYPES = [
                ['character', t('gallery.filter_character')],
                ['game_asset', t('gallery.filter_game_asset')],
                ['environment', t('gallery.filter_environment')],
                ['icon', t('gallery.filter_icon')],
                ['marketing_banner', t('gallery.filter_marketing_banner')],
                ['photorealistic', t('gallery.filter_photorealistic')],
            ];
            const backdrop = document.createElement('div');
            backdrop.className = 'fixed inset-0 z-[130] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            backdrop.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-5 space-y-4 max-h-[92vh] overflow-y-auto">
                    <div>
                        <h3 class="text-sm font-semibold text-brand-text">${t('gallery.import_title')}</h3>
                        <p class="text-[11px] text-brand-text-dim mt-1">${t('gallery.import_subtitle')}</p>
                    </div>
                    <!-- Drop zone (click to browse or drag-drop) -->
                    <div id="gi-drop" class="rounded-lg border-2 border-dashed border-brand-border hover:border-brand-accent/60 cursor-pointer transition-colors flex items-center justify-center text-center p-4" style="min-height: 200px;">
                        <img id="gi-preview" class="hidden max-h-64 w-auto rounded-lg object-contain" alt="preview" />
                        <p id="gi-drop-text" class="text-xs text-brand-text-muted px-6">${t('gallery.import_drop')}</p>
                    </div>
                    <input id="gi-file" type="file" accept="image/*" class="hidden" />
                    <div>
                        <label class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-1 block">${t('gallery.import_asset_type')}</label>
                        <select id="gi-type" class="input text-sm w-full">
                            <option value="">${t('gallery.import_asset_type_ph')}</option>
                            ${TYPES.map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}
                        </select>
                        <p class="text-[9px] text-brand-text-dim mt-1">${t('gallery.import_asset_type_hint')}</p>
                    </div>
                    <div>
                        <label class="text-[10px] text-brand-text-muted uppercase tracking-wider mb-1 block">${t('gallery.import_title_label')}</label>
                        <input id="gi-title" type="text" class="input text-sm w-full" placeholder="${t('gallery.import_title_ph')}" />
                    </div>
                    <div class="flex flex-wrap gap-4">
                        <label class="flex items-center gap-2 cursor-pointer text-[11px] text-brand-text">
                            <input id="gi-ip-owned" type="checkbox" class="accent-brand-accent" /> ${t('gallery.import_ip_owned')}
                        </label>
                        <label class="flex items-center gap-2 cursor-pointer text-[11px] text-brand-text">
                            <input id="gi-ip-licensed" type="checkbox" class="accent-brand-accent" /> ${t('gallery.import_ip_licensed')}
                        </label>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="gi-submit" class="btn btn-primary btn-sm flex-1" disabled>${t('gallery.import_submit')}</button>
                        <button id="gi-cancel" class="btn btn-secondary btn-sm">${t('prompt_designer.cancel')}</button>
                    </div>
                </div>`;

            const $ = (s) => backdrop.querySelector(s);
            const fileInput = $('#gi-file'), dropZone = $('#gi-drop');
            const preview = $('#gi-preview'), dropText = $('#gi-drop-text');
            const typeSel = $('#gi-type'), submitBtn = $('#gi-submit');
            let chosenFile = null;

            const refreshSubmit = () => { submitBtn.disabled = !(chosenFile && typeSel.value); };
            const setFile = (f) => {
                if (!f || !f.type.startsWith('image/')) { window.showToast?.(t('gallery.import_pick_file'), 'warning'); return; }
                chosenFile = f;
                const url = URL.createObjectURL(f);
                preview.src = url; preview.classList.remove('hidden'); dropText.classList.add('hidden');
                refreshSubmit();
            };

            dropZone.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => setFile(e.target.files?.[0]));
            ['dragover', 'dragenter'].forEach(ev => dropZone.addEventListener(ev, (e) => {
                e.preventDefault(); dropZone.classList.add('border-brand-accent');
            }));
            ['dragleave', 'drop'].forEach(ev => dropZone.addEventListener(ev, (e) => {
                e.preventDefault(); dropZone.classList.remove('border-brand-accent');
            }));
            dropZone.addEventListener('drop', (e) => setFile(e.dataTransfer?.files?.[0]));
            typeSel.addEventListener('change', refreshSubmit);

            const close = () => backdrop.remove();
            $('#gi-cancel').addEventListener('click', close);
            backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });

            submitBtn.addEventListener('click', async () => {
                if (!chosenFile) { window.showToast?.(t('gallery.import_pick_file'), 'warning'); return; }
                if (!typeSel.value) { window.showToast?.(t('gallery.import_pick_type'), 'warning'); return; }
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<span class="spinner-sm"></span> ${t('gallery.import_importing')}`;
                try {
                    const item = await API.gallery.import(chosenFile, {
                        assetType: typeSel.value,
                        title: $('#gi-title').value || '',
                        ipOwned: $('#gi-ip-owned').checked,
                        ipLicensed: $('#gi-ip-licensed').checked,
                    });
                    window.showToast?.(t('gallery.import_success'), 'success');
                    close();
                    await this.refresh();
                    // Open the freshly imported asset so the user can act on it immediately.
                    const fresh = (this._items || []).find(i => i.id === item.id) || item;
                    fresh._media = 'image';
                    window.AssetViewer?.open?.(fresh, this._items || [fresh], 0);
                } catch (err) {
                    window.showToast?.(t('gallery.import_failed') + ': ' + (err.message || ''), 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = t('gallery.import_submit');
                }
            });

            document.body.appendChild(backdrop);
        },

        /** Called when navigating back to gallery (view already cached) */
        onShow() {
            if (Date.now() - this._lastLoadTime > 10000) {
                this._loadItems(true);
            }
        },

        // --------------------------------------------------------
        //  Data
        // --------------------------------------------------------

        async _loadStylesFilter() {
            try {
                const data = await API.styles.list();
                this._styles = Array.isArray(data) ? data : (data.styles || data.items || []);
            } catch (_) {
                this._styles = [];
            }

            const sel = document.getElementById('gal-filter-style');
            if (!sel) return;
            // Keep "All" option
            this._styles.forEach((s) => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.name;
                sel.appendChild(opt);
            });
        },

        /** Public: force a full gallery refresh (e.g. after an edit). */
        refresh() {
            this._cacheKey = String(Date.now());
            return this._loadItems(true);
        },

        async _loadItems(reset = true) {
            if (this._loading) return;
            this._loading = true;

            const grid = document.getElementById('gallery-grid');
            const mediaFilter = document.getElementById('gal-filter-media')?.value || '';

            if (reset) {
                this._items = [];
                this._offset = 0;
                this._cacheKey = String(Date.now());
                if (grid) grid.innerHTML = this._skeletons(8);
            }

            const params = { limit: PAGE_SIZE, offset: this._offset };
            const styleId = document.getElementById('gal-filter-style')?.value;
            const assetType = document.getElementById('gal-filter-type')?.value;

            if (styleId) params.style_id = styleId;
            if (assetType) params.asset_type = assetType;

            try {
                // Load image assets (unless video-only filter)
                if (mediaFilter !== 'video') {
                    const data = await API.gallery.list(params);
                    const page = Array.isArray(data) ? data : (data.items || data.gallery || []);
                    page.forEach(item => { item._media = 'image'; });
                    this._items.push(...page);
                    this._offset += page.length;
                    this._hasMore = page.length === PAGE_SIZE;
                }

                // Load video assets (unless image-only filter)
                if (mediaFilter !== 'image') {
                    try {
                        const videoData = await API.video.jobs({ status: 'Completed', limit: PAGE_SIZE });
                        const videoJobs = videoData.jobs || [];
                        videoJobs.forEach(j => {
                            j._media = 'video';
                            j.id = j.job_id || j.video_id;
                            j.created_at = j.completed_at || j.started_at;
                        });
                        this._items.push(...videoJobs);
                    } catch (_) { /* video endpoint may not exist yet */ }
                }

                // Sort unified list
                const sortBy = document.getElementById('gal-sort')?.value || 'newest';
                this._items.sort((a, b) => {
                    const da = new Date(a.created_at || 0).getTime();
                    const db = new Date(b.created_at || 0).getTime();
                    return sortBy === 'newest' ? db - da : da - db;
                });

                this._lastLoadTime = Date.now();
                this._renderGrid();
                this._updateLoadMore();
            } catch (err) {
                console.error('Gallery load error:', err);
                if (grid && this._items.length === 0) {
                    grid.innerHTML = `<div class="col-span-full text-center py-8 text-red-400">${t('gallery.load_error')}</div>`;
                }
            } finally {
                this._loading = false;
            }
        },

        async _loadMore() {
            await this._loadItems(false);
        },

        _updateSelectionUI() {
            const bar = document.getElementById('gal-selection-bar');
            const count = document.getElementById('gal-selected-count');
            const n = this._selected.size;
            if (bar) bar.classList.toggle('hidden', n === 0);
            if (count) count.textContent = t('gallery.selected', { count: n, plural: n !== 1 ? 's' : '' });

            // Sync checkboxes
            document.querySelectorAll('.gal-select-cb').forEach(cb => {
                cb.checked = this._selected.has(cb.dataset.id);
                const card = cb.closest('.gallery-card');
                if (card) {
                    card.classList.toggle('ring-2', cb.checked);
                    card.classList.toggle('ring-red-500/50', cb.checked);
                }
            });
        },

        async _handleDelete() {
            const ids = Array.from(this._selected);
            if (ids.length === 0) return;

            if (!await window.showConfirm(t('gallery.delete_confirm', { count: ids.length, plural: ids.length !== 1 ? 's' : '' }), { title: t('gallery.delete_title'), detail: t('gallery.delete_detail'), confirmLabel: t('gallery.confirm_label'), danger: true })) return;

            window.showLoading?.(t('gallery.deleting', { count: ids.length, plural: ids.length !== 1 ? 's' : '' }));
            try {
                // Separate image and video IDs
                const imageIds = [];
                const videoIds = [];
                ids.forEach(id => {
                    const item = this._items.find(i => String(i.id) === String(id));
                    if (item?._media === 'video') {
                        videoIds.push(id);
                    } else {
                        imageIds.push(id);
                    }
                });

                let deletedCount = 0;
                if (imageIds.length > 0) {
                    const result = await API.gallery.delete(imageIds);
                    deletedCount += (result.deleted || []).length;
                }
                if (videoIds.length > 0) {
                    for (const vid of videoIds) {
                        try { await API.video.delete(vid); deletedCount++; } catch (_) {}
                    }
                }

                window.hideLoading?.();
                this._selected.clear();
                window.showToast?.(t('gallery.deleted', { count: deletedCount, plural: deletedCount !== 1 ? 's' : '' }), 'success');
                this._loading = false;  // Ensure reload is not blocked
                await this._loadItems(true);
            } catch (err) {
                window.hideLoading?.();
            }
        },

        _applySearch() {
            const query = (document.getElementById('gal-search')?.value || '').toLowerCase().trim();
            if (!query) {
                this._filteredItems = null;
            } else {
                this._filteredItems = this._items.filter(item => {
                    const text = [
                        item.prompt || '',
                        item.original_prompt || '',
                        item.style_id || '',
                        item.asset_type || '',
                        item.model_label || '',
                        item.id || '',
                    ].join(' ').toLowerCase();
                    return text.includes(query);
                });
            }
            this._renderGrid();
            this._updateLoadMore();
        },

        _updateLoadMore() {
            const section = document.getElementById('gal-load-more');
            if (section) {
                section.classList.toggle('hidden', !this._hasMore);
            }
            const countEl = document.getElementById('gal-count');
            if (countEl) {
                countEl.classList.remove('hidden');
                const displayItems = this._filteredItems !== null ? this._filteredItems : this._items;
                const countText = t('gallery.asset_count', { count: this._items.length, plural: this._items.length !== 1 ? 's' : '' });
                const searchNote = this._filteredItems !== null ? t('gallery.matching', { count: displayItems.length }) : '';
                const moreNote = this._hasMore ? t('gallery.more_available') : '';
                countEl.textContent = `${countText}${searchNote}${moreNote}`;
            }
        },

        // --------------------------------------------------------
        //  Rendering
        // --------------------------------------------------------

        _filteredItems: null,

        _renderGrid() {
            const grid = document.getElementById('gallery-grid');
            if (!grid) return;

            const displayItems = this._filteredItems !== null ? this._filteredItems : this._items;

            if (displayItems.length === 0 && this._items.length > 0) {
                // Search returned no results
                grid.innerHTML = `
                    <div class="col-span-full text-center py-12 text-brand-text-muted">
                        <p class="text-sm">${t('gallery.no_results')}</p>
                    </div>
                `;
                return;
            }

            if (this._items.length === 0) {
                grid.innerHTML = `
                    <div class="col-span-full empty-state py-16">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                        </svg>
                        <h3 class="text-lg font-semibold text-brand-text mb-1">${t('gallery.no_assets')}</h3>
                        <p class="text-brand-text-muted text-sm mb-4">${t('gallery.no_assets_desc')}</p>
                        <a href="#image-studio" class="btn btn-primary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                            </svg>
                            ${t('gallery.go_to_studio')}
                        </a>
                    </div>
                `;
                return;
            }

            grid.innerHTML = displayItems.map((item) => this._cardHTML(item)).join('');

            // Card click → open viewer (image) or video player (video)
            grid.querySelectorAll('.gallery-card').forEach((card) => {
                card.addEventListener('click', () => {
                    const id = card.dataset.id;
                    const media = card.dataset.media;
                    const idx = displayItems.findIndex((i) => String(i.id) === String(id));
                    if (idx < 0) return;
                    if (media === 'video' && window.VideoStudio?._openVideoPlayer) {
                        window.VideoStudio._openVideoPlayer(id);
                    } else {
                        AssetViewer.open(displayItems[idx], displayItems, idx);
                    }
                });
            });

            // Checkbox change → toggle selection
            grid.querySelectorAll('.gal-select-cb').forEach((cb) => {
                cb.addEventListener('change', () => {
                    const id = cb.dataset.id;
                    if (cb.checked) {
                        this._selected.add(id);
                    } else {
                        this._selected.delete(id);
                    }
                    // Update card ring highlight
                    const card = cb.closest('.gallery-card');
                    if (card) card.classList.toggle('ring-2', cb.checked);
                    if (card) card.classList.toggle('ring-red-500/50', cb.checked);
                    this._updateSelectionUI();
                });
            });

            // Sync selection bar visibility after render
            this._updateSelectionUI();
        },

        _cardHTML(item) {
            const isVideo = item._media === 'video';
            const thumbUrl = isVideo
                ? API.video.thumbnailUrl(item.id) + `?t=${this._cacheKey || '0'}`
                : API.gallery.pngUrl(item.id) + `?t=${this._cacheKey || '0'}`;
            const createdAt = item.created_at ? window.formatDate(item.created_at) : '';
            const styleName = item.style_name || this._findStyleName(item.style_id) || '';
            const prompt = item.original_prompt || item.prompt || '';
            const truncPrompt = prompt.length > 80 ? prompt.substring(0, 80) + '...' : prompt;
            const isSelected = this._selected.has(item.id);
            const duration = item.duration_seconds ? `${Math.round(item.duration_seconds)}s` : '';

            return `
                <div class="gallery-card card cursor-pointer overflow-hidden group ${isSelected ? 'ring-2 ring-red-500/50' : ''}" data-id="${this._esc(item.id)}" data-media="${isVideo ? 'video' : 'image'}">
                    <div class="img-hover-zoom ${isVideo ? 'aspect-video' : 'aspect-[4/3]'} bg-brand-bg flex items-center justify-center overflow-hidden relative">
                        ${item.async_status === 'pending' || item.async_status === 'generating'
                            ? `<div class="w-full h-full flex flex-col items-center justify-center text-cyan-400/60 gap-2">
                                <svg class="w-8 h-8 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                                <span class="text-[10px]">Generating...</span>
                               </div>`
                            : item.async_status === 'failed'
                            ? `<div class="w-full h-full flex flex-col items-center justify-center text-red-400/60 gap-2">
                                <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.962-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                                <span class="text-[10px]">Failed</span>
                               </div>`
                            : `<img src="${thumbUrl}" alt="${isVideo ? t('gallery.alt_video_thumb') : t('gallery.alt_asset')}"
                                 class="w-full h-full object-cover"
                                 loading="lazy" />`
                        }
                        ${isVideo ? `
                            <div class="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/40 transition-colors">
                                <svg class="w-10 h-10 text-white/80 group-hover:text-white group-hover:scale-110 transition-all" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M8 5v14l11-7z"/>
                                </svg>
                            </div>
                            ${duration ? `<span class="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] px-1.5 py-0.5 rounded">${duration}</span>` : ''}
                        ` : ''}
                        <label class="gal-checkbox absolute top-2 left-2 z-10" onclick="event.stopPropagation()">
                            <input type="checkbox" class="gal-select-cb w-4 h-4 rounded border-brand-border bg-brand-bg/80 text-red-500 focus:ring-red-500 cursor-pointer"
                                data-id="${this._esc(item.id)}" ${isSelected ? 'checked' : ''} />
                        </label>
                        ${isVideo ? `<span class="absolute top-2 right-2 bg-brand-accent/80 text-white text-[9px] px-1.5 py-0.5 rounded font-medium">${t('gallery.video_badge')}</span>` : ''}
                    </div>
                    <div class="p-4 space-y-2">
                        <p class="text-sm text-brand-text line-clamp-2 group-hover:text-brand-accent transition-colors">${this._esc(truncPrompt) || `<em class="text-brand-text-muted">${t('gallery.no_prompt')}</em>`}</p>
                        <div class="flex items-center flex-wrap gap-2 text-xs text-brand-text-muted">
                            ${item.image_model === 'imported'
                                ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('gallery.imported_badge')}</span>`
                                : (item.model_label ? `<span class="badge badge-indigo">${this._esc(item.model_label)}</span>` : '')}
                            ${styleName ? `<span class="badge badge-indigo">${this._esc(styleName)}</span>` : ''}
                            ${item.asset_type && item.asset_type !== 'video' ? `<span class="badge badge-indigo">${this._esc(item.asset_type)}</span>` : ''}
                            ${createdAt ? `<span>${createdAt}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        },

        _skeletons(n) {
            let html = '';
            for (let i = 0; i < n; i++) {
                html += `
                    <div class="card overflow-hidden">
                        <div class="skeleton aspect-[4/3]"></div>
                        <div class="p-4 space-y-2">
                            <div class="skeleton h-4 w-full rounded"></div>
                            <div class="skeleton h-4 w-2/3 rounded"></div>
                            <div class="skeleton h-3 w-1/3 rounded"></div>
                        </div>
                    </div>`;
            }
            return html;
        },

        _findStyleName(styleId) {
            if (!styleId) return '';
            const s = this._styles.find((st) => String(st.id) === String(styleId));
            return s ? s.name : '';
        },

        _esc(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        },
    };
})();
