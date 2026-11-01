from fastapi import APIRouter, status

from app.api.deps import AppSettings, DbSession
from app.schemas.auth import AccessTokenResponse, LoginRequest, RegisterRequest, RegisterResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register user and tenant",
    description=(
        "Creates a global user, a new tenant workspace, and owner membership. "
        "Returns a bearer access token for subsequent calls."
    ),
)
async def register(
    session: DbSession,
    settings: AppSettings,
    payload: RegisterRequest,
) -> RegisterResponse:
    return await AuthService(session, settings).register(payload)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    summary="Login",
    description="Returns a JWT access token. Pair with `X-Tenant-Slug` on RAG routes.",
)
async def login(
    session: DbSession,
    settings: AppSettings,
    payload: LoginRequest,
) -> AccessTokenResponse:
    return await AuthService(session, settings).login(
        email=payload.email,
        password=payload.password,
    )
