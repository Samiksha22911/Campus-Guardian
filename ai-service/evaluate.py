"""Measure plate accuracy: compare results.json with the plates you KNOW are in the video.

  python ai-service/evaluate.py demo-data/results.json MP07SA1908 MP07ME0643 MP07SK1491 MP30ML2268 MP07CG2432

Reports exact-match rate, character accuracy, and events that matched no real plate (false alarms).
Use the same numbers on your resume - they're honest because they come from your own ground truth.
"""
import difflib
import json
import sys

res = json.load(open(sys.argv[1], encoding="utf-8"))
truth = [t.upper() for t in sys.argv[2:]]
events = [e for e in res["events"] if e["plate_text"]]
used, exact, chars = set(), 0, 0.0
for t in truth:
    best = max(range(len(events)), key=lambda i: difflib.SequenceMatcher(None, t, events[i]["plate_text"]).ratio() if i not in used else -1, default=None)
    if best is None or best in used:
        print(f"MISSED     {t}")
        continue
    used.add(best)
    got = events[best]["plate_text"]
    r = difflib.SequenceMatcher(None, t, got).ratio()
    chars += r
    exact += got == t
    print(f"{'EXACT ' if got == t else 'WRONG '}     {t} -> {got}  (similarity {r:.2f})")
extra = [e["plate_text"] for i, e in enumerate(events) if i not in used]
print(f"\nExact: {exact}/{len(truth)} = {exact/len(truth):.0%}   char similarity: {chars/len(truth):.0%}   false events: {len(extra)} {extra}")
