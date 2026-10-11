"""Standalone AI-component tests - run BEFORE trusting the full pipeline.

Implements the "Important Testing Strategy" from the project notes
(section 37): test each component independently before integrating
everything into the backend, and don't assume a model works just because
training finished.

Usage (from backend/, venv active, MOCK_AI=false, weights already trained
and placed at the paths configured in .env):

    python -m app.test_ai_components --plate-image /path/to/vehicle.jpg
    python -m app.test_ai_components --face-image /path/to/face.jpg
    python -m app.test_ai_components --plate-image v.jpg --face-image f.jpg --compare-face-image f2.jpg

With no arguments, it runs the face detector against the three generic
sample images shipped in app/ai/samples/ (public dataset images used only
to sanity-check that the face-detection code runs end-to-end - they are
NOT tied to any student record).

Each test prints exactly what the corresponding pipeline stage returned, so
you can tell whether a "no detections" result is a real model/dataset
problem (project notes, section 36) rather than a wiring bug.
"""

import argparse
import glob
import os

from .ai.face_detector import FaceDetector
from .ai.face_embedding import compute_embedding, cosine_similarity
from .ai.image_utils import bytes_to_bgr
from .ai.ocr_service import OCRService
from .ai.plate_detector import PlateDetector

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "ai", "samples")


def test_plate_detection(image_path: str):
    print(f"\n[TEST 1] Plate detection on: {image_path}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    result = PlateDetector().detect(image_bytes)
    print(f"  plate_detected = {result['plate_detected']}")
    print(f"  confidence     = {result['confidence']}")
    print(f"  bounding_box   = {result['bounding_box']}")

    if not result["plate_detected"]:
        print("  -> No plate found. Before assuming the model is broken, check:")
        print("     dataset/label quality, confidence threshold (PLATE_DETECTOR_CONF),")
        print("     image resolution, and how different this photo is from training images.")
    return result


def test_ocr(image_path: str, plate_result: dict):
    print(f"\n[TEST 2] OCR on the plate crop from: {image_path}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ocr = OCRService().read_plate(
        image_bytes,
        known_plates=[],
        plate_crop_jpeg=plate_result.get("plate_crop_jpeg"),
    )
    print(f"  plate_number   = {ocr['plate_number']}")
    print(f"  ocr_confidence = {ocr['ocr_confidence']}")
    print(f"  raw_text       = {ocr['raw_text']!r}")
    return ocr


def test_face_detection(image_path: str):
    print(f"\n[TEST 4] Face detection on: {image_path}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    result = FaceDetector().detect(image_bytes)
    print(f"  face_detected  = {result['face_detected']}")
    print(f"  confidence     = {result['confidence']}")
    print(f"  bounding_box   = {result['bounding_box']}")
    print(f"  multiple_faces = {result['multiple_faces']}")
    return result, image_bytes


def test_face_similarity(image_path_a: str, image_path_b: str):
    print(f"\n[TEST 5] Face embedding similarity: {image_path_a}  vs  {image_path_b}")

    detector = FaceDetector()

    def _embed(path):
        with open(path, "rb") as f:
            image_bytes = f.read()
        det = detector.detect(image_bytes)
        if not det["face_detected"]:
            print(f"  No face detected in {path} - cannot compute similarity.")
            return None
        frame = bytes_to_bgr(image_bytes)
        x1, y1, x2, y2 = det["bounding_box_xyxy"]
        crop = frame[y1:y2, x1:x2]
        return compute_embedding(crop)

    vec_a = _embed(image_path_a)
    vec_b = _embed(image_path_b)
    if vec_a is None or vec_b is None:
        return None

    similarity = cosine_similarity(vec_a, vec_b)
    print(f"  similarity = {similarity:.4f}  (>= MIN_FACE_CONFIDENCE in .env => considered a match)")
    return similarity


def run_sample_smoke_test():
    """No arguments given - just prove the face pipeline runs at all using
    the generic sample images shipped with the project."""
    samples = sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.jpg")))
    if not samples:
        print("No sample images found in app/ai/samples/.")
        return

    print("No --plate-image / --face-image given - running a smoke test on")
    print("the generic sample images in app/ai/samples/ instead:\n")
    for path in samples:
        test_face_detection(path)


def main():
    parser = argparse.ArgumentParser(description="Run individual AI pipeline components in isolation")
    parser.add_argument("--plate-image", help="Photo of a vehicle to test plate detection + OCR on")
    parser.add_argument("--face-image", help="Photo containing a face to test face detection on")
    parser.add_argument("--compare-face-image", help="A second face photo to compare against --face-image")
    args = parser.parse_args()

    if not args.plate_image and not args.face_image:
        run_sample_smoke_test()
        return

    if args.plate_image:
        plate_result = test_plate_detection(args.plate_image)
        if plate_result["plate_detected"]:
            test_ocr(args.plate_image, plate_result)

    if args.face_image:
        test_face_detection(args.face_image)
        if args.compare_face_image:
            test_face_similarity(args.face_image, args.compare_face_image)


if __name__ == "__main__":
    main()
