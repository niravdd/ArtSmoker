/**
 * ArtSmoker — AssetViewer Component
 *
 * Modal overlay showing full-size image, complete metadata,
 * and a "Reload in Generator" button.
 *
 * Usage:
 *   AssetViewer.open(galleryItem)   // opens modal, fetches full metadata
 *   AssetViewer.close()
 */
(function () {
    'use strict';

    const MODEL_LABELS = {
        nova_canvas: 'Amazon Nova Canvas',
        titan_image: 'Amazon Titan Image v2',
    };

    const TYPE_LABELS = {
        game_asset: 'Game Asset',
        marketing_banner: 'Marketing Banner',
        icon: 'Icon',
        character: 'Character',
        environment: 'Environment',
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
                            <button class="btn-reload btn btn-primary btn-sm" title="Reload this batch in Generator">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                </svg>
                                Reload in Generator
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
                        <button class="tab" data-tab="svg">SVG</button>
                        <button class="tab" data-tab="meta">Metadata</button>
                    </div>

                    <!-- Tab Content -->
                    <div class="flex-1 overflow-auto p-6">
                        <!-- PNG tab -->
                        <div class="tab-panel" data-panel="png">
                            <div class="preview-checkerboard rounded-lg flex items-center justify-center p-4 min-h-[300px]">
                                <img src="${pngUrl}" alt="Generated PNG" class="max-w-full max-h-[60vh] rounded shadow-lg" loading="lazy" />
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
                        <a href="${svgUrl}" download="${this._esc(item.svg_filename || 'asset.svg')}" class="btn btn-secondary btn-sm">
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
            const modelLabel = MODEL_LABELS[meta.image_model] || meta.image_model || 'N/A';
            const typeLabel = TYPE_LABELS[meta.asset_type] || meta.asset_type || 'N/A';

            container.innerHTML = `
                ${meta.original_prompt ? `
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Original Prompt</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.original_prompt)}</p>
                </div>` : ''}
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">${meta.original_prompt ? 'AI-Improved Prompt' : 'Prompt'}</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(meta.prompt || 'N/A')}</p>
                </div>
                <div>
                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Generation Prompt (sent to image model)</label>
                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._esc(meta.refined_prompt || 'N/A')}</p>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Style</label>
                        <p class="font-medium">${this._esc(meta.style_id || 'None')}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Asset Type</label>
                        <p class="font-medium">${typeLabel}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Image Model</label>
                        <p class="font-medium">${modelLabel}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Dimensions</label>
                        <p class="font-medium">${meta.width || '?'} x ${meta.height || '?'}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Seed</label>
                        <p class="font-medium font-mono text-xs">${meta.seed ?? 'N/A'}</p>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Created</label>
                        <p class="font-medium">${createdAt}</p>
                    </div>
                </div>
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
            `;
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

            // Reload in Generator
            this._overlay.querySelector('.btn-reload')?.addEventListener('click', async () => {
                const meta = this._meta;
                if (!meta) {
                    window.showToast?.('Metadata not loaded yet', 'warning');
                    return;
                }
                const batchId = meta.batch_id || meta.id;
                this.close();
                await Generator.loadBatch(batchId);
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
