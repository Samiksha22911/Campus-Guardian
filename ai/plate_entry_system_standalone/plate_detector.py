"""
plate_detector.py
------------------
Thin wrapper around the fine-tuned YOLOv11 model that detects number
plates in an image/frame and returns cropped plate images.
"""

from dataclasses import dataclass
from typing import List
import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class PlateDetection:
    crop: np.ndarray          # cropped plate image (BGR)
    box: tuple                # (x1, y1, x2, y2) in original image
    confidence: float


class PlateDetector:
    def __init__(self, weights_path: str, conf_threshold: float = 0.4, device: str = "cpu"):
        """
        weights_path: path to best.pt produced by train_yolo.py
        conf_threshold: minimum detection confidence to keep a box
        device: 'cpu' or '0' (gpu index)
        """
        self.model = YOLO(weights_path)
        self.conf_threshold = conf_threshold
        self.device = device

    def detect(self, frame: np.ndarray, pad_ratio: float = 0.06) -> List[PlateDetection]:
        """
        Run detection on a single BGR frame (as read by cv2.imread /
        cv2.VideoCapture) and return a list of PlateDetection, one per
        plate found (usually 0 or 1 at a gate camera, but supports many).

        pad_ratio: small padding added around each box before cropping,
        which noticeably helps OCR accuracy (avoids clipping edge characters).
        """
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            device=self.device,
            verbose=False,
        )

        detections: List[PlateDetection] = []
        h, w = frame.shape[:2]

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())

                bw, bh = x2 - x1, y2 - y1
                x1 = max(0, int(x1 - bw * pad_ratio))
                y1 = max(0, int(y1 - bh * pad_ratio))
                x2 = min(w, int(x2 + bw * pad_ratio))
                y2 = min(h, int(y2 + bh * pad_ratio))

                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                detections.append(PlateDetection(crop=crop, box=(x1, y1, x2, y2), confidence=conf))

        # Highest confidence first — useful when multiple boxes fire
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections

    def draw_boxes(self, frame: np.ndarray, detections: List[PlateDetection], texts=None) -> np.ndarray:
        """Draw bounding boxes (and optional OCR text) for display/debugging."""
        out = frame.copy()
        for i, det in enumerate(detections):
            x1, y1, x2, y2 = det.box
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det.confidence:.2f}"
            if texts and i < len(texts) and texts[i]:
                label = f"{texts[i]} ({det.confidence:.2f})"
            cv2.putText(out, label, (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return out
