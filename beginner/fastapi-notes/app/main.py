from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A small notes list for learning FastAPI. Notes live in memory and reset when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/notes` — list notes. Filter with `pinned` and `search`.
2. `POST /api/v1/notes` — add a note.
3. `PATCH /api/v1/notes/{id}` — change only the fields you send.
4. `POST /api/v1/notes/{id}/pin` or `/unpin` — move a note to the top or back.
5. `DELETE /api/v1/notes/{id}` — remove a note.

### Rules
- **Title** is required, 1–120 characters after leading and trailing spaces are removed.
- **Body** is optional, at most 2000 characters.
- **Pinned** defaults to false. Pinning a pinned note leaves it pinned.
  Unpinning an unpinned note leaves it unpinned.
- Pinned notes are listed first. Inside each group, smaller ids come first.
- `search` matches title or body and ignores case. A blank search is ignored.
- Missing ids return `404` with `{"detail": "Note {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "notes",
        "description": "Create, list, search, update, pin, unpin, and delete notes.",
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
