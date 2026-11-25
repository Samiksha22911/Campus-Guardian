"""Shared helpers for the common results format (see demo-data/results.schema.json).

Light on purpose: only stdlib + SQLAlchemy. Used by BOTH modes:
  * DEMO_MODE=true : load demo-data/results.json and re-check each plate against
                     the real database, so the "database status" column is live.
  * DEMO_MODE=false: ai-service/analyze_video.py calls lookup_plate() to fill
                     db_status / decision while it analyses an uploaded video.
"""

import json
import os
from datetime import datetime

from sqlalchemy.orm import Session

from .config import settings
from .models import Alert, EntryLog, Gate, Vehicle
from .utils import fuzzy_match_plate, normalize_plate

SCHEMA_VERSION = "1.0"

# db_status -> (decision, EntryLog.status, EntryLog.verification_status)
_STATUS_MAP = {
    "REGISTERED": ("ALLOWED", "granted", "GRANTED"),
    "UNREGISTERED": ("DENIED", "denied", "UNKNOWN_VEHICLE"),
    "BLOCKLISTED": ("DENIED", "denied", "BLOCKLISTED"),
    "INACTIVE": ("DENIED", "denied", "UNKNOWN_VEHICLE"),
    "PENDING": ("DENIED", "denied", "UNKNOWN_VEHICLE"),
    "LOW_CONFIDENCE": ("REVIEW", "uncertain", "MANUAL_REVIEW"),
    "NO_PLATE": ("REVIEW", "uncertain", "MANUAL_REVIEW"),
}


def lookup_plate(db: Session, plate_text: str | None, confidence: float):
    """Database check for one plate reading -> (info_dict, Vehicle | None).

    Same rules as the per-frame /api/verification/process endpoint: exact match
    first, then fuzzy match (OCR O/0, I/1 mix-ups), blocklist overrides all.
    """
    plate = normalize_plate(plate_text or "")
    if not plate:
        return {"db_status": "NO_PLATE", "decision": "REVIEW", "owner_name": None, "matched_plate": None}, None
    if confidence < settings.MIN_PLATE_CONFIDENCE:
        return {"db_status": "LOW_CONFIDENCE", "decision": "REVIEW", "owner_name": None, "matched_plate": None}, None

    vehicle = db.query(Vehicle).filter(Vehicle.registration_number == plate).first()
    if not vehicle and settings.PLATE_FUZZY_MATCHING:
        known = [v.registration_number for v in db.query(Vehicle.registration_number).all()]
        best, _ = fuzzy_match_plate(plate, known, threshold=settings.PLATE_FUZZY_THRESHOLD)
        if best:
            vehicle = db.query(Vehicle).filter(Vehicle.registration_number == best).first()

    if not vehicle:
        status = "UNREGISTERED"
    elif vehicle.is_blocklisted:
        status = "BLOCKLISTED"
    elif vehicle.status == "pending":
        status = "PENDING"
    elif vehicle.status != "active":
        status = "INACTIVE"
    else:
        status = "REGISTERED"

    info = {
        "db_status": status,
        "decision": _STATUS_MAP[status][0],
        "owner_name": vehicle.student.name if vehicle and vehicle.student else None,
        "matched_plate": vehicle.registration_number if vehicle else None,
    }
    return info, vehicle


# ---------------------------------------------------------------- demo mode

def load_demo_results() -> dict | None:
    """demo-data/results.json (real pipeline output). Falls back to
    results.sample.json - a FORMAT EXAMPLE whose meta.generated_by is "sample",
    which makes the UI show a different banner so it is never passed off as
    real pipeline output."""
    for name in ("results.json", "results.sample.json"):
        path = os.path.join(settings.DEMO_DATA_DIR, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return None


def enrich_with_db(results: dict, db: Session) -> dict:
    """Re-run the database check for every event against the LIVE database."""
    for ev in results.get("events", []):
        ev["precomputed_db_status"] = ev.get("db_status")
        ev["precomputed_decision"] = ev.get("decision")
        info, _ = lookup_plate(db, ev.get("plate_text"), float(ev.get("plate_confidence") or 0))
        ev["db_status"] = info["db_status"]
        ev["decision"] = info["decision"]
        ev["owner_name"] = info["owner_name"]
    results.setdefault("meta", {})["db_status_source"] = "live-database"
    return results


# --------------------------------------------------------------- local mode

def persist_events(db: Session, events: list[dict], operator_id: int | None) -> int:
    """Write analysed events into entry_logs (+ alerts) so the normal dashboard,
    logs and alerts pages show them. Local mode only."""
    gate = db.query(Gate).order_by(Gate.id).first()
    if not gate:
        return 0
    n = 0
    for ev in events:
        decision, status, vstatus = _STATUS_MAP.get(ev["db_status"], _STATUS_MAP["NO_PLATE"])
        info, vehicle = lookup_plate(db, ev.get("plate_text"), float(ev.get("plate_confidence") or 0))
        reason = None if decision == "ALLOWED" else f"{ev['db_status']} - plate {ev.get('plate_text') or 'unreadable'}"
        entry = EntryLog(
            detected_plate=ev.get("plate_text"),
            detected_vehicle_type=vehicle.vehicle_type if vehicle else None,
            vehicle_id=vehicle.id if vehicle else None,
            student_id=vehicle.owner_student_id if vehicle else None,
            gate_id=gate.id,
            plate_confidence=float(ev.get("plate_confidence") or 0),
            face_confidence=float(ev.get("face_score") or 0),
            plate_match=vehicle is not None,
            face_match="not_performed" if ev.get("face_score") is None else ("match" if ev.get("face_match_name") else "mismatch"),
            status=status,
            verification_status=vstatus,
            rejection_reason=reason,
            decision_source="ai",
            entry_time=datetime.utcnow(),
            operator_id=operator_id,
        )
        db.add(entry)
        db.flush()
        if vstatus != "GRANTED":
            sev = "critical" if vstatus == "BLOCKLISTED" else ("high" if vstatus == "UNKNOWN_VEHICLE" else "medium")
            db.add(Alert(entry_id=entry.id, type=vstatus.replace("_", " ").title(), severity=sev, detail=reason or vstatus))
        n += 1
    db.commit()
    return n
