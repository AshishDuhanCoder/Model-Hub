/* ============================================================
   ModelHub — main.js
   ============================================================ */

// ── Navbar scroll effect ─────────────────────────────────────
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  }, { passive: true });
}

// ── Stagger animation index ──────────────────────────────────
document.querySelectorAll('.model-card').forEach((card, i) => {
  card.style.setProperty('--i', i);
});

// ── Debounce helper ──────────────────────────────────────────
function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/* ============================================================
   SEARCH / ASK MODE TOGGLE
   ============================================================ */
const modeBtns   = document.querySelectorAll('.search-mode-btn');
const askSendBtn = document.getElementById('ask-send-btn');
const kbdHint    = document.getElementById('search-kbd-hint');
const barIcon    = document.getElementById('search-bar-icon');
const chatWindow = document.getElementById('chat-window');
const chatMsgs   = document.getElementById('chat-messages');
const chatWelcome= document.getElementById('chat-welcome');
const chatNewBtn = document.getElementById('chat-new-btn');

let currentMode   = 'search';   // 'search' | 'ask'
let contextTopic  = '';          // last resolved topic for follow-up awareness
let typingEl      = null;        // current typing indicator node
let tokenHistory  = [];

function renderUsageCharts(usage) {
  if (!usage) return;
  tokenHistory.push({
    prompt: Number(usage.prompt_tokens || 0),
    answer: Number(usage.completion_tokens || 0),
    total: Number(usage.total_tokens || 0),
    estimated: Boolean(usage.estimated),
  });
  tokenHistory = tokenHistory.slice(-8);
  const total = document.getElementById('usage-total');
  const svg = document.getElementById('usage-sparkline');
  const bars = document.getElementById('usage-bars');
  const detail = document.getElementById('usage-detail');
  if (!total || !svg || !bars) return;
  total.textContent = `${tokenHistory.reduce((sum, item) => sum + item.total, 0)} tokens`;
  const max = Math.max(1, ...tokenHistory.map(item => item.total));
  const points = tokenHistory.map((item, index) => `${index * 24 + 6},${38 - (item.total / max) * 30}`).join(' ');
  svg.innerHTML = `<polyline points="${points}" fill="none" stroke="var(--accent-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
  bars.innerHTML = tokenHistory.map((item, index) => `<span class="usage-bar" title="Call ${index + 1}: ${item.prompt} prompt + ${item.answer} answer tokens" style="height:${Math.max(5, (item.total / max) * 30)}px"><i style="height:${Math.max(2, (item.prompt / Math.max(1, item.total)) * 100)}%"></i></span>`).join('');
  detail.textContent = `Latest call: ${tokenHistory.at(-1).prompt} prompt + ${tokenHistory.at(-1).answer} answer = ${tokenHistory.at(-1).total} tokens${tokenHistory.at(-1).estimated ? ' (estimated for DuckDuckGo)' : ''}`;
}

/* ============================================================
   API KEY MANAGEMENT  (stored in localStorage, sent as header)
   ============================================================ */
const _KEY_STORAGE = 'modelhub_groq_key';

function getUserKey()        { return localStorage.getItem(_KEY_STORAGE) || ''; }
function setUserKey(k)       { localStorage.setItem(_KEY_STORAGE, k.trim()); _syncKeyUI(); }
function clearUserKey()      { localStorage.removeItem(_KEY_STORAGE); _syncKeyUI(); }

function _syncKeyUI() {
  const key     = getUserKey();
  const keyBtn  = document.getElementById('chat-key-btn');
  const keyDot  = document.getElementById('chat-key-dot');
  const keyInput= document.getElementById('chat-key-input');
  if (key) {
    if (keyBtn)  { keyBtn.textContent = '🔑 Key Set'; keyBtn.classList.add('key-active'); }
    if (keyDot)  keyDot.classList.add('key-active');
    if (keyInput) keyInput.value = key;
  } else {
    if (keyBtn)  { keyBtn.textContent = '🔑 Add Key'; keyBtn.classList.remove('key-active'); }
    if (keyDot)  keyDot.classList.remove('key-active');
    if (keyInput) keyInput.value = '';
  }
}

// Toggle the key bar on header button click
document.addEventListener('click', e => {
  if (e.target.id === 'chat-key-btn') {
    const bar = document.getElementById('chat-key-bar');
    if (bar) {
      bar.classList.toggle('hidden');
      if (!bar.classList.contains('hidden')) {
        const inp = document.getElementById('chat-key-input');
        if (inp) { inp.value = getUserKey(); inp.focus(); }
      }
    }
  }
  if (e.target.id === 'chat-key-save-btn') {
    const inp = document.getElementById('chat-key-input');
    const val = inp ? inp.value.trim() : '';
    if (val) {
      setUserKey(val);
      document.getElementById('chat-key-bar').classList.add('hidden');
    }
  }
  if (e.target.id === 'chat-key-clear-btn') {
    clearUserKey();
    document.getElementById('chat-key-bar').classList.add('hidden');
  }
});

// Save on Enter inside key input
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.target.id === 'chat-key-input') {
    document.getElementById('chat-key-save-btn')?.click();
  }
});

// Sync UI on page load
document.addEventListener('DOMContentLoaded', _syncKeyUI);
_syncKeyUI();

/* ── Mode switch ─────────────────────────────────────────── */
function setMode(mode) {
  currentMode = mode;
  const heroSearch = document.getElementById('hero-search');
  modeBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.mode === mode));

  if (mode === 'ask') {
    heroSearch.placeholder = 'Ask anything — AI, science, tech, history…';
    if (barIcon)   barIcon.textContent = '✨';
    if (askSendBtn) askSendBtn.classList.remove('hidden');
    if (kbdHint)   kbdHint.classList.add('hidden');
    hideDropdown();
    if (chatWindow) chatWindow.classList.remove('hidden');
  } else {
    heroSearch.placeholder = 'Search models, providers, capabilities…';
    if (barIcon)   barIcon.textContent = '🔍';
    if (askSendBtn) askSendBtn.classList.add('hidden');
    if (kbdHint)   kbdHint.classList.remove('hidden');
    if (chatWindow) chatWindow.classList.add('hidden');
  }
}

modeBtns.forEach(btn => btn.addEventListener('click', () => setMode(btn.dataset.mode)));

/* ── Escape helper ───────────────────────────────────────── */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ── Chat helpers ────────────────────────────────────────── */
function hideChatWelcome() {
  if (chatWelcome) chatWelcome.style.display = 'none';
}

function scrollChatBottom() {
  if (chatMsgs) chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

function appendUserBubble(text) {
  hideChatWelcome();
  const wrap = document.createElement('div');
  wrap.className = 'chat-bubble-wrap user';
  wrap.innerHTML = `<div class="chat-bubble-user">${escapeHtml(text)}</div>`;
  chatMsgs.appendChild(wrap);
  scrollChatBottom();
}

function showTyping() {
  typingEl = document.createElement('div');
  typingEl.className = 'chat-bubble-wrap ai';
  typingEl.innerHTML = `
    <div class="chat-typing">
      <span class="chat-typing-dot"></span>
      <span class="chat-typing-dot"></span>
      <span class="chat-typing-dot"></span>
    </div>`;
  chatMsgs.appendChild(typingEl);
  scrollChatBottom();
}

function removeTyping() {
  if (typingEl) { typingEl.remove(); typingEl = null; }
}

function appendAiBubble(data) {
  removeTyping();
  const items = data.bullets || [];
  const bulletsHtml = items.length
    ? `<div class="chat-ai-bullets-label">Key Points</div>
       <ul class="chat-ai-bullets">
         ${items.map((b, i) => `
           <li class="chat-ai-bullet" style="--bi:${i}">
             <span class="chat-ai-bullet-num">${i + 1}</span>
             <span class="chat-ai-bullet-text">${escapeHtml(b)}</span>
           </li>`).join('')}
       </ul>`
    : '';

  let footerHtml = '';
  if (data.source || data.url) {
    const srcLink = data.url
      ? `<a class="chat-ai-source-link" href="${data.url}" target="_blank" rel="noopener">${escapeHtml(data.source || '')}</a>`
      : `<span class="chat-ai-source-link">${escapeHtml(data.source || '')}</span>`;
    footerHtml = `<div class="chat-ai-footer">
      <span class="chat-ai-source-label">Source:</span> ${srcLink}
      ${data.url ? `<a class="chat-ai-full-link" href="${data.url}" target="_blank" rel="noopener">Full article →</a>` : ''}
    </div>`;
  }

  const wrap = document.createElement('div');
  wrap.className = 'chat-bubble-wrap ai';
  wrap.innerHTML = `
    <div class="chat-bubble-ai">
      ${data.title ? `<div class="chat-ai-title">
        <span class="chat-ai-title-icon">📖</span>
        <span class="chat-ai-title-text">${escapeHtml(data.title)}</span>
      </div>` : ''}
      ${data.description ? `<p class="chat-ai-desc">${escapeHtml(data.description)}</p>` : ''}
      ${bulletsHtml}
      ${footerHtml}
    </div>`;
  chatMsgs.appendChild(wrap);
  scrollChatBottom();
}

function appendErrorBubble(msg) {
  removeTyping();
  const wrap = document.createElement('div');
  wrap.className = 'chat-bubble-wrap ai';
  wrap.innerHTML = `<div class="chat-error-bubble">⚠ ${escapeHtml(msg)}</div>`;
  chatMsgs.appendChild(wrap);
  scrollChatBottom();
}

/* ── Clear chat ──────────────────────────────────────────── */
function clearChat() {
  if (!chatMsgs) return;
  // Remove all messages except the welcome state
  [...chatMsgs.children].forEach(el => {
    if (el.id !== 'chat-welcome') el.remove();
  });
  if (chatWelcome) chatWelcome.style.display = '';
  contextTopic = '';
  tokenHistory = [];
  const usageTotal = document.getElementById('usage-total');
  const usageBars = document.getElementById('usage-bars');
  const usageSparkline = document.getElementById('usage-sparkline');
  const usageDetail = document.getElementById('usage-detail');
  if (usageTotal) usageTotal.textContent = '0 tokens';
  if (usageBars) usageBars.innerHTML = '';
  if (usageSparkline) usageSparkline.innerHTML = '';
  if (usageDetail) usageDetail.textContent = 'Ask a question to see prompt and answer tokens.';
}

if (chatNewBtn) chatNewBtn.addEventListener('click', clearChat);

/* ── Suggestion chips ────────────────────────────────────── */
document.addEventListener('click', e => {
  if (e.target.classList.contains('chat-chip')) {
    const q = e.target.dataset.q;
    if (q) {
      const heroSearch = document.getElementById('hero-search');
      if (heroSearch) heroSearch.value = q;
      submitAsk(q);
    }
  }
});

/* ── Main ask fetch ──────────────────────────────────────── */
async function submitAsk(q) {
  q = (q || '').trim();
  if (q.length < 2) return;

  const heroSearch = document.getElementById('hero-search');
  if (heroSearch) heroSearch.value = '';

  appendUserBubble(q);
  showTyping();

  try {
    const params = new URLSearchParams({ q });
    if (contextTopic) params.set('context_topic', contextTopic);
    const headers = {};
    const userKey = getUserKey();
    if (userKey) headers['X-User-Key'] = userKey;
    const res  = await fetch(`/api/ask?${params}`, { headers });
    const data = await res.json();
    if (!res.ok || data.error) {
      if (res.status === 401 && getUserKey()) {
        clearUserKey();
        const keyBar = document.getElementById('chat-key-bar');
        const keyInput = document.getElementById('chat-key-input');
        if (keyBar) keyBar.classList.remove('hidden');
        if (keyInput) {
          keyInput.value = '';
          keyInput.focus();
        }
        appendErrorBubble('Your saved API key is invalid or expired. It was removed. Enter a new key to continue, or leave it empty to use DuckDuckGo.');
      } else {
        appendErrorBubble(data.error || 'No answer found. Try rephrasing your question.');
      }
    } else {
      if (data.topic) contextTopic = data.topic;
      renderUsageCharts(data.usage);
      appendAiBubble(data);
    }
  } catch {
    appendErrorBubble('Network error. Please try again.');
  }
}

if (askSendBtn) {
  askSendBtn.addEventListener('click', () => {
    const heroSearch = document.getElementById('hero-search');
    if (heroSearch) submitAsk(heroSearch.value.trim());
  });
}

// hideAskPanel shim — used by setMode search branch (now just hides chat window)
function hideAskPanel() {
  if (chatWindow) chatWindow.classList.add('hidden');
}

/* ============================================================
   HERO SEARCH with live dropdown
   ============================================================ */
const heroSearch    = document.getElementById('hero-search');
const searchDropdown = document.getElementById('search-dropdown');

function hideDropdown() {
  if (searchDropdown) searchDropdown.classList.add('hidden');
}

function renderDropdown(results) {
  if (!searchDropdown) return;
  if (!results.length) { hideDropdown(); return; }

  searchDropdown.innerHTML = results.map(r => `
    <a class="dropdown-item" href="${r.url}" role="option">
      <span class="dropdown-name">${r.name}</span>
      <span class="dropdown-cat">${r.category}${r.badge ? ' · ' + r.badge : ''}</span>
    </a>
  `).join('');

  searchDropdown.classList.remove('hidden');
}

async function fetchSearchResults(q) {
  if (q.length < 2) { hideDropdown(); return; }
  try {
    const res  = await fetch(`/api/search?q=${encodeURIComponent(q)}&cat=all`);
    const data = await res.json();
    renderDropdown(data.results || []);
  } catch {
    hideDropdown();
  }
}

if (heroSearch) {
  heroSearch.addEventListener('input', debounce(e => {
    if (currentMode === 'search') fetchSearchResults(e.target.value.trim());
  }, 200));

  heroSearch.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      heroSearch.value = '';
      hideDropdown();
      hideAskPanel();
    }
    if (e.key === 'Enter' && currentMode === 'ask') {
      e.preventDefault();
      submitAsk(heroSearch.value.trim());
    }
  });
}

// Close dropdown when clicking outside
document.addEventListener('click', e => {
  if (!e.target.closest('.search-wrapper')) hideDropdown();
});

/* ============================================================
   INTEGRATE MODAL
   ============================================================ */
const modal      = document.getElementById('integrate-modal');
const modalTitle = document.getElementById('modal-title');
const modalCode  = document.getElementById('modal-code');
const modalDocs  = document.getElementById('modal-docs-link');
const copyBtn    = document.getElementById('copy-btn');
const closeBtn   = document.getElementById('modal-close');

let currentSnippets = {};

async function openIntegrateModal(modelId) {
  try {
    const res  = await fetch(`/api/integrate/${modelId}`);
    const data = await res.json();

    if (data.error) { alert('Model not found.'); return; }

    currentSnippets = data.snippet || {};
    if (modalTitle) modalTitle.textContent = `Integrate ${data.name}`;
    if (modalDocs)  modalDocs.href = data.docs || '#';

    showSnippet('python');
    openModal();
  } catch {
    alert('Failed to load snippet. Please try again.');
  }
}

function showSnippet(lang) {
  if (modalCode) {
    modalCode.textContent = currentSnippets[lang] || '# No snippet available for this language.';
  }
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
  if (copyBtn) copyBtn.textContent = 'Copy';
}

function openModal() {
  if (!modal) return;
  modal.classList.add('active');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  if (!modal) return;
  modal.classList.remove('active');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => showSnippet(btn.dataset.lang));
});

// Copy button
if (copyBtn) {
  copyBtn.addEventListener('click', () => {
    const text = modalCode ? modalCode.textContent : '';
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.textContent = '✓ Copied!';
      setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
    }).catch(() => {
      // Fallback for older browsers
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      copyBtn.textContent = '✓ Copied!';
      setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
    });
  });
}

// Close on X button
if (closeBtn) closeBtn.addEventListener('click', closeModal);

// Close on backdrop click
if (modal) {
  modal.addEventListener('click', e => {
    if (e.target === modal) closeModal();
  });
}

// Close on Escape key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && modal && modal.classList.contains('active')) closeModal();
});

// Expose globally for onclick handlers in templates
window.openIntegrateModal = openIntegrateModal;

/* ============================================================
   PER-PAGE CLIENT-SIDE FILTER  (category pages)
   ============================================================ */
const pageSearch   = document.getElementById('page-search');
const filterChips  = document.querySelectorAll('.filter-chip');
const allCards     = document.querySelectorAll('.model-card');
const emptyState   = document.getElementById('empty-state');

let activeStatus = 'all';
let activeQuery  = '';

function applyFilters() {
  let visible = 0;

  allCards.forEach(card => {
    const name   = card.dataset.name  || '';
    const tags   = card.dataset.tags  || '';
    const status = card.dataset.status || '';

    const nameMatch   = !activeQuery || name.includes(activeQuery) || tags.includes(activeQuery);
    const statusMatch = activeStatus === 'all' || status === activeStatus;
    const show        = nameMatch && statusMatch;

    card.style.display = show ? '' : 'none';
    if (show) visible++;
  });

  if (emptyState) emptyState.style.display = visible === 0 ? 'block' : 'none';
}

if (pageSearch) {
  pageSearch.addEventListener('input', debounce(e => {
    activeQuery = e.target.value.toLowerCase().trim();
    applyFilters();
  }, 150));
}

filterChips.forEach(chip => {
  chip.addEventListener('click', () => {
    filterChips.forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    activeStatus = chip.dataset.filter;
    applyFilters();
  });
});

/* ============================================================
   PRICING — Annual / Monthly toggle
   ============================================================ */
const annualToggle = document.getElementById('annual-toggle');
if (annualToggle) {
  annualToggle.addEventListener('change', () => {
    const isAnnual = annualToggle.checked;
    document.querySelectorAll('.plan-amount[data-monthly]').forEach(el => {
      const monthly = parseFloat(el.dataset.monthly);
      if (!isNaN(monthly) && monthly > 0) {
        el.textContent = isAnnual ? Math.round(monthly * 0.8) : monthly;
      }
    });
  });
}

/* ============================================================
   KEYBOARD SHORTCUT  ⌘K / Ctrl+K  → focus hero search
   ============================================================ */
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    if (heroSearch) {
      heroSearch.focus();
      heroSearch.select();
    }
  }
});

/* ============================================================
   TWO-PANE CHAT INTERFACE
   ============================================================ */
let selectedModel = null;

function selectModel(cardElement) {
  // Remove active class from all cards
  document.querySelectorAll('.model-list-item').forEach(card => {
    card.classList.remove('active');
  });
  
  // Add active class to clicked card
  cardElement.classList.add('active');
  
  // Extract model info
  const modelId = cardElement.id;
  const modelName = cardElement.querySelector('.model-name').textContent;
  const modelDesc = cardElement.querySelector('.model-desc').textContent;
  
  selectedModel = { id: modelId, name: modelName, desc: modelDesc };
  
  // Show chat container, hide welcome
  const chatContainer = document.getElementById('chat-container');
  const modelWelcome = document.getElementById('model-welcome');
  const selectedInfo = document.getElementById('selected-model-info');
  const closeBtn = document.getElementById('close-model-btn');
  
  if (chatContainer) chatContainer.style.display = 'flex';
  if (modelWelcome) modelWelcome.style.display = 'none';
  if (selectedInfo) {
    selectedInfo.innerHTML = `
      <h2>${escapeHtml(modelName)}</h2>
      <p>${escapeHtml(modelDesc.substring(0, 100))}...</p>
    `;
  }
  if (closeBtn) closeBtn.style.display = 'flex';
  
  // Clear chat and show welcome
  const chatMsgs = document.getElementById('chat-messages');
  if (chatMsgs) {
    chatMsgs.innerHTML = `
      <div id="chat-welcome" class="chat-welcome">
        <div class="chat-welcome-icon">💬</div>
        <p class="chat-welcome-text">Start a conversation with ${escapeHtml(modelName)}</p>
        <div class="chat-suggestions">
          <button class="chat-chip" data-q="What are your capabilities?">Capabilities</button>
          <button class="chat-chip" data-q="How do I integrate?">Integration</button>
          <button class="chat-chip" data-q="What's your pricing?">Pricing</button>
        </div>
      </div>
    `;
  }
}

function clearModelSelection() {
  // Remove active class
  document.querySelectorAll('.model-list-item').forEach(card => {
    card.classList.remove('active');
  });
  
  selectedModel = null;
  
  // Hide chat, show welcome
  const chatContainer = document.getElementById('chat-container');
  const modelWelcome = document.getElementById('model-welcome');
  const selectedInfo = document.getElementById('selected-model-info');
  const closeBtn = document.getElementById('close-model-btn');
  
  if (chatContainer) chatContainer.style.display = 'none';
  if (modelWelcome) modelWelcome.style.display = 'flex';
  if (selectedInfo) {
    selectedInfo.innerHTML = `
      <h2>Select a Model</h2>
      <p>Choose a model from the list to start chatting</p>
    `;
  }
  if (closeBtn) closeBtn.style.display = 'none';
}

function submitChat() {
  if (!selectedModel) return;
  
  const chatInput = document.getElementById('chat-input');
  const message = chatInput ? chatInput.value.trim() : '';
  
  if (!message) return;
  
  // Add user message
  const chatMsgs = document.getElementById('chat-messages');
  if (chatMsgs) {
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble-wrap user';
    userBubble.innerHTML = `<div class="chat-bubble-user">${escapeHtml(message)}</div>`;
    chatMsgs.appendChild(userBubble);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
  }
  
  // Clear input
  if (chatInput) chatInput.value = '';
  
  // Show typing indicator
  if (chatMsgs) {
    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-bubble-wrap ai';
    typingBubble.id = 'typing-indicator';
    typingBubble.innerHTML = `
      <div class="chat-typing">
        <span class="chat-typing-dot"></span>
        <span class="chat-typing-dot"></span>
        <span class="chat-typing-dot"></span>
      </div>`;
    chatMsgs.appendChild(typingBubble);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
  }
  
  // Simulate API response (replace with actual API call)
  setTimeout(() => {
    const typingEl = document.getElementById('typing-indicator');
    if (typingEl) typingEl.remove();
    
    if (chatMsgs) {
      const aiBubble = document.createElement('div');
      aiBubble.className = 'chat-bubble-wrap ai';
      aiBubble.innerHTML = `
        <div class="chat-bubble-ai">
          <p class="chat-ai-desc">Thanks for asking about ${escapeHtml(selectedModel.name)}! This is a demo response. You can integrate real API responses here.</p>
        </div>`;
      chatMsgs.appendChild(aiBubble);
      chatMsgs.scrollTop = chatMsgs.scrollHeight;
    }
  }, 1500);
}

// Chat suggestions click handler
document.addEventListener('click', e => {
  if (e.target.classList.contains('chat-chip')) {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
      chatInput.value = e.target.dataset.q;
      chatInput.focus();
    }
  }
});

// Initialize filter behavior for two-pane layout
document.addEventListener('DOMContentLoaded', () => {
  const pageSearch = document.getElementById('page-search');
  if (pageSearch) {
    pageSearch.addEventListener('input', debounce(e => {
      activeQuery = e.target.value.toLowerCase().trim();
      applyFilters();
    }, 150));
  }

  // Homepage category search/filter
  const categorySearch = document.getElementById('category-search');
  if (categorySearch) {
    categorySearch.addEventListener('input', e => {
      const query = e.target.value.toLowerCase().trim();
      const categoryItems = document.querySelectorAll('.home-nav-item');
      
      categoryItems.forEach(item => {
        const categoryText = item.dataset.category.toLowerCase();
        const matchesQuery = categoryText.includes(query);
        item.style.display = matchesQuery ? 'flex' : 'none';
      });
    });
  }

  // Sidebar toggle functionality
  const homeSidebarToggle = document.getElementById('sidebar-toggle-home');
  const categorySidebarToggle = document.getElementById('sidebar-toggle-category');
  
  if (homeSidebarToggle) {
    homeSidebarToggle.addEventListener('click', () => {
      const sidebar = document.getElementById('home-sidebar');
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('home-sidebar-collapsed', sidebar.classList.contains('collapsed'));
    });
    
    // Restore sidebar state
    if (localStorage.getItem('home-sidebar-collapsed') === 'true') {
      const sidebar = document.getElementById('home-sidebar');
      sidebar.classList.add('collapsed');
    }
  }
  
  if (categorySidebarToggle) {
    categorySidebarToggle.addEventListener('click', () => {
      const sidebar = document.getElementById('category-sidebar');
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('category-sidebar-collapsed', sidebar.classList.contains('collapsed'));
    });
    
    // Restore sidebar state
    if (localStorage.getItem('category-sidebar-collapsed') === 'true') {
      const sidebar = document.getElementById('category-sidebar');
      sidebar.classList.add('collapsed');
    }
  }
});
