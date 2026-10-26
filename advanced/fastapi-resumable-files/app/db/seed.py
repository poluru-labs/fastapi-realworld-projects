from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.upload_tokens import hash_upload_token
from app.models.uploads import UploadPart, UploadSession
from app.schemas.uploads import UploadStatus

SEED_UPLOAD_TOKEN = "seed-upload-demo-archive"


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(UploadSession).where(UploadSession.key == "demo-archive")
    )
    if existing is not None:
        return

    now = datetime.now(UTC)
    upload = UploadSession(
        key="demo-archive",
        filename="demo.bin",
        content_type="application/octet-stream",
        total_bytes=1000,
        chunk_size_bytes=250,
        status=UploadStatus.UPLOADING.value,
        upload_token_hash=hash_upload_token(SEED_UPLOAD_TOKEN),
        bytes_received=500,
        created_at=now,
        completed_at=None,
    )
    session.add(upload)
    await session.flush()

    session.add_all(
        [
            UploadPart(
                session_id=upload.id,
                part_index=0,
                byte_start=0,
                byte_end=249,
                size_bytes=250,
                data=b"a" * 250,
            ),
            UploadPart(
                session_id=upload.id,
                part_index=1,
                byte_start=250,
                byte_end=499,
                size_bytes=250,
                data=b"b" * 250,
            ),
        ]
    )
    await session.commit()
