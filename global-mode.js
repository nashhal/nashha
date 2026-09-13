(function () {
  'use strict';

  const DATA_URL = 'data/news.json';
  const CATEGORIES = [
    ['all', 'الكل', 'All'],
    ['اليمن', 'اليمن', 'Yemen'],
    ['الخليج', 'الخليج', 'Gulf'],
    ['العالم العربي', 'العالم العربي', 'Arab World'],
    ['العالم', 'العالم', 'World'],
    ['اقتصاد', 'اقتصاد', 'Business'],
    ['تقنية', 'تقنية', 'Technology'],
    ['علوم', 'علوم', 'Science'],
    ['ثقافة', 'ثقافة', 'Culture'],
    ['رياضة', 'رياضة', 'Sports']
  ];

  let items = [];
  let filter = 'all';
  let lang = window.NashhalLang ? window.NashhalLang.get() : 'ar';

  const clean = value => String(value || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  const esc = value => clean(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const url = value => {
    try {
      const u = new URL(String(value || ''), location.href);
      return /^https?:$/.test(u.protocol) ? u.href : '#';
    } catch (_) { return '#'; }
  };
  const timeAgo = iso => {
    const t = Date.parse(iso || '');
    if (Number.isNaN(t)) return '';
    const m = Math.max(0, Math.floor((Date.now() - t) / 60000));
    if (m < 1) return lang === 'ar' ? 'الآن' : 'now';
    if (m < 60) return lang === 'ar' ? `قبل ${m} دقيقة` : `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return lang === 'ar' ? `قبل ${h} ساعة` : `${h}h ago`;
    const d = Math.floor(h / 24);
    return lang === 'ar' ? `قبل ${d} يوم` : `${d}d ago`;
  };
  const isPublished = x => ['published'].includes(clean(x.status || 'published')) && ['high','medium',''].includes(clean(x.confidence || ''));
  const sorted = () => items.filter(isPublished).sort((a,b) => (Date.parse(b.published_at || b.published) || 0) - (Date.parse(a.published_at || a.published) || 0));
  const filtered = () => filter === 'all' ? sorted() : sorted().filter(x => clean(x.category) === filter);

  function articleHref(item) {
    return `article.html?id=${encodeURIComponent(item.id || item.source_url || item.link || '')}`;
  }

  function label(code) {
    const row = CATEGORIES.find(x => x[0] === code);
    return row ? (lang === 'ar' ? row[1] : row[2]) : code;
  }

  function rewriteStatic() {
    const first = document.querySelector('.top .wrap > div:first-child');
    const mast = document.querySelector('.mast');
    const desc = document.querySelector('meta[name="description"]');
    const title = document.querySelector('.panel-head span');
    const sub = document.querySelector('.brand-sub');
    if (first) first.textContent = lang === 'ar' ? 'نشهل · منصة أخبار عربية وعالمية' : 'Nashhal · Arabic & Global News';
    if (mast) mast.innerHTML = `<strong>نشهل</strong>${lang === 'ar' ? 'خبر · سياق · تحليل' : 'News · Context · Analysis'}`;
    if (sub) sub.textContent = lang === 'ar' ? 'خبر · سياق · تحليل' : 'News · Context · Analysis';
    if (title) title.textContent = lang === 'ar' ? 'تحديث مستمر · تغطية عربية وعالمية' : 'Live updates · Arabic & global coverage';
    if (desc) desc.content = lang === 'ar'
      ? 'نشهل منصة أخبار عربية وعالمية تقدم الخبر والسياق والتحليل بصياغة عربية دقيقة.'
      : 'Nashhal is an Arabic and global news platform focused on accurate reporting, context and analysis.';
    document.title = lang === 'ar' ? 'نشهل | أخبار عربية وعالمية' : 'Nashhal | Arabic & Global News';
  }

  function renderNav() {
    const nav = document.getElementById('sectionNav');
    if (!nav) return;
    nav.innerHTML = CATEGORIES.map(([code, ar, en]) => `
      <button type="button" data-global-filter="${esc(code)}" class="${code === filter ? 'active' : ''}">${esc(lang === 'ar' ? ar : en)}</button>
    `).join('');
    nav.querySelectorAll('[data-global-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        filter = btn.dataset.globalFilter || 'all';
        renderNav();
        render();
      });
    });
  }

  function card(item, featured) {
    const category = clean(item.category) || 'العالم';
    const title = clean(item.title || item.original_title);
    const summary = clean(item.summary || item.description || item.content);
    const media = item.image
      ? `<img src="${esc(url(item.image))}" alt="" loading="lazy" decoding="async">`
      : `<div class="global-ph">${esc(lang === 'ar' ? 'نشهل' : 'Nashhal')}</div>`;
    return `<article class="global-card ${featured ? 'global-featured' : ''}">
      <a class="global-media" href="${esc(articleHref(item))}">${media}<span class="global-tag">${esc(label(category))}</span></a>
      <div class="global-body">
        <span class="global-kicker">${esc(label(category))}</span>
        <h3><a href="${esc(articleHref(item))}">${esc(title)}</a></h3>
        <p>${esc(summary)}</p>
        <div class="global-meta">${esc(timeAgo(item.published_at || item.published))}</div>
      </div>
    </article>`;
  }

  function renderHero(list) {
    const root = document.getElementById('heroGrid');
    if (!root) return;
    if (!list.length) {
      root.innerHTML = `<div class="empty-state">${lang === 'ar' ? 'لا توجد أخبار منشورة في هذا القسم حاليًا' : 'No published stories in this section yet'}</div>`;
      return;
    }
    const main = list[0];
    const rail = list.slice(1,5);
    const media = main.image
      ? `<img class="hero-photo" src="${esc(url(main.image))}" alt="" loading="eager" fetchpriority="high" decoding="async">`
      : `<div class="media-ph">${esc(lang === 'ar' ? 'نشهل' : 'Nashhal')}</div>`;
    root.innerHTML = `<article class="hero-main global-hero-main">
      <a class="hero-media" href="${esc(articleHref(main))}">${media}</a>
      <div class="hero-body">
        <span class="kicker">${esc(label(main.category))}</span>
        <h1><a href="${esc(articleHref(main))}">${esc(clean(main.title || main.original_title))}</a></h1>
        <p class="hero-summary">${esc(clean(main.summary || main.description || main.content))}</p>
        <div class="meta-line"><span>${esc(timeAgo(main.published_at || main.published))}</span></div>
      </div>
    </article>
    <aside class="hero-rail" aria-label="${esc(lang === 'ar' ? 'أحدث الأخبار' : 'Latest stories')}">
      ${rail.map((item, i) => `<article class="rail-item"><div class="rail-index">0${i+1}</div><a class="rail-media" href="${esc(articleHref(item))}">${item.image ? `<img class="rail-photo" src="${esc(url(item.image))}" alt="" loading="lazy">` : ''}</a><div class="rail-content"><span class="kicker">${esc(label(item.category))}</span><h2><a href="${esc(articleHref(item))}">${esc(clean(item.title || item.original_title))}</a></h2><div class="meta-line"><span>${esc(timeAgo(item.published_at || item.published))}</span></div></div></article>`).join('')}
    </aside>`;
  }

  function renderGrid(list) {
    const grid = document.getElementById('newsGrid');
    if (!grid) return;
    grid.innerHTML = list.length
      ? list.slice(5, 21).map((item, i) => card(item, i === 0)).join('')
      : `<div class="empty-state">${lang === 'ar' ? 'لا مزيد من الأخبار في هذا القسم حاليًا' : 'No more stories in this section'}</div>`;
  }

  function renderTicker(list) {
    const track = document.getElementById('tickerTrack');
    if (!track) return;
    track.innerHTML = list.slice(0, 8).map(item => `<a class="ticker-item" href="${esc(articleHref(item))}"><strong>${esc(lang === 'ar' ? 'خبر' : 'NEWS')}</strong><span>${esc(clean(item.title || item.original_title))}</span><small>${esc(timeAgo(item.published_at || item.published))}</small></a>`).join('') || `<span class="ticker-item">${esc(lang === 'ar' ? 'لا توجد تحديثات جديدة حاليًا' : 'No new updates')}</span>`;
  }

  function render() {
    rewriteStatic();
    renderNav();
    const list = filtered();
    const heading = document.getElementById('gridTitle');
    if (heading) heading.textContent = filter === 'all' ? (lang === 'ar' ? 'أحدث الأخبار' : 'Latest News') : label(filter);
    renderHero(list);
    renderGrid(list);
    renderTicker(sorted());
  }

  async function init() {
    try {
      const r = await fetch(`${DATA_URL}?v=${Math.floor(Date.now()/300000)}`, { cache: 'default' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      items = (Array.isArray(data) ? data : (data.news || data.items || [])).filter(x => x && x.title);
    } catch (e) {
      items = [];
      console.error('Nashhal global mode:', e);
    }
    render();
  }

  document.addEventListener('nashhal-language-change', event => {
    lang = event.detail && event.detail.lang ? event.detail.lang : lang;
    render();
  });
  document.addEventListener('DOMContentLoaded', init);
})();
