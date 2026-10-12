"""
main_pipeline.py
------------------
End-to-end vehicle-entry pipeline:

    frame -> PlateDetector (YOLOv11) -> crop -> PlateOCR (EasyOCR)
          -> database.check_plate() -> ALLOWED/DENIED -> log + (optional) gate signal

Two modes:
    --image path/to/photo.jpg      run once on a single image
    --webcam                       run continuously on a live camera (gate demo)

Usage:
    python main_pipeline.py --weights runs_plate/plate_yolo11/weights/best.pt --image test_car.jpg
    python main_pipeline.py --weights runs_plate/plate_yolo11/weights/best.pt --webcam
"""

import argparse
import time
import cv2

from plate_detector import PlateDetector
from ocr_reader import PlateOCR
from database import init_db, check_plate, log_entry


def open_gate():
    """
    Placeholder for actuating the physical barrier.
    On a Raspberry Pi you'd swap this for e.g. RPi.GPIO to trigger a
    relay/servo controlling the boom barrier. Left as a stub so this
    project runs anywhere without extra hardware.
    """
    print(">>> GATE OPEN <<<")


def process_frame(frame, detector: PlateDetector, ocr: PlateOCR, show=True):
    detections = detector.detect(frame)
    texts = []

    for det in detections:
        plate_text, ocr_conf = ocr.read_plate(det.crop)
        texts.append(plate_text)

        if not plate_text:
            print("Plate detected but OCR could not read it clearly. Skipping.")
            continue

        result = check_plate(plate_text)
        log_entry(plate_text, result)

        if result.allowed:
            owner = result.record.owner_name if result.record else "Unknown"
            print(f"[ALLOWED] Detected: {plate_text}  ->  Matched: {result.matched_plate} "
                  f"(owner: {owner}, similarity: {result.similarity:.2f}, OCR conf: {ocr_conf:.2f})")
            open_gate()
        else:
            print(f"[DENIED]  Detected: {plate_text}  -> No match in registry "
                  f"(closest similarity: {result.similarity:.2f}). Access denied.")

    if show:
        annotated = detector.draw_boxes(frame, detections, texts)
        return annotated
    return frame


def run_on_image(args):
    detector = PlateDetector(args.weights, conf_threshold=args.conf, device=args.device)
    ocr = PlateOCR(gpu=(args.device != "cpu"))

    frame = cv2.imread(args.image)
    if frame is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    annotated = process_frame(frame, detector, ocr)
    out_path = "result_" + args.image.split("/")[-1]
    cv2.imwrite(out_path, annotated)
    print(f"Annotated result saved to {out_path}")


def run_on_webcam(args):
    detector = PlateDetector(args.weights, conf_threshold=args.conf, device=args.device)
    ocr = PlateOCR(gpu=(args.device != "cpu"))

    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam/camera source.")

    last_process_time = 0
    process_every_n_seconds = args.interval  # throttle OCR - it's the slow step

    print("Press 'q' to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        now = time.time()
        if now - last_process_time >= process_every_n_seconds:
            frame = process_frame(frame, detector, ocr)
            last_process_time = now

        cv2.imshow("College Gate - Plate Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Number plate entry system")
    parser.add_argument("--weights", required=True, help="Path to trained YOLOv11 best.pt")
    parser.add_argument("--conf", type=float, default=0.4, help="Detection confidence threshold")
    parser.add_argument("--device", default="cpu", help="'cpu' or '0' for GPU")
    parser.add_argument("--image", help="Path to a single image to test")
    parser.add_argument("--webcam", action="store_true", help="Run continuously on live camera")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--interval", type=float, default=1.5,
                         help="Seconds between OCR passes in webcam mode (throttles CPU load)")
    args = parser.parse_args()

    init_db()

    if args.image:
        run_on_image(args)
    elif args.webcam:
        run_on_webcam(args)
    else:
        parser.error("Pass either --image <path> or --webcam")


if __name__ == "__main__":
    main()
