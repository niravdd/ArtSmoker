/**
 * ArtSmoker — PromptEditor Component
 *
 * Two-area prompt editor:
 *   1. User prompt textarea — the artist writes here in their own words
 *   2. Composed generation prompt — AI-enhanced version combining user prompt
 *      with style guidelines, asset type directives, and quality details
 *
 * The composed prompt is what actually gets sent to the image model.
 * "Compose Generation Prompt" button triggers the AI composition.
 */
(function () {
    'use strict';

    // Realistic example prompts per asset type — written as a real person would start describing
    const _ASSET_PLACEHOLDERS = {
        game_asset: "A weathered wooden treasure chest with iron straps and a brass lock, slightly open with golden light spilling out...",
        character: "A young female warrior in ornate silver armor, long dark hair braided, holding a glowing sword, standing on a cliff edge at sunset...",
        environment: "A misty Japanese garden at dawn, stone lanterns lining a curved path through moss-covered rocks, cherry blossoms drifting in still air...",
        marketing_banner: "An epic dragon soaring over a burning medieval castle, dramatic storm clouds and lightning, armies clashing below...",
        icon: "A golden shield with a dragon emblem, simple bold design...",
        photorealistic: "A woman standing at a rain-soaked city intersection at night, neon signs reflecting in puddles, shot on a 35mm lens with shallow depth of field...",
    };

    const _ASSET_STEP_LABEL_KEYS = {
        game_asset: "image_studio.step1_game_asset",
        character: "image_studio.step1_character",
        environment: "image_studio.step1_environment",
        marketing_banner: "image_studio.step1_banner",
        icon: "image_studio.step1_icon",
        photorealistic: "image_studio.step1_photo",
    };

    class PromptEditor {
        constructor(container, opts = {}) {
            this.container = container;
            this.opts = opts;
            this._changeCb = null;
            this._composedText = null;
            this._userComposed = false;  // true only when user clicked "Compose"
            this._originalText = null;
            this._moderationOriginal = null;
            this._isComposing = false;
            this._assetTypeConfirmed = false;  // true after first classification check
            this._decomposedData = null;       // saved decomposition from Prompt Designer

            this._render();
            this._attachEvents();
            this._updateAssetContext();
        }

        // -- Public API --

        /** Get the prompt to send to generation. Returns composed if available, else user text. */
        getText() {
            return this._composedText || this._textareaEl.value;
        }

        /** Get the raw user prompt (before any AI composition). */
        getUserText() {
            return this._textareaEl.value;
        }

        /** Get the original user prompt before any modifications. */
        getOriginalText() {
            return this._originalText || this._textareaEl.value;
        }

        /** Get the composed prompt (null if not yet composed). */
        getComposedText() {
            return this._composedText;
        }

        /** Check if the user explicitly composed a prompt (via button click). */
        hasComposedPrompt() {
            return !!this._composedText && this._userComposed;
        }

        /** Get the negative prompt extracted during composition. */
        getNegativePrompt() {
            return this._negativePrompt || '';
        }

        setText(text) {
            this._textareaEl.value = text;
            this._updateCharCount();
            // Clear composed prompt when user text changes externally
            this._clearComposed();
            if (this._changeCb) this._changeCb(text);
        }

        setComposedText(text) {
            this._composedText = text;
            this._userComposed = true; // Treat programmatic composed text same as user-composed
            this._showComposed(text);
        }

        setDecomposedText(text) {
            const panel = this.container.querySelector('.decomposed-panel');
            const textarea = this.container.querySelector('.decomposed-textarea');
            if (panel && textarea) {
                textarea.value = text || '';
                // Show the Step-2 box only when there's consolidated text; hide it
                // when cleared (empty) so we don't leave a blank panel behind.
                panel.classList.toggle('hidden', !(text && text.trim()));
            }
        }

        getDecomposedText() {
            const textarea = this.container.querySelector('.decomposed-textarea');
            return textarea?.value || '';
        }

        onChanged(cb) {
            this._changeCb = cb;
        }

        setContext(opts) {
            this.opts = { ...this.opts, ...opts };
            this._updateStyleNote();
            this._updateAssetContext();
            // Clear composed prompt when context changes (style/type switched)
            if (this._composedText) {
                this._clearComposed();
            }
        }

        destroy() {
            if (this._voice) this._voice.destroy();
            this.container.innerHTML = '';
        }

        // -- Private --

        _render() {
            // nosemgrep
            this.container.innerHTML = html`
                <div class="prompt-editor space-y-3">
                    <!-- Step 1: User prompt -->
                    <div>
                        <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[10px] font-bold text-brand-accent bg-brand-accent/10 rounded px-1.5 py-0.5">${typeof t !== 'undefined' ? t('prompt_editor.step') : 'STEP'} 1</span>
                            <span class="text-[10px] text-brand-text-muted uppercase tracking-wide step1-label">${typeof t !== 'undefined' ? t('prompt_editor.step1_describe') : 'Describe your idea'}</span>
                            <div class="voice-container ml-auto"></div>
                        </div>
                        <div class="relative">
                            <textarea
                                id="prompt-textarea"
                                class="input w-full min-h-[100px] pr-12"
                                placeholder="${typeof t !== 'undefined' ? t('prompt_editor.placeholder') : 'Describe what you want to generate...'}"
                                rows="3"
                            ></textarea>
                            <div class="absolute bottom-2 right-2 flex items-center gap-1">
                                <span class="char-count text-xs text-brand-text-muted tabular-nums">0</span>
                            </div>
                        </div>
                        <p class="prompt-language-hint text-[9px] text-brand-text-muted/50 mt-0.5 ${typeof i18n !== 'undefined' && i18n.getLang() === 'en' ? 'hidden' : ''}">${typeof t !== 'undefined' ? t('image_studio.prompt_language_hint') : ''}</p>
                    </div>

                    <!-- Translation preview (shown when non-English detected) -->
                    <div class="translation-preview hidden">
                        <div class="flex items-center gap-1 mb-1">
                            <span class="translation-lang-badge text-[9px] px-1.5 py-0.5 rounded bg-brand-accent/15 text-brand-accent font-medium"></span>
                            <div class="flex gap-0.5 ml-auto">
                                <button type="button" class="translation-tab-original text-[10px] px-2 py-0.5 rounded bg-brand-accent text-white font-medium">${typeof t !== 'undefined' ? t('common.prompt') : 'Original'}</button>
                                <button type="button" class="translation-tab-english text-[10px] px-2 py-0.5 rounded bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent">English</button>
                            </div>
                        </div>
                        <div class="translation-english-text hidden p-2 rounded-lg bg-emerald-950/10 border border-emerald-500/20 text-xs text-brand-text/70 whitespace-pre-wrap max-h-24 overflow-auto"></div>
                    </div>

                    <!-- Step 2: Prompt Designer (optional) -->
                    <div>
                        <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[10px] font-bold text-amber-400 bg-amber-400/10 rounded px-1.5 py-0.5">${typeof t !== 'undefined' ? t('prompt_editor.step') : 'STEP'} 2</span>
                            <span class="text-[10px] text-brand-text-muted uppercase tracking-wide">${typeof t !== 'undefined' ? t('prompt_editor.step2_refine') : 'Decompose & refine'}</span>
                            <span class="text-[9px] text-brand-text-muted/40 italic ml-1">${typeof t !== 'undefined' ? t('common.optional') : 'optional'}</span>
                        </div>
                        <button type="button" class="btn-prompt-designer text-xs py-2.5 w-full rounded-lg flex items-center justify-center gap-2 bg-amber-500/15 border border-amber-500/30 text-amber-300 hover:bg-amber-500/25 hover:border-amber-500/50 transition-all font-medium">
                            <span>🎨</span> ${typeof t !== 'undefined' ? t('prompt_editor.prompt_designer') : 'Prompt Designer'}
                        </button>
                        <p class="compose-note text-[10px] text-brand-text-muted/60 mt-1">${typeof t !== 'undefined' ? t('prompt_editor.step2_tip') : 'Breaks down your prompt into editable visual components — subject, scene, lighting, colors. Skip this and go straight to Generate if you prefer.'}</p>
                        <div class="decomposed-panel hidden mt-2">
                            <textarea
                                class="decomposed-textarea input w-full min-h-[120px] text-xs text-brand-text/70 bg-amber-950/10 border-amber-500/20"
                                rows="8" readonly
                                placeholder="Recomposed prompt will appear here after generation..."
                            ></textarea>
                            <p class="text-[10px] text-brand-text-muted/40 mt-0.5">Recomposed from your prompt. Click Prompt Designer above to edit components.</p>
                        </div>
                    </div>

                    <!-- Step 3: Enhanced Prompt Preview -->
                    <div>
                        <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[10px] font-bold text-emerald-400/50 bg-emerald-400/5 rounded px-1.5 py-0.5 step3-badge">${typeof t !== 'undefined' ? t('prompt_editor.step') : 'STEP'} 3</span>
                            <span class="text-[10px] text-brand-text-muted/50 uppercase tracking-wide step3-label">${typeof t !== 'undefined' ? t('prompt_editor.step3_review') : 'Enhanced prompt preview'}</span>
                            <button type="button" class="btn-clear-composed hidden text-[10px] text-brand-text-muted hover:text-red-400 transition-colors ml-auto">${typeof t !== 'undefined' ? t('prompt_editor.clear') : 'Clear'}</button>
                        </div>
                        <div class="composed-panel hidden space-y-2">
                            <textarea
                                class="composed-textarea input w-full min-h-[80px] text-xs text-brand-text/80 bg-emerald-950/10 border-emerald-500/20"
                                rows="3"
                            ></textarea>
                            <p class="text-[10px] text-brand-text-muted/50">${typeof t !== 'undefined' ? t('prompt_editor.step3_desc') : 'This is what the image model will receive. You can edit it before generating.'}</p>
                        </div>
                        <div class="composed-placeholder">
                            <button type="button" class="btn-compose text-xs py-2 w-full rounded-lg flex items-center justify-center gap-2 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 hover:border-emerald-500/50 transition-all font-medium">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                                </svg>
                                ${typeof t !== 'undefined' ? t('prompt_editor.generate_enhanced') : 'Generate Enhanced Prompt'}
                            </button>
                            <p class="text-[10px] text-brand-text-muted/30 mt-1 italic">${typeof t !== 'undefined' ? t('prompt_editor.step3_hint') : 'Optional — click to preview the enhanced prompt before generating. Or just click Generate below to auto-enhance and create.'}</p>
                        </div>
                    </div>
                </div>
            `;

            // Cache DOM refs
            this._textareaEl = this.container.querySelector('#prompt-textarea');
            this._charCountEl = this.container.querySelector('.char-count');
            this._btnCompose = this.container.querySelector('.btn-compose');
            this._btnDesigner = this.container.querySelector('.btn-prompt-designer');
            this._composeNote = this.container.querySelector('.compose-note');
            this._composedPanel = this.container.querySelector('.composed-panel');
            this._composedTextarea = this.container.querySelector('.composed-textarea');
            this._btnClearComposed = this.container.querySelector('.btn-clear-composed');

            // Initialize VoiceInput
            const voiceContainer = this.container.querySelector('.voice-container');
            try {
                this._voice = new VoiceInput(voiceContainer);
                this._voice.onTranscript((text) => {
                    const current = this._textareaEl.value;
                    const separator = current && !current.endsWith(' ') ? ' ' : '';
                    this._textareaEl.value = current + separator + text;
                    this._updateCharCount();
                    this._clearComposed();
                    if (this._changeCb) this._changeCb(this._textareaEl.value);
                });
            } catch (e) {
                // Voice input not available
            }

            this._updateStyleNote();
        }

        _attachEvents() {
            // User typing clears the composed prompt + triggers translation preview
            this._translationTimer = null;
            this._lastTranslation = null;

            this._textareaEl.addEventListener('input', () => {
                this._updateCharCount();
                // Editing Step 1 invalidates any prior composition AND any
                // Designer-derived Step-2 data (it no longer matches this text).
                // Clear when EITHER exists so nothing stale is sent on Generate.
                if (this._composedText || this._recomposedPrompt || this._decomposedData) this._clearComposed();
                this._assetTypeConfirmed = false;  // New text = re-check asset type
                this._galleryReload = false;       // User is writing fresh — not a reload
                if (this._changeCb) this._changeCb(this._textareaEl.value);
                // Debounced translation preview (500ms after user stops typing)
                clearTimeout(this._translationTimer);
                this._translationTimer = setTimeout(() => this._checkTranslation(), 500);
            });

            // Translation tab switching
            this.container.querySelector('.translation-tab-original')?.addEventListener('click', () => {
                this.container.querySelector('.translation-tab-original').className = 'translation-tab-original text-[10px] px-2 py-0.5 rounded bg-brand-accent text-white font-medium';
                this.container.querySelector('.translation-tab-english').className = 'translation-tab-english text-[10px] px-2 py-0.5 rounded bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent';
                this.container.querySelector('.translation-english-text')?.classList.add('hidden');
                this._textareaEl.classList.remove('hidden');
            });
            this.container.querySelector('.translation-tab-english')?.addEventListener('click', () => {
                this.container.querySelector('.translation-tab-english').className = 'translation-tab-english text-[10px] px-2 py-0.5 rounded bg-brand-accent text-white font-medium';
                this.container.querySelector('.translation-tab-original').className = 'translation-tab-original text-[10px] px-2 py-0.5 rounded bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent';
                this.container.querySelector('.translation-english-text')?.classList.remove('hidden');
                this._textareaEl.classList.add('hidden');
            });

            // Prompt Designer button — opens Designer (with or without prompt)
            this._btnDesigner?.addEventListener('click', async () => {
                const text = this._textareaEl.value.trim();
                let assetType = this.opts.assetType || 'photorealistic';

                // Asset type classification — only once per prompt session
                if (text && !this._assetTypeConfirmed) {
                    try {
                        window.showLoading?.(typeof t !== 'undefined' ? t('prompt_designer.asset_check') : 'Checking asset type...');
                        const resp = await fetch('/api/refine-prompt/classify-asset-type', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ prompt: text, asset_type: assetType }),
                        });
                        window.hideLoading?.();

                        if (resp.ok && window.showConfirm) {
                            const check = await resp.json();
                            if (check.mismatch) {
                                const sugLabel = (check.suggested || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                                const curLabel = (check.current || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                                const shouldSwitch = await window.showConfirm(
                                    check.reason,
                                    {
                                        title: typeof t !== 'undefined' ? t('prompt_designer.asset_mismatch_title') : 'Asset Type may not be right',
                                        detail: t('prompt_editor.asset_type_wrong_detail').replace('{{cur}}', curLabel).replace('{{sug}}', sugLabel),
                                        confirmLabel: t('image_studio.switch_to').replace('{{sug}}', sugLabel),
                                        cancelLabel: t('image_studio.keep').replace('{{cur}}', curLabel),
                                    }
                                );
                                if (shouldSwitch) {
                                    assetType = check.suggested;
                                    if (this.opts.onAssetTypeChange) this.opts.onAssetTypeChange(assetType);
                                    this.opts.assetType = assetType;
                                }
                            }
                        }
                        this._assetTypeConfirmed = true;
                    } catch {
                        window.hideLoading?.();
                    }
                }

                // Open Designer — pass saved decomposition if available
                window.PromptDesigner?.open(text || '', {
                    styleId: this.opts.styleId,
                    assetType: assetType,
                    imageModel: this.opts.imageModel,
                    decomposedData: this._decomposedData,
                    galleryReload: this._galleryReload && !this._decomposedData,
                    onAssetTypeChange: (newType) => {
                        if (this.opts.onAssetTypeChange) this.opts.onAssetTypeChange(newType);
                        this.opts.assetType = newType;
                    },
                    onPromptSet: (prompt) => {
                        // Populate Step 1 with the prompt from the Designer
                        this._textareaEl.value = prompt;
                        this._updateCharCount();
                    },
                    onApply: (designerData, varyFlags, selectorState) => {
                        this._originalText = text || this._textareaEl.value;
                        this._designerData = designerData;
                        this._decomposedData = designerData;
                        this._varyFlags = varyFlags || null;
                        // Sync asset type and style back from the Designer selectors
                        if (selectorState) {
                            if (selectorState.assetType) {
                                this.opts.assetType = selectorState.assetType;
                                if (this.opts.onAssetTypeChange) this.opts.onAssetTypeChange(selectorState.assetType);
                            }
                            if (selectorState.styleId !== undefined) {
                                this.opts.styleId = selectorState.styleId;
                                if (this.opts.onStyleChange) this.opts.onStyleChange(selectorState.styleId);
                            }
                        }
                        this._composeFromDesigner(designerData);
                    },
                });
            });

            // Compose button
            this._btnCompose.addEventListener('click', () => this._handleCompose());

            // Clear composed
            this._btnClearComposed.addEventListener('click', () => this._clearComposed());

            // Allow editing the composed textarea directly
            this._composedTextarea.addEventListener('input', () => {
                this._composedText = this._composedTextarea.value;
            });
        }

        _updateCharCount() {
            if (this._charCountEl) {
                this._charCountEl.textContent = this._textareaEl.value.length;
            }
        }

        _consolidateDesigner(designerData) {
            // DETERMINISTIC Step-2 consolidation (no LLM): flatten every field
            // value across sections into one plain-text string. Mirrors the
            // backend _consolidate_decomposed so the Step-2 box and the stored
            // "source" match. This is the input the single enhance pass turns
            // into the Step-3 prompt.
            if (!designerData || typeof designerData !== 'object') return '';
            const parts = [];
            for (const section of Object.values(designerData)) {
                if (section && typeof section === 'object') {
                    for (const field of Object.values(section)) {
                        if (field && typeof field === 'object' && field.value) {
                            parts.push(String(field.value).trim());
                        } else if (typeof field === 'string' && field.trim()) {
                            parts.push(field.trim());
                        }
                    }
                }
            }
            return parts.filter(Boolean).join(' ');
        }

        async _composeFromDesigner(designerData) {
            // Step 2 → Step 3 with a SINGLE LLM pass:
            //   1. Consolidate the designer fields into flat text (no LLM) — this
            //      is the Step-2 box content and the recorded source of Step 3.
            //   2. Enhance that once for the model → the Step-3 prompt sent to it.
            // (Previously this did recompose-LLM THEN refine-LLM — two passes that
            //  double-enhanced and added latency/cost.)
            if (this._isComposing) return;
            this._isComposing = true;

            const origHTML = this._btnCompose.innerHTML;
            // nosemgrep
            this._btnCompose.innerHTML = html`<span class="spinner-sm"></span> ${typeof t !== 'undefined' ? t('prompt_editor.composing') : 'Composing...'}`;
            this._btnCompose.disabled = true;

            try {
                // Step 2 → deterministic consolidation (no LLM call)
                const recomposedPrompt = this._consolidateDesigner(designerData);
                this.setDecomposedText(recomposedPrompt);
                this._recomposedPrompt = recomposedPrompt;

                // Step 3 → single enhance for the model (the consolidation is input)
                const enhancePayload = {
                    prompt: recomposedPrompt || this._textareaEl.value,
                    style_id: this.opts.styleId || undefined,
                    asset_type: this.opts.assetType || undefined,
                    image_model: this.opts.imageModel || undefined,
                };
                const enhanceResult = await API.refinePrompt(enhancePayload);
                const enhanced = enhanceResult.refined || enhanceResult.enhanced_prompt || enhanceResult;

                this._originalText = this._textareaEl.value;
                this._composedText = enhanced;
                this._negativePrompt = enhanceResult.negative_prompt || '';
                this._userComposed = true;
                this._showComposed(enhanced);
            } catch (err) {
                console.error('Failed to compose from designer data:', err);
                window.showToast?.(t('misc.pe_failed_enhance'), 'error');
            } finally {
                // nosemgrep
                this._btnCompose.innerHTML = raw(origHTML);
                this._btnCompose.disabled = false;
                this._isComposing = false;
            }
        }

        _updateAssetContext() {
            const type = this.opts.assetType || 'photorealistic';
            // Update placeholder
            if (this._textareaEl) {
                this._textareaEl.placeholder = _ASSET_PLACEHOLDERS[type] || _ASSET_PLACEHOLDERS.game_asset;
            }
            // Update Step 1 label
            const step1Label = this.container.querySelector('.step1-label');
            if (step1Label) {
                const labelKey = _ASSET_STEP_LABEL_KEYS[type] || _ASSET_STEP_LABEL_KEYS.game_asset;
                step1Label.textContent = typeof t !== 'undefined' ? t(labelKey) : type;
            }
        }

        _updateStyleNote() {
            if (!this._composeNote) return;
            const hasStyle = !!this.opts.styleId;
            if (hasStyle) {
                this._composeNote.textContent = typeof t !== 'undefined' ? t('prompt_editor.compose_tip') : 'Your prompt will be composed with the selected style guidelines.';
            } else {
                this._composeNote.textContent = typeof t !== 'undefined' ? t('prompt_editor.compose_tip') : 'AI will enhance your prompt with composition, lighting, and quality details.';
            }
        }

        async _handleCompose() {
            const text = this._textareaEl.value.trim();
            if (!text) {
                window.showToast?.(typeof t !== 'undefined' ? t('prompt_editor.compose_error') : 'Enter a prompt first', 'warning');
                return;
            }
            if (this._isComposing) return;
            this._isComposing = true;

            const origHTML = this._btnCompose.innerHTML;
            // nosemgrep
            this._btnCompose.innerHTML = html`<span class="spinner-sm"></span> ${typeof t !== 'undefined' ? t('prompt_editor.composing') : 'Composing...'}`;
            this._btnCompose.disabled = true;

            try {
                const payload = {
                    prompt: text,
                    style_id: this.opts.styleId || undefined,
                    asset_type: this.opts.assetType || undefined,
                    image_model: this.opts.imageModel || undefined,
                };

                let result = await API.refinePrompt(payload);

                const composed = result.refined || result.enhanced_prompt || result;

                this._originalText = text;
                this._composedText = composed;
                this._negativePrompt = result.negative_prompt || '';
                this._userComposed = true;  // User explicitly clicked Compose
                this._showComposed(composed);
            } catch (err) {
                console.error('Compose error:', err);
                window.showToast?.(t('misc.pe_failed_compose'), 'error');
            } finally {
                // nosemgrep
                this._btnCompose.innerHTML = raw(origHTML);
                this._btnCompose.disabled = false;
                this._isComposing = false;
            }
        }

        _showComposed(text) {
            this._composedTextarea.value = text;
            this._composedPanel.classList.remove('hidden');
            this._btnClearComposed?.classList.remove('hidden');
            // Activate Step 3 badge
            const badge = this.container.querySelector('.step3-badge');
            const label = this.container.querySelector('.step3-label');
            const placeholder = this.container.querySelector('.composed-placeholder');
            if (badge) { badge.classList.remove('text-emerald-400/50', 'bg-emerald-400/5'); badge.classList.add('text-emerald-400', 'bg-emerald-400/10'); }
            if (label) { label.classList.remove('text-brand-text-muted/50'); label.classList.add('text-brand-text-muted'); }
            if (placeholder) placeholder.classList.add('hidden');
        }

        _clearComposed() {
            this._composedText = null;
            this._negativePrompt = '';
            this._userComposed = false;
            // Also drop the Step-2 Designer-derived data so a subsequently
            // edited/retyped prompt does NOT carry stale recomposed_prompt /
            // decomposed_data / vary_fields into the next Generate (they'd no
            // longer match the new prompt). Cleared together as one unit.
            this._recomposedPrompt = null;
            this._decomposedData = null;
            this._designerData = null;
            this._varyFlags = null;
            this.setDecomposedText('');
            this._composedPanel.classList.add('hidden');
            this._btnClearComposed?.classList.add('hidden');
            this._composedTextarea.value = '';
            // Deactivate Step 3 badge
            const badge = this.container.querySelector('.step3-badge');
            const label = this.container.querySelector('.step3-label');
            const placeholder = this.container.querySelector('.composed-placeholder');
            if (badge) { badge.classList.add('text-emerald-400/50', 'bg-emerald-400/5'); badge.classList.remove('text-emerald-400', 'bg-emerald-400/10'); }
            if (label) { label.classList.add('text-brand-text-muted/50'); label.classList.remove('text-brand-text-muted'); }
            if (placeholder) placeholder.classList.remove('hidden');
        }

        async _checkTranslation() {
            const text = this._textareaEl.value.trim();
            const preview = this.container.querySelector('.translation-preview');
            const langBadge = this.container.querySelector('.translation-lang-badge');
            const englishText = this.container.querySelector('.translation-english-text');
            if (!preview || !text) {
                preview?.classList.add('hidden');
                this._lastTranslation = null;
                return;
            }

            // Quick heuristic: check if text has non-ASCII characters
            const hasNonAscii = /[^\x00-\x7F]/.test(text);
            // Also check for French/Spanish accented words
            const hasAccented = /[àâäéèêëïîôùûüÿçñ¿¡]/i.test(text);
            // Check for common non-English word patterns
            const looksNonEnglish = hasNonAscii || hasAccented;

            if (!looksNonEnglish) {
                preview.classList.add('hidden');
                this._lastTranslation = null;
                // Ensure textarea is visible (in case English tab was active)
                this._textareaEl.classList.remove('hidden');
                englishText?.classList.add('hidden');
                return;
            }

            // Fetch translation preview
            try {
                const resp = await fetch('/api/refine-prompt/translate-preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, ui_lang: (typeof I18n !== 'undefined' ? I18n.getLang() : '') }),
                });
                if (!resp.ok) return;
                const result = await resp.json();

                if (result.was_translated && result.source_lang !== 'en') {
                    this._lastTranslation = result;
                    const langNames = { ja: '日本語', zh: '中文', ko: '한국어', hi: 'हिन्दी', ru: 'Русский', fr: 'Français', es: 'Español', de: 'Deutsch' };
                    langBadge.textContent = `${langNames[result.source_lang] || result.source_lang} → English`;
                    englishText.textContent = result.translated;
                    preview.classList.remove('hidden');
                    // Reset to original tab
                    this.container.querySelector('.translation-tab-original').className = 'translation-tab-original text-[10px] px-2 py-0.5 rounded bg-brand-accent text-white font-medium';
                    this.container.querySelector('.translation-tab-english').className = 'translation-tab-english text-[10px] px-2 py-0.5 rounded bg-brand-bg border border-brand-border text-brand-text-muted hover:border-brand-accent';
                    this._textareaEl.classList.remove('hidden');
                    englishText.classList.add('hidden');
                } else {
                    preview.classList.add('hidden');
                    this._lastTranslation = null;
                }
            } catch {
                // Silent failure — translation preview is a nice-to-have
            }
        }
    }

    window.PromptEditor = PromptEditor;
})();
