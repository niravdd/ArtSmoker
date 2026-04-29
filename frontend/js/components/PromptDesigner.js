/**
 * ArtSmoker — Prompt Designer Modal
 *
 * Decomposes a user prompt into structured visual components using an LLM,
 * displays them in a tabbed interface with color swatches and lock/unlock per field.
 * "Generate Enhanced Prompt" stores the data and triggers enhanced prompt composition.
 */
(function () {
    'use strict';

    const _t = (key) => typeof t !== 'undefined' ? t(key) : key.split('.').pop();

    const TABS = [
        { key: 'subject', labelKey: 'prompt_designer.tab_subject', icon: '👤', fields: ['description', 'clothing', 'accessories', 'expression_pose', 'details'] },
        { key: 'scene', labelKey: 'prompt_designer.tab_scene', icon: '🏔', fields: ['setting', 'background', 'props', 'time_of_day'] },
        { key: 'composition', labelKey: 'prompt_designer.tab_composition', icon: '📐', fields: ['camera_angle', 'framing', 'depth_of_field'] },
        { key: 'lighting', labelKey: 'prompt_designer.tab_lighting', icon: '💡', fields: ['key_light', 'fill_rim', 'mood'] },
        { key: 'style', labelKey: 'prompt_designer.tab_style', icon: '🎨', fields: ['art_style', 'quality'] },
    ];

    function _fieldLabel(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    // Asset types list — must match backend AssetType enum and ImageStudio's ASSET_TYPES
    const ASSET_TYPES = [
        { value: 'game_asset', labelKey: 'image_studio.asset_type_game' },
        { value: 'marketing_banner', labelKey: 'image_studio.asset_type_banner' },
        { value: 'icon', labelKey: 'image_studio.asset_type_icon' },
        { value: 'character', labelKey: 'image_studio.asset_type_character' },
        { value: 'environment', labelKey: 'image_studio.asset_type_environment' },
        { value: 'photorealistic', labelKey: 'image_studio.asset_type_photo' },
    ];

    window.PromptDesigner = {
        _modal: null,
        _data: null,
        _onApply: null,
        _activeTab: 'subject',
        _stylesList: null,  // cached styles from API

        /**
         * Open the Prompt Designer modal.
         * @param {string} prompt - User's original prompt
         * @param {object} opts - { styleId, assetType, imageModel, onApply(designerData) }
         */
        async open(prompt, opts = {}) {
            this._onApply = opts.onApply || null;
            this._onPromptSet = opts.onPromptSet || null;
            this._opts = opts;

            // Pre-fetch styles for the selector row (non-blocking cache)
            this._fetchStyles();

            const newPrompt = (prompt || '').trim();

            // If we have saved data and the prompt hasn't changed, restore it
            if (this._data && this._originalPrompt === newPrompt) {
                this._showModal('');
                this._renderDesigner();
                return;
            }

            // If caller provides saved decomposition data (e.g., from Gallery reload), restore it
            if (opts.decomposedData && typeof opts.decomposedData === 'object') {
                this._originalPrompt = newPrompt;
                this._activeTab = 'subject';
                this._data = opts.decomposedData;
                this._varyFlags = opts.varyFlags || this._initVaryFlags(opts.decomposedData);
                this._showModal('');
                this._renderDesigner();
                return;
            }

            // Gallery reload with no decomposed data — don't re-analyze
            if (opts.galleryReload && !opts.decomposedData) {
                this._showModal(`
                    <div class="text-center py-12">
                        <p class="text-sm text-brand-text-muted">${_t('prompt_designer.no_decomposed_data')}</p>
                        <p class="text-[10px] text-brand-text-muted/50 mt-2">${_t('prompt_designer.no_decomposed_data_sub')}</p>
                    </div>`);
                return;
            }

            this._activeTab = 'subject';
            this._originalPrompt = newPrompt;

            if (this._originalPrompt) {
                // Has prompt → decompose immediately
                this._showModal(`
                    <div class="text-center py-12">
                        <div class="text-3xl mb-3" style="display:inline-block;animation:spin 2s linear infinite">⏳</div>
                        <style>@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style>
                        <p class="text-sm text-brand-text-muted">${_t('prompt_designer.analyzing')}</p>
                        <p class="text-[10px] text-brand-text-muted/50 mt-1">${_t('prompt_designer.analyzing_sub')}</p>
                    </div>`);
                await this._decompose(this._originalPrompt);
            } else {
                // No prompt → show input form first
                this._showModal('');
                this._renderInputForm();
            }
        },

        _renderInputForm() {
            const body = this._modal?.querySelector('.pd-body');
            if (!body) return;

            const assetType = this._opts?.assetType || 'game_asset';
            const curStyleId = this._opts?.styleId || '';
            const assetOptions = ASSET_TYPES.map(a =>
                `<option value="${a.value}" ${a.value === assetType ? 'selected' : ''}>${_t(a.labelKey)}</option>`
            ).join('');
            const styles = this._stylesList || [];
            const styleOptions = [`<option value="">${_t('image_studio.style_none') || 'None (standalone mode)'}</option>`]
                .concat(styles.map(s => `<option value="${s.id}" ${s.id === curStyleId ? 'selected' : ''}>${s.name}</option>`))
                .join('');

            body.innerHTML = `
                <div class="px-5 py-4 space-y-4">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1.5">Asset Type</label>
                            <select id="pd-asset-type" class="input text-xs w-full">${assetOptions}</select>
                        </div>
                        <div>
                            <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1.5">Art Style</label>
                            <select id="pd-style" class="input text-xs w-full">${styleOptions}</select>
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs text-brand-text-muted uppercase tracking-wider mb-1.5">Describe your idea</label>
                        <textarea id="pd-prompt-input" class="input w-full text-sm" rows="3" placeholder="e.g. A fierce tiger, a cozy cabin in the woods, a futuristic spaceship..." autofocus></textarea>
                    </div>
                    <button id="pd-decompose-btn" class="w-full py-2.5 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white text-sm font-medium transition-colors">
                        🎨 Decompose & Design
                    </button>
                </div>
                <div class="px-5 pb-4">
                    <p class="text-[10px] text-brand-text-muted/40 text-center">The AI will break down your idea into editable components: subject, scene, composition, lighting, and style.</p>
                </div>
                <div class="flex border-b border-brand-border opacity-30 pointer-events-none">
                    ${TABS.map(tab => `<div class="flex-1 py-2.5 text-[11px] font-medium text-brand-text-muted/30 text-center">
                        <span class="block">${tab.icon}</span>
                        <span class="block mt-0.5">${_t(tab.labelKey)}</span>
                    </div>`).join('')}
                </div>
                <div class="px-5 py-8 text-center text-brand-text-muted/20 text-xs">
                    Enter a prompt above to populate these fields
                </div>
                <div class="flex items-center justify-end px-5 py-3 border-t border-brand-border bg-black/10">
                    <button class="pd-cancel text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${_t('prompt_designer.cancel')}</button>
                </div>`;

            body.querySelector('#pd-decompose-btn')?.addEventListener('click', async () => {
                const prompt = body.querySelector('#pd-prompt-input')?.value.trim();
                if (!prompt) { window.showToast?.('Enter a prompt first', 'warning'); return; }

                this._originalPrompt = prompt;

                // Update asset type and style from dropdowns
                const selectedAsset = body.querySelector('#pd-asset-type')?.value;
                if (selectedAsset && this._opts) {
                    this._opts.assetType = selectedAsset;
                    if (this._opts.onAssetTypeChange) this._opts.onAssetTypeChange(selectedAsset);
                }
                const selectedStyle = body.querySelector('#pd-style')?.value;
                if (this._opts) this._opts.styleId = selectedStyle || '';

                // Show loading in the decompose button
                const btn = body.querySelector('#pd-decompose-btn');
                if (btn) { btn.disabled = true; btn.textContent = '⏳ Analyzing...'; }

                await this._decompose(prompt);
            });

            // Also allow Enter key in textarea to trigger decompose
            body.querySelector('#pd-prompt-input')?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    body.querySelector('#pd-decompose-btn')?.click();
                }
            });

            body.querySelector('.pd-cancel')?.addEventListener('click', () => this.close());
            body.querySelector('#pd-prompt-input')?.focus();
        },

        async _decompose(prompt) {
            try {
                const resp = await fetch('/api/refine-prompt/decompose', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: prompt,
                        style_id: this._opts?.styleId || undefined,
                        asset_type: this._opts?.assetType || 'character',
                        image_model: this._opts?.imageModel || '',
                    }),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                this._data = await resp.json();
                this._varyFlags = this._initVaryFlags(this._data);

                // Notify the editor that a prompt was set (populates Step 1)
                if (this._onPromptSet) this._onPromptSet(prompt);

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

        async _redecompose() {
            if (!this._originalPrompt) return;
            // Show loading spinner in the content area
            const body = this._modal?.querySelector('.pd-body');
            if (body) {
                body.innerHTML = `
                    <div class="text-center py-12">
                        <div class="text-3xl mb-3" style="display:inline-block;animation:spin 2s linear infinite">⏳</div>
                        <style>@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style>
                        <p class="text-sm text-brand-text-muted">${_t('prompt_designer.analyzing')}</p>
                        <p class="text-[10px] text-brand-text-muted/50 mt-1">Updating with new settings...</p>
                    </div>`;
            }
            // Reset vary flags so new decomposition gets fresh source-based flags
            this._varyFlags = null;
            await this._decompose(this._originalPrompt);
        },

        close() {
            if (this._modal) {
                this._modal.remove();
                this._modal = null;
            }
        },

        /** Clear all saved state (called on view reset). */
        reset() {
            this.close();
            this._data = null;
            this._originalPrompt = null;
            this._activeTab = 'subject';
        },

        _showModal(innerHtml) {
            if (this._modal) this._modal.remove();
            this._modal = document.createElement('div');
            this._modal.className = 'fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto';
            this._modal.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl w-full max-w-3xl h-[80vh] flex flex-col overflow-hidden">
                    <div class="flex items-center justify-between px-5 py-3 border-b border-brand-border">
                        <h2 class="text-sm font-semibold text-brand-text flex items-center gap-2">
                            <span class="text-lg">🎨</span> ${_t('prompt_designer.title')}
                        </h2>
                        <button class="pd-close text-brand-text-muted hover:text-brand-text text-lg leading-none">&times;</button>
                    </div>
                    <div class="pd-body flex-1 overflow-y-auto">${innerHtml}</div>
                </div>`;
            this._modal.querySelector('.pd-close')?.addEventListener('click', () => this.close());
            this._modal.addEventListener('click', (e) => { if (e.target === this._modal) this.close(); });
            document.body.appendChild(this._modal);
        },

        _renderDesigner() {
            const d = this._data;
            if (!d) return;

            // Translation banner (if prompt was non-English)
            let translationBanner = '';
            const meta = d._meta || {};
            if (meta.was_translated) {
                const langNames = { ja: '日本語', zh: '中文', ko: '한국어', fr: 'Français', es: 'Español' };
                const langName = langNames[meta.original_language] || meta.original_language;
                translationBanner = `
                    <div class="mx-5 mt-4 p-3 rounded-lg bg-brand-accent/5 border border-brand-accent/20 space-y-1.5">
                        <div class="flex items-center gap-2">
                            <span class="text-[9px] px-1.5 py-0.5 rounded bg-brand-accent/15 text-brand-accent font-medium">${langName} → English</span>
                            <span class="text-[10px] text-brand-text-muted">${_t('prompt_designer.translated_notice') || 'Your prompt was translated to English for the designer.'}</span>
                        </div>
                        <p class="text-[10px] text-brand-text-muted/70 italic">${meta.original_prompt}</p>
                        <p class="text-[10px] text-brand-text/80">${meta.english_prompt}</p>
                    </div>`;
            }

            // Tab bar
            let tabBar = '<div class="flex border-b border-brand-border">';
            for (const tab of TABS) {
                const active = tab.key === this._activeTab;
                const count = (d[tab.key] ? Object.values(d[tab.key]).filter(v => {
                    if (v && typeof v === 'object' && v.value) return v.value.length > 0;
                    return v && typeof v === 'string' && v.length > 0;
                }).length : 0);
                tabBar += `<button class="pd-tab flex-1 py-2.5 text-[11px] font-medium transition-all border-b-2 ${
                    active
                        ? 'text-brand-accent border-brand-accent bg-brand-accent/5'
                        : 'text-brand-text-muted border-transparent hover:text-brand-text hover:bg-white/3'
                }" data-tab="${tab.key}">
                    <span class="block">${tab.icon}</span>
                    <span class="block mt-0.5">${_t(tab.labelKey)}</span>
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
                    const raw = sectionData[field] || '';
                    const value = (raw && typeof raw === 'object' && raw.value) ? raw.value : (typeof raw === 'string' ? raw : '');
                    if (!value) continue;
                    const flagKey = `${tab.key}.${field}`;
                    const isLocked = (this._varyFlags || {})[flagKey] === 'lock';
                    const toggleLabel = isLocked ? '🔒 Fixed' : '🎲 Randomise';
                    const toggleTitle = isLocked
                        ? 'This element stays the same across all options. Click to allow variation.'
                        : 'This element will be different in each option. Click to keep it fixed.';
                    const toggleBg = isLocked ? 'bg-amber-500/15 text-amber-400' : 'bg-brand-accent/10 text-brand-accent';
                    fields += `
                        <div class="pd-field group">
                            <div class="flex items-center justify-between mb-1">
                                <label class="text-[10px] text-brand-text-muted uppercase tracking-wide font-medium">${_fieldLabel(field)}</label>
                                <button class="pd-vary-toggle text-[9px] px-2 py-0.5 rounded-full font-medium transition-all hover:brightness-125 ${toggleBg}"
                                    data-flag-key="${flagKey}" title="${toggleTitle}">${toggleLabel}</button>
                            </div>
                            <textarea class="pd-input w-full rounded-md px-3 py-2 text-xs resize-none focus:outline-none transition-all
                                bg-black/20 border border-brand-border/50 text-brand-text focus:border-brand-accent/50
                                ${isLocked ? 'border-l-2 border-l-amber-500/50' : 'border-l-2 border-l-brand-accent/30'}"
                                rows="${value.length > 150 ? 3 : 2}"
                                data-section="${tab.key}" data-field="${field}">${value}</textarea>
                        </div>`;
                }

                // Color palette (in Style tab)
                let colorHtml = '';
                if (tab.key === 'style') {
                    const palette = d.style?.color_palette || [];
                    if (palette.length) {
                        colorHtml = `
                            <div class="mt-3">
                                <label class="text-[10px] text-brand-text-muted uppercase tracking-wide font-medium block mb-2">${_t('prompt_designer.color_palette')}</label>
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

            // Original prompt (always visible at top of content)
            const originalPromptBar = this._originalPrompt ? `
                <div class="mx-5 mt-3 mb-1">
                    <label class="block text-[9px] text-brand-text-muted uppercase tracking-wider mb-1">Original Prompt</label>
                    <p class="text-[11px] text-brand-text/70 italic bg-black/10 rounded-lg px-3 py-2 line-clamp-2">${this._esc(this._originalPrompt)}</p>
                </div>` : '';

            // Asset Type + Art Style selector row
            const curAssetType = this._opts?.assetType || 'game_asset';
            const curStyleId = this._opts?.styleId || '';
            const assetOptions = ASSET_TYPES.map(a =>
                `<option value="${a.value}" ${a.value === curAssetType ? 'selected' : ''}>${_t(a.labelKey)}</option>`
            ).join('');
            const styles = this._stylesList || [];
            const styleOptions = [`<option value="">${_t('image_studio.style_none') || 'None (standalone mode)'}</option>`]
                .concat(styles.map(s => `<option value="${s.id}" ${s.id === curStyleId ? 'selected' : ''}>${s.name}</option>`))
                .join('');
            const selectorRow = `
                <div class="mx-5 mt-2 mb-1 flex items-center gap-3">
                    <div class="flex items-center gap-1.5 min-w-0">
                        <label class="text-[9px] text-brand-text-muted uppercase tracking-wider whitespace-nowrap">Type</label>
                        <select id="pd-asset-type-sel" class="text-[11px] bg-black/20 border border-brand-border/50 rounded px-2 py-1 text-brand-text focus:border-brand-accent/50 focus:outline-none">${assetOptions}</select>
                    </div>
                    <div class="flex items-center gap-1.5 min-w-0 flex-1">
                        <label class="text-[9px] text-brand-text-muted uppercase tracking-wider whitespace-nowrap">Style</label>
                        <select id="pd-style-sel" class="text-[11px] bg-black/20 border border-brand-border/50 rounded px-2 py-1 text-brand-text focus:border-brand-accent/50 focus:outline-none truncate w-full">${styleOptions}</select>
                    </div>
                </div>`;

            // Live preview (constructed from current fields — no LLM, instant)
            const previewBar = `
                <div class="mx-5 mb-2">
                    <div class="flex items-center justify-between mb-1">
                        <label class="text-[9px] text-brand-text-muted uppercase tracking-wider">Prompt Preview <span class="text-brand-text-muted/40">(constructed from fields above)</span></label>
                        <span id="pd-preview-stats" class="text-[9px] text-brand-text-muted/40 font-mono"></span>
                    </div>
                    <p id="pd-live-preview" class="text-[10px] text-brand-text/60 bg-black/10 rounded-lg px-3 py-2.5 max-h-32 overflow-y-auto font-mono leading-relaxed"></p>
                </div>`;

            // Action bar
            const actionBar = `
                <div class="flex items-center justify-end px-5 py-3 border-t border-brand-border bg-black/10 gap-2">
                    <button class="pd-cancel text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${_t('prompt_designer.cancel')}</button>
                    <button class="pd-save text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">${_t('prompt_designer.save_continue')}</button>
                </div>`;

            // Info footer explaining lock/vary — below buttons, visible on every tab
            const infoFooter = `
                <div class="px-5 py-2.5 bg-black/5">
                    <p class="text-[10.5px] text-brand-text-muted/80 leading-loose">
                        <span class="text-brand-accent font-medium">🎲 Randomise</span> <span class="text-brand-text-muted/50">(default)</span> — each generated option gets a different creative take on this element.<br>
                        <span class="text-amber-400 font-medium">🔒 Fixed</span> — this element stays identical across all options.<br>
                        Edit any field freely and choose whether it should be randomised or fixed. With a single option (1×1), all fields are used as-is.
                    </p>
                </div>`;

            const body = this._modal?.querySelector('.pd-body');
            if (body) body.innerHTML = originalPromptBar + selectorRow + translationBanner + tabBar + tabContent + previewBar + actionBar + infoFooter;

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

            this._modal?.querySelectorAll('.pd-input').forEach(input => {
                input.addEventListener('input', () => {
                    const section = input.dataset.section;
                    const field = input.dataset.field;
                    if (this._data[section]) this._data[section][field] = input.value;
                });
            });

            this._modal?.querySelector('.pd-save')?.addEventListener('click', () => this._save());
            this._modal?.querySelector('.pd-cancel')?.addEventListener('click', () => this.close());

            // Lock/vary toggle handlers
            this._modal?.querySelectorAll('.pd-vary-toggle').forEach(btn => {
                btn.addEventListener('click', () => {
                    const key = btn.dataset.flagKey;
                    if (!this._varyFlags) this._varyFlags = {};
                    const current = this._varyFlags[key] || 'vary';
                    const next = current === 'lock' ? 'vary' : 'lock';
                    this._varyFlags[key] = next;
                    btn.innerHTML = next === 'lock' ? '🔒 Fixed' : '🎲 Randomise';
                    btn.title = next === 'lock'
                        ? 'This element stays the same across all options. Click to allow variation.'
                        : 'This element will be different in each option. Click to keep it fixed.';
                    btn.className = btn.className.replace(/bg-\S+\s*text-\S+/g, '');
                    btn.classList.add(
                        ...(next === 'lock'
                            ? ['bg-amber-500/15', 'text-amber-400']
                            : ['bg-brand-accent/10', 'text-brand-accent'])
                    );
                    const textarea = btn.closest('.pd-field')?.querySelector('.pd-input');
                    if (textarea) {
                        textarea.classList.toggle('border-l-amber-500/50', next === 'lock');
                        textarea.classList.toggle('border-l-brand-accent/30', next === 'vary');
                    }
                });
            });

            // Asset Type / Style selector change → re-decompose
            this._modal?.querySelector('#pd-asset-type-sel')?.addEventListener('change', (e) => {
                if (this._opts) this._opts.assetType = e.target.value;
                this._redecompose();
            });
            this._modal?.querySelector('#pd-style-sel')?.addEventListener('change', (e) => {
                if (this._opts) this._opts.styleId = e.target.value;
                this._redecompose();
            });

            // Live preview: update on any field change
            this._modal?.querySelectorAll('.pd-input').forEach(input => {
                input.addEventListener('input', () => {
                    const field = input.closest('.pd-field');
                    if (field) {
                        const tab = field.closest('[data-tab-content]')?.dataset.tabContent;
                        const key = field.dataset.key;
                        if (tab && key && this._data[tab]) {
                            this._data[tab][key] = input.value;
                        }
                    }
                    this._updateLivePreview();
                });
            });
            // Initial preview render
            this._updateLivePreview();
        },

        _save() {
            if (this._onApply) {
                this._onApply(this._data, this._varyFlags, {
                    assetType: this._opts?.assetType,
                    styleId: this._opts?.styleId,
                });
            }
            this.close();
            window.showToast?.(_t('prompt_designer.saved'), 'success');
        },

        _initVaryFlags(data) {
            const flags = {};
            if (!data) return flags;
            for (const [section, fields] of Object.entries(data)) {
                if (!fields || typeof fields !== 'object' || Array.isArray(fields)) continue;
                for (const [field, val] of Object.entries(fields)) {
                    if (Array.isArray(val)) continue;
                    const source = (val && typeof val === 'object' && val.source) ? val.source : 'inferred';
                    flags[`${section}.${field}`] = source === 'user' ? 'lock' : 'vary';
                }
            }
            return flags;
        },

        async _fetchStyles() {
            if (this._stylesList) return this._stylesList;
            try {
                const data = await (typeof API !== 'undefined' ? API.styles.list() : fetch('/api/styles/').then(r => r.json()));
                this._stylesList = Array.isArray(data) ? data : [];
            } catch { this._stylesList = []; }
            return this._stylesList;
        },

        _esc(str) {
            const d = document.createElement('div');
            d.textContent = str || '';
            return d.innerHTML;
        },

        _updateLivePreview() {
            const el = this._modal?.querySelector('#pd-live-preview');
            const statsEl = this._modal?.querySelector('#pd-preview-stats');
            if (!el || !this._data) return;

            // Construct prompt from current field values (no LLM — instant)
            const parts = [];
            for (const tab of TABS) {
                const section = this._data[tab.key];
                if (!section || typeof section !== 'object') continue;
                for (const [key, val] of Object.entries(section)) {
                    if (key === 'colors' || key === 'palette' || key === 'color_palette') continue;
                    const text = (val && typeof val === 'object' && val.value) ? val.value : (typeof val === 'string' ? val : '');
                    if (text.trim()) parts.push(text.trim());
                }
            }
            // Add color palette if present
            const colors = this._data?.style?.color_palette || this._data?.style?.colors || this._data?.style?.palette;
            if (Array.isArray(colors) && colors.length > 0) {
                const colorStr = colors.map(c => typeof c === 'object' ? `${c.name || c.hex || ''}` : c).filter(Boolean).join(', ');
                if (colorStr) parts.push(`Color palette: ${colorStr}`);
            }
            const text = parts.join('. ') + '.';
            el.textContent = text;

            // Show character and word count
            if (statsEl) {
                const chars = text.length;
                const words = text.trim().split(/\s+/).filter(Boolean).length;
                statsEl.textContent = `${chars} chars · ${words} words`;
            }
        },
    };
})();
