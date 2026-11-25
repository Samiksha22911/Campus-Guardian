"""Convert the detections JSON your CURRENT pipeline already produced (e.g. the
Colab notebook's results/detections JSON) into the common results.json format.

  python ai-service/convert_pipeline_output.py detections.json gate.mp4 --out demo-data/results.json --publish

Reads video size/fps from the video itself. Accepts either a list of detections or
{"detections"|"events"|"results"|"plates": [...]}. Each detection needs at least a
time (seconds, or a frame number) and a plate text; confidence and box are used if present.
Key names are matched flexibly (see ALIASES). If your file uses other names, add them
to ALIASES - or just run analyze_video.py, which needs no conversion.

Pure Python + cv2 (only to read the video's size/fps). No torch / YOLO needed.
"""

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from results_format import apply_lookup, build_results, clean_plate, group_readings, validate_results  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIASES = {
    "time": ["timestamp", "time", "t", "time_s", "time_sec", "seconds", "second", "video_time", "frame_time"],
    "frame": ["frame", "frame_idx", "frame_index", "frame_no", "frame_number"],
    "text": ["plate_text", "plate", "text", "plate_number", "number", "ocr_text", "ocr", "registration"],
    "conf": ["plate_confidence", "ocr_confidence", "ocr_conf", "confidence", "conf", "score"],
    "det_conf": ["detector_confidence", "det_conf", "yolo_conf", "detection_confidence"],
    "box": ["bbox", "box", "bounding_box", "xyxy", "xywh", "plate_box"],
}


def pick(d, key, default=None):
    for k in ALIASES[key]:
        if k in d and d[k] is not None:
            return d[k]
    return default


def to_xywh_norm(box, w, h):
    """Accepts [x1,y1,x2,y2] / [x,y,w,h] / {x1,y1,x2,y2} / {x,y,width|w,height|h} in PIXELS or 0-1."""
    if isinstance(box, dict):
        if "x1" in box:
            x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
        else:
            x1, y1 = box["x"], box["y"]
            x2, y2 = x1 + box.get("w", box.get("width")), y1 + box.get("h", box.get("height"))
    else:
        x1, y1, a, b = box
        # heuristic: if 3rd/4th are greater than 1st/2nd they are corners (xyxy); otherwise assume w,h
        x2, y2 = (a, b) if (a > x1 and b > y1) else (x1 + a, y1 + b)
    if max(x1, y1, x2, y2) > 1.5:  # pixels -> fractions
        x1, x2, y1, y2 = x1 / w, x2 / w, y1 / h, y2 / h
    x1, y1 = max(0.0, x1), max(0.0, y1)
    return (x1, y1, max(0.0, min(1 - x1, x2 - x1)), max(0.0, min(1 - y1, y2 - y1)))


def main():
    import cv2

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("detections_json")
    ap.add_argument("video")
    ap.add_argument("--out", default=os.path.join(ROOT, "demo-data", "results.json"))
    ap.add_argument("--no-db", action="store_true")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    a.detections_json, a.video, a.out = (os.path.abspath(x) for x in (a.detections_json, a.video, a.out))

    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    cap.release()

    raw = json.load(open(a.detections_json, encoding="utf-8"))
    if isinstance(raw, dict):
        raw = next((raw[k] for k in ("detections", "events", "results", "plates", "records") if isinstance(raw.get(k), list)), None)
        if raw is None:
            sys.exit("Could not find a list of detections in the JSON (looked for detections/events/results/plates/records).")

    readings, skipped = [], 0
    for d in raw:
        t = pick(d, "time")
        if t is None and pick(d, "frame") is not None:
            t = float(pick(d, "frame")) / fps
        box = pick(d, "box")
        if t is None or box is None:
            skipped += 1
            continue
        conf = pick(d, "conf", 0.0)
        readings.append({
            "t": float(t), "text": clean_plate(pick(d, "text")) or None, "conf": float(conf),
            "det_conf": float(pick(d, "det_conf", conf)), "box": to_xywh_norm(box, w, h),
        })
    if not readings:
        sys.exit(f"No usable detections (skipped {skipped}). Each needs a time/frame and a box - see ALIASES in this file.")

    lookup = None
    if not a.no_db:
        try:
            sys.path.insert(0, os.path.join(ROOT, "backend"))
            os.chdir(os.path.join(ROOT, "backend"))
            from app.database import SessionLocal
            from app.demo_support import lookup_plate
            db = SessionLocal()
            lookup = lambda text, conf: lookup_plate(db, text, conf)[0]  # noqa: E731
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] DB check unavailable ({exc}); db_status = NOT_CHECKED (the hosted demo re-checks live).")

    events = apply_lookup(group_readings(readings), lookup)
    res = build_results(events, source_video=os.path.basename(a.video), duration_s=dur, fps=fps, width=w, height=h,
                        models={"plate_detector": "YOLO (from your existing pipeline)", "ocr": "EasyOCR", "face": None})
    if a.publish:
        for dest in (os.path.join(ROOT, "demo-data", "demo.mp4"), os.path.join(ROOT, "frontend", "public", "demo.mp4")):
            if os.path.abspath(a.video) != os.path.abspath(dest):
                shutil.copyfile(a.video, dest)
        res["video"]["src"] = "/demo.mp4"
    problems = validate_results(res)
    if problems:
        sys.exit("Invalid output: " + "; ".join(problems[:5]))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf-8"), indent=2)
    print(f"{len(raw)} detections ({skipped} skipped) -> {len(events)} events -> {a.out}")
    for e in events:
        print(f"  t={e['timestamp']:>6.2f}s  {e['plate_text'] or '(unreadable)':<12} {e['plate_confidence']:.2f}  {e['db_status']} -> {e['decision']}")


if __name__ == "__main__":
    main()
