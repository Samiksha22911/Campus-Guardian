import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine

from .routers import (
    alerts,
    analytics,
    audit,
    auth,
    dashboard,
    entries,
    gates,
    reports,
    student_portal,
    students,
    users,
    vehicles,
    verification,
)

# Import models so SQLAlchemy knows about all tables.
from . import models  # noqa: F401

logger = logging.getLogger("campus_guardian")

# =========================================================
# CREATE DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Campus Guardian API",
    description=(
        "Backend API for the AI-powered Campus Guardian smart campus "
        "entry verification system (vehicle + face verification)."
    ),
    version="1.0.0",
)

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# STATIC FILES (uploaded student photos / vehicle photos / entry frames)
# =========================================================

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# =========================================================
# GLOBAL ERROR HANDLING
# Never leak internal exception details to the client.
# =========================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again."},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request data.", "errors": exc.errors()},
    )


# =========================================================
# ROUTERS
# =========================================================

app.include_router(auth.router)
app.include_router(student_portal.router)
app.include_router(students.router)
app.include_router(vehicles.router)
app.include_router(verification.router)
app.include_router(entries.router)
app.include_router(gates.router)
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(users.router)
app.include_router(audit.router)


# =========================================================
# MODEL WARM-UP (real AI only) - load YOLO + EasyOCR in the background at boot
# so the first request is not slow enough to hit a gateway timeout.
# =========================================================

@app.on_event("startup")
def _warm_models():
    if settings.MOCK_AI:
        return

    import threading

    def _load():
        try:
            from .ai.ocr_service import _get_reader
            from .ai.plate_detector import _load_model

            _load_model()
            _get_reader()
            logger.info("AI models warmed up")
        except Exception:
            logger.exception("AI model warm-up failed")

    threading.Thread(target=_load, daemon=True).start()


# =========================================================
# BASIC ROUTES
# =========================================================

@app.get("/")
def root():
    return {"message": "Campus Guardian API is running", "mock_ai": settings.MOCK_AI}


@app.get("/health")
def health():
    return {"status": "healthy"}
