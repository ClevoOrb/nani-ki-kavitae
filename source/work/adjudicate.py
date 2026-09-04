"""Pass 3b: settle the lines where the three transcribers disagreed.

Rather than a fourth blind transcription, each disputed line is put back to two
models as a focused question - "here are the candidate readings, look at the scan
and tell us which is actually printed" - at full scan resolution. Where both
adjudicators agree the line is settled; anything else is left for human review.
"""
import json, re, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from azure_client import ask

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "pages_raw"
OUT = ROOT / "ocr" / "adjudged"
OUT.mkdir(parents=True, exist_ok=True)

SYSTEM = ("You are an expert proofreader of printed Hindi (Devanagari) books. You compare "
          "candidate transcriptions against the scanned page and report exactly what is "
          "printed, character by character. You never translate or improve the text.")

TEMPLATE = """Three OCR passes over this scanned Hindi page disagreed on some lines.

Here is the full page as one pass read it, for context:
---
{context}
---

For each disputed line below, look very carefully at the scan and decide what is
ACTUALLY PRINTED. You may pick one of the candidates, or supply a different reading
if all candidates are wrong.

{items}

Answer with strict JSON only, no markdown fence:
{{"decisions": [{{"key": "<the key shown above>", "text": "<exact printed line>", "confident": true|false}}]}}

Set "confident" to false only if the print is genuinely too damaged to resolve."""

_lock = threading.Lock()


def build_items(disputes):
    out = []
    for d in disputes:
        variants = d["variants"]
        lines = [f'  key: {d["line"]}']
        for voter, text in variants.items():
            lines.append(f'    candidate {voter}: {text!r}')
        out.append("\n".join(lines))
    return "\n\n".join(out)


def parse(raw):
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    return {str(d["key"]): d for d in data.get("decisions", []) if "key" in d and "text" in d}


def run(page):
    pid = page["id"]
    dst = OUT / f"{pid}.json"
    if dst.exists():
        return
    prompt = TEMPLATE.format(context=page["context"], items=build_items(page["disputes"]))
    imgs = [RAW / f for f in page["files"]]
    res = {}
    for model in ("gpt55", "gpt54"):
        try:
            res[model] = parse(ask(model, SYSTEM, prompt, imgs, max_tokens=20000, max_side=2480))
        except Exception as e:
            res[model] = {}
            res[model + "_error"] = repr(e)[:200]

    settled, open_ = {}, []
    for d in page["disputes"]:
        k = str(d["line"])
        a, b = res["gpt55"].get(k), res["gpt54"].get(k)
        if a and b and a["text"].strip() == b["text"].strip() and a.get("confident", True):
            settled[k] = a["text"].strip()
        else:
            open_.append(dict(key=k, variants=d["variants"],
                              gpt55=(a or {}).get("text"), gpt54=(b or {}).get("text")))
    dst.write_text(json.dumps(dict(id=pid, settled=settled, open=open_),
                              ensure_ascii=False, indent=2), encoding="utf-8")
    with _lock:
        print(f"{pid:22s} settled {len(settled):>2}/{len(page['disputes'])}"
              f"  open {len(open_)}", flush=True)


if __name__ == "__main__":
    recs = json.load(open(ROOT / "ocr" / "reconciled.json"))
    jobs = []
    for r in recs:
        if r["status"] != "DISPUTED":
            continue
        jobs.append(dict(id=r["id"], files=r["files"], context=r["text"],
                         disputes=r["disputes"]))
    print("pages needing adjudication:", len(jobs))
    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(run, jobs))
    total_open = 0
    for j in jobs:
        d = json.load(open(OUT / f"{j['id']}.json"))
        total_open += len(d["open"])
    print("lines still open for human review:", total_open)
