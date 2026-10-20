from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Social feed API with JWT auth. Posts, follows, likes, and comments live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Two lists
- **Explore** (`GET /posts`) — published posts with `visibility=public` only.
- **Home feed** (`GET /feed`) — published posts from you and people you follow,
  including followers-only posts when you are allowed to read them.

### Who can read a post
- **Draft** and **archived** posts: author and platform admin. Everyone else gets **404**.
- **Published + public**: anyone (no token on single-post reads).
- **Published + followers**: author, admin, and accounts that follow the author. Others get **404**.

A missing `Authorization` header is anonymous. A bad token is **401**.

### Social edges
- **Follow** — `POST /users/{id}/follow`. No self-follows; duplicates are **409**.
- **Like** — one like per user on a published post.

### Publishing workflow
`draft` → `published` → `archived`, and `archived` → `draft`.
Unpublish returns a live post to draft.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Public post: `writing-apis-that-teach`. Draft: `draft-pagination-notes` (404 without a token).
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
        "description": "Accounts, public profiles, and follow/unfollow edges.",
    },
    {
        "name": "feed",
        "description": "Signed-in home timeline built from your follow graph.",
    },
    {
        "name": "posts",
        "description": (
            "Short-form posts by slug. Explore is public-only; "
            "drafts use the same 404 privacy as before."
        ),
    },
    {
        "name": "comments",
        "description": (
            "Thread on a post. Creating one requires a published post and a signed-in user."
        ),
    },
    {
        "name": "tags",
        "description": "Hashtags on published posts, with counts (explore-visible posts only).",
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
