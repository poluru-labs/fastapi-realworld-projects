from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
**Media processing** API for intermediate FastAPI practice: JWT auth, owned **assets** (metadata),
reusable **presets**, and synchronous **jobs** that simulate thumbnail, resize, transcode, and
audio-extract pipelines.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

### Assets
- Register files with mime type, kind (`image`, `video`, `audio`), and optional dimensions.
- You can read assets you own. Platform **admin** can list everyone's assets.
- Editing or deleting someone else's asset returns **404** (not **403**).

### Presets
- Save an `operation` plus JSON **parameters** for repeat jobs.
- Same ownership rules as assets.

### Submit jobs
1. `POST /api/v1/jobs` with `asset_id` and either `preset_id` **or** inline
   `operation` + `parameters`.
2. Processing runs synchronously and returns **completed** with simulated `output_uri` metadata.
3. Wrong operation for the asset kind → **409** before the job is stored.

### Jobs
- `GET /api/v1/jobs` — your history, newest first.
- `GET /api/v1/jobs/{id}` — full result; other users' ids → **404**.

### Operations catalog
`GET /api/v1/jobs/operations` is **admin only** — documents allowed kinds and parameter shapes.

### Seed
| Account | Password | Notes |
|---------|----------|--------|
| `admin@example.com` | `AdminPass123!` | Asset `hero-banner.jpg`, preset `1`, completed job `1` |
| `demo@example.com` | `DemoPass123!` | Video asset `promo-reel.mp4` |
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
        "name": "assets",
        "description": "Registered media metadata owned per user (admin can list all).",
    },
    {
        "name": "presets",
        "description": "Named operation + parameters for repeatable processing.",
    },
    {
        "name": "jobs",
        "description": "Submit simulated jobs, list results, and admin operations catalog.",
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
