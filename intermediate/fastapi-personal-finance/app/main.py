from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A **personal finance** API for intermediate FastAPI practice. Accounts and transactions live in
memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can see an account
- Only the **account owner** and **platform admin** can read accounts and transactions.
- Everyone else gets **404**, not **403**, so slugs do not leak across users.
- All routes require a valid Bearer token (login uses OAuth2 form fields).

### Balances
- **current_balance** = `opening_balance` plus the sum of **posted** transaction amounts.
- **Draft** and **voided** rows are ignored for balances.

### Transaction workflow
`draft` → `post` → `posted` → `void` → `voided`. Only **draft** rows can be edited or posted.
Only **posted** rows can be voided.

### Spending insight
- `GET /api/v1/spending/categories` totals **posted** expenses (negative amounts) by category.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Account `checking-main` (balance reflects posted groceries and salary; draft cafe not included).
Savings: `savings-emergency`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "auth",
        "description": "Register, login, refresh rotation, and logout. Login uses form fields.",
    },
    {"name": "users", "description": "Platform accounts. Listing all users requires admin."},
    {
        "name": "accounts",
        "description": "Checking, savings, and credit accounts with computed balances.",
    },
    {
        "name": "transactions",
        "description": "Draft, post, and void money movement on an account.",
    },
    {
        "name": "spending",
        "description": "Category totals from posted expenses.",
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
