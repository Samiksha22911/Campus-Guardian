"""
ocr_reader.py
-------------
Reads the alphanumeric plate number out of a cropped plate image using
EasyOCR, with basic preprocessing and text cleanup so the output matches
typical plate formats (uppercase, no spaces/dashes noise, etc.).
"""

import re
import cv2
import numpy as np
import easyocr


class PlateOCR:
    def __init__(self, languages=("en",), gpu: bool = False):
        # Loading the reader is slow (~few seconds) - do it once at
        # startup, not per-frame.
        self.reader = easyocr.Reader(list(languages), gpu=gpu)

    @staticmethod
    def _preprocess(crop: np.ndarray) -> np.ndarray:
        """Upscale + denoise + threshold to make thin plate characters
        easier for OCR, especially on low-res gate-camera crops."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Upscale small crops - OCR accuracy drops sharply below ~32px char height
        h, w = gray.shape[:2]
        scale = max(1, 200 // max(h, 1))
        if scale > 1:
            gray = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        gray = cv2.equalizeHist(gray)

        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
        )
        return thresh

    @staticmethod
    def _clean_text(raw: str) -> str:
        """Keep only letters/digits, uppercase, strip common OCR noise chars."""
        text = raw.upper()
        text = re.sub(r"[^A-Z0-9]", "", text)
        return text

    def read_plate(self, crop: np.ndarray, min_confidence: float = 0.3) -> tuple[str, float]:
        """
        Returns (plate_text, confidence). plate_text is '' if nothing
        readable was found. Tries the preprocessed image first, then
        falls back to the raw crop if preprocessing yields nothing.
        """
        for image in (self._preprocess(crop), crop):
            results = self.reader.readtext(image, detail=1, paragraph=False)
            if not results:
                continue

            # Concatenate all detected text fragments left-to-right
            # (plates sometimes get split into 2 boxes by OCR), keep
            # only fragments above the confidence floor.
            results.sort(key=lambda r: r[0][0][0])  # sort by x position of top-left corner
            fragments = [(text, conf) for (_, text, conf) in results if conf >= min_confidence]
            if not fragments:
                continue

            combined_text = self._clean_text("".join(t for t, _ in fragments))
            avg_conf = sum(c for _, c in fragments) / len(fragments)

            if len(combined_text) >= 4:  # too short = probably noise, not a plate
                return combined_text, avg_conf

        return "", 0.0
