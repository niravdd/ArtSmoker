/**
 * ArtSmoker — Model Settings Component
 *
 * Admin modal for managing AI model configurations.
 * Three tabs: Image Models, LLM & Post-Processing, Raw Registry JSON.
 * Refresh All button discovers models, pricing, and regions from AWS.
 */
(function () {
    'use strict';

    window.ModelSettings = {
        _registry: null,
        _refreshing: false,

        async open() {
            document.getElementById('model-settings-modal')?.remove();
            window.showLoading?.('Loading model settings...');

            try {
                this._registry = await API.admin.getModels();
                window.hideLoading?.();
                this._renderModal();
            } catch (err) {
                window.hideLoading?.();
                window.showToast?.('Failed to load model settings: ' + (err.message || ''), 'error');
            }
        },

        _renderModal() {
            const reg = this._registry;
            if (!reg) return;

            const lastUpdated = reg.last_updated
                ? new Date(reg.last_updated).toLocaleString()
                : 'never';

            const modal = document.createElement('div');
            modal.id = 'model-settings-modal';
            modal.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                        <div class="flex items-center gap-3">
                            <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            </svg>
                            <h2 class="text-lg font-semibold">Model Settings</h2>
                        </div>
                        <div class="flex items-center gap-3">
                            <button id="ms-refresh-all" class="btn btn-sm text-xs bg-amber-600 hover:bg-amber-500 text-white" title="Scans all AWS regions for models, fetches pricing. Makes multiple API calls — run only when needed.">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                                Sync from AWS
                            </button>
                            <span class="text-[10px] text-brand-text-muted" title="Run only when AWS adds new models or you need updated pricing">Updated: ${lastUpdated}</span>
                            <button class="ms-close p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Tabs -->
                    <div class="tab-bar px-6 pt-3">
                        <button class="tab active" data-ms-tab="image-models">Image Models</button>
                        <button class="tab" data-ms-tab="llm-post">LLM & Post-Processing</button>
                        <button class="tab" data-ms-tab="registry-json">Registry JSON</button>
                    </div>

                    <!-- Tab content -->
                    <div class="flex-1 overflow-auto p-6">

                        <!-- Tab 1: Image Models -->
                        <div class="ms-tab-panel" data-ms-panel="image-models">
                            <div id="ms-image-models" class="space-y-3">
                                ${this._renderImageModels(reg)}
                            </div>
                        </div>

                        <!-- Tab 2: LLM & Post-Processing -->
                        <div class="ms-tab-panel hidden" data-ms-panel="llm-post">
                            <div class="space-y-6">
                                <div>
                                    <h3 class="text-sm font-semibold text-brand-accent uppercase tracking-wider mb-3">AI / LLM Models</h3>
                                    <div class="space-y-3">
                                        ${Object.entries(reg.categories || {}).map(([name, cat]) => this._renderCategory(name, cat)).join('')}
                                    </div>
                                </div>
                                <div>
                                    <h3 class="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3">Post-Processing</h3>
                                    <div class="space-y-3">
                                        ${Object.entries(reg.post_processing || {}).map(([key, m]) => this._renderPostProcess(key, m)).join('')}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Tab 3: Raw Registry JSON -->
                        <div class="ms-tab-panel hidden" data-ms-panel="registry-json">
                            <p class="text-xs text-brand-text-muted mb-2">Raw model_registry.json — edit carefully. Invalid JSON will be rejected.</p>
                            <textarea id="ms-json-editor" class="w-full h-[50vh] font-mono text-xs p-3 rounded-lg bg-brand-bg border border-brand-border text-brand-text resize-none" spellcheck="false">${this._esc(JSON.stringify(reg, null, 2))}</textarea>
                            <div class="flex items-center gap-2 mt-2">
                                <button id="ms-json-save" class="btn btn-primary btn-sm text-xs">Save JSON</button>
                                <button id="ms-json-reset" class="btn btn-secondary btn-sm text-xs">Reset</button>
                                <span id="ms-json-status" class="text-[10px] text-brand-text-muted"></span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            this._attachEvents(modal);
        },

        _renderImageModels(reg) {
            const models = reg.image_models || {};
            if (Object.keys(models).length === 0) {
                return '<p class="text-sm text-brand-text-muted py-4 text-center">No image models in registry. Click "Sync from AWS" to discover available models.</p>';
            }

            // Group models by purpose
            const groups = {};
            const PURPOSE_LABELS = {
                'text_to_image': 'Image Generation',
                'inpainting': 'Image Editing — Inpainting',
                'outpainting': 'Image Editing — Outpainting',
                'erase': 'Image Editing — Erase',
                'search_replace': 'Image Editing — Search & Replace',
                'search_recolor': 'Image Editing — Search & Recolor',
                'control_sketch': 'Image Control — Sketch',
                'control_structure': 'Image Control — Structure',
                'style_guide': 'Style — Guide',
                'style_transfer': 'Style — Transfer',
                'remove_background': 'Post-Processing — Remove Background',
                'upscale_creative': 'Post-Processing — Creative Upscale',
                'upscale_conservative': 'Post-Processing — Conservative Upscale',
                'upscale_fast': 'Post-Processing — Fast Upscale',
            };
            const PURPOSE_ORDER = Object.keys(PURPOSE_LABELS);

            for (const [key, m] of Object.entries(models)) {
                const purpose = m.model_purpose || 'other';
                if (!groups[purpose]) groups[purpose] = [];
                groups[purpose].push([key, m]);
            }

            // Render grouped
            const sortedPurposes = Object.keys(groups).sort((a, b) => {
                const ai = PURPOSE_ORDER.indexOf(a);
                const bi = PURPOSE_ORDER.indexOf(b);
                return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
            });

            return sortedPurposes.map(purpose => {
                const label = PURPOSE_LABELS[purpose] || purpose;
                const entries = groups[purpose];
                const isEditing = purpose !== 'text_to_image' && !purpose.startsWith('upscale') && purpose !== 'remove_background';
                return `
                    <div class="mb-4">
                        <h4 class="text-xs font-semibold ${isEditing ? 'text-emerald-400' : 'text-brand-accent'} uppercase tracking-wider mb-2 flex items-center gap-2">
                            ${label}
                            <span class="text-[10px] font-normal text-brand-text-muted">(${entries.length})</span>
                        </h4>
                        <div class="space-y-2">
                            ${entries.map(([key, m]) => this._renderSingleModel(key, m)).join('')}
                        </div>
                    </div>
                `;
            }).join('');
        },

        _renderSingleModel(key, m) {
            return (() => {
                const regions = (m.available_regions || [m.region]).join(', ');
                const quality = (m.quality_options || []).map(q => q.label).join(' / ') || 'No tiers';
                const price = m.base_price_usd != null ? `$${m.base_price_usd.toFixed(2)}/img` : 'unknown';
                const strictColor = m.moderation_strictness === 'very_strict' ? 'text-red-400' : m.moderation_strictness === 'strict' ? 'text-amber-400' : 'text-emerald-400';

                return `
                    <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${m.enabled ? '' : 'opacity-50'}" data-image-model="${key}">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center gap-2">
                                <label class="toggle toggle-sm">
                                    <input type="checkbox" class="ms-img-toggle" data-key="${key}" ${m.enabled ? 'checked' : ''} />
                                    <span class="toggle-slider"></span>
                                </label>
                                <span class="text-sm font-medium">${this._esc(m.label || key)}</span>
                                <span class="text-[10px] text-brand-text-muted">${this._esc(m.provider || '')}</span>
                            </div>
                            <span class="${strictColor} text-[10px]">${m.moderation_strictness || ''}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-brand-text-muted mb-2">
                            <span>Model ID: <span class="font-mono text-brand-text/70">${this._esc(m.model_id || '')}</span></span>
                            <span>Format: <span class="text-brand-text/70">${this._esc(m.format_family || '')}</span></span>
                            <span>Regions: <span class="text-brand-text/70">${regions || 'none'}</span></span>
                            <span>Prompt limit: <span class="text-brand-text/70">${m.prompt_limit || '?'} chars</span></span>
                            <span>Quality: <span class="text-brand-text/70">${quality}</span></span>
                            <span>Price: <span class="text-emerald-400/70">${price}</span></span>
                        </div>
                        <details class="group">
                            <summary class="text-[10px] text-brand-accent cursor-pointer hover:text-brand-accent-hover">
                                <span class="group-open:hidden">Edit</span>
                                <span class="hidden group-open:inline">Close editor</span>
                            </summary>
                            <div class="mt-2 space-y-2 p-2 rounded bg-brand-bg/60 border border-brand-border/50">
                                <div class="grid grid-cols-2 gap-2">
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">Model ID</label>
                                        <input type="text" class="ms-edit-field input text-xs font-mono w-full" data-key="${key}" data-field="model_id" value="${this._esc(m.model_id || '')}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">Label</label>
                                        <input type="text" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="label" value="${this._esc(m.label || '')}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">Prompt Limit</label>
                                        <input type="number" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="prompt_limit" value="${m.prompt_limit || 900}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">Base Price ($/img)</label>
                                        <input type="number" step="0.01" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="base_price_usd" value="${m.base_price_usd || ''}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">Moderation</label>
                                        <select class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="moderation_strictness">
                                            ${['moderate', 'strict', 'very_strict'].map(s => `<option value="${s}" ${s === m.moderation_strictness ? 'selected' : ''}>${s}</option>`).join('')}
                                        </select>
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">Default Region</label>
                                        <input type="text" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="region" value="${this._esc(m.region || '')}" />
                                    </div>
                                </div>
                                <button class="ms-edit-save btn btn-primary btn-sm text-xs" data-key="${key}">Save Changes</button>
                            </div>
                        </details>
                    </div>
                `;
            }).join('');
        },

        _renderCategory(name, cat) {
            if (!cat) return '';
            return `
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border" data-category="${name}">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm font-medium">${this._esc(cat.label || name)}</span>
                        <span class="text-[10px] text-brand-text-muted font-mono bg-brand-bg px-2 py-0.5 rounded">${this._esc(cat.region || '')}</span>
                    </div>
                    <p class="text-[10px] text-brand-text-muted/50 mb-2">${this._esc(cat.description || '')}</p>
                    <div class="flex gap-2">
                        <input type="text" class="ms-cat-model input text-xs flex-1 font-mono" value="${this._esc(cat.current || '')}" data-cat="${name}" placeholder="Model ID" />
                        <input type="text" class="ms-cat-region input text-xs w-28" value="${this._esc(cat.region || '')}" data-cat="${name}" placeholder="Region" />
                        <button class="ms-cat-save btn btn-primary btn-sm text-xs" data-cat="${name}">Save</button>
                    </div>
                </div>
            `;
        },

        _renderPostProcess(key, m) {
            return `
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${m.enabled ? '' : 'opacity-50'}" data-pp="${key}">
                    <div class="flex items-center gap-2 mb-2">
                        <label class="toggle toggle-sm">
                            <input type="checkbox" class="ms-pp-toggle" data-key="${key}" ${m.enabled ? 'checked' : ''} />
                            <span class="toggle-slider"></span>
                        </label>
                        <span class="text-sm font-medium">${this._esc(m.label || key)}</span>
                        <span class="text-[10px] font-mono text-brand-text-muted ml-auto">${this._esc(m.region || '')}</span>
                    </div>
                    <div class="flex gap-2">
                        <input type="text" class="ms-pp-field input text-xs font-mono flex-1" value="${this._esc(m.model_id || '')}" data-key="${key}" data-field="model_id" />
                        <input type="text" class="ms-pp-field input text-xs w-28" value="${this._esc(m.region || '')}" data-key="${key}" data-field="region" />
                        <button class="ms-pp-save btn btn-primary btn-sm text-xs" data-key="${key}">Save</button>
                    </div>
                </div>
            `;
        },

        _attachEvents(modal) {
            // Close
            modal.querySelector('.ms-close')?.addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

            // Tab switching
            modal.querySelectorAll('[data-ms-tab]').forEach(tab => {
                tab.addEventListener('click', () => {
                    modal.querySelectorAll('[data-ms-tab]').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    modal.querySelectorAll('.ms-tab-panel').forEach(p => {
                        p.classList.toggle('hidden', p.dataset.msPanel !== tab.dataset.msTab);
                    });
                });
            });

            // Refresh All
            modal.querySelector('#ms-refresh-all')?.addEventListener('click', async () => {
                if (this._refreshing) return;
                if (!confirm('This will scan all AWS Bedrock regions for available models and fetch pricing data. This makes multiple AWS API calls and may take 30-60 seconds.\n\nRun this only when:\n• Setting up for the first time\n• AWS has released new models\n• You need updated pricing\n\nContinue?')) return;
                this._refreshing = true;
                const btn = modal.querySelector('#ms-refresh-all');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> Syncing from AWS...';

                try {
                    const result = await API.admin.refreshAll();
                    window.showToast?.(
                        `Refreshed: ${result.regions_scanned} regions, ${result.total_new} new models, ${result.total_updated} updated` +
                        (result.disabled?.length ? `, ${result.disabled.length} disabled` : ''),
                        'success', 6000
                    );
                    // Reload the modal with fresh data
                    this._registry = await API.admin.getModels();
                    modal.remove();
                    this._renderModal();
                } catch (err) {
                    window.showToast?.('Refresh failed: ' + (err.message || ''), 'error');
                } finally {
                    this._refreshing = false;
                }
            });

            // Image model toggles (enable/disable)
            modal.querySelectorAll('.ms-img-toggle').forEach(cb => {
                cb.addEventListener('change', async () => {
                    const key = cb.dataset.key;
                    const enabled = cb.checked;
                    const container = cb.closest('[data-image-model]');
                    container?.classList.toggle('opacity-50', !enabled);
                    try {
                        await API.admin.updateImageModel(key, { enabled });
                        window.showToast?.(`${key} ${enabled ? 'enabled' : 'disabled'}`, 'success');
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                        cb.checked = !enabled; // Revert
                        container?.classList.toggle('opacity-50', enabled);
                    }
                });
            });

            // Image model edit saves
            modal.querySelectorAll('.ms-edit-save').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const key = btn.dataset.key;
                    const container = btn.closest('[data-image-model]');
                    const data = {};
                    container.querySelectorAll('.ms-edit-field').forEach(el => {
                        if (el.dataset.key !== key) return;
                        const field = el.dataset.field;
                        let val = el.value;
                        if (el.type === 'number') val = parseFloat(val) || 0;
                        data[field] = val;
                    });
                    btn.disabled = true;
                    try {
                        await API.admin.updateImageModel(key, data);
                        window.showToast?.(`${key} updated`, 'success');
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                    }
                    btn.disabled = false;
                });
            });

            // Category saves
            modal.querySelectorAll('.ms-cat-save').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const cat = btn.dataset.cat;
                    const container = modal.querySelector(`[data-category="${cat}"]`);
                    const modelId = container.querySelector('.ms-cat-model')?.value;
                    const region = container.querySelector('.ms-cat-region')?.value;
                    btn.disabled = true;
                    try {
                        await API.admin.updateCategory(cat, { current: modelId, region });
                        window.showToast?.(`${cat} updated`, 'success');
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                    }
                    btn.disabled = false;
                });
            });

            // Post-process toggles and saves
            modal.querySelectorAll('.ms-pp-toggle').forEach(cb => {
                cb.addEventListener('change', async () => {
                    const key = cb.dataset.key;
                    const enabled = cb.checked;
                    cb.closest('[data-pp]')?.classList.toggle('opacity-50', !enabled);
                    try {
                        await API.admin.updatePostProcess(key, { enabled });
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                        cb.checked = !enabled;
                    }
                });
            });

            modal.querySelectorAll('.ms-pp-save').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const key = btn.dataset.key;
                    const container = modal.querySelector(`[data-pp="${key}"]`);
                    const data = {};
                    container.querySelectorAll('.ms-pp-field').forEach(el => {
                        data[el.dataset.field] = el.value;
                    });
                    data.enabled = container.querySelector('.ms-pp-toggle')?.checked;
                    btn.disabled = true;
                    try {
                        await API.admin.updatePostProcess(key, data);
                        window.showToast?.(`${key} updated`, 'success');
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                    }
                    btn.disabled = false;
                });
            });

            // JSON editor — save and reset
            const jsonEditor = modal.querySelector('#ms-json-editor');
            const jsonStatus = modal.querySelector('#ms-json-status');

            modal.querySelector('#ms-json-save')?.addEventListener('click', async () => {
                try {
                    const parsed = JSON.parse(jsonEditor.value);
                    // Validate it has required top-level keys
                    if (!parsed.categories || !parsed.image_models) {
                        throw new Error('Missing required keys: categories, image_models');
                    }
                    // Save via a full registry write
                    // We'll use a PUT-style approach: update every section
                    const resp = await fetch('/api/admin/models', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: jsonEditor.value,
                    });
                    if (!resp.ok) {
                        // PUT may not be supported — fall back to info
                        jsonStatus.textContent = 'Direct JSON save requires PUT /api/admin/models (not yet implemented). Use individual edit fields instead.';
                        jsonStatus.className = 'text-[10px] text-amber-400';
                        return;
                    }
                    jsonStatus.textContent = 'Saved successfully';
                    jsonStatus.className = 'text-[10px] text-emerald-400';
                    window.showToast?.('Registry JSON saved', 'success');
                } catch (err) {
                    jsonStatus.textContent = err.message;
                    jsonStatus.className = 'text-[10px] text-red-400';
                }
            });

            modal.querySelector('#ms-json-reset')?.addEventListener('click', () => {
                jsonEditor.value = JSON.stringify(this._registry, null, 2);
                jsonStatus.textContent = 'Reset to loaded state';
                jsonStatus.className = 'text-[10px] text-brand-text-muted';
            });
        },

        _esc(str) {
            const d = document.createElement('div');
            d.textContent = str || '';
            return d.innerHTML;
        },
    };
})();
