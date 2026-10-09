from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A small contact book for learning FastAPI. Contacts live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/contacts` — list contacts. Filter with `favorite` and `search`.
2. `POST /api/v1/contacts` — add someone to the book.
3. `PATCH /api/v1/contacts/{id}` — change only the fields you send.
4. `POST /api/v1/contacts/{id}/favorite` or `/unfavorite` — sort helpers.
5. `DELETE /api/v1/contacts/{id}` — remove a contact.

### Rules
- **full_name** is required, 1–120 characters after leading and trailing spaces are removed.
- **email** is optional. When set, it must be valid and unique (case insensitive).
- **phone**, **company**, and **notes** are optional strings with length limits.
- **favorite** defaults to false. Favorites are listed first.
- Duplicate email on create or patch returns **409**.
- Missing ids return **404** with `{"detail": "Contact {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "contacts",
        "description": "Create, list, search, update, favorite, and delete contacts.",
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
