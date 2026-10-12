"""
train_face_yolo.py
--------------------
Trains a YOLOv11 detector on the face-detection dataset
(face-detection_v1-version-3_yolov11.zip - single class "Face").

This is a plain face LOCALIZER (finds "where is a face"), not a face
recognizer - recognition/verification is a separate step done by
backend/app/ai/face_embedding.py using a pretrained FaceNet model (no
training needed there, just inference).

Run this in Google Colab (Runtime -> Change runtime type -> GPU):

    !pip install ultralytics
    from google.colab import files
    files.upload()   # upload face-detection_v1-version-3_yolov11.zip
    !unzip -q face-detection_v1-version-3_yolov11.zip -d face_dataset
    !python train_face_yolo.py --data face_dataset/data.yaml --epochs 60 --device 0

Then download runs_face/face_yolo11/weights/best.pt and copy it to
backend/app/ai/weights/face_best.pt in this project.
"""

import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv11 on the face-detection dataset")
    parser.add_argument("--data", type=str, required=True, help="Path to the dataset's data.yaml")
    parser.add_argument("--model", type=str, default="yolo11n.pt",
                         help="Base checkpoint: yolo11n.pt (fast) / yolo11s.pt (more accurate)")
    parser.add_argument("--epochs", type=int, default=60,
                         help="Faces are a well-studied, fairly uniform object class, so this "
                              "usually needs fewer epochs than the plate model to converge well.")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0", help="'0' for GPU, 'cpu' if none")
    parser.add_argument("--project", type=str, default="runs_face")
    parser.add_argument("--name", type=str, default="face_yolo11")
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"Could not find {data_path}")

    model = YOLO(args.model)
    model.train(
        data=str(data_path), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        device=args.device, project=args.project, name=args.name,
        patience=15, pretrained=True, optimizer="auto", verbose=True,
        # Faces ARE meaningfully mirror-symmetric, so (unlike the plate
        # model) horizontal flip augmentation is fine and helpful here.
        degrees=8.0, translate=0.1, scale=0.4, fliplr=0.5, mosaic=1.0,
    )

    metrics = model.val(data=str(data_path), split="test")
    print("Test metrics:", metrics.results_dict)

    best_weights = Path(args.project) / args.name / "weights" / "best.pt"
    print(f"\nTraining complete. Best weights: {best_weights}")
    print("Copy this file to backend/app/ai/weights/face_best.pt")


if __name__ == "__main__":
    main()
