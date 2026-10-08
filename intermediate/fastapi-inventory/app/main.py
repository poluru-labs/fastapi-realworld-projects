from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Team task board with JWT auth. Users, teams, and tasks live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Two different roles
- **Platform role** (`user` or `admin`) comes from the account.
  Admins can see and change every team.
- **Team role** (`owner` or `member`) exists only inside one team.
  The creator is the owner.

A route that says "member" means team membership. Platform admin bypasses that check.

### Task status
`todo` → `in_progress` → `done`. `done` can return to `in_progress`.
`todo` cannot jump straight to `done`.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`. Team `Platform` (id 1) has one todo task.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {"name": "auth", "description": "Register, login, refresh rotation, and logout."},
    {"name": "users", "description": "Platform accounts. Listing every user requires admin."},
    {
        "name": "teams",
        "description": "Teams and membership. Owner and platform admin manage the roster.",
    },
    {
        "name": "tasks",
        "description": "Work items on a team. Status changes follow the allowed transitions.",
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
