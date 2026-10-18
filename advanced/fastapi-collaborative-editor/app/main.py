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
A **collaborative editor** API for advanced FastAPI practice: async SQLAlchemy, Alembic, JWT auth,
**documents** with optimistic **base_revision** checks, an append-only **revision log**,
**Idempotency-Key** on submits, **last seen revision** cursors, and **sync nodes** that claim
leased **outbox** jobs to push edits to other collaborators.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Mental model
- **Documents** hold the latest **body** and monotonic **revision** (`active` or `archived`).
  **Public** docs accept `POST .../join`. **Private** docs return **404** to non-members.
- **Edits** send a **base_revision** plus a single **patch** (`start`, `delete`, `insert`).
  Mismatch → **409** stale conflict.
- **Sync outbox** rows fan each applied revision to other members; **sync nodes** claim and
  complete with **expected_version** (same lease pattern as distributed chat relays).

### Seed data
After migrate + seed: `admin@example.com` / `AdminPass123!`, public doc `team-playbook`
(revision 1, body `Hello team`), private `private-design-doc`.
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
        "name": "documents",
        "description": "Create, join, archive docs; member seen-revision cursors.",
    },
    {
        "name": "edits",
        "description": "Revision log sync and idempotent patch submission.",
    },
    {
        "name": "sync",
        "description": "Register sync nodes, claim leased outbox jobs, report completion.",
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
