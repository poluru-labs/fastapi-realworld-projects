from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **gradebook** API for learning FastAPI. Students, courses, enrollments, and grades live in
memory and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### How to use this API
1. `GET /api/v1/students` — list students; `GET .../{id}/report` averages **final** grades.
2. `GET /api/v1/courses` — list courses and manage enrollments under `.../enrollments`.
3. `POST /api/v1/courses/{id}/grades` — record a **draft** grade (student must be enrolled).
4. `GET /api/v1/grades` — filter by course, student, category; drafts hidden unless requested.
5. `PATCH /api/v1/grades/{id}` — edit **draft** scores only.
6. `POST .../finalize` or `.../reopen` — publish or revert a grade.
7. `DELETE` routes remove students or grades permanently.

### Rules
- **Unique** `student_number` and `course_code` (normalized to uppercase) → **409** on duplicate.
- **percentage** on each grade is computed from points; student report uses **final** grades only.
- **Draft** grades are excluded from the default list and from report averages.
- Missing ids return **404** with `{"detail": "… not found"}`.
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {"name": "students", "description": "Roster CRUD and final-grade report."},
    {"name": "courses", "description": "Course catalog, enrollments, and grade entry."},
    {
        "name": "grades",
        "description": "List and update grades; finalize/reopen workflow.",
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
