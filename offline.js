// Header tugmasi: offline yuklash va yangilash.
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
    const [imgs, auds] = await Promise.all([
      fetch('/rasmlar.json', { cache: 'no-store' }).then(r => r.json()).catch(() => []),
      fetch('/ovozlar.json', { cache: 'no-store' }).then(r => r.json()).catch(() => []),
    ]);
    const list = imgs.concat(auds);
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
