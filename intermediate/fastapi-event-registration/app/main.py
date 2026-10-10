from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Event registration API with JWT auth. Events, registrations, and users live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can see an event
- **Published** events are public. No token required.
- **Draft** and **cancelled** events are visible to a platform admin only.
  Everyone else gets **404**, so a hidden event looks missing.
- A missing `Authorization` header is anonymous. A bad token is **401**.

### Registrations
- Any signed-in user registers for a **published** event with `POST /api/v1/registrations`.
- When `registered_count` reaches **capacity**, new sign-ups become **waitlisted**.
- Cancelling a **registered** seat promotes the oldest waitlisted attendee.
- Another user's registration id returns **404**, not **403**.

### Event status (admin)
`draft` → `published` → `cancelled`, and `published` → `draft` only when no active
registrations exist.
Cancelling an event cancels every active registration.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Published: `fastapi-meetup` (capacity 2; admin already registered). Draft: `draft-planning-session`.
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
        "name": "events",
        "description": (
            "Events addressed by slug. The public list is published-only. "
            "Status changes are separate routes so the legal move is obvious in /docs."
        ),
    },
    {
        "name": "registrations",
        "description": "Attendee sign-ups, waitlist promotion, and self-service cancel.",
    },
    {
        "name": "tags",
        "description": "Tags that appear on at least one published event, with counts.",
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
