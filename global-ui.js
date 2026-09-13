(function () {
  'use strict';

  const sections = [
    ['all', 'الرئيسية'],
    ['اليمن', 'اليمن'],
    ['العالم العربي', 'العالم العربي'],
    ['الخليج', 'الخليج'],
    ['العالم', 'العالم'],
    ['اقتصاد', 'اقتصاد'],
    ['تقنية', 'تقنية'],
    ['علوم', 'علوم']
  ];

  function applyGlobalIdentity() {
    document.title = 'نشهل | منصة أخبار عربية وعالمية';
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.content = 'نشهل منصة أخبار عربية وعالمية تتابع التطورات العربية والدولية مع اهتمام خاص باليمن والجنوب.';

    const top = document.querySelector('.top .wrap > div:first-child');
    if (top) top.textContent = 'نشهل · منصة أخبار عربية وعالمية';

    const mast = document.querySelector('.mast');
    if (mast) mast.innerHTML = '<strong>نشهل</strong>العالم العربي · التطورات الدولية';

    const brandSub = document.querySelector('.brand-sub');
    if (brandSub) brandSub.textContent = 'خبر · سياق · تحليل';

    const panel = document.querySelector('.panel-head span');
    if (panel) panel.textContent = 'تحديث مستمر · تغطية عربية وعالمية';

    const about = document.querySelector('.info-card:first-child p');
    if (about) about.textContent = 'تكتشف نشهل التطورات من مصادر مفتوحة ومتنوعة، ثم تمررها عبر طبقة تحقق وتحليل آلي قبل صياغتها ونشرها، مع فصل واضح بين الخبر المؤكد والرصد قيد المتابعة.';
  }

  function remapControls() {
    const nav = document.getElementById('sectionNav');
    if (nav) {
      const buttons = nav.querySelectorAll('button');
      buttons.forEach((button, index) => {
        const entry = sections[index];
        if (!entry) return;
        button.dataset.filter = entry[0];
        button.textContent = entry[1];
      });
      if (!nav.querySelector('.active')) {
        const first = nav.querySelector('button');
        if (first) first.classList.add('active');
      }
    }

    const sectionLinks = document.querySelectorAll('.section-list a');
    sectionLinks.forEach((link, index) => {
      const entry = sections[index + 1];
      if (!entry) return;
      link.textContent = entry[1];
      link.href = '#south';
      link.dataset.filter = entry[0];
      link.addEventListener('click', function (event) {
        const navButton = document.querySelector(`#sectionNav button[data-filter="${CSS.escape(entry[0])}"]`);
        if (navButton) navButton.click();
        event.preventDefault();
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyGlobalIdentity();
    remapControls();
  });
})();
