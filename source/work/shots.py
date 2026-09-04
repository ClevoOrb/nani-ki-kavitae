"""Render the site at real device widths and lay the results out as contact
sheets, so every breakpoint can actually be looked at rather than reasoned about.

Usage:  python3 shots.py <view> [sizes...]
        views: hero | books | about | gift | reader | toc | divider
"""
import subprocess, sys, urllib.parse
from pathlib import Path
from PIL import Image, ImageDraw

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = Path("/private/tmp/claude-501/-Users-pranavgangwal-Desktop-claude-codes/"
           "eca67227-21c9-4bd7-8f1d-be8015e7dc2e/scratchpad/shots")
OUT.mkdir(parents=True, exist_ok=True)

PHONE = [(320, 568), (375, 667), (390, 844), (430, 932)]
TABLET = [(600, 900), (768, 1024), (1024, 768)]
DESK = [(1280, 800), (1440, 900), (1920, 1080)]

JUMP = ('var s=document.getElementById("slider");s.value=%d;'
        's.dispatchEvent(new Event("input",{bubbles:true}));'
        's.dispatchEvent(new Event("change",{bubbles:true}));')

VIEWS = {
    "hero":    ("index.html", "", 2600),
    "books":   ("index.html", 'document.getElementById("kitaben").scrollIntoView()', 3000),
    "about":   ("index.html", 'document.querySelector(".about").scrollIntoView()', 3000),
    "gift":    ("index.html", 'document.querySelector(".gift").scrollIntoView()', 3000),
    "reader":  ("index.html", 'document.getElementById("btnRead").click();'
                              'setTimeout(function(){%s},2200);' % (JUMP % 41), 9000),
    "divider": ("index.html", 'document.getElementById("btnRead").click();'
                              'setTimeout(function(){%s},2200);' % (JUMP % 63), 9000),
    "toc":     ("index.html", 'document.getElementById("btnRead").click();'
                              'setTimeout(function(){document.getElementById("btnToc").click();},2200);', 9000),
}


def shot(view, w, h):
    url, act, budget = VIEWS[view]
    q = f"_vp.html?w={w}&h={h}&u={url}"
    if act:
        q += "&act=" + urllib.parse.quote(act)
    png = OUT / f"{view}_{w}x{h}.png"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={max(520, w + 24)},{h + 24}",
                    f"--virtual-time-budget={budget}",
                    f"--screenshot={png}", f"http://localhost:8899/{q}"],
                   capture_output=True)
    im = Image.open(png).convert("RGB").crop((0, 0, w, h))
    return im


def sheet(view, sizes, name):
    tiles, scale = [], 1
    ims = [(w, h, shot(view, w, h)) for w, h in sizes]
    maxh = max(i.height for _, _, i in ims)
    cap = 30
    total_w = sum(i.width for _, _, i in ims) + 16 * (len(ims) + 1)
    board = Image.new("RGB", (total_w, maxh + cap + 20), (46, 46, 46))
    d = ImageDraw.Draw(board)
    x = 16
    for w, h, im in ims:
        board.paste(im, (x, cap))
        d.text((x + 2, 9), f"{w} x {h}", fill=(255, 235, 190))
        d.rectangle([x - 1, cap - 1, x + w, cap + h], outline=(120, 120, 120))
        x += w + 16
    p = OUT / f"sheet_{view}_{name}.png"
    board.save(p)
    print(p)
    return p


if __name__ == "__main__":
    view = sys.argv[1]
    group = sys.argv[2] if len(sys.argv) > 2 else "phone"
    sizes = {"phone": PHONE, "tablet": TABLET, "desk": DESK}[group]
    sheet(view, sizes, group)
