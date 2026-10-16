from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **bookmarks** API for learning FastAPI. Saved links live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/bookmarks` — browse active bookmarks (pinned first, then by title).
2. `GET /api/v1/bookmarks/tags` — distinct tags across all bookmarks.
3. `POST /api/v1/bookmarks` — save a URL with optional tags, note, and pin flag.
4. `PATCH /api/v1/bookmarks/{id}` — partial update; send only fields you want to change.
5. `POST .../pin` or `.../unpin` — float important links to the top of the list.
6. `POST .../archive` or `.../unarchive` — hide links without deleting them.
7. `DELETE /api/v1/bookmarks/{id}` — remove permanently.

### Rules
- **Unique URLs** — trailing slashes and letter casing are normalized; duplicates return **409**.
- **Archived** bookmarks are excluded from the default list; pass `archived=true` to list them.
- Missing ids return **404** with `{"detail": "Bookmark {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "bookmarks",
        "description": "Save links, tags, pin/archive workflow, and search filters.",
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
