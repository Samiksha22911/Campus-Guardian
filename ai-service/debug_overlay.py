"""Draw the boxes stored in results.json onto the REAL video frames (no browser involved).

  python ai-service/debug_overlay.py demo-data/results.json demo-data/demo.mp4

Writes demo-data/debug_overlay.mp4. Open it:
  * boxes sit on the plates here  -> the data is right, the problem is only in the web player
  * boxes are wrong here too      -> the detector/coordinates are wrong (re-run analyze_video.py)
"""
import json
import sys

import cv2

res = json.load(open(sys.argv[1], encoding="utf-8"))
cap = cv2.VideoCapture(sys.argv[2])
fps = cap.get(cv2.CAP_PROP_FPS) or 25
ok, f = cap.read()
h, w = f.shape[:2]
out = cv2.VideoWriter("demo-data/debug_overlay.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
i = 0
while ok:
    t = i / fps
    for e in res["events"]:
        if e.get("ts_start", e["timestamp"]) - 0.15 <= t <= e.get("ts_end", e["timestamp"]) + 0.5:
            tr = e.get("track") or []
            b = min(tr, key=lambda p: abs(p["t"] - t)) if tr else e["bbox"]
            x1, y1, x2, y2 = int(b["x"] * w), int(b["y"] * h), int((b["x"] + b["w"]) * w), int((b["y"] + b["h"]) * h)
            cv2.rectangle(f, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(f, f'{e["plate_text"]} {e["decision"]}', (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    out.write(f)
    ok, f = cap.read()
    i += 1
out.release()
print("Wrote demo-data/debug_overlay.mp4")
