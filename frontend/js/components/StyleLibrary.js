/**
 * ArtSmoker — StyleLibrary Component
 *
 * Grid of style profile cards with CRUD, reference image upload,
 * drag-and-drop, and AI analysis.
 */
(function () {
    'use strict';

    window.StyleLibrary = {
        _styles: [],
        _activeDetail: null,  // style id currently shown in detail

        /** Render the view HTML */
        render() {
            return `
                <div id="style-library" class="space-y-6 view-enter">
                    <!-- Header -->
                    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 class="text-2xl font-bold">Style Library</h1>
                            <p class="text-sm text-brand-text-muted mt-1">Manage your art style profiles and reference images</p>
                        </div>
                        <button class="btn-create-style btn btn-primary">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                            </svg>
                            Create New Style
                        </button>
                    </div>

                    <!-- Grid / empty state -->
                    <div id="styles-grid" class="gallery-grid">
                        <!-- Skeleton placeholders while loading -->
                        ${StyleLibrary._skeletons(6)}
                    </div>

                    <!-- Detail overlay (hidden) -->
                    <div id="style-detail-overlay" class="hidden"></div>
                </div>

                <!-- Create / Edit Modal -->
                <div id="style-modal" class="hidden fixed inset-0 z-[70] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
                    <div class="modal-content bg-brand-surface rounded-xl border border-brand-border shadow-2xl w-full max-w-lg">
                        <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                            <h3 id="style-modal-title" class="text-lg font-semibold">Create New Style</h3>
                            <button class="btn-close-modal p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                        <form id="style-form" class="p-6 space-y-4">
                            <input type="hidden" id="style-form-id" value="">
                            <div>
                                <label class="block text-sm font-medium mb-1" for="style-name">Name</label>
                                <input id="style-name" class="input" type="text" placeholder="e.g. Pixel Art, Watercolor..." required>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1" for="style-description">Description</label>
                                <textarea id="style-description" class="input" rows="3" placeholder="Describe this art style..."></textarea>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1" for="style-hints">Generation Hints</label>
                                <textarea id="style-hints" class="input" rows="2" placeholder="Additional hints for the AI when generating..."></textarea>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1" for="style-import-path">Import References From</label>
                                <div class="flex gap-2">
                                    <input id="style-import-path" class="input flex-1" type="text" placeholder="/path/to/images  or  s3://bucket/prefix">
                                    <button type="button" id="btn-browse-local" class="btn btn-secondary btn-sm whitespace-nowrap">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                                        </svg>
                                        Local
                                    </button>
                                    <button type="button" id="btn-browse-s3" class="btn btn-secondary btn-sm whitespace-nowrap">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/>
                                        </svg>
                                        S3
                                    </button>
                                </div>
                                <p class="text-[10px] text-brand-text-muted mt-1">Paste a path, or use Local / S3 to browse and select.</p>
                            </div>
                            <div class="flex justify-end gap-2 pt-2">
                                <button type="button" class="btn-cancel-modal btn btn-secondary">Cancel</button>
                                <button type="submit" class="btn btn-primary">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                    </svg>
                                    Save
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
        },

        /** Attach event listeners after render */
        async init() {
            // Create style button
            document.querySelector('.btn-create-style')?.addEventListener('click', () => this._openModal());

            // Modal close / cancel
            document.querySelector('.btn-close-modal')?.addEventListener('click', () => this._closeModal());
            document.querySelector('.btn-cancel-modal')?.addEventListener('click', () => this._closeModal());

            // Click outside modal
            document.getElementById('style-modal')?.addEventListener('click', (e) => {
                if (e.target.id === 'style-modal') this._closeModal();
            });

            // Form submit
            document.getElementById('style-form')?.addEventListener('submit', (e) => {
                e.preventDefault();
                this._handleSave();
            });

            // Browse Local button in create modal
            document.getElementById('btn-browse-local')?.addEventListener('click', () => {
                this._openBrowseModal('local', 'style-import-path');
            });

            // Browse S3 button in create modal
            document.getElementById('btn-browse-s3')?.addEventListener('click', () => {
                this._openBrowseModal('s3', 'style-import-path');
            });

            // Load styles
            await this._loadStyles();
        },

        // --------------------------------------------------------
        //  Data Loading
        // --------------------------------------------------------

        async _loadStyles() {
            try {
                const data = await API.styles.list();
                this._styles = Array.isArray(data) ? data : (data.styles || data.items || []);
                this._renderGrid();
            } catch (err) {
                console.error('Failed to load styles:', err);
                this._renderGrid();
            }
        },

        // --------------------------------------------------------
        //  Grid Rendering
        // --------------------------------------------------------

        _renderGrid() {
            const grid = document.getElementById('styles-grid');
            if (!grid) return;

            if (this._styles.length === 0) {
                grid.innerHTML = `
                    <div class="col-span-full empty-state py-16">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                                d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
                        </svg>
                        <h3 class="text-lg font-semibold text-brand-text mb-1">No Styles Yet</h3>
                        <p class="text-brand-text-muted text-sm mb-4">Create your first art style profile to get started.</p>
                        <button class="btn btn-primary btn-sm btn-create-first">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                            </svg>
                            Create Style
                        </button>
                    </div>
                `;
                grid.querySelector('.btn-create-first')?.addEventListener('click', () => this._openModal());
                return;
            }

            grid.innerHTML = this._styles.map((s) => this._cardHTML(s)).join('');

            // Attach click listeners to cards
            grid.querySelectorAll('.style-card').forEach((card) => {
                card.addEventListener('click', () => {
                    const id = card.dataset.id;
                    this._showDetail(id);
                });
            });
        },

        _cardHTML(style) {
            const thumb = style.reference_images && style.reference_images.length > 0
                ? API.styles.referenceUrl(style.id, style.reference_images[0])
                : null;
            const refCount = (style.reference_images || []).length;

            return `
                <div class="style-card card cursor-pointer overflow-hidden group" data-id="${this._esc(style.id)}">
                    <div class="img-hover-zoom aspect-video bg-brand-bg flex items-center justify-center overflow-hidden">
                        ${thumb
                            ? `<img src="${thumb}" alt="${this._esc(style.name)}" class="w-full h-full object-cover" loading="lazy"/>`
                            : `<svg class="w-12 h-12 text-brand-text-muted/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                               </svg>`
                        }
                    </div>
                    <div class="p-4">
                        <h3 class="font-semibold text-brand-text group-hover:text-brand-accent transition-colors truncate">${this._esc(style.name)}</h3>
                        <p class="text-sm text-brand-text-muted mt-1 line-clamp-2">${this._esc(style.description || 'No description')}</p>
                        <div class="flex items-center gap-3 mt-3 text-xs text-brand-text-muted">
                            <span class="badge badge-indigo">${refCount} ref${refCount !== 1 ? 's' : ''}</span>
                            ${style.analyzed_style ? '<span class="badge badge-green">Analyzed</span>' : ''}
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
                        <div class="skeleton aspect-video"></div>
                        <div class="p-4 space-y-2">
                            <div class="skeleton h-5 w-3/4 rounded"></div>
                            <div class="skeleton h-4 w-full rounded"></div>
                            <div class="skeleton h-4 w-1/2 rounded"></div>
                        </div>
                    </div>`;
            }
            return html;
        },

        // --------------------------------------------------------
        //  Detail View
        // --------------------------------------------------------

        async _showDetail(id) {
            this._activeDetail = id;
            const overlay = document.getElementById('style-detail-overlay');
            if (!overlay) return;

            overlay.classList.remove('hidden');
            overlay.innerHTML = `<div class="flex items-center justify-center py-12"><div class="loading-spinner w-8 h-8 border-4 border-brand-accent/20 border-t-brand-accent rounded-full"></div></div>`;

            try {
                const style = await API.styles.get(id);
                if (this._activeDetail !== id) return; // user navigated away
                overlay.innerHTML = this._detailHTML(style);
                this._attachDetailEvents(style);
            } catch (err) {
                overlay.innerHTML = `<div class="text-center py-12 text-red-400">Failed to load style.</div>`;
            }
        },

        _detailHTML(style) {
            const refs = style.reference_images || [];
            const analyzedJson = style.analyzed_style ? JSON.stringify(style.analyzed_style, null, 2) : null;

            return `
                <div class="card-static p-6 space-y-6 fade-in">
                    <!-- Back + Title -->
                    <div class="flex items-start justify-between gap-4">
                        <div class="flex items-center gap-3">
                            <button class="btn-back-list btn btn-secondary btn-sm !p-2 rounded-lg">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                                </svg>
                            </button>
                            <div>
                                <h2 class="text-xl font-bold">${this._esc(style.name)}</h2>
                                <p class="text-sm text-brand-text-muted mt-0.5">${this._esc(style.description || '')}</p>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button class="btn-edit-style btn btn-secondary btn-sm" data-id="${style.id}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                </svg>
                                Edit
                            </button>
                            <button class="btn-delete-style btn btn-danger btn-sm" data-id="${style.id}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                                </svg>
                                Delete
                            </button>
                        </div>
                    </div>

                    ${style.generation_hints ? `
                    <div>
                        <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wider mb-2">Generation Hints</h3>
                        <p class="text-sm p-3 rounded-lg bg-brand-bg/60">${this._esc(style.generation_hints)}</p>
                    </div>` : ''}

                    <!-- Reference Images -->
                    <div>
                        <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wider mb-3">Reference Images (${refs.length})</h3>
                        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-4">
                            ${refs.map((filename) => `
                                <div class="img-hover-zoom rounded-lg overflow-hidden aspect-square bg-brand-bg border border-brand-border">
                                    <img src="${API.styles.referenceUrl(style.id, filename)}" alt="Reference" class="w-full h-full object-cover" loading="lazy"/>
                                </div>
                            `).join('')}
                        </div>

                        <!-- Upload Zone -->
                        <div class="upload-zone p-8 text-center" id="ref-upload-zone" data-style-id="${style.id}">
                            <svg class="w-10 h-10 mx-auto text-brand-text-muted mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                            </svg>
                            <p class="text-sm text-brand-text-muted mb-1">Drag & drop reference images here</p>
                            <p class="text-xs text-brand-text-muted/60">or click to browse</p>
                            <input type="file" class="ref-file-input hidden" multiple accept="image/*" />
                        </div>

                        <!-- Import from path -->
                        <div class="mt-4 p-4 rounded-lg border border-brand-border bg-brand-bg/40 space-y-3">
                            <h4 class="text-sm font-medium flex items-center gap-2">
                                <svg class="w-4 h-4 text-brand-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                                </svg>
                                Import from directory or S3
                            </h4>
                            <div class="flex gap-2">
                                <input
                                    type="text"
                                    id="import-path-input"
                                    class="input flex-1"
                                    placeholder="/path/to/images  or  s3://bucket/prefix"
                                />
                                <button id="btn-detail-browse-local" class="btn btn-secondary btn-sm whitespace-nowrap">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                                    </svg>
                                    Local
                                </button>
                                <button id="btn-detail-browse-s3" class="btn btn-secondary btn-sm whitespace-nowrap">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/>
                                    </svg>
                                    S3
                                </button>
                                <button id="btn-import-path" class="btn btn-primary btn-sm whitespace-nowrap">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707"/>
                                    </svg>
                                    Import & Analyze
                                </button>
                            </div>
                            <p class="text-[10px] text-brand-text-muted/60">Imports images recursively from a local directory or S3 URI, then runs AI style analysis.</p>
                        </div>
                    </div>

                    <!-- Re-Analyze Button (only useful after editing hints or to refresh) -->
                    ${refs.length > 0 ? `
                    <div class="flex items-center gap-3">
                        <button class="btn-analyze btn ${style.analyzed_style ? 'btn-secondary' : 'btn-primary'}" data-id="${style.id}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                            </svg>
                            ${style.analyzed_style ? 'Re-Analyze Style' : 'Analyze Style'}
                        </button>
                        <span class="text-xs text-brand-text-muted">${style.analyzed_style
                            ? 'Re-run analysis — useful after editing generation hints or adding new references'
                            : 'Run AI analysis on your reference images to extract the style profile'
                        }</span>
                    </div>` : ''}

                    <!-- Analyzed Style JSON -->
                    ${analyzedJson ? `
                    <div>
                        <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wider mb-2">Analyzed Style</h3>
                        <pre class="p-4 rounded-lg bg-brand-bg/80 text-xs text-brand-text-muted overflow-x-auto border border-brand-border font-mono leading-relaxed">${this._esc(analyzedJson)}</pre>
                    </div>` : ''}
                </div>
            `;
        },

        _attachDetailEvents(style) {
            // Back button
            document.querySelector('.btn-back-list')?.addEventListener('click', () => {
                this._activeDetail = null;
                const overlay = document.getElementById('style-detail-overlay');
                if (overlay) overlay.classList.add('hidden');
            });

            // Edit button
            document.querySelector('.btn-edit-style')?.addEventListener('click', () => {
                this._openModal(style);
            });

            // Delete button
            document.querySelector('.btn-delete-style')?.addEventListener('click', async () => {
                if (!confirm(`Delete style "${style.name}"? This cannot be undone.`)) return;
                try {
                    window.showLoading && window.showLoading('Deleting...');
                    await API.styles.delete(style.id);
                    window.hideLoading && window.hideLoading();
                    window.showToast && window.showToast('Style deleted', 'success');
                    this._activeDetail = null;
                    const overlay = document.getElementById('style-detail-overlay');
                    if (overlay) overlay.classList.add('hidden');
                    await this._loadStyles();
                } catch (err) {
                    window.hideLoading && window.hideLoading();
                }
            });

            // Upload zone — drag and drop
            const zone = document.getElementById('ref-upload-zone');
            const fileInput = zone?.querySelector('.ref-file-input');

            if (zone && fileInput) {
                zone.addEventListener('click', () => fileInput.click());
                zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
                zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
                zone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    zone.classList.remove('drag-over');
                    if (e.dataTransfer.files.length) this._uploadRefs(style.id, e.dataTransfer.files);
                });
                fileInput.addEventListener('change', () => {
                    if (fileInput.files.length) this._uploadRefs(style.id, fileInput.files);
                });
            }

            // Browse Local / S3 in detail view
            document.getElementById('btn-detail-browse-local')?.addEventListener('click', () => {
                this._openBrowseModal('local', 'import-path-input');
            });
            document.getElementById('btn-detail-browse-s3')?.addEventListener('click', () => {
                this._openBrowseModal('s3', 'import-path-input');
            });

            // Import & Analyze button
            document.getElementById('btn-import-path')?.addEventListener('click', async () => {
                const input = document.getElementById('import-path-input');
                const path = input?.value.trim();
                if (!path) {
                    window.showToast?.('Enter a directory path or S3 URI', 'warning');
                    return;
                }
                const btn = document.getElementById('btn-import-path');
                const origHTML = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-sm"></span> Importing & analyzing...';
                btn.disabled = true;
                try {
                    await API.styles.importPath(style.id, path, true);
                    window.showToast?.('References imported and analyzed', 'success');
                    this._showDetail(style.id);
                    await this._loadStyles();
                } catch (err) {
                    btn.innerHTML = origHTML;
                    btn.disabled = false;
                }
            });

            // Enter key in import input
            document.getElementById('import-path-input')?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    document.getElementById('btn-import-path')?.click();
                }
            });

            // Analyze button
            document.querySelector('.btn-analyze')?.addEventListener('click', async () => {
                const btn = document.querySelector('.btn-analyze');
                const origHTML = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-sm"></span> Analyzing...';
                btn.disabled = true;
                try {
                    await API.styles.analyze(style.id);
                    window.showToast && window.showToast('Style analysis complete', 'success');
                    // Refresh detail
                    this._showDetail(style.id);
                } catch (err) {
                    btn.innerHTML = origHTML;
                    btn.disabled = false;
                }
            });
        },

        async _uploadRefs(styleId, files) {
            window.showLoading && window.showLoading('Uploading references...');
            try {
                await API.styles.uploadReferences(styleId, files);
                window.hideLoading && window.hideLoading();
                window.showToast && window.showToast(`${files.length} image(s) uploaded`, 'success');
                this._showDetail(styleId);
                await this._loadStyles(); // refresh cards too
            } catch (err) {
                window.hideLoading && window.hideLoading();
            }
        },

        // --------------------------------------------------------
        //  Modal (Create / Edit)
        // --------------------------------------------------------

        _openModal(style = null) {
            const modal = document.getElementById('style-modal');
            const title = document.getElementById('style-modal-title');
            const idField = document.getElementById('style-form-id');
            const nameField = document.getElementById('style-name');
            const descField = document.getElementById('style-description');
            const hintsField = document.getElementById('style-hints');
            if (!modal) return;

            const importField = document.getElementById('style-import-path');

            if (style) {
                title.textContent = 'Edit Style';
                idField.value = style.id;
                nameField.value = style.name || '';
                descField.value = style.description || '';
                hintsField.value = style.generation_hints || '';
                if (importField) importField.value = '';
            } else {
                title.textContent = 'Create New Style';
                idField.value = '';
                nameField.value = '';
                descField.value = '';
                hintsField.value = '';
                if (importField) importField.value = '';
            }

            modal.classList.remove('hidden');
            nameField.focus();
        },

        _closeModal() {
            document.getElementById('style-modal')?.classList.add('hidden');
        },

        async _handleSave() {
            const idField = document.getElementById('style-form-id');
            const name = document.getElementById('style-name').value.trim();
            const description = document.getElementById('style-description').value.trim();
            const generation_hints = document.getElementById('style-hints').value.trim();
            const importPath = document.getElementById('style-import-path').value.trim();

            if (!name) {
                window.showToast?.('Name is required', 'warning');
                return;
            }

            const data = { name, description, generation_hints };

            try {
                let styleId = idField.value;

                if (styleId) {
                    window.showLoading?.('Saving...');
                    await API.styles.update(styleId, data);
                    window.showToast?.('Style updated', 'success');
                } else {
                    window.showLoading?.('Creating style...');
                    const created = await API.styles.create(data);
                    styleId = created?.id;
                    window.showToast?.('Style created', 'success');
                }

                // Import references: browsed files take priority over path
                if (this._browsedFiles && this._browsedFiles.length > 0 && styleId) {
                    window.showLoading?.('Uploading references...');
                    try {
                        // Filter to image files only
                        const imageFiles = Array.from(this._browsedFiles).filter(f =>
                            /\.(png|jpe?g|gif|bmp|webp|tiff?)$/i.test(f.name)
                        );
                        if (imageFiles.length > 0) {
                            await API.styles.uploadReferences(styleId, imageFiles);
                            window.showLoading?.('Analyzing style...');
                            await API.styles.analyze(styleId);
                            window.showToast?.(`${imageFiles.length} images uploaded and analyzed`, 'success');
                        } else {
                            window.showToast?.('No image files found in selected folder', 'warning');
                        }
                    } catch (err) {
                        window.showToast?.('Style created but upload failed: ' + err.message, 'warning');
                    }
                    this._browsedFiles = null;
                } else if (importPath && !importPath.startsWith('[Browse]') && styleId) {
                    window.showLoading?.('Importing references & analyzing...');
                    try {
                        await API.styles.importPath(styleId, importPath, true);
                        window.showToast?.('References imported and analyzed', 'success');
                    } catch (err) {
                        window.showToast?.('Style created but import failed: ' + err.message, 'warning');
                    }
                }

                window.hideLoading?.();
                this._closeModal();
                await this._loadStyles();

                // Open the detail view if we just created
                if (styleId && !idField.value) {
                    this._showDetail(styleId);
                }
            } catch (err) {
                window.hideLoading?.();
            }
        },

        // --------------------------------------------------------
        //  Helpers
        // --------------------------------------------------------

        // ── Browse Modal ─────────────────────────────────────────

        _openBrowseModal(mode, targetInputId) {
            // Remove any existing browse modal
            document.getElementById('browse-modal')?.remove();

            const modal = document.createElement('div');
            modal.id = 'browse-modal';
            modal.className = 'fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
                    <div class="flex items-center justify-between px-5 py-3 border-b border-brand-border">
                        <h3 class="text-base font-semibold">${mode === 's3' ? 'Browse S3' : 'Browse Local'}</h3>
                        <button class="browse-close p-1.5 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="px-5 py-3 border-b border-brand-border">
                        <div class="flex gap-2 items-center text-sm">
                            <button id="browse-back-btn" class="p-1.5 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors disabled:opacity-30 disabled:cursor-not-allowed" title="Go to parent" disabled>
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                                </svg>
                            </button>
                            <span class="text-brand-text-muted font-mono text-xs flex-1 truncate" id="browse-location">Loading...</span>
                        </div>
                    </div>
                    <div class="flex-1 overflow-auto p-3" id="browse-list">
                        <div class="flex justify-center py-8"><div class="loading-spinner w-6 h-6 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div></div>
                    </div>
                    <div class="px-5 py-2 border-t border-brand-border">
                        <p class="text-[10px] text-brand-text-muted/50">Click to choose a folder or file. Double-click a folder to open it. Double-click a file to choose it directly.</p>
                    </div>
                    <div class="px-5 py-3 border-t border-brand-border flex items-center justify-between">
                        <span id="browse-info" class="text-xs text-brand-text-muted"></span>
                        <div class="flex gap-2">
                            <button class="browse-cancel btn btn-secondary btn-sm">Cancel</button>
                            <button class="browse-select btn btn-primary btn-sm" id="browse-select-btn">Select This</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Close handlers
            modal.querySelector('.browse-close').addEventListener('click', () => modal.remove());
            modal.querySelector('.browse-cancel').addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

            // Select handler — puts the current location into the target input
            let currentPath = '';
            modal.querySelector('#browse-select-btn').addEventListener('click', () => {
                const input = document.getElementById(targetInputId);
                if (input && currentPath) input.value = currentPath;
                modal.remove();
            });

            // Shared navigate function — declared first so click handlers can reference it
            let navigate;
            let parentPath = null;

            // Back button
            const backBtn = modal.querySelector('#browse-back-btn');
            backBtn.addEventListener('click', () => {
                if (parentPath === '__BUCKET_LIST__') {
                    // S3: go back to bucket list
                    if (typeof navigate._resetBucket === 'function') navigate._resetBucket();
                    navigate('');
                } else if (parentPath !== null) {
                    navigate(parentPath);
                }
            });

            const renderList = (items, location, info, parent) => {
                currentPath = location;
                parentPath = parent;
                modal.querySelector('#browse-location').textContent = location;
                modal.querySelector('#browse-info').textContent = info;
                backBtn.disabled = (parent === null || parent === undefined);

                const list = modal.querySelector('#browse-list');
                if (items.length === 0) {
                    list.innerHTML = '<p class="text-center text-brand-text-muted text-sm py-8">Empty — no subdirectories or images here</p>';
                    return;
                }
                list.innerHTML = items.map(item => `
                    <div class="browse-item w-full text-left px-3 py-2 rounded-lg hover:bg-white/5 flex items-center gap-3 text-sm transition-colors cursor-pointer select-none"
                            data-path="${this._esc(item.path || item.uri || item.prefix || '')}"
                            data-type="${item.type}">
                        ${item.type === 'directory'
                            ? '<svg class="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>'
                            : '<svg class="w-5 h-5 text-brand-accent flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>'
                        }
                        <span class="flex-1 truncate">${this._esc(item.name)}</span>
                        ${item.size ? `<span class="text-xs text-brand-text-muted">${(item.size / 1024).toFixed(0)}K</span>` : ''}
                        ${item.type === 'directory' ? '<svg class="w-4 h-4 text-brand-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>' : ''}
                    </div>
                `).join('');

                // ".." = single-click navigates (like back button)
                // Directory = single-click selects, double-click navigates in
                // File = single-click selects
                list.querySelectorAll('.browse-item').forEach(el => {
                    const isParent = el.querySelector('.truncate')?.textContent === '..';

                    if (isParent) {
                        el.addEventListener('click', () => {
                            navigate(el.dataset.path);
                        });
                    } else {
                        el.addEventListener('click', () => {
                            list.querySelectorAll('.browse-item').forEach(x => x.classList.remove('bg-brand-accent/10', 'border', 'border-brand-accent/30'));
                            el.classList.add('bg-brand-accent/10', 'border', 'border-brand-accent/30');
                            currentPath = el.dataset.path || location;
                        });

                        if (el.dataset.type === 'directory') {
                            el.addEventListener('dblclick', () => {
                                navigate(el.dataset.path);
                            });
                        } else {
                            // Double-click a file = select it and close
                            el.addEventListener('dblclick', () => {
                                const input = document.getElementById(targetInputId);
                                if (input) input.value = el.dataset.path;
                                modal.remove();
                            });
                        }
                    }
                });
            };

            if (mode === 'local') {
                navigate = async (path) => {
                    const list = modal.querySelector('#browse-list');
                    list.innerHTML = '<div class="flex justify-center py-8"><div class="loading-spinner w-6 h-6 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div></div>';
                    try {
                        const data = await API.browse.local(path);
                        const items = [];
                        if (data.parent) {
                            items.push({ name: '..', type: 'directory', path: data.parent });
                        }
                        items.push(...data.items);
                        renderList(items, data.current, `${data.image_count} image(s)`, data.parent);
                    } catch (err) {
                        list.innerHTML = `<p class="text-center text-red-400 text-sm py-8">${err.message}</p>`;
                    }
                };
                navigate('~');
            } else {
                // S3 mode
                let currentBucket = '';

                navigate = async (pathOrPrefix) => {
                    const list = modal.querySelector('#browse-list');
                    list.innerHTML = '<div class="flex justify-center py-8"><div class="loading-spinner w-6 h-6 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div></div>';
                    try {
                        if (!currentBucket) {
                            const data = await API.browse.s3Buckets();
                            const items = data.buckets.map(b => ({
                                name: b.name, type: 'directory', path: b.name,
                            }));
                            renderList(items, 's3://', `${items.length} bucket(s)`, null);
                            // Override: clicking a bucket sets it and enters it
                            list.querySelectorAll('.browse-item').forEach(btn => {
                                btn.replaceWith(btn.cloneNode(true));
                            });
                            list.querySelectorAll('.browse-item').forEach(btn => {
                                btn.addEventListener('click', () => {
                                    currentBucket = btn.dataset.path;
                                    navigate('');
                                });
                            });
                        } else {
                            const data = await API.browse.s3(currentBucket, pathOrPrefix);
                            const items = [];
                            if (data.parent !== null && data.parent !== undefined) {
                                const parentPath = data.parent === ''
                                    ? '__BUCKET_LIST__'
                                    : data.parent;
                                items.push({ name: '..', type: 'directory', path: parentPath });
                            }
                            items.push(...data.items.map(i => ({
                                ...i,
                                path: i.type === 'directory' ? (i.prefix || i.uri) : (i.uri || i.key),
                            })));
                            const s3Parent = data.parent === '' ? '__BUCKET_LIST__' : (data.parent || null);
                            renderList(items, data.uri, `${data.image_count} image(s)`, s3Parent);
                            // Handle ".." that points to bucket list
                            list.querySelectorAll('.browse-item').forEach(el => {
                                if (el.dataset.path === '__BUCKET_LIST__') {
                                    // Replace all listeners — single click goes to bucket list
                                    const clone = el.cloneNode(true);
                                    el.replaceWith(clone);
                                    clone.addEventListener('click', () => {
                                        currentBucket = '';
                                        navigate('');
                                    });
                                }
                            });
                        }
                    } catch (err) {
                        list.innerHTML = `<p class="text-center text-red-400 text-sm py-8">${err.message}</p>`;
                    }
                };
                navigate._resetBucket = () => { currentBucket = ''; };
                navigate('');
            }
        },

        _esc(str) {
            const div = document.createElement('div');
            div.textContent = str || '';
            return div.innerHTML;
        },
    };
})();
