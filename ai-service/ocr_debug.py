"""See EXACTLY what the detector + OCR do on your video. Saves every plate crop and prints every OCR attempt.

  python ai-service/ocr_debug.py demo-data/demo.mp4            (every 0.5 s)
  python ai-service/ocr_debug.py demo-data/demo.mp4 --every 0.25

Crops are saved in demo-data/ocr_debug/. Look at them: if a crop does not contain the whole plate, the DETECTOR
is the problem; if the crop is clean but the text is wrong, the OCR is. Paste the printed output to get help.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2  # noqa: E402
from analyze_video import ROOT, HERE, read_plate_variants  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--every", type=float, default=0.5)
ap.add_argument("--weights", default=os.path.join(HERE, "weights", "plate_best.pt"))
ap.add_argument("--conf", type=float, default=0.25)
a = ap.parse_args()

from ultralytics import YOLO  # noqa: E402
import easyocr  # noqa: E402

yolo = YOLO(a.weights)
reader = easyocr.Reader(["en"], gpu=False)
out_dir = os.path.join(ROOT, "demo-data", "ocr_debug")
os.makedirs(out_dir, exist_ok=True)
cap = cv2.VideoCapture(a.video)
fps = cap.get(cv2.CAP_PROP_FPS) or 25
step = max(1, round(fps * a.every))
i = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if i % step == 0:
        H, W = frame.shape[:2]
        boxes = [b for r in yolo.predict(frame, conf=a.conf, verbose=False) for b in (r.boxes or [])]
        print(f"\n=== t={i / fps:.2f}s  frame {W}x{H}  detections: {len(boxes)}")
        for k, b in enumerate(boxes):
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            pw, ph = int((x2 - x1) * 0.12), int((y2 - y1) * 0.12)
            crop = frame[max(0, y1 - ph):min(H, y2 + ph), max(0, x1 - pw):min(W, x2 + pw)]
            name = f"t{i / fps:05.2f}_{k}.jpg"
            cv2.imwrite(os.path.join(out_dir, name), crop)
            print(f"  box {k}: x={x1}-{x2} y={y1}-{y2} det_conf={float(b.conf[0]):.2f} crop={crop.shape[1]}x{crop.shape[0]} -> {name}")
            for c in read_plate_variants(reader, crop)[:6]:
                print(f"     [{c['variant']:<9}] text={c['text']:<12} conf={c['conf']:.2f} score={c['score']:.2f} fragments={c['fragments']}")
    i += 1
print("\nCrops saved in", out_dir)
