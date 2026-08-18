/**
 * ArtSmoker — Chat Studio Component (Phase 1-3)
 *
 * Full-featured LLM chat: streaming, markdown, code highlighting,
 * sessions, search, export, vision/images, context compaction,
 * system prompt templates, regenerate, edit/resend, model comparison.
 */
(function () {
    'use strict';

    let _container = null;
    let _models = [];
    let _sessions = [];
    let _currentSession = null;
    let _streaming = false;
    let _abortController = null;
    let _searchQuery = '';
    let _sessionStartTime = null; // Track when user started interacting with current session
    let _selectedModelId = ''; // Custom dropdown selection state

    // System prompt templates
    const TEMPLATES = [
        { name: () => t('chat_studio.template_general'), prompt: 'You are a helpful, accurate, and concise assistant.' },
        { name: () => t('chat_studio.template_coding'), prompt: 'You are an expert software engineer. Write clean, efficient, well-documented code. Explain your reasoning. Use best practices and modern patterns. When showing code, always include the language in fenced code blocks.' },
        { name: () => t('chat_studio.template_creative'), prompt: 'You are a creative writing assistant. Help with storytelling, dialogue, world-building, and prose. Be imaginative and evocative. Offer multiple options when asked.' },
        { name: () => t('chat_studio.template_game'), prompt: 'You are a game design consultant. Help with game mechanics, level design, balance, narrative design, and player experience. Reference established design patterns and successful games as examples.' },
        { name: () => t('chat_studio.template_data'), prompt: 'You are a data analysis expert. Help with data exploration, statistics, visualization recommendations, SQL queries, and Python/pandas code. Be precise with numbers.' },
        { name: () => t('chat_studio.template_technical'), prompt: 'You are a technical documentation expert. Write clear, structured documentation with proper formatting. Use headings, bullet points, tables, and code examples. Optimize for readability.' },
    ];

    window.ChatStudio = {
        render() {
            return _renderShell();
        },

        async init() {
            _container = document.querySelector('[data-view="chat-studio"]');
            if (!_container) return;
            _attachEvents();
            await _loadModels();
            await _loadSessions();
            if (_sessions.length === 0) await _createSession();
            else await _loadSession(_sessions[0].session_id);
            window.addEventListener('model-settings-closed', () => _loadModels());
        },

        onShow() { _scrollToBottom(); },
    };

    // ── Shell layout ─────────────────────────────────────────────────

    function _renderShell() {
        return `
        <div class="flex gap-4 h-[calc(100vh-7rem)]">
            <!-- Session Sidebar -->
            <div class="w-60 flex-shrink-0 flex flex-col bg-brand-surface/50 rounded-xl border border-brand-border overflow-hidden">
                <div class="p-3 border-b border-brand-border space-y-2">
                    <button id="cs-new-chat" class="btn btn-primary btn-sm w-full text-xs">${t('chat_studio.new_chat')}</button>
                    <input id="cs-session-search" type="text" class="input text-[10px] w-full" placeholder="${t('chat_studio.search_sessions')}">
                </div>
                <div id="cs-session-list" class="flex-1 overflow-auto p-2 space-y-1"></div>
                <p class="artsmoker-version text-[9px] text-brand-text-dim/30 text-center py-2">ArtSmoker</p>
            </div>

            <!-- Main Chat Area -->
            <div class="flex-1 flex flex-col bg-brand-surface/30 rounded-xl border border-brand-border overflow-hidden">
                <!-- Header -->
                <div class="px-4 py-3 border-b border-brand-border space-y-2">
                    <!-- Sync hint (shown when few models available) -->
                    <div id="cs-sync-hint" class="hidden text-[10px] text-amber-400 bg-amber-400/5 border border-amber-400/20 rounded-lg px-3 py-1.5 flex items-center gap-2">
                        <span>${t('chat_studio.sync_hint')}</span>
                        <button id="cs-open-settings" class="text-brand-accent hover:text-brand-accent-hover font-medium">${t('chat_studio.open_settings')}</button>
                    </div>
                    <div class="flex items-center gap-3 flex-wrap">
                        <div id="cs-model-multi" class="relative flex-1 min-w-[200px]">
                            <button id="cs-model-btn" type="button" class="input text-left flex items-center justify-between w-full cursor-pointer text-xs font-mono">
                                <span id="cs-model-label" class="truncate">${t('chat.select_model')}</span>
                                <svg class="w-3.5 h-3.5 text-brand-text-muted flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                            </button>
                            <div id="cs-model-dropdown" class="hidden absolute z-50 mt-1 min-w-full w-max max-h-[28rem] overflow-y-auto rounded-lg border border-brand-border shadow-xl" style="background: var(--bg, #0f172a)"></div>
                        </div>
                        <select id="cs-region-picker" class="input text-[10px] font-mono w-32" title="${t('common.region')}"></select>
                        <div class="flex items-center gap-2 text-[10px] text-brand-text-muted">
                            <span>${t('chat_studio.temperature')}: <input type="number" id="cs-temperature" class="input text-[10px] w-14 text-center" value="0.7" min="0" max="2" step="0.1"></span>
                            <span>${t('chat_studio.max_tokens')}: <input type="number" id="cs-max-tokens" class="input text-[10px] w-16 text-center" value="4096" min="1" max="32000" step="256"></span>
                            <span>|</span>
                            <button id="cs-export-md" class="text-brand-accent hover:text-brand-accent-hover" title="${t('chat_studio.export_title')}">${t('chat_studio.export_md')}</button>
                            <button id="cs-compact-btn" class="text-amber-400 hover:text-amber-300" title="${t('chat_studio.compact_title')}">${t('chat_studio.compact')}</button>
                            <button id="cs-search-btn" class="text-brand-text-muted hover:text-brand-text" title="${t('common.search')}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                            </button>
                            <button id="cs-model-settings" class="p-1 rounded bg-emerald-700 text-white hover:bg-emerald-600 transition-colors" title="${t('chat_studio.model_settings')}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                            </button>
                        </div>
                    </div>
                    <!-- Context bar -->
                    <div class="flex items-center gap-2">
                        <span class="text-[10px] text-brand-text-muted flex-shrink-0">${t('chat_studio.context')}:</span>
                        <div class="flex-1 h-2 rounded-full bg-brand-bg overflow-hidden">
                            <div id="cs-context-bar" class="h-full rounded-full bg-gradient-to-r from-brand-accent to-purple-500 transition-all duration-300" style="width: 0%"></div>
                        </div>
                        <span id="cs-context-label" class="text-[10px] text-brand-text-muted font-mono flex-shrink-0">0 / 128K</span>
                    </div>
                    <!-- Pricing info -->
                    <div id="cs-pricing-info" class="text-[10px] text-brand-text-muted"></div>
                    <!-- System prompt -->
                    <details class="group">
                        <summary class="text-[10px] text-brand-accent cursor-pointer hover:text-brand-accent-hover select-none">
                            <span class="group-open:hidden">${t('chat_studio.system_prompt')}</span>
                            <span class="hidden group-open:inline">${t('chat_studio.system_prompt_hide')}</span>
                        </summary>
                        <div class="flex gap-2 mt-1">
                            <select id="cs-template-picker" class="input text-[10px] w-40">
                                <option value="">${t('chat_studio.templates')}</option>
                                ${TEMPLATES.map(tpl => `<option value="${_esc(tpl.prompt)}">${_esc(tpl.name())}</option>`).join('')}
                            </select>
                            <textarea id="cs-system-prompt" class="input text-xs flex-1 h-16 resize-y font-mono" placeholder="${t('chat_studio.system_prompt')}..."></textarea>
                        </div>
                    </details>
                    <!-- Search bar (hidden by default) -->
                    <div id="cs-search-bar" class="hidden flex gap-2">
                        <input id="cs-chat-search" type="text" class="input text-xs flex-1" placeholder="${t('chat_studio.search_in_chat')}">
                        <button id="cs-search-close" class="text-brand-text-muted hover:text-brand-text text-xs px-2">&times;</button>
                        <span id="cs-search-results" class="text-[10px] text-brand-text-muted self-center"></span>
                    </div>
                </div>

                <!-- Messages -->
                <div id="cs-messages" class="flex-1 overflow-auto px-4 py-3 space-y-4"></div>

                <!-- Input area -->
                <div class="px-4 py-3 border-t border-brand-border">
                    <!-- Image attachments preview -->
                    <div id="cs-attachments" class="hidden flex gap-2 mb-2 flex-wrap"></div>
                    <div class="flex gap-2">
                        <div class="flex flex-col gap-1 justify-end">
                            <label id="cs-attach-btn" class="btn btn-secondary btn-sm text-xs px-2 cursor-pointer" title="${t('chat_studio.attach_image')}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
                                <input type="file" id="cs-file-input" class="hidden" accept="image/*" multiple>
                            </label>
                        </div>
                        <textarea id="cs-input" class="input text-sm flex-1 resize-none" rows="2" placeholder="${t('chat_studio.input_placeholder')}"></textarea>
                        <div class="flex flex-col gap-1">
                            <button id="cs-send" class="btn btn-primary btn-sm text-xs px-4 h-full">${t('chat_studio.send')}</button>
                            <button id="cs-stop" class="btn btn-sm text-xs px-4 bg-red-600 hover:bg-red-500 text-white hidden">${t('chat_studio.stop')}</button>
                        </div>
                    </div>
                    <div id="cs-totals" class="flex items-center gap-4 mt-2 text-[10px] text-brand-text-muted">
                        <span>${t('chat_studio.tokens')}: <span id="cs-total-tokens" class="font-mono">0</span></span>
                        <span>${t('chat_studio.est_cost')}: <span id="cs-total-cost" class="font-mono text-brand-accent">$0.00</span></span>
                        <span>${t('chat_studio.messages')}: <span id="cs-msg-count" class="font-mono">0</span></span>
                    </div>
                </div>
            </div>
        </div>`;
    }

    // ── Events ───────────────────────────────────────────────────────

    function _attachEvents() {
        _container.querySelector('#cs-new-chat')?.addEventListener('click', _createSession);
        _container.querySelector('#cs-send')?.addEventListener('click', () => _sendMessage());
        _container.querySelector('#cs-stop')?.addEventListener('click', _stopStream);

        const input = _container.querySelector('#cs-input');
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); _sendMessage(); }
        });

        // Paste image from clipboard
        input?.addEventListener('paste', (e) => {
            const items = e.clipboardData?.items;
            if (!items) return;
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    e.preventDefault();
                    const file = item.getAsFile();
                    if (file) _addImageAttachment(file);
                }
            }
        });

        // File input
        _container.querySelector('#cs-file-input')?.addEventListener('change', (e) => {
            for (const file of e.target.files) _addImageAttachment(file);
            e.target.value = '';
        });

        // Custom model dropdown: toggle open/close
        _container.querySelector('#cs-model-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            const dd = _container.querySelector('#cs-model-dropdown');
            dd?.classList.toggle('hidden');
        });
        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#cs-model-multi')) {
                _container?.querySelector('#cs-model-dropdown')?.classList.add('hidden');
            }
        });
        // Handle model selection from custom dropdown
        _container.querySelector('#cs-model-dropdown')?.addEventListener('click', (e) => {
            const item = e.target.closest('.cs-model-item');
            if (!item) return;
            const modelId = item.dataset.modelId;
            _selectedModelId = modelId;
            // Update button label (show short model name, not full label)
            const label = _container.querySelector('#cs-model-label');
            const modelObj = _models.find(m => m.model_id === modelId);
            if (label) label.textContent = modelObj?.label || modelId;
            // Highlight active item
            _container.querySelectorAll('.cs-model-item').forEach(el => el.classList.remove('bg-brand-accent/15'));
            item.classList.add('bg-brand-accent/15');
            // Close dropdown
            _container.querySelector('#cs-model-dropdown')?.classList.add('hidden');
            // Update session state
            if (_currentSession) {
                _currentSession.model_id = modelId;
                _updateRegionPicker();
                _updatePricingInfo();
                _updateContextBar();
                _saveCurrentSession();
            }
        });

        // Region picker
        _container.querySelector('#cs-region-picker')?.addEventListener('change', (e) => {
            if (_currentSession) {
                _currentSession.region_override = e.target.value;
                _saveCurrentSession();
            }
        });

        // Open Model Settings — jump to Chat Studio tab
        _container.querySelector('#cs-open-settings')?.addEventListener('click', () => window.ModelSettings?.open('chat-studio'));
        _container.querySelector('#cs-model-settings')?.addEventListener('click', () => window.ModelSettings?.open('chat-studio'));

        _container.querySelector('#cs-temperature')?.addEventListener('change', (e) => {
            if (_currentSession) { _currentSession.temperature = parseFloat(e.target.value) || 0.7; _saveCurrentSession(); }
        });
        _container.querySelector('#cs-max-tokens')?.addEventListener('change', (e) => {
            if (_currentSession) { _currentSession.max_tokens = parseInt(e.target.value) || 4096; _saveCurrentSession(); }
        });
        _container.querySelector('#cs-system-prompt')?.addEventListener('blur', (e) => {
            if (_currentSession) { _currentSession.system_prompt = e.target.value; _saveCurrentSession(); }
        });

        // Template picker
        _container.querySelector('#cs-template-picker')?.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val) {
                const sys = _container.querySelector('#cs-system-prompt');
                if (sys) sys.value = val;
                if (_currentSession) { _currentSession.system_prompt = val; _saveCurrentSession(); }
            }
            e.target.value = '';
        });

        // Export
        _container.querySelector('#cs-export-md')?.addEventListener('click', _exportMarkdown);

        // Compact
        _container.querySelector('#cs-compact-btn')?.addEventListener('click', _compactContext);

        // Search
        _container.querySelector('#cs-search-btn')?.addEventListener('click', () => {
            _container.querySelector('#cs-search-bar')?.classList.toggle('hidden');
            _container.querySelector('#cs-chat-search')?.focus();
        });
        _container.querySelector('#cs-search-close')?.addEventListener('click', () => {
            _container.querySelector('#cs-search-bar')?.classList.add('hidden');
            _container.querySelector('#cs-chat-search').value = '';
            _searchQuery = '';
            _renderMessages();
        });
        _container.querySelector('#cs-chat-search')?.addEventListener('input', (e) => {
            _searchQuery = e.target.value;
            _highlightSearch();
        });

        // Session search
        _container.querySelector('#cs-session-search')?.addEventListener('input', (e) => {
            _renderSessionList(e.target.value.toLowerCase());
        });

        // Delegate clicks on messages (regenerate, edit, fork)
        _container.querySelector('#cs-messages')?.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const action = btn.dataset.action;
            const idx = parseInt(btn.dataset.idx);
            if (action === 'regenerate') _regenerateAt(idx);
            else if (action === 'edit') _editMessage(idx);
            else if (action === 'fork') _forkAt(idx);
        });
    }

    // ── Image attachments (Phase 3: Vision) ──────────────────────────

    let _pendingImages = []; // [{name, base64, dataUrl}]

    function _addImageAttachment(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUrl = e.target.result;
            const base64 = dataUrl.split(',')[1];
            _pendingImages.push({ name: file.name, base64, dataUrl });
            _renderAttachments();
        };
        reader.readAsDataURL(file);
    }

    function _renderAttachments() {
        const el = _container.querySelector('#cs-attachments');
        if (!el) return;
        if (_pendingImages.length === 0) { el.classList.add('hidden'); el.innerHTML = ''; return; }
        el.classList.remove('hidden');
        // nosemgrep
        el.innerHTML = _pendingImages.map((img, i) => html`
            <div class="relative group">
                <img src="${img.dataUrl}" class="w-16 h-16 object-cover rounded-lg border border-brand-border">
                <button class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" onclick="this.closest('[id=cs-attachments]')?.dispatchEvent(new CustomEvent('remove-img', {detail: ${i}}))">&times;</button>
            </div>`).join('');
        el.addEventListener('remove-img', (e) => { _pendingImages.splice(e.detail, 1); _renderAttachments(); }, { once: true });
    }

    // ── Models ───────────────────────────────────────────────────────

    async function _loadModels() {
        try {
            const data = await fetch('/api/chat/models').then(r => r.json());
            _models = data.models || [];
            _renderModelPicker();
        } catch (err) { console.error('Failed to load chat models:', err); }
    }

    function _renderModelPicker() {
        const dd = _container.querySelector('#cs-model-dropdown');
        if (!dd) return;

        // Group by provider
        const byProvider = {};
        for (const m of _models) {
            const provider = m.provider || t('common.unknown');
            if (!byProvider[provider]) byProvider[provider] = [];
            byProvider[provider].push(m);
        }

        const rows = [];
        for (const [provider, models] of Object.entries(byProvider)) {
            rows.push(html`<div class="px-3 pt-2 pb-1 text-[10px] font-semibold text-brand-text-muted uppercase tracking-wider">${provider}</div>`);
            for (const m of models) {
                const ctx = m.max_context_tokens >= 1000000 ? `${Math.round(m.max_context_tokens / 1000000)}M` : `${Math.round(m.max_context_tokens / 1000)}K`;
                const vision = m.has_vision ? ' [vision]' : '';
                const source = m.model_source !== 'foundation' ? ` (${m.model_source})` : '';
                const regions = (m.available_regions || []).length;
                const regionHint = regions > 1 ? ` [${regions} regions]` : '';
                const price = m.pricing?.input_per_1k ? ` · $${m.pricing.input_per_1k}/1K in` : '';
                const label = `${m.label} — ${ctx}${price}${vision}${source}${regionHint}`;
                const active = m.model_id === _selectedModelId ? ' bg-brand-accent/15' : '';
                rows.push(html`<div class="cs-model-item flex items-center gap-2 text-xs font-mono cursor-pointer py-1.5 px-3 hover:bg-brand-bg/60 whitespace-nowrap${active}" data-model-id="${m.model_id}" data-label="${label}">${label}</div>`);
            }
        }
        // nosemgrep
        dd.innerHTML = html`${rows}`;

        // If no selection yet, auto-select first model
        if (!_selectedModelId && _models.length) {
            _selectedModelId = _models[0].model_id;
        }
        // Update button label to match current selection
        const selected = _models.find(m => m.model_id === _selectedModelId);
        if (selected) {
            const label = _container.querySelector('#cs-model-label');
            if (label) label.textContent = selected.label;
        }

        _updatePricingInfo();

        // Show sync hint if only category models are available (no discovered chat_models)
        const hint = _container.querySelector('#cs-sync-hint');
        if (hint) {
            const hasDiscovered = _models.some(m => !m.key.startsWith('cat_'));
            hint.classList.toggle('hidden', hasDiscovered || _models.length > 5);
        }

        _updateRegionPicker();
    }

    function _getSelectedModel() {
        return _models.find(m => m.model_id === _selectedModelId) || _models[0] || {};
    }

    function _updateRegionPicker() {
        const model = _getSelectedModel();
        const sel = _container.querySelector('#cs-region-picker');
        if (!sel) return;

        const regions = model.available_regions || [model.region].filter(Boolean);
        if (regions.length <= 1) {
            // nosemgrep
            sel.innerHTML = html`<option value="${regions[0] || ''}">${regions[0] || t('common.default')}</option>`;
            sel.disabled = true;
        } else {
            // nosemgrep
            sel.innerHTML = regions.map(r => html`<option value="${r}">${r}</option>`).join('');
            sel.disabled = false;
            // Restore region override if saved
            if (_currentSession?.region_override && regions.includes(_currentSession.region_override)) {
                sel.value = _currentSession.region_override;
            }
        }
    }

    function _updatePricingInfo() {
        const model = _getSelectedModel();
        const el = _container.querySelector('#cs-pricing-info');
        if (!el) return;

        const p = model.pricing;
        if (p && p.input_per_1k) {
            const input1k = `$${p.input_per_1k.toFixed(4)}`;
            const output1k = `$${p.output_per_1k.toFixed(4)}`;
            // Calculate what 10K tokens would cost (typical short conversation)
            const est10k = ((p.input_per_1k * 7) + (p.output_per_1k * 3)).toFixed(3);
            // Calculate what 100K tokens would cost (long conversation)
            const est100k = ((p.input_per_1k * 70) + (p.output_per_1k * 30)).toFixed(2);
            // nosemgrep
            el.innerHTML = html`${t('chat_studio.pricing_label')}: <span class="text-brand-text/70">${input1k}/1K input</span> · <span class="text-brand-text/70">${output1k}/1K output</span> · <span class="text-brand-accent/70" title="Estimated cost for ~10K tokens (70% input, 30% output)">~$${est10k}/10K tokens</span> · <span class="text-amber-400/70" title="Estimated cost for ~100K tokens (70% input, 30% output)">~$${est100k}/100K tokens</span>`;
        } else {
            // nosemgrep
            el.innerHTML = html`<span class="text-brand-text-muted/50">${t('chat_studio.pricing_not_available')}</span>`;
        }
    }

    // ── Context bar ──────────────────────────────────────────────────

    function _updateContextBar() {
        const model = _getSelectedModel();
        const maxCtx = model.max_context_tokens || 128000;
        const used = (_currentSession?.total_input_tokens || 0) + (_currentSession?.total_output_tokens || 0);
        const pct = Math.min(100, Math.round(used / maxCtx * 100));
        const bar = _container.querySelector('#cs-context-bar');
        const label = _container.querySelector('#cs-context-label');
        if (bar) {
            bar.style.width = `${pct}%`;
            if (pct > 90) bar.className = 'h-full rounded-full bg-gradient-to-r from-red-500 to-red-400 transition-all duration-300';
            else if (pct > 70) bar.className = 'h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400 transition-all duration-300';
            else bar.className = 'h-full rounded-full bg-gradient-to-r from-brand-accent to-purple-500 transition-all duration-300';
        }
        if (label) {
            const fmt = (n) => n >= 1000000 ? `${(n / 1000000).toFixed(1)}M` : n >= 1000 ? `${Math.round(n / 1000)}K` : String(n);
            label.textContent = `${fmt(used)} / ${fmt(maxCtx)} (${pct}%)`;
        }
    }

    function _updateTotals() {
        if (!_currentSession) return;
        const totalTok = (_currentSession.total_input_tokens || 0) + (_currentSession.total_output_tokens || 0);
        const el = (id) => _container.querySelector(`#${id}`);
        if (el('cs-total-tokens')) el('cs-total-tokens').textContent = totalTok.toLocaleString();
        if (el('cs-total-cost')) el('cs-total-cost').textContent = `$${(_currentSession.total_cost_usd || 0).toFixed(4)}`;
        if (el('cs-msg-count')) el('cs-msg-count').textContent = (_currentSession.messages || []).length;
        _updateContextBar();
    }

    // ── Sessions ─────────────────────────────────────────────────────

    async function _loadSessions() {
        try {
            const data = await fetch('/api/chat/sessions').then(r => r.json());
            _sessions = data.sessions || [];
            _renderSessionList();
        } catch (err) { console.error('Failed to load sessions:', err); }
    }

    function _renderSessionList(filter = '') {
        const el = _container.querySelector('#cs-session-list');
        if (!el) return;
        const filtered = filter ? _sessions.filter(s => s.title.toLowerCase().includes(filter)) : _sessions;

        // nosemgrep
        el.innerHTML = filtered.length === 0
            ? html`<p class="text-[10px] text-brand-text-muted text-center py-4">${t('chat_studio.no_conversations')}</p>`
            : filtered.map(s => {
                const active = _currentSession?.session_id === s.session_id;
                const msgs = s.message_count || 0;
                const cost = s.total_cost_usd > 0 ? ` · $${s.total_cost_usd.toFixed(2)}` : '';
                return html`
                    <div class="cs-session-item group flex items-center gap-1 px-2 py-1.5 rounded-lg cursor-pointer text-xs transition-colors ${active ? 'bg-brand-accent/15 text-brand-accent' : 'text-brand-text-muted hover:bg-white/5'}" data-sid="${s.session_id}">
                        <span class="cs-session-title flex-1 truncate" data-sid="${s.session_id}">${s.title}</span>
                        <span class="text-[9px] opacity-60 flex-shrink-0">${msgs}${cost}</span>
                        <div class="hidden group-hover:flex items-center gap-0.5 flex-shrink-0">
                            <button class="cs-rename-session text-brand-text-muted hover:text-brand-text text-[10px] px-0.5" data-sid="${s.session_id}" title="${t('chat_studio.rename')}">${t('chat_studio.rename')}</button>
                            <button class="cs-dup-session text-brand-text-muted hover:text-brand-text text-[10px] px-0.5" data-sid="${s.session_id}" title="${t('chat_studio.duplicate')}">${t('chat_studio.duplicate')}</button>
                            <button class="cs-delete-session text-red-400 hover:text-red-300 text-[10px] px-0.5" data-sid="${s.session_id}" title="${t('common.delete')}">&times;</button>
                        </div>
                    </div>`;
            }).join('');

        // Click handlers
        el.querySelectorAll('.cs-session-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('.cs-rename-session, .cs-dup-session, .cs-delete-session')) return;
                _loadSession(item.dataset.sid);
            });
        });
        el.querySelectorAll('.cs-delete-session').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (!await window.showConfirm(t('chat_studio.delete_confirm'), { title: t('chat_studio.delete_title'), confirmLabel: t('common.delete'), danger: true })) return;
                await fetch(`/api/chat/sessions/${btn.dataset.sid}`, { method: 'DELETE' });
                if (_currentSession?.session_id === btn.dataset.sid) _currentSession = null;
                await _loadSessions();
                if (_sessions.length > 0 && !_currentSession) await _loadSession(_sessions[0].session_id);
                else if (_sessions.length === 0) await _createSession();
            });
        });
        el.querySelectorAll('.cs-dup-session').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const resp = await fetch(`/api/chat/sessions/${btn.dataset.sid}/duplicate`, { method: 'POST' });
                if (resp.ok) { const s = await resp.json(); await _loadSessions(); await _loadSession(s.session_id); }
            });
        });
        el.querySelectorAll('.cs-rename-session').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const titleEl = el.querySelector(`.cs-session-title[data-sid="${btn.dataset.sid}"]`);
                if (!titleEl) return;
                const currentTitle = titleEl.textContent;
                // nosemgrep
                titleEl.innerHTML = html`<input type="text" class="input text-[10px] w-full" value="${currentTitle}">`;
                const inp = titleEl.querySelector('input');
                inp.focus();
                inp.select();
                const save = async () => {
                    const newTitle = inp.value.trim() || currentTitle;
                    await fetch(`/api/chat/sessions/${btn.dataset.sid}`, {
                        method: 'PUT', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: newTitle }),
                    });
                    if (_currentSession?.session_id === btn.dataset.sid) _currentSession.title = newTitle;
                    await _loadSessions();
                };
                inp.addEventListener('blur', save, { once: true });
                inp.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') inp.blur(); });
            });
        });
    }

    async function _createSession() {
        const model = _getSelectedModel();
        try {
            const session = await fetch('/api/chat/sessions', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: t('chat_studio.new_chat').replace('+ ', ''), model_id: model.model_id || '' }),
            }).then(r => r.json());
            await _loadSessions();
            await _loadSession(session.session_id);
        } catch (err) { window.showToast?.(t('misc.chat_failed_session') + ': ' + err.message, 'error'); }
    }

    async function _loadSession(sessionId) {
        // Flush telemetry for the previous session before switching
        _flushSessionTelemetry();

        try {
            const session = await fetch(`/api/chat/sessions/${sessionId}`).then(r => r.json());
            _currentSession = session;
            _sessionStartTime = Date.now();
            _pendingImages = [];
            _renderAttachments();

            // Update custom model dropdown selection
            if (session.model_id) {
                _selectedModelId = session.model_id;
                const selected = _models.find(m => m.model_id === session.model_id);
                const label = _container.querySelector('#cs-model-label');
                if (label && selected) label.textContent = selected.label;
                // Update highlight in dropdown
                _container.querySelectorAll('.cs-model-item').forEach(el => {
                    el.classList.toggle('bg-brand-accent/15', el.dataset.modelId === session.model_id);
                });
            }
            const temp = _container.querySelector('#cs-temperature');
            if (temp) temp.value = session.temperature || 0.7;
            const maxTok = _container.querySelector('#cs-max-tokens');
            if (maxTok) maxTok.value = session.max_tokens || 4096;
            const sys = _container.querySelector('#cs-system-prompt');
            if (sys) sys.value = session.system_prompt || '';

            _updateRegionPicker();
            _renderMessages();
            _updateTotals();
            _renderSessionList();
        } catch (err) { console.error('Failed to load session:', err); }
    }

    async function _saveCurrentSession() {
        if (!_currentSession) return;
        try {
            await fetch(`/api/chat/sessions/${_currentSession.session_id}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(_currentSession),
            });
        } catch (err) { console.error('Failed to save session:', err); }
    }

    // ── Messages ─────────────────────────────────────────────────────

    function _renderMessages() {
        const el = _container.querySelector('#cs-messages');
        if (!el) return;
        const msgs = _currentSession?.messages || [];

        if (msgs.length === 0) {
            // nosemgrep
            el.innerHTML = html`
                <div class="flex items-center justify-center h-full">
                    <div class="text-center text-brand-text-muted">
                        <svg class="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                        </svg>
                        <p class="text-sm font-medium">${t('chat_studio.start_conversation')}</p>
                        <p class="text-[10px] mt-1">${t('chat_studio.start_hint')}</p>
                    </div>
                </div>`;
            return;
        }

        // nosemgrep
        el.innerHTML = msgs.map((msg, i) => _renderMessage(msg, i)).join('');
        _scrollToBottom();
    }

    function _renderMessage(msg, index) {
        // Model switch divider
        if (msg.role === 'system_divider') {
            return html`
                <div class="flex items-center gap-3 py-1" data-msg-idx="${index}">
                    <div class="flex-1 border-t border-brand-border/50"></div>
                    <span class="text-[10px] text-brand-text-muted/50 flex-shrink-0 px-2">${msg.content}</span>
                    <div class="flex-1 border-t border-brand-border/50"></div>
                </div>`;
        }

        const isUser = msg.role === 'user';
        const isCompacted = msg.compacted;
        const avatar = isUser ? 'U' : (isCompacted ? 'S' : 'AI');
        const avatarClass = isUser ? 'bg-brand-accent/20 text-brand-accent'
            : isCompacted ? 'bg-amber-500/20 text-amber-400'
            : 'bg-emerald-500/20 text-emerald-400';

        let contentHtml;
        if (isUser) {
            contentHtml = html`<div class="text-sm whitespace-pre-wrap">${typeof msg.content === 'string' ? msg.content : ''}</div>`;
            // Show attached images
            if (msg.images && msg.images.length > 0) {
                contentHtml = html`${contentHtml}<div class="flex gap-2 mt-2 flex-wrap">${msg.images.map(img =>
                    html`<img src="data:image/png;base64,${img}" class="w-20 h-20 object-cover rounded-lg border border-brand-border">`
                )}</div>`;
            }
        } else {
            contentHtml = html`<div class="cs-md-content text-sm">${raw(_renderMarkdown(msg.content || ''))}</div>`;
            // Show content safety block if saved
            if (msg.content_blocked) {
                contentHtml = html`${contentHtml}
                    <div class="cs-content-blocked mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                        <div class="flex items-center gap-2 mb-2">
                            <svg class="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                            </svg>
                            <span class="text-sm font-medium text-amber-400">${t('chat_studio.content_safety')}</span>
                        </div>
                        <div class="cs-md-content text-xs text-amber-200/80">${raw(_renderMarkdown(msg.content_blocked))}</div>
                    </div>`;
            }
        }

        let meta = '';
        if (!isUser && (msg.input_tokens || msg.output_tokens)) {
            const latency = msg.latency_ms ? `${(msg.latency_ms / 1000).toFixed(1)}s` : '';
            const cost = msg.cost_usd ? `~$${msg.cost_usd.toFixed(4)}` : '';
            const modelLabel = msg.model_id ? msg.model_id.split('.').pop().split(':')[0] : '';
            meta = html`<div class="flex items-center gap-3 mt-2 text-[10px] text-brand-text-muted/60">
                ${latency ? html`<span>${latency}</span>` : ''}
                <span>${(msg.input_tokens || 0).toLocaleString()} in / ${(msg.output_tokens || 0).toLocaleString()} out</span>
                ${cost ? html`<span class="text-brand-accent/60" title="${t('misc.cost_tooltip')}">${cost}</span>` : ''}
                ${modelLabel ? html`<span class="font-mono">${modelLabel}</span>` : ''}
            </div>`;
        }

        // Action buttons
        const actions = isUser
            ? html`<div class="hidden group-hover:flex items-center gap-1 mt-1">
                <button data-action="edit" data-idx="${index}" class="text-[9px] text-brand-text-muted hover:text-brand-text px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10">${t('chat_studio.edit')}</button>
                <button data-action="fork" data-idx="${index}" class="text-[9px] text-brand-text-muted hover:text-brand-text px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10">${t('chat_studio.fork')}</button>
               </div>`
            : html`<div class="hidden group-hover:flex items-center gap-1 mt-1">
                <button data-action="regenerate" data-idx="${index}" class="text-[9px] text-brand-text-muted hover:text-brand-text px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10">${t('chat_studio.regenerate')}</button>
                <button data-action="fork" data-idx="${index}" class="text-[9px] text-brand-text-muted hover:text-brand-text px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10">${t('chat_studio.fork')}</button>
               </div>`;

        return html`
            <div class="group flex gap-3 ${isUser ? '' : 'cs-assistant-msg'}" data-msg-idx="${index}">
                <div class="w-7 h-7 rounded-lg ${avatarClass} flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">${avatar}</div>
                <div class="flex-1 min-w-0">
                    ${contentHtml}
                    ${meta}
                    ${actions}
                </div>
            </div>`;
    }

    function _appendStreamingMessage() {
        const el = _container.querySelector('#cs-messages');
        if (!el) return null;
        const msgDiv = document.createElement('div');
        msgDiv.id = 'cs-streaming-msg';
        msgDiv.className = 'flex gap-3 cs-assistant-msg';
        msgDiv.innerHTML = `
            <div class="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">AI</div>
            <div class="flex-1 min-w-0">
                <div class="cs-md-content text-sm"><span class="cs-cursor animate-pulse">|</span></div>
                <div class="flex items-center gap-2 mt-2 text-[10px] text-brand-text-muted/60">
                    <span class="cs-stream-timer">0.0s</span>
                    <span class="cs-stream-tokens"></span>
                </div>
            </div>`;
        el.appendChild(msgDiv);
        _scrollToBottom();
        return msgDiv;
    }

    // ── Send / Stream ────────────────────────────────────────────────

    async function _sendMessage(overrideText = null, truncateAt = null) {
        if (_streaming || !_currentSession) return;
        const input = _container.querySelector('#cs-input');
        const text = overrideText || input.value.trim();
        if (!text && _pendingImages.length === 0) return;

        const model = _getSelectedModel();
        if (!model.model_id) { window.showToast?.(t('chat_studio.select_model'), 'error'); return; }

        // If truncating (edit/fork), remove messages after truncateAt
        if (truncateAt !== null) {
            _currentSession.messages = _currentSession.messages.slice(0, truncateAt);
        }

        // Detect model switch — insert a divider message if model changed mid-conversation
        const prevAssistant = [...(_currentSession.messages || [])].reverse().find(m => m.role === 'assistant');
        const prevModelId = prevAssistant?.model_id || _currentSession.model_id || '';
        if (prevModelId && model.model_id !== prevModelId && _currentSession.messages.length > 0) {
            const prevLabel = prevModelId.split('.').pop().split(':')[0];
            const newLabel = model.model_id.split('.').pop().split(':')[0];
            _currentSession.messages.push({
                role: 'system_divider',
                content: t('chat_studio.model_switched').replace('{{prev}}', prevLabel).replace('{{new}}', newLabel),
                timestamp: new Date().toISOString(),
                prev_model: prevModelId,
                new_model: model.model_id,
            });
        }

        // Build user message with optional images
        const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() };
        if (_pendingImages.length > 0) {
            userMsg.images = _pendingImages.map(img => img.base64);
        }
        _currentSession.messages.push(userMsg);
        _currentSession.model_id = model.model_id;
        if (!overrideText) input.value = '';
        _pendingImages = [];
        _renderAttachments();

        // Quick title from first message (immediate, before LLM responds)
        if (_currentSession.messages.filter(m => m.role === 'user').length === 1 && (_currentSession.title === 'New Chat' || _currentSession.title === t('chat_studio.new_chat').replace('+ ', ''))) {
            _currentSession.title = text.slice(0, 50) + (text.length > 50 ? '...' : '');
        }

        _renderMessages();
        _setStreaming(true);

        const streamMsg = _appendStreamingMessage();
        const contentEl = streamMsg?.querySelector('.cs-md-content');
        const timerEl = streamMsg?.querySelector('.cs-stream-timer');
        const tokensEl = streamMsg?.querySelector('.cs-stream-tokens');

        let fullText = '';
        let metadata = null;
        let contentBlocked = null;  // Set if content safety triggers
        const startTime = Date.now();
        const timerInterval = setInterval(() => { if (timerEl) timerEl.textContent = `${((Date.now() - startTime) / 1000).toFixed(1)}s`; }, 100);

        // Build messages for API — skip dividers, convert images to Converse format
        const apiMessages = _currentSession.messages.filter(m => m.role !== 'system_divider').map(m => {
            if (m.role === 'user' && m.images && m.images.length > 0) {
                const content = [];
                for (const imgB64 of m.images) {
                    content.push({ image: { format: 'png', source: { bytes: imgB64 } } });
                }
                if (m.content) content.push({ text: m.content });
                return { role: 'user', content };
            }
            return { role: m.role, content: m.content };
        });

        _abortController = new AbortController();

        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model_id: model.model_id,
                    region: _container.querySelector('#cs-region-picker')?.value || model.region,
                    messages: apiMessages,
                    system_prompt: _currentSession.system_prompt || '',
                    temperature: _currentSession.temperature || 0.7,
                    max_tokens: _currentSession.max_tokens || 4096,
                }),
                signal: _abortController.signal,
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    let event;
                    try { event = JSON.parse(line.slice(6)); } catch { continue; }
                    if (event.type === 'delta' && event.text) {
                        fullText += event.text;
                        // nosemgrep
                        if (contentEl) contentEl.innerHTML = html`${raw(_renderMarkdown(fullText))}<span class="cs-cursor animate-pulse">|</span>`;
                        _scrollToBottom();
                    } else if (event.type === 'metadata') {
                        metadata = event;
                        if (tokensEl) tokensEl.textContent = `${event.input_tokens.toLocaleString()} in / ${event.output_tokens.toLocaleString()} out · $${event.cost_usd.toFixed(4)}`;
                    } else if (event.type === 'content_blocked') {
                        // Content safety block — show styled warning with guidance
                        contentBlocked = event.message;
                        if (contentEl) {
                            // nosemgrep
                            contentEl.innerHTML = html`${raw(fullText ? _renderMarkdown(fullText) : '')}<div class="cs-content-blocked mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                    <div class="flex items-center gap-2 mb-2">
                                        <svg class="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                        </svg>
                                        <span class="text-sm font-medium text-amber-400">${t('chat_studio.content_safety')}</span>
                                    </div>
                                    <div class="cs-md-content text-xs text-amber-200/80">${raw(_renderMarkdown(event.message))}</div>
                                </div>`;
                        }
                        _scrollToBottom();
                    } else if (event.type === 'error') {
                        fullText += `\n\n**Error:** ${event.detail}`;
                        // nosemgrep
                        if (contentEl) contentEl.innerHTML = raw(_renderMarkdown(fullText));
                    }
                }
            }
        } catch (err) {
            if (err.name !== 'AbortError') fullText += `\n\n**${t('common.error')}:** ${err.message}`;
        }

        clearInterval(timerInterval);

        const assistantMsg = {
            role: 'assistant',
            content: contentBlocked ? (fullText || '') : fullText,
            content_blocked: contentBlocked || null,
            timestamp: new Date().toISOString(),
            input_tokens: metadata?.input_tokens || 0, output_tokens: metadata?.output_tokens || 0,
            latency_ms: metadata?.latency_ms || (Date.now() - startTime), cost_usd: metadata?.cost_usd || 0,
            model_id: model.model_id,
        };
        _currentSession.messages.push(assistantMsg);
        _currentSession.total_input_tokens = (_currentSession.total_input_tokens || 0) + (metadata?.input_tokens || 0);
        _currentSession.total_output_tokens = (_currentSession.total_output_tokens || 0) + (metadata?.output_tokens || 0);
        _currentSession.total_cost_usd = (_currentSession.total_cost_usd || 0) + (metadata?.cost_usd || 0);

        _renderMessages();
        _updateTotals();
        _setStreaming(false);
        await _saveCurrentSession();
        await _loadSessions();

        // After the first exchange, ask the LLM for a smart title (fire-and-forget)
        const userMsgs = _currentSession.messages.filter(m => m.role === 'user');
        const assistantMsgs = _currentSession.messages.filter(m => m.role === 'assistant');
        if (userMsgs.length === 1 && assistantMsgs.length === 1 && !_currentSession._titleGenerated) {
            _currentSession._titleGenerated = true;
            _generateSmartTitle(userMsgs[0].content, assistantMsgs[0].content?.slice(0, 300) || '');
        }
    }

    async function _generateSmartTitle(userMessage, assistantSnippet) {
        try {
            const resp = await fetch('/api/chat/generate-title', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_message: userMessage, assistant_snippet: assistantSnippet }),
            });
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.title && _currentSession) {
                _currentSession.title = data.title;
                await _saveCurrentSession();
                await _loadSessions();
            }
        } catch { /* silent — title is a nice-to-have */ }
    }

    function _stopStream() {
        if (_abortController) { _abortController.abort(); _abortController = null; }
        _setStreaming(false);
    }

    function _setStreaming(streaming) {
        _streaming = streaming;
        const send = _container.querySelector('#cs-send');
        const stop = _container.querySelector('#cs-stop');
        const input = _container.querySelector('#cs-input');
        if (send) send.classList.toggle('hidden', streaming);
        if (stop) stop.classList.toggle('hidden', !streaming);
        if (input) input.disabled = streaming;
    }

    // ── Regenerate / Edit / Fork (Phase 3) ───────────────────────────

    async function _regenerateAt(index) {
        if (_streaming || !_currentSession) return;
        const msgs = _currentSession.messages;
        if (index < 1 || msgs[index]?.role !== 'assistant') return;

        // Remove the assistant message at index and everything after
        // Re-send with the user message before it
        const userMsgIdx = index - 1;
        _currentSession.messages = msgs.slice(0, userMsgIdx + 1);
        _renderMessages();

        // Trigger send with the existing user message (no new text)
        const userText = msgs[userMsgIdx].content;
        _currentSession.messages.pop(); // Remove the user message — _sendMessage will re-add it
        await _sendMessage(userText);
    }

    function _editMessage(index) {
        if (_streaming || !_currentSession) return;
        const msg = _currentSession.messages[index];
        if (!msg || msg.role !== 'user') return;

        // Put the message text into the input and truncate conversation
        const input = _container.querySelector('#cs-input');
        if (input) input.value = typeof msg.content === 'string' ? msg.content : '';

        // Restore images if any
        if (msg.images && msg.images.length > 0) {
            _pendingImages = msg.images.map((b64, i) => ({
                name: `image_${i}.png`,
                base64: b64,
                dataUrl: `data:image/png;base64,${b64}`,
            }));
            _renderAttachments();
        }

        // Remove this message and everything after
        _currentSession.messages = _currentSession.messages.slice(0, index);
        _renderMessages();
        input?.focus();
    }

    async function _forkAt(index) {
        if (!_currentSession) return;
        // Duplicate session up to this point
        const resp = await fetch(`/api/chat/sessions/${_currentSession.session_id}/duplicate`, { method: 'POST' });
        if (!resp.ok) return;
        const newSession = await resp.json();

        // Truncate the new session to the fork point
        newSession.messages = _currentSession.messages.slice(0, index + 1);
        newSession.title = `${_currentSession.title} (fork)`;
        await fetch(`/api/chat/sessions/${newSession.session_id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSession),
        });

        await _loadSessions();
        await _loadSession(newSession.session_id);
        window.showToast?.(t('chat_studio.fork_success'), 'success');
    }

    // ── Export (Phase 2) ─────────────────────────────────────────────

    async function _exportMarkdown() {
        if (!_currentSession) return;
        try {
            const resp = await fetch(`/api/chat/sessions/${_currentSession.session_id}/export`);
            if (!resp.ok) throw new Error(t('chat_studio.export_failed'));
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = resp.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1] || 'chat.md';
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) { window.showToast?.(t('chat_studio.export_failed') + ': ' + err.message, 'error'); }
    }

    // ── Compact (Phase 3) ────────────────────────────────────────────

    async function _compactContext() {
        if (!_currentSession || _streaming) return;
        const msgCount = _currentSession.messages?.length || 0;
        if (msgCount <= 6) { window.showToast?.(t('chat_studio.compact_not_enough'), 'info'); return; }

        if (!await window.showConfirm(t('chat_studio.compact_confirm').replace('{{count}}', msgCount - 6), {
            title: t('chat_studio.compact_title'),
            detail: t('chat_studio.compact_detail'),
            confirmLabel: t('chat_studio.compact_btn'),
        })) return;

        try {
            window.showLoading?.(t('chat_studio.compacting'));
            const resp = await fetch('/api/chat/compact', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: _currentSession.session_id, keep_recent: 6 }),
            });
            window.hideLoading?.();

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || t('model_settings.templates_enhance_failed'));
            }

            const result = await resp.json();
            window.showToast?.(t('chat_studio.compacted').replace('{{count}}', result.messages_removed), 'success');
            await _loadSession(_currentSession.session_id);
        } catch (err) {
            window.hideLoading?.();
            window.showToast?.(t('chat_studio.compact_title') + ': ' + err.message, 'error');
        }
    }

    // ── Search (Phase 2) ─────────────────────────────────────────────

    function _highlightSearch() {
        const query = _searchQuery.toLowerCase();
        const resultEl = _container.querySelector('#cs-search-results');
        if (!query) {
            if (resultEl) resultEl.textContent = '';
            // Remove highlights
            _container.querySelectorAll('.cs-search-highlight').forEach(el => {
                el.replaceWith(document.createTextNode(el.textContent));
            });
            return;
        }

        let count = 0;
        _container.querySelectorAll('[data-msg-idx]').forEach(msgEl => {
            const idx = parseInt(msgEl.dataset.msgIdx);
            const msg = _currentSession?.messages?.[idx];
            if (!msg) return;
            const content = (msg.content || '').toLowerCase();
            if (content.includes(query)) {
                count++;
                msgEl.classList.add('ring-1', 'ring-brand-accent/30', 'rounded-lg');
            } else {
                msgEl.classList.remove('ring-1', 'ring-brand-accent/30', 'rounded-lg');
            }
        });

        if (resultEl) resultEl.textContent = `${count} match${count !== 1 ? 'es' : ''}`;
    }

    // ── Markdown rendering ───────────────────────────────────────────

    function _renderMarkdown(text) {
        if (!text) return '';
        if (typeof marked !== 'undefined') {
            try {
                const html = marked.parse(text, { breaks: true, gfm: true });
                return html.replace(/<pre><code(.*?)>([\s\S]*?)<\/code><\/pre>/g, (match, attrs, code) => {
                    const langMatch = attrs.match(/class="language-(\w+)"/);
                    const lang = langMatch ? langMatch[1] : '';
                    let highlighted = code;
                    if (typeof hljs !== 'undefined') {
                        try {
                            const decoded = code.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&').replace(/&quot;/g,'"');
                            highlighted = lang
                                ? hljs.highlight(decoded, { language: lang }).value
                                : hljs.highlightAuto(decoded).value;
                        } catch { /* use unhighlighted */ }
                    }
                    const langBadge = lang ? `<span class="absolute top-2 left-3 text-[9px] text-brand-text-muted/40 font-mono">${_esc(lang)}</span>` : '';
                    return `<pre class="cs-code-block relative group">${langBadge}<div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"><button class="cs-copy-btn text-[9px] px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 text-brand-text-muted" onclick="navigator.clipboard.writeText(this.closest('pre').querySelector('code').textContent);this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',1500)">Copy</button></div><code class="language-${lang}">${highlighted}</code></pre>`;
                });
            } catch { /* fallback */ }
        }
        return `<pre class="whitespace-pre-wrap">${_esc(text)}</pre>`;
    }

    // ── Helpers ───────────────────────────────────────────────────────

    function _scrollToBottom() {
        const el = _container.querySelector('#cs-messages');
        if (el) requestAnimationFrame(() => el.scrollTop = el.scrollHeight);
    }

    // ── Telemetry (PulseBoard) ─────────────────────────────────────

    function _flushSessionTelemetry() {
        if (!_currentSession || !_sessionStartTime) return;
        const msgs = _currentSession.messages || [];
        if (msgs.length === 0) return; // Don't report empty sessions

        const duration = Math.round((Date.now() - _sessionStartTime) / 1000);
        const hasVision = msgs.some(m => m.images && m.images.length > 0);
        const compacted = msgs.some(m => m.compacted);

        // Fire-and-forget — don't block navigation
        fetch('/api/chat/telemetry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: _currentSession.session_id,
                model_id: _currentSession.model_id || '',
                messages: msgs.length,
                input_tokens: _currentSession.total_input_tokens || 0,
                output_tokens: _currentSession.total_output_tokens || 0,
                cost_usd: _currentSession.total_cost_usd || 0,
                duration_seconds: duration,
                has_vision: hasVision,
                compacted: compacted,
            }),
        }).catch(() => {}); // Silently ignore errors
    }

    // Flush on page unload (beacon for reliability)
    window.addEventListener('beforeunload', () => {
        if (!_currentSession || !_sessionStartTime) return;
        const msgs = _currentSession.messages || [];
        if (msgs.length === 0) return;
        const duration = Math.round((Date.now() - _sessionStartTime) / 1000);
        navigator.sendBeacon('/api/chat/telemetry', JSON.stringify({
            session_id: _currentSession.session_id,
            model_id: _currentSession.model_id || '',
            messages: msgs.length,
            input_tokens: _currentSession.total_input_tokens || 0,
            output_tokens: _currentSession.total_output_tokens || 0,
            cost_usd: _currentSession.total_cost_usd || 0,
            duration_seconds: duration,
            has_vision: msgs.some(m => m.images?.length > 0),
            compacted: msgs.some(m => m.compacted),
        }));
    });

    function _esc(str) {
        if (!str) return '';
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }
})();
