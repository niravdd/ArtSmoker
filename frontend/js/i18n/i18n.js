/**
 * ArtSmoker — Internationalization (i18n) System
 *
 * Provides `t(key)` for string lookup, language switching, and localStorage persistence.
 * Supported languages: en, ja, zh, ko, fr, es
 *
 * Usage:
 *   t('nav.image_studio')          → "2D Image Studio" (or translated equivalent)
 *   t('gallery.selected_count', {count: 5, plural: 's'})  → "5 items selected"
 *   I18n.setLang('ja')             → Switch to Japanese, reloads UI
 *   I18n.getLang()                  → Current language code
 */
(function () {
    'use strict';

    const SUPPORTED_LANGS = [
        { code: 'en', label: 'English', flag: 'EN' },
        { code: 'ja', label: '日本語', flag: 'JA' },
        { code: 'zh', label: '中文', flag: 'ZH' },
        { code: 'ko', label: '한국어', flag: 'KO' },
        { code: 'fr', label: 'Français', flag: 'FR' },
        { code: 'es', label: 'Español', flag: 'ES' },
    ];

    const STORAGE_KEY = 'artsmoker_lang';
    const DEFAULT_LANG = 'en';

    let _currentLang = DEFAULT_LANG;
    let _strings = {};       // Current language strings (flat: "nav.image_studio" → "2D Image Studio")
    let _fallback = {};      // English fallback strings
    let _loaded = false;
    let _onChangeCallbacks = [];

    // ── Public API ───────────────────────────────────────────────────

    window.I18n = {
        SUPPORTED_LANGS,

        /**
         * Update all DOM elements with data-i18n attributes.
         * Call after language change or page render.
         *   <span data-i18n="nav.gallery">Gallery</span>
         *   <input data-i18n-placeholder="common.search" placeholder="Search">
         *   <button data-i18n-title="common.settings" title="Settings">
         */
        updateDOM() {
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.dataset.i18n;
                if (key) el.textContent = t(key);
            });
            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                const key = el.dataset.i18nPlaceholder;
                if (key) el.placeholder = t(key);
            });
            document.querySelectorAll('[data-i18n-title]').forEach(el => {
                const key = el.dataset.i18nTitle;
                if (key) el.title = t(key);
            });
        },

        async init() {
            _currentLang = localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG;
            if (!SUPPORTED_LANGS.some(l => l.code === _currentLang)) _currentLang = DEFAULT_LANG;

            // Always load English as fallback
            _fallback = await _loadLangFile('en');

            if (_currentLang !== 'en') {
                _strings = await _loadLangFile(_currentLang);
            } else {
                _strings = _fallback;
            }
            _buildReverseLookup();
            _loaded = true;
        },

        getLang() {
            return _currentLang;
        },

        async setLang(code) {
            if (code === _currentLang) return;
            if (!SUPPORTED_LANGS.some(l => l.code === code)) return;

            _currentLang = code;
            localStorage.setItem(STORAGE_KEY, code);

            if (code === 'en') {
                _strings = _fallback;
            } else {
                _strings = await _loadLangFile(code);
            }
            _buildReverseLookup();

            // Update the lang attribute for CSS selectors / font loading
            document.documentElement.lang = code;

            // Notify listeners (components can re-render)
            for (const cb of _onChangeCallbacks) {
                try { cb(code); } catch (e) { console.error('i18n onChange error:', e); }
            }
        },

        onChange(callback) {
            _onChangeCallbacks.push(callback);
        },

        isLoaded() {
            return _loaded;
        },
    };

    // ── t() — the main translation function ──────────────────────────

    window.t = function (key, params) {
        let str = _strings[key] || _fallback[key] || key;

        // Replace {{param}} placeholders
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), v);
            }
        }
        return str;
    };

    // ── Language file loader ─────────────────────────────────────────

    async function _loadLangFile(code) {
        try {
            const resp = await fetch(`/js/i18n/${code}.json?v=${Date.now()}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const nested = await resp.json();
            return _flatten(nested);
        } catch (err) {
            console.warn(`Failed to load language file ${code}.json:`, err);
            return {};
        }
    }

    /**
     * Build a reverse lookup: English text → translation key.
     * Used for post-render DOM translation of component-generated HTML.
     */
    let _reverseLookup = null;  // English text → i18n key

    function _buildReverseLookup() {
        if (_currentLang === 'en') { _reverseLookup = null; return; }
        _reverseLookup = {};
        for (const [key, enText] of Object.entries(_fallback)) {
            if (typeof enText === 'string' && enText.length > 1 && !/^\d+$/.test(enText)) {
                _reverseLookup[enText] = key;
            }
        }
    }

    /**
     * Translate component-rendered HTML by scanning text nodes and replacing
     * known English strings with translations. Safe: only touches textContent,
     * not structure or attributes.
     *
     * Call after a component renders: I18n.translateView(container)
     */
    window.I18n.translateView = function (container) {
        if (!container || _currentLang === 'en' || !_reverseLookup) return;

        // Translate text in elements with common UI roles
        const selectors = 'h1,h2,h3,h4,h5,h6,p,span,label,button,a,option,summary,th,td';
        container.querySelectorAll(selectors).forEach(el => {
            // Skip elements with data-i18n (already handled)
            if (el.dataset.i18n) return;
            // Skip elements with children that are also text-bearing (avoid double-translating)
            if (el.querySelector(selectors)) return;

            const text = el.textContent.trim();
            if (!text) return;

            // Exact match
            const key = _reverseLookup[text];
            if (key && _strings[key]) {
                el.textContent = _strings[key];
                return;
            }
        });

        // Translate placeholders
        container.querySelectorAll('input[placeholder],textarea[placeholder]').forEach(el => {
            const ph = el.placeholder;
            if (!ph) return;
            const key = _reverseLookup[ph];
            if (key && _strings[key]) {
                el.placeholder = _strings[key];
            }
        });

        // Translate title attributes
        container.querySelectorAll('[title]').forEach(el => {
            const title = el.title;
            if (!title) return;
            const key = _reverseLookup[title];
            if (key && _strings[key]) {
                el.title = _strings[key];
            }
        });

        // Also handle data-i18n attributes in dynamic content
        I18n.updateDOM();
    };

    /**
     * Flatten nested JSON into dot-notation keys.
     * { nav: { home: "Home" } } → { "nav.home": "Home" }
     */
    function _flatten(obj, prefix = '') {
        const result = {};
        for (const [key, value] of Object.entries(obj)) {
            const fullKey = prefix ? `${prefix}.${key}` : key;
            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                Object.assign(result, _flatten(value, fullKey));
            } else {
                result[fullKey] = value;
            }
        }
        return result;
    }
})();
