from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import models
import schemas
import deps
import os
import uuid

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    try:
        print(f"Registration attempt for email: {user.email}")
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user:
            print("Email already exists")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        print("Hashing password...")
        hashed_password = get_password_hash(user.password)
        
        print("Creating user object...")
        db_user = models.User(
            id=str(uuid.uuid4()),
            email=user.email, 
            hashed_password=hashed_password,
            role=models.UserRole.USER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        print("Adding to database...")
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print("User created successfully")
        return db_user
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(user: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

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
        db_user = db.query(models.User).filter(models.User.email == request.email).first()
        if db_user:
            # Generate password reset token (expires in 1 hour)
            reset_token = create_access_token(
                data={"sub": db_user.email, "type": "password_reset"}, 
                expires_delta=timedelta(hours=1)
            )
            
            # In a real application, you would send an email here
            # For now, we'll just log the reset token
            print(f"Password reset token for {request.email}: {reset_token}")
            print(f"Reset URL would be: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={reset_token}")
        
        # Always return success message regardless of whether email exists
        return {"message": "If an account with that email exists, you will receive a password reset link shortly."}
    except Exception as e:
        print(f"Forgot password error: {str(e)}")
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
        
        # Find the user
        db_user = db.query(models.User).filter(models.User.email == email).first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Update the password
        db_user.hashed_password = get_password_hash(request.new_password)
        db_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Password reset successfully"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    except Exception as e:
        print(f"Reset password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
