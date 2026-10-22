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
**A/B experimentation** API for advanced FastAPI practice: async SQLAlchemy, Alembic,
experiment **provisioning**, per-experiment **ingest tokens**, deterministic **assignments**,
idempotent **exposure/conversion** events, and rolling **results**.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Keys
- **X-Admin-Key** — provision experiments, add variants, start/stop, read results.
- **X-Experiment-Token** — ingest events for one running experiment (returned once at provision).
- **Idempotency-Key** — required on ingest; safe retries return the stored event.

### Lifecycle
1. `POST /experiments` — **draft** + one-time ingest token.
2. `POST .../variants` — add arms (weights must sum to **100** before start).
3. `POST .../start` — **running**; assignment + ingest enabled.
4. `POST .../stop` — ingest rejected with **409**.

### Assignment (public)
`GET /experiments/{key}/assignment?subject_id=` — stable hash bucketing by weights.
No auth; non-running experiments return **404**.

### Ingest rules
- Only **running** experiments accept events.
- `variant_key` must match the assignment for `subject_id` or ingest returns **409**.
- Event types: **exposure** and **conversion**.

### Seed
After migrate + seed: running experiment `checkout-button` with token in README,
variants `control` / `treatment` (50/50), sample events for results.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {
        "name": "experiments",
        "description": "Provision, variants, lifecycle, public assignment, admin results.",
    },
    {
        "name": "events",
        "description": "Experiment-token ingest with idempotency and assignment checks.",
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
