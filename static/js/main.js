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
    const res  = await fetch(`/api/ask?${params}`);
    const data = await res.json();
    if (!res.ok || data.error) {
      appendErrorBubble(data.error || 'No answer found. Try rephrasing your question.');
    } else {
      if (data.topic) contextTopic = data.topic;
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
