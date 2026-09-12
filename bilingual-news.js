(function(){'use strict';
let cache=null;
async function data(){if(cache)return cache;try{const r=await fetch(`data/news.json?v=${Date.now()}`,{cache:'no-store'});const d=await r.json();cache=Array.isArray(d)?d:(d.items||d.news||[]);return cache}catch(_){cache=[];return cache}}
const clean=v=>String(v||'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
function setText(e,v){if(e&&v)e.textContent=v}
async function apply(){const lang=window.NashhalLang?NashhalLang.get():'ar';const items=(await data()).filter(x=>x&&x.status==='published'&&['high','medium'].includes(x.confidence));
const titleOf=x=>lang==='en'?(clean(x.title_en)||clean(x.title)):clean(x.title);const summaryOf=x=>lang==='en'?(clean(x.summary_en)||clean(x.summary)):clean(x.summary);
const hero=document.querySelector('#heroGrid .hero-main');if(hero&&items[0]){setText(hero.querySelector('h1 a'),titleOf(items[0]));setText(hero.querySelector('.hero-summary'),summaryOf(items[0]))}
const rails=[...document.querySelectorAll('#heroGrid .hero-rail .rail-item')];rails.forEach((e,i)=>{const x=items[i+1];if(!x)return;setText(e.querySelector('h2 a'),titleOf(x))});
const cards=[...document.querySelectorAll('#newsGrid .news-card')];cards.forEach((e,i)=>{const x=items[i+5];if(!x)return;setText(e.querySelector('h3 a'),titleOf(x));setText(e.querySelector('p'),summaryOf(x))});
const ticker=[...document.querySelectorAll('#tickerTrack .ticker-item span')];ticker.forEach((e,i)=>{const x=items[i];if(x)setText(e,titleOf(x))});
}
window.addEventListener('nashhal-language-change',apply);document.addEventListener('DOMContentLoaded',apply);})();