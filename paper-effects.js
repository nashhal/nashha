/* Southern Revolution Newspaper — Paper Edition motion layer */
(() => {
  const root = document.documentElement;
  const body = document.body;
  if (!body) return;

  root.classList.add('paper-edition');
  body.classList.add('paper-edition');

  const grain = document.createElement('div');
  grain.className = 'paper-grain-layer';
  grain.setAttribute('aria-hidden', 'true');
  body.appendChild(grain);

  const revealTargets = body.querySelectorAll(
    '.section, .hero-grid, .news-panel, .sidebar, .verify-panel, .article, .trust-panel, .box'
  );

  revealTargets.forEach((el, index) => {
    el.classList.add('paper-reveal');
    const slot = index % 4;
    if (slot) el.classList.add('paper-stagger-' + slot);
  });

  requestAnimationFrame(() => {
    root.classList.add('paper-ready');
    body.classList.add('paper-ready');
  });

  window.setTimeout(() => {
    body.classList.remove('paper-ready');
  }, 1400);
})();
