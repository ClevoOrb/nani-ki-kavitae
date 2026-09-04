"""Pass 5: proofread the finished text against the scans.

The voting pipeline only ever examined lines where the transcribers disagreed.
Lines all three read identically were accepted untouched - and two of the three
voters share a model family, so a correlated error could pass unseen.

This pass asks a different question, of two different models: here is the page and
here is what we believe it says - point at anything that does not match. Comparing
is a different task from transcribing and fails differently, so it catches what
agreement hid. Anything either proofreader flags goes to human review.
"""
import json, re, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from azure_client import ask

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "pages_raw"
OUT = ROOT / "ocr" / "proof"
OUT.mkdir(parents=True, exist_ok=True)

SYSTEM = ("You are a proofreader checking a transcription of a printed Hindi book "
          "against the scanned page. You report only genuine differences between the "
          "transcription and what is actually printed. You never suggest improvements, "
          "corrections of the author's spelling, or modernisations.")

PROMPT = """Below is our transcription of this scanned page, with line numbers.

Compare it against the scan character by character and report every line where the
transcription does NOT match what is printed.

Only report a real difference in the printed words or letters. Do NOT report:
- differences in how many dots an ellipsis has
- । vs ॥ vs ।। danda styling, or : vs ः
- spacing, indentation, or trailing punctuation spacing
- the author's own non-standard spelling (report what is printed, do not fix it)

TRANSCRIPTION
{body}

Answer with strict JSON only, no markdown fence:
{{"mismatches": [{{"line": <line number>, "printed": "<what the page actually says, full line>"}}]}}

If every line matches, answer {{"mismatches": []}}."""

_lock = threading.Lock()


def parse(raw):
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0)).get("mismatches", [])
    except json.JSONDecodeError:
        return None


def run(rec):
    pid = rec["id"]
    dst = OUT / f"{pid}.json"
    if dst.exists():
        return
    lines = rec["text"].split("\n")
    body = "\n".join(f"{i}: {l}" for i, l in enumerate(lines) if l.strip())
    if not body.strip():
        dst.write_text(json.dumps({"id": pid, "gpt55": [], "gpt54": []}))
        return
    head = f'HEADING: {rec["heading"]}\n' if rec.get("heading") else ""
    prompt = PROMPT.format(body=head + body)
    imgs = [RAW / f for f in rec["files"]]
    out = {"id": pid}
    for model in ("gpt55", "gpt54"):
        try:
            out[model] = parse(ask(model, SYSTEM, prompt, imgs,
                                   max_tokens=20000, max_side=2480))
        except Exception as e:
            out[model] = None
            out[model + "_error"] = repr(e)[:200]
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    n55 = len(out.get("gpt55") or [])
    n54 = len(out.get("gpt54") or [])
    with _lock:
        print(f"{pid:12s} flagged 5.5={n55:>2} 5.4={n54:>2}", flush=True)


if __name__ == "__main__":
    recs = json.load(open(ROOT / "ocr" / "final.json"))
    with ThreadPoolExecutor(max_workers=14) as ex:
        list(ex.map(run, recs))
    print("done", len(recs))
