from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import PlainTextResponse

from app.api.deps import get_csv_import_service, get_current_user
from app.schemas.import_job import ImportJobPage, ImportJobRead
from app.schemas.user import UserRead
from app.services.csv_import_service import CsvImportService

router = APIRouter()

_IMPORT_DESCRIPTION = """
Upload a UTF-8 CSV file to bulk-create **draft** posts for the signed-in user.

### Header row (required columns)
- **title** — post title (1–120 characters)
- **body** — main content (1–20,000 characters)

### Optional columns
- **summary** — short blurb for list views (defaults to empty)
- **tags** — pipe-separated list, e.g. `fastapi|csv|docs` (same rules as JSON create)
- **slug** — explicit slug; omit to derive from title
- **publish** — `true`, `1`, `yes`, or `y` to publish immediately after create

Blank data rows are skipped. Each bad row is recorded in `errors`; good rows still import.

Use **dry_run=true** to validate the file without writing posts. The response shape is the same.

Download a starter file from **GET /api/v1/imports/template** and try it here in Swagger
(`Choose File` on the `file` field).
"""


@router.get(
    "/template",
    response_class=PlainTextResponse,
    summary="Download CSV template",
    description=(
        "Returns an example CSV with the expected header and two sample rows. "
        "Save it, edit the rows, then POST to `/imports/posts`."
    ),
    responses={
        200: {
            "content": {"text/csv": {"example": "title,summary,body,tags,slug,publish\n..."}},
        }
    },
)
def download_csv_template(
    service: Annotated[CsvImportService, Depends(get_csv_import_service)],
) -> PlainTextResponse:
    return PlainTextResponse(
        content=service.template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="posts-import-template.csv"'},
    )


@router.get(
    "",
    response_model=ImportJobPage,
    summary="List your import jobs",
    description="Newest first. Only jobs you started appear here.",
)
def list_import_jobs(
    service: Annotated[CsvImportService, Depends(get_csv_import_service)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ImportJobPage:
    return service.list_jobs(current_user, limit=limit, offset=offset)


@router.get(
    "/{job_id}",
    response_model=ImportJobRead,
    summary="Get one import job",
    description="Includes per-row errors so you can fix the CSV and upload again.",
    responses={404: {"description": "Unknown job id or another user's job"}},
)
def get_import_job(
    job_id: str,
    service: Annotated[CsvImportService, Depends(get_csv_import_service)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ImportJobRead:
    return service.get_job(current_user, job_id)


@router.post(
    "/posts",
    response_model=ImportJobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Import posts from CSV",
    description=_IMPORT_DESCRIPTION,
    responses={
        400: {"description": "Missing columns, empty file, or file too large"},
        401: {"description": "Bearer access token required"},
    },
)
async def import_posts_from_csv(
    service: Annotated[CsvImportService, Depends(get_csv_import_service)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
    file: Annotated[
        UploadFile,
        File(description="UTF-8 CSV with a header row. Use the template endpoint for a sample."),
    ],
    dry_run: Annotated[
        bool,
        Query(
            description="Parse and validate only; do not create or publish posts.",
        ),
    ] = False,
) -> ImportJobRead:
    content = await file.read()
    filename = file.filename or "upload.csv"
    return service.import_posts(
        current_user,
        filename=filename,
        content=content,
        dry_run=dry_run,
    )
