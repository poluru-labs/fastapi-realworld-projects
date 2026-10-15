from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **habit tracker** for learning FastAPI. Habits and check-ins live in memory and reset
on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/habits` — browse habits. Filter by category, paused flag, or search text.
2. `GET /api/v1/habits/categories` — distinct category labels.
3. `POST /api/v1/habits` — create a habit with a weekly `target_days_per_week` goal.
4. `PATCH /api/v1/habits/{id}` — change only the fields you send.
5. `POST /api/v1/habits/{id}/check-ins` — log a completion for a calendar day.
6. `GET /api/v1/habits/{id}/stats` — streak and weekly progress vs your target.
7. `POST .../pause` or `.../resume` — temporarily stop check-ins without deleting.
8. `DELETE /api/v1/habits/{id}` — remove the habit and its check-ins.

### Rules
- **One check-in per habit per day** — duplicates return **409**.
- **Paused** habits reject new check-ins with **409**.
- Missing ids return **404** with `{"detail": "Habit {id} not found"}` (or CheckIn).
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "habits",
        "description": "Habit CRUD, check-ins, streak stats, pause and resume.",
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
