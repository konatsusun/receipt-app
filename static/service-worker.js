self.addEventListener('install', function(event) {
  console.log('SWきたよーん🛎️');
});

self.addEventListener('fetch', function(event) {
  event.respondWith(fetch(event.request));
});
