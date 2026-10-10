from datetime import UTC, datetime

from app.core.config import Settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair
from app.schemas.user import UserCreate, UserRead


class AuthService:
    def __init__(
        self,
        *,
        settings: Settings,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._settings = settings
        self._users = users
        self._refresh_tokens = refresh_tokens

    def register(self, payload: UserCreate) -> UserRead:
        if self._users.email_exists(payload.email):
            raise ConflictError("Email already registered")
        return self._users.create(payload)

    def login(self, *, email: str, password: str) -> TokenPair:
        user = self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        return self._issue_token_pair(user_id=user.id, role=user.role.value)

    def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(
            settings=self._settings,
            token=refresh_token,
            expected_type="refresh",
        )
        jti = str(payload["jti"])
        stored = self._refresh_tokens.get(jti)
        if stored is None:
            raise UnauthorizedError("Refresh token revoked or unknown")

        if stored.expires_at < datetime.now(UTC):
            self._refresh_tokens.revoke(jti)
            raise UnauthorizedError("Refresh token expired")

        user_id = int(payload["sub"])
        if stored.user_id != user_id:
            raise UnauthorizedError()

        user = self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError()

        self._refresh_tokens.revoke(jti)
        return self._issue_token_pair(user_id=user.id, role=user.role.value)

    def logout(self, refresh_token: str) -> None:
        payload = decode_token(
            settings=self._settings,
            token=refresh_token,
            expected_type="refresh",
        )
        self._refresh_tokens.revoke(str(payload["jti"]))

    def _issue_token_pair(self, *, user_id: int, role: str) -> TokenPair:
        access = create_access_token(settings=self._settings, user_id=user_id, role=role)
        refresh, jti, expires_at = create_refresh_token(settings=self._settings, user_id=user_id)
        self._refresh_tokens.save(jti=jti, user_id=user_id, expires_at=expires_at)
        return TokenPair(access_token=access, refresh_token=refresh)
