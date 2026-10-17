import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.chat import ChatMessage, DeliveryOutbox
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.chat import MessageCreate, MessageRead, OutboxStatus
from app.schemas.user import UserRead
from app.services.room_service import RoomService


class MessageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rooms = RoomRepository(session)
        self._messages = MessageRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._room_service = RoomService(session)

    async def list_messages(
        self,
        actor: UserRead,
        slug: str,
        *,
        after_sequence: int,
        limit: int,
    ) -> list[MessageRead]:
        room = await self._room_service.require_member_room(actor, slug)
        rows = await self._messages.list_after_sequence(
            room.id,
            after_sequence=after_sequence,
            limit=limit,
        )
        return [MessageRead.model_validate(row) for row in rows]

    async def send(
        self,
        actor: UserRead,
        slug: str,
        payload: MessageCreate,
        *,
        idempotency_key: str,
    ) -> MessageRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        room = await self._room_service.require_member_room(actor, slug)
        now = datetime.now(UTC)
        room.message_sequence += 1
        sequence = room.message_sequence
        room.updated_at = now

        message = ChatMessage(
            room_id=room.id,
            author_id=actor.id,
            sequence=sequence,
            body=payload.body.strip(),
            created_at=now,
        )
        await self._messages.add(message)
        members = await self._rooms.list_members(room.id)
        for member in members:
            if member.user_id == actor.id:
                continue
            await self._messages.add_outbox(
                DeliveryOutbox(
                    message_id=message.id,
                    room_id=room.id,
                    recipient_id=member.user_id,
                    status=OutboxStatus.PENDING.value,
                    version=1,
                    created_at=now,
                )
            )
        await self._rooms.save()
        await self._session.commit()

        body = MessageRead.model_validate(message)
        await self._store_idempotent(actor, idempotency_key, body)
        await self._session.commit()
        return body

    async def _load_idempotent(self, actor: UserRead, key: str) -> MessageRead | None:
        record = await self._idempotency.get(key)
        if record is None:
            return None
        if record.user_id != actor.id:
            raise ConflictError("Idempotency-Key was used by another user")
        data = json.loads(record.response_json)
        return MessageRead.model_validate(data)

    async def _store_idempotent(
        self,
        actor: UserRead,
        key: str,
        body: MessageRead,
    ) -> None:
        await self._idempotency.save(
            key=key,
            user_id=actor.id,
            response_json=body.model_dump_json(),
            status_code=201,
        )
