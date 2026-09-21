// Oson Prava tayyorgarlik — offline kesh. Versiya: 6f34494635
const VERSION = '6f34494635';
const CORE = 'op-core-' + VERSION;
const IMG = 'op-img';
const CORE_FILES = ["/", "/manifest.webmanifest", "/offline.js", "/icon-192.png", "/icon-512.png", "/barcha-guruhlar.html", "/eng-kop-xato.html", "/index.html", "/reja.html", "/savollar/guruh-001.html", "/savollar/guruh-002.html", "/savollar/guruh-003.html", "/savollar/guruh-004.html", "/savollar/guruh-005.html", "/savollar/guruh-006.html", "/savollar/guruh-007.html", "/savollar/guruh-008.html", "/savollar/guruh-009.html", "/savollar/guruh-010.html", "/savollar/guruh-011.html", "/savollar/guruh-012.html", "/savollar/guruh-013.html", "/savollar/guruh-014.html", "/savollar/guruh-015.html", "/savollar/guruh-016.html", "/savollar/guruh-017.html", "/savollar/guruh-018.html", "/savollar/guruh-019.html", "/savollar/guruh-020.html", "/savollar/guruh-021.html", "/savollar/guruh-022.html", "/savollar/guruh-023.html", "/savollar/guruh-024.html", "/savollar/guruh-025.html", "/savollar/guruh-026.html", "/savollar/guruh-027.html", "/savollar/guruh-028.html", "/savollar/guruh-029.html", "/savollar/guruh-030.html", "/savollar/guruh-031.html", "/savollar/guruh-032.html", "/savollar/guruh-033.html", "/savollar/guruh-034.html", "/savollar/guruh-035.html", "/savollar/guruh-036.html", "/savollar/guruh-037.html", "/savollar/guruh-038.html", "/savollar/guruh-039.html", "/savollar/guruh-040.html", "/savollar/guruh-041.html", "/savollar/guruh-042.html", "/savollar/guruh-043.html", "/savollar/guruh-044.html", "/savollar/guruh-045.html", "/savollar/guruh-046.html", "/savollar/guruh-047.html", "/savollar/guruh-048.html", "/savollar/guruh-049.html", "/savollar/guruh-050.html", "/savollar/guruh-051.html", "/savollar/guruh-052.html", "/savollar/guruh-053.html", "/savollar/guruh-054.html", "/savollar/guruh-055.html", "/savollar/guruh-056.html", "/savollar/guruh-057.html", "/savollar/guruh-058.html", "/savollar/guruh-059.html", "/savollar/guruh-060.html", "/savollar/guruh-061.html", "/savollar/guruh-062.html", "/savollar/guruh-063.html", "/savollar/guruh-064.html", "/savollar/guruh-065.html", "/savollar/guruh-066.html", "/savollar/guruh-067.html", "/savollar/guruh-068.html", "/savollar/guruh-069.html", "/savollar/guruh-070.html", "/savollar/guruh-071.html", "/savollar/guruh-072.html", "/savollar/guruh-073.html", "/savollar/guruh-074.html", "/savollar/guruh-075.html", "/savollar/guruh-076.html", "/savollar/guruh-077.html", "/savollar/guruh-078.html", "/savollar/guruh-079.html", "/savollar/guruh-080.html", "/savollar/guruh-081.html", "/savollar/guruh-082.html", "/savollar/guruh-083.html", "/savollar/guruh-084.html", "/savollar/guruh-085.html", "/savollar/guruh-086.html", "/savollar/guruh-087.html", "/savollar/guruh-088.html", "/savollar/guruh-089.html", "/savollar/guruh-090.html", "/savollar/guruh-091.html", "/savollar/guruh-092.html", "/savollar/guruh-093.html", "/savollar/guruh-094.html", "/savollar/guruh-095.html", "/savollar/guruh-096.html", "/savollar/guruh-097.html", "/savollar/guruh-098.html", "/savollar/guruh-099.html", "/savollar/guruh-100.html", "/savollar/guruh-101.html", "/savollar/guruh-102.html", "/savollar/guruh-103.html", "/savollar/guruh-104.html", "/savollar/guruh-105.html", "/savollar/guruh-106.html", "/savollar/guruh-107.html", "/savollar/guruh-108.html", "/savollar/guruh-109.html", "/savollar/guruh-110.html", "/savollar/guruh-111.html", "/shpargalka.html", "/xatolarim/eng-kop-adashganlarim.html", "/xatolarim/index.html", "/xatolarim/saqlanganlar.html", "/xatolarim/xatolarim.html", "/yangi-savollar.html"];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CORE).then(c => c.addAll(CORE_FILES)));
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith('op-core-') && k !== CORE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', e => {
  if (e.data === 'SKIP_WAITING') self.skipWaiting();
  if (e.data === 'VERSION') e.source.postMessage({ version: VERSION });
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  const isImg = url.pathname.startsWith('/rasmlar/');
  e.respondWith((async () => {
    const cache = await caches.open(isImg ? IMG : CORE);
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    } catch (err) {
      const fallback = await caches.match('/index.html');
      return fallback || new Response('Offline', { status: 503, headers: { 'content-type': 'text/plain' } });
    }
  })());
});
