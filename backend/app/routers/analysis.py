"""Upload ANY video -> run the real pipeline -> results in the common format.

Only registered when DEMO_MODE=false (see main.py), so this file - and the
heavy ai-service imports inside _run_job - never load on the hosted demo.
"""

import json
import os
import sys
import threading
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, get_db
from ..demo_support import lookup_plate, persist_events
from ..models import User
from ..security import require_roles

router = APIRouter(prefix="/api/analysis", tags=["Video analysis (local mode)"])

JOBS: dict[str, dict] = {}
ALLOWED_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def _dirs():
    vid = os.path.join(settings.UPLOAD_DIR, "videos")
    res = os.path.join(settings.UPLOAD_DIR, "results")
    os.makedirs(vid, exist_ok=True)
    os.makedirs(res, exist_ok=True)
    return vid, res


def _run_job(job_id: str, video_path: str, filename: str, operator_id: int):
    job = JOBS[job_id]
    db = SessionLocal()
    try:
        job["status"] = "running"
        if settings.AI_SERVICE_DIR not in sys.path:
            sys.path.insert(0, settings.AI_SERVICE_DIR)
        from analyze_video import analyze_video  # heavy import happens HERE, not at startup

        def lookup(text, conf):
            info, _ = lookup_plate(db, text, conf)
            return info

        results = analyze_video(
            video_path,
            weights_path=settings.PLATE_MODEL_PATH,
            lookup=lookup,
            plate_conf=settings.PLATE_DETECTOR_CONF,
            device=settings.AI_DEVICE,
            progress=lambda p: job.update(progress=round(p, 3)),
            source_name=filename,
        )
        results["video"]["src"] = f"/uploads/videos/{job_id}.mp4"
        _, res_dir = _dirs()
        with open(os.path.join(res_dir, f"{job_id}.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        persist_events(db, results["events"], operator_id)
        job.update(status="done", progress=1.0, results=results)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI
        job.update(status="error", message=f"{type(exc).__name__}: {exc}")
    finally:
        db.close()


@router.post("/upload")
def upload_video(
    video: UploadFile = File(...),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    ext = os.path.splitext(video.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported video type '{ext}'. Use one of: {', '.join(sorted(ALLOWED_EXT))}")
    vid_dir, _ = _dirs()
    job_id = uuid.uuid4().hex[:12]
    path = os.path.join(vid_dir, f"{job_id}.mp4" if ext == ".mp4" else f"{job_id}{ext}")
    limit = settings.MAX_VIDEO_MB * 1024 * 1024
    size = 0
    with open(path, "wb") as out:
        while chunk := video.file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                out.close()
                os.remove(path)
                raise HTTPException(413, f"Video larger than {settings.MAX_VIDEO_MB} MB.")
            out.write(chunk)
    JOBS[job_id] = {"status": "queued", "progress": 0.0, "message": None, "results": None}
    threading.Thread(target=_run_job, args=(job_id, path, video.filename or path, user.id), daemon=True).start()
    return {"job_id": job_id}


@router.get("/{job_id}")
def job_status(job_id: str, _: User = Depends(require_roles("admin", "security_officer"))):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job (the server may have restarted).")
    return job
