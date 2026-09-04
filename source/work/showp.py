"""Print the proofreader's claims for the given pages, minus lines already verified."""
import json, sys
R="/Users/pranavgangwal/Desktop/KEEP"
M=json.load(open('/Users/pranavgangwal/Desktop/claude codes/nani-book/proof_win/manifest.json'))
ov=json.load(open('/Users/pranavgangwal/Desktop/claude codes/nani-book/ocr/overrides.json'))
by={m['page']:m for m in M}
for pid in sys.argv[1:]:
    m=by.get(pid)
    if not m: print(f"=== {pid}: no flags ==="); continue
    fresh=[l for l in m['lines'] if str(l['line']) not in ov.get(pid,{})]
    if not fresh: print(f"=== {pid}: all flags already verified ==="); continue
    print(f"=== {pid} (printed {m['printed']}) heading={m['heading']!r}")
    for l in fresh:
        who='BOTH' if len(l['claims'])==2 else list(l['claims'])[0]
        print(f"  L{l['line']} [{who}]")
        print(f"    ours: {l['current']}")
        for k,v in l['claims'].items(): print(f"    {k}: {v}")
