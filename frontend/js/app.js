/**
 * ArtSmoker — Main Application
 *
 * Client-side hash router with DOM caching (views survive navigation),
 * global helpers (loading, toast), and view initialization.
 */
(function () {
    'use strict';

    // ============================================================
    //  Routes
    // ============================================================

    const ROUTES = {
        'image-studio':  { component: window.ImageStudio, label: 'Image Studio' },
        'type-studio':   { component: window.TypeStudio, label: 'Type Studio' },
        'video-studio':  { component: window.VideoStudio, label: 'Video Studio' },
        'chat-studio':   { component: window.ChatStudio, label: 'Chat Studio' },
        styles:          { component: window.StyleLibrary, label: 'Style Library' },
        gallery:         { component: window.Gallery, label: 'Gallery' },
    };

    const DEFAULT_ROUTE = 'image-studio';
    let currentRoute = null;

    // DOM cache: once a view is rendered, keep its DOM alive
    const _viewCache = {};   // route -> HTMLElement (wrapper div)
    const _viewInited = {};  // route -> true if init() has been called

    // ============================================================
    //  Router (DOM-caching)
    // ============================================================

    function getRoute() {
        const hash = window.location.hash.replace(/^#\/?/, '').split('?')[0];
        if (hash && ROUTES[hash]) return hash;
        // Unknown or empty hash — redirect to default and update URL bar
        if (hash && hash !== DEFAULT_ROUTE) {
            window.location.hash = '#' + DEFAULT_ROUTE;
        }
        return DEFAULT_ROUTE;
    }

    async function navigate() {
        const route = getRoute();
        if (route === currentRoute) return;

        const app = document.getElementById('app');
        if (!app) return;

        const routeDef = ROUTES[route];
        if (!routeDef || !routeDef.component) {
            // nosemgrep
            app.innerHTML = html`<p class="text-center py-12 text-brand-text-muted">${t('artsmoker.onboarding.page_not_found')}</p>`;
            currentRoute = null;
            return;
        }

        // Hide the current view (don't destroy it)
        if (currentRoute && _viewCache[currentRoute]) {
            _viewCache[currentRoute].style.display = 'none';
        }

        currentRoute = route;

        // Update active nav link
        document.querySelectorAll('.nav-link').forEach((link) => {
            link.classList.toggle('active', link.dataset.nav === route);
        });

        // Close mobile menu if open
        document.getElementById('mobile-menu')?.classList.add('hidden');

        // If this view was already rendered, just show it
        if (_viewCache[route]) {
            _viewCache[route].style.display = '';
            // Notify component it's visible again (for refreshes like gallery)
            if (typeof routeDef.component.onShow === 'function') {
                routeDef.component.onShow();
            }
            // Translate cached view if language changed
            if (typeof I18n !== 'undefined' && I18n.isLoaded()) {
                I18n.translateView(_viewCache[route]);
            }
            return;
        }

        // First visit: render, cache, and init
        const wrapper = document.createElement('div');
        wrapper.dataset.view = route;
        // nosemgrep
        wrapper.innerHTML = raw(routeDef.component.render());
        app.appendChild(wrapper);
        _viewCache[route] = wrapper;

        if (typeof routeDef.component.init === 'function' && !_viewInited[route]) {
            _viewInited[route] = true;
            try {
                await routeDef.component.init();
            } catch (err) {
                console.error('Error initializing route:', route, err);
            }
        }

        // Translate the rendered view if not in English
        if (typeof I18n !== 'undefined' && I18n.isLoaded()) {
            I18n.translateView(wrapper);
        }

        // Apply version string to newly rendered view
        if (_appVersion) _applyVersion();
    }

    /**
     * Reset a view — destroys its cached DOM so it re-renders fresh next time.
     * Call from a component: window.resetView('generator')
     */
    window.resetView = function (route) {
        if (_viewCache[route]) {
            _viewCache[route].remove();
            delete _viewCache[route];
            delete _viewInited[route];
        }
        // If we're currently on that route, re-navigate to rebuild it
        if (currentRoute === route) {
            currentRoute = null;
            navigate();
        }
    };

    // Listen for hash changes
    window.addEventListener('hashchange', navigate);

    // ============================================================
    //  Global Helpers
    // ============================================================

    window.showLoading = function (text) {
        const overlay = document.getElementById('loading-overlay');
        const textEl = document.getElementById('loading-text');
        if (overlay) overlay.classList.remove('hidden');
        if (textEl) textEl.textContent = text || 'Loading...';
    };

    window.hideLoading = function () {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.add('hidden');
    };

    // ── Global date formatters (dd-MMM-yyyy + timezone) ─────────────
    // Single source of truth for ALL displayed dates. Format: dd-MMM-yyyy
    // (zero-padded day) so dates sort/read consistently app-wide.
    const _MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    // Backend stores timestamps as naive UTC (datetime.utcnow().isoformat(), no
    // 'Z' suffix). JS `new Date()` would read a timezone-less string as LOCAL
    // time, shifting it by the viewer's UTC offset. Append 'Z' so a bare
    // date-time is correctly parsed as UTC (then rendered in the viewer's tz).
    // Strings that already carry a timezone (Z or ±HH:MM) are left untouched.
    function _parseDate(dateStr) {
        let s = String(dateStr);
        const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(s);
        if (!hasTz && /\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(s)) s += 'Z';
        return new Date(s);
    }
    window.formatDate = function(dateStr) {
        if (!dateStr) return '';
        try {
            const d = _parseDate(dateStr);
            if (isNaN(d)) return '';
            const dd = String(d.getDate()).padStart(2, '0');
            return `${dd}-${_MONTHS[d.getMonth()]}-${d.getFullYear()}`;
        } catch { return ''; }
    };
    window.formatTimestamp = function(dateStr) {
        if (!dateStr) return '';
        try {
            const d = _parseDate(dateStr);
            if (isNaN(d)) return '';
            const dd = String(d.getDate()).padStart(2, '0');
            const mon = _MONTHS[d.getMonth()];
            const yyyy = d.getFullYear();
            const hh = String(d.getHours()).padStart(2, '0');
            const mm = String(d.getMinutes()).padStart(2, '0');
            const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'local';
            return `${dd}-${mon}-${yyyy}, ${hh}:${mm} (${tz})`;
        } catch { return ''; }
    };

    window.showToast = function (message, type, duration) {
        type = type || 'info';
        duration = duration || 4000;

        const container = document.getElementById('toast-container');
        if (!container) return;

        const iconMap = {
            success: `<svg class="w-5 h-5 text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
            error:   `<svg class="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
            warning: `<svg class="w-5 h-5 text-yellow-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>`,
            info:    `<svg class="w-5 h-5 text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        };
        const bgMap = {
            success: 'border-green-500/30',
            error:   'border-red-500/30',
            warning: 'border-yellow-500/30',
            info:    'border-blue-500/30',
        };

        const toast = document.createElement('div');
        toast.className = `toast flex items-start gap-3 px-4 py-3 rounded-lg bg-brand-surface border ${bgMap[type] || bgMap.info} shadow-lg`;
        // nosemgrep
        toast.innerHTML = html`
            ${raw(iconMap[type] || iconMap.info)}
            <p class="text-sm text-brand-text flex-1">${message}</p>
            <button class="toast-close p-0.5 rounded hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors flex-shrink-0" title="${typeof t !== 'undefined' ? t('artsmoker.common.dismiss') : 'Dismiss'}">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        `;

        container.appendChild(toast);
        toast.querySelector('.toast-close').addEventListener('click', () => dismissToast(toast));

        const timer = setTimeout(() => dismissToast(toast), duration);
        toast.addEventListener('mouseenter', () => clearTimeout(timer));
        toast.addEventListener('mouseleave', () => {
            setTimeout(() => dismissToast(toast), 2000);
        });

        // Send errors and warnings to the server for logging
        if ((type === 'error' || type === 'warning') && typeof API !== 'undefined') {
            API.log(type, message);
        }
    };

    function dismissToast(toast) {
        if (toast._dismissed) return;
        toast._dismissed = true;
        toast.classList.add('toast-exit');
        toast.addEventListener('animationend', () => toast.remove());
    }

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Styled confirmation dialog — replaces browser confirm().
     * Returns a Promise<boolean>.
     *
     * Usage:
     *   if (!await showConfirm('Delete this?', { detail: 'Cannot be undone.', confirmLabel: 'Delete', danger: true })) return;
     *
     * Options:
     *   title     — heading text (default: 'Confirm')
     *   detail    — optional secondary text (supports \n for line breaks)
     *   confirmLabel — confirm button text (default: 'Continue')
     *   cancelLabel  — cancel button text (default: 'Cancel')
     *   danger    — if true, confirm button is red instead of accent
     */
    window.showConfirm = function (message, opts = {}) {
        return new Promise((resolve) => {
            const title = opts.title || 'Confirm';
            const detail = opts.detail || '';
            const confirmLabel = opts.confirmLabel || 'Continue';
            const cancelLabel = opts.cancelLabel || 'Cancel';
            const danger = opts.danger || false;
            const btnClass = danger
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-brand-accent hover:bg-brand-accent-hover text-white';

            const backdrop = document.createElement('div');
            backdrop.className = 'fixed inset-0 z-[110] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
            // nosemgrep
            backdrop.innerHTML = html`
                <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-md w-full p-6 space-y-4 animate-[fadeIn_0.15s_ease-out]">
                    <h3 class="text-sm font-semibold text-brand-text">${title}</h3>
                    <p class="text-sm text-brand-text-muted">${message}</p>
                    ${detail ? html`<p class="text-xs text-brand-text-muted/70 whitespace-pre-line">${detail}</p>` : ''}
                    <div class="flex gap-2 justify-end pt-2">
                        ${cancelLabel ? html`<button class="cs-confirm-cancel btn btn-sm text-xs px-4 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${cancelLabel}</button>` : ''}
                        <button class="cs-confirm-ok btn btn-sm text-xs px-4 py-2 rounded-lg ${btnClass} font-medium">${confirmLabel}</button>
                    </div>
                </div>`;

            const cleanup = (result) => {
                backdrop.remove();
                resolve(result);
            };

            backdrop.querySelector('.cs-confirm-cancel')?.addEventListener('click', () => cleanup(false));
            backdrop.querySelector('.cs-confirm-ok')?.addEventListener('click', () => cleanup(true));
            backdrop.addEventListener('click', (e) => { if (e.target === backdrop) cleanup(false); });
            document.addEventListener('keydown', function handler(e) {
                if (e.key === 'Escape') { document.removeEventListener('keydown', handler); cleanup(false); }
                if (e.key === 'Enter') { document.removeEventListener('keydown', handler); cleanup(true); }
            });

            document.body.appendChild(backdrop);
            backdrop.querySelector('.cs-confirm-ok').focus();
        });
    };

    // ============================================================
    //  Language Switcher
    // ============================================================

    function _renderLangSwitcher() {
        const container = document.getElementById('lang-switcher');
        if (!container || typeof I18n === 'undefined') return;

        const current = I18n.getLang();
        // nosemgrep
        container.innerHTML = I18n.SUPPORTED_LANGS.map(l => {
            const active = l.code === current;
            return html`<button class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${active
                ? 'bg-brand-accent text-white'
                : 'text-brand-text-muted hover:text-brand-text hover:bg-white/5'}" data-lang="${l.code}" title="${l.tooltip || l.label}">${l.flag}</button>`;
        }).join('');

        container.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-lang]');
            if (btn) I18n.setLang(btn.dataset.lang);
        });
    }

    // ============================================================
    //  Mobile Menu Toggle
    // ============================================================

    document.getElementById('mobile-menu-btn')?.addEventListener('click', () => {
        const menu = document.getElementById('mobile-menu');
        if (menu) menu.classList.toggle('hidden');
    });

    // ============================================================
    //  Boot
    // ============================================================

    // Initialize i18n, then navigate
    (async function _boot() {
        if (typeof I18n !== 'undefined') {
            await I18n.init();
            _renderLangSwitcher();
            I18n.updateDOM(); // Translate static HTML elements
            I18n.onChange(() => {
                // On language change: update static HTML, re-render lang switcher,
                // clear all cached views and re-navigate
                I18n.updateDOM();
                _renderLangSwitcher();
                for (const route of Object.keys(_viewCache)) {
                    _viewCache[route].remove();
                    delete _viewCache[route];
                    delete _viewInited[route];
                }
                currentRoute = null;
                navigate();
            });
        }

        if (!window.location.hash || window.location.hash === '#') {
            window.location.hash = '#' + DEFAULT_ROUTE;
        }
        navigate();
    })();

    // Fetch version from backend — store globally, apply to all views
    // Also check if server is still starting up (auto-Sync in progress)
    let _appVersion = '';
    function _checkHealth() {
        fetch('/api/health').then(r => r.json()).then(data => {
            if (data.version) {
                _appVersion = data.version;
                _applyVersion();
                setTimeout(_applyVersion, 500);
            }
            // Surface background notices (e.g. a deploy that failed while the
            // user was offline → auto-torn-down). Shown once per load; dismissible.
            if (Array.isArray(data.notices) && data.notices.length) {
                _showNotices(data.notices);
            }
            // Show sync-in-progress modal if server is still starting
            if (data.sync_in_progress) {
                _showSyncModal(data.sync_message || 'Discovering model availability in Amazon Bedrock...', true);
                setTimeout(_checkHealth, 3000);
            } else if (!data.ready) {
                _showSyncModal('Server starting up...', false);
                setTimeout(_checkHealth, 2000);
            } else if (data.sync_error) {
                _closeSyncModal(true, data.sync_error);
            } else {
                _closeSyncModal(false);
            }
        }).catch(() => {
            // Server not responding yet — retry
            setTimeout(_checkHealth, 2000);
        });
    }
    _checkHealth();

    // Render durable server notices (deploy started/ready/failed/removed…) in
    // the SAME bottom-right stack as live toasts — one notification system, one
    // position, one look. Severity decides lifetime: info/success auto-close
    // after 8s (and are auto-dismissed server-side so they don't reappear on the
    // next load); warning/error persist until manually dismissed.
    const _shownNotices = new Set();
    function _showNotices(notices) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        notices.forEach(n => {
            if (!n || !n.id || _shownNotices.has(n.id)) return;
            _shownNotices.add(n.id);
            const level = ['success', 'error', 'warning', 'info'].includes(n.level) ? n.level : 'info';
            const iconMap = {
                success: `<svg class="w-5 h-5 text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
                error:   `<svg class="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
                warning: `<svg class="w-5 h-5 text-yellow-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>`,
                info:    `<svg class="w-5 h-5 text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
            };
            const bgMap = {
                success: 'border-green-500/30',
                error:   'border-red-500/30',
                warning: 'border-yellow-500/30',
                info:    'border-blue-500/30',
            };
            const toast = document.createElement('div');
            toast.className = `toast flex items-start gap-3 px-4 py-3 rounded-lg bg-brand-surface border ${bgMap[level]} shadow-lg`;
            // nosemgrep
            toast.innerHTML = html`
                ${raw(iconMap[level])}
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold text-brand-text">${n.title || 'Notice'}</p>
                    <p class="text-xs text-brand-text-muted mt-0.5 leading-relaxed">${n.message || ''}</p>
                </div>
                <button class="toast-close p-0.5 rounded hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors flex-shrink-0" title="${typeof t !== 'undefined' ? t('artsmoker.common.dismiss') : 'Dismiss'}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>`;
            container.appendChild(toast);

            const dismissServerSide = () => {
                fetch(`/api/notices/${encodeURIComponent(n.id)}/dismiss`, { method: 'POST' }).catch(() => {});
            };
            toast.querySelector('.toast-close').addEventListener('click', () => {
                dismissToast(toast);
                dismissServerSide();
            });

            // info/success: auto-close like a regular toast (longer, 8s, since
            // there's a title+body to read) AND mark dismissed server-side so it
            // doesn't come back. warning/error: persist until clicked away.
            if (level === 'info' || level === 'success') {
                let timer = setTimeout(() => { dismissToast(toast); dismissServerSide(); }, 8000);
                toast.addEventListener('mouseenter', () => clearTimeout(timer));
                toast.addEventListener('mouseleave', () => {
                    timer = setTimeout(() => { dismissToast(toast); dismissServerSide(); }, 2000);
                });
            }
        });
    }
    function _escapeNotice(s) {
        const d = document.createElement('div');
        d.textContent = String(s == null ? '' : s);
        return d.innerHTML;
    }

    let _syncModal = null;
    let _sseConnected = false;
    function _showSyncModal(message, connectSSE) {
        if (_syncModal) {
            _syncModal.querySelector('.sync-msg').textContent = message;
            // Connect SSE if not yet connected and sync is active
            if (connectSSE && !_sseConnected) _connectSyncSSE();
            return;
        }
        _syncModal = document.createElement('div');
        _syncModal.className = 'fixed inset-0 z-[200] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
        // nosemgrep
        _syncModal.innerHTML = html`
            <div class="bg-brand-surface rounded-xl border border-brand-border shadow-2xl max-w-lg w-full p-8 space-y-4">
                <div class="text-center">
                    <div class="text-3xl mb-2 sync-timer" style="display:inline-block;animation:spin 2s linear infinite">⏳</div>
                    <style>@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style>
                    <h3 class="text-sm font-semibold text-brand-text">${t('artsmoker.onboarding.setup_title')}</h3>
                    <p class="text-xs text-brand-text-muted mt-1">${t('artsmoker.onboarding.setup_desc')}</p>
                </div>
                <div class="bg-black/20 rounded-lg p-3 space-y-2">
                    <p class="sync-msg text-xs text-brand-accent font-medium">${message}</p>
                    <div class="sync-counts text-[10px] text-brand-text-muted flex gap-4"></div>
                    <div class="sync-log text-[10px] text-brand-text-muted/50 max-h-32 overflow-y-auto font-mono space-y-0.5"></div>
                </div>
            </div>`;
        document.body.appendChild(_syncModal);

        // Connect SSE if sync is active
        if (connectSSE) _connectSyncSSE();
    }

    function _connectSyncSSE() {
        if (_sseConnected) return;
        _sseConnected = true;
        try {
            const sse = new EventSource('/api/sync-progress');
            sse.onmessage = (e) => {
                try {
                    const d = JSON.parse(e.data);
                    if (d.ready || d.message === 'done') {
                        sse.close();
                        return;
                    }
                    const msgEl = _syncModal?.querySelector('.sync-msg');
                    if (msgEl) msgEl.textContent = d.message;
                    // Update model counts
                    const countsEl = _syncModal?.querySelector('.sync-counts');
                    if (countsEl && d.models) {
                        const parts = [];
                        if (d.models.image) parts.push(`🖼 ${d.models.image} image`);
                        if (d.models.chat) parts.push(`💬 ${d.models.chat} chat`);
                        if (d.models.video) parts.push(`🎬 ${d.models.video} video`);
                        const regionMatch = d.message?.match(/(\d+)\/(\d+)/);
                        const regionInfo = regionMatch ? t('artsmoker.onboarding.across_regions').replace('{{done}}', regionMatch[1]).replace('{{total}}', regionMatch[2]) : t('artsmoker.onboarding.in_bedrock');
                        if (parts.length) countsEl.textContent = t('artsmoker.onboarding.models_discovered').replace('{{region}}', regionInfo).replace('{{parts}}', parts.join('  ·  '));
                    }
                    // Prepend to log (newest on top), mark previous as done
                    const logEl = _syncModal?.querySelector('.sync-log');
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
            sse.onerror = () => { sse.close(); _sseConnected = false; };
        } catch { _sseConnected = false; }
    }
    function _closeSyncModal(hadError, errorMsg) {
        if (!_syncModal) return;
        const inner = _syncModal.querySelector('.bg-brand-surface');
        if (hadError) {
            // nosemgrep
            inner.innerHTML = html`
                <div class="text-3xl mb-2">⚠</div>
                <h3 class="text-sm font-semibold text-amber-400">${t('artsmoker.onboarding.discovery_failed')}</h3>
                <p class="text-xs text-brand-text-muted">${t('artsmoker.onboarding.discovery_failed_desc')} <strong>${t('artsmoker.onboarding.sync_from_aws')}</strong> ${t('artsmoker.onboarding.before_using')}</p>
                <p class="text-[10px] text-brand-text-muted/50 mt-1">${errorMsg || t('artsmoker.onboarding.unknown_error')}</p>
                <div class="flex gap-2 justify-center mt-4">
                    <button class="sync-open-settings btn btn-sm text-xs px-5 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">${t('artsmoker.onboarding.open_model_settings')}</button>
                    <button class="sync-dismiss btn btn-sm text-xs px-5 py-2 rounded-lg border border-brand-border hover:bg-white/5 text-brand-text-muted">${t('artsmoker.common.dismiss')}</button>
                </div>`;
            inner.querySelector('.sync-open-settings').addEventListener('click', () => {
                _syncModal.remove();
                _syncModal = null;
                // Open Model Settings modal
                if (window.ModelSettings?.open) window.ModelSettings.open();
            });
            inner.querySelector('.sync-dismiss').addEventListener('click', () => {
                _syncModal.remove();
                _syncModal = null;
            });
            return;
        } else {
            // nosemgrep
            inner.innerHTML = html`
                <div class="text-3xl mb-2">✓</div>
                <h3 class="text-sm font-semibold text-brand-text">${t('artsmoker.onboarding.ready_title')}</h3>
                <p class="text-xs text-brand-text-muted">${t('artsmoker.onboarding.ready_desc')}</p>
                <button class="btn btn-sm text-xs px-6 py-2 mt-3 rounded-lg bg-brand-accent hover:bg-brand-accent-hover text-white font-medium">${t('artsmoker.common.ok')}</button>`;
        }
        inner.querySelector('button').addEventListener('click', () => {
            _syncModal.remove();
            _syncModal = null;
            // Reload the current view so model dropdowns pick up discovered models
            window.resetView?.(window.location.hash.slice(1) || 'image-studio');
            window.dispatchEvent(new HashChangeEvent('hashchange'));
        });
    }

    function _applyVersion() {
        if (!_appVersion) return;
        document.querySelectorAll('.artsmoker-version').forEach(el => {
            el.textContent = `ArtSmoker v${_appVersion}`;
        });
    }

    // Re-apply version after any navigation (views render lazily)
    window.addEventListener('hashchange', () => setTimeout(_applyVersion, 100));

    // Telemetry: track frontend load with client info (fire-and-forget)
    fetch('/api/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // nosemgrep -- serialized HTTP request body; key ordering is irrelevant (not used as an object/map key)
        body: JSON.stringify({
            os: navigator.platform || navigator.userAgentData?.platform || '',
            browser: navigator.userAgent?.split(/[()]/)[1] || '',
            screen: `${screen.width}x${screen.height}`,
        }),
    }).catch(() => {});

    // ============================================================
    //  Global error logging to server
    // ============================================================

    window.addEventListener('error', (e) => {
        if (typeof API !== 'undefined') {
            API.log('error', e.message || 'Uncaught error', `${e.filename}:${e.lineno}:${e.colno}`);
        }
    });

    window.addEventListener('unhandledrejection', (e) => {
        if (typeof API !== 'undefined') {
            const msg = e.reason?.message || e.reason || 'Unhandled promise rejection';
            API.log('error', String(msg), e.reason?.stack?.split('\n')[1]?.trim() || '');
        }
    });

    // ============================================================
    //  Auto-update monitor — detects server restart and reconnects
    // ============================================================

    // Auto-update monitor: lightweight check every 5 minutes (not 30s — restarts
    // happen at most once per 24 hours). If server goes down during a restart,
    // the page stays alive (all content is already rendered in the browser) and
    // we poll until the server comes back, then reload for fresh frontend code.
    (function initUpdateMonitor() {
        let restartBanner = null;
        let waitingForRestart = false;

        let updateDisabled = false;

        async function checkUpdateStatus() {
            if (waitingForRestart || updateDisabled) return;
            try {
                const resp = await fetch('/api/update-status');
                if (!resp.ok) return;
                const status = await resp.json();

                // Stop polling entirely if auto-update is disabled on this server
                if (status.disabled) {
                    updateDisabled = true;
                    return;
                }

                if (status.restarting) {
                    showRestartBanner();
                    waitForServerRestart();
                }
            } catch {
                // Server unreachable but we weren't expecting a restart —
                // this is a crash or network issue, not an auto-update.
                // Don't show any banner — the user's next action will fail
                // naturally and they can refresh.
            }
        }

        function showRestartBanner() {
            if (restartBanner) return;
            restartBanner = document.createElement('div');
            restartBanner.className = 'fixed top-0 inset-x-0 z-[200] bg-amber-600 text-white text-center py-2 text-sm font-medium shadow-lg';
            restartBanner.innerHTML = `
                <span class="animate-pulse mr-2">⟳</span>
                Server updating — restarting with new code. Please wait... <span class="elapsed-time text-white/70 ml-1"></span>
            `;
            document.body.appendChild(restartBanner);
        }

        function waitForServerRestart() {
            if (waitingForRestart) return;
            waitingForRestart = true;
            let elapsed = 0;
            const timeout = 8 * 60 * 1000;  // 8 minutes max wait
            const interval = 10000;          // Poll every 10 seconds

            const poll = setInterval(async () => {
                elapsed += interval;
                // Update banner with elapsed time
                if (restartBanner) {
                    const mins = Math.floor(elapsed / 60000);
                    const secs = Math.floor((elapsed % 60000) / 1000);
                    const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
                    restartBanner.querySelector('.elapsed-time').textContent = timeStr;
                }
                try {
                    const resp = await fetch('/api/update-status');
                    if (resp.ok) {
                        const status = await resp.json();
                        if (!status.restarting) {
                            // Server is back with new code — reload page for fresh frontend
                            clearInterval(poll);
                            if (restartBanner) {
                                restartBanner.innerHTML = '<span class="mr-2">✓</span> Server updated — reloading...';
                                restartBanner.className = restartBanner.className.replace('bg-amber-600', 'bg-emerald-600');
                            }
                            setTimeout(() => location.reload(), 1000);
                            return;
                        }
                    }
                } catch {
                    // Server still down — keep polling (page stays alive, all
                    // rendered content preserved in the browser)
                }
                if (elapsed >= timeout) {
                    clearInterval(poll);
                    waitingForRestart = false;
                    if (restartBanner) {
                        // nosemgrep
                        restartBanner.innerHTML = html`<span class="mr-2">⚠</span> ${t('artsmoker.onboarding.server_timeout')} <button onclick="location.reload()" class="underline ml-2 font-semibold">${t('artsmoker.onboarding.refresh')}</button>`;
                        restartBanner.className = restartBanner.className.replace('bg-amber-600', 'bg-red-600');
                    }
                }
            }, interval);
        }

        // Check once on page load (catch a restart that started while page was closed).
        // Then check every 24 hours (aligned with backend's periodic checker).
        // No need for frequent polling — the backend handles the timing.
        checkUpdateStatus();
        setInterval(checkUpdateStatus, 24 * 60 * 60 * 1000);
    })();

})();
