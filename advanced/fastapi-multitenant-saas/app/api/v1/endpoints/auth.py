from fastapi import APIRouter, status

from app.api.deps import AppSettings, DbSession
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPair,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

REGISTER_EXAMPLE = {
    "email": "owner@acme.example",
    "password": "SecurePass123!",
    "full_name": "Alex Owner",
    "tenant_name": "Acme Corp",
    "tenant_slug": "acme-corp",
}


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up and bootstrap a tenant",
    description=(
        "Creates a **global user**, a **new tenant**, and an **owner** membership "
        "in one transaction. Returns JWT access and refresh tokens. "
        "Use `X-Tenant-Slug` on later calls."
    ),
    openapi_extra={
        "requestBody": {
            "content": {"application/json": {"examples": {"default": {"value": REGISTER_EXAMPLE}}}}
        }
    },
)
async def register(
    payload: RegisterRequest,
    session: DbSession,
    settings: AppSettings,
) -> RegisterResponse:
    return await AuthService(session, settings).register(payload)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Obtain JWT pair",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "value": {
                                "email": "owner@acme.example",
                                "password": "SecurePass123!",
                            }
                        }
                    }
                }
            }
        }
    },
)
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
