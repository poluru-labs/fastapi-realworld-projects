from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**Report generator** API for intermediate FastAPI practice: JWT auth, owned **templates**,
admin **metrics catalog**, and synchronous **report runs** that aggregate seed data into JSON
sections.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Templates
- Each user creates templates with a **kind**: `sales_summary` or `activity_ledger`.
- You can read templates you own. Platform **admin** can list everyone's templates.
- Editing or deleting someone else's template returns **404** (not **403**).

### Generate
1. `POST /api/v1/reports/runs` with `template_id`, `period_start`, `period_end`.
2. The service filters metrics in the closed interval and builds sections.
3. `sales_summary` — totals grouped by **category** with a grand total.
4. `activity_ledger` — chronological rows with label and amount.

### Runs
- `GET /api/v1/reports/runs` — your history, newest first.
- `GET /api/v1/reports/runs/{id}` — full result JSON; other users' ids → **404**.

### Metrics catalog
`GET /api/v1/reports/metrics` is **admin only** — inspect raw rows that feed generation.

### Seed
| Account | Password | Notes |
|---------|----------|--------|
| `admin@example.com` | `AdminPass123!` | Template id `1`, metrics catalog |
| `demo@example.com` | `DemoPass123!` | Sample user |

Five metric rows span Jan–Mar 2026 for Q1-style reports.
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
        "name": "templates",
        "description": "Report definitions owned per user (admin can list all).",
    },
    {
        "name": "reports",
        "description": "Generate runs, list results, and admin metrics catalog.",
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
