from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, EntryLog, Student, User, Vehicle
from ..schemas import AlertResponse, EntryResponse
from ..security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today_start = datetime.combine(datetime.utcnow().date(), time.min)

    total_students = db.query(Student).filter(Student.status == "active").count()
    total_vehicles = db.query(Vehicle).filter(Vehicle.status == "active").count()

    todays_entries = db.query(EntryLog).filter(EntryLog.entry_time >= today_start)
    today_total = todays_entries.count()
    granted = todays_entries.filter(EntryLog.status == "granted").count()
    denied = todays_entries.filter(EntryLog.status == "denied").count()
    manual_review = todays_entries.filter(EntryLog.status.in_(["uncertain", "manual"])).count()

    open_alerts = db.query(Alert).filter(Alert.status == "open").count()

    return {
        "total_students": total_students,
        "total_vehicles": total_vehicles,
        "todays_entries": today_total,
        "successful_entries": granted,
        "denied_entries": denied,
        "pending_manual_reviews": manual_review,
        "open_alerts": open_alerts,
    }


@router.get("/recent-activity", response_model=list[EntryResponse])
def recent_activity(limit: int = 10, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(EntryLog).order_by(EntryLog.entry_time.desc()).limit(min(limit, 50)).all()


@router.get("/recent-alerts", response_model=list[AlertResponse])
def recent_alerts(limit: int = 10, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Alert).order_by(Alert.created_at.desc()).limit(min(limit, 50)).all()
