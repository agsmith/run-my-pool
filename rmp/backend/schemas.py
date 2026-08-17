import enum
import re
from datetime import datetime, time
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRole(str, enum.Enum):
    USER = "USER"
    POOL_ADMIN = "POOL_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class LifecycleEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: Literal[
        "landing_view",
        "pricing_view",
        "plan_selected",
        "account_creation_view",
        "checkout_started",
        "payment_confirmed",
        "pool_launch_checklist_view",
        "pool_invite_link_copied",
        "member_onboarding_view",
        "weekly_action_center_view",
        "weekly_picks_action_clicked",
        "billing_overview_view",
        "support_hub_view",
        "support_contact_clicked",
    ]
    session_id: str = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    page: Literal[
        "home",
        "pricing",
        "create_account",
        "billing_success",
        "pool_home",
        "profile",
        "support",
    ]
    plan: Optional[Literal["free", "squares-plus", "commissioner", "pro", "club", "club-unlimited"]] = (
        None
    )
    source: Optional[Literal["homepage", "pricing", "billing", "direct"]] = None


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.USER
    is_active: bool = True
    email_verified: bool = False


def validate_account_password(value: str) -> str:
    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$", value):
        raise ValueError(
            "Password must be at least 8 characters and include uppercase, "
            "lowercase, a number, and a special character"
        )
    return value


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_account_password(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class EmailVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=256)


class EmailVerificationResendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_account_password(value)


class UserOut(UserBase):
    id: str

    class Config:
        orm_mode = True


class AdminUserOut(UserOut):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pool_count: int = 0


class AdminUserDashboardOut(BaseModel):
    total: int
    active: int
    locked: int
    pool_admins: int
    super_admins: int
    unassigned: int
    users: List[AdminUserOut]


class CheckoutSessionCreate(BaseModel):
    plan: Optional[str] = None
    season: int = Field(ge=2020, le=2100)
    order_type: str = "plan"
    quantity: int = Field(default=1, ge=1, le=50)


class CheckoutSessionOut(BaseModel):
    checkout_url: str
    session_id: str
    order_id: str


class BillingOrderOut(BaseModel):
    id: str
    plan: str
    order_type: str = "plan"
    quantity: int = 1
    season: int
    status: str
    amount_total: Optional[int] = None
    currency: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class CommissionerEntitlementOut(BaseModel):
    plan: str
    season: int
    status: str
    included_entries: Optional[int] = None
    entry_block_count: int = 0
    max_pools: Optional[int] = None
    unlimited_entries: bool = False
    activated_at: datetime

    class Config:
        orm_mode = True


class BillingOverviewOut(BaseModel):
    season: int
    entitlement: Optional[CommissionerEntitlementOut] = None
    orders: List[BillingOrderOut]
    used_entries: int = 0


class LeagueAdminUserSummary(BaseModel):
    id: str
    email: EmailStr
    total_entries: int
    surviving_entries: int
    picked_entries: int
    has_current_week_pick: bool
    all_surviving_entries_picked: bool
    is_admin: bool
    admin_role: str
    dues_paid: bool


class PoolDuesStatusUpdate(BaseModel):
    paid: bool


class PoolDuesStatusOut(BaseModel):
    pool_id: str
    user_id: str
    paid: bool
    updated_at: datetime
    updated_by: str


class LeagueAdminUserOverview(BaseModel):
    pool_id: str
    current_week: int
    total_users: int
    users: List[LeagueAdminUserSummary]


class LeagueAutoPickOut(BaseModel):
    audit_id: str
    week: int
    user_id: Optional[str] = None
    user_email: str
    entry_id: str
    entry_name: str
    team: str
    created_at: datetime


class LeagueAdminAssignment(BaseModel):
    email: EmailStr


class LeagueAdminAssignmentOut(BaseModel):
    pool_id: str
    user_id: str
    email: EmailStr
    is_admin: bool
    changed: bool


class LeagueOwnershipTransfer(BaseModel):
    email: EmailStr


class LeagueOwnershipTransferOut(BaseModel):
    pool_id: str
    previous_owner_id: str
    previous_owner_email: EmailStr
    owner_id: str
    owner_email: EmailStr


class PoolRuleValueCreate(BaseModel):
    rule_id: str
    rule_value: str


class PoolBase(BaseModel):
    name: str
    description: Optional[str] = None
    pool_type: str = "survivor"
    pickem_games_per_week: Optional[int] = Field(default=None, ge=1, le=16)
    squares_game_id: Optional[int] = None
    squares_game_ids: Optional[List[int]] = None
    lock_time: Optional[str] = None
    lock_day_of_week: Optional[int] = None
    lock_time_of_day: Optional[str] = None
    lock_timezone: Optional[str] = None
    join_lock_time: Optional[str] = None
    is_private: bool = False

    @field_validator("pool_type")
    @classmethod
    def validate_pool_type(cls, value: str) -> str:
        normalized = (value or "survivor").strip().lower()
        if normalized not in {"survivor", "pickem", "squares"}:
            raise ValueError("Pool type must be survivor, pickem, or squares")
        return normalized


class PoolCreate(PoolBase):
    join_password: Optional[str] = None
    # Optional rule values for enhanced pool settings
    rule_values: Optional[List[PoolRuleValueCreate]] = []


class PoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    lock_time: Optional[str] = None
    lock_day_of_week: Optional[int] = None
    lock_time_of_day: Optional[str] = None
    lock_timezone: Optional[str] = None
    join_lock_time: Optional[str] = None
    is_private: Optional[bool] = None
    join_password: Optional[str] = None
    rule_values: Optional[List[PoolRuleValueCreate]] = None


class PoolJoin(BaseModel):
    password: Optional[str] = None


class PoolEmailInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class PoolEmailInviteOut(BaseModel):
    message: str


class PoolInviteOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    join_lock_time: Optional[datetime] = None
    is_private: bool

    class Config:
        orm_mode = True


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
    pool_type: str = "survivor"
    pickem_games_per_week: Optional[int] = None
    squares_game_id: Optional[int] = None
    squares_game_ids: Optional[List[int]] = None
    lock_time: Optional[datetime] = None
    lock_day_of_week: Optional[int] = None
    lock_time_of_day: Optional[time] = None
    lock_timezone: Optional[str] = None
    join_lock_time: Optional[datetime] = None
    is_private: bool = False
    owner_id: str
    billing_entitlement_id: Optional[str] = None
    billing_season: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    rule_values: Optional[List[PoolRuleValueOut]] = []

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class PoolMemberDirectoryUser(BaseModel):
    id: str
    email: EmailStr
    pool_role: str
    entry_count: int = 0
    remaining_entry_count: int = 0
    total_entry_count: int = 0
    joined_at: Optional[datetime] = None


class PoolMemberDirectoryOut(BaseModel):
    pool_id: str
    total_users: int
    users: List[PoolMemberDirectoryUser]


class SquareClaimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_index: int = Field(ge=0, le=9)
    column_index: int = Field(ge=0, le=9)
    user_id: Optional[str] = None
    display_name: Optional[str] = Field(default=None, max_length=100)


class SquarePayoutConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pot_mode: Literal["fixed", "per_square"] = "fixed"
    total_pot_cents: Optional[int] = Field(default=None, ge=0)
    per_square_cents: Optional[int] = Field(default=None, ge=0)
    q1_percent: int = Field(ge=0, le=100)
    halftime_percent: int = Field(ge=0, le=100)
    q3_percent: int = Field(ge=0, le=100)
    final_percent: int = Field(ge=0, le=100)


class EntryBase(BaseModel):
    name: str


class EntryCreate(BaseModel):
    pool_id: str
    name: Optional[str] = None
    generate_name: bool = False


class EntryUpdate(BaseModel):
    name: Optional[str] = None


class EntryTransfer(BaseModel):
    entry_id: str
    to_email: str


class AdminPickUpdate(BaseModel):
    team: str  # Team abbreviation, e.g. "NE", "KC"


class AdminPickCorrection(BaseModel):
    team: str
    reason: Optional[str] = None


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
    week: int = Field(ge=1, le=18)
    team: str
    game_id: Optional[int] = None


class PickCreate(PickBase):
    entry_id: str


class PickUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team: Optional[str] = None


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


class PickEmStandingOut(BaseModel):
    rank: int
    entry_id: str
    entry_name: str
    user_id: str
    user_email: EmailStr
    points: int
    possible_points: int
    picks_made: int


class AuditLogOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    action: str
    details: str
    created_at: datetime

    class Config:
        orm_mode = True


class AuditFilterUser(BaseModel):
    id: str
    email: EmailStr


class AuditFilterOptions(BaseModel):
    event_types: List[str]
    users: List[AuditFilterUser]
    includes_system_events: bool = False


class PickBreakdownUser(BaseModel):
    user_id: str
    email: EmailStr
    entry_count: int


class PickBreakdownItem(BaseModel):
    team: str
    team_id: int
    team_name: str
    team_abbrv: str
    team_logo: Optional[str] = None
    count: int
    users: List[PickBreakdownUser] = Field(default_factory=list)


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


class PoolUserLockByEmail(BaseModel):
    email: EmailStr
    locked: bool
    reason: Optional[str] = None


class PoolUserLockOut(BaseModel):
    pool_id: str
    user_id: str
    locked_at: datetime
    reason: Optional[str] = None

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# League schemas
# ---------------------------------------------------------------------------


class LeagueBase(BaseModel):
    name: str
    description: Optional[str] = None
    lock_time: Optional[str] = None
    is_private: bool = False


class LeagueCreate(LeagueBase):
    rule_values: Optional[List["PoolRuleValueCreate"]] = None


class LeagueUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    lock_time: Optional[datetime] = None
    is_private: Optional[bool] = None
    rule_values: Optional[List["PoolRuleValueCreate"]] = None


class LeagueOut(BaseModel):
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
