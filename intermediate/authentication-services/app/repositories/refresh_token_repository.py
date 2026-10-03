from dataclasses import dataclass
from datetime import datetime


@dataclass
class RefreshTokenRecord:
    jti: str
    user_id: int
    expires_at: datetime


class RefreshTokenRepository:
    """In-memory refresh token store (replace with Redis/DB in production)."""

    def __init__(self) -> None:
        self._tokens: dict[str, RefreshTokenRecord] = {}

    def save(self, *, jti: str, user_id: int, expires_at: datetime) -> None:
        self._tokens[jti] = RefreshTokenRecord(jti=jti, user_id=user_id, expires_at=expires_at)

    def get(self, jti: str) -> RefreshTokenRecord | None:
        return self._tokens.get(jti)

    def revoke(self, jti: str) -> None:
        self._tokens.pop(jti, None)

    def revoke_all_for_user(self, user_id: int) -> None:
        to_remove = [jti for jti, rec in self._tokens.items() if rec.user_id == user_id]
        for jti in to_remove:
            self._tokens.pop(jti, None)
