from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(*, settings: Settings, user_id: int) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(
    *,
    settings: Settings,
    token: str,
    expected_type: str = "access",
) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise UnauthorizedError() from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type")

    if not payload.get("sub"):
        raise UnauthorizedError()

    return payload
