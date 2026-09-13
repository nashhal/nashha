const CACHE='nashhal-shell-v3';
const DATA='nashhal-data-v2';
const SHELL=['./','./index.html','./article.html','./about.html','./editorial-policy.html','./ai-policy.html','./corrections.html','./language.js','./global-ui.js','./news-loader.js','./bilingual-news.js','./logo.jpg','./manifest.webmanifest'];

self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>![CACHE,DATA].includes(k)).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});

self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET') return;

  if(url.pathname.endsWith('/data/news.json')){
    event.respondWith((async()=>{
      const cache=await caches.open(DATA);
      const cached=await cache.match(event.request);
      const network=fetch(event.request,{cache:'no-store'}).then(response=>{
        if(response.ok) cache.put(event.request,response.clone());
        return response;
      }).catch(()=>cached);
      return cached || network;
    })());
    return;
  }

  if(url.origin===self.location.origin){
    event.respondWith((async()=>{
      try{
        const response=await fetch(event.request);
        const path=url.pathname;
        const cacheable=/\.(js|css|html|jpg|jpeg|png|webp|webmanifest)$/.test(path);
        if(response.ok&&cacheable){
          const cache=await caches.open(CACHE);
          cache.put(event.request,response.clone());
        }
        return response;
      }catch(_){
        return (await caches.match(event.request)) || Response.error();
      }
    })());
  }
});
