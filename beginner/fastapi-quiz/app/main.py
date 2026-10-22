from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **multiple-choice quiz** API for learning FastAPI. Quizzes, questions, and scores live
in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). Request bodies on create, add-question,
and submit include **Examples** you can run from Swagger.

### Authoring flow
1. `POST /api/v1/quizzes` — create a **draft** quiz.
2. `POST /api/v1/quizzes/{id}/questions` — 2–6 choices plus `correct_index` (zero-based).
3. `PATCH /api/v1/questions/{id}` or `DELETE` — edit only while the quiz stays a draft.
4. `POST /api/v1/quizzes/{id}/publish` — needs at least one question.

### Taking a quiz
1. `GET /api/v1/quizzes` — **published** quizzes by default (`?status=draft` for authoring).
2. `GET /api/v1/quizzes/{id}/play` — player view without the answer key.
3. `POST /api/v1/quizzes/{id}/submit` — score, percentage, and per-question feedback.

### Author vs player views
| Route | Shows `correct_index` | When |
|-------|----------------------|------|
| `GET /quizzes/{id}` | Yes | Any status (build content) |
| `GET /quizzes/{id}/play` | No | **Published** only (else **404**) |
| `POST /quizzes/{id}/submit` | In results after submit | **Published** only |

### Status workflow
`draft` → `published` → `archived`, plus unpublish (`published` → `draft`) and restore
(`archived` → `draft`). Illegal transitions return **409**.

### Errors
Missing ids → **404**. Wrong status or duplicate rules → **409**. Invalid bodies → **422**.

### Seed data
| Id | Title | Status | Notes |
|----|-------|--------|--------|
| `1` | Python basics | published | 3 questions — try `/play` then `/submit` |
| `2` | FastAPI draft | draft | Hidden from default list; `/play` returns **404** |
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
