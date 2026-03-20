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
                        <h1 class="text-2xl font-bold">Video Studio</h1>
                        <p class="text-brand-text-muted text-sm mt-1">Generate AI-powered videos and animations from text prompts</p>
                    </div>

                    <div class="flex flex-col lg:flex-row gap-6">

                        <!-- Left Sidebar: Settings -->
                        <aside class="lg:w-72 xl:w-80 flex-shrink-0 space-y-5">
                            <div class="card-static p-5 space-y-5">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
                                    </svg>
                                    Settings
                                </h2>

                                <!-- Model -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Video Model</label>
                                    <select id="vs-model" class="input">
                                        <option value="">Loading models...</option>
                                    </select>
                                    <p id="vs-model-summary" class="text-[10px] text-brand-text-muted mt-1"></p>
                                </div>

                                <!-- Task Type (Nova Reel only) -->
                                <div id="vs-task-type-group" class="hidden">
                                    <label class="block text-sm font-medium mb-1.5">Generation Mode</label>
                                    <select id="vs-task-type" class="input">
                                        <option value="TEXT_VIDEO">Single Shot (6s)</option>
                                        <option value="MULTI_SHOT_AUTOMATED">Multi-Shot Auto (12-120s)</option>
                                        <option value="MULTI_SHOT_MANUAL">Multi-Shot Manual</option>
                                    </select>
                                </div>

                                <!-- Duration -->
                                <div>
                                    <label class="block text-sm font-medium mb-1.5">Duration</label>
                                    <select id="vs-duration" class="input">
                                        <option value="6">6 seconds</option>
                                    </select>
                                </div>

                                <!-- Aspect Ratio (Luma only) -->
                                <div id="vs-aspect-group" class="hidden">
                                    <label class="block text-sm font-medium mb-1.5">Aspect Ratio</label>
                                    <select id="vs-aspect" class="input">
                                        <option value="16:9">16:9</option>
                                    </select>
                                </div>

                                <!-- Resolution (Luma only) -->
                                <div id="vs-resolution-group" class="hidden">
                                    <label class="block text-sm font-medium mb-1.5">Resolution</label>
                                    <select id="vs-resolution" class="input">
                                        <option value="720p">720p</option>
                                    </select>
                                </div>

                                <!-- Loop (Luma only) -->
                                <div id="vs-loop-group" class="hidden">
                                    <label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
                                        <input type="checkbox" id="vs-loop" class="w-4 h-4 rounded border-brand-border bg-brand-bg text-brand-accent focus:ring-brand-accent">
                                        Seamless Loop
                                    </label>
                                </div>

                                <!-- Advanced: Region + Seed -->
                                <details class="group">
                                    <summary class="text-xs font-medium text-brand-text-muted cursor-pointer hover:text-brand-text transition-colors select-none">
                                        <span class="group-open:hidden">\u25B8 Advanced (region, seed)</span>
                                        <span class="hidden group-open:inline">\u25BE Advanced</span>
                                    </summary>
                                    <div class="mt-2 space-y-3 p-2.5 rounded-lg bg-brand-bg/40 border border-brand-border/50">
                                        <div>
                                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1">Region</label>
                                            <select id="vs-region" class="input text-xs">
                                                <option value="">Auto</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label class="block text-[10px] text-brand-text-muted uppercase tracking-wider mb-1">Seed</label>
                                            <input type="number" id="vs-seed" class="input text-xs w-full" placeholder="Random" min="0">
                                        </div>
                                    </div>
                                </details>

                                <!-- Cost estimate -->
                                <div id="vs-cost-estimate" class="text-[10px] text-emerald-400/70 font-mono"></div>

                                <!-- Source Image (optional) -->
                                <details id="vs-image-input-group" class="hidden">
                                    <summary class="text-xs font-medium cursor-pointer text-brand-accent hover:text-brand-accent-hover select-none">
                                        \u25B8 Source Image (Image-to-Video)
                                    </summary>
                                    <div class="mt-2 p-2.5 border border-brand-border/50 rounded-lg bg-brand-bg/40 space-y-2">
                                        <input type="file" id="vs-source-image" accept="image/png,image/jpeg" class="text-xs w-full">
                                        <p class="text-[10px] text-brand-text-muted">Optional: reference image as the first frame.</p>
                                        <div id="vs-source-preview" class="hidden">
                                            <img id="vs-source-img" class="max-h-24 rounded border border-brand-border" alt="Source">
                                            <button id="vs-clear-source" class="btn btn-secondary btn-sm mt-1 text-[10px]">Clear</button>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <!-- Video Settings button -->
                            <button id="vs-settings-btn" class="w-full text-left p-3 rounded-lg bg-brand-bg/30 border border-brand-border/50 hover:border-brand-accent/30 hover:bg-brand-bg/50 transition-colors flex items-center gap-2 text-xs text-brand-text-muted">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                                Video Settings (S3 Storage)
                            </button>
                        </aside>

                        <!-- Center: Prompt + Generate + Jobs + Results -->
                        <div class="flex-1 min-w-0 space-y-5">

                            <!-- S3 Setup Banner (shown when bucket not configured) -->
                            <div id="vs-s3-banner" class="hidden card-static p-4 bg-amber-950/30 border-amber-500/30">
                                <div class="flex items-start gap-3">
                                    <svg class="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                    </svg>
                                    <div>
                                        <p class="text-sm text-amber-200 font-medium">S3 Bucket Required</p>
                                        <p class="text-xs text-amber-300/70 mt-1">Video generation outputs to Amazon S3. Configure your S3 bucket in Video Settings to get started.</p>
                                    </div>
                                </div>
                            </div>

                            <!-- Prompt -->
                            <div class="card-static p-5 space-y-4">
                                <h2 class="text-lg font-semibold flex items-center gap-2">
                                    <svg class="w-5 h-5 text-brand-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                    </svg>
                                    Prompt
                                </h2>
                                <textarea id="vs-prompt" rows="4" class="input w-full"
                                    placeholder="Describe the video scene you want to generate..."></textarea>
                                <div class="flex items-center justify-between">
                                    <span id="vs-char-count" class="text-xs text-brand-text-muted">0 / 512</span>
                                    <label class="flex items-center gap-1.5 text-xs text-brand-text-muted cursor-pointer">
                                        <input type="checkbox" id="vs-enhance" checked class="w-3.5 h-3.5 rounded border-brand-border bg-brand-bg text-brand-accent focus:ring-brand-accent">
                                        AI-enhance prompt
                                    </label>
                                </div>
                            </div>

                            <!-- Generate Button -->
                            <button id="vs-generate-btn" class="btn btn-primary btn-lg text-base w-full" disabled>
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                Generate Video
                            </button>

                            <!-- Active Jobs -->
                            <div id="vs-jobs-section" class="card-static p-4 hidden">
                                <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
                                    <div class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></div>
                                    Active Jobs
                                </h3>
                                <div id="vs-jobs-list" class="space-y-3"></div>
                            </div>

                            <!-- Completed Videos -->
                            <div id="vs-completed" class="hidden space-y-4">
                                <h2 class="text-lg font-semibold">Recent Videos</h2>
                                <div id="vs-completed-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Video Settings Dialog -->
                <div id="vs-settings-dialog" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div class="card-static p-6 w-full max-w-md space-y-4">
                        <div class="flex items-center justify-between">
                            <h3 class="text-lg font-semibold">Video Settings</h3>
                            <button id="vs-settings-close" class="text-brand-text-muted hover:text-brand-text">&times;</button>
                        </div>
                        <div class="space-y-3">
                            <div>
                                <label class="block text-sm font-medium mb-1">S3 Bucket Name</label>
                                <input type="text" id="vs-s3-bucket" class="input w-full" placeholder="my-artsmoker-bucket">
                                <p class="text-xs text-brand-text-muted mt-1">The S3 bucket where videos will be stored. Must have read/write access.</p>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1">S3 Prefix</label>
                                <input type="text" id="vs-s3-prefix" class="input w-full" placeholder="artsmoker/video/" value="artsmoker/video/">
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1">Video Storage</label>
                                <select id="vs-store-mode" class="input w-full">
                                    <option value="local">Download & store locally (recommended)</option>
                                    <option value="s3">Keep on S3 only (stream on demand)</option>
                                </select>
                                <p class="text-xs text-brand-text-muted mt-1">
                                    <strong>Local:</strong> Videos are downloaded after generation for fast playback.<br>
                                    <strong>S3 only:</strong> Videos stream from S3 each time. Saves disk space.
                                </p>
                            </div>
                            <div id="vs-s3-status" class="hidden text-xs p-2 rounded"></div>
                            <div class="flex gap-2 justify-end">
                                <button id="vs-settings-test" class="btn btn-secondary btn-sm">Test & Save</button>
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

            // Generate button
            document.getElementById('vs-generate-btn')?.addEventListener('click', () => this._generate());

            // Settings dialog
            document.getElementById('vs-settings-btn')?.addEventListener('click', () => this._showSettings());
            document.getElementById('vs-settings-close')?.addEventListener('click', () => this._hideSettings());
            document.getElementById('vs-settings-test')?.addEventListener('click', () => this._testAndSaveSettings());

            // Source image upload
            const fileInput = document.getElementById('vs-source-image');
            fileInput?.addEventListener('change', (e) => this._onSourceImage(e));
            document.getElementById('vs-clear-source')?.addEventListener('click', () => this._clearSourceImage());

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
            const banner = document.getElementById('vs-s3-banner');
            const genBtn = document.getElementById('vs-generate-btn');
            if (!this._videoSettings.s3_bucket) {
                banner?.classList.remove('hidden');
                if (genBtn) genBtn.disabled = true;
            } else {
                banner?.classList.add('hidden');
            }
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
                sel.innerHTML = '<option value="">No video models found — run Sync from AWS</option>';
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
                    ? `Auto \u2014 ${defaultRegion} ($${price}/sec)`
                    : `Auto \u2014 ${defaultRegion}`;
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
                    durSel.innerHTML = '<option value="6">6 seconds</option>';
                } else {
                    const min = tt?.min_duration || 6;
                    const max = tt?.max_duration || 120;
                    const step = tt?.duration_step || 6;
                    for (let d = min; d <= max; d += step) {
                        const opt = document.createElement('option');
                        opt.value = d;
                        opt.textContent = d >= 60 ? `${Math.floor(d/60)}m ${d%60 ? d%60 + 's' : ''}` : `${d} seconds`;
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
            el.textContent = `Estimated cost: ~$${cost} (${seconds}s × $${model.base_price_per_second_usd}/s)`;
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
            const prompt = document.getElementById('vs-prompt')?.value?.trim();
            if (!prompt) {
                window.showToast?.('Please enter a video prompt', 'warning');
                return;
            }

            const modelKey = document.getElementById('vs-model')?.value;
            if (!modelKey) {
                window.showToast?.('Please select a model', 'warning');
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
            if (btn) { btn.disabled = true; btn.textContent = 'Starting...'; }

            try {
                const job = await API.video.generate(payload);
                window.showToast?.(`Video generation started: ${job.model_label}`, 'success');
                this._activeJobs.push(job);
                this._renderJobsList(this._activeJobs.filter(j => j.status === 'InProgress'));
                this._startPolling(job.job_id);
            } catch (err) {
                window.showToast?.('Generation failed: ' + err.message, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Generate Video`;
                }
            }
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
                        window.showToast?.('Video generation complete!', 'success');
                        this._loadRecentJobs();
                        // Refresh gallery if visible
                        if (window.Gallery?.refresh) window.Gallery.refresh();
                    } else if (status.status === 'Failed') {
                        this._stopPolling(jobId);
                        window.showToast?.(`Video failed: ${status.failure_message || 'Unknown error'}`, 'error');
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
                return `
                    <div class="p-3 rounded-lg bg-brand-bg border border-brand-border space-y-1.5">
                        <div class="flex items-center gap-2">
                            <div class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></div>
                            <span class="text-xs font-medium">${_esc(j.model_label || j.model_key)}</span>
                        </div>
                        <p class="text-xs text-brand-text-muted line-clamp-2">${_esc(j.original_prompt || j.prompt || '')}</p>
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
            // Simple modal video player
            const mp4Url = API.video.mp4Url(videoId);
            const overlay = document.createElement('div');
            overlay.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm';
            overlay.innerHTML = `
                <div class="relative max-w-4xl w-full mx-4">
                    <button class="absolute -top-10 right-0 text-white text-2xl hover:text-brand-accent z-10">&times;</button>
                    <video controls autoplay class="w-full rounded-lg shadow-2xl" src="${mp4Url}">
                        Your browser does not support video playback.
                    </video>
                    <div class="flex gap-2 mt-3 justify-center">
                        <button class="btn btn-secondary btn-sm vs-revise-btn" data-video-id="${_esc(videoId)}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                            Revise
                        </button>
                        <button class="btn btn-secondary btn-sm vs-delete-btn" data-video-id="${_esc(videoId)}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                            Delete
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            // Close handlers
            overlay.querySelector('button')?.addEventListener('click', () => overlay.remove());
            overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

            // Revise handler
            overlay.querySelector('.vs-revise-btn')?.addEventListener('click', async () => {
                overlay.remove();
                try {
                    const meta = await API.video.metadata(videoId);
                    const prompt = document.getElementById('vs-prompt');
                    if (prompt) prompt.value = meta.original_prompt || meta.prompt || '';
                    this._updateCharCount();
                    window.showToast?.('Prompt loaded for revision. Edit and re-generate.', 'info');
                } catch (_) {}
            });

            // Delete handler
            overlay.querySelector('.vs-delete-btn')?.addEventListener('click', async () => {
                if (!confirm('Delete this video permanently?')) return;
                try {
                    await API.video.delete(videoId);
                    overlay.remove();
                    window.showToast?.('Video deleted', 'success');
                    this._loadRecentJobs();
                } catch (_) {}
            });
        },

        // ── Settings dialog ─────────────────────────────────────────

        _showSettings() {
            const dialog = document.getElementById('vs-settings-dialog');
            if (!dialog) return;

            const vs = this._videoSettings || {};
            document.getElementById('vs-s3-bucket').value = vs.s3_bucket || '';
            document.getElementById('vs-s3-prefix').value = vs.s3_prefix || 'artsmoker/video/';
            document.getElementById('vs-store-mode').value = vs.store_local === false ? 's3' : 'local';

            const statusEl = document.getElementById('vs-s3-status');
            if (statusEl) statusEl.classList.add('hidden');

            dialog.classList.remove('hidden');
        },

        _hideSettings() {
            document.getElementById('vs-settings-dialog')?.classList.add('hidden');
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
                    statusEl.textContent = 'Bucket name is required.';
                }
                return;
            }

            if (statusEl) {
                statusEl.classList.remove('hidden');
                statusEl.className = 'text-xs p-2 rounded bg-blue-950/50 text-blue-300';
                statusEl.textContent = 'Testing S3 access...';
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
                    statusEl.textContent = `S3 bucket "${bucket}" validated. Read/write access confirmed.`;
                }
                // Hide the S3 banner and enable generation
                document.getElementById('vs-s3-banner')?.classList.add('hidden');
                const genBtn = document.getElementById('vs-generate-btn');
                if (genBtn && document.getElementById('vs-model')?.value) genBtn.disabled = false;

                window.showToast?.('Video settings saved', 'success');
            } catch (err) {
                if (statusEl) {
                    statusEl.className = 'text-xs p-2 rounded bg-red-950/50 text-red-300';
                    statusEl.textContent = err.message || 'S3 validation failed';
                }
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
