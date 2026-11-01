from fastapi import APIRouter, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.policy import TokenResponse, UserLogin, UserRead, UserRegister, WhoAmI
from app.services.policy_service import PolicyService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
)
async def register(
    session: DbSession,
    settings: AppSettings,
    payload: UserRegister,
) -> UserRead:
    return await PolicyService(session, settings).register(payload)


@router.post("/login", response_model=TokenResponse, summary="Login and receive JWT")
async def login(session: DbSession, settings: AppSettings, payload: UserLogin) -> TokenResponse:
    return await PolicyService(session, settings).login(payload)


@router.get("/me", response_model=WhoAmI, summary="Current principal")
async def me(user: CurrentUser) -> WhoAmI:
    return WhoAmI(user=user)
