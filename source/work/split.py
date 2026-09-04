import os, sys, numpy as np
from PIL import Image

SRC = "/Users/pranavgangwal/Downloads/Nani book"
OUT = "/Users/pranavgangwal/Desktop/claude codes/nani-book/pages_raw"

def find_fold(gray):
    h, w = gray.shape
    # look in central 40% band for darkest horizontal row (the book gutter)
    lo, hi = int(h*0.30), int(h*0.70)
    rowmean = gray[lo:hi].mean(axis=1)
    # smooth with edge padding (zero-padding would bias the array ends downward)
    k = 25
    pad = np.pad(rowmean, k//2, mode='edge')
    sm = np.convolve(pad, np.ones(k)/k, mode='valid')
    return lo + int(np.argmin(sm))

def process(fn):
    im = Image.open(os.path.join(SRC, fn)).convert("RGB")
    g = np.asarray(im.convert("L"), dtype=np.float32)
    fold = find_fold(g)
    w, h = im.size
    top = im.crop((0, 0, w, fold))
    bot = im.crop((0, fold, w, h))
    # rotate 90 clockwise -> top becomes RIGHT page, bottom becomes LEFT page
    top = top.rotate(-90, expand=True)
    bot = bot.rotate(-90, expand=True)
    base = os.path.splitext(fn)[0]
    top.save(os.path.join(OUT, base + "_R.jpg"), quality=95)
    bot.save(os.path.join(OUT, base + "_L.jpg"), quality=95)
    return fold, h

if __name__ == "__main__":
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".jpg"))
    if len(sys.argv) > 1:
        files = [f for f in files if f in sys.argv[1:]]
    for f in files:
        fold, h = process(f)
        print(f, "fold", fold, "/", h, "=%.2f" % (fold/h))
