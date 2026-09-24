/* The Southern Revolution — paper interaction layer */
(() => {
  'use strict';

  const body = document.body;
  const root = document.documentElement;
  if (!body) return;

  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const OPEN_KEY = 'southern-revolution-paper-open-v2';

  root.classList.add('paper-edition');
  body.classList.add('paper-edition');

  const finishOpening = () => {
    body.classList.remove('paper-boot');
    body.classList.add('paper-open-complete', 'paper-motion-ready');
    window.setTimeout(() => body.classList.remove('paper-open-complete'), 800);
    observePaperParts();
  };

  if (reduce || sessionStorage.getItem(OPEN_KEY) === '1') {
    finishOpening();
  } else {
    sessionStorage.setItem(OPEN_KEY, '1');
    window.setTimeout(finishOpening, 1180);
  }

  function observePaperParts() {
    if (!('IntersectionObserver' in window)) {
      document.querySelectorAll('.paper-section,.news-card,.rail-item').forEach(el => el.classList.add('is-visible'));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: .08, rootMargin: '0px 0px -5% 0px' });

    document.querySelectorAll('.paper-section,.news-card,.rail-item').forEach(el => {
      if (!el.classList.contains('is-visible')) observer.observe(el);
    });
  }

  const refreshObserver = () => window.requestAnimationFrame(observePaperParts);

  window.addEventListener('nashhal-data-ready', refreshObserver);
  window.addEventListener('load', refreshObserver);

  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link) return;
    if (link.target === '_blank' || link.hasAttribute('download')) return;

    const href = link.getAttribute('href') || '';
    if (!href.includes('articles/')) return;
    if (href.startsWith('#')) return;

    try {
      const url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (reduce) return;

      event.preventDefault();
      body.classList.add('paper-navigating-out');
      window.setTimeout(() => { window.location.href = url.href; }, 340);
    } catch (_) {}
  });

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-filter]');
    if (!button || reduce) return;
    body.classList.remove('paper-filter-in');
    body.classList.add('paper-filter-out');
    window.clearTimeout(body.__paperFilterTimer);
    body.__paperFilterTimer = window.setTimeout(() => {
      body.classList.remove('paper-filter-out');
      void document.body.offsetWidth;
      body.classList.add('paper-filter-in');
      refreshObserver();
      window.setTimeout(() => body.classList.remove('paper-filter-in'), 560);
    }, 220);
  }, true);

  const paper = document.querySelector('.paper-page');
  if (paper && !reduce && window.matchMedia('(pointer:fine)').matches) {
    let raf = 0;
    let px = 0;
    let py = 0;
    paper.addEventListener('pointermove', (event) => {
      const rect = paper.getBoundingClientRect();
      px = ((event.clientX - rect.left) / rect.width - .5) * 2;
      py = ((event.clientY - rect.top) / rect.height - .5) * 2;
      if (raf) return;
      raf = requestAnimationFrame(() => {
        paper.style.setProperty('--paper-mx', (px * 2).toFixed(2) + 'px');
        paper.style.setProperty('--paper-my', (py * 1.2).toFixed(2) + 'px');
        raf = 0;
      });
    });
    paper.addEventListener('pointerleave', () => {
      paper.style.setProperty('--paper-mx', '0px');
      paper.style.setProperty('--paper-my', '0px');
    });
  }

  const patchDynamicParts = () => {
    document.querySelectorAll('.news-card-new').forEach(el => {
      if (!el.dataset.paperPatched) {
        el.dataset.paperPatched = '1';
        el.classList.add('is-visible');
      }
    });
  };

  const mo = new MutationObserver(patchDynamicParts);
  mo.observe(document.body, { childList: true, subtree: true });
})();
