from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Group, GroupMember, Expense, Settlement
from app.schemas import (
    SettlementCreate,
    SettlementOut,
    GroupBalancesResponse,
    MemberBalance,
    SimplifiedDebt,
    ActivityItem,
    ExpenseOut,
    ExpenseSplitOut,
    format_iso_z,
)
from app.deps import get_current_user, require_member
from app.services.balances import compute_net_balances, simplify_debts
from app.errors import ApiError

router = APIRouter(prefix="/groups/{gid}", tags=["settlements", "balances", "activity"])


def _build_settlement_out(s: Settlement) -> SettlementOut:
    return SettlementOut(
        id=s.id,
        group_id=s.group_id,
        from_user=s.from_user,
        to_user=s.to_user,
        amount_cents=s.amount_cents,
        note=s.note,
        created_by=s.created_by,
        created_at=format_iso_z(s.created_at),
    )


def _build_expense_out(e: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=e.id,
        group_id=e.group_id,
        description=e.description,
        amount_cents=e.amount_cents,
        paid_by=e.paid_by,
        created_by=e.created_by,
        split_type=e.split_type,
        expense_date=e.expense_date.strftime("%Y-%m-%d"),
        created_at=format_iso_z(e.created_at),
        splits=[
            ExpenseSplitOut(user_id=sp.user_id, share_cents=sp.share_cents)
            for sp in e.splits
        ],
    )


@router.get("/balances", response_model=GroupBalancesResponse, status_code=status.HTTP_200_OK)
def get_balances(
    gid: int,
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Get net balances and simplified debt graph for all group members."""
    group = db.query(Group).filter(Group.id == gid).first()
    if not group:
        raise ApiError(404, "not_found", "Group does not exist.")

    member_map = {m.user_id: m.user.name for m in group.members}
    member_ids = list(member_map.keys())

    net = compute_net_balances(member_ids, group.expenses, group.settlements)
    simplified_debts_raw = simplify_debts(net)

    balances_out = [
        MemberBalance(user_id=uid, name=member_map[uid], net_cents=net.get(uid, 0))
        for uid in member_ids
    ]
    simplified_out = [
        SimplifiedDebt(
            from_user_id=item["from_user_id"],
            to_user_id=item["to_user_id"],
            amount_cents=item["amount_cents"],
        )
        for item in simplified_debts_raw
    ]

    return GroupBalancesResponse(balances=balances_out, simplified=simplified_out)


@router.post("/settlements", response_model=SettlementOut, status_code=status.HTTP_201_CREATED)
def create_settlement(
    gid: int,
    data: SettlementCreate,
    current_user: User = Depends(get_current_user),
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Record a settlement payment between two group members."""
    group = db.query(Group).filter(Group.id == gid).first()
    if not group:
        raise ApiError(404, "not_found", "Group does not exist.")

    # Validation: from_user != to_user
    if data.from_user == data.to_user:
        raise ApiError(422, "validation_error", "You can't pay yourself.")

    # Both users must be members
    group_member_ids = {m.user_id for m in group.members}
    if data.from_user not in group_member_ids or data.to_user not in group_member_ids:
        raise ApiError(422, "validation_error", "Everyone in the split must be a member of this group.")

    settlement = Settlement(
        group_id=gid,
        from_user=data.from_user,
        to_user=data.to_user,
        amount_cents=data.amount_cents,
        note=data.note,
        created_by=current_user.id,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)

    return _build_settlement_out(settlement)


@router.delete("/settlements/{sid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_settlement(
    gid: int,
    sid: int,
    current_user: User = Depends(get_current_user),
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Delete a settlement (used for 'Undo')."""
    settlement = db.query(Settlement).filter(Settlement.id == sid).first()
    if not settlement or settlement.group_id != gid:
        raise ApiError(404, "not_found", "Settlement does not exist in this group.")

    group = db.query(Group).filter(Group.id == gid).first()
    if current_user.id != settlement.created_by and current_user.id != group.owner_id:
        raise ApiError(
            403,
            "forbidden",
            "Only the person who added this payment or the group owner can undo it.",
        )

    db.delete(settlement)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/activity", response_model=List[ActivityItem], status_code=status.HTTP_200_OK)
def get_activity(
    gid: int,
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Get activity feed containing expenses and settlements sorted by created_at DESC then id DESC."""
    group = db.query(Group).filter(Group.id == gid).first()
    if not group:
        raise ApiError(404, "not_found", "Group does not exist.")

    items = []
    for exp in group.expenses:
        items.append({
            "type": "expense",
            "created_at": exp.created_at,
            "id": exp.id,
            "expense": _build_expense_out(exp),
            "settlement": None,
        })

    for st in group.settlements:
        items.append({
            "type": "settlement",
            "created_at": st.created_at,
            "id": st.id,
            "expense": None,
            "settlement": _build_settlement_out(st),
        })

    # Sort by created_at DESC then id DESC
    items.sort(key=lambda x: (x["created_at"], x["id"]), reverse=True)

    return [
        ActivityItem(
            type=item["type"],
            created_at=format_iso_z(item["created_at"]),
            expense=item["expense"],
            settlement=item["settlement"],
        )
        for item in items
    ]
