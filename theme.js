/* Theme controller: dark mode with persistent preference and OS fallback. */
(function(){'use strict';
  const key='nashhal-theme';
  const root=document.documentElement;
  const button=()=>document.getElementById('darkToggle');
  function preferred(){
    const saved=localStorage.getItem(key);
    if(saved==='dark'||saved==='light') return saved;
    return window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
  }
  function apply(mode){root.classList.toggle('dark',mode==='dark');document.body.classList.toggle('dark',mode==='dark');localStorage.setItem(key,mode);const b=button();if(b)b.setAttribute('aria-pressed',String(mode==='dark'));}
  document.addEventListener('DOMContentLoaded',function(){apply(preferred());const b=button();if(b)b.addEventListener('click',()=>apply(root.classList.contains('dark')?'light':'dark'));});
})();
