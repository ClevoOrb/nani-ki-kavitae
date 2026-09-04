"""Collect what the proofreaders flagged, drop the noise, and render the survivors
for human review."""
import json, re, sys
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
from reconcile import norm

ROOT = Path(__file__).resolve().parent.parent
PROOF = ROOT / "ocr" / "proof"
RAW = ROOT / "pages_raw"
OUT = ROOT / "proof_win"
OUT.mkdir(exist_ok=True)

SKIP = {"front-08", "front-09"}          # rebuilt from verified headings


def trivial(a, b):
    """Differences the page cannot actually express, or that we deliberately keep."""
    def canon(s):
        s = norm(s or "")
        s = re.sub(r"[.…]{2,}", "…", s)
        s = re.sub(r"[•·]", ".", s)
        s = re.sub(r"[-–—]", "-", s)
        s = re.sub(r"\s*[.…]+\s*$", "", s)
        s = s.replace("ॄ", "ृ")
        return re.sub(r"\s+", "", s)
    return canon(a) == canon(b)


def collect():
    recs = {r["id"]: r for r in json.load(open(ROOT / "ocr" / "final.json"))}
    flags = {}
    for f in sorted(PROOF.glob("*.json")):
        d = json.load(open(f))
        pid = d["id"]
        if pid in SKIP:
            continue
        rec = recs[pid]
        lines = rec["text"].split("\n")
        for model in ("gpt55", "gpt54"):
            for m in (d.get(model) or []):
                try:
                    i = int(m["line"])
                except (KeyError, ValueError, TypeError):
                    continue
                if not (0 <= i < len(lines)):
                    continue
                cur, printed = lines[i], (m.get("printed") or "")
                if not printed.strip() or trivial(cur, printed):
                    continue
                key = (pid, i)
                flags.setdefault(key, {"current": cur, "claims": {}})
                flags[key]["claims"][model] = printed
    return recs, flags


def window(rec, idx_list):
    im = Image.open(RAW / rec["files"][0]).convert("L")
    a = np.asarray(im); dark = a < 110
    keep = dark.mean(axis=0) < 0.35
    rows = np.where((dark & keep[None, :]).sum(axis=1) > 18)[0]
    cols = np.where((dark & keep[None, :]).sum(axis=0) > 5)[0]
    if not len(rows):
        return None
    x0, y0, x1, y1 = (max(0, cols[0]-30), max(0, rows[0]-25),
                      min(im.width, cols[-1]+30), min(im.height, rows[-1]+25))
    lines = rec["text"].split("\n")
    total = sum(1 for l in lines if l.strip()) + (1 if rec.get("heading") else 0)
    pos = []
    for i in idx_list:
        before = sum(1 for l in lines[:i] if l.strip()) + (1 if rec.get("heading") else 0)
        pos.append(before / max(total, 1))
    lo, hi = max(0.0, min(pos)-0.10), min(1.0, max(pos)+0.13)
    top, bot = int(y0 + lo*(y1-y0)), int(y0 + hi*(y1-y0))
    c = im.crop((x0, top, x1, bot))
    s = min(2.6, 2000/max(c.width, c.height))
    if s > 1:
        c = c.resize((int(c.width*s), int(c.height*s)), Image.LANCZOS)
    return ImageOps.autocontrast(c, cutoff=1)


if __name__ == "__main__":
    recs, flags = collect()
    by_page = {}
    for (pid, i), v in flags.items():
        by_page.setdefault(pid, []).append((i, v))
    print(f"pages with flags : {len(by_page)}")
    print(f"lines flagged    : {len(flags)}")
    both = sum(1 for v in flags.values() if len(v["claims"]) == 2)
    print(f"  flagged by both proofreaders : {both}")
    print(f"  flagged by one               : {len(flags)-both}")
    manifest = []
    for pid in sorted(by_page):
        items = sorted(by_page[pid])
        img = window(recs[pid], [i for i, _ in items])
        name = f"{pid}.png"
        if img:
            img.save(OUT / name)
        manifest.append(dict(page=pid, image=name, printed=recs[pid].get("printed"),
                             heading=recs[pid].get("heading"),
                             lines=[dict(line=i, current=v["current"], claims=v["claims"])
                                    for i, v in items]))
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
