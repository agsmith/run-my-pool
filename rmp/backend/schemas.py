from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    USER = "USER"
    POOL_ADMIN = "POOL_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.USER
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class UserOut(UserBase):
    id: str
    class Config:
        orm_mode = True

class PoolBase(BaseModel):
    name: str
    description: Optional[str] = None
    lock_time: Optional[str] = None
    is_private: bool = False

class PoolCreate(PoolBase):
    pass

class PoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    lock_time: Optional[str] = None
    is_private: Optional[bool] = None

class PoolOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    lock_time: Optional[datetime] = None
    is_private: bool = False
    owner_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class EntryBase(BaseModel):
    name: str

class EntryCreate(EntryBase):
    pool_id: str

class EntryUpdate(BaseModel):
    name: Optional[str] = None

class EntryOut(BaseModel):
    id: str
    name: str
    user_id: str
    pool_id: str
    alive: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class PickBase(BaseModel):
    week: int
    team: str

class PickCreate(PickBase):
    entry_id: str

class PickUpdate(BaseModel):
    week: Optional[int] = None
    team: Optional[str] = None
    locked: Optional[bool] = None
    result: Optional[str] = None

class PickOut(PickBase):
    id: str
    entry_id: str
    locked: bool = False
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class AuditLogOut(BaseModel):
    id: str
    user_id: str
    action: str
    details: str
    class Config:
        orm_mode = True

class MessageBoardOut(BaseModel):
    id: str
    user_id: str
    message: str
    class Config:
        orm_mode = True
