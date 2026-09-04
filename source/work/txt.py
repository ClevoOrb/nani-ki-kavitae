"""Print the stored text of pages, line-numbered, for comparison against the scan."""
import json, sys
R=json.load(open('/Users/pranavgangwal/Desktop/claude codes/nani-book/ocr/final.json'))
r={x['id']:x for x in R}
for pid in sys.argv[1:]:
    x=r[pid]
    print(f"===== {pid}  (printed {x['printed']})")
    print(f"  H | {x['heading']}")
    for i,l in enumerate(x['text'].split('\n')):
        if l.strip(): print(f"{i:>3} | {l}")
