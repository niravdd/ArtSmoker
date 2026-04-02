/**
 * ArtSmoker — Prompt Designer Modal
 *
 * Decomposes a user prompt into structured visual components using an LLM,
 * displays them in a tabbed interface with color swatches and lock/unlock per field.
 * "Save & Continue" stores the data and triggers enhanced prompt composition.
 */
(function () {
    'use strict';

    const TABS = [
        { key: 'subject', label: 'Subject', icon: '👤', fields: ['description', 'clothing', 'accessories', 'expression_pose', 'details'] },
        { key: 'scene', label: 'Scene', icon: '🏔', fields: ['setting', 'background', 'props', 'time_of_day'] },
        { key: 'composition', label: 'Composition', icon: '📐', fields: ['camera_angle', 'framing', 'depth_of_field'] },
        { key: 'lighting', label: 'Lighting', icon: '💡', fields: ['key_light', 'fill_rim', 'mood'] },
        { key: 'style', label: 'Style & Colors', icon: '🎨', fields: ['art_style', 'quality'] },
    ];

    function _fieldLabel(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    window.PromptDesigner = {
        _modal: null,
        _data: null,
        _locks: {},
        _onApply: null,
        _activeTab: 'subject',

        /**
         * Open the Prompt Designer modal.
         * @param {string} prompt - User's original prompt
         * @param {object} opts - { styleId, assetType, imageModel, onApply(designerData) }
         */
        async open(prompt, opts = {}) {
            if (!prompt?.trim()) {
                window.showToast?.('Enter a prompt first', 'warning');
                return;
            }
            this._onApply = opts.onApply || null;
            this._locks = {};
            this._activeTab = 'subject';

            this._showModal(`
                <div class="text-center py-12">
                    <div class="text-3xl mb-3" style="display:inline-block;animation:spin 2s linear infinite">⏳</div>
                    <style>@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style>
                    <p class="text-sm text-brand-text-muted">Analyzing your prompt...</p>
                    <p class="text-[10px] text-brand-text-muted/50 mt-1">Breaking down into visual components</p>
                </div>`);

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
                this._renderDesigner();
            } catch (err) {
                const body = this._modal?.querySelector('.pd-body');
                if (body) body.innerHTML = `
                    <div class="text-center py-8">
                        <p class="text-red-400 text-sm">Failed to decompose prompt: ${err.message}</p>
                        <button class="btn btn-sm mt-4 px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted" onclick="PromptDesigner.close()">Close</button>
                    </div>`;
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
            this._modal.className = 'fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto';
            this._modal.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl w-full max-w-3xl">
                    <div class="flex items-center justify-between px-5 py-3 border-b border-brand-border">
                        <h2 class="text-sm font-semibold text-brand-text flex items-center gap-2">
                            <span class="text-lg">🎨</span> Prompt Designer
                        </h2>
                        <button class="pd-close text-brand-text-muted hover:text-brand-text text-lg leading-none">&times;</button>
                    </div>
                    <div class="pd-body">${innerHtml}</div>
                </div>`;
            this._modal.querySelector('.pd-close')?.addEventListener('click', () => this.close());
            this._modal.addEventListener('click', (e) => { if (e.target === this._modal) this.close(); });
            document.body.appendChild(this._modal);
        },

        _renderDesigner() {
            const d = this._data;
            if (!d) return;

            // Tab bar
            let tabBar = '<div class="flex border-b border-brand-border">';
            for (const tab of TABS) {
                const active = tab.key === this._activeTab;
                const count = (d[tab.key] ? Object.values(d[tab.key]).filter(v => v && typeof v === 'string' && v.length > 0).length : 0);
                tabBar += `<button class="pd-tab flex-1 py-2.5 text-[11px] font-medium transition-all border-b-2 ${
                    active
                        ? 'text-brand-accent border-brand-accent bg-brand-accent/5'
                        : 'text-brand-text-muted border-transparent hover:text-brand-text hover:bg-white/3'
                }" data-tab="${tab.key}">
                    <span class="block">${tab.icon}</span>
                    <span class="block mt-0.5">${tab.label}</span>
                    ${count ? `<span class="text-[9px] opacity-50">(${count})</span>` : ''}
                </button>`;
            }
            tabBar += '</div>';

            // Tab content
            let tabContent = '';
            for (const tab of TABS) {
                const sectionData = d[tab.key] || {};
                const isActive = tab.key === this._activeTab;
                let fields = '';

                for (const field of tab.fields) {
                    const value = sectionData[field] || '';
                    if (!value) continue;
                    const lockKey = `${tab.key}.${field}`;
                    const isLocked = this._locks[lockKey];
                    fields += `
                        <div class="pd-field group" data-key="${lockKey}">
                            <div class="flex items-center justify-between mb-1">
                                <label class="text-[10px] text-brand-text-muted uppercase tracking-wide font-medium">${_fieldLabel(field)}</label>
                                <button class="pd-lock text-[10px] px-2 py-0.5 rounded-full transition-all ${
                                    isLocked
                                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                        : 'bg-white/5 text-brand-text-muted/50 border border-transparent hover:border-brand-border'
                                }" data-lock="${lockKey}" title="${isLocked ? 'Locked — click to unlock' : 'Unlocked — click to lock'}">
                                    ${isLocked ? '🔒 Locked' : '🔓 Editable'}
                                </button>
                            </div>
                            <textarea class="pd-input w-full rounded-md px-3 py-2 text-xs resize-none focus:outline-none transition-all ${
                                isLocked
                                    ? 'bg-amber-950/10 border border-amber-500/20 text-brand-text/50 cursor-not-allowed'
                                    : 'bg-black/20 border border-brand-border/50 text-brand-text focus:border-brand-accent/50'
                            }" rows="${value.length > 150 ? 3 : 2}"
                                data-section="${tab.key}" data-field="${field}"
                                ${isLocked ? 'readonly' : ''}>${value}</textarea>
                        </div>`;
                }

                // Color palette (in Style tab)
                let colorHtml = '';
                if (tab.key === 'style') {
                    const palette = d.style?.color_palette || [];
                    if (palette.length) {
                        colorHtml = `
                            <div class="mt-3">
                                <label class="text-[10px] text-brand-text-muted uppercase tracking-wide font-medium block mb-2">Color Palette</label>
                                <div class="grid grid-cols-2 gap-2">`;
                        for (const color of palette) {
                            colorHtml += `
                                <div class="flex items-center gap-2.5 bg-black/20 rounded-lg px-3 py-2.5 border border-brand-border/30">
                                    <div class="w-10 h-10 rounded-lg border-2 border-white/10 flex-shrink-0 shadow-inner" style="background-color: ${color.hex}"></div>
                                    <div class="min-w-0">
                                        <div class="text-xs font-medium text-brand-text">${color.name}</div>
                                        <div class="text-[10px] text-brand-text-muted font-mono">${color.hex}</div>
                                        <div class="text-[9px] text-brand-text-muted/60 truncate">${color.usage || ''}</div>
                                    </div>
                                </div>`;
                        }
                        colorHtml += '</div></div>';
                    }
                }

                tabContent += `<div class="pd-tab-content p-4 space-y-3 ${isActive ? '' : 'hidden'}" data-tab-content="${tab.key}">
                    ${fields}${colorHtml}
                </div>`;
            }

            // Action bar
            const actionBar = `
                <div class="flex items-center justify-between px-5 py-3 border-t border-brand-border bg-black/10">
                    <p class="text-[10px] text-brand-text-muted/50">Lock fields to keep them fixed when regenerating</p>
                    <div class="flex gap-2">
                        <button class="pd-cancel text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">Cancel</button>
                        <button class="pd-save text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">Save &amp; Continue</button>
                    </div>
                </div>`;

            const body = this._modal?.querySelector('.pd-body');
            if (body) body.innerHTML = tabBar + tabContent + actionBar;

            // Attach events
            this._modal?.querySelectorAll('.pd-tab').forEach(btn => {
                btn.addEventListener('click', () => {
                    this._activeTab = btn.dataset.tab;
                    // Toggle tabs
                    this._modal.querySelectorAll('.pd-tab').forEach(t => {
                        const active = t.dataset.tab === this._activeTab;
                        t.classList.toggle('text-brand-accent', active);
                        t.classList.toggle('border-brand-accent', active);
                        t.classList.toggle('bg-brand-accent/5', active);
                        t.classList.toggle('text-brand-text-muted', !active);
                        t.classList.toggle('border-transparent', !active);
                    });
                    this._modal.querySelectorAll('.pd-tab-content').forEach(c => {
                        c.classList.toggle('hidden', c.dataset.tabContent !== this._activeTab);
                    });
                });
            });

            this._modal?.querySelectorAll('.pd-lock').forEach(btn => {
                btn.addEventListener('click', () => {
                    const key = btn.dataset.lock;
                    this._locks[key] = !this._locks[key];
                    const locked = this._locks[key];
                    btn.innerHTML = locked ? '🔒 Locked' : '🔓 Editable';
                    btn.title = locked ? 'Locked — click to unlock' : 'Unlocked — click to lock';
                    btn.className = `pd-lock text-[10px] px-2 py-0.5 rounded-full transition-all ${
                        locked
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-white/5 text-brand-text-muted/50 border border-transparent hover:border-brand-border'
                    }`;
                    // Update textarea
                    const field = this._modal.querySelector(`.pd-field[data-key="${key}"] .pd-input`);
                    if (field) {
                        field.readOnly = locked;
                        field.className = `pd-input w-full rounded-md px-3 py-2 text-xs resize-none focus:outline-none transition-all ${
                            locked
                                ? 'bg-amber-950/10 border border-amber-500/20 text-brand-text/50 cursor-not-allowed'
                                : 'bg-black/20 border border-brand-border/50 text-brand-text focus:border-brand-accent/50'
                        }`;
                    }
                });
            });

            this._modal?.querySelectorAll('.pd-input').forEach(input => {
                input.addEventListener('input', () => {
                    const section = input.dataset.section;
                    const field = input.dataset.field;
                    if (this._data[section]) this._data[section][field] = input.value;
                });
            });

            this._modal?.querySelector('.pd-save')?.addEventListener('click', () => this._save());
            this._modal?.querySelector('.pd-cancel')?.addEventListener('click', () => this.close());
        },

        _save() {
            if (this._onApply) {
                this._onApply(this._data);
            }
            this.close();
            window.showToast?.('Designer saved — composing enhanced prompt...', 'success');
        },
    };
})();
