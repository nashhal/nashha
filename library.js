(() => {
  'use strict';
  const DATA='data/library.json';
  const $=id=>document.getElementById(id);
  const state={items:[],filtered:[],visible:28,query:'',type:'',region:'',year:'',source:'',sort:'date-desc',collection:''};
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const dateValue=v=>{const d=Date.parse(v||'');return Number.isNaN(d)?0:d};
  const yearOf=v=>{const m=String(v||'').match(/\d{4}/);return m?m[0]:''};
  const searchText=x=>clean([x.title,x.description,x.source,x.region,x.location,(x.subjects||[]).join(' '),(x.people||[]).join(' '),(x.institutions||[]).join(' ')].join(' ')).toLowerCase();

  function unique(field){
    const vals=new Set();
    state.items.forEach(x=>{if(field==='year'){const y=yearOf(x.date);if(y)vals.add(y)}else{const v=clean(x[field]);if(v)vals.add(v)}});
    return [...vals].sort((a,b)=>field==='year'?b.localeCompare(a):a.localeCompare(b));
  }
  function fillSelect(id,vals,label){
    const el=$(id); el.innerHTML='<option value="">'+label+'</option>'+vals.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');
  }
  function renderCollections(data){
    const wrap=$('collections'); if(!wrap)return;
    const cols=Array.isArray(data.collections)?data.collections:[];
    wrap.innerHTML='<button class="collection-chip active" data-collection="">All Collections</button>'+cols.map(c=>'<button class="collection-chip" data-collection="'+esc(c.id)+'">'+esc(c.name)+' <span>'+Number(c.count||0)+'</span></button>').join('');
    wrap.querySelectorAll('[data-collection]').forEach(b=>b.addEventListener('click',()=>{
      wrap.querySelectorAll('[data-collection]').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');state.collection=b.dataset.collection||'';state.visible=28;apply();
    }));
    const cc=$('collectionCounts');
    if(cc)cc.innerHTML=cols.map(c=>'<div class="collection-count"><strong>'+esc(c.name)+'</strong><span>'+Number(c.count||0)+'</span></div>').join('');
  }
  function relevanceScore(x){
    if(!state.query)return 0;
    const q=state.query.toLowerCase().split(/\s+/).filter(w=>w.length>1);
    const t=searchText(x);
    return q.reduce((n,w)=>n+(t.includes(w)?(t.startsWith(w)?4:2):0),0);
  }
  function matches(x){
    if(state.type && x.type!==state.type)return false;
    if(state.region && x.region!==state.region)return false;
    if(state.year && yearOf(x.date)!==state.year)return false;
    if(state.source && x.source!==state.source)return false;
    if(state.collection && x.collection!==state.collection)return false;
    if(state.query){
      const q=state.query.toLowerCase();
      if(!searchText(x).includes(q) && relevanceScore(x)<2)return false;
    }
    return true;
  }
  function apply(){
    state.filtered=state.items.filter(matches);
    state.filtered.sort((a,b)=>{
      if(state.sort==='date-asc')return dateValue(a.date)-dateValue(b.date);
      if(state.sort==='title-asc')return clean(a.title).localeCompare(clean(b.title));
      if(state.sort==='relevance'){const d=relevanceScore(b)-relevanceScore(a);return d||dateValue(b.date)-dateValue(a.date)}
      return dateValue(b.date)-dateValue(a.date);
    });
    render();
  }
  function render(){
    const count=$('resultCount'); if(count)count.textContent=state.filtered.length+' records';
    const stateEl=$('state'); if(stateEl)stateEl.textContent=(state.query?'Search «'+state.query+'» · ':'')+(state.filtered.length+' matching records');
    const root=$('records');
    if(!state.filtered.length){root.innerHTML='<div class="empty-records">No records match the current archive filters.</div>';$('loadMore').hidden=true;return}
    const shown=state.filtered.slice(0,state.visible);
    root.innerHTML=shown.map(x=>{
      const y=yearOf(x.date);
      return '<article class="record"><div class="record-year">'+esc(y||'—')+'<div class="record-type">'+esc(x.type||'record')+'</div></div><div class="record-main"><div class="record-kicker">'+(x.collection_name?'<span>'+esc(x.collection_name)+'</span>':'')+'<span>·</span><span>'+esc(x.region||'Southern Yemen')+'</span></div><h3 class="record-title"><a href="'+esc(x.page_url||('library/item/'+encodeURIComponent(x.id)+'.html'))+'">'+esc(x.title)+'</a></h3><p class="record-desc">'+esc(x.description||'Archive record preserved for research and reference.')+'</p><div class="record-meta"><span class="badge">'+esc(x.language||'English')+'</span><span>'+esc(x.source||'Unknown source')+'</span>'+(x.verification?'<span>·</span><span>'+esc(x.verification)+'</span>':'')+'</div></div><div class="record-source"><span>Source</span><strong>'+esc(x.source||'Archive record')+'</strong>'+(x.source_url?'<a href="'+esc(x.source_url)+'" target="_blank" rel="noopener noreferrer">Original source ↗</a>':'')+'</div></article>';
    }).join('');
    $('loadMore').hidden=state.visible>=state.filtered.length;
  }
  function bind(){
    $('librarySearchButton').addEventListener('click',()=>{state.query=clean($('libraryQuery').value);state.sort=$('sortFilter').value;state.visible=28;apply()});
    $('libraryQuery').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();state.query=clean(e.currentTarget.value);state.visible=28;apply()}});
    [['typeFilter','type'],['regionFilter','region'],['yearFilter','year'],['sourceFilter','source'],['sortFilter','sort']].forEach(([id,key])=>$(id).addEventListener('change',e=>{state[key]=e.target.value;state.visible=28;apply()}));
    $('loadMore').addEventListener('click',()=>{state.visible+=28;render()});
  }
  fetch(DATA+'?v='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(new Error('Library unavailable'))).then(data=>{
    state.items=Array.isArray(data.items)?data.items:[];
    renderCollections(data);
    fillSelect('typeFilter',unique('type'),'All types');
    fillSelect('regionFilter',unique('region'),'All regions');
    fillSelect('yearFilter',unique('year'),'All years');
    fillSelect('sourceFilter',unique('source'),'All sources');
    const stats=data.stats||{};
    $('statline').innerHTML='<span>'+Number(stats.total_records||state.items.length)+' records</span><span>'+Number(stats.sources||unique('source').length)+' sources</span><span>'+Number(stats.regions||unique('region').length)+' regions</span>';
    bind();
    apply();
  }).catch(err=>{$('records').innerHTML='<div class="empty-records">The archive data could not be loaded.</div>';$('state').textContent='Archive unavailable';console.error(err)});
})();