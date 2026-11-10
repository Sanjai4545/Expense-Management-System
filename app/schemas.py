from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, StrictInt, EmailStr, field_validator, field_serializer


def format_iso_z(dt: datetime) -> str:
    """Format naive UTC datetime as ISO 8601 with trailing Z."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Auth Schemas ---

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 1 or len(s) > 50:
            raise ValueError("Name must be between 1 and 50 characters.")
        return s

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        b = v.encode("utf-8")
        if len(b) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(b) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    id: StrictInt
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# --- Group Schemas ---

class GroupCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 1 or len(s) > 60:
            raise ValueError("Group name must be between 1 and 60 characters.")
        return s


class MemberPreview(BaseModel):
    id: StrictInt
    name: str

    model_config = ConfigDict(from_attributes=True)


class GroupSummary(BaseModel):
    id: StrictInt
    name: str
    member_count: StrictInt
    members_preview: List[MemberPreview]
    my_balance_cents: StrictInt
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class GroupMemberOut(BaseModel):
    id: StrictInt
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class GroupDetail(BaseModel):
    id: StrictInt
    name: str
    owner_id: StrictInt
    created_at: str
    members: List[GroupMemberOut]

    model_config = ConfigDict(from_attributes=True)


class AddMemberRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


# --- Expense Schemas ---

class ParticipantInput(BaseModel):
    user_id: StrictInt
    value: Optional[StrictInt] = None


class ExpenseCreateOrUpdate(BaseModel):
    description: str
    amount_cents: StrictInt
    paid_by: StrictInt
    split_type: str  # equal, exact, percent
    expense_date: Optional[date] = None
    participants: List[ParticipantInput]

    @field_validator("description")
    @classmethod
    def validate_desc(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 1 or len(s) > 100:
            raise ValueError("Description must be between 1 and 100 characters.")
        return s

    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v < 1 or v > 1_000_000_000:
            raise ValueError("Amount must be between 1 and 1,000,000,000 paise (₹1 crore).")
        return v

    @field_validator("split_type")
    @classmethod
    def validate_split_type(cls, v: str) -> str:
        s = v.strip().lower()
        if s not in ("equal", "exact", "percent"):
            raise ValueError("Split type must be 'equal', 'exact', or 'percent'.")
        return s


class ExpenseSplitOut(BaseModel):
    user_id: StrictInt
    share_cents: StrictInt

    model_config = ConfigDict(from_attributes=True)


class ExpenseOut(BaseModel):
    id: StrictInt
    group_id: StrictInt
    description: str
    amount_cents: StrictInt
    paid_by: StrictInt
    created_by: StrictInt
    split_type: str
    expense_date: str
    created_at: str
    splits: List[ExpenseSplitOut]

    model_config = ConfigDict(from_attributes=True)


# --- Settlement Schemas ---

class SettlementCreate(BaseModel):
    from_user: StrictInt
    to_user: StrictInt
    amount_cents: StrictInt
    note: Optional[str] = None

    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v < 1 or v > 1_000_000_000:
            raise ValueError("Amount must be between 1 and 1,000,000,000 paise (₹1 crore).")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if len(s) > 100:
            raise ValueError("Note must not exceed 100 characters.")
        return s


class SettlementOut(BaseModel):
    id: StrictInt
    group_id: StrictInt
    from_user: StrictInt
    to_user: StrictInt
    amount_cents: StrictInt
    note: Optional[str] = None
    created_by: StrictInt
    created_at: str

    model_config = ConfigDict(from_attributes=True)


# --- Balances and Activity Schemas ---

class MemberBalance(BaseModel):
    user_id: StrictInt
    name: str
    net_cents: StrictInt


class SimplifiedDebt(BaseModel):
    from_user_id: StrictInt
    to_user_id: StrictInt
    amount_cents: StrictInt


class GroupBalancesResponse(BaseModel):
    balances: List[MemberBalance]
    simplified: List[SimplifiedDebt]


class ActivityItem(BaseModel):
    type: str  # "expense" or "settlement"
    created_at: str
    expense: Optional[ExpenseOut] = None
    settlement: Optional[SettlementOut] = None
