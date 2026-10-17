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
A **distributed chat** API for advanced FastAPI practice: async SQLAlchemy, Alembic, JWT auth,
**rooms** with public/private visibility, **monotonic message sequences**, **Idempotency-Key** on
sends, **read cursors** per member, and **relay workers** that claim leased **delivery outbox**
rows to fan messages to connected clients.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Mental model
- **Rooms** are channels (`active` or `archived`). **Public** rooms appear in discovery and accept
  `POST .../join`. **Private** rooms return **404** to non-members (including metadata).
- **Messages** append a per-room **sequence** used for cursor sync (`after_sequence`).
- **Outbox** rows represent work to push a message to each other member; **relays** claim and
  complete deliveries with a time-bounded **lease** and **expected_version**.

### Idempotency and concurrency
- **Idempotency-Key** on `POST .../messages` — safe retries return the same message body.
- **expected_version** on relay complete — stale edge nodes get **409** after reclaim.

### Seed data
After migrate + seed: `admin@example.com` / `AdminPass123!`, public room `general` (sequence 1
welcome message), private room `private-ops` (admin member only).
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
        "name": "rooms",
        "description": "Discover, create, join, archive rooms; member read cursors.",
    },
    {
        "name": "messages",
        "description": "Cursor-based history and idempotent sends that enqueue outbox work.",
    },
    {
        "name": "relays",
        "description": "Register edge relays, claim leased deliveries, report completion.",
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
