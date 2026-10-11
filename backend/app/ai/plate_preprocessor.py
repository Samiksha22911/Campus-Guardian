"""Turns a raw plate crop into an OCR-friendly image.

Operations: upscale small crops (OCR accuracy drops sharply below ~30px
character height on typical gate-camera photos), denoise, contrast-enhance,
then adaptively threshold. This is intentionally a single tunable function
(project notes, section 9: "Preprocessing should be configurable because
different lighting conditions may require different approaches") - adjust
target_char_height or swap the threshold method here if a particular
gate/camera needs different handling.
"""

import cv2
import numpy as np


def prepare_for_ocr(crop_bgr: np.ndarray, target_char_height: int = 200) -> np.ndarray:
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]
    scale = max(1, target_char_height // max(h, 1))
    if scale > 1:
        gray = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    gray = cv2.bilateralFilter(gray, 11, 17, 17)   # denoise while keeping edges sharp
    gray = cv2.equalizeHist(gray)                  # contrast enhancement

    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return thresh
