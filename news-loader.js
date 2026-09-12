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

    const title = hero.querySelector('h1, h2');
    const summary = hero.querySelector('p');
    const link = hero.querySelector('a[href]');
    const meta = hero.querySelector('[data-hero-meta]');

    if (title) title.textContent = item.title;
    if (summary) summary.textContent = item.summary || 'متابعة مستمرة من نشهل لأبرز التطورات والأخبار.';
    if (link) {
      link.href = item.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
    }
    if (meta) meta.innerHTML = sourceLabel(item);

    if (item.image) {
      hero.style.backgroundImage = `linear-gradient(90deg, rgba(10,24,19,.92), rgba(10,24,19,.42)), url("${item.image}")`;
      hero.style.backgroundSize = 'cover';
      hero.style.backgroundPosition = 'center';
    }
  }

  function renderTicker(items) {
    const ticker = document.querySelector('[data-breaking-ticker]') ||
      document.querySelector('.breaking-ticker');
    if (!ticker || !items.length) return;

    const stories = items.slice(0, 4);
    ticker.innerHTML = stories.map(item =>
      `<a href="${escapeHTML(item.href)}" target="_blank" rel="noopener noreferrer">` +
      `<strong>عاجل</strong> ${escapeHTML(item.title)} <small>${escapeHTML(formatRelative(item.published))}</small></a>`
    ).join('');
  }

  function renderCards(items) {
    const cards = document.querySelector('#cards');
    if (!cards) return;

    cards.innerHTML = items.slice(0, 12).map(item => `
      <article class="news-card" data-region="${escapeHTML(item.region || '')}">
        ${item.image ? `<img src="${escapeHTML(item.image)}" alt="" loading="lazy">` : ''}
        <div class="news-card-body">
          <div class="news-meta">${sourceLabel(item)}</div>
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
    const date = report.querySelector('[data-report-date]');
    const link = report.querySelector('a[href]');
    if (title) title.textContent = 'ملخص نشهل لأبرز أخبار اليوم';
    if (date) date.textContent = latest ? formatDate(latest.published) : 'اليوم';
    if (link && latest) link.href = latest.href;
    report.style.fontFamily = 'Tajawal, "Noto Kufi Arabic", sans-serif';
  }

  function setHomepageMeta(items) {
    const latest = items[0];
    const title = document.querySelector('[data-latest-title]');
    const time = document.querySelector('[data-latest-time]');
    if (title && latest) title.textContent = latest.title;
    if (time && latest) time.textContent = formatDate(latest.published);
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

      // South Yemen gets priority for the hero; Yemen-wide coverage fills the cards.
      const hero = sortedSouth[0] || sortedAll[0];
      renderHero(hero);
      renderTicker(sortedAll);
      renderCards(sortedAll);
      renderReport(sortedAll);
      setHomepageMeta(sortedAll);

      document.dispatchEvent(new CustomEvent('nashhal:news-ready', {
        detail: { all: sortedAll, south: sortedSouth }
      }));
    })
    .catch(error => {
      console.error('Nashhal news loader:', error);
    });
})();
