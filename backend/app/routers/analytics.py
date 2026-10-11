from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EntryLog, User
from ..security import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("")
def get_analytics(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    entries = db.query(EntryLog).all()

    hourly = [{"hour": f"{hour:02d}:00", "entries": 0, "denied": 0} for hour in range(24)]
    by_gate = defaultdict(int)

    outcomes = {"granted": 0, "manual": 0, "uncertain": 0, "denied": 0}

    total_ocr = 0.0
    total_face = 0.0
    face_checks = 0

    for entry in entries:
        hour = entry.entry_time.hour
        hourly[hour]["entries"] += 1

        if entry.status == "denied":
            hourly[hour]["denied"] += 1

        by_gate[str(entry.gate_id)] += 1

        if entry.status in outcomes:
            outcomes[entry.status] += 1

        total_ocr += entry.plate_confidence
        if entry.face_match != "not_performed":
            total_face += entry.face_confidence
            face_checks += 1

    total = len(entries)
    peak = max(hourly, key=lambda item: item["entries"])

    return {
        "total_entries": total,
        "grant_rate": (outcomes["granted"] / total * 100) if total else 0,
        "avg_ocr_confidence": (total_ocr / total * 100) if total else 0,
        "avg_face_confidence": (total_face / face_checks * 100) if face_checks else 0,
        "peak_hour": peak["hour"],
        "hourly": hourly,
        "by_gate": [{"gate": gate, "count": count} for gate, count in by_gate.items()],
        "outcomes": [
            {"name": "Granted", "value": outcomes["granted"]},
            {"name": "Manual", "value": outcomes["manual"]},
            {"name": "Uncertain", "value": outcomes["uncertain"]},
            {"name": "Denied", "value": outcomes["denied"]},
        ],
    }
