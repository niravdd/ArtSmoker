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
            this._collectionId = collectionId;
            this._mount(t('collection.viewer_title'));
            try {
                const data = await API.collections.get(collectionId);
                this._data = data;
                this._render(data);
            } catch (e) {
                this._renderError(e.message || t('collection.error'));
            }
        },

        close() {
            document.getElementById('collection-viewer-overlay')?.remove(); this._data = null;
            // A version pin / Batch retry / 3D run inside the viewer changes covers + badges.
            window.ImageStudio?.refreshCollections?.();
        },

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
                            <!-- Primary + default action (first, focused → Enter): reload the set into Image Studio. -->
                            <button id="cv-reload" class="btn btn-xs btn-primary">${t('collection.reload_studio')}</button>
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
            // Header actions are bound ONCE here (not in _render, which re-runs on
            // every Back-from-Batch and would stack duplicate handlers).
            document.getElementById('cv-close').addEventListener('click', () => this.close());
            // Reload the whole collection into Image Studio (review / regenerate / tweak),
            // mirroring the single-asset "reload" in AssetViewer.
            document.getElementById('cv-reload').addEventListener('click', () => {
                const id = this._collectionId;
                this.close();
                window.ImageStudio?.loadCollection?.(id);
            });
            document.getElementById('cv-delete').addEventListener('click', () => this._delete(this._collectionId));
            document.getElementById('cv-3d').addEventListener('click', () => this._open3dPane(this._collectionId));
            document.getElementById('cv-dl-images').addEventListener('click', () => this._downloadImages(this._collectionId));
            document.getElementById('cv-dl-3d').addEventListener('click', () => this._download3d(this._collectionId));
            document.getElementById('cv-reload').focus();
            overlay.addEventListener('click', (e) => { if (e.target === overlay) this.close(); });
            overlay.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !document.getElementById('cv-3d-pane')) this.close(); });
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
            this._updateSelInfo();
        },

        // ── Selection — a Set of "assetId@version" targets (job + version level;
        //    a whole batch = every version of every job) that drives 3D + downloads.
        _key(assetId, version) { return `${assetId}@${version || 1}`; },
        _selTargets() {
            return this._sel ? Array.from(this._sel).map(k => {
                const i = k.lastIndexOf('@');
                return { asset_id: k.slice(0, i), version: parseInt(k.slice(i + 1), 10) || 1 };
            }) : [];
        },
        _selCount() { return this._sel ? this._sel.size : 0; },
        _updateSelInfo() {
            const el = document.getElementById('cv-selinfo');
            if (el) el.textContent = this._selCount() ? t('collection.selected_count', { count: this._selCount() }) : '';
        },
        _jobVersions(v) { return (v && v.versions && v.versions.length) ? v.versions : [(v && v.current_version) || 1]; },
        /** All (asset_id, version) targets of a batch = EVERY version of EVERY job. */
        _batchJobTargets(batchId) {
            const entry = (this._data.batches || []).find(x => (x.roster_entry || {}).batch_id === batchId);
            const opts = (entry && entry.batch && entry.batch.options) || [];
            const out = [];
            opts.forEach(o => (o.variants || []).forEach(v => this._jobVersions(v).forEach(ver => out.push({ asset_id: v.id, version: ver }))));
            return out;
        },
        _batchAllSelected(batchId) {
            const tgs = this._batchJobTargets(batchId);
            return tgs.length > 0 && tgs.every(t => this._sel.has(this._key(t.asset_id, t.version)));
        },
        _toggleBatchSel(batchId, on) {
            this._batchJobTargets(batchId).forEach(t =>
                on ? this._sel.add(this._key(t.asset_id, t.version)) : this._sel.delete(this._key(t.asset_id, t.version)));
            this._updateSelInfo();
        },
        _jobAllSelected(v) { return this._jobVersions(v).every(ver => this._sel.has(this._key(v.id, ver))); },
        _toggleJobSel(v, on) {
            this._jobVersions(v).forEach(ver => on ? this._sel.add(this._key(v.id, ver)) : this._sel.delete(this._key(v.id, ver)));
            this._updateSelInfo();
        },
        _toggleVersionSel(assetId, version, on) {
            on ? this._sel.add(this._key(assetId, version)) : this._sel.delete(this._key(assetId, version));
            this._updateSelInfo();
        },

        /** How many 3D jobs a Convert would submit: the explicit selection, else one
         *  per generated Batch (its representative image — the backend's fallback). */
        _3dTargetCount() {
            const n = this._selCount();
            if (n) return n;
            return (this._data?.batches || []).filter(e =>
                ((e.batch && e.batch.options) || []).some(o => (o.variants || []).length)).length;
        },

        /** Bulk duration — minutes, or hours once it runs long. */
        _fmtDuration(s) {
            if (!s) return '~?';
            const m = Math.round(s / 60);
            return m >= 90 ? `~${(m / 60).toFixed(1)} h` : (m >= 1 ? `~${m} min` : `~${s}s`);
        },

        // ── Convert to 3D: one settings pane, applied uniformly ────────────
        // Parity with the per-asset 3D form (AssetViewer): same pipeline chooser,
        // license panel, quality presets → steps/guidance/faces/octree, advanced
        // fields, save-as, S3 preflight — plus a per-job × N total estimate and a
        // confirm of the total before anything is spent. Presets/estimate/license
        // come from the shared AssetViewer.threeD* helpers (single source).
        async _open3dPane(collectionId) {
            if (document.getElementById('cv-3d-pane')) return;
            const AV = window.AssetViewer;
            const count = this._3dTargetCount();
            if (!count) { window.showToast?.(t('collection.pane_nothing'), 'warning'); return; }
            let available = true, instances = [];
            try { available = !!(await API.threeD.check())?.available; } catch (_) { available = false; }
            if (available) {
                try { instances = ((await API.threeD.instances())?.instances || []).filter(i => i.available); } catch (_) {}
            }
            const pane = document.createElement('div');
            pane.id = 'cv-3d-pane';
            pane.className = 'fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4';
            const header = html`
                <div class="flex items-center justify-between">
                    <h3 class="text-sm font-semibold">${t('collection.convert_3d')}</h3>
                    <button id="cv3p-close" class="text-brand-text-muted hover:text-brand-text text-xl leading-none">&times;</button>
                </div>`;
            if (!available || !AV) {
                // nosemgrep
                pane.innerHTML = html`
                    <div class="card w-full max-w-md p-4 space-y-3">
                        ${header}
                        <p class="text-sm text-brand-text-muted text-center py-4">${t('asset_viewer.three_d_not_deployed')}</p>
                        <div class="flex justify-center"><button id="cv3p-settings" class="btn btn-sm btn-secondary">${t('asset_viewer.three_d_open_settings')}</button></div>
                    </div>`;
                document.body.appendChild(pane);
                const close = () => pane.remove();
                document.getElementById('cv3p-close').addEventListener('click', close);
                pane.addEventListener('click', (e) => { if (e.target === pane) close(); });
                document.getElementById('cv3p-settings').addEventListener('click', () => {
                    close(); this.close(); window.ModelSettings?.open?.('custom-models');
                });
                return;
            }
            const A = (k) => t('asset_viewer.' + k);
            // nosemgrep
            pane.innerHTML = html`
                <div class="card w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 space-y-3">
                    ${header}
                    <p class="text-[11px] text-brand-text-muted">${this._selCount() > 0 ? t('collection.pane_applies_sel', { count }) : t('collection.pane_applies_all_n', { count })}</p>
                    <div>
                        <label class="block text-[11px] text-brand-text-muted mb-1">${t('collection.pane_pipeline')}</label>
                        <select id="cv3p-model" class="input text-sm w-full">
                            ${instances.length
                                ? instances.map((inst, i) => html`<option value="${inst.model_key}" ${i === 0 ? 'selected' : ''}>${AV.threeDInstanceLabel(inst)}</option>`)
                                : html`<option value="">${t('collection.pane_default_pipeline')}</option>`}
                        </select>
                    </div>
                    <div id="cv3p-license" class="rounded-lg border border-brand-border bg-brand-bg/40 p-3 text-[11px] space-y-1 hidden"></div>
                    <div>
                        <label class="block text-[11px] text-brand-text-muted mb-1">${A('three_d_quality')}</label>
                        <select id="cv3p-quality" class="input text-sm w-full">
                            <option value="fast">${A('three_d_quality_fast')}</option>
                            <option value="standard">${A('three_d_quality_standard')}</option>
                            <option value="high" selected>${A('three_d_quality_high')}</option>
                        </select>
                        <p id="cv3p-est" class="text-[10px] text-brand-text-dim mt-1.5"></p>
                        <p id="cv3p-total" class="text-[11px] text-emerald-400/90 font-mono mt-0.5"></p>
                        <p class="text-[9px] text-brand-text-dim">${t('collection.pane_queue_note')}</p>
                    </div>
                    <details class="border border-brand-border rounded-lg">
                        <summary class="px-3 py-2 text-xs text-brand-text-muted cursor-pointer hover:text-brand-text">${A('three_d_advanced')}</summary>
                        <div class="px-3 pb-3 pt-2 grid grid-cols-2 gap-x-4 gap-y-3">
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${A('three_d_steps')}</label>
                                <div class="flex items-center gap-2">
                                    <input id="cv3p-steps" type="range" min="20" max="100" value="50" class="flex-1 min-w-0" />
                                    <span id="cv3p-steps-label" class="text-[10px] text-brand-text-muted w-6 text-right">50</span>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${A('three_d_guidance')}</label>
                                <div class="flex items-center gap-2">
                                    <input id="cv3p-guidance" type="range" min="1" max="20" step="0.5" value="7.5" class="flex-1 min-w-0" />
                                    <span id="cv3p-guidance-label" class="text-[10px] text-brand-text-muted w-6 text-right">7.5</span>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${A('three_d_faces')}</label>
                                <select id="cv3p-faces" class="input text-xs w-full">
                                    <option value="0">${A('three_d_faces_unlimited')}</option>
                                    <option value="50000">50,000</option>
                                    <option value="100000" selected>100,000</option>
                                    <option value="200000">200,000</option>
                                    <option value="300000">300,000</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${A('three_d_depth')}</label>
                                <select id="cv3p-depth" class="input text-xs w-full">
                                    <option value="128">${A('three_d_depth_low')}</option>
                                    <option value="256" selected>${A('three_d_depth_medium')}</option>
                                    <option value="512">${A('three_d_depth_high')}</option>
                                </select>
                            </div>
                            <div class="col-span-2">
                                <label class="text-[10px] text-brand-text-muted mb-0.5 block">${A('three_d_seed')}</label>
                                <input id="cv3p-seed" type="number" class="input text-xs w-full max-w-xs" placeholder="${A('three_d_seed_placeholder')}" />
                                <p class="text-[9px] text-brand-text-dim mt-1">${t('collection.pane_seed_hint')}</p>
                            </div>
                        </div>
                    </details>
                    <div class="rounded-lg border border-brand-border bg-brand-bg/40 p-3">
                        <label class="text-xs text-brand-text-muted mb-2 block">${t('collection.pane_saveas_title')}</label>
                        <label class="flex items-start gap-2 mb-1.5 cursor-pointer">
                            <input type="radio" name="cv3p-saveas" value="default" checked class="mt-0.5" />
                            <span class="text-[11px]"><span class="font-medium">${A('three_d_saveas_replace')}</span><br><span class="text-brand-text-dim">${A('three_d_saveas_replace_hint')}</span></span>
                        </label>
                        <label class="flex items-start gap-2 cursor-pointer">
                            <input type="radio" name="cv3p-saveas" value="variant" class="mt-0.5" />
                            <span class="text-[11px]"><span class="font-medium">${A('three_d_saveas_variant')}</span><br><span class="text-brand-text-dim">${A('three_d_saveas_variant_hint')}</span></span>
                        </label>
                    </div>
                    <p class="text-[10px] text-brand-text-dim">${t('collection.pane_source_note')}</p>
                    <div class="flex justify-end pt-1">
                        <button id="cv3p-go" class="btn btn-primary btn-sm">${t('collection.pane_convert_n', { count })}</button>
                    </div>
                </div>`;
            document.body.appendChild(pane);
            const $ = (id) => document.getElementById(id);
            const close = () => pane.remove();
            $('cv3p-close').addEventListener('click', close);
            pane.addEventListener('click', (e) => { if (e.target === pane) close(); });
            pane.addEventListener('keydown', (e) => { if (e.key === 'Escape') { e.stopPropagation(); close(); } });

            const selInst = () => {
                const key = $('cv3p-model')?.value;
                return (key && instances.find(i => i.model_key === key)) || instances[0] || null;
            };
            // Per-job estimate + the N-job total (jobs queue on the endpoint, so the
            // total time is sequential on one instance).
            const estimate = () => {
                const inst = selInst();
                const e = AV.threeDEstimate(inst, parseInt($('cv3p-steps').value, 10));
                return { inst, per: e, totalLat: e.lat * count, totalCost: e.cost != null ? e.cost * count : null };
            };
            const updateEstimate = () => {
                const { inst, per, totalLat, totalCost } = estimate();
                const faces = AV.threeDFacesText(parseInt($('cv3p-faces').value || '0', 10));
                const perCost = per.cost != null ? ` · ~$${per.cost.toFixed(2)}` : '';
                const backend = inst?.texture_backend ? ` · ${inst.texture_backend}` : '';
                $('cv3p-est').textContent = `${faces}${inst ? ` · ${AV.threeDFmtTime(per.lat)}${perCost}${backend}` : ''} ${t('collection.pane_per_job')}`;
                $('cv3p-total').textContent = t('collection.pane_total', {
                    count, time: this._fmtDuration(totalLat),
                    cost: totalCost != null ? '~$' + totalCost.toFixed(2) : t('collection.pane_cost_unknown'),
                });
            };
            const updateLicense = () => {
                const el = $('cv3p-license');
                const inst = selInst();
                if (!inst || !inst.license_name) { el.classList.add('hidden'); return; }
                // nosemgrep
                el.innerHTML = AV.threeDLicenseHTML(inst);
                el.classList.remove('hidden');
            };
            const applyPreset = () => {
                const p = AV.THREE_D_QUALITY_PRESETS[$('cv3p-quality').value];
                if (!p) return;
                $('cv3p-steps').value = p.steps; $('cv3p-steps-label').textContent = p.steps;
                $('cv3p-guidance').value = p.guidance; $('cv3p-guidance-label').textContent = p.guidance;
                $('cv3p-faces').value = String(p.faces);
                $('cv3p-depth').value = String(p.depth);
                updateEstimate();
            };
            $('cv3p-quality').addEventListener('change', applyPreset);
            $('cv3p-faces').addEventListener('change', updateEstimate);
            $('cv3p-model').addEventListener('change', () => { updateEstimate(); updateLicense(); });
            $('cv3p-steps').addEventListener('input', () => { $('cv3p-steps-label').textContent = $('cv3p-steps').value; updateEstimate(); });
            $('cv3p-guidance').addEventListener('input', () => { $('cv3p-guidance-label').textContent = $('cv3p-guidance').value; });
            updateLicense();
            applyPreset();   // sync advanced fields + estimate to the default (High)

            $('cv3p-go').addEventListener('click', async () => {
                const go = $('cv3p-go');
                if (go.disabled) return;
                // Confirm the TOTAL before spending — a whole set is N GPU jobs.
                const { per, totalLat, totalCost } = estimate();
                const ok = window.showConfirm
                    ? await window.showConfirm(
                        t('collection.pane_confirm_body', {
                            count, time: this._fmtDuration(totalLat),
                            cost: totalCost != null ? '~$' + totalCost.toFixed(2) : t('collection.pane_cost_unknown'),
                            per: AV.threeDFmtTime(per.lat),
                        }),
                        { title: t('collection.pane_confirm_title', { count }),
                          confirmLabel: t('collection.pane_convert_n', { count }),
                          cancelLabel: t('common.cancel') })
                    : window.confirm(t('collection.pane_confirm_title', { count }));
                if (!ok) return;
                if (!(await AV.threeDBucketPreflight())) return;
                const settings = {
                    quality: $('cv3p-quality').value || 'standard',
                    steps: parseInt($('cv3p-steps').value, 10) || 50,
                    guidance: parseFloat($('cv3p-guidance').value) || 7.5,
                    max_faces: parseInt($('cv3p-faces').value, 10) || 0,
                    mesh_resolution: parseInt($('cv3p-depth').value, 10) || 256,
                    save_as: pane.querySelector('input[name="cv3p-saveas"]:checked')?.value || 'default',
                };
                const mk = $('cv3p-model').value;
                if (mk) settings.model_key = mk;
                const seedV = parseInt($('cv3p-seed').value, 10);
                if (Number.isFinite(seedV)) settings.seed = seedV;
                go.disabled = true; go.textContent = '…';
                try {
                    const r = await API.collections.generate3d(collectionId, { targets: this._selTargets(), settings });
                    window.showToast?.(t('collection.threed_submitted', { count: (r.submitted || []).length }), 'success');
                    if ((r.failures || []).length) window.showToast?.(r.failures[0].error, 'warning');
                    close();
                    setTimeout(() => this.open(collectionId), 800);   // reflect submitted status
                } catch (e) {
                    window.showToast?.(e.message || t('collection.error'), 'error');
                    go.disabled = false; go.textContent = t('collection.pane_convert_n', { count });
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
                <div class="flex flex-wrap gap-3 items-start">
                    ${opts.map((o, oi) => {
                        // Each option = a bounded box (side-by-side in a row, wrapping if
                        // many): header (option # + the model that produced it) then all
                        // its variations laid out in a row inside the box.
                        const v0 = (o.variants && o.variants[0]) || {};
                        const model = v0.model_label || v0.model_used || '';   // friendly name, else the key
                        return html`
                        <div class="rounded-lg border border-brand-border bg-brand-bg/40 p-2 max-w-xs">
                            <div class="flex items-center gap-2 mb-1.5">
                                <span class="text-[11px] font-semibold">${t('collection.option_label')} ${oi + 1}</span>
                                ${model ? html`<span class="text-[10px] px-1.5 py-0.5 rounded bg-brand-surface border border-brand-border text-brand-text-muted" title="${t('collection.model_label')}">${model}</span>` : ''}
                            </div>
                            <div class="flex flex-wrap gap-2">
                                ${(o.variants || []).map((v, vi) => {
                                    const vers = this._jobVersions(v);
                                    return html`
                                    <div class="inline-block align-top">
                                        <button class="cv-bd-cell relative rounded-md overflow-hidden border block ${oi === bd.sel.o && vi === bd.sel.v ? 'border-cyan-400 ring-1 ring-cyan-400' : 'border-brand-border hover:border-brand-text-muted'}" data-o="${oi}" data-v="${vi}" style="width:84px;height:84px" title="${t('collection.option_label')} ${oi + 1} · ${t('collection.variation_label')} ${vi + 1}">
                                            <input type="checkbox" class="cv-job-sel absolute top-0.5 left-0.5 z-10 w-3.5 h-3.5 accent-cyan-500 cursor-pointer" title="${t('collection.select_job')}" ${this._jobAllSelected(v) ? 'checked' : ''} />
                                            <img src="/api/gallery/${v.id}/png?t=${cb}" class="w-full h-full object-cover" alt="" loading="lazy" />
                                            ${v.has_3d ? html`<span class="absolute top-0.5 right-0.5 text-[8px] px-1 rounded bg-violet-600/80 text-white">3D</span>` : ''}
                                            <span class="absolute bottom-0 right-0 text-[9px] px-1 bg-black/70 text-white rounded-tl">v${vi + 1}</span>
                                        </button>
                                        ${vers.length > 1 ? html`<div class="flex flex-wrap gap-0.5 mt-0.5" style="max-width:84px">
                                            ${vers.map((ver) => html`<button class="cv-ver-chip text-[8px] leading-none px-1 py-0.5 rounded border ${this._sel.has(this._key(v.id, ver)) ? 'bg-cyan-600 text-white border-cyan-500' : 'border-brand-border text-brand-text-muted hover:border-brand-text-muted'}" data-id="${v.id}" data-ver="${ver}" title="${t('collection.select_version')} ${ver}">v${ver}</button>`)}
                                        </div>` : ''}
                                    </div>`;
                                })}
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
                    const cell = cb.closest('.cv-bd-cell');
                    const v = cell && opts[+cell.dataset.o] && opts[+cell.dataset.o].variants[+cell.dataset.v];
                    if (v) this._toggleJobSel(v, cb.checked);
                    this._renderBatchDetail();   // sync per-version chips
                });
            });
            body.querySelectorAll('.cv-ver-chip').forEach((chip) => {
                chip.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const ver = parseInt(chip.dataset.ver, 10);
                    this._toggleVersionSel(chip.dataset.id, ver, !this._sel.has(this._key(chip.dataset.id, ver)));
                    this._renderBatchDetail();   // reflect chip + job-checkbox state
                });
            });
        },

        async _delete(collectionId) {
            if (!collectionId || !confirm(t('collection.delete_confirm'))) return;
            try {
                await API.collections.del(collectionId);
                this.close();   // also refreshes Studio's "Your Collections" panel
                window.Gallery?.refresh?.();
            } catch (e) { alert(e.message || t('collection.error')); }
        },
    };

    window.CollectionAssetViewer = CollectionAssetViewer;
})();
