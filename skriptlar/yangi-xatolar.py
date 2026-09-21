"""Oson Prava'dagi yangi xatolarni aniqlab, xatolarim sahifalari tagiga «Yangi xatolarim» bo'limini qo'shadi.

python3 yangi-xatolar.py --stats   # faqat hisobot
python3 yangi-xatolar.py           # sahifalarga yozadi
Eski 238 talik ro'yxatga tegilmaydi; bo'lim qayta ishga tushirilganda almashtiriladi (takrorlanmaydi).
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
STATS_ONLY = "--stats" in sys.argv
MARK_START, MARK_END = "<!--yangi-xatolar-->", "<!--/yangi-xatolar-->"

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
    return norm(x["q"]), tuple(sorted(norm(a) for a in x["answers"])), img_name(x.get("img"))


base = load("osonprava-savollar.json")
base_by_n = {b["n"]: b for b in base}
groups = load("guruhlar.json")
group_of = {n: g for g in groups for n in g["n"]}
by_full = {}
for b in sorted(base, key=lambda b: b["n"]):
    by_full.setdefault(key(b), b)


def matched(name):
    found, missing = [], []
    for x in load(name):
        if x.get("error"):
            continue
        b = by_full.get(key(x))
        (found.append((x, b)) if b else missing.append(x.get("pos")))
    return found, missing


old_pairs, old_missing = matched("osonprava-xatolarim.json")
new_pairs, new_missing = matched("osonprava-xatolarim-2026-09-21.json")
mark_ns = {b["n"] for _, b in matched("osonprava-saqlanganlar.json")[0]}

old_ns = {b["n"] for _, b in old_pairs}
seen, fresh = set(), []
for x, b in new_pairs:
    if b["n"] not in old_ns and b["n"] not in seen:
        seen.add(b["n"])
        fresh.append((x, b))

still_ns = {b["n"] for _, b in new_pairs}
print(f"eski ro'yxat: {len(old_pairs)} ta (moslanmagan {old_missing})")
print(f"ilovadagi hozirgi ro'yxat: {len(new_pairs)} ta (moslanmagan {new_missing})")
print(f"yangi xatolar (eskida yo'q): {len(fresh)} ta")
print(f"eskilardan tuzatilganlar (endi ilovada yo'q): {len(old_ns - still_ns)} ta")
print(f"yangilardan chalg'ituvchi guruhga tushadiganlar: {sum(1 for _, b in fresh if group_of.get(b['n']))} ta")
for x, b in fresh[:10]:
    print(f"   #{b['n']} {b['q'][:80]} | ✅ {b['answers'][b['correct']][:50]}")
if STATS_ONLY:
    sys.exit(0)

urls = {x.get("img") or b.get("img") for x, b in fresh if x.get("img") or b.get("img")}
for _, b in fresh:
    g = group_of.get(b["n"])
    if g:
        urls |= {base_by_n[n]["img"] for n in g["variants"] if base_by_n[n].get("img")}


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


with ThreadPoolExecutor(6) as pool:
    failed = [f for f in pool.map(fetch, sorted(urls)) if f]
print("rasm yuklash xatolari:", failed or 0)

IMG_PREFIX = "../rasmlar/"


def card(i, x, b):
    g = group_of.get(b["n"])
    ci = next((k for k, a in enumerate(x["answers"]) if norm(a) == norm(b["answers"][b["correct"]])), -1)
    badges = [f'<span class="num">{i}</span>', f'<span class="badge">Barcha testlar #{b["n"]}</span>']
    if g:
        badges.append(f'<a class="badge grp" href="../savollar/guruh-{g["g"]:03d}.html">chalg\'ituvchi · {g["g"]}-guruh</a>')
    if b["n"] in mark_ns:
        badges.append('<span class="badge">saqlanganlarda ham</span>')
    img_url = x.get("img") or b.get("img")
    img = f'<img class="qimg" loading="lazy" src="{IMG_PREFIX}{html.escape(local_img(img_url))}" alt="rasm">' if img_url else ""
    answers = "".join(
        f'<button class="ans" data-c="{1 if k == ci else 0}" data-k="{k}"><b>F{k + 1}</b><span>{html.escape(a)}</span></button>'
        for k, a in enumerate(x["answers"])
    )
    miss = '<p class="miss">To\'g\'ri javob bazadan topilmadi — ilovada tekshiring.</p>' if ci < 0 else ""
    twins = ""
    if g:
        rows = []
        for n in g["variants"]:
            if n == b["n"]:
                continue
            t = base_by_n[n]
            thumb = f'<img src="{IMG_PREFIX}{html.escape(local_img(t["img"]))}" alt="" loading="lazy">' if t.get("img") else ""
            rows.append(
                f'<div class="twin">{thumb}<div><b>#{n}</b> {html.escape(t["q"])}<br>'
                f'<span class="ok">✅ {html.escape(t["answers"][t["correct"]])}</span></div></div>'
            )
        own = f'<div class="twin"><div><b>Shu savol</b><br><span class="ok">✅ {html.escape(b["answers"][b["correct"]])}</span></div></div>'
        twins = f'<details class="twins"><summary>Egizak savollari ({len(rows)}) — javobi farq qiladi</summary>{own}{"".join(rows)}</details>'
    search = html.escape(norm(x["q"]) + " " + " ".join(norm(a) for a in x["answers"]))
    return (
        f'<article class="card item" data-n="y-{i}" data-grp="{1 if g else 0}" data-search="{search}">'
        f'<div class="meta">{"".join(badges)}</div>{img}<h3 class="q">{html.escape(x["q"])}</h3>'
        f'<div class="answers">{answers}</div>{miss}{twins}</article>'
    )


in_groups = sum(1 for _, b in fresh if group_of.get(b["n"]))
block = (
    f'{MARK_START}<h2 class="part" style="text-align:center">Yangi xatolarim — {len(fresh)} ta</h2>'
    f'<p class="stats" style="text-align:center">21-sentabr holati: ilovadagi xatolar ro\'yxatida bor, lekin yuqoridagi '
    f'{len(old_pairs)} talik ro\'yxatda yo\'q savollar. {in_groups} tasi chalg\'ituvchi guruhlarga kiradi.</p>'
    f'<div class="grid">{"".join(card(i, x, b) for i, (x, b) in enumerate(fresh, 1))}</div>{MARK_END}'
)

pages = ["xatolarim/xatolarim.html", "xatolarim/index.html"]
for rel in pages:
    path = os.path.join(ROOT, rel)
    s = open(path, encoding="utf-8").read()
    if MARK_START in s:
        s = re.sub(re.escape(MARK_START) + ".*?" + re.escape(MARK_END), block, s, flags=re.S)
    else:
        m = re.search(r'<section class="list[^"]*" data-list="errors">', s)
        j = s.index("</section>", m.start())
        s = s[:j] + block + s[j:]
    open(path, "w", encoding="utf-8").write(s)
    print("yozildi:", rel)

# Bosh sahifadagi «Xatolarim» kartasi yangi savollarni ham sanasin.
hub = os.path.join(ROOT, "index.html")
s = open(hub, encoding="utf-8").read()
m = re.search(r"const DATA=(\{.*?\});\nconst KEY=", s, re.S)
data = json.loads(m.group(1))
ids, oks = [], []
for i, (x, b) in enumerate(fresh, 1):
    ci = next((k for k, a in enumerate(x["answers"]) if norm(a) == norm(b["answers"][b["correct"]])), -1)
    ids.append(f"y-{i}")
    oks.append(ci)
data["errors"]["ids"] = [i for i in data["errors"]["ids"] if not i.startswith("y-")] + ids
data["errors"]["ok"] = data["errors"]["ok"][: len(data["errors"]["ids"]) - len(ids)] + oks
s = s[: m.start(1)] + json.dumps(data, ensure_ascii=False) + s[m.end(1):]
open(hub, "w", encoding="utf-8").write(s)
print("bosh sahifa yangilandi: Xatolarim kartasi endi", len(data["errors"]["ids"]), "savolni sanaydi")
