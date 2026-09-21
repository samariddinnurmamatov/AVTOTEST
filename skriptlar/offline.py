"""Saytni netsiz ishlaydigan qiladi: Service Worker, manifest, ikonka va header tugmasi.

python3 offline.py
Savol-javob mazmuniga tegmaydi — faqat <head> ga 4 qator va </body> oldiga 1 qator qo'shadi.
Qayta ishga tushirilsa, eski qo'shilganlar almashtiriladi (takrorlanmaydi).
"""
import hashlib
import json
import os
import re
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD_START, HEAD_END = "<!--pwa-->", "<!--/pwa-->"
BODY_START, BODY_END = "<!--pwa-js-->", "<!--/pwa-js-->"


def html_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "data", "skriptlar")]
        for f in filenames:
            if f.endswith(".html"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def web_path(path):
    return "/" + os.path.relpath(path, ROOT).replace(os.sep, "/")


# --- ikonka: rul ko'rinishidagi oddiy PNG (kutubxonasiz) ---
def png(size, path):
    bg, ring, spoke = (16, 18, 22), (67, 196, 122), (67, 196, 122)
    c, r_out, r_in, hub = size / 2, size * 0.38, size * 0.30, size * 0.10
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            dx, dy = x - c + 0.5, y - c + 0.5
            d = (dx * dx + dy * dy) ** 0.5
            px = bg
            if r_in <= d <= r_out:
                px = ring
            elif d <= hub:
                px = spoke
            elif d < r_in:
                # uchta spitsa
                for ang in (90, 210, 330):
                    a = ang * 3.14159 / 180
                    ux, uy = -dx * 0.0 + dx, dy
                    proj = ux * (a and __import__("math").cos(a)) + uy * __import__("math").sin(a)
                    perp = abs(-ux * __import__("math").sin(a) + uy * __import__("math").cos(a))
                    if proj > 0 and perp < size * 0.035:
                        px = spoke
                        break
            row += bytes(px)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(raw, 9))
    out += chunk(b"IEND", b"")
    open(path, "wb").write(out)


png(192, os.path.join(ROOT, "icon-192.png"))
png(512, os.path.join(ROOT, "icon-512.png"))

manifest = {
    "name": "Oson Prava — tayyorgarlik",
    "short_name": "Tayyorgarlik",
    "start_url": "/index.html",
    "display": "standalone",
    "background_color": "#101216",
    "theme_color": "#101216",
    "lang": "uz",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}
open(os.path.join(ROOT, "manifest.webmanifest"), "w", encoding="utf-8").write(json.dumps(manifest, ensure_ascii=False, indent=2))

pages = html_files()
digest = hashlib.sha1()
for f in pages:
    digest.update(open(f, "rb").read())
VERSION = digest.hexdigest()[:10]

images = sorted(
    "/rasmlar/" + f for f in os.listdir(os.path.join(ROOT, "rasmlar"))
    if not f.startswith(".")
)
open(os.path.join(ROOT, "rasmlar.json"), "w", encoding="utf-8").write(json.dumps(images, ensure_ascii=False))

core = ["/", "/manifest.webmanifest", "/offline.js", "/icon-192.png", "/icon-512.png"] + [web_path(f) for f in pages]

SW = """// Oson Prava tayyorgarlik — offline kesh. Versiya: %s
const VERSION = '%s';
const CORE = 'op-core-' + VERSION;
const IMG = 'op-img';
const CORE_FILES = %s;

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
""" % (VERSION, VERSION, json.dumps(core, ensure_ascii=False))
open(os.path.join(ROOT, "sw.js"), "w", encoding="utf-8").write(SW)

OFFLINE_JS = """// Header tugmasi: offline yuklash va yangilash.
(() => {
  if (!('serviceWorker' in navigator)) return;
  const wrap = document.querySelector('.bar .wrap');
  if (!wrap) return;
  const btn = document.createElement('button');
  btn.className = 'btn';
  btn.id = 'op-offline';
  btn.type = 'button';
  btn.textContent = 'Offline…';
  const score = wrap.querySelector('.score');
  score ? wrap.insertBefore(btn, score) : wrap.appendChild(btn);
  let waitingWorker = null;
  let busy = false;

  const set = (text, accent) => {
    btn.textContent = text;
    btn.style.borderColor = accent ? 'var(--accent)' : '';
    btn.style.color = accent ? 'var(--accent)' : '';
    btn.style.fontWeight = accent ? '700' : '';
  };

  async function imageState() {
    const list = await fetch('/rasmlar.json', { cache: 'no-store' }).then(r => r.json()).catch(() => []);
    const cache = await caches.open('op-img');
    const keys = await cache.keys();
    const have = new Set(keys.map(k => new URL(k.url).pathname));
    return { list, missing: list.filter(p => !have.has(p)) };
  }

  async function refresh() {
    if (busy || waitingWorker) return;
    const { list, missing } = await imageState();
    if (!list.length) { set('Offline'); return; }
    if (!missing.length) set('✓ Offline tayyor');
    else set('⬇ Offline yuklash (' + Math.round((list.length - missing.length) * 100 / list.length) + '%)');
  }

  async function download() {
    busy = true;
    const { list, missing } = await imageState();
    const cache = await caches.open('op-img');
    let done = list.length - missing.length;
    const batch = 6;
    for (let i = 0; i < missing.length; i += batch) {
      await Promise.all(missing.slice(i, i + batch).map(async p => {
        try { await cache.add(p); } catch (e) {}
        done++;
      }));
      set('Yuklanmoqda ' + Math.round(done * 100 / list.length) + '%');
    }
    busy = false;
    refresh();
  }

  btn.addEventListener('click', () => {
    if (waitingWorker) { waitingWorker.postMessage('SKIP_WAITING'); set('Yangilanmoqda…'); return; }
    if (!busy) download();
  });

  navigator.serviceWorker.register('/sw.js').then(reg => {
    const check = () => {
      if (reg.waiting && navigator.serviceWorker.controller) {
        waitingWorker = reg.waiting;
        set('⟳ Yangilash', true);
      }
    };
    check();
    reg.addEventListener('updatefound', () => {
      const sw = reg.installing;
      if (sw) sw.addEventListener('statechange', check);
    });
    setInterval(() => reg.update().catch(() => {}), 60 * 60 * 1000);
    refresh();
  }).catch(() => btn.remove());

  let reloaded = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloaded) return;
    reloaded = true;
    location.reload();
  });
})();
"""
open(os.path.join(ROOT, "offline.js"), "w", encoding="utf-8").write(OFFLINE_JS)

head_block = (
    f'{HEAD_START}<link rel="manifest" href="/manifest.webmanifest">'
    f'<meta name="theme-color" content="#101216">'
    f'<link rel="apple-touch-icon" href="/icon-192.png">{HEAD_END}'
)
body_block = f'{BODY_START}<script src="/offline.js" defer></script>{BODY_END}'
changed = 0
for f in pages:
    s = open(f, encoding="utf-8").read()
    before = s
    s = re.sub(re.escape(HEAD_START) + ".*?" + re.escape(HEAD_END), head_block, s, flags=re.S) if HEAD_START in s \
        else s.replace("</head>", head_block + "</head>", 1)
    s = re.sub(re.escape(BODY_START) + ".*?" + re.escape(BODY_END), body_block, s, flags=re.S) if BODY_START in s \
        else s.replace("</body>", body_block + "</body>", 1)
    if s != before:
        open(f, "w", encoding="utf-8").write(s)
        changed += 1

print(f"versiya: {VERSION}")
print(f"sahifalar: {len(pages)} (yangilandi: {changed}) | kesh ro'yxati: {len(core)} fayl | rasmlar: {len(images)}")
print("yozildi: sw.js, offline.js, manifest.webmanifest, icon-192.png, icon-512.png, rasmlar.json")
