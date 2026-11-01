from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A beginner **image metadata** API: upload images, extract **width**, **height**,
and **format** with Pillow, and manage captions and tags in memory (data resets on restart).

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Upload
1. `POST /api/v1/images` — multipart form with `file`, optional `caption`,
   and optional comma-separated `tags`.
2. Supported formats: **JPEG**, **PNG**, **WEBP**, **GIF**. Other files return **400**.
3. Size is limited by `MAX_UPLOAD_BYTES` (default 5 MiB). Oversize uploads return **413**.

### Metadata and download
1. `GET /api/v1/images/{id}` — stored dimensions, format, caption, and tags.
2. `GET /api/v1/images/{id}/content` — raw image bytes (`Content-Disposition: inline`).
3. `PATCH /api/v1/images/{id}` — update caption and/or tags (pixels and format are immutable).

### List and filter
`GET /api/v1/images` supports `format`, `min_width`, `min_height`, and search `q`
on filename, caption, or tags.

### Seed data
| Id | Filename | Format | Size |
|----|----------|--------|------|
| `1` | hero.jpg | JPEG | 1280×720 |
| `2` | icon.png | PNG | 64×64 |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "images",
        "description": "Upload images, read extracted metadata, download bytes, and manage tags.",
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
