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
            window.showLoading?.(t('artsmoker.ui.model_settings.loading_settings'));

            try {
                this._registry = await API.admin.getModels();
                window.hideLoading?.();
                this._renderModal();
            } catch (err) {
                window.hideLoading?.();
                window.showToast?.(t('artsmoker.ui.model_settings.load_failed') + ': ' + (err.message || ''), 'error');
            }
        },

        _renderModal() {
            const reg = this._registry;
            if (!reg) return;

            const lastUpdated = reg.last_updated
                ? window.formatTimestamp(reg.last_updated)
                : t('artsmoker.ui.common.unknown');

            // Count models per tab
            const imgCount = Object.keys(reg.image_models || {}).length;
            const vidCount = Object.keys(reg.video_models || {}).length;
            const llmCount = Object.keys(reg.categories || {}).length + Object.keys(reg.post_processing || {}).length;

            const modal = document.createElement('div');
            modal.id = 'model-settings-modal';
            modal.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            // nosemgrep
            modal.innerHTML = html`
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl w-full h-[90vh] flex flex-col overflow-hidden" style="max-width: 80rem;">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-brand-border">
                        <div class="flex items-center gap-3">
                            <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            </svg>
                            <h2 class="text-lg font-semibold">${t('artsmoker.ui.model_settings.title')}</h2>
                        </div>
                        <div class="flex items-center gap-3">
                            <button id="ms-refresh-all" class="btn btn-sm text-xs bg-amber-600 hover:bg-amber-500 text-white" title="${t('artsmoker.ui.model_settings.sync_tooltip')}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                                ${t('artsmoker.ui.model_settings.sync_aws')}
                            </button>
                            <span class="text-[10px] text-brand-text-muted" title="${t('artsmoker.ui.model_settings.discovers_tooltip')}">${t('artsmoker.ui.model_settings.updated')}: ${lastUpdated}</span>
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
                                🖼️  ${t('artsmoker.ui.model_settings.tab_image')} <span class="text-[9px] opacity-50 ml-1">(${imgCount})</span>
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="video-studio">
                                🎬  ${t('artsmoker.ui.model_settings.tab_video')} <span class="text-[9px] opacity-50 ml-1">(${vidCount})</span>
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="chat-studio">
                                💬  ${t('artsmoker.ui.model_settings.tab_chat')} <span class="text-[9px] opacity-50 ml-1">(${Object.keys(reg.chat_models || {}).length})</span>
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="type-studio">
                                ✍️  ${t('artsmoker.ui.model_settings.tab_type')}
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="shared-ai">
                                ⚙️  ${t('artsmoker.ui.model_settings.tab_shared')} <span class="text-[9px] opacity-50 ml-1">(${llmCount})</span>
                            </button>
                            <div class="border-t border-brand-border my-1"></div>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="custom-models">
                                🔧  ${t('artsmoker.ui.custom_models.tab_title')}
                            </button>
                            <div class="border-t border-brand-border my-1"></div>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="prompt-templates">
                                📝  ${t('artsmoker.ui.model_settings.tab_templates')}
                            </button>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="registry-json">
                                { }  ${t('artsmoker.ui.model_settings.tab_json')}
                            </button>
                            <div class="border-t border-brand-border my-1"></div>
                            <button class="ms-vtab w-full text-left text-sm px-4 py-2.5 hover:bg-white/5 transition-colors" data-ms-tab="maintenance">
                                🛠️  ${t('artsmoker.ui.model_settings.tab_maintenance')}
                            </button>
                        </div>

                        <!-- Tab content -->
                        <div class="flex-1 overflow-auto p-6">

                        <!-- Tab: Image Studio -->
                        <div class="ms-tab-panel" data-ms-panel="image-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.desc_image')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="image-studio">${t('artsmoker.ui.model_settings.ms_show_all')}</button>
                            </div>
                            <div id="ms-image-models" class="space-y-3">
                                ${this._renderImageModels(reg)}
                            </div>
                        </div>

                        <!-- Tab: Video Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="video-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.desc_video')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="video-studio">${t('artsmoker.ui.model_settings.ms_show_all')}</button>
                            </div>
                            <details class="ms-collapsible">
                                <summary class="text-sm font-semibold text-brand-accent uppercase tracking-wider cursor-pointer hover:opacity-80 select-none mb-2">${t('artsmoker.ui.model_settings.tab_video')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(reg.video_models || {}).length})</span></summary>
                                <div id="ms-video-models" class="space-y-3">
                                    ${this._renderVideoModels(reg)}
                                </div>
                            </details>
                        </div>

                        <!-- Tab: Chat Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="chat-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.desc_chat')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="chat-studio">${t('artsmoker.ui.model_settings.ms_show_all')}</button>
                            </div>
                            <div id="ms-chat-models" class="space-y-2">
                                ${this._renderChatModels(reg)}
                            </div>
                        </div>

                        <!-- Tab: Type Studio -->
                        <div class="ms-tab-panel hidden" data-ms-panel="type-studio">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.desc_type')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="type-studio">${t('artsmoker.ui.model_settings.ms_show_all')}</button>
                            </div>
                            <div class="space-y-4">
                                <details class="ms-collapsible">
                                    <summary class="text-sm font-semibold text-cyan-400 uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('artsmoker.ui.model_settings.type_llm_heading')}</summary>
                                    <p class="text-[10px] text-brand-text-muted mb-2 mt-2">${t('artsmoker.ui.model_settings.type_llm_desc')}</p>
                                    <div class="space-y-3">
                                        ${['complex_llm', 'fast_llm'].map(name => {
                                            const cat = (reg.categories || {})[name];
                                            return cat ? this._renderCategory(name, cat) : '';
                                        })}
                                    </div>
                                </details>
                                <details class="ms-collapsible">
                                    <summary class="text-sm font-semibold text-amber-400 uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('artsmoker.ui.model_settings.post_processing')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(reg.post_processing || {}).length})</span></summary>
                                    <p class="text-[10px] text-brand-text-muted mb-2 mt-2">${t('artsmoker.ui.model_settings.type_pp_desc')}</p>
                                    <div class="space-y-3">
                                        ${Object.entries(reg.post_processing || {}).map(([key, m]) => this._renderPostProcess(key, m))}
                                    </div>
                                </details>
                            </div>
                        </div>

                        <!-- Tab: Shared AI -->
                        <div class="ms-tab-panel hidden" data-ms-panel="shared-ai">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.desc_shared')}</p>
                                <button class="ms-toggle-sections btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" data-panel="shared-ai">${t('artsmoker.ui.model_settings.ms_show_all')}</button>
                            </div>
                            <div class="space-y-4">
                                <details class="ms-collapsible">
                                    <summary class="text-sm font-semibold text-brand-accent uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('artsmoker.ui.model_settings.llm_categories')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(reg.categories || {}).length - (reg.categories?.custom_llms ? 1 : 0)})</span></summary>
                                    <div class="space-y-3 mt-2">
                                        ${Object.entries(reg.categories || {}).filter(([name]) => name !== 'custom_llms').map(([name, cat]) => this._renderCategory(name, cat))}
                                    </div>
                                </details>
                                ${this._renderCustomLLMs(reg)}
                            </div>
                        </div>

                        <!-- Tab: Prompt Templates -->
                        <div class="ms-tab-panel hidden" data-ms-panel="prompt-templates">
                            <p class="text-xs text-red-400 mb-2">${t('artsmoker.ui.model_settings.templates_desc')}</p>
                            <div class="flex items-center gap-2 mb-3 p-2 rounded-lg bg-brand-bg/40 border border-brand-border/50">
                                <span class="text-[10px] text-brand-text-muted flex-shrink-0">${t('artsmoker.ui.model_settings.templates_refinement_model')}:</span>
                                <select id="ms-tmpl-model" class="input text-xs font-mono flex-1"></select>
                                <input type="text" id="ms-tmpl-instructions" class="input text-xs flex-1" placeholder="${t('artsmoker.ui.model_settings.templates_instructions_placeholder')}">
                                <button id="ms-tmpl-toggle-all" class="btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-brand-accent whitespace-nowrap" title="${t('artsmoker.ui.model_settings.ms_show_hide_editors')}">${t('artsmoker.ui.model_settings.ms_view_all')}</button>
                                <button id="ms-tmpl-reset-all" class="btn btn-sm text-[10px] px-3 border border-brand-border text-brand-text-muted hover:border-red-500 hover:text-red-400 whitespace-nowrap" title="${t('artsmoker.ui.model_settings.ms_reset_all_templates')}">${t('artsmoker.ui.model_settings.templates_reset_all') || 'Reset All'}</button>
                            </div>
                            <div id="ms-templates-list" class="space-y-3">
                                <p class="text-xs text-brand-text-muted text-center py-4">${t('artsmoker.ui.model_settings.ms_loading_templates')}</p>
                            </div>
                        </div>

                        <!-- Tab: Custom Models -->
                        <div class="ms-tab-panel hidden" data-ms-panel="custom-models">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-xs text-brand-text-muted">${t('artsmoker.ui.custom_models.subtitle')}</p>
                                <div class="flex gap-2">
                                    <button id="ms-cm-hf-token" class="btn btn-sm text-xs flex items-center gap-1 border border-amber-500/30 text-amber-300 hover:bg-amber-500/10 rounded-lg px-3 py-1.5" title="${t('artsmoker.ui.model_settings.ms_manage_hf')}">
                                        🔑 HF Token
                                    </button>
                                    <button id="ms-cm-add" class="btn btn-sm text-xs flex items-center gap-1 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 rounded-lg px-3 py-1.5" title="${t('artsmoker.ui.custom_models.add_model_advanced_hint')}">
                                        + ${t('artsmoker.ui.custom_models.add_model')} <span class="text-[8px] opacity-50">(${t('artsmoker.ui.custom_models.advanced')})</span>
                                    </button>
                                    <button id="ms-cm-refresh" class="btn btn-secondary btn-sm text-xs flex items-center gap-1">
                                        🔄 ${t('artsmoker.ui.custom_models.refresh_status') || 'Refresh Status'}
                                    </button>
                                </div>
                            </div>
                            <div id="ms-custom-models-content">
                                <p class="text-xs text-brand-text-muted">${t('artsmoker.ui.custom_models.loading_catalog')}</p>
                            </div>
                        </div>

                        <!-- Tab: Registry JSON -->
                        <div class="ms-tab-panel hidden" data-ms-panel="registry-json">
                            <p class="text-xs text-brand-text-muted mb-2">${t('artsmoker.ui.model_settings.json_desc')}</p>
                            <textarea id="ms-json-editor" class="w-full h-[50vh] font-mono text-xs p-3 rounded-lg bg-brand-bg border border-brand-border text-brand-text resize-none" spellcheck="false">${JSON.stringify(reg, null, 2)}</textarea>
                            <div class="flex items-center gap-2 mt-2">
                                <button id="ms-json-save" class="btn btn-primary btn-sm text-xs">${t('artsmoker.ui.model_settings.save_json')}</button>
                                <button id="ms-json-reset" class="btn btn-secondary btn-sm text-xs">${t('artsmoker.ui.model_settings.reset_json')}</button>
                                <span id="ms-json-status" class="text-[10px] text-brand-text-muted"></span>
                            </div>
                        </div>

                        <!-- Tab: Maintenance / system tools -->
                        <div class="ms-tab-panel hidden" data-ms-panel="maintenance">
                            <h3 class="text-sm font-semibold text-brand-text mb-1">${t('artsmoker.ui.model_settings.blender_title')}</h3>
                            <p class="text-xs text-brand-text-muted mb-3">${t('artsmoker.ui.model_settings.blender_desc')}</p>
                            <div class="flex items-center gap-3 flex-wrap">
                                <button id="ms-blender-update" class="btn btn-secondary btn-sm text-xs">${t('artsmoker.ui.model_settings.blender_update_btn')}</button>
                                <span id="ms-blender-status" class="text-[11px] text-brand-text-muted">${t('artsmoker.ui.model_settings.blender_status_loading')}</span>
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

            // Activate the requested tab (opened from a specific studio) or
            // restore the tab that was active before a re-render (e.g. after a
            // Sync), so the user stays where they were instead of snapping to
            // Image Studio.
            const tabToActivate = this._requestedTab || this._activeTab;
            if (tabToActivate) {
                const targetTab = modal.querySelector(`[data-ms-tab="${tabToActivate}"]`);
                if (targetTab) {
                    targetTab.click();
                }
                this._requestedTab = null;
            }
        },

        _sourceBadge(model) {
            const source = model.model_source || 'foundation';
            if (source === 'custom') return raw('<span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20 font-medium">Custom</span>');
            if (source === 'imported') return raw('<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/20 font-medium">Imported</span>');
            return '';
        },

        // Lifecycle badge — the ONLY place a Legacy/EOL/unavailable model is surfaced
        // (they're excluded from the pickers). Data is AWS-objective (lifecycle_status /
        // end_of_life_time from the base registry) plus the per-account
        // lifecycle_unavailable flag from user.json.
        _lifecycleBadge(m) {
            if (!m) return '';
            const eol = String(m.end_of_life_time || '').slice(0, 10);
            if (m.lifecycle_unavailable) {
                return html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/20 font-medium" title="${t('artsmoker.ui.model_settings.lifecycle_unavailable_hint')}">${t('artsmoker.ui.model_settings.lifecycle_unavailable')}${eol ? ' · EOL ' + eol : ''}</span>`;
            }
            if ((m.lifecycle_status || 'ACTIVE') === 'LEGACY') {
                return html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20 font-medium" title="${t('artsmoker.ui.model_settings.lifecycle_legacy_hint')}">${t('artsmoker.ui.model_settings.lifecycle_legacy')}${eol ? ' · EOL ' + eol : ''}</span>`;
            }
            return '';
        },

        _renderImageModels(reg) {
            const models = reg.image_models || {};
            if (Object.keys(models).length === 0) {
                return html`<p class="text-sm text-brand-text-muted py-4 text-center">${t('artsmoker.ui.model_settings.no_models')}</p>`;
            }

            // Per-purpose short tag shown on each model card (its specific role).
            const PURPOSE_TAG = {
                'text_to_image': t('artsmoker.ui.model_settings.generation'),
                'image_edit': t('artsmoker.ui.model_settings.image_edit'),
                'inpainting': t('artsmoker.ui.model_settings.inpainting'),
                'outpainting': t('artsmoker.ui.model_settings.outpainting'),
                'erase': t('artsmoker.ui.model_settings.erase_label'),
                'search_replace': t('artsmoker.ui.model_settings.search_replace'),
                'search_recolor': t('artsmoker.ui.model_settings.search_recolor'),
                'control_sketch': t('artsmoker.ui.model_settings.control_sketch'),
                'control_structure': t('artsmoker.ui.model_settings.control_structure'),
                'style_guide': t('artsmoker.ui.model_settings.style_guide'),
                'style_transfer': t('artsmoker.ui.model_settings.style_transfer'),
                'remove_background': t('artsmoker.ui.model_settings.remove_bg'),
                'upscale_creative': t('artsmoker.ui.model_settings.upscale_creative'),
                'upscale_conservative': t('artsmoker.ui.model_settings.upscale_conservative'),
                'upscale_fast': t('artsmoker.ui.model_settings.upscale_fast'),
            };

            // Consolidate the many fine-grained purposes into a few top-level
            // sections so the list stays navigable (was 16 sections, mostly with
            // one model each). Each model still shows its specific role via a tag.
            // Mapping is purpose→section; an UNKNOWN purpose falls back to its own
            // section (keyed by the raw purpose) so nothing is ever hidden.
            const SECTIONS = [
                { id: 'generation', label: t('artsmoker.ui.model_settings.section_generation'),
                  purposes: ['text_to_image'] },
                { id: 'editing', label: t('artsmoker.ui.model_settings.section_editing'),
                  purposes: ['image_edit', 'inpainting', 'outpainting', 'erase', 'search_replace', 'search_recolor'] },
                { id: 'upscaling', label: t('artsmoker.ui.model_settings.section_upscaling'),
                  purposes: ['upscale_creative', 'upscale_conservative', 'upscale_fast'] },
                { id: 'control_style', label: t('artsmoker.ui.model_settings.section_control_style'),
                  purposes: ['control_sketch', 'control_structure', 'style_guide', 'style_transfer'] },
                { id: 'background', label: t('artsmoker.ui.model_settings.section_background'),
                  purposes: ['remove_background'] },
            ];
            // purpose → section index (built from the map above).
            const _purposeToSection = {};
            SECTIONS.forEach((s, i) => s.purposes.forEach(p => { _purposeToSection[p] = i; }));

            // A purpose may be missing on Amazon variants (e.g. nova_canvas_inpaint
            // carries no model_purpose) — infer it from the key so it still lands
            // in the right section. Discovery/editing use capabilities, not this;
            // this is purely for grouping the settings list.
            const _inferPurpose = (key, m) => {
                if (m.model_purpose) return m.model_purpose;
                const k = key.toLowerCase();
                if (k.includes('inpaint')) return 'inpainting';
                if (k.includes('outpaint')) return 'outpainting';
                if (k.includes('erase')) return 'erase';
                if (k.includes('upscale')) return 'upscale_creative';
                if (k.includes('background') || k.includes('_bg')) return 'remove_background';
                return 'other';
            };

            // Bucket models into sections; unknown purposes get their own trailing section.
            const buckets = SECTIONS.map(() => []);
            const extraSections = {};  // rawPurpose → entries[]
            for (const [key, m] of Object.entries(models)) {
                const purpose = _inferPurpose(key, m);
                const si = _purposeToSection[purpose];
                if (si != null) buckets[si].push([key, m, purpose]);
                else (extraSections[purpose] = extraSections[purpose] || []).push([key, m, purpose]);
            }

            const _sectionColors = ['text-brand-accent', 'text-emerald-400', 'text-purple-400', 'text-cyan-400', 'text-amber-400', 'text-pink-400', 'text-teal-400', 'text-indigo-400'];
            const renderSection = (label, entries, idx) => {
                if (!entries.length) return '';
                const color = _sectionColors[idx % _sectionColors.length];
                return html`
                    <details class="mb-3 ms-collapsible">
                        <summary class="text-sm font-semibold ${color} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">
                            ${label}
                            <span class="text-[10px] font-normal text-brand-text-muted">(${entries.length})</span>
                        </summary>
                        <div class="space-y-2 mt-2">
                            ${entries.map(([key, m, purpose]) => this._renderSingleModel(key, m, PURPOSE_TAG[purpose] || ''))}
                        </div>
                    </details>
                `;
            };

            let idx = 0;
            const mainHtml = SECTIONS.map((s, i) => renderSection(s.label, buckets[i], idx++));
            // Any unmapped purposes (future/unknown) render after, labeled by their tag or raw key.
            const extraHtml = Object.entries(extraSections)
                .map(([purpose, entries]) => renderSection(PURPOSE_TAG[purpose] || purpose, entries, idx++));
            return html`${mainHtml}${extraHtml}`;
        },

        // Custom-hosted (SageMaker) models are billed per HOUR of instance uptime, so
        // a per-image price is misleading (idle/spin-up bills on top of generation).
        // Resolve the live hourly rate from the registry the component already loaded
        // (sagemaker_pricing[instance|region] → gpu_instances seed) + typical latency.
        _customHourly(m) {
            const inst = m.deployment && m.deployment.instance_type;
            const region = m.deployment && m.deployment.region;
            let hourly = null;
            if (inst) {
                const sp = (this._registry && this._registry.sagemaker_pricing) || {};
                hourly = sp[`${inst}|${region}`] || null;
                if (!hourly) {
                    const gi = (this._registry && this._registry.custom_model_catalog
                                && this._registry.custom_model_catalog.gpu_instances) || {};
                    hourly = (gi[inst] && gi[inst].cost_per_hour_usd) || null;
                }
            }
            const lat = (m.invoke && m.invoke.typical_latency_seconds) || 0;
            return { hourly, minutes: lat ? Math.max(1, Math.round(lat / 60)) : null };
        },

        _isCustomHosted(m) {
            return m.model_source === 'custom_hosted' || String(m.model_id || '').startsWith('sagemaker:');
        },

        // Cost label: per-HOUR + typical time for custom models (no per-image $);
        // per-image for Bedrock foundation models. "Pricing unavailable" when the
        // registry has no rate (never a fabricated number).
        _costLabel(m) {
            if (this._isCustomHosted(m)) {
                const d = this._customHourly(m);
                if (d.hourly) {
                    const hr = t('artsmoker.ui.model_settings.cost_hourly', { cost: d.hourly.toFixed(2) });
                    return d.minutes ? `${hr} · ${t('artsmoker.ui.model_settings.cost_per_gen_time', { min: d.minutes })}` : hr;
                }
                return t('artsmoker.ui.model_settings.pricing_unavailable');
            }
            return m.base_price_usd != null ? `$${m.base_price_usd.toFixed(2)}/img` : t('artsmoker.ui.common.unknown');
        },

        // Cost label for a CUSTOM-MODEL CATALOG entry (not yet deployed): per-hour of
        // its recommended instance + typical time. Different data shape than a deployed
        // model (recommended_instance + pricing.instance_cost_per_hour, or live
        // gpu_instances), hence its own resolver.
        _catalogCostLabel(m) {
            const inst = m.requirements && m.requirements.recommended_instance;
            const ich = (m.pricing && m.pricing.instance_cost_per_hour) || {};
            let hourly = inst ? ich[inst] : null;
            if (!hourly) { const vals = Object.values(ich); hourly = vals.length ? vals[0] : null; }
            if (!hourly && inst) {
                const gi = (this._registry && this._registry.custom_model_catalog
                            && this._registry.custom_model_catalog.gpu_instances) || {};
                hourly = (gi[inst] && gi[inst].cost_per_hour_usd) || null;
            }
            const lat = (m.invoke && m.invoke.typical_latency_seconds) || 0;
            const min = lat ? Math.max(1, Math.round(lat / 60)) : null;
            if (hourly) {
                const hr = t('artsmoker.ui.model_settings.cost_hourly', { cost: hourly.toFixed(2) });
                return min ? `${hr} · ${t('artsmoker.ui.model_settings.cost_per_gen_time', { min })}` : hr;
            }
            return t('artsmoker.ui.model_settings.pricing_unavailable');
        },

        _renderSingleModel(key, m, purposeTag = '') {
            const regions = (m.available_regions || [m.region]).join(', ');
            const quality = (m.quality_options || []).map(q => q.label).join(' / ') || t('artsmoker.ui.model_settings.no_tiers');
            const price = this._costLabel(m);
            const strictColor = m.moderation_strictness === 'very_strict' ? 'text-red-400' : m.moderation_strictness === 'strict' ? 'text-amber-400' : 'text-emerald-400';
            const sourceBadge = this._sourceBadge(m);

            // A single instruction-editor (e.g. Qwen-Image-Edit) can serve MANY
            // edit modes. It's listed once here (one endpoint, one enable toggle),
            // so surface every edit purpose its capabilities cover — otherwise a
            // user seeing it only under "Image Editing — Instruction" would think
            // it can't inpaint/outpaint/erase. Derived from cfg.capabilities, so
            // nothing is hard-coded: new capability flags appear automatically.
            const _editModeLabels = {
                image_edit: t('artsmoker.ui.model_settings.image_edit'),
                inpainting: t('artsmoker.ui.model_settings.inpainting'),
                outpainting: t('artsmoker.ui.model_settings.outpainting'),
                erase: t('artsmoker.ui.model_settings.erase_label'),
                search_replace: t('artsmoker.ui.model_settings.search_replace'),
                search_recolor: t('artsmoker.ui.model_settings.search_recolor'),
                reference_guided: t('artsmoker.ui.model_settings.reference_guided'),
            };
            const coveredModes = m.capabilities && typeof m.capabilities === 'object'
                ? Object.keys(_editModeLabels).filter(p => m.capabilities[p] === true)
                : [];
            const capabilitiesHtml = coveredModes.length
                ? html`<div class="text-[10px] text-brand-text-muted mb-2">${t('artsmoker.ui.model_settings.also_covers')}: <span class="text-brand-text/70">${coveredModes.map(p => _editModeLabels[p]).join(' · ')}</span></div>`
                : '';

            // Default absent `enabled` to ON — matches backend .get("enabled", True)
            // and the chat/video rows. (Discovered models are enabled by default and
            // no longer carry an explicit enabled:true in user.json.)
            const enabled = m.enabled !== false;
            return html`
                    <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${enabled ? '' : 'opacity-50'}" data-image-model="${key}">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center gap-2">
                                <label class="toggle toggle-sm">
                                    <input type="checkbox" class="ms-img-toggle" data-key="${key}" ${enabled ? 'checked' : ''} />
                                    <span class="toggle-slider"></span>
                                </label>
                                <span class="text-sm font-medium">${m.label || key}</span>
                                ${purposeTag ? html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-brand-accent/15 text-brand-accent/90 uppercase tracking-wide">${purposeTag}</span>` : ''}
                                <span class="text-[10px] text-brand-text-muted">${m.provider || ''}</span>
                                ${sourceBadge}
                                ${this._lifecycleBadge(m)}
                            </div>
                            <span class="${strictColor} text-[10px]">${m.moderation_strictness || ''}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-brand-text-muted mb-2">
                            <span>${t('artsmoker.ui.model_settings.field_model_id')}: <span class="font-mono text-brand-text/70">${m.model_id || ''}</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_format')}: <span class="text-brand-text/70">${m.format_family || ''}</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_regions')}: <span class="text-brand-text/70">${regions || t('artsmoker.ui.common.none').toLowerCase()}</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_prompt_limit_short')}: <span class="text-brand-text/70">${m.prompt_limit || '?'} chars</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_quality')}: <span class="text-brand-text/70">${quality}</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_price')}: <span class="text-emerald-400/70">${price}</span></span>
                        </div>
                        ${capabilitiesHtml}
                        <details class="group">
                            <summary class="text-[10px] text-brand-accent cursor-pointer hover:text-brand-accent-hover">
                                <span class="group-open:hidden">${t('artsmoker.ui.model_settings.edit_link')}</span>
                                <span class="hidden group-open:inline">${t('artsmoker.ui.model_settings.close_editor')}</span>
                            </summary>
                            <div class="mt-2 space-y-2 p-2 rounded bg-brand-bg/60 border border-brand-border/50">
                                <div class="grid grid-cols-2 gap-2">
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.field_model_id')}</label>
                                        <input type="text" class="ms-edit-field input text-xs font-mono w-full" data-key="${key}" data-field="model_id" value="${m.model_id || ''}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.field_label')}</label>
                                        <input type="text" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="label" value="${m.label || ''}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.field_prompt_limit')}</label>
                                        <input type="number" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="prompt_limit" value="${m.prompt_limit || 900}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.field_base_price')}</label>
                                        <input type="number" step="0.01" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="base_price_usd" value="${m.base_price_usd || ''}" />
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.field_moderation')}</label>
                                        <select class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="moderation_strictness">
                                            ${['moderate', 'strict', 'very_strict'].map(s => html`<option value="${s}" ${s === m.moderation_strictness ? 'selected' : ''}>${s}</option>`)}
                                        </select>
                                    </div>
                                    <div>
                                        <label class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.field_default_region')}</label>
                                        <input type="text" class="ms-edit-field input text-xs w-full" data-key="${key}" data-field="region" value="${m.region || ''}" />
                                    </div>
                                </div>
                                <button class="ms-edit-save btn btn-primary btn-sm text-xs" data-key="${key}">${t('artsmoker.ui.model_settings.save_changes')}</button>
                            </div>
                        </details>
                    </div>
                `;
        },

        _renderChatModels(reg) {
            const models = reg.chat_models || {};
            if (Object.keys(models).length === 0) {
                return html`<p class="text-sm text-brand-text-muted py-4 text-center">${t('artsmoker.ui.model_settings.no_chat_models')}</p>`;
            }

            // Group by provider
            const groups = {};
            for (const [key, m] of Object.entries(models)) {
                const provider = m.provider || 'Other';
                if (!groups[provider]) groups[provider] = [];
                groups[provider].push([key, m]);
            }

            const _providerColors = ['text-brand-accent', 'text-emerald-400', 'text-purple-400', 'text-cyan-400', 'text-amber-400', 'text-pink-400', 'text-teal-400', 'text-indigo-400'];
            return html`${Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0])).map(([provider, entries], idx) => {
                const color = _providerColors[idx % _providerColors.length];
                return html`
                    <details class="mb-3 ms-collapsible">
                        <summary class="text-sm font-semibold ${color} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">
                            ${provider}
                            <span class="text-[10px] font-normal text-brand-text-muted">(${entries.length})</span>
                        </summary>
                        <div class="space-y-1.5 mt-2">
                            ${entries.sort((a, b) => (a[1].label || '').localeCompare(b[1].label || '')).map(([key, m]) => {
                                const regions = (m.available_regions || []).length;
                                const vision = m.has_vision ? html`<span class="text-[9px] px-1 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20">${t('artsmoker.ui.model_settings.vision_badge')}</span>` : '';
                                const streaming = m.streaming_supported ? '' : html`<span class="text-[9px] px-1 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20">${t('artsmoker.ui.model_settings.no_stream')}</span>`;
                                const ctx = (m.max_context_tokens || 128000) >= 1000000
                                    ? `${Math.round((m.max_context_tokens || 128000) / 1000000)}M`
                                    : `${Math.round((m.max_context_tokens || 128000) / 1000)}K`;
                                const enabled = m.enabled !== false;
                                return html`
                                    <div class="p-2.5 rounded-lg bg-brand-bg/40 border border-brand-border ${enabled ? '' : 'opacity-50'} flex items-center gap-3">
                                        <label class="toggle toggle-sm flex-shrink-0">
                                            <input type="checkbox" class="ms-chat-toggle" data-key="${key}" ${enabled ? 'checked' : ''} />
                                            <span class="toggle-slider"></span>
                                        </label>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center gap-2">
                                                <span class="text-xs font-medium truncate">${m.label || key}</span>
                                                ${vision}${streaming}
                                                ${this._lifecycleBadge(m)}
                                                <span class="text-[9px] text-brand-text-muted">${ctx} ${t('artsmoker.ui.model_settings.context_label')}</span>
                                            </div>
                                            <div class="text-[10px] text-brand-text-muted font-mono truncate mt-0.5">${m.model_id || ''}</div>
                                        </div>
                                        <div class="flex-shrink-0 text-right">
                                            <span class="text-[10px] text-brand-accent">${regions} ${t('artsmoker.ui.common.region').toLowerCase()}${regions !== 1 ? 's' : ''}</span>
                                            <div class="flex flex-wrap gap-0.5 mt-0.5 justify-end max-w-[200px]">
                                                ${(m.available_regions || []).map(r => html`<span class="text-[8px] px-1 py-0 rounded bg-brand-bg text-brand-text-muted/60">${r}</span>`)}
                                            </div>
                                        </div>
                                    </div>`;
                            })}
                        </div>
                    </details>`;
            })}`;
        },

        _renderVideoModels(reg) {
            const models = reg.video_models || {};
            if (Object.keys(models).length === 0) {
                return html`<p class="text-sm text-brand-text-muted py-4 text-center">${t('artsmoker.ui.model_settings.no_video_models')}</p>`;
            }
            return html`${Object.entries(models).map(([key, m]) => {
                const enabled = m.enabled !== false;
                const regions = m.available_regions || [m.region].filter(Boolean);
                // Custom-hosted video → per-hour + time; Bedrock video → per-second.
                const price = this._isCustomHosted(m)
                    ? this._costLabel(m)
                    : (m.base_price_per_second_usd ? `$${m.base_price_per_second_usd}/sec` : '');
                const sourceBadge = this._sourceBadge(m);
                return html`
                    <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${!enabled ? 'opacity-50' : ''}" data-video-key="${key}">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center gap-2">
                                <label class="toggle toggle-sm">
                                    <input type="checkbox" class="ms-video-toggle" data-key="${key}" ${enabled ? 'checked' : ''} />
                                    <span class="toggle-slider"></span>
                                </label>
                                <span class="text-sm font-medium">${m.label || key}</span>
                                <span class="text-[10px] text-brand-text-muted">${m.provider || ''}</span>
                                ${sourceBadge}
                                ${this._lifecycleBadge(m)}
                            </div>
                            <div class="flex items-center gap-1.5">
                                ${price ? html`<span class="badge badge-indigo">${price}</span>` : ''}
                                ${m.supports_image_input ? raw('<span class="badge badge-indigo">img\u2192vid</span>') : ''}
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-brand-text-muted mb-2">
                            <span>${t('artsmoker.ui.model_settings.field_model_id')}: <span class="font-mono text-brand-text/70">${m.model_id || ''}</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_format')}: <span class="text-brand-text/70">${m.format_family || ''}</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_prompt_limit_short')}: <span class="text-brand-text/70">${m.prompt_limit || '?'} chars</span></span>
                            <span>${t('artsmoker.ui.model_settings.field_default_region')}: <span class="text-brand-text/70">${m.region || ''}</span></span>
                        </div>
                        <div class="flex flex-wrap gap-1 mb-1">
                            ${regions.map(r => html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-brand-accent/10 text-brand-accent border border-brand-accent/20">${r}</span>`)}
                        </div>
                    </div>
                `;
            })}`;
        },

        _renderCategory(name, cat) {
            if (!cat) return '';
            const chatModels = this._registry?.chat_models || {};
            const currentId = cat.current || '';
            // Match the category's current model to a chat_models entry by EXACT
            // id (modulo the us. inference-profile prefix). The old code matched
            // by "family" (everything before the first digit), so e.g. the
            // current opus-4-8 matched the FIRST "claude" entry encountered —
            // showing a stale older Opus/Sonnet label even though current was the
            // newest. Exact match only; no family fuzz.
            const bare = (id) => (id || '').replace(/^us\./, '');
            const isExact = (mid) => mid === currentId || bare(mid) === bare(currentId);

            // Build options grouped by provider
            const groups = {};
            Object.entries(chatModels)
                .filter(([, m]) => m.enabled !== false)
                .forEach(([, m]) => {
                    const provider = m.provider || 'Other';
                    if (!groups[provider]) groups[provider] = [];
                    const mid = m.model_id || '';
                    const selected = isExact(mid);
                    const regions = (m.available_regions || []).length;
                    groups[provider].push({ mid, label: m.label || mid, provider, regions, region: m.region || '', selected });
                });

            let optionsHtml = '';
            for (const [provider, models] of Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]))) {
                // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                optionsHtml += `<optgroup label="${this._esc(provider)}">`;
                models.sort((a, b) => a.label.localeCompare(b.label)).forEach(m => {
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    optionsHtml += `<option value="${this._esc(m.mid)}" data-region="${this._esc(m.region)}" ${m.selected ? 'selected' : ''}>${this._esc(m.label)}${m.regions > 1 ? ` (${m.regions} regions)` : ''}</option>`;
                });
                optionsHtml += '</optgroup>';
            }

            // Find the exact current model's label; fallback option if absent.
            let currentLabel = currentId;
            let hasMatch = false;
            for (const m of Object.values(chatModels)) {
                if (isExact(m.model_id || '')) { currentLabel = m.label || m.model_id; hasMatch = true; break; }
            }
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            const fallbackOpt = !hasMatch && currentId ? `<option value="${this._esc(currentId)}" selected>${this._esc(currentId)} (current)</option>` : '';

            return html`
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border" data-category="${name}">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm font-medium">${cat.label || name}</span>
                        <span class="text-[10px] text-brand-text-muted font-mono bg-brand-bg px-2 py-0.5 rounded">${cat.region || ''}</span>
                    </div>
                    <p class="text-[10px] text-brand-text-muted/50 mb-2">${cat.description || ''}</p>
                    <div class="flex gap-2">
                        <div class="flex-1 relative ms-searchable-select">
                            <input type="text" class="ms-cat-search input text-xs w-full" data-cat="${name}" placeholder="${t('artsmoker.ui.custom_models.search_models')}" value="${currentLabel}" autocomplete="off" />
                            <select class="ms-cat-model hidden" data-cat="${name}">
                                ${raw(fallbackOpt)}
                                ${raw(optionsHtml)}
                            </select>
                            <div class="ms-cat-dropdown hidden absolute left-0 right-0 top-full mt-1 z-50 bg-brand-surface border border-brand-border rounded-lg shadow-xl max-h-60 overflow-y-auto"></div>
                        </div>
                        <input type="text" class="ms-cat-region input text-xs w-28" value="${cat.region || ''}" data-cat="${name}" placeholder="${t('artsmoker.ui.common.region')}" />
                        <button class="ms-cat-save btn btn-primary btn-sm text-xs" data-cat="${name}">${t('artsmoker.ui.common.save')}</button>
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
            return html`
                <details class="ms-collapsible">
                    <summary class="text-sm font-semibold text-purple-400 uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${t('artsmoker.ui.model_settings.custom_llms')} <span class="text-[10px] font-normal text-brand-text-muted">(${Object.keys(models).length})</span></summary>
                    <p class="text-[10px] text-brand-text-muted mb-2 mt-2">${t('artsmoker.ui.model_settings.custom_llms_desc')}</p>
                    <div class="space-y-2">
                        ${Object.entries(models).map(([key, m]) => {
                            const source = m.model_source || 'custom';
                            const badge = source === 'imported'
                                ? raw('<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/20 font-medium">Imported</span>')
                                : raw('<span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20 font-medium">Custom</span>');
                            const enabledBadge = m.enabled
                                ? html`<span class="text-[9px] text-emerald-400">${t('artsmoker.ui.model_settings.ready')}</span>`
                                : html`<span class="text-[9px] text-amber-400">${t('artsmoker.ui.model_settings.needs_throughput')}</span>`;
                            return html`
                                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${m.enabled ? '' : 'opacity-60'}">
                                    <div class="flex items-center gap-2 mb-1">
                                        <span class="text-sm font-medium">${m.label || key}</span>
                                        ${badge}
                                        ${enabledBadge}
                                    </div>
                                    <div class="grid grid-cols-2 gap-x-4 text-[10px] text-brand-text-muted">
                                        <span>${t('artsmoker.ui.model_settings.field_model_id')}: <span class="font-mono text-brand-text/70 break-all">${(m.model_id || '').slice(-40)}</span></span>
                                        <span>${t('artsmoker.ui.common.region')}: <span class="text-brand-text/70">${m.region || ''}</span></span>
                                        ${m.architecture ? html`<span>Architecture: <span class="text-brand-text/70">${m.architecture}</span></span>` : ''}
                                        ${m.customization_type ? html`<span>Type: <span class="text-brand-text/70">${m.customization_type}</span></span>` : ''}
                                    </div>
                                </div>
                            `;
                        })}
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
                    // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
                    return `<option value="${this._esc(isMatch ? currentId : mid)}" data-region="${this._esc(im.region || '')}" ${isMatch ? 'selected' : ''}>${this._esc(im.label || mid)} (${this._esc(im.provider || '')})</option>`;
                }).join('');
            const hasMatch = modelOptions.includes('selected');
            // nosemgrep -- hand-escaped raw HTML template (values via _esc/escAttr, i18n via t()); not the html`` helper
            const fallbackOpt = !hasMatch && currentId ? `<option value="${this._esc(currentId)}" selected>${this._esc(m.label || currentId)}</option>` : '';

            return html`
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border ${m.enabled ? '' : 'opacity-50'}" data-pp="${key}">
                    <div class="flex items-center gap-2 mb-2">
                        <label class="toggle toggle-sm">
                            <input type="checkbox" class="ms-pp-toggle" data-key="${key}" ${m.enabled ? 'checked' : ''} />
                            <span class="toggle-slider"></span>
                        </label>
                        <span class="text-sm font-medium">${m.label || key}</span>
                        <span class="text-[10px] font-mono text-brand-text-muted ml-auto">${m.region || ''}</span>
                    </div>
                    <div class="flex gap-2">
                        <select class="ms-pp-field input text-xs font-mono flex-1" data-key="${key}" data-field="model_id">
                            ${raw(fallbackOpt)}
                            ${raw(modelOptions)}
                        </select>
                        <input type="text" class="ms-pp-field input text-xs w-28" value="${m.region || ''}" data-key="${key}" data-field="region" />
                        <button class="ms-pp-save btn btn-primary btn-sm text-xs" data-key="${key}">${t('artsmoker.ui.common.save')}</button>
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
                    // Remember the active tab so a post-sync re-render restores it
                    // (instead of snapping back to Image Studio).
                    this._activeTab = tab.dataset.msTab;
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
                                this._loadCustomModels(modal, true);  // force = bypass status cache
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
                    // Maintenance tab: load Blender status + wire the Update button (once)
                    if (tab.dataset.msTab === 'maintenance') {
                        this._loadBlenderStatus(modal);
                        const upd = modal.querySelector('#ms-blender-update');
                        if (upd && !upd._wired) {
                            upd._wired = true;
                            upd.addEventListener('click', async () => {
                                const orig = upd.textContent;
                                upd.disabled = true;
                                upd.textContent = t('artsmoker.ui.model_settings.blender_updating') || 'Checking…';
                                try {
                                    const r = await API.admin.blenderUpdate();
                                    if (r.updated) {
                                        window.showToast?.((t('artsmoker.ui.model_settings.blender_update_done') || 'Updated to {{v}}').replace('{{v}}', r.current || ''), 'success');
                                    } else if (r.error) {
                                        window.showToast?.((t('artsmoker.ui.model_settings.blender_update_failed') || 'Update failed') + ': ' + r.error, 'error');
                                    } else {
                                        window.showToast?.(t('artsmoker.ui.model_settings.blender_up_to_date') || 'Already up to date', 'info');
                                    }
                                } catch (e) {
                                    window.showToast?.((t('artsmoker.ui.model_settings.blender_update_failed') || 'Update failed') + ': ' + (e.message || ''), 'error');
                                } finally {
                                    upd.disabled = false;
                                    upd.textContent = orig;
                                    this._loadBlenderStatus(modal);
                                }
                            });
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

            // Reset ALL templates to defaults
            modal.querySelector('#ms-tmpl-reset-all')?.addEventListener('click', async () => {
                if (!await window.showConfirm?.(
                    t('artsmoker.ui.model_settings.templates_reset_all_confirm') || 'Reset ALL prompt templates to their built-in defaults?',
                    { title: t('artsmoker.ui.model_settings.templates_reset_all') || 'Reset All Templates',
                      detail: t('artsmoker.ui.model_settings.templates_reset_all_detail') || 'This discards every edit you have made to every prompt template and restores the shipped defaults. This cannot be undone.',
                      confirmLabel: t('artsmoker.ui.model_settings.templates_reset_all') || 'Reset All' })) return;
                try {
                    const resp = await fetch('/api/admin/templates/reset-all', { method: 'POST' });
                    if (resp.ok) {
                        window.showToast?.(t('artsmoker.ui.model_settings.templates_reset_all_done') || 'All templates reset to defaults', 'success');
                        this._templatesLoaded = false;
                        this._loadTemplates(modal);
                    } else {
                        window.showToast?.(t('artsmoker.ui.model_settings.templates_save_failed') || 'Reset failed', 'error');
                    }
                } catch (e) {
                    window.showToast?.((t('artsmoker.ui.model_settings.templates_save_failed') || 'Reset failed') + ': ' + e.message, 'error');
                }
            });

            // Refresh All
            modal.querySelector('#ms-refresh-all')?.addEventListener('click', async () => {
                if (this._refreshing) return;
                if (!await window.showConfirm(t('artsmoker.ui.model_settings.sync_confirm'), {
                    title: t('artsmoker.ui.model_settings.sync_title'),
                    detail: t('artsmoker.ui.model_settings.sync_detail_full'),
                    confirmLabel: t('artsmoker.ui.model_settings.sync_now'),
                })) return;
                this._refreshing = true;
                const btn = modal.querySelector('#ms-refresh-all');
                btn.disabled = true;
                // nosemgrep
                btn.innerHTML = html`<span class="spinner-sm"></span> ${t('artsmoker.ui.model_settings.syncing')}`;

                // Show progress overlay (dismissible — sync continues in background)
                const overlay = this._showSyncProgress();

                try {
                    const result = await API.admin.refreshAll();
                    // nosemgrep -- {count: …} is a t() params object, not a template string
                    const customMsg = result.total_custom > 0 ? `\n${t('artsmoker.ui.model_settings.sync_custom_count', {count: result.total_custom})}` : '';
                    // nosemgrep -- {count: …} is a t() params object, not a template string
                    const disabledMsg = result.disabled?.length ? `\n${t('artsmoker.ui.model_settings.sync_disabled_count', {count: result.disabled.length})}` : '';

                    this._registry = await API.admin.getModels();
                    const imgCount = Object.keys(this._registry.image_models || {}).length;
                    const vidCount = Object.keys(this._registry.video_models || {}).length;
                    const chatModels = Object.keys(this._registry.chat_models || {}).length;

                    // Close progress overlay and refresh modal
                    overlay?.remove();
                    modal.remove();
                    this._renderModal();

                    await window.showConfirm(
                        t('artsmoker.ui.model_settings.sync_scanned', {count: result.regions_scanned}), {
                        title: t('artsmoker.ui.model_settings.sync_complete'),
                        detail: `${t('artsmoker.ui.model_settings.sync_new')}: ${result.total_new}\n${t('artsmoker.ui.model_settings.sync_updated')}: ${result.total_updated}${customMsg}${disabledMsg}\n\n${t('artsmoker.ui.model_settings.sync_totals')}:\n  ${t('artsmoker.ui.model_settings.sync_image')}: ${imgCount}\n  ${t('artsmoker.ui.model_settings.sync_video')}: ${vidCount}\n  ${t('artsmoker.ui.model_settings.sync_chat')}: ${chatModels}\n  ${t('artsmoker.ui.model_settings.sync_errors')}: ${result.errors || 0}`,
                        confirmLabel: t('artsmoker.ui.common.ok'),
                        cancelLabel: '',
                    });
                } catch (err) {
                    overlay?.remove();
                    await window.showConfirm(t('artsmoker.ui.model_settings.sync_failed_msg'), {
                        title: t('artsmoker.ui.model_settings.sync_failed'),
                        detail: err.message || t('artsmoker.ui.common.unknown'),
                        confirmLabel: t('artsmoker.ui.common.ok'),
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
                        window.showToast?.(`${key} ${enabled ? t('artsmoker.ui.common.enabled') : t('artsmoker.ui.common.disabled')}`, 'success');
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + (err.message || ''), 'error');
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
                        window.showToast?.(`${key} ${enabled ? t('artsmoker.ui.common.enabled') : t('artsmoker.ui.common.disabled')}`, 'success');
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + (err.message || ''), 'error');
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
                        window.showToast?.(`${key} ${enabled ? t('artsmoker.ui.common.enabled') : t('artsmoker.ui.common.disabled')}`, 'success');
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + (err.message || ''), 'error');
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
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_updated').replace('{{name}}', key), 'success');
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + (err.message || ''), 'error');
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
                    let out = '';
                    let hasResults = false;
                    hiddenSelect.querySelectorAll('optgroup, option').forEach(el => {
                        if (el.tagName === 'OPTGROUP') {
                            const groupLabel = el.label || '';
                            const options = Array.from(el.querySelectorAll('option'))
                                .filter(o => !lower || o.textContent.toLowerCase().includes(lower) || groupLabel.toLowerCase().includes(lower));
                            if (options.length > 0) {
                                out += html`<div class="px-3 py-1 text-[9px] text-brand-text-muted/50 uppercase tracking-wider font-semibold bg-black/20 sticky top-0">${groupLabel}</div>`;
                                options.forEach(o => {
                                    const selected = o.selected ? 'bg-brand-accent/10 text-brand-accent' : 'hover:bg-white/5';
                                    out += html`<div class="ms-dd-item px-3 py-1.5 text-xs cursor-pointer ${selected}" data-value="${o.value}" data-region="${o.dataset.region || ''}">${o.textContent}</div>`;
                                });
                                hasResults = true;
                            }
                        } else if (!el.closest('optgroup')) {
                            if (!lower || el.textContent.toLowerCase().includes(lower)) {
                                const selected = el.selected ? 'bg-brand-accent/10 text-brand-accent' : 'hover:bg-white/5';
                                out += html`<div class="ms-dd-item px-3 py-1.5 text-xs cursor-pointer ${selected}" data-value="${el.value}" data-region="${el.dataset.region || ''}">${el.textContent}</div>`;
                                hasResults = true;
                            }
                        }
                    });
                    if (!hasResults) out = html`<div class="px-3 py-2 text-xs text-brand-text-muted">${t('artsmoker.ui.custom_models.no_search_results')}</div>`;
                    // nosemgrep
                    dropdown.innerHTML = out;

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
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_updated').replace('{{name}}', cat), 'success');
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + (err.message || ''), 'error');
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
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + (err.message || ''), 'error');
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
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_updated').replace('{{name}}', key), 'success');
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + (err.message || ''), 'error');
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
                        throw new Error(t('artsmoker.ui.model_settings.missing_keys'));
                    }
                    const resp = await fetch('/api/admin/models', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: jsonEditor.value,
                    });
                    if (!resp.ok) {
                        jsonStatus.textContent = t('artsmoker.ui.model_settings.json_save_not_impl');
                        jsonStatus.className = 'text-[10px] text-amber-400';
                        return;
                    }
                    jsonStatus.textContent = t('artsmoker.ui.model_settings.saved_successfully');
                    jsonStatus.className = 'text-[10px] text-emerald-400';
                    window.showToast?.(t('artsmoker.ui.model_settings.json_saved'), 'success');
                } catch (err) {
                    jsonStatus.textContent = err.message;
                    jsonStatus.className = 'text-[10px] text-red-400';
                }
            });

            modal.querySelector('#ms-json-reset')?.addEventListener('click', () => {
                jsonEditor.value = JSON.stringify(this._registry, null, 2);
                jsonStatus.textContent = t('artsmoker.ui.model_settings.reset_to_loaded');
                jsonStatus.className = 'text-[10px] text-brand-text-muted';
            });
        },

        async _loadBlenderStatus(modal) {
            const el = modal.querySelector('#ms-blender-status');
            if (!el) return;
            try {
                const s = await API.admin.blenderStatus();
                if (!s.available) {
                    const none = t('artsmoker.ui.model_settings.blender_status_none')
                        || 'Not installed — downloads automatically on first FBX export.';
                    // Show WHERE it will be downloaded so the user knows the target dir.
                    el.textContent = s.tools_dir ? `${none} → ${s.tools_dir}` : none;
                    el.title = s.tools_dir || '';
                    return;
                }
                const src = s.source === 'managed'
                    ? (t('artsmoker.ui.model_settings.blender_status_managed') || 'Managed copy')
                    : (t('artsmoker.ui.model_settings.blender_status_system') || 'System install (reused)');
                // Include the exact path so the user knows which Blender is in use.
                el.textContent = `${src} · Blender ${s.version} · ${s.path}`;
                el.title = s.path || '';
            } catch {
                el.textContent = t('artsmoker.ui.model_settings.blender_status_error') || 'Status unavailable';
            }
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
                        // nosemgrep
                        modelSel.innerHTML = (modelData.models || []).map(m =>
                            html`<option value="${m.model_id}" data-region="${m.region}">${m.label} (${m.provider})</option>`
                        ).join('');
                    // nosemgrep
                    } catch { modelSel.innerHTML = html`<option value="">${t('artsmoker.ui.model_settings.ms_no_models')}</option>`; }
                }

                this._renderTemplates(modal);
            } catch (err) {
                // nosemgrep
                container.innerHTML = html`<p class="text-xs text-red-400 py-4">Failed to load templates: ${err.message}</p>`;
            }
        },

        _renderTemplates(modal) {
            const container = modal.querySelector('#ms-templates-list');
            if (!container || !this._templatesData) return;
            const templates = this._templatesData;

            // Group templates by studio/area. Every group lists its known
            // templates; any registry template NOT explicitly listed is collected
            // into a catch-all "Other" group so NOTHING is ever hidden and newly
            // added templates always appear (self-healing). friendlyLabel is an
            // optional nicety — the authoritative label/description come from the
            // registry and are shown by _renderSingleTemplate.
            // Six workflow sections — every template placed once, nothing hidden.
            // Any registry template NOT listed here still self-heals into a
            // catch-all "Other" group below (so newly added prompts always appear).
            const GROUPS = [
                { key: 'image_generation', label: 'Image Generation', color: 'text-brand-accent', templates: [
                    { name: 'image_refine_single', friendlyLabel: 'Prompt Refinement — how your text is turned into a detailed image prompt' },
                    { name: 'image_concepts_multi', friendlyLabel: 'Creative Options — how multiple distinct concepts are generated from one idea' },
                    { name: 'image_refine_marketing', friendlyLabel: 'Marketing Banners — specialized prompt for banner compositions' },
                    { name: 'image_asset_type_context', friendlyLabel: 'Asset-Type Intent — the creative direction per asset type (game asset, character, etc.)' },
                    { name: 'image_style_section', friendlyLabel: 'Style-Hints Framing — how a Style Library style is woven into the prompt' },
                    { name: 'asset_type_classify', friendlyLabel: 'Asset-Type Suggestion — suggests the best asset type for your prompt' },
                    { name: 'prompt_decompose', friendlyLabel: 'Prompt Designer — breaks your idea into editable visual components' },
                    { name: 'prompt_recompose', friendlyLabel: 'Prompt Designer — recomposes edited components into a final prompt' },
                ]},
                { key: 'image_editing', label: 'Image Editing & Reference', color: 'text-cyan-400', templates: [
                    { name: 'edit_prompt_suggestion', friendlyLabel: 'Generate Prompt (Edit tab) — reads the image + intent and suggests an edit prompt per mode' },
                    { name: 'reference_intent_extraction', friendlyLabel: 'Inspired-By — reads reference image(s) + your instruction into an enhanced prompt' },
                    { name: 'reference_edit_instruction', friendlyLabel: 'Match-the-Reference — shapes your instruction for the reference edit model' },
                    { name: 'inpaint_removal_transform', friendlyLabel: 'Inpaint Removal — turns a "remove X" request into a fill description' },
                ]},
                { key: 'style_library', label: t('artsmoker.ui.nav.style_library'), color: 'text-purple-400', templates: [
                    { name: 'style_analysis_full', friendlyLabel: 'Style Analysis — how reference images are analyzed for visual attributes' },
                    { name: 'style_hints_generation', friendlyLabel: 'Style Hints — how analyzed style is distilled into generation directives' },
                    { name: 'style_cohesion_check', friendlyLabel: 'Cohesion Check — quick check if references are unified or diverse' },
                ]},
                { key: 'three_d_video', label: '3D & Video', color: 'text-pink-400', templates: [
                    { name: 'three_d_source_analysis', friendlyLabel: 'Source Check — detects if a 2D image is cropped/incomplete before image-to-3D' },
                    { name: 'video_enhance_prompt', friendlyLabel: 'Video Prompt Enhancement — adds camera movements, lighting, and temporal cues' },
                ]},
                { key: 'moderation', label: 'Content Safety', color: 'text-amber-400', templates: [
                    { name: 'moderation_prescreen', friendlyLabel: 'Pre-Screen — predicts if a prompt will be blocked before generating' },
                    { name: 'moderation_rewrite', friendlyLabel: 'Rewrite — rewrites blocked prompts to pass moderation' },
                ]},
                { key: 'system_utilities', label: 'System & Utilities', color: 'text-teal-400', templates: [
                    { name: 'translate_detect_language', friendlyLabel: 'Language Detection — detects language when heuristics are ambiguous' },
                    { name: 'translate_to_english', friendlyLabel: 'Translation to English — translates non-English prompts before generation' },
                    { name: 'chat_context_compact', friendlyLabel: 'Chat: Context Compaction — summarizes older messages to free context space' },
                    { name: 'chat_title_generate', friendlyLabel: 'Chat: Session Title — auto-generates a title from the first exchange' },
                    { name: 'typestudio_layout', friendlyLabel: 'Type Studio: Text Layout — designs text positions, fonts, sizes, and effects' },
                    { name: 'typestudio_layout_output_multi', friendlyLabel: 'Type Studio: Layout Output (multiple) — output format for multiple layout options' },
                    { name: 'typestudio_layout_output_single', friendlyLabel: 'Type Studio: Layout Output (single) — output format for one layout' },
                    { name: 'admin_template_enhance', friendlyLabel: 'Template Editor: Enhance-with-AI — the prompt behind the "Enhance with AI" button here' },
                    { name: 'admin_template_fix_variables', friendlyLabel: 'Template Editor: Fix Variables — the prompt behind "Fix & Save" to reinsert missing variables' },
                ]},
            ];

            // Catch-all: any registry template not placed above → "Other".
            const _grouped = new Set(GROUPS.flatMap(g => g.templates.map(t => t.name)));
            const _ungrouped = Object.keys(templates).filter(n => !_grouped.has(n));
            if (_ungrouped.length) {
                GROUPS.push({ key: 'other', label: 'Other', color: 'text-brand-text-muted',
                    templates: _ungrouped.map(n => ({ name: n, friendlyLabel: '' })) });
            }

            // nosemgrep
            container.innerHTML = GROUPS.map(group => {
                const groupTemplates = group.templates.filter(gt => templates[gt.name]);
                if (groupTemplates.length === 0) return '';
                return html`
                    <details class="mb-4 ms-collapsible">
                        <summary class="text-sm font-semibold ${group.color} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">${group.label} <span class="text-[10px] font-normal text-brand-text-muted">(${groupTemplates.length})</span></summary>
                        <div class="mt-2">
                            <div class="flex justify-end mb-1">
                                <button class="ms-tmpl-group-toggle text-[9px] text-brand-text-muted hover:text-brand-accent cursor-pointer" data-group="${group.key}">${t('artsmoker.ui.model_settings.ms_expand_editors')}</button>
                            </div>
                            <div class="space-y-2">
                                ${groupTemplates.map(gt => {
                                    const name = gt.name;
                                    const tmpl = templates[name];
                                    return this._renderSingleTemplate(name, tmpl, gt.friendlyLabel);
                                })}
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
            const modified = tmpl.modified ? html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20 ml-2">${t('artsmoker.ui.model_settings.templates_modified')}</span>` : '';
            const vars = (tmpl.variables || []).map(v => html`<code class="text-[9px] text-brand-accent bg-brand-accent/10 px-1 rounded">${v}</code>`).join(' ');
            // The registry's authoritative label + description + used_by (no longer masked).
            const title = friendlyLabel || tmpl.label || name;
            const desc = tmpl.description ? html`<p class="text-[10px] text-brand-text-muted/70 mb-1">${tmpl.description}</p>` : '';
            const usedBy = tmpl.used_by ? html`<p class="text-[9px] text-brand-text-muted/50 mb-2">${t('artsmoker.ui.model_settings.templates_used_by') || 'Used by'}: ${tmpl.used_by}</p>` : '';
            const hasSystem = typeof tmpl.system_prompt === 'string';
            const systemEditor = hasSystem ? html`
                            <label class="block text-[10px] text-brand-text-muted mt-1">${t('artsmoker.ui.model_settings.templates_system_prompt') || 'System prompt (steers the LLM)'}</label>
                            <textarea class="ms-tmpl-system input w-full h-28 font-mono text-xs resize-y" data-tmpl="${name}" spellcheck="false">${tmpl.system_prompt || ''}</textarea>` : '';
            return html`
                <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border" data-tmpl="${name}">
                    <div class="flex items-center justify-between mb-1">
                        <div class="flex items-center gap-2">
                            <span class="text-sm font-medium">${title}</span>
                            ${modified}
                        </div>
                        <span class="text-[9px] text-brand-text-muted">${tmpl.model || ''}</span>
                    </div>
                    ${desc}
                    ${usedBy}
                    <p class="text-[10px] text-brand-text-muted/60 mb-2">${t('artsmoker.ui.model_settings.templates_variables')}: ${raw(vars || 'none')}</p>
                    <details class="group">
                        <summary class="text-[10px] text-brand-accent cursor-pointer hover:text-brand-accent-hover">
                            <span class="group-open:hidden">${t('artsmoker.ui.model_settings.templates_edit')}</span>
                            <span class="hidden group-open:inline">${t('artsmoker.ui.model_settings.templates_close_editor')}</span>
                        </summary>
                        <div class="mt-2 space-y-2">
                            <label class="block text-[10px] text-brand-text-muted ${hasSystem ? '' : 'hidden'}">${t('artsmoker.ui.model_settings.templates_prompt_body') || 'Prompt body'}</label>
                            <textarea class="ms-tmpl-text input w-full h-48 font-mono text-xs resize-y" data-tmpl="${name}" spellcheck="false">${tmpl.text || ''}</textarea>
                            ${systemEditor}
                            <div class="flex gap-2 flex-wrap">
                                <button class="ms-tmpl-save btn btn-primary btn-sm text-xs" data-tmpl="${name}">${t('artsmoker.ui.model_settings.templates_save')}</button>
                                <button class="ms-tmpl-enhance btn btn-sm text-xs bg-purple-600 hover:bg-purple-500 text-white" data-tmpl="${name}">${t('artsmoker.ui.model_settings.templates_enhance')}</button>
                                <button class="ms-tmpl-reset btn btn-sm text-xs border border-brand-border text-brand-text-muted hover:border-amber-500 hover:text-amber-400" data-tmpl="${name}">${t('artsmoker.ui.model_settings.templates_reset')}</button>
                            </div>
                            <div class="ms-tmpl-suggestion hidden mt-2 p-2 rounded-lg bg-purple-950/20 border border-purple-500/20" data-tmpl="${name}">
                                <div class="flex items-center justify-between mb-1">
                                    <span class="text-[10px] text-purple-400 font-medium">${t('artsmoker.ui.model_settings.templates_ai_suggestion')}</span>
                                    <div class="flex gap-1">
                                        <button class="ms-tmpl-accept text-[10px] px-2 py-0.5 rounded bg-purple-600 text-white hover:bg-purple-500" data-tmpl="${name}">${t('artsmoker.ui.model_settings.templates_accept')}</button>
                                        <button class="ms-tmpl-dismiss text-[10px] px-2 py-0.5 rounded bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent" data-tmpl="${name}">${t('artsmoker.ui.model_settings.templates_dismiss')}</button>
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
                    // Optional system-prompt editor (only present for templates that have one).
                    const sysArea = container.querySelector(`.ms-tmpl-system[data-tmpl="${name}"]`);
                    const systemVal = sysArea ? sysArea.value : null;  // null = leave unchanged
                    btn.disabled = true;

                    const doSave = async (force = false) => {
                        const resp = await fetch(`/api/admin/templates/${encodeURIComponent(name)}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ text: textarea.value, force, system_prompt: systemVal }),
                        });
                        if (resp.ok) {
                            window.showToast?.(t('artsmoker.ui.model_settings.templates_saved'), 'success');
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
                                    t('artsmoker.ui.model_settings.ms_missing_vars_msg'), {
                                    title: t('artsmoker.ui.model_settings.ms_missing_vars_title'),
                                    detail: t('artsmoker.ui.model_settings.ms_missing_vars_detail').replace('{{vars}}', varList),
                                    confirmLabel: t('artsmoker.ui.model_settings.ms_fix_save'),
                                });
                                if (doFix) {
                                    // Call API with fix_variables=true
                                    btn.textContent = t('artsmoker.ui.model_settings.ms_fixing');
                                    const fixResp = await fetch(`/api/admin/templates/${encodeURIComponent(name)}`, {
                                        method: 'PATCH',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ text: textarea.value, fix_variables: true, system_prompt: systemVal }),
                                    });
                                    if (fixResp.ok) {
                                        const fixResult = await fixResp.json();
                                        window.showToast?.(t('artsmoker.ui.model_settings.ms_template_fixed').replace('{{count}}', fixResult.fixed_variables?.length || 0), 'success');
                                        this._templatesLoaded = false;
                                        this._loadTemplates(modal);
                                    } else {
                                        const fixErr = await fixResp.json();
                                        window.showToast?.(t('artsmoker.ui.model_settings.templates_save_failed') + ': ' + (fixErr.detail || ''), 'error');
                                    }
                                }
                            } else {
                                window.showToast?.(t('artsmoker.ui.model_settings.templates_save_failed') + ': ' + message, 'error');
                            }
                        }
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.templates_save_failed') + ': ' + err.message, 'error');
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

                    if (!modelId) { window.showToast?.(t('artsmoker.ui.model_settings.templates_no_model'), 'warning'); return; }

                    btn.disabled = true;
                    const origText = btn.textContent;
                    btn.textContent = t('artsmoker.ui.model_settings.templates_enhancing');

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
                        window.showToast?.(t('artsmoker.ui.model_settings.templates_enhance_failed') + ': ' + err.message, 'error');
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
                        window.showToast?.(t('artsmoker.ui.model_settings.templates_accepted_hint'), 'info');
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
                    if (!await window.showConfirm?.(t('artsmoker.ui.model_settings.templates_reset_confirm'), { title: t('artsmoker.ui.model_settings.templates_reset_title'), confirmLabel: t('artsmoker.ui.image_studio.reset'), danger: true })) return;
                    try {
                        await fetch(`/api/admin/templates/${encodeURIComponent(name)}/reset`, { method: 'POST' });
                        window.showToast?.(t('artsmoker.ui.model_settings.templates_reset_done'), 'success');
                        this._templatesLoaded = false;
                        this._loadTemplates(modal);
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_reset_failed') + ': ' + err.message, 'error');
                    }
                });
            });
        },

        async _refreshAfterSync() {
            // Re-fetch the registry and re-render the open Model Settings modal so
            // post-sync changes (auto-rolled LLM categories, new/Mantle models,
            // pruned models) are reflected without a manual page reload. Guarded
            // so a failure here never throws into the SSE handler.
            try {
                if (this._refreshingAfterSync) return;
                this._refreshingAfterSync = true;
                this._registry = await API.admin.getModels();
                const modal = document.getElementById('model-settings-modal');
                if (modal && typeof this._renderModal === 'function') {
                    modal.remove();
                    this._renderModal();
                }
            } catch (err) {
                console.warn('Post-sync refresh failed:', err);
            } finally {
                this._refreshingAfterSync = false;
            }
        },

        _showSyncProgress() {
            const overlay = document.createElement('div');
            overlay.className = 'fixed inset-0 z-[150] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4';
            // nosemgrep
            overlay.innerHTML = html`
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-4">
                    <div class="flex items-center justify-between">
                        <h3 class="text-sm font-semibold text-brand-text">${t('artsmoker.ui.model_settings.sync_progress_title')}</h3>
                        <button class="sync-dismiss text-brand-text-muted hover:text-brand-text text-lg leading-none" title="${t('artsmoker.ui.model_settings.sync_dismiss')}">&times;</button>
                    </div>
                    <p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.model_settings.sync_progress_hint')}</p>
                    <div class="bg-black/20 rounded-lg p-3 space-y-2">
                        <p class="sync-msg text-xs text-brand-accent font-medium">${t('artsmoker.ui.model_settings.syncing')}...</p>
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
                        if (d.ready || d.message === 'done') {
                            sse.close();
                            // Self-refresh on completion: re-fetch the registry and
                            // re-render so category labels (auto-rolled models, e.g.
                            // newest Claude) update even if the user dismissed this
                            // overlay or the trigger's await chain detached.
                            this._refreshAfterSync?.();
                            return;
                        }
                        const msgEl = overlay.querySelector('.sync-msg');
                        if (msgEl) msgEl.textContent = d.message;
                        const countsEl = overlay.querySelector('.sync-counts');
                        if (countsEl && d.models) {
                            const parts = [];
                            if (d.models.image) parts.push(`🖼 ${d.models.image} ${t('artsmoker.ui.model_settings.sync_image').toLowerCase()}`);
                            if (d.models.chat) parts.push(`💬 ${d.models.chat} ${t('artsmoker.ui.model_settings.sync_chat').toLowerCase()}`);
                            if (d.models.video) parts.push(`🎬 ${d.models.video} ${t('artsmoker.ui.model_settings.sync_video').toLowerCase()}`);
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
                // model offers selectable backends (e.g. TripoSG: TRELLIS.2/Hunyuan).
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
                            ? html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-white/5 border border-brand-border/30 text-brand-text-muted">${lic.name}</span>`
                            : '';
                        return html`<label class="flex items-start gap-2 cursor-pointer p-2.5 rounded-lg border border-brand-border hover:border-brand-accent/40 has-[:checked]:border-brand-accent/60 has-[:checked]:bg-brand-accent/5">
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
                    });
                    textureHtml = html`
                        <div>
                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1.5">${t('artsmoker.ui.custom_models.tex_backend_title')}</label>
                            <div class="space-y-2 deploy-texbackend-group">${cards}</div>
                            <div class="deploy-tex-attest mt-2 p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 hidden">
                                <p class="deploy-tex-attest-warn text-[10px] text-amber-400 mb-1.5"></p>
                                <ul class="deploy-tex-attest-terms text-[9px] text-brand-text-muted list-disc ml-4 mb-2 space-y-0.5"></ul>
                                <div class="deploy-tex-attest-deps mb-2 hidden">
                                    <p class="text-[9px] font-semibold text-brand-text-muted uppercase tracking-wider mb-1">${t('artsmoker.ui.custom_models.tex_attest_deps')}</p>
                                    <div class="deploy-tex-attest-deps-rows space-y-1"></div>
                                </div>
                                <label class="flex items-start gap-2 cursor-pointer">
                                    <input type="checkbox" class="deploy-tex-attest-check mt-0.5" />
                                    <span class="text-[10px] text-brand-text"><span class="deploy-tex-attest-labeltext">${t('artsmoker.ui.custom_models.tex_attest_label')}</span> <a class="deploy-tex-attest-link text-brand-accent underline" target="_blank" rel="noopener">${t('artsmoker.ui.custom_models.tex_attest_readlicense')}</a></span>
                                </label>
                            </div>
                        </div>`;
                }

                // Build instance dropdown with ALL options — available first, then needs-quota
                let instanceHtml = '';
                let quotaHtml = '';
                const allOptions = [...available, ...needsQuota];

                if (allOptions.length === 0) {
                    instanceHtml = html`<div class="text-xs text-red-400 py-3 space-y-2">
                        <p class="font-medium">${t('artsmoker.ui.custom_models.no_instances')}</p>
                        <p class="text-brand-text-muted">${t('artsmoker.ui.custom_models.no_instances_hint')}</p>
                    </div>`;
                } else {
                    instanceHtml = html`${allOptions.map(opt => {
                        const isRec = opt.is_recommended && !opt.needs_quota;
                        const costStr = `$${opt.cost_per_hour_usd.toFixed(2)}`;
                        const quotaTag = opt.needs_quota
                            ? (opt.quota_reason === 'all_in_use' ? ' ⚠ IN USE' : ' ⚠ NO QUOTA')
                            : '';
                        const usageNote = !opt.needs_quota && opt.quota > 1 ? ` (${opt.quota_available}/${opt.quota} avail)` : '';
                        return html`<option value="${opt.instance_type}" ${isRec ? 'selected' : ''} data-cost="${opt.cost_per_hour_usd}" data-needs-quota="${opt.needs_quota}" data-quota-code="${opt.quota_code || ''}" data-quota="${opt.quota || 0}">
                            ${opt.instance_type} — ${opt.gpus}× ${opt.gpu_type} (${opt.total_vram_gb}GB) — ${costStr}/hr ${isRec ? '★' : ''}${opt.speed_note}${usageNote}${quotaTag}
                        </option>`;
                    })}`;
                }

                // Quota section — shown dynamically when a needs-quota instance is selected
                quotaHtml = html`
                    <div class="mt-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 hidden" id="deploy-quota-section">
                        <p class="text-[10px] text-amber-400 font-medium mb-1">${t('artsmoker.ui.custom_models.quota_needed_title')}</p>
                        <p class="text-[9px] text-brand-text-muted mb-2">${t('artsmoker.ui.custom_models.quota_needed_desc').replace('{{region}}', deployRegion || 'unknown')}</p>
                        <div id="deploy-quota-row" class="flex items-center justify-between py-1.5"></div>
                    </div>`;

                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
                // nosemgrep
                backdrop.innerHTML = html`
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto">
                        <h3 class="text-sm font-semibold text-brand-text">${t('artsmoker.ui.custom_models.deploy_config_title')}</h3>

                        ${textureHtml}

                        <div class="deploy-gated-access hidden p-2.5 rounded-lg border" data-state="loading">
                            <div class="flex items-center justify-between gap-2 mb-1.5">
                                <p class="text-[10px] font-semibold uppercase tracking-wider deploy-gated-title">${t('artsmoker.ui.custom_models.gated_title')}</p>
                                <button type="button" class="deploy-gated-recheck text-[9px] px-2 py-0.5 rounded border border-brand-border/40 text-brand-text-muted hover:bg-white/5 hidden">${t('artsmoker.ui.custom_models.gated_recheck')}</button>
                            </div>
                            <div class="deploy-gated-rows space-y-1.5"></div>
                            <p class="deploy-gated-hint text-[9px] text-brand-text-muted/80 mt-1.5"></p>
                        </div>

                        <div>
                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1.5">${t('artsmoker.ui.custom_models.instance')}</label>
                            ${allOptions.length > 0 ? html`<select class="deploy-instance input w-full text-xs">${instanceHtml}</select>` : instanceHtml}
                            <p class="deploy-instance-info text-[10px] text-brand-text-muted mt-1"></p>
                            ${allOptions.length > 0 ? html`
                            <div class="mt-2 flex items-start gap-1.5 p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
                                <svg class="w-3 h-3 text-emerald-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                                <p class="text-[9px] text-brand-text-muted/90 leading-relaxed">${t('artsmoker.ui.custom_models.instance_validated_note')}</p>
                            </div>` : ''}
                            ${quotaHtml}
                        </div>

                        <div>
                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1.5">${t('artsmoker.ui.custom_models.deploy_type_title')}</label>
                            <div class="space-y-2">
                                <label class="flex items-start gap-2 cursor-pointer p-2.5 rounded-lg border border-brand-border hover:border-emerald-500/30 has-[:checked]:border-emerald-500/50 has-[:checked]:bg-emerald-500/5">
                                    <input type="radio" name="deploy-type" value="async" checked class="mt-0.5" />
                                    <div>
                                        <span class="text-xs font-medium text-brand-text">${t('artsmoker.ui.custom_models.ondemand_title')}</span>
                                        <p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.custom_models.ondemand_desc')}</p>
                                    </div>
                                </label>
                                <label class="flex items-start gap-2 cursor-pointer p-2.5 rounded-lg border border-brand-border hover:border-amber-500/30 has-[:checked]:border-amber-500/50 has-[:checked]:bg-amber-500/5">
                                    <input type="radio" name="deploy-type" value="realtime" class="mt-0.5" />
                                    <div>
                                        <span class="text-xs font-medium text-brand-text">${t('artsmoker.ui.custom_models.alwayson_title')}</span>
                                        <p class="text-[10px] text-brand-text-muted deploy-always-on-cost">${t('artsmoker.ui.custom_models.alwayson_desc')}</p>
                                    </div>
                                </label>
                            </div>
                        </div>

                        <div class="flex gap-2 justify-end pt-2">
                            <button class="deploy-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">Cancel</button>
                            <button class="deploy-confirm btn btn-sm text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium" ${allOptions.length === 0 ? 'disabled' : ''}>${t('artsmoker.ui.custom_models.deploy')}</button>
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
                        alwaysOnCost.textContent = t('artsmoker.ui.custom_models.alwayson_cost').replace('{{cost}}', cost.toFixed(2));
                    }

                    // Show/hide quota section based on selected instance
                    if (quotaSection) {
                        if (needsQ) {
                            quotaSection.classList.remove('hidden');
                            if (quotaRow) {
                                const inst = sel.value;
                                // nosemgrep
                                quotaRow.innerHTML = html`
                                    <div>
                                        <span class="text-[11px] text-brand-text">${inst}</span>
                                        <span class="text-[9px] text-brand-text-muted/60 ml-1">${qVal > 0 ? t('artsmoker.ui.custom_models.quota_all_in_use').replace('{{used}}', qVal).replace('{{quota}}', qVal) : t('artsmoker.ui.custom_models.quota_none')}</span>
                                    </div>
                                    <button class="quota-request-btn text-[10px] px-2 py-0.5 rounded bg-brand-accent/20 text-brand-accent hover:bg-brand-accent/30"
                                        data-instance="${inst}" data-code="${qCode}" data-desired="${qVal + 1}">
                                        ${t('artsmoker.ui.custom_models.quota_request_btn')}
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
                        // Commercial-OK pipelines don't need the "valid license / will
                        // use within non-commercial terms" wording — just a read-and-agree.
                        const labelEl = attestBox.querySelector('.deploy-tex-attest-labeltext');
                        if (labelEl) labelEl.textContent = lic.commercial
                            ? t('artsmoker.ui.custom_models.tex_attest_label_commercial')
                            : t('artsmoker.ui.custom_models.tex_attest_label');
                        // nosemgrep
                        if (warnEl) warnEl.innerHTML = (lic.warnings || []).map(w => html`${w}`).join('<br>');
                        // nosemgrep
                        if (termsEl) termsEl.innerHTML = (lic.key_terms || []).map(x => html`<li>${x}</li>`).join('');
                        if (linkEl && lic.url) linkEl.href = lic.url;
                        // Per-dependency licensing table (name · license · badges · link).
                        // Lets the user see EXACTLY which models/repos are pulled and
                        // each one's license + commercial/gated status before agreeing.
                        const depsBox = attestBox.querySelector('.deploy-tex-attest-deps');
                        const depsRows = attestBox.querySelector('.deploy-tex-attest-deps-rows');
                        const deps = lic.dependencies || [];
                        if (depsBox && depsRows) {
                            if (deps.length) {
                                // nosemgrep
                                depsRows.innerHTML = deps.map(d => {
                                    const comm = d.commercial
                                        ? html`<span class="text-[8px] px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('artsmoker.ui.custom_models.license_commercial_ok')}</span>`
                                        : html`<span class="text-[8px] px-1 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">${t('artsmoker.ui.custom_models.license_commercial_no')}</span>`;
                                    const gated = d.gated
                                        ? raw('<span class="text-[8px] px-1 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">gated · accept on HF</span>')
                                        : '';
                                    const nameEl = d.url
                                        ? html`<a href="${d.url}" target="_blank" rel="noopener" class="text-brand-accent underline">${d.name}</a>`
                                        : html`<span class="text-brand-text">${d.name}</span>`;
                                    return html`<div class="text-[9px] leading-relaxed">
                                        <div class="flex items-center gap-1.5 flex-wrap">
                                            ${nameEl} ${comm} ${gated}
                                        </div>
                                        <div class="text-brand-text-muted/80">${d.license || ''}${d.role ? ' — ' + d.role : ''}</div>
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
                    const blocked = (needAttest && !attested)
                        || !!deployBtn.dataset.quotaBlocked
                        || deployBtn.dataset.gatedBlocked === '1';
                    deployBtn.disabled = blocked;
                    deployBtn.classList.toggle('opacity-50', blocked);
                }
                backdrop.querySelectorAll('input[name="deploy-texbackend"]').forEach(r => r.addEventListener('change', syncTextureBackend));
                attestCheck?.addEventListener('change', updateDeployGate);
                if (tbOptions) syncTextureBackend();

                // ── Gated-repo access pre-check ────────────────────────────────
                // Probe — via the backend, using the stored HF token — whether
                // EVERY repo this deploy will pull is actually accessible. Replaces
                // the vague "gated · accept on HF" badge with a per-repo ✓ / ✗ and
                // the exact next step, and blocks deploy while a required repo is
                // inaccessible (with a clear reason, not a silent failure 10 min in).
                const gatedBox = backdrop.querySelector('.deploy-gated-access');
                const gatedRows = backdrop.querySelector('.deploy-gated-rows');
                const gatedHint = backdrop.querySelector('.deploy-gated-hint');
                const gatedRecheck = backdrop.querySelector('.deploy-gated-recheck');
                const esc = (s) => this._esc(s);
                const runGatedCheck = async () => {
                    if (!gatedBox) return;
                    gatedBox.classList.remove('hidden');
                    gatedBox.className = 'deploy-gated-access p-2.5 rounded-lg border border-brand-border/40 bg-white/5';
                    // nosemgrep
                    gatedRows.innerHTML = html`<p class="text-[10px] text-brand-text-muted">${t('artsmoker.ui.custom_models.gated_checking')}</p>`;
                    gatedHint.textContent = '';
                    if (gatedRecheck) gatedRecheck.classList.add('hidden');
                    let data;
                    try {
                        const resp = await fetch(`/api/custom-models/gated-access/${encodeURIComponent(modelKey)}`);
                        data = await resp.json();
                        if (!resp.ok) throw new Error(data.detail || 'check failed');
                    } catch (e) {
                        // Don't hard-block on a probe failure — show a soft warning.
                        // nosemgrep
                        gatedRows.innerHTML = html`<p class="text-[10px] text-amber-400">${t('artsmoker.ui.custom_models.gated_check_failed')}</p>`;
                        if (gatedRecheck) gatedRecheck.classList.remove('hidden');
                        if (deployBtn) { deployBtn.dataset.gatedBlocked = '0'; updateDeployGate(); }
                        return;
                    }
                    // No HF repos at all → hide the panel entirely.
                    if (!data.repos || !data.repos.length) {
                        gatedBox.classList.add('hidden');
                        if (deployBtn) { deployBtn.dataset.gatedBlocked = '0'; updateDeployGate(); }
                        return;
                    }
                    // nosemgrep
                    gatedRows.innerHTML = data.repos.map(r => {
                        const ok = r.accessible;
                        const icon = ok
                            ? raw('<span class="text-emerald-400">✓</span>')
                            : raw('<span class="text-amber-400">✗</span>');
                        const link = html`<a href="${r.license_url}" target="_blank" rel="noopener" class="text-brand-accent underline">${r.name}</a>`;
                        const action = ok ? '' :
                            html`<div class="text-[9px] text-amber-300/90 mt-0.5">${r.action}
                                <a href="${r.license_url}" target="_blank" rel="noopener" class="text-brand-accent underline ml-1">${t('artsmoker.ui.custom_models.gated_open_hf')} ↗</a></div>`;
                        return html`<div class="text-[10px] leading-relaxed">
                            <div class="flex items-center gap-1.5">${icon} ${link}
                                ${r.gated ? html`<span class="text-[8px] px-1 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${t('artsmoker.ui.custom_models.gated_badge')}</span>` : ''}
                            </div>${action}
                        </div>`;
                    }).join('');
                    if (gatedRecheck) gatedRecheck.classList.remove('hidden');

                    if (data.all_clear) {
                        gatedBox.className = 'deploy-gated-access p-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5';
                        gatedHint.textContent = t('artsmoker.ui.custom_models.gated_all_clear');
                        if (deployBtn) { deployBtn.dataset.gatedBlocked = '0'; }
                    } else {
                        gatedBox.className = 'deploy-gated-access p-2.5 rounded-lg border border-amber-500/30 bg-amber-500/5';
                        // nosemgrep
                        gatedHint.innerHTML = raw(data.needs_token
                            ? t('artsmoker.ui.custom_models.gated_needs_token')
                            : t('artsmoker.ui.custom_models.gated_blocked_hint'));
                        // Block deploy ONLY when a gated/required repo is inaccessible.
                        if (deployBtn) { deployBtn.dataset.gatedBlocked = '1'; }
                    }
                    updateDeployGate();
                };
                if (gatedRecheck) gatedRecheck.addEventListener('click', runGatedCheck);
                runGatedCheck();

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
                    btn.textContent = t('artsmoker.ui.custom_models.quota_requesting');
                    try {
                        const resp = await fetch('/api/custom-models/quota-request', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ instance_type: inst, quota_code: code, desired_value: desired }),
                        });
                        const data = await resp.json();
                        if (resp.ok) {
                            const msg = data.status === 'already_pending'
                                ? t('artsmoker.ui.custom_models.quota_already_pending')
                                : data.status === 'already_sufficient'
                                ? t('artsmoker.ui.custom_models.quota_already_sufficient')
                                : t('artsmoker.ui.custom_models.quota_submitted');
                            // nosemgrep
                            btn.outerHTML = html`<span class="text-[10px] text-emerald-400">${msg}</span>`;
                            window.showToast?.(data.message, 'success');
                        } else {
                            btn.textContent = t('artsmoker.ui.custom_models.quota_request_btn');
                            btn.disabled = false;
                            window.showToast?.(data.detail || t('artsmoker.ui.custom_models.quota_failed'), 'error');
                        }
                    } catch (err) {
                        btn.textContent = t('artsmoker.ui.custom_models.quota_request_btn');
                        btn.disabled = false;
                        window.showToast?.(t('artsmoker.ui.custom_models.quota_failed'), 'error');
                    }
                });

                document.body.appendChild(backdrop);
            });
        },

        _showLicenseAgreement(modelLabel, licenseAgreement) {
            return new Promise((resolve) => {
                const la = licenseAgreement;
                const termsHtml = (la.key_terms || []).map(term =>
                    html`<li class="flex items-start gap-2">
                        <span class="text-emerald-400 mt-0.5 flex-shrink-0">&#10003;</span>
                        <span>${term}</span>
                    </li>`
                );
                // Per-dependency licensing table — each model/repo this pipeline
                // pulls, its license, commercial/gated status + role. Lets the user
                // see EXACTLY what's involved before accepting (well-split, clear).
                const deps = la.dependencies || [];
                const depsHtml = deps.length
                    ? html`<div class="p-3 rounded-lg bg-brand-bg/60 border border-brand-border/50">
                        <p class="text-[10px] font-semibold text-brand-text-muted uppercase tracking-wider mb-2">${t('artsmoker.ui.custom_models.tex_attest_deps')}</p>
                        <div class="space-y-2">
                            ${deps.map(d => {
                                const comm = d.commercial
                                    ? html`<span class="text-[8px] px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${t('artsmoker.ui.custom_models.license_commercial_ok')}</span>`
                                    : html`<span class="text-[8px] px-1 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">${t('artsmoker.ui.custom_models.license_commercial_no')}</span>`;
                                const gated = d.gated
                                    ? raw('<span class="text-[8px] px-1 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">gated &middot; accept on HF</span>')
                                    : '';
                                const nameEl = d.url
                                    ? html`<a href="${d.url}" target="_blank" rel="noopener" class="text-brand-accent underline">${d.name}</a>`
                                    : html`<span class="text-brand-text">${d.name}</span>`;
                                return html`<div class="text-[10px] leading-relaxed">
                                    <div class="flex items-center gap-1.5 flex-wrap">${nameEl} ${comm} ${gated}</div>
                                    <div class="text-brand-text-muted/80">${d.license || ''}${d.role ? ' — ' + d.role : ''}</div>
                                </div>`;
                            })}
                        </div>
                    </div>`
                    : '';
                const warningsHtml = (la.warnings || []).length > 0
                    ? html`<div class="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 space-y-1.5">
                        <p class="text-[10px] font-semibold text-red-400 uppercase tracking-wider">Restrictions &amp; Warnings</p>
                        <ul class="space-y-1.5 text-xs text-red-300">
                            ${la.warnings.map(w => html`<li class="flex items-start gap-2"><span class="text-red-400 mt-0.5 flex-shrink-0">&#9888;</span><span>${w}</span></li>`)}
                        </ul>
                    </div>`
                    : '';

                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
                // nosemgrep
                backdrop.innerHTML = html`
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-4">
                        <h3 class="text-sm font-semibold text-brand-text">${t('artsmoker.ui.custom_models.license_title')}</h3>
                        <div class="text-xs text-brand-text-muted space-y-3">
                            <div class="flex items-center gap-2">
                                <span class="font-medium text-brand-text">${modelLabel}</span>
                                <span class="text-[9px] px-1.5 py-0.5 rounded bg-white/5 border border-brand-border/30">${la.license_name}</span>
                            </div>
                            <div class="p-3 rounded-lg bg-brand-bg/60 border border-brand-border/50">
                                <p class="text-[10px] font-semibold text-brand-text-muted uppercase tracking-wider mb-2">${t('artsmoker.ui.custom_models.license_key_terms')}</p>
                                <ul class="space-y-1.5 text-xs">${termsHtml}</ul>
                            </div>
                            ${depsHtml}
                            ${warningsHtml}
                            <a href="${la.license_url}" target="_blank" rel="noopener" class="inline-flex items-center gap-1 text-brand-accent hover:underline text-xs">
                                ${t('artsmoker.ui.custom_models.license_read_full')} &#8599;
                            </a>
                        </div>
                        <label class="license-agree-label flex items-start gap-2.5 cursor-pointer p-3 rounded-lg border border-brand-border hover:border-brand-accent/30 transition-colors">
                            <input type="checkbox" class="license-agree-checkbox mt-0.5 accent-brand-accent" />
                            <span class="text-xs text-brand-text">${t('artsmoker.ui.custom_models.license_agree_checkbox')}</span>
                        </label>
                        <div class="flex gap-2 justify-end pt-1">
                            <button class="license-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${t('artsmoker.ui.prompt_designer.cancel')}</button>
                            <button class="license-continue btn btn-sm text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium opacity-40 cursor-not-allowed" disabled>${t('artsmoker.ui.custom_models.license_continue')}</button>
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
                    ? html`<a href="${licenseUrl}" target="_blank" rel="noopener" class="text-brand-accent hover:underline">Open model page ↗</a>`
                    : '';
                const backdrop = document.createElement('div');
                backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
                // nosemgrep
                backdrop.innerHTML = html`
                    <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-md w-full p-6 space-y-4">
                        <h3 class="text-sm font-semibold text-brand-text">${t('artsmoker.ui.custom_models.hf_title')}</h3>
                        <div class="text-xs text-brand-text-muted space-y-2">
                            <p>${t('artsmoker.ui.custom_models.hf_desc')}</p>
                            <ol class="list-decimal ml-4 space-y-1.5">
                                <li>${t('artsmoker.ui.custom_models.hf_step1')} ${licenseLink}</li>
                                <li>${t('artsmoker.ui.custom_models.hf_step2')}</li>
                                <li>${t('artsmoker.ui.custom_models.hf_step3')}</li>
                            </ol>
                            <p class="text-[10px] text-amber-400/80 mt-2">${t('artsmoker.ui.custom_models.hf_warning')}</p>
                        </div>
                        <input type="password" class="hf-token-input input w-full text-xs font-mono" placeholder="${t('artsmoker.ui.custom_models.hf_placeholder')}" autocomplete="off" />
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

        async _loadCustomModels(modal, force = false) {
            const container = modal.querySelector('#ms-custom-models-content');
            if (!container) return;

            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 20000);
                const resp = await fetch(`/api/custom-models/catalog${force ? '?force=true' : ''}`, { signal: controller.signal });
                clearTimeout(timeout);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                const models = data.models || [];
                this._customModelsLoaded = true;
                this._catalogModels = models;
                // Deploy requires an S3 bucket (handler upload). Gate all Deploy
                // buttons on this — no bucket = deploy physically can't work.
                this._deploymentBucket = data.deployment_bucket || '';

                if (models.length === 0) {
                    // nosemgrep
                    container.innerHTML = html`<p class="text-xs text-brand-text-muted">${t('artsmoker.ui.custom_models.no_models')}</p>`;
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
                    image_generation: t('artsmoker.ui.custom_models.cat_image_generation'),
                    '3d_generation': t('artsmoker.ui.custom_models.cat_3d_generation'),
                    post_processing: t('artsmoker.ui.custom_models.cat_post_processing'),
                    utility: t('artsmoker.ui.custom_models.cat_utility'),
                    video_generation: t('artsmoker.ui.custom_models.cat_video_generation'),
                    other: t('artsmoker.ui.custom_models.other'),
                };
                const categoryOrder = ['image_generation', '3d_generation', 'post_processing', 'utility', 'video_generation', 'other'];
                const _studioColors = ['text-brand-accent', 'text-cyan-400', 'text-amber-400'];
                const _catColors = ['text-brand-accent', 'text-emerald-400', 'text-purple-400', 'text-cyan-400', 'text-amber-400'];

                // Preserve which sections are expanded before re-rendering
                const openSections = new Set();
                container.querySelectorAll('details[data-cm-studio][open]').forEach(d => openSections.add(d.dataset.cmStudio));
                container.querySelectorAll('details[data-cm-cat][open]').forEach(d => openSections.add(d.dataset.cmCat));

                let out = '<div class="space-y-4">';
                out += html`<p class="text-xs text-brand-text-muted">${t('artsmoker.ui.custom_models.description_line')}</p>`;

                // S3-bucket config — IN-PLACE setter at the top of Custom Models.
                // A deployment bucket is REQUIRED to deploy any custom model (the
                // handler is uploaded there) and is where async-jobs + 3D jobs +
                // notices persist. Configure it here directly (no detour to Video
                // Studio); writes the SAME shared video_settings.s3_bucket.
                const _bkt = data.deployment_bucket || '';
                const _bktLocked = !!data.bucket_locked;
                const _bktLockReasons = (data.bucket_lock_reasons || []).join(', ');
                if (_bkt) {
                    // Set. If LOCKED (a custom endpoint is deployed / job in-flight /
                    // ArtSmoker data present), show a READ-ONLY record — SageMaker
                    // permanently binds deployed endpoints to this bucket, so it must
                    // not change. Otherwise (set but unused) allow Change.
                    out += html`<div id="ms-s3-card" class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border flex items-center gap-2.5">
                        <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                        <div class="flex-1 min-w-0">
                            <p class="text-[10px] uppercase tracking-wider text-brand-text-muted">${t('artsmoker.ui.custom_models.s3_bucket_label')}${_bktLocked ? ` · ${t('artsmoker.ui.custom_models.s3_locked')}` : ''}</p>
                            <p class="text-sm font-mono truncate">${_bkt}</p>
                            ${_bktLocked ? html`<p class="text-[10px] text-brand-text-muted/70 mt-0.5">${t('artsmoker.ui.custom_models.s3_locked_hint').replace('{{reasons}}', _bktLockReasons)}</p>` : ''}
                        </div>
                        ${_bktLocked ? '' : html`<button id="ms-s3-edit" class="btn btn-secondary btn-sm text-xs whitespace-nowrap">${t('artsmoker.ui.custom_models.s3_change')}</button>`}
                    </div>`;
                } else {
                    out += html`<div class="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40">
                        <div class="flex items-start gap-2.5 mb-2">
                            <svg class="w-4 h-4 text-amber-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.962-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                            <div class="flex-1 min-w-0">
                                <p class="text-xs font-semibold text-amber-300">${t('artsmoker.ui.custom_models.bucket_required_title')}</p>
                                <p class="text-[11px] text-brand-text-muted mt-0.5 leading-relaxed">${t('artsmoker.ui.custom_models.bucket_required_desc')}</p>
                            </div>
                        </div>
                        <div id="ms-s3-editor" class="flex gap-2">
                            <input type="text" id="ms-s3-input" class="input flex-1 text-xs font-mono" placeholder="${t('artsmoker.ui.custom_models.s3_bucket_placeholder')}" />
                            <button id="ms-s3-save" class="btn btn-primary btn-sm text-xs whitespace-nowrap">${t('artsmoker.ui.custom_models.s3_save')}</button>
                        </div>
                        <p id="ms-s3-msg" class="text-[10px] mt-1.5 hidden"></p>
                    </div>`;
                }

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

                    out += html`<details class="mb-3 ms-collapsible" data-cm-studio="${studio}" ${studioOpen ? 'open' : ''}>
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
                        // Sort alphabetically by label (case-insensitive) within each
                        // category — mirrors the Image Studio dropdown ordering. Key is
                        // the stable tiebreak when two models share a label.
                        const catModels = categories[cat].sort((a, b) =>
                            (a.label || '').localeCompare(b.label || '', undefined, { sensitivity: 'base' })
                            || (a.key || '').localeCompare(b.key || '')
                        );
                        const catOpen = openSections.has(cat);
                        const catColor = _catColors[cIdx % _catColors.length];

                        out += html`<details class="mb-2 ms-collapsible" data-cm-cat="${cat}" ${catOpen ? 'open' : ''}>
                            <summary class="text-xs font-semibold ${catColor} uppercase tracking-wider cursor-pointer hover:opacity-80 select-none">
                                ${categoryLabels[cat] || cat}
                                <span class="text-[10px] font-normal text-brand-text-muted">(${catModels.length})</span>
                            </summary>
                            <div class="space-y-2 mt-2">`;

                    // Within image_generation, split generators vs image-EDIT models
                    // into a labeled "Image Editing" sub-group (mirrors the Image
                    // Studio section, which sub-groups image models by purpose).
                    // model_purpose "image_edit" → editor; anything else → generator.
                    let _renderModels = catModels;
                    let _subGrouped = null;
                    if (cat === 'image_generation') {
                        const gens = catModels.filter(m => (m.model_purpose || 'text_to_image') !== 'image_edit');
                        const edits = catModels.filter(m => (m.model_purpose || '') === 'image_edit');
                        if (edits.length) {
                            _subGrouped = [
                                { label: t('artsmoker.ui.custom_models.subgroup_generation'), models: gens },
                                { label: t('artsmoker.ui.custom_models.subgroup_editing'), models: edits },
                            ].filter(g => g.models.length);
                            _renderModels = [];  // render via sub-groups below
                        }
                    }

                    // Deploy is impossible without an S3 bucket (the handler is
                    // uploaded there). Render Deploy buttons DISABLED + explained
                    // when no bucket is configured — a basic guardrail so the user
                    // can't start a deploy that would only fail.
                    const _noBucket = !this._deploymentBucket;
                    const _deployBtn = (m, label, extraTitle = '') => {
                        if (_noBucket) {
                            return html`<button class="btn btn-sm text-[10px] px-3 py-1 rounded bg-brand-border/30 text-brand-text-muted/50 cursor-not-allowed" disabled title="${t('artsmoker.ui.custom_models.bucket_required_title')}">${label}</button>`;
                        }
                        return html`<button class="ms-cm-deploy btn btn-sm text-[10px] px-3 py-1 rounded bg-brand-accent hover:bg-brand-accent-hover text-white" data-model="${m.key}" data-auth="${m.requires_hf_auth ? '1' : '0'}" data-license="${m.hf_license_url || ''}" title="${extraTitle}">${label}</button>`;
                    };

                    const _renderCard = (m) => {
                        const isInService = m.deployment_status === 'InService';
                        const active = isInService && !m.warming_up && m.instance_count > 0;
                        const idle = isInService && !m.warming_up && !active;
                        const warmingUp = isInService && m.warming_up;
                        const scalingUp = m.deployment_status === 'Updating' && (m.instance_count === 0 || m.instance_count === undefined);
                        const deploying = !scalingUp && !isInService && (m.deployment_status === 'Creating' || m.deployment_status === 'Updating' || m.deploy_stage === 'preparing' || m.deploy_stage === 'downloading' || m.deploy_stage === 'uploading' || m.deploy_stage === 'deploying' || (m.deploy_progress && m.deploy_stage !== 'failed'));
                        const failed = m.deployment_status === 'Failed' || m.deploy_stage === 'failed';
                        const deployed = active || idle;
                        const cacheHint = m.has_cache ? t('artsmoker.ui.custom_models.cached_faster') : t('artsmoker.ui.custom_models.cold_start_activation');
                        const statusColor = active ? 'text-emerald-400' : idle ? 'text-blue-400' : warmingUp ? 'text-cyan-400' : (deploying || scalingUp) ? 'text-amber-400' : failed ? 'text-red-400' : 'text-brand-text-muted/50';
                        // On failure, surface the REAL reason (e.g. InsufficientInstanceCapacity)
                        // and note that we auto-clean it so the user can redeploy.
                        const failReason = (m.failure_reason || '').trim();
                        const failText = failReason
                            ? `${t('artsmoker.ui.custom_models.failed')}: ${failReason.split('.')[0]} — ${t('artsmoker.ui.custom_models.failed_autocleanup')}`
                            : `${t('artsmoker.ui.custom_models.failed')} — ${t('artsmoker.ui.custom_models.failed_autocleanup')}`;
                        const statusText = active ? t('artsmoker.ui.custom_models.active') : idle ? `Inactive — activates on next request (${cacheHint})` : warmingUp ? (m.warmup_detail || t('artsmoker.ui.custom_models.warming_up')) : scalingUp ? 'Starting instance...' : deploying ? (m.deploy_progress || t('artsmoker.ui.custom_models.deploying')) : failed ? failText : t('artsmoker.ui.custom_models.not_deployed');
                        const authBadge = m.requires_hf_auth ? html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${t('artsmoker.ui.custom_models.hf_auth')}</span>` : '';
                        const licenseBadge = html`<span class="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-brand-text-muted border border-brand-border/30">${m.license?.split(' ')[0] || '?'}</span>`;
                        const userBadge = m.user_added ? raw('<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">User</span>') : '';
                        const statusDot = active ? 'bg-emerald-400' : idle ? 'bg-blue-400' : warmingUp ? 'bg-cyan-400 animate-pulse' : (deploying || scalingUp) ? 'bg-amber-400 animate-pulse' : failed ? 'bg-red-400' : 'bg-brand-text-muted/30';

                        return html`
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
                                            <span>${this._catalogCostLabel(m)}</span>
                                            <span>${m.requirements?.min_vram_gb || '?'}GB VRAM</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-2 flex-shrink-0">
                                        ${failed
                                            ? html`<span class="text-[10px] text-red-400 max-w-[260px] text-right" title="${failReason}">${failText}</span>
                                               ${_deployBtn(m, t('artsmoker.ui.custom_models.deploy'))}`
                                            : !deployed && !deploying && !warmingUp && !scalingUp
                                            ? html`<span class="text-[10px] text-brand-text-muted/50">${t('artsmoker.ui.custom_models.not_deployed')}</span>
                                               ${_deployBtn(m, t('artsmoker.ui.custom_models.deploy'))}`
                                            : (deploying || warmingUp || scalingUp)
                                            ? html`<span class="text-[10px] text-amber-400">${m.deploy_progress || t('artsmoker.ui.custom_models.deploying')}</span>`
                                            : _deployBtn(m, t('artsmoker.ui.custom_models.deploy_another'), t('artsmoker.ui.custom_models.deploy_another_hint'))
                                        }
                                    </div>
                                </div>
                                ${(m.deployed_instances || []).length > 0 ? html`
                                <div class="px-3 pb-3 pt-0 space-y-1.5 border-t border-brand-border/20 mt-0 ml-4">
                                    <div class="text-[9px] text-brand-text-muted/40 pt-2">${(m.deployed_instances || []).length} deployed instance${(m.deployed_instances || []).length > 1 ? 's' : ''}:</div>
                                    ${(m.deployed_instances || []).map(inst => {
                                        const iActive = inst.status === 'InService' && !inst.warming_up && inst.instance_count > 0;
                                        const iIdle = inst.status === 'InService' && !inst.warming_up && !iActive;
                                        const iWarm = inst.status === 'InService' && inst.warming_up;
                                        const iDot = iActive ? 'bg-emerald-400' : iIdle ? 'bg-blue-400' : iWarm ? 'bg-cyan-400 animate-pulse' : 'bg-brand-text-muted/30';
                                        const iColor = iActive ? 'text-emerald-400' : iIdle ? 'text-blue-400' : iWarm ? 'text-cyan-400' : 'text-brand-text-muted/50';
                                        const iStatusTxt = iActive ? t('artsmoker.ui.custom_models.active') : iIdle ? t('artsmoker.ui.custom_models.instance_inactive') : iWarm ? t('artsmoker.ui.custom_models.warming_up') : inst.status;
                                        return html`
                                        <div class="flex items-center gap-2 p-2 rounded bg-black/10 border border-brand-border/20">
                                            <div class="w-1.5 h-1.5 rounded-full ${iDot} flex-shrink-0"></div>
                                            <span class="text-[11px] text-cyan-300/80 truncate flex-1 min-w-0" title="${inst.label}">${inst.label}</span>
                                            <span class="text-[10px] ${iColor} flex-shrink-0 w-[200px] text-right">${iStatusTxt}</span>
                                            <button class="ms-cm-teardown btn text-[10px] px-2 py-0.5 rounded border border-red-500/20 text-red-400/70 hover:bg-red-500/10 flex-shrink-0 w-[60px] text-center" data-model="${inst.deployed_key}">${t('artsmoker.ui.custom_models.remove')}</button>
                                            ${iIdle ? (_noBucket
                                                ? html`<button class="btn text-[10px] px-2.5 py-0.5 rounded border border-brand-border/30 text-brand-text-muted/40 cursor-not-allowed flex-shrink-0 w-[110px] text-center" disabled title="${t('artsmoker.ui.custom_models.bucket_required_title')}">${t('artsmoker.ui.custom_models.redeploy')}</button>`
                                                : html`<button class="ms-cm-redeploy btn text-[10px] px-2.5 py-0.5 rounded border border-brand-accent/30 text-brand-accent/80 hover:bg-brand-accent/10 hover:text-brand-accent flex-shrink-0 w-[110px] text-center" data-model="${inst.deployed_key}" data-auth="${m.requires_hf_auth ? '1' : '0'}">${t('artsmoker.ui.custom_models.redeploy')}</button>`) : raw('<span class="w-[110px] flex-shrink-0"></span>')}
                                        </div>`;
                                    })}
                                </div>` : ''}
                            </div>`;
                    };  // end _renderCard

                    if (_subGrouped) {
                        // Editors get a labeled "Image Editing" sub-header; generators
                        // render under a "Generation" sub-header — same visual language
                        // as the Image Studio purpose sub-groups.
                        _subGrouped.forEach(g => {
                            out += html`<div class="text-[10px] font-semibold text-cyan-300/70 uppercase tracking-wider mt-1 mb-1.5 pl-0.5">${g.label} <span class="text-brand-text-muted/50 font-normal">(${g.models.length})</span></div>`;
                            out += g.models.map(_renderCard).join('');
                        });
                    } else {
                        out += _renderModels.map(_renderCard).join('');
                    }
                    out += '</div></details>';  // close category
                    });
                    out += '</div></details>';  // close studio
                });
                out += '</div>';
                // nosemgrep
                container.innerHTML = out;

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

                // S3-bucket setter handlers (in-place at top of Custom Models).
                const _s3msg = (text, ok) => {
                    const el = container.querySelector('#ms-s3-msg');
                    if (!el) return;
                    el.textContent = text;
                    el.className = `text-[10px] mt-1.5 ${ok ? 'text-emerald-400' : 'text-red-400'}`;
                    el.classList.remove('hidden');
                };
                const _saveS3 = async () => {
                    const input = container.querySelector('#ms-s3-input');
                    const saveBtn = container.querySelector('#ms-s3-save');
                    const name = (input?.value || '').trim();
                    if (!name) { _s3msg(t('artsmoker.ui.custom_models.s3_required'), false); return; }
                    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = t('artsmoker.ui.custom_models.s3_saving'); }
                    try {
                        const resp = await fetch('/api/custom-models/s3-bucket', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ s3_bucket: name }),
                        });
                        if (!resp.ok) {
                            const err = await resp.json().catch(() => ({}));
                            throw new Error(err.detail || `HTTP ${resp.status}`);
                        }
                        _s3msg(t('artsmoker.ui.custom_models.s3_saved'), true);
                        window.showToast?.(t('artsmoker.ui.custom_models.s3_saved'), 'success');
                        // Reload the tab so deploy buttons re-enable + card shows the bucket.
                        this._customModelsLoaded = false;
                        this._loadCustomModels(modal, true);
                    } catch (e) {
                        _s3msg(e.message || 'Save failed', false);
                    } finally {
                        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = t('artsmoker.ui.custom_models.s3_save'); }
                    }
                };
                container.querySelector('#ms-s3-save')?.addEventListener('click', _saveS3);
                container.querySelector('#ms-s3-input')?.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') { e.preventDefault(); _saveS3(); }
                });
                // "Change" (bucket already set) → swap the card for the editor.
                container.querySelector('#ms-s3-edit')?.addEventListener('click', () => {
                    const card = container.querySelector('#ms-s3-card');
                    if (!card) return;
                    // nosemgrep
                    card.outerHTML = html`<div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border">
                        <p class="text-[10px] uppercase tracking-wider text-brand-text-muted mb-1.5">${t('artsmoker.ui.custom_models.s3_bucket_label')}</p>
                        <div class="flex gap-2">
                            <input type="text" id="ms-s3-input" class="input flex-1 text-xs font-mono" value="${_bkt}" placeholder="${t('artsmoker.ui.custom_models.s3_bucket_placeholder')}" />
                            <button id="ms-s3-save" class="btn btn-primary btn-sm text-xs whitespace-nowrap">${t('artsmoker.ui.custom_models.s3_save')}</button>
                        </div>
                        <p id="ms-s3-msg" class="text-[10px] mt-1.5 hidden"></p>
                    </div>`;
                    container.querySelector('#ms-s3-save')?.addEventListener('click', _saveS3);
                    container.querySelector('#ms-s3-input')?.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter') { e.preventDefault(); _saveS3(); }
                    });
                    container.querySelector('#ms-s3-input')?.focus();
                });

                // Attach deploy/teardown handlers
                container.querySelectorAll('.ms-cm-deploy').forEach(btn => {
                    btn.addEventListener('click', () => {
                        // Disable immediately to prevent double-click
                        btn.disabled = true;
                        btn.textContent = t('artsmoker.ui.custom_models.starting');
                        btn.className = 'btn btn-sm text-[10px] px-3 py-1 rounded bg-amber-500/20 border border-amber-500/30 text-amber-400 cursor-wait';
                        // Update the status text next to it
                        const statusEl = btn.closest('.flex')?.querySelector('.text-brand-text-muted\\/50, .text-\\[10px\\]');
                        if (statusEl && statusEl.textContent.trim() === t('artsmoker.ui.custom_models.not_deployed')) {
                            statusEl.textContent = t('artsmoker.ui.custom_models.preparing_deploy');
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
                // nosemgrep
                container.innerHTML = html`<p class="text-xs text-red-400">Failed to load custom models: ${msg}</p>`;
            }
        },

        async _deployCustomModel(modelKey, needsAuth, modal, isRedeploy = false, licenseUrl = '') {
            // Helper to reset all deploy buttons for this model if user cancels at any step
            const _resetDeployBtn = () => {
                modal?.querySelectorAll(`.ms-cm-deploy[data-model="${modelKey}"]`).forEach(btn => {
                    const isDeployAnother = btn.title === t('artsmoker.ui.custom_models.deploy_another_hint');
                    btn.textContent = isDeployAnother ? t('artsmoker.ui.custom_models.deploy_another') : t('artsmoker.ui.custom_models.deploy');
                    btn.disabled = false;
                    btn.className = 'ms-cm-deploy btn btn-sm text-[10px] px-3 py-1 rounded bg-brand-accent/20 border border-brand-accent/30 text-brand-accent hover:bg-brand-accent/30';
                    // Reset any "Preparing deployment..." status text nearby
                    const row = btn.closest('.flex');
                    if (row) {
                        row.querySelectorAll('.text-amber-400').forEach(el => {
                            if (el !== btn && el.textContent.includes('Preparing') || el.textContent.includes('Starting')) {
                                el.textContent = t('artsmoker.ui.custom_models.not_deployed');
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
            // user picks TRELLIS.2 vs Hunyuan at deploy). Registry-driven — the
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
                    window.showToast?.(result.message || t('artsmoker.ui.custom_models.deploy_started'), 'success');
                    // Immediately update UI to show deploying state (before catalog refresh)
                    modal?.querySelectorAll(`.ms-cm-deploy[data-model="${modelKey}"]`).forEach(btn => {
                        btn.textContent = t('artsmoker.ui.custom_models.deploying');
                        btn.disabled = true;
                        btn.className = 'btn btn-sm text-[10px] px-3 py-1 rounded bg-amber-500/20 border border-amber-500/30 text-amber-400 cursor-wait';
                        const row = btn.closest('.flex');
                        if (row) {
                            row.querySelectorAll('.text-brand-text-muted\\/50').forEach(el => {
                                if (el.textContent.includes(t('artsmoker.ui.custom_models.not_deployed')) || el.textContent.includes('Preparing')) {
                                    el.textContent = t('artsmoker.ui.custom_models.deploying');
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
                window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + err.message, 'error');
            }
        },

        async _addCustomModelWizard(modal) {
            // Step 1: Ask for HuggingFace repo URL
            const backdrop = document.createElement('div');
            backdrop.className = 'fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
            // nosemgrep
            backdrop.innerHTML = html`
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-6 space-y-4">
                    <h3 class="text-sm font-semibold text-brand-text flex items-center gap-2">
                        <span>+</span> ${t('artsmoker.ui.custom_models.add_model_title') || 'Add Custom Model'}
                    </h3>
                    <p class="text-xs text-brand-text-muted">${t('artsmoker.ui.custom_models.add_model_desc') || 'Enter a HuggingFace model URL or repo ID. The system will auto-detect the model type, library, and requirements.'}</p>
                    <input type="text" class="cm-repo-input input w-full text-xs" placeholder="e.g. runwayml/stable-diffusion-v1-5 or https://huggingface.co/..." autocomplete="off" />
                    <div class="cm-token-row hidden space-y-2">
                        <p class="text-[10px] text-amber-400">${t('artsmoker.ui.custom_models.add_model_gated') || 'This repo may be gated. Provide a token if needed (used once, not stored):'}</p>
                        <input type="password" class="cm-token-input input w-full text-xs font-mono" placeholder="${t('artsmoker.ui.custom_models.hf_placeholder')}" autocomplete="off" />
                    </div>
                    <div class="cm-result hidden"></div>
                    <div class="flex gap-2 justify-end">
                        <button class="cm-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${t('artsmoker.ui.prompt_designer.cancel')}</button>
                        <button class="cm-detect btn btn-sm text-xs px-4 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">${t('artsmoker.ui.custom_models.detect') || 'Detect Model'}</button>
                        <button class="cm-add hidden btn btn-sm text-xs px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium">${t('artsmoker.ui.custom_models.add_to_catalog') || 'Add to Catalog'}</button>
                    </div>
                </div>`;

            let detectedEntry = null;

            backdrop.querySelector('.cm-cancel').addEventListener('click', () => backdrop.remove());
            backdrop.addEventListener('click', (e) => { if (e.target === backdrop) backdrop.remove(); });

            backdrop.querySelector('.cm-detect').addEventListener('click', async () => {
                const repoUrl = backdrop.querySelector('.cm-repo-input').value.trim();
                if (!repoUrl) return;

                const detectBtn = backdrop.querySelector('.cm-detect');
                detectBtn.textContent = t('artsmoker.ui.custom_models.detecting');
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
                        // nosemgrep
                        backdrop.querySelector('.cm-result').innerHTML = html`<p class="text-xs text-red-400">${detail}</p>`;
                        backdrop.querySelector('.cm-result').classList.remove('hidden');
                        return;
                    }

                    const data = await resp.json();
                    detectedEntry = data.entry;

                    // Show detected info
                    const e = detectedEntry;
                    const warning = e.invoke?._warning ? html`<p class="text-[10px] text-amber-400 mt-2">⚠ ${e.invoke._warning}</p>` : '';
                    // nosemgrep
                    backdrop.querySelector('.cm-result').innerHTML = html`
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
                    // nosemgrep
                    backdrop.querySelector('.cm-result').innerHTML = html`<p class="text-xs text-red-400">${err.message}</p>`;
                    backdrop.querySelector('.cm-result').classList.remove('hidden');
                } finally {
                    detectBtn.textContent = t('artsmoker.ui.custom_models.detect') || 'Detect Model';
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
                        window.showToast?.(t('artsmoker.ui.custom_models.model_added').replace('{{name}}', detectedEntry.label), 'success');
                        backdrop.remove();
                        this._customModelsLoaded = false;
                        this._loadCustomModels(modal);
                    } else {
                        const err = await resp.json();
                        window.showToast?.(err.detail || 'Failed to add model', 'error');
                    }
                } catch (err) {
                    window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + err.message, 'error');
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
                            window.showToast?.(status.progress || t('artsmoker.ui.custom_models.deploy_complete'), 'success');
                            this._customModelsLoaded = false;
                            this._loadCustomModels(modal);
                            this._activePolls.delete(modelKey);
                            return;
                        }
                        if (status.stage === 'failed') {
                            window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + status.error, 'error');
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
            if (!await window.showConfirm(t('artsmoker.ui.custom_models.remove_confirm'), { title: t('artsmoker.ui.custom_models.remove_title'), confirmLabel: t('artsmoker.ui.custom_models.remove'), danger: true })) return;

            try {
                const resp = await fetch(`/api/custom-models/teardown/${modelKey}`, { method: 'DELETE' });
                if (resp.ok) {
                    window.showToast?.(t('artsmoker.ui.custom_models.remove_done'), 'success');
                    this._customModelsLoaded = false;
                    this._loadCustomModels(modal);
                }
            } catch (err) {
                window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + err.message, 'error');
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
            // nosemgrep
            backdrop.innerHTML = html`
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-md w-full p-6 space-y-4">
                    <h3 class="text-sm font-semibold text-brand-text">🔑 ${t('artsmoker.ui.custom_models.hf_title')}</h3>
                    <div class="text-xs text-brand-text-muted space-y-2">
                        <p>${t('artsmoker.ui.custom_models.hf_status')} ${stored
                            ? html`<span class="text-emerald-400 font-medium">${t('artsmoker.ui.model_settings.ms_token_stored')}</span> ${t('artsmoker.ui.custom_models.hf_encrypted')}`
                            : html`<span class="text-amber-400 font-medium">${t('artsmoker.ui.model_settings.ms_no_token')}</span>`
                        }</p>
                        <p>${t('artsmoker.ui.custom_models.hf_desc')}</p>
                    </div>
                    <input type="password" class="hf-token-input input w-full text-xs font-mono" placeholder="${stored ? t('artsmoker.ui.custom_models.hf_placeholder_update') : t('artsmoker.ui.custom_models.hf_placeholder_store')}" autocomplete="off" />
                    <div class="flex gap-2 justify-end">
                        ${stored ? html`<button class="hf-delete btn btn-sm text-xs px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10">${t('artsmoker.ui.model_settings.ms_delete_token')}</button>` : ''}
                        <button class="hf-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${t('artsmoker.ui.model_settings.ms_close')}</button>
                        <button class="hf-save btn btn-sm text-xs px-4 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">${t('artsmoker.ui.model_settings.ms_save_token')}</button>
                    </div>
                </div>`;

            const cleanup = () => backdrop.remove();
            backdrop.querySelector('.hf-cancel').addEventListener('click', cleanup);
            backdrop.addEventListener('click', (e) => { if (e.target === backdrop) cleanup(); });

            backdrop.querySelector('.hf-save').addEventListener('click', async () => {
                const token = backdrop.querySelector('.hf-token-input').value.trim();
                if (!token) { window.showToast?.(t('artsmoker.ui.custom_models.enter_token'), 'error'); return; }
                try {
                    const resp = await fetch('/api/custom-models/hf-token', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ hf_token: token }),
                    });
                    if (resp.ok) {
                        window.showToast?.(t('artsmoker.ui.custom_models.token_saved'), 'success');
                        cleanup();
                    } else {
                        const err = await resp.json();
                        window.showToast?.(err.detail || 'Failed to save token', 'error');
                    }
                } catch (err) {
                    window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + err.message, 'error');
                }
            });

            const deleteBtn = backdrop.querySelector('.hf-delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', async () => {
                    if (!await window.showConfirm(t('artsmoker.ui.custom_models.delete_token_confirm'), { title: t('artsmoker.ui.custom_models.delete_token_title'), confirmLabel: t('artsmoker.ui.custom_models.remove'), danger: true })) return;
                    try {
                        await fetch('/api/custom-models/hf-token', { method: 'DELETE' });
                        window.showToast?.(t('artsmoker.ui.custom_models.token_deleted'), 'success');
                        cleanup();
                    } catch (err) {
                        window.showToast?.(t('artsmoker.ui.model_settings.ms_failed') + ': ' + err.message, 'error');
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
