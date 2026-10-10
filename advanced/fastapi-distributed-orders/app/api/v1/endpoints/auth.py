from fastapi import APIRouter, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shopper account",
)
async def register(payload: UserCreate, session: DbSession, settings: AppSettings) -> UserRead:
    return await AuthService(session, settings).register(payload)


@router.post("/login", response_model=TokenPair, summary="Obtain JWT pair")
async def login(payload: LoginRequest, session: DbSession, settings: AppSettings) -> TokenPair:
    return await AuthService(session, settings).login(
        email=payload.email,
        password=payload.password,
    )


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
async def refresh(payload: RefreshRequest, session: DbSession, settings: AppSettings) -> TokenPair:
    return await AuthService(session, settings).refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke refresh token")
async def logout(payload: RefreshRequest, session: DbSession, settings: AppSettings) -> None:
    await AuthService(session, settings).logout(payload.refresh_token)


@router.get("/me", response_model=UserRead, summary="Current user")
async def read_me(user: CurrentUser) -> UserRead:
    return user
