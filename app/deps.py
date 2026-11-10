from fastapi import Request, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, GroupMember, Group
from app.security import decode_token
from app.errors import ApiError


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Extract and verify JWT bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ApiError(401, "unauthorized", "Missing, invalid, or expired token.")
    token = auth_header[7:].strip()
    if not token:
        raise ApiError(401, "unauthorized", "Missing, invalid, or expired token.")
    user_id = decode_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ApiError(401, "unauthorized", "Missing, invalid, or expired token.")
    return user


def check_membership(group_id: int, user: User, db: Session) -> GroupMember:
    """Verify that user is a member of group_id."""
    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
        .first()
    )
    if not member:
        raise ApiError(403, "forbidden", "You're not a member of this group.")
    return member


def require_member(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupMember:
    """Require caller to be a member of the group specified in path params."""
    raw_id = request.path_params.get("gid") or request.path_params.get("id")
    if raw_id is None:
        raise ApiError(400, "validation_error", "Missing group ID parameter.")
    try:
        group_id = int(raw_id)
    except (ValueError, TypeError):
        raise ApiError(422, "validation_error", "Invalid group ID parameter.")
    return check_membership(group_id, current_user, db)
