from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Measure and reshape plain text: counts, reading time, palindromes, and simple transforms.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/options` — limits, transform modes, and the stop-word list.
2. `POST /api/v1/analyze` — counts and the most common words.
3. `POST /api/v1/transform` — lower, upper, title, reverse, or slug.

### Counting rules
- A **word** is ASCII letters or digits, with an optional apostrophe (`don't`).
- **Sentences** split on `.`, `!`, and `?`. Abbreviations such as `Dr.` count as a break.
- **Paragraphs** split on a blank line.
- **Palindromes** ignore case, spaces, and punctuation.
- **Reading time** uses 200 words per minute, rounded half-up to whole seconds.

Each request is stateless. Text is not stored.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "options",
        "description": "Limits, reading speed, transform modes, and stop words.",
    },
    {
        "name": "analyze",
        "description": "Character, word, sentence, and paragraph statistics for one text.",
    },
    {
        "name": "transform",
        "description": "Rewrite text: case, reverse, or a URL slug.",
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
