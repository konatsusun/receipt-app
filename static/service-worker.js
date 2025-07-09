const CACHE_NAME = 'receipt-app-cache-v1';
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/icon.png',
  '/static/icon-512.png',
  '/manifest.json',
];

// 🔹 install時にキャッシュ
self.addEventListener('install', function (event) {
  console.log('SW install ✅');
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(urlsToCache);
    })
  );
});

// 🔹 fetch時はキャッシュを使う
self.addEventListener('fetch', function (event) {
  event.respondWith(
    caches.match(event.request).then(function (response) {
      return response || fetch(event.request);
    })
  );
});
