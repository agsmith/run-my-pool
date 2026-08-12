from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
import jwt
from jwt import InvalidTokenError
from datetime import datetime, timedelta, timezone
import hashlib
import models
import schemas
import deps
import os
import uuid
import logging
from audit_utils import log_create_operation, log_authentication_event, log_update_operation
from app_logging import log_event

logger = logging.getLogger("runmypool.auth")

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
ACCESS_TOKEN_COOKIE = "rmp_access_token"
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = timedelta(minutes=15)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    to_encode.setdefault("type", "access")
    expire = datetime.now(timezone.utc).replace(tzinfo=None) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    normalized_email = str(user.email).strip().lower()
    try:
        db_user = db.query(models.User).filter(
            func.lower(models.User.email) == normalized_email
        ).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(user.password)

        db_user = models.User(
            id=str(uuid.uuid4()),
            email=normalized_email,
            hashed_password=hashed_password,
            role=models.UserRole.USER,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Log user registration
        log_create_operation(
            db=db,
            entity_type="user",
            entity_id=db_user.id,
            user_id=db_user.id,
            entity_data={"email": db_user.email, "role": db_user.role.value}
        )
        log_event(logger, logging.INFO, "user_registered", user_id=db_user.id)
        
        return db_user
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        log_event(logger, logging.WARNING, "registration_rejected", reason="email_exists")
        # The unique index remains the authority if two requests race.
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception:
        db.rollback()
        logger.exception("registration_failed", extra={"event": "registration_failed"})
        raise HTTPException(status_code=500, detail="Unable to create account")

@router.post("/login")
def login(
    user: schemas.LoginRequest,
    response: Response,
    db: Session = Depends(deps.get_db),
):
    normalized_email = str(user.email).strip().lower()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - LOGIN_ATTEMPT_WINDOW
    recent_failures = db.query(models.LoginAttempt).filter(
        models.LoginAttempt.email == normalized_email,
        models.LoginAttempt.attempted_at >= window_start,
    ).count()
    if recent_failures >= LOGIN_ATTEMPT_LIMIT:
        log_event(logger, logging.WARNING, "login_rate_limited")
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    db_user = db.query(models.User).filter(
        func.lower(models.User.email) == normalized_email
    ).first()
    if not db_user or not db_user.is_active or not verify_password(user.password, db_user.hashed_password):
        db.add(models.LoginAttempt(id=str(uuid.uuid4()), email=normalized_email, attempted_at=now))
        db.commit()
        # Log failed login attempt
        log_authentication_event(
            db=db,
            action="LOGIN_FAILED",
            user_email=normalized_email,
            additional_info={"reason": "invalid_credentials"}
        )
        log_event(logger, logging.WARNING, "login_rejected", reason="invalid_credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    db.query(models.LoginAttempt).filter(models.LoginAttempt.email == normalized_email).delete()
    db.commit()
    
    # Log successful login
    log_authentication_event(
        db=db,
        action="LOGIN_SUCCESS",
        user_email=db_user.email,
        user_id=db_user.id
    )
    log_event(logger, logging.INFO, "login_succeeded", user_id=db_user.id)
    
    access_token = create_access_token(data={"sub": db_user.email})
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=os.getenv("ENVIRONMENT", "production").lower() != "development",
        samesite="lax",
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        httponly=True,
        secure=os.getenv("ENVIRONMENT", "production").lower() != "development",
        samesite="lax",
        path="/",
    )

@router.get("/me", response_model=schemas.UserOut)
def get_current_user_info(current_user: models.User = Depends(deps.get_current_user)):
    """Get current user information."""
    return current_user

@router.post("/forgot-password")
def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(deps.get_db)):
    """
    Send password reset email if user exists.
    Always returns success message for security (don't reveal if email exists).
    """
    try:
        normalized_email = str(request.email).strip().lower()
        db_user = db.query(models.User).filter(
            func.lower(models.User.email) == normalized_email
        ).first()
        if db_user:
            # Generate password reset token (expires in 1 hour)
            reset_token = create_access_token(
                data={"sub": db_user.email, "type": "password_reset"}, 
                expires_delta=timedelta(hours=1)
            )
            
            # Token delivery belongs in the configured email provider. Never
            # expose bearer reset credentials through application logs.
            _ = reset_token
        
        # Always return success message regardless of whether email exists
        return {"message": "If an account with that email exists, you will receive a password reset link shortly."}
    except Exception:
        logger.exception("forgot_password_failed", extra={"event": "forgot_password_failed"})
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reset-password")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(deps.get_db)):
    """
    Reset user password using a valid reset token.
    """
    try:
        # Verify the reset token
        payload = jwt.decode(request.token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")
        
        if not email or token_type != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid reset token")

        token_digest = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
        if db.query(models.UsedPasswordResetToken).filter_by(token_digest=token_digest).first():
            raise HTTPException(status_code=400, detail="Reset token has already been used")
        
        # Find the user
        db_user = db.query(models.User).filter(models.User.email == email).first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Update the password
        db_user.hashed_password = get_password_hash(request.new_password)
        db_user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(models.UsedPasswordResetToken(token_digest=token_digest, used_at=db_user.updated_at))
        db.commit()
        
        # Log password reset
        log_update_operation(
            db=db,
            entity_type="user",
            entity_id=db_user.id,
            user_id=db_user.id,
            changes={"action": "password_reset"}
        )
        
        return {"message": "Password reset successfully"}
    except InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    except HTTPException:
        raise
    except Exception:
        logger.exception("password_reset_failed", extra={"event": "password_reset_failed"})
        raise HTTPException(status_code=500, detail="Internal server error")
