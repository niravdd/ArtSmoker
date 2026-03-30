/**
 * ArtSmoker — Model Settings Component
 *
 * Admin modal for managing AI model configurations.
 * Tabs aligned with app studios: Image Studio, Video Studio, AI Engine.
 * Sync from AWS discovers foundation, custom, and imported models.
 */
(function () {
    'use strict';

    window.ModelSettings = {
        _registry: null,
        _refreshing: false,

        async open() {
            document.getElementById('model-settings-modal')?.remove();
            window.showLoading?.(t('model_settings.loading_settings'));

            try {
                this._registry = await API.admin.getModels();
                window.hideLoading?.();
                this._renderModal();
            } catch (err) {
                window.hideLoading?.();
                window.showToast?.(t('model_settings.load_failed') + ': ' + (err.message || ''), 'error');
            }
        },

        _renderModal() {
            const reg = this._registry;
            if (!reg) return;

            const lastUpdated = reg.last_updated
                ? new Date(reg.last_updated).toLocaleString()
                : t('common.unknown');

            // Count models per tab
            const imgCount = Object.keys(reg.image_models || {}).length;
            const vidCount = Object.keys(reg.video_models || {}).length;
            const llmCount = Object.keys(reg.categories || {}).length + Object.keys(reg.post_processing || {}).length;

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
                            <h2 class="text-lg font-semibold">${t('model_settings.title')}</h2>
                        </div>
                        <div class="flex items-center gap-3">
                            <button id="ms-refresh-all" class="btn btn-sm text-xs bg-amber-600 hover:bg-amber-500 text-white" title="${t('model_settings.sync_tooltip')}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                                ${t('model_settings.sync_aws')}
                            </button>
                            <span class="text-[10px] text-brand-text-muted" title="${t('model_settings.discovers_tooltip')}">${t('model_settings.updated')}: ${lastUpdated}</span>
                            <button class="ms-close p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Tabs — aligned with app studios -->
                    <div class="tab-bar px-6 pt-3">
                        <button class="tab active" data-ms-tab="image-studio">
                            ${t('model_settings.tab_image')}
                            <span class="text-[9px] opacity-60 ml-1">(${imgCount})</span>
                        </button>
                        <button class="tab" data-ms-tab="video-studio">
                            ${t('model_settings.tab_video')}
                            <span class="text-[9px] opacity-60 ml-1">(${vidCount})</span>
                        </button>
                        <button class="tab" data-ms-tab="chat-studio">
                            ${t('model_settings.tab_chat')}
                            <span class="text-[9px] opacity-60 ml-1">(${Object.keys(reg.chat_models || {}).length})</span>
                        </button>
                        <button class="tab" data-ms-tab="ai-engine">
                            ${t('model_settings.tab_ai')}
                            <span class="text-[9px] opacity-60 ml-1">(${llmCount})</span>
                        </button>
                        <button class="tab" data-ms-tab="registry-json">${t('model_settings.tab_json')}</button>
                    </div>

                    <!-- Tab content -->
                    <div class="flex-1 overflow-auto p-6">

                        <!-- Tab: Image Studio -->
                        <div class="ms-tab-panel" data-ms-panel="image-studio">
                            <p class="text-[10px] text-brand-text-muted mb-3">${t('model_settings.desc_image')}</p>
                            <div id="ms-image-models" class="space-y-3">
                                ${this._renderImageModels(reg)}
                            </div>
                        </div>

                        <!-- Tab: Video Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="video-studio">
                            <p class="text-[10px] text-brand-text-muted mb-3">${t('model_settings.desc_video')}</p>
                            <div id="ms-video-models" class="space-y-3">
                                ${this._renderVideoModels(reg)}
                            </div>
                        </div>

                        <!-- Tab: Chat Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="chat-studio">
                            <p class="text-[10px] text-brand-text-muted mb-3">${t('model_settings.desc_chat')}</p>
                            <div id="ms-chat-models" class="space-y-2">
                                ${this._renderChatModels(reg)}
                            </div>
                        </div>

                        <!-- Tab: AI Engine -->
                        <div class="ms-tab-panel hidden" data-ms-panel="ai-engine">
                            <p class="text-[10px] text-brand-text-muted mb-3">${t('model_settings.desc_ai')}</p>
                            <div class="space-y-6">
                                <div>
                                    <h3 class="text-sm font-semibold text-brand-accent uppercase tracking-wider mb-3">${t('model_settings.llm_categories')}</h3>
                                    <div class="space-y-3">
                                        ${Object.entries(reg.categories || {}).filter(([name]) => name !== 'custom_llms').map(([name, cat]) => this._renderCategory(name, cat)).join('')}
                                    </div>
                                </div>
                                ${this._renderCustomLLMs(reg)}
                                <div>
                                    <h3 class="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3">${t('model_settings.post_processing')}</h3>
                                    <div class="space-y-3">
                                        ${Object.entries(reg.post_processing || {}).map(([key, m]) => this._renderPostProcess(key, m)).join('')}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Tab: Registry JSON -->
                        <div class="ms-tab-panel hidden" data-ms-panel="registry-json">
                            <p class="text-xs text-brand-text-muted mb-2">${t('model_settings.json_desc')}</p>
                            <textarea id="ms-json-editor" class="w-full h-[50vh] font-mono text-xs p-3 rounded-lg bg-brand-bg border border-brand-border text-brand-text resize-none" spellcheck="false">${this._esc(JSON.stringify(reg, null, 2))}</textarea>
                            <div class="flex items-center gap-2 mt-2">
                                <button id="ms-json-save" class="btn btn-primary btn-sm text-xs">${t('model_settings.save_json')}</button>
                                <button id="ms-json-reset" class="btn btn-secondary btn-sm text-xs">${t('model_settings.reset_json')}</button>
                                <span id="ms-json-status" class="text-[10px] text-brand-text-muted"></span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            this._attachEvents(modal);
        },

        _sourceBadge(model) {
            const source = model.model_source || 'foundation';
            if (source === 'custom') return '<span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20 font-medium">Custom</span>';
            if (source === 'imported') return '<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/20 font-medium">Imported</span>';
            return '';
        },

        _renderImageModels(reg) {
            const models = reg.image_models || {};
            if (Object.keys(models).length === 0) {
                return '<p class="text-sm text-brand-text-muted py-4 text-center">' + t('model_settings.no_models') + '</p>';
            }

            // Group models by purpose
            const groups = {};
            const PURPOSE_LABELS = {
                'text_to_image': t('model_settings.generation'),
                'inpainting': t('model_settings.inpainting'),
                'outpainting': t('model_settings.outpainting'),
                'erase': t('model_settings.erase_label'),
                'search_replace': t('model_settings.search_replace'),
                'search_recolor': t('model_settings.search_recolor'),
                'control_sketch': t('model_settings.control_sketch'),
                'control_structure': t('model_settings.control_structure'),
                'style_guide': t('model_settings.style_guide'),
                'style_transfer': t('model_settings.style_transfer'),
                'remove_background': t('model_settings.remove_bg'),
                'upscale_creative': t('model_settings.upscale_creative'),
                'upscale_conservative': t('model_settings.upscale_conservative'),
                'upscale_fast': t('model_settings.upscale_fast'),
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
            const regions = (m.available_regions || [m.region]).join(', ');
            const quality = (m.quality_options || []).map(q => q.label).join(' / ') || t('model_settings.no_tiers');
            const price = m.base_price_usd != null ? `$${m.base_price_usd.toFixed(2)}/img` : t('common.unknown');
            const strictColor = m.moderation_strictness === 'very_strict' ? 'text-red-400' : m.moderation_strictness === 'strict' ? 'text-amber-400' : 'text-emerald-400';
            const sourceBadge = this._sourceBadge(m);

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
                                ${sourceBadge}
                            </div>
                            <span class="${strictColor} text-[10px]">${m.moderation_strictness || ''}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-brand-text-muted mb-2">
                            <span>${t('model_settings.field_model_id')}: <span class="font-mono text-brand-text/70">${this._esc(m.model_id || '')}</span></span>
                            <span>${t('model_settings.field_format')}: <span class="text-brand-text/70">${this._esc(m.format_family || '')}</span></span>
                            <span>${t('model_settings.field_regions')}: <span class="text-brand-text/70">${regions || t('common.none').toLowerCase()}</span></span>
                            <span>${t('model_settings.field_prompt_limit_short')}: <span class="text-brand-text/70">${m.prompt_limit || '?'} chars</span></span>
                            <span>${t('model_settings.field_quality')}: <span class="text-brand-text/70">${quality}</span></span>
                            <span>${t('model_settings.field_price')}: <span class="text-emerald-400/70">${price}</span></span>
                        </div>
                        <details class="group">
                            <summary class="text-[10px] text-brand-accent cursor-pointer hover:text-brand-accent-hover">
                                <span class="group-open:hidden">${t('model_settings.edit_link')}</span>
                                <span class="hidden group-open:inline">${t('model_settings.close_editor')}</span>
                            </summary>
                            <div class="mt-2 space-y-2 p-2 rounded bg-brand-bg/60 border border-brand-border/50">
                                <div class="grid grid-cols-2 gap-2">
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('model_settings.field_model_id')}</label>
                                        <input type="text" class="ms-edit-field input text-xs font-mono w-full" data-key="${key}" data-field="model_id" value="${this._esc(m.model_id || '')}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('model_settings.field_label')}</label>
                                        <input type="text" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="label" value="${this._esc(m.label || '')}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('model_settings.field_prompt_limit')}</label>
                                        <input type="number" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="prompt_limit" value="${m.prompt_limit || 900}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('model_settings.field_base_price')}</label>
                                        <input type="number" step="0.01" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="base_price_usd" value="${m.base_price_usd || ''}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('model_settings.field_moderation')}</label>
                                        <select class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="moderation_strictness">
                                            ${['moderate', 'strict', 'very_strict'].map(s => `<option value="${s}" ${s === m.moderation_strictness ? 'selected' : ''}>${s}</option>`).join('')}
                                        </select>
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('model_settings.field_default_region')}</label>
                                        <input type="text" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="region" value="${this._esc(m.region || '')}" />
                                    </div>
                                </div>
                                <button class="ms-edit-save btn btn-primary btn-sm text-xs" data-key="${key}">${t('model_settings.save_changes')}</button>
                            </div>
                        </details>
                    </div>
                `;
        },

        _renderChatModels(reg) {
            const models = reg.chat_models || {};
            if (Object.keys(models).length === 0) {
                return '<p class="text-sm text-brand-text-muted py-4 text-center">' + t('model_settings.no_chat_models') + '</p>';
            }

            // Group by provider
            const groups = {};
            for (const [key, m] of Object.entries(models)) {
                const provider = m.provider || 'Other';
                if (!groups[provider]) groups[provider] = [];
                groups[provider].push([key, m]);
            }

            return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0])).map(([provider, entries]) => {
                return `
                    <div class="mb-4">
                        <h4 class="text-xs font-semibold text-brand-accent uppercase tracking-wider mb-2 flex items-center gap-2">
                            ${this._esc(provider)}
                            <span class="text-[10px] font-normal text-brand-text-muted">(${entries.length})</span>
                        </h4>
                        <div class="space-y-1.5">
                            ${entries.sort((a, b) => (a[1].label || '').localeCompare(b[1].label || '')).map(([key, m]) => {
                                const regions = (m.available_regions || []).length;
                                const vision = m.has_vision ? '<span class="text-[9px] px-1 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20">' + t('model_settings.vision_badge') + '</span>' : '';
                                const streaming = m.streaming_supported ? '' : '<span class="text-[9px] px-1 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20">' + t('model_settings.no_stream') + '</span>';
                                const ctx = (m.max_context_tokens || 128000) >= 1000000
                                    ? `${Math.round((m.max_context_tokens || 128000) / 1000000)}M`
                                    : `${Math.round((m.max_context_tokens || 128000) / 1000)}K`;
                                const enabled = m.enabled !== false;
                                return `
                                    <div class="p-2.5 rounded-lg bg-brand-bg/40 border border-brand-border ${enabled ? '' : 'opacity-50'} flex items-center gap-3">
                                        <label class="toggle toggle-sm flex-shrink-0">
                                            <input type="checkbox" class="ms-chat-toggle" data-key="${this._esc(key)}" ${enabled ? 'checked' : ''} />
                                            <span class="toggle-slider"></span>
                                        </label>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center gap-2">
                                                <span class="text-xs font-medium truncate">${this._esc(m.label || key)}</span>
                                                ${vision}${streaming}
                                                <span class="text-[9px] text-brand-text-muted">${ctx} ${t('model_settings.context_label')}</span>
                                            </div>
                                            <div class="text-[10px] text-brand-text-muted font-mono truncate mt-0.5">${this._esc(m.model_id || '')}</div>
                                        </div>
                                        <div class="flex-shrink-0 text-right">
                                            <span class="text-[10px] text-brand-accent">${regions} ${t('common.region').toLowerCase()}${regions !== 1 ? 's' : ''}</span>
                                            <div class="flex flex-wrap gap-0.5 mt-0.5 justify-end max-w-[200px]">
                                                ${(m.available_regions || []).map(r => `<span class="text-[8px] px-1 py-0 rounded bg-brand-bg text-brand-text-muted/60">${this._esc(r)}</span>`).join('')}
                                            </div>
                                        </div>
                                    </div>`;
                            }).join('')}
                        </div>
                    </div>`;
            }).join('');
        },

        _renderVideoModels(reg) {
            const models = reg.video_models || {};
            if (Object.keys(models).length === 0) {
                return '<p class="text-sm text-brand-text-muted py-4 text-center">' + t('model_settings.no_video_models') + '</p>';
            }
            return Object.entries(models).map(([key, m]) => {
                const enabled = m.enabled !== false;
                const regions = m.available_regions || [m.region].filter(Boolean);
                const price = m.base_price_per_second_usd ? `$${m.base_price_per_second_usd}/sec` : '';
                const sourceBadge = this._sourceBadge(m);
                return `
                    <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${!enabled ? 'opacity-50' : ''}" data-video-key="${key}">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center gap-2">
                                <label class="toggle toggle-sm">
                                    <input type="checkbox" class="ms-video-toggle" data-key="${this._esc(key)}" ${enabled ? 'checked' : ''} />
                                    <span class="toggle-slider"></span>
                                </label>
                                <span class="text-sm font-medium">${this._esc(m.label || key)}</span>
                                <span class="text-[10px] text-brand-text-muted">${this._esc(m.provider || '')}</span>
                                ${sourceBadge}
                            </div>
                            <div class="flex items-center gap-1.5">
                                ${price ? `<span class="badge badge-indigo">${price}</span>` : ''}
                                ${m.supports_image_input ? '<span class="badge badge-indigo">img\u2192vid</span>' : ''}
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-brand-text-muted mb-2">
                            <span>${t('model_settings.field_model_id')}: <span class="font-mono text-brand-text/70">${this._esc(m.model_id || '')}</span></span>
                            <span>${t('model_settings.field_format')}: <span class="text-brand-text/70">${this._esc(m.format_family || '')}</span></span>
                            <span>${t('model_settings.field_prompt_limit_short')}: <span class="text-brand-text/70">${m.prompt_limit || '?'} chars</span></span>
                            <span>${t('model_settings.field_default_region')}: <span class="text-brand-text/70">${this._esc(m.region || '')}</span></span>
                        </div>
                        <div class="flex flex-wrap gap-1 mb-1">
                            ${regions.map(r => `<span class="text-[9px] px-1.5 py-0.5 rounded bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${this._esc(r)}</span>`).join('')}
                        </div>
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
                        <input type="text" class="ms-cat-model input text-xs flex-1 font-mono" value="${this._esc(cat.current || '')}" data-cat="${name}" placeholder="${t('model_settings.model_id_placeholder')}" />
                        <input type="text" class="ms-cat-region input text-xs w-28" value="${this._esc(cat.region || '')}" data-cat="${name}" placeholder="${t('model_settings.region_placeholder')}" />
                        <button class="ms-cat-save btn btn-primary btn-sm text-xs" data-cat="${name}">${t('model_settings.save_label')}</button>
                    </div>
                </div>
            `;
        },

        _renderCustomLLMs(reg) {
            const customLLMs = (reg.categories || {}).custom_llms;
            if (!customLLMs || !customLLMs.models || Object.keys(customLLMs.models).length === 0) {
                return '';
            }
            const models = customLLMs.models;
            return `
                <div>
                    <h3 class="text-sm font-semibold text-purple-400 uppercase tracking-wider mb-3">${t('model_settings.custom_llms')}</h3>
                    <p class="text-[10px] text-brand-text-muted mb-2">${t('model_settings.custom_llms_desc')}</p>
                    <div class="space-y-2">
                        ${Object.entries(models).map(([key, m]) => {
                            const source = m.model_source || 'custom';
                            const badge = source === 'imported'
                                ? '<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/20 font-medium">Imported</span>'
                                : '<span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20 font-medium">Custom</span>';
                            const enabledBadge = m.enabled
                                ? '<span class="text-[9px] text-emerald-400">' + t('model_settings.ready') + '</span>'
                                : '<span class="text-[9px] text-amber-400">' + t('model_settings.needs_throughput') + '</span>';
                            return `
                                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${m.enabled ? '' : 'opacity-60'}">
                                    <div class="flex items-center gap-2 mb-1">
                                        <span class="text-sm font-medium">${this._esc(m.label || key)}</span>
                                        ${badge}
                                        ${enabledBadge}
                                    </div>
                                    <div class="grid grid-cols-2 gap-x-4 text-[10px] text-brand-text-muted">
                                        <span>${t('model_settings.field_model_id')}: <span class="font-mono text-brand-text/70 break-all">${this._esc((m.model_id || '').slice(-40))}</span></span>
                                        <span>${t('common.region')}: <span class="text-brand-text/70">${this._esc(m.region || '')}</span></span>
                                        ${m.architecture ? `<span>Architecture: <span class="text-brand-text/70">${this._esc(m.architecture)}</span></span>` : ''}
                                        ${m.customization_type ? `<span>Type: <span class="text-brand-text/70">${this._esc(m.customization_type)}</span></span>` : ''}
                                    </div>
                                </div>
                            `;
                        }).join('')}
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
                        <button class="ms-pp-save btn btn-primary btn-sm text-xs" data-key="${key}">${t('model_settings.save_label')}</button>
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
                if (!await window.showConfirm(t('model_settings.sync_confirm'), {
                    title: t('model_settings.sync_title'),
                    detail: t('model_settings.sync_detail_full'),
                    confirmLabel: t('model_settings.sync_now'),
                })) return;
                this._refreshing = true;
                const btn = modal.querySelector('#ms-refresh-all');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-sm"></span> ' + t('model_settings.syncing');

                try {
                    const result = await API.admin.refreshAll();
                    const customMsg = result.total_custom > 0 ? `\nCustom/imported models: ${result.total_custom}` : '';
                    const disabledMsg = result.disabled?.length ? `\nDisabled (no longer available): ${result.disabled.length}` : '';
                    const chatCount = result.per_region ? Object.values(result.per_region).reduce((s, r) => s + (r.new || 0), 0) : 0;

                    // Reload the modal with fresh data first
                    this._registry = await API.admin.getModels();
                    const imgCount = Object.keys(this._registry.image_models || {}).length;
                    const vidCount = Object.keys(this._registry.video_models || {}).length;
                    const chatModels = Object.keys(this._registry.chat_models || {}).length;

                    modal.remove();
                    this._renderModal();

                    // Show completion summary
                    await window.showConfirm(
                        t('model_settings.sync_scanned', {count: result.regions_scanned}), {
                        title: t('model_settings.sync_complete'),
                        detail: `New models discovered: ${result.total_new}\nExisting models updated: ${result.total_updated}${customMsg}${disabledMsg}\n\nRegistry totals:\n  Image models: ${imgCount}\n  Video models: ${vidCount}\n  Chat/LLM models: ${chatModels}\n  Errors: ${result.errors || 0}`,
                        confirmLabel: t('common.ok'),
                        cancelLabel: '',
                    });
                } catch (err) {
                    await window.showConfirm(t('model_settings.sync_failed_msg'), {
                        title: t('model_settings.sync_failed'),
                        detail: err.message || t('common.unknown'),
                        confirmLabel: t('common.ok'),
                        cancelLabel: '',
                        danger: true,
                    });
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
                        window.showToast?.(`${key} ${enabled ? t('common.enabled') : t('common.disabled')}`, 'success');
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                        cb.checked = !enabled; // Revert
                        container?.classList.toggle('opacity-50', enabled);
                    }
                });
            });

            // Chat model toggles (enable/disable)
            modal.querySelectorAll('.ms-chat-toggle').forEach(cb => {
                cb.addEventListener('change', async () => {
                    const key = cb.dataset.key;
                    const enabled = cb.checked;
                    cb.closest('.rounded-lg')?.classList.toggle('opacity-50', !enabled);
                    try {
                        // Update chat_models in registry via full PUT
                        if (this._registry?.chat_models?.[key]) {
                            this._registry.chat_models[key].enabled = enabled;
                        }
                        const resp = await fetch('/api/admin/models', {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this._registry),
                        });
                        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                        window.showToast?.(`${key} ${enabled ? t('common.enabled') : t('common.disabled')}`, 'success');
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                        cb.checked = !enabled;
                        cb.closest('.rounded-lg')?.classList.toggle('opacity-50', enabled);
                    }
                });
            });

            // Video model toggles (enable/disable)
            modal.querySelectorAll('.ms-video-toggle').forEach(cb => {
                cb.addEventListener('change', async () => {
                    const key = cb.dataset.key;
                    const enabled = cb.checked;
                    const container = cb.closest('[data-video-key]');
                    container?.classList.toggle('opacity-50', !enabled);
                    try {
                        const resp = await fetch(`/api/admin/models/video/${encodeURIComponent(key)}`, {
                            method: 'PATCH', body: JSON.stringify({ enabled }),
                            headers: { 'Content-Type': 'application/json' },
                        });
                        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                        window.showToast?.(`${key} ${enabled ? t('common.enabled') : t('common.disabled')}`, 'success');
                    } catch (err) {
                        window.showToast?.('Failed: ' + (err.message || ''), 'error');
                        cb.checked = !enabled;
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
                        throw new Error(t('model_settings.missing_keys'));
                    }
                    const resp = await fetch('/api/admin/models', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: jsonEditor.value,
                    });
                    if (!resp.ok) {
                        jsonStatus.textContent = t('model_settings.json_save_not_impl');
                        jsonStatus.className = 'text-[10px] text-amber-400';
                        return;
                    }
                    jsonStatus.textContent = t('model_settings.saved_successfully');
                    jsonStatus.className = 'text-[10px] text-emerald-400';
                    window.showToast?.(t('model_settings.json_saved'), 'success');
                } catch (err) {
                    jsonStatus.textContent = err.message;
                    jsonStatus.className = 'text-[10px] text-red-400';
                }
            });

            modal.querySelector('#ms-json-reset')?.addEventListener('click', () => {
                jsonEditor.value = JSON.stringify(this._registry, null, 2);
                jsonStatus.textContent = t('model_settings.reset_to_loaded');
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
