/**
 * ArtSmoker — ImageStudio Component
 *
 * Two-level generation:
 *   Options    — distinctly different creative concepts
 *   Variations — seed variants of the selected concept
 */
(function () {
    'use strict';

    const ASSET_TYPES = [
        { value: 'photorealistic', labelKey: 'image_studio.asset_type_photo' },
        { value: 'character', labelKey: 'image_studio.asset_type_character' },
        { value: 'environment', labelKey: 'image_studio.asset_type_environment' },
        { value: 'game_asset', labelKey: 'image_studio.asset_type_game' },
        { value: 'marketing_banner', labelKey: 'image_studio.asset_type_banner' },
        { value: 'icon', labelKey: 'image_studio.asset_type_icon' },
    ];

    // Fallback models — used only if API fetch fails on first render.
    // The real model list is loaded dynamically from the registry via _loadModels().
    let MODELS = [
        { value: 'nova_canvas', label: 'Nova Canvas' },
        { value: 'titan_image', label: 'Titan Image v2' },
        { value: 'sd35_large', label: 'Stable Diffusion 3.5 Large' },
        { value: 'stable_image_ultra', label: 'Stable Image Ultra' },
        { value: 'all_models', label: '\u2500\u2500 All Available Models' },
    ];

    const SIZE_PRESETS = [
        { label: '512 x 512', w: 512, h: 512 },
        { label: '768 x 768', w: 768, h: 768 },
        { label: '1024 x 1024', w: 1024, h: 1024 },
        { label: '1024 x 576', w: 1024, h: 576 },
        { label: '576 x 1024', w: 576, h: 1024 },
        { label: '1280 x 720', w: 1280, h: 720 },
    ];

    const COUNT_OPTIONS = [1, 2, 3, 4, 5];

    window.ImageStudio = {
        _styles: [],
        _promptEditor: null,
        _skipPreCheck: false,
        _generating: false,
        _result: null,
        _selectedOption: 0,
        _selectedVariant: 0,
        _lastNegativePrompt: '',
        _selectedModels: [],

        render() {
            return `
                <div id="generator-view" class="view-enter">
                    <div class="mb-6">
                        <h1 class="text-2xl font-bold">${t('image_studio.title')}</h1>
                        <p class="text-brand-text-muted text-sm mt-1">${t('image_studio.subtitle')}</p>
                    </div>

                    <div class="flex flex-col lg:flex-row gap-6">

                        <!-- Left Sidebar -->
                        <aside class="lg:w-72 xl:w-80 flex-shrink-0 space-y-5">
                            <div class="card-static p-5 space-y-5">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
                                    </svg>
                                    ${t('common.settings')}
                                </h2>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('image_studio.style')}</label>
                                    <div class="select-expand-wrap">
                                        <select id="gen-style" class="input">
                                            <option value="">${t('image_studio.style_none')}</option>
                                        </select>
                                    </div>
                                </div>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('image_studio.asset_type')}</label>
                                    <div class="select-expand-wrap">
                                        <select id="gen-asset-type" class="input">
                                            ${ASSET_TYPES.map(at => `<option value="${at.value}">${t(at.labelKey)}</option>`).join('')}
                                        </select>
                                    </div>
                                </div>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('image_studio.model')}</label>
                                    <div id="gen-model-multi" class="relative">
                                        <button id="gen-model-btn" type="button" class="input text-left flex items-center justify-between w-full cursor-pointer">
                                            <span id="gen-model-label" class="truncate text-sm">Select models...</span>
                                            <svg class="w-4 h-4 text-brand-text-muted flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                                        </button>
                                        <div id="gen-model-dropdown" class="hidden absolute z-50 mt-1 min-w-full w-max max-h-60 overflow-y-auto rounded-lg border border-brand-border shadow-xl" style="background: var(--bg, #0f172a)"></div>
                                    </div>
                                    <!-- Smart summary line -->
                                    <p id="gen-model-summary" class="text-[10px] text-brand-text-dim mt-1"></p>
                                    <!-- Multi-model mode options -->
                                    <div id="gen-all-models-opts" class="hidden mt-2 p-2 rounded-lg bg-brand-bg/50 space-y-1.5">
                                        <label class="flex items-center gap-2 text-xs text-brand-text-muted cursor-pointer">
                                            <input type="checkbox" id="gen-model-optimized" class="rounded" checked />
                                            ${t('image_studio.model_optimized_prompts')}
                                        </label>
                                        <p class="text-[10px] text-brand-text-dim">${t('image_studio.model_optimized_desc')}</p>
                                        <p id="gen-all-models-info" class="text-[10px] text-emerald-400/70"></p>
                                    </div>
                                </div>

                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('image_studio.dimensions')}</label>
                                    <div class="select-expand-wrap">
                                        <select id="gen-size" class="input">
                                            ${SIZE_PRESETS.map((s, i) => `<option value="${i}" ${i === 2 ? 'selected' : ''}>${s.label}</option>`).join('')}
                                        </select>
                                    </div>
                                </div>

                                <!-- Advanced: Quality + Region (collapsible) -->
                                <details id="gen-advanced-section" class="group">
                                    <summary class="text-xs font-medium text-brand-text-muted cursor-pointer hover:text-brand-text transition-colors select-none">
                                        <span class="group-open:hidden">\u25B8 ${t('image_studio.advanced_expand')}</span>
                                        <span class="hidden group-open:inline">\u25BE ${t('image_studio.advanced_collapse')}</span>
                                    </summary>
                                    <div class="mt-2 space-y-3 p-2.5 rounded-lg bg-brand-bg/40 border border-brand-border/50">
                                        <div>
                                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1">${t('image_studio.quality')}</label>
                                            <select id="gen-quality" class="input text-xs">
                                                <option value="">${t('common.default')}</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1">${t('image_studio.region')}</label>
                                            <select id="gen-region" class="input text-xs">
                                                <option value="">${t('image_studio.region_auto')}</option>
                                            </select>
                                        </div>
                                    </div>
                                </details>

                                <!-- Cost estimate -->
                                <div id="gen-cost-estimate" class="text-[10px] text-emerald-400/70 font-mono"></div>

                                <!-- Two-level counts -->
                                <div class="grid grid-cols-2 gap-3">
                                    <div>
                                        <label class="block text-sm font-medium mb-1.5">${t('image_studio.num_options')}</label>
                                        <select id="gen-num-options" class="input">
                                            ${COUNT_OPTIONS.map(n => `<option value="${n}" ${n === 5 ? 'selected' : ''}>${n}</option>`).join('')}
                                        </select>
                                        <p class="text-[10px] text-brand-text-muted mt-0.5">${t('image_studio.different_designs')}</p>
                                    </div>
                                    <div>
                                        <label class="block text-sm font-medium mb-1.5">${t('image_studio.num_variations')}</label>
                                        <select id="gen-num-variations" class="input">
                                            ${COUNT_OPTIONS.map(n => `<option value="${n}" ${n === 5 ? 'selected' : ''}>${n}</option>`).join('')}
                                        </select>
                                        <p class="text-[10px] text-brand-text-muted mt-0.5">${t('image_studio.per_option')}</p>
                                    </div>
                                </div>

                            </div>

                            <!-- Intellectual Property & Content Check -->
                            <div class="card-static p-4 space-y-3">
                                <h2 class="text-sm font-semibold flex items-center gap-2 text-brand-text-muted uppercase tracking-wide">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                    </svg>
                                    ${t('image_studio.ip_declaration')}
                                </h2>
                                <div class="space-y-2">
                                    <label class="flex items-start gap-2 cursor-pointer">
                                        <input type="checkbox" id="gen-ip-own" class="mt-0.5 rounded border-brand-border bg-brand-bg text-brand-accent focus:ring-brand-accent">
                                        <span class="text-xs text-brand-text/80">${t('image_studio.ip_own')}</span>
                                    </label>
                                    <label class="flex items-start gap-2 cursor-pointer">
                                        <input type="checkbox" id="gen-ip-license" class="mt-0.5 rounded border-brand-border bg-brand-bg text-brand-accent focus:ring-brand-accent">
                                        <span class="text-xs text-brand-text/80">${t('image_studio.ip_license')}</span>
                                    </label>
                                </div>
                                <div id="gen-ip-model-note" class="hidden p-2 rounded-lg bg-amber-950/20 border border-amber-500/20 text-[10px] text-amber-300/80"></div>
                                <p class="text-[10px] text-brand-text-muted/50">${t('image_studio.ip_help')}</p>

                                <!-- Prompt Pre-Check (within IP section) -->
                                <div class="flex items-center justify-between pt-2 border-t border-brand-border/30">
                                    <div class="flex items-center gap-2">
                                        <svg class="w-3.5 h-3.5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                                        </svg>
                                        <label class="text-xs font-medium">${t('image_studio.pre_check_label')}</label>
                                    </div>
                                    <label class="toggle"><input type="checkbox" id="gen-precheck" checked><span class="toggle-slider"></span></label>
                                </div>
                                <p class="text-[10px] text-brand-text-muted/50 -mt-1">${t('image_studio.pre_check_help')}</p>
                            </div>

                            <!-- Model Settings -->
                            <button id="btn-model-settings" class="w-full text-left p-3 rounded-lg bg-emerald-700 hover:bg-emerald-600 border border-emerald-500/30 transition-colors flex items-center gap-2 text-xs text-white font-medium">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                                ${t('image_studio.model_settings')}
                            </button>

                            <!-- Processing Options -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-sm font-semibold flex items-center gap-2 text-brand-text-muted uppercase tracking-wide">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343"/>
                                    </svg>
                                    <span id="gen-processing-label">${t('image_studio.post_processing')}</span>
                                </h2>
                                <div class="space-y-3">
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">${t('image_studio.remove_bg')}</label>
                                        <label class="toggle"><input type="checkbox" id="gen-remove-bg"><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">${t('image_studio.convert_svg')}</label>
                                        <label class="toggle"><input type="checkbox" id="gen-svg" checked><span class="toggle-slider"></span></label>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm">${t('image_studio.upscale')}</label>
                                        <label class="toggle"><input type="checkbox" id="gen-upscale"><span class="toggle-slider"></span></label>
                                    </div>
                                </div>
                                <button id="btn-apply-postprocess" class="btn btn-secondary btn-sm w-full hidden">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                    </svg>
                                    ${t('image_studio.pp_apply')}
                                </button>
                                <p id="pp-hint" class="text-[10px] text-brand-text-muted/50 hidden">${t('image_studio.pp_hint')}</p>
                            </div>

                            <p class="artsmoker-version text-[9px] text-brand-text-dim/30 text-center mt-4">${t('app.version_prefix')}</p>
                        </aside>

                        <!-- Center: Prompt + Results -->
                        <div class="flex-1 min-w-0 space-y-5">

                            <!-- Prompt / Reference-guided tabs -->
                            <div class="card-static p-5 space-y-4">
                                <div class="flex items-center gap-1.5 p-1 rounded-xl bg-brand-bg/60 border border-brand-border -mt-1">
                                    <button id="tab-prompt" data-tab="prompt" class="is-tab flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg transition-all bg-cyan-500 text-white shadow-sm">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                        </svg>
                                        ${t('image_studio.tab_text_inspiration')}
                                    </button>
                                    <button id="tab-reference" data-tab="reference" class="is-tab flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg transition-all bg-cyan-500/15 text-cyan-300/80 hover:bg-cyan-500/25 hover:text-cyan-200">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                                        </svg>
                                        ${t('image_studio.reference_tab')}
                                    </button>
                                </div>
                                <div id="prompt-editor-container"></div>
                                <div id="reference-studio-container" class="hidden"></div>
                            </div>

                            <!-- Generate / Reset -->
                            <div class="grid grid-cols-2 gap-3 mt-2">
                                <button id="btn-generate" class="btn btn-primary btn-lg text-base">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                    </svg>
                                    ${t('image_studio.generate')}
                                </button>
                                <button id="btn-reset" class="btn btn-lg text-base bg-amber-600 hover:bg-amber-500 text-white">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                    </svg>
                                    ${t('image_studio.reset')}
                                </button>
                            </div>

                            <!-- Pending Jobs (async custom models) -->
                            <button id="btn-pending-jobs" class="w-full text-left p-2 rounded-lg bg-cyan-700/10 border border-cyan-600/20 hover:border-cyan-500/40 hover:bg-cyan-700/20 transition-colors flex items-center gap-2 text-xs text-cyan-400 mt-2 hidden">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                                <span id="pending-jobs-label">${t('custom_models.pending_jobs')}</span>
                            </button>

                            <!-- Prompt info (original + AI-improved + negative) -->
                            <div id="gen-prompt-info" class="hidden card-static p-4 space-y-3">
                                <div id="gen-original-prompt-section">
                                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold mb-1">${t('image_studio.original_prompt_label')}</p>
                                    <p id="gen-original-prompt-text" class="text-sm text-brand-text/80 leading-relaxed"></p>
                                </div>
                                <div id="gen-used-prompt-section">
                                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold mb-1">${t('image_studio.enhanced_prompt_label')}</p>
                                    <p id="gen-used-prompt-text" class="text-sm text-brand-text/60 leading-relaxed"></p>
                                </div>
                                <div id="gen-negative-prompt-section" class="hidden">
                                    <p class="text-[10px] text-amber-400/80 uppercase tracking-wider font-semibold mb-1">${t('image_studio.negative_prompt_exclusions')}</p>
                                    <p id="gen-negative-prompt-text" class="text-sm text-amber-300/60 leading-relaxed italic"></p>
                                </div>
                                <div id="gen-cost-breakdown" class="hidden p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/20">
                                    <div class="flex items-center justify-between mb-1">
                                        <span class="text-[10px] text-emerald-400/80 uppercase tracking-wider font-semibold">${t('image_studio.est_cost')}</span>
                                        <span id="gen-cost-total" class="text-sm font-bold text-emerald-400">$0.00</span>
                                    </div>
                                    <div id="gen-cost-details" class="text-[10px] text-emerald-300/60 space-y-0.5"></div>
                                </div>
                                <div id="gen-rewrite-disclaimer" class="hidden p-3 rounded-lg bg-amber-950/20 border border-amber-500/20">
                                    <p class="text-[10px] text-amber-300/80"><strong>${t('image_studio.rewritten_prompt_note')}</strong> ${t('image_studio.rewrite_disclaimer_text')}</p>
                                </div>
                            </div>

                            <!-- Concept prompt display -->
                            <div id="gen-concept-prompt" class="hidden card-static p-3 space-y-2">
                                <p id="gen-concept-prompt-label" class="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold">${t('image_studio.generated_prompt')}</p>
                                <p id="gen-concept-prompt-text" class="text-xs text-brand-text/70 leading-relaxed"></p>
                                <div id="gen-concept-negative" class="hidden">
                                    <p class="text-[10px] text-amber-400/80 uppercase tracking-wider font-semibold mb-0.5">${t('image_studio.negative_prompt_label')}</p>
                                    <p id="gen-concept-negative-text" class="text-xs text-amber-300/60 italic leading-relaxed"></p>
                                </div>
                            </div>

                            <!-- OPTIONS ROW (different concepts) -->
                            <div id="gen-options-section" class="hidden">
                                <div class="flex items-center justify-between mb-2">
                                    <h3 id="gen-options-header" class="text-sm font-semibold text-brand-text-muted uppercase tracking-wide">
                                        ${t('image_studio.options_header')}
                                    </h3>
                                    <span id="gen-options-count" class="text-xs text-brand-text-muted"></span>
                                </div>
                                <div id="gen-options-grid" class="grid grid-cols-5 gap-3"></div>
                            </div>

                            <!-- VARIATIONS ROW (seed variants of selected option) -->
                            <div id="gen-variations-section" class="hidden">
                                <div class="flex items-center justify-between mb-2">
                                    <h3 class="text-sm font-semibold text-brand-text-muted uppercase tracking-wide">
                                        ${t('image_studio.variations_header')}
                                    </h3>
                                    <span id="gen-variations-count" class="text-xs text-brand-text-muted"></span>
                                </div>
                                <div id="gen-variations-grid" class="grid grid-cols-5 gap-3"></div>
                            </div>

                            <!-- Main Preview -->
                            <div class="card-static overflow-hidden">
                                <div id="gen-preview" class="preview-checkerboard min-h-[350px] lg:min-h-[450px] flex items-center justify-center p-6 relative">
                                    <div id="gen-placeholder" class="text-center">
                                        <svg class="w-16 h-16 mx-auto text-brand-text-muted/20 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                                        </svg>
                                        <p class="text-brand-text-muted/40 text-sm">${t('image_studio.placeholder_text')}</p>
                                    </div>
                                    <div id="gen-loading" class="hidden absolute inset-0 bg-brand-bg/60 flex flex-col items-center justify-center gap-4 px-8">
                                        <div class="loading-spinner w-10 h-10 border-4 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                        <p id="gen-loading-text" class="text-sm text-brand-text-muted font-medium">${t('image_studio.generating')}</p>
                                        <p id="gen-loading-sub" class="text-xs text-brand-text-muted/60"></p>
                                        <div class="w-full max-w-xs mt-2">
                                            <div class="h-1.5 bg-brand-border rounded-full overflow-hidden">
                                                <div id="gen-progress-bar" class="h-full bg-brand-accent rounded-full transition-all duration-1000 ease-out" style="width: 0%"></div>
                                            </div>
                                            <p id="gen-loading-elapsed" class="text-[10px] text-brand-text-muted/40 text-center mt-1.5"></p>
                                        </div>
                                    </div>
                                    <img id="gen-result-img" class="hidden max-w-full max-h-[60vh] rounded-lg shadow-2xl" alt="${t('image_studio.title')}" />
                                </div>

                                <!-- Download bar -->
                                <div id="gen-download-bar" class="hidden border-t border-brand-border p-4 flex flex-wrap items-center justify-between gap-3 bg-brand-surface">
                                    <div class="text-sm text-brand-text-muted">
                                        <span id="gen-result-info"></span>
                                    </div>
                                    <div class="flex gap-2">
                                        <a id="dl-png" href="#" download class="btn btn-secondary btn-sm">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                            </svg>
                                            PNG
                                        </a>
                                        <a id="dl-svg" href="#" download class="btn btn-secondary btn-sm hidden">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                                            </svg>
                                            SVG
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        },

        /** Called when navigating back to ImageStudio (view already cached) */
        onShow() {
            this._loadModels();  // Refresh model list (picks up newly deployed custom models)
            this._loadStyles();
            this._ensurePromptEditor();
            // Re-render results if async jobs completed while we were on another view
            if (this._result?.options) {
                const hasNewImages = this._result.options.some(opt =>
                    (opt.variants || []).some(v => v.png_path && !v.async_job)
                );
                if (hasNewImages) {
                    this._renderOptionsRow(this._result.options);
                    this._selectOption(this._selectedOption || 0);
                }
            }
            // One-time check — if active jobs found, polling resumes. If not, stops.
            this._checkAsyncJobs();
        },

        _ensurePromptEditor() {
            // Check if the editor exists AND its textarea is still in the live DOM
            // (after resetView, the old editor's DOM is destroyed but the object remains)
            if (this._promptEditor && this._promptEditor._textareaEl && document.contains(this._promptEditor._textareaEl)) return;
            this._promptEditor = null; // Clear stale reference
            const container = document.getElementById('prompt-editor-container');
            if (container) {
                try {
                    this._promptEditor = new PromptEditor(container, {
                        styleId: this._getStyleId(),
                        assetType: this._getAssetType(),
                        imageModel: (this._selectedModels?.[0] || ''),
                        onAssetTypeChange: (newType) => {
                            const sel = document.getElementById('gen-asset-type');
                            if (sel) {
                                sel.value = newType;
                                sel.dispatchEvent(new Event('change'));
                            }
                        },
                        onStyleChange: (newStyleId) => {
                            const sel = document.getElementById('gen-style');
                            if (sel) {
                                sel.value = newStyleId;
                                sel.dispatchEvent(new Event('change'));
                            }
                        },
                    });
                } catch (err) {
                    console.error('Failed to create PromptEditor:', err);
                    if (typeof API !== 'undefined') API.log('error', 'PromptEditor init failed: ' + err.message);
                }
            }
        },

        _ensureReferenceStudio() {
            if (this._referenceStudio && this._referenceStudio._promptEl && document.contains(this._referenceStudio._promptEl)) return;
            this._referenceStudio = null;
            const container = document.getElementById('reference-studio-container');
            if (container && typeof ReferenceStudio !== 'undefined') {
                try {
                    this._referenceStudio = new ReferenceStudio(container, {
                        assetType: () => this._getAssetType(),
                    });
                } catch (err) {
                    console.error('Failed to create ReferenceStudio:', err);
                }
            }
        },

        /** Switch the center panel between the Prompt editor and the Reference-guided studio. */
        _switchTab(tab) {
            this._activeTab = tab === 'reference' ? 'reference' : 'prompt';
            const promptC = document.getElementById('prompt-editor-container');
            const refC = document.getElementById('reference-studio-container');
            const isRef = this._activeTab === 'reference';
            promptC?.classList.toggle('hidden', isRef);
            refC?.classList.toggle('hidden', !isRef);
            if (isRef) this._ensureReferenceStudio();
            // Reflect active tab styling — both tabs use CYAN (distinct from the
            // indigo Generate / amber Reset buttons): the active tab is a bright
            // solid cyan fill, the inactive tab a dim translucent cyan.
            const ACTIVE = ['bg-cyan-500', 'text-white', 'shadow-sm'];
            const INACTIVE = ['bg-cyan-500/15', 'text-cyan-300/80', 'hover:bg-cyan-500/25', 'hover:text-cyan-200'];
            const setActive = (btn, active) => {
                if (!btn) return;
                ACTIVE.concat(INACTIVE).forEach(c => btn.classList.remove(c));
                (active ? ACTIVE : INACTIVE).forEach(c => btn.classList.add(c));
            };
            setActive(document.getElementById('tab-prompt'), !isRef);
            setActive(document.getElementById('tab-reference'), isRef);
        },

        async init() {
            await this._loadModels();
            await this._loadStyles();
            this._ensurePromptEditor();

            // Refresh models when Model Settings closes (enable/disable, deploy/teardown)
            window.addEventListener('model-settings-closed', () => this._loadModels());

            document.getElementById('gen-style')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ styleId: this._getStyleId() });
            });
            document.getElementById('gen-asset-type')?.addEventListener('change', () => {
                if (this._promptEditor) this._promptEditor.setContext({ assetType: this._getAssetType() });
            });
            // Multi-select model dropdown: toggle open/close
            // Multi-select dropdown: toggle
            document.getElementById('gen-model-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                const dd = document.getElementById('gen-model-dropdown');
                if (!dd) return;
                const wasOpen = !dd.classList.contains('hidden');
                dd.classList.toggle('hidden');
                // If closing and nothing selected, auto-select first
                if (wasOpen && !this._selectedModels.length) {
                    const realModels = MODELS.filter(m => m.value !== 'all_models');
                    if (realModels.length) {
                        this._selectedModels = [realModels[0].value];
                        this._syncModelCheckboxes();
                        window.showToast?.(`Selected ${realModels[0].label} — at least one model is required`, 'info');
                    }
                }
            });
            // Close dropdown on outside click — auto-select first model if empty
            document.addEventListener('click', (e) => {
                if (!e.target.closest('#gen-model-multi')) {
                    const dd = document.getElementById('gen-model-dropdown');
                    if (dd && !dd.classList.contains('hidden')) {
                        dd.classList.add('hidden');
                        if (!this._selectedModels.length) {
                            const realModels = MODELS.filter(m => m.value !== 'all_models');
                            if (realModels.length) {
                                this._selectedModels = [realModels[0].value];
                                this._syncModelCheckboxes();
                                window.showToast?.(`Selected ${realModels[0].label} — at least one model is required`, 'info');
                            }
                        }
                    }
                }
            });
            // Checkbox change handler (delegated) — allows unchecking everything
            document.getElementById('gen-model-dropdown')?.addEventListener('change', (e) => {
                const cb = e.target;
                if (cb.id === 'gen-model-all') {
                    const realModels = MODELS.filter(m => m.value !== 'all_models');
                    this._selectedModels = cb.checked ? realModels.map(m => m.value) : [];
                } else if (cb.classList.contains('gen-model-cb')) {
                    if (cb.checked) {
                        if (!this._selectedModels.includes(cb.value)) this._selectedModels.push(cb.value);
                    } else {
                        this._selectedModels = this._selectedModels.filter(v => v !== cb.value);
                    }
                }
                // Update prompt editor context with first selected model
                if (this._promptEditor && this._selectedModels.length) {
                    this._promptEditor.setContext({ imageModel: this._selectedModels[0] });
                }
                this._syncModelCheckboxes();
            });

            // Quality change: update region prices + summary
            document.getElementById('gen-quality')?.addEventListener('change', () => {
                if (this._selectedModels.length === 1) {
                    this._updateRegionForModel(this._selectedModels[0]);
                }
                this._updateMultiModelCostEstimate();
            });
            document.getElementById('gen-region')?.addEventListener('change', () => this._updateMultiModelCostEstimate());
            document.getElementById('gen-size')?.addEventListener('change', () => this._updateMultiModelCostEstimate());
            document.getElementById('gen-num-options')?.addEventListener('change', () => this._updateMultiModelCostEstimate());
            document.getElementById('gen-num-variations')?.addEventListener('change', () => this._updateMultiModelCostEstimate());
            document.getElementById('btn-generate')?.addEventListener('click', () => this._handleGenerate());
            // Prompt ⇄ Reference-guided tab switching (ImageStudio binds via
            // document.getElementById — it's a singleton, not a scoped component).
            document.querySelectorAll('#tab-prompt, #tab-reference').forEach(btn => {
                btn.addEventListener('click', () => this._switchTab(btn.dataset.tab));
            });
            document.getElementById('btn-model-settings')?.addEventListener('click', () => ModelSettings.open('image-studio'));
            document.getElementById('btn-pending-jobs')?.addEventListener('click', () => this._showPendingJobs());

            // Start polling for pending jobs count
            this._pollPendingJobs();

            // IP declaration — show model recommendation + disable pre-check when claimed
            const updateIpNote = () => {
                this._updateIpModelNote();
                const ip = this._getIpDeclaration();
                const precheck = document.getElementById('gen-precheck');
                if (precheck) {
                    if (ip.ip_owned || ip.ip_licensed) {
                        precheck.checked = false;
                        precheck.disabled = true;
                        precheck.closest('.flex')?.classList.add('opacity-40');
                    } else {
                        precheck.disabled = false;
                        precheck.closest('.flex')?.classList.remove('opacity-40');
                    }
                }
            };
            document.getElementById('gen-ip-own')?.addEventListener('change', updateIpNote);
            document.getElementById('gen-ip-license')?.addEventListener('change', updateIpNote);
            document.getElementById('btn-apply-postprocess')?.addEventListener('click', () => this._handlePostProcess());

            // Click on preview image → open AssetViewer with zoom/pan and full metadata
            document.getElementById('gen-result-img')?.addEventListener('click', () => {
                const result = this._result;
                if (!result) return;
                const option = (result.options || [])[this._selectedOption];
                if (!option) return;
                const variant = (option.variants || [])[this._selectedVariant];
                if (!variant) return;
                // Build a gallery-compatible item for AssetViewer
                const item = {
                    id: variant.id,
                    prompt: result.prompt,
                    style_id: result.style_id,
                    asset_type: result.asset_type,
                    png_url: variant.png_path,
                    svg_url: variant.svg_path,
                    png_filename: variant.png_filename,
                    svg_filename: variant.svg_filename,
                };
                if (typeof AssetViewer !== 'undefined') {
                    // Build a list of all variants for prev/next navigation
                    const allVariants = [];
                    let currentIdx = 0;
                    (result.options || []).forEach(opt => {
                        (opt.variants || []).forEach(v => {
                            if (v.id === variant.id) currentIdx = allVariants.length;
                            allVariants.push({
                                id: v.id, prompt: result.prompt,
                                style_id: result.style_id, asset_type: result.asset_type,
                                png_url: v.png_path, svg_url: v.svg_path,
                                png_filename: v.png_filename, svg_filename: v.svg_filename,
                            });
                        });
                    });
                    AssetViewer.open(item, allVariants, currentIdx);
                }
            });
            // Show pointer cursor on the preview image
            const previewImg = document.getElementById('gen-result-img');
            if (previewImg) previewImg.style.cursor = 'pointer';
            document.getElementById('btn-reset')?.addEventListener('click', async () => {
                if (this._result && !await window.showConfirm(t('image_studio.reset_confirm'), { title: t('image_studio.reset'), detail: t('image_studio.reset_detail'), confirmLabel: t('image_studio.reset'), danger: true })) return;
                // Clear all state before rebuilding the view
                this._result = null;
                this._selectedOption = 0;
                this._selectedVariant = 0;
                this._lastNegativePrompt = '';
                this._promptEditor = null;
                this._stopAsyncPolling();
                this._notifiedJobIds = new Set();
                window.PromptDesigner?.reset();
                window.resetView('image-studio');
            });
        },

        async _loadModels(regionFilter) {
            try {
                const data = await API.admin.getImageOptions(regionFilter || undefined);
                if (data?.models?.length) {
                    MODELS = data.models.map(m => ({
                        value: m.key,
                        label: m.model_source === 'custom_hosted' ? `⚡ ${m.label} (self-hosted)` : m.label,
                        provider: m.provider,
                        model_source: m.model_source,
                        region: m.region,
                        available_regions: m.available_regions || [m.region],
                        region_pricing: m.region_pricing || [],
                        prompt_limit: m.prompt_limit,
                        moderation_strictness: m.moderation_strictness,
                        quality_options: m.quality_options || [],
                        default_quality: m.default_quality || '',
                        base_price_usd: m.base_price_usd || null,
                        supported_sizes: m.supported_sizes || null,
                    }));
                    // Append the virtual "All Available Models" entry
                    MODELS.push({ value: 'all_models', label: '\u2500\u2500 All Available Models' });
                    console.log(`Loaded ${data.models.length} image models from registry` +
                        (regionFilter ? ` (filtered: ${regionFilter})` : ''));
                }

                // Populate region dropdown from model availability (shows only regions with enabled models)
                if (data?.available_regions && !regionFilter) {
                    this._populateRegions(data.available_regions);
                }
            } catch (err) {
                console.warn('Failed to load image models from registry, using fallback:', err);
            }

            // Populate the multi-select checkbox dropdown
            const dropdown = document.getElementById('gen-model-dropdown');
            if (!dropdown) return;
            dropdown.innerHTML = '';
            const realModels = MODELS.filter(m => m.value !== 'all_models');

            realModels.forEach((m, idx) => {
                const row = document.createElement('label');
                row.className = 'flex items-center gap-2 text-xs cursor-pointer py-1.5 px-3 hover:bg-brand-bg/60';
                row.innerHTML = `<input type="checkbox" class="gen-model-cb rounded border-brand-border" value="${m.value}" data-idx="${idx}" />
                    <span class="whitespace-nowrap">${m.label}</span>`;
                dropdown.appendChild(row);
            });

            // "All Available Models" toggle at the bottom
            const sep = document.createElement('div');
            sep.className = 'border-t border-brand-border/50 mt-1 pt-1 px-3 pb-1';
            sep.innerHTML = `<label class="flex items-center gap-2 text-xs cursor-pointer py-1 hover:bg-brand-bg/60 rounded px-1">
                <input type="checkbox" id="gen-model-all" class="rounded border-brand-border" />
                <span class="text-brand-text-muted">\u2500\u2500 ${t('image_studio.all_models') || 'All Available Models'}</span>
            </label>`;
            dropdown.appendChild(sep);

            // Restore or initialize selection — keep valid previously selected models
            if (this._selectedModels.length) {
                const validKeys = new Set(realModels.map(m => m.value));
                this._selectedModels = this._selectedModels.filter(k => validKeys.has(k));
            }
            if (!this._selectedModels.length && realModels.length) {
                this._selectedModels = [realModels[0].value];
            }
            this._syncModelCheckboxes();
        },

        _updateQualityForModel(modelKey) {
            const qualSel = document.getElementById('gen-quality');
            if (!qualSel || modelKey === 'all_models') {
                if (qualSel) { qualSel.innerHTML = `<option value="">${t('image_studio.quality_default')}</option>`; }
                return;
            }
            const modelData = MODELS.find(m => m.value === modelKey);
            const options = modelData?.quality_options || [];
            const defaultQ = modelData?.default_quality || '';

            qualSel.innerHTML = '';
            if (options.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = t('image_studio.quality_default_no_tiers');
                qualSel.appendChild(opt);
            } else {
                options.forEach(q => {
                    const opt = document.createElement('option');
                    opt.value = q.value;
                    opt.textContent = q.value === defaultQ ? `${q.label} (${t('common.default')})` : q.label;
                    if (q.value === defaultQ) opt.selected = true;
                    qualSel.appendChild(opt);
                });
            }
        },

        /** Per-image price for a model, region- and quality-aware — the single
         *  source of truth for cost estimates. Mirrors the backend registry
         *  pricing (region_pricing[].quality_prices → region price → base_price).
         *  Returns null when the registry has no price (caller omits the estimate
         *  rather than showing a guessed/hardcoded figure). */
        _perImagePrice(modelData, region, quality) {
            if (!modelData) return null;
            const regionPricing = modelData.region_pricing || [];
            const rp = regionPricing.find(r => r.region === region) || regionPricing[0] || {};
            if (rp.quality_prices && quality && rp.quality_prices[quality] != null) {
                return rp.quality_prices[quality];
            }
            if (rp.price_usd != null) return rp.price_usd;
            if (modelData.base_price_usd != null) return modelData.base_price_usd;
            return null;
        },

        _updateModelSummary() {
            const summaryEl = document.getElementById('gen-model-summary');
            const costEl = document.getElementById('gen-cost-estimate');
            if (!summaryEl) return;

            const modelKey = (this._selectedModels?.[0] || '');
            if (modelKey === 'all_models') {
                summaryEl.textContent = '';
                if (costEl) costEl.textContent = '';
                return;
            }

            const modelData = MODELS.find(m => m.value === modelKey);
            if (!modelData) { summaryEl.textContent = ''; return; }

            const quality = document.getElementById('gen-quality')?.value || modelData.default_quality || '';
            const region = document.getElementById('gen-region')?.value || modelData.region || '';
            const price = this._perImagePrice(modelData, region, quality);
            const priceStr = price != null ? `$${price.toFixed(2)}/img` : '';
            const qualityLabel = quality ? quality.charAt(0).toUpperCase() + quality.slice(1) : '';

            // Summary line: "us-east-1 · Premium · $0.06/img"
            const parts = [region, qualityLabel, priceStr].filter(Boolean);
            summaryEl.textContent = parts.join(' \u00b7 ');

            // Cost estimate
            if (costEl && price != null) {
                const numOpts = parseInt(document.getElementById('gen-num-options')?.value || '5', 10);
                const numVars = parseInt(document.getElementById('gen-num-variations')?.value || '5', 10);
                const total = numOpts * numVars;
                const est = (price * total).toFixed(2);
                costEl.textContent = t('image_studio.est_cost_line').replace('{{est}}', est).replace('{{total}}', total).replace('{{price}}', price.toFixed(2));
            } else if (costEl) {
                costEl.textContent = '';
            }
        },

        _updateRegionForModel(modelKey) {
            const regionSel = document.getElementById('gen-region');
            if (!regionSel || modelKey === 'all_models') return;

            const modelData = MODELS.find(m => m.value === modelKey);
            const regionPricing = modelData?.region_pricing || [];
            const selectedQuality = document.getElementById('gen-quality')?.value || modelData?.default_quality || '';

            const basePrice = modelData?.base_price_usd || null;

            // Resolve price per region for the currently selected quality
            const regions = regionPricing.length > 0
                ? regionPricing.map(rp => {
                    let price = null;
                    if (rp.quality_prices && selectedQuality && rp.quality_prices[selectedQuality] != null) {
                        price = rp.quality_prices[selectedQuality];
                    } else if (rp.price_usd != null) {
                        price = rp.price_usd;
                    } else if (basePrice != null) {
                        price = basePrice;
                    }
                    return { region: rp.region, price_usd: price };
                })
                : (modelData?.available_regions || [modelData?.region]).filter(Boolean).map(r => ({ region: r, price_usd: null }));

            // Sort by price (cheapest first)
            regions.sort((a, b) => {
                if (a.price_usd == null && b.price_usd == null) return 0;
                if (a.price_usd == null) return 1;
                if (b.price_usd == null) return -1;
                return a.price_usd - b.price_usd;
            });

            const currentValue = regionSel.value;
            regionSel.innerHTML = '';

            if (regions.length <= 1) {
                const rp = regions[0] || { region: '', price_usd: null };
                const opt = document.createElement('option');
                opt.value = rp.region;
                opt.textContent = rp.price_usd != null
                    ? `${rp.region} ($${rp.price_usd.toFixed(2)}/img)`
                    : rp.region;
                regionSel.appendChild(opt);
            } else {
                const cheapest = regions[0];
                const auto = document.createElement('option');
                auto.value = '';
                auto.textContent = cheapest.price_usd != null
                    ? `${t('image_studio.region_auto')} \u2014 ${cheapest.region} ($${cheapest.price_usd.toFixed(2)}/img)`
                    : `${t('image_studio.region_auto')} \u2014 ${cheapest.region}`;
                regionSel.appendChild(auto);
                regions.forEach(rp => {
                    const opt = document.createElement('option');
                    opt.value = rp.region;
                    opt.textContent = rp.price_usd != null
                        ? `${rp.region} ($${rp.price_usd.toFixed(2)}/img)`
                        : rp.region;
                    regionSel.appendChild(opt);
                });
            }
            // Restore previous selection if still valid
            if (currentValue && [...regionSel.options].some(o => o.value === currentValue)) {
                regionSel.value = currentValue;
            }
        },

        _populateRegions(regions) {
            const regionSel = document.getElementById('gen-region');
            if (!regionSel) return;
            const current = regionSel.value;
            regionSel.innerHTML = `<option value="">${t('image_studio.region_all')}</option>`;
            (regions || []).forEach(r => {
                const opt = document.createElement('option');
                opt.value = r;
                opt.textContent = r;
                regionSel.appendChild(opt);
            });
            if (current) regionSel.value = current;
        },

        async _loadStyles() {
            try {
                const data = await API.styles.list();
                this._styles = Array.isArray(data) ? data : [];
            } catch { this._styles = []; }

            const sel = document.getElementById('gen-style');
            if (!sel) return;
            const currentValue = sel.value;
            const none = sel.querySelector('option');
            sel.innerHTML = '';
            sel.appendChild(none);
            this._styles.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.name;
                sel.appendChild(opt);
            });
            // Restore previous selection if it still exists
            if (currentValue) sel.value = currentValue;
        },

        // ── Generation ──────────────────────────────────────────────

        async _handleGenerate() {
            if (this._generating) return;

            // Reference-guided tab has its own prompt + validation + payload patch.
            const isReference = this._activeTab === 'reference' && this._referenceStudio;
            let referencePatch = null;
            let userPrompt, prompt, hasComposed = false;
            if (isReference) {
                const err = this._referenceStudio.validate();
                if (err) { window.showToast?.(err, 'warning'); return; }
                userPrompt = this._referenceStudio.getPrompt();
                prompt = userPrompt;
                referencePatch = this._referenceStudio.getPayloadPatch();
            } else {
                // Get the user's raw prompt (always required)
                userPrompt = this._promptEditor ? this._promptEditor.getUserText().trim() : '';
                if (!userPrompt) {
                    window.showToast?.(t('image_studio.enter_prompt'), 'warning');
                    return;
                }
                // If a composed prompt exists, use it directly (skip re-refinement in backend)
                // If not, send the raw user prompt (backend will refine it)
                hasComposed = this._promptEditor?.hasComposedPrompt();
                prompt = hasComposed
                    ? this._promptEditor.getComposedText().trim()
                    : userPrompt;
            }

            const sizeIdx = parseInt(document.getElementById('gen-size').value, 10);
            const activeSizes = this._activeSizePresets || SIZE_PRESETS;
            const size = activeSizes[sizeIdx] || activeSizes[Math.min(2, activeSizes.length - 1)];

            // Check if any selected model doesn't support the chosen dimensions
            const unsupportedModels = this._selectedModels.map(key => {
                const m = MODELS.find(m => m.value === key);
                if (!m?.supported_sizes?.length) return null;
                const match = m.supported_sizes.some(s => s.w === size.w && s.h === size.h);
                return match ? null : m;
            }).filter(Boolean);

            if (unsupportedModels.length > 0 && window.showConfirm) {
                const modelNames = unsupportedModels.map(m => m.label).join(', ');
                const shouldContinue = await window.showConfirm(
                    `${modelNames} ${unsupportedModels.length === 1 ? 'does' : 'do'} not support ${size.label}. The closest supported size will be used for ${unsupportedModels.length === 1 ? 'this model' : 'these models'}.`,
                    {
                        title: 'Dimension not supported by all models',
                        confirmLabel: 'Continue anyway',
                        cancelLabel: 'Change dimensions',
                    }
                );
                if (!shouldContinue) return;
            }

            const numOptions = parseInt(document.getElementById('gen-num-options').value, 10) || 5;
            const numVariations = parseInt(document.getElementById('gen-num-variations').value, 10) || 5;
            const total = numOptions * numVariations;

            const moderationOriginal = this._promptEditor?._moderationOriginal || null;

            // Carry the negative prompt from the Compose step (if user pre-composed)
            const composedNegative = this._promptEditor?.getNegativePrompt?.() || '';

            const isMultiModel = this._isAllModels();

            // Validate model selection (reference "match" mode uses the deployed
            // reference model, and "inspired" uses whatever is selected — but both
            // still fall back to a T2I model, so a selection is only strictly
            // required outside reference mode).
            if (!this._selectedModels.length && !isReference) {
                window.showToast?.(t('image_studio.select_at_least_one_model') || 'Select at least one model', 'error');
                return;
            }

            // Include Prompt Designer data if available (so backend doesn't re-decompose)
            const decomposedData = this._promptEditor?._decomposedData || null;
            const recomposedPrompt = this._promptEditor?._recomposedPrompt || null;

            const payload = {
                prompt: hasComposed ? prompt : userPrompt,
                original_prompt: userPrompt,
                pre_composed: hasComposed || false,
                moderation_original: moderationOriginal || null,
                negative_prompt: composedNegative,
                decomposed_data: decomposedData || undefined,
                recomposed_prompt: recomposedPrompt || undefined,
                vary_fields: this._promptEditor?._varyFlags || undefined,
                all_models: isMultiModel,
                selected_models: isMultiModel ? this._selectedModels : undefined,
                model_optimized_prompts: isMultiModel && (document.getElementById('gen-model-optimized')?.checked || false),
                style_id: this._getStyleId() || null,
                asset_type: this._getAssetType(),
                image_model: this._selectedModels[0] || 'nova_canvas',
                quality: document.getElementById('gen-quality')?.value || null,
                region: document.getElementById('gen-region')?.value || null,
                width: size.w,
                height: size.h,
                num_options: numOptions,
                num_variations: numVariations,
                remove_background: document.getElementById('gen-remove-bg').checked,
                generate_svg: document.getElementById('gen-svg').checked,
                upscale: document.getElementById('gen-upscale').checked,
                ui_lang: (typeof I18n !== 'undefined' ? I18n.getLang() : ''),
                ...this._getIpDeclaration(),
            };

            // Reference-guided overrides: single-concept, single model. "match" routes
            // to the deployed reference edit model; "inspired" uses the selected T2I model.
            if (isReference && referencePatch) {
                payload.reference_images = referencePatch.reference_images;
                payload.reference_mode = referencePatch.reference_mode;
                payload.all_models = false;
                payload.selected_models = undefined;
                payload.num_options = 1;  // reference-guided yields one concept; variations vary the seed
                payload.pre_composed = false;
                payload.decomposed_data = undefined;
                payload.recomposed_prompt = undefined;
                payload.vary_fields = undefined;
                if (referencePatch.reference_mode === 'match') {
                    const refModelKey = this._referenceStudio?._available?.model_key;
                    if (refModelKey) payload.image_model = refModelKey;
                }
            }

            // Immediate visual feedback — show the user something is happening
            const btn = document.getElementById('btn-generate');
            const _resetBtn = () => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> ${t('image_studio.generate')}`;
                }
            };
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<span class="spinner-sm"></span> ${t('image_studio.checking')}`;
            }

            // ── Asset Type Classification (LLM-powered) — only if not already confirmed ─────
            if (window.showConfirm && this._promptEditor && !this._promptEditor._assetTypeConfirmed) {
                try {
                    const classifyResp = await fetch('/api/refine-prompt/classify-asset-type', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: userPrompt, asset_type: payload.asset_type }),
                    });
                    if (classifyResp.ok) {
                        const assetCheck = await classifyResp.json();
                        if (assetCheck.mismatch) {
                            const sugLabel = (assetCheck.suggested || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                            const curLabel = (assetCheck.current || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                            const shouldSwitch = await window.showConfirm(
                                assetCheck.reason,
                                {
                                    title: `Asset Type may not be right`,
                                    detail: `You selected "${curLabel}" but your prompt looks like a "${sugLabel}". The right asset type significantly affects the quality of the generated image.`,
                                    confirmLabel: `Switch to ${sugLabel}`,
                                    cancelLabel: `Keep ${curLabel}`,
                                }
                            );
                            if (shouldSwitch) {
                                const sel = document.getElementById('gen-asset-type');
                                if (sel) { sel.value = assetCheck.suggested; sel.dispatchEvent(new Event('change')); }
                                payload.asset_type = assetCheck.suggested;
                            }
                        }
                    }
                    this._promptEditor._assetTypeConfirmed = true;
                } catch {}
            }

            // ── Prompt Pre-Check (if enabled and not skipped) ─────
            const preCheckOn = document.getElementById('gen-precheck')?.checked && !this._skipPreCheck;
            this._skipPreCheck = false; // Reset flag after reading
            if (preCheckOn) {
                try {
                    window.showLoading?.(t('image_studio.pre_checking'));
                    const screen = await API.preScreen({
                        prompt: prompt,
                        image_model: payload.image_model,
                    });
                    window.hideLoading?.();

                    if (!screen.likely_safe) {
                        _resetBtn();
                        this._showPreCheckDialog(prompt, screen, payload);
                        return;
                    }
                } catch (preErr) {
                    window.hideLoading?.();
                    // Pre-check failed — proceed anyway
                }
            }

            this._setGenerating(true, total, payload);
            this._moderationErrors = [];
            document.getElementById('gen-rewrite-disclaimer')?.classList.add('hidden');
            document.getElementById('gen-cost-breakdown')?.classList.add('hidden');

            // Show cold-start warning for self-hosted async models
            const selectedModelInfo = MODELS.find(m => m.value === payload.image_model);
            if (selectedModelInfo?.model_source === 'custom_hosted') {
                const sub = document.getElementById('gen-loading-sub');
                if (sub) sub.textContent = t('custom_models.cold_start_warning');
            }
            // Unlock upscale toggle for new generation
            const upscaleToggle = document.getElementById('gen-upscale');
            if (upscaleToggle) { upscaleToggle.disabled = false; upscaleToggle.closest('label')?.removeAttribute('title'); }

            let moderationBlocked = false;
            let promptRefused = false;
            let refusalReason = '';

            try {
                const result = await API.generateStream(payload, (evt) => {
                    this._handleProgressEvent(evt, total);
                    // Asset type mismatch suggestion — show toast with guidance
                    if (evt.type === 'asset_type_suggestion') {
                        const sugLabel = (evt.suggested || '').replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
                        window.showToast?.(
                            `Tip: Your prompt describes a ${sugLabel.toLowerCase()}. Consider switching Asset Type to "${sugLabel}" for better results.`,
                            'info', 8000
                        );
                    }
                    // Show the composed/refined prompts in the editor
                    if (evt.type === 'prompts_ready') {
                        if (this._promptEditor) {
                            const prompts = evt.prompts || [];
                            if (prompts.length > 0 && !evt.pre_composed) {
                                // Backend refined the prompt — show it in the composed area
                                this._promptEditor.setComposedText(prompts[0]);
                            }
                            // Show recomposed prompt in Step 2 (read-only flat text)
                            if (evt.recomposed_prompt) {
                                this._promptEditor.setDecomposedText(evt.recomposed_prompt);
                            }
                        }
                        // Capture negative prompt for display after generation
                        if (evt.negative_prompt) {
                            this._lastNegativePrompt = evt.negative_prompt;
                        }
                    }
                    // Track moderation blocks
                    if (evt.type === 'moderation_blocked') {
                        moderationBlocked = true;
                        this._moderationErrors.push(evt.error || t('image_studio.moderation_blocked'));
                    }
                    // Track prompt refusals (Claude declined to refine)
                    if (evt.type === 'prompt_refused') {
                        promptRefused = true;
                        refusalReason = evt.reason || evt.message || t('image_studio.prompt_declined');
                    }
                    if (evt.type === 'image_error' && evt.error) {
                        const errLower = (evt.error || '').toLowerCase();
                        if (errLower.includes('generation failed') || errLower.includes('moderation') || errLower.includes('blocked')) {
                            this._moderationErrors.push(evt.error);
                        }
                    }
                });

                const totalGenerated = (result.options || []).reduce((n, o) => n + (o.variants || []).length, 0);

                // Prompt refusal — Claude declined to process this prompt
                if (promptRefused) {
                    this._result = null;
                    this._showPromptRefusalDialog(prompt, refusalReason);
                }
                // All Models mode — partial results are valid
                else if (result.all_models) {
                    this._result = result;
                    this._selectedOption = 0;
                    this._selectedVariant = 0;
                    this._renderResults(result);

                    // Build summary toast
                    const succeeded = (result.options || []).filter(o => o.status === 'success').length;
                    const blocked = (result.options || []).filter(o => o.status === 'moderation_blocked');
                    const failed = (result.options || []).filter(o => o.status === 'error');
                    const totalModels = (result.options || []).length;

                    if (blocked.length > 0 || failed.length > 0) {
                        const parts = [t('image_studio.models_generated').replace('{{succeeded}}', succeeded).replace('{{total}}', totalModels)];
                        if (blocked.length > 0) {
                            const names = blocked.map(o => o.model_label || t('common.unknown')).join(', ');
                            parts.push(t('image_studio.models_blocked').replace('{{count}}', blocked.length).replace('{{names}}', names));
                        }
                        if (failed.length > 0) parts.push(t('image_studio.models_failed').replace('{{count}}', failed.length));
                        window.showToast?.(parts.join('. ') + '.', succeeded > 0 ? 'warning' : 'error', 8000);
                    } else {
                        window.showToast?.(t('image_studio.all_models_success').replace('{{count}}', totalModels), 'success');
                    }
                }
                // Single-model moderation block
                else if (moderationBlocked || (totalGenerated === 0 && this._moderationErrors.length > 0)) {
                    this._result = null;
                    this._showModerationDialog(prompt, this._moderationErrors[0] || t('image_studio.moderation_blocked'), payload);
                } else if (totalGenerated === 0) {
                    window.showToast?.(t('image_studio.all_failed'), 'error');
                } else {
                    // Render results (full or partial)
                    this._result = result;
                    this._selectedOption = 0;
                    this._selectedVariant = 0;
                    this._renderResults(result);

                    const blocked = result.blocked_count || 0;
                    const costStr = result.total_cost_usd ? ` (Cost: $${result.total_cost_usd.toFixed(4)})` : '';
                    if (blocked > 0) {
                        window.showToast?.(
                            t('image_studio.images_partial').replace('{{generated}}', totalGenerated).replace('{{total}}', totalGenerated + blocked).replace('{{blocked}}', blocked) + costStr,
                            'warning', 10000
                        );
                    } else {
                        window.showToast?.(t('image_studio.images_generated').replace('{{count}}', totalGenerated).replace('{{options}}', (result.options || []).length) + costStr, 'success');
                    }

                    // Show cost breakdown in prompt info section
                    if (result.total_cost_usd > 0) {
                        this._showCostBreakdown(result.total_cost_usd, result.cost_breakdown || {});
                    }
                }
            } catch (err) {
                console.error('Generation error:', err);
                // If we had any moderation errors during the stream, show the dialog
                if (this._moderationErrors.length > 0 || moderationBlocked) {
                    this._showModerationDialog(prompt, this._moderationErrors[0] || t('image_studio.generation_failed'), payload);
                } else {
                    window.showToast?.(err.message || t('image_studio.generation_failed'), 'error');
                }
            } finally {
                this._setGenerating(false);
            }
        },

        async _handlePostProcess() {
            if (!this._result) {
                window.showToast?.(t('image_studio.generate_first'), 'warning');
                return;
            }

            // Collect all variant asset IDs from current results
            const assetIds = [];
            for (const opt of (this._result.options || [])) {
                for (const v of (opt.variants || [])) {
                    assetIds.push(v.id);
                }
            }
            if (assetIds.length === 0) {
                window.showToast?.(t('image_studio.no_images_process'), 'warning');
                return;
            }

            const removeBg = document.getElementById('gen-remove-bg').checked;
            const genSvg = document.getElementById('gen-svg').checked;
            const upscale = document.getElementById('gen-upscale').checked;

            if (!removeBg && !genSvg && !upscale) {
                window.showToast?.(t('image_studio.enable_pp_option'), 'warning');
                return;
            }

            const btn = document.getElementById('btn-apply-postprocess');
            const origHTML = btn.innerHTML;
            btn.innerHTML = `<span class="spinner-sm"></span> ${t('image_studio.processing_btn')}`;
            btn.disabled = true;

            try {
                const result = await API.postProcess({
                    asset_ids: assetIds,
                    remove_background: removeBg,
                    generate_svg: genSvg,
                    upscale: upscale,
                });
                const count = (result.processed || []).length;
                window.showToast?.(t('image_studio.pp_applied').replace('{{count}}', count).replace('{{plural}}', count !== 1 ? 's' : ''), 'success');

                // Refresh the preview to show updated images (cache-bust)
                const img = document.getElementById('gen-result-img');
                if (img && img.src) {
                    img.src = img.src.split('?')[0] + '?t=' + Date.now();
                }
            } catch (err) {
                console.error('Post-process error:', err);
            } finally {
                btn.innerHTML = origHTML;
                btn.disabled = false;
            }
        },

        // ── Moderation Dialog ────────────────────────────────────────

        _moderationErrors: [],

        async _showModerationDialog(originalPrompt, errorMessage, payload) {
            // Remove any existing dialog
            document.getElementById('moderation-dialog')?.remove();

            // Show loading state while AI analyzes
            const dialog = document.createElement('div');
            dialog.id = 'moderation-dialog';
            dialog.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            dialog.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center gap-3 px-6 py-4 border-b border-brand-border bg-amber-950/30">
                        <svg class="w-6 h-6 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                        </svg>
                        <h2 class="text-lg font-semibold text-amber-300">${t('image_studio.content_moderation_issue')}</h2>
                        <button class="mod-close ml-auto p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex-1 overflow-auto p-6" id="mod-content">
                        <div class="flex flex-col items-center justify-center py-8 gap-3 text-brand-text-muted">
                            <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                            <p>${t('image_studio.testing_alternative')}</p>
                            <p class="text-[10px] text-brand-text-muted/50">${t('image_studio.alternative_hint')}</p>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            dialog.querySelector('.mod-close').addEventListener('click', () => dialog.remove());
            dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.remove(); });

            // Call smart moderation — tries alternative models first, rewrites only as last resort
            try {
                const analysis = await API.analyzeModeration({
                    prompt: originalPrompt,
                    error_message: errorMessage,
                    image_model: payload?.image_model || 'nova_canvas',
                    width: 512,
                    height: 512,
                });

                const content = document.getElementById('mod-content');
                if (!content) return;

                const action = analysis.action || 'rewrite';
                const verified = analysis.verified;
                const workingModel = analysis.working_model;
                const workingModelLabel = analysis.working_model_label || workingModel;
                const originalModelLabel = analysis.original_model_label || analysis.original_model;

                // Store attempt history for metadata
                this._moderationAttempts = analysis.attempts || [];

                const ipOwned = payload?.ip_owned;
                const ipLicensed = payload?.ip_licensed;
                const hasIpClaim = ipOwned || ipLicensed;

                if (action === 'switch_model') {
                    // ── Model switch dialog — prompt is fine, just needs a different model ──
                    content.innerHTML = `
                        <div class="space-y-5">
                            <div class="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/20">
                                <div class="flex items-center gap-2 mb-2">
                                    <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                    </svg>
                                    <span class="text-sm font-semibold text-emerald-300">${t('image_studio.prompt_works_with').replace('{{model}}', this._escapeHtml(workingModelLabel))}</span>
                                </div>
                                <p class="text-sm text-brand-text/90 leading-relaxed">${this._escapeHtml(analysis.explanation)}</p>
                            </div>

                            ${hasIpClaim ? `
                            <div class="p-3 rounded-lg bg-brand-accent/10 border border-brand-accent/20 text-xs text-brand-text/80">
                                <strong>${t('image_studio.ip_declaration_noted')}</strong>
                                ${ipOwned ? ' ' + t('image_studio.ip_own_noted') : ''}${ipLicensed ? ' ' + t('image_studio.ip_license_noted') : ''}
                                <br>${t('image_studio.ip_moderation_note').replace('{{model}}', this._escapeHtml(originalModelLabel))}
                            </div>` : ''}

                            <p class="text-xs text-brand-text-muted">${!hasIpClaim ? t('image_studio.prompt_preserved_game') : t('image_studio.prompt_preserved')}</p>

                            ${!hasIpClaim ? `
                            <div class="p-3 rounded-lg bg-brand-bg/40 border border-brand-border space-y-2">
                                <p class="text-[10px] text-brand-text-muted font-medium">${t('image_studio.ip_reference_hint')}</p>
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" id="mod-ip-own" class="rounded border-brand-border bg-brand-bg text-brand-accent">
                                    <span class="text-xs text-brand-text/80">${t('image_studio.ip_own')}</span>
                                </label>
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" id="mod-ip-license" class="rounded border-brand-border bg-brand-bg text-brand-accent">
                                    <span class="text-xs text-brand-text/80">${t('image_studio.ip_license')}</span>
                                </label>
                            </div>` : ''}

                            <div class="flex gap-3 pt-2">
                                <button id="mod-switch-model" class="btn bg-emerald-600 hover:bg-emerald-500 text-white flex-1">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                    </svg>
                                    ${t('image_studio.generate_with').replace('{{model}}', this._escapeHtml(workingModelLabel))}
                                </button>
                                <button id="mod-rewrite-instead" class="btn btn-secondary btn-sm">
                                    ${t('image_studio.rewrite_for').replace('{{model}}', this._escapeHtml(originalModelLabel))}
                                </button>
                            </div>

                            <details class="text-xs">
                                <summary class="text-brand-text-muted cursor-pointer hover:text-brand-text">${t('image_studio.view_model_tests').replace('{{count}}', (analysis.attempts || []).length)}</summary>
                                <div class="mt-2 space-y-1">
                                    ${(analysis.attempts || []).map(a => `
                                        <div class="p-1.5 rounded bg-brand-bg/40 text-[10px] flex items-center gap-2">
                                            <span class="font-mono">${a.model || '?'}</span>
                                            <span class="${a.status === 'passed' ? 'text-emerald-400' : 'text-red-400'}">${a.status}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </details>
                        </div>
                    `;

                    document.getElementById('mod-switch-model')?.addEventListener('click', () => {
                        // Sync IP checkboxes from dialog to sidebar (if declared here)
                        const modIpOwn = document.getElementById('mod-ip-own')?.checked;
                        const modIpLic = document.getElementById('mod-ip-license')?.checked;
                        if (modIpOwn) { const cb = document.getElementById('gen-ip-own'); if (cb) cb.checked = true; }
                        if (modIpLic) { const cb = document.getElementById('gen-ip-license'); if (cb) cb.checked = true; }

                        // Switch model selection and generate
                        this._selectedModels = [workingModel];
                        this._syncModelCheckboxes();
                        if (this._promptEditor) this._promptEditor.setText(originalPrompt);
                        this._promptEditor._moderationOriginal = null;
                        dialog.remove();
                        // Skip pre-check — user already went through moderation dialog and chose this model
                        this._skipPreCheck = true;
                        setTimeout(() => this._handleGenerate(), 100);
                    });

                    document.getElementById('mod-rewrite-instead')?.addEventListener('click', async () => {
                        // User insists on original model — need a rewrite that passes it
                        const content = document.getElementById('mod-content');
                        if (content) {
                            content.innerHTML = `<div class="flex flex-col items-center justify-center py-8 gap-3 text-brand-text-muted">
                                <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                                <p>${t('image_studio.attempting_rewrite').replace('{{model}}', this._escapeHtml(originalModelLabel))}</p>
                                <p class="text-[10px] text-brand-text-muted/50">${t('image_studio.canary_hint')}</p>
                            </div>`;
                        }
                        try {
                            // Force rewrite by pretending all models failed
                            const rewriteResult = await API.analyzeModeration({
                                prompt: originalPrompt,
                                error_message: 'User requested rewrite for ' + analysis.original_model,
                                image_model: analysis.original_model,
                                width: 512,
                                height: 512,
                            });
                            if (rewriteResult.rewritten_prompt) {
                                const verifiedBadge = rewriteResult.verified
                                    ? `<span class="text-[10px] font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">${t('image_studio.passed_canary')}</span>`
                                    : `<span class="text-[10px] font-medium text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full">${t('image_studio.not_verified')}</span>`;
                                const content = document.getElementById('mod-content');
                                if (content) {
                                    content.innerHTML = `<div class="space-y-4">
                                        <div>
                                            <h3 class="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                                ${t('image_studio.rewritten_for').replace('{{model}}', this._escapeHtml(originalModelLabel))} ${verifiedBadge}
                                            </h3>
                                            <textarea id="mod-inline-rewrite" class="input w-full min-h-[100px] text-sm">${this._escapeHtml(rewriteResult.rewritten_prompt)}</textarea>
                                        </div>
                                        <div class="p-3 rounded-lg bg-amber-950/20 border border-amber-500/20">
                                            <p class="text-[10px] text-amber-300/80"><strong>${t('image_studio.best_effort_rewrite')}</strong> ${t('image_studio.rewrite_disclaimer').replace('{{model}}', this._escapeHtml(originalModelLabel))}</p>
                                        </div>
                                        <div class="flex gap-3 pt-2">
                                            <button id="mod-accept-inline-rewrite" class="btn btn-primary flex-1">${t('image_studio.use_rewrite_review')}</button>
                                            <button class="mod-close-btn btn btn-secondary">${t('common.cancel')}</button>
                                        </div>
                                    </div>`;
                                    content.querySelector('#mod-accept-inline-rewrite')?.addEventListener('click', () => {
                                        const edited = document.getElementById('mod-inline-rewrite')?.value?.trim();
                                        if (edited && this._promptEditor) {
                                            this._promptEditor._moderationOriginal = originalPrompt;
                                            this._promptEditor.setComposedText(edited);
                                        }
                                        this._selectedModels = [analysis.original_model];
                                        this._syncModelCheckboxes();
                                        document.getElementById('gen-rewrite-disclaimer')?.classList.remove('hidden');
                                        this._skipPreCheck = true; // Skip pre-check — rewrite IS the moderation fix
                                        dialog.remove();
                                    });
                                    content.querySelector('.mod-close-btn')?.addEventListener('click', () => dialog.remove());
                                }
                            } else {
                                dialog.remove();
                                window.showToast?.(t('image_studio.could_not_rewrite').replace('{{model}}', originalModelLabel), 'warning');
                            }
                        } catch (err) {
                            dialog.remove();
                            window.showToast?.(t('image_studio.rewrite_failed') + ': ' + (err.message || ''), 'error');
                        }
                    });

                } else {
                    // ── Rewrite dialog — all models rejected, need to modify the prompt ──
                    const verifiedBadge = verified
                        ? `<span class="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">${t('image_studio.verified_passed')}</span>`
                        : `<span class="inline-flex items-center gap-1 text-xs font-medium text-red-400 bg-red-400/10 px-2 py-0.5 rounded-full">${t('image_studio.not_verified_may_reject')}</span>`;

                    content.innerHTML = `
                        <div class="space-y-5">
                            <div>
                                <p class="text-sm text-brand-text/90 leading-relaxed">${this._escapeHtml(analysis.explanation || t('image_studio.all_models_rejected'))}</p>
                                <p class="text-xs text-brand-text-muted mt-1">${t('image_studio.attempts_tested').replace('{{count}}', (analysis.attempts || []).length)}</p>
                        </div>

                        ${(analysis.issues || []).length > 0 ? `
                        <div>
                            <h3 class="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">${t('image_studio.issues_detected')}</h3>
                            <ul class="space-y-1.5">
                                ${analysis.issues.map(issue => `
                                    <li class="flex items-start gap-2 text-sm text-brand-text-muted">
                                        <svg class="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01"/>
                                        </svg>
                                        ${this._escapeHtml(issue)}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>` : ''}

                        <div>
                            <h3 class="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                ${t('image_studio.recommended_rewrite')} ${verifiedBadge}
                            </h3>
                            <textarea id="mod-rewritten-prompt" class="input w-full min-h-[120px] text-sm">${this._escapeHtml(analysis.rewritten_prompt || '')}</textarea>
                            <p class="text-[10px] text-brand-text-muted mt-1">${verified ? t('image_studio.rewrite_verified_note') : t('image_studio.rewrite_not_verified_note')} ${t('image_studio.review_edit_note')}</p>
                        </div>

                        <div>
                            <details class="text-xs">
                                <summary class="text-brand-text-muted cursor-pointer hover:text-brand-text">${t('image_studio.view_original_prompt')}</summary>
                                <p class="mt-2 p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._escapeHtml(originalPrompt)}</p>
                            </details>
                        </div>

                        ${(analysis.attempts || []).length > 1 ? `
                        <div>
                            <details class="text-xs">
                                <summary class="text-brand-text-muted cursor-pointer hover:text-brand-text">${t('image_studio.view_rewrite_attempts').replace('{{count}}', analysis.attempts.length)}</summary>
                                <div class="mt-2 space-y-2">
                                    ${(analysis.attempts || []).map((a, i) => `
                                        <div class="p-2 rounded-lg bg-brand-bg/40 border border-brand-border">
                                            <div class="flex items-center gap-2 mb-1">
                                                <span class="text-[10px] font-bold">${t('image_studio.attempt_label').replace('{{num}}', a.attempt)}</span>
                                                <span class="text-[10px] ${a.status === 'passed' ? 'text-emerald-400' : 'text-red-400'}">${a.status}</span>
                                            </div>
                                            <p class="text-[10px] text-brand-text-muted whitespace-pre-wrap">${this._escapeHtml(a.prompt || '').substring(0, 200)}${(a.prompt || '').length > 200 ? '...' : ''}</p>
                                        </div>
                                    `).join('')}
                                </div>
                            </details>
                        </div>` : ''}

                        <div class="flex gap-3 pt-2">
                            <button id="mod-use-rewrite" class="btn btn-primary flex-1">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                </svg>
                                ${t('image_studio.review_rewritten_prompt')}
                            </button>
                            <button id="mod-dismiss" class="btn btn-secondary">
                                ${t('image_studio.edit_manually')}
                            </button>
                        </div>
                    </div>
                `;

                    // Wire up rewrite buttons (inside the else block)
                document.getElementById('mod-use-rewrite')?.addEventListener('click', () => {
                    const rewritten = document.getElementById('mod-rewritten-prompt')?.value?.trim();
                    if (rewritten && this._promptEditor) {
                        this._promptEditor._moderationOriginal = originalPrompt;
                        this._promptEditor.setComposedText(rewritten);
                    }
                    document.getElementById('gen-rewrite-disclaimer')?.classList.remove('hidden');
                    this._skipPreCheck = true; // Skip pre-check — rewrite IS the moderation fix
                    dialog.remove();
                });

                document.getElementById('mod-dismiss')?.addEventListener('click', () => {
                    const rewritten = document.getElementById('mod-rewritten-prompt')?.value?.trim();
                    if (rewritten && this._promptEditor) {
                        this._promptEditor._moderationOriginal = originalPrompt;
                        this._promptEditor.setComposedText(rewritten);
                    }
                    document.getElementById('gen-rewrite-disclaimer')?.classList.remove('hidden');
                    this._skipPreCheck = true; // Skip pre-check — rewrite IS the moderation fix
                    dialog.remove();
                });

                } // end else (rewrite dialog)

            } catch (err) {
                const content = document.getElementById('mod-content');
                if (content) {
                    content.innerHTML = `
                        <div class="text-center py-8">
                            <p class="text-red-400 mb-2">${t('image_studio.analyze_failed')}</p>
                            <p class="text-sm text-brand-text-muted">${t('image_studio.analyze_failed_hint')}</p>
                            <button class="mod-close-btn btn btn-secondary btn-sm mt-4">${t('common.close')}</button>
                        </div>
                    `;
                    content.querySelector('.mod-close-btn')?.addEventListener('click', () => dialog.remove());
                }
            }
        },

        _showPromptRefusalDialog(originalPrompt, reason) {
            document.getElementById('moderation-dialog')?.remove();

            const dialog = document.createElement('div');
            dialog.id = 'moderation-dialog';
            dialog.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            dialog.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center gap-3 px-6 py-4 border-b border-brand-border bg-red-950/30">
                        <svg class="w-6 h-6 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                        </svg>
                        <h2 class="text-lg font-semibold text-red-300">${t('image_studio.prompt_cannot_be_processed')}</h2>
                        <button class="mod-close ml-auto p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex-1 overflow-auto p-6 space-y-4">
                        <p class="text-sm text-brand-text/90 leading-relaxed">${t('image_studio.prompt_declined_reason')}</p>
                        <ul class="space-y-1 text-sm text-brand-text-muted">
                            <li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">•</span> ${t('image_studio.decline_likeness')}</li>
                            <li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">•</span> ${t('image_studio.decline_misinfo')}</li>
                            <li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">•</span> ${t('image_studio.decline_harmful')}</li>
                        </ul>
                        <div class="p-3 rounded-lg bg-brand-bg/60 text-xs text-brand-text-muted">
                            <p class="font-medium mb-1">${t('image_studio.ai_response')}</p>
                            <p class="whitespace-pre-wrap">${this._escapeHtml(reason).substring(0, 500)}</p>
                        </div>
                        <p class="text-xs text-brand-text-muted">${t('image_studio.decline_note')}</p>
                        <div class="flex gap-3 pt-2">
                            <button class="mod-close-btn btn btn-secondary flex-1">${t('image_studio.edit_prompt_btn')}</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            dialog.querySelector('.mod-close')?.addEventListener('click', () => dialog.remove());
            dialog.querySelector('.mod-close-btn')?.addEventListener('click', () => dialog.remove());
            dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.remove(); });
        },

        _showPreCheckDialog(originalPrompt, screen, payload) {
            document.getElementById('moderation-dialog')?.remove();

            const issues = screen.issues || [];
            const suggested = screen.suggested_model;
            const suggestedLabel = screen.suggested_model_label || suggested;
            const currentModel = payload.image_model;
            // Build model labels from the dynamic MODELS array (loaded from registry)
            const modelLabels = {};
            MODELS.forEach(m => { if (m.value !== 'all_models') modelLabels[m.value] = m.label; });
            const currentLabel = modelLabels[currentModel] || currentModel;

            const dialog = document.createElement('div');
            dialog.id = 'moderation-dialog';
            dialog.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
            dialog.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                    <div class="flex items-center gap-3 px-6 py-4 border-b border-brand-border bg-brand-accent/10">
                        <svg class="w-6 h-6 text-brand-accent flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                        </svg>
                        <h2 class="text-lg font-semibold">${t('image_studio.pre_check_title')}</h2>
                        <button class="mod-close ml-auto p-2 rounded-lg hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex-1 overflow-auto p-6 space-y-5">
                        <p class="text-sm text-brand-text/90">${this._escapeHtml(screen.explanation || '')}</p>

                        ${issues.length > 0 ? `
                        <div>
                            <h3 class="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">${t('image_studio.potential_issues')}</h3>
                            <ul class="space-y-1">
                                ${issues.map(i => `<li class="flex items-start gap-2 text-sm text-brand-text-muted">
                                    <span class="text-amber-400 mt-0.5">•</span> ${this._escapeHtml(i)}
                                </li>`).join('')}
                            </ul>
                        </div>` : ''}

                        ${suggested ? `
                        <div class="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/20">
                            <p class="text-sm text-emerald-300 font-medium mb-1">${t('image_studio.recommended_switch').replace('{{model}}', this._escapeHtml(suggestedLabel))}</p>
                            <p class="text-xs text-brand-text-muted">${t('image_studio.prompt_works_as_is')}</p>
                        </div>` : ''}

                        <div class="flex flex-wrap gap-3 pt-2">
                            ${suggested ? `
                            <button id="precheck-switch" class="btn bg-emerald-600 hover:bg-emerald-500 text-white flex-1">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                </svg>
                                ${t('image_studio.generate_with').replace('{{model}}', this._escapeHtml(suggestedLabel))}
                            </button>` : ''}
                            <button id="precheck-rewrite" class="btn bg-amber-600 hover:bg-amber-500 text-white">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                </svg>
                                ${t('image_studio.rewrite_for').replace('{{model}}', this._escapeHtml(currentLabel))}
                            </button>
                            <button id="precheck-proceed" class="btn btn-secondary">
                                ${t('image_studio.try_anyway').replace('{{model}}', this._escapeHtml(currentLabel))}
                            </button>
                            <button id="precheck-cancel" class="btn btn-secondary btn-sm">
                                ${t('common.cancel')}
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(dialog);
            dialog.querySelector('.mod-close')?.addEventListener('click', () => dialog.remove());
            dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.remove(); });
            document.getElementById('precheck-cancel')?.addEventListener('click', () => dialog.remove());

            // Switch model and generate
            document.getElementById('precheck-switch')?.addEventListener('click', () => {
                if (suggested) { this._selectedModels = [suggested]; this._syncModelCheckboxes(); }
                dialog.remove();
                // Skip pre-check for this generation — user already reviewed and chose the model
                this._skipPreCheck = true;
                this._handleGenerate();
            });

            // Proceed with original model anyway (skip pre-check this time)
            document.getElementById('precheck-proceed')?.addEventListener('click', () => {
                dialog.remove();
                this._skipPreCheck = true;
                this._handleGenerate();
            });

            // Rewrite prompt for the current model
            document.getElementById('precheck-rewrite')?.addEventListener('click', async () => {
                const content = dialog.querySelector('.flex-1.overflow-auto');
                if (content) {
                    content.innerHTML = `<div class="flex flex-col items-center justify-center py-8 gap-3 text-brand-text-muted">
                        <div class="loading-spinner w-5 h-5 border-2 border-brand-accent/20 border-t-brand-accent rounded-full"></div>
                        <p>${t('image_studio.attempting_rewrite').replace('{{model}}', this._escapeHtml(currentLabel))}</p>
                        <p class="text-[10px] text-brand-text-muted/50">${t('image_studio.canary_hint')}</p>
                    </div>`;
                }
                try {
                    const rewriteResult = await API.analyzeModeration({
                        prompt: originalPrompt,
                        error_message: 'Pre-check flagged: ' + (issues.join(', ') || screen.explanation || 'potential moderation issue'),
                        image_model: currentModel,
                        width: 512,
                        height: 512,
                        force_rewrite: true,
                    });
                    if (rewriteResult.rewritten_prompt) {
                        const verifiedBadge = rewriteResult.verified
                            ? `<span class="text-[10px] font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">${t('image_studio.passed_canary')}</span>`
                            : `<span class="text-[10px] font-medium text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full">${t('image_studio.not_verified')}</span>`;

                        if (content) {
                            content.innerHTML = `<div class="space-y-4">
                                <div>
                                    <h3 class="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                        ${t('image_studio.rewritten_prompt')} ${verifiedBadge}
                                    </h3>
                                    <textarea id="precheck-rewritten-text" class="input w-full min-h-[100px] text-sm">${this._escapeHtml(rewriteResult.rewritten_prompt)}</textarea>
                                </div>
                                <div class="p-3 rounded-lg bg-amber-950/20 border border-amber-500/20">
                                    <p class="text-[10px] text-amber-300/80"><strong>${t('image_studio.best_effort_rewrite')}</strong> ${t('image_studio.rewrite_not_guaranteed').replace('{{model}}', this._escapeHtml(currentLabel))}</p>
                                </div>
                                <details class="text-xs">
                                    <summary class="text-brand-text-muted cursor-pointer hover:text-brand-text">${t('image_studio.view_original_prompt')}</summary>
                                    <p class="mt-2 p-3 rounded-lg bg-brand-bg/60 whitespace-pre-wrap text-brand-text-muted">${this._escapeHtml(originalPrompt)}</p>
                                </details>
                                <div class="flex gap-3 pt-2">
                                    <button id="precheck-accept-rewrite" class="btn btn-primary flex-1">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4"/>
                                        </svg>
                                        ${t('image_studio.use_rewrite_review')}
                                    </button>
                                    <button class="mod-close-btn btn btn-secondary">${t('common.cancel')}</button>
                                </div>
                            </div>`;

                            content.querySelector('#precheck-accept-rewrite')?.addEventListener('click', () => {
                                const editedRewrite = document.getElementById('precheck-rewritten-text')?.value?.trim();
                                if (editedRewrite && this._promptEditor) {
                                    this._promptEditor.setComposedText(editedRewrite);
                                    this._promptEditor._moderationOriginal = originalPrompt;
                                }
                                document.getElementById('gen-rewrite-disclaimer')?.classList.remove('hidden');
                                this._skipPreCheck = true; // Skip pre-check — rewrite IS the moderation fix
                                dialog.remove();
                            });
                            content.querySelector('.mod-close-btn')?.addEventListener('click', () => dialog.remove());
                        }
                    } else {
                        if (content) {
                            const explanation = rewriteResult.explanation || t('image_studio.rewrite_unavailable');
                            content.innerHTML = `<div class="p-4 text-center space-y-3">
                                <p class="text-sm text-red-300">${this._escapeHtml(explanation)}</p>
                                <p class="text-xs text-brand-text-muted">${t('image_studio.retry_hint')}</p>
                                <button class="mod-close-btn btn btn-secondary">${t('common.close')}</button>
                            </div>`;
                            content.querySelector('.mod-close-btn')?.addEventListener('click', () => dialog.remove());
                        }
                    }
                } catch (err) {
                    window.showToast?.(t('image_studio.rewrite_failed') + ': ' + (err.message || ''), 'error');
                    dialog.remove();
                }
            });
        },

        _progressTimer: null,

        _setGenerating(on, total, payload) {
            this._generating = on;
            const btn = document.getElementById('btn-generate');
            const loadingEl = document.getElementById('gen-loading');
            const loadingText = document.getElementById('gen-loading-text');
            const loadingSub = document.getElementById('gen-loading-sub');
            const progressBar = document.getElementById('gen-progress-bar');
            const elapsed = document.getElementById('gen-loading-elapsed');
            const placeholder = document.getElementById('gen-placeholder');

            if (on) {
                btn.disabled = true;
                btn.innerHTML = `<span class="spinner-sm"></span> ${t('image_studio.generating')}`;
                loadingEl?.classList.remove('hidden');
                placeholder?.classList.add('hidden');
                document.getElementById('gen-result-img')?.classList.add('hidden');
                document.getElementById('gen-download-bar')?.classList.add('hidden');
                document.getElementById('gen-options-section')?.classList.add('hidden');
                document.getElementById('gen-variations-section')?.classList.add('hidden');
                document.getElementById('gen-concept-prompt')?.classList.add('hidden');
                document.getElementById('gen-prompt-info')?.classList.add('hidden');

                // Start progress simulation
                this._startProgress(total, payload);
            } else {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    ${t('image_studio.generate')}`;
                loadingEl?.classList.add('hidden');
                this._stopProgress();
            }
        },

        _startProgress(total, payload) {
            this._stopProgress();

            const elapsedEl = document.getElementById('gen-loading-elapsed');
            const text = document.getElementById('gen-loading-text');
            const sub = document.getElementById('gen-loading-sub');
            const bar = document.getElementById('gen-progress-bar');
            const startTime = Date.now();

            if (text) text.textContent = t('image_studio.starting');
            if (sub) sub.textContent = t('image_studio.images_queued').replace('{{count}}', total).replace('{{plural}}', total > 1 ? 's' : '');
            if (bar) bar.style.width = '2%';

            // Elapsed timer
            const tick = setInterval(() => {
                const secs = Math.floor((Date.now() - startTime) / 1000);
                const min = Math.floor(secs / 60);
                const sec = secs % 60;
                if (elapsedEl) elapsedEl.textContent = min > 0 ? t('image_studio.elapsed_min').replace('{{min}}', min).replace('{{sec}}', sec) : t('image_studio.elapsed_sec').replace('{{sec}}', sec);
            }, 1000);

            this._progressTimer = { tick };
        },

        _stopProgress() {
            if (this._progressTimer) {
                clearInterval(this._progressTimer.tick);
                this._progressTimer = null;
            }
        },

        _handleProgressEvent(evt, total) {
            const text = document.getElementById('gen-loading-text');
            const sub = document.getElementById('gen-loading-sub');
            const bar = document.getElementById('gen-progress-bar');

            switch (evt.type) {
                case 'started':
                    if (text) text.textContent = t('image_studio.starting_generation');
                    if (bar) bar.style.width = '5%';
                    break;

                case 'stage':
                    if (text) text.textContent = evt.message || evt.stage;
                    if (evt.stage === 'prompts') {
                        if (sub) sub.textContent = t('image_studio.creating_concepts');
                        if (bar) bar.style.width = '10%';
                    } else if (evt.stage === 'generating') {
                        if (sub) sub.textContent = t('image_studio.concepts_ready').replace('{{count}}', evt.prompts_done || '').replace('{{plural}}', (evt.prompts_done || 0) > 1 ? 's' : '');
                        if (bar) bar.style.width = '20%';
                    } else if (evt.stage === 'finalizing') {
                        if (sub) sub.textContent = t('image_studio.saving_assets');
                        if (bar) bar.style.width = '95%';
                    }
                    break;

                case 'image_done': {
                    const done = evt.completed || 0;
                    const tot = evt.total || total;
                    const pct = 20 + Math.round((done / tot) * 70);
                    if (text) text.textContent = t('image_studio.generating_images').replace('{{done}}', done).replace('{{total}}', tot);
                    if (sub) sub.textContent = t('image_studio.option_variation_complete').replace('{{opt}}', (evt.option || 0) + 1).replace('{{var}}', (evt.variation || 0) + 1);
                    if (bar) bar.style.width = Math.min(pct, 92) + '%';
                    break;
                }

                case 'async_submitted': {
                    const done = evt.completed || 0;
                    const tot = evt.total || total;
                    const pct = 20 + Math.round((done / tot) * 70);
                    if (text) text.textContent = t('custom_models.async_submitted').replace('{{model}}', evt.model_label);
                    if (sub) sub.textContent = t('custom_models.async_submitted_hint');
                    if (bar) bar.style.width = Math.min(pct, 92) + '%';
                    // Show the pending jobs button immediately with count
                    const pendBtn = document.getElementById('btn-pending-jobs');
                    const pendLabel = document.getElementById('pending-jobs-label');
                    if (pendBtn) {
                        pendBtn.classList.remove('hidden');
                        if (pendLabel) {
                            const remaining = tot - done;
                            pendLabel.textContent = t('custom_models.pending_jobs_count').replace('{{count}}', remaining);
                        }
                    }
                    this._startAsyncPolling();
                    // Trigger first poll immediately (don't wait 5s)
                    this._checkAsyncJobs();
                    break;
                }

                case 'image_error': {
                    const done = evt.completed || 0;
                    const tot = evt.total || total;
                    if (sub) sub.textContent = t('image_studio.option_variation_failed').replace('{{opt}}', (evt.option || 0) + 1).replace('{{var}}', (evt.variation || 0) + 1);
                    break;
                }

                case 'throttled': {
                    if (text) text.textContent = t('image_studio.api_throttled');
                    if (sub) sub.textContent = t('image_studio.option_variation_waiting').replace('{{opt}}', (evt.option || 0) + 1).replace('{{var}}', (evt.variation || 0) + 1).replace('{{delay}}', evt.delay || '?');
                    break;
                }

                case 'retry': {
                    if (text) text.textContent = t('image_studio.retrying').replace('{{attempt}}', evt.attempt || '?').replace('{{max}}', evt.max_retries || '?');
                    if (sub) sub.textContent = `${t('image_studio.option')} ${(evt.option || 0) + 1}, ${t('image_studio.variation')} ${(evt.variation || 0) + 1}`;
                    break;
                }

                case 'canary':
                    if (text) text.textContent = evt.message || t('image_studio.testing_prompt');
                    if (sub) sub.textContent = t('image_studio.verifying_moderation');
                    if (bar) bar.style.width = '15%';
                    break;

                case 'moderation_blocked':
                    if (text) text.textContent = t('image_studio.moderation_blocked');
                    if (sub) sub.textContent = evt.message || t('image_studio.moderation_stopping');
                    if (bar) bar.style.width = '100%';
                    // Track for the dialog
                    this._moderationErrors.push(evt.error || 'Content moderation blocked');
                    break;

                case 'prompt_refused':
                    if (text) text.textContent = t('image_studio.prompt_cannot_process');
                    if (sub) sub.textContent = evt.message || t('image_studio.prompt_declined');
                    if (bar) bar.style.width = '100%';
                    break;

                case 'complete':
                    if (bar) bar.style.width = '100%';
                    if (text) text.textContent = t('image_studio.done');
                    break;
            }
        },

        // ── Render Results ──────────────────────────────────────────

        _renderResults(result) {
            const options = result.options || [];

            // Switch to "Post-Processing" mode now that results exist
            const labelEl = document.getElementById('gen-processing-label');
            if (labelEl) labelEl.textContent = t('image_studio.post_processing');
            document.getElementById('btn-apply-postprocess')?.classList.remove('hidden');
            document.getElementById('pp-hint')?.classList.remove('hidden');

            // Show prompt sent to model + negative prompt
            // Original prompt is already in Step 1 — no need to repeat here.
            // The per-option prompt updates when user selects an option (in _selectOption).
            const infoSection = document.getElementById('gen-prompt-info');
            const origSection = document.getElementById('gen-original-prompt-section');
            const usedText = document.getElementById('gen-used-prompt-text');
            if (infoSection) {
                infoSection.classList.remove('hidden');
                origSection?.classList.add('hidden');  // Step 1 already shows original
                // Prompt + negative are updated per-option in _selectOption
            }
            const negSection = document.getElementById('gen-negative-prompt-section');
            if (negSection) negSection.classList.remove('hidden');

            // Show options row
            this._renderOptionsRow(options);

            // Select first option, first variant
            this._selectOption(0);
        },

        _renderOptionsRow(options) {
            const section = document.getElementById('gen-options-section');
            const grid = document.getElementById('gen-options-grid');
            const countEl = document.getElementById('gen-options-count');
            if (!section || !grid) return;

            const isAllModels = this._result?.all_models;
            const optsPerModel = this._result?.all_models_summary?.options_per_model || 1;

            if (options.length <= 1 && !isAllModels) {
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');

            const header = document.getElementById('gen-options-header');
            if (header) {
                header.textContent = isAllModels
                    ? t('image_studio.models_header')
                    : t('image_studio.options_header');
            }
            if (countEl) {
                const totalImages = options.reduce((s, o) => s + (o.variants?.length || 0), 0);
                countEl.textContent = isAllModels
                    ? `${totalImages} images across ${new Set(options.map(o => o.image_model)).size} models`
                    : `${options.length} ${t('image_studio.num_options').toLowerCase()}`;
            }

            // Grouped layout: when All Models with multiple options per model
            const useGrouped = isAllModels && optsPerModel > 1;

            if (useGrouped) {
                // Group options by model — 1 card per option (first variant thumbnail)
                const groups = new Map();
                options.forEach((opt, i) => {
                    const mk = opt.image_model || 'unknown';
                    if (!groups.has(mk)) groups.set(mk, []);
                    groups.get(mk).push({ opt, globalIdx: i });
                });

                let html = '';
                for (const [mk, entries] of groups) {
                    const label = entries[0].opt.model_label || mk;
                    const succCount = entries.filter(e => e.opt.status === 'success').length;
                    const totalCount = entries.length;
                    const statusBadge = succCount === totalCount
                        ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">${succCount}/${totalCount}</span>`
                        : `<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">${succCount}/${totalCount}</span>`;

                    const cols = Math.min(entries.length, 5);
                    html += `<div class="mb-4">
                        <div class="flex items-center gap-2 mb-2">
                            <h4 class="text-xs font-semibold text-brand-text">${this._escapeHtml(label)}</h4>
                            ${statusBadge}
                        </div>
                        <div class="grid gap-2 grid-cols-${cols}">`;

                    entries.forEach((e, conceptIdx) => {
                        html += this._renderOptionCard(e.opt, e.globalIdx, `o${e.globalIdx + 1} · Concept ${conceptIdx + 1}`);
                    });

                    html += '</div></div>';
                }
                grid.className = '';
                grid.innerHTML = html;
            } else {
                // Flat layout (single-model or All Models with 1 option each)
                const cols = options.length <= 5 ? options.length : 5;
                grid.className = `grid gap-3 grid-cols-${cols}`;
                grid.innerHTML = options.map((opt, i) => {
                    const modelPart = opt.model_label || `${t('image_studio.option')} ${i + 1}`;
                    const cardLabel = `o${i + 1} · ${modelPart}`;
                    return this._renderOptionCard(opt, i, cardLabel);
                }).join('');
            }

            grid.querySelectorAll('.option-card').forEach(btn => {
                btn.addEventListener('click', () => {
                    this._selectOption(parseInt(btn.dataset.optionIndex, 10));
                });
            });
        },

        _renderOptionCard(opt, index, label) {
            const thumb = opt.variants?.[0];
            const thumbSrc = thumb ? thumb.png_path : '';
            const isAsync = thumb?.async_job || (opt.variants || []).some(v => v.async_job);
            const asyncJobId = thumb?.async_job?.job_id || '';
            const asyncAssetId = thumb?.id || '';
            const isSelected = index === (this._selectedOption || 0);
            return `
                <button
                    class="option-card group relative rounded-xl overflow-hidden border-2 transition-all duration-200 cursor-pointer
                           ${isSelected ? 'border-brand-accent ring-2 ring-brand-accent/40 shadow-lg shadow-brand-accent/20' : 'border-brand-border hover:border-brand-accent/50'}"
                    data-option-index="${index}" ${isAsync ? `data-async-job="${asyncJobId}" data-async-asset="${asyncAssetId}"` : ''}
                >
                    <div class="aspect-square bg-brand-bg async-thumb-container">
                        ${thumbSrc
                            ? `<img src="${thumbSrc}" alt="${label}" class="w-full h-full object-cover" loading="lazy" />`
                            : isAsync
                            ? `<div class="async-placeholder w-full h-full flex flex-col items-center justify-center text-cyan-400/50 text-xs gap-2"><svg class="w-6 h-6 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><span>Generating...</span></div>`
                            : `<div class="w-full h-full flex items-center justify-center text-brand-text-muted/30 text-xs">${t('image_studio.no_image')}</div>`
                        }
                    </div>
                    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors"></div>
                    <div class="absolute top-1.5 left-1.5 bg-black/70 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                        ${this._escapeHtml(label)}
                    </div>
                    ${opt.status === 'moderation_blocked' || opt.status === 'error' || opt.status === 'failed' ? `
                    <div class="absolute inset-0 bg-black/60 flex items-center justify-center">
                        <span class="px-2 py-1 rounded text-xs font-semibold ${opt.status === 'moderation_blocked' ? 'bg-amber-500/80 text-amber-950' : 'bg-red-500/80 text-white'}">
                            ${opt.status === 'moderation_blocked' ? t('image_studio.blocked_moderation') : t('image_studio.failed')}
                        </span>
                    </div>` : ''}
                    <div class="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 to-transparent p-2 pt-6">
                        <p class="text-white text-[10px] leading-tight line-clamp-2">${this._escapeHtml(opt.enhanced_prompt || '').substring(0, 80)}...</p>
                    </div>
                </button>
            `;
        },

        _selectOption(index) {
            const result = this._result;
            if (!result) return;
            const options = result.options || [];
            const option = options[index];
            if (!option) return;

            this._selectedOption = index;
            this._selectedVariant = 0;

            // Update option highlight
            const grid = document.getElementById('gen-options-grid');
            if (grid) {
                grid.querySelectorAll('.option-card').forEach((btn, i) => {
                    if (i === index) {
                        btn.classList.remove('border-brand-border');
                        btn.classList.add('border-brand-accent', 'ring-2', 'ring-brand-accent/40', 'shadow-lg', 'shadow-brand-accent/20');
                    } else {
                        btn.classList.remove('border-brand-accent', 'ring-2', 'ring-brand-accent/40', 'shadow-lg', 'shadow-brand-accent/20');
                        btn.classList.add('border-brand-border');
                    }
                });
            }

            // Show per-option prompt with label
            // Per-option prompt is shown in the main gen-prompt-info panel (updated above).
            // Hide the legacy concept-prompt section to avoid duplication.
            const conceptSection = document.getElementById('gen-concept-prompt');
            if (conceptSection) conceptSection.classList.add('hidden');

            // Update the main prompt info panel to match selected option
            const usedText = document.getElementById('gen-used-prompt-text');
            const usedLabel = document.querySelector('#gen-used-prompt-section > p:first-child');
            if (usedText) {
                usedText.textContent = option.enhanced_prompt || result.enhanced_prompt || result.refined_prompt || result.prompt || '';
            }
            if (usedLabel) {
                const modelPart = option.model_label || `${t('image_studio.option')} ${index + 1}`;
                usedLabel.textContent = `${t('image_studio.prompt_sent_to_model')} \u2014 o${index + 1} · ${modelPart}`;
            }
            const negText = document.getElementById('gen-negative-prompt-text');
            const negLabel = document.querySelector('#gen-negative-prompt-section > p:first-child');
            if (negText) {
                negText.textContent = option.negative_prompt || t('image_studio.negative_prompt_none');
            }
            if (negLabel) {
                const modelPart = option.model_label || `${t('image_studio.option')} ${index + 1}`;
                negLabel.textContent = `${t('image_studio.negative_prompt_exclusions')} \u2014 o${index + 1} · ${modelPart}`;
            }

            // Render variations for this option
            this._renderVariationsRow(option.variants || []);
            this._selectVariant(0);

            // Scroll down to the preview area
            document.getElementById('gen-preview')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        },

        _renderVariationsRow(variants) {
            const section = document.getElementById('gen-variations-section');
            const grid = document.getElementById('gen-variations-grid');
            const countEl = document.getElementById('gen-variations-count');
            if (!section || !grid) return;

            if (variants.length <= 1) {
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');
            if (countEl) countEl.textContent = `${variants.length} ${t('image_studio.num_variations').toLowerCase()}`;

            grid.className = `grid gap-3 grid-cols-${Math.min(variants.length, 5)}`;

            grid.innerHTML = variants.map((v, i) => {
                const isAsync = v.async_job && !v.png_path;
                const vAsyncJobId = v.async_job?.job_id || '';
                const vAsyncAssetId = v.id || '';
                return `
                <button
                    class="variant-thumb group relative aspect-square rounded-lg overflow-hidden border-2 transition-all duration-200 cursor-pointer
                           ${i === 0 ? 'border-emerald-400 ring-2 ring-emerald-400/30' : 'border-brand-border hover:border-emerald-400/50'}"
                    data-variant-index="${i}" ${isAsync ? `data-async-job="${vAsyncJobId}" data-async-asset="${vAsyncAssetId}"` : ''}
                >
                    ${isAsync
                        ? `<div class="async-placeholder w-full h-full flex flex-col items-center justify-center bg-brand-bg text-cyan-400/50 text-[10px] gap-1"><svg class="w-5 h-5 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Generating</div>`
                        : v.png_path
                        ? `<img src="${v.png_path}" alt="${t('image_studio.variation')} ${i + 1}" class="w-full h-full object-cover" loading="lazy" />`
                        : `<div class="w-full h-full flex items-center justify-center bg-brand-bg text-brand-text-muted/30 text-xs">${t('image_studio.no_image')}</div>`
                    }
                    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors"></div>
                    <span class="absolute bottom-1 right-1 text-[10px] font-bold bg-black/60 text-white px-1.5 py-0.5 rounded">
                        v${i + 1}
                    </span>
                </button>`;
            }).join('');

            grid.querySelectorAll('.variant-thumb').forEach(btn => {
                btn.addEventListener('click', () => {
                    this._selectVariant(parseInt(btn.dataset.variantIndex, 10));
                });
            });
        },

        _selectVariant(index) {
            const result = this._result;
            if (!result) return;
            const option = (result.options || [])[this._selectedOption];
            if (!option) return;
            const variants = option.variants || [];
            const variant = variants[index];
            if (!variant) return;

            this._selectedVariant = index;

            // Update variation highlight
            const grid = document.getElementById('gen-variations-grid');
            if (grid) {
                grid.querySelectorAll('.variant-thumb').forEach((btn, i) => {
                    if (i === index) {
                        btn.classList.remove('border-brand-border');
                        btn.classList.add('border-emerald-400', 'ring-2', 'ring-emerald-400/30');
                    } else {
                        btn.classList.remove('border-emerald-400', 'ring-2', 'ring-emerald-400/30');
                        btn.classList.add('border-brand-border');
                    }
                });
            }

            // Update main preview
            const img = document.getElementById('gen-result-img');
            const placeholder = document.getElementById('gen-placeholder');
            const downloadBar = document.getElementById('gen-download-bar');

            const isAsync = variant.async_job && !variant.png_path;
            if (isAsync) {
                // Async job still pending — show generating indicator in main preview
                img?.classList.add('hidden');
                if (placeholder) {
                    placeholder.classList.remove('hidden');
                    placeholder.innerHTML = `
                        <div class="flex flex-col items-center justify-center gap-3 py-12 text-cyan-400/60">
                            <div class="w-10 h-10 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin"></div>
                            <span class="text-sm font-medium">Generating with ${variant.model_label || 'custom model'}...</span>
                            <span class="text-[10px] text-brand-text-muted/50">Image will appear automatically when ready</span>
                        </div>`;
                }
            } else if (variant.png_path) {
                img.src = variant.png_path;
                img.classList.remove('hidden');
                placeholder?.classList.add('hidden');
            } else {
                img?.classList.add('hidden');
                placeholder?.classList.remove('hidden');
            }

            if (downloadBar) {
                downloadBar.classList.toggle('hidden', isAsync || !variant.png_path);
                const info = document.getElementById('gen-result-info');
                if (info) {
                    // Show the filename as the label
                    info.textContent = variant.png_filename || variant.id;
                }
                const dlPng = document.getElementById('dl-png');
                const dlSvg = document.getElementById('dl-svg');
                if (dlPng) {
                    dlPng.href = variant.png_path;
                    dlPng.setAttribute('download', variant.png_filename || 'asset.png');
                }
                if (dlSvg) {
                    if (variant.svg_path) {
                        dlSvg.href = variant.svg_path;
                        dlSvg.setAttribute('download', variant.svg_filename || 'asset.svg');
                        dlSvg.classList.remove('hidden');
                    } else {
                        dlSvg.classList.add('hidden');
                    }
                }
            }
        },

        // ── Load batch from Gallery ──────────────────────────────────

        async loadBatch(batchId) {
            window.showLoading?.(t('image_studio.loading_batch'));

            // Navigate to image-studio and wait for the view to be fully ready.
            // Setting the hash triggers navigate() via hashchange, but navigate()
            // is async (may need to render + init the view). We need to ensure
            // the DOM is fully built before we write batch data into it.
            window.location.hash = '#image-studio';

            // Clear old result BEFORE navigating — prevents onShow from re-rendering stale data
            this._result = null;

            // Yield to let the hashchange event fire and navigate() start
            await new Promise(r => setTimeout(r, 0));

            // Wait until the view's DOM is actually ready — poll for a known
            // element that only exists after render() + init() complete.
            const maxWait = 10000;
            const start = Date.now();
            while (!document.getElementById('gen-preview') && (Date.now() - start) < maxWait) {
                await new Promise(r => setTimeout(r, 100));
            }

            // Extra yield to let any pending init() / onShow() finish
            await new Promise(r => setTimeout(r, 200));

            try {
                const result = await API.gallery.getBatch(batchId);
                this._result = result;
                this._selectedOption = 0;
                this._selectedVariant = 0;

                // Ensure prompt editor exists, then populate
                this._ensurePromptEditor();
                if (this._promptEditor) {
                    // Step 1: original user prompt
                    const originalPrompt = result.original_prompt || result.prompt || '';
                    this._promptEditor.setText(originalPrompt);
                    this._promptEditor._originalText = originalPrompt;

                    // Step 3: AI-enhanced prompt
                    const enhancedPrompt = result.enhanced_prompt || '';
                    if (enhancedPrompt) {
                        this._promptEditor.setComposedText(enhancedPrompt);
                        this._promptEditor._negativePrompt = result.negative_prompt || '';
                    }

                    // Restore decomposed data from metadata, or clear stale state
                    if (result.decomposed_data) {
                        this._promptEditor._decomposedData = result.decomposed_data;
                    } else {
                        this._promptEditor._decomposedData = null;
                    }
                    if (result.recomposed_prompt) {
                        this._promptEditor.setDecomposedText(result.recomposed_prompt);
                    } else {
                        this._promptEditor.setDecomposedText('');
                        const panel = this._promptEditor.container?.querySelector('.decomposed-panel');
                        if (panel) panel.classList.add('hidden');
                    }

                    // Asset type was already set for this generation — skip re-classification
                    this._promptEditor._assetTypeConfirmed = true;
                    // Mark as gallery reload — Designer shows saved data or "no data" message
                    this._promptEditor._galleryReload = !result.decomposed_data;
                }

                // Restore model selection from batch metadata
                if (result.all_models && result.model_map) {
                    const usedModels = [...new Set(Object.values(result.model_map))];
                    this._selectedModels = usedModels.length ? usedModels : [result.image_model || MODELS[0]?.value].filter(Boolean);
                } else if (result.image_model) {
                    this._selectedModels = [result.image_model];
                }
                this._syncModelCheckboxes();

                // Set sidebar controls to match the batch settings
                const styleSel = document.getElementById('gen-style');
                if (styleSel) styleSel.value = result.style_id || '';

                const typeSel = document.getElementById('gen-asset-type');
                if (typeSel && result.asset_type) typeSel.value = result.asset_type;

                // Model selector is restored above (handles all_models + deleted endpoints)

                // Restore dimension preset
                const sizeSel = document.getElementById('gen-size');
                if (sizeSel && result.width && result.height) {
                    const sizeStr = `${result.width} x ${result.height}`;
                    for (let i = 0; i < sizeSel.options.length; i++) {
                        if (sizeSel.options[i].text === sizeStr) {
                            sizeSel.value = i;
                            break;
                        }
                    }
                }

                // Restore toggle switches
                const removeBg = document.getElementById('gen-remove-bg');
                if (removeBg) removeBg.checked = result.remove_background ?? false;

                const genSvg = document.getElementById('gen-svg');
                if (genSvg) genSvg.checked = result.generate_svg ?? false;

                const upscale = document.getElementById('gen-upscale');
                if (upscale) {
                    upscale.checked = result.upscale ?? false;
                    // If images were already upscaled, lock the toggle
                    if (result.upscale) {
                        upscale.disabled = true;
                        upscale.closest('label')?.setAttribute('title', t('image_studio.already_upscaled'));
                    }
                }

                // Restore options/variations counts
                const optsSel = document.getElementById('gen-num-options');
                if (optsSel && result.num_options) optsSel.value = result.num_options;

                const varsSel = document.getElementById('gen-num-variations');
                if (varsSel && result.num_variations) varsSel.value = result.num_variations;

                // Render the results
                this._renderResults(result);

                window.hideLoading?.();

                // Inform user about batch state — full or partial
                const surviving = result.batch_surviving_count || 0;
                const originalTotal = result.batch_original_total || 0;
                const deletedCount = result.batch_deleted_count || 0;
                if (deletedCount > 0 && originalTotal > 0) {
                    window.showToast?.(
                        t('image_studio.batch_loaded_partial').replace('{{surviving}}', surviving).replace('{{total}}', originalTotal).replace('{{deleted}}', deletedCount),
                        'info', 6000
                    );
                } else {
                    window.showToast?.(
                        t('image_studio.batch_loaded').replace('{{options}}', result.num_options).replace('{{variations}}', result.num_variations),
                        'success'
                    );
                }
            } catch (err) {
                window.hideLoading?.();
                console.error('Failed to load batch:', err);
            }
        },

        // ── Helpers ─────────────────────────────────────────────────

        _getStyleId() {
            return document.getElementById('gen-style')?.value || '';
        },
        _getAssetType() {
            return document.getElementById('gen-asset-type')?.value || 'photorealistic';
        },

        _checkAssetTypeMismatch(prompt, assetType) {
            if (assetType !== 'game_asset') return null;
            const lower = prompt.toLowerCase();
            const charWords = ['character','warrior','knight','archer','mage','wizard','witch','pirate',
                'captain','soldier','sailor','pilot','merchant','hunter','king','queen','prince','princess',
                'hero','heroine','female','male','woman','man','girl','boy','lady','lord','young','old',
                'wearing','holding','wielding','standing','sitting','running','fighting','armor','cloak',
                'robe','dress','uniform','sword','bow','staff','shield','weapon','hair','eyes','portrait','pose'];
            const sceneWords = ['scene','landscape','environment','background','cinematic','village','city',
                'forest','ocean','sea','mountain','desert','beach','castle','temple','harbor','sunset',
                'sunrise','sky','clouds','rain','storm','on a ship','on a boat','on a horse','on a dragon',
                'on a throne','on deck','standing in','walking through','sitting on','riding','sailing',
                'behind the','in front of','surrounded by','in the distance'];
            const charHits = charWords.filter(w => lower.includes(w)).length;
            const sceneHits = sceneWords.filter(w => lower.includes(w)).length;
            if (charHits >= 2 && sceneHits >= 1) {
                return { current: 'game_asset', suggested: 'character',
                    reason: "Your prompt describes a character in a setting. 'Character' type keeps the figure as the focal point while preserving scene context. 'Game Asset' forces an isolated sprite on a transparent background." };
            }
            if (charHits >= 2) {
                return { current: 'game_asset', suggested: 'character',
                    reason: "Your prompt describes a character. 'Character' type optimizes for figure proportions, pose, and silhouette readability." };
            }
            if (sceneHits >= 2) {
                return { current: 'game_asset', suggested: 'environment',
                    reason: "Your prompt describes a scene or environment. 'Environment' type preserves the full composition. 'Game Asset' forces an isolated object on a transparent background." };
            }
            return null;
        },
        _isAllModels() {
            return this._selectedModels.length > 1;
        },

        _updateAllModelsUI(isAllModels) {
            const allModelsOpts = document.getElementById('gen-all-models-opts');
            const optsSelect = document.getElementById('gen-num-options');
            const varsSelect = document.getElementById('gen-num-variations');
            const infoEl = document.getElementById('gen-all-models-info');

            if (isAllModels) {
                allModelsOpts?.classList.remove('hidden');
                // Keep selectors enabled — user controls options × variations per model
                if (optsSelect) optsSelect.disabled = false;
                if (varsSelect) varsSelect.disabled = false;
                this._updateMultiModelCostEstimate();
            } else {
                allModelsOpts?.classList.add('hidden');
                if (optsSelect) optsSelect.disabled = false;
                if (varsSelect) varsSelect.disabled = false;
            }
        },

        _syncModelCheckboxes() {
            const checkboxes = document.querySelectorAll('.gen-model-cb');
            const allCheck = document.getElementById('gen-model-all');
            const realModels = MODELS.filter(m => m.value !== 'all_models');

            checkboxes.forEach(cb => {
                cb.checked = this._selectedModels.includes(cb.value);
            });
            if (allCheck) {
                allCheck.checked = this._selectedModels.length === realModels.length;
            }

            // Update button label
            const label = document.getElementById('gen-model-label');
            if (label) {
                if (this._selectedModels.length === 0) {
                    label.textContent = t('image_studio.select_models') || 'Select models...';
                } else if (this._selectedModels.length === 1) {
                    const m = MODELS.find(m => m.value === this._selectedModels[0]);
                    label.textContent = m?.label || this._selectedModels[0];
                } else if (this._selectedModels.length === realModels.length) {
                    label.textContent = `${t('image_studio.all_models') || 'All'} (${realModels.length} ${t('image_studio.models_count') || 'models'})`;
                } else {
                    label.textContent = `${this._selectedModels.length} ${t('image_studio.models_selected') || 'models selected'}`;
                }
            }

            // Show/hide multi-model options
            const isMulti = this._selectedModels.length > 1;
            this._updateAllModelsUI(isMulti);

            // Update quality/region for single model, or clear for multi
            if (this._selectedModels.length === 1) {
                this._updateQualityForModel(this._selectedModels[0]);
                this._updateRegionForModel(this._selectedModels[0]);
            } else {
                this._updateQualityForModel('all_models');
                this._updateRegionForModel('all_models');
            }

            // Update size dropdown based on selected models' supported_sizes
            this._updateSizePresetsForModels();

            this._updateMultiModelCostEstimate();
        },

        _updateSizePresetsForModels() {
            const sizeSel = document.getElementById('gen-size');
            if (!sizeSel) return;

            const currentValue = sizeSel.value;
            const currentSize = SIZE_PRESETS[parseInt(currentValue, 10)] || null;

            // Collect supported_sizes from selected models
            const selectedData = this._selectedModels
                .map(key => MODELS.find(m => m.value === key))
                .filter(Boolean);

            // If any selected model declares supported_sizes, use union of all
            const modelSizes = selectedData
                .filter(m => m.supported_sizes?.length)
                .flatMap(m => m.supported_sizes);

            let sizes;
            if (modelSizes.length > 0) {
                // Deduplicate by "WxH" key, preserve order
                const seen = new Set();
                sizes = [];
                for (const s of modelSizes) {
                    const key = `${s.w}x${s.h}`;
                    if (!seen.has(key)) {
                        seen.add(key);
                        sizes.push(s);
                    }
                }
                // Sort: square first, then landscape, then portrait, by area ascending
                sizes.sort((a, b) => {
                    const areaA = a.w * a.h, areaB = b.w * b.h;
                    if (areaA !== areaB) return areaA - areaB;
                    return b.w - a.w;
                });
            } else {
                // No model declares sizes — use defaults
                sizes = SIZE_PRESETS;
            }

            // Rebuild the dropdown
            sizeSel.innerHTML = '';
            sizes.forEach((s, i) => {
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = s.label;
                sizeSel.appendChild(opt);
            });

            // Store current sizes for payload construction
            this._activeSizePresets = sizes;

            // Try to restore previous selection by matching dimensions
            if (currentSize) {
                const match = sizes.findIndex(s => s.w === currentSize.w && s.h === currentSize.h);
                if (match >= 0) {
                    sizeSel.value = match;
                    return;
                }
            }
            // Default to 1024x1024 or index 2
            const default1024 = sizes.findIndex(s => s.w === 1024 && s.h === 1024);
            sizeSel.value = default1024 >= 0 ? default1024 : Math.min(2, sizes.length - 1);
        },

        _updateMultiModelCostEstimate() {
            const costEl = document.getElementById('gen-cost-estimate');
            const summaryEl = document.getElementById('gen-model-summary');
            const infoEl = document.getElementById('gen-all-models-info');

            if (this._selectedModels.length === 1) {
                // Delegate to existing single-model summary
                if (infoEl) infoEl.textContent = '';
                this._updateModelSummary();
                return;
            }

            // Multi-model cost estimate
            if (summaryEl) summaryEl.textContent = '';

            const nOpts = parseInt(document.getElementById('gen-num-options')?.value || '1', 10);
            const nVars = parseInt(document.getElementById('gen-num-variations')?.value || '1', 10);
            const modelCount = this._selectedModels.length;
            const totalImages = modelCount * nOpts * nVars;

            // Sum region/quality-aware per-image prices (same resolver as the
            // single-model estimate — no hardcoded fallback price, so the same
            // model shows the same price whether 1 or N models are selected). If
            // ANY selected model has no registry price, we can't total honestly →
            // omit the dollar figure rather than guess.
            const quality = document.getElementById('gen-quality')?.value || '';
            const region = document.getElementById('gen-region')?.value || '';
            const perImage = this._selectedModels.map(key => {
                const m = MODELS.find(m => m.value === key);
                return this._perImagePrice(m, region || (m?.region || ''), quality || (m?.default_quality || ''));
            });
            const anyMissing = perImage.some(p => p == null);
            const totalCost = anyMissing ? 0 : perImage.reduce((sum, p) => sum + p * nOpts * nVars, 0);

            let msg = `${modelCount} models \u00d7 ${nOpts} option${nOpts > 1 ? 's' : ''} \u00d7 ${nVars} variation${nVars > 1 ? 's' : ''} = ${totalImages} images`;
            if (totalCost > 0) msg += ` (~$${totalCost.toFixed(2)})`;

            if (infoEl) {
                if (totalImages > 100) {
                    infoEl.className = 'text-[10px] text-red-400';
                    msg += ' \u2014 large batch, will take several minutes';
                } else if (totalImages > 50) {
                    infoEl.className = 'text-[10px] text-amber-400';
                } else {
                    infoEl.className = 'text-[10px] text-emerald-400/70';
                }
                infoEl.textContent = msg;
            }

            if (costEl) {
                costEl.textContent = totalCost > 0
                    ? `Est. ~$${totalCost.toFixed(2)} (${totalImages} images \u00d7 ${modelCount} models)`
                    : '';
            }
        },

        _getIpDeclaration() {
            return {
                ip_owned: document.getElementById('gen-ip-own')?.checked || false,
                ip_licensed: document.getElementById('gen-ip-license')?.checked || false,
            };
        },

        _updateIpModelNote() {
            const note = document.getElementById('gen-ip-model-note');
            if (!note) return;
            const ip = this._getIpDeclaration();
            const model = (this._selectedModels?.[0] || '') || '';
            const strictModels = ['nova_canvas', 'titan_image'];

            if ((ip.ip_owned || ip.ip_licensed) && strictModels.includes(model)) {
                const modelData = MODELS.find(m => m.value === model);
                const modelLabel = modelData?.label || model;
                note.innerHTML = `
                    ${t('image_studio.ip_strict_model_warning').replace('{{model}}', '<strong>' + modelLabel + '</strong>')}
                    <button id="gen-ip-switch-model" class="underline text-amber-200 hover:text-amber-100 ml-1">${t('image_studio.ip_switch_now')}</button>
                `;
                note.classList.remove('hidden');

                // Wire up the quick-switch button
                setTimeout(() => {
                    document.getElementById('gen-ip-switch-model')?.addEventListener('click', () => {
                        this._selectedModels = ['sd35_large'];
                        this._syncModelCheckboxes();
                        this._updateIpModelNote();
                        window.showToast?.(t('image_studio.switched_to'), 'success');
                    });
                }, 0);
            } else {
                note.classList.add('hidden');
            }
        },

        _showCostBreakdown(totalCost, breakdown) {
            const section = document.getElementById('gen-cost-breakdown');
            const totalEl = document.getElementById('gen-cost-total');
            const detailsEl = document.getElementById('gen-cost-details');
            if (!section || !totalEl || !detailsEl) return;

            section.classList.remove('hidden');
            totalEl.textContent = `$${totalCost.toFixed(4)}`;

            const labels = {
                'llm': t('image_studio.cost_llm'),
                'image_generation': t('image_studio.cost_image_generation'),
                'image_inpainting': t('image_studio.cost_image_inpainting'),
                'image_outpainting': t('image_studio.cost_image_outpainting'),
                'image_erase': t('image_studio.cost_image_erase'),
                'image_remove_background': t('image_studio.cost_image_remove_bg'),
                'image_upscale_creative': t('image_studio.cost_image_upscale'),
                'image_search_replace': t('image_studio.cost_image_search_replace'),
            };

            detailsEl.innerHTML = Object.entries(breakdown)
                .sort((a, b) => b[1].cost - a[1].cost)
                .map(([key, val]) => {
                    const label = labels[key] || key.replace(/_/g, ' ');
                    return `<div class="flex justify-between"><span>${label} (${val.count}x)</span><span>$${val.cost.toFixed(4)}</span></div>`;
                }).join('');

            // Also show in prompt info section
            document.getElementById('gen-prompt-info')?.classList.remove('hidden');
        },

        _escapeHtml(str) {
            const d = document.createElement('div');
            d.textContent = str;
            return d.innerHTML;
        },

        // ── Pending Jobs (async custom models) ─────────────────────────

        _pendingJobsTimer: null,
        _pendingJobsActive: false,  // Whether polling is active
        _notifiedJobIds: new Set(), // Track which completions we've toasted

        _pollPendingJobs() {
            // One-time check at startup for recovery after server restart.
            // If active jobs found → starts polling. If not → stops. No loop.
            this._checkAsyncJobs();
        },

        _startAsyncPolling() {
            if (this._pendingJobsActive) return;
            this._pendingJobsActive = true;
            this._pollingStartedAt = Date.now();
            this._asyncPollLoop();
        },

        _stopAsyncPolling() {
            // Don't stop within 30s of starting — jobs may not be registered yet
            if (this._pollingStartedAt && Date.now() - this._pollingStartedAt < 30000) return;
            this._pendingJobsActive = false;
            clearTimeout(this._pendingJobsTimer);
        },

        async _asyncPollLoop() {
            if (!this._pendingJobsActive) return;
            await this._checkAsyncJobs();
            // Continue polling only if there are still active jobs
            if (this._pendingJobsActive) {
                this._pendingJobsTimer = setTimeout(() => this._asyncPollLoop(), 5000);
            }
        },

        async _checkAsyncJobs() {
            try {
                const resp = await fetch('/api/generate/async-jobs');
                if (!resp.ok) return;
                const data = await resp.json();
                const count = data.pending_count || 0;
                const jobs = data.jobs || [];
                const hasActive = data.has_active || false;

                // Update button visibility and label
                const btn = document.getElementById('btn-pending-jobs');
                const label = document.getElementById('pending-jobs-label');
                if (btn) {
                    btn.classList.toggle('hidden', jobs.length === 0);
                    if (label) label.textContent = count > 0
                        ? t('custom_models.pending_jobs_count').replace('{{count}}', count)
                        : t('custom_models.pending_jobs_total').replace('{{count}}', jobs.length);
                }

                // Toast + live update for newly completed jobs
                let newlyCompleted = 0;
                jobs.filter(j => j.status === 'complete' && !this._notifiedJobIds.has(j.job_id)).forEach(j => {
                    window.showToast?.(t('custom_models.async_ready_toast').replace('{{model}}', j.model_label), 'success');
                    this._notifiedJobIds.add(j.job_id);
                    newlyCompleted++;

                    const assetId = j.asset_id || '';
                    if (assetId) {
                        const imgSrc = `/api/gallery/${assetId}/png`;

                        // Update the in-memory result data so re-renders show the image
                        if (this._result?.options) {
                            for (const opt of this._result.options) {
                                for (const v of (opt.variants || [])) {
                                    if (v.async_job?.job_id === j.job_id || v.id === assetId) {
                                        v.png_path = imgSrc;
                                        v.async_job = null; // No longer async
                                    }
                                }
                            }
                        }

                        // Replace async placeholders in DOM
                        document.querySelectorAll(`[data-async-job="${j.job_id}"] .async-placeholder, [data-async-asset="${assetId}"] .async-placeholder`).forEach(ph => {
                            ph.outerHTML = `<img src="${imgSrc}" alt="Generated" class="w-full h-full object-cover" loading="lazy" />`;
                        });

                        // Also update variation thumbnails if this option is currently selected
                        document.querySelectorAll(`.variant-thumb[data-async-job="${j.job_id}"] .async-placeholder, .variant-thumb[data-async-asset="${assetId}"] .async-placeholder`).forEach(ph => {
                            ph.outerHTML = `<img src="${imgSrc}" alt="Generated" class="w-full h-full object-cover" loading="lazy" />`;
                        });

                        // Re-render the options row to update thumbnails that weren't in DOM
                        if (this._result) {
                            this._renderOptionsRow(this._result.options || []);
                            this._selectOption(this._selectedOption || 0);
                        }
                    }
                });

                // Refresh Gallery component so completed async items update there too
                if (newlyCompleted > 0 && window.Gallery?.refresh) {
                    window.Gallery.refresh();
                }

                // Smart polling: start/stop based on active jobs
                if (hasActive && !this._pendingJobsActive) {
                    this._startAsyncPolling();
                } else if (!hasActive && this._pendingJobsActive) {
                    this._stopAsyncPolling();
                }
            } catch {}
        },

        async _showPendingJobs() {
            let data;
            try {
                const resp = await fetch('/api/generate/async-jobs');
                if (!resp.ok) return;
                data = await resp.json();
            } catch { return; }

            const jobs = data.jobs || [];
            const backdrop = document.createElement('div');
            backdrop.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';

            const jobsHtml = jobs.length === 0
                ? `<p class="text-xs text-brand-text-muted py-4 text-center">${t('custom_models.async_no_jobs')}</p>`
                : jobs.map(j => {
                    const isActive = j.status === 'generating' || j.status === 'pending';
                    const statusColor = j.status === 'complete' ? 'text-emerald-400' : j.status === 'failed' ? 'text-red-400' : 'text-cyan-400';
                    const statusIcon = j.status === 'complete' ? '✓' : j.status === 'failed' ? '✗' : '';
                    const thumb = j.status === 'complete' && j.image_path
                        ? `<img src="/api/gallery/${j.image_path.split('/').slice(-2, -1)[0]}/png" class="w-12 h-12 rounded object-cover flex-shrink-0" />`
                        : `<div class="w-12 h-12 rounded bg-brand-border/20 flex items-center justify-center flex-shrink-0">
                            ${j.status === 'failed'
                                ? `<span class="text-red-400 text-lg">✗</span>`
                                : `<div class="w-5 h-5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin"></div>`
                            }
                        </div>`;
                    const elapsed = j.submitted_at ? Math.round((Date.now() - new Date(j.submitted_at).getTime()) / 1000) : 0;
                    const elapsedStr = elapsed > 60 ? `${Math.floor(elapsed/60)}m ${elapsed%60}s` : `${elapsed}s`;

                    // Stage-based status with queue position
                    let statusText;
                    const isCurrentlyGenerating = isActive && j.queue_position === 1;
                    const isQueued = isActive && j.queue_position > 1;
                    if (j.status === 'complete') {
                        statusText = `Generated${j.compute_cost_usd ? ` (~$${j.compute_cost_usd.toFixed(4)})` : ''}`;
                        if (j.duration_seconds) statusText += ` in ${Math.round(j.duration_seconds)}s`;
                    } else if (j.status === 'failed') {
                        statusText = 'Failed';
                    } else if (isQueued) {
                        statusText = `Queued — #${j.queue_position} of ${j.queue_total}`;
                    } else {
                        statusText = j.stage_label || 'Generating...';
                    }

                    // Progress bar: active spinner for #1, static dim bar for queued
                    let progressBar = '';
                    if (isCurrentlyGenerating) {
                        progressBar = `<div class="flex items-center gap-2 mt-1"><div class="flex-1 h-1.5 rounded-full bg-brand-border/30 overflow-hidden"><div class="h-full rounded-full bg-cyan-400 animate-pulse" style="width:100%"></div></div><span class="text-[9px] text-cyan-400/70">${elapsedStr}</span></div>`;
                    } else if (isQueued) {
                        progressBar = `<div class="flex items-center gap-2 mt-1"><div class="flex-1 h-1 rounded-full bg-brand-border/20"></div><span class="text-[9px] text-brand-text-muted/40">waiting</span></div>`;
                    }

                    return `
                        <div class="flex items-center gap-3 p-3 rounded-lg ${isCurrentlyGenerating ? 'bg-cyan-950/20 border-cyan-500/30' : 'bg-brand-bg/40 border-brand-border'} border">
                            ${thumb}
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2">
                                    <span class="text-xs font-semibold text-brand-text">${j.model_label}</span>
                                    ${isCurrentlyGenerating ? '<span class="text-[9px] text-cyan-400 bg-cyan-400/10 rounded px-1">ACTIVE</span>' : ''}
                                    <span class="text-[10px] ${statusColor}">${statusText}</span>
                                </div>
                                <p class="text-[10px] text-brand-text-muted truncate">${j.prompt || ''}</p>
                                ${j.status === 'failed' ? `<p class="text-[10px] text-red-400 mt-0.5">${j.error || ''}</p>` : ''}
                                ${progressBar}
                            </div>
                        </div>`;
                }).join('');

            backdrop.innerHTML = `
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full max-h-[70vh] flex flex-col overflow-hidden">
                    <div class="flex items-center justify-between px-5 py-3 border-b border-brand-border">
                        <h3 class="text-sm font-semibold text-brand-text flex items-center gap-2">
                            <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            ${t('custom_models.pending_jobs')}
                        </h3>
                        <div class="flex gap-2">
                            ${jobs.some(j => j.status === 'complete' || j.status === 'failed') ? `<button class="pj-clear text-[10px] text-brand-text-muted hover:text-red-400">${t('custom_models.async_clear_completed')}</button>` : ''}
                            <button class="pj-close p-1 rounded hover:bg-white/5 text-brand-text-muted hover:text-brand-text">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="px-4 py-2 text-[10px] text-brand-text-muted/70 border-b border-brand-border bg-brand-bg/30">
                        ${t('custom_models.async_footer')}
                    </div>
                    <div class="flex-1 overflow-auto p-4 space-y-2">
                        ${jobsHtml}
                    </div>
                </div>`;

            backdrop.querySelector('.pj-close').addEventListener('click', () => backdrop.remove());
            backdrop.addEventListener('click', (e) => { if (e.target === backdrop) backdrop.remove(); });
            backdrop.querySelector('.pj-clear')?.addEventListener('click', async () => {
                await fetch('/api/generate/async-jobs/clear', { method: 'POST' });
                backdrop.remove();
                this._showPendingJobs();
            });

            document.body.appendChild(backdrop);
        },
    };
})();
