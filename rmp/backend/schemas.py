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


class PoolRuleValueCreate(BaseModel):
    rule_id: str
    rule_value: str


class PoolBase(BaseModel):
    name: str
    description: Optional[str] = None
    lock_time: Optional[str] = None
    is_private: bool = False


class PoolCreate(PoolBase):
    # Optional rule values for enhanced pool settings
    rule_values: Optional[List[PoolRuleValueCreate]] = []


class PoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    lock_time: Optional[str] = None
    is_private: Optional[bool] = None
    rule_values: Optional[List[PoolRuleValueCreate]] = None


class RuleOut(BaseModel):
    id: str
    pool_type: Optional[str] = None
    rule_text: str
    rule_type: str
    default_value: Optional[str] = None
    enabled_by_default: bool = True

    class Config:
        orm_mode = True


class PoolRuleValueOut(BaseModel):
    rule_id: str
    rule_value: str
    rule: Optional[RuleOut] = None

    class Config:
        orm_mode = True


class PoolOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    lock_time: Optional[datetime] = None
    is_private: bool = False
    owner_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    rule_values: Optional[List[PoolRuleValueOut]] = []

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class EntryBase(BaseModel):
    name: str


class EntryCreate(EntryBase):
    pool_id: str


class EntryUpdate(BaseModel):
    name: Optional[str] = None


class EntryTransfer(BaseModel):
    entry_id: str
    to_email: str


class AdminPickUpdate(BaseModel):
    team: str  # Team abbreviation, e.g. "NE", "KC"


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
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


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
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class AuditLogOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    action: str
    details: str
    created_at: datetime

    class Config:
        orm_mode = True


class PickBreakdownItem(BaseModel):
    team: str
    team_id: int
    team_name: str
    team_abbrv: str
    team_logo: Optional[str] = None
    count: int


class MessageBoardCreate(BaseModel):
    pool_id: str
    message: str


class MessageBoardOut(BaseModel):
    id: str
    pool_id: str
    user_id: str
    message: str
    created_at: str
    user_email: Optional[str] = None

    class Config:
        orm_mode = True


class PoolUserLockCreate(BaseModel):
    reason: Optional[str] = None


class PoolUserLockOut(BaseModel):
    pool_id: str
    user_id: str
    locked_at: datetime
    reason: Optional[str] = None

    class Config:
        orm_mode = True
