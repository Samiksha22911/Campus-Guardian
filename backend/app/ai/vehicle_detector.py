"""Vehicle detection service - NOT part of the active AI pipeline.

The project's design decision (see the spec: "there is NO vehicle-type
classification AI model in this project") is that vehicle type is a plain
database field the admin sets when registering a vehicle, not something an
AI model guesses from the image. verification_pipeline.py no longer
imports or calls this module - it's kept here only in case a future
version of the project explicitly wants to reintroduce vehicle-type
classification as its own opt-in step.

If you do want to re-enable it: import VehicleDetector in
verification_pipeline.py, call it before plate detection as before, and
implement `.detect()` below with a real YOLO model loaded once at import
time, returning the same shaped dict.
"""

import hashlib

from ..config import settings

VEHICLE_TYPES = ["Bike", "Scooty", "Activa", "Car", "Other"]


class VehicleDetector:
    def detect(self, image_bytes: bytes) -> dict:
        if not settings.MOCK_AI:
            raise NotImplementedError(
                "Real vehicle detection is not configured. Set MOCK_AI=true "
                "or implement VehicleDetector.detect() with your YOLO model."
            )

        digest = hashlib.sha256(image_bytes).hexdigest()
        seed = int(digest[:8], 16)

        # ~92% detection rate in mock mode
        detected = (seed % 100) < 92
        vehicle_type = VEHICLE_TYPES[seed % len(VEHICLE_TYPES)]

        return {
            "vehicle_detected": detected,
            "vehicle_type": vehicle_type if detected else None,
            "confidence": round(0.80 + (seed % 20) / 100, 2) if detected else 0.0,
        }
