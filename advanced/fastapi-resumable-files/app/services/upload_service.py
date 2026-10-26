import math
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.upload_tokens import generate_upload_token, hash_upload_token, verify_upload_token
from app.models.uploads import UploadPart, UploadPartIdempotencyRecord, UploadSession
from app.repositories.upload_repository import UploadRepository
from app.schemas.uploads import (
    PartRead,
    UploadCreate,
    UploadProvisioned,
    UploadRead,
    UploadStatus,
    UploadStatusDetail,
)


class UploadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UploadRepository(session)

    async def list_uploads(self) -> list[UploadRead]:
        rows = await self._repo.list_sessions()
        reads: list[UploadRead] = []
        for row in rows:
            reads.append(await self._read_session(row))
        return reads

    async def provision(self, payload: UploadCreate) -> UploadProvisioned:
        if await self._repo.get_by_key(payload.key) is not None:
            raise ConflictError(f"Upload key {payload.key!r} already exists")
        plaintext = generate_upload_token()
        now = datetime.now(UTC)
        record = UploadSession(
            key=payload.key,
            filename=payload.filename,
            content_type=payload.content_type,
            total_bytes=payload.total_bytes,
            chunk_size_bytes=payload.chunk_size_bytes,
            status=UploadStatus.INITIATED.value,
            upload_token_hash=hash_upload_token(plaintext),
            bytes_received=0,
            created_at=now,
            completed_at=None,
        )
        await self._repo.add_session(record)
        await self._session.commit()
        base = await self._read_session(record)
        return UploadProvisioned(**base.model_dump(), upload_token=plaintext)

    async def get_upload(self, key: str) -> UploadRead:
        return await self._read_session(await self._require_session(key))

    async def status(self, key: str, token: str) -> UploadStatusDetail:
        session = await self._verify_token(key, token)
        return await self._status_detail(session)

    async def abort(self, key: str) -> UploadRead:
        session = await self._require_session(key)
        if session.status == UploadStatus.COMPLETED.value:
            raise ConflictError("Completed uploads cannot be aborted")
        if session.status == UploadStatus.ABORTED.value:
            raise ConflictError("Upload is already aborted")
        session.status = UploadStatus.ABORTED.value
        await self._session.commit()
        return await self._read_session(session)

    async def upload_part(
        self,
        key: str,
        token: str,
        idempotency_key: str,
        part_index: int,
        data: bytes,
    ) -> PartRead:
        session = await self._verify_token(key, token)
        if session.status in {UploadStatus.COMPLETED.value, UploadStatus.ABORTED.value}:
            raise ConflictError("Upload is not accepting parts")

        cached = await self._repo.get_idempotency(session.id, idempotency_key)
        if cached is not None:
            return PartRead.model_validate_json(cached.response_json)

        expected_parts = self._expected_parts(session)
        if part_index < 0 or part_index >= expected_parts:
            raise ConflictError("part_index is out of range for this upload")

        expected_size = self._part_size(session, part_index)
        if len(data) != expected_size:
            raise ConflictError(
                f"Part size must be {expected_size} bytes for index {part_index}"
            )

        existing = await self._repo.get_part(session.id, part_index)
        if existing is not None:
            if existing.data == data:
                body = await self._part_read(session, existing)
                await self._store_idempotency(session.id, idempotency_key, body)
                await self._session.commit()
                return body
            raise ConflictError("Part index already uploaded with different content")

        byte_start = part_index * session.chunk_size_bytes
        byte_end = byte_start + len(data) - 1
        part = UploadPart(
            session_id=session.id,
            part_index=part_index,
            byte_start=byte_start,
            byte_end=byte_end,
            size_bytes=len(data),
            data=data,
        )
        await self._repo.add_part(part)
        session.bytes_received += len(data)
        session.status = UploadStatus.UPLOADING.value
        body = await self._part_read(session, part)
        await self._store_idempotency(session.id, idempotency_key, body)
        await self._session.commit()
        return body

    async def complete(self, key: str, token: str) -> UploadStatusDetail:
        session = await self._verify_token(key, token)
        if session.status == UploadStatus.COMPLETED.value:
            return await self._status_detail(session)
        if session.status == UploadStatus.ABORTED.value:
            raise ConflictError("Upload was aborted")

        detail = await self._status_detail(session)
        if detail.missing_part_indexes:
            raise ConflictError("Upload is missing one or more parts")

        session.status = UploadStatus.COMPLETED.value
        session.completed_at = datetime.now(UTC)
        await self._session.commit()
        return await self._status_detail(session)

    async def _verify_token(self, key: str, token: str) -> UploadSession:
        session = await self._repo.get_by_key(key)
        if session is None or not verify_upload_token(token, session.upload_token_hash):
            raise NotFoundError("Upload", key)
        return session

    async def _require_session(self, key: str) -> UploadSession:
        session = await self._repo.get_by_key(key)
        if session is None:
            raise NotFoundError("Upload", key)
        return session

    async def _read_session(self, session: UploadSession) -> UploadRead:
        parts = await self._repo.list_parts(session.id)
        expected = self._expected_parts(session)
        return UploadRead(
            id=session.id,
            key=session.key,
            filename=session.filename,
            content_type=session.content_type,
            total_bytes=session.total_bytes,
            chunk_size_bytes=session.chunk_size_bytes,
            status=UploadStatus(session.status),
            bytes_received=session.bytes_received,
            parts_received=len(parts),
            expected_parts=expected,
            created_at=session.created_at,
            completed_at=session.completed_at,
        )

    async def _status_detail(self, session: UploadSession) -> UploadStatusDetail:
        base = await self._read_session(session)
        parts = await self._repo.list_parts(session.id)
        present = {part.part_index for part in parts}
        expected = self._expected_parts(session)
        missing = [index for index in range(expected) if index not in present]
        progress = 0.0 if session.total_bytes == 0 else round(
            (session.bytes_received / session.total_bytes) * 100,
            2,
        )
        return UploadStatusDetail(
            **base.model_dump(),
            missing_part_indexes=missing,
            progress_percent=progress,
        )

    async def _part_read(self, session: UploadSession, part: UploadPart) -> PartRead:
        return PartRead(
            upload_key=session.key,
            part_index=part.part_index,
            byte_start=part.byte_start,
            byte_end=part.byte_end,
            size_bytes=part.size_bytes,
            bytes_received=session.bytes_received,
            status=UploadStatus(session.status),
        )

    async def _store_idempotency(
        self,
        session_id: int,
        idempotency_key: str,
        body: PartRead,
    ) -> None:
        await self._repo.add_idempotency(
            UploadPartIdempotencyRecord(
                session_id=session_id,
                idempotency_key=idempotency_key,
                response_json=body.model_dump_json(),
            )
        )

    @staticmethod
    def _expected_parts(session: UploadSession) -> int:
        return math.ceil(session.total_bytes / session.chunk_size_bytes)

    @staticmethod
    def _part_size(session: UploadSession, part_index: int) -> int:
        expected = UploadService._expected_parts(session)
        if part_index == expected - 1:
            remainder = session.total_bytes % session.chunk_size_bytes
            return session.chunk_size_bytes if remainder == 0 else remainder
        return session.chunk_size_bytes
