const CACHE = 'vigilantex-v1';
const ASSETS = ['/', '/static/manifest.json'];

// Instala e faz cache dos assets
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

// Ativa e limpa caches antigos
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Estratégia: Network First, fallback para cache
self.addEventListener('fetch', e => {
  // Não intercepta chamadas de API (sempre vai ao servidor)
  if (e.request.url.includes('/api/')) return;

  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

// Sincronização em background quando volta a internet
self.addEventListener('sync', e => {
  if (e.tag === 'sync-plantao') {
    e.waitUntil(sincronizarDados());
  }
});

async function sincronizarDados() {
  // Envia dados offline armazenados no IndexedDB
  const db = await abrirDB();
  const pendentes = await db.getAll('pendentes');
  for (const item of pendentes) {
    try {
      await fetch(item.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item.data),
      });
      await db.delete('pendentes', item.id);
    } catch (e) {
      console.log('Ainda offline, tentará depois:', e);
    }
  }
}

function abrirDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('vigilantex-offline', 1);
    req.onupgradeneeded = e => {
      e.target.result.createObjectStore('pendentes', { keyPath: 'id', autoIncrement: true });
    };
    req.onsuccess = e => resolve({
      getAll: store => new Promise((res, rej) => {
        const tx = e.target.result.transaction(store, 'readonly');
        const req = tx.objectStore(store).getAll();
        req.onsuccess = () => res(req.result);
        req.onerror = () => rej(req.error);
      }),
      delete: (store, id) => new Promise((res, rej) => {
        const tx = e.target.result.transaction(store, 'readwrite');
        const req = tx.objectStore(store).delete(id);
        req.onsuccess = () => res();
        req.onerror = () => rej(req.error);
      }),
    });
    req.onerror = () => reject(req.error);
  });
}
