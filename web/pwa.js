/*
 * PWA lifecycle for trusted HTTPS origins only.
 * On local development origins, retire *our* old worker and static cache so
 * browser restarts never mix legacy assets with the current app.js.
 * This reduces stale-asset risk; it is NOT malware detection or remediation.
 */
(() => {
  'use strict';
  if (!('serviceWorker' in navigator)) return;

  const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);
  const isLocal = LOCAL_HOSTS.has(window.location.hostname.toLowerCase());

  async function retireLocalPwa() {
    const registrations = await navigator.serviceWorker.getRegistrations();
    const owned = registrations.filter(registration =>
      [registration.active, registration.waiting, registration.installing].some(worker => {
        if (!worker || !worker.scriptURL) return false;
        try {
          const url = new URL(worker.scriptURL);
          return url.origin === window.location.origin && url.pathname === '/static/sw.js';
        } catch {
          return false;
        }
      })
    );
    await Promise.all(owned.map(registration => registration.unregister()));

    if ('caches' in window) {
      const names = await window.caches.keys();
      await Promise.all(names.filter(name => name.startsWith('swing-static-'))
        .map(name => window.caches.delete(name)));
    }
  }

  window.addEventListener('load', () => {
    if (isLocal) {
      retireLocalPwa().catch(error => console.warn('Local PWA cleanup failed:', error));
    } else if (window.location.protocol === 'https:') {
      navigator.serviceWorker.register('/static/sw.js')
        .catch(error => console.warn('PWA registration failed:', error));
    }
  }, {once: true});
})();
