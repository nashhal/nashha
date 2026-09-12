/* news-loader.js
   يقرأ data/news.json الذي ينتجه news_bot_v2.py دون تعديل على بنيته
   ويبني واجهة نشهل: عاجل، خبر رئيسي، آخر الأخبار، شبكة الأخبار، وقيد التحقق.
*/
(function () {
  'use strict';

  const DATA_URL = `data/news.json?v=${Date.now()}`;
  const GRID_LIMIT = 12;
  const VERIFY_LIMIT = 6;
  const TICKER_LIMIT = 8;

  let allItems = [];
  let currentFilter = 'all';

  const platformLabel = { X: 'رصد من X', Facebook: 'رصد من فيسبوك' };

  const clean = (value = '') => String(value)
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const escapeHtml = (value = '') => clean(value).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));

  const safeUrl = (value = '') => {
    try {
      const url = new URL(String(value), window.location.href);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : '#';
    } catch (_) { return '#'; }
  };

  function timeAgo(iso) {
    if (!iso) return '';
    const then = Date.parse(iso);
    if (Number.isNaN(then)) return '';
    const diffMin = Math.max(0, Math.floor((Date.now() - then) / 60000));
    if (diffMin < 1) return 'الآن';
    if (diffMin < 60) return `قبل ${diffMin} دقيقة`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `قبل ${diffHr} ساعة`;
    const diffDay = Math.floor(diffHr / 24);
    return `قبل ${diffDay} يوم`;
  }

  function normalize(item = {}) {
    const title = clean(item.title || item.headline || '');
    const summary = clean(item.summary || item.description || '');
    const sourceName = clean(item.source_name || item.source || item.publisher || 'المصدر');
    const sourceUrl = safeUrl(item.source_url || item.link || item.url || '#');
    const published = item.published || item.published_at || item.pubDate || item.date || item.collected_at || '';
    const category = clean(item.category || item.region || 'اليمن');
    const status = clean(item.status || 'published');
    const confidence = clean(item.confidence || '');
    const platform = clean(item.platform || 'news');
    const image = safeUrl(item.image || item.thumbnail || '') === '#' ? '' : safeUrl(item.image || item.thumbnail || '');

    return { title, summary, sourceName, sourceUrl, published, category, status, confidence, platform, image };
  }

  function confirmed(item) {
    return item.status === 'published' && ['high', 'medium'].includes(item.confidence);
  }

  function review(item) {
    return item.status === 'review';
  }

  function sortRecent(items) {
    return [...items].sort((a, b) => (Date.parse(b.published) || 0) - (Date.parse(a.published) || 0));
  }

  function confirmedItems(filter = 'all') {
    let items = allItems.filter(confirmed);
    if (filter !== 'all') items = items.filter(item => item.category === filter);
    return sortRecent(items);
  }

  function sourceLink(item) {
    if (!item.sourceName) return '';
    return item.sourceUrl && item.sourceUrl !== '#'
      ? `<a class="src-link" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.sourceName)}</a>`
      : escapeHtml(item.sourceName);
  }

  function metaLine(item) {
    return `<div class="meta-line"><span>${escapeHtml(item.category)}</span><span class="dot"></span><span>${escapeHtml(timeAgo(item.published))}</span><span class="dot"></span>${sourceLink(item)}</div>`;
  }

  function placeholder(label = 'صورة الخبر') {
    return `<div class="media-ph"><span>${escapeHtml(label)}</span></div>`;
  }

  function media(item, klass = '') {
    return item.image
      ? `<img class="${klass}" src="${escapeHtml(item.image)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
      : placeholder('نشهل');
  }

  function renderTicker() {
    const track = document.getElementById('tickerTrack');
    if (!track) return;
    const items = confirmedItems().slice(0, TICKER_LIMIT);
    track.innerHTML = items.length
      ? items.map(item => `<a class="ticker-item" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer"><strong>عاجل</strong><span>${escapeHtml(item.title)}</span><small>${escapeHtml(timeAgo(item.published))}</small></a>`).join('')
      : `<span class="ticker-item">لا توجد تحديثات جديدة حاليًا</span>`;
  }

  function renderHero(filter = 'all') {
    const root = document.getElementById('heroGrid');
    if (!root) return;
    const items = confirmedItems(filter);
    if (!items.length) {
      root.innerHTML = '<div class="empty-state">لا توجد أخبار منشورة في هذا القسم حاليًا</div>';
      return;
    }
    const main = items[0];
    const rail = items.slice(1, 5);
    root.innerHTML = `
      <article class="hero-main">
        <a class="hero-media" href="${escapeHtml(main.sourceUrl)}" target="_blank" rel="noopener noreferrer">${media(main, 'hero-photo')}</a>
        <div class="hero-body">
          <span class="kicker">${escapeHtml(main.category)}</span>
          <h1><a href="${escapeHtml(main.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(main.title)}</a></h1>
          <p class="hero-summary">${escapeHtml(main.summary)}</p>
          ${metaLine(main)}
        </div>
      </article>
      <aside class="hero-rail" aria-label="أحدث أربعة أخبار">
        ${rail.map((item, index) => `
          <article class="rail-item">
            <div class="rail-index">0${index + 1}</div>
            <a class="rail-media" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${media(item, 'rail-photo')}</a>
            <div class="rail-content">
              <span class="kicker">${escapeHtml(item.category)}</span>
              <h2><a href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h2>
              ${metaLine(item)}
            </div>
          </article>`).join('')}
      </aside>`;
  }

  function renderGrid(filter = 'all') {
    const grid = document.getElementById('newsGrid');
    const title = document.getElementById('gridTitle');
    if (!grid) return;
    if (title) title.textContent = filter === 'all' ? 'أحدث الأخبار' : `أحدث أخبار ${filter}`;
    const items = confirmedItems(filter).slice(5, 5 + GRID_LIMIT);
    if (!items.length) {
      grid.innerHTML = '<div class="empty-state">لا مزيد من الأخبار في هذا القسم حاليًا</div>';
      return;
    }
    grid.innerHTML = items.map((item, index) => `
      <article class="news-card ${index === 0 ? 'news-card-featured' : ''}">
        <a class="card-media" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${media(item, 'card-photo')}<span class="card-tag">${escapeHtml(item.category)}</span></a>
        <div class="card-body">
          <span class="kicker">${escapeHtml(item.category)}</span>
          <h3><a href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
          <p>${escapeHtml(item.summary)}</p>
          ${metaLine(item)}
        </div>
      </article>`).join('');
  }

  function renderVerify() {
    const wrap = document.getElementById('verifySection');
    const list = document.getElementById('verifyList');
    if (!wrap || !list) return;
    const items = sortRecent(allItems.filter(review)).slice(0, VERIFY_LIMIT);
    wrap.hidden = !items.length;
    list.innerHTML = items.map(item => `
      <article class="verify-item">
        <span class="verify-badge">${escapeHtml(platformLabel[item.platform] || 'قيد التحقق')}</span>
        <div>
          <h3><a href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
          <div class="verify-meta">${escapeHtml(item.category)} · ${escapeHtml(timeAgo(item.published))}</div>
        </div>
      </article>`).join('');
  }

  function setupFilters() {
    const nav = document.getElementById('sectionNav');
    if (!nav) return;
    nav.querySelectorAll('[data-filter]').forEach(button => {
      button.addEventListener('click', () => {
        nav.querySelectorAll('[data-filter]').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        currentFilter = button.dataset.filter || 'all';
        renderHero(currentFilter);
        renderGrid(currentFilter);
      });
    });
  }

  function setupDarkMode() {
    const root = document.documentElement;
    const saved = localStorage.getItem('nahshal-theme');
    if (saved === 'dark') root.classList.add('dark');
    const toggle = document.getElementById('darkToggle');
    if (toggle) toggle.addEventListener('click', () => {
      root.classList.toggle('dark');
      localStorage.setItem('nahshal-theme', root.classList.contains('dark') ? 'dark' : 'light');
    });
  }

  function setupSearch() {
    const button = document.getElementById('searchToggle');
    const panel = document.getElementById('searchPanel');
    const form = document.getElementById('searchForm');
    const input = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    if (!button || !panel || !form || !input || !results) return;
    button.addEventListener('click', () => panel.classList.toggle('open'));
    form.addEventListener('submit', event => {
      event.preventDefault();
      const q = clean(input.value).toLowerCase();
      const matches = confirmedItems().filter(item => `${item.title} ${item.summary} ${item.category}`.toLowerCase().includes(q)).slice(0, 8);
      results.innerHTML = q && matches.length ? matches.map(item => `<a href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)} <small>${escapeHtml(item.sourceName)}</small></a>`).join('') : (q ? '<span>لا توجد نتائج مطابقة</span>' : '');
    });
  }

  async function init() {
    setupFilters();
    setupDarkMode();
    setupSearch();
    try {
      const response = await fetch(DATA_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const raw = Array.isArray(data) ? data : (data.items || data.news || []);
      allItems = raw.map(normalize).filter(item => item.title && item.sourceUrl !== '#');
    } catch (error) {
      console.error('تعذر تحميل الأخبار:', error);
      allItems = [];
    }
    renderTicker();
    renderHero(currentFilter);
    renderGrid(currentFilter);
    renderVerify();
  }

  document.addEventListener('DOMContentLoaded', init);
})();