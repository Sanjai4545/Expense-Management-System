from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Group, GroupMember, Expense, ExpenseSplit
from app.schemas import (
    ExpenseCreateOrUpdate,
    ExpenseOut,
    ExpenseSplitOut,
    format_iso_z,
)
from app.deps import get_current_user, require_member
from app.services.splits import split_equal, split_exact, split_percent
from app.errors import ApiError

router = APIRouter(prefix="/groups/{gid}/expenses", tags=["expenses"])


def _validate_and_compute_splits(data: ExpenseCreateOrUpdate, group_member_ids: set) -> tuple[datetime.date, dict]:
    """Validate expense inputs, membership, date and compute splits."""
    today_utc = datetime.now(timezone.utc).date()
    if not data.expense_date:
        exp_date = today_utc
    else:
        exp_date = data.expense_date
        if exp_date > today_utc + timedelta(days=1):
            raise ApiError(422, "validation_error", "Expense date cannot be more than 1 day in the future.")

    # Participants count and uniqueness
    participant_ids = [p.user_id for p in data.participants]
    if len(participant_ids) < 1 or len(participant_ids) > 50:
        raise ApiError(422, "validation_error", "Participants must have between 1 and 50 entries.")
    if len(participant_ids) != len(set(participant_ids)):
        raise ApiError(422, "validation_error", "Duplicate participants are not allowed.")

    # Membership check: paid_by and all participants
    if data.paid_by not in group_member_ids:
        raise ApiError(422, "validation_error", "Everyone in the split must be a member of this group.")
    for uid in participant_ids:
        if uid not in group_member_ids:
            raise ApiError(422, "validation_error", "Everyone in the split must be a member of this group.")

    # Compute shares based on split_type
    if data.split_type == "equal":
        shares = split_equal(data.amount_cents, participant_ids)
    elif data.split_type == "exact":
        values = {p.user_id: (p.value if p.value is not None else 0) for p in data.participants}
        shares = split_exact(data.amount_cents, values)
    elif data.split_type == "percent":
        bps = {p.user_id: (p.value if p.value is not None else 0) for p in data.participants}
        shares = split_percent(data.amount_cents, bps)
    else:
        raise ApiError(422, "validation_error", "Invalid split type.")

    if sum(shares.values()) != data.amount_cents:
        raise ApiError(422, "validation_error", "Sum of shares does not equal total amount.")

    return exp_date, shares


def _build_expense_out(expense: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=expense.id,
        group_id=expense.group_id,
        description=expense.description,
        amount_cents=expense.amount_cents,
        paid_by=expense.paid_by,
        created_by=expense.created_by,
        split_type=expense.split_type,
        expense_date=expense.expense_date.strftime("%Y-%m-%d"),
        created_at=format_iso_z(expense.created_at),
        splits=[
            ExpenseSplitOut(user_id=s.user_id, share_cents=s.share_cents)
            for s in expense.splits
        ],
    )


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    gid: int,
    data: ExpenseCreateOrUpdate,
    current_user: User = Depends(get_current_user),
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Add a new expense to the group."""
    group = db.query(Group).filter(Group.id == gid).first()
    if not group:
        raise ApiError(404, "not_found", "Group does not exist.")

    group_member_ids = {m.user_id for m in group.members}
    exp_date, shares = _validate_and_compute_splits(data, group_member_ids)

    expense = Expense(
        group_id=gid,
        paid_by=data.paid_by,
        created_by=current_user.id,
        description=data.description,
        amount_cents=data.amount_cents,
        split_type=data.split_type,
        expense_date=exp_date,
    )
    db.add(expense)
    db.flush()

    for uid, share in shares.items():
        db.add(ExpenseSplit(expense_id=expense.id, user_id=uid, share_cents=share))

    db.commit()
    db.refresh(expense)

    return _build_expense_out(expense)


@router.put("/{eid}", response_model=ExpenseOut, status_code=status.HTTP_200_OK)
def update_expense(
    gid: int,
    eid: int,
    data: ExpenseCreateOrUpdate,
    current_user: User = Depends(get_current_user),
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Update an existing expense in one transaction."""
    expense = db.query(Expense).filter(Expense.id == eid).first()
    if not expense or expense.group_id != gid:
        raise ApiError(404, "not_found", "Expense does not exist in this group.")

    group = db.query(Group).filter(Group.id == gid).first()
    if current_user.id != expense.created_by and current_user.id != group.owner_id:
        raise ApiError(
            403,
            "forbidden",
            "Only the person who added this expense or the group owner can change it.",
        )

    group_member_ids = {m.user_id for m in group.members}
    exp_date, shares = _validate_and_compute_splits(data, group_member_ids)

    expense.description = data.description
    expense.amount_cents = data.amount_cents
    expense.paid_by = data.paid_by
    expense.split_type = data.split_type
    expense.expense_date = exp_date

    # Replace splits cleanly
    db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == eid).delete()
    db.flush()
    for uid, share in shares.items():
        db.add(ExpenseSplit(expense_id=expense.id, user_id=uid, share_cents=share))

    db.commit()
    db.refresh(expense)

    return _build_expense_out(expense)


@router.delete("/{eid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    gid: int,
    eid: int,
    current_user: User = Depends(get_current_user),
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Delete an expense; cascade deletes splits."""
    expense = db.query(Expense).filter(Expense.id == eid).first()
    if not expense or expense.group_id != gid:
        raise ApiError(404, "not_found", "Expense does not exist in this group.")

    group = db.query(Group).filter(Group.id == gid).first()
    if current_user.id != expense.created_by and current_user.id != group.owner_id:
        raise ApiError(
            403,
            "forbidden",
            "Only the person who added this expense or the group owner can change it.",
        )

    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
