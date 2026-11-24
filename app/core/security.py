import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt only looks at the first 72 bytes; bcrypt 5 raises on longer input, so cut it
# explicitly (the same result passlib gave, so existing hashes keep verifying).
_BCRYPT_MAX_BYTES = 72

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(plain), hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(subject: Any, role: str = "member") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(subject), "role": role, "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def create_refresh_token(subject: Any) -> tuple[str, str]:
    """Return (token, jti). The jti is tracked in Redis for rotation/revocation."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = uuid.uuid4().hex
    token = jwt.encode(
        {"sub": str(subject), "exp": expire, "type": "refresh", "jti": jti},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    return token, jti


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None


AVATAR_COLORS = [
    "#7c5cbf",
    "#9b7fd4",
    "#c46bb5",
    "#4ecdc4",
    "#378add",
    "#639922",
    "#d85a30",
    "#854f0b",
]


def pick_avatar_color(username: str) -> str:
    idx = sum(ord(c) for c in username) % len(AVATAR_COLORS)
    return AVATAR_COLORS[idx]
