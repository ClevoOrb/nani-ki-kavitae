"""Pass 3c: fold adjudicated decisions back into the page text.

Produces ocr/final.json (the text the site is built from) and ocr/open.json
(the handful of lines two adjudicators could not agree on, for human review).
"""
import json, re
from pathlib import Path
from reconcile import norm

ROOT = Path(__file__).resolve().parent.parent
ADJ = ROOT / "ocr" / "adjudged"

# The in-book contents pages are rebuilt from verified headings, so OCR disputes
# on their two-column layout never reach the reader.
SKIP_REVIEW = {"front-08", "front-09"}


def same_reading(a, b):
    """Do two adjudications differ only in ways the page cannot actually show?
    Ellipsis length, danda glyph choice and stray bullet/period marks vary between
    readers without changing a single word of the poem."""
    if not a or not b:
        return False
    def canon(s):
        s = norm(s)
        s = re.sub(r"[.…]{2,}", "…", s)      # ..... / ...... / … are one mark
        s = re.sub(r"[•·]", ".", s)
        s = re.sub(r"\s*[.…]+\s*$", "", s)   # trailing dot runs
        return s.strip()
    return canon(a) == canon(b)


def main():
    recs = json.load(open(ROOT / "ocr" / "reconciled.json"))
    overrides = json.load(open(ROOT / "ocr" / "overrides.json")) if (ROOT / "ocr" / "overrides.json").exists() else {}

    out, still_open = [], []
    applied = 0
    for r in recs:
        pid = r["id"]
        lines = r["text"].split("\n")
        heading = r.get("heading", "")

        f = ADJ / f"{pid}.json"
        if f.exists():
            adj = json.load(open(f))
            for key, text in adj["settled"].items():
                if key == "HEADING":
                    heading = text
                    applied += 1
                elif key == "PAGE":
                    continue
                elif key.isdigit() and int(key) < len(lines):
                    lines[int(key)] = text
                    applied += 1
            for o in adj["open"]:
                key = o["key"]
                # both adjudicators agree on the words - only the punctuation glyphs differ
                if same_reading(o.get("gpt55"), o.get("gpt54")):
                    if key.isdigit() and int(key) < len(lines):
                        lines[int(key)] = o["gpt55"]
                        applied += 1
                    elif key == "HEADING":
                        heading = o["gpt55"]
                        applied += 1
                    continue
                if key == "PAGE" or pid in SKIP_REVIEW:
                    continue
                still_open.append(dict(page=pid, files=r["files"], **o))

        # hand-checked corrections win over everything
        for key, text in overrides.get(pid, {}).items():
            if key == "HEADING":
                heading = text
            elif key.isdigit() and int(key) < len(lines):
                lines[int(key)] = text

        out.append(dict(id=pid, printed=r["printed"], kind=r["kind"],
                        section=r.get("section"), heading=heading,
                        text="\n".join(lines), files=r["files"]))

    (ROOT / "ocr" / "final.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    (ROOT / "ocr" / "open.json").write_text(json.dumps(still_open, ensure_ascii=False, indent=2))
    reviewed = sum(len(v) for v in overrides.values())
    unresolved = [o for o in still_open
                  if str(o["key"]) not in overrides.get(o["page"], {})]
    print(f"pages                    : {len(out)}")
    print(f"lines settled by models  : {applied}")
    print(f"lines settled by review  : {reviewed}")
    print(f"lines still unresolved   : {len(unresolved)}")


if __name__ == "__main__":
    main()
