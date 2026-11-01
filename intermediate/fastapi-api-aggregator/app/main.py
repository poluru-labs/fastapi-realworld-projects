from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**API aggregator** for intermediate FastAPI practice: JWT auth, owned **sources**,
**aggregate plans** that fan out to mock upstreams, and stored **runs** with optional idempotency.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Sources (mock upstreams)
- Register slugs that map to a `mock_catalog` (`users`, `orders`, `inventory`).
- `base_url` documents intent; this sample never calls the public internet.
- Pause a source with `PATCH ... {"is_active": false}` — fragments return **409** while paused.
- You only see sources you own. Admins list everything. Other people's slugs → **404**.

### Aggregate plans
- A plan lists **fragments**: each has a stable `key`, `source_slug`, and GET `path`.
- Plans start as **draft**; `POST /aggregates/{slug}/publish` enables execution.
- Every referenced source must belong to the same signed-in user.

### Runs
1. `POST /api/v1/aggregates/{slug}/runs` executes all fragments concurrently
   (`asyncio.gather` + mock client).
2. Response includes per-fragment HTTP status and JSON (`partial: true` if any fragment failed).
3. Send **Idempotency-Key** to replay the same stored run for your account and slug.

### Seed (sign in as demo)
| Account | Password | Published aggregate |
|---------|----------|---------------------|
| `demo@example.com` | `DemoPass123!` | `customer-360` (profile + recent orders) |
| `admin@example.com` | `AdminPass123!` | Can inspect all sources and runs |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "auth",
        "description": "Register, login, refresh rotation, and logout. Login is a form, not JSON.",
    },
    {
        "name": "users",
        "description": "Platform accounts. Listing every user requires the admin role.",
    },
    {
        "name": "sources",
        "description": "Mock upstream registrations and pause toggles.",
    },
    {
        "name": "aggregates",
        "description": "Multi-upstream plans, publish workflow, parallel runs, and history.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()

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

    @application.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @application.get("/", tags=["meta"], summary="Welcome")
    def root() -> dict[str, str]:
        return {"message": f"{settings.app_name} — see /docs for OpenAPI"}

    application.include_router(api_router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
