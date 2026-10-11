from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, User
from ..schemas import AuditLogResponse
from ..security import require_roles

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
