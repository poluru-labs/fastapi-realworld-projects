from typing import Annotated

from fastapi import APIRouter, Depends, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import AdminKey, AppSettings, CurrentUser, DbSession
from app.core.exceptions import UnauthorizedError
from app.schemas.identity import (
    AuthorizeRequest,
    AuthorizeResponse,
    IntrospectRequest,
    IntrospectResponse,
    TokenResponse,
    UserInfoResponse,
)
from app.services.identity_service import IdentityService

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


@router.get(
    "/.well-known/openid-configuration",
    summary="OpenID Provider metadata",
    description="Discovery document for token, userinfo, and introspection URLs.",
)
async def openid_configuration(session: DbSession, settings: AppSettings) -> dict[str, object]:
    return IdentityService(session, settings).openid_configuration()


@router.post(
    "/authorize",
    response_model=AuthorizeResponse,
    summary="Issue an authorization code",
    description=(
        "Requires a logged-in user bearer token from `/auth/login`. "
        "Returns a one-time code the client exchanges at `/oauth/token`."
    ),
)
async def authorize(
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
    payload: AuthorizeRequest,
) -> AuthorizeResponse:
    return await IdentityService(session, settings).authorize_user(user.id, payload)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 token endpoint",
    description=(
        "Supports `client_credentials`, `authorization_code`, and `refresh_token`. "
        "Send fields as `application/x-www-form-urlencoded`."
    ),
)
async def token_endpoint(
    session: DbSession,
    settings: AppSettings,
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str | None, Form()] = None,
    code: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    scope: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
) -> TokenResponse:
    return await IdentityService(session, settings).token(
        grant_type=grant_type,
        client_id=client_id,
        client_secret=client_secret,
        code=code,
        redirect_uri=redirect_uri,
        scope=scope,
        refresh_token=refresh_token,
    )


@router.post(
    "/introspect",
    response_model=IntrospectResponse,
    summary="Token introspection (RFC 7662-style)",
    description="Admin key or resource servers use this to check whether a bearer token is active.",
)
async def introspect(
    _: AdminKey,
    session: DbSession,
    settings: AppSettings,
    payload: IntrospectRequest,
) -> IntrospectResponse:
    return await IdentityService(session, settings).introspect(payload.token)


@router.get(
    "/userinfo",
    response_model=UserInfoResponse,
    summary="OpenID Connect userinfo",
    description="Requires `openid` scope on the OAuth access token (not the login session token).",
)
async def userinfo(
    session: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserInfoResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    return await IdentityService(session, settings).userinfo(credentials.credentials)
