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
from app.db.seed import seed_catalog_if_empty
from app.db.session import make_engine, make_session_factory
from app.middleware.request_context import RequestContextMiddleware
from app.models import Base

logger = logging.getLogger(__name__)

API_DESCRIPTION = """
Usage metering and billing API backed by async SQLAlchemy.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Credentials
| Header | Used for |
|--------|----------|
| `X-Admin-Key` | Create customers, subscriptions, invoices |
| `X-Api-Key` | Ingest usage (`POST /usage/events`) and read `/me` routes |

Customer API keys are shown **once** on `POST /customers`. Only a hash is stored.

### Typical flow
1. `GET /meters` and `GET /plans` — discover billable metrics and the `starter` plan.
2. `POST /customers` (admin) — receive `api_key`.
3. `POST /customers/{id}/subscriptions` with `{"plan_code":"starter"}`.
4. `POST /usage/events` (customer key) with `idempotency_key` per event.
5. `GET /me/invoices/preview` or admin `GET /customers/{id}/invoices/preview`.
6. `POST /customers/{id}/invoices` to persist an `open` invoice for the period.

Usage rows store the request id from `X-Request-ID` when present, matching access logs.

### Operations
- **Liveness** — `/health/live` (no database)
- **Readiness** — `/health/ready` (`SELECT 1`)
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness does not touch the database. Readiness runs SELECT 1.",
    },
    {"name": "customers", "description": "Accounts that own subscriptions and usage (admin)."},
    {"name": "meters", "description": "Billable metrics referenced by usage events."},
    {"name": "plans", "description": "Included units and overage pricing per meter."},
    {"name": "subscriptions", "description": "Links a customer to a plan and billing period."},
    {"name": "usage", "description": "Idempotent usage ingestion and period totals."},
    {"name": "invoices", "description": "Preview and persist overage charges."},
    {"name": "me", "description": "Customer-scoped reads using `X-Api-Key`."},
]


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    application.state.engine = engine
    application.state.session_factory = make_session_factory(engine)

    if settings.environment == "test":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    session_factory = application.state.session_factory
    async with session_factory() as session:
        await seed_catalog_if_empty(session)
        await session.commit()

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
