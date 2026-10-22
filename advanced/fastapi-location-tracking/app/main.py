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
**Location tracking** API for advanced FastAPI practice: async SQLAlchemy, Alembic,
**tracker provisioning**, per-tracker **ingest tokens**, idempotent GPS ingest,
**circular geofences**, and enter/exit **events** evaluated on each ping.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Keys
- **X-Admin-Key** — provision trackers, define geofences, assign monitors, read trails and events.
- **X-Tracker-Token** — ingest locations for one tracker (returned once at provision).
- **Idempotency-Key** — required on ingest; safe retries return the stored ping and events.

### Trackers
- Stable lowercase **tracker_key** (`delivery-van-01`).
- **Suspended** trackers reject ingest with **409**.
- **last_latitude**, **last_longitude**, and **last_seen_at** update from accepted pings.

### Locations
- WGS84 **latitude** / **longitude** with optional **accuracy_m** and edge **recorded_at**.
- Optional **dedupe_key** prevents duplicate points from flaky mobile clients.

### Geofences
- Circular regions: center coordinates plus **radius_m** (Haversine distance).
- **Monitors** link a tracker to a geofence; ingest compares inside/outside state.
- **Enter** and **exit** events are returned inline on ingest and listed historically.

### Seed data
After migrate + seed: tracker `delivery-van-01` with token documented in README,
a warehouse geofence, monitor assignment, and sample pings.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {
        "name": "trackers",
        "description": "Provision, suspend, resume, overview, and geofence monitors.",
    },
    {
        "name": "locations",
        "description": "Tracker-token ingest with idempotency; admin location trail.",
    },
    {
        "name": "geofences",
        "description": "Circular geofence CRUD and disable.",
    },
    {
        "name": "geofence-events",
        "description": "Historical enter/exit events per tracker.",
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
