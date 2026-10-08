from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_service, get_current_user
from app.schemas.auth import MessageResponse, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRead:
    return service.register(payload)


@router.post("/login", response_model=TokenPair)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    return service.login(email=form.username, password=form.password)


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    return service.refresh(body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    service.logout(body.refresh_token)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    return current_user
