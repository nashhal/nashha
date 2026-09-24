/* Shared paper utility. Keeps article pages lightweight; homepage motion is handled by paper-architecture.js. */
(() => {
  'use strict';
  const root=document.documentElement;
  const body=document.body;
  if(!body)return;
  root.classList.add('paper-edition');
  body.classList.add('paper-edition');

  const mastBrand=document.querySelector('.mast-brand');
  if(mastBrand&&!mastBrand.querySelector('.southern-flag-badge')){
    const flag=document.createElement('a');
    flag.className='southern-flag-badge';
    flag.href='index.html';
    flag.setAttribute('aria-label','The Southern Revolution');
    const flagSrc=location.pathname.includes('/articles/')?'../southern-flag.svg':'southern-flag.svg';
    flag.innerHTML='<img src="'+flagSrc+'" alt="Southern flag">';
    mastBrand.insertBefore(flag,mastBrand.firstChild);
  }
})();
