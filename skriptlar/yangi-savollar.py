"""Ilovaga qo'shilgan yangi savollar uchun alohida sahifa va bosh sahifada karta yasaydi.

python3 yangi-savollar.py <barcha-testlar-royxati.json>
Mavjud sahifalarga tegmaydi; faqat yangi-savollar.html yoziladi va index.html ga karta qo'shiladi
(marker bilan, qayta ishga tushirilsa almashtiriladi).
"""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
IMG_DIR = os.path.join(ROOT, "rasmlar")
PAGE = os.path.join(ROOT, "yangi-savollar.html")
HUB = os.path.join(ROOT, "index.html")
MARK_START, MARK_END = "<!--yangi-savollar-karta-->", "<!--/yangi-savollar-karta-->"

LOOKALIKE = str.maketrans({
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K", "М": "M", "О": "O",
    "Р": "P", "Т": "T", "Х": "X", "а": "a", "с": "c", "е": "e", "о": "o", "р": "p", "х": "x",
})


def norm(s):
    s = s.translate(LOOKALIKE).lower()
    s = re.sub(r"[‘’ʻʼ`´']", "", s)
    s = re.sub(r"[^\w ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def img_name(url):
    return urllib.parse.unquote(url.rsplit("/", 1)[-1]) if url else None


def local_img(url):
    return re.sub(r"[^\w.\-]+", "_", img_name(url))


def key(x):
    # Rasm nomi hisobga olinmaydi: ilova eski savolga rasm qo'shsa ham u yangi savol emas.
    return norm(x["q"]), tuple(sorted(norm(a) for a in x["answers"]))


base = json.load(open(os.path.join(DATA, "osonprava-savollar.json"), encoding="utf-8"))
live = [x for x in json.load(open(sys.argv[1], encoding="utf-8")) if not x.get("error")]
base_keys = {key(b) for b in base}
fresh, seen = [], set()
for x in live:
    k = key(x)
    if k not in base_keys and k not in seen:
        seen.add(k)
        fresh.append(x)
print(f"bazada {len(base)}, ilovada {len(live)} | yangi savollar: {len(fresh)} ta")
for x in fresh:
    print(f"   {x['pos']}-o'rin | {x['q'][:90]} | rasm: {'bor' if x.get('img') else 'yoq'}")
if not fresh:
    sys.exit(0)

# Javob kaliti: ilovada hech narsa bosilmagani uchun yangi savollarda to'g'ri javob NOMA'LUM.
answers_key = {}
key_file = os.path.join(DATA, "yangi-savollar-javoblari.json")
if os.path.isfile(key_file):
    answers_key = {str(k): v for k, v in json.load(open(key_file, encoding="utf-8")).items()}


def fetch(url):
    path = os.path.join(IMG_DIR, local_img(url))
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return None
    try:
        req = urllib.request.Request(url.replace("[", "%5B").replace("]", "%5D"), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
            f.write(r.read())
    except Exception as e:  # noqa: BLE001
        return f"{url}: {e}"
    return None


with ThreadPoolExecutor(4) as pool:
    failed = [f for f in pool.map(fetch, sorted({x["img"] for x in fresh if x.get("img")})) if f]
print("rasm yuklash xatolari:", failed or 0)

# CSS/JS — mavjud sahifalardan olinadi, ko'rinish bir xil bo'lsin.
src = open(os.path.join(ROOT, "barcha-guruhlar.html"), encoding="utf-8").read()
CSS = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
JS = re.search(r"<script>(.*?)</script>", src, re.S).group(1)

cards = []
for i, x in enumerate(fresh, 1):
    ci = answers_key.get(str(i), -1)
    img = f'<img class="qimg" loading="lazy" src="rasmlar/{html.escape(local_img(x["img"]))}" alt="rasm">' if x.get("img") else ""
    answers = "".join(
        f'<button class="ans" data-c="{1 if k == ci else 0}" data-k="{k}"><b>F{k + 1}</b><span>{html.escape(a)}</span></button>'
        for k, a in enumerate(x["answers"])
    )
    note = "" if ci >= 0 else (
        '<p class="miss">To\'g\'ri javob hali aniqlanmagan — ilovada javob bosilmagani uchun. '
        'Bu savolni faqat o\'qib qo\'ying.</p>'
    )
    search = html.escape(norm(x["q"]) + " " + " ".join(norm(a) for a in x["answers"]))
    cards.append(
        f'<article class="card" data-n="n-{i}" data-search="{search}"><div class="meta">'
        f'<span class="num">{i}</span><span class="badge">ilovada {x["pos"]}-o\'rin</span></div>'
        f'{img}<h3 class="q">{html.escape(x["q"])}</h3><div class="answers">{answers}</div>{note}</article>'
    )

known = sum(1 for i in range(1, len(fresh) + 1) if answers_key.get(str(i), -1) >= 0)
body = (
    f'<p class="stats"><a href="index.html">← Bosh sahifa</a> · 21-sentabr holati: ilovada {len(live)} ta savol bor, '
    f'bizning bazada {len(base)} ta edi. Quyidagilari yangi qo\'shilgan.'
    + ("" if known == len(fresh) else f' To\'g\'ri javobi ma\'lum: {known}/{len(fresh)}.') + '</p>'
    f'<section class="group"><header class="ghead"><h2>Yangi qo\'shilgan savollar — {len(fresh)} ta</h2>'
    f'<p class="gsub">Oson Prava ro\'yxatiga 14-sentabrdan keyin qo\'shilgan savollar</p></header>'
    f'<div class="grid">{"".join(cards)}</div></section>'
)
page = f"""<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yangi qo'shilgan savollar</title><style>{CSS}</style></head>
<body><div class="bar"><div class="wrap"><a class="home" href="index.html">⌂ Bosh sahifa</a><h1>Yangi qo'shilgan savollar</h1>
<input id="search" type="search" placeholder="Qidirish…">
<div class="seg" role="group" aria-label="Rejim"><button data-mode="solve" aria-pressed="true">Yechish</button><button data-mode="memo" aria-pressed="false">Yodlash</button></div>
<button class="btn" id="reset">Qayta boshlash</button><button class="btn" id="theme" aria-label="Yorug'/qorong'i rejim">◐</button>
<span class="score" id="score"></span></div></div>
<div class="wrap">{body}</div><a class="totop" href="#top" aria-label="Tepaga">↑</a><script>{JS}</script></body></html>"""
open(PAGE, "w", encoding="utf-8").write(page)
print("yozildi:", PAGE)

# Bosh sahifaga karta
s = open(HUB, encoding="utf-8").read()
chips = f'<span>{len(fresh)} savol</span><span>21-sentabrda qo\'shilgan</span>'
if known < len(fresh):
    chips += f'<span>javobi ma\'lum: {known}/{len(fresh)}</span>'
card_html = (
    f'{MARK_START}<article class="hub" data-page="yangi"><div class="hub-top"><span class="step">6</span>'
    f'<h3><a href="yangi-savollar.html">Yangi qo\'shilgan savollar</a></h3></div>'
    f'<p class="desc">Oson Prava ro\'yxatiga 14-sentabrdan keyin qo\'shilgan savollar.</p>'
    f'<div class="chips">{chips}</div>'
    f'<div class="prog" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-label="Yangi qo\'shilgan savollar progressi"><div class="fill"></div></div>'
    f'<div class="prog-row"><span class="prog-text"></span><b class="pct">0%</b></div>'
    f'<div class="actions"><span class="open">Ochish →</span><button class="reset" type="button" hidden>Qayta boshlash</button></div></article>{MARK_END}'
)
if MARK_START in s:
    s = re.sub(re.escape(MARK_START) + ".*?" + re.escape(MARK_END), card_html, s, flags=re.S)
else:
    j = s.index("</div>", s.index('<div class="hubs">'))
    s = s[:j] + card_html + s[j:]
m = re.search(r"const DATA=(\{.*?\});\nconst KEY=", s, re.S)
data = json.loads(m.group(1))
data["yangi"] = {
    "ids": [f"n-{i}" for i in range(1, len(fresh) + 1)],
    "ok": [answers_key.get(str(i), -1) for i in range(1, len(fresh) + 1)],
}
s = s[: m.start(1)] + json.dumps(data, ensure_ascii=False) + s[m.end(1):]
open(HUB, "w", encoding="utf-8").write(s)
print("bosh sahifaga karta qo'shildi; kartalar:", list(data))
