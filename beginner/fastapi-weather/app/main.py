from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A beginner **weather** API with in-memory locations, **current conditions**, and **forecasts**
(no external provider — ideal for learning FastAPI patterns).

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Locations
1. `GET /api/v1/locations` — list tracked cities; filter with search `q`.
2. `POST /api/v1/locations` — add a city (`country_code` is ISO 3166-1 alpha-2, e.g. `US`).
3. Duplicate city + country returns **409**.

### Current weather
1. `GET /api/v1/locations/{id}/current` — temperature, humidity, wind, and condition.
2. `PATCH /api/v1/locations/{id}/current` — simulate a refresh; updates `observed_at`.

### Forecast
`GET /api/v1/locations/{id}/forecast` — multi-day highs, lows, and precipitation chance.

### Seed data
| Id | City | Country | Sample condition |
|----|------|---------|------------------|
| `1` | San Francisco | US | Partly cloudy |
| `2` | London | GB | Overcast |
| `3` | Tokyo | JP | Clear |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "weather",
        "description": "Locations, live-style current readings, and short-range forecasts.",
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
