from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.repositories.key_repository import KeyRepository, get_key_repository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserRole
from app.services.access_service import AccessService
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.principal import Principal
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


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


def get_api_key_service(
    repository: Annotated[KeyRepository, Depends(get_key_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApiKeyService:
    return ApiKeyService(repository, settings)


def get_access_service(
    repository: Annotated[KeyRepository, Depends(get_key_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AccessService:
    return AccessService(repository, users, settings)


def _user_from_access_token(token: str, settings: Settings, users: UserRepository) -> UserRead:
    payload = decode_token(settings=settings, token=token, expected_type="access")
    user_id = int(payload["sub"])
    record = users.get_by_id(user_id)
    if record is None or not record.is_active:
        raise UnauthorizedError()
    return record.to_read()


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserRead:
    return _user_from_access_token(token, settings, users)


def get_principal(
    access: Annotated[AccessService, Depends(get_access_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key", include_in_schema=True)] = None,
    token: Annotated[str | None, Depends(oauth2_scheme_optional)] = None,
) -> Principal:
    if x_api_key is not None and x_api_key.strip():
        return access.resolve_api_key(x_api_key.strip())
    if token:
        user = _user_from_access_token(token, settings, users)
        return Principal(user=user, auth_method="jwt")
    raise UnauthorizedError("Provide Authorization Bearer token or X-Api-Key")


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require_roles(*allowed: UserRole) -> Callable[..., UserRead]:
    def checker(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
        if current_user.role not in allowed:
            raise ForbiddenError()
        return current_user

    return checker
