"""For every unresolved line, cut the actual printed line out of the scan and stack
the cut-outs into one tall strip per page, so each disagreement can be read at full
magnification instead of squinting at a whole page.

Lines are located by horizontal projection: each band of rows containing ink is one
printed line. Band 0 is the page heading when the page has one, after which bands run
in the same order as the non-empty lines of the transcription.
"""
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "pages_raw"
OUT = ROOT / "review_lines"
OUT.mkdir(exist_ok=True)

GAP = 26            # white space between stacked cut-outs
CONTEXT = 6         # rows of padding kept around each line


def load_page(files):
    im = Image.open(RAW / files[0]).convert("L")
    a = np.asarray(im)
    dark = a < 150
    h, w = dark.shape
    dark[:, : int(w * .03)] = False
    dark[:, int(w * .97):] = False
    rows = np.where(dark.sum(axis=1) > 3)[0]
    cols = np.where(dark.sum(axis=0) > 3)[0]
    if not len(rows):
        return im, []
    box = (max(0, cols[0] - 30), max(0, rows[0] - 20),
           min(w, cols[-1] + 30), min(h, rows[-1] + 20))
    im = im.crop(box)
    return im, bands(np.asarray(im))


def bands(a, thresh=150, min_ink=4):
    """Rows of the page that carry ink, grouped into printed lines."""
    ink = (a < thresh).sum(axis=1)
    on = ink > min_ink
    out, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= 8:                 # ignore speckle
                out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(on)))
    # merge bands separated by less than a matra's gap (vowel signs sit apart)
    merged = []
    for b in out:
        if merged and b[0] - merged[-1][1] < 10:
            merged[-1] = (merged[-1][0], b[1])
        else:
            merged.append(list(b))
            merged[-1] = tuple(merged[-1])
    return [tuple(b) for b in merged]


def band_for(text, line_idx, has_heading):
    """Map a transcription line index onto a printed line band."""
    lines = text.split("\n")
    non_empty_before = sum(1 for l in lines[:line_idx] if l.strip())
    return non_empty_before + (1 if has_heading else 0)


def build(page_id, files, text, has_heading, keys):
    im, bs = load_page(files)
    if not bs:
        return None
    strips = []
    for k in keys:
        bi = band_for(text, int(k), has_heading)
        if bi >= len(bs):
            bi = len(bs) - 1
        lo = max(0, bs[bi][0] - CONTEXT)
        hi = min(im.height, bs[bi][1] + CONTEXT)
        strips.append(im.crop((0, lo, im.width, hi)))
    if not strips:
        return None
    w = max(s.width for s in strips)
    h = sum(s.height for s in strips) + GAP * (len(strips) - 1)
    canvas = Image.new("L", (w, h), 255)
    y = 0
    for s in strips:
        canvas.paste(s, (0, y))
        y += s.height + GAP
    # magnify so every matra is unambiguous
    scale = min(2.4, 1900 / max(1, canvas.width))
    if scale > 1:
        canvas = canvas.resize((int(canvas.width * scale), int(canvas.height * scale)),
                               Image.LANCZOS)
    canvas = ImageOps.autocontrast(canvas, cutoff=1)
    dst = OUT / f"{page_id}.png"
    canvas.save(dst)
    return dst


if __name__ == "__main__":
    open_lines = json.load(open(ROOT / "ocr" / "open.json"))
    recs = {r["id"]: r for r in json.load(open(ROOT / "ocr" / "final.json"))}
    by_page = {}
    for o in open_lines:
        by_page.setdefault(o["page"], []).append(o)

    manifest = []
    for pid, items in sorted(by_page.items()):
        keys = [i["key"] for i in items if str(i["key"]).isdigit()]
        if not keys:
            continue
        r = recs[pid]
        dst = build(pid, r["files"], r["text"], bool(r.get("heading")), keys)
        manifest.append(dict(page=pid, image=str(dst), keys=keys,
                             candidates=[dict(key=i["key"], gpt55=i["gpt55"], gpt54=i["gpt54"])
                                         for i in items if str(i["key"]).isdigit()]))
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("pages:", len(manifest), " lines:", sum(len(m["keys"]) for m in manifest))
