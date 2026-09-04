"""Pass 1: identify the printed page number + heading of every split page image."""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from azure_client import ask

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "pages_raw"
OUT = ROOT / "ocr" / "index.json"

SYSTEM = "You inspect scanned pages of a printed Hindi poetry book and report structural facts about them."

PROMPT = """Look at this scanned page from a Hindi book.

Report, as strict JSON only (no markdown fence):
{
  "page_number": <the printed page number, usually at the bottom in parentheses like (48); use null if none is printed>,
  "kind": "<one of: text, toc, title, cover, blank, photo, dedication, other>",
  "heading": "<the Hindi heading/title printed on the page, or empty string>",
  "first_line": "<the first line of body text in Hindi, or empty string>",
  "legibility": "<one of: clear, slightly_blurred, badly_blurred>",
  "has_photo": <true/false - does the page contain a photograph of a person>
}"""


def one(p):
    try:
        raw = ask("gpt55", SYSTEM, PROMPT, [p], max_tokens=1200)
        m = re.search(r"\{.*\}", raw, re.S)
        d = json.loads(m.group(0))
    except Exception as e:
        d = {"error": repr(e)[:200]}
    d["file"] = p.name
    print(p.name, d.get("page_number"), d.get("kind"), (d.get("heading") or "")[:30], flush=True)
    return d


if __name__ == "__main__":
    files = sorted(RAW.glob("*.jpg"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(one, files))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print("wrote", OUT, len(results))
