# Deploy the demo (Aiven MySQL → Render → Vercel)

Order matters: **database → backend → frontend → tell the backend the frontend URL**.

## 0. Generate the demo data (once, on your laptop)
1. Put your best gate video somewhere (H.264 MP4, ≤ ~25 MB; compress if needed:
   `ffmpeg -i gate.mp4 -vf scale=-2:720 -c:v libx264 -crf 28 -an gate_small.mp4`).
2. Follow *Run the full project locally* in the README, then
   `python ai-service/analyze_video.py gate_small.mp4 --publish`.
3. Open `demo-data/results.json` and check the plates are right. Edit `demo-data/demo_vehicles.json`
   so some plates are registered, one is blocklisted, one is missing (→ DENIED) — that is what makes the demo interesting.
4. Run locally once in demo mode (`DEMO_MODE=true`) and check **Video Analysis** looks right.
5. Commit and push everything to ONE GitHub repo.
   (`ai-service/weights/plate_best.pt` ~5 MB is fine to commit; `results.sample.json` can stay or go.)

## 1. Aiven MySQL
Use your existing free service and create a **new database** (e.g. `campus_guardian`) — don't mix tables with another project.
Copy the service URI → `mysql+pymysql://avnadmin:PASSWORD@HOST:PORT/campus_guardian`. The CA cert is already at `backend/certs/aiven-ca.pem`.
Make sure the service is **running** (free plans can power off when idle).

## 2. Render (backend)
New → **Blueprint** → pick the repo (it reads `render.yaml`), or New → Web Service with:

| Field | Value |
|---|---|
| Runtime | **Python** (not Docker) |
| Root Directory | **leave empty (repo root)** — the backend reads `demo-data/` which sits outside `backend/` |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Environment variables: `DEMO_MODE=true`, `APP_ENV=production`, `JWT_SECRET` (≥ 32 chars; `python -c "import secrets; print(secrets.token_urlsafe(48))"`),
`DATABASE_URL` (step 1), `DB_SSL_CA=certs/aiven-ca.pem`, `CORS_ORIGINS` (fill in after step 3), optional `GOOGLE_CLIENT_ID`.

On boot the backend creates tables and seeds users/gates/vehicles automatically. Check `https://YOUR-API.onrender.com/api/config` → `{"demo_mode":true,...}`.

## 3. Vercel (frontend)
Import the repo → **Root Directory = `frontend`**, Framework = Vite (auto), Build `npm run build`, Output `dist`.
Environment variables: `VITE_API_URL=https://YOUR-API.onrender.com`, `VITE_DEMO_MODE=true` (+ `VITE_GOOGLE_CLIENT_ID` if used). Deploy.

## 4. Close the loop
Back on Render set `CORS_ORIGINS=https://YOUR-APP.vercel.app` (exact, no trailing slash) → redeploy.
Put the Vercel URL in the README "Live demo" line.

## Checklist before sending the link
- [ ] Open the Vercel URL in a private window → sign in as `recruiter@campus.edu` / `Demo@123`
- [ ] **Video Analysis**: banner says "precomputed by the real pipeline", NOT "Sample data"
- [ ] Boxes follow the car, plate + ALLOWED/DENIED appear at the right moment, entry log fills up, clicking a row seeks the video
- [ ] Dashboard / Entry Logs / Students pages load (real DB)
- [ ] Wake the Render service a minute before showing it to anyone (free tier sleeps)

## Troubleshooting
| Symptom | Cause |
|---|---|
| "Could not reach the server" | `VITE_API_URL` wrong, or Render asleep — wait, retry |
| Login works locally, CORS error on Vercel | `CORS_ORIGINS` not exactly the Vercel URL |
| `404 demo-data/results.json not found` + banner "Sample data" | you haven't committed your real `demo-data/results.json` (or Render root isn't the repo root) |
| Backend crashes on boot with JWT error | `JWT_SECRET` shorter than 32 chars while `APP_ENV=production` |
| Video doesn't play | not H.264 MP4 — re-encode with the ffmpeg command above |
| All plates DENIED | the plates in the video aren't in `demo_vehicles.json` / DB (OCR reading may also differ by a character — fuzzy match tolerates ~1) |
