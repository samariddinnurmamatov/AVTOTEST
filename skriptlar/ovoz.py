"""Ovozli sharh fayllarini yasaydi (macOS say + afconvert) va ro'yxatini yozadi.

python3 ovoz.py            # faqat yo'q fayllarni yasaydi
python3 ovoz.py --force    # hammasini qayta yasaydi
Matnlar: data/ovoz-matn/batch-*.json ([{n, text}, ...])
Natija:  ovoz/r-<n>.m4a va ovozlar.json
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS = os.path.join(ROOT, "data", "ovoz-matn")
OUT = os.path.join(ROOT, "ovoz")
VOICE = os.environ.get("OVOZ_VOICE", "Yelda")   # turkcha ovoz o'zbek lotiniga eng yaqin
RATE = os.environ.get("OVOZ_RATE", "175")
BITRATE = "24000"
FORCE = "--force" in sys.argv

# O'zbek lotinini turkcha imloga yaqinlashtirish — talaffuz to'g'riroq chiqadi.
REPL = [
    ("o‘", "o"), ("o'", "o"), ("O‘", "O"), ("O'", "O"),
    ("g‘", "ğ"), ("g'", "ğ"), ("G‘", "Ğ"), ("G'", "Ğ"),
    ("ʻ", ""), ("’", ""), ("‘", ""),
    ("sh", "ş"), ("Sh", "Ş"), ("SH", "Ş"),
    ("ch", "ç"), ("Ch", "Ç"), ("CH", "Ç"),
    ("x", "h"), ("X", "H"), ("q", "k"), ("Q", "K"), ("w", "v"),
]


def to_tts(s):
    s = s.replace("km/s", "kilometr soatiga").replace("km/soat", "kilometr soatiga")
    for a, b in REPL:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def load_texts():
    out = {}
    for f in sorted(glob.glob(os.path.join(TEXTS, "batch-*.json"))):
        try:
            for item in json.load(open(f, encoding="utf-8")):
                if item.get("n") and item.get("text"):
                    out[int(item["n"])] = item["text"].strip()
        except Exception as e:  # noqa: BLE001
            print("o'qib bo'lmadi:", f, e)
    return out


def render(job):
    n, text = job
    path = os.path.join(OUT, f"r-{n}.m4a")
    if os.path.isfile(path) and os.path.getsize(path) > 0 and not FORCE:
        return None
    raw = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False).name
    try:
        subprocess.run(["say", "-v", VOICE, "-r", RATE, "-o", raw, "--data-format=aac", to_tts(text)],
                       check=True, capture_output=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", BITRATE, raw, path],
                       check=True, capture_output=True)
        return None
    except subprocess.CalledProcessError as e:
        return f"#{n}: {e.stderr.decode()[:120]}"
    finally:
        os.path.exists(raw) and os.remove(raw)


texts = load_texts()
os.makedirs(OUT, exist_ok=True)
print(f"matnlar: {len(texts)} ta | ovoz: {VOICE} | tezlik: {RATE}")
with ThreadPoolExecutor(4) as pool:
    errors = [e for e in pool.map(render, sorted(texts.items())) if e]
files = sorted(f"/ovoz/{f}" for f in os.listdir(OUT) if f.endswith(".m4a"))
json.dump(files, open(os.path.join(ROOT, "ovozlar.json"), "w", encoding="utf-8"), ensure_ascii=False)
size = sum(os.path.getsize(os.path.join(OUT, os.path.basename(f))) for f in files)
print(f"tayyor: {len(files)} ta fayl, {size / 1024 / 1024:.1f} MB | xatolar: {errors[:3] or 0}")
print("ovozlar.json yozildi")
