// Installable shell only. Never cache /v1 API or personal research data.
const CACHE = 'swing-static-v011';
const ASSETS = ['/', '/static/styles.css', '/static/app.js', '/static/manifest.webmanifest', '/static/icon-192.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('swing-static-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if(event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/v1/') || url.pathname.startsWith('/health/') || url.pathname === '/api-docs') return;
  if(!ASSETS.includes(url.pathname)) return;
  event.respondWith(fetch(event.request).then(response => {
    if(response.ok){const copy=response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, copy));}
    return response;
  }).catch(() => caches.match(event.request)));
});
