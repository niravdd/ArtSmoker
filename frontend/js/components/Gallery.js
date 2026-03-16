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

        render() {
            return `
                <div id="gallery-view" class="space-y-6 view-enter">
                    <!-- Header -->
                    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 class="text-2xl font-bold">Gallery</h1>
                            <p class="text-sm text-brand-text-muted mt-1">Browse your generated art assets</p>
                        </div>
                        <a href="#image-studio" class="btn btn-primary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                            </svg>
                            Generate New
                        </a>
                    </div>

                    <!-- Selection bar (hidden until items are selected) -->
                    <div id="gal-selection-bar" class="hidden card-static p-3 bg-red-950/30 border-red-500/30 flex items-center justify-between gap-4">
                        <div class="flex items-center gap-3">
                            <button id="gal-select-all" class="btn btn-secondary btn-sm text-xs">Select All</button>
                            <button id="gal-deselect-all" class="btn btn-secondary btn-sm text-xs">Deselect All</button>
                            <span id="gal-selected-count" class="text-sm text-red-300 font-medium"></span>
                        </div>
                        <div class="flex items-center gap-3">
                            <span class="text-[10px] text-red-400/70">Deletion is permanent and cannot be undone</span>
                            <button id="gal-delete-btn" class="btn btn-sm bg-red-600 hover:bg-red-500 text-white">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                                </svg>
                                Delete Selected
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
                            <input type="text" id="gal-search" class="input w-full pl-10" placeholder="Search prompts, styles, types...">
                        </div>
                        <!-- Filters -->
                        <div class="flex flex-wrap items-center gap-3">
                            <div class="flex-1 min-w-[160px]">
                                <label class="block text-xs text-brand-text-muted mb-1">Style</label>
                                <select id="gal-filter-style" class="input">
                                    <option value="">All Styles</option>
                                </select>
                            </div>
                            <div class="flex-1 min-w-[160px]">
                                <label class="block text-xs text-brand-text-muted mb-1">Asset Type</label>
                                <select id="gal-filter-type" class="input">
                                    <option value="">All Types</option>
                                    <option value="game_asset">Game Asset</option>
                                    <option value="marketing_banner">Marketing Banner</option>
                                    <option value="icon">Icon</option>
                                    <option value="character">Character</option>
                                    <option value="environment">Environment</option>
                                </select>
                            </div>
                            <div class="flex-1 min-w-[160px]">
                                <label class="block text-xs text-brand-text-muted mb-1">Sort By</label>
                                <select id="gal-sort" class="input">
                                    <option value="newest">Newest First</option>
                                    <option value="oldest">Oldest First</option>
                                </select>
                            </div>
                            <div class="flex items-end">
                                <button id="gal-apply-filter" class="btn btn-secondary btn-sm mt-4">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/>
                                    </svg>
                                    Apply
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
                        <button id="btn-load-more" class="btn btn-secondary btn-sm">Load More</button>
                    </div>
                </div>
            `;
        },

        async init() {
            // Load styles for filter dropdown
            this._loadStylesFilter();

            // Filter apply button
            document.getElementById('gal-apply-filter')?.addEventListener('click', () => this._loadItems(true));

            // Also apply on dropdown change
            ['gal-filter-style', 'gal-filter-type', 'gal-sort'].forEach((id) => {
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
                const items = this._filteredItems !== null ? this._filteredItems : this._items;
                items.forEach(i => this._selected.add(i.id));
                this._updateSelectionUI();
            });
            document.getElementById('gal-deselect-all')?.addEventListener('click', () => {
                this._selected.clear();
                this._updateSelectionUI();
            });
            document.getElementById('gal-delete-btn')?.addEventListener('click', () => this._handleDelete());

            // Load items
            await this._loadItems(true);
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

        async _loadItems(reset = true) {
            if (this._loading) return;
            this._loading = true;

            const grid = document.getElementById('gallery-grid');

            if (reset) {
                this._items = [];
                this._offset = 0;
                if (grid) grid.innerHTML = this._skeletons(8);
            }

            const params = { limit: PAGE_SIZE, offset: this._offset };
            const styleId = document.getElementById('gal-filter-style')?.value;
            const assetType = document.getElementById('gal-filter-type')?.value;

            if (styleId) params.style_id = styleId;
            if (assetType) params.asset_type = assetType;

            try {
                const data = await API.gallery.list(params);
                const page = Array.isArray(data) ? data : (data.items || data.gallery || []);
                this._items.push(...page);
                this._offset += page.length;
                this._hasMore = page.length === PAGE_SIZE;
                this._lastLoadTime = Date.now();
                this._renderGrid();
                this._updateLoadMore();
            } catch (err) {
                console.error('Gallery load error:', err);
                if (grid && this._items.length === 0) {
                    grid.innerHTML = `<div class="col-span-full text-center py-8 text-red-400">Failed to load gallery.</div>`;
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
            if (count) count.textContent = `${n} item${n !== 1 ? 's' : ''} selected`;

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

            if (!confirm(`Permanently delete ${ids.length} asset${ids.length !== 1 ? 's' : ''}? This cannot be undone.`)) return;

            window.showLoading?.(`Deleting ${ids.length} asset${ids.length !== 1 ? 's' : ''}...`);
            try {
                const result = await API.gallery.delete(ids);
                window.hideLoading?.();
                this._selected.clear();
                window.showToast?.(`${(result.deleted || []).length} asset${(result.deleted || []).length !== 1 ? 's' : ''} deleted`, 'success');
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
                        item.style_id || '',
                        item.asset_type || '',
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
                const searchNote = this._filteredItems !== null ? ` (${displayItems.length} matching)` : '';
                countEl.textContent = `${this._items.length} asset${this._items.length !== 1 ? 's' : ''}${searchNote}${this._hasMore ? ' — more available' : ''}`;
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
                        <p class="text-sm">No assets match your search.</p>
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
                        <h3 class="text-lg font-semibold text-brand-text mb-1">No Assets Yet</h3>
                        <p class="text-brand-text-muted text-sm mb-4">Generate your first image to see it here.</p>
                        <a href="#image-studio" class="btn btn-primary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                            </svg>
                            Go to 2D Image Studio
                        </a>
                    </div>
                `;
                return;
            }

            grid.innerHTML = displayItems.map((item) => this._cardHTML(item)).join('');

            // Card click → open viewer
            grid.querySelectorAll('.gallery-card').forEach((card) => {
                card.addEventListener('click', () => {
                    const id = card.dataset.id;
                    const item = displayItems.find((i) => String(i.id) === String(id));
                    if (item) AssetViewer.open(item);
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
            const pngUrl = API.gallery.pngUrl(item.id);
            const createdAt = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
            const styleName = item.style_name || this._findStyleName(item.style_id) || '';
            const prompt = item.prompt || '';
            const truncPrompt = prompt.length > 80 ? prompt.substring(0, 80) + '...' : prompt;
            const isSelected = this._selected.has(item.id);

            return `
                <div class="gallery-card card cursor-pointer overflow-hidden group ${isSelected ? 'ring-2 ring-red-500/50' : ''}" data-id="${this._esc(item.id)}">
                    <div class="img-hover-zoom aspect-[4/3] bg-brand-bg flex items-center justify-center overflow-hidden relative">
                        <img src="${pngUrl}" alt="Generated asset"
                             class="w-full h-full object-cover"
                             loading="lazy" />
                        <label class="gal-checkbox absolute top-2 left-2 z-10" onclick="event.stopPropagation()">
                            <input type="checkbox" class="gal-select-cb w-4 h-4 rounded border-brand-border bg-brand-bg/80 text-red-500 focus:ring-red-500 cursor-pointer"
                                data-id="${this._esc(item.id)}" ${isSelected ? 'checked' : ''} />
                        </label>
                    </div>
                    <div class="p-4 space-y-2">
                        <p class="text-sm text-brand-text line-clamp-2 group-hover:text-brand-accent transition-colors">${this._esc(truncPrompt) || '<em class="text-brand-text-muted">No prompt</em>'}</p>
                        <div class="flex items-center flex-wrap gap-2 text-xs text-brand-text-muted">
                            ${styleName ? `<span class="badge badge-indigo">${this._esc(styleName)}</span>` : ''}
                            ${item.asset_type ? `<span class="badge badge-indigo">${this._esc(item.asset_type)}</span>` : ''}
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
