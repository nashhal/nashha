const CACHE='nashhal-shell-v1';
const DATA='nashhal-data-v1';
const SHELL=['./','./index.html','./article.html','./language.js','./news-loader.js','./logo.jpg','./manifest.webmanifest'];

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
      const cached=await caches.match(event.request);
      if(cached) return cached;
      try{
        const response=await fetch(event.request);
        if(response.ok && (url.pathname.endsWith('.js')||url.pathname.endsWith('.css')||url.pathname.endsWith('.html')||url.pathname.endsWith('.jpg')||url.pathname.endsWith('.webmanifest'))){
          const cache=await caches.open(CACHE); cache.put(event.request,response.clone());
        }
        return response;
      }catch(_){ return cached || Response.error(); }
    })());
  }
});
