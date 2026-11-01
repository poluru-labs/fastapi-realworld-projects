import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.session import make_engine, make_session_factory
from app.middleware.request_context import RequestContextMiddleware

logger = logging.getLogger(__name__)

API_DESCRIPTION = """
**Identity gateway** API for advanced FastAPI practice: register **OAuth clients**, run
**authorization_code** and **client_credentials** grants, issue JWT **access tokens**, expose
**userinfo**, and **introspect** tokens for downstream services.

This is a teaching stand-in for Auth0, Keycloak, or Okta — not a certified OIDC product.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Roles
| Actor | How to authenticate |
|-------|---------------------|
| Platform admin | `X-Admin-Key` — register/list OAuth clients, introspect tokens |
| End user | `/auth/login` bearer — consent via `POST /oauth/authorize` |
| OAuth client | `client_id` + `client_secret` on `/oauth/token` |

### Grants
| Grant | Use case |
|-------|----------|
| `authorization_code` | User delegated access (login → authorize → token) |
| `client_credentials` | Machine-to-machine with scoped service token |
| `refresh_token` | Rotate access tokens after code exchange |

### Token claims
Access tokens are HS256 JWTs with `iss`, `aud`, `sub`, `client_id`, and `scope`. Resource APIs
should validate signature + audience, then optionally call **introspect** when using opaque tokens
in production.

### Discovery
`GET /api/v1/oauth/.well-known/openid-configuration` links token, userinfo, and introspection
endpoints for SDK configuration.

### Seed
| Item | Value |
|------|--------|
| User | `demo@example.com` / `DemoPass123!` |
| Client | `cli_seed_dashboard` / secret in README (tests only) |
| Redirect | `http://127.0.0.1:3000/callback` |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {"name": "auth", "description": "Local user registration and login for consent."},
    {"name": "clients", "description": "Admin OAuth client registration (secrets shown once)."},
    {"name": "oauth", "description": "Authorize, token, userinfo, introspection, discovery."},
]


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    application.state.engine = engine
    application.state.session_factory = make_session_factory(engine)
    logger.info("Started %s (%s)", settings.app_name, settings.environment)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextMiddleware)

    @application.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @application.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        if settings.debug:
            return JSONResponse(status_code=500, content={"detail": str(exc)})
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @application.get("/", tags=["meta"], summary="Welcome")
    def root() -> dict[str, str]:
        return {"message": f"{settings.app_name} — see /docs for OpenAPI"}

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
