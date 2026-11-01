from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response

from app.api.deps import get_image_service
from app.schemas.image import ImageRead, ImageUpdate
from app.services.image_service import ImageService

router = APIRouter()


def _parse_tags(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


@router.get(
    "",
    response_model=list[ImageRead],
    summary="List image metadata",
    description=(
        "Newest first. Filter by `format`, minimum `min_width` / `min_height`, "
        "or search `q` across filename, caption, and tags."
    ),
)
def list_images(
    service: Annotated[ImageService, Depends(get_image_service)],
    image_format: Annotated[
        str | None,
        Query(alias="format", max_length=20, description="Exact format, e.g. JPEG or PNG"),
    ] = None,
    min_width: Annotated[int | None, Query(ge=1)] = None,
    min_height: Annotated[int | None, Query(ge=1)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[ImageRead]:
    return service.list_images(
        image_format=image_format,
        min_width=min_width,
        min_height=min_height,
        q=q,
    )


@router.post(
    "",
    response_model=ImageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image",
    description=(
        "Multipart form with `file`, optional `caption`, and optional comma-separated `tags`. "
        "Width, height, and format are extracted with Pillow."
    ),
    responses={
        400: {"description": "Not an image or unsupported format."},
        413: {"description": "File exceeds MAX_UPLOAD_BYTES."},
    },
)
async def upload_image(
    service: Annotated[ImageService, Depends(get_image_service)],
    file: Annotated[UploadFile, File(description="JPEG, PNG, WEBP, or GIF")],
    caption: Annotated[str, Form()] = "",
    tags: Annotated[str, Form(description="Comma-separated labels, e.g. hero,banner")] = "",
) -> ImageRead:
    content = await file.read()
    return await service.upload_image(
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
        caption=caption.strip(),
        tags=_parse_tags(tags),
    )


@router.get(
    "/{image_id}",
    response_model=ImageRead,
    summary="Get image metadata",
)
def get_image(
    image_id: int,
    service: Annotated[ImageService, Depends(get_image_service)],
) -> ImageRead:
    return service.get_image(image_id)


@router.get(
    "/{image_id}/content",
    summary="Download image bytes",
    responses={200: {"content": {"image/*": {}}}},
)
def download_image(
    image_id: int,
    service: Annotated[ImageService, Depends(get_image_service)],
) -> Response:
    content, content_type, filename = service.get_content(image_id)
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return Response(content=content, media_type=content_type, headers=headers)


@router.patch(
    "/{image_id}",
    response_model=ImageRead,
    summary="Update caption or tags",
)
def update_image(
    image_id: int,
    payload: ImageUpdate,
    service: Annotated[ImageService, Depends(get_image_service)],
) -> ImageRead:
    return service.update_image(image_id, payload)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an image",
)
def delete_image(
    image_id: int,
    service: Annotated[ImageService, Depends(get_image_service)],
) -> None:
    service.delete_image(image_id)
