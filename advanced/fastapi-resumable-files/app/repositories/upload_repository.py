from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.uploads import UploadPart, UploadPartIdempotencyRecord, UploadSession


class UploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_sessions(self) -> list[UploadSession]:
        result = await self._session.scalars(select(UploadSession).order_by(UploadSession.key))
        return list(result)

    async def get_by_key(self, key: str) -> UploadSession | None:
        return await self._session.scalar(select(UploadSession).where(UploadSession.key == key))

    async def add_session(self, session: UploadSession) -> UploadSession:
        self._session.add(session)
        await self._session.flush()
        return session

    async def list_parts(self, session_id: int) -> list[UploadPart]:
        result = await self._session.scalars(
            select(UploadPart)
            .where(UploadPart.session_id == session_id)
            .order_by(UploadPart.part_index)
        )
        return list(result)

    async def get_part(self, session_id: int, part_index: int) -> UploadPart | None:
        return await self._session.scalar(
            select(UploadPart).where(
                UploadPart.session_id == session_id,
                UploadPart.part_index == part_index,
            )
        )

    async def add_part(self, part: UploadPart) -> UploadPart:
        self._session.add(part)
        await self._session.flush()
        return part

    async def get_idempotency(
        self,
        session_id: int,
        idempotency_key: str,
    ) -> UploadPartIdempotencyRecord | None:
        return await self._session.scalar(
            select(UploadPartIdempotencyRecord).where(
                UploadPartIdempotencyRecord.session_id == session_id,
                UploadPartIdempotencyRecord.idempotency_key == idempotency_key,
            )
        )

    async def add_idempotency(self, record: UploadPartIdempotencyRecord) -> None:
        self._session.add(record)
        await self._session.flush()
