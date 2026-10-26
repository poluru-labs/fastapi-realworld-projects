from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **URL shortener** API for learning FastAPI. Links live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). Create bodies include **Examples**.

### Create and manage links
1. `POST /api/v1/links` — shorten a URL; optional **custom_code** vanity slug.
2. `PATCH /api/v1/links/{code}` — change target, title, or deactivate.
3. Duplicate custom codes return **409**.

### Redirect
`GET /api/v1/r/{code}` returns **302** to the target and increments **click_count**.
Inactive links return **410 Gone**.

### List and filter
`GET /api/v1/links` supports `is_active` and search `q` across code, title, and URL.

### Seed data
| Code | Target | Active | Clicks |
|------|--------|--------|--------|
| `docs` | fastapi.tiangolo.com | yes | 12 |
| `github` | GitHub repo | yes | 4 |
| `old-sale` | example promo | no | 99 |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "links",
        "description": "Create, list, update, and delete short link metadata.",
    },
    {
        "name": "redirect",
        "description": "Public redirect endpoint that records clicks.",
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
