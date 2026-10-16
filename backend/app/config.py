import os

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    # "development" (default) or "production". Production turns on stricter
    # startup checks (see the bottom of this file).
    APP_ENV: str = os.getenv("APP_ENV", "development").strip().lower()

    # Database
    # Defaults to a local SQLite file so the project runs with zero setup
    # (no MySQL server, no password to configure). Set DATABASE_URL in .env
    # to something like mysql+pymysql://root:PASSWORD@localhost:3306/campus_gate_ai
    # if you specifically want MySQL instead.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./campus_gate_ai.db",
    )

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-secret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )

    # CORS - comma separated list of allowed origins
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        ).split(",")
        if origin.strip()
    ]

    # AI pipeline
    # When true (default) the AI pipeline uses deterministic/mock logic so the
    # rest of the application can be built and tested before the real
    # YOLO / OCR / OpenCV / face-verification models are wired in.
    MOCK_AI: bool = _bool(os.getenv("MOCK_AI"), True)

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "8"))
    ALLOWED_IMAGE_TYPES: set[str] = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    # Verification decision thresholds (can be tuned without code changes)
    MIN_PLATE_CONFIDENCE: float = float(os.getenv("MIN_PLATE_CONFIDENCE", "0.55"))
    MIN_FACE_CONFIDENCE: float = float(os.getenv("MIN_FACE_CONFIDENCE", "0.60"))
    REQUIRE_FACE_VERIFICATION: bool = _bool(
        os.getenv("REQUIRE_FACE_VERIFICATION"), False
    )

    # Plate OCR readings rarely come back character-perfect (O/0, I/1, S/5,
    # B/8 mix-ups are common). When the exact-normalized plate isn't found,
    # optionally fall back to the closest registered plate if it's similar
    # enough, rather than immediately flagging an unknown vehicle.
    PLATE_FUZZY_MATCHING: bool = _bool(os.getenv("PLATE_FUZZY_MATCHING"), True)
    PLATE_FUZZY_THRESHOLD: float = float(os.getenv("PLATE_FUZZY_THRESHOLD", "0.82"))

    # ------------------------------------------------------------
    # Real AI model configuration (only used once MOCK_AI=false)
    # ------------------------------------------------------------
    # Paths are relative to the backend/ working directory (i.e. where you
    # run `python run.py` from). Train these with the scripts in the
    # project-root ai/ folder (train_plate_yolo.py, train_face_yolo.py) and
    # copy the resulting best.pt files here.
    PLATE_MODEL_PATH: str = os.getenv("PLATE_MODEL_PATH", "app/ai/weights/plate_best.pt")
    FACE_MODEL_PATH: str = os.getenv("FACE_MODEL_PATH", "app/ai/weights/face_best.pt")

    # "cpu" or a CUDA device index as a string, e.g. "0"
    AI_DEVICE: str = os.getenv("AI_DEVICE", "cpu")

    PLATE_DETECTOR_CONF: float = float(os.getenv("PLATE_DETECTOR_CONF", "0.4"))
    FACE_DETECTOR_CONF: float = float(os.getenv("FACE_DETECTOR_CONF", "0.5"))

    OCR_LANGUAGES: list[str] = [
        lang.strip()
        for lang in os.getenv("OCR_LANGUAGES", "en").split(",")
        if lang.strip()
    ]


    # ------------------------------------------------------------
    # Cloud database (Aiven MySQL requires SSL)
    # ------------------------------------------------------------
    # Path to the CA certificate downloaded from the Aiven console
    # (e.g. certs/aiven-ca.pem). Empty = encrypted but unverified connection.
    DB_SSL_CA: str = os.getenv("DB_SSL_CA", "").strip()

    # ------------------------------------------------------------
    # Google sign-in (Google Identity Services / OpenID Connect ID token)
    # ------------------------------------------------------------
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    # false (default): only emails that already exist in the users table can
    # sign in with Google. true: unknown Google accounts are auto-created as
    # security_officer (handy for a demo, risky for production).
    GOOGLE_AUTO_CREATE: bool = _bool(os.getenv("GOOGLE_AUTO_CREATE"), False)
    # Comma separated emails that become admin when auto-created.
    GOOGLE_ADMIN_EMAILS: list[str] = [
        e.strip().lower()
        for e in os.getenv("GOOGLE_ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]

    # ------------------------------------------------------------
    # Looping demo video: ignore the same plate at the same gate for N
    # seconds so one car does not create dozens of entry logs / alerts.
    # ------------------------------------------------------------
    DEDUPE_WINDOW_SECONDS: int = int(os.getenv("DEDUPE_WINDOW_SECONDS", "45"))


settings = Settings()


# ----------------------------------------------------------------------
# Refuse to boot a production server with a guessable JWT secret - anyone who
# knows the secret can forge a valid admin token.
# ----------------------------------------------------------------------
_WEAK_SECRETS = {
    "",
    "change-this-secret",
    "change-this-secret-in-production",
    "campus-gate-ai-secret-change-this-later",
}

if settings.APP_ENV == "production" and (
    settings.JWT_SECRET in _WEAK_SECRETS or len(settings.JWT_SECRET) < 32
):
    raise RuntimeError(
        "APP_ENV=production but JWT_SECRET is missing, default, or shorter than "
        "32 characters. Generate one with: "
        'python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
