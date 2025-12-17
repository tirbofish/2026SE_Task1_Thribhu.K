const STATIC_PREFIX = "/static/";

const assets = [
  "/",
  STATIC_PREFIX + "css/style.css",
  STATIC_PREFIX + "css/bootstrap.min.css",
  STATIC_PREFIX + "js/bootstrap.bundle.min.js",
  STATIC_PREFIX + "js/app.js",
  STATIC_PREFIX + "images/logo.png",
  STATIC_PREFIX + "images/favicon.jpg",
  STATIC_PREFIX + "icons/icon-128x128.png",
  STATIC_PREFIX + "icons/icon-192x192.png",
  STATIC_PREFIX + "icons/icon-384x384.png",
  STATIC_PREFIX + "icons/icon-512x512.png",
  STATIC_PREFIX + "icons/desktop_screenshot.png",
  STATIC_PREFIX + "icons/mobile_screenshot.png",
];

const CATALOGUE_ASSETS = "catalogue-assets";

self.addEventListener("install", (installEvt) => {
  installEvt.waitUntil(
    caches
      .open(CATALOGUE_ASSETS)
      .then((cache) => {
        return cache.addAll(assets);
      })
      .then(() => self.skipWaiting())
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
            if (key !== CATALOGUE_ASSETS) return caches.delete(key);
            return undefined;
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
});