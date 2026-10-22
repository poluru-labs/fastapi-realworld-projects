from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**In-app notifications** API for intermediate FastAPI practice: JWT auth, per-user
inboxes, read/unread state, delivery preferences, and admin **dispatch**.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Inbox rules
- Every notification belongs to exactly one user. Listing and reading require a bearer token.
- You only see **your** rows. Another user's id returns **404**, not **403**.
- `read_at` is `null` while unread. Mark-read sets a timestamp; repeating mark-read is **409**.

### Pagination
`GET /notifications` returns a page (`items`, `total`, `limit`, `offset`). Newest first.
Use `unread_only=true` for badge trays.

### Preferences
`GET/PATCH /notifications/preferences` stores demo toggles (email/push) in memory per user.

### Admin dispatch
`POST /notifications/dispatch` lets a platform admin enqueue a message for any user id.

### Seed data
| Account | Password | Inbox |
|---------|----------|--------|
| `admin@example.com` | `AdminPass123!` | 3 notifications (2 unread) |
| `demo@example.com` | `DemoPass123!` | 1 unread welcome message |
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
        "name": "notifications",
        "description": (
            "Personal inbox, unread counts, mark-read, preferences, and admin dispatch."
        ),
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
