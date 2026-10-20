from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.analytics import STREAM_KEY_PATTERN, StreamCreate, StreamRead, StreamUpdate
from app.services.stream_service import StreamService

router = APIRouter()

StreamKey = Annotated[
    str,
    Path(pattern=STREAM_KEY_PATTERN.pattern, min_length=1, max_length=64),
]


@router.get(
    "",
    response_model=list[StreamRead],
    summary="List event streams",
    description="Admin key required. Returns every stream and its pause state.",
)
async def list_streams(_: AdminKey, session: DbSession) -> list[StreamRead]:
    return await StreamService(session).list_streams()


@router.post(
    "",
    response_model=StreamRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stream",
    description="Admin key required. Stream keys are immutable and lowercase.",
    responses={409: {"description": "Another stream already uses this key."}},
)
async def create_stream(_: AdminKey, session: DbSession, payload: StreamCreate) -> StreamRead:
    return await StreamService(session).create_stream(payload)


@router.get(
    "/{stream_key}",
    response_model=StreamRead,
    summary="Get one stream",
    description="Admin key required.",
)
async def get_stream(_: AdminKey, session: DbSession, stream_key: StreamKey) -> StreamRead:
    return await StreamService(session).get_stream(stream_key)


@router.patch(
    "/{stream_key}",
    response_model=StreamRead,
    summary="Update stream metadata",
    description="Admin key required. Does not change the stream key or status.",
)
async def update_stream(
    _: AdminKey,
    session: DbSession,
    stream_key: StreamKey,
    payload: StreamUpdate,
) -> StreamRead:
    return await StreamService(session).update_stream(stream_key, payload)


@router.post(
    "/{stream_key}/pause",
    response_model=StreamRead,
    summary="Pause ingestion",
    description="Paused streams reject new events with 409 until resumed.",
)
async def pause_stream(_: AdminKey, session: DbSession, stream_key: StreamKey) -> StreamRead:
    return await StreamService(session).pause_stream(stream_key)


@router.post(
    "/{stream_key}/resume",
    response_model=StreamRead,
    summary="Resume ingestion",
)
async def resume_stream(_: AdminKey, session: DbSession, stream_key: StreamKey) -> StreamRead:
    return await StreamService(session).resume_stream(stream_key)
