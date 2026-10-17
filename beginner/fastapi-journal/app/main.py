from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **journal** API for learning FastAPI. Entries live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/entries` — browse entries (starred first, then by date).
2. `GET /api/v1/entries/tags` — distinct tags used across entries.
3. `GET /api/v1/entries/by-date/{YYYY-MM-DD}` — lookup a single calendar day.
4. `POST /api/v1/entries` — write an entry with optional mood and tags.
5. `PATCH /api/v1/entries/{id}` — partial update (date is fixed after create).
6. `POST .../star` or `.../unstar` — highlight important days.
7. `DELETE /api/v1/entries/{id}` — remove permanently.

### Rules
- **One entry per calendar day** — duplicate `entry_date` returns **409**.
- **Mood** is optional: `great`, `good`, `okay`, `low`, or `rough`.
- Missing ids return **404** with `{"detail": "Entry {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "entries",
        "description": "Daily journal entries, moods, tags, and filters.",
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
