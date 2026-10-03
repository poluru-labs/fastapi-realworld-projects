from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserRole
from app.services.auth_service import AuthService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository()


@lru_cache
def get_refresh_token_repository() -> RefreshTokenRepository:
    return RefreshTokenRepository()


def get_auth_service(
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_tokens: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> AuthService:
    return AuthService(settings=settings, users=users, refresh_tokens=refresh_tokens)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserRead:
    payload = decode_token(settings=settings, token=token, expected_type="access")
    user_id = int(payload["sub"])
    record = users.get_by_id(user_id)
    if record is None or not record.is_active:
        raise UnauthorizedError()
    return record.to_read()


def require_roles(*allowed: UserRole) -> Callable[..., UserRead]:
    def checker(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
        if current_user.role not in allowed:
            raise ForbiddenError()
        return current_user

    return checker
