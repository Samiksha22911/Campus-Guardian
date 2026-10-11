from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, EntryLog, User
from ..schemas import EntryResponse, ManualDecisionRequest
from ..security import get_current_user, require_roles
from ..utils import write_audit_log

router = APIRouter(prefix="/api/entries", tags=["Entry Logs"])


@router.get("", response_model=list[EntryResponse])
def get_entries(
    status_filter: str | None = None,
    gate_id: int | None = None,
    vehicle_plate: str | None = None,
    student_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(EntryLog)

    if status_filter:
        query = query.filter(EntryLog.status == status_filter)
    if gate_id:
        query = query.filter(EntryLog.gate_id == gate_id)
    if vehicle_plate:
        query = query.filter(EntryLog.detected_plate.ilike(f"%{vehicle_plate}%"))
    if student_id:
        query = query.filter(EntryLog.student_id == student_id)

    return query.order_by(EntryLog.entry_time.desc()).limit(500).all()


@router.get("/recent", response_model=list[EntryResponse])
def get_recent_entries(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(EntryLog).order_by(EntryLog.entry_time.desc()).limit(20).all()


@router.post("/{entry_id}/manual-decision", response_model=EntryResponse)
def manual_decision(
    entry_id: int,
    data: ManualDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    if data.status not in ("granted", "denied"):
        raise HTTPException(status_code=400, detail="Status must be 'granted' or 'denied'")

    if not data.reason.strip():
        raise HTTPException(status_code=400, detail="A reason is required for a manual override")

    entry = db.query(EntryLog).filter(EntryLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.status = "manual"
    entry.verification_status = "GRANTED" if data.status == "granted" else "DENIED"
    entry.decision_source = "manual"
    entry.rejection_reason = f"{data.status.upper()}: {data.reason.strip()}"
    entry.operator_id = user.id

    # Any open alert tied to this entry is auto-resolved by the override.
    db.query(Alert).filter(Alert.entry_id == entry.id, Alert.status == "open").update(
        {"status": "resolved", "resolved_at": datetime.utcnow(), "resolved_by": user.id}
    )

    db.commit()
    db.refresh(entry)

    write_audit_log(
        db,
        user_id=user.id,
        action="MANUAL_DECISION",
        entity_type="entry_log",
        entity_id=entry.id,
        description=f"Manual {data.status} — {data.reason.strip()}",
    )

    return entry
