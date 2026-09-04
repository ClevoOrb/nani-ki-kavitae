"""Build the ordered page manifest: reading order -> all scan versions of that page.

Section dividers carry no printed page number, so they are placed by the numbered
page that shares their spread. One divider (नव प्रेरणा) was misread as page 53 by
the indexing pass and is corrected here.
"""
import json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
idx = json.load(open(ROOT / "ocr" / "index.json"))
by_file = {x["file"]: x for x in idx}

COVERS = {
    "front": "20260903143441_001.jpg",   # front cover, upright
    "front_alt": "20260903143148_002.jpg",  # same cover, scanned 180deg
    "back": "20260903155629_001.jpg",    # back cover, carries the author photo
}
COVER_SCANS = {v[:-4].rsplit("_", 1)[0] + "_" + v[:-4].rsplit("_", 1)[1] for v in COVERS.values()}
COVER_STEMS = {"20260903143441_001", "20260903143148_002", "20260903155629_001"}

# Unnumbered section dividers -> the printed page they immediately precede.
DIVIDERS = [
    ("20260903145926_006_R.jpg", "आत्मबोध", 1),
    ("20260903151409_002_L.jpg", "चिन्तन के स्वर", 23),
    ("20260903153013_010_L.jpg", "प्रकृति सौंदर्य", 52),
    ("20260903154324_002_R.jpg", "नव प्रेरणा", 68),
    ("20260903154324_009_L.jpg", "विविध", 80),
]
DIVIDER_FILES = {d[0] for d in DIVIDERS}

# Front matter, in reading order, before the first section divider.
FRONT = [
    "20260903145926_002_L.jpg", "20260903145926_002_R.jpg",
    "20260903145926_003_L.jpg", "20260903145926_003_R.jpg",
    "20260903145926_004_L.jpg", "20260903145926_004_R.jpg",
    "20260903145926_005_L.jpg", "20260903145926_005_R.jpg",
    "20260903145926_006_L.jpg",
]


def norm_num(x):
    n = x.get("page_number")
    if isinstance(n, str) and n.strip().isdigit():
        n = int(n.strip())
    return n if isinstance(n, int) else None


def scan_key(fname):
    scan, side = fname[:-4].rsplit("_", 1)
    return (scan, 0 if side == "L" else 1)


numbered = collections.defaultdict(list)
for x in idx:
    f = x["file"]
    stem = f[:-4].rsplit("_", 1)[0]
    if stem in COVER_STEMS or f in DIVIDER_FILES or f in FRONT:
        continue
    n = norm_num(x)
    if n is None:
        raise SystemExit(f"unplaced page with no number: {f}")
    numbered[n].append(f)

for n in numbered:
    numbered[n].sort(key=scan_key)

missing = [i for i in range(1, 91) if i not in numbered]
if missing:
    raise SystemExit(f"missing printed pages: {missing}")

pages = []


def add(pid, kind, files, heading="", printed=None, section=None):
    pages.append(dict(id=pid, kind=kind, printed=printed, heading=heading,
                      section=section, files=files))


for i, f in enumerate(FRONT, 1):
    m = by_file[f]
    add(f"front-{i:02d}", m.get("kind", "text"), [f], m.get("heading", ""))

div_at = {d[2]: d for d in DIVIDERS}
current_section = None
for n in range(1, 91):
    if n in div_at:
        f, title, _ = div_at[n]
        current_section = title
        add(f"div-{title}", "divider", [f], title, section=title)
    m = by_file[numbered[n][0]]
    add(f"p{n:03d}", "text", numbered[n], m.get("heading", ""), printed=n,
        section=current_section)

out = ROOT / "ocr" / "manifest.json"
out.write_text(json.dumps(dict(covers=COVERS, pages=pages), ensure_ascii=False, indent=2))

print("total leaves:", len(pages))
print("front matter:", sum(1 for p in pages if p["id"].startswith("front")))
print("dividers:", sum(1 for p in pages if p["kind"] == "divider"))
print("numbered:", sum(1 for p in pages if p["printed"]))
print("multi-version pages:", sorted(p["printed"] for p in pages if len(p["files"]) > 1))
print("version counts:", collections.Counter(len(p["files"]) for p in pages))
