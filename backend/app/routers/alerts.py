from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, User
from ..schemas import AlertResponse, AlertStatusUpdate
from ..security import get_current_user, require_roles
from ..utils import write_audit_log

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
def get_alerts(
    status_filter: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Alert)

    if status_filter:
        query = query.filter(Alert.status == status_filter)
    if severity:
        query = query.filter(Alert.severity == severity)

    return query.order_by(Alert.created_at.desc()).limit(200).all()


@router.patch("/{alert_id}/status", response_model=AlertResponse)
def update_alert_status(
    alert_id: int,
    data: AlertStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    allowed = ["open", "acknowledged", "resolved"]

    if data.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid alert status")

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = data.status

    if data.status == "resolved":
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = user.id
    else:
        alert.resolved_at = None
        alert.resolved_by = None

    db.commit()
    db.refresh(alert)

    write_audit_log(
        db,
        user_id=user.id,
        action="ALERT_STATUS",
        entity_type="alert",
        entity_id=alert.id,
        description=f"Alert #{alert.id} set to {data.status}",
    )

    return alert
