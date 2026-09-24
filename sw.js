/* TEGA'S EDGE service worker — app shell caching.
 * v3 (2026-09-24): the HTML shell document is NETWORK-FIRST so UI fixes reach
 * users on their next visit. v2 was cache-first for the shell, which served a
 * stale index.html indefinitely after the sort controls were restored — the
 * root cause of the "missing sort button" report. Icons/webmanifest stay
 * cache-first (immutable assets). ALL *.json data files are network-only and
 * never cached: the dashboard must never show a cached run as if it were
 * fresh. */
var CACHE = 'edge-shell-v3';
var SHELL = [
  './',
  './index.html',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
  './manifest.webmanifest'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE && k.indexOf('edge-shell-') === 0; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

function isShellDocument(url) {
  return /(^|\/)index\.html$/.test(url.pathname) || /\/$/.test(url.pathname);
}

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  // Data files: network-only, never cached, never served from cache.
  if (/\.json(\?|$)/.test(url.pathname)) return;
  if (e.request.mode === 'navigate' || isShellDocument(url)) {
    // Shell document: network-first so UI updates land on the next visit;
    // cache fallback keeps the app working offline.
    e.respondWith(
      fetch(e.request).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      }).catch(function () {
        return caches.match(e.request, { ignoreSearch: true });
      })
    );
    return;
  }
  // Immutable assets: cache-first.
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(function (hit) {
      if (hit) return hit;
      return fetch(e.request).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      });
    })
  );
});
