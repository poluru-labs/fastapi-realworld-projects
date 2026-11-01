from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**Uptime monitor** API for intermediate FastAPI practice: JWT-owned **monitors**,
on-demand **probes**, check **history**, and optional **public status pages**.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Monitors
- Register a `target_url` and expected HTTP status (default 200).
- Probes use a **mock client** — URLs containing `down`/`fail` simulate outages;
  `slow`/`degraded` mark latency issues. No real outbound HTTP.
- **Pause** with `POST /monitors/{slug}/pause` — manual checks return **409** while paused.

### Checks
1. `POST /api/v1/monitors/{slug}/checks` — run a probe now (async service + stored result).
2. `GET /api/v1/monitors/{slug}/checks` — newest-first history (`up`, `down`, `degraded`).

### Public status
`GET /api/v1/status/{slug}` requires `is_public=true` on the monitor. Private slugs → **404**.

### Seed (demo owner)
| Slug | Status | Public page |
|------|--------|-------------|
| `api-gateway` | up | yes |
| `billing-service` | down | no |
| `docs-site` | degraded | yes |

Sign in: `demo@example.com` / `DemoPass123!`
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
        "name": "monitors",
        "description": "CRUD, pause/resume, manual probes, and check history.",
    },
    {
        "name": "status",
        "description": "Anonymous status pages for public monitors.",
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
