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
            this._sel = new Map();   // asset_id -> version, selection for 3D + downloads
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
                            <span id="cv-selinfo" class="text-[11px] text-cyan-300"></span>
                            <button id="cv-3d" class="btn btn-xs bg-violet-700/70 hover:bg-violet-600 text-white">${t('collection.convert_3d')}</button>
                            <button id="cv-dl-images" class="btn btn-xs bg-brand-bg border border-brand-border">${t('collection.download_images')}</button>
                            <button id="cv-dl-3d" class="btn btn-xs bg-brand-bg border border-brand-border">${t('collection.download_3d')}</button>
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

        _fact(label, value) {
            if (value === undefined || value === null || value === '') return '';
            return html`<div><span class="text-brand-text-muted/60">${label}:</span> <span class="text-brand-text">${value}</span></div>`;
        },

        /** Collection-level metadata panel (SPEC §18) — the collection counterpart of
         *  the AssetViewer Metadata tab. All fields come from the master record. */
        _metaPanelHTML(rec, summary) {
            const k = rec.knobs || {};
            const N = (rec.roster || []).length || summary.batch_count || 0;
            const O = k.O, V = k.V;
            const total = (N && O && V) ? N * O * V : null;
            const models = (k.models || summary.models || []).join(', ');
            const cohesion = k.cohesion_mode ? t('collection.cohesion_' + k.cohesion_mode) : '';
            const created = rec.created_at
                ? (window.formatTimestamp ? window.formatTimestamp(rec.created_at) : rec.created_at) : '';
            const costObj = (rec.cost_actual && rec.cost_actual.total != null) ? rec.cost_actual
                : (rec.cost_estimate || null);
            const cost = costObj && costObj.total != null ? '$' + Number(costObj.total).toFixed(3) : null;
            const ad = rec.overarching_art_direction || '';
            const F = (l, v) => this._fact(l, v);
            // nosemgrep
            return html`
                <details class="mb-3 rounded-lg border border-brand-border bg-brand-bg/40" open>
                    <summary class="cursor-pointer select-none px-3 py-2 text-xs font-semibold text-brand-text-muted">${t('collection.details')}</summary>
                    <div class="px-3 pb-3 space-y-2">
                        <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1 text-[11px]">
                            ${F(t('collection.roster_label'), N)}
                            ${F(t('collection.options_label'), O)}
                            ${F(t('collection.variations_label'), V)}
                            ${total ? html`<div>${t('collection.images_count', { count: total })}</div>` : ''}
                            ${F(t('collection.model_label'), models)}
                            ${F(t('collection.cohesion_label'), cohesion)}
                            ${F(t('collection.meta_status'), rec.status)}
                            ${F(t('collection.meta_created'), created)}
                            ${F(t('collection.cost_total'), cost)}
                        </div>
                        ${ad ? html`<div>
                            <div class="text-[10px] uppercase tracking-wide text-brand-text-muted/60 mb-0.5">${t('collection.art_direction_label')}</div>
                            <div class="text-[11px] text-brand-text/80 whitespace-pre-wrap bg-brand-bg/60 rounded p-2 border border-brand-border/50 max-h-40 overflow-y-auto">${ad}</div>
                        </div>` : ''}
                    </div>
                </details>`;
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
                ${this._metaPanelHTML(rec, summary)}
                <div class="gallery-grid">
                    ${batches.map((b) => {
                        const failed = (b.status === 'failed' || b.status === 'blocked');
                        return html`
                        <div class="cv-batch gallery-card card ${failed ? '' : 'cursor-pointer'} overflow-hidden group" data-batch="${b.batch_id}" data-slug="${b.slug}" data-status="${b.status}">
                            <div class="bg-brand-bg overflow-hidden relative">
                                <input type="checkbox" class="cv-batch-sel absolute top-1.5 left-1.5 z-10 w-4 h-4 accent-cyan-500 cursor-pointer" data-batch="${b.batch_id}" title="${t('collection.select_batch')}" ${this._batchAllSelected(b.batch_id) ? 'checked' : ''} />
                                ${b.thumb_path
                                    ? html`<img src="${b.thumb_path}?t=${summary.updated_at || ''}" class="w-full h-auto block" alt="${b.name}" loading="lazy" />`
                                    : html`<div class="w-full flex items-center justify-center" style="min-height:140px">${this._statusBadge(b.status)}</div>`}
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
            // Batch card → drill into the batch detail. (Checkbox toggles selection.)
            body.querySelectorAll('.cv-batch').forEach((card) => {
                card.addEventListener('click', (e) => {
                    if (e.target.closest('.cv-batch-sel')) return;   // checkbox handles itself
                    this._openBatch(card.dataset.batch);
                });
            });
            body.querySelectorAll('.cv-batch-sel').forEach((cb) => {
                cb.addEventListener('click', (e) => e.stopPropagation());
                cb.addEventListener('change', (e) => { e.stopPropagation(); this._toggleBatchSel(cb.dataset.batch, cb.checked); });
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
            document.getElementById('cv-3d').addEventListener('click', () => this._open3dPane(rec.collection_id));
            document.getElementById('cv-dl-images').addEventListener('click', () => this._downloadImages(rec.collection_id));
            document.getElementById('cv-dl-3d').addEventListener('click', () => this._download3d(rec.collection_id));
            this._updateSelInfo();
        },

        // ── Selection (batches / jobs) — drives 3D + downloads ─────────────
        _selTargets() {
            return this._sel ? Array.from(this._sel.entries()).map(([asset_id, version]) => ({ asset_id, version })) : [];
        },
        _selCount() { return this._sel ? this._sel.size : 0; },
        _updateSelInfo() {
            const el = document.getElementById('cv-selinfo');
            if (el) el.textContent = this._selCount() ? t('collection.selected_count', { count: this._selCount() }) : '';
        },
        /** All {asset_id, version} jobs of a batch (from the full reconstruction). */
        _batchJobTargets(batchId) {
            const entry = (this._data.batches || []).find(x => (x.roster_entry || {}).batch_id === batchId);
            const opts = (entry && entry.batch && entry.batch.options) || [];
            const out = [];
            opts.forEach(o => (o.variants || []).forEach(v => out.push({ asset_id: v.id, version: v.current_version || 1 })));
            return out;
        },
        _batchAllSelected(batchId) {
            const jobs = this._batchJobTargets(batchId);
            return jobs.length > 0 && jobs.every(j => this._sel && this._sel.has(j.asset_id));
        },
        _toggleBatchSel(batchId, on) {
            const jobs = this._batchJobTargets(batchId);
            jobs.forEach(j => on ? this._sel.set(j.asset_id, j.version) : this._sel.delete(j.asset_id));
            this._updateSelInfo();
        },
        _toggleJobSel(assetId, version, on) {
            if (on) this._sel.set(assetId, version || 1); else this._sel.delete(assetId);
            this._updateSelInfo();
        },

        // ── Convert to 3D: one settings pane, applied uniformly ────────────
        async _open3dPane(collectionId) {
            const count = this._selCount();
            let instances = [], defaults = {};
            try { const r = await API.threeD.instances(); instances = (r.instances || []).filter(i => i.available); } catch (_) {}
            try { defaults = (await API.threeD.defaults()) || {}; } catch (_) {}
            const pane = document.createElement('div');
            pane.id = 'cv-3d-pane';
            pane.className = 'fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4';
            // nosemgrep
            pane.innerHTML = html`
                <div class="card w-full max-w-md p-4 space-y-3">
                    <div class="flex items-center justify-between">
                        <h3 class="text-sm font-semibold">${t('collection.convert_3d')}</h3>
                        <button id="cv3p-close" class="text-brand-text-muted hover:text-brand-text text-xl leading-none">&times;</button>
                    </div>
                    <p class="text-[11px] text-brand-text-muted">${count > 0 ? t('collection.pane_applies_sel', { count }) : t('collection.pane_applies_all')}</p>
                    <div>
                        <label class="block text-[11px] mb-1">${t('collection.pane_pipeline')}</label>
                        <select id="cv3p-model" class="input text-sm w-full">
                            ${instances.length
                                ? instances.map(i => html`<option value="${i.key}">${i.label || i.key}</option>`)
                                : html`<option value="">${t('collection.pane_default_pipeline')}</option>`}
                        </select>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div><label class="block text-[11px] mb-1">${t('collection.pane_quality')}</label>
                            <select id="cv3p-quality" class="input text-sm w-full">
                                <option value="standard">standard</option><option value="premium">premium</option>
                            </select></div>
                        <div><label class="block text-[11px] mb-1">${t('collection.pane_seed')}</label>
                            <input id="cv3p-seed" type="number" class="input text-sm w-full" placeholder="${t('collection.count_auto')}" /></div>
                    </div>
                    <div class="flex justify-end pt-1">
                        <button id="cv3p-go" class="btn btn-primary btn-sm">${t('collection.pane_convert')}</button>
                    </div>
                </div>`;
            document.body.appendChild(pane);
            const close = () => pane.remove();
            document.getElementById('cv3p-close').addEventListener('click', close);
            pane.addEventListener('click', (e) => { if (e.target === pane) close(); });
            if (defaults.quality) document.getElementById('cv3p-quality').value = defaults.quality;
            document.getElementById('cv3p-go').addEventListener('click', async () => {
                const settings = { quality: document.getElementById('cv3p-quality').value || 'standard' };
                const mk = document.getElementById('cv3p-model').value;
                if (mk) settings.model_key = mk;
                const seedV = parseInt(document.getElementById('cv3p-seed').value, 10);
                if (Number.isFinite(seedV)) settings.seed = seedV;
                const go = document.getElementById('cv3p-go');
                go.disabled = true; go.textContent = '…';
                try {
                    const r = await API.collections.generate3d(collectionId, { targets: this._selTargets(), settings });
                    window.showToast?.(t('collection.threed_submitted', { count: (r.submitted || []).length }), 'success');
                    if ((r.failures || []).length) window.showToast?.(r.failures[0].error, 'warning');
                    close();
                    setTimeout(() => this.open(collectionId), 800);   // reflect submitted status
                } catch (e) {
                    window.showToast?.(e.message || t('collection.error'), 'error');
                    go.disabled = false; go.textContent = t('collection.pane_convert');
                }
            });
        },

        // ── Downloads (whole collection or selected) ───────────────────────
        async _zipDownload(path, body, fallbackName) {
            try {
                // nosemgrep -- serialized HTTP body; ZIP response streamed to a download
                const resp = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
                if (!resp.ok) { let d = ''; try { d = (await resp.json()).detail; } catch (_) {} window.showToast?.(d || t('collection.error'), 'error'); return; }
                const blob = await resp.blob();
                const cd = resp.headers.get('Content-Disposition') || '';
                const m = /filename="?([^"]+)"?/.exec(cd);
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = (m && m[1]) || fallbackName;
                document.body.appendChild(a); a.click(); a.remove();
                setTimeout(() => URL.revokeObjectURL(a.href), 5000);
            } catch (e) { window.showToast?.(e.message || t('collection.error'), 'error'); }
        },
        _downloadImages(collectionId) {
            this._zipDownload(`/api/collections/${collectionId}/download-images`, { targets: this._selTargets() }, 'collection_images.zip');
        },
        _download3d(collectionId) {
            const fmt = (window.prompt(t('collection.download_3d_fmt'), 'glb') || '').trim().toLowerCase();
            if (!fmt) return;
            if (!['glb', 'fbx', 'usd'].includes(fmt)) { window.showToast?.('fmt must be glb, fbx, or usd', 'warning'); return; }
            this._zipDownload(`/api/collections/${collectionId}/download-3d`, { targets: this._selTargets(), fmt }, `collection_3d_${fmt}.zip`);
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
            if (!batch || !(batch.options || []).length) return;
            // Drill into a batch-DETAIL view (SPEC §18.8) that shows the whole
            // options × variations grid — like the Image Studio result view — instead
            // of opening a single image with no way to reach the siblings.
            this._batchDetail = { batch, name: (entry.roster_entry || {}).name || batch.batch_id || '', sel: { o: 0, v: 0 } };
            this._renderBatchDetail();
        },

        /** Batch detail: a large preview + every option with its variation thumbnails
         *  (click a thumb to switch the preview; click the preview for the full viewer). */
        _renderBatchDetail() {
            const bd = this._batchDetail;
            const body = document.getElementById('cv-body');
            if (!bd || !body) return;
            const opts = bd.batch.options || [];
            const cb = this._data.summary?.updated_at || '';
            // Flat list (option-major) for the full AssetViewer's prev/next.
            const flat = [];
            opts.forEach((o) => (o.variants || []).forEach((v) => flat.push({ id: v.id, prompt: o.enhanced_prompt })));
            const selVariant = (opts[bd.sel.o]?.variants || [])[bd.sel.v] || flat[0];
            const selId = selVariant && selVariant.id;
            // nosemgrep
            body.innerHTML = html`
                <div class="mb-3 flex items-center gap-2">
                    <button id="cv-bd-back" class="btn btn-xs bg-brand-bg border border-brand-border">← ${t('collection.back_to_set')}</button>
                    <h3 class="text-sm font-semibold truncate">${bd.name}</h3>
                </div>
                <div class="bg-brand-bg rounded-lg flex items-center justify-center overflow-hidden mb-3 p-2" style="max-height:45vh">
                    ${selId
                        ? html`<img id="cv-bd-preview" src="/api/gallery/${selId}/png?t=${cb}" class="max-w-full object-contain cursor-pointer rounded" style="max-height:42vh" title="${t('collection.open_full')}" alt="${bd.name}" />`
                        : html`<span class="text-brand-text-muted text-xs py-10">${t('collection.empty')}</span>`}
                </div>
                <div class="space-y-2">
                    ${opts.map((o, oi) => {
                        // Each option = a bounded row: header (option # + the model that
                        // produced it) then all its variations laid out in a row.
                        const model = (o.variants && o.variants[0] && o.variants[0].model_label) || '';
                        return html`
                        <div class="rounded-lg border border-brand-border bg-brand-bg/40 p-2">
                            <div class="flex items-center gap-2 mb-1.5">
                                <span class="text-[11px] font-semibold">${t('collection.option_label')} ${oi + 1}</span>
                                ${model ? html`<span class="text-[10px] px-1.5 py-0.5 rounded bg-brand-surface border border-brand-border text-brand-text-muted">${model}</span>` : ''}
                            </div>
                            <div class="flex flex-wrap gap-2">
                                ${(o.variants || []).map((v, vi) => html`
                                    <button class="cv-bd-cell relative rounded-md overflow-hidden border ${oi === bd.sel.o && vi === bd.sel.v ? 'border-cyan-400 ring-1 ring-cyan-400' : 'border-brand-border hover:border-brand-text-muted'}" data-o="${oi}" data-v="${vi}" style="width:84px;height:84px" title="${t('collection.option_label')} ${oi + 1} · ${t('collection.variation_label')} ${vi + 1}">
                                        <input type="checkbox" class="cv-job-sel absolute top-0.5 left-0.5 z-10 w-3.5 h-3.5 accent-cyan-500 cursor-pointer" data-id="${v.id}" data-version="${v.current_version || 1}" title="${t('collection.select_job')}" ${this._sel && this._sel.has(v.id) ? 'checked' : ''} />
                                        <img src="/api/gallery/${v.id}/png?t=${cb}" class="w-full h-full object-cover" alt="" loading="lazy" />
                                        ${v.has_3d ? html`<span class="absolute top-0.5 right-0.5 text-[8px] px-1 rounded bg-violet-600/80 text-white">3D</span>` : ''}
                                        <span class="absolute bottom-0 right-0 text-[9px] px-1 bg-black/70 text-white rounded-tl">v${vi + 1}</span>
                                    </button>`)}
                            </div>
                        </div>`;
                    })}
                </div>`;
            document.getElementById('cv-bd-back').addEventListener('click', () => this._render(this._data));
            document.getElementById('cv-bd-preview')?.addEventListener('click', () => {
                const idx = Math.max(0, flat.findIndex(x => x.id === selId));
                window.AssetViewer?.open(flat[idx], flat, idx);
            });
            body.querySelectorAll('.cv-bd-cell').forEach((btn) => {
                btn.addEventListener('click', (e) => {
                    if (e.target.closest('.cv-job-sel')) return;   // checkbox handles itself
                    bd.sel = { o: +btn.dataset.o, v: +btn.dataset.v };
                    this._renderBatchDetail();
                });
            });
            body.querySelectorAll('.cv-job-sel').forEach((cb) => {
                cb.addEventListener('click', (e) => e.stopPropagation());
                cb.addEventListener('change', (e) => {
                    e.stopPropagation();
                    this._toggleJobSel(cb.dataset.id, parseInt(cb.dataset.version, 10) || 1, cb.checked);
                });
            });
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
