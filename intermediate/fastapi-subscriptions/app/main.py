from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
SaaS **subscriptions** API with JWT auth. Plans and subscriptions live in memory and reset on
restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can see a plan
- **Active** plans are public. No token required.
- **Draft** and **archived** plans are visible to a platform admin only.
  Everyone else gets **404**, so a hidden plan looks missing.
- A missing `Authorization` header is anonymous. A bad token is **401**.

### Subscriptions
- Signed-in users subscribe to an **active** plan with `POST /api/v1/subscriptions`.
- Each user may hold one **active** subscription per plan.
- Cancelling sets status to **cancelled** immediately (no payment gateway in this demo).
- Another user's subscription id returns **404**, not **403**.

### Plan status (admin)
`draft` → `active` → `archived`, and `active` → `draft` only when no active subscriptions remain.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Active plans: `starter-monthly`, `pro-yearly`. Draft: `draft-internal`.
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
        "name": "plans",
        "description": (
            "Billing plans addressed by slug. The public list is active-only. "
            "Lifecycle routes make legal status changes obvious in /docs."
        ),
    },
    {
        "name": "subscriptions",
        "description": "Customer subscribe and cancel with billing period metadata.",
    },
    {
        "name": "tags",
        "description": "Tags that appear on at least one active plan, with counts.",
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
