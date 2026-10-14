from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Restaurant **menu and orders** API with JWT auth. Menu items and orders live in memory and reset
on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Menu
- **Active** and **available** items are public on `GET /api/v1/menu`.
- Draft or sold-out items return **404** to guests (admins can preview drafts).
- Kitchen staff (admin) creates items, activates them, and toggles sold-out.

### Orders
- Signed-in customers **place** orders with menu slugs and quantities.
- Line prices are **snapshotted** when the order is created.
- Status flow: `placed` → `preparing` → `ready` → `completed`, or **cancelled**.
- Customers cancel only while **placed**. Kitchen advances prep and ready states.
- Another customer's order id returns **404**, not **403**.

### Seed data
Login as `admin@example.com` / `AdminPass123!`.
Menu: `classic-burger`, `fries`. Draft: `draft-seasonal-soup`.
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
        "name": "menu",
        "description": "Kitchen menu CRUD, activation, and sold-out toggles.",
    },
    {
        "name": "orders",
        "description": "Place orders and advance kitchen workflow with explicit routes.",
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
