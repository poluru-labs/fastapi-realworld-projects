from fastapi import APIRouter, status

from app.api.deps import AppSettings, DbSession
from app.schemas.identity import LoginResponse, UserLogin, UserRead, UserRegister
from app.services.identity_service import IdentityService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
    description=(
        "Local account for authorization_code consent (login before POST /oauth/authorize)."
    ),
)
async def register(
    session: DbSession,
    settings: AppSettings,
    payload: UserRegister,
) -> UserRead:
    return await IdentityService(session, settings).register(payload)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description=(
        "Returns a short-lived bearer token for calling `POST /oauth/authorize`. "
        "Not a substitute for OAuth client access tokens."
    ),
)
async def login(session: DbSession, settings: AppSettings, payload: UserLogin) -> LoginResponse:
    return await IdentityService(session, settings).login(payload)
