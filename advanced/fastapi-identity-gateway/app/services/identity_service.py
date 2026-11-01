from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.scopes import parse_scope_string, validate_requested_scopes
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_authorization_code,
    generate_client_id,
    generate_client_secret,
    generate_refresh_token,
    hash_password,
    hash_secret,
    verify_password,
    verify_secret,
)
from app.models.identity import AuthorizationCode, OAuthClient, RefreshToken, User
from app.repositories.identity_repository import IdentityRepository
from app.schemas.identity import (
    AuthorizeRequest,
    AuthorizeResponse,
    ClientCreate,
    ClientCreated,
    ClientRead,
    GrantType,
    IntrospectResponse,
    LoginResponse,
    OAuthScope,
    TokenResponse,
    UserInfoResponse,
    UserLogin,
    UserRead,
    UserRegister,
)


class IdentityService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = IdentityRepository(session)

    async def register(self, payload: UserRegister) -> UserRead:
        if await self._repo.email_exists(payload.email):
            raise ConflictError("Email already registered")
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        await self._repo.add_user(user)
        await self._session.commit()
        return UserRead.model_validate(user)

    async def login(self, payload: UserLogin) -> LoginResponse:
        user = await self._repo.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        token = create_access_token(
            settings=self._settings,
            subject=str(user.id),
            client_id="user-login",
            scopes=[OAuthScope.OPENID.value, OAuthScope.PROFILE.value],
            extra={"kind": "user_session"},
        )
        await self._session.commit()
        return LoginResponse(access_token=token, user=UserRead.model_validate(user))

    async def create_client(self, payload: ClientCreate) -> ClientCreated:
        secret = generate_client_secret()
        client_id = generate_client_id()
        row = OAuthClient(
            client_id=client_id,
            client_secret_hash=hash_secret(secret, pepper=self._settings.client_secret_pepper),
            name=payload.name,
            grant_types=[grant.value for grant in payload.grant_types],
            allowed_scopes=[scope.value for scope in payload.allowed_scopes],
            redirect_uris=payload.redirect_uris,
            is_confidential=payload.is_confidential,
        )
        await self._repo.add_client(row)
        await self._session.commit()
        return ClientCreated(client=ClientRead.model_validate(row), client_secret=secret)

    async def list_clients(self) -> list[ClientRead]:
        rows = await self._repo.list_clients()
        return [ClientRead.model_validate(row) for row in rows]

    async def authorize_user(
        self,
        user_id: int,
        payload: AuthorizeRequest,
    ) -> AuthorizeResponse:
        client = await self._require_client(payload.client_id)
        if GrantType.AUTHORIZATION_CODE.value not in client.grant_types:
            raise ForbiddenError("Client is not allowed to use authorization_code grant")
        if payload.redirect_uri not in client.redirect_uris:
            raise ForbiddenError("redirect_uri is not registered for this client")

        requested = parse_scope_string(payload.scope)
        scopes = validate_requested_scopes(requested, client.allowed_scopes)

        plain_code = generate_authorization_code()
        ttl = self._settings.authorization_code_ttl_minutes
        expires = datetime.now(UTC) + timedelta(minutes=ttl)
        await self._repo.add_auth_code(
            AuthorizationCode(
                code_hash=hash_secret(plain_code, pepper=self._settings.client_secret_pepper),
                client_id=client.id,
                user_id=user_id,
                redirect_uri=payload.redirect_uri,
                scopes=scopes,
                expires_at=expires,
            )
        )
        await self._session.commit()
        return AuthorizeResponse(
            code=plain_code,
            state=payload.state,
            expires_in=self._settings.authorization_code_ttl_minutes * 60,
        )

    async def token(
        self,
        *,
        grant_type: str,
        client_id: str,
        client_secret: str | None,
        code: str | None,
        redirect_uri: str | None,
        scope: str | None,
        refresh_token: str | None,
    ) -> TokenResponse:
        client = await self._require_client(client_id)
        if client.is_confidential:
            if not client_secret or not verify_secret(
                client_secret,
                client.client_secret_hash,
                pepper=self._settings.client_secret_pepper,
            ):
                raise UnauthorizedError("Invalid client credentials")

        if grant_type == GrantType.CLIENT_CREDENTIALS.value:
            if GrantType.CLIENT_CREDENTIALS.value not in client.grant_types:
                raise ForbiddenError("Client is not allowed to use client_credentials grant")
            requested = parse_scope_string(scope or "")
            scopes = validate_requested_scopes(requested, client.allowed_scopes)
            return await self._issue_tokens(
                client=client,
                subject=client.client_id,
                user_id=None,
                scopes=scopes,
                include_refresh=False,
            )

        if grant_type == GrantType.AUTHORIZATION_CODE.value:
            if not code or not redirect_uri:
                raise AppError("code and redirect_uri are required")
            return await self._exchange_code(client, code, redirect_uri)

        if grant_type == GrantType.REFRESH_TOKEN.value:
            if not refresh_token:
                raise AppError("refresh_token is required")
            return await self._refresh_access(client, refresh_token)

        raise AppError(f"Unsupported grant_type {grant_type!r}")

    async def introspect(self, token: str) -> IntrospectResponse:
        try:
            payload = decode_access_token(settings=self._settings, token=token)
        except UnauthorizedError:
            return IntrospectResponse(active=False)
        return IntrospectResponse(
            active=True,
            sub=str(payload.get("sub")),
            client_id=str(payload.get("client_id")),
            scope=str(payload.get("scope", "")),
            exp=int(payload.get("exp", 0)),
            token_type="access_token",
        )

    async def userinfo(self, token: str) -> UserInfoResponse:
        payload = decode_access_token(settings=self._settings, token=token)
        scopes = parse_scope_string(str(payload.get("scope", "")))
        if OAuthScope.OPENID.value not in scopes:
            raise ForbiddenError("openid scope is required for userinfo")

        sub = str(payload["sub"])
        email = None
        name = None
        if sub.isdigit():
            user = await self._repo.get_user_by_id(int(sub))
            if user is None:
                raise NotFoundError("User", sub)
            if OAuthScope.EMAIL.value in scopes:
                email = user.email
            if OAuthScope.PROFILE.value in scopes:
                name = user.full_name

        return UserInfoResponse(
            sub=sub,
            email=email,
            name=name,
            client_id=str(payload.get("client_id")),
            scope=str(payload.get("scope", "")),
        )

    def openid_configuration(self) -> dict[str, object]:
        prefix = self._settings.api_v1_prefix
        issuer = self._settings.token_issuer
        return {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}{prefix}/oauth/authorize",
            "token_endpoint": f"{issuer}{prefix}/oauth/token",
            "userinfo_endpoint": f"{issuer}{prefix}/oauth/userinfo",
            "introspection_endpoint": f"{issuer}{prefix}/oauth/introspect",
            "grant_types_supported": [grant.value for grant in GrantType],
            "scopes_supported": [scope.value for scope in OAuthScope],
            "token_endpoint_auth_methods_supported": ["client_secret_post"],
        }

    async def _exchange_code(
        self,
        client: OAuthClient,
        code: str,
        redirect_uri: str,
    ) -> TokenResponse:
        code_hash = hash_secret(code, pepper=self._settings.client_secret_pepper)
        row = await self._repo.get_auth_code_by_hash(code_hash)
        if row is None or row.client_id != client.id:
            raise UnauthorizedError("Invalid authorization code")
        if row.consumed_at is not None:
            raise UnauthorizedError("Authorization code already used")
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise UnauthorizedError("Authorization code expired")
        if row.redirect_uri != redirect_uri:
            raise ForbiddenError("redirect_uri mismatch")

        row.consumed_at = datetime.now(UTC)
        return await self._issue_tokens(
            client=client,
            subject=str(row.user_id),
            user_id=row.user_id,
            scopes=row.scopes,
            include_refresh=True,
        )

    async def _refresh_access(self, client: OAuthClient, refresh_token: str) -> TokenResponse:
        token_hash = hash_secret(refresh_token, pepper=self._settings.client_secret_pepper)
        stored = await self._repo.get_refresh_by_hash(token_hash)
        if stored is None or stored.client_id != client.id:
            raise UnauthorizedError("Invalid refresh token")
        if stored.revoked_at is not None:
            raise UnauthorizedError("Refresh token revoked")
        expires = stored.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            raise UnauthorizedError("Refresh token expired")

        stored.revoked_at = datetime.now(UTC)
        subject = str(stored.user_id) if stored.user_id is not None else client.client_id
        return await self._issue_tokens(
            client=client,
            subject=subject,
            user_id=stored.user_id,
            scopes=stored.scopes,
            include_refresh=True,
        )

    async def _issue_tokens(
        self,
        *,
        client: OAuthClient,
        subject: str,
        user_id: int | None,
        scopes: list[str],
        include_refresh: bool,
    ) -> TokenResponse:
        access = create_access_token(
            settings=self._settings,
            subject=subject,
            client_id=client.client_id,
            scopes=scopes,
        )
        refresh_plain = None
        if include_refresh:
            refresh_plain = generate_refresh_token()
            expires = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_expire_days)
            await self._repo.add_refresh_token(
                RefreshToken(
                    token_hash=hash_secret(
                        refresh_plain,
                        pepper=self._settings.client_secret_pepper,
                    ),
                    client_id=client.id,
                    user_id=user_id,
                    scopes=scopes,
                    expires_at=expires,
                )
            )
        await self._session.commit()
        return TokenResponse(
            access_token=access,
            expires_in=self._settings.access_token_expire_minutes * 60,
            scope=" ".join(scopes),
            refresh_token=refresh_plain,
        )

    async def _require_client(self, client_id: str) -> OAuthClient:
        client = await self._repo.get_client_by_client_id(client_id)
        if client is None:
            raise NotFoundError("Client", client_id)
        return client
