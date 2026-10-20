from dataclasses import dataclass
from datetime import datetime


@dataclass
class MessageRecord:
    id: int
    room_id: int
    author_id: int
    sequence: int
    body: str
    created_at: datetime


def _seed_messages() -> dict[int, MessageRecord]:
    created = datetime.fromisoformat("2026-03-01T12:05:00+00:00")
    return {
        1: MessageRecord(
            id=1,
            room_id=1,
            author_id=1,
            sequence=1,
            body="Welcome to general — connect the WebSocket and send messages over REST.",
            created_at=created,
        ),
    }


class MessageRepository:
    def __init__(self) -> None:
        self._by_id = dict(_seed_messages())
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_for_room(self, room_id: int) -> list[MessageRecord]:
        rows = [message for message in self._by_id.values() if message.room_id == room_id]
        rows.sort(key=lambda message: message.sequence)
        return rows

    def list_after_sequence(
        self,
        room_id: int,
        *,
        after_sequence: int,
        limit: int,
    ) -> list[MessageRecord]:
        rows = [
            message
            for message in self.list_for_room(room_id)
            if message.sequence > after_sequence
        ]
        return rows[:limit]

    def allocate_id(self) -> int:
        message_id = self._next_id
        self._next_id += 1
        return message_id

    def add(self, record: MessageRecord) -> MessageRecord:
        self._by_id[record.id] = record
        return record

    def delete_for_room(self, room_id: int) -> None:
        self._by_id = {
            message_id: message
            for message_id, message in self._by_id.items()
            if message.room_id != room_id
        }
