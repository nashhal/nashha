(function(){'use strict';
const KEY='nashhal-language';
let lang=localStorage.getItem(KEY)||'ar';
const dict={
 ar:{
  search:'بحث',searchPlaceholder:'ابحث في أخبار الصحيفة',searchButton:'بحث',lang:'English',
  nav:['الرئيسية','الجنوب','عدن','حضرموت','شبوة','أبين','لحج','الضالع','المهرة','سقطرى','اليمن'],
  sectionMeta:'خبر · مصدر · تحقق',breaking:'عاجل',latest:'أحدث الأخبار',
  latestMeta:'تغطية مستمرة · المصدر الأصلي · حالة التحقق',
  edition:'إصدار رقمي',daily:'النشرة اليومية',trust:'سجل التوثيق',about:'عن الصحيفة',
  newspaper:'صحيفة الثورة الجنوبية',subtitle:'أخبار الجنوب واليمن',
  trustTitle:'سجل الصحيفة',trustMeta:'شفافية المصدر وحالة النشر',
  review:'رصد قيد التحقق',reviewMeta:'لا يظهر كخبر منشور حتى تتوفر معطيات كافية',
  footerNews:'الصحيفة',footerTransparency:'الشفافية'
 },
 en:{
  search:'Search',searchPlaceholder:'Search the newspaper',searchButton:'Search',lang:'العربية',
  nav:['Home','South','Aden','Hadramout','Shabwah','Abyan','Lahj','Al Dhale’e','Al Mahrah','Socotra','Yemen'],
  sectionMeta:'News · Source · Verification',breaking:'BREAKING',latest:'Latest News',
  latestMeta:'Continuous coverage · Original source · Verification status',
  edition:'Digital edition',daily:'Daily bulletin',trust:'Verification log',about:'About',
  newspaper:'Southern Revolution Newspaper',subtitle:'South Yemen · Yemen',
  trustTitle:'Newspaper Record',trustMeta:'Source transparency and publication status',
  review:'Monitoring under review',reviewMeta:'Not treated as published news until sufficient evidence is available',
  footerNews:'Newspaper',footerTransparency:'Transparency'
 }
};
function q(sel){return document.querySelector(sel)}
function setText(sel,value){document.querySelectorAll(sel).forEach(e=>e.textContent=value)}
function nav(){
 const navEl=document.getElementById('sectionNav'); if(!navEl)return;
 const buttons=navEl.querySelectorAll('button[data-filter]');
 buttons.forEach((b,i)=>{if(dict[lang].nav[i])b.textContent=dict[lang].nav[i]});
 const more=navEl.querySelector('.nav-more'); if(more)more.textContent=lang==='ar'?'بحث موسع':'Advanced Search';
}
function apply(){
 document.documentElement.lang=lang;
 document.documentElement.dir=lang==='ar'?'rtl':'ltr';
 const d=dict[lang];
 const st=q('#searchToggle'); if(st){st.textContent=d.search;st.setAttribute('aria-label',d.search)}
 const sb=q('#searchForm button'); if(sb)sb.textContent=d.searchButton;
 const si=q('#searchInput'); if(si)si.placeholder=d.searchPlaceholder;
 const lb=q('#langToggle'); if(lb)lb.textContent=d.lang;
 const meta=q('#sectionMeta'); if(meta)meta.textContent=d.sectionMeta;
 const br=q('#breakingLabelText'); if(br)br.textContent=d.breaking;
 const heading=q('#gridTitle'); if(heading&&!heading.dataset.dynamic)heading.textContent=d.latest;
 const sm=q('#sectionMeta'); if(sm)sm.textContent=d.latestMeta;
 setText('.edition span',d.edition);
 setText('.utility-links a:nth-child(1)',d.daily);
 setText('.utility-links a:nth-child(2)',d.trust);
 setText('.utility-links a:nth-child(3)',d.about);
 setText('.edition strong',d.newspaper);
 setText('.mast-en','SOUTHERN REVOLUTION NEWSPAPER');
 setText('.trust-panel .section-head h2',d.trustTitle);
 setText('.trust-panel .section-head p',d.trustMeta);
 setText('.verify-head h2',d.review);
 setText('.verify-head p',d.reviewMeta);
 setText('.footer-grid > div:nth-child(2) h3',d.footerNews);
 setText('.footer-grid > div:nth-child(3) h3',d.footerTransparency);
 const m=q('meta[name="description"]');
 if(m)m.content=lang==='ar'?'صحيفة الثورة الجنوبية — أخبار الجنوب واليمن مع متابعة المصدر وحالة التحقق.':'Southern Revolution Newspaper — South Yemen and Yemen news with source and verification context.';
 document.title=lang==='ar'?'صحيفة الثورة الجنوبية | أخبار الجنوب واليمن':'Southern Revolution Newspaper | South Yemen & Yemen News';
 nav();
 window.dispatchEvent(new CustomEvent('nashhal-language-change',{detail:{lang}}));
}
window.NashhalLang={get:()=>lang,toggle:()=>{lang=lang==='ar'?'en':'ar';localStorage.setItem(KEY,lang);apply()}};
document.addEventListener('DOMContentLoaded',()=>{const b=q('#langToggle');if(b)b.addEventListener('click',()=>window.NashhalLang.toggle());apply()});
})();