from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.repositories.key_repository import DEMO_SEED_API_KEY

API_DESCRIPTION = """
**API keys** service for intermediate FastAPI practice: mint and revoke keys with **scopes**,
store only **hashes**, and call protected routes with `X-Api-Key` or JWT.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Key management (JWT only)
1. `POST /api/v1/keys` — returns the secret **once** in `secret` (prefix stored for display).
2. `GET /api/v1/keys` — metadata only (`prefix`, scopes, revoked_at).
3. `POST /api/v1/keys/{id}/revoke` — immediate 401 for future requests.
4. `POST /api/v1/keys/{id}/rotate` — revoke old key and mint a new secret.

Secrets are hashed with `API_KEY_PEPPER` (see settings). Plaintext keys never persist.

### Scopes
| Scope | Grants |
|-------|--------|
| `projects:read` | `GET /access/projects` |
| `projects:write` | `POST /access/projects` |
| `metrics:read` | `GET /access/metrics` |

JWT access tokens **bypass** scope checks on `/access/*` (full account access).

### Machine access
- Send `X-Api-Key: sk_live_...` on `/api/v1/access/*`.
- `GET /api/v1/access/whoami` shows whether the caller used JWT or a key.
- If both `Authorization` and `X-Api-Key` are present, the **API key wins**.

### Seed
| Account | Password | Demo key (all scopes) |
|---------|----------|------------------------|
| `demo@example.com` | `DemoPass123!` | `{seed_key}` |
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
        "name": "keys",
        "description": "Create, list, revoke, and rotate hashed API keys (JWT required).",
    },
    {
        "name": "access",
        "description": "Dual-auth routes using Bearer JWT or scoped `X-Api-Key`.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    description = API_DESCRIPTION.replace("{seed_key}", DEMO_SEED_API_KEY)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=description,
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
