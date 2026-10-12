from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A personal **recipe box** for learning FastAPI. Recipes live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/recipes` — browse the box. Filter with `cuisine`, `search`, `featured`,
   `difficulty`, `vegetarian`, and `max_total_minutes`.
2. `GET /api/v1/recipes/cuisines` — distinct cuisine labels for filters.
3. `POST /api/v1/recipes` — add a recipe.
4. `PATCH /api/v1/recipes/{id}` — change only the fields you send.
5. `POST /api/v1/recipes/{id}/feature` or `/unfeature` — sort helpers for the home page.
6. `DELETE /api/v1/recipes/{id}` — remove a recipe.

### Rules
- **title** and **chef** are required (1–200 and 1–120 characters after trim).
- **source_url** is optional. When set, it must be unique (trailing slashes ignored).
- **cuisine** defaults to `General`. **servings** defaults to 4.
- **difficulty** is `easy`, `medium`, or `hard` (default `easy`).
- **total_minutes** in responses is prep + cook when both are set.
- Duplicate source URL on create or patch returns **409**.
- Missing ids return **404** with `{"detail": "Recipe {id} not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "recipes",
        "description": "Recipe CRUD, cuisine list, search filters, and featured helpers.",
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
