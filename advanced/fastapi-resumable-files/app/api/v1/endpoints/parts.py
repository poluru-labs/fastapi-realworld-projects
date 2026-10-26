from typing import Annotated

from fastapi import APIRouter, Path, Request, status

from app.api.deps import DbSession, IdempotencyKey, PartIndex, UploadToken
from app.schemas.uploads import UPLOAD_KEY_PATTERN, PartRead
from app.services.upload_service import UploadService

router = APIRouter()

UploadKey = Annotated[
    str,
    Path(pattern=UPLOAD_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.post(
    "",
    response_model=PartRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload one part",
    description=(
        "Send raw bytes in the body. Headers: **X-Upload-Token**, **Idempotency-Key**, "
        "**X-Part-Index**. Part size must match the session chunk layout."
    ),
    responses={409: {"description": "Wrong size, duplicate index, or closed session."}},
)
async def upload_part(
    request: Request,
    session: DbSession,
    upload_key: UploadKey,
    token: UploadToken,
    idempotency_key: IdempotencyKey,
    part_index: PartIndex,
) -> PartRead:
    data = await request.body()
    return await UploadService(session).upload_part(
        upload_key,
        token,
        idempotency_key,
        part_index,
        data,
    )
