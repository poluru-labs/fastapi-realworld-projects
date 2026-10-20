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
**Realtime analytics** API for advanced FastAPI practice: async SQLAlchemy, Alembic,
**event streams**, idempotent **ingest**, rolling **metrics**, and threshold **alerts**.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Keys (not JWT)
- **X-Admin-Key** — manage streams, read metrics, configure alerts.
- **X-Ingest-Key** — append events to active streams.
- **Idempotency-Key** — required on ingest; safe retries return the same stored body.

Defaults in `.env.example` are for local dev only.

### Streams
- Each stream has a stable lowercase **key** (`web-traffic`).
- **Paused** streams reject ingest with **409** until resumed.
- Optional **dedupe_key** on each event prevents duplicate business ids per stream.

### Metrics
- **Overview** — totals and a 15-minute rolling window by `occurred_at`.
- **Time series** — fixed-width buckets computed in the service (SQLite + Postgres parity).

### Seed data
After migrate + seed: stream `web-traffic` (12 sample events + alert rule),
paused stream `checkout` (ingest disabled demo).
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {
        "name": "streams",
        "description": "Create and pause event streams (admin key).",
    },
    {
        "name": "events",
        "description": "Idempotent single and batch ingest (ingest key + Idempotency-Key).",
    },
    {
        "name": "metrics",
        "description": "Rolling counts and bucketed volume for dashboards.",
    },
    {
        "name": "alerts",
        "description": "Threshold rules evaluated against recent event volume.",
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
