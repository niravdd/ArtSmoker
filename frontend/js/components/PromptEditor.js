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

            this._render();
            this._attachEvents();
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
            this._showComposed(text);
        }

        onChanged(cb) {
            this._changeCb = cb;
        }

        setContext(opts) {
            this.opts = { ...this.opts, ...opts };
            // Update the style note under the compose button
            this._updateStyleNote();
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
            this.container.innerHTML = `
                <div class="prompt-editor space-y-3">
                    <!-- User prompt textarea -->
                    <div class="relative">
                        <textarea
                            id="prompt-textarea"
                            class="input w-full min-h-[100px] pr-12"
                            placeholder="Describe what you want to generate..."
                            rows="3"
                        ></textarea>
                        <div class="absolute bottom-2 right-2 flex items-center gap-1">
                            <span class="char-count text-xs text-brand-text-muted tabular-nums">0</span>
                        </div>
                    </div>

                    <!-- Toolbar: Compose button + Voice -->
                    <div class="flex flex-wrap items-center gap-2">
                        <button type="button" class="btn-compose btn btn-secondary btn-sm flex-1 sm:flex-none">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                            </svg>
                            Compose Generation Prompt
                        </button>
                        <div class="voice-container"></div>
                    </div>
                    <p class="compose-note text-[10px] text-brand-text-muted/60 -mt-1"></p>

                    <!-- Composed generation prompt (hidden until composed) -->
                    <div class="composed-panel hidden space-y-2">
                        <div class="flex items-center justify-between">
                            <h4 class="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                Generation Prompt
                            </h4>
                            <button type="button" class="btn-clear-composed text-[10px] text-brand-text-muted hover:text-red-400 transition-colors">Clear</button>
                        </div>
                        <textarea
                            class="composed-textarea input w-full min-h-[80px] text-xs text-brand-text/80 bg-emerald-950/10 border-emerald-500/20"
                            rows="3"
                        ></textarea>
                        <p class="text-[10px] text-brand-text-muted/50">This is what the image model will receive. You can edit it. Style guidelines and asset type directives have been integrated.</p>
                    </div>
                </div>
            `;

            // Cache DOM refs
            this._textareaEl = this.container.querySelector('#prompt-textarea');
            this._charCountEl = this.container.querySelector('.char-count');
            this._btnCompose = this.container.querySelector('.btn-compose');
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
            // User typing clears the composed prompt
            this._textareaEl.addEventListener('input', () => {
                this._updateCharCount();
                if (this._composedText) this._clearComposed();
                if (this._changeCb) this._changeCb(this._textareaEl.value);
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

        _updateStyleNote() {
            if (!this._composeNote) return;
            const hasStyle = !!this.opts.styleId;
            if (hasStyle) {
                this._composeNote.textContent = 'Your prompt will be composed with the selected style guidelines, asset type directives, and AI-enhanced details.';
            } else {
                this._composeNote.textContent = 'No style selected — AI will enhance your prompt with composition, lighting, and quality details based on the asset type.';
            }
        }

        async _handleCompose() {
            const text = this._textareaEl.value.trim();
            if (!text) {
                window.showToast?.('Enter a prompt first', 'warning');
                return;
            }
            if (this._isComposing) return;
            this._isComposing = true;

            const origHTML = this._btnCompose.innerHTML;
            this._btnCompose.innerHTML = '<span class="spinner-sm"></span> Composing...';
            this._btnCompose.disabled = true;

            try {
                const payload = {
                    prompt: text,
                    style_id: this.opts.styleId || undefined,
                    asset_type: this.opts.assetType || undefined,
                    image_model: this.opts.imageModel || undefined,
                };

                const result = await API.refinePrompt(payload);
                const composed = result.refined || result.refined_prompt || result;

                this._originalText = text;
                this._composedText = composed;
                this._negativePrompt = result.negative_prompt || '';
                this._userComposed = true;  // User explicitly clicked Compose
                this._showComposed(composed);
            } catch (err) {
                console.error('Compose error:', err);
                window.showToast?.('Failed to compose prompt', 'error');
            } finally {
                this._btnCompose.innerHTML = origHTML;
                this._btnCompose.disabled = false;
                this._isComposing = false;
            }
        }

        _showComposed(text) {
            this._composedTextarea.value = text;
            this._composedPanel.classList.remove('hidden');
        }

        _clearComposed() {
            this._composedText = null;
            this._negativePrompt = '';
            this._userComposed = false;
            this._composedPanel.classList.add('hidden');
            this._composedTextarea.value = '';
        }
    }

    window.PromptEditor = PromptEditor;
})();
