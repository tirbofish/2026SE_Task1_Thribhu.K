const staticAddr = window.STATIC_ADDRESS;

const assets = [
    "/",
    staticAddr + "css/style.css",
    staticAddr + "css/bootstrap.min.css",
    staticAddr + "js/bootstrap.bundle.min.js",
    staticAddr + "js/app.js",
    staticAddr + "images/logo.png",
    staticAddr + "images/favicon.jpg",
    staticAddr + "icons/icon-128x128.png",
    staticAddr + "icons/icon-192x192.png",
    staticAddr + "icons/icon-384x384.png",
    staticAddr + "icons/icon-512x512.png",
    staticAddr + "icons/desktop_screenshot.png",
    staticAddr + "icons/mobile_screenshot.png"
  ];

const CATALOGUE_ASSETS = "catalogue-assets";

self.addEventListener("install", (installEvt) => {
  installEvt.waitUntil(
    caches
      .open(CATALOGUE_ASSETS)
      .then((cache) => {
        console.log(cache)
        cache.addAll(assets);
      })
      .then(self.skipWaiting())
      .catch((e) => {
        console.log(e);
      })
  );
});

self.addEventListener("activate", function (evt) {
  evt.waitUntil(
    caches
      .keys()
      .then((keyList) => {
        return Promise.all(
          keyList.map((key) => {
            if (key === CATALOGUE_ASSETS) {
              console.log("Removed old cache from", key);
              return caches.delete(key);
            }
          })
        );
      })
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", function (evt) {
  evt.respondWith(
    fetch(evt.request).catch(() => {
      return caches.open(CATALOGUE_ASSETS).then((cache) => {
        return cache.match(evt.request);
      });
    })
  );
})