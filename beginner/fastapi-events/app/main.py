from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **community events** API for learning FastAPI. Events and registrations live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). Create bodies include **Examples**.

### Manage events
1. `POST /api/v1/events` — create a **scheduled** event (`ends_at` must be after `starts_at`).
2. `PATCH /api/v1/events/{id}` — change details or capacity.
3. `POST /api/v1/events/{id}/cancel` — stop new registrations (existing rows stay).

### Register attendees
1. `POST /api/v1/events/{id}/registrations` — name + email.
2. Duplicate email on the same event → **409**. Full capacity → **409**. Cancelled event → **409**.

### List and filter
`GET /api/v1/events` supports `status`, `starts_after`, `starts_before`, and `q` in title or
description.

### Seed data
| Id | Title | Status | Registrations |
|----|-------|--------|----------------|
| `1` | Python meetup | scheduled | 2 (cap 50) |
| `2` | Cancelled workshop | cancelled | 0 |
| `3` | Open house | scheduled | unlimited cap |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "events",
        "description": "Event CRUD, cancel, filters, and attendee registrations.",
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
