from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **file upload** API for learning FastAPI. Files live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Upload
1. `POST /api/v1/files` — multipart form with `file` and optional `description`.
2. Size is limited by `MAX_UPLOAD_BYTES` (default 5 MiB). Oversize uploads return **413**.

### Download and manage
1. `GET /api/v1/files/{id}/content` — raw bytes with `Content-Disposition`.
2. `PATCH /api/v1/files/{id}` — update description only (content is immutable).
3. `DELETE /api/v1/files/{id}` — remove metadata and bytes.

### List and filter
`GET /api/v1/files` supports `content_type` substring and search `q` in filename or description.

### Seed data
| Id | Filename | Type |
|----|----------|------|
| `1` | welcome.txt | text/plain |
| `2` | notes.md | text/markdown |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "files",
        "description": "Multipart upload, metadata, download, and delete.",
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
