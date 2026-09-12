/* Nashhal — dynamic homepage news loader */
(() => {
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

  const normalize = (item) => {
    const title = cleanText(item.title || item.headline || '');
    const summary = cleanText(item.summary || item.description || '');
    const source = cleanText(item.source || item.publisher || 'المصدر');
    const published = item.published || item.pubDate || item.date || item.collected_at || '';
    const text = `${title} ${summary}`.toLowerCase();
    const isSouth = SOUTH_TERMS.some(term => text.includes(term.toLowerCase()));
    const isYemen = isSouth || YEMEN_TERMS.some(term => text.includes(term.toLowerCase()));
    return {
      ...item,
      title,
      summary,
      source,
      published,
      href: item.href || item.link || item.url || '#',
      image: item.image || item.thumbnail || '',
      region: item.region || item.category || '',
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
      year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
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
    return `<span>${source}</span><span>·</span><span>${date}</span>`;
  };

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
      image.alt = escapeHTML(item.title);
    }
    if (meta) meta.innerHTML = sourceLabel(item) + `<span>${escapeHTML(formatRelative(item.published))}</span>`;
  }

  function renderTicker(items) {
    const ticker = document.querySelector('[data-breaking-ticker]') || document.querySelector('.ticker');
    if (!ticker || !items.length) return;
    const stories = items.slice(0, 4);
    ticker.innerHTML = stories.map(item =>
      `<a href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer"><strong>عاجل</strong> ${escapeHTML(item.title)} <small>${escapeHTML(formatRelative(item.published))}</small></a>`
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

    cards.innerHTML = items.slice(0, 12).map(item => `
      <article class="card" data-region="${escapeHTML(item.region || '')}" data-title="${escapeHTML(item.title)}">
        ${item.image ? `<a class="card-image" href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer"><img src="${escapeHTML(item.image)}" alt="" loading="lazy"><span class="tag">${escapeHTML(item.region || (item.isSouth ? 'الجنوب' : 'اليمن'))}</span></a>` : ''}
        <div class="card-body">
          <div class="card-meta">${sourceLabel(item)} · ${escapeHTML(formatRelative(item.published))}</div>
          <h3><a href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(item.title)}</a></h3>
          ${item.summary ? `<p>${escapeHTML(item.summary)}</p>` : ''}
        </div>
      </article>
    `).join('');
  }

  function renderReport(items) {
    const report = document.querySelector('.report');
    if (!report) return;
    const latest = items[0];
    const title = report.querySelector('[data-report-title]');
    const text = report.querySelector('[data-report-text]');
    const day = report.querySelector('[data-report-day]');
    const month = report.querySelector('[data-report-month]');
    const link = report.querySelector('[data-report-link]');

    if (latest) {
      const date = new Date(Date.parse(latest.published));
      if (title) title.textContent = 'ملخص نشهل لأبرز أخبار اليوم';
      if (text) text.textContent = `${latest.title} — المصدر: ${latest.source}.`;
      if (day && !Number.isNaN(date.getTime())) day.textContent = String(date.getDate()).padStart(2, '0');
      if (month && !Number.isNaN(date.getTime())) month.textContent = new Intl.DateTimeFormat('ar-SA', { month: 'long', year: 'numeric' }).format(date);
      if (link) {
        link.href = latest.href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'فتح الخبر الأصلي ←';
      }
    }
    report.style.fontFamily = 'Tajawal, "Noto Kufi Arabic", sans-serif';
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
        const f = btn.dataset.filter;
        document.querySelectorAll('#south .card').forEach(card => {
          const region = card.dataset.region || '';
          const title = card.dataset.title || '';
          card.style.display = f === 'all' || region.includes(f) || title.includes(f) ? 'block' : 'none';
        });
      };
    });
  }

  fetch(NEWS_URL, { cache: 'no-store' })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(data => {
      const raw = Array.isArray(data) ? data : (data.news || data.items || []);
      const all = raw.map(normalize).filter(item => item.title && item.isYemen);
      const south = all.filter(item => item.isSouth);
      const sortedAll = [...all].sort((a, b) => dateValue(b) - dateValue(a));
      const sortedSouth = [...south].sort((a, b) => dateValue(b) - dateValue(a));

      // South Yemen gets priority for the hero while the full Yemen stream fills the cards.
      const hero = sortedSouth[0] || sortedAll[0];
      renderHero(hero);
      renderTicker(sortedAll);
      renderLatest(sortedSouth.length ? sortedSouth : sortedAll);
      renderCards(sortedAll);
      renderReport(sortedAll);
      setHomepageMeta(sortedAll);
      rebindFilters();

      document.dispatchEvent(new CustomEvent('nashhal:news-ready', {
        detail: { all: sortedAll, south: sortedSouth }
      }));
    })
    .catch(error => {
      console.error('Nashhal news loader:', error);
    });
})();
