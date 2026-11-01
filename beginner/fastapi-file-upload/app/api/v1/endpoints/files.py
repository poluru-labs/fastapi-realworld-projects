from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response

from app.api.deps import get_file_service
from app.schemas.file import FileRead, FileUpdate
from app.services.file_service import FileService

router = APIRouter()


@router.get(
    "",
    response_model=list[FileRead],
    summary="List uploaded files",
    description="Sorted by newest first. Filter with `content_type` substring or search `q`.",
)
def list_files(
    service: Annotated[FileService, Depends(get_file_service)],
    content_type: Annotated[str | None, Query(max_length=120)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[FileRead]:
    return service.list_files(content_type=content_type, q=q)


@router.post(
    "",
    response_model=FileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Multipart form with `file` and optional `description`.",
    responses={413: {"description": "File exceeds MAX_UPLOAD_BYTES."}},
)
async def upload_file(
    service: Annotated[FileService, Depends(get_file_service)],
    file: Annotated[UploadFile, File(description="Binary file to store in memory")],
    description: Annotated[str, Form()] = "",
) -> FileRead:
    content = await file.read()
    return await service.upload_file(
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
        description=description.strip(),
    )


@router.get(
    "/{file_id}",
    response_model=FileRead,
    summary="Get file metadata",
)
def get_file(
    file_id: int,
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileRead:
    return service.get_file(file_id)


@router.get(
    "/{file_id}/content",
    summary="Download file bytes",
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def download_file(
    file_id: int,
    service: Annotated[FileService, Depends(get_file_service)],
) -> Response:
    content, content_type, filename = service.get_content(file_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=content_type, headers=headers)


@router.patch(
    "/{file_id}",
    response_model=FileRead,
    summary="Update file description",
)
def update_file(
    file_id: int,
    payload: FileUpdate,
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileRead:
    return service.update_file(file_id, payload)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
)
def delete_file(
    file_id: int,
    service: Annotated[FileService, Depends(get_file_service)],
) -> None:
    service.delete_file(file_id)
