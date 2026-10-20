from datetime import UTC, datetime

from app.core.exceptions import ConflictError
from app.repositories.message_repository import MessageRecord, MessageRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import MessageCreate, MessagePage, MessageRead, RoomStatus, WsEvent
from app.schemas.user import UserRead
from app.services.room_service import RoomService
from app.services.ws_hub import WsHub


class MessageService:
    def __init__(
        self,
        *,
        rooms: RoomRepository,
        messages: MessageRepository,
        users: UserRepository,
        ws_hub: WsHub,
    ) -> None:
        self._rooms = rooms
        self._messages = messages
        self._users = users
        self._ws_hub = ws_hub
        self._room_service = RoomService(rooms=rooms, messages=messages, users=users)

    def list_messages(
        self,
        actor: UserRead,
        slug: str,
        *,
        after_sequence: int,
        limit: int,
    ) -> MessagePage:
        room = self._room_service.require_member_room(actor, slug)
        rows = self._messages.list_after_sequence(
            room.id,
            after_sequence=after_sequence,
            limit=limit,
        )
        return MessagePage(
            items=[self._to_read(message) for message in rows],
            room_slug=slug,
            after_sequence=after_sequence,
            latest_sequence=room.message_sequence,
        )

    async def send(
        self,
        actor: UserRead,
        slug: str,
        payload: MessageCreate,
    ) -> MessageRead:
        room = self._room_service.require_member_room(actor, slug)
        if room.status is not RoomStatus.ACTIVE:
            raise ConflictError("Cannot send messages to an archived room")
        now = datetime.now(UTC)
        room.message_sequence += 1
        sequence = room.message_sequence
        room.updated_at = now
        message = MessageRecord(
            id=self._messages.allocate_id(),
            room_id=room.id,
            author_id=actor.id,
            sequence=sequence,
            body=payload.body.strip(),
            created_at=now,
        )
        self._messages.add(message)
        self._rooms.save(room)
        body = self._to_read(message)
        event = WsEvent(payload=body)
        await self._ws_hub.broadcast(slug, event.model_dump(mode="json"))
        return body

    def _to_read(self, record: MessageRecord) -> MessageRead:
        author = self._users.get_by_id(record.author_id)
        return MessageRead(
            id=record.id,
            room_id=record.room_id,
            author_id=record.author_id,
            author_name=author.full_name if author is not None else "Unknown",
            sequence=record.sequence,
            body=record.body,
            created_at=record.created_at,
        )
