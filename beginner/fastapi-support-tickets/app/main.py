from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **support tickets** API for learning FastAPI. Tickets and comments live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). Create bodies include **Examples**.

### File and track tickets
1. `POST /api/v1/tickets` — open a ticket with subject, requester email, and priority.
2. `PATCH /api/v1/tickets/{id}` — update details, assignee, or status.
3. `POST /api/v1/tickets/{id}/resolve` and `/close` — lifecycle shortcuts (**409** when invalid).

### Comments
1. `POST /api/v1/tickets/{id}/comments` — public or internal notes.
2. Closed tickets reject new comments with **409**.

### List and filter
`GET /api/v1/tickets` supports `status`, `priority`, and `q` in subject or description.

### Seed data
| Id | Subject | Status | Comments |
|----|---------|--------|----------|
| `1` | Login page returns 500 | open | 2 |
| `2` | Invoice total looks wrong | in_progress | 1 |
| `3` | Typo on pricing page | closed | 0 |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "tickets",
        "description": "Ticket CRUD, comments, resolve/close/reopen, and filters.",
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
