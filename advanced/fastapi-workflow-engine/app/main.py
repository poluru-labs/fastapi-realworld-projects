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
**Workflow engine** API: versioned definitions, running instances, append-only history,
JWT auth, **Idempotency-Key** on commands, and **expected_version** optimistic concurrency.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Definitions (templates)
- Admins author a **directed graph**: `states`, `transitions`, and optional `terminal_states`.
- Transitions may declare `roles` (for example `admin`) so only privileged actors can fire them.
- Lifecycle: `draft` → `published` → `archived` (with legal restore edges). Only **published**
  definitions can start instances. Draft slugs return **404** to guests.

### Instances (runtime)
- `POST /workflow-instances` starts at `initial_state` and records `instance_started`.
- `POST .../transitions` validates `(action, current_state)` against the definition, appends
  `state_changed`, bumps `version`, and marks **completed** when entering a terminal state.
- `GET .../events` is the audit trail ordered by `sequence`.

### Safety
- **Idempotency-Key** on start and transition: safe retries return the same JSON body.
- **expected_version** must match the instance row or the API returns **409**.
- Another user's instance id returns **404**, not **403**.

### Seed data
Login as `admin@example.com` / `AdminPass123!`.
Published workflow: `employee-onboarding`. Draft (admin-only): `draft-internal`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness does not touch the database. Readiness runs SELECT 1.",
    },
    {
        "name": "auth",
        "description": "Register, login, refresh rotation, and logout (JSON bodies).",
    },
    {
        "name": "workflow-definitions",
        "description": "Admin-authored graphs and publish/archive lifecycle.",
    },
    {
        "name": "workflow-instances",
        "description": (
            "Start instances, fire transitions with version checks, and read event history."
        ),
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
