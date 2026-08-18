/**
 * ArtSmoker — VoiceInput Component
 *
 * Uses MediaRecorder API to capture microphone audio,
 * sends it to API.transcribe(), and passes the text to a callback.
 *
 * Usage:
 *   const voice = new VoiceInput(containerEl);
 *   voice.onTranscript(text => { ... });
 */
(function () {
    'use strict';

    class VoiceInput {
        /**
         * @param {HTMLElement} container - element where the mic button will be rendered
         */
        constructor(container) {
            this.container = container;
            this._recording = false;
            this._mediaRecorder = null;
            this._chunks = [];
            this._startTime = null;
            this._timerInterval = null;
            this._transcriptCb = null;

            this._render();
            this._attachEvents();
        }

        // -- Public API --

        /** Start recording */
        async start() {
            if (this._recording) return;
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this._chunks = [];

                // Prefer webm; fall back to whatever the browser supports
                const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus'
                    : 'audio/webm';

                this._mediaRecorder = new MediaRecorder(stream, { mimeType });

                this._mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) this._chunks.push(e.data);
                };

                this._mediaRecorder.onstop = () => {
                    // Stop all tracks so the browser mic indicator goes away
                    stream.getTracks().forEach((t) => t.stop());
                    this._handleStop();
                };

                this._mediaRecorder.start();
                this._recording = true;
                this._startTime = Date.now();
                this._startTimer();
                this._updateUI();
            } catch (err) {
                if (typeof window.showToast === 'function') {
                    window.showToast(t('artsmoker.ui.misc.voice_mic_denied'), 'error');
                }
                console.error('VoiceInput: mic error', err);
            }
        }

        /** Stop recording */
        stop() {
            if (!this._recording || !this._mediaRecorder) return;
            this._mediaRecorder.stop();
            this._recording = false;
            this._stopTimer();
            this._updateUI();
        }

        /** Register a callback for when transcription completes */
        onTranscript(cb) {
            this._transcriptCb = cb;
        }

        /** Remove DOM + cleanup */
        destroy() {
            this.stop();
            this.container.innerHTML = '';
        }

        // -- Private --

        _render() {
            // nosemgrep
            this.container.innerHTML = html`
                <div class="voice-input-wrap inline-flex items-center gap-2">
                    <button type="button" class="voice-btn btn btn-secondary btn-sm rounded-full w-9 h-9 !p-0 relative"
                            title="${t('artsmoker.ui.misc.voice_record')}">
                        <svg class="voice-icon-mic w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M19 11a7 7 0 01-14 0m7 7v4m-4 0h8m-4-16a3 3 0 00-3 3v4a3 3 0 006 0V6a3 3 0 00-3-3z"/>
                        </svg>
                        <svg class="voice-icon-stop w-4 h-4 hidden" fill="currentColor" viewBox="0 0 24 24">
                            <rect x="6" y="6" width="12" height="12" rx="2"/>
                        </svg>
                    </button>
                    <span class="voice-timer text-xs text-brand-text-muted hidden">0:00</span>
                    <span class="voice-status hidden items-center gap-1.5">
                        <span class="recording-dot"></span>
                        <span class="text-xs text-red-400 font-medium">Recording</span>
                    </span>
                    <span class="voice-transcribing hidden items-center gap-1.5">
                        <span class="spinner-sm"></span>
                        <span class="text-xs text-brand-text-muted">Transcribing...</span>
                    </span>
                </div>
            `;

            this._btnEl = this.container.querySelector('.voice-btn');
            this._micIcon = this.container.querySelector('.voice-icon-mic');
            this._stopIcon = this.container.querySelector('.voice-icon-stop');
            this._timerEl = this.container.querySelector('.voice-timer');
            this._statusEl = this.container.querySelector('.voice-status');
            this._transcribingEl = this.container.querySelector('.voice-transcribing');
        }

        _attachEvents() {
            this._btnEl.addEventListener('click', () => {
                if (this._recording) {
                    this.stop();
                } else {
                    this.start();
                }
            });
        }

        _updateUI() {
            if (this._recording) {
                this._btnEl.classList.add('recording-pulse', '!border-red-500', '!text-red-400');
                this._micIcon.classList.add('hidden');
                this._stopIcon.classList.remove('hidden');
                this._timerEl.classList.remove('hidden');
                this._statusEl.classList.remove('hidden');
                this._statusEl.classList.add('inline-flex');
            } else {
                this._btnEl.classList.remove('recording-pulse', '!border-red-500', '!text-red-400');
                this._micIcon.classList.remove('hidden');
                this._stopIcon.classList.add('hidden');
                this._timerEl.classList.add('hidden');
                this._statusEl.classList.add('hidden');
                this._statusEl.classList.remove('inline-flex');
            }
        }

        _startTimer() {
            this._timerEl.textContent = '0:00';
            this._timerInterval = setInterval(() => {
                const elapsed = Math.floor((Date.now() - this._startTime) / 1000);
                const min = Math.floor(elapsed / 60);
                const sec = String(elapsed % 60).padStart(2, '0');
                this._timerEl.textContent = `${min}:${sec}`;
            }, 500);
        }

        _stopTimer() {
            clearInterval(this._timerInterval);
        }

        async _handleStop() {
            if (this._chunks.length === 0) return;
            const blob = new Blob(this._chunks, { type: 'audio/webm' });

            // Show transcribing indicator
            this._transcribingEl.classList.remove('hidden');
            this._transcribingEl.classList.add('inline-flex');

            try {
                const result = await API.transcribe(blob);
                const text = typeof result === 'string' ? result : (result.text || result.transcript || '');
                // Check if the response is a setup placeholder (Nova Sonic not configured)
                if (text && text.startsWith('[Audio received')) {
                    window.showToast?.(t('artsmoker.ui.misc.voice_unavailable'), 'info', 8000);
                } else if (this._transcriptCb && text) {
                    this._transcriptCb(text);
                } else if (!text) {
                    window.showToast?.(t('artsmoker.ui.misc.voice_no_speech'), 'warning');
                }
            } catch (err) {
                console.error('Transcription error:', err);
            } finally {
                this._transcribingEl.classList.add('hidden');
                this._transcribingEl.classList.remove('inline-flex');
            }
        }
    }

    window.VoiceInput = VoiceInput;
})();
