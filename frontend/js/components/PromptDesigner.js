/**
 * ArtSmoker — Prompt Designer Modal
 *
 * Decomposes a user prompt into structured visual components using an LLM,
 * displays them in an editable panel with color swatches, lock/unlock per field,
 * and recomposes into a flat generation prompt.
 *
 * Opened via "Prompt Designer" button in Image Studio.
 */
(function () {
    'use strict';

    const SECTIONS = [
        { key: 'subject', label: 'Subject', icon: '👤', fields: ['description', 'clothing', 'accessories', 'expression_pose', 'details'] },
        { key: 'scene', label: 'Scene', icon: '🏔', fields: ['setting', 'background', 'props', 'time_of_day'] },
        { key: 'composition', label: 'Composition', icon: '📐', fields: ['camera_angle', 'framing', 'depth_of_field'] },
        { key: 'lighting', label: 'Lighting', icon: '💡', fields: ['key_light', 'fill_rim', 'mood'] },
        { key: 'style', label: 'Style', icon: '🎨', fields: ['art_style', 'quality'] },
    ];

    function _fieldLabel(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    window.PromptDesigner = {
        _modal: null,
        _data: null,
        _locks: {},
        _onApply: null,

        /**
         * Open the Prompt Designer modal.
         * @param {string} prompt - User's original prompt
         * @param {object} opts - { styleId, assetType, imageModel, onApply(composedPrompt, negativePrompt) }
         */
        async open(prompt, opts = {}) {
            if (!prompt?.trim()) {
                window.showToast?.('Enter a prompt first', 'warning');
                return;
            }
            this._onApply = opts.onApply || null;
            this._locks = {};

            // Show loading
            this._showModal('<div class="text-center py-12"><div class="loading-spinner mx-auto mb-3"></div><p class="text-sm text-brand-text-muted">Analyzing your prompt...</p></div>');

            try {
                const resp = await fetch('/api/refine-prompt/decompose', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: prompt,
                        style_id: opts.styleId || undefined,
                        asset_type: opts.assetType || 'character',
                    }),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                this._data = await resp.json();
                this._imageModel = opts.imageModel || 'nova_canvas';
                this._renderDesigner();
            } catch (err) {
                this._showModal(`<div class="text-center py-8"><p class="text-red-400 text-sm">Failed to decompose prompt: ${err.message}</p><button class="btn btn-sm mt-4 px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted" onclick="PromptDesigner.close()">Close</button></div>`);
            }
        },

        close() {
            if (this._modal) {
                this._modal.remove();
                this._modal = null;
            }
        },

        _showModal(innerHtml) {
            if (this._modal) this._modal.remove();
            this._modal = document.createElement('div');
            this._modal.className = 'fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-start justify-center p-4 pt-8 overflow-y-auto';
            this._modal.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl w-full max-w-3xl">
                    <div class="flex items-center justify-between px-5 py-3 border-b border-brand-border">
                        <h2 class="text-sm font-semibold text-brand-text flex items-center gap-2">
                            <span class="text-lg">🎨</span> Prompt Designer
                        </h2>
                        <button class="pd-close text-brand-text-muted hover:text-brand-text text-lg">&times;</button>
                    </div>
                    <div class="pd-body p-5">${innerHtml}</div>
                </div>`;
            this._modal.querySelector('.pd-close')?.addEventListener('click', () => this.close());
            this._modal.addEventListener('click', (e) => { if (e.target === this._modal) this.close(); });
            document.body.appendChild(this._modal);
        },

        _renderDesigner() {
            const d = this._data;
            if (!d) return;

            let html = '';

            // Sections
            for (const section of SECTIONS) {
                const sectionData = d[section.key] || {};
                html += `<details class="pd-section mb-3" open>
                    <summary class="flex items-center gap-2 cursor-pointer py-2 px-3 rounded-lg bg-black/20 hover:bg-black/30 text-sm font-medium text-brand-text">
                        <span>${section.icon}</span>
                        <span>${section.label}</span>
                        <span class="text-[10px] text-brand-text-muted ml-1">(${section.fields.filter(f => sectionData[f]).length})</span>
                    </summary>
                    <div class="pl-3 pr-1 pt-2 space-y-2">`;

                for (const field of section.fields) {
                    const value = sectionData[field] || '';
                    if (!value) continue;
                    const lockKey = `${section.key}.${field}`;
                    const isLocked = this._locks[lockKey];
                    html += `
                        <div class="pd-field flex items-start gap-2 group" data-key="${lockKey}">
                            <button class="pd-lock mt-1 text-xs opacity-50 hover:opacity-100 transition-opacity flex-shrink-0"
                                    title="${isLocked ? 'Locked — will stay fixed on regenerate' : 'Unlocked — may change on regenerate'}"
                                    data-lock="${lockKey}">
                                ${isLocked ? '🔒' : '🔓'}
                            </button>
                            <div class="flex-1 min-w-0">
                                <label class="text-[10px] text-brand-text-muted uppercase tracking-wide">${_fieldLabel(field)}</label>
                                <textarea class="pd-input w-full bg-black/20 border border-brand-border/50 rounded-md px-2 py-1.5 text-xs text-brand-text resize-none focus:border-brand-accent/50 focus:outline-none"
                                          rows="${value.length > 120 ? 3 : 2}"
                                          data-section="${section.key}" data-field="${field}">${value}</textarea>
                            </div>
                        </div>`;
                }
                html += '</div></details>';
            }

            // Color palette
            const palette = d.style?.color_palette || [];
            if (palette.length) {
                html += `<details class="pd-section mb-3" open>
                    <summary class="flex items-center gap-2 cursor-pointer py-2 px-3 rounded-lg bg-black/20 hover:bg-black/30 text-sm font-medium text-brand-text">
                        <span>🎨</span> Color Palette <span class="text-[10px] text-brand-text-muted ml-1">(${palette.length})</span>
                    </summary>
                    <div class="pl-3 pr-1 pt-2 flex flex-wrap gap-3">`;
                for (const color of palette) {
                    html += `
                        <div class="flex items-center gap-2 bg-black/20 rounded-lg px-3 py-2">
                            <div class="w-8 h-8 rounded-md border border-white/20 flex-shrink-0" style="background-color: ${color.hex}"></div>
                            <div>
                                <div class="text-xs font-medium text-brand-text">${color.name}</div>
                                <div class="text-[10px] text-brand-text-muted">${color.hex} — ${color.usage || ''}</div>
                            </div>
                        </div>`;
                }
                html += '</div></details>';
            }

            // Action buttons
            html += `
                <div class="flex gap-2 justify-end pt-4 border-t border-brand-border mt-4">
                    <button class="pd-regenerate btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">
                        🔄 Regenerate Unlocked Fields
                    </button>
                    <button class="pd-apply btn btn-sm text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">
                        Use This Prompt →
                    </button>
                </div>`;

            const body = this._modal?.querySelector('.pd-body');
            if (body) body.innerHTML = html;

            // Attach events
            this._modal?.querySelectorAll('.pd-lock').forEach(btn => {
                btn.addEventListener('click', () => {
                    const key = btn.dataset.lock;
                    this._locks[key] = !this._locks[key];
                    btn.textContent = this._locks[key] ? '🔒' : '🔓';
                    btn.title = this._locks[key] ? 'Locked — will stay fixed on regenerate' : 'Unlocked — may change on regenerate';
                });
            });

            this._modal?.querySelectorAll('.pd-input').forEach(input => {
                input.addEventListener('input', () => {
                    const section = input.dataset.section;
                    const field = input.dataset.field;
                    if (this._data[section]) this._data[section][field] = input.value;
                });
            });

            this._modal?.querySelector('.pd-apply')?.addEventListener('click', () => this._applyPrompt());
            this._modal?.querySelector('.pd-regenerate')?.addEventListener('click', () => this._regenerateUnlocked());
        },

        async _applyPrompt() {
            const btn = this._modal?.querySelector('.pd-apply');
            if (btn) { btn.disabled = true; btn.textContent = 'Composing...'; }

            try {
                const resp = await fetch('/api/refine-prompt/recompose', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        structured: this._data,
                        image_model: this._imageModel,
                    }),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const result = await resp.json();

                if (this._onApply) {
                    this._onApply(result.prompt, result.negative_prompt);
                }
                this.close();
                window.showToast?.('Prompt composed from designer', 'success');
            } catch (err) {
                window.showToast?.('Failed to compose prompt', 'error');
                if (btn) { btn.disabled = false; btn.textContent = 'Use This Prompt →'; }
            }
        },

        async _regenerateUnlocked() {
            // TODO: Re-call decompose with locked fields preserved
            window.showToast?.('Regenerate coming soon', 'info');
        },
    };
})();
