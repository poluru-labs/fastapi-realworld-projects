from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
E-commerce API with JWT auth. Products, carts, and orders live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can see a product
- **Active** products are public. No token required.
- **Draft** and **archived** products are visible to a platform admin only.
  Everyone else gets **404**, so a hidden listing looks missing.
- A missing `Authorization` header is anonymous. A bad token is **401**.

### Cart and checkout
- Only signed-in users have a cart (`GET /api/v1/cart`).
- Cart lines reference **active** products with available **stock**.
- **Checkout** (`POST /api/v1/orders`) decrements stock, snapshots prices, and clears the cart.
- Another user's order id returns **404**, not **403**.

### Product status (admin)
`draft` → `active` → `archived`, and `archived` → `draft`.
Active products can return to draft without cancelling past orders.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Active product: `usb-c-hub` (stock 10). Draft: `draft-wireless-mouse`.
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
            "Catalog items addressed by slug. The public list is active-only. "
            "Status changes are separate routes so the legal move is obvious in /docs."
        ),
    },
    {
        "name": "cart",
        "description": "Per-user shopping cart with stock-aware line updates.",
    },
    {
        "name": "orders",
        "description": "Checkout from cart, order history, cancel with stock restock.",
    },
    {
        "name": "tags",
        "description": "Tags that appear on at least one active product, with counts.",
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
