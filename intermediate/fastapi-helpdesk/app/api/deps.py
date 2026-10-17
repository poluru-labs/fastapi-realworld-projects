from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.reply_repository import ReplyRepository
from app.repositories.ticket_repository import TicketRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserRole
from app.services.auth_service import AuthService
from app.services.reply_service import ReplyService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository()


@lru_cache
def get_refresh_token_repository() -> RefreshTokenRepository:
    return RefreshTokenRepository()


@lru_cache
def get_ticket_repository() -> TicketRepository:
    return TicketRepository()


@lru_cache
def get_reply_repository() -> ReplyRepository:
    return ReplyRepository()


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


def get_ticket_service(
    tickets: Annotated[TicketRepository, Depends(get_ticket_repository)],
    replies: Annotated[ReplyRepository, Depends(get_reply_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> TicketService:
    return TicketService(tickets=tickets, replies=replies, users=users)


def get_reply_service(
    tickets: Annotated[TicketService, Depends(get_ticket_service)],
    replies: Annotated[ReplyRepository, Depends(get_reply_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> ReplyService:
    return ReplyService(tickets=tickets, replies=replies, users=users)


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


def get_optional_user(
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> UserRead | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError()
    return _user_from_access_token(token, settings, users)


def require_roles(*allowed: UserRole) -> Callable[..., UserRead]:
    def checker(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
        if current_user.role not in allowed:
            raise ForbiddenError()
        return current_user

    return checker
