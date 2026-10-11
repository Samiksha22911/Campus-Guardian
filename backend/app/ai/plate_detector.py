"""Number-plate detection service (localizes the plate region on a vehicle).

Real mode (MOCK_AI=false): runs a YOLO model fine-tuned on the license-plate
dataset (see ../../ai/train_plate_yolo.py at the project root for the
training script; point PLATE_MODEL_PATH at the resulting best.pt).

Mock mode (MOCK_AI=true, the default): deterministic, hash-seeded output so
the rest of the app (DB lookup, decision engine, logging, dashboard) can be
built and tested before the real model is trained. Behavior here is
unchanged from the original mock.
"""

import hashlib
import os

from ..config import settings
from .image_utils import bytes_to_bgr, bgr_to_jpeg_bytes

_model_singleton = None


def _load_model():
    """Lazy-load the YOLO model once per process. Importing ultralytics/torch
    at module import time would slow down every request in mock mode and
    would break the app entirely on a machine that hasn't installed the
    (heavy) real-AI dependencies yet."""
    global _model_singleton
    if _model_singleton is None:
        from ultralytics import YOLO
        _model_singleton = YOLO(settings.PLATE_MODEL_PATH)
    return _model_singleton


class PlateDetector:
    def detect(self, image_bytes: bytes) -> dict:
        if settings.MOCK_AI:
            return self._mock_detect(image_bytes)
        return self._real_detect(image_bytes)

    # ------------------------------------------------------------------
    # Real implementation
    # ------------------------------------------------------------------
    def _real_detect(self, image_bytes: bytes) -> dict:
        if not os.path.exists(settings.PLATE_MODEL_PATH):
            raise NotImplementedError(
                f"Real plate detection is not configured: weights file "
                f"'{settings.PLATE_MODEL_PATH}' was not found. Train a model "
                f"with ai/train_plate_yolo.py (see project root), copy the "
                f"resulting best.pt to that path, or set MOCK_AI=true in .env."
            )

        model = _load_model()
        frame = bytes_to_bgr(image_bytes)
        h, w = frame.shape[:2]

        results = model.predict(
            source=frame,
            conf=settings.PLATE_DETECTOR_CONF,
            device=settings.AI_DEVICE,
            verbose=False,
        )

        boxes = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                boxes.append((x1, y1, x2, y2, conf))

        if not boxes:
            return {
                "plate_detected": False,
                "bounding_box": None,
                "confidence": 0.0,
                "plate_crop_jpeg": None,
            }

        # Highest-confidence box wins (a gate camera should only ever see one
        # plate at a time in frame; this also protects against stray false
        # positives elsewhere in the image).
        boxes.sort(key=lambda b: b[4], reverse=True)
        x1, y1, x2, y2, conf = boxes[0]

        # Small padding around the box noticeably helps OCR - it avoids
        # clipping the first/last character.
        bw, bh = x2 - x1, y2 - y1
        pad = 0.06
        x1 = max(0, int(x1 - bw * pad))
        y1 = max(0, int(y1 - bh * pad))
        x2 = min(w, int(x2 + bw * pad))
        y2 = min(h, int(y2 + bh * pad))

        crop = frame[y1:y2, x1:x2]
        crop_jpeg = bgr_to_jpeg_bytes(crop) if crop.size else None

        return {
            "plate_detected": True,
            "bounding_box": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
            "confidence": round(conf, 4),
            "plate_crop_jpeg": crop_jpeg,
        }

    # ------------------------------------------------------------------
    # Mock implementation (unchanged from the original scaffold)
    # ------------------------------------------------------------------
    @staticmethod
    def _mock_detect(image_bytes: bytes) -> dict:
        digest = hashlib.sha256(image_bytes + b"plate").hexdigest()
        seed = int(digest[:8], 16)

        # ~88% of the time a plate region is located
        detected = (seed % 100) < 88

        return {
            "plate_detected": detected,
            "bounding_box": (
                {"x": 40, "y": 220, "width": 160, "height": 48} if detected else None
            ),
            "confidence": round(0.75 + (seed % 24) / 100, 2) if detected else 0.0,
            "plate_crop_jpeg": None,
        }
