/**
 * ArtSmoker — Video Studio Component
 *
 * Text-to-video generation using Amazon Nova Reel and Luma AI Ray v2.
 * Supports single-shot, multi-shot, and image-to-video workflows.
 * Jobs are async — polls for completion and shows progress.
 */
(function () {
    'use strict';

    const POLL_INTERVAL = 5000; // 5 seconds

    window.VideoStudio = {
        _models: [],
        _activeJobs: [],
        _pollTimers: {},
        _videoSettings: null,

        render() {
            return `
                <div id="video-studio-view" class="view-enter">
                    <div class="mb-6">
                        <h1 class="text-2xl font-bold">${t('video_studio.title')}</h1>
                        <p class="text-brand-text-muted text-sm mt-1">${t('video_studio.subtitle')}</p>
                    </div>

                    <div class="flex flex-col lg:flex-row gap-6">

                        <!-- Left Sidebar: Settings -->
                        <aside class="lg:w-72 xl:w-80 flex-shrink-0 space-y-5">
                            <div class="card-static p-5 space-y-5">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
                                    </svg>
                                    ${t('video_studio.settings_heading')}
                                </h2>

                                <!-- Model -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('video_studio.model')}</label>
                                    <select id="vs-model" class="input">
                                        <option value="">${t('video_studio.model_loading')}</option>
                                    </select>
                                    <p id="vs-model-summary" class="text-[10px] text-brand-text-muted mt-1"></p>
                                </div>

                                <!-- Task Type (Nova Reel only) -->
                                <div id="vs-task-type-group" class="hidden">
                                    <label class="block text-sm font-medium mb-1.5">${t('video_studio.generation_mode')}</label>
                                    <select id="vs-task-type" class="input">
                                        <option value="TEXT_VIDEO">${t('video_studio.task_single')}</option>
                                        <option value="MULTI_SHOT_AUTOMATED">${t('video_studio.task_multi_auto')}</option>
                                        <option value="MULTI_SHOT_MANUAL">${t('video_studio.task_multi_manual')}</option>
                                    </select>
                                </div>

                                <!-- Duration -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">${t('video_studio.duration')}</label>
                                    <select id="vs-duration" class="input">
                                        <option value="6">6 ${t('video_studio.seconds')}</option>
                                    </select>
                                </div>

                                <!-- Aspect Ratio (Luma only) -->
                                <div id="vs-aspect-group" class="hidden">
                                    <label class="block text-sm font-medium mb-1.5">${t('video_studio.aspect_ratio')}</label>
                                    <select id="vs-aspect" class="input">
                                        <option value="16:9">16:9</option>
                                    </select>
                                </div>

                                <!-- Resolution (Luma only) -->
                                <div id="vs-resolution-group" class="hidden">
                                    <label class="block text-sm font-medium mb-1.5">${t('video_studio.resolution')}</label>
                                    <select id="vs-resolution" class="input">
                                        <option value="720p">720p</option>
                                    </select>
                                </div>

                                <!-- Loop (Luma only) -->
                                <div id="vs-loop-group" class="hidden">
                                    <label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
                                        <input type="checkbox" id="vs-loop" class="w-4 h-4 rounded border-brand-border bg-brand-bg text-brand-accent focus:ring-brand-accent">
                                        ${t('video_studio.loop')}
                                    </label>
                                </div>

                                <!-- Advanced: Region + Seed -->
                                <details class="group">
                                    <summary class="text-xs font-medium text-brand-text-muted cursor-pointer hover:text-brand-text transition-colors select-none">
                                        <span class="group-open:hidden">\u25B8 ${t('video_studio.advanced_collapsed')}</span>
                                        <span class="hidden group-open:inline">\u25BE ${t('video_studio.advanced_expanded')}</span>
                                    </summary>
                                    <div class="mt-2 space-y-3 p-2.5 rounded-lg bg-brand-bg/40 border border-brand-border/50">
                                        <div>
                                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1">${t('common.region')}</label>
                                            <select id="vs-region" class="input text-xs">
                                                <option value="">${t('video_studio.auto')}</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1">${t('video_studio.seed')}</label>
                                            <input type="number" id="vs-seed" class="input text-xs w-full" placeholder="${t('video_studio.seed_placeholder')}" min="0">
                                        </div>
                                    </div>
                                </details>

                                <!-- Cost estimate -->
                                <div id="vs-cost-estimate" class="text-[10px] text-emerald-400/70 font-mono"></div>

                                <!-- Source Image (optional) -->
                                <details id="vs-image-input-group" class="hidden">
                                    <summary class="text-xs font-medium cursor-pointer text-brand-accent hover:text-brand-accent-hover select-none">
                                        \u25B8 ${t('video_studio.source_image')}
                                    </summary>
                                    <div class="mt-2 p-2.5 border border-brand-border/50 rounded-lg bg-brand-bg/40 space-y-2">
                                        <input type="file" id="vs-source-image" accept="image/png,image/jpeg" class="text-xs w-full">
                                        <p class="text-[10px] text-brand-text-muted">${t('video_studio.source_image_hint')}</p>
                                        <div id="vs-source-preview" class="hidden">
                                            <img id="vs-source-img" class="max-h-24 rounded border border-brand-border" alt="Source">
                                            <button id="vs-clear-source" class="btn btn-secondary btn-sm mt-1 text-[10px]">${t('video_studio.source_image_clear')}</button>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <!-- Settings buttons -->
                            <button id="vs-model-settings-btn" class="w-full text-left p-3 rounded-lg bg-brand-bg/30 border border-brand-border/50 hover:border-brand-accent/30 hover:bg-brand-bg/50 transition-colors flex items-center gap-2 text-xs text-brand-text-muted">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                                ${t('video_studio.model_settings')}
                            </button>
                            <button id="vs-settings-btn" class="w-full text-left p-3 rounded-lg bg-brand-bg/30 border border-brand-border/50 hover:border-brand-accent/30 hover:bg-brand-bg/50 transition-colors flex items-center gap-2 text-xs text-brand-text-muted">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/>
                                </svg>
                                ${t('video_studio.video_settings')}
                            </button>

                            <p class="artsmoker-version text-[9px] text-brand-text-dim/30 text-center mt-4">ArtSmoker</p>
                        </aside>

                        <!-- Center: Prompt + Generate + Jobs + Results -->
                        <div class="flex-1 min-w-0 space-y-5">

                            <!-- S3 Status Banner -->
                            <div id="vs-s3-banner" class="hidden card-static p-4">
                                <div class="flex items-start gap-3" id="vs-s3-banner-content"></div>
                            </div>

                            <!-- Prompt -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                    </svg>
                                    ${t('common.prompt')}
                                </h2>
                                <textarea id="vs-prompt" rows="4" class="input w-full"
                                    placeholder="${t('video_studio.prompt_placeholder')}"></textarea>
                                <div class="flex items-center justify-between">
                                    <span id="vs-char-count" class="text-xs text-brand-text-muted">0 / 512</span>
                                    <label class="flex items-center gap-1.5 text-xs text-brand-text-muted cursor-pointer">
                                        <input type="checkbox" id="vs-enhance" checked class="w-3.5 h-3.5 rounded border-brand-border bg-brand-bg text-brand-accent focus:ring-brand-accent">
                                        ${t('video_studio.enhance_prompt')}
                                    </label>
                                </div>
                            </div>

                            <!-- Generate Button -->
                            <!-- Generate / Reset Buttons -->
                            <div class="grid grid-cols-2 gap-3">
                                <button id="vs-generate-btn" class="btn btn-primary btn-lg text-base" disabled>
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                    </svg>
                                    ${t('video_studio.generate')}
                                </button>
                                <button id="vs-reset-btn" class="btn btn-lg text-base bg-amber-600 hover:bg-amber-500 text-white">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                    </svg>
                                    ${t('common.reset')}
                                </button>
                            </div>

                            <!-- Prompt Info (shown after generation starts) -->
                            <div id="vs-prompt-info" class="hidden card-static p-4 space-y-3">
                                <div>
                                    <p class="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold mb-1">${t('video_studio.original_prompt')}</p>
                                    <p id="vs-original-prompt" class="text-sm text-brand-text/80 leading-relaxed"></p>
                                </div>
                                <div id="vs-enhanced-prompt-section" class="hidden">
                                    <p class="text-[10px] text-brand-accent uppercase tracking-wider font-semibold mb-1">${t('video_studio.enhanced_prompt')}</p>
                                    <p id="vs-enhanced-prompt" class="text-sm text-brand-text/60 leading-relaxed"></p>
                                </div>
                                <div id="vs-negative-section" class="hidden">
                                    <p class="text-[10px] text-amber-400/80 uppercase tracking-wider font-semibold mb-1">${t('video_studio.negative_concepts_note')}</p>
                                    <p id="vs-negative-concepts" class="text-sm text-amber-300/60 leading-relaxed italic"></p>
                                </div>
                            </div>

                            <!-- Active Jobs -->
                            <div id="vs-jobs-section" class="card-static p-4 hidden">
                                <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
                                    <div class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></div>
                                    ${t('video_studio.active_jobs')}
                                </h3>
                                <div id="vs-jobs-list" class="space-y-3"></div>
                            </div>

                            <!-- Completed Videos -->
                            <div id="vs-completed" class="hidden space-y-4">
                                <h2 class="text-lg font-semibold">${t('video_studio.recent_videos')}</h2>
                                <div id="vs-completed-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Video Settings Dialog -->
                <div id="vs-settings-dialog" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div class="card-static p-6 w-full max-w-lg space-y-4">
                        <div class="flex items-center justify-between">
                            <h3 class="text-lg font-semibold">${t('video_studio.settings_title')}</h3>
                            <button id="vs-settings-close" class="text-brand-text-muted hover:text-brand-text text-xl">&times;</button>
                        </div>
                        <div class="space-y-4">
                            <!-- S3 Bucket Selection -->
                            <div>
                                <label class="block text-sm font-medium mb-1.5">${t('video_studio.s3_bucket')}</label>
                                <div class="flex gap-2">
                                    <input type="text" id="vs-s3-bucket" class="input flex-1" placeholder="${t('video_studio.s3_bucket_placeholder')}">
                                    <button id="vs-browse-s3" class="btn btn-secondary btn-sm whitespace-nowrap">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                                        </svg>
                                        ${t('video_studio.s3_browse')}
                                    </button>
                                </div>
                                <p class="text-[10px] text-brand-text-muted mt-1">${t('video_studio.s3_bucket_hint')}</p>
                            </div>

                            <!-- Bucket list (shown after Browse click) -->
                            <div id="vs-bucket-list" class="hidden border border-brand-border rounded-lg overflow-hidden">
                                <div class="px-3 py-2 bg-brand-bg/60 border-b border-brand-border flex items-center justify-between">
                                    <span class="text-xs font-medium text-brand-text-muted">${t('video_studio.your_s3_buckets')}</span>
                                    <button id="vs-create-bucket-btn" class="text-[10px] text-brand-accent hover:text-brand-accent-hover font-medium">${t('video_studio.create_new')}</button>
                                </div>
                                <div id="vs-bucket-items" class="max-h-40 overflow-auto">
                                    <div class="text-xs text-brand-text-muted p-3 text-center">${t('common.loading')}</div>
                                </div>
                            </div>

                            <!-- Create bucket form (hidden by default) -->
                            <div id="vs-create-bucket-form" class="hidden p-3 border border-brand-accent/30 rounded-lg bg-brand-accent/5 space-y-2">
                                <label class="block text-xs font-medium">${t('video_studio.new_bucket_name')}</label>
                                <div class="flex gap-2">
                                    <input type="text" id="vs-new-bucket-name" class="input flex-1 text-sm" placeholder="my-artsmoker-videos" pattern="[a-z0-9][a-z0-9.\\-]{1,61}[a-z0-9]">
                                    <select id="vs-new-bucket-region" class="input text-xs w-32">
                                        <option value="us-east-1">us-east-1</option>
                                    </select>
                                </div>
                                <p class="text-[10px] text-brand-text-muted">${t('video_studio.bucket_name_hint')}</p>
                                <div class="flex gap-2">
                                    <button id="vs-create-bucket-go" class="btn btn-primary btn-sm text-xs">${t('video_studio.s3_create')}</button>
                                    <button id="vs-create-bucket-cancel" class="btn btn-secondary btn-sm text-xs">${t('common.cancel')}</button>
                                </div>
                            </div>

                            <!-- S3 Prefix -->
                            <div>
                                <label class="block text-sm font-medium mb-1">${t('video_studio.s3_prefix')}</label>
                                <input type="text" id="vs-s3-prefix" class="input w-full" placeholder="artsmoker/video/" value="artsmoker/video/">
                            </div>

                            <!-- Storage mode -->
                            <div>
                                <label class="block text-sm font-medium mb-1">${t('video_studio.s3_storage_mode')}</label>
                                <select id="vs-store-mode" class="input w-full">
                                    <option value="local">${t('video_studio.s3_local')}</option>
                                    <option value="s3">${t('video_studio.s3_only')}</option>
                                </select>
                                <p class="text-[10px] text-brand-text-muted mt-1">
                                    <strong>${t('video_studio.s3_local_desc_local')}</strong><br>
                                    <strong>${t('video_studio.s3_local_desc_s3')}</strong>
                                </p>
                            </div>

                            <div id="vs-s3-status" class="hidden text-xs p-2 rounded"></div>
                            <div class="flex gap-2 justify-end">
                                <button id="vs-settings-close-bottom" class="btn btn-secondary btn-sm hidden">${t('common.close')}</button>
                                <button id="vs-settings-test" class="btn btn-primary btn-sm">${t('video_studio.s3_test_save')}</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        },

        async init() {
            this._attachEvents();
            await this._loadVideoSettings();
            await this._loadModels();
            await this._loadRecentJobs();
        },

        onShow() {
            this._loadRecentJobs();
        },

        // ── Events ──────────────────────────────────────────────────

        _attachEvents() {
            // Prompt char counter
            const prompt = document.getElementById('vs-prompt');
            prompt?.addEventListener('input', () => this._updateCharCount());

            // Model change
            document.getElementById('vs-model')?.addEventListener('change', () => this._onModelChange());

            // Task type change (Nova Reel)
            document.getElementById('vs-task-type')?.addEventListener('change', () => this._onTaskTypeChange());

            // Region change → update summary + cost
            document.getElementById('vs-region')?.addEventListener('change', () => {
                this._updateModelSummary();
                this._updateCostEstimate();
            });

            // Generate / Reset buttons
            document.getElementById('vs-generate-btn')?.addEventListener('click', () => this._generate());
            document.getElementById('vs-reset-btn')?.addEventListener('click', () => this._reset());

            // Settings
            document.getElementById('vs-model-settings-btn')?.addEventListener('click', () => window.ModelSettings?.open());
            document.getElementById('vs-settings-btn')?.addEventListener('click', () => this._showSettings());
            document.getElementById('vs-settings-close')?.addEventListener('click', () => this._hideSettings());
            document.getElementById('vs-settings-test')?.addEventListener('click', () => this._testAndSaveSettings());

            // S3 bucket browser
            document.getElementById('vs-browse-s3')?.addEventListener('click', () => this._loadBucketList());
            document.getElementById('vs-create-bucket-btn')?.addEventListener('click', () => this._showCreateBucket());
            document.getElementById('vs-create-bucket-cancel')?.addEventListener('click', () => {
                document.getElementById('vs-create-bucket-form')?.classList.add('hidden');
            });
            document.getElementById('vs-create-bucket-go')?.addEventListener('click', () => this._createBucket());

            // Source image upload
            const fileInput = document.getElementById('vs-source-image');
            fileInput?.addEventListener('change', (e) => this._onSourceImage(e));
            document.getElementById('vs-clear-source')?.addEventListener('click', () => this._clearSourceImage());

            // Re-enable Test & Save when bucket input changes
            document.getElementById('vs-s3-bucket')?.addEventListener('input', () => {
                const testBtn = document.getElementById('vs-settings-test');
                if (testBtn) { testBtn.disabled = false; testBtn.textContent = t('video_studio.s3_test_save'); }
                document.getElementById('vs-settings-close-bottom')?.classList.add('hidden');
                const statusEl = document.getElementById('vs-s3-status');
                if (statusEl) statusEl.classList.add('hidden');
            });

            // Close dialog on backdrop click
            document.getElementById('vs-settings-dialog')?.addEventListener('click', (e) => {
                if (e.target.id === 'vs-settings-dialog') this._hideSettings();
            });
        },

        // ── Data loading ────────────────────────────────────────────

        async _loadVideoSettings() {
            try {
                this._videoSettings = await API.admin.getVideoSettings();
            } catch (_) {
                this._videoSettings = { s3_bucket: '', store_local: true };
            }
            this._updateS3Banner();
        },

        async _loadModels() {
            const sel = document.getElementById('vs-model');
            if (!sel) return;
            try {
                const data = await API.admin.getVideoOptions();
                this._models = data.models || [];
            } catch (_) {
                this._models = [];
            }
            sel.innerHTML = '';
            if (this._models.length === 0) {
                sel.innerHTML = `<option value="">${t('video_studio.model_not_found')}</option>`;
                return;
            }
            this._models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.key;
                opt.textContent = `${m.label} (${m.provider})`;
                opt.dataset.family = m.format_family;
                sel.appendChild(opt);
            });
            this._onModelChange();
        },

        async _loadRecentJobs() {
            try {
                const data = await API.video.jobs({ limit: 20 });
                const jobs = data.jobs || [];
                this._renderJobsList(jobs.filter(j => j.status === 'InProgress'));
                this._renderCompletedGrid(jobs.filter(j => j.status === 'Completed'));

                // Resume polling for active jobs
                jobs.filter(j => j.status === 'InProgress').forEach(j => {
                    if (!this._pollTimers[j.job_id]) {
                        this._startPolling(j.job_id);
                    }
                });
            } catch (_) {}
        },

        // ── Model change handling ───────────────────────────────────

        _onModelChange() {
            const sel = document.getElementById('vs-model');
            if (!sel) return;
            const model = this._models.find(m => m.key === sel.value);
            if (!model) return;

            const family = model.format_family;
            const isNovaReel = family === 'nova_reel';
            const isLuma = family === 'luma_ray';

            // Task type (Nova Reel only)
            document.getElementById('vs-task-type-group')?.classList.toggle('hidden', !isNovaReel);

            // Aspect ratio (Luma only)
            const aspectGroup = document.getElementById('vs-aspect-group');
            aspectGroup?.classList.toggle('hidden', !isLuma);
            if (isLuma && model.parameters?.aspect_ratio?.options) {
                const aspectSel = document.getElementById('vs-aspect');
                if (aspectSel) {
                    aspectSel.innerHTML = model.parameters.aspect_ratio.options
                        .map(o => `<option value="${o}" ${o === '16:9' ? 'selected' : ''}>${o}</option>`).join('');
                }
            }

            // Resolution (Luma only)
            const resGroup = document.getElementById('vs-resolution-group');
            resGroup?.classList.toggle('hidden', !isLuma);
            if (isLuma && model.parameters?.resolution?.options) {
                const resSel = document.getElementById('vs-resolution');
                if (resSel) {
                    resSel.innerHTML = model.parameters.resolution.options
                        .map(o => `<option value="${o}" ${o === '720p' ? 'selected' : ''}>${o}</option>`).join('');
                }
            }

            // Loop (Luma only)
            document.getElementById('vs-loop-group')?.classList.toggle('hidden', !isLuma);

            // Source image support
            document.getElementById('vs-image-input-group')?.classList.toggle('hidden', !model.supports_image_input && !isLuma);

            // Duration options
            this._updateDurationOptions(model, isNovaReel);

            // Region dropdown
            this._updateRegionForModel(model);

            // Char count limit
            this._updateCharCount();

            // Summary + cost
            this._updateModelSummary();
            this._updateCostEstimate();

            // Enable generate button if bucket is configured
            const genBtn = document.getElementById('vs-generate-btn');
            if (genBtn && this._videoSettings?.s3_bucket) {
                genBtn.disabled = false;
            }
        },

        _onTaskTypeChange() {
            const model = this._models.find(m => m.key === document.getElementById('vs-model')?.value);
            if (!model) return;
            this._updateDurationOptions(model, true);
            this._updateCharCount();
            this._updateCostEstimate();
        },

        _updateRegionForModel(model) {
            const regionSel = document.getElementById('vs-region');
            if (!regionSel) return;

            const regions = model.available_regions || [model.region];
            const price = model.base_price_per_second_usd;
            const currentValue = regionSel.value;

            regionSel.innerHTML = '';

            if (regions.length <= 1) {
                const r = regions[0] || model.region || '';
                const opt = document.createElement('option');
                opt.value = r;
                opt.textContent = price ? `${r} ($${price}/sec)` : r;
                regionSel.appendChild(opt);
            } else {
                // Auto option → default region (cheapest for now, same price across regions)
                const defaultRegion = model.region || regions[0];
                const auto = document.createElement('option');
                auto.value = '';
                auto.textContent = price
                    ? `${t('video_studio.auto')} \u2014 ${defaultRegion} ($${price}/sec)`
                    : `${t('video_studio.auto')} \u2014 ${defaultRegion}`;
                regionSel.appendChild(auto);

                regions.forEach(r => {
                    const opt = document.createElement('option');
                    opt.value = r;
                    opt.textContent = price ? `${r} ($${price}/sec)` : r;
                    regionSel.appendChild(opt);
                });
            }

            // Restore previous selection if still valid
            if (currentValue && regions.includes(currentValue)) {
                regionSel.value = currentValue;
            }
        },

        _updateModelSummary() {
            const summary = document.getElementById('vs-model-summary');
            if (!summary) return;
            const model = this._models.find(m => m.key === document.getElementById('vs-model')?.value);
            if (!model) { summary.textContent = ''; return; }

            const region = document.getElementById('vs-region')?.value || model.region || '';
            const price = model.base_price_per_second_usd;
            const priceStr = price ? `$${price}/sec` : '';
            const regionCount = (model.available_regions || []).length;
            const regionNote = regionCount > 1 ? `${regionCount} regions available` : '';

            summary.textContent = [region, priceStr, regionNote].filter(Boolean).join(' \u00B7 ');
        },

        _updateDurationOptions(model, isNovaReel) {
            const durSel = document.getElementById('vs-duration');
            if (!durSel) return;

            if (isNovaReel) {
                const taskType = document.getElementById('vs-task-type')?.value || 'TEXT_VIDEO';
                const tt = model.task_types?.[taskType];
                durSel.innerHTML = '';
                if (taskType === 'TEXT_VIDEO') {
                    durSel.innerHTML = `<option value="6">6 ${t('video_studio.seconds')}</option>`;
                } else {
                    const min = tt?.min_duration || 6;
                    const max = tt?.max_duration || 120;
                    const step = tt?.duration_step || 6;
                    for (let d = min; d <= max; d += step) {
                        const opt = document.createElement('option');
                        opt.value = d;
                        opt.textContent = d >= 60 ? `${Math.floor(d/60)}m ${d%60 ? d%60 + 's' : ''}` : `${d} ${t('video_studio.seconds')}`;
                        durSel.appendChild(opt);
                    }
                }
            } else {
                // Luma: 5s or 9s
                const opts = model.parameters?.duration?.options || ['5s', '9s'];
                durSel.innerHTML = opts.map(o => `<option value="${o}">${o}</option>`).join('');
            }
        },

        _updateCharCount() {
            const prompt = document.getElementById('vs-prompt')?.value || '';
            const model = this._models.find(m => m.key === document.getElementById('vs-model')?.value);
            let limit = model?.prompt_limit || 512;

            // Nova Reel: task type may have different limit
            if (model?.format_family === 'nova_reel') {
                const taskType = document.getElementById('vs-task-type')?.value || 'TEXT_VIDEO';
                const tt = model.task_types?.[taskType];
                if (tt?.prompt_limit) limit = tt.prompt_limit;
            }

            const counter = document.getElementById('vs-char-count');
            if (counter) {
                counter.textContent = `${prompt.length} / ${limit}`;
                counter.classList.toggle('text-red-400', prompt.length > limit);
            }
        },

        _updateCostEstimate() {
            const el = document.getElementById('vs-cost-estimate');
            if (!el) return;
            const model = this._models.find(m => m.key === document.getElementById('vs-model')?.value);
            if (!model || !model.base_price_per_second_usd) { el.textContent = ''; return; }

            const durSel = document.getElementById('vs-duration');
            let seconds = parseInt(durSel?.value) || 6;
            if (String(durSel?.value).endsWith('s')) seconds = parseInt(durSel.value);

            const cost = (seconds * model.base_price_per_second_usd).toFixed(2);
            el.textContent = t('video_studio.est_cost_detail')
                .replace('{{cost}}', cost)
                .replace('{{seconds}}', seconds)
                .replace('{{rate}}', model.base_price_per_second_usd);
        },

        // ── Source image handling ───────────────────────────────────

        _sourceImageB64: null,

        _onSourceImage(e) {
            const file = e.target?.files?.[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => {
                this._sourceImageB64 = reader.result.split(',')[1]; // strip data: prefix
                const img = document.getElementById('vs-source-img');
                if (img) img.src = reader.result;
                document.getElementById('vs-source-preview')?.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        },

        _clearSourceImage() {
            this._sourceImageB64 = null;
            const input = document.getElementById('vs-source-image');
            if (input) input.value = '';
            document.getElementById('vs-source-preview')?.classList.add('hidden');
        },

        // ── Generation ──────────────────────────────────────────────

        async _generate() {
            // S3 bucket check — open settings if not configured
            if (!this._videoSettings?.s3_bucket) {
                window.showToast?.(t('video_studio.s3_not_configured'), 'warning');
                this._showSettings();
                return;
            }

            const prompt = document.getElementById('vs-prompt')?.value?.trim();
            if (!prompt) {
                window.showToast?.(t('video_studio.enter_prompt'), 'warning');
                return;
            }

            const modelKey = document.getElementById('vs-model')?.value;
            if (!modelKey) {
                window.showToast?.(t('video_studio.select_model'), 'warning');
                return;
            }

            const model = this._models.find(m => m.key === modelKey);
            const isNovaReel = model?.format_family === 'nova_reel';
            const isLuma = model?.format_family === 'luma_ray';

            // Region override (empty string = use model default)
            const regionOverride = document.getElementById('vs-region')?.value || undefined;

            const payload = {
                model_key: modelKey,
                prompt,
                enhance_prompt: document.getElementById('vs-enhance')?.checked ?? true,
                seed: document.getElementById('vs-seed')?.value ? parseInt(document.getElementById('vs-seed').value) : undefined,
                region_override: regionOverride,
            };

            // Duration
            const durVal = document.getElementById('vs-duration')?.value;
            if (durVal) payload.duration = isLuma ? durVal : parseInt(durVal);

            // Task type (Nova Reel)
            if (isNovaReel) {
                payload.task_type = document.getElementById('vs-task-type')?.value || 'TEXT_VIDEO';
            }

            // Luma-specific
            if (isLuma) {
                payload.aspect_ratio = document.getElementById('vs-aspect')?.value;
                payload.resolution = document.getElementById('vs-resolution')?.value;
                payload.loop = document.getElementById('vs-loop')?.checked || false;
            }

            // Source image
            if (this._sourceImageB64) {
                payload.source_image = this._sourceImageB64;
            }

            const btn = document.getElementById('vs-generate-btn');
            if (btn) { btn.disabled = true; btn.textContent = t('video_studio.starting'); }

            try {
                const job = await API.video.generate(payload);
                window.showToast?.(`${t('video_studio.started')}: ${job.model_label}`, 'success');

                // Show prompt info
                this._showPromptInfo(job);

                this._activeJobs.push(job);
                this._renderJobsList(this._activeJobs.filter(j => j.status === 'InProgress'));
                this._startPolling(job.job_id);
            } catch (err) {
                const msg = err.message || '';
                const isS3Issue = msg.includes('S3') || msg.includes('bucket') || msg.includes('s3');
                if (isS3Issue) {
                    window.showToast?.(t('video_studio.s3_issue'), 'warning');
                    this._showSettings();
                    // Pre-fill the status with the error
                    const statusEl = document.getElementById('vs-s3-status');
                    if (statusEl) {
                        statusEl.classList.remove('hidden');
                        statusEl.className = 'text-xs p-2 rounded bg-red-950/50 text-red-300';
                        statusEl.textContent = msg;
                    }
                } else {
                    window.showToast?.(t('video_studio.generation_failed').replace('{{msg}}', msg), 'error');
                }
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> ${t('video_studio.generate')}`;
                }
            }
        },

        _showPromptInfo(job) {
            const section = document.getElementById('vs-prompt-info');
            if (!section) return;

            section.classList.remove('hidden');

            const origEl = document.getElementById('vs-original-prompt');
            if (origEl) origEl.textContent = job.original_prompt || job.prompt || '';

            const enhSection = document.getElementById('vs-enhanced-prompt-section');
            const enhEl = document.getElementById('vs-enhanced-prompt');
            if (job.enhanced_prompt && job.enhanced_prompt !== job.original_prompt) {
                enhSection?.classList.remove('hidden');
                if (enhEl) enhEl.textContent = job.enhanced_prompt;
            } else {
                enhSection?.classList.add('hidden');
            }

            const negSection = document.getElementById('vs-negative-section');
            const negEl = document.getElementById('vs-negative-concepts');
            if (job.negative_concepts) {
                negSection?.classList.remove('hidden');
                if (negEl) negEl.textContent = job.negative_concepts;
            } else {
                negSection?.classList.add('hidden');
            }
        },

        _reset() {
            // Clear prompt
            const prompt = document.getElementById('vs-prompt');
            if (prompt) prompt.value = '';
            this._updateCharCount();

            // Reset model to first option
            const modelSel = document.getElementById('vs-model');
            if (modelSel && modelSel.options.length > 0) modelSel.selectedIndex = 0;
            this._onModelChange();

            // Clear seed
            const seed = document.getElementById('vs-seed');
            if (seed) seed.value = '';

            // Clear source image
            this._clearSourceImage();

            // Reset enhance checkbox
            const enhance = document.getElementById('vs-enhance');
            if (enhance) enhance.checked = true;

            // Hide prompt info
            document.getElementById('vs-prompt-info')?.classList.add('hidden');

            // Re-render active jobs — they must persist across resets
            this._renderJobsList(this._activeJobs.filter(j => j.status === 'InProgress'));

            // Focus prompt
            prompt?.focus();
        },

        // ── Polling ─────────────────────────────────────────────────

        _startPolling(jobId) {
            if (this._pollTimers[jobId]) return;
            this._pollTimers[jobId] = setInterval(async () => {
                try {
                    const status = await API.video.status(jobId);
                    // Update in active jobs
                    const idx = this._activeJobs.findIndex(j => j.job_id === jobId);
                    if (idx >= 0) this._activeJobs[idx] = status;

                    if (status.status === 'Completed') {
                        this._stopPolling(jobId);
                        window.showToast?.(t('video_studio.complete'), 'success');
                        this._loadRecentJobs();
                        // Refresh gallery if visible
                        if (window.Gallery?.refresh) window.Gallery.refresh();
                    } else if (status.status === 'Failed') {
                        this._stopPolling(jobId);
                        window.showToast?.(t('video_studio.video_failed').replace('{{msg}}', status.failure_message || t('common.unknown')), 'error');
                        this._renderJobsList(this._activeJobs.filter(j => j.status === 'InProgress'));
                    }
                    this._renderJobsList(this._activeJobs.filter(j => j.status === 'InProgress'));
                } catch (_) {}
            }, POLL_INTERVAL);
        },

        _stopPolling(jobId) {
            if (this._pollTimers[jobId]) {
                clearInterval(this._pollTimers[jobId]);
                delete this._pollTimers[jobId];
            }
        },

        // ── Rendering ───────────────────────────────────────────────

        _renderJobsList(jobs) {
            const container = document.getElementById('vs-jobs-list');
            const section = document.getElementById('vs-jobs-section');
            if (!container) return;

            if (section) section.classList.toggle('hidden', jobs.length === 0);
            if (jobs.length === 0) return;

            container.innerHTML = jobs.map(j => {
                const elapsed = j.started_at ? _timeSince(j.started_at) : '';
                const hasEnhanced = j.enhanced_prompt && j.enhanced_prompt !== j.original_prompt;
                return `
                    <div class="p-3 rounded-lg bg-brand-bg border border-brand-border space-y-1.5">
                        <div class="flex items-center gap-2">
                            <div class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></div>
                            <span class="text-xs font-medium">${_esc(j.model_label || j.model_key)}</span>
                            ${hasEnhanced ? `<span class="text-[9px] text-brand-accent">${t('video_studio.ai_enhanced')}</span>` : ''}
                        </div>
                        <p class="text-xs text-brand-text-muted line-clamp-2">${_esc(j.original_prompt || j.prompt || '')}</p>
                        ${hasEnhanced ? `<details class="group"><summary class="text-[10px] text-brand-accent cursor-pointer">${t('video_studio.show_enhanced')}</summary><p class="text-[10px] text-brand-text/50 mt-1 leading-relaxed">${_esc(j.enhanced_prompt)}</p></details>` : ''}
                        <div class="text-[10px] text-brand-text-muted/70">${j.job_id} · ${elapsed}</div>
                    </div>
                `;
            }).join('');
        },

        _renderCompletedGrid(jobs) {
            const container = document.getElementById('vs-completed-grid');
            const section = document.getElementById('vs-completed');
            if (!container || !section) return;

            if (jobs.length === 0) {
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');
            container.innerHTML = jobs.map(j => {
                const thumbUrl = API.video.thumbnailUrl(j.job_id || j.video_id);
                const dur = j.duration_seconds ? `${Math.round(j.duration_seconds)}s` : '';
                const model = j.model_label || j.model_key || '';
                return `
                    <div class="card cursor-pointer overflow-hidden group video-card" data-job-id="${_esc(j.job_id || j.video_id)}">
                        <div class="aspect-video bg-brand-bg relative overflow-hidden">
                            <img src="${thumbUrl}" alt="Video thumbnail"
                                 class="w-full h-full object-cover" loading="lazy"
                                 onerror="this.style.display='none'">
                            <div class="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
                                <svg class="w-12 h-12 text-white/90" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M8 5v14l11-7z"/>
                                </svg>
                            </div>
                            ${dur ? `<span class="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] px-1.5 py-0.5 rounded">${dur}</span>` : ''}
                        </div>
                        <div class="p-3 space-y-1">
                            <p class="text-xs text-brand-text line-clamp-2">${_esc(j.original_prompt || j.prompt || '')}</p>
                            <div class="text-[10px] text-brand-text-muted">${model}</div>
                        </div>
                    </div>
                `;
            }).join('');

            // Click → play video
            container.querySelectorAll('.video-card').forEach(card => {
                card.addEventListener('click', () => {
                    const jobId = card.dataset.jobId;
                    this._openVideoPlayer(jobId);
                });
            });
        },

        _openVideoPlayer(videoId) {
            const mp4Url = API.video.mp4Url(videoId);
            const overlay = document.createElement('div');
            overlay.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm overflow-auto py-8';
            overlay.innerHTML = `
                <div class="relative max-w-4xl w-full mx-4">
                    <button class="vs-player-close absolute -top-10 right-0 text-white text-2xl hover:text-brand-accent z-10">&times;</button>
                    <video controls autoplay class="w-full rounded-lg shadow-2xl" src="${mp4Url}">
                        ${t('video_studio.browser_no_video')}
                    </video>
                    <!-- Prompt info (loaded from metadata) -->
                    <div class="vs-player-meta mt-3 rounded-lg bg-brand-surface/90 p-4 space-y-2 hidden">
                        <div class="vs-meta-original">
                            <p class="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold mb-0.5">${t('video_studio.original_prompt')}</p>
                            <p class="vs-meta-original-text text-sm text-brand-text/80 leading-relaxed"></p>
                        </div>
                        <div class="vs-meta-enhanced hidden">
                            <p class="text-[10px] text-brand-accent uppercase tracking-wider font-semibold mb-0.5">${t('video_studio.enhanced_prompt')}</p>
                            <p class="vs-meta-enhanced-text text-sm text-brand-text/60 leading-relaxed"></p>
                        </div>
                        <div class="vs-meta-negative hidden">
                            <p class="text-[10px] text-amber-400/80 uppercase tracking-wider font-semibold mb-0.5">${t('video_studio.negative_concepts')}</p>
                            <p class="vs-meta-negative-text text-sm text-amber-300/60 leading-relaxed italic"></p>
                        </div>
                        <div class="flex flex-wrap gap-3 text-[10px] text-brand-text-muted pt-1">
                            <span class="vs-meta-model"></span>
                            <span class="vs-meta-duration"></span>
                            <span class="vs-meta-region"></span>
                        </div>
                    </div>
                    <div class="flex gap-2 mt-3 justify-center">
                        <button class="btn btn-secondary btn-sm vs-revise-btn" data-video-id="${_esc(videoId)}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                            ${t('video_studio.revise')}
                        </button>
                        <button class="btn btn-secondary btn-sm vs-delete-btn" data-video-id="${_esc(videoId)}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                            ${t('video_studio.delete_video')}
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            // Load metadata and populate prompt info
            API.video.metadata(videoId).then(meta => {
                const metaEl = overlay.querySelector('.vs-player-meta');
                if (!metaEl || !meta) return;
                metaEl.classList.remove('hidden');

                const origText = metaEl.querySelector('.vs-meta-original-text');
                if (origText) origText.textContent = meta.original_prompt || meta.prompt || '';

                if (meta.enhanced_prompt && meta.enhanced_prompt !== meta.original_prompt) {
                    const enhSection = metaEl.querySelector('.vs-meta-enhanced');
                    const enhText = metaEl.querySelector('.vs-meta-enhanced-text');
                    enhSection?.classList.remove('hidden');
                    if (enhText) enhText.textContent = meta.enhanced_prompt;
                }

                if (meta.negative_concepts) {
                    const negSection = metaEl.querySelector('.vs-meta-negative');
                    const negText = metaEl.querySelector('.vs-meta-negative-text');
                    negSection?.classList.remove('hidden');
                    if (negText) negText.textContent = meta.negative_concepts;
                }

                const modelEl = metaEl.querySelector('.vs-meta-model');
                if (modelEl) modelEl.textContent = `${t('video_studio.meta_model')}: ${meta.model_label || meta.model_key || ''}`;
                const durEl = metaEl.querySelector('.vs-meta-duration');
                if (durEl && meta.duration_seconds) durEl.textContent = `${t('video_studio.meta_duration')}: ${Math.round(meta.duration_seconds)}s`;
                const regEl = metaEl.querySelector('.vs-meta-region');
                if (regEl && meta.region) regEl.textContent = `${t('video_studio.meta_region')}: ${meta.region}`;
            }).catch(() => {});

            // Close handlers
            overlay.querySelector('.vs-player-close')?.addEventListener('click', () => overlay.remove());
            overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

            // Revise handler
            overlay.querySelector('.vs-revise-btn')?.addEventListener('click', async () => {
                overlay.remove();
                try {
                    const meta = await API.video.metadata(videoId);
                    const prompt = document.getElementById('vs-prompt');
                    if (prompt) prompt.value = meta.original_prompt || meta.prompt || '';
                    this._updateCharCount();
                    window.showToast?.(t('video_studio.prompt_loaded'), 'info');
                } catch (_) {}
            });

            // Delete handler
            overlay.querySelector('.vs-delete-btn')?.addEventListener('click', async () => {
                if (!await window.showConfirm(t('video_studio.delete_confirm'), { title: t('video_studio.delete_title'), detail: t('video_studio.delete_detail'), confirmLabel: t('common.delete'), danger: true })) return;
                try {
                    await API.video.delete(videoId);
                    overlay.remove();
                    window.showToast?.(t('video_studio.deleted'), 'success');
                    this._loadRecentJobs();
                } catch (_) {}
            });
        },

        // ── Settings dialog ─────────────────────────────────────────

        _showSettings() {
            const dialog = document.getElementById('vs-settings-dialog');
            if (!dialog) return;

            const vs = this._videoSettings || {};
            const bucketInput = document.getElementById('vs-s3-bucket');
            if (bucketInput) {
                bucketInput.value = vs.s3_bucket || '';
            }
            document.getElementById('vs-s3-prefix').value = vs.s3_prefix || 'artsmoker/video/';
            document.getElementById('vs-store-mode').value = vs.store_local === false ? 's3' : 'local';

            // Reset sub-panels and button states
            document.getElementById('vs-bucket-list')?.classList.add('hidden');
            document.getElementById('vs-create-bucket-form')?.classList.add('hidden');
            const statusEl = document.getElementById('vs-s3-status');
            if (statusEl) statusEl.classList.add('hidden');
            const testBtn = document.getElementById('vs-settings-test');
            if (testBtn) { testBtn.disabled = false; testBtn.textContent = t('video_studio.s3_test_save'); }
            document.getElementById('vs-settings-close-bottom')?.classList.add('hidden');

            dialog.classList.remove('hidden');
        },

        _hideSettings() {
            document.getElementById('vs-settings-dialog')?.classList.add('hidden');
        },

        _updateS3Banner() {
            const banner = document.getElementById('vs-s3-banner');
            const content = document.getElementById('vs-s3-banner-content');
            const genBtn = document.getElementById('vs-generate-btn');
            if (!banner || !content) return;

            const vs = this._videoSettings || {};
            banner.classList.remove('hidden');

            if (!vs.s3_bucket) {
                banner.className = banner.className.replace(/bg-\S+/g, '').replace(/border-\S+/g, '') +
                    ' bg-amber-950/30 border-amber-500/30';
                content.innerHTML = `
                    <svg class="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                    </svg>
                    <div>
                        <p class="text-sm text-amber-200 font-medium">${t('video_studio.s3_required')}</p>
                        <p class="text-xs text-amber-300/70 mt-1">${t('video_studio.s3_required_desc')}</p>
                    </div>
                `;
                if (genBtn) genBtn.disabled = true;
            } else {
                const storeMode = vs.store_local !== false ? t('video_studio.s3_local_plus') : t('video_studio.s3_only_label');
                banner.className = banner.className.replace(/bg-\S+/g, '').replace(/border-\S+/g, '') +
                    ' bg-emerald-950/20 border-emerald-500/20';
                content.innerHTML = `
                    <svg class="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <div class="flex-1">
                        <p class="text-sm text-emerald-200 font-medium">${t('video_studio.s3_configured')}: <span class="font-mono">${_esc(vs.s3_bucket)}</span></p>
                        <p class="text-xs text-emerald-300/60 mt-0.5">${t('video_studio.s3_prefix_label')}: ${_esc(vs.s3_prefix || 'artsmoker/video/')} · ${t('video_studio.s3_storage_label')}: ${storeMode}</p>
                    </div>
                `;
            }
        },

        async _testAndSaveSettings() {
            const bucket = document.getElementById('vs-s3-bucket')?.value?.trim();
            const prefix = document.getElementById('vs-s3-prefix')?.value?.trim() || 'artsmoker/video/';
            const storeMode = document.getElementById('vs-store-mode')?.value;
            const statusEl = document.getElementById('vs-s3-status');

            if (!bucket) {
                if (statusEl) {
                    statusEl.classList.remove('hidden');
                    statusEl.className = 'text-xs p-2 rounded bg-red-950/50 text-red-300';
                    statusEl.textContent = t('video_studio.bucket_required');
                }
                return;
            }

            if (statusEl) {
                statusEl.classList.remove('hidden');
                statusEl.className = 'text-xs p-2 rounded bg-blue-950/50 text-blue-300';
                statusEl.textContent = t('video_studio.s3_testing');
            }

            try {
                const result = await API.admin.updateVideoSettings({
                    s3_bucket: bucket,
                    s3_prefix: prefix,
                    store_local: storeMode !== 's3',
                });
                this._videoSettings = result;
                if (statusEl) {
                    statusEl.className = 'text-xs p-2 rounded bg-green-950/50 text-green-300';
                    statusEl.textContent = t('video_studio.s3_validated_msg').replace('{{name}}', bucket);
                }
                // Update banner and enable generation
                this._updateS3Banner();
                const genBtn = document.getElementById('vs-generate-btn');
                if (genBtn && document.getElementById('vs-model')?.value) genBtn.disabled = false;

                // Swap Test & Save → disabled, show Close button
                const testBtn = document.getElementById('vs-settings-test');
                const closeBtn = document.getElementById('vs-settings-close-bottom');
                if (testBtn) { testBtn.disabled = true; testBtn.textContent = t('video_studio.saved'); }
                if (closeBtn) { closeBtn.classList.remove('hidden'); }
                closeBtn?.addEventListener('click', () => this._hideSettings(), { once: true });

                window.showToast?.(t('video_studio.settings_saved'), 'success');
            } catch (err) {
                const msg = err.message || 'S3 validation failed';
                const isNotFound = msg.includes('not found') || msg.includes('does not exist');

                if (isNotFound) {
                    // Bucket doesn't exist — offer to create it
                    if (statusEl) {
                        statusEl.classList.remove('hidden');
                        statusEl.className = 'text-xs p-2 rounded bg-amber-950/50 text-amber-300 space-y-2';
                        statusEl.innerHTML = `
                            <p>${t('video_studio.bucket_not_exist').replace('{{name}}', _esc(bucket))}</p>
                            <div class="flex items-center gap-2">
                                <button id="vs-create-inline-btn" class="btn btn-primary btn-sm text-xs">${t('video_studio.create_it_now')}</button>
                                <select id="vs-create-inline-region" class="input text-xs py-1 px-2 w-28">
                                    <option value="us-east-1">us-east-1</option>
                                    <option value="us-west-2">us-west-2</option>
                                    <option value="eu-west-1">eu-west-1</option>
                                    <option value="ap-northeast-1">ap-northeast-1</option>
                                </select>
                            </div>
                        `;
                        document.getElementById('vs-create-inline-btn')?.addEventListener('click', async () => {
                            const region = document.getElementById('vs-create-inline-region')?.value || 'us-east-1';
                            statusEl.innerHTML = `<p>${t('video_studio.creating_bucket_status')}</p>`;
                            try {
                                await API.browse.createS3Bucket(bucket, region);
                                window.showToast?.(t('video_studio.bucket_created').replace('{{name}}', bucket).replace('{{region}}', region), 'success');
                                // Retry the save now that the bucket exists
                                await this._testAndSaveSettings();
                            } catch (createErr) {
                                statusEl.className = 'text-xs p-2 rounded bg-red-950/50 text-red-300';
                                statusEl.textContent = t('video_studio.create_failed').replace('{{msg}}', createErr.message || '');
                            }
                        });
                    }
                    return;
                }

                if (statusEl) {
                    statusEl.className = 'text-xs p-2 rounded bg-red-950/50 text-red-300';
                    statusEl.textContent = msg;
                }
            }
        },

        // ── S3 Bucket Browser ───────────────────────────────────────

        async _loadBucketList() {
            const listEl = document.getElementById('vs-bucket-list');
            const itemsEl = document.getElementById('vs-bucket-items');
            if (!listEl || !itemsEl) return;

            listEl.classList.remove('hidden');
            document.getElementById('vs-create-bucket-form')?.classList.add('hidden');
            itemsEl.innerHTML = `<div class="text-xs text-brand-text-muted p-3 text-center">${t('video_studio.loading_buckets')}</div>`;

            try {
                const data = await API.browse.s3Buckets();
                const buckets = data.buckets || [];
                if (buckets.length === 0) {
                    itemsEl.innerHTML = `<div class="text-xs text-brand-text-muted p-3 text-center">${t('video_studio.no_buckets')}</div>`;
                    return;
                }
                const currentBucket = document.getElementById('vs-s3-bucket')?.value || '';
                itemsEl.innerHTML = buckets.map(b => `
                    <button class="vs-bucket-item w-full text-left px-3 py-2 text-sm hover:bg-brand-accent/10 transition-colors flex items-center justify-between border-b border-brand-border/30 last:border-0 ${b.name === currentBucket ? 'bg-brand-accent/10 text-brand-accent' : ''}"
                            data-bucket="${_esc(b.name)}">
                        <span class="flex items-center gap-2">
                            <svg class="w-4 h-4 text-brand-text-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                            </svg>
                            ${_esc(b.name)}
                        </span>
                        <span class="text-[10px] text-brand-text-muted">${b.created ? new Date(b.created).toLocaleDateString() : ''}</span>
                    </button>
                `).join('');

                // Click to select bucket
                itemsEl.querySelectorAll('.vs-bucket-item').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const input = document.getElementById('vs-s3-bucket');
                        if (input) input.value = btn.dataset.bucket;
                        listEl.classList.add('hidden');
                    });
                });
            } catch (err) {
                itemsEl.innerHTML = `<div class="text-xs text-red-400 p-3 text-center">${err.message || t('common.error')}</div>`;
            }
        },

        _showCreateBucket() {
            const form = document.getElementById('vs-create-bucket-form');
            form?.classList.remove('hidden');

            // Populate region dropdown from known Bedrock regions
            const regionSel = document.getElementById('vs-new-bucket-region');
            if (regionSel && regionSel.options.length <= 1) {
                const regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                    'eu-west-1', 'eu-west-2', 'eu-central-1', 'ap-northeast-1',
                    'ap-southeast-1', 'ap-southeast-2', 'ap-south-1'];
                regionSel.innerHTML = regions.map(r =>
                    `<option value="${r}" ${r === 'us-east-1' ? 'selected' : ''}>${r}</option>`
                ).join('');
            }
        },

        async _createBucket() {
            const nameInput = document.getElementById('vs-new-bucket-name');
            const regionSel = document.getElementById('vs-new-bucket-region');
            const name = nameInput?.value?.trim();
            const region = regionSel?.value || 'us-east-1';

            if (!name) {
                window.showToast?.(t('video_studio.bucket_name_required'), 'warning');
                return;
            }

            const goBtn = document.getElementById('vs-create-bucket-go');
            if (goBtn) { goBtn.disabled = true; goBtn.textContent = t('video_studio.s3_creating'); }

            try {
                const result = await API.browse.createS3Bucket(name, region);
                window.showToast?.(
                    result.created
                        ? t('video_studio.bucket_created').replace('{{name}}', name).replace('{{region}}', region)
                        : t('video_studio.bucket_exists').replace('{{name}}', name),
                    'success'
                );
                // Set the bucket in the input
                const input = document.getElementById('vs-s3-bucket');
                if (input) input.value = name;
                // Hide create form, refresh bucket list
                document.getElementById('vs-create-bucket-form')?.classList.add('hidden');
                this._loadBucketList();
            } catch (err) {
                window.showToast?.(t('video_studio.create_failed').replace('{{msg}}', err.message || ''), 'error');
            } finally {
                if (goBtn) { goBtn.disabled = false; goBtn.textContent = t('video_studio.s3_create'); }
            }
        },
    };

    // ── Helpers ──────────────────────────────────────────────────────

    function _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function _timeSince(isoStr) {
        try {
            const ms = Date.now() - new Date(isoStr).getTime();
            const s = Math.floor(ms / 1000);
            if (s < 60) return `${s}s ago`;
            const m = Math.floor(s / 60);
            if (m < 60) return `${m}m ago`;
            return `${Math.floor(m / 60)}h ${m % 60}m ago`;
        } catch (_) { return ''; }
    }
})();
