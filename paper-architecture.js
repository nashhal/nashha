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

  let observer = null;
  function observePaperParts() {
    const targets = document.querySelectorAll('.paper-section,.news-card,.rail-item');
    if (!('IntersectionObserver' in window)) {
      targets.forEach(el => el.classList.add('is-visible'));
      return;
    }
    if (!observer) {
      observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: .08, rootMargin: '0px 0px -5% 0px' });
    }
    targets.forEach(el => {
      if (!el.classList.contains('is-visible')) observer.observe(el);
    });
  }

  const refreshObserver = () => window.requestAnimationFrame(observePaperParts);

  window.addEventListener('nashhal-data-ready', refreshObserver, { passive:true });
  window.addEventListener('load', refreshObserver, { passive:true });

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

  // No pointer-follow transforms: the newspaper should remain visually stable while reading.
})();
