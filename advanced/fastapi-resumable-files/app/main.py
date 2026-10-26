import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.session import make_engine, make_session_factory
from app.middleware.request_context import RequestContextMiddleware

logger = logging.getLogger(__name__)

API_DESCRIPTION = """
**Resumable file uploads** for advanced FastAPI practice: admin **sessions**, chunked **parts**
with idempotency, **status** for resume, and **complete** when every byte is present.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Sessions
- Admin creates an upload with `total_bytes` and `chunk_size_bytes`.
- Provisioning returns a one-time **upload_token** (`X-Upload-Token` on client routes).

### Parts
1. `POST /api/v1/uploads/{key}/parts` — raw body bytes per part.
2. Headers: **X-Upload-Token**, **Idempotency-Key**, **X-Part-Index** (0-based).
3. Wrong part size or duplicate index with different bytes → **409**.

### Resume
- `GET /api/v1/uploads/{key}/status` — missing part indexes and progress percent.

### Complete
- `POST /api/v1/uploads/{key}/complete` — marks **completed** when all parts exist.

### Seed
| Key | Size | Chunk | Progress | Token |
|-----|------|-------|----------|--------|
| `demo-archive` | 1000 B | 250 B | 2/4 parts | `seed-upload-demo-archive` |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness does not touch the database. Readiness runs SELECT 1.",
    },
    {
        "name": "uploads",
        "description": "Admin session CRUD, client status, complete, and abort.",
    },
    {
        "name": "parts",
        "description": "Chunked part uploads with upload token and idempotency.",
    },
]


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    application.state.engine = engine
    application.state.session_factory = make_session_factory(engine)
    logger.info("Started %s (%s)", settings.app_name, settings.environment)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

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
    application.add_middleware(RequestContextMiddleware)

    @application.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @application.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        if settings.debug:
            return JSONResponse(status_code=500, content={"detail": str(exc)})
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @application.get("/", tags=["meta"], summary="Welcome")
    def root() -> dict[str, str]:
        return {"message": f"{settings.app_name} — see /docs for OpenAPI"}

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
