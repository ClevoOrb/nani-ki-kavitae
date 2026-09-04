"""Pass 4: turn the adjudicated text into the static htmx site."""
import hashlib, html, json, re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
FRAG = SITE / "fragments"
DATA = SITE / "data"
ASSETS = SITE / "assets"
for d in (FRAG, DATA, ASSETS):
    d.mkdir(parents=True, exist_ok=True)

SECTIONS = [
    ("आत्मबोध",        "#FFC95C", "#EFA61F"),
    ("चिन्तन के स्वर", "#C3AEF5", "#8E6FE0"),
    ("प्रकृति सौंदर्य", "#74D8B4", "#34B389"),
    ("नव प्रेरणा",      "#FFA6C4", "#EE6D9C"),
    ("विविध",          "#8FC7F5", "#4E9FDD"),
]
TINT = {s[0]: s[1] for s in SECTIONS}
ACCENT = {s[0]: s[2] for s in SECTIONS}

FRONT_TITLES = {
    "front-02": "कवर पन्ना",
    "front-03": "प्रकाशन",
    "front-04": "मेरा कवि मन",
    "front-05": "मेरा परिवार",
    "front-06": "संपादकीय",
    "front-08": "विषय सूची",
    "front-09": "विषय सूची",
}


# The front matter is a title page, a colophon and several pages of prose —
# none of it is verse, and rendering it as verse is what left those pages
# looking empty.
FRONT_KIND = {
    "front-01": "blank",
    "front-02": "title",
    "front-03": "colophon",
}

STAR = re.compile(r"^[*∗✳\s]+$")


def esc(s):
    return html.escape(s or "")


TRAILING_STAR = re.compile(r"^(.*?\S)\s+([*∗✳]{2,})\s*$")


def normalise_stars(text):
    """The *** poem rule is sometimes set flush right on the last verse line rather
    than on a line of its own; give it its own line so it reads as a separator."""
    out = []
    for ln in (text or "").split("\n"):
        m = TRAILING_STAR.match(ln)
        if m:
            out.append(m.group(1))
            out.append(m.group(2))
        else:
            out.append(ln)
    return "\n".join(out)


def body_lines(text):
    return [ln for ln in normalise_stars(text).split("\n") if ln.strip()]


def find_poems(section_pages):
    """Split a section into poems.

    The book marks the end of every poem with a *** rule, so a new poem begins at
    the first line after one (and at the start of a section). A page heading titles
    the poem when the poem opens at the top of that page; a heading on a page where
    a poem is still running is a sub-heading of that poem - which is how the ten
    lakshanas and the sixteen bhavanas are printed. Untitled poems, as in the
    विविध section, take their first line as their title.
    """
    poems, current, running = [], None, False
    for idx, page, rec in section_pages:
        lines = body_lines(rec.get("text"))
        heading = rec.get("heading") or ""
        heading_used = False

        if running and heading and current is not None:
            current["subs"].append(dict(title=heading, index=idx))
            heading_used = True

        for j, ln in enumerate(lines):
            if STAR.match(ln):
                running = False
                continue
            if running:
                continue
            if j == 0 and heading and not heading_used:
                title = heading
                heading_used = True
            else:
                title = ln.strip().rstrip(",;।॥")
            current = dict(title=title, index=idx, printed=page.get("printed"), subs=[])
            poems.append(current)
            running = True
    return poems


def verse_html(text):
    """Render the poem body, turning the printed *** rule into a real separator."""
    out = []
    body = normalise_stars(text).strip("\n")
    for block in body.split("\n"):
        if re.fullmatch(r"\s*[*∗]{2,}\s*", block):
            out.append('<span class="sep">✳ ✳ ✳</span>')
        else:
            out.append(esc(block))
    return "\n".join(out)


def prose_html(text):
    """Prose, unlike verse, should re-wrap: the line breaks in the scan are
       where the printed column ended, not where the author broke a line."""
    paras = []
    for block in re.split(r"\n\s*\n", text.strip()):
        joined = " ".join(ln.strip() for ln in block.split("\n") if ln.strip())
        if joined:
            paras.append(f"<p>{esc(joined)}</p>")
    return "".join(paras)


def title_page_fragment(rec):
    lines = [ln.strip(" •\t") for ln in rec.get("text", "").split("\n") if ln.strip(" •\t")]
    author = lines[0] if lines else "रूक्मिणी बड़जातिया"
    return ('<div class="page title-page">'
            '<div class="tp-orn"></div>'
            '<p class="tp-kind">काव्य संग्रह</p>'
            f'<h1>{esc(rec.get("heading") or "उन्मुक्त मन")}</h1>'
            '<div class="tp-rule"></div>'
            f'<p class="tp-author">{esc(author)}</p>'
            '<div class="tp-orn flip"></div>'
            '</div>')


def colophon_fragment(rec):
    """The imprint is a handful of label/value pairs — set them as such and
       centre them, rather than letting 170 characters rattle around a page."""
    rows = []
    for block in re.split(r"\n\s*\n", rec.get("text", "").strip()):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if lines[0].rstrip().endswith(":"):
            rows.append(f'<dt>{esc(lines[0].rstrip(": "))}</dt>'
                        f'<dd>{esc(" ".join(lines[1:]))}</dd>')
        else:
            for ln in lines:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    rows.append(f'<dt>{esc(k.strip())}</dt><dd>{esc(v.strip())}</dd>')
                else:
                    rows.append(f'<dd class="lone">{esc(ln)}</dd>')
    return ('<div class="page colophon">'
            f'<h2>{esc(rec.get("heading") or "प्रकाशन")}</h2>'
            f'<dl>{"".join(rows)}</dl>'
            '<div class="col-orn"></div></div>')


def prose_page_fragment(rec, accent):
    """A drop cap is only safe when the first cluster is a plain letter — on a
       conjunct like स्ट, ::first-letter takes the स and orphans the virama."""
    num = f'<div class="page-num">({rec["printed"]})</div>' if rec.get("printed") else ""
    h = f'<h2>{esc(rec["heading"])}</h2>' if rec.get("heading") else ""
    body = prose_html(rec.get("text", ""))
    # Only a virama immediately after the first letter matters (\u0938\u094d\u091f). One
    # deeper in the word belongs to a later cluster and is harmless (\u092e\u0927\u094d\u092f).
    opening = re.sub(r"<[^>]+>", "", body)[:2]
    cap = "" if opening[1:2] == "\u094d" else " has-cap"
    return (f'<div class="page prose-page" style="--accent:{accent}">{h}'
            f'<div class="prose{cap}">{body}</div>{num}</div>')


def page_fragment(rec, section):
    accent = ACCENT.get(section, "#EFA61F")
    heading = rec.get("heading") or ""
    body = verse_html(rec.get("text", ""))
    num = f'<div class="page-num">({rec["printed"]})</div>' if rec.get("printed") else ""
    h = f'<h2>{esc(heading)}</h2>' if heading else ""
    # "leaf" marks the pages that carry verse, so the ornamental treatment
    # lands on those and not on the covers, dividers or contents pages.
    return (f'<div class="page leaf-page" style="--accent:{accent}">{h}'
            f'<div class="verse">{body}</div>{num}</div>')


# The book's own two-column contents pages defeat page-level OCR (voters read one
# column, or interleave the two). They are rebuilt here from the per-page headings,
# which were transcribed and adjudicated individually. The epigraph beneath the
# second one was proof-read against the scan by hand.
EPIGRAPH = """परस्परोपग्रहो जीवानाम् ॥

एक ऐसा मंत्र, जो देता प्रत्येक जीव को महत्वपूर्ण सन्देश,
है परस्पर अवलम्बित् हम सब बँधे हैं अटूट बन्धन में।

हम सब जिएँ प्यार से, अपनत्व और शान्ति से,
परस्पर सहारा बन, सँवारे जिन्दगी खूबसूरती से॥"""


def toc_page_fragment(groups, tail_title=None, epigraph=None):
    cols = []
    for title, items in groups:
        lis = "".join(f"<li>{esc(t)}</li>" for t in items)
        cols.append(f'<div class="toc-col"><h3 style="--accent:{ACCENT[title]}">{esc(title)}</h3>'
                    f'<ul>{lis}</ul></div>')
    tail = ""
    if tail_title:
        tail = (f'<h3 class="toc-tail" style="--accent:{ACCENT[tail_title]}">'
                f'{esc(tail_title)}</h3>')
    epi = ""
    if epigraph:
        epi = f'<div class="epigraph">{esc(epigraph)}</div>'
    return ('<div class="page toc-page"><div class="toc-cols">' + "".join(cols) +
            '</div>' + tail + epi + '</div>')


def divider_fragment(title, count):
    tint, accent = TINT[title], ACCENT[title]
    return (f'<div class="page divider" style="--tint:{tint}">'
            f'<p class="eyebrow">खंड</p><h1>{esc(title)}</h1>'
            f'<div class="rule" style="background:{accent}"></div>'
            f'<p class="count">{count} कविताएँ</p></div>')


def build():
    man = json.load(open(ROOT / "ocr" / "manifest.json"))
    recs = {r["id"]: r for r in json.load(open(ROOT / "ocr" / "final.json"))}

    # Reading order of the leaves, so a poem's TOC entry can point at a page index.
    order = {}
    n = 1                       # index 0 is the front cover
    for p in man["pages"]:
        order[p["id"]] = n
        n += 1

    # Group the numbered pages by section, then split each section into poems.
    by_section = {s[0]: [] for s in SECTIONS}
    for p in man["pages"]:
        r = recs.get(p["id"])
        if p["kind"] == "divider" or not r or not p.get("section"):
            continue
        by_section[p["section"]].append((order[p["id"]], p, r))

    poems = {name: find_poems(pages) for name, pages in by_section.items()}
    counts = {name: len(v) for name, v in poems.items()}
    titles = {name: [x["title"] for x in v] for name, v in poems.items()}

    toc_pages = {
        "front-08": dict(groups=[("आत्मबोध", titles["आत्मबोध"]),
                                 ("चिन्तन के स्वर", titles["चिन्तन के स्वर"])]),
        "front-09": dict(groups=[("प्रकृति सौंदर्य", titles["प्रकृति सौंदर्य"]),
                                 ("नव प्रेरणा", titles["नव प्रेरणा"])],
                         tail_title="विविध", epigraph=EPIGRAPH),
    }

    pages, toc = [], []
    cur_section = None

    def emit(pid, frag, meta):
        FRAG.joinpath(pid + ".html").write_text(frag, encoding="utf-8")
        pages.append(meta)

    # --- front cover ---
    emit("cover-front",
         '<div class="page cover"><img src="assets/cover.webp" alt="उन्मुक्त मन" '
         'width="940" height="1409" loading="lazy" decoding="async"></div>',
         dict(id="cover-front", kind="cover", printed=None, heading="कवर", section=None))

    for p in man["pages"]:
        r = recs.get(p["id"])
        if p["kind"] == "divider":
            title = p["heading"]
            cur_section = title
            emit(p["id"], divider_fragment(title, counts[title]),
                 dict(id=p["id"], kind="divider", printed=None, heading=title, section=title))
            toc.append(dict(title=title, tint=TINT[title], accent=ACCENT[title],
                            start=len(pages) - 1,
                            items=[dict(title=x["title"], index=x["index"],
                                        printed=x["printed"],
                                        subs=[dict(title=s["title"], index=s["index"])
                                              for s in x["subs"]])
                                   for x in poems[title]]))
            continue

        if not r:
            continue

        if p["id"] in toc_pages:
            emit(p["id"], toc_page_fragment(**toc_pages[p["id"]]),
                 dict(id=p["id"], kind="toc", printed=None,
                      heading="विषय सूची", section=None))
            continue

        text = r.get("text", "").strip()
        heading = r.get("heading") or FRONT_TITLES.get(p["id"], "")
        rec = dict(r, heading=heading)
        kind = FRONT_KIND.get(p["id"])
        if kind == "title":
            frag = title_page_fragment(dict(rec, heading="उन्मुक्त मन"))
        elif kind == "colophon":
            frag = colophon_fragment(rec)
        elif kind == "blank" or (not text and not heading):
            frag = '<div class="page blank-page"></div>'
            kind = "blank"      # so the reader can step over it on a phone
        elif p["id"].startswith("front-"):
            frag = prose_page_fragment(rec, ACCENT["आत्मबोध"])
        else:
            frag = page_fragment(rec, p.get("section"))
        emit(p["id"], frag,
             dict(id=p["id"], kind=(kind or p["kind"]), printed=p.get("printed"),
                  heading=heading, section=p.get("section")))

    # --- back cover ---
    emit("cover-back",
         '<div class="page cover" style="background:linear-gradient(#FBF2D8 0 55%, #FFC95C 55% 100%)">'
         '<img src="assets/back-cover.webp" alt="पिछला कवर" '
         'width="931" height="1410" loading="lazy" decoding="async"></div>',
         dict(id="cover-back", kind="cover", printed=None, heading="पिछला कवर", section=None))

    poem_count = sum(len(s["items"]) for s in toc)
    # A content hash of every fragment. The reader appends it to fragment URLs
    # so a rebuild can never be masked by a stale copy in someone's cache.
    h = hashlib.sha1()
    for f in sorted(FRAG.glob("*.html")):
        h.update(f.read_bytes())
    version = h.hexdigest()[:10]
    DATA.joinpath("book.json").write_text(json.dumps(
        dict(pages=pages, toc=toc, poemCount=poem_count, version=version,
             printedCount=sum(1 for p in pages if p["printed"])),
        ensure_ascii=False, indent=2), encoding="utf-8")

    # The scans are ~1670px wide but are never shown above ~470px, so they are
    # downscaled and re-encoded to WebP on the way in — same picture, a tenth
    # of the bytes.
    for name, box, q in (("cover.jpg", (940, 1410), 86),
                         ("back-cover.jpg", (940, 1410), 86)):
        src = ROOT / "assets" / name
        if src.exists():
            im = Image.open(src).convert("RGB")
            im.thumbnail(box, Image.LANCZOS)
            im.save(ASSETS / (Path(name).stem + ".webp"), "WEBP", quality=q, method=6)

    print(f"version   : {version}")
    print(f"fragments : {len(pages)}")
    print(f"poems     : {poem_count}")
    for s in toc:
        print(f"  {s['title']:18s} {len(s['items']):>3} कविताएँ (start idx {s['start']})")


if __name__ == "__main__":
    build()
