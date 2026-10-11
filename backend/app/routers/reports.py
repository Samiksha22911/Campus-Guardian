import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EntryLog, User
from ..security import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Reports"])


def _apply_date_range(query, date_from: str | None, date_to: str | None):
    if date_from:
        query = query.filter(EntryLog.entry_time >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(EntryLog.entry_time <= datetime.fromisoformat(date_to))
    return query


@router.get("/statistics")
def get_statistics(
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = _apply_date_range(db.query(EntryLog), date_from, date_to)
    entries = query.all()

    total = len(entries)
    granted = sum(1 for e in entries if e.status == "granted")
    denied = sum(1 for e in entries if e.status == "denied")
    unknown_vehicle = sum(1 for e in entries if e.verification_status == "UNKNOWN_VEHICLE")
    face_mismatch = sum(1 for e in entries if e.verification_status == "FACE_MISMATCH")

    by_day: dict[str, int] = {}
    for e in entries:
        key = e.entry_time.strftime("%Y-%m-%d")
        by_day[key] = by_day.get(key, 0) + 1

    return {
        "total_entries": total,
        "successful_entries": granted,
        "denied_entries": denied,
        "unknown_vehicles": unknown_vehicle,
        "face_mismatches": face_mismatch,
        "daily_trend": [{"date": d, "count": c} for d, c in sorted(by_day.items())],
    }


@router.get("/entries")
def report_entries(
    date_from: str | None = None,
    date_to: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = _apply_date_range(db.query(EntryLog), date_from, date_to)
    entries = query.order_by(EntryLog.entry_time.desc()).all()

    if format == "json":
        return [
            {
                "id": e.id,
                "entry_time": e.entry_time.isoformat(),
                "plate": e.detected_plate,
                "vehicle_type": e.detected_vehicle_type,
                "student_id": e.student_id,
                "status": e.status,
                "verification_status": e.verification_status,
                "plate_confidence": e.plate_confidence,
                "face_confidence": e.face_confidence,
                "reason": e.rejection_reason,
            }
            for e in entries
        ]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["id", "entry_time", "plate", "vehicle_type", "student_id", "status", "verification_status",
         "plate_confidence", "face_confidence", "reason"]
    )
    for e in entries:
        writer.writerow(
            [e.id, e.entry_time.isoformat(), e.detected_plate, e.detected_vehicle_type, e.student_id,
             e.status, e.verification_status, e.plate_confidence, e.face_confidence, e.rejection_reason]
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=entry-logs.csv"},
    )
