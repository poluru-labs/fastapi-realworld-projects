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
**Multitenant retrieval-augmented generation (RAG)** API for advanced FastAPI practice.

Every knowledge row carries a **`tenant_id`**. Business routes require:

1. **`Authorization: Bearer <access_token>`** — global user identity (JWT).
2. **`X-Tenant-Slug: acme-corp`** — selects the tenant partition for collections,
   documents, chunks, and queries.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Ingest pipeline
`POST /collections/{slug}/documents` accepts plain text, splits it into overlapping chunks,
computes **deterministic demo embeddings** (SHA-based vectors stored as JSON in SQL), and
persists chunks for similarity search. This teaches RAG data modeling without Pinecone or
pgvector — swap in real embedders and a vector index in production.

### Query pipeline
`POST /collections/{slug}/query` embeds the question, ranks tenant chunks with cosine
similarity, returns **citations** (document title, excerpt, score), and stitches a short
**answer** from the top excerpts. Plug an LLM between retrieval and response when ready.

### Isolation guarantees (sample)
- Repositories filter on `tenant_id` from membership-validated context.
- Cross-tenant collection slugs are independent (unique per tenant, not globally).
- Missing membership → **403**; unknown tenant → **404**.

### Seed
After migrate + seed: `demo@example.com` / `DemoPass123!`, tenant `acme-corp`, collection
`product-docs` with a refund policy document ready to query.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {
        "name": "health",
        "description": "Liveness skips the database. Readiness runs SELECT 1.",
    },
    {"name": "auth", "description": "Register a workspace or login for JWT access."},
    {"name": "tenants", "description": "Discover tenant slugs for the `X-Tenant-Slug` header."},
    {
        "name": "collections",
        "description": "Tenant-scoped knowledge bases, ingest, and RAG query.",
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
