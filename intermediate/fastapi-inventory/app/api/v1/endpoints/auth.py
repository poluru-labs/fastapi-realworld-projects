from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_service, get_current_user
from app.schemas.auth import MessageResponse, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description=(
        "Password must be at least 8 characters. Email is stored in lowercase. "
        "New accounts get the platform role `user` and may record stock movements."
    ),
    responses={409: {"description": "That email is already registered."}},
)
def register(
    payload: UserCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRead:
    return service.register(payload)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Log in with email and password",
    description=(
        "OAuth2 password form, not JSON. The form field is named `username`; "
        "send the email as its value. Returns a short-lived access token and a refresh token."
    ),
    responses={401: {"description": "Email or password is wrong, or the account is inactive."}},
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    return service.login(email=form.username, password=form.password)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate the refresh token",
    description=(
        "Issues a new access token and a new refresh token. The refresh token you sent "
        "is revoked, so replaying it returns 401."
    ),
    responses={
        401: {"description": "Refresh token is unknown, revoked, expired, or the wrong type."},
    },
)
def refresh_tokens(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    return service.refresh(body.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke a refresh token",
    description="Forgets this refresh token. The access token stays valid until it expires.",
    responses={401: {"description": "Refresh token is missing, expired, or the wrong type."}},
)
def logout(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    service.logout(body.refresh_token)
    return MessageResponse(message="Logged out")


@router.get(
    "/me",
    response_model=UserRead,
    summary="Read the signed-in account",
    description="Requires `Authorization: Bearer <access_token>`.",
)
def read_current_user(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    return current_user
