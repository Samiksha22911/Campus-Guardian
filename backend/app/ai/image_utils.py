"""Shared helpers for converting between raw upload bytes and OpenCV arrays.

cv2/numpy are imported lazily INSIDE the functions so the backend can start
(in DEMO_MODE) on a host where OpenCV is not installed at all.
"""


def bytes_to_bgr(image_bytes: bytes):
    """Decode raw image bytes into an OpenCV BGR array. Raises ValueError on
    corrupt/unsupported data."""
    import cv2
    import numpy as np

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image bytes - unsupported or corrupted image.")
    return frame


def bgr_to_jpeg_bytes(frame) -> bytes:
    """Encode an OpenCV BGR array back to JPEG bytes."""
    import cv2

    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("Could not encode image to JPEG.")
    return buf.tobytes()
