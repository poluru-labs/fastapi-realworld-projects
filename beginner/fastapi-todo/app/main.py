from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A small todo list for learning FastAPI. Tasks live in memory and reset when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/todos` — list tasks. Filter with `completed` and `priority`.
2. `POST /api/v1/todos` — add a task.
3. `PATCH /api/v1/todos/{id}` — change only the fields you send.
4. `POST /api/v1/todos/{id}/complete` or `/reopen` — flip finished on or off.
5. `DELETE /api/v1/todos/{id}` — remove a task.

### Rules
- **Title** is required, 1–120 characters after leading and trailing spaces are removed.
- **Notes** are optional, at most 500 characters.
- **Priority** is `low`, `medium`, or `high`. New tasks default to `medium`.
- **Completed** defaults to false. Completing a finished task, or reopening an open one, is a no-op.
- Missing ids return `404` with `{"detail": "Todo {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "todos",
        "description": "Create, list, update, complete, reopen, and delete tasks.",
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
