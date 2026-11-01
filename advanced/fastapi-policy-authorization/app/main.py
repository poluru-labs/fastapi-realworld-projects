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
**Policy-based authorization** API for advanced FastAPI practice: store **RBAC** role assignments,
define **allow/deny** rules with priorities, evaluate decisions centrally, and enforce them on
sample **document** resources with **ABAC clearance** levels.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Model
| Layer | What it stores |
|-------|----------------|
| Roles | `admin`, `editor`, `viewer` (seed) |
| User roles | Many-to-many bindings (admin API) |
| Policy rules | Effect, actions, resource patterns, roles, optional clearance |
| Clearance | User attribute `public` / `internal` / `secret` compared to document classification |

### Decision algorithm (`app/core/policy_engine.py`)
1. Collect rules matching action, resource pattern, roles, and clearance.
2. Sort by **priority** (highest first).
3. Any matching **deny** → reject.
4. Any matching **allow** → permit.
5. Otherwise **default deny**.

### Typical flow
1. Admin `POST /policy/rules` and `POST /policy/role-assignments` (or use seed users).
2. Developer `POST /policy/evaluate` while building services.
3. Apps call `/documents` — services invoke the same engine as evaluate.

### Auth
- **JWT** — user routes (`Authorization: Bearer`).
- **X-Admin-Key** — manage rules and role assignments.

### Seed users
| Email | Password | Role | Clearance | Sees |
|-------|----------|------|-----------|------|
| `editor@example.com` | `DemoPass123!` | editor | internal | public + internal docs |
| `viewer@example.com` | `DemoPass123!` | viewer | public | public docs only |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness and readiness probes."},
    {"name": "auth", "description": "Register, login, and `/auth/me` principal."},
    {"name": "policy", "description": "Admin rules, role assignments, and evaluate PDP."},
    {"name": "documents", "description": "Protected resources enforced by the policy engine."},
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
