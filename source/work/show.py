"""Print the unresolved candidate readings for the given pages."""
import json, sys
M = json.load(open('/Users/pranavgangwal/Desktop/claude codes/nani-book/review_win/manifest.json'))
by = {m['page']: m for m in M}
for pid in sys.argv[1:]:
    m = by.get(pid)
    if not m:
        print(f"=== {pid}: nothing open ==="); continue
    print(f"=== {pid}  (printed {m['printed']})  heading={m['heading']!r}  imgs={m['images']}")
    for ln in m['lines']:
        print(f"  L{ln['key']}")
        print(f"     A: {ln['a']}")
        print(f"     B: {ln['b']}")
