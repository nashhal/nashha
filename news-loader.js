/* Nashhal news engine
   Event-first publishing, verification-first UX, performant client rendering.
*/
(function () {
  'use strict';

  const DATA_URL = 'data/news.json';
  const CACHE_KEY = 'southern-revolution-news-cache-v1';
  const GRID_LIMIT = 12;
  const VERIFY_LIMIT = 6;
  const TICKER_LIMIT = 8;
  const CURRENT_HOURS = 72;
  const CITY_TERMS = ['Aden','Hadramout','Shabwah','Abyan','Lahj','Al Dhale’e','Al Mahrah','Socotra'];
  const platformLabel = { X: 'SOCIAL MONITORING', Facebook: 'SOCIAL MONITORING' };
  let allItems = [];
  let currentFilter = 'all';
  let lang = 'en';
  let lastRenderSignature = '';
  const UI={en:{news:'NEWS',monitor:'MONITORING',review:'UNDER REVIEW',latest:'Latest News',latestMeta:'Continuous coverage',none:'No recent published stories in this section',more:'No more published stories',verify:'Monitoring under review',verifyMeta:'Not treated as published news until sufficient evidence is available',update:'UPDATE',digital:'The Southern Revolution'}};

  const clean = (value = '') => String(value).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  const escapeHtml = (value = '') => clean(value).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
  const safeUrl = (value = '') => {
    if (!String(value).trim()) return '#';
    try { const url = new URL(String(value), window.location.href); return ['http:', 'https:'].includes(url.protocol) ? url.href : '#'; }
    catch (_) { return '#'; }
  };
  const articleUrl = item => `articles/${encodeURIComponent(item.id)}.html`;

  function timeAgo(iso) {
    const then = Date.parse(iso || '');
    if (Number.isNaN(then)) return '';
    const min = Math.max(0, Math.floor((Date.now() - then) / 60000));
    if (min < 1) return 'Now';
    if (min < 60) return `${min} min ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    return `${Math.floor(hr / 24)}d ago`;
  }

  function isCurrent(item) {
    const published = Date.parse(item.published);
    if (Number.isNaN(published)) return false;
    return (Date.now() - published) <= CURRENT_HOURS * 3600000 + 600000;
  }

  function noisyText(value = '') {
    const text = clean(value);
    if (!text) return true;
    const markers = [
      'English UN Logo',
      'UN data search',
      'About the UN',
      'UN Logo',
      'Submit search',
      'Breadcrumb',
      'Media Center'
    ];
    const hits = markers.filter(m => text.includes(m)).length;
    return hits >= 2 || (text.length > 700 && hits >= 1);
  }

  function displaySummary(item) {
    const candidates = [item.summary_en];
    for (const candidate of candidates) {
      const text = clean(candidate);
      if (text && !noisyText(text)) return text.slice(0, 260);
    }
    return '';
  }

  function normalize(item = {}, index = 0) {
    const title = clean(item.title_en || '');
    const summary = clean(item.summary_en || '');
    const sourceName = clean(item.source_name_en || item.source_name || item.source || item.publisher || '');
    const sourceUrl = safeUrl(item.source_url || item.link || item.url || '#');
    const published = item.published || item.published_at || item.pubDate || item.date || '';
    const category = clean(item.category_en || item.category || item.region || 'Yemen');
    const text = `${title} ${summary}`.toLowerCase();
    const city = item.region_en || CITY_TERMS.find(term => text.includes(term.toLowerCase())) || '';
    const imageValue = String(item.image || item.image_url || item.thumbnail || '').trim();
    const id = String(item.id || item.event_key || `${Date.parse(published) || index}-${title.slice(0,40)}`);
    return {
      id, title, summary, sourceName, sourceUrl, published, category,
      status: clean(item.status || 'published'), confidence: clean(item.confidence || ''),
      verification: clean(item.verification || ''), verificationScore: Number(item.verification_score || 0),
      evidenceCount: Number(item.verification_evidence_count || 0),
      platform: clean(item.platform || 'news'), city,
      image: imageValue ? safeUrl(imageValue) : ''
    };
  }

  const confirmed = item => item.status === 'published' && ['high', 'medium'].includes(item.confidence) && isCurrent(item) && Boolean(item.title_en);
  const review = item => ['review', 'developing_review'].includes(item.status) || item.verification === 'unconfirmed';
  const sortRecent = items => [...items].sort((a, b) => (Date.parse(b.published) || 0) - (Date.parse(a.published) || 0));
  const confirmedItems = (filter = 'all') => {
    let items = allItems.filter(confirmed);
    if (filter !== 'all') items = items.filter(item => item.category === filter || item.city === filter || item.region_en === filter);
    return sortRecent(items);
  };
  const categoryLabel = value => value || 'Yemen';
  const metaLine = item => `<div class="meta-line"><span>${escapeHtml(categoryLabel(item.category))}</span><span class="dot"></span><span>${escapeHtml(timeAgo(item.published))}</span></div>`;
  const placeholder = (label = UI?.[lang]?.digital || 'The Southern Revolution') => `<div class="media-ph"><span>${escapeHtml(label)}</span></div>`;
  const media = (item, klass = '') => item.image ? `<img class="${klass}" src="${escapeHtml(item.image)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : placeholder(UI.en.digital);

  function injectPerformanceCSS() {
    if (document.getElementById('nashhal-perf-css')) return;
    const style = document.createElement('style'); style.id = 'nashhal-perf-css';
    style.textContent = `.news-skeleton{display:grid;gap:10px;padding:18px;background:var(--paper);border:1px solid var(--line)}.sk{background:linear-gradient(90deg,var(--soft) 25%,rgba(255,255,255,.55) 50%,var(--soft) 75%);background-size:200% 100%;animation:nashhalShimmer 1.25s linear infinite;border-radius:4px}.sk.h{height:260px}.sk.t{height:24px;width:78%}.sk.s{height:15px;width:92%}.sk.m{height:13px;width:60%}@keyframes nashhalShimmer{to{background-position:-200% 0}}.trust-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:0;background:var(--paper);border:1px solid var(--line);margin:0 0 20px}.trust-strip a,.trust-strip div{padding:14px;border-left:1px solid var(--line);font:700 10px/1.7 'IBM Plex Sans';color:var(--ink)}.trust-strip a:last-child,.trust-strip div:last-child{border-left:0}.trust-strip strong{display:block;color:var(--green);font-size:12px;margin-bottom:3px}.verify-live{display:inline-flex;align-items:center;gap:5px}.verify-live i{width:6px;height:6px;border-radius:50%;background:#18794e}@media(max-width:650px){.trust-strip{grid-template-columns:1fr 1fr}.trust-strip a,.trust-strip div{border-bottom:1px solid var(--line)}}@media(prefers-reduced-motion:reduce){.sk{animation:none}.ticker-track,.live-dot{animation:none!important}}`;
    document.head.appendChild(style);
  }

  function showSkeleton() {
    const hero = document.getElementById('heroGrid'), grid = document.getElementById('newsGrid');
    if (hero && !hero.children.length) hero.innerHTML = '<div class="news-skeleton"><div class="sk h"></div><div class="sk t"></div><div class="sk s"></div><div class="sk m"></div></div>';
    if (grid && !grid.children.length) grid.innerHTML = Array.from({length:6},()=>'<div class="news-skeleton"><div class="sk h" style="height:150px"></div><div class="sk t"></div><div class="sk s"></div></div>').join('');
  }

  function renderTicker(){const track=document.getElementById('tickerTrack');if(!track)return;const items=confirmedItems().slice(0,TICKER_LIMIT);track.innerHTML=items.length?items.map(item=>`<a class="ticker-item" href="${articleUrl(item)}"><strong>${UI[lang].update}</strong><span>${escapeHtml(item.title)}</span><small>${escapeHtml(timeAgo(item.published))}</small></a>`).join(''):`<span class="ticker-item">${'No verified updates at the moment'}</span>`;}

  function renderHero(filter='all'){const root=document.getElementById('heroGrid');if(!root)return;const items=confirmedItems(filter);if(!items.length){root.innerHTML=`<div class="empty-state">${UI[lang].none}</div>`;return;}const main=items[0],rail=items.slice(1,5);root.innerHTML=`<article class="hero-main" data-news-id="${esc(main.id)}" tabindex="0" role="button"><a class="hero-media" href="${articleUrl(main)}" tabindex="-1">${media(main,'hero-photo')}</a><div class="hero-body"><span class="kicker">${escapeHtml(categoryLabel(main.category))}</span><h1>${escapeHtml(main.title)}</h1><p class="hero-summary">${escapeHtml(main.summary)}</p>${metaLine(main)}</div></article><aside class="hero-rail"><div class="rail-head"><h2>${UI[lang].latest}</h2><span>${UI[lang].latestMeta}</span></div>${rail.map((item,index)=>`<article class="rail-item" data-news-id="${esc(item.id)}" tabindex="0" role="button"><div class="rail-index">0${index+1}</div><a class="rail-media" href="${articleUrl(item)}" tabindex="-1">${media(item,'rail-photo')}</a><div class="rail-content"><span class="kicker">${escapeHtml(categoryLabel(item.category))}</span><h2>${escapeHtml(item.title)}</h2>${metaLine(item)}</div></article>`).join('')}</aside>`;}

  function renderGrid(filter='all'){const grid=document.getElementById('newsGrid'),title=document.getElementById('gridTitle');if(!grid)return;if(title){title.dataset.dynamic='1';title.textContent=filter==='all'?UI.en.latest:(categoryLabel(filter)+' News');}const items=confirmedItems(filter).slice(5,5+GRID_LIMIT);if(!items.length){grid.innerHTML=`<div class="empty-state">${UI[lang].more}</div>`;return;}grid.innerHTML=items.map((item,index)=>{const kind=item.platform==='X'||item.platform==='Facebook'?'social':item.status==='review'?'review':'news';const label=kind==='social'?`◉ ${UI.en.monitor}`:kind==='review'?`◌ ${UI.en.review}`:`✓ ${UI.en.news}`;const cls=kind==='news'?'tag-news':kind==='review'?'tag-review':'tag-social';return `<article class="news-card ${index===0?'news-card-featured':''} news-card-new" data-news-id="${esc(item.id)}" tabindex="0" role="button"><a class="card-media" href="${articleUrl(item)}" tabindex="-1">${media(item,'card-photo')}<span class="card-tag ${cls}">${label}</span></a><div class="card-body"><div class="card-status"><span class="status-icon" aria-hidden="true">${kind==='social'?'◉':kind==='review'?'◌':'✓'}</span>${label.replace(/^..\s*/,'')}</div><h3>${escapeHtml(item.title)}</h3>${item.summary ? `<p>${escapeHtml(item.summary)}</p>` : ''}${metaLine(item)}</div></article>`;}).join('');}

  function renderVerify(){const wrap=document.getElementById('verifySection'),list=document.getElementById('verifyList');if(!wrap||!list)return;const items=sortRecent(allItems.filter(review)).slice(0,VERIFY_LIMIT);wrap.hidden=!items.length;list.innerHTML=items.map(item=>`<article class="verify-item"><span class="verify-badge">◉ ${UI.en.review}</span><div><h3><a href="${articleUrl(item)}">${escapeHtml(item.title)}</a></h3><div class="verify-meta">${escapeHtml(item.category)} · ${escapeHtml(timeAgo(item.published))}</div></div></article>`).join('');}

  function setupFilters(){const nav=document.getElementById('sectionNav');if(!nav)return;nav.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{nav.querySelectorAll('[data-filter]').forEach(btn=>{btn.classList.remove('active');btn.setAttribute('aria-selected','false')});button.classList.add('active');button.setAttribute('aria-selected','true');currentFilter=button.dataset.filter||'all';const draw=()=>{renderHero(currentFilter);renderGrid(currentFilter)};if(document.startViewTransition)document.startViewTransition(draw);else draw();history.pushState({filter:currentFilter},'',currentFilter==='all'?location.pathname+location.search:`#${encodeURIComponent(currentFilter)}`);}));}
  function setupDarkMode(){const root=document.body,saved=localStorage.getItem('nashhal-theme');if(saved==='dark'||(!saved&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches))root.classList.add('dark');const toggle=document.getElementById('darkToggle');if(toggle)toggle.addEventListener('click',()=>{root.classList.toggle('dark');localStorage.setItem('nashhal-theme',root.classList.contains('dark')?'dark':'light')});}
  function setupSearch(){const button=document.getElementById('searchToggle'),panel=document.getElementById('searchPanel'),form=document.getElementById('searchForm'),input=document.getElementById('searchInput');if(!button||!panel||!form||!input)return;button.addEventListener('click',()=>{panel.classList.toggle('open');if(panel.classList.contains('open'))requestAnimationFrame(()=>input.focus())});}
  function registerPWA(){const manifest=document.createElement('link');manifest.rel='manifest';manifest.href='manifest.webmanifest?v=10';document.head.appendChild(manifest);if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js?v=10',{updateViaCache:'none'}).then(reg=>reg.update()).catch(err=>console.warn('SW',err)));}
  function dataSignature(items){
    return items.map(item => [
      item.id,item.title,item.published,item.status,item.confidence,item.category,item.image
    ].join('|')).join('||');
  }

  function renderAll(options = {}){
    const signature = dataSignature(allItems);
    if (!options.force && signature === lastRenderSignature) return false;

    const preserveScroll = options.preserveScroll !== false;
    const scrollY = preserveScroll ? window.scrollY : 0;
    const active = document.activeElement;
    const activeId = active && active.id ? active.id : '';

    renderTicker();
    renderHero(currentFilter);
    renderGrid(currentFilter);
    renderVerify();
    lastRenderSignature = signature;
    window.dispatchEvent(new CustomEvent('nashhal-data-ready',{detail:allItems}));

    if (preserveScroll) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo({top:scrollY,left:0,behavior:'auto'});
          if(activeId){
            const next=document.getElementById(activeId);
            if(next) try{next.focus({preventScroll:true});}catch(_){next.focus();}
          }
        });
      });
    }
    return true;
  }

  async function loadNews(force=false){
    let cached=null;
    if(!force){
      try{cached=JSON.parse(localStorage.getItem(CACHE_KEY)||'null')}catch(_){ }
    }

    if(Array.isArray(cached)&&cached.length){
      allItems=cached.map(normalize).filter(item=>item.title);
      renderAll({preserveScroll:false});
    }

    try{
      const url=`${DATA_URL}${force?'?t=':'?v='}${Date.now()}`;
      const response=await fetch(url,{cache:'no-store'});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const data=await response.json();
      const raw=Array.isArray(data)?data:(data.items||data.news||[]);
      const nextItems=raw.map(normalize).filter(item=>item.title);
      const changed=dataSignature(nextItems)!==dataSignature(allItems);
      allItems=nextItems;
      localStorage.setItem(CACHE_KEY,JSON.stringify(allItems));
      if(changed || force) renderAll({preserveScroll:true,force:true});
    }catch(error){
      console.error('News loading failed:',error);
      if(!allItems.length){
        const hero=document.getElementById('heroGrid');
        if(hero)hero.innerHTML='<div class="error-state">News are temporarily unavailable<div><button type="button" id="retryNews">Retry</button></div></div>';
        const retry=document.getElementById('retryNews');
        if(retry)retry.onclick=()=>{showSkeleton();loadNews(true)};
      }
    }
  }
  
  document.addEventListener('DOMContentLoaded',()=>{
    if('scrollRestoration' in history) history.scrollRestoration='manual';
    injectPerformanceCSS();
    showSkeleton();
    setupFilters();
    setupDarkMode();
    setupSearch();
    registerPWA();
    loadNews(false);
  });
})();
