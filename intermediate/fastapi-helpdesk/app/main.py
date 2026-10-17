from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A **help desk** API for intermediate FastAPI practice. Support tickets and replies live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can see a ticket
- **Requester**, **assignee**, and **platform admin** can read the ticket and replies.
- Everyone else gets **404**, not **403**, so ticket ids do not leak across customers.
- There is no anonymous access; send a valid Bearer token.

### Workflow
`draft` → `submit` → `open` → `start` → `in_progress` → `resolve` → `resolved` → `close` → `closed`.
Use `reopen` to move `closed` back to `open`.

### Replies
- Allowed on **open**, **in_progress**, and **resolved** tickets.
- **Draft** and **closed** tickets return **409** when you try to reply.

### Admin queue
- `GET /api/v1/tickets` lists the support queue (admin only, drafts excluded).
- Admins assign agents with `PATCH` and `assignee_id`.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Open ticket: `cannot-reset-password`. Draft: `draft-vpn-request`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "auth",
        "description": "Register, login, refresh rotation, and logout. Login uses form fields.",
    },
    {"name": "users", "description": "Platform accounts. Listing all users requires admin."},
    {
        "name": "tickets",
        "description": "Support tickets by slug, queue filters, and status routes.",
    },
    {
        "name": "replies",
        "description": "Conversation thread on a ticket.",
    },
    {
        "name": "categories",
        "description": "Tag counts across submitted (non-draft) tickets.",
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
