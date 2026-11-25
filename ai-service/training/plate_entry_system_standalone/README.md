# College Vehicle Entry System — Plate Detection + OCR + Database Check

This project uses your `Plate_Number_v1-version-2_yolov11` dataset to train a
YOLOv11 detector that finds license plates, reads the text with OCR, and
checks it against a database of registered vehicles to decide whether to
allow entry.

## 1. Your dataset (already inspected)

```
train/images  9685 images   train/labels  9685 label files
valid/images   200 images   valid/labels   200 label files
test/images    100 images   test/labels    100 label files

data.yaml:
  nc: 1
  names: ['license_plate']
```

It's a standard Roboflow YOLO export — one class, `license_plate`, with
normalized-YOLO-format `.txt` labels (`class x_center y_center width height`).
That means this model only draws a box around the plate; it does **not**
read the characters — that's what the separate OCR step below is for.

## 2. Architecture

```
Camera/Image
     │
     ▼
[1] YOLOv11 detector  → finds the plate, crops it out
     │  (train_yolo.py trains this on your dataset)
     ▼
[2] EasyOCR           → reads the characters off the crop
     │  (ocr_reader.py — includes preprocessing: upscale, denoise, threshold)
     ▼
[3] SQLite registry    → exact + fuzzy match against registered plates
     │  (database.py — fuzzy match tolerates 1-2 char OCR mistakes like O/0)
     ▼
ALLOWED → open gate / log      DENIED → log, deny entry
```

## 3. Files in this project

| File | Purpose |
|---|---|
| `data.yaml` | Copied from your dataset — tells YOLO where train/valid/test images live |
| `train_yolo.py` | Fine-tunes a YOLOv11 checkpoint on your plate dataset |
| `plate_detector.py` | Loads the trained weights, detects & crops plates from a frame |
| `ocr_reader.py` | EasyOCR wrapper with preprocessing + text cleanup |
| `database.py` | SQLite schema, `add_vehicle`, `check_plate` (exact + fuzzy), `log_entry` |
| `add_vehicle.py` | CLI to register/remove/list vehicles without writing SQL |
| `main_pipeline.py` | Full pipeline runnable on a single image or a live webcam |
| `dashboard.py` | Streamlit web UI — upload a photo, see detection + OCR + allow/deny + log table |
| `requirements.txt` | All Python dependencies |

## 4. Step-by-step setup

### Step 1 — Environment
```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
```
A GPU (even a laptop GTX/RTX card) makes training far faster, but everything
also runs on CPU — just slower for training (inference is fine on CPU).

### Step 2 — Unzip your dataset
Unzip `Plate_Number_v1-version-2_yolov11.zip` somewhere, e.g.:
```
~/datasets/plate_number_v1/
    data.yaml
    train/images  train/labels
    valid/images  valid/labels
    test/images   test/labels
```
Copy the extracted folder's `data.yaml` over the one in this project, or just
point `--data` at the extracted one directly (see Step 3).

### Step 3 — Train the detector
```bash
python train_yolo.py --data ~/datasets/plate_number_v1/data.yaml \
                      --model yolo11n.pt \
                      --epochs 100 \
                      --device 0        # or "cpu"
```
- `yolo11n.pt` (nano) trains fastest and is plenty accurate for a single-class,
  fairly consistent object like a plate. Use `yolo11s.pt` if you want a small
  accuracy bump and have the compute.
- With ~9.7k training images, 100 epochs on a mid-range GPU takes roughly
  1–3 hours; on CPU expect much longer — consider dropping to ~30–50 epochs
  or a Colab GPU runtime if you don't have local GPU access.
- Best weights land at `runs_plate/plate_yolo11/weights/best.pt`.

### Step 4 — Seed the vehicle database
```bash
python database.py          # creates vehicles.db with 3 sample vehicles
python add_vehicle.py list  # confirm they're there
```
Now register your college's real vehicles:
```bash
python add_vehicle.py add --plate MP04CD5566 --name "Priya Patel" --role student --dept ECE --type bike
python add_vehicle.py add --plate MP09AB1122 --name "Dr. Sharma"  --role faculty --dept Admin --type car
```
(In practice you'd bulk-import this from your college's existing vehicle
registration spreadsheet — happy to add a CSV-import script if you have one.)

### Step 5 — Test on a single image
```bash
python main_pipeline.py --weights runs_plate/plate_yolo11/weights/best.pt \
                         --image test_car.jpg
```
This prints ALLOWED/DENIED to the console and saves `result_test_car.jpg`
with the detected box and OCR text drawn on it.

### Step 6 — Test on a live camera (gate simulation)
```bash
python main_pipeline.py --weights runs_plate/plate_yolo11/weights/best.pt --webcam
```
Press `q` to quit. `open_gate()` in `main_pipeline.py` currently just prints
`>>> GATE OPEN <<<` — replace it with your actual hardware trigger (see
Step 7).

### Step 7 (optional) — Demo dashboard
```bash
streamlit run dashboard.py -- --weights runs_plate/plate_yolo11/weights/best.pt
```
Upload a photo, see the box + OCR reading + allow/deny result + a live log
table. Good for a viva/demo since it needs no camera hardware.

## 5. Wiring to real gate hardware (if this needs to physically open a barrier)

`open_gate()` in `main_pipeline.py` is a stub. On a Raspberry Pi:
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

def open_gate():
    GPIO.output(RELAY_PIN, GPIO.HIGH)   # trigger relay -> barrier motor/servo
    time.sleep(5)
    GPIO.output(RELAY_PIN, GPIO.LOW)
```
If instead this feeds a college ID-card/turnstile system, `open_gate()` is
where you'd call that system's API instead.

## 6. Why detection + OCR are separate models

YOLO is good at *finding where* an object is, not at *reading fine-grained
text* — it wasn't trained to distinguish "8" from "B" at the character
level. So the standard pipeline (and what this project does) is:
1. YOLO finds and crops the plate (this is what your dataset trains),
2. a dedicated OCR engine (EasyOCR here) reads the characters off that crop.

## 7. Accuracy tips once it's running

- **False plate reads**: tighten `min_confidence` in `ocr_reader.read_plate`,
  or add a regex check in `database.check_plate` for your region's plate
  format (e.g. Indian plates: `^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$`) to
  reject obviously-malformed OCR output before even checking the DB.
- **Fuzzy match threshold**: `fuzzy_threshold=0.82` in `database.check_plate`
  balances tolerating OCR slips vs. accidentally admitting a wrong-but-similar
  plate. Lower it cautiously — a stricter threshold is safer for a security
  gate.
- **Multiple plates in frame**: `PlateDetector.detect` returns all boxes
  sorted by confidence; `main_pipeline.py` currently checks every one found,
  which is right for a gate camera that might catch two vehicles at once.
- **Low light / motion blur**: this dataset looks like a mix of clear photos;
  if your real gate camera has to handle night traffic, consider adding a
  handful of your own low-light plate photos to `train/images` +
  `train/labels` (same YOLO format) and retraining, or add an IR/flood light
  at the gate — cheaper than fixing it purely in software.

## 8. Suggested demo/report structure

For a college project report or viva:
1. Problem statement — manual gate entry is slow / unregistered vehicles.
2. Dataset — 9,685 train / 200 valid / 100 test images, Roboflow license
   plate dataset, single class.
3. Model — YOLOv11n fine-tuned via transfer learning; report your final
   `mAP50`/`mAP50-95` from Step 3's validation output.
4. OCR — EasyOCR + preprocessing pipeline; report OCR accuracy on a sample
   of test images (compare `read_plate()` output vs. ground truth you type
   in by hand).
5. System integration — SQLite registry, exact + fuzzy matching, entry
   logging, (optional) live dashboard.
6. Results/limitations — mention lighting, angle, and motion-blur failure
   cases; propose the retraining/hardware fixes from Section 7 as future work.
