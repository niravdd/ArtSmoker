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
                            <button id="cv-3d" class="btn btn-xs bg-violet-700/70 hover:bg-violet-600 text-white">${t('collection.viewer_3d_set')}</button>
                            <button id="cv-export" class="btn btn-xs bg-brand-bg border border-brand-border">${t('collection.viewer_export_set')}</button>
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
                failed: ['status_failed', 'bg-red-600/70'],
                blocked: ['status_blocked', 'bg-amber-600/80'],
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
                    ${batches.map((b) => {
                        const failed = (b.status === 'failed' || b.status === 'blocked');
                        return html`
                        <div class="cv-batch card ${failed ? '' : 'cursor-pointer'} overflow-hidden group" data-batch="${b.batch_id}" data-slug="${b.slug}" data-status="${b.status}">
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
                                    ${failed
                                        ? html`<button class="cv-retry text-[10px] px-1.5 py-0.5 rounded bg-cyan-600/70 hover:bg-cyan-500 text-white ml-auto" data-slug="${b.slug}" data-blocked="${b.status === 'blocked' ? '1' : ''}" title="${b.error || ''}">${t('collection.retry')}</button>`
                                        : html`<span class="text-[10px] text-brand-text-muted ml-auto">${t('collection.images_count', { count: b.job_count })}</span>`}
                                </div>
                                ${(b.versions && b.versions.length > 1) ? html`
                                    <select class="cv-version input text-[10px] mt-1 py-0.5" data-batch="${b.batch_id}" title="${t('collection.version_label')}">
                                        ${b.versions.map((v) => html`<option value="${v}" ${v === b.selected_version ? 'selected' : ''}>${t('collection.version_label')} ${v}</option>`)}
                                    </select>` : ''}
                            </div>
                        </div>`;
                    })}
                </div>`;
            // Batch card → drill into the existing AssetViewer for that Batch.
            body.querySelectorAll('.cv-batch').forEach((card) => {
                card.addEventListener('click', () => this._openBatch(card.dataset.batch));
            });
            // Per-Batch version picker (Phase M) — pins which version represents the
            // Batch in the set. Stop propagation so it doesn't open the drill-down.
            body.querySelectorAll('.cv-version').forEach((sel) => {
                sel.addEventListener('click', (e) => e.stopPropagation());
                sel.addEventListener('change', async (e) => {
                    e.stopPropagation();
                    try {
                        await API.collections.selectVersion(rec.collection_id,
                            { batch_id: sel.dataset.batch, version: parseInt(sel.value, 10) });
                        this.open(rec.collection_id);   // reflect the new cover
                    } catch (err) { window.showToast?.(err.message || t('collection.error'), 'error'); }
                });
            });
            // Per-Batch retry (failed/blocked). stopPropagation so it doesn't drill down.
            body.querySelectorAll('.cv-retry').forEach((btn) => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._retryBatch(rec.collection_id, btn.dataset.slug, btn.dataset.blocked === '1', btn);
                });
            });
            document.getElementById('cv-delete').addEventListener('click', () => this._delete(rec.collection_id));
            document.getElementById('cv-3d').addEventListener('click', () => this._generate3d(rec.collection_id));
            document.getElementById('cv-export').addEventListener('click', () => this._export(rec.collection_id));
        },

        _export(collectionId) {
            // Simple engine/format prompt → stream the bundle via a hidden download.
            const fmt = (window.prompt(t('collection.export_prompt'), 'fbx') || '').trim().toLowerCase();
            if (!fmt) return;
            if (!['fbx', 'usd', 'glb'].includes(fmt)) { window.showToast?.('fmt must be fbx, usd, or glb', 'warning'); return; }
            window.location.href = API.collections.exportUrl(collectionId, 'generic', fmt);
        },

        async _generate3d(collectionId) {
            const btn = document.getElementById('cv-3d');
            if (!collectionId || !btn) return;
            btn.disabled = true; const orig = btn.textContent; btn.textContent = '…';
            try {
                const r = await API.collections.generate3d(collectionId);
                const n = (r.submitted || []).length;
                window.showToast?.(t('collection.threed_submitted', { count: n }), 'success');
                if ((r.failures || []).length) window.showToast?.(r.failures[0].error, 'warning');
                setTimeout(() => this.open(collectionId), 800);   // reopen to reflect status
            } catch (e) {
                window.showToast?.(e.message || t('collection.error'), 'error');
                btn.disabled = false; btn.textContent = orig;
            }
        },

        /** Retry a Failed/Blocked Batch. For a content-filter block, prompt the user
         *  to edit the piece's prompt first (same-prompt retry would fail again). */
        async _retryBatch(collectionId, slug, blocked, btn) {
            let editedPrompt;
            if (blocked) {
                const entry = ((this._data && this._data.record && this._data.record.roster) || []).find(e => e.slug === slug);
                editedPrompt = window.prompt(t('collection.retry_edit'), (entry && entry.model_agnostic_prompt) || '');
                if (editedPrompt === null) return;   // cancelled
            }
            if (btn) { btn.disabled = true; btn.textContent = t('collection.retrying'); }
            try {
                await API.collections.generateBatch(collectionId, { slug, prompt: editedPrompt || undefined });
            } catch (e) {
                window.showToast?.(e.message || t('collection.error'), 'error');
            }
            this.open(collectionId);   // reload the board either way (reflect new status)
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
