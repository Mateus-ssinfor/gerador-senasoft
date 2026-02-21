const CACHE = "senasoft-v1";
const ASSETS = [
  "/",
  "/static/app.css",
  "/static/app.js",
  "/static/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
  "/static/img/logo.png",
  "/static/img/s.png"
];

// instala e guarda o “básico”
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// ativa e limpa caches antigos
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// estratégia: network-first para páginas, cache-first para assets
self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // não cachear downloads/geração de PDF (sempre ao vivo)
  if (url.pathname.includes("/baixar") || url.pathname.includes("/contrato") || url.pathname.includes("/promissoria")) {
    return; // deixa ir direto para rede
  }

  // cache-first para arquivos estáticos
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then(cached => cached || fetch(req))
    );
    return;
  }

  // network-first para páginas do app
  event.respondWith(
    fetch(req)
      .then(resp => {
        const copy = resp.clone();
        caches.open(CACHE).then(cache => cache.put(req, copy));
        return resp;
      })
      .catch(() => caches.match(req).then(cached => cached || caches.match("/")))
  );
});