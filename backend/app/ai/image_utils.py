"""Shared helpers for converting between raw upload bytes and OpenCV arrays.

Used by plate_detector.py and face_detector.py so both real implementations
decode/encode images the same way.
"""

import cv2
import numpy as np


def bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes (as received from a FastAPI UploadFile) into
    an OpenCV BGR array. Raises ValueError on corrupt/unsupported data."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image bytes - unsupported or corrupted image.")
    return frame


def bgr_to_jpeg_bytes(frame: np.ndarray) -> bytes:
    """Encode an OpenCV BGR array back to JPEG bytes (e.g. to hand a cropped
    plate region to the OCR stage without re-reading it from disk)."""
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("Could not encode image to JPEG.")
    return buf.tobytes()
