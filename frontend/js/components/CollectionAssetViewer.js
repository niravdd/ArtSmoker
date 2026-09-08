/**
 * CollectionAssetViewer — the collection-level counterpart to the batch view +
 * AssetViewer (SPEC §18.8). A board of the collection's Batches (one per roster
 * subject); each Batch card drills into that Batch's options/variations/versions
 * via the EXISTING per-asset AssetViewer (reuse, don't rebuild). Collection-level
 * actions: delete; "3D the whole set" + "Export set" are fast-follow placeholders
 * (Phase N).
 */
(function () {
    const t = (k, p) => (window.t ? window.t('artsmoker.ui.' + k, p) : k);

    const CollectionAssetViewer = {
        _data: null,

        async open(collectionId) {
            this._mount(t('collection.viewer_title'));
            try {
                const data = await API.collections.get(collectionId);
                this._data = data;
                this._render(data);
            } catch (e) {
                this._renderError(e.message || t('collection.error'));
            }
        },

        close() { document.getElementById('collection-viewer-overlay')?.remove(); this._data = null; },

        _mount(title) {
            document.getElementById('collection-viewer-overlay')?.remove();
            const overlay = document.createElement('div');
            overlay.id = 'collection-viewer-overlay';
            overlay.className = 'fixed inset-0 z-[55] flex items-center justify-center bg-black/70 p-4';
            // nosemgrep
            overlay.innerHTML = html`
                <div class="card w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center justify-between p-4 border-b border-brand-border">
                        <h2 id="cv-title" class="text-lg font-semibold truncate">${title}</h2>
                        <div class="flex items-center gap-2">
                            <button id="cv-3d" class="btn btn-xs bg-brand-bg border border-brand-border opacity-50 cursor-not-allowed" disabled title="Fast-follow">${t('collection.viewer_3d_set')}</button>
                            <button id="cv-export" class="btn btn-xs bg-brand-bg border border-brand-border opacity-50 cursor-not-allowed" disabled title="Fast-follow">${t('collection.viewer_export_set')}</button>
                            <button id="cv-delete" class="btn btn-xs bg-red-700/70 hover:bg-red-600 text-white">${t('collection.delete')}</button>
                            <button id="cv-close" class="text-brand-text-muted hover:text-brand-text text-2xl leading-none ml-2">&times;</button>
                        </div>
                    </div>
                    <div id="cv-body" class="flex-1 overflow-y-auto p-4"></div>
                </div>`;
            document.body.appendChild(overlay);
            document.getElementById('cv-close').addEventListener('click', () => this.close());
            overlay.addEventListener('click', (e) => { if (e.target === overlay) this.close(); });
        },

        _renderError(msg) {
            const b = document.getElementById('cv-body');
            if (b) b.innerHTML = html`<div class="text-center py-10 text-red-400 text-sm">${msg}</div>`; // nosemgrep
        },

        _statusBadge(status) {
            const map = {
                complete: ['viewer_status_complete', 'bg-emerald-600/70'],
                partial: ['viewer_status_partial', 'bg-amber-600/70'],
                generating: ['viewer_status_generating', 'bg-cyan-600/70'],
            };
            const [key, cls] = map[status] || ['viewer_status_generating', 'bg-slate-600/70'];
            return html`<span class="text-[10px] px-1.5 py-0.5 rounded ${cls} text-white">${t('collection.' + key)}</span>`;
        },

        _render(data) {
            const rec = data.record || {};
            const summary = data.summary || {};
            const titleEl = document.getElementById('cv-title');
            if (titleEl) titleEl.textContent = rec.name || t('collection.viewer_title');
            const batches = summary.batches || [];
            const body = document.getElementById('cv-body');
            // nosemgrep
            body.innerHTML = html`
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                    ${batches.map((b) => html`
                        <div class="cv-batch card cursor-pointer overflow-hidden group" data-batch="${b.batch_id}">
                            <div class="aspect-square bg-brand-bg flex items-center justify-center overflow-hidden">
                                ${b.thumb_path
                                    ? html`<img src="${b.thumb_path}?t=${summary.updated_at || ''}" class="w-full h-full object-cover" alt="${b.name}" />`
                                    : html`<span class="text-brand-text-muted text-xs">${this._statusBadge(b.status)}</span>`}
                            </div>
                            <div class="p-2">
                                <p class="text-xs font-medium truncate">${b.name || b.slug}</p>
                                <div class="flex items-center gap-1 mt-1">
                                    ${this._statusBadge(b.status)}
                                    ${b.has_3d ? html`<span class="text-[10px] px-1.5 py-0.5 rounded bg-violet-600/70 text-white">3D</span>` : ''}
                                    <span class="text-[10px] text-brand-text-muted ml-auto">${b.job_count} img</span>
                                </div>
                            </div>
                        </div>`)}
                </div>`;
            // Batch card → drill into the existing AssetViewer for that Batch.
            body.querySelectorAll('.cv-batch').forEach((card) => {
                card.addEventListener('click', () => this._openBatch(card.dataset.batch));
            });
            document.getElementById('cv-delete').addEventListener('click', () => this._delete(rec.collection_id));
        },

        _openBatch(batchId) {
            const entry = (this._data.batches || []).find(x => (x.roster_entry || {}).batch_id === batchId);
            const batch = entry && entry.batch;
            if (!batch || !batch.options) return;
            // Flatten this Batch's options × variations into a gallery-item list so
            // the existing AssetViewer's prev/next walks the whole Batch.
            const list = [];
            batch.options.forEach((o) => (o.variants || []).forEach((v) => list.push({ id: v.id, prompt: o.enhanced_prompt })));
            if (!list.length) return;
            window.AssetViewer?.open(list[0], list, 0);
        },

        async _delete(collectionId) {
            if (!collectionId || !confirm(t('collection.delete_confirm'))) return;
            try {
                await API.collections.del(collectionId);
                this.close();
                window.Gallery?.refresh?.();
            } catch (e) { alert(e.message || t('collection.error')); }
        },
    };

    window.CollectionAssetViewer = CollectionAssetViewer;
})();
