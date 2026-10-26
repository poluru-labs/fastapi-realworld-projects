from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession, UploadToken
from app.schemas.uploads import (
    UPLOAD_KEY_PATTERN,
    UploadCreate,
    UploadProvisioned,
    UploadRead,
    UploadStatusDetail,
)
from app.services.upload_service import UploadService

router = APIRouter()

UploadKey = Annotated[
    str,
    Path(pattern=UPLOAD_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[UploadRead],
    summary="List upload sessions",
    description="Admin key required.",
)
async def list_uploads(_: AdminKey, session: DbSession) -> list[UploadRead]:
    return await UploadService(session).list_uploads()


@router.post(
    "",
    response_model=UploadProvisioned,
    status_code=status.HTTP_201_CREATED,
    summary="Create a resumable upload session",
    description="Returns a one-time **upload_token** for part uploads.",
)
async def create_upload(
    _: AdminKey,
    session: DbSession,
    payload: UploadCreate,
) -> UploadProvisioned:
    return await UploadService(session).provision(payload)


@router.get(
    "/{upload_key}",
    response_model=UploadRead,
    summary="Get upload session metadata",
)
async def get_upload(_: AdminKey, session: DbSession, upload_key: UploadKey) -> UploadRead:
    return await UploadService(session).get_upload(upload_key)


@router.get(
    "/{upload_key}/status",
    response_model=UploadStatusDetail,
    summary="Resume status for clients",
    description="Requires **X-Upload-Token**. Lists missing part indexes and progress.",
)
async def upload_status(
    session: DbSession,
    upload_key: UploadKey,
    token: UploadToken,
) -> UploadStatusDetail:
    return await UploadService(session).status(upload_key, token)


@router.post(
    "/{upload_key}/abort",
    response_model=UploadRead,
    summary="Abort an upload session",
    responses={409: {"description": "Already completed or aborted."}},
)
async def abort_upload(_: AdminKey, session: DbSession, upload_key: UploadKey) -> UploadRead:
    return await UploadService(session).abort(upload_key)


@router.post(
    "/{upload_key}/complete",
    response_model=UploadStatusDetail,
    summary="Finalize upload",
    description="Requires **X-Upload-Token**. Fails with **409** if parts are missing.",
)
async def complete_upload(
    session: DbSession,
    upload_key: UploadKey,
    token: UploadToken,
) -> UploadStatusDetail:
    return await UploadService(session).complete(upload_key, token)
