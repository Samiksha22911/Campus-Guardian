"""Run the REAL pipeline (YOLO plate detector -> EasyOCR -> database check) on a video
and write results in the common format.

  python ai-service/analyze_video.py gate.mp4 --out demo-data/results.json --publish

Also imported by the backend (DEMO_MODE=false) for browser uploads.
HEAVY imports (cv2/ultralytics/easyocr) happen inside functions on purpose.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plate_fix import assemble_plate, fix_indian_plate, is_valid_format, plate_score  # noqa: E402
from results_format import apply_lookup, build_results, clean_plate, group_readings, validate_results  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def join_text_lines(frags):
    """frags = [(box4pts, text, conf)]. Two-line plates (MP.07 / SA.1908) must be read top line first,
    then left-to-right inside each line - sorting by x alone interleaves the lines and scrambles digits."""
    if not frags:
        return "", 0.0
    items = []
    for box, text, conf in frags:
        ys = [pt[1] for pt in box]
        xs = [pt[0] for pt in box]
        items.append({"yc": sum(ys) / 4, "h": max(ys) - min(ys), "x": min(xs), "t": text, "c": conf})
    items.sort(key=lambda i: i["yc"])
    med_h = sorted(i["h"] for i in items)[len(items) // 2] or 1
    lines = []
    for it in items:
        if lines and abs(it["yc"] - sum(i["yc"] for i in lines[-1]) / len(lines[-1])) < 0.6 * med_h:
            lines[-1].append(it)
        else:
            lines.append([it])
    text = "".join(i["t"] for ln in lines for i in sorted(ln, key=lambda i: i["x"]))
    return text, sum(i["c"] for i in items) / len(items)


OCR_ALLOW = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"   # '.' allowed so the printed dot is not misread as a letter/digit


def _rotate(img, angle):
    import cv2

    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2 - w / 2
    m[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(img, m, (nw, nh), borderMode=cv2.BORDER_REPLICATE)


def read_plate_variants(reader, crop):
    """OCR several versions of the crop (and, if needed, slightly rotated ones), pool every text fragment,
    and assemble head (MP07) + tail (SA1908). Returns candidate dicts, best first."""
    import cv2

    h, w = crop.shape[:2]
    scale = max(1.0, 160.0 / max(h, 1))
    big = cv2.resize(crop, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC) if scale > 1 else crop
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    eq = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(cv2.bilateralFilter(gray, 9, 17, 17))
    thr = cv2.adaptiveThreshold(eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)

    cands, pool = [], []

    def run(name, img):
        # width_ths: merge boxes across the wide gap in 'MP.07   ME0643'; low_text: keep faint characters
        res = reader.readtext(img, detail=1, paragraph=False, allowlist=OCR_ALLOW,
                              width_ths=1.0, low_text=0.3, text_threshold=0.5)
        frags = [(b, t, c) for (b, t, c) in res if c >= 0.15]
        pool.extend((t, float(c)) for _, t, c in frags)
        joined, conf = join_text_lines(frags)
        text = fix_indian_plate(clean_plate(joined))
        if len(text) >= 4:
            cands.append({"variant": name, "fragments": [(t, round(float(c), 2)) for _, t, c in frags],
                          "text": text, "conf": float(conf), "score": plate_score(text) * float(conf)})

    for name, img in (("raw", big), ("clahe", eq), ("threshold", thr)):
        run(name, img)
    if not assemble_plate(pool)["full"]:          # plate is probably tilted: try a few angles
        for ang in (12, -12, 25, -25):
            run(f"clahe{ang:+d}", _rotate(eq, ang))
            run(f"raw{ang:+d}", _rotate(big, ang))

    asm = assemble_plate(pool)
    for kind in ("full", "head", "tail"):
        if asm[kind]:
            text, conf = asm[kind]
            cands.append({"variant": f"assembled-{kind}", "fragments": [], "text": text, "conf": conf,
                          "score": (4.0 if kind == "full" else 1.0) * conf})
    return sorted(cands, key=lambda c: -c["score"])


def pick_readings(cands):
    """Best overall reading + best head + best tail (the tracker joins halves seen in different frames)."""
    if not cands:
        return []
    out = [(cands[0]["text"], cands[0]["conf"])]
    for kind in ("assembled-head", "assembled-tail"):
        c = next((x for x in cands if x["variant"] == kind), None)
        if c and c["text"] not in [t for t, _ in out]:
            out.append((c["text"], c["conf"]))
    return out


def _build_models(weights_path, device, plate_conf):
    from ultralytics import YOLO
    import easyocr

    yolo = YOLO(weights_path)
    reader = easyocr.Reader(["en"], gpu=(device != "cpu"))

    def detect(frame):
        out = []
        for r in yolo.predict(source=frame, conf=plate_conf, device=device, verbose=False):
            if r.boxes is None:
                continue
            for b in r.boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                out.append((x1, y1, x2, y2, float(b.conf[0])))
        return out

    def ocr(crop):
        return pick_readings(read_plate_variants(reader, crop)) or [(None, 0.0)]

    return detect, ocr


def analyze_video(video_path, weights_path, lookup=None, plate_conf=0.4, device="cpu", stride_s=0.1,
                  progress=None, source_name=None, detect_fn=None, ocr_fn=None):
    import cv2

    if detect_fn is None or ocr_fn is None:
        detect_fn, ocr_fn = _build_models(weights_path, device, plate_conf)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = max(1, round(fps * stride_s))

    readings, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        height, width = frame.shape[:2]   # ground truth: the size of the frames we actually analyse
        if idx % step == 0:
            t = idx / fps
            for (x1, y1, x2, y2, dconf) in detect_fn(frame):
                bw, bh = x2 - x1, y2 - y1
                px1, py1 = max(0, int(x1 - bw * 0.12)), max(0, int(y1 - bh * 0.12))
                px2, py2 = min(width, int(x2 + bw * 0.12)), min(height, int(y2 + bh * 0.12))
                crop = frame[py1:py2, px1:px2]
                out = ocr_fn(crop) if crop.size else [(None, 0.0)]
                if isinstance(out, tuple):
                    out = [out]
                for text, oconf in out:
                    readings.append({
                        "t": t, "text": text, "conf": float(oconf), "det_conf": dconf,
                        "box": (max(0, x1) / width, max(0, y1) / height, min(bw, width) / width, min(bh, height) / height),
                    })
            if progress and total:
                progress(idx / total)
        idx += 1
    cap.release()

    events = apply_lookup(group_readings(readings), lookup)
    results = build_results(
        events, source_video=source_name or os.path.basename(video_path), duration_s=idx / fps, fps=fps,
        width=width, height=height, stride_s=stride_s,
        models={"plate_detector": f"YOLO ({os.path.basename(weights_path)})", "ocr": "EasyOCR", "face": None},
    )
    problems = validate_results(results)
    if problems:
        raise RuntimeError("Produced invalid results: " + "; ".join(problems[:5]))
    return results


def _db_lookup():
    """Use the backend's database for db_status/decision. Returns (lookup, close)."""
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    os.chdir(os.path.join(ROOT, "backend"))
    from app.database import SessionLocal
    from app.demo_support import lookup_plate

    db = SessionLocal()
    return (lambda text, conf: lookup_plate(db, text, conf)[0]), db.close


def main():
    import json
    import shutil

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", default=os.path.join(ROOT, "demo-data", "results.json"))
    ap.add_argument("--weights", default=os.path.join(HERE, "weights", "plate_best.pt"))
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--stride", type=float, default=0.1, help="seconds between analysed frames")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--no-db", action="store_true", help="skip DB check (hosted demo re-checks live anyway)")
    ap.add_argument("--publish", action="store_true",
                    help="copy the video to demo-data/demo.mp4 + frontend/public/demo.mp4 and point results at it")
    a = ap.parse_args()
    a.video, a.out, a.weights = (os.path.abspath(x) for x in (a.video, a.out, a.weights))  # _db_lookup() changes cwd

    lookup, close = (None, lambda: None)
    if not a.no_db:
        try:
            lookup, close = _db_lookup()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] DB check unavailable ({exc}); continuing with --no-db behaviour.")

    out = os.path.abspath(a.out)
    print(f"Analysing {a.video} ...")
    results = analyze_video(a.video, a.weights, lookup=lookup, plate_conf=a.conf, device=a.device, stride_s=a.stride,
                            progress=lambda p: print(f"\r  {p:5.0%}", end="", flush=True))
    close()
    print()
    if a.publish:
        for dest in (os.path.join(ROOT, "demo-data", "demo.mp4"), os.path.join(ROOT, "frontend", "public", "demo.mp4")):
            if os.path.abspath(a.video) != os.path.abspath(dest):
                shutil.copyfile(a.video, dest)
        results["video"]["src"] = "/demo.mp4"
        if os.path.getsize(a.video) > 25 * 1024 * 1024:
            print("[warn] video > 25 MB - compress it (see README: ffmpeg command) so Vercel serves it quickly.")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {out}: {len(results['events'])} events")
    for e in results["events"]:
        print(f"  t={e['timestamp']:>6.2f}s  {e['plate_text'] or '(unreadable)':<12} conf={e['plate_confidence']:.2f}  {e['db_status']:<13} -> {e['decision']}")


if __name__ == "__main__":
    main()
