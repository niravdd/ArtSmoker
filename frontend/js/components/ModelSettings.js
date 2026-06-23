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

        async open(activeTab) {
            this._requestedTab = activeTab || null;
            document.getElementById('model-settings-modal')?.remove();
            // Reset state so tabs reload fresh content when modal is reopened
            this._customModelsLoaded = false;
            this._templatesLoaded = false;
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
                ? window.formatTimestamp(reg.last_updated)
                : t('common.unknown');

            // Count models per tab
            const imgCount = Object.keys(reg.image_models || {}).length;
            const vidCount = Object.keys(reg.video_models || {}).length;
            const llmCount = Object.keys(reg.categories || {}).length + Object.keys(reg.post_processing || {}).length;

            const modal = document.createElement('div');
            modal.id = 'model-settings-modal';
            modal.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl w-full h-[90vh] flex flex-col overflow-hidden" style="max-width: 80rem;">
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

                    <!-- Vertical tabs + content -->
                    <div class="flex flex-1 min-h-0">
                        <!-- Sidebar tabs -->
                        <div class="w-48 flex-shrink-0 border-r border-brand-border bg-black/10 py-2 overflow-y-auto">
                            <button class="ms-vtab active w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors bg-brand-accent/10 text-brand-accent border-l-2 border-brand-accent" data-ms-tab="image-studio">
                                🖼️  ${t('model_settings.tab_image')} <span class="text-[9px] opacity-50 ml-1">(${imgCount})</span>
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="video-studio">
                                🎬  ${t('model_settings.tab_video')} <span class="text-[9px] opacity-50 ml-1">(${vidCount})</span>
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="chat-studio">
                                💬  ${t('model_settings.tab_chat')} <span class="text-[9px] opacity-50 ml-1">(${Object.keys(reg.chat_models || {}).length})</span>
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="type-studio">
                                ✍️  ${t('model_settings.tab_type')}
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="shared-ai">
                                ⚙️  ${t('model_settings.tab_shared')} <span class="text-[9px] opacity-50 ml-1">(${llmCount})</span>
                            </button>
                            <div class="border-t border-brand-border my-1"></div>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="custom-models">
                                🔧  ${t('custom_models.tab_title')}
                            </button>
                            <div class="border-t border-brand-border my-1"></div>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="prompt-templates">
                                📝  ${t('model_settings.tab_templates')}
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="registry-json">
                                { }  ${t('model_settings.tab_json')}
                            </button>
                        </div>

                        <!-- Tab content -->
                        <div class="flex-1 overflow-auto p-6">

                        <!-- Tab: Image Studio -->
                        <div class="ms-tab-panel" data-ms-panel="image-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('model_settings.desc_image')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="image-studio">Show All</button>
                            </div>
                            <div id="ms-image-models" class="space-y-3">
                                ${this._renderImageModels(reg)}
                            </div>
                        </div>

                        <!-- Tab: Video Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="video-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('model_settings.desc_video')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="video-studio">Show All</button>
                            </div>
                            <details class="ms-collapsible">
                                <summary class="text-sm font-semibold text-brand-accent uppercase tracking-wider cursor-pointer hover:opacity-80 select-none mb-2">${t('model_settings.tab_video')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(reg.video_models || {}).length})</span></summary>
                                <div id="ms-video-models" class="space-y-3">
                                    ${this._renderVideoModels(reg)}
                                </div>
                            </details>
                        </div>

                        <!-- Tab: Chat Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="chat-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('model_settings.desc_chat')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="chat-studio">Show All</button>
                            </div>
                            <div id="ms-chat-models" class="space-y-2">
                                ${this._renderChatModels(reg)}
                            </div>
                        </div>

                        <!-- Tab: Type Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="type-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('model_settings.desc_type')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="type-studio">Show All</button>
                            </div>
                            <div class="space-y-4">
                                <details class="ms-collapsible">
                                    <summary class="text-sm font-semibold text-cyan-400 uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('model_settings.type_llm_heading')}</summary>
                                    <p class="text-[10px] text-brand-text-muted mb-2 mt-2">${t('model_settings.type_llm_desc')}</p>
                                    <div class="space-y-3">
                                        ${['complex_llm', 'fast_llm'].map(name => {
                                            const cat = (reg.categories || {})[name];
                                            return cat ? this._renderCategory(name, cat) : '';
                                        }).join('')}
                                    </div>
                                </details>
                                <details class="ms-collapsible">
                                    <summary class="text-sm font-semibold text-amber-400 uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('model_settings.post_processing')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(reg.post_processing || {}).length})</span></summary>
                                    <p class="text-[10px] text-brand-text-muted mb-2 mt-2">${t('model_settings.type_pp_desc')}</p>
                                    <div class="space-y-3">
                                        ${Object.entries(reg.post_processing || {}).map(([key, m]) => this._renderPostProcess(key, m)).join('')}
                                    </div>
                                </details>
                            </div>
                        </div>

                        <!-- Tab: Shared AI -->
                        <div class="ms-tab-panel hidden" data-ms-panel="shared-ai">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('model_settings.desc_shared')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="shared-ai">Show All</button>
                            </div>
                            <div class="space-y-4">
                                <details class="ms-collapsible">
                                    <summary class="text-sm font-semibold text-brand-accent uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('model_settings.llm_categories')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(reg.categories || {}).length - (reg.categories?.custom_llms ? 1 : 0)})</span></summary>
                                    <div class="space-y-3 mt-2">
                                        ${Object.entries(reg.categories || {}).filter(([name]) => name !== 'custom_llms').map(([name, cat]) => this._renderCategory(name, cat)).join('')}
                                    </div>
                                </details>
                                ${this._renderCustomLLMs(reg)}
                            </div>
                        </div>

                        <!-- Tab: Prompt Templates -->
                        <div class="ms-tab-panel hidden" data-ms-panel="prompt-templates">
                            <p class="text-xs text-red-400 mb-2">${t('model_settings.templates_desc')}</p>
                            <div class="flex items-center gap-2 mb-3 p-2 rounded-lg bg-brand-bg/40 border border-brand-border/50">
                                <span class="text-[10px] text-brand-text-muted flex-shrink-0">${t('model_settings.templates_refinement_model')}:</span>
                                <select id="ms-tmpl-model" class="input text-xs font-mono flex-1"></select>
                                <input type="text" id="ms-tmpl-instructions" class="input text-xs flex-1" placeholder="${t('model_settings.templates_instructions_placeholder')}">
                                <button id="ms-tmpl-toggle-all" class="btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" title="Show or hide all template editors">View All</button>
                            </div>
                            <div id="ms-templates-list" class="space-y-3">
                                <p class="text-xs text-brand-text-muted text-center py-4">Loading templates...</p>
                            </div>
                        </div>

                        <!-- Tab: Custom Models -->
                        <div class="ms-tab-panel hidden" data-ms-panel="custom-models">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-xs text-brand-text-muted">${t('custom_models.subtitle')}</p>
                                <div class="flex gap-2">
                                    <button id="ms-cm-hf-token" class="btn btn-sm text-xs flex items-center gap-1 border border-amber-500/30 text-amber-300 hover:bg-amber-500/10 rounded-lg px-3 py-1.5" title="Manage your shared HuggingFace token for gated models">
                                        🔑 HF Token
                                    </button>
                                    <button id="ms-cm-add" class="btn btn-sm text-xs flex items-center gap-1 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 rounded-lg px-3 py-1.5" title="${t('custom_models.add_model_advanced_hint')}">
                                        + ${t('custom_models.add_model')} <span class="text-[8px] opacity-50">(${t('custom_models.advanced')})</span>
                                    </button>
                                    <button id="ms-cm-refresh" class="btn btn-secondary btn-sm text-xs flex items-center gap-1">
                                        🔄 ${t('custom_models.refresh_status') || 'Refresh Status'}
                                    </button>
                                </div>
                            </div>
                            <div id="ms-custom-models-content">
                                <p class="text-xs text-brand-text-muted">Loading custom models catalog...</p>
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
                    </div>  <!-- end tab content -->
                    </div>  <!-- end flex (sidebar + content) -->

                    <!-- Footer -->
                    <div class="flex-shrink-0 flex items-center justify-end px-6 py-3 border-t border-brand-border bg-black/10">
                        <button class="ms-close btn btn-sm text-xs px-6 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">Close</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            this._attachEvents(modal);

            // Activate requested tab (if opened from a specific studio)
            if (this._requestedTab) {
                const targetTab = modal.querySelector(`[data-ms-tab="${this._requestedTab}"]`);
                if (targetTab) {
                    targetTab.click();
                }
                this._requestedTab = null;
            }
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

            const _purposeColors = ['text-brand-accent', 'text-emerald-400', 'text-purple-400', 'text-cyan-400', 'text-amber-400', 'text-pink-400', 'text-teal-400', 'text-indigo-400'];
            return sortedPurposes.map((purpose, idx) => {
                const label = PURPOSE_LABELS[purpose] || purpose;
                const entries = groups[purpose];
                const color = _purposeColors[idx % _purposeColors.length];
                return `
                    <details class="mb-3 ms-collapsible">
                        <summary class="text-sm font-semibold ${color} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">
                            ${label}
                            <span class="text-[10px] font-normal text-brand-text-muted">(${entries.length})</span>
                        </summary>
                        <div class="space-y-2 mt-2">
                            ${entries.map(([key, m]) => this._renderSingleModel(key, m)).join('')}
                        </div>
                    </details>
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

            const _providerColors = ['text-brand-accent', 'text-emerald-400', 'text-purple-400', 'text-cyan-400', 'text-amber-400', 'text-pink-400', 'text-teal-400', 'text-indigo-400'];
            return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0])).map(([provider, entries], idx) => {
                const color = _providerColors[idx % _providerColors.length];
                return `
                    <details class="mb-3 ms-collapsible">
                        <summary class="text-sm font-semibold ${color} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">
                            ${this._esc(provider)}
                            <span class="text-[10px] font-normal text-brand-text-muted">(${entries.length})</span>
                        </summary>
                        <div class="space-y-1.5 mt-2">
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
                    </details>`;
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
            const chatModels = this._registry?.chat_models || {};
            const currentId = cat.current || '';
            const familyOf = (id) => {
                const tail = id.replace(/^us\./, '').split('.').pop() || '';
                return tail.replace(/-\d.*/, '').toLowerCase();
            };
            const currentFamily = familyOf(currentId);

            // Build options grouped by provider
            const groups = {};
            Object.entries(chatModels)
                .filter(([, m]) => m.enabled !== false)
                .forEach(([, m]) => {
                    const provider = m.provider || 'Other';
                    if (!groups[provider]) groups[provider] = [];
                    const mid = m.model_id || '';
                    const isMatch = mid === currentId
                        || currentId.includes(mid.replace('us.', ''))
                        || mid.includes(currentId.replace('us.', ''))
                        || (currentFamily && familyOf(mid) === currentFamily);
                    const regions = (m.available_regions || []).length;
                    groups[provider].push({ mid: currentId && isMatch ? currentId : mid, label: m.label || mid, provider, regions, region: m.region || '', selected: isMatch });
                });

            let optionsHtml = '';
            for (const [provider, models] of Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]))) {
                optionsHtml += `<optgroup label="${this._esc(provider)}">`;
                models.sort((a, b) => a.label.localeCompare(b.label)).forEach(m => {
                    optionsHtml += `<option value="${this._esc(m.mid)}" data-region="${this._esc(m.region)}" ${m.selected ? 'selected' : ''}>${this._esc(m.label)}${m.regions > 1 ? ` (${m.regions} regions)` : ''}</option>`;
                });
                optionsHtml += '</optgroup>';
            }

            // Fallback if current model not in list
            const hasMatch = Object.values(chatModels).some(m => {
                const mid = m.model_id || '';
                return mid === currentId || currentId.includes(mid.replace('us.', '')) || mid.includes(currentId.replace('us.', '')) || (currentFamily && familyOf(mid) === currentFamily);
            });
            const fallbackOpt = !hasMatch && currentId ? `<option value="${this._esc(currentId)}" selected>${this._esc(currentId)} (current)</option>` : '';

            // Find current model label for display
            let currentLabel = currentId;
            for (const m of Object.values(chatModels)) {
                const mid = m.model_id || '';
                if (mid === currentId || currentId.includes(mid.replace('us.', '')) || mid.includes(currentId.replace('us.', '')) || (currentFamily && familyOf(mid) === currentFamily)) {
                    currentLabel = m.label || mid;
                    break;
                }
            }

            return `
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border" data-category="${name}">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm font-medium">${this._esc(cat.label || name)}</span>
                        <span class="text-[10px] text-brand-text-muted font-mono bg-brand-bg px-2 py-0.5 rounded">${this._esc(cat.region || '')}</span>
                    </div>
                    <p class="text-[10px] text-brand-text-muted/50 mb-2">${this._esc(cat.description || '')}</p>
                    <div class="flex gap-2">
                        <div class="flex-1 relative ms-searchable-select">
                            <input type="text" class="ms-cat-search input text-xs w-full" data-cat="${name}" placeholder="${t('custom_models.search_models')}" value="${this._esc(currentLabel)}" autocomplete="off" />
                            <select class="ms-cat-model hidden" data-cat="${name}">
                                ${fallbackOpt}
                                ${optionsHtml}
                            </select>
                            <div class="ms-cat-dropdown hidden absolute left-0 right-0 top-full mt-1 z-50 bg-brand-surface border border-brand-border rounded-lg shadow-xl max-h-60 overflow-y-auto"></div>
                        </div>
                        <input type="text" class="ms-cat-region input text-xs w-28" value="${this._esc(cat.region || '')}" data-cat="${name}" placeholder="${t('common.region')}" />
                        <button class="ms-cat-save btn btn-primary btn-sm text-xs" data-cat="${name}">${t('common.save')}</button>
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
                <details class="ms-collapsible">
                    <summary class="text-sm font-semibold text-purple-400 uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('model_settings.custom_llms')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(models).length})</span></summary>
                    <p class="text-[10px] text-brand-text-muted mb-2 mt-2">${t('model_settings.custom_llms_desc')}</p>
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
                </details>
            `;
        },

        _renderPostProcess(key, m) {
            // Build model options filtered to ONLY models matching this entry's purpose
            const imgModels = this._registry?.image_models || {};
            const currentId = m.model_id || '';
            const familyOf = (id) => (id || '').replace(/^us\./, '').split('.').pop().replace(/-\d.*/, '').toLowerCase();
            const currentFamily = familyOf(currentId);

            // Determine which purposes match this post-processing entry
            const purposeFilter = key.includes('remove') || key.includes('bg')
                ? (p) => p === 'remove_background'
                : key.includes('conservative')
                ? (p) => p === 'upscale_conservative'
                : key.includes('fast')
                ? (p) => p === 'upscale_fast'
                : key.includes('upscale')
                ? (p) => p.includes('upscale')  // "upscale" entry shows all upscale types
                : (p) => p.includes('upscale') || p === 'remove_background';

            // Deduplicate by model family (same model in multiple regions → one option)
            const seenFamilies = new Set();
            const modelOptions = Object.entries(imgModels)
                .filter(([, im]) => {
                    const p = im.model_purpose || '';
                    if (!purposeFilter(p)) return false;
                    const fam = familyOf(im.model_id || '');
                    if (seenFamilies.has(fam)) return false;
                    seenFamilies.add(fam);
                    return true;
                })
                .sort((a, b) => (a[1].label || '').localeCompare(b[1].label || ''))
                .map(([, im]) => {
                    const mid = im.model_id || '';
                    const isMatch = mid === currentId || familyOf(mid) === currentFamily;
                    return `<option value="${this._esc(isMatch ? currentId : mid)}" data-region="${this._esc(im.region || '')}" ${isMatch ? 'selected' : ''}>${this._esc(im.label || mid)} (${this._esc(im.provider || '')})</option>`;
                }).join('');
            const hasMatch = modelOptions.includes('selected');
            const fallbackOpt = !hasMatch && currentId ? `<option value="${this._esc(currentId)}" selected>${this._esc(m.label || currentId)}</option>` : '';

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
                        <select class="ms-pp-field input text-xs font-mono flex-1" data-key="${key}" data-field="model_id">
                            ${fallbackOpt}
                            ${modelOptions}
                        </select>
                        <input type="text" class="ms-pp-field input text-xs w-28" value="${this._esc(m.region || '')}" data-key="${key}" data-field="region" />
                        <button class="ms-pp-save btn btn-primary btn-sm text-xs" data-key="${key}">${t('common.save')}</button>
                    </div>
                </div>
            `;
        },

        _attachEvents(modal) {
            // Close — notify studios to refresh their model dropdowns
            const _closeModal = () => {
                modal.remove();
                window.dispatchEvent(new CustomEvent('model-settings-closed'));
            };
            modal.querySelectorAll('.ms-close').forEach(btn => btn.addEventListener('click', _closeModal));
            modal.addEventListener('click', (e) => { if (e.target === modal) _closeModal(); });

            // Tab switching
            modal.querySelectorAll('[data-ms-tab]').forEach(tab => {
                tab.addEventListener('click', () => {
                    modal.querySelectorAll('[data-ms-tab]').forEach(t2 => {
                        t2.classList.remove('active', 'bg-brand-accent/10', 'text-brand-accent', 'border-l-2', 'border-brand-accent');
                        t2.classList.add('text-brand-text-muted');
                    });
                    tab.classList.add('active', 'bg-brand-accent/10', 'text-brand-accent', 'border-l-2', 'border-brand-accent');
                    tab.classList.remove('text-brand-text-muted');
                    modal.querySelectorAll('.ms-tab-panel').forEach(p => {
                        p.classList.toggle('hidden', p.dataset.msPanel !== tab.dataset.msTab);
                    });
                    // Load templates on first click
                    if (tab.dataset.msTab === 'prompt-templates' && !this._templatesLoaded) {
                        this._loadTemplates(modal);
                    }
                    // Load custom models catalog on first click
                    if (tab.dataset.msTab === 'custom-models' && !this._customModelsLoaded) {
                        this._loadCustomModels(modal);
                    }
                    // Wire custom models buttons (once)
                    if (tab.dataset.msTab === 'custom-models') {
                        const refreshBtn = modal.querySelector('#ms-cm-refresh');
                        if (refreshBtn && !refreshBtn._wired) {
                            refreshBtn._wired = true;
                            refreshBtn.addEventListener('click', () => {
                                this._customModelsLoaded = false;
                                this._loadCustomModels(modal);
                            });
                        }
                        const addBtn = modal.querySelector('#ms-cm-add');
                        if (addBtn && !addBtn._wired) {
                            addBtn._wired = true;
                            addBtn.addEventListener('click', () => this._addCustomModelWizard(modal));
                        }
                        const hfTokenBtn = modal.querySelector('#ms-cm-hf-token');
                        if (hfTokenBtn && !hfTokenBtn._wired) {
                            hfTokenBtn._wired = true;
                            hfTokenBtn.addEventListener('click', () => this._manageHfToken(modal));
                        }
                    }
                });
            });

            // Default: open the first section in each tab on fresh load
            modal.querySelectorAll('.ms-tab-panel').forEach(panel => {
                const sections = panel.querySelectorAll('details.ms-collapsible');
                if (sections.length > 0) {
                    sections[0].open = true;  // First section open
                    for (let i = 1; i < sections.length; i++) sections[i].open = false;  // Rest collapsed
                }
            });

            // Toggle all sections per tab (Show All / Hide All)
            modal.querySelectorAll('.ms-toggle-sections').forEach(btn => {
                let expanded = false;
                btn.addEventListener('click', () => {
                    expanded = !expanded;
                    const panel = btn.dataset.panel;
                    const container = modal.querySelector(`[data-ms-panel="${panel}"]`);
                    if (container) {
                        container.querySelectorAll('details.ms-collapsible').forEach(d => { d.open = expanded; });
                    }
                    btn.textContent = expanded ? 'Hide All' : 'Show All';
                });
            });

            // Prompt Templates: View All only toggles GROUP sections (not inner editors)
            let _tmplGroupsExpanded = false;
            modal.querySelector('#ms-tmpl-toggle-all')?.addEventListener('click', () => {
                _tmplGroupsExpanded = !_tmplGroupsExpanded;
                const btn = modal.querySelector('#ms-tmpl-toggle-all');
                // Only toggle the top-level group <details>, not inner template <details>
                modal.querySelectorAll('#ms-templates-list > details.ms-collapsible').forEach(d => {
                    d.open = _tmplGroupsExpanded;
                });
                if (btn) btn.textContent = _tmplGroupsExpanded ? 'Hide All' : 'View All';
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

                // Show progress overlay (dismissible — sync continues in background)
                const overlay = this._showSyncProgress();

                try {
                    const result = await API.admin.refreshAll();
                    const customMsg = result.total_custom > 0 ? `\n${t('model_settings.sync_custom_count', {count: result.total_custom})}` : '';
                    const disabledMsg = result.disabled?.length ? `\n${t('model_settings.sync_disabled_count', {count: result.disabled.length})}` : '';

                    this._registry = await API.admin.getModels();
                    const imgCount = Object.keys(this._registry.image_models || {}).length;
                    const vidCount = Object.keys(this._registry.video_models || {}).length;
                    const chatModels = Object.keys(this._registry.chat_models || {}).length;

                    // Close progress overlay and refresh modal
                    overlay?.remove();
                    modal.remove();
                    this._renderModal();

                    await window.showConfirm(
                        t('model_settings.sync_scanned', {count: result.regions_scanned}), {
                        title: t('model_settings.sync_complete'),
                        detail: `${t('model_settings.sync_new')}: ${result.total_new}\n${t('model_settings.sync_updated')}: ${result.total_updated}${customMsg}${disabledMsg}\n\n${t('model_settings.sync_totals')}:\n  ${t('model_settings.sync_image')}: ${imgCount}\n  ${t('model_settings.sync_video')}: ${vidCount}\n  ${t('model_settings.sync_chat')}: ${chatModels}\n  ${t('model_settings.sync_errors')}: ${result.errors || 0}`,
                        confirmLabel: t('common.ok'),
                        cancelLabel: '',
                    });
                } catch (err) {
                    overlay?.remove();
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

            // Searchable model dropdowns for categories
            modal.querySelectorAll('.ms-searchable-select').forEach(wrapper => {
                const searchInput = wrapper.querySelector('.ms-cat-search');
                const hiddenSelect = wrapper.querySelector('.ms-cat-model');
                const dropdown = wrapper.querySelector('.ms-cat-dropdown');
                if (!searchInput || !hiddenSelect || !dropdown) return;

                // Build dropdown items from select options (grouped by optgroup)
                const buildDropdown = (filter = '') => {
                    const lower = filter.toLowerCase();
                    let html = '';
                    let hasResults = false;
                    hiddenSelect.querySelectorAll('optgroup, option').forEach(el => {
                        if (el.tagName === 'OPTGROUP') {
                            const groupLabel = el.label || '';
                            const options = Array.from(el.querySelectorAll('option'))
                                .filter(o => !lower || o.textContent.toLowerCase().includes(lower) || groupLabel.toLowerCase().includes(lower));
                            if (options.length > 0) {
                                html += `<div class="px-3 py-1 text-[9px] text-brand-text-muted/50 uppercase tracking-wider font-semibold bg-black/20 sticky top-0">${wrapper.parentElement.closest('[data-category]') ? '' : ''}${groupLabel}</div>`;
                                options.forEach(o => {
                                    const selected = o.selected ? 'bg-brand-accent/10 text-brand-accent' : 'hover:bg-white/5';
                                    html += `<div class="ms-dd-item px-3 py-1.5 text-xs cursor-pointer ${selected}" data-value="${o.value}" data-region="${o.dataset.region || ''}">${o.textContent}</div>`;
                                });
                                hasResults = true;
                            }
                        } else if (!el.closest('optgroup')) {
                            if (!lower || el.textContent.toLowerCase().includes(lower)) {
                                const selected = el.selected ? 'bg-brand-accent/10 text-brand-accent' : 'hover:bg-white/5';
                                html += `<div class="ms-dd-item px-3 py-1.5 text-xs cursor-pointer ${selected}" data-value="${el.value}" data-region="${el.dataset.region || ''}">${el.textContent}</div>`;
                                hasResults = true;
                            }
                        }
                    });
                    if (!hasResults) html = `<div class="px-3 py-2 text-xs text-brand-text-muted">${t('custom_models.no_search_results')}</div>`;
                    dropdown.innerHTML = html;

                    // Wire click handlers
                    dropdown.querySelectorAll('.ms-dd-item').forEach(item => {
                        item.addEventListener('click', () => {
                            hiddenSelect.value = item.dataset.value;
                            searchInput.value = item.textContent.trim();
                            dropdown.classList.add('hidden');
                            // Auto-populate region
                            const regionInput = wrapper.closest('[data-category]')?.querySelector('.ms-cat-region');
                            if (item.dataset.region && regionInput) regionInput.value = item.dataset.region;
                        });
                    });
                };

                searchInput.addEventListener('focus', () => {
                    buildDropdown(searchInput.value === searchInput.defaultValue ? '' : searchInput.value);
                    dropdown.classList.remove('hidden');
                    searchInput.select();
                });
                searchInput.addEventListener('input', () => {
                    buildDropdown(searchInput.value);
                    dropdown.classList.remove('hidden');
                });
                // Close on click outside
                document.addEventListener('click', (e) => {
                    if (!wrapper.contains(e.target)) dropdown.classList.add('hidden');
                });
            });

            // Auto-populate region when post-processing model selected
            modal.querySelectorAll('[data-pp] select.ms-pp-field').forEach(sel => {
                sel.addEventListener('change', () => {
                    const opt = sel.selectedOptions[0];
                    const region = opt?.dataset.region;
                    const regionInput = sel.closest('[data-pp]')?.querySelector('input.ms-pp-field[data-field="region"]');
                    if (region && regionInput) regionInput.value = region;
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

        async _loadTemplates(modal) {
            const container = modal.querySelector('#ms-templates-list');
            if (!container) return;
            try {
                // Load templates
                const resp = await fetch('/api/admin/templates');
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                this._templatesLoaded = true;
                this._templatesData = data.templates || {};

                // Populate model dropdown for refinement (reuse chat models)
                const modelSel = modal.querySelector('#ms-tmpl-model');
                if (modelSel && modelSel.options.length <= 1) {
                    try {
                        const modelResp = await fetch('/api/chat/models');
                        const modelData = await modelResp.json();
                        modelSel.innerHTML = (modelData.models || []).map(m =>
                            `<option value="${this._esc(m.model_id)}" data-region="${this._esc(m.region)}">${this._esc(m.label)} (${this._esc(m.provider)})</option>`
                        ).join('');
                    } catch { modelSel.innerHTML = '<option value="">No models available</option>'; }
                }

                this._renderTemplates(modal);
            } catch (err) {
                container.innerHTML = `<p class="text-xs text-red-400 py-4">Failed to load templates: ${this._esc(err.message)}</p>`;
            }
        },

        _renderTemplates(modal) {
            const container = modal.querySelector('#ms-templates-list');
            if (!container || !this._templatesData) return;
            const templates = this._templatesData;

            // Group templates by studio/area with user-friendly labels
            const GROUPS = [
                { key: 'image_studio', label: t('nav.image_studio'), color: 'text-brand-accent', templates: [
                    { name: 'image_refine_single', friendlyLabel: 'Prompt Refinement — how your text is turned into a detailed image prompt' },
                    { name: 'image_concepts_multi', friendlyLabel: 'Creative Options — how multiple distinct concepts are generated from one idea' },
                    { name: 'image_refine_marketing', friendlyLabel: 'Marketing Banners — specialized prompt for banner compositions' },
                ]},
                { key: 'style_library', label: t('nav.style_library'), color: 'text-purple-400', templates: [
                    { name: 'style_analysis_full', friendlyLabel: 'Style Analysis — how reference images are analyzed for visual attributes' },
                    { name: 'style_hints_generation', friendlyLabel: 'Style Hints — how analyzed style is distilled into generation directives' },
                    { name: 'style_cohesion_check', friendlyLabel: 'Cohesion Check — quick check if references are unified or diverse' },
                ]},
                { key: 'moderation', label: 'Content Safety', color: 'text-amber-400', templates: [
                    { name: 'moderation_prescreen', friendlyLabel: 'Pre-Screen — predicts if a prompt will be blocked before generating' },
                    { name: 'moderation_rewrite', friendlyLabel: 'Rewrite — rewrites blocked prompts to pass moderation' },
                ]},
                { key: 'video_studio', label: t('nav.video_studio'), color: 'text-emerald-400', templates: [
                    { name: 'video_enhance_prompt', friendlyLabel: 'Prompt Enhancement — adds camera movements, lighting, and temporal cues' },
                ]},
                { key: 'type_studio', label: t('nav.type_studio'), color: 'text-cyan-400', templates: [
                    { name: 'typestudio_layout', friendlyLabel: 'Text Layout — designs text positions, fonts, sizes, and effects' },
                ]},
                { key: 'chat_studio', label: t('nav.chat_studio'), color: 'text-indigo-400', templates: [
                    { name: 'chat_context_compact', friendlyLabel: 'Context Compaction — summarizes older messages to free context space' },
                    { name: 'chat_title_generate', friendlyLabel: 'Session Title — auto-generates a title from the first exchange' },
                ]},
                { key: 'translation', label: 'Translation', color: 'text-teal-400', templates: [
                    { name: 'translate_detect_language', friendlyLabel: 'Language Detection — detects language when heuristics are ambiguous' },
                    { name: 'translate_to_english', friendlyLabel: 'Translation to English — translates non-English prompts before generation' },
                ]},
            ];

            container.innerHTML = GROUPS.map(group => {
                const groupTemplates = group.templates.filter(gt => templates[gt.name]);
                if (groupTemplates.length === 0) return '';
                return `
                    <details class="mb-4 ms-collapsible">
                        <summary class="text-sm font-semibold ${group.color} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${this._esc(group.label)} <span class="text-[10px] font-normal text-brand-text-muted">(${groupTemplates.length})</span></summary>
                        <div class="mt-2">
                            <div class="flex justify-end mb-1">
                                <button class="ms-tmpl-group-toggle text-[9px] text-brand-text-muted hover:text-brand-accent cursor-pointer" data-group="${group.key}">Expand editors</button>
                            </div>
                            <div class="space-y-2">
                                ${groupTemplates.map(gt => {
                                    const name = gt.name;
                                    const tmpl = templates[name];
                                    return this._renderSingleTemplate(name, tmpl, gt.friendlyLabel);
                                }).join('')}
                            </div>
                        </div>
                    </details>`;
            }).join('');

            // Default: open the first group section on fresh load
            const tmplSections = container.querySelectorAll('details.ms-collapsible');
            if (tmplSections.length > 0 && !Array.from(tmplSections).some(d => d.open)) {
                tmplSections[0].open = true;
            }

            this._attachTemplateEvents(container, modal, templates);
        },

        _renderSingleTemplate(name, tmpl, friendlyLabel) {
            const modified = tmpl.modified ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20 ml-2">${t('model_settings.templates_modified')}</span>` : '';
            const vars = (tmpl.variables || []).map(v => `<code class="text-[9px] text-brand-accent bg-brand-accent/10 px-1 rounded">${this._esc(v)}</code>`).join(' ');
            return `
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border" data-tmpl="${this._esc(name)}">
                    <div class="flex items-center justify-between mb-1">
                        <div class="flex items-center gap-2">
                            <span class="text-sm font-medium">${this._esc(friendlyLabel || tmpl.label || name)}</span>
                            ${modified}
                        </div>
                        <span class="text-[9px] text-brand-text-muted">${this._esc(tmpl.model || '')}</span>
                    </div>
                    <p class="text-[10px] text-brand-text-muted/60 mb-2">${t('model_settings.templates_variables')}: ${vars || 'none'}</p>
                    <details class="group">
                        <summary class="text-[10px] text-brand-accent cursor-pointer hover:text-brand-accent-hover">
                            <span class="group-open:hidden">${t('model_settings.templates_edit')}</span>
                            <span class="hidden group-open:inline">${t('model_settings.templates_close_editor')}</span>
                        </summary>
                        <div class="mt-2 space-y-2">
                            <textarea class="ms-tmpl-text input w-full h-48 font-mono text-xs resize-y" data-tmpl="${this._esc(name)}" spellcheck="false">${this._esc(tmpl.text || '')}</textarea>
                            <div class="flex gap-2 flex-wrap">
                                <button class="ms-tmpl-save btn btn-primary btn-sm text-xs" data-tmpl="${this._esc(name)}">${t('model_settings.templates_save')}</button>
                                <button class="ms-tmpl-enhance btn btn-sm text-xs bg-purple-600 hover:bg-purple-500 text-white" data-tmpl="${this._esc(name)}">${t('model_settings.templates_enhance')}</button>
                                <button class="ms-tmpl-reset btn btn-sm text-xs border border-brand-border text-brand-text-muted hover:border-amber-500 hover:text-amber-400" data-tmpl="${this._esc(name)}">${t('model_settings.templates_reset')}</button>
                            </div>
                            <div class="ms-tmpl-suggestion hidden mt-2 p-2 rounded-lg bg-purple-950/20 border border-purple-500/20" data-tmpl="${this._esc(name)}">
                                <div class="flex items-center justify-between mb-1">
                                    <span class="text-[10px] text-purple-400 font-medium">${t('model_settings.templates_ai_suggestion')}</span>
                                    <div class="flex gap-1">
                                        <button class="ms-tmpl-accept text-[10px] px-2 py-0.5 rounded bg-purple-600 text-white hover:bg-purple-500" data-tmpl="${this._esc(name)}">${t('model_settings.templates_accept')}</button>
                                        <button class="ms-tmpl-dismiss text-[10px] px-2 py-0.5 rounded bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent" data-tmpl="${this._esc(name)}">${t('model_settings.templates_dismiss')}</button>
                                    </div>
                                </div>
                                <div class="ms-tmpl-suggestion-warning hidden text-[10px] text-amber-400 mb-1"></div>
                                <pre class="ms-tmpl-suggestion-text text-xs font-mono whitespace-pre-wrap text-purple-200/70 max-h-48 overflow-auto"></pre>
                            </div>
                        </div>
                    </details>
                </div>`;
        },

        _attachTemplateEvents(container, modal, templates) {
            // Per-group expand/collapse for template editors within each group
            container.querySelectorAll('.ms-tmpl-group-toggle').forEach(btn => {
                let expanded = false;
                btn.addEventListener('click', () => {
                    expanded = !expanded;
                    const group = btn.dataset.group;
                    const groupEl = btn.closest('details.ms-collapsible');
                    if (groupEl) {
                        groupEl.querySelectorAll('details.group').forEach(d => { d.open = expanded; });
                    }
                    btn.textContent = expanded ? 'Collapse editors' : 'Expand editors';
                });
            });

            // Save handlers (with variable validation)
            container.querySelectorAll('.ms-tmpl-save').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const name = btn.dataset.tmpl;
                    const textarea = container.querySelector(`.ms-tmpl-text[data-tmpl="${name}"]`);
                    if (!textarea) return;
                    btn.disabled = true;

                    const doSave = async (force = false) => {
                        const resp = await fetch(`/api/admin/templates/${encodeURIComponent(name)}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ text: textarea.value, force }),
                        });
                        if (resp.ok) {
                            window.showToast?.(t('model_settings.templates_saved'), 'success');
                            this._templatesLoaded = false;
                            this._loadTemplates(modal);
                            return true;
                        }
                        return resp;
                    };

                    try {
                        const result = await doSave(false);
                        if (result !== true) {
                            // Validation failed — show missing variables warning
                            const err = await result.json();
                            const detail = err.detail;
                            const missing = typeof detail === 'object' ? detail.missing_variables : [];
                            const message = typeof detail === 'object' ? detail.message : (detail || 'Unknown error');

                            if (missing?.length || (typeof message === 'string' && message.includes('missing'))) {
                                const varList = missing?.join(', ') || message;
                                const doFix = await window.showConfirm?.(
                                    'Required variables are missing from your template.', {
                                    title: 'Missing Variables',
                                    detail: `Missing: ${varList}\n\nThese variables are replaced with actual values at runtime. Without them, the feature won't receive the expected input.\n\nClick "Fix & Save" to let the AI insert the missing variables in the right places automatically.`,
                                    confirmLabel: 'Fix & Save',
                                });
                                if (doFix) {
                                    // Call API with fix_variables=true
                                    btn.textContent = 'Fixing...';
                                    const fixResp = await fetch(`/api/admin/templates/${encodeURIComponent(name)}`, {
                                        method: 'PATCH',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ text: textarea.value, fix_variables: true }),
                                    });
                                    if (fixResp.ok) {
                                        const fixResult = await fixResp.json();
                                        window.showToast?.(`Template fixed and saved — ${fixResult.fixed_variables?.length || 0} variables inserted`, 'success');
                                        this._templatesLoaded = false;
                                        this._loadTemplates(modal);
                                    } else {
                                        const fixErr = await fixResp.json();
                                        window.showToast?.(t('model_settings.templates_save_failed') + ': ' + (fixErr.detail || ''), 'error');
                                    }
                                }
                            } else {
                                window.showToast?.(t('model_settings.templates_save_failed') + ': ' + message, 'error');
                            }
                        }
                    } catch (err) {
                        window.showToast?.(t('model_settings.templates_save_failed') + ': ' + err.message, 'error');
                    }
                    btn.disabled = false;
                });
            });

            // Enhance with AI handlers
            container.querySelectorAll('.ms-tmpl-enhance').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const name = btn.dataset.tmpl;
                    const modelSel = modal.querySelector('#ms-tmpl-model');
                    const modelId = modelSel?.value;
                    const region = modelSel?.selectedOptions[0]?.dataset.region || '';
                    const instructions = modal.querySelector('#ms-tmpl-instructions')?.value || '';

                    if (!modelId) { window.showToast?.(t('model_settings.templates_no_model'), 'warning'); return; }

                    btn.disabled = true;
                    const origText = btn.textContent;
                    btn.textContent = t('model_settings.templates_enhancing');

                    try {
                        const resp = await fetch(`/api/admin/templates/${encodeURIComponent(name)}/enhance`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ model_id: modelId, region, instructions }),
                        });
                        if (!resp.ok) {
                            const err = await resp.json();
                            throw new Error(err.detail || `HTTP ${resp.status}`);
                        }
                        const result = await resp.json();

                        // Show suggestion
                        const suggBox = container.querySelector(`.ms-tmpl-suggestion[data-tmpl="${name}"]`);
                        const suggText = suggBox?.querySelector('.ms-tmpl-suggestion-text');
                        const suggWarn = suggBox?.querySelector('.ms-tmpl-suggestion-warning');
                        if (suggBox && suggText) {
                            suggText.textContent = result.improved;
                            if (result.warning) {
                                suggWarn.textContent = result.warning;
                                suggWarn.classList.remove('hidden');
                            } else {
                                suggWarn.classList.add('hidden');
                            }
                            suggBox.classList.remove('hidden');
                        }
                    } catch (err) {
                        window.showToast?.(t('model_settings.templates_enhance_failed') + ': ' + err.message, 'error');
                    }
                    btn.disabled = false;
                    btn.textContent = origText;
                });
            });

            // Accept suggestion handlers
            container.querySelectorAll('.ms-tmpl-accept').forEach(btn => {
                btn.addEventListener('click', () => {
                    const name = btn.dataset.tmpl;
                    const suggBox = container.querySelector(`.ms-tmpl-suggestion[data-tmpl="${name}"]`);
                    const suggText = suggBox?.querySelector('.ms-tmpl-suggestion-text')?.textContent;
                    const textarea = container.querySelector(`.ms-tmpl-text[data-tmpl="${name}"]`);
                    if (textarea && suggText) {
                        textarea.value = suggText;
                        suggBox?.classList.add('hidden');
                        window.showToast?.(t('model_settings.templates_accepted_hint'), 'info');
                    }
                });
            });

            // Dismiss suggestion handlers
            container.querySelectorAll('.ms-tmpl-dismiss').forEach(btn => {
                btn.addEventListener('click', () => {
                    const name = btn.dataset.tmpl;
                    container.querySelector(`.ms-tmpl-suggestion[data-tmpl="${name}"]`)?.classList.add('hidden');
                });
            });

            // Reset handlers
            container.querySelectorAll('.ms-tmpl-reset').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const name = btn.dataset.tmpl;
                    if (!await window.showConfirm?.(t('model_settings.templates_reset_confirm'), { title: t('model_settings.templates_reset_title'), confirmLabel: t('image_studio.reset'), danger: true })) return;
                    try {
                        await fetch(`/api/admin/templates/${encodeURIComponent(name)}/reset`, { method: 'POST' });
                        window.showToast?.(t('model_settings.templates_reset_done'), 'success');
                        this._templatesLoaded = false;
                        this._loadTemplates(modal);
                    } catch (err) {
                        window.showToast?.('Reset failed: ' + err.message, 'error');
                    }
                });
            });
        },

        _showSyncProgress() {
            const overlay = document.createElement('div');
            overlay.className = 'fixed inset-0 z-[150] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4';
            overlay.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-4">
                    <div class="flex items-center justify-between">
                        <h3 class="text-sm font-semibold text-brand-text">${t('model_settings.sync_progress_title')}</h3>
                        <button class="sync-dismiss text-brand-text-muted hover:text-brand-text text-lg leading-none" title="${t('model_settings.sync_dismiss')}">&times;</button>
                    </div>
                    <p class="text-[10px] text-brand-text-muted">${t('model_settings.sync_progress_hint')}</p>
                    <div class="bg-black/20 rounded-lg p-3 space-y-2">
                        <p class="sync-msg text-xs text-brand-accent font-medium">${t('model_settings.syncing')}...</p>
                        <div class="sync-counts text-[10px] text-brand-text-muted flex gap-4"></div>
                        <div class="sync-log text-[10px] text-brand-text-muted/50 max-h-40 overflow-y-auto font-mono space-y-0.5"></div>
                    </div>
                </div>`;
            document.body.appendChild(overlay);

            overlay.querySelector('.sync-dismiss')?.addEventListener('click', () => overlay.remove());

            // Connect to SSE for real-time progress
            let sse;
            try {
                sse = new EventSource('/api/sync-progress');
                sse.onmessage = (e) => {
                    try {
                        const d = JSON.parse(e.data);
                        if (d.ready || d.message === 'done') { sse.close(); return; }
                        const msgEl = overlay.querySelector('.sync-msg');
                        if (msgEl) msgEl.textContent = d.message;
                        const countsEl = overlay.querySelector('.sync-counts');
                        if (countsEl && d.models) {
                            const parts = [];
                            if (d.models.image) parts.push(`🖼 ${d.models.image} ${t('model_settings.sync_image').toLowerCase()}`);
                            if (d.models.chat) parts.push(`💬 ${d.models.chat} ${t('model_settings.sync_chat').toLowerCase()}`);
                            if (d.models.video) parts.push(`🎬 ${d.models.video} ${t('model_settings.sync_video').toLowerCase()}`);
                            if (parts.length) countsEl.textContent = parts.join('  ·  ');
                        }
                        const logEl = overlay.querySelector('.sync-log');
                        if (logEl && d.message) {
                            const prev = logEl.firstChild;
                            if (prev && prev.dataset.active) {
                                prev.dataset.active = '';
                                prev.textContent = prev.textContent.replace(/^⟳ /, '✓ ');
                                prev.classList.remove('text-brand-accent');
                                prev.classList.add('text-brand-text-muted/40');
                            }
                            const line = document.createElement('div');
                            line.textContent = '⟳ ' + d.message;
                            line.dataset.active = '1';
                            line.classList.add('text-brand-accent');
                            logEl.prepend(line);
                        }
                    } catch {}
                };
                sse.onerror = () => { sse.close(); };
            } catch {}

            // Clean up SSE when overlay is removed
            const observer = new MutationObserver(() => {
                if (!document.body.contains(overlay)) { sse?.close(); observer.disconnect(); }
            });
            observer.observe(document.body, { childList: true });

            return overlay;
        },

        _showDeployDialog(modelKey, instanceOptions, recommendedInstance, minVram, deployRegion, textureBackends = null) {
            return new Promise((resolve) => {
                const available = instanceOptions.filter(o => !o.needs_quota);
                const needsQuota = instanceOptions.filter(o => o.needs_quota);

                // Texture-backend picker (registry-driven). Rendered only when the
                // model offers selectable backends (e.g. TripoSG: MVPainter/Hunyuan).
                const tbOptions = (textureBackends && textureBackends.options) || null;
                const tbDefault = (textureBackends && textureBackends.default) || (tbOptions ? Object.keys(tbOptions)[0] : null);
                let textureHtml = '';
                if (tbOptions) {
                    const cards = Object.entries(tbOptions).map(([key, b]) => {
                        const lic = b.license || {};
                        // License shown as the standard neutral name pill (matches the
                        // model License Agreement modal) — the license NAME is the
                        // unambiguous signal; the attestation block spells out terms.
                        const licPill = lic.name
                            ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-white/5 border border-brand-border/30 text-brand-text-muted">${lic.name}</span>`
                            : '';
                        return `<label class="flex items-start gap-2 cursor-pointer p-2.5 rounded-lg border border-brand-border hover:border-brand-accent/40 has-[:checked]:border-brand-accent/60 has-[:checked]:bg-brand-accent/5">
                            <input type="radio" name="deploy-texbackend" value="${key}" ${key === tbDefault ? 'checked' : ''} class="mt-0.5 deploy-texbackend-radio" data-attest="${lic.attestation_required ? '1' : '0'}" />
                            <div class="min-w-0">
                                <div class="flex items-center gap-2 flex-wrap">
                                    <span class="text-xs font-medium text-brand-text">${b.label || key}</span>
                                    ${licPill}
                                </div>
                                <p class="text-[10px] text-brand-text-muted mt-0.5">${b.description || ''}</p>
                                <p class="text-[10px] text-brand-text-muted/80 mt-0.5">${b.instance_note || ''}</p>
                            </div>
                        </label>`;
                    }).join('');
                    textureHtml = `
                        <div>
                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1.5">${t('custom_models.tex_backend_title')}</label>
                            <div class="space-y-2 deploy-texbackend-group">${cards}</div>
                            <div class="deploy-tex-attest mt-2 p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 hidden">
                                <p class="deploy-tex-attest-warn text-[10px] text-amber-400 mb-1.5"></p>
                                <ul class="deploy-tex-attest-terms text-[9px] text-brand-text-muted list-disc ml-4 mb-2 space-y-0.5"></ul>
                                <div class="deploy-tex-attest-deps mb-2 hidden">
                                    <p class="text-[9px] font-semibold text-brand-text-muted uppercase tracking-wider mb-1">${t('custom_models.tex_attest_deps')}</p>
                                    <div class="deploy-tex-attest-deps-rows space-y-1"></div>
                                </div>
                                <label class="flex items-start gap-2 cursor-pointer">
                                    <input type="checkbox" class="deploy-tex-attest-check mt-0.5" />
                                    <span class="text-[10px] text-brand-text">${t('custom_models.tex_attest_label')} <a class="deploy-tex-attest-link text-brand-accent underline" target="_blank" rel="noopener">${t('custom_models.tex_attest_readlicense')}</a></span>
                                </label>
                            </div>
                        </div>`;
                }

                // Build instance dropdown with ALL options — available first, then needs-quota
                let instanceHtml = '';
                let quotaHtml = '';
                const allOptions = [...available, ...needsQuota];

                if (allOptions.length === 0) {
                    instanceHtml = `<div class="text-xs text-red-400 py-3 space-y-2">
                        <p class="font-medium">${t('custom_models.no_instances')}</p>
                        <p class="text-brand-text-muted">${t('custom_models.no_instances_hint')}</p>
                    </div>`;
                } else {
                    instanceHtml = allOptions.map(opt => {
                        const isRec = opt.is_recommended && !opt.needs_quota;
                        const costStr = `$${opt.cost_per_hour_usd.toFixed(2)}`;
                        const quotaTag = opt.needs_quota
                            ? (opt.quota_reason === 'all_in_use' ? ' ⚠ IN USE' : ' ⚠ NO QUOTA')
                            : '';
                        const usageNote = !opt.needs_quota && opt.quota > 1 ? ` (${opt.quota_available}/${opt.quota} avail)` : '';
                        return `<option value="${opt.instance_type}" ${isRec ? 'selected' : ''} data-cost="${opt.cost_per_hour_usd}" data-needs-quota="${opt.needs_quota}" data-quota-code="${opt.quota_code || ''}" data-quota="${opt.quota || 0}">
                            ${opt.instance_type} — ${opt.gpus}× ${opt.gpu_type} (${opt.total_vram_gb}GB) — ${costStr}/hr ${isRec ? '★' : ''}${opt.speed_note}${usageNote}${quotaTag}
                        </option>`;
                    }).join('');
                }

                // Quota section — shown dynamically when a needs-quota instance is selected
                quotaHtml = `
                    <div class="mt-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 hidden" id="deploy-quota-section">
                        <p class="text-[10px] text-amber-400 font-medium mb-1">${t('custom_models.quota_needed_title')}</p>
                        <p class="text-[9px] text-brand-text-muted mb-2">${t('custom_models.quota_needed_desc').replace('{{region}}', deployRegion || 'unknown')}</p>
                        <div id="deploy-quota-row" class="flex items-center justify-between py-1.5"></div>
                    </div>`;

                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
                backdrop.innerHTML = `
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto">
                        <h3 class="text-sm font-semibold text-brand-text">${t('custom_models.deploy_config_title')}</h3>

                        ${textureHtml}

                        <div>
                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1.5">${t('custom_models.instance')}</label>
                            ${allOptions.length > 0 ? `<select class="deploy-instance input w-full text-xs">${instanceHtml}</select>` : instanceHtml}
                            <p class="deploy-instance-info text-[10px] text-brand-text-muted mt-1"></p>
                            ${quotaHtml}
                        </div>

                        <div>
                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1.5">${t('custom_models.deploy_type_title')}</label>
                            <div class="space-y-2">
                                <label class="flex items-start gap-2 cursor-pointer p-2.5 rounded-lg border border-brand-border hover:border-emerald-500/30 has-[:checked]:border-emerald-500/50 has-[:checked]:bg-emerald-500/5">
                                    <input type="radio" name="deploy-type" value="async" checked class="mt-0.5" />
                                    <div>
                                        <span class="text-xs font-medium text-brand-text">On-Demand (scale-to-zero)</span>
                                        <p class="text-[10px] text-brand-text-muted">$0 when idle. Cold start ~5-15 min on first request. Recommended for development.</p>
                                    </div>
                                </label>
                                <label class="flex items-start gap-2 cursor-pointer p-2.5 rounded-lg border border-brand-border hover:border-amber-500/30 has-[:checked]:border-amber-500/50 has-[:checked]:bg-amber-500/5">
                                    <input type="radio" name="deploy-type" value="realtime" class="mt-0.5" />
                                    <div>
                                        <span class="text-xs font-medium text-brand-text">Always-On (no cold start)</span>
                                        <p class="text-[10px] text-brand-text-muted deploy-always-on-cost">Model stays loaded. Billed continuously even when idle.</p>
                                    </div>
                                </label>
                            </div>
                        </div>

                        <div class="flex gap-2 justify-end pt-2">
                            <button class="deploy-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">Cancel</button>
                            <button class="deploy-confirm btn btn-sm text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium" ${allOptions.length === 0 ? 'disabled' : ''}>${t('custom_models.deploy')}</button>
                        </div>
                    </div>`;

                // Update cost display when instance changes
                const instanceSelect = backdrop.querySelector('.deploy-instance');
                const infoEl = backdrop.querySelector('.deploy-instance-info');
                const alwaysOnCost = backdrop.querySelector('.deploy-always-on-cost');

                const quotaSection = backdrop.querySelector('#deploy-quota-section');
                const quotaRow = backdrop.querySelector('#deploy-quota-row');
                const deployBtn = backdrop.querySelector('.deploy-confirm');
                // Texture-attestation elements — declared HERE (before updateInfo,
                // which can call updateDeployGate during the initial render) to
                // avoid a temporal-dead-zone error referencing them too early.
                const attestBox = backdrop.querySelector('.deploy-tex-attest');
                const attestCheck = backdrop.querySelector('.deploy-tex-attest-check');

                const updateInfo = () => {
                    const sel = instanceSelect?.options[instanceSelect.selectedIndex];
                    if (!sel) return;
                    const cost = parseFloat(sel.dataset.cost || 0);
                    const needsQ = sel.dataset.needsQuota === 'true';
                    const qCode = sel.dataset.quotaCode || '';
                    const qVal = parseInt(sel.dataset.quota || '0');

                    if (infoEl && cost > 0) {
                        infoEl.textContent = `Est. ~$${cost.toFixed(2)}/hr when running`;
                    }
                    if (alwaysOnCost && cost > 0) {
                        alwaysOnCost.textContent = `Model stays loaded. Costs ~$${cost.toFixed(2)}/hr continuously, even when idle.`;
                    }

                    // Show/hide quota section based on selected instance
                    if (quotaSection) {
                        if (needsQ) {
                            quotaSection.classList.remove('hidden');
                            if (quotaRow) {
                                const inst = sel.value;
                                quotaRow.innerHTML = `
                                    <div>
                                        <span class="text-[11px] text-brand-text">${inst}</span>
                                        <span class="text-[9px] text-brand-text-muted/60 ml-1">${qVal > 0 ? t('custom_models.quota_all_in_use').replace('{{used}}', qVal).replace('{{quota}}', qVal) : t('custom_models.quota_none')}</span>
                                    </div>
                                    <button class="quota-request-btn text-[10px] px-2 py-0.5 rounded bg-brand-accent/20 text-brand-accent hover:bg-brand-accent/30"
                                        data-instance="${inst}" data-code="${qCode}" data-desired="${qVal + 1}">
                                        ${t('custom_models.quota_request_btn')}
                                    </button>`;
                            }
                        } else {
                            quotaSection.classList.add('hidden');
                        }
                    }

                    // Enable/disable deploy button. Record the quota block as a
                    // flag so the texture-attestation gate (updateDeployGate) can
                    // compose with it instead of overwriting it.
                    if (deployBtn) {
                        if (needsQ) deployBtn.dataset.quotaBlocked = '1';
                        else delete deployBtn.dataset.quotaBlocked;
                        if (typeof updateDeployGate === 'function') updateDeployGate();
                        else { deployBtn.disabled = needsQ; deployBtn.classList.toggle('opacity-50', needsQ); }
                    }
                };
                instanceSelect?.addEventListener('change', updateInfo);
                updateInfo();

                // ── Texture-backend interaction: filter instances to the chosen
                // backend's allowed set, pre-select its recommended instance, and
                // gate the deploy button on the license attestation. ──
                // (attestBox / attestCheck are declared above, before updateInfo.)
                const syncTextureBackend = () => {
                    if (!tbOptions) return;
                    const sel = backdrop.querySelector('input[name="deploy-texbackend"]:checked');
                    const key = sel?.value;
                    const b = key && tbOptions[key];
                    if (!b) return;
                    // Filter the instance dropdown to this backend's allowed instances.
                    const allowed = b.allowed_instances || null;
                    if (instanceSelect && allowed) {
                        let firstAllowed = null;
                        Array.from(instanceSelect.options).forEach(o => {
                            const ok = allowed.includes(o.value);
                            o.hidden = !ok;
                            o.disabled = !ok;
                            if (ok && firstAllowed === null) firstAllowed = o.value;
                        });
                        // If current selection is now disallowed, pick the backend's
                        // recommended (or first allowed) instance.
                        const cur = instanceSelect.options[instanceSelect.selectedIndex];
                        if (!cur || cur.hidden) {
                            instanceSelect.value = (allowed.includes(b.recommended_instance) ? b.recommended_instance : firstAllowed) || instanceSelect.value;
                        }
                        updateInfo();
                    }
                    // Attestation block for non-commercial backends.
                    const lic = b.license || {};
                    if (lic.attestation_required && attestBox) {
                        attestBox.classList.remove('hidden');
                        const warnEl = attestBox.querySelector('.deploy-tex-attest-warn');
                        const termsEl = attestBox.querySelector('.deploy-tex-attest-terms');
                        const linkEl = attestBox.querySelector('.deploy-tex-attest-link');
                        if (warnEl) warnEl.innerHTML = (lic.warnings || []).map(w => this._esc(w)).join('<br>');
                        if (termsEl) termsEl.innerHTML = (lic.key_terms || []).map(x => `<li>${this._esc(x)}</li>`).join('');
                        if (linkEl && lic.url) linkEl.href = lic.url;
                        // Per-dependency licensing table (name · license · badges · link).
                        // Lets the user see EXACTLY which models/repos are pulled and
                        // each one's license + commercial/gated status before agreeing.
                        const depsBox = attestBox.querySelector('.deploy-tex-attest-deps');
                        const depsRows = attestBox.querySelector('.deploy-tex-attest-deps-rows');
                        const deps = lic.dependencies || [];
                        if (depsBox && depsRows) {
                            if (deps.length) {
                                depsRows.innerHTML = deps.map(d => {
                                    const comm = d.commercial
                                        ? `<span class="text-[8px] px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">commercial-OK</span>`
                                        : `<span class="text-[8px] px-1 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">non-commercial</span>`;
                                    const gated = d.gated
                                        ? `<span class="text-[8px] px-1 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">gated · accept on HF</span>`
                                        : '';
                                    const nameEl = d.url
                                        ? `<a href="${d.url}" target="_blank" rel="noopener" class="text-brand-accent underline">${this._esc(d.name)}</a>`
                                        : `<span class="text-brand-text">${this._esc(d.name)}</span>`;
                                    return `<div class="text-[9px] leading-relaxed">
                                        <div class="flex items-center gap-1.5 flex-wrap">
                                            ${nameEl} ${comm} ${gated}
                                        </div>
                                        <div class="text-brand-text-muted/80">${this._esc(d.license || '')}${d.role ? ' — ' + this._esc(d.role) : ''}</div>
                                    </div>`;
                                }).join('');
                                depsBox.classList.remove('hidden');
                            } else {
                                depsRows.innerHTML = '';
                                depsBox.classList.add('hidden');
                            }
                        }
                        if (attestCheck) attestCheck.checked = false;
                    } else if (attestBox) {
                        attestBox.classList.add('hidden');
                        if (attestCheck) attestCheck.checked = false;
                    }
                    updateDeployGate();
                };
                function updateDeployGate() {
                    if (!deployBtn) return;
                    const sel = backdrop.querySelector('input[name="deploy-texbackend"]:checked');
                    const needAttest = sel?.dataset.attest === '1';
                    const attested = attestCheck?.checked;
                    const blocked = (needAttest && !attested) || !!deployBtn.dataset.quotaBlocked;
                    deployBtn.disabled = blocked;
                    deployBtn.classList.toggle('opacity-50', blocked);
                }
                backdrop.querySelectorAll('input[name="deploy-texbackend"]').forEach(r => r.addEventListener('change', syncTextureBackend));
                attestCheck?.addEventListener('change', updateDeployGate);
                if (tbOptions) syncTextureBackend();

                backdrop.querySelector('.deploy-cancel').addEventListener('click', () => {
                    backdrop.remove();
                    resolve(null);
                });
                backdrop.querySelector('.deploy-confirm')?.addEventListener('click', () => {
                    const instanceType = instanceSelect?.value || recommendedInstance;
                    const endpointType = backdrop.querySelector('input[name="deploy-type"]:checked')?.value || 'async';
                    const texSel = backdrop.querySelector('input[name="deploy-texbackend"]:checked');
                    const textureBackend = texSel?.value || null;
                    const textureLicenseAccepted = !!(attestCheck && attestCheck.checked);
                    backdrop.remove();
                    resolve({ instanceType, endpointType, textureBackend, textureLicenseAccepted });
                });
                backdrop.addEventListener('click', (e) => {
                    if (e.target === backdrop) { backdrop.remove(); resolve(null); }
                });

                // Quota request button handler (event delegation for dynamically rendered buttons)
                backdrop.addEventListener('click', async (e) => {
                    const btn = e.target.closest('.quota-request-btn');
                    if (!btn) return;
                    const inst = btn.dataset.instance;
                    const code = btn.dataset.code;
                    const desired = parseInt(btn.dataset.desired) || 1;
                    btn.disabled = true;
                    btn.textContent = t('custom_models.quota_requesting');
                    try {
                        const resp = await fetch('/api/custom-models/quota-request', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ instance_type: inst, quota_code: code, desired_value: desired }),
                        });
                        const data = await resp.json();
                        if (resp.ok) {
                            const msg = data.status === 'already_pending'
                                ? t('custom_models.quota_already_pending')
                                : data.status === 'already_sufficient'
                                ? t('custom_models.quota_already_sufficient')
                                : t('custom_models.quota_submitted');
                            btn.outerHTML = `<span class="text-[10px] text-emerald-400">${msg}</span>`;
                            window.showToast?.(data.message, 'success');
                        } else {
                            btn.textContent = t('custom_models.quota_request_btn');
                            btn.disabled = false;
                            window.showToast?.(data.detail || t('custom_models.quota_failed'), 'error');
                        }
                    } catch (err) {
                        btn.textContent = t('custom_models.quota_request_btn');
                        btn.disabled = false;
                        window.showToast?.(t('custom_models.quota_failed'), 'error');
                    }
                });

                document.body.appendChild(backdrop);
            });
        },

        _showLicenseAgreement(modelLabel, licenseAgreement) {
            return new Promise((resolve) => {
                const la = licenseAgreement;
                const termsHtml = (la.key_terms || []).map(term =>
                    `<li class="flex items-start gap-2">
                        <span class="text-emerald-400 mt-0.5 flex-shrink-0">&#10003;</span>
                        <span>${term}</span>
                    </li>`
                ).join('');
                const warningsHtml = (la.warnings || []).length > 0
                    ? `<div class="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 space-y-1.5">
                        <p class="text-[10px] font-semibold text-red-400 uppercase tracking-wider">Restrictions &amp; Warnings</p>
                        <ul class="space-y-1.5 text-xs text-red-300">
                            ${la.warnings.map(w => `<li class="flex items-start gap-2"><span class="text-red-400 mt-0.5 flex-shrink-0">&#9888;</span><span>${w}</span></li>`).join('')}
                        </ul>
                    </div>`
                    : '';

                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
                backdrop.innerHTML = `
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-4">
                        <h3 class="text-sm font-semibold text-brand-text">${t('custom_models.license_title')}</h3>
                        <div class="text-xs text-brand-text-muted space-y-3">
                            <div class="flex items-center gap-2">
                                <span class="font-medium text-brand-text">${modelLabel}</span>
                                <span class="text-[9px] px-1.5 py-0.5 rounded bg-white/5 border border-brand-border/30">${la.license_name}</span>
                            </div>
                            <div class="p-3 rounded-lg bg-brand-bg/60 border border-brand-border/50">
                                <p class="text-[10px] font-semibold text-brand-text-muted uppercase tracking-wider mb-2">${t('custom_models.license_key_terms')}</p>
                                <ul class="space-y-1.5 text-xs">${termsHtml}</ul>
                            </div>
                            ${warningsHtml}
                            <a href="${la.license_url}" target="_blank" rel="noopener" class="inline-flex items-center gap-1 text-brand-accent hover:underline text-xs">
                                ${t('custom_models.license_read_full')} &#8599;
                            </a>
                        </div>
                        <label class="license-agree-label flex items-start gap-2.5 cursor-pointer p-3 rounded-lg border border-brand-border hover:border-brand-accent/30 transition-colors">
                            <input type="checkbox" class="license-agree-checkbox mt-0.5 accent-brand-accent" />
                            <span class="text-xs text-brand-text">${t('custom_models.license_agree_checkbox')}</span>
                        </label>
                        <div class="flex gap-2 justify-end pt-1">
                            <button class="license-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${t('prompt_designer.cancel')}</button>
                            <button class="license-continue btn btn-sm text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium opacity-40 cursor-not-allowed" disabled>${t('custom_models.license_continue')}</button>
                        </div>
                    </div>`;

                const checkbox = backdrop.querySelector('.license-agree-checkbox');
                const continueBtn = backdrop.querySelector('.license-continue');

                checkbox.addEventListener('change', () => {
                    if (checkbox.checked) {
                        continueBtn.disabled = false;
                        continueBtn.classList.remove('opacity-40', 'cursor-not-allowed');
                    } else {
                        continueBtn.disabled = true;
                        continueBtn.classList.add('opacity-40', 'cursor-not-allowed');
                    }
                });

                backdrop.querySelector('.license-cancel').addEventListener('click', () => {
                    backdrop.remove();
                    resolve(false);
                });
                continueBtn.addEventListener('click', () => {
                    backdrop.remove();
                    resolve(true);
                });
                backdrop.addEventListener('click', (e) => {
                    if (e.target === backdrop) { backdrop.remove(); resolve(false); }
                });

                document.body.appendChild(backdrop);
            });
        },

        _askHfToken(licenseUrl) {
            return new Promise((resolve) => {
                const licenseLink = licenseUrl
                    ? `<a href="${licenseUrl}" target="_blank" rel="noopener" class="text-brand-accent hover:underline">Open model page ↗</a>`
                    : '';
                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
                backdrop.innerHTML = `
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-md w-full p-6 space-y-4">
                        <h3 class="text-sm font-semibold text-brand-text">${t('custom_models.hf_title')}</h3>
                        <div class="text-xs text-brand-text-muted space-y-2">
                            <p>${t('custom_models.hf_desc')}</p>
                            <ol class="list-decimal ml-4 space-y-1.5">
                                <li>${t('custom_models.hf_step1')} ${licenseLink}</li>
                                <li>${t('custom_models.hf_step2')}</li>
                                <li>${t('custom_models.hf_step3')}</li>
                            </ol>
                            <p class="text-[10px] text-amber-400/80 mt-2">${t('custom_models.hf_warning')}</p>
                        </div>
                        <input type="password" class="hf-token-input input w-full text-xs font-mono" placeholder="${t('custom_models.hf_placeholder')}" autocomplete="off" />
                        <div class="flex gap-2 justify-end">
                            <button class="hf-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">Cancel</button>
                            <button class="hf-submit btn btn-sm text-xs px-4 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">Continue</button>
                        </div>
                    </div>`;

                const cleanup = (result) => { backdrop.remove(); resolve(result); };
                backdrop.querySelector('.hf-cancel').addEventListener('click', () => cleanup(null));
                backdrop.querySelector('.hf-submit').addEventListener('click', () => {
                    const token = backdrop.querySelector('.hf-token-input').value.trim();
                    cleanup(token || null);
                });
                backdrop.querySelector('.hf-token-input').addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') backdrop.querySelector('.hf-submit').click();
                    if (e.key === 'Escape') cleanup(null);
                });

                document.body.appendChild(backdrop);
                backdrop.querySelector('.hf-token-input').focus();
            });
        },

        _customModelsLoaded: false,

        async _loadCustomModels(modal) {
            const container = modal.querySelector('#ms-custom-models-content');
            if (!container) return;

            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 20000);
                const resp = await fetch('/api/custom-models/catalog', { signal: controller.signal });
                clearTimeout(timeout);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                const models = data.models || [];
                this._customModelsLoaded = true;
                this._catalogModels = models;

                if (models.length === 0) {
                    container.innerHTML = `<p class="text-xs text-brand-text-muted">${t('custom_models.no_models')}</p>`;
                    return;
                }

                // Group: Studio → Category → Models
                // Top level: Image Studio, Video Studio (matches sidebar tabs)
                // Second level: Image Generation, Post Processing, Utility, etc.
                const studioGroups = {};
                models.forEach(m => {
                    const studio = m.studio || 'other';
                    const cat = m.category || 'other';
                    if (!studioGroups[studio]) studioGroups[studio] = {};
                    if (!studioGroups[studio][cat]) studioGroups[studio][cat] = [];
                    studioGroups[studio][cat].push(m);
                });

                const studioLabels = {
                    image: 'Image Studio',
                    video: 'Video Studio',
                    other: 'Other',
                };
                const studioOrder = ['image', 'video', 'other'];
                const categoryLabels = {
                    image_generation: t('custom_models.cat_image_generation'),
                    '3d_generation': t('custom_models.cat_3d_generation'),
                    post_processing: t('custom_models.cat_post_processing'),
                    utility: t('custom_models.cat_utility'),
                    video_generation: t('custom_models.cat_video_generation'),
                    other: t('custom_models.other'),
                };
                const categoryOrder = ['image_generation', '3d_generation', 'post_processing', 'utility', 'video_generation', 'other'];
                const _studioColors = ['text-brand-accent', 'text-cyan-400', 'text-amber-400'];
                const _catColors = ['text-brand-accent', 'text-emerald-400', 'text-purple-400', 'text-cyan-400', 'text-amber-400'];

                // Preserve which sections are expanded before re-rendering
                const openSections = new Set();
                container.querySelectorAll('details[data-cm-studio][open]').forEach(d => openSections.add(d.dataset.cmStudio));
                container.querySelectorAll('details[data-cm-cat][open]').forEach(d => openSections.add(d.dataset.cmCat));

                let html = '<div class="space-y-4">';
                html += `<p class="text-xs text-brand-text-muted">${t('custom_models.description_line')}</p>`;

                const sortedStudios = Object.keys(studioGroups).sort((a, b) => {
                    const ai = studioOrder.indexOf(a);
                    const bi = studioOrder.indexOf(b);
                    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
                });

                sortedStudios.forEach((studio, sIdx) => {
                    const categories = studioGroups[studio];
                    const studioTotal = Object.values(categories).reduce((s, arr) => s + arr.length, 0);
                    const studioOpen = openSections.has(studio);
                    const studioColor = _studioColors[sIdx % _studioColors.length];

                    html += `<details class="mb-3 ms-collapsible" data-cm-studio="${studio}" ${studioOpen ? 'open' : ''}>
                        <summary class="text-sm font-semibold ${studioColor} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">
                            ${studioLabels[studio] || studio}
                            <span class="text-[10px] font-normal text-brand-text-muted">(${studioTotal})</span>
                        </summary>
                        <div class="space-y-3 mt-2 ml-2">`;

                    const sortedCats = Object.keys(categories).sort((a, b) => {
                        const ai = categoryOrder.indexOf(a);
                        const bi = categoryOrder.indexOf(b);
                        return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
                    });

                    sortedCats.forEach((cat, cIdx) => {
                        // Sort newest models first within each category
                        const catModels = categories[cat].sort((a, b) =>
                            (b.last_updated || '').localeCompare(a.last_updated || '') || b.label.localeCompare(a.label)
                        );
                        const catOpen = openSections.has(cat);
                        const catColor = _catColors[cIdx % _catColors.length];

                        html += `<details class="mb-2 ms-collapsible" data-cm-cat="${cat}" ${catOpen ? 'open' : ''}>
                            <summary class="text-xs font-semibold ${catColor} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">
                                ${categoryLabels[cat] || cat}
                                <span class="text-[10px] font-normal text-brand-text-muted">(${catModels.length})</span>
                            </summary>
                            <div class="space-y-2 mt-2">`;

                    for (const m of catModels) {
                        const isInService = m.deployment_status === 'InService';
                        const active = isInService && !m.warming_up && m.instance_count > 0;
                        const idle = isInService && !m.warming_up && !active;
                        const warmingUp = isInService && m.warming_up;
                        const scalingUp = m.deployment_status === 'Updating' && (m.instance_count === 0 || m.instance_count === undefined);
                        const deploying = !scalingUp && !isInService && (m.deployment_status === 'Creating' || m.deployment_status === 'Updating' || m.deploy_stage === 'preparing' || m.deploy_stage === 'downloading' || m.deploy_stage === 'uploading' || m.deploy_stage === 'deploying' || (m.deploy_progress && m.deploy_stage !== 'failed'));
                        const failed = m.deployment_status === 'Failed' || m.deploy_stage === 'failed';
                        const deployed = active || idle;
                        const cacheHint = m.has_cache ? 'Cached — faster startup' : 'Cold start on activation';
                        const statusColor = active ? 'text-emerald-400' : idle ? 'text-blue-400' : warmingUp ? 'text-cyan-400' : (deploying || scalingUp) ? 'text-amber-400' : failed ? 'text-red-400' : 'text-brand-text-muted/50';
                        const statusText = active ? t('custom_models.active') : idle ? `Inactive — activates on next request (${cacheHint})` : warmingUp ? (m.warmup_detail || t('custom_models.warming_up')) : scalingUp ? 'Starting instance...' : deploying ? (m.deploy_progress || t('custom_models.deploying')) : failed ? t('custom_models.failed') : t('custom_models.not_deployed');
                        const authBadge = m.requires_hf_auth ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${t('custom_models.hf_auth')}</span>` : '';
                        const licenseBadge = `<span class="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-brand-text-muted border border-brand-border/30">${m.license?.split(' ')[0] || '?'}</span>`;
                        const userBadge = m.user_added ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">User</span>` : '';
                        const statusDot = active ? 'bg-emerald-400' : idle ? 'bg-blue-400' : warmingUp ? 'bg-cyan-400 animate-pulse' : (deploying || scalingUp) ? 'bg-amber-400 animate-pulse' : failed ? 'bg-red-400' : 'bg-brand-text-muted/30';

                        html += `
                            <div class="rounded-lg bg-brand-bg/40 border border-brand-border ${failed ? 'border-red-500/20' : ''}">
                                <div class="p-3 flex items-center gap-3">
                                    <div class="flex-shrink-0 w-2 h-2 rounded-full ${statusDot}" title="${statusText}"></div>
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center gap-2 flex-wrap">
                                            <span class="text-xs font-semibold text-brand-text">${m.label}</span>
                                            ${authBadge}${licenseBadge}${userBadge}
                                        </div>
                                        <p class="text-[10px] text-brand-text-muted mt-0.5 truncate">${m.description}</p>
                                        <div class="flex gap-3 mt-1 text-[10px] text-brand-text-muted/60">
                                            <span>${m.provider}</span>
                                            <span>${m.requirements?.recommended_instance || '?'}</span>
                                            <span>~$${m.pricing?.estimated_cost_per_image?.toFixed(2) || m.pricing?.estimated_cost_per_video?.toFixed(2) || '?'}/unit</span>
                                            <span>${m.requirements?.min_vram_gb || '?'}GB VRAM</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-2 flex-shrink-0">
                                        ${!deployed && !deploying && !warmingUp && !scalingUp && !failed
                                            ? `<span class="text-[10px] text-brand-text-muted/50">${t('custom_models.not_deployed')}</span>
                                               <button class="ms-cm-deploy btn btn-sm text-[10px] px-3 py-1 rounded bg-brand-accent hover:bg-brand-accent-hover text-white" data-model="${m.key}" data-auth="${m.requires_hf_auth ? '1' : '0'}" data-license="${m.hf_license_url || ''}">${t('custom_models.deploy')}</button>`
                                            : (deploying || warmingUp || scalingUp)
                                            ? `<span class="text-[10px] text-amber-400">${m.deploy_progress || t('custom_models.deploying')}</span>`
                                            : `<button class="ms-cm-deploy btn btn-sm text-[10px] px-3 py-1 rounded bg-brand-accent hover:bg-brand-accent-hover text-white" data-model="${m.key}" data-auth="${m.requires_hf_auth ? '1' : '0'}" data-license="${m.hf_license_url || ''}" title="${t('custom_models.deploy_another_hint')}">${t('custom_models.deploy_another')}</button>`
                                        }
                                    </div>
                                </div>
                                ${(m.deployed_instances || []).length > 0 ? `
                                <div class="px-3 pb-3 pt-0 space-y-1.5 border-t border-brand-border/20 mt-0 ml-4">
                                    <div class="text-[9px] text-brand-text-muted/40 pt-2">${(m.deployed_instances || []).length} deployed instance${(m.deployed_instances || []).length > 1 ? 's' : ''}:</div>
                                    ${(m.deployed_instances || []).map(inst => {
                                        const iActive = inst.status === 'InService' && !inst.warming_up && inst.instance_count > 0;
                                        const iIdle = inst.status === 'InService' && !inst.warming_up && !iActive;
                                        const iWarm = inst.status === 'InService' && inst.warming_up;
                                        const iDot = iActive ? 'bg-emerald-400' : iIdle ? 'bg-blue-400' : iWarm ? 'bg-cyan-400 animate-pulse' : 'bg-brand-text-muted/30';
                                        const iColor = iActive ? 'text-emerald-400' : iIdle ? 'text-blue-400' : iWarm ? 'text-cyan-400' : 'text-brand-text-muted/50';
                                        const iStatusTxt = iActive ? t('custom_models.active') : iIdle ? t('custom_models.instance_inactive') : iWarm ? t('custom_models.warming_up') : inst.status;
                                        return `
                                        <div class="flex items-center gap-2 p-2 rounded bg-black/10 border border-brand-border/20">
                                            <div class="w-1.5 h-1.5 rounded-full ${iDot} flex-shrink-0"></div>
                                            <span class="text-[11px] text-cyan-300/80 truncate flex-1 min-w-0" title="${inst.label}">${inst.label}</span>
                                            <span class="text-[10px] ${iColor} flex-shrink-0 w-[200px] text-right">${iStatusTxt}</span>
                                            <button class="ms-cm-teardown btn text-[10px] px-2 py-0.5 rounded border border-red-500/20 text-red-400/70 hover:bg-red-500/10 flex-shrink-0 w-[60px] text-center" data-model="${inst.deployed_key}">${t('custom_models.remove')}</button>
                                            ${iIdle ? `<button class="ms-cm-redeploy btn text-[10px] px-2.5 py-0.5 rounded border border-brand-accent/30 text-brand-accent/80 hover:bg-brand-accent/10 hover:text-brand-accent flex-shrink-0 w-[110px] text-center" data-model="${inst.deployed_key}" data-auth="${m.requires_hf_auth ? '1' : '0'}">${t('custom_models.redeploy')}</button>` : `<span class="w-[110px] flex-shrink-0"></span>`}
                                        </div>`;
                                    }).join('')}
                                </div>` : ''}
                            </div>`;
                    }
                    html += '</div></details>';  // close category
                    });
                    html += '</div></details>';  // close studio
                });
                html += '</div>';
                container.innerHTML = html;

                // Default: open the first top-level section if none are open (fresh load)
                const cmSections = container.querySelectorAll('details.ms-collapsible[data-cm-studio]');
                if (cmSections.length > 0 && !Array.from(cmSections).some(d => d.open)) {
                    cmSections[0].open = true;
                    // Also open first sub-section within it
                    const firstSub = cmSections[0].querySelector('details.ms-collapsible[data-cm-cat]');
                    if (firstSub) firstSub.open = true;
                }

                // Auto-refresh based on model states:
                // - Deploying/warming up: every 2 min (need progress updates)
                // - Active (instances running): every 10 min (catch scale-in transitions)
                // - Idle: no auto-refresh needed
                const hasInProgress = models.some(m =>
                    m.deployment_status === 'Creating' || m.deployment_status === 'Updating' || m.warming_up
                );
                const hasActive = !hasInProgress && models.some(m =>
                    m.deployment_status === 'InService' && m.instance_count > 0 && !m.warming_up
                );
                if (hasInProgress) {
                    clearTimeout(this._cmPollTimer);
                    this._cmPollTimer = setTimeout(() => {
                        this._customModelsLoaded = false;
                        this._loadCustomModels(modal);
                    }, 120000);  // 2 min during active loading
                } else if (hasActive) {
                    clearTimeout(this._cmPollTimer);
                    this._cmPollTimer = setTimeout(() => {
                        this._customModelsLoaded = false;
                        this._loadCustomModels(modal);
                    }, 600000);  // 10 min for active models — catch scale-in
                }

                // Attach deploy/teardown handlers
                container.querySelectorAll('.ms-cm-deploy').forEach(btn => {
                    btn.addEventListener('click', () => {
                        // Disable immediately to prevent double-click
                        btn.disabled = true;
                        btn.textContent = 'Starting...';
                        btn.className = 'btn btn-sm text-[10px] px-3 py-1 rounded bg-amber-500/20 border border-amber-500/30 text-amber-400 cursor-wait';
                        // Update the status text next to it
                        const statusEl = btn.closest('.flex')?.querySelector('.text-brand-text-muted\\/50, .text-\\[10px\\]');
                        if (statusEl && statusEl.textContent.trim() === t('custom_models.not_deployed')) {
                            statusEl.textContent = 'Preparing deployment...';
                            statusEl.className = 'text-[10px] font-medium text-amber-400';
                        }
                        this._deployCustomModel(btn.dataset.model, btn.dataset.auth === '1', modal, false, btn.dataset.license);
                    });
                });
                container.querySelectorAll('.ms-cm-teardown').forEach(btn => {
                    btn.addEventListener('click', () => this._teardownCustomModel(btn.dataset.model, modal));
                });
                container.querySelectorAll('.ms-cm-redeploy').forEach(btn => {
                    btn.addEventListener('click', () => this._deployCustomModel(btn.dataset.model, btn.dataset.auth === '1', modal, true));
                });

            } catch (err) {
                const msg = err.name === 'AbortError' ? 'Request timed out — Amazon SageMaker status check may be slow. Try Refresh Status.' : err.message;
                container.innerHTML = `<p class="text-xs text-red-400">Failed to load custom models: ${msg}</p>`;
            }
        },

        async _deployCustomModel(modelKey, needsAuth, modal, isRedeploy = false, licenseUrl = '') {
            // Helper to reset all deploy buttons for this model if user cancels at any step
            const _resetDeployBtn = () => {
                modal?.querySelectorAll(`.ms-cm-deploy[data-model="${modelKey}"]`).forEach(btn => {
                    const isDeployAnother = btn.title === t('custom_models.deploy_another_hint');
                    btn.textContent = isDeployAnother ? t('custom_models.deploy_another') : t('custom_models.deploy');
                    btn.disabled = false;
                    btn.className = 'ms-cm-deploy btn btn-sm text-[10px] px-3 py-1 rounded bg-brand-accent/20 border border-brand-accent/30 text-brand-accent hover:bg-brand-accent/30';
                    // Reset any "Preparing deployment..." status text nearby
                    const row = btn.closest('.flex');
                    if (row) {
                        row.querySelectorAll('.text-amber-400').forEach(el => {
                            if (el !== btn && el.textContent.includes('Preparing') || el.textContent.includes('Starting')) {
                                el.textContent = t('custom_models.not_deployed');
                                el.className = 'text-[10px] text-brand-text-muted/50';
                            }
                        });
                    }
                });
            };

            // Show license agreement before proceeding (skip for redeploys — already accepted)
            let licenseAccepted = false;
            if (!isRedeploy) {
                const catalogModel = (this._catalogModels || []).find(m => m.key === modelKey);
                const licenseAgreement = catalogModel?.license_agreement;
                if (licenseAgreement?.required) {
                    const accepted = await this._showLicenseAgreement(
                        catalogModel.label || modelKey,
                        licenseAgreement
                    );
                    if (!accepted) { _resetDeployBtn(); return; }
                    licenseAccepted = true;
                }
            }

            let hfToken = null;

            if (needsAuth) {
                // Check if a shared HF token is already stored in Secrets Manager
                try {
                    const tokenResp = await fetch('/api/custom-models/hf-token-status');
                    const tokenStatus = tokenResp.ok ? await tokenResp.json() : {};
                    if (tokenStatus.stored) {
                        // Token already stored — no need to ask again
                        hfToken = null;  // Backend will reuse the stored one
                    } else {
                        // No token stored yet — ask the user
                        hfToken = await this._askHfToken(licenseUrl);
                        if (!hfToken) { _resetDeployBtn(); return; }
                    }
                } catch {
                    // Can't check token status — ask the user just in case
                    hfToken = await this._askHfToken(licenseUrl);
                    if (!hfToken) { _resetDeployBtn(); return; }
                }
            }

            // Fetch viable instances for this model
            let instanceOptions = [];
            let recommendedInstance = '';
            let minVram = 0;
            let deployRegion = '';
            try {
                const optResp = await fetch(`/api/custom-models/instance-options/${modelKey}`);
                if (optResp.ok) {
                    const optData = await optResp.json();
                    instanceOptions = optData.options || [];
                    recommendedInstance = optData.recommended_instance || '';
                    minVram = optData.min_vram_gb || 0;
                    deployRegion = optData.region || '';
                }
            } catch {}

            // Fetch the catalog entry for texture-backend metadata (TripoSG: the
            // user picks MVPainter vs Hunyuan at deploy). Registry-driven — the
            // dialog renders entirely from texture_backends.options.
            let textureBackends = null;
            try {
                const catResp = await fetch(`/api/custom-models/catalog/${modelKey}`);
                if (catResp.ok) {
                    const cat = await catResp.json();
                    textureBackends = cat.texture_backends || null;
                }
            } catch {}

            // Build instance selector + deployment type dialog
            const deployConfig = await this._showDeployDialog(modelKey, instanceOptions, recommendedInstance, minVram, deployRegion, textureBackends);
            if (!deployConfig) { _resetDeployBtn(); return; } // User cancelled

            const { instanceType: selectedInstance, endpointType, textureBackend, textureLicenseAccepted } = deployConfig;

            window.showLoading?.(`${isRedeploy ? 'Redeploying' : 'Deploying'} model...`);

            try {
                const url = isRedeploy ? `/api/custom-models/redeploy/${modelKey}` : '/api/custom-models/deploy';
                const body = isRedeploy
                    ? { endpoint_type: endpointType, instance_type: selectedInstance, hf_token: hfToken }
                    : { model_key: modelKey, endpoint_type: endpointType, instance_type: selectedInstance, hf_token: hfToken, license_accepted: licenseAccepted };
                // Texture-backend choice (TripoSG etc.) — only set when the model offers it.
                if (!isRedeploy && textureBackend) {
                    body.texture_backend = textureBackend;
                    body.texture_license_accepted = !!textureLicenseAccepted;
                }

                const resp = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });

                window.hideLoading?.();

                if (resp.ok) {
                    const result = await resp.json();
                    window.showToast?.(result.message || t('custom_models.deploy_started'), 'success');
                    // Immediately update UI to show deploying state (before catalog refresh)
                    modal?.querySelectorAll(`.ms-cm-deploy[data-model="${modelKey}"]`).forEach(btn => {
                        btn.textContent = t('custom_models.deploying');
                        btn.disabled = true;
                        btn.className = 'btn btn-sm text-[10px] px-3 py-1 rounded bg-amber-500/20 border border-amber-500/30 text-amber-400 cursor-wait';
                        const row = btn.closest('.flex');
                        if (row) {
                            row.querySelectorAll('.text-brand-text-muted\\/50').forEach(el => {
                                if (el.textContent.includes(t('custom_models.not_deployed')) || el.textContent.includes('Preparing')) {
                                    el.textContent = t('custom_models.deploying');
                                    el.className = 'text-[10px] font-medium text-amber-400 animate-pulse';
                                }
                            });
                        }
                    });
                    // Start polling deployment progress
                    this._pollDeployProgress(modelKey, modal);
                    this._customModelsLoaded = false;
                    setTimeout(() => this._loadCustomModels(modal), 5000);
                } else {
                    const err = await resp.json();
                    const detail = typeof err.detail === 'string' ? err.detail : err.detail?.message || 'Deployment failed';

                    // If auth failed (stored token was invalid), prompt for a new one
                    if (err.detail?.error === 'hf_auth_required') {
                        window.hideLoading?.();
                        const newToken = await this._askHfToken(licenseUrl);
                        if (newToken) {
                            // Store the new token and retry deployment
                            await fetch('/api/custom-models/hf-token', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ hf_token: newToken }),
                            });
                            return this._deployCustomModel(modelKey, needsAuth, modal, isRedeploy, licenseUrl);
                        }
                    }
                    window.showToast?.(detail, 'error');
                }
            } catch (err) {
                window.hideLoading?.();
                window.showToast?.(`Deployment failed: ${err.message}`, 'error');
            }
        },

        async _addCustomModelWizard(modal) {
            // Step 1: Ask for HuggingFace repo URL
            const backdrop = document.createElement('div');
            backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
            backdrop.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-4">
                    <h3 class="text-sm font-semibold text-brand-text flex items-center gap-2">
                        <span>+</span> ${t('custom_models.add_model_title') || 'Add Custom Model'}
                    </h3>
                    <p class="text-xs text-brand-text-muted">${t('custom_models.add_model_desc') || 'Enter a HuggingFace model URL or repo ID. The system will auto-detect the model type, library, and requirements.'}</p>
                    <input type="text" class="cm-repo-input input w-full text-xs" placeholder="e.g. runwayml/stable-diffusion-v1-5 or https://huggingface.co/..." autocomplete="off" />
                    <div class="cm-token-row hidden space-y-2">
                        <p class="text-[10px] text-amber-400">${t('custom_models.add_model_gated') || 'This repo may be gated. Provide a token if needed (used once, not stored):'}</p>
                        <input type="password" class="cm-token-input input w-full text-xs font-mono" placeholder="${t('custom_models.hf_placeholder')}" autocomplete="off" />
                    </div>
                    <div class="cm-result hidden"></div>
                    <div class="flex gap-2 justify-end">
                        <button class="cm-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${t('prompt_designer.cancel')}</button>
                        <button class="cm-detect btn btn-sm text-xs px-4 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">${t('custom_models.detect') || 'Detect Model'}</button>
                        <button class="cm-add hidden btn btn-sm text-xs px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium">${t('custom_models.add_to_catalog') || 'Add to Catalog'}</button>
                    </div>
                </div>`;

            let detectedEntry = null;

            backdrop.querySelector('.cm-cancel').addEventListener('click', () => backdrop.remove());
            backdrop.addEventListener('click', (e) => { if (e.target === backdrop) backdrop.remove(); });

            backdrop.querySelector('.cm-detect').addEventListener('click', async () => {
                const repoUrl = backdrop.querySelector('.cm-repo-input').value.trim();
                if (!repoUrl) return;

                const detectBtn = backdrop.querySelector('.cm-detect');
                detectBtn.textContent = 'Detecting...';
                detectBtn.disabled = true;

                try {
                    const token = backdrop.querySelector('.cm-token-input').value.trim() || null;
                    const resp = await fetch('/api/custom-models/detect', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ repo_url: repoUrl, hf_token: token }),
                    });

                    if (!resp.ok) {
                        const err = await resp.json();
                        const detail = typeof err.detail === 'string' ? err.detail : 'Detection failed';
                        if (detail.includes('authentication') || detail.includes('401') || detail.includes('403')) {
                            backdrop.querySelector('.cm-token-row').classList.remove('hidden');
                        }
                        backdrop.querySelector('.cm-result').innerHTML = `<p class="text-xs text-red-400">${detail}</p>`;
                        backdrop.querySelector('.cm-result').classList.remove('hidden');
                        return;
                    }

                    const data = await resp.json();
                    detectedEntry = data.entry;

                    // Show detected info
                    const e = detectedEntry;
                    const warning = e.invoke?._warning ? `<p class="text-[10px] text-amber-400 mt-2">⚠ ${e.invoke._warning}</p>` : '';
                    backdrop.querySelector('.cm-result').innerHTML = `
                        <div class="p-3 rounded-lg bg-black/20 border border-brand-border/30 space-y-2">
                            <h4 class="text-xs font-semibold text-emerald-400">✓ Model Detected</h4>
                            <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-brand-text-muted">
                                <span>Label:</span><span class="text-brand-text">${e.label}</span>
                                <span>Library:</span><span class="text-brand-text">${e.invoke?.library || '?'}</span>
                                <span>Type:</span><span class="text-brand-text">${e.invoke?.predictor_type || '?'}</span>
                                <span>Category:</span><span class="text-brand-text">${e.category}</span>
                                <span>License:</span><span class="text-brand-text">${e.license}</span>
                                <span>VRAM:</span><span class="text-brand-text">${e.requirements?.min_vram_gb || '?'} GB</span>
                                <span>Auth:</span><span class="text-brand-text">${e.requires_hf_auth ? 'Yes (gated)' : 'No'}</span>
                            </div>
                            ${warning}
                        </div>`;
                    backdrop.querySelector('.cm-result').classList.remove('hidden');
                    backdrop.querySelector('.cm-add').classList.remove('hidden');

                } catch (err) {
                    backdrop.querySelector('.cm-result').innerHTML = `<p class="text-xs text-red-400">${err.message}</p>`;
                    backdrop.querySelector('.cm-result').classList.remove('hidden');
                } finally {
                    detectBtn.textContent = t('custom_models.detect') || 'Detect Model';
                    detectBtn.disabled = false;
                }
            });

            backdrop.querySelector('.cm-add').addEventListener('click', async () => {
                if (!detectedEntry) return;
                // Generate a key from the repo ID
                const repoUrl = backdrop.querySelector('.cm-repo-input').value.trim();
                let key = repoUrl.split('/').pop().replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();

                try {
                    const resp = await fetch('/api/custom-models/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key, entry: detectedEntry }),
                    });
                    if (resp.ok) {
                        window.showToast?.(`Model "${detectedEntry.label}" added to catalog`, 'success');
                        backdrop.remove();
                        this._customModelsLoaded = false;
                        this._loadCustomModels(modal);
                    } else {
                        const err = await resp.json();
                        window.showToast?.(err.detail || 'Failed to add model', 'error');
                    }
                } catch (err) {
                    window.showToast?.(`Failed: ${err.message}`, 'error');
                }
            });

            document.body.appendChild(backdrop);
            backdrop.querySelector('.cm-repo-input').focus();
        },

        _pollDeployProgress(modelKey, modal) {
            // Track active polls to avoid duplicates
            if (!this._activePolls) this._activePolls = new Set();
            if (this._activePolls.has(modelKey)) return;
            this._activePolls.add(modelKey);

            const poll = async () => {
                // Stop if modal was closed
                if (!document.getElementById('model-settings-modal')) {
                    this._activePolls.delete(modelKey);
                    return;
                }
                try {
                    const resp = await fetch(`/api/custom-models/deploy-status/${modelKey}`);
                    if (resp.ok) {
                        const status = await resp.json();

                        // Update inline progress text without full reload
                        const container = modal.querySelector('#ms-custom-models-content');
                        if (container && status.progress) {
                            // Find the model card and update its status text
                            const cards = container.querySelectorAll('[data-model]');
                            cards.forEach(btn => {
                                if (btn.dataset.model === modelKey) {
                                    const statusEl = btn.closest('.p-3')?.querySelector('.text-amber-400, .text-emerald-400');
                                    if (statusEl) statusEl.textContent = status.progress;
                                }
                            });
                        }

                        if (status.stage === 'complete') {
                            window.showToast?.(status.progress || t('custom_models.deploy_complete'), 'success');
                            this._customModelsLoaded = false;
                            this._loadCustomModels(modal);
                            this._activePolls.delete(modelKey);
                            return;
                        }
                        if (status.stage === 'failed') {
                            window.showToast?.(`Deployment failed: ${status.error}`, 'error');
                            this._customModelsLoaded = false;
                            this._loadCustomModels(modal);
                            this._activePolls.delete(modelKey);
                            return;
                        }
                        // Still in progress — poll again (don't full-reload, just update inline)
                        setTimeout(poll, 8000);
                    }
                } catch {
                    setTimeout(poll, 8000);
                }
            };
            // First poll: do a full tab refresh to show "deploying" state, then poll inline
            this._customModelsLoaded = false;
            this._loadCustomModels(modal);
            setTimeout(poll, 5000);
        },

        async _teardownCustomModel(modelKey, modal) {
            if (!await window.showConfirm(t('custom_models.remove_confirm'), { title: t('custom_models.remove_title'), confirmLabel: t('custom_models.remove'), danger: true })) return;

            try {
                const resp = await fetch(`/api/custom-models/teardown/${modelKey}`, { method: 'DELETE' });
                if (resp.ok) {
                    window.showToast?.(t('custom_models.remove_done'), 'success');
                    this._customModelsLoaded = false;
                    this._loadCustomModels(modal);
                }
            } catch (err) {
                window.showToast?.(`Teardown failed: ${err.message}`, 'error');
            }
        },

        async _manageHfToken(modal) {
            // Check current status
            let stored = false;
            try {
                const resp = await fetch('/api/custom-models/hf-token-status');
                if (resp.ok) {
                    const data = await resp.json();
                    stored = data.stored;
                }
            } catch {}

            const backdrop = document.createElement('div');
            backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
            backdrop.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-md w-full p-6 space-y-4">
                    <h3 class="text-sm font-semibold text-brand-text">🔑 HuggingFace Token</h3>
                    <div class="text-xs text-brand-text-muted space-y-2">
                        <p>Status: ${stored
                            ? '<span class="text-emerald-400 font-medium">Token stored</span> (encrypted in AWS Secrets Manager)'
                            : '<span class="text-amber-400 font-medium">No token stored</span>'
                        }</p>
                        <p>A single Read-only token is shared across all gated HuggingFace models. It's stored encrypted in your AWS account and used by Amazon SageMaker containers at startup.</p>
                    </div>
                    <input type="password" class="hf-token-input input w-full text-xs font-mono" placeholder="hf_xxxxxxxxx (paste to ${stored ? 'update' : 'store'} token)" autocomplete="off" />
                    <div class="flex gap-2 justify-end">
                        ${stored ? '<button class="hf-delete btn btn-sm text-xs px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10">Delete Token</button>' : ''}
                        <button class="hf-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">Close</button>
                        <button class="hf-save btn btn-sm text-xs px-4 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">Save Token</button>
                    </div>
                </div>`;

            const cleanup = () => backdrop.remove();
            backdrop.querySelector('.hf-cancel').addEventListener('click', cleanup);
            backdrop.addEventListener('click', (e) => { if (e.target === backdrop) cleanup(); });

            backdrop.querySelector('.hf-save').addEventListener('click', async () => {
                const token = backdrop.querySelector('.hf-token-input').value.trim();
                if (!token) { window.showToast?.('Please enter a token', 'error'); return; }
                try {
                    const resp = await fetch('/api/custom-models/hf-token', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ hf_token: token }),
                    });
                    if (resp.ok) {
                        window.showToast?.('HuggingFace token saved', 'success');
                        cleanup();
                    } else {
                        const err = await resp.json();
                        window.showToast?.(err.detail || 'Failed to save token', 'error');
                    }
                } catch (err) {
                    window.showToast?.(`Failed: ${err.message}`, 'error');
                }
            });

            const deleteBtn = backdrop.querySelector('.hf-delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', async () => {
                    if (!await window.showConfirm(t('custom_models.delete_token_confirm'), { title: t('custom_models.delete_token_title'), confirmLabel: t('custom_models.remove'), danger: true })) return;
                    try {
                        await fetch('/api/custom-models/hf-token', { method: 'DELETE' });
                        window.showToast?.('HuggingFace token deleted', 'success');
                        cleanup();
                    } catch (err) {
                        window.showToast?.(`Failed: ${err.message}`, 'error');
                    }
                });
            }

            backdrop.querySelector('.hf-token-input').addEventListener('keydown', (e) => {
                if (e.key === 'Enter') backdrop.querySelector('.hf-save').click();
                if (e.key === 'Escape') cleanup();
            });

            document.body.appendChild(backdrop);
            backdrop.querySelector('.hf-token-input').focus();
        },

        _esc(str) {
            const d = document.createElement('div');
            d.textContent = str || '';
            return d.innerHTML;
        },
    };
})();
