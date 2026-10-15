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
**Webhook delivery** API with JWT auth, subscriber endpoints, signed outbound HTTP POSTs,
delivery attempt history, and safe retries.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Endpoints (subscriptions)
- Register a target URL and receive a **signing secret** once.
- Filter by `event_types`, or use `["*"]` to receive every event you publish.
- Enable/disable without deleting configuration.

### Events (publisher)
- `POST /webhook-events` stores the event and **fans out** to matching endpoints.
- Each attempt records HTTP status, duration, and errors.
- **Idempotency-Key** prevents duplicate events (and duplicate fan-out) on retries.

### Signatures
Outbound requests include:
- `X-Webhook-Timestamp`
- `X-Webhook-Signature: sha256=<hmac>` over `{timestamp}.{body}`

Verify on your server with the secret from endpoint creation.

### Local testing
Point an endpoint at `POST /api/v1/dev/capture` — an in-memory sink for demos.

### Seed data
Login as `admin@example.com` / `AdminPass123!`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness does not touch the database. Readiness runs SELECT 1.",
    },
    {"name": "auth", "description": "Register, login, refresh rotation, and logout."},
    {"name": "webhook-endpoints", "description": "Subscriber URLs, secrets, and filters."},
    {"name": "webhook-events", "description": "Publish events and inspect delivery fan-out."},
    {"name": "webhook-deliveries", "description": "Retry failed HTTP delivery attempts."},
    {
        "name": "dev",
        "description": "Capture sink for local development and automated tests.",
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
        client = getattr(application.state, "webhook_http_client", None)
        if client is not None:
            await client.aclose()
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
