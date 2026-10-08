from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Inventory API with JWT auth. Products, quantities, and movement history live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can do what
- **Any signed-in user** lists active products, reads stock levels, and records
  receive, sale, and adjust movements.
- **Platform admin** creates and updates catalog rows, deactivates SKUs, and lists
  inactive products with `include_inactive=true`.

Route dependencies prove **who you are** (`get_current_user`).
`InventoryService` applies stock and permission rules.

### Stock rules
- **receive** adds units. **sale** removes units. **adjust** uses a signed delta.
- Quantity on hand never goes below zero. Overselling returns **409**.
- Each movement appends a ledger row with `quantity_after` and the actor.
- **is_low_stock** is true when `quantity_on_hand <= reorder_level`.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
`GADGET-B` and `CABLE-C` are low stock. `CABLE-C` has zero on hand until you receive stock.
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
        "name": "products",
        "description": (
            "Catalog and stock movements. Movement routes change quantity_on_hand "
            "and append history."
        ),
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
