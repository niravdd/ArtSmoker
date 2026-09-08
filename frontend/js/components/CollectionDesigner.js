/**
 * CollectionDesigner — the Collections (Set Generation) design surface (SPEC §18).
 *
 * A self-contained modal (NOT a mutation of the Prompt Designer). Opening it
 * seeds from the current prompt and auto-decomposes into a shared art direction
 * + a roster of distinct Batches, each with an editable model-agnostic prompt.
 * Editing the art direction recomposes every Batch; per-Batch lock / regenerate /
 * delete; knobs for count / options / variations / cohesion. Generate streams the
 * whole-collection generation and refreshes the Gallery.
 *
 * Terminology (locked): Collection -> Batch (one roster subject) -> Job (image).
 * The collection design is held IN MEMORY here until Generate (no pre-gen
 * persistence — matches the single-asset flow).
 */
(function () {
    const t = (k, p) => (window.t ? window.t('artsmoker.ui.' + k, p) : k);

    const CollectionDesigner = {
        _state: null,   // { collectionId, name, prompt, artDirection{}, roster[], knobs{}, designCost }
        _ctx: null,     // { image_model, asset_type, style_id }
        _busy: false,

        /** Open the designer for a prompt. ctx = {image_model, asset_type, style_id}. */
        async open(prompt, ctx = {}) {
            this._ctx = {
                image_model: ctx.image_model || 'sd35_large',
                asset_type: ctx.asset_type || 'game_asset',
                style_id: ctx.style_id || null,
            };
            this._state = {
                collectionId: null, name: '', prompt: (prompt || '').trim(),
                artDirection: {}, roster: [], designCost: 0,
                knobs: { count: null, options: 3, variations: 2, cohesion: 'prompt' },
            };
            this._mount();
            if (!this._state.prompt) { this._renderError(t('collection.error')); return; }
            await this._decompose();
        },

        close() {
            document.getElementById('collection-designer-overlay')?.remove();
            this._state = null;
            // Let Image Studio clear its collection-mode toggle.
            window.ImageStudio?._onCollectionDesignerClosed?.();
        },

        // ── Backend calls ────────────────────────────────────────────────

        async _decompose() {
            this._setBusy(true, t('collection.decomposing'));
            try {
                const r = await API.collections.decompose({
                    prompt: this._state.prompt,
                    image_model: this._ctx.image_model,
                    asset_type: this._ctx.asset_type,
                    style_id: this._ctx.style_id,
                    count: this._state.knobs.count,
                });
                this._state.collectionId = r.collection_id;
                this._state.name = r.name || 'Collection';
                this._state.artDirection = r.art_direction || {};
                this._state.roster = (r.roster || []).map(e => ({ ...e, locked: false }));
                this._state.designCost += (r.cost || 0);
                window.Telemetry?.track?.('collection_designed', { batch_count: this._state.roster.length });
                this._render();
            } catch (e) {
                this._renderError(e.message || t('collection.error'));
            } finally {
                this._setBusy(false);
            }
        },

        async _recomposeAll() {
            this._setBusy(true, t('collection.recomposing'));
            try {
                const r = await API.collections.recomposeAll({
                    art_direction: this._adText(),
                    roster: this._state.roster.map(e => ({ name: e.name, slug: e.slug, concept: e.concept })),
                    image_model: this._ctx.image_model,
                    asset_type: this._ctx.asset_type,
                });
                // Preserve lock flags; take fresh prompts.
                const locks = Object.fromEntries(this._state.roster.map(e => [e.slug, e.locked]));
                this._state.roster = (r.roster || []).map(e => ({ ...e, locked: !!locks[e.slug] }));
                this._state.designCost += (r.cost || 0);
                window.Telemetry?.track?.('collection_art_direction_edited', {});
                this._render();
            } catch (e) { this._toast(e.message); } finally { this._setBusy(false); }
        },

        async _regenerateBatch(idx) {
            const e = this._state.roster[idx];
            if (!e) return;
            this._setBusy(true, t('collection.recomposing'));
            try {
                const r = await API.collections.recomposeBatch({
                    art_direction: this._adText(), name: e.name, concept: e.concept,
                    image_model: this._ctx.image_model, asset_type: this._ctx.asset_type,
                });
                e.model_agnostic_prompt = r.model_agnostic_prompt;
                this._state.designCost += (r.cost || 0);
                window.Telemetry?.track?.('collection_batch_regenerated', {});
                this._render();
            } catch (err) { this._toast(err.message); } finally { this._setBusy(false); }
        },

        async _regenerateAllUnlocked() {
            this._setBusy(true, t('collection.recomposing'));
            try {
                const locked = this._state.roster.filter(e => e.locked)
                    .map(e => ({ name: e.name, slug: e.slug, concept: e.concept, model_agnostic_prompt: e.model_agnostic_prompt }));
                const r = await API.collections.regenerateRoster({
                    prompt: this._state.prompt, art_direction: this._adText(),
                    count: this._state.knobs.count, locked,
                    image_model: this._ctx.image_model, asset_type: this._ctx.asset_type,
                    style_id: this._ctx.style_id,
                });
                const locks = Object.fromEntries(locked.map(e => [e.slug, true]));
                this._state.roster = (r.roster || []).map(e => ({ ...e, locked: !!locks[e.slug] }));
                this._state.designCost += (r.cost || 0);
                window.Telemetry?.track?.('collection_roster_regenerated', {});
                this._render();
            } catch (e) { this._toast(e.message); } finally { this._setBusy(false); }
        },

        async _generate() {
            if (!this._valid()) return;
            const s = this._state;
            this._setBusy(true, t('collection.generating'));
            const bar = document.getElementById('cd-progress');
            let doneBatches = 0;
            const total = s.roster.length;
            try {
                window.Telemetry?.track?.('collection_generation_started',
                    { batches: total, options: s.knobs.options, variations: s.knobs.variations });
                await API.collections.generateStream({
                    collection_id: s.collectionId, name: s.name, raw_ask: s.prompt,
                    art_direction: s.artDirection, roster: s.roster,
                    image_model: this._ctx.image_model, asset_type: this._ctx.asset_type,
                    style_id: this._ctx.style_id,
                    num_options: s.knobs.options, num_variations: s.knobs.variations,
                    cohesion_mode: s.knobs.cohesion,
                }, (evt) => {
                    if (evt.type === 'batch_complete') { doneBatches++; }
                    if (bar) {
                        const label = evt.collection_batch_name || evt.batch_name || '';
                        bar.textContent = `${doneBatches}/${total} — ${label}`;
                    }
                });
                window.Telemetry?.track?.('collection_generation_complete', { batches: total });
                this.close();
                // Jump to the Gallery + refresh so the new collection card appears.
                if (location.hash !== '#gallery') location.hash = '#gallery';
                setTimeout(() => window.Gallery?.refresh?.(), 150);
            } catch (e) {
                this._toast(e.message || t('collection.error'));
                this._setBusy(false);
            }
        },

        // ── Helpers ──────────────────────────────────────────────────────

        _adText() {
            // Prefer the edited textarea; fall back to the structured "text".
            const el = document.getElementById('cd-art-direction');
            return el ? el.value : (this._state.artDirection.text || '');
        },
        _valid() {
            const s = this._state;
            return s && s.roster.length > 0 && this._adText().trim() &&
                s.roster.every(e => (e.model_agnostic_prompt || '').trim());
        },
        _projectedImages() {
            const s = this._state;
            return s.roster.length * s.knobs.options * s.knobs.variations;
        },

        // ── Rendering ──────────────────────────────────────────────────────

        _mount() {
            document.getElementById('collection-designer-overlay')?.remove();
            const overlay = document.createElement('div');
            overlay.id = 'collection-designer-overlay';
            overlay.className = 'fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4';
            // nosemgrep
            overlay.innerHTML = html`
                <div class="card w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center justify-between p-4 border-b border-brand-border">
                        <h2 class="text-lg font-semibold">${t('collection.designer_title')}</h2>
                        <button id="cd-close" class="text-brand-text-muted hover:text-brand-text text-2xl leading-none">&times;</button>
                    </div>
                    <div id="cd-body" class="flex-1 overflow-y-auto p-4 space-y-4"></div>
                    <div class="p-4 border-t border-brand-border flex items-center justify-between gap-3">
                        <div id="cd-cost" class="text-xs text-brand-text-muted"></div>
                        <div class="flex items-center gap-2">
                            <span id="cd-progress" class="text-xs text-cyan-300"></span>
                            <button id="cd-generate" class="btn btn-primary btn-sm">${t('collection.generate')}</button>
                        </div>
                    </div>
                </div>`;
            document.body.appendChild(overlay);
            document.getElementById('cd-close').addEventListener('click', () => this._confirmClose());
            overlay.addEventListener('click', (e) => { if (e.target === overlay) this._confirmClose(); });
            document.getElementById('cd-generate').addEventListener('click', () => this._generate());
        },

        _confirmClose() {
            if (this._state && this._state.designCost > 0) {
                if (!confirm(t('collection.reset_confirm', { cost: '$' + this._state.designCost.toFixed(3) }))) return;
            }
            this.close();
        },

        _renderError(msg) {
            const body = document.getElementById('cd-body');
            if (body) body.innerHTML = html`<div class="text-center py-10 text-red-400 text-sm">${msg}</div>`; // nosemgrep
        },

        _setBusy(on, msg) {
            this._busy = on;
            const gen = document.getElementById('cd-generate');
            const prog = document.getElementById('cd-progress');
            if (gen) gen.disabled = on || !this._valid();
            if (prog && msg) prog.textContent = msg;
            if (prog && !on && !msg) prog.textContent = '';
        },

        _toast(msg) {
            const prog = document.getElementById('cd-progress');
            if (prog) prog.textContent = msg || '';
        },

        _updateCost() {
            const el = document.getElementById('cd-cost');
            if (!el || !this._state) return;
            el.textContent =
                `${t('collection.cost_design')}: $${this._state.designCost.toFixed(3)} · ` +
                `${this._projectedImages()} images (${this._state.roster.length}×${this._state.knobs.options}×${this._state.knobs.variations})`;
        },

        _render() {
            const body = document.getElementById('cd-body');
            if (!body || !this._state) return;
            const s = this._state;
            // nosemgrep
            body.innerHTML = html`
                <div>
                    <label class="block text-sm font-medium mb-1">${t('collection.art_direction_label')}</label>
                    <textarea id="cd-art-direction" rows="5" class="input w-full text-sm font-mono">${s.artDirection.text || ''}</textarea>
                    <p class="text-[10px] text-brand-text-muted mt-1">${t('collection.art_direction_hint')}</p>
                    <button id="cd-recompose-all" class="btn btn-xs mt-1 bg-brand-bg border border-brand-border">${t('collection.recomposing').replace('…','')} ↻</button>
                </div>
                <div class="grid grid-cols-4 gap-2 items-end">
                    <div><label class="block text-[11px] mb-1">${t('collection.count_label')}</label>
                        <input id="cd-count" type="number" min="1" max="60" placeholder="${t('collection.count_auto')}" value="${s.knobs.count ?? ''}" class="input text-sm" /></div>
                    <div><label class="block text-[11px] mb-1">${t('collection.options_label')}</label>
                        <select id="cd-options" class="input text-sm">${[1,2,3,4,5].map(n => html`<option value="${n}" ${n===s.knobs.options?'selected':''}>${n}</option>`)}</select></div>
                    <div><label class="block text-[11px] mb-1">${t('collection.variations_label')}</label>
                        <select id="cd-variations" class="input text-sm">${[1,2,3,4,5].map(n => html`<option value="${n}" ${n===s.knobs.variations?'selected':''}>${n}</option>`)}</select></div>
                    <div><label class="block text-[11px] mb-1">${t('collection.model_label')}</label>
                        <input class="input text-sm" value="${this._ctx.image_model}" disabled /></div>
                </div>
                <div class="flex items-center justify-between">
                    <h3 class="text-sm font-semibold uppercase tracking-wide text-brand-text-muted">${t('collection.roster_label')} (${s.roster.length})</h3>
                    <button id="cd-regen-all" class="btn btn-xs bg-brand-bg border border-brand-border">${t('collection.regenerate_all')}</button>
                </div>
                <div id="cd-roster" class="space-y-2">
                    ${s.roster.length === 0
                        ? html`<p class="text-sm text-brand-text-muted">${t('collection.empty')}</p>`
                        : s.roster.map((e, i) => this._batchRow(e, i))}
                </div>
                <button id="cd-add" class="btn btn-xs bg-brand-bg border border-brand-border">＋ ${t('collection.add_batch')}</button>
            `;
            // Wire controls
            document.getElementById('cd-recompose-all').addEventListener('click', () => this._recomposeAll());
            document.getElementById('cd-regen-all').addEventListener('click', () => this._regenerateAllUnlocked());
            document.getElementById('cd-add').addEventListener('click', () => this._addBatch());
            document.getElementById('cd-count').addEventListener('change', (ev) => {
                const v = parseInt(ev.target.value, 10); s.knobs.count = (v > 0 ? v : null); });
            document.getElementById('cd-options').addEventListener('change', (ev) => { s.knobs.options = +ev.target.value; this._updateCost(); this._setBusy(false); });
            document.getElementById('cd-variations').addEventListener('change', (ev) => { s.knobs.variations = +ev.target.value; this._updateCost(); this._setBusy(false); });
            s.roster.forEach((e, i) => {
                document.getElementById(`cd-lock-${i}`)?.addEventListener('click', () => { e.locked = !e.locked; this._render(); });
                document.getElementById(`cd-regen-${i}`)?.addEventListener('click', () => this._regenerateBatch(i));
                document.getElementById(`cd-del-${i}`)?.addEventListener('click', () => { s.roster.splice(i, 1); this._render(); });
                document.getElementById(`cd-name-${i}`)?.addEventListener('change', (ev) => { e.name = ev.target.value; });
                document.getElementById(`cd-concept-${i}`)?.addEventListener('change', (ev) => { e.concept = ev.target.value; });
                document.getElementById(`cd-prompt-${i}`)?.addEventListener('change', (ev) => { e.model_agnostic_prompt = ev.target.value; this._setBusy(false); });
            });
            this._updateCost();
            this._setBusy(false);
        },

        _batchRow(e, i) {
            return html`
                <div class="card-static p-2 space-y-1 ${e.locked ? 'ring-1 ring-cyan-500/40' : ''}">
                    <div class="flex items-center gap-2">
                        <input id="cd-name-${i}" value="${e.name || ''}" placeholder="${t('collection.batch_name')}" class="input text-sm font-medium flex-1" />
                        <button id="cd-lock-${i}" class="btn btn-xs ${e.locked ? 'bg-cyan-600 text-white' : 'bg-brand-bg border border-brand-border'}" title="${e.locked ? t('collection.unlock') : t('collection.lock')}">${e.locked ? '🔒' : '🔓'}</button>
                        <button id="cd-regen-${i}" class="btn btn-xs bg-brand-bg border border-brand-border" title="${t('collection.regenerate')}">↻</button>
                        <button id="cd-del-${i}" class="btn btn-xs bg-brand-bg border border-brand-border" title="${t('collection.delete')}">🗑</button>
                    </div>
                    <input id="cd-concept-${i}" value="${e.concept || ''}" placeholder="${t('collection.batch_concept')}" class="input text-xs w-full" />
                    <textarea id="cd-prompt-${i}" rows="2" placeholder="${t('collection.batch_prompt')}" class="input text-xs w-full">${e.model_agnostic_prompt || ''}</textarea>
                </div>`;
        },

        _addBatch() {
            this._state.roster.push({ name: '', slug: 'batch_' + (this._state.roster.length + 1), concept: '', model_agnostic_prompt: '', locked: false });
            this._render();
        },
    };

    window.CollectionDesigner = CollectionDesigner;
})();
