"""CLI helper to enroll REAL face embeddings for the demo students seeded
by seed.py, once you've switched to real AI mode (MOCK_AI=false) and
trained/placed the face-detection weights.

This deliberately does NOT ship with any actual photos of the demo
students - their seeded `profile_image` is a synthetic placeholder avatar,
not a real photo of a real person (see seed.py's module docstring for why).
To actually test face verification, supply your own photo of a real face
for each student you want to enroll:

    python -m app.enroll_demo_faces --student STU2001 --photo /path/to/photo.jpg

This calls the exact same FaceDetector + face_embedding pipeline used by
`POST /api/students/{id}/photo`, so if this script works, the API endpoint
(and therefore the enrollment flow in the frontend) will too.
"""

import argparse

from .ai.face_detector import FaceDetector
from .ai.face_embedding import compute_embedding, serialize_embedding
from .ai.image_utils import bytes_to_bgr
from .database import SessionLocal
from .models import Student


def enroll(student_code: str, photo_path: str) -> None:
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.student_id == student_code.upper()).first()
        if not student:
            raise SystemExit(
                f"No student with student_id={student_code!r} found. Run `python -m app.seed` first."
            )

        with open(photo_path, "rb") as f:
            image_bytes = f.read()

        detection = FaceDetector().detect(image_bytes)
        if not detection["face_detected"]:
            raise SystemExit("No face detected in that photo - try a clearer, front-facing photo.")
        if detection.get("multiple_faces"):
            raise SystemExit("Multiple faces detected in that photo - use one with only a single person.")

        frame = bytes_to_bgr(image_bytes)
        x1, y1, x2, y2 = detection["bounding_box_xyxy"]
        crop = frame[y1:y2, x1:x2]

        vector = compute_embedding(crop)
        student.face_embedding = serialize_embedding(vector)
        db.commit()

        print(f"Enrolled a real face embedding for {student.student_id} ({student.name}).")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enroll a real face embedding for a seeded demo student")
    parser.add_argument("--student", required=True, help="student_id, e.g. STU2001")
    parser.add_argument("--photo", required=True, help="Path to a photo containing exactly one clear face")
    args = parser.parse_args()
    enroll(args.student, args.photo)
