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

        /** Generate an image */
        generate(data) {
            return request('/api/generate/', {
                method: 'POST',
                body: data,
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

            /** Get a single gallery item */
            get(id) {
                return request(`/api/gallery/${encodeURIComponent(id)}`);
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
    };
})();
