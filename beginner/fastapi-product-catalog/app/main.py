from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **product catalog** API for learning FastAPI. Products live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/products` — browse active products (featured first, then by name).
2. `GET /api/v1/products/categories` — distinct categories in the active catalog.
3. `GET /api/v1/products/by-sku/{sku}` — warehouse lookup (SKU is case-insensitive).
4. `POST /api/v1/products` — add a product with SKU, price, category, tags, and stock.
5. `PATCH /api/v1/products/{id}` — partial update; send only fields you want to change.
6. `POST .../feature` or `.../unfeature` — highlight products on a storefront.
7. `POST .../discontinue` or `.../restore` — hide end-of-life SKUs without deleting history.
8. `DELETE /api/v1/products/{id}` — remove permanently.

### Rules
- **Unique SKUs** — normalized to uppercase; duplicates return **409**.
- **in_stock** is derived from `stock_quantity > 0` on every response.
- **Discontinued** products are hidden by default; query with `discontinued=true` to include them.
- Missing ids or SKUs return **404** with `{"detail": "Product … not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "products",
        "description": "Catalog CRUD, SKU lookup, filters, feature and discontinue workflow.",
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
