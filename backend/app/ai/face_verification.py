"""Face verification service.

Compares the face captured at the gate against the face embedding stored
for the student associated with the *already-matched* vehicle. This only
ever answers a 1:1 question - "does this face match the registered owner?"
- never open-set identification against arbitrary people (project notes,
section 18: "Very Important Face Matching Rule"). The number plate lookup
(done by the caller, before this is invoked) is what determines whose face
to expect; this module never searches the whole student database.

Real mode (MOCK_AI=false): FaceDetector -> crop -> face_embedding ->
cosine similarity against the student's stored embedding.

Mock mode (MOCK_AI=true, the default): unchanged from the original scaffold.
"""

import hashlib
import random

from ..config import settings
from . import face_embedding as face_embedding_module
from .face_detector import FaceDetector
from .image_utils import bytes_to_bgr

_detector_singleton = None


def _get_detector() -> FaceDetector:
    global _detector_singleton
    if _detector_singleton is None:
        _detector_singleton = FaceDetector()
    return _detector_singleton


class FaceVerificationService:
    def verify(
        self,
        image_bytes: bytes,
        reference_embedding: str | None,
        scenario: str | None = None,
    ) -> dict:
        if settings.MOCK_AI:
            return self._mock_verify(image_bytes, reference_embedding, scenario)
        return self._real_verify(image_bytes, reference_embedding)

    # ------------------------------------------------------------------
    # Real implementation
    # ------------------------------------------------------------------
    def _real_verify(self, image_bytes: bytes, reference_embedding: str | None) -> dict:
        stored_vector = face_embedding_module.deserialize_embedding(reference_embedding)
        if stored_vector is None:
            return {
                "face_detected": True,
                "face_match": False,
                "similarity": 0.0,
                "reason": "no_reference",
                "multiple_faces": False,
            }

        detector = _get_detector()
        det = detector.detect(image_bytes)

        if not det["face_detected"]:
            return {
                "face_detected": False,
                "face_match": False,
                "similarity": 0.0,
                "reason": "no_face_detected",
                "multiple_faces": False,
            }

        frame = bytes_to_bgr(image_bytes)
        x1, y1, x2, y2 = det["bounding_box_xyxy"]
        crop = frame[y1:y2, x1:x2]

        live_vector = face_embedding_module.compute_embedding(crop)
        similarity = face_embedding_module.cosine_similarity(live_vector, stored_vector)

        return {
            "face_detected": True,
            "face_match": similarity >= settings.MIN_FACE_CONFIDENCE,
            "similarity": round(similarity, 4),
            "reason": None,
            "multiple_faces": det.get("multiple_faces", False),
        }

    # ------------------------------------------------------------------
    # Mock implementation (unchanged from the original scaffold)
    # ------------------------------------------------------------------
    def _mock_verify(self, image_bytes, reference_embedding, scenario=None) -> dict:
        if not reference_embedding:
            return {
                "face_detected": True,
                "face_match": False,
                "similarity": 0.0,
                "reason": "no_reference",
                "multiple_faces": False,
            }

        digest = hashlib.sha256(image_bytes + b"face").hexdigest()
        rng = random.Random(int(digest[:8], 16))

        if scenario == "face_mismatch":
            return {
                "face_detected": True,
                "face_match": False,
                "similarity": round(rng.uniform(0.20, 0.45), 2),
                "reason": None,
                "multiple_faces": False,
            }

        if scenario == "no_face":
            return {
                "face_detected": False,
                "face_match": False,
                "similarity": 0.0,
                "reason": "no_face_detected",
                "multiple_faces": False,
            }

        matched = rng.random() < 0.85
        similarity = round(rng.uniform(0.72, 0.98), 2) if matched else round(rng.uniform(0.15, 0.55), 2)

        return {
            "face_detected": True,
            "face_match": matched,
            "similarity": similarity,
            "reason": None,
            "multiple_faces": False,
        }
