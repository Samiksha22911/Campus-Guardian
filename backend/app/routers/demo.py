"""Mode-independent endpoints: /api/config and /api/demo/results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..demo_support import enrich_with_db, load_demo_results
from ..models import User
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["Demo"])


@router.get("/config")
def public_config():
    """Public. The frontend reads this to decide which UI to show."""
    return {"demo_mode": settings.DEMO_MODE, "upload_enabled": not settings.DEMO_MODE}


@router.get("/demo/results")
def demo_results(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Precomputed events (demo-data/results.json) + a LIVE database check per plate."""
    results = load_demo_results()
    if results is None:
        raise HTTPException(
            status_code=404,
            detail="demo-data/results.json not found. Run ai-service/analyze_video.py locally and commit the result.",
        )
    return enrich_with_db(results, db)
