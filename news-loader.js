/* Nashhal — secure dynamic homepage news loader */
(() => {
  'use strict';

  const NEWS_URL = `data/news.json?v=${Date.now()}`;
  const SOUTH_TERMS = [
    'عدن','حضرموت','شبوة','أبين','لحج','الضالع','سقطرى','المهرة',
    'الجنوب','جنوب اليمن','المجلس الانتقالي','الساحل الغربي','العند'
  ];
  const YEMEN_TERMS = [
    'اليمن','يمني','صنعاء','تعز','مأرب','الحديدة','حجة','إب','صعدة','الضالع',
    'الحوثي','الحوثيين','الحوثيون','حكومة اليمن','الأمم المتحدة في اليمن'
  ];

  const escapeHTML = (value = '') => String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const cleanText = (value = '') => String(value)
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const safeURL = (value = '') => {
    try {
      const url = new URL(String(value), window.location.href);
      if (url.protocol === 'http:' || url.protocol === 'https:') return url.href;
    } catch (_) {}
    return '#';
  };

  const safeImageURL = (value = '') => {
    const url = safeURL(value);
    return url === '#' ? '' : url;
  };

  const normalize = (item = {}) => {
    const title = cleanText(item.title || item.headline || '');
    const summary = cleanText(item.summary || item.description || '');
    const source = cleanText(item.source || item.publisher || 'المصدر');
    const published = item.published || item.pubDate || item.date || item.collected_at || '';
    const text = `${title} ${summary}`.toLowerCase();
    const isSouth = SOUTH_TERMS.some(term => text.includes(term.toLowerCase()));
    const isYemen = isSouth || YEMEN_TERMS.some(term => text.includes(term.toLowerCase()));

    return {
      title,
      summary,
      source,
      published,
      status: cleanText(item.status || 'published'),
      platform: cleanText(item.platform || 'news'),
      confidence: cleanText(item.confidence || ''),
      href: safeURL(item.href || item.link || item.url || '#'),
      image: safeImageURL(item.image || item.thumbnail || ''),
      region: cleanText(item.region || item.category || ''),
      isSouth,
      isYemen
    };
  };

  const dateValue = (item) => {
    const time = Date.parse(item.published || '');
    return Number.isNaN(time) ? 0 : time;
  };

  const formatDate = (value) => {
    const time = Date.parse(value || '');
    if (Number.isNaN(time)) return 'الآن';
    return new Intl.DateTimeFormat('ar-SA', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    }).format(new Date(time));
  };

  const formatRelative = (value) => {
    const time = Date.parse(value || '');
    if (Number.isNaN(time)) return 'الآن';
    const minutes = Math.max(0, Math.floor((Date.now() - time) / 60000));
    if (minutes < 1) return 'الآن';
    if (minutes < 60) return `قبل ${minutes} دقيقة`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `قبل ${hours} ساعة`;
    const days = Math.floor(hours / 24);
    return `قبل ${days} يوم`;
  };

  const sourceLabel = (item) => {
    const source = escapeHTML(item.source || 'المصدر');
    const date = escapeHTML(formatDate(item.published));
    const relative = escapeHTML(formatRelative(item.published));
    return `<span>${source}</span><span aria-hidden="true">·</span><span>${date}</span><span class="news-age">${relative}</span>`;
  };

  function enhanceIdentity() {
    document.body.classList.add('nashhal-enhanced');
    if (document.getElementById('nashhal-enhanced-style')) return;
    const style = document.createElement('style');
    style.id = 'nashhal-enhanced-style';
    style.textContent = `
      :root{--nh-accent:#1d513a;--nh-accent-soft:#e9efe9}
      .nashhal-enhanced .brand-name{letter-spacing:-.04em}
      .nashhal-enhanced .brand::after{content:'NEWS';font:800 9px/1 Tajawal,sans-serif;letter-spacing:.16em;color:var(--accent2);align-self:flex-end;margin:0 0 8px -5px}
      .nashhal-enhanced .hero-main{overflow:hidden;position:relative}
      .nashhal-enhanced .hero-main::before{content:'';position:absolute;inset:0 auto 0 0;width:4px;background:var(--accent2);z-index:2}
      .nashhal-enhanced .label{text-transform:none;letter-spacing:.01em}
      .nashhal-enhanced .ticker{scrollbar-width:none}
      .nashhal-enhanced .ticker a{padding:0 10px;border-left:1px solid rgba(255,255,255,.12)}
      .nashhal-enhanced .ticker strong{font:800 10px Tajawal,sans-serif;color:#f3b9b5;margin-left:5px}
      .nashhal-enhanced .ticker small,.news-age{opacity:.62;font-size:10px}
      .nashhal-enhanced .card-meta,.nashhal-enhanced .meta{align-items:center;gap:8px}
      .nashhal-enhanced .card,.nashhal-enhanced .hero-main,.nashhal-enhanced .side{transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}
      .nashhal-enhanced .card:hover,.nashhal-enhanced .side:hover{border-color:#c9d5cc}
      .nashhal-enhanced a:focus-visible,.nashhal-enhanced button:focus-visible,.nashhal-enhanced input:focus-visible{outline:3px solid rgba(47,122,82,.28);outline-offset:2px}
      .nashhal-x-review{margin:0 0 22px;border:1px solid var(--line);background:var(--paper);box-shadow:var(--shadow);overflow:hidden}
      .nashhal-x-review-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 15px;border-bottom:1px solid var(--line);background:var(--soft)}
      .nashhal-x-review-title{font:800 13px 'IBM Plex Sans Arabic',sans-serif;color:var(--green)}
      .nashhal-x-review-note{font-size:9px;color:var(--muted)}
      .nashhal-x-review-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0}
      .nashhal-x-item{display:block;padding:13px 14px;border-left:1px solid var(--line);min-width:0}
      .nashhal-x-item:last-child{border-left:0}
      .nashhal-x-item:hover{background:var(--soft)}
      .nashhal-x-badge{display:inline-block;font:800 8px 'IBM Plex Sans Arabic',sans-serif;color:var(--red);background:rgba(186,30,35,.08);padding:2px 6px;border-radius:4px;margin-bottom:6px}
      .nashhal-x-item h3{font:600 11px/1.7 'IBM Plex Sans Arabic',sans-serif}
      .nashhal-x-item p{margin-top:4px;font-size:8px;color:var(--muted)}
      @media(max-width:900px){.nashhal-x-review-list{grid-template-columns:1fr}.nashhal-x-item{border-left:0;border-bottom:1px solid var(--line)}.nashhal-x-item:last-child{border-bottom:0}}
      @media(max-width:600px){.nashhal-enhanced .brand::after{display:none}.nashhal-enhanced .hero-main::before{width:3px}.nashhal-enhanced .news-age{display:none}.nashhal-x-review{margin-bottom:15px}.nashhal-x-review-head{align-items:flex-start;flex-direction:column;gap:3px}}
    `;
    document.head.appendChild(style);
  }

  function renderXReview(items) {
    const existing = document.querySelector('.nashhal-x-review');
    if (existing) existing.remove();
    if (!items.length) return;

    const breaking = document.querySelector('.breaking');
    if (!breaking) return;

    const box = document.createElement('section');
    box.className = 'nashhal-x-review wrap';
    box.setAttribute('aria-label', 'رصد من منصة X قيد التحقق');
    box.innerHTML = `
      <div class="nashhal-x-review-head">
        <div class="nashhal-x-review-title">رصد X · قيد التحقق</div>
        <div class="nashhal-x-review-note">إشارات سريعة من X لا تُعد خبرًا منشورًا قبل التحقق من المصدر</div>
      </div>
      <div class="nashhal-x-review-list">
        ${items.slice(0, 6).map(item => `
          <a class="nashhal-x-item" href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer">
            <span class="nashhal-x-badge">قيد التحقق</span>
            <h3>${escapeHTML(item.title)}</h3>
            <p>X · ${escapeHTML(formatRelative(item.published))}</p>
          </a>
        `).join('')}
      </div>
    `;
    breaking.insertAdjacentElement('afterend', box);
  }

  function renderHero(item) {
    if (!item) return;
    const hero = document.querySelector('.hero');
    if (!hero) return;

    const title = hero.querySelector('[data-hero-title]');
    const summary = hero.querySelector('[data-hero-summary]');
    const link = hero.querySelector('[data-hero-link]');
    const image = hero.querySelector('[data-hero-image]');
    const meta = hero.querySelector('[data-hero-meta]');

    if (title) title.innerHTML = `<a href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer" style="color:inherit">${escapeHTML(item.title)}</a>`;
    if (summary) summary.textContent = item.summary || 'متابعة مستمرة من نشهل لأبرز التطورات والأخبار.';
    if (link) {
      link.href = item.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
    }
    if (image && item.image) {
      image.src = item.image;
      image.alt = item.title;
      image.loading = 'eager';
      image.referrerPolicy = 'no-referrer';
    }
    if (meta) meta.innerHTML = sourceLabel(item);
  }

  function renderTicker(items) {
    const ticker = document.querySelector('[data-breaking-ticker]') || document.querySelector('.ticker');
    if (!ticker || !items.length) return;
    ticker.innerHTML = items.slice(0, 5).map(item =>
      `<a href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer"><strong>عاجل</strong>${escapeHTML(item.title)} <small>${escapeHTML(formatRelative(item.published))}</small></a>`
    ).join('');
  }

  function renderLatest(items) {
    const list = document.querySelector('[data-latest-list]');
    if (!list) return;
    list.innerHTML = items.slice(0, 4).map((item, index) => `
      <div class="rank">
        <div class="rank-num">${String(index + 1).padStart(2, '0')}</div>
        <div>
          <h3><a href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(item.title)}</a></h3>
          <p>${escapeHTML(item.source)} · ${escapeHTML(formatRelative(item.published))}</p>
        </div>
      </div>
    `).join('');
  }

  function renderCards(items) {
    const cards = document.querySelector('#cards');
    if (!cards) return;

    cards.innerHTML = items.slice(0, 12).map(item => {
      const region = item.region || (item.isSouth ? 'الجنوب' : 'اليمن');
      const image = item.image ? `<a class="card-image" href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer"><img src="${escapeHTML(item.image)}" alt="" loading="lazy" referrerpolicy="no-referrer"><span class="tag">${escapeHTML(region)}</span></a>` : '';
      return `
        <article class="card" data-region="${escapeHTML(region)}" data-title="${escapeHTML(item.title)}">
          ${image}
          <div class="card-body">
            <div class="card-meta">${sourceLabel(item)}</div>
            <h3><a href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(item.title)}</a></h3>
            ${item.summary ? `<p>${escapeHTML(item.summary)}</p>` : ''}
          </div>
        </article>
      `;
    }).join('');
  }

  function renderReport(items) {
    const report = document.querySelector('.report');
    if (!report || !items.length) return;
    const latest = items[0];
    const title = report.querySelector('[data-report-title]');
    const text = report.querySelector('[data-report-text]');
    const day = report.querySelector('[data-report-day]');
    const month = report.querySelector('[data-report-month]');
    const link = report.querySelector('[data-report-link]');

    if (title) title.textContent = 'ملخص نشهل لأبرز أخبار اليوم';
    if (text) text.textContent = `${latest.title} — المصدر: ${latest.source}.`;

    const date = new Date(Date.parse(latest.published));
    if (!Number.isNaN(date.getTime())) {
      if (day) day.textContent = String(date.getDate()).padStart(2, '0');
      if (month) month.textContent = new Intl.DateTimeFormat('ar-SA', { month: 'long', year: 'numeric' }).format(date);
    }

    if (link) {
      link.href = latest.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'فتح الخبر الأصلي ←';
    }
  }

  function setHomepageMeta(items) {
    const latest = items[0];
    const title = document.querySelector('[data-latest-title]');
    const time = document.querySelector('[data-latest-time]');
    if (title && latest) title.textContent = latest.title;
    if (time && latest) time.textContent = formatDate(latest.published);
  }

  function rebindFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = cleanText(btn.dataset.filter || 'all');
        document.querySelectorAll('#south .card').forEach(card => {
          const region = card.dataset.region || '';
          const title = card.dataset.title || '';
          card.style.display = filter === 'all' || region.includes(filter) || title.includes(filter) ? 'block' : 'none';
        });
      };
    });
  }

  enhanceIdentity();

  fetch(NEWS_URL, { cache: 'no-store' })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(data => {
      const raw = Array.isArray(data) ? data : (data.news || data.items || []);
      const normalized = raw.map(normalize).filter(item => item.title && item.href !== '#');
      const review = normalized
        .filter(item => item.status === 'review' && item.platform.toLowerCase() === 'x')
        .filter(item => item.isYemen)
        .sort((a, b) => dateValue(b) - dateValue(a));
      const all = normalized
        .filter(item => item.status === 'published' || !item.status)
        .filter(item => item.isYemen);
      const south = all.filter(item => item.isSouth);
      const sortedAll = [...all].sort((a, b) => dateValue(b) - dateValue(a));
      const sortedSouth = [...south].sort((a, b) => dateValue(b) - dateValue(a));

      renderXReview(review);
      const hero = sortedSouth[0] || sortedAll[0];
      renderHero(hero);
      renderTicker(sortedAll);
      renderLatest(sortedSouth.length ? sortedSouth : sortedAll);
      renderCards(sortedAll);
      renderReport(sortedAll);
      setHomepageMeta(sortedAll);
      rebindFilters();

      document.dispatchEvent(new CustomEvent('nashhal:news-ready', {
        detail: { all: sortedAll, south: sortedSouth, xReview: review }
      }));
    })
    .catch(error => {
      console.error('Nashhal news loader:', error);
      const cards = document.querySelector('#cards');
      if (cards) cards.innerHTML = '<div class="card"><div class="card-body"><h3>تعذر تحديث الأخبار حاليًا</h3><p>سيبقى المحتوى الحالي ظاهرًا حتى عودة خدمة الأخبار.</p></div></div>';
    });
})();
