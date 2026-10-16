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
A **distributed scheduler** API for advanced FastAPI practice: async SQLAlchemy, Alembic,
JWT auth, **schedule definitions**, **scheduled runs**, **worker leases**, **Idempotency-Key**
on triggers, and **expected_version** when completing work.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Mental model
- **Schedules** describe cron or interval work (`draft` → `published` → `paused` / `archived`).
- **Runs** are concrete executions enqueued by `POST .../trigger` (or a future cron dispatcher).
- **Workers** register capabilities, **claim** pending runs, and **complete** them while holding
  a time-bounded **lease** so two workers do not execute the same run.

### Idempotency and concurrency
- **Idempotency-Key** on trigger — safe retries return the same run body.
- **expected_version** on complete — stale workers get **409** after another claim or completion.
- Failed runs re-queue with `retry_delay_seconds` until `max_attempts` is exhausted.

### Visibility
- Published schedules are public. Draft/archived schedules return **404** to guests.
- Run details are visible to the **owner** who triggered them and to **admins**.
  Others get **404**.

### Seed data
After migrate + seed: `admin@example.com` / `AdminPass123!`, published schedule `nightly-report`
(`task_type`: `report`), draft `draft-cleanup`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {
        "name": "auth",
        "description": "Register, login, refresh rotation, logout (JSON bodies).",
    },
    {
        "name": "schedules",
        "description": "Schedule CRUD, publish/pause lifecycle, manual trigger.",
    },
    {
        "name": "runs",
        "description": "Inspect and cancel runs you enqueued.",
    },
    {
        "name": "workers",
        "description": "Register workers, claim leased work, report outcomes.",
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
