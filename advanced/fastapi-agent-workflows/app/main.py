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
**Agent workflow orchestration** API for advanced FastAPI practice: define ordered **agent** and
**tool** steps, publish definitions, execute runs with **runner** authentication, and inspect
append-only **step logs**.

This complements `fastapi-workflow-engine` (state machines). Here the focus is LLM-agent-shaped
pipelines — prompt templates, tool stubs, and shared run **context** — not FSM transitions.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Keys
- **X-Admin-Key** — create/update/publish workflow definitions, list runs.
- **X-Runner-Key** — start executions (`POST /agent-runs`).
- **Idempotency-Key** — required on run start; retries return the stored run.

### Step types
| Type | Behavior in this sample |
|------|-------------------------|
| `agent` | Formats `prompt_template` with run input + context; returns mock `agent:…` text |
| `tool` | Calls mock tools (`search`, `calculator`, or echo) using prior step output |

Each step writes `{step_key}_output` into the run context for downstream templates.

### Lifecycle
1. Admin `POST /agent-workflows` — draft definition with validated steps JSON.
2. Admin `POST /agent-workflows/{slug}/publish` — runners may execute.
3. Runner `POST /agent-runs` — synchronous execution + persisted step logs.
4. Runner or admin `GET /agent-runs/{id}` — debug agent traces.

### Seed
Published workflow **`research-assistant`**: plan → search tool → summarize (ready to run with
`{"goal": "…"}` input).

### Production notes
Runs execute inline in the API process. Real systems enqueue runs, stream tokens, retry tools,
and version definitions. Swap `app/core/agent_runner.py` for your orchestrator.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {
        "name": "workflows",
        "description": "Admin CRUD + publish for agent step definitions.",
    },
    {
        "name": "runs",
        "description": "Runner execution with idempotency and step logs.",
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
