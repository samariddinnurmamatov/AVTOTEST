"""4 kunlik reja va shpargalka sahifalari — FAQAT foydalanuvchining xatolari asosida.

python3 reja.py
Yozadi: reja.html, shpargalka.html va index.html ga bitta karta (marker bilan).
Boshqa sahifalarga tegmaydi.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MARK_START, MARK_END = "<!--reja-karta-->", "<!--/reja-karta-->"

LOOKALIKE = str.maketrans({
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K", "М": "M", "О": "O",
    "Р": "P", "Т": "T", "Х": "X", "а": "a", "с": "c", "е": "e", "о": "o", "р": "p", "х": "x",
})


def norm(s):
    s = s.translate(LOOKALIKE).lower()
    s = re.sub(r"[‘’ʻʼ`´']", "", s)
    s = re.sub(r"[^\w ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def local_img(url):
    import urllib.parse
    return re.sub(r"[^\w.\-]+", "_", urllib.parse.unquote(url.rsplit("/", 1)[-1]))


def load(name):
    raw = json.load(open(os.path.join(DATA, name), encoding="utf-8"))
    return list(raw.values()) if isinstance(raw, dict) else raw


def key(x):
    return norm(x["q"]), tuple(sorted(norm(a) for a in x["answers"]))


base = load("osonprava-savollar.json")
bn = {b["n"]: b for b in base}
groups = load("guruhlar.json")
group_of = {n: g for g in groups for n in g["n"]}
by_key = {}
for b in sorted(base, key=lambda b: b["n"]):
    by_key.setdefault(key(b), b)

old_ns, new_ns = set(), set()
for f, bucket in (("osonprava-xatolarim.json", old_ns), ("osonprava-xatolarim-2026-09-21.json", new_ns)):
    for x in load(f):
        if x.get("error"):
            continue
        b = by_key.get(key(x))
        if b:
            bucket.add(b["n"])
err_ns = old_ns | new_ns
# Egasi so'ragan qo'shimcha savollar: xato qilmagan, lekin oila to'liq ko'rinsin
# (#1067, #1088 — #1065/#1066 bilan bitta zebra oilasi).
EXTRA_NS = {1067, 1088}
stubborn = old_ns & new_ns
text = {b["n"]: norm(b["q"] + " " + " ".join(b["answers"])) for b in base}
correct = {b["n"]: b["answers"][b["correct"]] for b in base}

BUCKETS = [
    (1, "Raqamlar: tezlik, masofa, vaqt, foiz", "javobi raqam bo'lgan savollar — jadval bo'lib yodlanadi", "raqam",
     lambda b: re.search(r"^\s*\d+([.,]\d+)?\s*(km|m|mm|%|metr|daqiqa|soat|kun)\b", correct[b["n"]], re.I)
     or re.search(r"\b(qanday eng katta tezlik|qancha|nechta|necha)\b", norm(b["q"]))),
    (1, "To'xtash va to'xtab turish", "qayerda mumkin, qayerda taqiqlangan", "toxtash",
     lambda b: re.search(r"\btoxta\w*", text[b["n"]])),
    (1, "Yotiq chiziqlar", "sariq, uzuq-uzuq, uzluksiz, enli chiziqlar", "chiziq",
     lambda b: re.search(r"\bchizi\w*", text[b["n"]])),
    (2, "Yo'l belgilari", "eng ko'p xato qiladigan bo'limingiz", "belgi",
     lambda b: re.search(r"\bbelgi\w*", text[b["n"]])),
    (2, "Yuk va odam tashish, gabaritlar", "o'lchamlar, chiqib turish, yo'lovchi tashish", "yuk",
     lambda b: re.search(r"\b(yuk tash\w*|odam tash\w*|yolovchi\w*|yukxona\w*|olcham\w*|gabarit\w*|kuzov\w*)\b", text[b["n"]])),
    (2, "Shatakka olish", "ulagich turlari, masofa, kim nimani tortadi", "shatak",
     lambda b: re.search(r"\b(shatak\w*|ulagich\w*|tirkagich\w*)\b", text[b["n"]])),
    (3, "Manyovr: burilish, qayrilish, quvib o'tish", "kim kimga yo'l beradi, qayerda taqiqlanadi", "manyovr",
     lambda b: re.search(r"\b(buril\w*|qayril\w*|manyovr\w*|quvib ot\w*|ozib ket\w*|orqa bilan)\b", text[b["n"]])),
    (3, "Chorraha, yo'l berish, svetofor", "4 qadamli algoritm bilan yechiladi", "chorraha",
     lambda b: re.search(r"\b(chorraha\w*|yol berish\w*|svetofor\w*|nizomlovchi\w*|birinchi bolib|ikkinchi bolib|kesib otadi\w*)\b", text[b["n"]])),
    (3, "Texnik nosozlik va foydalanish", "qachon yurish mumkin emas", "texnik",
     lambda b: re.search(r"\b(nosoz\w*|tormoz\w*|protektor\w*|shina\w*|foydalanish taqiqlan\w*|jihozlan\w*)\b", text[b["n"]])),
    (3, "Ta'riflar", "juft-juft yodlanadi — eng o'jar bo'limingiz", "tarif",
     lambda b: re.search(r"\bdeb nimaga aytiladi|atama\w*", text[b["n"]])),
    (3, "Tibbiyot va birinchi yordam", "ketma-ketlikni yodlang", "tibbiyot",
     lambda b: re.search(r"\b(tibbiy\w*|jarohat\w*|qon|venoz|arterial\w*|jgut\w*|reanimats\w*|jonlantir\w*|suyak\w*|singan|zaharlan\w*|nafas\w*|yurak\w*|miya)\b", text[b["n"]])),
    (4, "Qolgan savollar", "boshqa bo'limlarga tushmagan xatolaringiz", "qolgan", lambda b: True),
]

pool = [bn[n] for n in sorted(err_ns | EXTRA_NS)]
assigned, blocks = set(), []
for day, title, sub, slug, match in BUCKETS:
    items = [b for b in pool if b["n"] not in assigned and match(b)]
    assigned |= {b["n"] for b in items}
    blocks.append({"day": day, "title": title, "sub": sub, "slug": slug, "items": items})

print(f"xato savollar: {len(pool)} | taqsimlandi: {len(assigned)}")
for bl in blocks:
    print(f"   {bl['day']}-kun | {bl['title']}: {len(bl['items'])} ta (o'jar: {sum(1 for b in bl['items'] if b['n'] in stubborn)})")

# ---------- shpargalka jadvallari (hammasi bazadagi TO'G'RI javoblardan) ----------
def num(s):
    m = re.search(r"\d+([.,]\d+)?", s)
    return float(m.group(0).replace(",", ".")) if m else 1e9


def table(pattern, skip_generic=True):
    rows = []
    for b in base:
        ca = correct[b["n"]]
        if re.search(pattern, ca, re.I) and not (skip_generic and re.search(r"barcha|hamma|hech", ca, re.I)):
            rows.append(b)
    return sorted(rows, key=lambda b: num(correct[b["n"]]))


SHEETS = [
    ("Tezlik (km/s)", "eng katta ruxsat etilgan tezliklar — o'sish tartibida", table(r"^\s*\d{2,3}\s*km")),
    ("Masofa (metr)", "ulagich, to'xtash, gabarit masofalari", table(r"\b\d+([.,]\d+)?\s*(m|metr)\b(?!\s*/)")),
    ("Protektor va qiyalik (mm, %)", "shina naqshi va tormoz tizimi", table(r"\d+([.,]\d+)?\s*(%|mm)")),
    ("Vaqt", "muddatlar", table(r"\b\d+\s*(daqiqa|soat|kun|oy|yil)\b")),
    ("Ta'riflar", "atamalar — juftlab solishtiring", [b for b in base if "deb nimaga aytiladi" in norm(b["q"])]),
]

ALGORITHM = """<ol>
<li><b>Tramvay bormi?</b> Teng sharoitda relssiz transportdan ustun (o'zi ham belgi/svetoforga bo'ysunadi).</li>
<li><b>Belgi bormi?</b> Asosiy yo'l — o'tadi; ikkinchi darajali — yo'l beradi.</li>
<li><b>O'ngdan xalaqit.</b> Belgi bo'lmasa yoki teng bo'lsa — o'ngdagi o'tadi.</li>
<li><b>Manyovr.</b> Chapga buriluvchi yoki qayriluvchi — oxirida.</li>
</ol>
<p class="miss">Bu qator — qoidaning qisqa umumlashmasi, jadvallardagi raqamlar esa to'g'ridan-to'g'ri savollar javobidan olingan.</p>"""

src = open(os.path.join(ROOT, "barcha-guruhlar.html"), encoding="utf-8").read()
CSS = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
JS = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
EXTRA_CSS = """
.badge{font-size:12px;border:1px solid var(--line);border-radius:6px;padding:1px 7px;color:var(--muted);text-decoration:none}
a.badge.grp{color:var(--bad);border-color:var(--bad);font-weight:600}
.badge.bad{color:var(--bad);border-color:var(--bad);font-weight:600}
.card.mine{border-color:var(--bad);border-width:2px}
.day{margin:26px 0 8px;padding:14px 16px;background:var(--panel);border:1px solid var(--line);border-radius:12px}
.day h2{margin:0 0 6px;font-size:19px}
.day .bar-wrap{height:10px;background:var(--bg);border:1px solid var(--line);border-radius:999px;overflow:hidden;margin-top:8px}
.day .bar-fill{height:100%;width:0;background:var(--ok);transition:width .3s}
.day .plan{color:var(--muted);font-size:14px;margin:4px 0 0}
.blockhead{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.blockhead label{display:inline-flex;gap:6px;align-items:center;font-size:13px;color:var(--muted);cursor:pointer}
.blockprog{font-size:13px;color:var(--muted)}
.sheet table{font-size:14px}
.sheet .n{white-space:nowrap;color:var(--muted)}
.sheet .a{color:var(--ok);font-weight:600}
.sheet tr.mine .n{color:var(--bad);font-weight:700}
.filterbar{display:inline-flex;gap:6px;align-items:center;color:var(--muted);font-size:14px}
"""

EXTRA_JS = """
(() => {
  const KEY='osonprava-javob-';
  const get=k=>{try{return localStorage.getItem(k)}catch(e){return null}};
  function stats(root){let done=0,ok=0,total=0;
    root.querySelectorAll('.card[data-n]').forEach(c=>{total++;const v=get(KEY+c.dataset.n);
      if(v!==null){done++;if(c.querySelector('.ans[data-c="1"]')?.dataset.k===v)ok++}});
    return {done,ok,total};}
  function refresh(){
    document.querySelectorAll('.day').forEach(d=>{
      const secs=document.querySelectorAll('[data-day="'+d.dataset.day+'"]');
      let done=0,ok=0,total=0;
      secs.forEach(s=>{const st=stats(s);done+=st.done;ok+=st.ok;total+=st.total});
      const pct=total?Math.round(done*100/total):0;
      d.querySelector('.bar-fill').style.width=pct+'%';
      d.querySelector('.dstat').textContent=done?`${done}/${total} yechildi · to'g'ri ${ok} · xato ${done-ok} · ${pct}%`:`${total} ta savol`;
    });
    document.querySelectorAll('section.group[data-day]').forEach(s=>{
      const st=stats(s);const el=s.querySelector('.blockprog');
      if(el)el.textContent=st.done?`${st.done}/${st.total} · xato ${st.done-st.ok}`:`${st.total} ta savol`;
    });
  }
  document.addEventListener('click',e=>{if(e.target.closest('.ans')||e.target.closest('#reset'))setTimeout(refresh,50)});
  document.querySelectorAll('.blockdone').forEach(cb=>{
    const k='reja-blok-'+cb.dataset.blok;
    try{cb.checked=get(k)==='1'}catch(e){}
    cb.addEventListener('change',()=>{try{localStorage.setItem(k,cb.checked?'1':'0')}catch(e){}
      cb.closest('section').style.opacity=cb.checked?'0.55':'';});
    if(cb.checked)cb.closest('section').style.opacity='0.55';
  });
  const only=document.getElementById('onlywrong');
  if(only)only.addEventListener('change',()=>{
    document.querySelectorAll('.card[data-n]').forEach(c=>{
      const v=get(KEY+c.dataset.n);
      const wrong=v!==null&&c.querySelector('.ans[data-c="1"]')?.dataset.k!==v;
      c.classList.toggle('hidden',only.checked&&!wrong);
    });
  });
  refresh();
})();
"""


def card(b):
    n = b["n"]
    g = group_of.get(n)
    badges = [f'<span class="num">#{n}</span>']
    if n in stubborn:
        badges.append('<span class="badge bad">o\'jar — 2 marta xato</span>')
    elif n in new_ns:
        badges.append('<span class="badge">yangi xato</span>')
    elif n in EXTRA_NS:
        badges.append('<span class="badge">qo\'shimcha — oila to\'liq bo\'lsin</span>')
    if g:
        badges.append(f'<a class="badge grp" href="savollar/guruh-{g["g"]:03d}.html">chalg\'ituvchi · {g["g"]}-guruh</a>')
    img = f'<img class="qimg" loading="lazy" src="rasmlar/{html.escape(local_img(b["img"]))}" alt="rasm">' if b.get("img") else ""
    answers = "".join(
        f'<button class="ans" data-c="{1 if k == b["correct"] else 0}" data-k="{k}"><b>F{k + 1}</b><span>{html.escape(a)}</span></button>'
        for k, a in enumerate(b["answers"])
    )
    mine = " mine" if n in stubborn else ""
    return (
        f'<article class="card{mine}" data-n="r-{n}" data-search="{html.escape(text[n])}">'
        f'<div class="meta">{"".join(badges)}</div>{img}<h3 class="q">{html.escape(b["q"])}</h3>'
        f'<div class="answers">{answers}</div></article>'
    )


def answer_table(items):
    rows = "".join(
        f'<tr class="{"mine" if b["n"] in stubborn else ""}"><td class="n">#{b["n"]}</td>'
        f'<td>{html.escape(b["q"])}</td><td class="a">{html.escape(correct[b["n"]])}</td></tr>'
        for b in items
    )
    return (
        f'<details class="key sheet"><summary>Javoblar jadvali ({len(items)} ta) — yodlash uchun</summary>'
        f'<div class="tablewrap"><table><thead><tr><th>Savol</th><th>Matn</th><th>To\'g\'ri javob</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div></details>'
    )


DAY_PLAN = {
    1: "Ertalab: raqamlar jadvalini yozib chiqing va yodlang. Tushdan keyin: to'xtash qoidalari. Kechqurun: chiziqlar + 3 ta imtihon simulyatsiyasi.",
    2: "Ertalab: yo'l belgilari (eng katta bo'lim). Tushdan keyin: yuk/gabarit va shatakka. Kechqurun: 1-kun xatolarini takror + 3 sim.",
    3: "Ertalab: manyovr. Tushdan keyin: chorraha algoritmi. Kechqurun: texnik, ta'riflar, tibbiyot + 3 sim.",
    4: "Faqat takror: yuqoridagi «faqat xato qilganlarim» belgisini qo'ying va qolganini yeching. So'ng 5 marta real imtihon rejimi — ketma-ket 3 marta o'tsangiz tayyorsiz.",
}

sections = []
for day in (1, 2, 3, 4):
    day_blocks = [bl for bl in blocks if bl["day"] == day and bl["items"]]
    total = sum(len(bl["items"]) for bl in day_blocks)
    sections.append(
        f'<div class="day" data-day="{day}"><h2>{day}-kun — {total} ta savol</h2>'
        f'<p class="plan">{html.escape(DAY_PLAN[day])}</p>'
        f'<div class="bar-wrap"><div class="bar-fill"></div></div>'
        f'<p class="plan dstat"></p></div>'
    )
    for bl in day_blocks:
        sections.append(
            f'<section class="group" data-day="{day}" id="b-{bl["slug"]}">'
            f'<header class="ghead"><div class="blockhead"><span class="kind">{day}-kun</span>'
            f'<h2>{html.escape(bl["title"])} — {len(bl["items"])} ta</h2>'
            f'<label><input type="checkbox" class="blockdone" data-blok="{bl["slug"]}"> tugatdim</label>'
            f'<span class="blockprog"></span></div>'
            f'<p class="gsub">{html.escape(bl["sub"])}</p></header>'
            + answer_table(bl["items"])
            + f'<div class="grid">{"".join(card(b) for b in bl["items"])}</div></section>'
        )

reja_body = (
    f'<p class="stats"><a href="index.html">← Bosh sahifa</a> · <a href="shpargalka.html">Shpargalka (qoidalar va jadvallar)</a><br>'
    f'Sizning xatolaringiz va {len(EXTRA_NS)} ta qo\'shimcha savol — jami {len(pool)} ta. Qizil ramka — ikkala ro\'yxatda ham turgan '
    f'<b>{len(stubborn)} ta o\'jar</b> savol, ularga ko\'proq vaqt bering. '
    f'Har blokdagi «Javoblar jadvali» — o\'sha blokning shpargalkasi.</p>'
    + "".join(sections)
)

def page(title, body, extra_bar=""):
    return f"""<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}{EXTRA_CSS}</style></head>
<body><div class="bar"><div class="wrap"><a class="home" href="index.html">⌂ Bosh sahifa</a><h1>{html.escape(title)}</h1>
<input id="search" type="search" placeholder="Qidirish…">{extra_bar}
<div class="seg" role="group" aria-label="Rejim"><button data-mode="solve" aria-pressed="true">Yechish</button><button data-mode="memo" aria-pressed="false">Yodlash</button></div>
<button class="btn" id="reset">Qayta boshlash</button><button class="btn" id="theme" aria-label="Yorug'/qorong'i rejim">◐</button>
<span class="score" id="score"></span></div></div>
<div class="wrap">{body}</div><a class="totop" href="#top" aria-label="Tepaga">↑</a>
<script>{JS}</script><script>{EXTRA_JS}</script></body></html>"""


open(os.path.join(ROOT, "reja.html"), "w", encoding="utf-8").write(
    page("4 kunlik reja", reja_body, '<label class="filterbar"><input type="checkbox" id="onlywrong"> faqat xato qilganlarim</label>')
)

sheet_sections = []
for title, sub, items in SHEETS:
    rows = "".join(
        f'<tr class="{"mine" if b["n"] in err_ns else ""}"><td class="n">#{b["n"]}</td>'
        f'<td>{html.escape(b["q"])}</td><td class="a">{html.escape(correct[b["n"]])}</td></tr>'
        for b in items
    )
    sheet_sections.append(
        f'<section class="group sheet"><header class="ghead"><h2>{html.escape(title)} — {len(items)} ta</h2>'
        f'<p class="gsub">{html.escape(sub)} · qizil raqam = siz xato qilgan savol</p></header>'
        f'<div class="tablewrap"><table><thead><tr><th>Savol</th><th>Matn</th><th>To\'g\'ri javob</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div></section>'
    )

shpargalka_body = (
    f'<p class="stats"><a href="index.html">← Bosh sahifa</a> · <a href="reja.html">4 kunlik reja</a><br>'
    f'Bu yerdagi har bir qator — bazadagi savolning <b>to\'g\'ri javobi</b>, o\'ylab topilgan qoida emas. '
    f'Raqamlar o\'sish tartibida — shunday yodlash oson.</p>'
    + "".join(sheet_sections)
    + f'<section class="group"><header class="ghead"><h2>Chorraha algoritmi</h2>'
      f'<p class="gsub">har chorraha savolida shu 4 qadamni tartib bilan yuriting</p></header>{ALGORITHM}</section>'
)
open(os.path.join(ROOT, "shpargalka.html"), "w", encoding="utf-8").write(page("Shpargalka", shpargalka_body))

hub = os.path.join(ROOT, "index.html")
s = open(hub, encoding="utf-8").read()
day_counts = " · ".join(f"{d}-kun {sum(len(bl['items']) for bl in blocks if bl['day'] == d)}" for d in (1, 2, 3, 4))
card_html = (
    f'{MARK_START}<article class="hub" data-page="reja"><div class="hub-top"><span class="step">8</span>'
    f'<h3><a href="reja.html">4 kunlik reja</a></h3></div>'
    f'<p class="desc">Faqat xatolaringiz, kun-kun bloklarga bo\'lingan. Shpargalka va javoblar jadvali bilan.</p>'
    f'<div class="chips"><span>{len(pool)} savol</span><span>{len(stubborn)} o\'jar</span><span>{html.escape(day_counts)}</span></div>'
    f'<div class="prog" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-label="Reja progressi"><div class="fill"></div></div>'
    f'<div class="prog-row"><span class="prog-text"></span><b class="pct">0%</b></div>'
    f'<div class="actions"><span class="open">Ochish →</span><button class="reset" type="button" hidden>Qayta boshlash</button></div></article>{MARK_END}'
)
s = re.sub(re.escape(MARK_START) + ".*?" + re.escape(MARK_END), card_html, s, flags=re.S) if MARK_START in s \
    else s.replace('</div><p class="tip"', card_html + '</div><p class="tip"', 1)
m = re.search(r"const DATA=(\{.*?\});\nconst KEY=", s, re.S)
data = json.loads(m.group(1))
data["reja"] = {"ids": [f"r-{b['n']}" for b in pool], "ok": [b["correct"] for b in pool]}
s = s[: m.start(1)] + json.dumps(data, ensure_ascii=False) + s[m.end(1):]
open(hub, "w", encoding="utf-8").write(s)
print("yozildi: reja.html, shpargalka.html | bosh sahifada kartalar:", list(data))
