from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **quiz** API for learning FastAPI. Quizzes, multiple-choice questions, and scoring live in
memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Authoring
1. `POST /api/v1/quizzes` — create a **draft**.
2. `POST /api/v1/quizzes/{id}/questions` — add choices and `correct_index`.
3. `POST /api/v1/quizzes/{id}/publish` — requires at least one question.

### Taking a quiz
1. `GET /api/v1/quizzes` — lists **published** quizzes by default.
2. `GET /api/v1/quizzes/{id}/play` — prompts without the answer key.
3. `POST /api/v1/quizzes/{id}/submit` — score and per-question feedback.

### Author vs player
- `GET /api/v1/quizzes/{id}` always shows **correct_index** (for building content).
- `/play` hides answers and only works when status is **published**.

### Status workflow
`draft` → `published` → `archived`, with unpublish and restore edges like other beginner APIs.

### Seed data
Published quiz **Python basics** (id `1`, three questions). Draft **FastAPI draft** (id `2`).
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {"name": "quizzes", "description": "Create, publish, play, and submit quizzes."},
    {"name": "questions", "description": "Edit individual questions while the quiz is a draft."},
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
