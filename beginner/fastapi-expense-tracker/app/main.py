from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **expense tracker** for learning FastAPI. Expenses live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/expenses` — browse the ledger. Filter by category, dates, amounts, and more.
2. `GET /api/v1/expenses/summary` — totals and per-category breakdown for a date range.
3. `GET /api/v1/expenses/categories` — distinct category labels.
4. `POST /api/v1/expenses` — record a purchase (`amount_cents` is always in cents).
5. `PATCH /api/v1/expenses/{id}` — change only the fields you send.
6. `POST /api/v1/expenses/{id}/flag` or `/unflag` — mark rows that need review.
7. `DELETE /api/v1/expenses/{id}` — remove a row.

### Rules
- **merchant** is required (1–120 characters after trim).
- **amount_cents** must be a positive integer (store dollars as cents, e.g. $4.50 → 450).
- **spent_on** is a calendar date (`YYYY-MM-DD`).
- **payment_method** is `card`, `cash`, or `transfer` (default `card`).
- **receipt_ref** is optional and must be unique when set.
- Duplicate receipt reference on create or patch returns **409**.
- Missing ids return **404** with `{"detail": "Expense {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "expenses",
        "description": "Expense CRUD, categories, summary totals, and review flags.",
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
