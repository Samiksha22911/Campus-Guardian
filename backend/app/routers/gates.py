from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Gate, User
from ..security import get_current_user

router = APIRouter(prefix="/api/gates", tags=["Gates"])


@router.get("")
def list_gates(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    gates = db.query(Gate).order_by(Gate.id).all()
    return [{"id": g.id, "name": g.name, "location": g.location, "camera_id": g.camera_id} for g in gates]
