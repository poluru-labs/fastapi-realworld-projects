from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A **job board** API with JWT auth for intermediate FastAPI practice. Job postings and applications
live in memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can see a job
- **Published** jobs are public. No token required on the board or job detail.
- **Draft** and **closed** jobs are visible to the **employer** and to a **platform admin**.
  Everyone else gets **404** so hidden listings do not leak existence.
- Missing `Authorization` means anonymous. A bad token is **401**, not a silent guest read.

### Who can change a job
- The **employer** edits, publishes, unpublishes, reopens, and deletes their postings.
- A **platform admin** can read anything, **close** a published job, and delete.
  Admins cannot rewrite someone else's description or publish their draft.

### Applications
- Candidates **apply** only to **published** jobs (not their own posting).
- **Employers** (and admins) list applications on jobs they can see.
- Applicants use `GET /api/v1/applications/mine` and may **withdraw** or delete their row.
- Duplicate active applications return **409**.

### Job status
`draft` → `published` → `closed`, and `closed` → `draft`. A draft cannot jump straight to closed.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`.
Published job: `senior-fastapi-engineer`. Draft: `draft-frontend-contract` (404 without a token).
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "auth",
        "description": (
            "Register, login, refresh rotation, and logout. Login uses form fields, not JSON."
        ),
    },
    {
        "name": "users",
        "description": "Platform accounts. Listing every user requires the admin role.",
    },
    {
        "name": "jobs",
        "description": (
            "Job postings by slug. Public list is published-only. "
            "Status changes use dedicated routes."
        ),
    },
    {
        "name": "applications",
        "description": "Apply to published jobs; employers review applicants on their postings.",
    },
    {
        "name": "skills",
        "description": "Skills that appear on at least one published job, with counts.",
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
