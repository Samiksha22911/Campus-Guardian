"""Orchestrates the AI side of the entry-verification pipeline.

    image
      -> plate detection
      -> plate crop
      -> OCR
      -> (caller does the DB lookup - see routers/verification.py)
      -> face verification (optional, only after the caller has identified
         the expected owner from the matched vehicle)
      -> decision

Per the project's design decision, there is deliberately no vehicle-type
classification step here - vehicle type is a plain database field on the
Vehicle record, not something an AI model guesses from the image. (See
vehicle_detector.py's docstring - that module is no longer called from
this pipeline; it's kept only in case a future version of the project
wants to reintroduce it explicitly.)

This module only talks to the other `ai/` services - it knows nothing
about SQLAlchemy or the database. The verification router is responsible
for the registered-vehicle lookup and for persisting the result; it calls
`run_pipeline()` and then `decide()` with the lookup outcome.
"""

from ..config import settings
from .face_verification import FaceVerificationService
from .ocr_service import OCRService
from .plate_detector import PlateDetector

plate_detector = PlateDetector()
ocr_service = OCRService()
face_service = FaceVerificationService()


def run_pipeline(
    image_bytes: bytes,
    known_plates: list[str],
    scenario: str | None = None,
) -> dict:
    """Runs plate detection -> OCR and returns a structured result. Does not
    touch the database and does not run face verification (that needs the
    matched student's reference embedding, which the caller supplies after
    doing the DB lookup)."""

    plate_result = plate_detector.detect(image_bytes)

    if not plate_result["plate_detected"]:
        return {
            "plate_detected": False,
            "plate_number": None,
            "ocr_confidence": 0.0,
            "plate_detector_confidence": 0.0,
        }

    ocr_result = ocr_service.read_plate(
        image_bytes,
        known_plates=known_plates,
        scenario=scenario,
        plate_crop_jpeg=plate_result.get("plate_crop_jpeg"),
    )

    return {
        "plate_detected": True,
        "plate_number": ocr_result["plate_number"],
        "ocr_confidence": ocr_result["ocr_confidence"],
        "plate_detector_confidence": plate_result["confidence"],
    }


def run_face_verification(
    image_bytes: bytes,
    reference_embedding: str | None,
    scenario: str | None = None,
) -> dict:
    return face_service.verify(image_bytes, reference_embedding, scenario=scenario)


def decide(
    *,
    plate_detected: bool,
    ocr_confidence: float,
    plate_number: str | None,
    vehicle_registered: bool,
    vehicle_blocklisted: bool,
    require_face: bool,
    face_result: dict | None,
) -> tuple[str, str, str | None]:
    """Applies the decision matrix from the project spec (section 20).

    Returns (simplified_status, verification_status, rejection_reason)
      simplified_status:   granted | denied | uncertain
      verification_status: GRANTED | DENIED-equivalent (UNKNOWN_VEHICLE,
                            BLOCKLISTED, FACE_MISMATCH) | MANUAL_REVIEW

    vehicle_registered and vehicle_blocklisted are passed separately (rather
    than one combined "is this vehicle OK" flag) because blocklist status
    must override everything else, including a face match that would
    otherwise pass (project notes, section 24: "Blocklist status overrides
    normal authorization" - even a matching face doesn't clear a
    blocklisted vehicle).
    """

    if not plate_detected or not plate_number:
        return "uncertain", "MANUAL_REVIEW", "Number plate could not be detected."

    if ocr_confidence < settings.MIN_PLATE_CONFIDENCE:
        return (
            "uncertain",
            "MANUAL_REVIEW",
            f"OCR confidence ({ocr_confidence:.0%}) is below the acceptance threshold.",
        )

    if not vehicle_registered and not vehicle_blocklisted:
        return "denied", "UNKNOWN_VEHICLE", f"Plate {plate_number} is not registered."

    # Blocklist overrides everything below, including a passing face match.
    if vehicle_blocklisted:
        return "denied", "BLOCKLISTED", f"Plate {plate_number} is on the blocklist."

    if require_face:
        if not face_result or not face_result.get("face_detected"):
            return "uncertain", "MANUAL_REVIEW", "No face detected for verification."

        if face_result.get("multiple_faces"):
            return "uncertain", "MANUAL_REVIEW", "Multiple faces detected at the gate - needs manual check."

        if not face_result.get("face_match"):
            return "denied", "FACE_MISMATCH", "Captured face does not match the registered owner."

        if face_result.get("similarity", 0) < settings.MIN_FACE_CONFIDENCE:
            return "uncertain", "MANUAL_REVIEW", "Face match confidence is below the acceptance threshold."

    return "granted", "GRANTED", None
