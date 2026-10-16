# Campus Guardian – fix + deploy guide

Stack: React (Vercel) → FastAPI (Render, Docker) → Aiven MySQL, Google sign-in, YOLO plate model + EasyOCR, looping demo video.

## 0. What was actually broken (found in your zip)

| # | Problem | Why it hurt |
|---|---------|-------------|
| 1 | **No Google OAuth code existed** – Login page is email/password only, backend only has `/api/auth/login` | Nothing to "integrate", so Google login could never work |
| 2 | `MOCK_AI=true` by default and `app/ai/weights/*.pt` is in `.gitignore` | Your trained model never reached GitHub/Render; results were random fake plates |
| 3 | Database defaults to SQLite; Aiven needs TLS and `database.py` had no SSL setup | Backend can't talk to Aiven |
| 4 | The seed script never runs on Render | Empty cloud DB → no users → can't log in |
| 5 | `CORS_ORIGINS` only allows localhost | Browser blocks every call from your Vercel domain |
| 6 | `VITE_API_URL` defaults to `http://localhost:8000` | Deployed frontend calls localhost |
| 7 | Live page only accepts a manual image upload; camera is a static picture | No looping video, no auto verification |
| 8 | A loop would create a new log + alert for every frame | Needed duplicate suppression + "no plate in frame" skipping |
| 9 | EasyOCR downloads its model on first request; torch is big | First request times out; image too heavy |

## 1. What the patched files change

- `backend/app/routers/auth.py` – new `POST /api/auth/google` (verifies Google ID token, maps email → user, issues your normal JWT)
- `backend/app/database.py`, `config.py` – Aiven MySQL SSL (`DB_SSL_CA`), Google + dedupe settings
- `backend/app/routers/verification.py` – `live` mode: frames with no plate are ignored; same plate at same gate within `DEDUPE_WINDOW_SECONDS` (45 s) returns the earlier result instead of a new log/alert
- `backend/app/main.py` – loads YOLO + EasyOCR at startup
- `backend/Dockerfile`, `requirements-ai-plate.txt` – CPU torch + ultralytics + EasyOCR, EasyOCR weights baked into the image
- `backend/.gitignore` – allows `plate_best.pt` to be committed
- `frontend`: `GoogleSignInButton.jsx` (no npm package needed), `LoopVideoPanel.jsx` (looping video + frame capture every 2/3/5 s), edits to `Login.tsx`, `Live.tsx`, `app-store.jsx`, `api-client.js`

Copy these files over your repo (same paths), commit, push.

## 2. Put your assets in the repo

1. **Plate model**: from Colab download your trained `best.pt` (usually `runs/detect/train/weights/best.pt`). Rename to `plate_best.pt`, place in `backend/app/ai/weights/`. (YOLO-nano/small is ~6–25 MB, fine for GitHub.)
2. **Video**: your recording as `frontend/public/demo.mp4`. Keep it under ~25 MB (H.264, 720p is enough). Use a clip where plates are clearly readable.
3. **Aiven CA cert** (after step 4): `backend/certs/aiven-ca.pem` (it's a public certificate, OK to commit).

## 3. Test everything locally FIRST (real model, local SQLite)

```bash
cd backend
python -m venv venv && venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-ai-plate.txt
copy .env.example .env
```
Edit `.env`: `MOCK_AI=false`, `APP_ENV=development`. Then:
```bash
python -m app.seed
python run.py            # http://localhost:8000/docs
```
In a second terminal: `cd frontend && npm install && npm run dev`, log in (`guard1@campus.edu / Guard@123`), open **Live Gate Monitoring**, click **Start auto-verify**.

Don't continue until the video gives sensible plates. If OCR is weak, tune in `.env`: `PLATE_DETECTOR_CONF`, `MIN_PLATE_CONFIDENCE` (try 0.4), `PLATE_FUZZY_THRESHOLD`.

**Register the plates that appear in your video**: Vehicles page → add them (or edit `DEMO_STUDENTS` in `seed.py`). Leave at least one plate unregistered, and have one unreadable moment → you can show green, red alert and manual review.

## 4. Aiven MySQL

1. Aiven console → create a **MySQL** service (free plan if offered; free services can power off when idle, so check it's running before a demo).
2. Overview page: copy host, port, user (`avnadmin`), password; download **CA certificate**.
3. Build the URL for SQLAlchemy – **replace `mysql://` with `mysql+pymysql://` and delete any `?ssl-mode=REQUIRED` at the end**:
   `mysql+pymysql://avnadmin:PASSWORD@HOST:PORT/defaultdb`
   (special characters in the password must be URL-encoded)
4. Make sure the service allows connections from anywhere (Allowed IP addresses `0.0.0.0/0`) – Render's IPs change.
5. Seed the cloud DB once from your laptop:
   ```bash
   set DATABASE_URL=mysql+pymysql://avnadmin:PASSWORD@HOST:PORT/defaultdb
   set DB_SSL_CA=certs/aiven-ca.pem
   python -m app.seed
   ```
   Tables are created automatically. Check the data in Aiven's console / any MySQL client.

## 5. Google OAuth (Google Cloud Console)

1. APIs & Services → **OAuth consent screen**: External, add your app name and email. While in "Testing", add your Gmail (and teammates') under **Test users**.
2. **Credentials → Create credentials → OAuth client ID → Web application**.
3. **Authorized JavaScript origins**: `http://localhost:5173` and your exact Vercel URL, e.g. `https://campus-guardian.vercel.app` (no trailing slash, no path). *Authorized redirect URIs: leave empty* – this flow returns an ID token to the page, not a redirect.
4. Copy the **Client ID** (the client secret is not used). Changes can take a few minutes.

Who may sign in: by default only emails that already exist in the `users` table. For the demo, set `GOOGLE_AUTO_CREATE=true` and `GOOGLE_ADMIN_EMAILS=yourgmail@gmail.com`, then switch auto-create off afterwards.

## 6. Render (backend)

New → **Web Service** → connect the GitHub repo → **Root Directory: `backend`** → **Runtime: Docker** → Health Check Path `/health`.

**Instance size matters**: torch + YOLO + EasyOCR need roughly 1.5–2 GB RAM. Render's free instance (512 MB, check current specs) will likely crash with out-of-memory. Use a paid instance with ≥2 GB for the demo, or run with `MOCK_AI=true` just to test the plumbing.

Environment variables:

| Key | Value |
|-----|-------|
| `APP_ENV` | `production` |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | the Aiven URL from step 4 |
| `DB_SSL_CA` | `certs/aiven-ca.pem` |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` (exact, no trailing `/`; comma-separate extra origins) |
| `MOCK_AI` | `false` |
| `PLATE_MODEL_PATH` | `app/ai/weights/plate_best.pt` |
| `GOOGLE_CLIENT_ID` | from step 5 |
| `GOOGLE_AUTO_CREATE` / `GOOGLE_ADMIN_EMAILS` | as above |
| `DEDUPE_WINDOW_SECONDS` | `45` |

After deploy open `https://YOUR-API.onrender.com/health` → `{"status":"healthy"}`, and `/` → shows `"mock_ai": false`. Watch Render logs for "AI models warmed up".

Note: Render's disk is wiped on redeploy, so captured entry images vanish (DB rows stay). Fine for a demo.

## 7. Vercel (frontend)

Project → Settings → Environment Variables (Root Directory `frontend`):

- `VITE_API_URL` = `https://YOUR-API.onrender.com` (no trailing slash)
- `VITE_GOOGLE_CLIENT_ID` = your client ID

**Redeploy after setting them** – Vite bakes them in at build time; editing them doesn't change an existing build.

## 8. Final test checklist

1. Open the Vercel site → "Sign in with Google" button visible → sign in → dashboard loads (no CORS errors in browser console).
2. Live page → video loops → **Start auto-verify**.
3. Registered plate → green GRANTED; unregistered → red + alert on Alerts page; unreadable → manual review.
4. Same car staying in frame doesn't create repeat logs for 45 s.
5. Dashboard / logs update.

Before presenting: open the Render URL a minute early (free/low tiers may sleep and cold-start), confirm Aiven is running.

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Browser: "blocked by CORS policy" | `CORS_ORIGINS` on Render must equal the Vercel URL exactly; redeploy Render |
| "Could not reach the Campus Guardian server" | `VITE_API_URL` missing/wrong on Vercel, or you didn't redeploy; Render asleep |
| Google button missing | `VITE_GOOGLE_CLIENT_ID` not set at build time |
| Google popup error `origin_mismatch` | Vercel URL not in Authorized JavaScript origins (exact match) |
| Google: "access blocked / app not verified" | add your Gmail under OAuth consent → Test users |
| "This Google account is not authorised" (403) | email not in `users`; use `GOOGLE_AUTO_CREATE=true` temporarily |
| 503 "Google sign-in is not configured" | `GOOGLE_CLIENT_ID` missing on Render |
| Render crashes/restarts at start | out of memory → bigger instance |
| `Can't connect to MySQL` / SSL error | URL scheme `mysql+pymysql://`, remove `?ssl-mode=…`, CA path correct, Aiven allows your IP |
| Logins fail with "Invalid email or password" on cloud | seed wasn't run against Aiven (step 4.5) |
| Plate read but "not registered" | plate not in Vehicles; check OCR text in the log; lower `PLATE_FUZZY_THRESHOLD` slightly |
| "Demo video not found" | `frontend/public/demo.mp4` missing from the repo |

## 10. Before sharing the link / resume

Change the seeded demo passwords (`Admin@123`, `Guard@123`) or remove those users, keep `.env` out of Git, never commit the Aiven password, and rotate anything that was ever pasted into a public place.
