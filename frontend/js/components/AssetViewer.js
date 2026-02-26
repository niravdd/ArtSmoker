/**
 * ArtSmoker — AssetViewer Component
 *
 * Modal overlay that shows full-size image with PNG/SVG tabs,
 * download buttons, and metadata.
 *
 * Usage:
 *   AssetViewer.open(galleryItem)   // show the modal
 *   AssetViewer.close()             // close it
 */
(function () {
    'use strict';

    const AssetViewer = {
        _overlay: null,
        _item: null,
        _currentTab: 'png',

        /**
         * Open the viewer for a gallery item.
         * @param {object} item - gallery item from API
         */
        open(item) {
            this._item = item;
            this._currentTab = 'png';
            this._renderModal();
            this._attachEvents();
            document.body.style.overflow = 'hidden';
        },

        /** Close and clean up */
        close() {
            if (this._overlay) {
                this._overlay.remove();
                this._overlay = null;
            }
            document.body.style.overflow = '';
        },

        // -- Private --

        _renderModal() {
            // Remove any existing overlay
            if (this._overlay) this._overlay.remove();

            const item = this._item;
            const pngUrl = API.gallery.pngUrl(item.id);
            const svgUrl = API.gallery.svgUrl(item.id);
            const createdAt = item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A';

            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            overlay.innerHTML = `
                <div class="modal-content bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                        <h2 class="text-lg font-semibold truncate">Generated Asset</h2>
                        <button class="btn-close p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors" title="Close">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
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

                        <!-- Metadata tab -->
                        <div class="tab-panel hidden" data-panel="meta">
                            <div class="space-y-4 text-sm">
                                <div>
                                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Prompt</label>
                                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(item.prompt || 'N/A')}</p>
                                </div>
                                ${item.refined_prompt ? `
                                <div>
                                    <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Refined Prompt</label>
                                    <p class="p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap">${this._esc(item.refined_prompt)}</p>
                                </div>` : ''}
                                <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                                    <div>
                                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Style</label>
                                        <p class="font-medium">${this._esc(item.style_name || item.style_id || 'None')}</p>
                                    </div>
                                    <div>
                                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Asset Type</label>
                                        <p class="font-medium">${this._esc(item.asset_type || 'N/A')}</p>
                                    </div>
                                    <div>
                                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Dimensions</label>
                                        <p class="font-medium">${item.width || '?'} x ${item.height || '?'}</p>
                                    </div>
                                    <div>
                                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Model</label>
                                        <p class="font-medium">${this._esc(item.model || 'N/A')}</p>
                                    </div>
                                    <div>
                                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1">Created</label>
                                        <p class="font-medium">${createdAt}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Footer with download buttons -->
                    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-brand-border">
                        <a href="${pngUrl}" download class="btn btn-secondary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                            </svg>
                            Download PNG
                        </a>
                        <a href="${svgUrl}" download class="btn btn-secondary btn-sm">
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

        _attachEvents() {
            if (!this._overlay) return;

            // Close button
            this._overlay.querySelector('.btn-close').addEventListener('click', () => this.close());

            // Click outside modal content
            this._overlay.addEventListener('click', (e) => {
                if (e.target === this._overlay) this.close();
            });

            // Escape key
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
                    const target = tab.dataset.tab;
                    // Update tabs
                    this._overlay.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
                    tab.classList.add('active');
                    // Update panels
                    this._overlay.querySelectorAll('.tab-panel').forEach((p) => {
                        p.classList.toggle('hidden', p.dataset.panel !== target);
                    });
                });
            });
        },

        /** Escape HTML to prevent XSS */
        _esc(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        },
    };

    window.AssetViewer = AssetViewer;
})();
