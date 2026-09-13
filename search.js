/* Client-side search: debounce, local filtering and safe highlighting. */
(function(){'use strict';
  let items=[]; let timer=null;
  const clean=v=>String(v||'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
  const esc=v=>String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const articleUrl=item=>`articles/${encodeURIComponent(item.id)}.html`;
  function highlight(text,q){
    const value=clean(text); if(!q)return esc(value);
    const safe=q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const re=new RegExp(`(${safe})`,'ig'); let out='',last=0,m;
    while((m=re.exec(value))){out+=esc(value.slice(last,m.index))+`<mark>${esc(m[0])}</mark>`;last=m.index+m[0].length;}
    return out+esc(value.slice(last));
  }
  function render(q){
    const root=document.getElementById('searchResults'); if(!root)return;
    q=clean(q); if(!q){root.innerHTML='';return;}
    const needle=q.toLocaleLowerCase('ar');
    const matches=items.filter(item=>`${item.title} ${item.summary}`.toLocaleLowerCase('ar').includes(needle)).slice(0,10);
    root.innerHTML=matches.length?matches.map(item=>`<a href="${articleUrl(item)}" data-news-id="${esc(item.id)}"><strong>${highlight(item.title,q)}</strong><small>${esc(item.category)} · ${esc(item.sourceName||'نشهل')}</small></a>`).join(''):'<div class="search-empty">لا توجد نتائج مطابقة · جرّب كلمات أخرى</div>';
  }
  function init(){
    const toggle=document.getElementById('searchToggle'),panel=document.getElementById('searchPanel'),input=document.getElementById('searchInput'),form=document.getElementById('searchForm');
    if(toggle&&panel&&input){toggle.addEventListener('click',()=>{panel.classList.toggle('open');if(panel.classList.contains('open'))requestAnimationFrame(()=>input.focus())});input.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>render(input.value),280)});}
    if(form)form.addEventListener('submit',e=>{e.preventDefault();render(input.value);});
    window.addEventListener('nashhal-data-ready',e=>{items=Array.isArray(e.detail)?e.detail:[];render(input?input.value:'');});
  }
  document.addEventListener('DOMContentLoaded',init);
})();
