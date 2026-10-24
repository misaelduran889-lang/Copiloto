// Service Worker mínimo: cachea la interfaz para abrir offline.
// NO cachea /api/* (esas respuestas deben ser siempre frescas).
const CACHE = "copiloto-v1";
const ASSETS = ["/", "/index.html", "/styles.css", "/app.js", "/manifest.json", "/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/")) return; // la red maneja la API
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
