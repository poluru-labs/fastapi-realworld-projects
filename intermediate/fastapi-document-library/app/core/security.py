from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

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


def _encode_token(
    *,
    settings: Settings,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    jti = uuid4().hex
    now = datetime.now(UTC)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def create_access_token(*, settings: Settings, user_id: int, role: str) -> str:
    token, _, _ = _encode_token(
        settings=settings,
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra={"role": role},
    )
    return token


def create_refresh_token(*, settings: Settings, user_id: int) -> tuple[str, str, datetime]:
    return _encode_token(
        settings=settings,
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(*, settings: Settings, token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise UnauthorizedError() from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type")

    sub = payload.get("sub")
    jti = payload.get("jti")
    if not sub or not jti:
        raise UnauthorizedError()

    return payload
