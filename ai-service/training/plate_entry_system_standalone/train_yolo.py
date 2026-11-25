"""
train_yolo.py
-------------
Trains a YOLOv11 object-detection model on the license-plate dataset
(train/valid/test, single class: "license_plate").

Dataset layout expected (this matches your unzipped Roboflow export):

    dataset_root/
        data.yaml
        train/images, train/labels
        valid/images, valid/labels
        test/images,  test/labels

Usage:
    python train_yolo.py --data /path/to/dataset_root/data.yaml --epochs 100
"""

import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv11 on the plate dataset")
    parser.add_argument("--data", type=str, default="data.yaml",
                         help="Path to the dataset's data.yaml")
    parser.add_argument("--model", type=str, default="yolo11n.pt",
                         help="Base checkpoint to fine-tune: yolo11n.pt (fast) / "
                              "yolo11s.pt / yolo11m.pt (more accurate, slower)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0",
                         help="'0' for first GPU, 'cpu' if you have no GPU")
    parser.add_argument("--project", type=str, default="runs_plate")
    parser.add_argument("--name", type=str, default="plate_yolo11")
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    if not data_path.exists():
        raise FileNotFoundError(
            f"Could not find {data_path}. Point --data at the data.yaml "
            f"that came with the unzipped dataset."
        )

    # Load a COCO-pretrained YOLOv11 checkpoint and fine-tune it on our
    # single-class license-plate dataset (transfer learning).
    model = YOLO(args.model)

    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=20,          # early stopping if val metrics stall
        pretrained=True,
        optimizer="auto",
        verbose=True,
        # Light augmentation is usually enough since plates are small,
        # rigid, high-contrast objects.
        degrees=5.0,
        translate=0.1,
        scale=0.3,
        fliplr=0.0,            # don't flip plates horizontally, text becomes unreadable/misleading
        mosaic=1.0,
    )

    # Evaluate on the held-out test split
    metrics = model.val(data=str(data_path), split="test")
    print("Test metrics:", metrics.results_dict)

    best_weights = Path(args.project) / args.name / "weights" / "best.pt"
    print(f"\nTraining complete. Best weights saved at: {best_weights}")
    print("Copy/point to this file as PLATE_MODEL_PATH in plate_detector.py")


if __name__ == "__main__":
    main()
