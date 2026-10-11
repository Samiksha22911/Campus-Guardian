"""Face detection service - localizes a face in the gate-camera frame.

Real mode (MOCK_AI=false): runs a YOLO model fine-tuned on the
face-detection dataset (see ../../ai/train_face_yolo.py at the project
root; point FACE_MODEL_PATH at the resulting best.pt).

Mock mode (MOCK_AI=true, the default): deterministic, hash-seeded output,
mirroring the style of plate_detector.py's mock so both stages behave
consistently before real models are trained.

Handles (per project notes, section 15): no face, one face, multiple
faces, very small/blurred faces - by reporting `multiple_faces` and letting
the decision engine route ambiguous cases to manual review rather than
guessing.
"""

import hashlib
import os

from ..config import settings
from .image_utils import bytes_to_bgr

_model_singleton = None


def _load_model():
    global _model_singleton
    if _model_singleton is None:
        from ultralytics import YOLO
        _model_singleton = YOLO(settings.FACE_MODEL_PATH)
    return _model_singleton


class FaceDetector:
    def detect(self, image_bytes: bytes) -> dict:
        if settings.MOCK_AI:
            return self._mock_detect(image_bytes)
        return self._real_detect(image_bytes)

    # ------------------------------------------------------------------
    # Real implementation
    # ------------------------------------------------------------------
    def _real_detect(self, image_bytes: bytes) -> dict:
        if not os.path.exists(settings.FACE_MODEL_PATH):
            raise NotImplementedError(
                f"Real face detection is not configured: weights file "
                f"'{settings.FACE_MODEL_PATH}' was not found. Train a model "
                f"with ai/train_face_yolo.py (see project root), copy the "
                f"resulting best.pt to that path, or set MOCK_AI=true in .env."
            )

        model = _load_model()
        frame = bytes_to_bgr(image_bytes)

        results = model.predict(
            source=frame,
            conf=settings.FACE_DETECTOR_CONF,
            device=settings.AI_DEVICE,
            verbose=False,
        )

        boxes = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                conf = float(box.conf[0])
                boxes.append((x1, y1, x2, y2, conf))

        if not boxes:
            return {
                "face_detected": False,
                "bounding_box": None,
                "bounding_box_xyxy": None,
                "confidence": 0.0,
                "multiple_faces": False,
            }

        boxes.sort(key=lambda b: b[4], reverse=True)
        x1, y1, x2, y2, conf = boxes[0]

        return {
            "face_detected": True,
            "bounding_box": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
            "bounding_box_xyxy": (x1, y1, x2, y2),
            "confidence": round(conf, 4),
            "multiple_faces": len(boxes) > 1,
        }

    # ------------------------------------------------------------------
    # Mock implementation
    # ------------------------------------------------------------------
    @staticmethod
    def _mock_detect(image_bytes: bytes) -> dict:
        digest = hashlib.sha256(image_bytes + b"faced").hexdigest()
        seed = int(digest[:8], 16)

        detected = (seed % 100) < 90
        if not detected:
            return {
                "face_detected": False,
                "bounding_box": None,
                "bounding_box_xyxy": None,
                "confidence": 0.0,
                "multiple_faces": False,
            }

        return {
            "face_detected": True,
            "bounding_box": {"x": 120, "y": 60, "width": 140, "height": 160},
            "bounding_box_xyxy": (120, 60, 260, 220),
            "confidence": round(0.75 + (seed % 20) / 100, 2),
            "multiple_faces": False,
        }
