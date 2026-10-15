from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**Learning platform** API with JWT auth, course catalog, lessons, enrollments, and progress.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Catalog
- **Published** courses are public on `GET /api/v1/courses`.
- Draft or archived courses return **404** to guests (admins can preview drafts).
- Lesson titles are visible in the catalog; **lesson body** unlocks after enrollment.

### Enrollments
- Students enroll in **published** courses only.
- Mark lessons complete; progress is `completed_lessons / total_lessons`.
- Finishing every published lesson sets status to **completed**.
- Another student's enrollment id returns **404**, not **403**.

### Seed data
Login as `admin@example.com` / `AdminPass123!`.
Published course: `fastapi-fundamentals`. Draft: `draft-async-deep-dive`.
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
        "name": "courses",
        "description": "Course catalog, lessons, and admin publish workflow.",
    },
    {
        "name": "enrollments",
        "description": "Enroll, track progress, complete lessons, or drop.",
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
