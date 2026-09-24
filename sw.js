/* SPORTY TEGA service worker.
   Cache-first for the app shell; network-only for ALL *.json (never cached).
   Cache name: sporty-shell-v1. Progressive enhancement: no SW => everything still works. */
var CACHE = "sporty-shell-v1";
var SHELL = ["./", "index.html", "icon-180.png", "icon-192.png", "icon-512.png", "manifest.webmanifest"];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
      .then(function () { return self.skipWaiting(); })
      .catch(function () {})
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k !== CACHE && k.indexOf("sporty-shell-") === 0; })
          .map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var url;
  try { url = new URL(e.request.url); } catch (err) { return; }
  if (e.request.method !== "GET") return;
  // JSON is live data: never serve from cache, never store in cache.
  if (/\.json(\?|$)/.test(url.pathname)) return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(function (hit) {
      if (hit) return hit;
      return fetch(e.request).then(function (resp) {
        var copy = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); }).catch(function () {});
        return resp;
      }).catch(function () {
        return caches.match("index.html");
      });
    })
  );
});
