from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Convert **temperature**, **distance**, and **weight** between common units.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/units` — look up categories, codes, symbols, and aliases.
2. `POST /api/v1/convert` — send a category, a finite number, and two unit codes.

### Conversion rules
- **Temperature** pivots through Celsius:
  `°F = (°C × 9/5) + 32` and `K = °C + 273.15`.
  Values colder than absolute zero (−273.15 °C) are rejected.
- **Distance** pivots through meters. Example: 1 inch = 0.0254 m exactly.
- **Weight** pivots through grams. Example: 1 pound = 453.59237 g exactly.

Unit codes are case-insensitive. When the units differ, `result` is rounded
half-up to 6 decimal places. The same unit returns the input unchanged.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "units",
        "description": "Catalog of categories, unit codes, symbols, aliases, and scale factors.",
    },
    {
        "name": "convert",
        "description": "Convert one numeric value between two units in the same category.",
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
