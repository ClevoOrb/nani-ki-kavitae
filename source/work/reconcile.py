"""Pass 3: reconcile the three OCR votes into one text, flagging what needs human eyes.

Line-level majority vote after normalisation. Any line where the three voters do not
reach a 2/3 agreement is written to disputes.json for adjudication against the scan.
"""
import json, re, unicodedata, difflib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOTES = ROOT / "ocr" / "votes"

# Visually identical Devanagari variants that carry no meaning difference in this book.
EQUIV = {
    "ः": ":",   # visarga vs colon - the scans cannot distinguish these
    "​": "", "‌": "", "‍": "", "﻿": "",
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-",
}


def sections(raw):
    """Split a vote into heading / body / page."""
    if not raw:
        return None
    m = re.search(r"@@HEADING\s*(.*?)\s*@@BODY\s*(.*?)\s*@@PAGE\s*(.*?)\s*@@END", raw, re.S)
    if not m:
        m = re.search(r"@@HEADING\s*(.*?)\s*@@BODY\s*(.*?)\s*@@PAGE\s*(.*)", raw, re.S)
        if not m:
            return None
    head, body, page = m.group(1).strip(), m.group(2).strip("\n"), m.group(3).strip()
    return dict(heading="" if head == "-" else head,
                body=body,
                page=None if page in ("-", "") else page)


def norm(s):
    """Normalisation used ONLY for comparing votes, never for the stored text."""
    s = unicodedata.normalize("NFC", s)
    for a, b in EQUIV.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([,;:।॥!?])", r"\1", s)   # spacing before punctuation varies by voter
    s = s.replace("...", "…")
    s = s.replace("।।", "॥")          # double danda: one glyph or two, same mark
    s = re.sub(r"[*∗]{2,}", "***", s)
    return s.strip()


def lines_of(body):
    """Split into lines, collapsing runs of blank lines so that differences in how
    each voter spaced the stanzas do not register as textual disagreement."""
    out = []
    for ln in body.split("\n"):
        ln = ln.rstrip()
        if not ln.strip():
            if out and not out[-1].strip():
                continue
            out.append("")
        else:
            out.append(ln)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def align(votes):
    """Align the vote line-lists against the median-length one - the longest vote
    would let a single hallucinating voter dictate the page's structure."""
    base = sorted(votes, key=len)[len(votes) // 2]
    out = []
    for v in votes:
        sm = difflib.SequenceMatcher(a=[norm(x) for x in base], b=[norm(x) for x in v])
        mapped = [None] * len(base)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("equal", "replace"):
                for k in range(i2 - i1):
                    mapped[i1 + k] = v[j1 + k] if j1 + k < j2 else None
            elif tag == "delete":
                pass
        out.append(mapped)
    return base, out


def reconcile_page(rec):
    parsed = {v: sections(rec.get(v)) for v in "ABC"}
    good = {v: p for v, p in parsed.items() if p}
    if not good:
        return dict(id=rec["id"], status="FAILED", text="", disputes=[])

    bodies = {v: lines_of(p["body"]) for v, p in good.items()}
    base, aligned = align(list(bodies.values()))
    voters = list(bodies.keys())

    final, disputes = [], []
    for i in range(len(base)):
        cands = [(voters[k], aligned[k][i]) for k in range(len(aligned)) if aligned[k][i] is not None]
        counts = Counter(norm(c[1]) for c in cands)
        if not counts:
            continue
        top, n = counts.most_common(1)[0]
        # pick the raw (un-normalised) form from a voter that agrees with the majority
        chosen = next(c[1] for c in cands if norm(c[1]) == top)
        final.append(chosen)
        if not top:                      # stanza spacing, not a textual disagreement
            continue
        if n < 2 or len(counts) > 1:
            disputes.append(dict(line=i, agree=n, of=len(cands),
                                 variants={v: t for v, t in cands}))

    headings = Counter(norm(p["heading"]) for p in good.values())
    htop, hn = headings.most_common(1)[0]
    heading = next(p["heading"] for p in good.values() if norm(p["heading"]) == htop)
    if hn < 2 and len(good) >= 2:
        disputes.append(dict(line="HEADING", agree=hn, of=len(good),
                             variants={v: p["heading"] for v, p in good.items()}))

    pages = Counter(str(p["page"]) for p in good.values())
    if len(pages) > 1:
        disputes.append(dict(line="PAGE", agree=pages.most_common(1)[0][1], of=len(good),
                             variants={v: str(p["page"]) for v, p in good.items()}))

    return dict(id=rec["id"], status="OK" if not disputes else "DISPUTED",
                heading=heading, text="\n".join(final),
                votes_used=len(good), disputes=disputes)


if __name__ == "__main__":
    man = json.load(open(ROOT / "ocr" / "manifest.json"))
    results, all_disputes = [], []
    for page in man["pages"]:
        f = VOTES / f"{page['id']}.json"
        if not f.exists():
            continue
        r = reconcile_page(json.load(open(f)))
        r["printed"] = page["printed"]
        r["files"] = page["files"]
        r["kind"] = page["kind"]
        r["section"] = page.get("section")
        results.append(r)
        for d in r["disputes"]:
            all_disputes.append(dict(page=page["id"], files=page["files"], **d))

    (ROOT / "ocr" / "reconciled.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2))
    (ROOT / "ocr" / "disputes.json").write_text(
        json.dumps(all_disputes, ensure_ascii=False, indent=2))

    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"pages reconciled : {len(results)}")
    print(f"clean (3/3 agree): {ok}")
    print(f"with disputes    : {len(results) - ok}")
    print(f"disputed lines   : {len(all_disputes)}")
