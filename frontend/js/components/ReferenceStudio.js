/**
 * ReferenceStudio — the Image Studio "Reference-guided" tab.
 *
 * The user supplies 1–3 reference images + a MANDATORY instruction, then picks
 * how the images are used:
 *   "match"    — "Match the reference": pixel-faithful edit via a deployed custom
 *                model (Qwen-Image-Edit). Preserves the exact product/character.
 *   "inspired" — "Inspired by the reference": a vision LLM reads the image(s) +
 *                the instruction and writes an enhanced prompt; any model renders.
 *
 * Both modes are ALWAYS selectable. "match" needs a deployed reference model — if
 * absent, a notice routes the user to the Custom Models deploy flow (like 3D).
 *
 * Styling mirrors PromptEditor exactly (same card context, STEP badges, spacing).
 * Draft (prompt + mode + downscaled images) auto-persists to localStorage so the
 * user never loses work when routing away to deploy, reloading, or returning later.
 */
(function () {
    'use strict';

    const MAX_IMAGES = 3;
    const DRAFT_KEY = 'artsmoker_reference_draft';
    const _t = (k, d) => (typeof t !== 'undefined' ? t(k) : (d || k));

    class ReferenceStudio {
        constructor(container, opts = {}) {
            this.container = container;
            this.opts = opts;               // { assetType, onGenerate(payload) }
            this._images = [];              // [{ dataUrl, b64 }]
            this._mode = 'inspired';        // "match" | "inspired"
            this._available = null;         // reference-model availability (cached)
            this._analysis = null;          // last "inspired" preview result
            this._render();
            this._restoreDraft();
            this._checkAvailability();
        }

        // ── Public ────────────────────────────────────────────────────
        getPayloadPatch() {
            // Fields merged into the generation payload by ImageStudio.
            return {
                reference_images: this._images.map(i => i.b64),
                reference_mode: this._mode,
            };
        }

        getPrompt() {
            return (this._promptEl?.value || '').trim();
        }

        hasImages() {
            return this._images.length > 0;
        }

        // ── Render ────────────────────────────────────────────────────
        _render() {
            // nosemgrep: javascript.browser.security.insecure-innerhtml.insecure-innerhtml
            this.container.innerHTML = html`
                <div class="reference-studio space-y-4">
                    <!-- Step 1: Reference images -->
                    <div>
                        <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[10px] font-bold text-brand-accent bg-brand-accent/10 rounded px-1.5 py-0.5">${_t('prompt_editor.step', 'STEP')} 1</span>
                            <span class="text-[10px] text-brand-text-muted uppercase tracking-wide">${_t('image_studio.reference_step1')}</span>
                            <span class="text-[9px] text-brand-text-muted/50 ml-auto rs-count">0 / ${MAX_IMAGES}</span>
                        </div>
                        <div class="rs-dropzone rounded-lg border-2 border-dashed border-brand-border hover:border-brand-accent/50 transition-colors cursor-pointer p-4 text-center">
                            <div class="rs-thumbs flex flex-wrap gap-2 justify-center ${'hidden'}"></div>
                            <div class="rs-empty text-brand-text-muted/70 text-xs py-3">
                                <svg class="w-7 h-7 mx-auto mb-1.5 text-brand-text-muted/40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                                ${_t('image_studio.reference_drop')}
                            </div>
                            <input type="file" class="rs-file hidden" accept="image/*" multiple>
                        </div>
                        <p class="text-[10px] text-brand-text-muted/60 mt-1">${_t('image_studio.reference_step1_tip')}</p>
                    </div>

                    <!-- Step 2: Instruction (mandatory) -->
                    <div>
                        <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[10px] font-bold text-brand-accent bg-brand-accent/10 rounded px-1.5 py-0.5">${_t('prompt_editor.step', 'STEP')} 2</span>
                            <span class="text-[10px] text-brand-text-muted uppercase tracking-wide">${_t('image_studio.reference_step2')}</span>
                        </div>
                        <textarea class="rs-prompt input w-full min-h-[90px]" rows="3"
                            placeholder="${_t('image_studio.reference_prompt_ph')}"></textarea>
                        <p class="rs-prompt-warn text-[10px] text-amber-400/80 mt-0.5 hidden">${_t('image_studio.reference_prompt_required')}</p>
                    </div>

                    <!-- Step 3: How to use the reference -->
                    <div>
                        <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[10px] font-bold text-emerald-400/70 bg-emerald-400/10 rounded px-1.5 py-0.5">${_t('prompt_editor.step', 'STEP')} 3</span>
                            <span class="text-[10px] text-brand-text-muted uppercase tracking-wide">${_t('image_studio.reference_step3')}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-2">
                            <button type="button" data-mode="match" class="rs-mode text-left p-2.5 rounded-lg border border-brand-border hover:border-brand-accent/50 transition-all">
                                <div class="text-xs font-semibold flex items-center gap-1.5">
                                    <svg class="w-3.5 h-3.5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                                    ${_t('image_studio.reference_mode_match')}
                                </div>
                                <div class="text-[10px] text-brand-text-muted/70 mt-0.5">${_t('image_studio.reference_mode_match_desc')}</div>
                            </button>
                            <button type="button" data-mode="inspired" class="rs-mode text-left p-2.5 rounded-lg border border-brand-border hover:border-brand-accent/50 transition-all">
                                <div class="text-xs font-semibold flex items-center gap-1.5">
                                    <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
                                    ${_t('image_studio.reference_mode_inspired')}
                                </div>
                                <div class="text-[10px] text-brand-text-muted/70 mt-0.5">${_t('image_studio.reference_mode_inspired_desc')}</div>
                            </button>
                        </div>
                        <!-- Deploy gate notice (shown when "match" chosen but no model deployed) -->
                        <div class="rs-gate hidden mt-2 p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/30">
                            <p class="text-[11px] text-amber-200/90">${_t('image_studio.reference_gate_msg')}</p>
                            <button type="button" class="rs-gate-deploy btn btn-sm text-xs mt-1.5 bg-amber-600 hover:bg-amber-500 text-white">
                                ${_t('image_studio.reference_gate_deploy')}
                            </button>
                        </div>
                        <!-- Inspired-by preview -->
                        <div class="rs-preview hidden mt-2">
                            <button type="button" class="rs-preview-btn text-[11px] w-full py-2 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 hover:bg-amber-500/20 transition-all">
                                ${_t('image_studio.reference_preview_btn')}
                            </button>
                            <div class="rs-preview-out hidden mt-1.5 p-2 rounded-lg bg-emerald-950/10 border border-emerald-500/20 text-[11px] text-brand-text/80 whitespace-pre-wrap max-h-32 overflow-auto"></div>
                        </div>
                    </div>
                    <p class="text-[10px] text-brand-text-muted/40">${_t('image_studio.reference_draft_note')}</p>
                </div>`;

            // Cache elements
            this._dropzone = this.container.querySelector('.rs-dropzone');
            this._fileInput = this.container.querySelector('.rs-file');
            this._thumbs = this.container.querySelector('.rs-thumbs');
            this._empty = this.container.querySelector('.rs-empty');
            this._countEl = this.container.querySelector('.rs-count');
            this._promptEl = this.container.querySelector('.rs-prompt');
            this._promptWarn = this.container.querySelector('.rs-prompt-warn');
            this._gateEl = this.container.querySelector('.rs-gate');
            this._previewWrap = this.container.querySelector('.rs-preview');
            this._previewOut = this.container.querySelector('.rs-preview-out');

            this._wire();
            this._reflectMode();
        }

        _wire() {
            // Dropzone: click + drag/drop
            this._dropzone.addEventListener('click', (e) => {
                if (e.target.closest('.rs-thumb-remove')) return;
                this._fileInput.click();
            });
            this._fileInput.addEventListener('change', (e) => this._addFiles(e.target.files));
            this._dropzone.addEventListener('dragover', (e) => { e.preventDefault(); this._dropzone.classList.add('border-brand-accent'); });
            this._dropzone.addEventListener('dragleave', () => this._dropzone.classList.remove('border-brand-accent'));
            this._dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                this._dropzone.classList.remove('border-brand-accent');
                this._addFiles(e.dataTransfer.files);
            });

            // Prompt persistence
            this._promptEl.addEventListener('input', () => {
                this._promptWarn.classList.add('hidden');
                this._analysis = null; // invalidate stale preview
                this._saveDraft();
            });

            // Mode toggle
            this.container.querySelectorAll('.rs-mode').forEach(btn => {
                btn.addEventListener('click', () => {
                    this._mode = btn.dataset.mode;
                    this._reflectMode();
                    this._saveDraft();
                });
            });

            // Deploy-gate route (mirror 3D: close nothing, open Custom Models)
            this.container.querySelector('.rs-gate-deploy')?.addEventListener('click', () => {
                window.ModelSettings?.open?.('custom-models');
            });

            // Inspired-by preview
            this.container.querySelector('.rs-preview-btn')?.addEventListener('click', () => this._runPreview());
        }

        // ── Images ────────────────────────────────────────────────────
        async _addFiles(fileList) {
            const files = Array.from(fileList || []);
            for (const f of files) {
                if (this._images.length >= MAX_IMAGES) break;
                if (!f.type.startsWith('image/')) continue;
                try {
                    const { dataUrl, b64 } = await this._downscale(f);
                    this._images.push({ dataUrl, b64 });
                } catch (e) { /* skip unreadable */ }
            }
            this._fileInput.value = '';
            this._analysis = null;
            this._renderThumbs();
            this._saveDraft();
        }

        _downscale(fileOrDataUrl, maxDim = 1280) {
            // Downscale to keep the vision payload small + the draft under localStorage limits.
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => {
                    let { width, height } = img;
                    const scale = Math.min(1, maxDim / Math.max(width, height));
                    width = Math.round(width * scale); height = Math.round(height * scale);
                    const canvas = document.createElement('canvas');
                    canvas.width = width; canvas.height = height;
                    canvas.getContext('2d').drawImage(img, 0, 0, width, height);
                    const dataUrl = canvas.toDataURL('image/png');
                    resolve({ dataUrl, b64: dataUrl.split(',')[1] });
                };
                img.onerror = reject;
                if (typeof fileOrDataUrl === 'string') {
                    img.src = fileOrDataUrl;
                } else {
                    const reader = new FileReader();
                    reader.onload = () => { img.src = reader.result; };
                    reader.onerror = reject;
                    reader.readAsDataURL(fileOrDataUrl);
                }
            });
        }

        _renderThumbs() {
            const n = this._images.length;
            this._countEl.textContent = `${n} / ${MAX_IMAGES}`;
            if (n === 0) {
                this._thumbs.classList.add('hidden');
                this._empty.classList.remove('hidden');
                this._thumbs.innerHTML = '';
                return;
            }
            this._empty.classList.add('hidden');
            this._thumbs.classList.remove('hidden');
            // nosemgrep: javascript.browser.security.insecure-innerhtml.insecure-innerhtml
            this._thumbs.innerHTML = this._images.map((im, i) => html`
                <div class="relative w-16 h-16 rounded-lg overflow-hidden border border-brand-border group">
                    <img src="${im.dataUrl}" class="w-full h-full object-cover">
                    <button type="button" data-i="${i}" class="rs-thumb-remove absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-black/70 text-white text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">×</button>
                </div>`).join('');
            this._thumbs.querySelectorAll('.rs-thumb-remove').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._images.splice(parseInt(btn.dataset.i, 10), 1);
                    this._analysis = null;
                    this._renderThumbs();
                    this._saveDraft();
                });
            });
        }

        // ── Mode reflection + availability gate ─────────────────────────
        _reflectMode() {
            this.container.querySelectorAll('.rs-mode').forEach(btn => {
                const active = btn.dataset.mode === this._mode;
                btn.classList.toggle('border-brand-accent', active);
                btn.classList.toggle('bg-brand-accent/5', active);
                btn.classList.toggle('border-brand-border', !active);
            });
            // Gate only applies to "match" (needs a deployed model). "inspired" never gated.
            const showGate = this._mode === 'match' && this._available && this._available.available === false;
            this._gateEl.classList.toggle('hidden', !showGate);
            // Inspired-by preview only meaningful in "inspired" mode.
            this._previewWrap.classList.toggle('hidden', this._mode !== 'inspired');
        }

        async _checkAvailability() {
            try {
                this._available = await API.referenceAvailable();
            } catch { this._available = { available: false }; }
            this._reflectMode();
        }

        /** Public: re-check whether a reference model is deployed. Called each time
         *  the tab is shown, so a model deployed AFTER this component mounted (the
         *  common case: user deploys, comes back) correctly hides the deploy gate. */
        refresh() {
            this._checkAvailability();
        }

        /** Called by ImageStudio before generating — returns an error string or null. */
        validate() {
            if (!this.hasImages()) return _t('image_studio.reference_need_image');
            if (!this.getPrompt()) { this._promptWarn.classList.remove('hidden'); return _t('image_studio.reference_prompt_required'); }
            if (this._mode === 'match' && this._available && this._available.available === false) {
                this._gateEl.classList.remove('hidden');
                return _t('image_studio.reference_gate_msg');
            }
            return null;
        }

        // ── Inspired-by preview ─────────────────────────────────────────
        async _runPreview() {
            const prompt = this.getPrompt();
            if (!this.hasImages()) { window.showToast?.(_t('image_studio.reference_need_image'), 'error'); return; }
            if (!prompt) { this._promptWarn.classList.remove('hidden'); return; }
            this._previewOut.classList.remove('hidden');
            this._previewOut.textContent = _t('image_studio.reference_preview_loading');
            try {
                const res = await API.analyzeReference({
                    images: this._images.map(i => i.b64),
                    prompt,
                    asset_type: (this.opts.assetType?.() || 'photorealistic'),
                    ui_lang: (typeof I18n !== 'undefined' ? I18n.getLang() : ''),
                });
                this._analysis = res;
                if (res.analyzed && res.enhanced_prompt) {
                    this._previewOut.textContent = res.enhanced_prompt + (res.notes ? `\n\n— ${res.notes}` : '');
                } else {
                    this._previewOut.textContent = _t('image_studio.reference_preview_none');
                }
            } catch (e) {
                this._previewOut.textContent = _t('image_studio.reference_preview_err');
            }
        }

        // ── Draft persistence (localStorage) ────────────────────────────
        _saveDraft() {
            try {
                localStorage.setItem(DRAFT_KEY, JSON.stringify({
                    prompt: this.getPrompt(),
                    mode: this._mode,
                    images: this._images.map(i => i.dataUrl),
                }));
            } catch { /* quota — ignore */ }
        }

        async _restoreDraft() {
            let draft;
            try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null'); } catch { draft = null; }
            if (!draft) return;
            if (draft.prompt) this._promptEl.value = draft.prompt;
            if (draft.mode) this._mode = draft.mode;
            if (Array.isArray(draft.images) && draft.images.length) {
                for (const dataUrl of draft.images.slice(0, MAX_IMAGES)) {
                    try {
                        const { b64 } = await this._downscale(dataUrl);
                        this._images.push({ dataUrl, b64 });
                    } catch { /* skip */ }
                }
                this._renderThumbs();
            }
            this._reflectMode();
            if (draft.prompt || (draft.images && draft.images.length)) {
                window.showToast?.(_t('image_studio.reference_draft_restored'), 'info');
            }
        }

        clearDraft() {
            try { localStorage.removeItem(DRAFT_KEY); } catch {}
        }
    }

    window.ReferenceStudio = ReferenceStudio;
})();
