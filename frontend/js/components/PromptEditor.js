/**
 * ArtSmoker — PromptEditor Component
 *
 * Text area for prompts with AI refinement, voice input, and character count.
 *
 * Usage:
 *   const editor = new PromptEditor(containerEl, { styleId, assetType });
 *   editor.getText()           // current prompt text
 *   editor.setText(text)       // set prompt text programmatically
 *   editor.onChanged(cb)       // listen for text changes
 */
(function () {
    'use strict';

    class PromptEditor {
        /**
         * @param {HTMLElement} container
         * @param {object} opts - { styleId, assetType } passed to refine-prompt
         */
        constructor(container, opts = {}) {
            this.container = container;
            this.opts = opts;
            this._changeCb = null;
            this._refinedText = null;
            this._originalText = null;
            this._isRefining = false;

            this._render();
            this._attachEvents();
        }

        // -- Public API --

        getText() {
            return this._textareaEl.value;
        }

        setText(text) {
            this._textareaEl.value = text;
            this._updateCharCount();
            if (this._changeCb) this._changeCb(text);
        }

        onChanged(cb) {
            this._changeCb = cb;
        }

        /** Update context passed to refine endpoint */
        setContext(opts) {
            this.opts = { ...this.opts, ...opts };
        }

        destroy() {
            if (this._voice) this._voice.destroy();
            this.container.innerHTML = '';
        }

        // -- Private --

        _render() {
            this.container.innerHTML = `
                <div class="prompt-editor space-y-3">
                    <!-- Main textarea row -->
                    <div class="relative">
                        <textarea
                            id="prompt-textarea"
                            class="input w-full min-h-[120px] pr-12"
                            placeholder="Describe the image you want to generate..."
                            rows="4"
                        ></textarea>
                        <div class="absolute bottom-2 right-2 flex items-center gap-1">
                            <span class="char-count text-xs text-brand-text-muted tabular-nums">0</span>
                        </div>
                    </div>

                    <!-- Toolbar -->
                    <div class="flex flex-wrap items-center gap-2">
                        <button type="button" class="btn-refine btn btn-secondary btn-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                            </svg>
                            Improve with AI
                        </button>
                        <div class="voice-container"></div>
                    </div>

                    <!-- Refine comparison (hidden by default) -->
                    <div class="refine-panel hidden card-static p-4 space-y-3">
                        <h4 class="text-sm font-semibold text-brand-accent flex items-center gap-2">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                            </svg>
                            AI-Refined Prompt
                        </h4>
                        <div class="prompt-compare">
                            <div>
                                <label class="block text-xs text-brand-text-muted mb-1 uppercase tracking-wider">Original</label>
                                <div class="refine-original p-3 rounded-lg bg-brand-bg/60 text-sm text-brand-text-muted min-h-[80px] whitespace-pre-wrap"></div>
                            </div>
                            <div>
                                <label class="block text-xs text-brand-text-muted mb-1 uppercase tracking-wider">Refined</label>
                                <div class="refine-refined p-3 rounded-lg bg-brand-bg/60 text-sm text-brand-text min-h-[80px] whitespace-pre-wrap border border-brand-accent/20"></div>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button type="button" class="btn-accept btn btn-primary btn-sm">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                </svg>
                                Accept Refined
                            </button>
                            <button type="button" class="btn-revert btn btn-secondary btn-sm">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                                Revert
                            </button>
                        </div>
                    </div>
                </div>
            `;

            // Cache DOM refs
            this._textareaEl = this.container.querySelector('#prompt-textarea');
            this._charCountEl = this.container.querySelector('.char-count');
            this._btnRefine = this.container.querySelector('.btn-refine');
            this._refinePanel = this.container.querySelector('.refine-panel');
            this._refineOriginal = this.container.querySelector('.refine-original');
            this._refineRefined = this.container.querySelector('.refine-refined');
            this._btnAccept = this.container.querySelector('.btn-accept');
            this._btnRevert = this.container.querySelector('.btn-revert');

            // Initialize VoiceInput inside the voice-container
            const voiceContainer = this.container.querySelector('.voice-container');
            this._voice = new VoiceInput(voiceContainer);
            this._voice.onTranscript((text) => {
                // Append transcribed text (with a space if textarea already has content)
                const current = this._textareaEl.value;
                const separator = current && !current.endsWith(' ') ? ' ' : '';
                this._textareaEl.value = current + separator + text;
                this._updateCharCount();
                if (this._changeCb) this._changeCb(this._textareaEl.value);
            });
        }

        _attachEvents() {
            // Character count on input
            this._textareaEl.addEventListener('input', () => {
                this._updateCharCount();
                if (this._changeCb) this._changeCb(this._textareaEl.value);
            });

            // Refine button
            this._btnRefine.addEventListener('click', () => this._handleRefine());

            // Accept refined
            this._btnAccept.addEventListener('click', () => {
                if (this._refinedText) {
                    this._textareaEl.value = this._refinedText;
                    this._updateCharCount();
                    if (this._changeCb) this._changeCb(this._textareaEl.value);
                }
                this._hideRefinePanel();
            });

            // Revert
            this._btnRevert.addEventListener('click', () => {
                this._hideRefinePanel();
            });
        }

        _updateCharCount() {
            this._charCountEl.textContent = this._textareaEl.value.length;
        }

        async _handleRefine() {
            const text = this._textareaEl.value.trim();
            if (!text) {
                window.showToast && window.showToast('Enter a prompt first', 'warning');
                return;
            }
            if (this._isRefining) return;
            this._isRefining = true;

            // Show loading state on button
            const origHTML = this._btnRefine.innerHTML;
            this._btnRefine.innerHTML = '<span class="spinner-sm"></span> Refining...';
            this._btnRefine.disabled = true;

            try {
                const payload = {
                    prompt: text,
                    style_id: this.opts.styleId || undefined,
                    asset_type: this.opts.assetType || undefined,
                };

                const result = await API.refinePrompt(payload);
                this._originalText = text;
                this._refinedText = result.refined_prompt || result.prompt || result;

                // Show comparison panel
                this._refineOriginal.textContent = this._originalText;
                this._refineRefined.textContent = this._refinedText;
                this._refinePanel.classList.remove('hidden');
                this._refinePanel.classList.add('fade-in');
            } catch (err) {
                console.error('Refine error:', err);
            } finally {
                this._btnRefine.innerHTML = origHTML;
                this._btnRefine.disabled = false;
                this._isRefining = false;
            }
        }

        _hideRefinePanel() {
            this._refinePanel.classList.add('hidden');
            this._refinedText = null;
            this._originalText = null;
        }
    }

    window.PromptEditor = PromptEditor;
})();
