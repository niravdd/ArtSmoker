/**
 * ArtSmoker — API Client
 * Provides window.API with methods for all backend endpoints.
 */
(function () {
    'use strict';

    const BASE = '';

    /**
     * Core request helper.
     * @param {string} path - URL path (appended to BASE)
     * @param {object} opts - fetch options
     * @returns {Promise<any>}
     */
    async function request(path, opts = {}) {
        const url = `${BASE}${path}`;
        const headers = opts.headers || {};

        // Default to JSON content-type unless FormData
        if (opts.body && !(opts.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            if (typeof opts.body !== 'string') {
                opts.body = JSON.stringify(opts.body);
            }
        }

        opts.headers = headers;

        try {
            const res = await fetch(url, opts);

            if (!res.ok) {
                let detail = `HTTP ${res.status}`;
                try {
                    const errJson = await res.json();
                    detail = errJson.detail || errJson.message || detail;
                } catch (_) {
                    // response wasn't JSON — keep the status text
                    detail = res.statusText || detail;
                }
                throw new Error(detail);
            }

            // 204 No Content
            if (res.status === 204) return null;

            const contentType = res.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                return await res.json();
            }
            return await res.text();
        } catch (err) {
            // Network error or thrown above
            if (typeof window.showToast === 'function') {
                window.showToast(err.message || 'Network error', 'error');
            }
            throw err;
        }
    }

    // --------------------------------------------------------
    //  Public API
    // --------------------------------------------------------

    window.API = {
        /** Style Profiles */
        styles: {
            /** List all styles */
            list() {
                return request('/api/styles/');
            },

            /** Get a single style by ID */
            get(id) {
                return request(`/api/styles/${encodeURIComponent(id)}`);
            },

            /** Create a new style */
            create(data) {
                return request('/api/styles/', {
                    method: 'POST',
                    body: data,
                });
            },

            /** Update (partial) a style */
            update(id, data) {
                return request(`/api/styles/${encodeURIComponent(id)}`, {
                    method: 'PATCH',
                    body: data,
                });
            },

            /** Delete a style */
            delete(id) {
                return request(`/api/styles/${encodeURIComponent(id)}`, {
                    method: 'DELETE',
                });
            },

            /**
             * Upload reference images for a style.
             * @param {string} id - Style ID
             * @param {FileList|File[]} files
             */
            uploadReferences(id, files) {
                const fd = new FormData();
                for (const f of files) {
                    fd.append('files', f);
                }
                return request(`/api/styles/${encodeURIComponent(id)}/references`, {
                    method: 'POST',
                    body: fd,
                });
            },

            /** Import references from a local directory or S3 URI */
            importPath(id, path, autoAnalyze = true) {
                return request(`/api/styles/${encodeURIComponent(id)}/import`, {
                    method: 'POST',
                    body: { path, auto_analyze: autoAnalyze },
                });
            },

            /** Trigger AI analysis of a style's references */
            analyze(id) {
                return request(`/api/styles/${encodeURIComponent(id)}/analyze`, {
                    method: 'POST',
                });
            },

            /**
             * Build the URL for a reference image (no fetch, just returns URL string).
             */
            referenceUrl(id, filename) {
                return `/api/styles/${encodeURIComponent(id)}/references/${encodeURIComponent(filename)}`;
            },
        },

        /** Generate images (synchronous fallback) */
        generate(data) {
            return request('/api/generate/', {
                method: 'POST',
                body: data,
            });
        },

        /** Pre-screen a prompt for moderation issues (fast, cheap via Sonnet) */
        preScreen(data) {
            return request('/api/generate/pre-screen', {
                method: 'POST',
                body: data,
            });
        },

        /** Analyze a moderation-blocked prompt — tries alternative models first */
        analyzeModeration(data) {
            return request('/api/generate/analyze-moderation', {
                method: 'POST',
                body: data,
            });
        },

        /** Apply post-processing to existing gallery assets */
        postProcess(data) {
            return request('/api/generate/post-process', {
                method: 'POST',
                body: data,
            });
        },

        /**
         * Generate images with SSE streaming progress.
         * @param {object} data - GenerationRequest payload
         * @param {function} onEvent - called with each progress event
         * @returns {Promise<object>} the final GenerationResult
         */
        generateStream(data, onEvent) {
            return new Promise((resolve, reject) => {
                fetch('/api/generate/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                }).then(response => {
                    if (!response.ok) {
                        return response.json().then(err => {
                            reject(new Error(err.detail || `HTTP ${response.status}`));
                        });
                    }
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';
                    let finalResult = null;

                    function read() {
                        reader.read().then(({ done, value }) => {
                            if (done) {
                                if (finalResult) resolve(finalResult);
                                else reject(new Error('Stream ended without result'));
                                return;
                            }
                            buffer += decoder.decode(value, { stream: true });
                            const lines = buffer.split('\n');
                            buffer = lines.pop() || '';

                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    try {
                                        const evt = JSON.parse(line.slice(6));
                                        if (onEvent) onEvent(evt);
                                        if (evt.type === 'complete' && evt.result) {
                                            finalResult = evt.result;
                                        }
                                        if (evt.type === 'error') {
                                            reject(new Error(evt.detail || 'Generation failed'));
                                            return;
                                        }
                                    } catch (_) {}
                                }
                            }
                            read();
                        }).catch(reject);
                    }
                    read();
                }).catch(reject);
            });
        },

        /** Refine / improve a prompt via AI */
        refinePrompt(data) {
            return request('/api/refine-prompt/', {
                method: 'POST',
                body: data,
            });
        },

        /** Transcribe an audio blob to text */
        transcribe(audioBlob) {
            const fd = new FormData();
            fd.append('file', audioBlob, 'recording.webm');
            return request('/api/transcribe/', {
                method: 'POST',
                body: fd,
            });
        },

        /** Gallery */
        gallery: {
            /** List gallery items with optional filters */
            list(params = {}) {
                const qs = new URLSearchParams();
                Object.entries(params).forEach(([k, v]) => {
                    if (v !== undefined && v !== null && v !== '') {
                        qs.set(k, v);
                    }
                });
                const query = qs.toString();
                return request(`/api/gallery/${query ? '?' + query : ''}`);
            },

            /** Get a single gallery item's full metadata */
            get(id) {
                return request(`/api/gallery/${encodeURIComponent(id)}`);
            },

            /** Delete one or more gallery assets permanently */
            delete(ids) {
                return request('/api/gallery/', {
                    method: 'DELETE',
                    body: { ids: Array.isArray(ids) ? ids : [ids] },
                });
            },

            /** Get full batch (options × variations) for reloading into Generator */
            getBatch(batchId) {
                return request(`/api/gallery/batch/${encodeURIComponent(batchId)}`);
            },

            /** PNG download URL */
            pngUrl(id) {
                return `/api/gallery/${encodeURIComponent(id)}/png`;
            },

            /** SVG download URL */
            svgUrl(id) {
                return `/api/gallery/${encodeURIComponent(id)}/svg`;
            },
        },

        /** Send a log entry to the server for recording */
        log(level, message, context) {
            // Fire-and-forget — don't block on this
            fetch('/api/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ level, message, context: context || '' }),
            }).catch(() => {}); // silently ignore if server is down
        },

        /** Admin — Model Registry */
        admin: {
            getModels() {
                return request('/api/admin/models');
            },
            updateCategory(name, data) {
                return request(`/api/admin/models/category/${encodeURIComponent(name)}`, {
                    method: 'PATCH', body: data,
                });
            },
            updateImageModel(key, data) {
                return request(`/api/admin/models/image/${encodeURIComponent(key)}`, {
                    method: 'PATCH', body: data,
                });
            },
            addImageModel(data) {
                return request('/api/admin/models/image', {
                    method: 'POST', body: data,
                });
            },
            updatePostProcess(key, data) {
                return request(`/api/admin/models/postprocess/${encodeURIComponent(key)}`, {
                    method: 'PATCH', body: data,
                });
            },
            discover(region) {
                return request(`/api/admin/discover/${encodeURIComponent(region)}`);
            },
            reload() {
                return request('/api/admin/models/reload', { method: 'POST' });
            },
        },

        /** Type Studio */
        typeStudio: {
            /** List available fonts, optionally filtered by style */
            fonts(styleId) {
                const qs = styleId ? `?style_id=${encodeURIComponent(styleId)}` : '';
                return request(`/api/type-studio/fonts${qs}`);
            },

            /** Ask AI for a layout suggestion */
            suggest(data) {
                return request('/api/type-studio/suggest', {
                    method: 'POST',
                    body: data,
                });
            },

            /** Render text preview and save as gallery asset */
            preview(data) {
                return request('/api/type-studio/preview', {
                    method: 'POST',
                    body: data,
                });
            },
        },

        /** File & S3 browser */
        browse: {
            local(path) {
                return request(`/api/browse/local?path=${encodeURIComponent(path || '~')}`);
            },
            s3Buckets() {
                return request('/api/browse/s3/buckets');
            },
            s3(bucket, prefix) {
                return request(`/api/browse/s3?bucket=${encodeURIComponent(bucket)}&prefix=${encodeURIComponent(prefix || '')}`);
            },
        },
    };
})();
