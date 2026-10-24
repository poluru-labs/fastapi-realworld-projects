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
**Rate limiter** control plane for advanced FastAPI practice: admin **policies** and **clients**,
plus SDK **quota** check/consume with fixed-window counters in SQL.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Policies
- Admin defines `limit` requests per `window_seconds` (fixed window algorithm).
- `POST .../pause` and `/resume` stop or allow consumption without deleting counters.

### Clients
- Each client binds to one policy. Provisioning returns a one-time **client_key**.
- Callers send `X-Client-Id` (slug) and `X-Client-Key` (secret) on quota routes.

### Quota
1. `POST /api/v1/quota/check` — dry-run; never increments counters.
2. `POST /api/v1/quota/consume` — increments when allowed; requires **Idempotency-Key**.
3. When over limit, consume returns **429** with the same JSON shape as check.

### Admin usage
`GET /api/v1/clients/{key}/usage` lists per-subject counts in the current window.

### Seed
| Policy | Client | Secret (X-Client-Key) | Subject usage |
|--------|--------|------------------------|---------------|
| `public-api` (10/min) | `mobile-app` | `seed-client-mobile-app` | `device-abc` at 3/10 |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness does not touch the database. Readiness runs SELECT 1.",
    },
    {
        "name": "policies",
        "description": "Fixed-window rate limit policies (admin key).",
    },
    {
        "name": "clients",
        "description": "API clients with hashed secrets and policy binding.",
    },
    {
        "name": "quota",
        "description": "Check and consume quota with client credentials.",
    },
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
