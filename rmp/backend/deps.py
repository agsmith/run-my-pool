from datetime import datetime, timezone
import hashlib
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from jwt import InvalidTokenError
from database import SessionLocal
import models
import os
from auth_session import PERSISTENT_SESSION_TTL

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    rmp_access_token: str | None = Cookie(default=None),
    rmp_persistent_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db)
):
    """Authenticate with a short-lived JWT or a revocable persistent session."""
    bearer = credentials.credentials if credentials else None
    bearer_is_cookie_marker = bearer in (None, "", "cookie", "null", "undefined")
    token = rmp_access_token if bearer_is_cookie_marker else bearer
    try:
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email and payload.get("type") == "access":
                user = db.query(models.User).filter(models.User.email == email).first()
                if user and user.is_active:
                    return user
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is unavailable",
                )
            if not bearer_is_cookie_marker:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
    except InvalidTokenError:
        if not bearer_is_cookie_marker:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

    if rmp_persistent_session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        digest = hashlib.sha256(rmp_persistent_session.encode("utf-8")).hexdigest()
        session = db.query(models.PersistentSession).filter(
            models.PersistentSession.token_digest == digest,
            models.PersistentSession.revoked_at.is_(None),
            models.PersistentSession.expires_at > now,
        ).first()
        if session:
            user = db.query(models.User).filter(models.User.id == session.user_id).first()
            if user and user.is_active:
                session.last_used_at = now
                session.expires_at = now + PERSISTENT_SESSION_TTL
                db.commit()
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )
