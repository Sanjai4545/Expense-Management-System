from datetime import datetime, timezone, timedelta
from typing import Optional
import bcrypt
import jwt
from app.config import SECRET_KEY
from app.errors import ApiError

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """Hash a password using bcrypt directly."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash directly."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: int) -> str:
    """Create a signed JWT token valid for 7 days."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    """Decode JWT token and return user_id, or raise ApiError(401)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise ApiError(401, "unauthorized", "Missing, invalid, or expired token; wrong login")
        return int(sub)
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "unauthorized", "Your session expired. Log in again.")
    except Exception:
        raise ApiError(401, "unauthorized", "Missing, invalid, or expired token; wrong login")
