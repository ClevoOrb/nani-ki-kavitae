"""Stamp a content hash onto every stylesheet and script referenced by index.html.

index.html is served with `must-revalidate`, so it is always fresh — but the
files it points at were not versioned, so a browser holding a cached copy kept
using it and a deploy appeared not to have landed. Giving each file a ?v=<hash>
means a changed file is a changed URL, so the new one is fetched at once and the
old one can be cached forever.

Run this from the repository root before committing:

    python3 source/work/stamp_assets.py
"""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
INDEX = ROOT / "index.html"
PATTERN = re.compile(r'((?:href|src)=")((?:css|js)/[^"?]+)(\?v=[^"]*)?(")')


def digest(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    seen = {}

    def stamp(m):
        prefix, rel, _old, close = m.groups()
        f = ROOT / rel
        if not f.exists():
            print(f"  !! {rel} is referenced but missing")
            return m.group(0)
        h = seen.setdefault(rel, digest(f))
        return f"{prefix}{rel}?v={h}{close}"

    out = PATTERN.sub(stamp, html)
    if out != html:
        INDEX.write_text(out, encoding="utf-8")
    for rel, h in sorted(seen.items()):
        print(f"  {rel:24s} v={h}")
    print(f"  {'index.html':24s} {'updated' if out != html else 'already current'}")


if __name__ == "__main__":
    main()
