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
        'image-studio':  { component: window.ImageStudio, label: '2D Image Studio' },
        'type-studio':   { component: window.TypeStudio, label: 'Type Studio' },
        'video-studio':  { component: window.VideoStudio, label: 'Video Studio' },
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
            app.innerHTML = '<p class="text-center py-12 text-brand-text-muted">Page not found.</p>';
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
            return;
        }

        // First visit: render, cache, and init
        const wrapper = document.createElement('div');
        wrapper.dataset.view = route;
        wrapper.innerHTML = routeDef.component.render();
        app.appendChild(wrapper);
        _viewCache[route] = wrapper;

        if (typeof routeDef.component.init === 'function' && !_viewInited[route]) {
            _viewInited[route] = true;
            try {
                await routeDef.component.init();
            } catch (err) {
                console.error(`Error initializing ${route}:`, err);
            }
        }
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
        toast.innerHTML = `
            ${iconMap[type] || iconMap.info}
            <p class="text-sm text-brand-text flex-1">${escapeHTML(message)}</p>
            <button class="toast-close p-0.5 rounded hover:bg-white/5 text-brand-text-muted hover:text-brand-text transition-colors flex-shrink-0" title="Dismiss">
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

    if (!window.location.hash || window.location.hash === '#') {
        window.location.hash = '#' + DEFAULT_ROUTE;
    }
    navigate();

    // Fetch version from backend — store globally, apply to all views
    let _appVersion = '';
    fetch('/api/health').then(r => r.json()).then(data => {
        if (data.version) {
            _appVersion = data.version;
            _applyVersion();
        }
    }).catch(() => {});

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

})();
