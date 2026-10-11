import difflib
import os
import re
import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .config import settings
from .models import AuditLog


def normalize_plate(raw: str) -> str:
    """Normalize a registration number for comparison / storage.

    'MP 07 AB 1234' and 'mp07ab1234' both become 'MP07AB1234' so lookups
    and the unique constraint treat them as the same vehicle.
    """
    if not raw:
        return ""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def fuzzy_match_plate(
    plate: str, known_plates: list[str], threshold: float = 0.82
) -> tuple[str | None, float]:
    """Finds the closest registered plate to a normalized OCR reading.

    OCR on plates is rarely character-perfect (O/0, I/1, S/5, B/8 mix-ups
    are the common ones - see project notes, section 10). Rather than
    immediately treating any non-exact reading as an unknown vehicle, this
    lets the verification router fall back to the closest registered plate
    when it's similar enough.

    Returns (best_plate_or_None, best_similarity_score). best_plate is None
    if no candidate clears `threshold`, even if one was closest.
    """
    best_plate, best_ratio = None, 0.0
    for candidate in known_plates:
        ratio = difflib.SequenceMatcher(None, plate, candidate).ratio()
        if ratio > best_ratio:
            best_plate, best_ratio = candidate, ratio

    if best_plate and best_ratio >= threshold:
        return best_plate, best_ratio
    return None, best_ratio


def write_audit_log(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    description: str | None = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        description=description,
    )
    db.add(log)
    db.commit()


def save_upload(file: UploadFile, subfolder: str, contents: bytes | None = None) -> str:
    """Validate and persist an uploaded image, returning a public URL path."""

    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Allowed: JPEG, PNG, WEBP.",
        )

    data = contents if contents is not None else file.file.read()

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image exceeds the {settings.MAX_UPLOAD_MB}MB upload limit.",
        )

    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[file.content_type]

    target_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(target_dir, filename)

    with open(full_path, "wb") as out:
        out.write(data)

    return f"/uploads/{subfolder}/{filename}"
