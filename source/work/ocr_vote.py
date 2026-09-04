"""Pass 2: transcribe every leaf three independent times and record the votes.

Vote A: gpt-5.5 on the raw scan(s)
Vote B: gpt-5.4 on the raw scan(s)          (different model family = independent errors)
Vote C: gpt-5.5 on a contrast-enhanced, sharpened render

Pages that were rescanned because of blur get every version handed to each voter.
"""
import json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from azure_client import ask

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "pages_raw"
ENH = ROOT / "work" / "enhanced"
OUTDIR = ROOT / "ocr" / "votes"
ENH.mkdir(exist_ok=True)
OUTDIR.mkdir(parents=True, exist_ok=True)

SYSTEM = (
    "You are a meticulous Devanagari OCR engine working on a scanned Hindi poetry book. "
    "You transcribe exactly what is printed. You never translate, never modernise spelling, "
    "never fix the poet's grammar, and never invent text that is not visible."
)

PROMPT = """Transcribe this page of a printed Hindi (Devanagari) book exactly as printed.

Rules:
- Reproduce every line separately, in printed order, preserving line breaks exactly.
- Preserve blank lines between stanzas.
- Preserve original spelling and punctuation exactly, including danda marks (। and ॥),
  ellipses, question marks, and the decorative *** separator if present.
- Do NOT translate. Do NOT correct spelling or grammar. Do NOT add anything.
- If a character is genuinely unreadable, write it as ⟨?⟩ rather than guessing.
- Ignore the page number printed in parentheses at the bottom; report it in PAGE instead.

Output in exactly this format and nothing else:

@@HEADING
<the poem/section title printed at the top, or - if there is none>
@@BODY
<the body text, line by line>
@@PAGE
<the printed page number, or - if none>
@@END"""

MULTI_NOTE = ("\n\nNOTE: You are given {n} scans of the SAME page (it was rescanned because "
              "parts were blurred). Combine them: for any word unclear in one scan, read it "
              "from the clearer scan. Produce ONE transcription of the page.")

_lock = threading.Lock()


def enhanced(name):
    """Autocontrast + sharpen render, used for the third vote."""
    dst = ENH / name
    if not dst.exists():
        im = Image.open(RAW / name).convert("L")
        im = ImageOps.autocontrast(im, cutoff=1)
        im = ImageEnhance.Sharpness(im).enhance(2.0)
        im = ImageEnhance.Contrast(im).enhance(1.35)
        im.convert("RGB").save(dst, quality=95)
    return dst


def transcribe(page, vote):
    files = page["files"]
    prompt = PROMPT + (MULTI_NOTE.format(n=len(files)) if len(files) > 1 else "")
    if vote == "A":
        return ask("gpt55", SYSTEM, prompt, [RAW / f for f in files])
    if vote == "B":
        return ask("gpt54", SYSTEM, prompt, [RAW / f for f in files])
    return ask("gpt55", SYSTEM, prompt, [enhanced(f) for f in files])


def run_vote(job):
    """One (page, vote) unit of work, cached individually so runs resume cheaply."""
    page, vote = job
    dst = OUTDIR / f"{page['id']}.{vote}.txt"
    if dst.exists():
        return
    try:
        text = transcribe(page, vote)
    except Exception as e:
        text = None
        (OUTDIR / f"{page['id']}.{vote}.err").write_text(repr(e)[:400])
    if text:
        dst.write_text(text)
    with _lock:
        print(f"{page['id']:22s} {vote} {'ok' if text else 'FAILED'}", flush=True)


def collect(pages):
    """Fold the per-vote files into one json per page."""
    for page in pages:
        out = {"id": page["id"], "files": page["files"], "printed": page["printed"]}
        for vote in "ABC":
            f = OUTDIR / f"{page['id']}.{vote}.txt"
            out[vote] = f.read_text() if f.exists() else None
        (OUTDIR / f"{page['id']}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    man = json.load(open(ROOT / "ocr" / "manifest.json"))
    pages = man["pages"]
    if len(sys.argv) > 1:
        want = set(sys.argv[1:])
        pages = [p for p in pages if p["id"] in want]
    jobs = [(p, v) for p in pages for v in "ABC"]
    with ThreadPoolExecutor(max_workers=18) as ex:
        list(ex.map(run_vote, jobs))
    collect(pages)
    print("done", len(pages), "pages,", len(jobs), "votes")
