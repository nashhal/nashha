/* News modal: accessible dialog, focus trap and shareable hash. */
(function(){'use strict';
  let items=[]; let opener=null;
  const $=id=>document.getElementById(id);
  const esc=v=>String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const urlId=()=>decodeURIComponent((location.hash||'').replace(/^#news-/,'')).trim();
  function find(id){return items.find(x=>String(x.id)===String(id));}
  function open(item,source){
    if(!item)return; const modal=$('newsModal'); if(!modal)return; opener=source||document.activeElement;
    $('modalKicker').textContent=item.category||'نشهل'; $('modalTitle').textContent=item.title||''; $('modalSummary').textContent=item.summary||'';
    $('modalStatus').textContent=item.platform==='X'||item.platform==='Facebook'?'◉ رصد · مادة قيد التحقق':item.status==='published'?'✓ خبر منشور':'◌ متابعة · قيد التحقق';
    $('modalMeta').innerHTML=[item.sourceName||'نشهل',item.published?new Date(item.published).toLocaleString('ar-SA',{dateStyle:'medium',timeStyle:'short'}):''].filter(Boolean).map(esc).map(v=>`<span>${v}</span>`).join('<span>·</span>');
    const sourceLink=$('modalSource'); sourceLink.href=item.sourceUrl||'#'; sourceLink.hidden=!item.sourceUrl||item.sourceUrl==='#';
    modal.classList.add('open'); document.body.style.overflow='hidden'; history.pushState({modal:item.id},'',`#news-${encodeURIComponent(item.id)}`); setTimeout(()=>$('modalClose').focus(),0);
  }
  function close(update=true){const modal=$('newsModal');if(!modal)return;modal.classList.remove('open');document.body.style.overflow='';if(update&&location.hash.startsWith('#news-'))history.pushState({},'',location.pathname+location.search);if(opener&&opener.focus)opener.focus();opener=null;}
  function trap(e){const modal=$('modalDialog');if(!$('newsModal').classList.contains('open'))return;if(e.key==='Escape'){e.preventDefault();close();return}if(e.key!=='Tab')return;const focusables=modal.querySelectorAll('button,a[href],input,textarea,select,[tabindex]:not([tabindex="-1"])');if(!focusables.length)return;const first=focusables[0],last=focusables[focusables.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}
  function init(){
    const modal=$('newsModal'); if(!modal)return;
    $('modalClose').addEventListener('click',()=>close()); modal.addEventListener('click',e=>{if(e.target===modal)close()}); document.addEventListener('keydown',trap);
    window.addEventListener('nashhal-data-ready',e=>{items=Array.isArray(e.detail)?e.detail:[];const id=urlId();if(id&&!location.hash.includes('#about')){const item=find(id);if(item)open(item,null);}});
    window.addEventListener('nashhal-open-news',e=>open(find(e.detail&&e.detail.id),e.detail&&e.detail.source)); window.addEventListener('popstate',()=>{const id=urlId();if(id){const item=find(id);if(item)open(item,null)}else if(modal.classList.contains('open'))close(false)});
    document.addEventListener('click',e=>{const trigger=e.target.closest('[data-news-id]');if(!trigger)return;e.preventDefault();window.dispatchEvent(new CustomEvent('nashhal-open-news',{detail:{id:trigger.dataset.newsId,source:trigger}}));});
  }
  document.addEventListener('DOMContentLoaded',init);
})();
