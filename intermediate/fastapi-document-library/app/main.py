from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**Document library** API for intermediate FastAPI practice: JWT auth, **folders**, nested
**documents**, publish workflow, and immutable **revisions** on each publish.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Visibility
- **Published** documents are public (`GET` without a token).
- **Draft** and **archived** documents return **404** to everyone except the author and admins.
- That 404 (not **403**) avoids leaking whether a hidden slug exists.

### Folders
- Authors organize documents under `/api/v1/folders/{folder_slug}/documents`.
- Document slugs are unique **per folder**, not globally.
- Folder listing requires JWT; folder metadata is public when it contains published docs.

### Workflow
`draft` → `published` → `archived`, with explicit routes such as `/publish` and `/archive`.
Publishing bumps `version` and appends a revision snapshot.

### Public discovery
- `GET /api/v1/library/documents` — search all published docs (`q`, `tag`, `folder_slug`).
- `GET /api/v1/library/tags` — tag counts from published docs only.

### Seed (demo author)
| Account | Password | Folder | Published doc |
|---------|----------|--------|----------------|
| `demo@example.com` | `DemoPass123!` | `product-docs` | `getting-started` |
| | | `engineering` | `api-standards` |
| Draft (404 without token) | | `product-docs` | `roadmap-draft` |
| `admin@example.com` | `AdminPass123!` | Platform admin | |
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
        "name": "library",
        "description": "Cross-folder search and tag index for published documents.",
    },
    {
        "name": "folders",
        "description": "Owned collections that group documents.",
    },
    {
        "name": "documents",
        "description": "Nested CRUD, workflow routes, and revision history.",
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
