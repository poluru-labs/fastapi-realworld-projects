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
**IoT telemetry** API for advanced FastAPI practice: async SQLAlchemy, Alembic,
**device provisioning**, per-device **ingest tokens**, idempotent telemetry, and
threshold **alerts** on metric time series.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Keys
- **X-Admin-Key** — provision devices, query metrics, manage alerts.
- **X-Device-Token** — ingest telemetry for one device (returned once at provision).
- **Idempotency-Key** — required on ingest; safe retries return the stored reading.

### Devices
- Stable lowercase **device_key** (`warehouse-temp-01`).
- **Suspended** or **decommissioned** devices reject ingest with **409**.
- **last_seen_at** updates from the newest `recorded_at` accepted.

### Readings
- JSON **metrics** map (snake_case keys) with edge **recorded_at**.
- Optional **dedupe_key** prevents duplicate batches from flaky firmware.

### Alerts
Rules compare the **max** metric value in a window to a threshold (`gte`, `gt`, `lte`, `lt`).

### Seed data
After migrate + seed: device `warehouse-temp-01` with token documented in README,
suspended `legacy-pump-02`, sample readings and a temperature alert.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {
        "name": "devices",
        "description": "Provision, suspend, and decommission fleet members.",
    },
    {
        "name": "telemetry",
        "description": "Device-token ingest with idempotency and dedupe keys.",
    },
    {
        "name": "metrics",
        "description": "Overview snapshots and metric time series for dashboards.",
    },
    {
        "name": "alerts",
        "description": "Per-device threshold rules and synchronous evaluation.",
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
