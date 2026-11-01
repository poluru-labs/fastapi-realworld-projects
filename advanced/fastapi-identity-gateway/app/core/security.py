import hashlib
import secrets
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


def hash_secret(value: str, *, pepper: str) -> str:
    digest = hashlib.sha256(f"{pepper}:{value}".encode()).hexdigest()
    return digest


def verify_secret(value: str, stored_hash: str, *, pepper: str) -> bool:
    return secrets.compare_digest(hash_secret(value, pepper=pepper), stored_hash)


def generate_client_id() -> str:
    return f"cli_{secrets.token_urlsafe(12)}"


def generate_client_secret() -> str:
    return f"cs_{secrets.token_urlsafe(24)}"


def generate_authorization_code() -> str:
    return f"ac_{secrets.token_urlsafe(32)}"


def generate_refresh_token() -> str:
    return f"rt_{secrets.token_urlsafe(32)}"


def create_access_token(
    *,
    settings: Settings,
    subject: str,
    client_id: str,
    scopes: list[str],
    token_type: str = "access",
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "client_id": client_id,
        "scope": " ".join(scopes),
        "type": token_type,
        "iss": settings.token_issuer,
        "aud": settings.token_audience,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(*, settings: Settings, token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.token_audience,
            issuer=settings.token_issuer,
        )
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    return payload
