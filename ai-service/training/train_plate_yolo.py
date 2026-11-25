"""
train_plate_yolo.py
--------------------
Trains a YOLOv11 detector on the license-plate dataset
(Plate_Number_v1-version-2_yolov11.zip - single class "license_plate").

Run this in Google Colab (Runtime -> Change runtime type -> GPU) since the
project's laptop has no dedicated GPU:

    !pip install ultralytics
    from google.colab import files
    files.upload()   # upload Plate_Number_v1-version-2_yolov11.zip
    !unzip -q Plate_Number_v1-version-2_yolov11.zip -d plate_dataset
    !python train_plate_yolo.py --data plate_dataset/data.yaml --epochs 100 --device 0

Then download runs_plate/plate_yolo11/weights/best.pt and copy it to
backend/app/ai/weights/plate_best.pt in this project.
"""

import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv11 on the plate dataset")
    parser.add_argument("--data", type=str, required=True, help="Path to the dataset's data.yaml")
    parser.add_argument("--model", type=str, default="yolo11n.pt",
                         help="Base checkpoint: yolo11n.pt (fast) / yolo11s.pt (more accurate)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0", help="'0' for GPU, 'cpu' if none")
    parser.add_argument("--project", type=str, default="runs_plate")
    parser.add_argument("--name", type=str, default="plate_yolo11")
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"Could not find {data_path}")

    model = YOLO(args.model)
    model.train(
        data=str(data_path), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        device=args.device, project=args.project, name=args.name,
        patience=20, pretrained=True, optimizer="auto", verbose=True,
        degrees=5.0, translate=0.1, scale=0.3, fliplr=0.0, mosaic=1.0,
    )

    metrics = model.val(data=str(data_path), split="test")
    print("Test metrics:", metrics.results_dict)

    best_weights = Path(args.project) / args.name / "weights" / "best.pt"
    print(f"\nTraining complete. Best weights: {best_weights}")
    print("Copy this file to backend/app/ai/weights/plate_best.pt")


if __name__ == "__main__":
    main()
