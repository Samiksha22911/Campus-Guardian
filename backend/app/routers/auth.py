from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, LoginResponse, UserResponse
from ..security import create_access_token, get_current_user, verify_password
from ..utils import write_audit_log

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()

    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role, "type": "user"})

    write_audit_log(
        db,
        user_id=user.id,
        action="LOGIN",
        entity_type="user",
        entity_id=user.id,
        description=f"{user.email} signed in",
    )

    return {"user": user, "access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # JWTs are stateless, so "logout" is enforced client-side by discarding
    # the token. We still record it for the audit trail.
    write_audit_log(
        db,
        user_id=user.id,
        action="LOGOUT",
        entity_type="user",
        entity_id=user.id,
        description=f"{user.email} signed out",
    )
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
