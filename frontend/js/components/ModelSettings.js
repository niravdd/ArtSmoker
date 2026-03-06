/**
 * ArtSmoker — Model Settings Component
 *
 * Admin modal for managing AI model configurations.
 * Accessible via settings icon in Image Studio and Type Studio.
 */
(function () {
    'use strict';

    const REGIONS = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1', 'ap-southeast-1'];

    window.ModelSettings = {
        _registry: null,
        _discovering: false,

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

            const modal = document.createElement('div');
            modal.id = 'model-settings-modal';
            modal.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                        <div class="flex items-center gap-3">
                            <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            </svg>
                            <h2 class="text-lg font-semibold">Model Settings</h2>
                        </div>
                        <button class="ms-close p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>

                    <div class="flex-1 overflow-auto p-6 space-y-6">

                        <!-- LLM Models -->
                        <div>
                            <h3 class="text-sm font-semibold text-brand-accent uppercase tracking-wider mb-3">AI / LLM Models</h3>
                            <div class="space-y-3">
                                ${this._renderCategory('fast_llm', reg.categories?.fast_llm)}
                                ${this._renderCategory('complex_llm', reg.categories?.complex_llm)}
                                ${this._renderCategory('fallback_llm', reg.categories?.fallback_llm)}
                            </div>
                        </div>

                        <!-- Image Generation Models -->
                        <div>
                            <h3 class="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-3">Image Generation Models</h3>
                            <div class="space-y-3">
                                ${Object.entries(reg.image_models || {}).map(([key, m]) => this._renderImageModel(key, m)).join('')}
                            </div>
                        </div>

                        <!-- Post-Processing Models -->
                        <div>
                            <h3 class="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3">Post-Processing Models</h3>
                            <div class="space-y-3">
                                ${Object.entries(reg.post_processing || {}).map(([key, m]) => this._renderPostProcess(key, m)).join('')}
                            </div>
                        </div>

                        <!-- Voice -->
                        <div>
                            <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wider mb-3">Voice</h3>
                            ${this._renderCategory('voice', reg.categories?.voice)}
                        </div>

                        <!-- Discovery -->
                        <div class="border-t border-brand-border pt-5">
                            <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wider mb-3">Discover Available Models</h3>
                            <div class="flex gap-2 items-center">
                                <select id="ms-discover-region" class="input text-sm">
                                    ${REGIONS.map(r => `<option value="${r}">${r}</option>`).join('')}
                                </select>
                                <button id="ms-discover-btn" class="btn btn-secondary btn-sm">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                    </svg>
                                    Discover
                                </button>
                            </div>
                            <div id="ms-discover-results" class="mt-3 hidden"></div>
                        </div>

                        <!-- Last Updated -->
                        <p class="text-[10px] text-brand-text-muted/40 text-right">
                            Registry last updated: ${reg.last_updated || 'unknown'}
                        </p>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            this._attachEvents(modal);
        },

        _renderCategory(name, cat) {
            if (!cat) return '';
            return `
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border" data-category="${name}">
                    <div class="flex items-center justify-between mb-2">
                        <div>
                            <span class="text-sm font-medium">${this._esc(cat.label || name)}</span>
                            <span class="text-[10px] text-brand-text-muted ml-2">${this._esc(cat.provider || '')}</span>
                        </div>
                        <span class="text-[10px] text-brand-text-muted font-mono bg-brand-bg px-2 py-0.5 rounded">${this._esc(cat.region || '')}</span>
                    </div>
                    <div class="flex gap-2">
                        <input type="text" class="ms-cat-model input text-xs flex-1 font-mono" value="${this._esc(cat.current || '')}" data-cat="${name}" data-field="current" placeholder="Model ID" />
                        <select class="ms-cat-region input text-xs w-28" data-cat="${name}" data-field="region">
                            ${REGIONS.map(r => `<option value="${r}" ${r === cat.region ? 'selected' : ''}>${r}</option>`).join('')}
                        </select>
                        <button class="ms-cat-save btn btn-primary btn-sm text-xs" data-cat="${name}">Save</button>
                    </div>
                    <p class="text-[10px] text-brand-text-muted/50 mt-1">${this._esc(cat.description || '')}</p>
                </div>
            `;
        },

        _renderImageModel(key, m) {
            return `
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${m.enabled ? '' : 'opacity-50'}" data-image-model="${key}">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2">
                            <label class="toggle toggle-sm">
                                <input type="checkbox" class="ms-img-enabled" data-key="${key}" ${m.enabled ? 'checked' : ''} />
                                <span class="toggle-slider"></span>
                            </label>
                            <span class="text-sm font-medium">${this._esc(m.label || key)}</span>
                            <span class="text-[10px] text-brand-text-muted">${this._esc(m.provider || '')}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-[10px] font-mono text-brand-text-muted bg-brand-bg px-2 py-0.5 rounded">${this._esc(m.region || '')}</span>
                            <span class="text-[10px] ${m.moderation_strictness === 'very_strict' ? 'text-red-400' : m.moderation_strictness === 'strict' ? 'text-amber-400' : 'text-emerald-400'}">${m.moderation_strictness || ''}</span>
                        </div>
                    </div>
                    <div class="flex gap-2 text-xs">
                        <div class="flex-1">
                            <label class="text-[10px] text-brand-text-muted">Model ID</label>
                            <input type="text" class="ms-img-field input text-xs font-mono w-full" value="${this._esc(m.model_id || '')}" data-key="${key}" data-field="model_id" />
                        </div>
                        <div class="w-20">
                            <label class="text-[10px] text-brand-text-muted">Prompt limit</label>
                            <input type="number" class="ms-img-field input text-xs w-full" value="${m.prompt_limit || 900}" data-key="${key}" data-field="prompt_limit" />
                        </div>
                        <div class="w-28">
                            <label class="text-[10px] text-brand-text-muted">Region</label>
                            <select class="ms-img-field input text-xs w-full" data-key="${key}" data-field="region">
                                ${REGIONS.map(r => `<option value="${r}" ${r === m.region ? 'selected' : ''}>${r}</option>`).join('')}
                            </select>
                        </div>
                        <div class="flex items-end">
                            <button class="ms-img-save btn btn-primary btn-sm text-xs" data-key="${key}">Save</button>
                        </div>
                    </div>
                    <div class="flex gap-4 mt-1.5 text-[10px] text-brand-text-muted/50">
                        <span>Dimensions: ${m.supports_dimensions ? 'yes' : 'no'}</span>
                        <span>Aspect ratio: ${m.supports_aspect_ratio ? 'yes' : 'no'}</span>
                    </div>
                </div>
            `;
        },

        _renderPostProcess(key, m) {
            return `
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${m.enabled ? '' : 'opacity-50'}" data-pp="${key}">
                    <div class="flex items-center gap-2 mb-2">
                        <label class="toggle toggle-sm">
                            <input type="checkbox" class="ms-pp-enabled" data-key="${key}" ${m.enabled ? 'checked' : ''} />
                            <span class="toggle-slider"></span>
                        </label>
                        <span class="text-sm font-medium">${this._esc(m.label || key)}</span>
                        <span class="text-[10px] font-mono text-brand-text-muted ml-auto">${this._esc(m.region || '')}</span>
                    </div>
                    <div class="flex gap-2">
                        <input type="text" class="ms-pp-field input text-xs font-mono flex-1" value="${this._esc(m.model_id || '')}" data-key="${key}" data-field="model_id" />
                        <select class="ms-pp-field input text-xs w-28" data-key="${key}" data-field="region">
                            ${REGIONS.map(r => `<option value="${r}" ${r === m.region ? 'selected' : ''}>${r}</option>`).join('')}
                        </select>
                        <button class="ms-pp-save btn btn-primary btn-sm text-xs" data-key="${key}">Save</button>
                    </div>
                </div>
            `;
        },

        _attachEvents(modal) {
            // Close
            modal.querySelector('.ms-close')?.addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

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

            // Image model saves
            modal.querySelectorAll('.ms-img-save').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const key = btn.dataset.key;
                    const container = modal.querySelector(`[data-image-model="${key}"]`);
                    const data = {};
                    container.querySelectorAll('.ms-img-field').forEach(el => {
                        const field = el.dataset.field;
                        const val = el.type === 'number' ? parseInt(el.value, 10) : el.value;
                        data[field] = val;
                    });
                    const enabled = container.querySelector('.ms-img-enabled')?.checked;
                    data.enabled = enabled;
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

            // Image model enable/disable toggles
            modal.querySelectorAll('.ms-img-enabled').forEach(cb => {
                cb.addEventListener('change', () => {
                    const container = cb.closest('[data-image-model]');
                    container?.classList.toggle('opacity-50', !cb.checked);
                });
            });

            // Post-process saves
            modal.querySelectorAll('.ms-pp-save').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const key = btn.dataset.key;
                    const container = modal.querySelector(`[data-pp="${key}"]`);
                    const data = {};
                    container.querySelectorAll('.ms-pp-field').forEach(el => {
                        data[el.dataset.field] = el.value;
                    });
                    data.enabled = container.querySelector('.ms-pp-enabled')?.checked;
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

            // Post-process toggles
            modal.querySelectorAll('.ms-pp-enabled').forEach(cb => {
                cb.addEventListener('change', () => {
                    cb.closest('[data-pp]')?.classList.toggle('opacity-50', !cb.checked);
                });
            });

            // Discover
            modal.querySelector('#ms-discover-btn')?.addEventListener('click', async () => {
                const region = modal.querySelector('#ms-discover-region')?.value;
                if (!region) return;
                const btn = modal.querySelector('#ms-discover-btn');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> Discovering...';
                const results = modal.querySelector('#ms-discover-results');

                try {
                    const data = await API.admin.discover(region);
                    results.classList.remove('hidden');
                    results.innerHTML = `
                        <p class="text-xs text-brand-text-muted mb-2">${data.total} models found in ${region}</p>
                        ${data.image_generators.length > 0 ? `
                        <details class="mb-2">
                            <summary class="text-xs font-medium text-emerald-400 cursor-pointer">Image Generators (${data.image_generators.length})</summary>
                            <div class="mt-1 space-y-1 max-h-40 overflow-auto">
                                ${data.image_generators.map(m => `
                                    <div class="text-[10px] p-1.5 bg-brand-bg/40 rounded flex items-center justify-between">
                                        <span class="font-mono">${m.model_id}</span>
                                        <span class="text-brand-text-muted">${m.provider}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </details>` : ''}
                        ${data.text_models.length > 0 ? `
                        <details class="mb-2">
                            <summary class="text-xs font-medium text-brand-accent cursor-pointer">Text/LLM Models (${data.text_models.length})</summary>
                            <div class="mt-1 space-y-1 max-h-40 overflow-auto">
                                ${data.text_models.map(m => `
                                    <div class="text-[10px] p-1.5 bg-brand-bg/40 rounded flex items-center justify-between">
                                        <span class="font-mono">${m.model_id}</span>
                                        <span class="text-brand-text-muted">${m.provider}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </details>` : ''}
                        ${data.vision_models.length > 0 ? `
                        <details>
                            <summary class="text-xs font-medium text-amber-400 cursor-pointer">Vision Models (${data.vision_models.length})</summary>
                            <div class="mt-1 space-y-1 max-h-40 overflow-auto">
                                ${data.vision_models.map(m => `
                                    <div class="text-[10px] p-1.5 bg-brand-bg/40 rounded flex items-center justify-between">
                                        <span class="font-mono">${m.model_id}</span>
                                        <span class="text-brand-text-muted">${m.provider}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </details>` : ''}
                    `;
                } catch (err) {
                    results.classList.remove('hidden');
                    results.innerHTML = `<p class="text-xs text-red-400">${err.message || 'Discovery failed'}</p>`;
                }
                btn.disabled = false;
                btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg> Discover';
            });
        },

        _esc(str) {
            const d = document.createElement('div');
            d.textContent = str || '';
            return d.innerHTML;
        },
    };
})();
