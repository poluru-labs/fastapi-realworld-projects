from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
Appointments API with JWT auth. Providers, bookings, and status history live in memory
and reset on restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Who can do what
- **Clients** book for themselves, list and read their appointments, reschedule while
  scheduled, and cancel while scheduled or confirmed.
- **Platform admin** manages providers, confirms and completes visits, and sees every
  appointment.

Someone else's appointment id returns **404**, not **403**.

### Overlap
Two non-cancelled appointments on the same provider cannot overlap in time.
Cancelled slots free the window.

### Status
`scheduled` → `confirmed` → `completed`, and `scheduled` or `confirmed` → `cancelled`.
Each move has its own route so the legal transition shows up in `/docs`.

### Seed data
Sign in as `admin@example.com` / `AdminPass123!`. Providers `Dr Ada Lovelace` (id 1)
and `Dr Grace Hopper` (id 2). Two sample appointments belong to the admin user.
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
        "name": "providers",
        "description": "Clinicians or rooms clients book against. Admins manage the roster.",
    },
    {
        "name": "appointments",
        "description": "Book, list, reschedule, confirm, complete, and cancel visits.",
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
