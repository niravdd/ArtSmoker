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

        render() {
            return `
                <div id="gallery-view" class="space-y-6 view-enter">
                    <!-- Header -->
                    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 class="text-2xl font-bold">Gallery</h1>
                            <p class="text-sm text-brand-text-muted mt-1">Browse your generated art assets</p>
                        </div>
                        <a href="#generator" class="btn btn-primary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                            </svg>
                            Generate New
                        </a>
                    </div>

                    <!-- Filter Bar -->
                    <div class="card-static p-4">
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

            // Load More button
            document.getElementById('btn-load-more')?.addEventListener('click', () => this._loadMore());

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

        _updateLoadMore() {
            const section = document.getElementById('gal-load-more');
            if (section) {
                section.classList.toggle('hidden', !this._hasMore);
            }
            const countEl = document.getElementById('gal-count');
            if (countEl) {
                countEl.classList.remove('hidden');
                countEl.textContent = `${this._items.length} asset${this._items.length !== 1 ? 's' : ''}${this._hasMore ? ' (more available)' : ''}`;
            }
        },

        // --------------------------------------------------------
        //  Rendering
        // --------------------------------------------------------

        _renderGrid() {
            const grid = document.getElementById('gallery-grid');
            if (!grid) return;

            if (this._items.length === 0) {
                grid.innerHTML = `
                    <div class="col-span-full empty-state py-16">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                        </svg>
                        <h3 class="text-lg font-semibold text-brand-text mb-1">No Assets Yet</h3>
                        <p class="text-brand-text-muted text-sm mb-4">Generate your first image to see it here.</p>
                        <a href="#generator" class="btn btn-primary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                            </svg>
                            Go to Generator
                        </a>
                    </div>
                `;
                return;
            }

            grid.innerHTML = this._items.map((item) => this._cardHTML(item)).join('');

            // Attach click events
            grid.querySelectorAll('.gallery-card').forEach((card) => {
                card.addEventListener('click', () => {
                    const id = card.dataset.id;
                    const item = this._items.find((i) => String(i.id) === String(id));
                    if (item) AssetViewer.open(item);
                });
            });
        },

        _cardHTML(item) {
            const pngUrl = API.gallery.pngUrl(item.id);
            const createdAt = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
            const styleName = item.style_name || this._findStyleName(item.style_id) || '';
            const prompt = item.prompt || '';
            const truncPrompt = prompt.length > 80 ? prompt.substring(0, 80) + '...' : prompt;

            return `
                <div class="gallery-card card cursor-pointer overflow-hidden group" data-id="${this._esc(item.id)}">
                    <div class="img-hover-zoom aspect-[4/3] bg-brand-bg flex items-center justify-center overflow-hidden relative">
                        <img src="${pngUrl}" alt="Generated asset"
                             class="w-full h-full object-cover"
                             loading="lazy" />
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
