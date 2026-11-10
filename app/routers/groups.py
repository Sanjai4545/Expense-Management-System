from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Group, GroupMember
from app.schemas import (
    GroupCreate,
    GroupSummary,
    MemberPreview,
    GroupDetail,
    GroupMemberOut,
    AddMemberRequest,
    format_iso_z,
)
from app.deps import get_current_user, require_member
from app.services.balances import compute_net_balances
from app.errors import ApiError

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=GroupDetail, status_code=status.HTTP_201_CREATED)
def create_group(
    data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new group; creator becomes owner and first member."""
    group = Group(name=data.name, owner_id=current_user.id)
    db.add(group)
    db.flush()  # get group.id

    membership = GroupMember(group_id=group.id, user_id=current_user.id)
    db.add(membership)
    db.commit()
    db.refresh(group)

    members_out = [
        GroupMemberOut(id=current_user.id, name=current_user.name, email=current_user.email)
    ]
    return GroupDetail(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        created_at=format_iso_z(group.created_at),
        members=members_out,
    )


@router.get("", response_model=List[GroupSummary], status_code=status.HTTP_200_OK)
def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List only groups caller belongs to, newest first."""
    memberships = (
        db.query(GroupMember)
        .filter(GroupMember.user_id == current_user.id)
        .all()
    )
    group_ids = [m.group_id for m in memberships]
    if not group_ids:
        return []

    groups = (
        db.query(Group)
        .filter(Group.id.in_(group_ids))
        .order_by(Group.created_at.desc())
        .all()
    )

    summaries = []
    for g in groups:
        member_ids = [m.user_id for m in g.members]
        net = compute_net_balances(member_ids, g.expenses, g.settlements)
        my_balance = net.get(current_user.id, 0)
        preview = [
            MemberPreview(id=m.user.id, name=m.user.name)
            for m in g.members[:4]
        ]
        summaries.append(
            GroupSummary(
                id=g.id,
                name=g.name,
                member_count=len(g.members),
                members_preview=preview,
                my_balance_cents=my_balance,
                created_at=format_iso_z(g.created_at),
            )
        )
    return summaries


@router.get("/{id}", response_model=GroupDetail, status_code=status.HTTP_200_OK)
def get_group(
    id: int,
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Get group details including all members."""
    group = db.query(Group).filter(Group.id == id).first()
    if not group:
        raise ApiError(404, "not_found", "Group does not exist.")

    members_out = [
        GroupMemberOut(id=m.user.id, name=m.user.name, email=m.user.email)
        for m in group.members
    ]
    return GroupDetail(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        created_at=format_iso_z(group.created_at),
        members=members_out,
    )


@router.post("/{id}/members", response_model=GroupMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    id: int,
    data: AddMemberRequest,
    _membership: GroupMember = Depends(require_member),
    db: Session = Depends(get_db),
):
    """Add a member to the group by email."""
    target_email = data.email.strip().lower()
    user_to_add = db.query(User).filter(User.email == target_email).first()
    if not user_to_add:
        raise ApiError(
            404,
            "not_found",
            "No account found for that email. Ask them to sign up first.",
        )

    # Check if already a member
    already_member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == id, GroupMember.user_id == user_to_add.id)
        .first()
    )
    if already_member:
        raise ApiError(
            409,
            "conflict",
            f"{user_to_add.name} is already in this group.",
        )

    new_member = GroupMember(group_id=id, user_id=user_to_add.id)
    db.add(new_member)
    db.commit()

    return GroupMemberOut(
        id=user_to_add.id,
        name=user_to_add.name,
        email=user_to_add.email,
    )
