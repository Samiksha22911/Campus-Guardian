from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserResponse, UserSelfUpdate
from ..security import get_current_user, hash_password, require_roles, verify_password
from ..utils import write_audit_log

router = APIRouter(prefix="/api/users", tags=["Users"])

ROLES = {"admin", "security_officer"}


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/me", response_model=UserResponse)
def update_own_profile(
    data: UserSelfUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lets ANY logged-in user (guard or admin) update their own name and/or
    password. Available to every role - unlike /api/users which is
    admin-only for managing other people's accounts."""

    if data.name:
        user.name = data.name

    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.password_hash = hash_password(data.new_password)

    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        user_id=user.id,
        action="UPDATE",
        entity_type="user",
        entity_id=user.id,
        description="Updated own profile",
    )

    return user


@router.post("", response_model=UserResponse)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles("admin")),
):
    if data.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(ROLES)}")

    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    user = User(
        name=data.name,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        role=data.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        user_id=admin_user.id,
        action="CREATE",
        entity_type="user",
        entity_id=user.id,
        description=f"Created {user.role} account for {user.email}",
    )

    return user


@router.patch("/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()

    write_audit_log(
        db,
        user_id=admin_user.id,
        action="DEACTIVATE",
        entity_type="user",
        entity_id=user.id,
        description=f"Deactivated account {user.email}",
    )

    return {"message": "User deactivated"}
