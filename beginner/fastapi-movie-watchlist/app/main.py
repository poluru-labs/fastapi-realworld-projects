from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A personal **movie watchlist** for learning FastAPI. Movies live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/movies` — browse your list. Filter with `genre`, `status`, `pinned`, and
   `search`.
2. `GET /api/v1/movies/genres` — distinct genre labels for filters.
3. `POST /api/v1/movies` — add a title you want to track.
4. `PATCH /api/v1/movies/{id}` — change only the fields you send (including `status`).
5. `POST /api/v1/movies/{id}/pin` or `/unpin` — highlight what to watch next.
6. `POST /api/v1/movies/{id}/mark-watched` — shortcut to set status to **watched**.
7. `DELETE /api/v1/movies/{id}` — remove a row.

### Rules
- **title** and **director** are required (1–200 and 1–120 characters after trim).
- **imdb_id** is optional. When set, it must be unique (case insensitive).
- **status** is one of `want_to_watch`, `watching`, or `watched` (default `want_to_watch`).
- **pinned** defaults to false. Pinned movies sort to the top of the list.
- Duplicate IMDb id on create or patch returns **409**.
- Missing ids return **404** with `{"detail": "Movie {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "movies",
        "description": "Watchlist CRUD, genre list, filters, pin helpers, and mark-watched.",
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
