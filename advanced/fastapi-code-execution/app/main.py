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
**Sandboxed code execution** API for advanced FastAPI practice: async SQLAlchemy, Alembic,
policy limits, **runner** authentication, idempotent run submission, AST validation, and
timeout-bound in-process Python execution.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Keys
- **X-Runner-Key** — submit runs (`POST /execution/runs`).
- **X-Admin-Key** — read/update policy, list runs, or read any run without the runner key.
- **Idempotency-Key** — required on run submission; retries return the stored run.

### Safety (read before production use)
Runs use **restricted `exec` in a worker thread**, not OS-level sandboxes (no gVisor,
Firecracker, or WASM). Validation blocks imports and many dangerous builtins, but determined
code may still exhaust CPU until timeout. Treat this sample as **architecture education** only.

### Run statuses
| Status | Meaning |
|--------|---------|
| `completed` | Exit code 0 |
| `failed` | User code raised or non-zero exit |
| `timeout` | Exceeded `max_timeout_ms` from policy |
| `rejected` | Failed static validation before execution |

### Typical flow
1. `GET /execution/policy` — inspect limits (admin).
2. `POST /execution/runs` — submit Python source with runner + idempotency headers.
3. `GET /execution/runs/{run_id}` — fetch stdout/stderr and timing.
4. `GET /execution/runs` — audit recent submissions (admin).

### Seed
After migrate + seed: default policy (8 KiB source, 2 s timeout, `python` only) and one
completed sample run with idempotency key `seed-run-hello`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {
        "name": "policy",
        "description": "Admin-only execution limits (bytes, timeout, languages).",
    },
    {
        "name": "runs",
        "description": "Runner submit + admin audit; idempotent create.",
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
