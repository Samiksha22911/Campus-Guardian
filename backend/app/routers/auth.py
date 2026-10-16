from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..config import settings
from ..schemas import GoogleLoginRequest, LoginRequest, LoginResponse, UserResponse
from ..security import create_access_token, get_current_user, hash_password, verify_password
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


@router.post("/google", response_model=LoginResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Sign in with a Google ID token.

    The browser gets the token from Google Identity Services; we verify its
    signature, audience (our client id) and expiry with Google's public keys,
    then map the verified email to a row in the users table and issue our own
    JWT - so every other endpoint keeps working unchanged.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on the server")

    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token

        info = id_token.verify_oauth2_token(
            data.credential, g_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google sign-in token")

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        if not settings.GOOGLE_AUTO_CREATE:
            raise HTTPException(
                status_code=403,
                detail="This Google account is not authorised. Ask an admin to add your email.",
            )
        import secrets

        user = User(
            name=info.get("name") or email.split("@")[0],
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),  # never used
            role="admin" if email in settings.GOOGLE_ADMIN_EMAILS else "security_officer",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    token = create_access_token({"sub": str(user.id), "role": user.role, "type": "user"})

    write_audit_log(
        db,
        user_id=user.id,
        action="LOGIN",
        entity_type="user",
        entity_id=user.id,
        description=f"{user.email} signed in with Google",
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
