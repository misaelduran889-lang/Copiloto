const CACHE="copiloto-v1";
const ASSETS=["./","./index.html","./manifest.json","./icon.svg"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  // No cachear llamadas a IA ni a Wikipedia (deben ir a la red)
  if(u.hostname!==location.hostname) return;
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});
