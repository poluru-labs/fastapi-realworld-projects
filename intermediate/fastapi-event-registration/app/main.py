from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Blog API with JWT auth. Users, posts, and comments live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can see a post
- **Published** posts are public. No token required.
- **Draft** and **archived** posts are visible to the author and to a platform admin.
  Everyone else gets **404**, so a hidden post is indistinguishable from a missing one.
- A missing `Authorization` header is anonymous. A bad token is **401**.

### Who can change it
- The **author** edits, publishes, unpublishes, archives, restores, and deletes.
- A **platform admin** can read anything, archive a published post, and delete.
  An admin cannot rewrite someone else's words or publish their draft.

### Status
`draft` → `published` → `archived`, and `archived` → `draft`.
`published` can return to `draft`. A draft cannot jump straight to `archived`.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Published post: `writing-apis-that-teach`. Draft: `draft-pagination-notes` (404 without a token).
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
        "name": "posts",
        "description": (
            "Articles addressed by slug. The public list is published-only. "
            "Status changes are their own routes so the legal move is in the path."
        ),
    },
    {
        "name": "comments",
        "description": (
            "Notes on a post. Creating one requires a published post and a signed-in user."
        ),
    },
    {
        "name": "tags",
        "description": "Tags that appear on at least one published post, with counts.",
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
