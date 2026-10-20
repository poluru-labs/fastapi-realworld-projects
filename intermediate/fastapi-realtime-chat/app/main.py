from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Realtime chat API with JWT auth. Rooms, memberships, and messages live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### REST + WebSocket
- **REST** creates rooms, joins public channels, loads history (`after_sequence`),
  and sends messages.
- **WebSocket** `/api/v1/ws/rooms/{slug}?access_token=...` pushes new messages
  to connected members. Browsers pass the JWT in the query string because they
  cannot set `Authorization` on the handshake.

### Privacy
- **Public** rooms appear in discovery and accept `POST .../join`.
- **Private** rooms return **404** to non-members (metadata and messages).
- **Archived** rooms reject new sends with **409**.

### Sequences
Each room keeps a monotonic **message_sequence**. History uses `after_sequence` for cursor sync;
members can persist **read cursors** per room.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Public room `general` (sequence 1 welcome message). Private room `team-leads` (admin only).
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
        "name": "rooms",
        "description": "Discover, create, join, invite, archive, and read cursors.",
    },
    {
        "name": "messages",
        "description": "Cursor-based history and sends that broadcast over WebSockets.",
    },
    {
        "name": "realtime",
        "description": "WebSocket endpoints (documented here; try them with wscat or your client).",
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
