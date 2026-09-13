/* Nashhal news engine
   Event-first publishing, verification-first UX, performant client rendering.
*/
(function () {
  'use strict';

  const DATA_URL = 'data/news.json';
  const CACHE_KEY = 'nashhal-news-cache-v3';
  const GRID_LIMIT = 12;
  const VERIFY_LIMIT = 6;
  const TICKER_LIMIT = 8;
  const CURRENT_HOURS = 72;
  const CITY_TERMS = ['عدن','حضرموت','شبوة','أبين','لحج','الضالع','المهرة','سقطرى'];
  const platformLabel = { X: 'رصد اجتماعي', Facebook: 'رصد اجتماعي' };
  let allItems = [];
  let currentFilter = 'all';

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
    if (min < 1) return 'الآن';
    if (min < 60) return `قبل ${min} دقيقة`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `قبل ${hr} ساعة`;
    return `قبل ${Math.floor(hr / 24)} يوم`;
  }

  function isCurrent(item) {
    const published = Date.parse(item.published);
    if (Number.isNaN(published)) return false;
    return (Date.now() - published) <= CURRENT_HOURS * 3600000 + 600000;
  }

  function normalize(item = {}, index = 0) {
    const title = clean(item.title || item.headline || '');
    const summary = clean(item.summary || item.description || '');
    const sourceName = clean(item.source_name || item.source || item.publisher || '');
    const sourceUrl = safeUrl(item.source_url || item.link || item.url || '#');
    const published = item.published || item.published_at || item.pubDate || item.date || '';
    const category = clean(item.category || item.region || 'اليمن');
    const text = `${title} ${summary}`.toLowerCase();
    const city = CITY_TERMS.find(term => text.includes(term.toLowerCase())) || '';
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

  const confirmed = item => item.status === 'published' && ['high', 'medium'].includes(item.confidence) && isCurrent(item);
  const review = item => ['review', 'developing_review'].includes(item.status) || item.verification === 'unconfirmed';
  const sortRecent = items => [...items].sort((a, b) => (Date.parse(b.published) || 0) - (Date.parse(a.published) || 0));
  const confirmedItems = (filter = 'all') => {
    let items = allItems.filter(confirmed);
    if (filter !== 'all') items = items.filter(item => item.category === filter || item.city === filter);
    return sortRecent(items);
  };
  const metaLine = item => `<div class="meta-line"><span>${escapeHtml(item.category)}</span><span class="dot"></span><span>${escapeHtml(timeAgo(item.published))}</span></div>`;
  const placeholder = (label = 'نشهل') => `<div class="media-ph"><span>${escapeHtml(label)}</span></div>`;
  const media = (item, klass = '') => item.image ? `<img class="${klass}" src="${escapeHtml(item.image)}" alt="" ${klass.includes('hero') ? 'fetchpriority="high" decoding="async"' : 'loading="lazy" decoding="async"'} referrerpolicy="no-referrer">` : placeholder('نشهل');

  function injectPerformanceCSS() {
    if (document.getElementById('nashhal-perf-css')) return;
    const style = document.createElement('style'); style.id = 'nashhal-perf-css';
    style.textContent = `.news-skeleton{display:grid;gap:10px;padding:18px;background:var(--paper);border:1px solid var(--line)}.sk{background:linear-gradient(90deg,var(--soft) 25%,rgba(255,255,255,.55) 50%,var(--soft) 75%);background-size:200% 100%;animation:nashhalShimmer 1.25s linear infinite;border-radius:4px}.sk.h{height:260px}.sk.t{height:24px;width:78%}.sk.s{height:15px;width:92%}.sk.m{height:13px;width:60%}@keyframes nashhalShimmer{to{background-position:-200% 0}}.trust-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:0;background:var(--paper);border:1px solid var(--line);margin:0 0 20px}.trust-strip a,.trust-strip div{padding:14px;border-left:1px solid var(--line);font:700 10px/1.7 'IBM Plex Sans Arabic';color:var(--ink)}.trust-strip a:last-child,.trust-strip div:last-child{border-left:0}.trust-strip strong{display:block;color:var(--green);font-size:12px;margin-bottom:3px}.verify-live{display:inline-flex;align-items:center;gap:5px}.verify-live i{width:6px;height:6px;border-radius:50%;background:#18794e}@media(max-width:650px){.trust-strip{grid-template-columns:1fr 1fr}.trust-strip a,.trust-strip div{border-bottom:1px solid var(--line)}}@media(prefers-reduced-motion:reduce){.sk{animation:none}.ticker-track,.live-dot{animation:none!important}}`;
    document.head.appendChild(style);
  }

  function showSkeleton() {
    const hero = document.getElementById('heroGrid'), grid = document.getElementById('newsGrid');
    if (hero && !hero.children.length) hero.innerHTML = '<div class="news-skeleton"><div class="sk h"></div><div class="sk t"></div><div class="sk s"></div><div class="sk m"></div></div>';
    if (grid && !grid.children.length) grid.innerHTML = Array.from({length:6},()=>'<div class="news-skeleton"><div class="sk h" style="height:150px"></div><div class="sk t"></div><div class="sk s"></div></div>').join('');
  }

  function injectTrustStrip() {
    const hero = document.getElementById('heroGrid');
    if (!hero || document.getElementById('nashhal-trust-strip')) return;
    const strip = document.createElement('section'); strip.id = 'nashhal-trust-strip'; strip.className = 'wrap trust-strip';
    strip.innerHTML = '<div><strong>الحدث أولًا</strong>نبحث عن الحدث نفسه لا عن عناوين القنوات</div><div><strong>التحقق أولًا</strong>نفصل بين الوقائع والادعاءات وما لم يثبت</div><a href="editorial-policy.html"><strong>سياسة التحرير</strong>معايير واضحة للدقة والتصحيح</a><a href="ai-policy.html"><strong>استخدام AI</strong>الذكاء الاصطناعي أداة مساعدة لا بديلًا عن التحقق</a>';
    hero.parentElement.insertBefore(strip, hero);
  }

  function renderTicker(){const track=document.getElementById('tickerTrack');if(!track)return;const items=confirmedItems().slice(0,TICKER_LIMIT);track.innerHTML=items.length?items.map(item=>`<a class="ticker-item" href="${articleUrl(item)}"><strong>تحديث</strong><span>${escapeHtml(item.title)}</span><small>${escapeHtml(timeAgo(item.published))}</small></a>`).join(''):'<span class="ticker-item">لا توجد تحديثات موثقة جديدة حاليًا</span>';}

  function renderHero(filter='all'){const root=document.getElementById('heroGrid');if(!root)return;const items=confirmedItems(filter);if(!items.length){root.innerHTML='<div class="empty-state">لا توجد أخبار منشورة حديثة في هذا القسم حاليًا</div>';return;}const main=items[0],rail=items.slice(1,5);root.innerHTML=`<article class="hero-main"><a class="hero-media" href="${articleUrl(main)}">${media(main,'hero-photo')}</a><div class="hero-body"><span class="kicker">${escapeHtml(main.category)}</span><h1><a href="${articleUrl(main)}">${escapeHtml(main.title)}</a></h1><p class="hero-summary">${escapeHtml(main.summary)}</p>${metaLine(main)}</div></article><aside class="hero-rail" aria-label="أحدث الأخبار">${rail.map((item,index)=>`<article class="rail-item"><div class="rail-index">0${index+1}</div><a class="rail-media" href="${articleUrl(item)}">${media(item,'rail-photo')}</a><div class="rail-content"><span class="kicker">${escapeHtml(item.category)}</span><h2><a href="${articleUrl(item)}">${escapeHtml(item.title)}</a></h2>${metaLine(item)}</div></article>`).join('')}</aside>`;}

  function renderGrid(filter='all'){const grid=document.getElementById('newsGrid'),title=document.getElementById('gridTitle');if(!grid)return;if(title)title.textContent=filter==='all'?'أحدث الأخبار':'أحدث أخبار '+filter;const items=confirmedItems(filter).slice(5,5+GRID_LIMIT);if(!items.length){grid.innerHTML='<div class="empty-state">لا مزيد من الأخبار المنشورة حاليًا</div>';return;}grid.innerHTML=items.map((item,index)=>`<article class="news-card ${index===0?'news-card-featured':''}"><a class="card-media" href="${articleUrl(item)}">${media(item,'card-photo')}<span class="card-tag">${escapeHtml(item.category)}</span></a><div class="card-body"><span class="kicker">${escapeHtml(item.category)}</span><h3><a href="${articleUrl(item)}">${escapeHtml(item.title)}</a></h3><p>${escapeHtml(item.summary)}</p>${metaLine(item)}</div></article>`).join('');}

  function renderVerify(){const wrap=document.getElementById('verifySection'),list=document.getElementById('verifyList');if(!wrap||!list)return;const items=sortRecent(allItems.filter(review)).slice(0,VERIFY_LIMIT);wrap.hidden=!items.length;list.innerHTML=items.map(item=>`<article class="verify-item"><span class="verify-badge">${escapeHtml(platformLabel[item.platform]||'قيد التحقق')}</span><div><h3><a href="${articleUrl(item)}">${escapeHtml(item.title)}</a></h3><div class="verify-meta">${escapeHtml(item.category)} · ${escapeHtml(timeAgo(item.published))}</div></div></article>`).join('');}

  function setupFilters(){const nav=document.getElementById('sectionNav');if(!nav)return;nav.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{nav.querySelectorAll('[data-filter]').forEach(btn=>btn.classList.remove('active'));button.classList.add('active');currentFilter=button.dataset.filter||'all';const draw=()=>{renderHero(currentFilter);renderGrid(currentFilter)};if(document.startViewTransition)document.startViewTransition(draw);else draw();}));}
  function setupDarkMode(){const root=document.body,saved=localStorage.getItem('nahshal-theme');if(saved==='dark')root.classList.add('dark');const toggle=document.getElementById('darkToggle');if(toggle)toggle.addEventListener('click',()=>{root.classList.toggle('dark');localStorage.setItem('nahshal-theme',root.classList.contains('dark')?'dark':'light')});}
  function setupSearch(){const button=document.getElementById('searchToggle'),panel=document.getElementById('searchPanel'),form=document.getElementById('searchForm'),input=document.getElementById('searchInput'),results=document.getElementById('searchResults');if(!button||!panel||!form||!input||!results)return;button.addEventListener('click',()=>{panel.classList.toggle('open');if(panel.classList.contains('open'))requestAnimationFrame(()=>input.focus())});form.addEventListener('submit',event=>{event.preventDefault();const q=clean(input.value).toLowerCase();const matches=confirmedItems().filter(item=>`${item.title} ${item.summary} ${item.category}`.toLowerCase().includes(q)).slice(0,8);results.innerHTML=q&&matches.length?matches.map(item=>`<a href="${articleUrl(item)}">${escapeHtml(item.title)}</a>`).join(''):(q?'<span>لا توجد نتائج مطابقة</span>':'');});}
  function setupLanguage(){window.addEventListener('nashhal-language-change',()=>{renderTicker();renderHero(currentFilter);renderGrid(currentFilter);renderVerify()});}
  function registerPWA(){const manifest=document.createElement('link');manifest.rel='manifest';manifest.href='manifest.webmanifest';document.head.appendChild(manifest);const theme=document.createElement('meta');theme.name='theme-color';theme.content='#0B2A4A';document.head.appendChild(theme);if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(err=>console.warn('SW',err)));}
  function renderAll(){injectTrustStrip();renderTicker();renderHero(currentFilter);renderGrid(currentFilter);renderVerify();}
  async function loadNews(){let cached=null;try{cached=JSON.parse(localStorage.getItem(CACHE_KEY)||'null')}catch(_){}if(Array.isArray(cached)&&cached.length){allItems=cached;renderAll()}try{const response=await fetch(DATA_URL,{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);const data=await response.json();const raw=Array.isArray(data)?data:(data.items||data.news||[]);allItems=raw.map(normalize).filter(item=>item.title);localStorage.setItem(CACHE_KEY,JSON.stringify(allItems));renderAll()}catch(error){console.error('تعذر تحميل الأخبار:',error);if(!allItems.length){allItems=[];renderAll()}}}
  document.addEventListener('DOMContentLoaded',()=>{injectPerformanceCSS();showSkeleton();setupFilters();setupDarkMode();setupSearch();setupLanguage();registerPWA();loadNews();});
})();
