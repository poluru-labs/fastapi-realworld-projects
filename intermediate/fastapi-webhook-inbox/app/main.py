from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**Webhook inbox** API for intermediate FastAPI practice: JWT auth, owned **endpoints**,
public **ingest** with shared secrets, and an inbox to **ack** deliveries.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Endpoints
- Each user provisions slugs that receive third-party callbacks.
- Provisioning returns a one-time **webhook_token** (send as `X-Webhook-Token`).
- You can read endpoints you own. Platform **admin** lists all endpoints.
- Editing or deleting someone else's endpoint returns **404** (not **403**).

### Ingest (senders)
1. `POST /api/v1/hooks/{slug}/deliveries` with JSON body, **X-Webhook-Token**, and
   **Idempotency-Key**.
2. Deliveries land as **pending** in the owner's inbox.
3. Paused endpoints reject ingest with **409**. Bad slug/token → **404**.

### Inbox
- `GET /api/v1/deliveries` — filter by endpoint slug and status.
- `POST /api/v1/deliveries/{id}/ack` — mark processed (**409** if already acked).

### Seed
| Account | Password | Endpoint | Token |
|---------|----------|----------|--------|
| `admin@example.com` | `AdminPass123!` | `billing-stripe` | `seed-webhook-billing-stripe` |
| `demo@example.com` | `DemoPass123!` | `crm-sync` (paused) | `seed-webhook-crm-sync` |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "auth",
        "description": "Register, login, refresh rotation, and logout. Login is a form, not JSON.",
    },
    {
        "name": "users",
        "description": "Platform accounts. Listing every user requires the admin role.",
    },
    {
        "name": "endpoints",
        "description": "Webhook endpoint CRUD and per-endpoint inbox listing.",
    },
    {
        "name": "deliveries",
        "description": "Cross-endpoint inbox queries and acknowledge.",
    },
    {
        "name": "hooks",
        "description": "Public ingest routes for external senders.",
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
