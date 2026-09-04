"""Render a tight, high-resolution crop of the text block on every page that still
has an unresolved line, so the remaining disagreements can be settled by eye."""
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "pages_raw"
OUT = ROOT / "review"
OUT.mkdir(exist_ok=True)


def text_bbox(im, thresh=140):
    g = np.asarray(im.convert("L"))
    dark = g < thresh
    # ignore the scanner's dark edges
    h, w = dark.shape
    dark[:, : int(w * 0.02)] = False
    dark[:, int(w * 0.98):] = False
    dark[: int(h * 0.01), :] = False
    dark[int(h * 0.99):, :] = False
    rows = np.where(dark.sum(axis=1) > 3)[0]
    cols = np.where(dark.sum(axis=0) > 3)[0]
    if not len(rows) or not len(cols):
        return (0, 0, w, h)
    pad = 40
    return (max(0, cols[0] - pad), max(0, rows[0] - pad),
            min(w, cols[-1] + pad), min(h, rows[-1] + pad))


def render(page_id, files, target_w=1900):
    src = RAW / files[0]
    im = Image.open(src)
    im = im.crop(text_bbox(im))
    if im.width < target_w:
        scale = target_w / im.width
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    im = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    dst = OUT / f"{page_id}.png"
    im.save(dst)
    return dst, im.size


if __name__ == "__main__":
    open_lines = json.load(open(ROOT / "ocr" / "open.json"))
    by_page = {}
    for o in open_lines:
        by_page.setdefault(o["page"], {"files": o["files"], "lines": []})
        by_page[o["page"]]["lines"].append(o)

    index = []
    for pid in sorted(by_page):
        dst, size = render(pid, by_page[pid]["files"])
        index.append(dict(page=pid, image=str(dst), size=size,
                          count=len(by_page[pid]["lines"])))
    (ROOT / "review" / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2))
    print(f"pages to review: {len(index)}   open lines: {len(open_lines)}")
