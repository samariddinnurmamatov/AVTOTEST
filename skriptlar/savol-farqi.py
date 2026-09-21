"""Ilovadagi «Barcha testlar» ro'yxatini bazamiz bilan solishtiradi: qaysi savol qo'shilgan/olib tashlangan.

python3 savol-farqi.py <yangi-royxat.json>
Hech narsa yozmaydi — faqat hisobot.
"""
import json
import os
import re
import sys
import urllib.parse
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
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


def key(x):
    return norm(x["q"]), tuple(sorted(norm(a) for a in x["answers"])), img_name(x.get("img"))


base = json.load(open(os.path.join(DATA, "osonprava-savollar.json"), encoding="utf-8"))
live = json.load(open(sys.argv[1], encoding="utf-8"))
live = [x for x in live if not x.get("error")]

base_keys, live_keys = {}, {}
for b in base:
    base_keys.setdefault(key(b), []).append(b)
for x in live:
    live_keys.setdefault(key(x), []).append(x)

added = [x for k, xs in live_keys.items() if k not in base_keys for x in xs]
removed = [b for k, bs in base_keys.items() if k not in live_keys for b in bs]

print(f"bazada: {len(base)} | ilovada: {len(live)} | farq: {len(live) - len(base)}")
print(f"ilovada bor, bazada yo'q: {len(added)} ta")
print(f"bazada bor, ilovada yo'q: {len(removed)} ta")


def closest(x, pool):
    best, r = None, 0.0
    for b in pool:
        s = SequenceMatcher(None, norm(x["q"]), norm(b["q"])).ratio()
        if s > r:
            best, r = b, s
    return best, r


for x in added:
    b, r = closest(x, base)
    print(f"\n[QO'SHILGAN] ilovadagi {x['pos']}-o'rin | rasm: {'bor' if x.get('img') else 'yo‘q'}")
    print(f"  {x['q']}")
    for i, a in enumerate(x["answers"], 1):
        print(f"     F{i} {a}")
    print(f"  bazadagi eng yaqin savol: #{b['n']} ({r:.2f}) {b['q'][:80]}")
for b in removed[:20]:
    x, r = closest(b, live)
    print(f"\n[YO'QOLGAN] baza #{b['n']} | {b['q'][:90]}")
    print(f"  ilovadagi eng yaqin: {x['pos']}-o'rin ({r:.2f}) {x['q'][:80]}")
