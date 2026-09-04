"""Tight single-line zooms for final contested readings."""
import json, sys
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter

ROOT = Path('/Users/pranavgangwal/Desktop/claude codes/nani-book')
recs = {r['id']: r for r in json.load(open(ROOT/'ocr'/'final.json'))}

def text_block(files):
    im = Image.open(ROOT/'pages_raw'/files[0]).convert('L')
    a = np.asarray(im); dark = a < 110
    keep = dark.mean(axis=0) < 0.35
    rows = np.where((dark & keep[None,:]).sum(axis=1) > 18)[0]
    cols = np.where((dark & keep[None,:]).sum(axis=0) > 5)[0]
    return im, (max(0,cols[0]-30), max(0,rows[0]-25),
                min(im.width,cols[-1]+30), min(im.height,rows[-1]+25))

def zoom(pid, idx, out):
    r = recs[pid]
    im, (x0,y0,x1,y1) = text_block(r['files'])
    lines = r['text'].split('\n')
    total = sum(1 for l in lines if l.strip()) + (1 if r.get('heading') else 0)
    before = sum(1 for l in lines[:idx] if l.strip()) + (1 if r.get('heading') else 0)
    h = y1-y0; lh = h/max(total,1)
    top = int(y0 + max(0,(before-0.55))*lh); bot = int(y0 + (before+1.65)*lh)
    c = im.crop((x0, top, x1, min(y1,bot)))
    s = min(3.2, 2000/c.width)
    c = c.resize((int(c.width*s), int(c.height*s)), Image.LANCZOS)
    a = np.asarray(c, dtype=np.float32)
    bg = np.asarray(c.filter(ImageFilter.GaussianBlur(45)), dtype=np.float32)
    out_img = ImageOps.autocontrast(Image.fromarray(np.clip(a-bg+230,0,255).astype(np.uint8)), cutoff=0.4)
    out_img.save(out)

targets = json.loads(sys.argv[1])
D = Path(sys.argv[2]); D.mkdir(exist_ok=True)
for pid, idx in targets:
    zoom(pid, int(idx), D/f"{pid}_L{idx}.png")
    print(pid, idx)
