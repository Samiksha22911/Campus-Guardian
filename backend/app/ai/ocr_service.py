"""OCR service - reads the plate number out of a detected plate region.

Real mode (MOCK_AI=false): EasyOCR on the preprocessed crop produced by
plate_detector.py, with text cleanup (project notes, section 11: uppercase,
strip separators, keep only A-Z0-9).

Mock mode (MOCK_AI=true, the default): unchanged from the original scaffold.
Deliberately biased so demos are useful:
- most of the time it "reads" a plate that is already registered (so
  GRANTED / face-verification flows can be exercised)
- sometimes it returns a plate that is NOT registered (UNKNOWN_VEHICLE)
- sometimes it returns a low-confidence / unreadable result (MANUAL_REVIEW)

`scenario` lets the caller (verification endpoint) force a specific
situation for demoing/testing without needing the real models.
"""

import hashlib
import random
import re

import cv2
import numpy as np

from ..config import settings
from .plate_preprocessor import prepare_for_ocr

_reader_singleton = None


def _get_reader():
    """Lazy-load EasyOCR once per process (loading the model is slow)."""
    global _reader_singleton
    if _reader_singleton is None:
        import easyocr
        _reader_singleton = easyocr.Reader(
            list(settings.OCR_LANGUAGES), gpu=(settings.AI_DEVICE != "cpu")
        )
    return _reader_singleton


def _clean_text(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


class OCRService:
    def read_plate(
        self,
        image_bytes: bytes,
        known_plates: list[str] | None = None,
        scenario: str | None = None,
        plate_crop_jpeg: bytes | None = None,
    ) -> dict:
        if settings.MOCK_AI:
            return self._mock_read(image_bytes, known_plates=known_plates, scenario=scenario)
        return self._real_read(plate_crop_jpeg)

    # ------------------------------------------------------------------
    # Real implementation
    # ------------------------------------------------------------------
    def _real_read(self, plate_crop_jpeg: bytes | None) -> dict:
        if not plate_crop_jpeg:
            return {"plate_number": None, "ocr_confidence": 0.0, "raw_text": ""}

        arr = np.frombuffer(plate_crop_jpeg, dtype=np.uint8)
        crop = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if crop is None:
            return {"plate_number": None, "ocr_confidence": 0.0, "raw_text": ""}

        reader = _get_reader()

        # Try the preprocessed (thresholded) image first; fall back to the
        # raw crop if preprocessing over-cleans a low-contrast plate.
        for image in (prepare_for_ocr(crop), crop):
            results = reader.readtext(image, detail=1, paragraph=False)
            if not results:
                continue

            # Sort left-to-right - plates sometimes get split into 2+
            # fragments by OCR (e.g. state code vs number).
            results.sort(key=lambda r: r[0][0][0])
            fragments = [(text, conf) for (_, text, conf) in results if conf >= 0.3]
            if not fragments:
                continue

            raw_text = "".join(t for t, _ in fragments)
            combined = _clean_text(raw_text)
            avg_conf = sum(c for _, c in fragments) / len(fragments)

            if len(combined) >= 4:  # too short = likely noise, not a plate
                return {
                    "plate_number": combined,
                    "ocr_confidence": round(avg_conf, 4),
                    "raw_text": raw_text,
                }

        return {"plate_number": None, "ocr_confidence": 0.0, "raw_text": ""}

    # ------------------------------------------------------------------
    # Mock implementation (unchanged from the original scaffold)
    # ------------------------------------------------------------------
    def _mock_read(self, image_bytes, known_plates=None, scenario=None) -> dict:
        digest = hashlib.sha256(image_bytes + b"ocr").hexdigest()
        rng = random.Random(int(digest[:8], 16))
        known_plates = known_plates or []

        if scenario == "ocr_failure":
            return {"plate_number": None, "ocr_confidence": 0.0, "raw_text": ""}

        if scenario == "low_confidence":
            plate = rng.choice(known_plates) if known_plates else self._random_plate(rng)
            return {"plate_number": plate, "ocr_confidence": round(rng.uniform(0.30, 0.50), 2), "raw_text": plate}

        if scenario == "unknown_vehicle":
            plate = self._random_plate(rng, avoid=known_plates)
            return {"plate_number": plate, "ocr_confidence": round(rng.uniform(0.80, 0.97), 2), "raw_text": plate}

        roll = rng.random()

        if roll < 0.10:
            return {"plate_number": None, "ocr_confidence": 0.0, "raw_text": ""}

        if roll < 0.20:
            plate = rng.choice(known_plates) if known_plates and rng.random() < 0.5 else self._random_plate(rng)
            return {"plate_number": plate, "ocr_confidence": round(rng.uniform(0.30, 0.54), 2), "raw_text": plate}

        if roll < 0.35 or not known_plates:
            plate = self._random_plate(rng, avoid=known_plates)
            return {"plate_number": plate, "ocr_confidence": round(rng.uniform(0.80, 0.98), 2), "raw_text": plate}

        plate = rng.choice(known_plates)
        return {"plate_number": plate, "ocr_confidence": round(rng.uniform(0.82, 0.99), 2), "raw_text": plate}

    @staticmethod
    def _random_plate(rng: random.Random, avoid: list[str] | None = None) -> str:
        avoid = set(avoid or [])
        for _ in range(10):
            plate = (
                f"MP{rng.randint(1, 70):02d}"
                f"{rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
                f"{rng.randint(1000, 9999)}"
            )
            if plate not in avoid:
                return plate
        return plate
