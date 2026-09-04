"""Cut, for each page that still has unresolved lines, the region of the scan those
lines fall in - magnified enough that every matra is unambiguous.

The position of a line is estimated from how far down the transcription it sits, and
the window is padded generously, so exact line detection is never required: the lines
are identified by reading them, not by trusting the crop.
"""
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "pages_raw"
OUT = ROOT / "review_win"
OUT.mkdir(exist_ok=True)

PAD_UP, PAD_DOWN = 0.10, 0.13     # generous margin around the estimated span
MAX_SPAN = 0.62                   # taller than this and the window is split in two


def text_block(files):
    """The printed area of the page, with the scanner's dark edges trimmed off."""
    im = Image.open(RAW / files[0]).convert("L")
    a = np.asarray(im)
    dark = a < 110
    keep = dark.mean(axis=0) < 0.35            # drop the dark page-block edge
    ink_rows = (dark & keep[None, :]).sum(axis=1)
    rows = np.where(ink_rows > 18)[0]
    cols = np.where((dark & keep[None, :]).sum(axis=0) > 5)[0]
    if not len(rows) or not len(cols):
        return im, (0, 0, im.width, im.height)
    box = (max(0, cols[0] - 30), max(0, rows[0] - 25),
           min(im.width, cols[-1] + 30), min(im.height, rows[-1] + 25))
    return im, box


def positions(text, has_heading, keys):
    lines = text.split("\n")
    total = sum(1 for l in lines if l.strip()) + (1 if has_heading else 0)
    total = max(total, 1)
    out = []
    for k in keys:
        before = sum(1 for l in lines[:int(k)] if l.strip()) + (1 if has_heading else 0)
        out.append(before / total)
    return out


def render(page_id, files, text, has_heading, keys):
    im, box = text_block(files)
    x0, y0, x1, y1 = box
    block_h = y1 - y0
    pos = positions(text, has_heading, keys)
    lo = max(0.0, min(pos) - PAD_UP)
    hi = min(1.0, max(pos) + PAD_DOWN)

    spans = [(lo, hi)]
    if hi - lo > MAX_SPAN:
        mid = (lo + hi) / 2
        spans = [(lo, min(1.0, mid + 0.06)), (max(0.0, mid - 0.06), hi)]

    made = []
    for n, (a, b) in enumerate(spans):
        top = int(y0 + a * block_h)
        bot = int(y0 + b * block_h)
        crop = im.crop((x0, top, x1, bot))
        # scale so the long side lands near 2000px, the most the viewer will show
        scale = min(2.6, 2000 / max(crop.width, crop.height))
        if scale > 1:
            crop = crop.resize((int(crop.width * scale), int(crop.height * scale)),
                               Image.LANCZOS)
        crop = ImageOps.autocontrast(crop, cutoff=1)
        name = f"{page_id}.png" if len(spans) == 1 else f"{page_id}_{n + 1}.png"
        crop.save(OUT / name)
        made.append(name)
    return made


if __name__ == "__main__":
    open_lines = json.load(open(ROOT / "ocr" / "open.json"))
    recs = {r["id"]: r for r in json.load(open(ROOT / "ocr" / "final.json"))}
    by_page = {}
    for o in open_lines:
        by_page.setdefault(o["page"], []).append(o)

    manifest = []
    for pid, items in sorted(by_page.items()):
        num = [i for i in items if str(i["key"]).isdigit()]
        if not num:
            continue
        r = recs[pid]
        imgs = render(pid, r["files"], r["text"], bool(r.get("heading")),
                      [i["key"] for i in num])
        manifest.append(dict(page=pid, images=imgs, printed=r.get("printed"),
                             heading=r.get("heading"),
                             lines=[dict(key=i["key"], a=i["gpt55"], b=i["gpt54"])
                                    for i in num]))
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("pages:", len(manifest),
          " images:", sum(len(m["images"]) for m in manifest),
          " lines:", sum(len(m["lines"]) for m in manifest))
