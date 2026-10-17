from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, DeliveryOutbox


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_after_sequence(
        self,
        room_id: int,
        *,
        after_sequence: int,
        limit: int,
    ) -> list[ChatMessage]:
        rows = await self._session.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.room_id == room_id,
                ChatMessage.sequence > after_sequence,
            )
            .order_by(ChatMessage.sequence)
            .limit(limit)
        )
        return list(rows)

    async def add(self, message: ChatMessage) -> ChatMessage:
        self._session.add(message)
        await self._session.flush()
        return message

    async def add_outbox(self, row: DeliveryOutbox) -> None:
        self._session.add(row)

    async def save(self) -> None:
        await self._session.flush()
