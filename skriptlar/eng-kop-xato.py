"""«Men eng ko'p xato qilganim» sahifasi: turkumlar (o'xshash savollar ketma-ket) + mavzular.

python3 eng-kop-xato.py --stats   # faqat hisobot
python3 eng-kop-xato.py           # eng-kop-xato.html + bosh sahifada karta
Savollar asl bo'limlarida qoladi — bu yerda nusxasi turadi.
BILAMAN ro'yxatidagi savollar FAQAT shu sahifadan chiqariladi.
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
PAGE = os.path.join(ROOT, "eng-kop-xato.html")
HUB = os.path.join(ROOT, "index.html")
STATS_ONLY = "--stats" in sys.argv
MARK_START, MARK_END = "<!--eng-kop-xato-karta-->", "<!--/eng-kop-xato-karta-->"

# Egasi «bilaman» degan savollar — faqat shu sahifada ko'rsatilmaydi.
BILAMAN = {1195, 1045, 1032, 1063, 466}

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


def load(name):
    raw = json.load(open(os.path.join(DATA, name), encoding="utf-8"))
    return list(raw.values()) if isinstance(raw, dict) else raw


def key(x):
    return norm(x["q"]), tuple(sorted(norm(a) for a in x["answers"]))


base = load("osonprava-savollar.json")
groups = load("guruhlar.json")
group_of = {n: g for g in groups for n in g["n"]}
by_key = {}
for b in sorted(base, key=lambda b: b["n"]):
    by_key.setdefault(key(b), b)

error_ns = set()
for f in ("osonprava-xatolarim.json", "osonprava-xatolarim-2026-09-21.json"):
    for x in load(f):
        if x.get("error"):
            continue
        b = by_key.get(key(x))
        if b:
            error_ns.add(b["n"])

text = {b["n"]: norm(b["q"] + " " + " ".join(b["answers"])) for b in base}
pool = [b for b in base if b["n"] not in BILAMAN]


def pick(pattern, only_errors=False, extra=None):
    rx = re.compile(pattern)
    out = [b for b in pool if rx.search(text[b["n"]]) and (not only_errors or b["n"] in error_ns)]
    if extra:
        have = {b["n"] for b in out}
        out += [b for b in pool if b["n"] in extra and b["n"] not in have]
    return sorted(out, key=lambda b: (group_of.get(b["n"], {}).get("g", 9999), norm(b["q"]), b["n"]))


# 1) TURKUMLAR — bir xil mavzudagi savollar ketma-ket tursin, yodlash oson bo'lsin.
def pick_ns(ns):
    return sorted((b for b in pool if b["n"] in ns), key=lambda b: (norm(b["q"]), b["n"]))


def matches(pattern, question_only=False):
    rx = re.compile(pattern)
    return {b["n"] for b in pool if rx.search(norm(b["q"]) if question_only else text[b["n"]])}


# Faqat SAVOL matnida uchragani hisoblanadi — javoblardagi tasodifiy so'zlar turkumni buzmasin.
xizmat = matches(r"\b(dyhx\w*|yhx\w*|ypx\w*)\b", True)
olcham = matches(r"\b(olcham\w*|gabarit\w*|chiqib tur\w*|ruxsatisiz)\b", True)
yuk = matches(r"\b(yuk\w*|avtopoezd\w*|avtopoyezd\w*|tirkama\w*)\b", True)
ruxsat_olcham = (xizmat & (olcham | yuk)) | (olcham & yuk)
xodim_yth = xizmat - ruxsat_olcham

FAMILIES = [
    ("Ko'k nomli belgi (aholi punkti) va tezlik", "belgi bir xil, savol matni va transport turi o'zgaradi",
     "f1", pick(r"\b(shunday|bunday|shu) yol belgisi\b.*\btezlik|\btezlik\b.*\b(shunday|bunday|shu) yol belgisi")),
    ("DYHX ruxsati, yuk o'lchamlari va gabaritlari", "ruxsatisiz yurish mumkin bo'lgan o'lcham, uzunlik, balandlik, chiqib turish va xizmat bilan bog'liq holatlar",
     "f2", pick_ns(ruxsat_olcham | xodim_yth)),
    ("Sariq chiziqlar", "sidirg'a va uzuq-uzuq sariq chiziq, to'xtash taqiqlari",
     "f4", pick(r"\bsariq chizi\w*")),
    ("Orolcha", "orolcha va unga kirish qoidalari", "f5", pick(r"\borolcha\w*")),
    ("Uzuq-uzuq va uzluksiz yotiq chiziqlar", "chiziq turlari va ularni kesib o'tish",
     "f6", pick(r"\b(uzuq uzuq|uzluksiz|enli)\w* chizi\w*|\benli uzuq")),
]
family_ns = {b["n"] for _, _, _, items in FAMILIES for b in items}

# 2) MAVZULAR — xatolaringiz mavzular bo'yicha (turkumga tushganlari takrorlanmaydi).
def topic(pattern):
    return [b for b in pick(pattern, only_errors=True) if b["n"] not in family_ns]


TOPICS = [
    ("Yo'l belgilari", "xatolaringiz ichidan yo'l belgilariga oid savollar", "bl", topic(r"\bbelgi\w*")),
    ("To'xtash va to'xtab turish", "xatolaringiz ichidan to'xtash/to'xtab turishga oid savollar", "tx", topic(r"\btoxta\w*")),
    ("Burilish, qayrilish, manyovr", "xatolaringiz ichidan manyovrga oid savollar", "br",
     topic(r"\b(buril\w*|qayril\w*|manyovr\w*|orqa bilan)\b")),
    ("Chorraha va yo'l berish", "xatolaringiz ichidan chorrahada o'tish tartibiga oid savollar", "ch",
     topic(r"\b(chorraha\w*|yol berish\w*|birinchi bolib|ikkinchi bolib|nechanchi bolib|kesib otadi\w*)\b")),
    ("Tibbiyot - birinchi yordam", "xatolaringiz ichidan tibbiyotga oid savollar", "m",
     topic(r"\b(tibbiy\w*|jarohat\w*|qon|venoz|arterial\w*|jgut\w*|reanimats\w*|jonlantir\w*|suyak\w*|singan|zaharlan\w*|nafas\w*|yurak\w*|miya|chayqal\w*)\b")),
    ("Tramvay - barcha savollar", "bazadagi barcha tramvay savollari (faqat xatolaringiz emas)", "t",
     [b for b in pick(r"\btramvay\w*") if b["n"] not in family_ns]),
]

SECTIONS = FAMILIES + TOPICS
print(f"xatolaringiz: {len(error_ns)} ta | «bilaman» deb chiqarilganlar: {sorted(BILAMAN)}")
print("TURKUMLAR:")
for title, _, _, items in FAMILIES:
    print(f"   {title}: {len(items)} ta ({sum(1 for b in items if b['n'] in error_ns)} tasi xatolaringizda) -> "
          + ", ".join(f"#{b['n']}" for b in items))
print("MAVZULAR:")
for title, _, _, items in TOPICS:
    print(f"   {title}: {len(items)} ta")
if STATS_ONLY:
    sys.exit(0)


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


with ThreadPoolExecutor(4) as pool_exec:
    failed = [f for f in pool_exec.map(fetch, sorted({b["img"] for _, _, _, items in SECTIONS for b in items if b.get("img")})) if f]
print("rasm yuklash xatolari:", failed or 0)

src = open(os.path.join(ROOT, "barcha-guruhlar.html"), encoding="utf-8").read()
CSS = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
JS = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
EXTRA_CSS = """
.badge{font-size:12px;border:1px solid var(--line);border-radius:6px;padding:1px 7px;color:var(--muted);text-decoration:none}
a.badge.grp{color:var(--bad);border-color:var(--bad);font-weight:600}
.badge.bad{color:var(--bad);border-color:var(--bad);font-weight:600}
.card.mine{border-color:var(--bad);border-width:2px}
.kind{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--accent);font-weight:700}
"""


def card(prefix, i, b):
    g = group_of.get(b["n"])
    badges = [f'<span class="num">{i}</span>', f'<span class="badge">Barcha testlar #{b["n"]}</span>']
    if b["n"] in error_ns:
        badges.append('<span class="badge bad">xatolarimda</span>')
    if g:
        badges.append(f'<a class="badge grp" href="savollar/guruh-{g["g"]:03d}.html">chalg\'ituvchi · {g["g"]}-guruh</a>')
    img = f'<img class="qimg" loading="lazy" src="rasmlar/{html.escape(local_img(b["img"]))}" alt="rasm">' if b.get("img") else ""
    answers = "".join(
        f'<button class="ans" data-c="{1 if k == b["correct"] else 0}" data-k="{k}"><b>F{k + 1}</b><span>{html.escape(a)}</span></button>'
        for k, a in enumerate(b["answers"])
    )
    mine = " mine" if b["n"] in error_ns else ""
    return (
        f'<article class="card{mine}" data-n="{prefix}-{b["n"]}" data-search="{html.escape(text[b["n"]])}">'
        f'<div class="meta">{"".join(badges)}</div>{img}<h3 class="q">{html.escape(b["q"])}</h3>'
        f'<div class="answers">{answers}</div></article>'
    )


def section(kind, title, sub, prefix, items):
    cards = "".join(card(prefix, i, b) for i, b in enumerate(items, 1))
    return (
        f'<section class="group" id="s-{prefix}"><header class="ghead"><span class="kind">{kind}</span>'
        f'<h2>{html.escape(title)} — {len(items)} ta</h2><p class="gsub">{html.escape(sub)}</p></header>'
        f'<div class="grid">{cards}</div></section>'
    )


toc = "".join(
    f'<li><a href="#s-{p}">{html.escape(t)}</a> <small>({len(i)} ta)</small></li>'
    for t, _, p, i in SECTIONS
)
body = (
    f'<p class="stats"><a href="index.html">← Bosh sahifa</a> · Yuqorida — bir xil turkumdagi savollar ketma-ket '
    f'(yodlash oson bo\'lsin uchun), pastda — mavzular bo\'yicha xatolaringiz. Savollar asl bo\'limlarida ham turibdi. '
    f'Qizil ramka: o\'zingiz xato qilgan savol. Siz «bilaman» degan {len(BILAMAN)} ta savol shu sahifadan chiqarilgan.</p>'
    f'<details class="toc"><summary><b>Mundarija — {len(FAMILIES)} turkum, {len(TOPICS)} mavzu</b></summary><ol>{toc}</ol></details>'
    + "".join(section("turkum", t, s, p, i) for t, s, p, i in FAMILIES)
    + "".join(section("mavzu", t, s, p, i) for t, s, p, i in TOPICS)
)
page = f"""<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Men eng ko'p xato qilganim</title><style>{CSS}{EXTRA_CSS}</style></head>
<body><div class="bar"><div class="wrap"><a class="home" href="index.html">⌂ Bosh sahifa</a><h1>Men eng ko'p xato qilganim</h1>
<input id="search" type="search" placeholder="Qidirish: sariq chiziq, orolcha, tramvay…">
<div class="seg" role="group" aria-label="Rejim"><button data-mode="solve" aria-pressed="true">Yechish</button><button data-mode="memo" aria-pressed="false">Yodlash</button></div>
<button class="btn" id="reset">Qayta boshlash</button><button class="btn" id="theme" aria-label="Yorug'/qorong'i rejim">◐</button>
<span class="score" id="score"></span></div></div>
<div class="wrap">{body}</div><a class="totop" href="#top" aria-label="Tepaga">↑</a><script>{JS}</script></body></html>"""
open(PAGE, "w", encoding="utf-8").write(page)
print("yozildi:", PAGE)

s = open(HUB, encoding="utf-8").read()
total = sum(len(i) for _, _, _, i in SECTIONS)
chips = "".join(f'<span>{html.escape(t.split(" -")[0].split(" (")[0].lower())}: {len(i)}</span>' for t, _, _, i in SECTIONS)
card_html = (
    f'{MARK_START}<article class="hub" data-page="mavzu"><div class="hub-top"><span class="step">7</span>'
    f'<h3><a href="eng-kop-xato.html">Men eng ko\'p xato qilganim</a></h3></div>'
    f'<p class="desc">O\'xshash savollar turkum-turkum ketma-ket, keyin eng ko\'p adashadigan mavzularingiz.</p>'
    f'<div class="chips">{chips}<span>jami {total} savol</span></div>'
    f'<div class="prog" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-label="Mavzu bo\'yicha progress"><div class="fill"></div></div>'
    f'<div class="prog-row"><span class="prog-text"></span><b class="pct">0%</b></div>'
    f'<div class="actions"><span class="open">Ochish →</span><button class="reset" type="button" hidden>Qayta boshlash</button></div></article>{MARK_END}'
)
if MARK_START in s:
    s = re.sub(re.escape(MARK_START) + ".*?" + re.escape(MARK_END), card_html, s, flags=re.S)
else:
    s = s.replace('</div><p class="tip"', card_html + '</div><p class="tip"', 1)
m = re.search(r"const DATA=(\{.*?\});\nconst KEY=", s, re.S)
data = json.loads(m.group(1))
data["mavzu"] = {
    "ids": [f"{p}-{b['n']}" for _, _, p, items in SECTIONS for b in items],
    "ok": [b["correct"] for _, _, _, items in SECTIONS for b in items],
}
s = s[: m.start(1)] + json.dumps(data, ensure_ascii=False) + s[m.end(1):]
open(HUB, "w", encoding="utf-8").write(s)
print("bosh sahifadagi karta yangilandi | jami:", total)
