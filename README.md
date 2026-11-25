# 🛡️ Campus Guardian — AI campus vehicle-entry verification

YOLO plate detection → OCR → database lookup → **ALLOWED / DENIED**, with a React dashboard, role-based login and entry logs.

**▶ Live demo:** `https://YOUR-APP.vercel.app` — sign in with `recruiter@campus.edu` / `Demo@123`, then open **Video Analysis**.
*(The free backend sleeps when idle; the first login can take ~30–60 s to wake it up.)*

> **Demo mode vs full mode.** The AI pipeline (PyTorch + YOLO + EasyOCR) is too heavy for free hosting, so the hosted demo
> replays results that I computed offline with the real pipeline on a recorded gate video. Login, database, dashboard and the
> database check are live. To run the real pipeline on **any** video, clone the repo and use full mode (below) — same UI, same results format.

## How it works

| | Live demo (`DEMO_MODE=true`) | Local full project (`DEMO_MODE=false`) |
|---|---|---|
| Hosting | Vercel (frontend) + Render (backend) + Aiven MySQL | your machine |
| Login / database / dashboard / entry logs | real | real |
| Plate detection + OCR | **precomputed** → `demo-data/results.json` | **runs live** on your uploaded video |
| Database status + decision | re-checked live against the DB | looked up live |
| Backend installs | `backend/requirements.txt` only (no torch/YOLO/OpenCV) | + `ai-service/requirements.txt` |

Both modes produce the **same `results.json`** (`demo-data/results.schema.json`) and render it with **one component**
(`frontend/src/components/app/ResultsPlayer.jsx`).

## Repository layout

```
Campus-Guardian/
├─ frontend/      React + Vite dashboard                 → deployed to Vercel (Root Directory = frontend)
├─ backend/       FastAPI + SQLAlchemy, light deps       → deployed to Render (service root = repo root, see render.yaml)
├─ ai-service/    HEAVY: analyze_video.py, weights, training notebooks, requirements.txt (torch/ultralytics/easyocr)
├─ demo-data/     results.json (+ schema, demo vehicles, demo.mp4)
├─ docs/          project overview
└─ render.yaml
```

## Run the full project locally (any video)

Windows / VS Code shown; use `source venv/bin/activate` on macOS/Linux.

```bash
# 1. backend + AI deps
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu   # CPU build, much smaller
pip install -r ../ai-service/requirements.txt
copy .env.example .env          # then set DEMO_MODE=false in .env
python -m app.seed              # users, gates, demo students/vehicles
python run.py                   # http://localhost:8000/docs

# 2. frontend (new terminal)
cd frontend
npm install
copy .env.example .env          # VITE_API_URL=http://localhost:8000
npm run dev                     # http://localhost:5173
```

Sign in (`guard1@campus.edu` / `Guard@123`, or `admin@campus.edu` / `Admin@123`) → **Video Analysis** → upload a video.
Progress is shown while the pipeline runs; results play back in sync with the video and are also written to *Entry Logs* and *Alerts*.

## Refresh the demo data (after changing the video or model)

```bash
python ai-service/analyze_video.py path\to\gate.mp4 --publish     # writes demo-data/results.json, copies the video
```
Already have detections from Colab? `python ai-service/convert_pipeline_output.py detections.json gate.mp4 --publish`.
Edit `demo-data/demo_vehicles.json` to choose which plates in the video are registered / blocklisted (unlisted plates → DENIED).
Commit `demo-data/` and `frontend/public/demo.mp4`, push, and both hosts redeploy.

## Plate accuracy
`ai-service/plate_fix.py` corrects OCR look-alike slips using the Indian plate pattern (`MP07SA1908`: 2 letters, 2 digits, 1–3 letters, 4 digits),
and events use character-by-character voting across all frames of a vehicle. Measure on your own video:
`python ai-service/evaluate.py demo-data/results.json MP07SA1908 MP07ME0643 ...` (exact-match %, character similarity, false events).
If detection (not OCR) is the weak part, retrain the detector in Colab with more/harder images (`ai-service/training/`) and replace `ai-service/weights/plate_best.pt`.

## Deployment
Step-by-step (Aiven → Render → Vercel, env vars, checklist): **[DEPLOY.md](DEPLOY.md)**.

## Results format (excerpt)
```json
{ "timestamp": 3.3, "plate_text": "MP07AB1234", "plate_confidence": 0.93,
  "face_match_name": null, "face_score": null,
  "db_status": "REGISTERED", "decision": "ALLOWED",
  "bbox": { "x": 0.38, "y": 0.58, "w": 0.16, "h": 0.07 } }
```
`face_*` is `null` when face verification was not performed. Full schema: `demo-data/results.schema.json`.

## Tech
React · Vite · Tailwind · FastAPI · SQLAlchemy · MySQL/SQLite · JWT + Google sign-in · YOLO (Ultralytics) · EasyOCR
