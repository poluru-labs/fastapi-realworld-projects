from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.repositories.flag_repository import RUNTIME_TOKEN_DEMO

API_DESCRIPTION = """
**Feature flags** API for intermediate FastAPI practice: JWT-managed **flags**, percentage
**rollouts**, **allowlists**, and a **runtime evaluate** endpoint for apps.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Flag management (JWT)
- Define flags with `enabled`, `rollout_percentage` (0–100), and optional `allowlist_user_ids`.
- Keys are stable identifiers (`new-checkout`, `dark-mode`).
- Filter list results with query `environment` (`development`, `staging`, `production`).

### Evaluation order
For each request context (`user_id` + optional attributes):
1. If the flag is disabled → **false** (`reason: flag disabled`).
2. Else if `user_id` is allowlisted → **true**.
3. Else if rollout is 100% → **true**; 0% → **false**.
4. Else deterministic bucket from `sha256(flag_key:user_id)` vs percentage.

### Runtime (machines)
`POST /api/v1/runtime/evaluate` with header **`X-Runtime-Token`** evaluates flags owned by
the token's account. Unknown flags return `enabled: false` with `reason: flag not found`.

### Seed
| Account | Password | Runtime token |
|---------|----------|----------------|
| `demo@example.com` | `DemoPass123!` | `{runtime_token}` |

| Flag key | Enabled | Rollout |
|----------|---------|---------|
| `new-checkout` | yes | 50% + allowlist `u_vip_1` |
| `dark-mode` | yes | 100% |
| `beta-api` | no | — |
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
        "name": "flags",
        "description": "Create and tune feature flags (JWT).",
    },
    {
        "name": "runtime",
        "description": "Evaluate flags from backend services using X-Runtime-Token.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    description = API_DESCRIPTION.replace("{runtime_token}", RUNTIME_TOKEN_DEMO)

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
