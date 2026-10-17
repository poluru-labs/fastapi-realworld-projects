from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReplyRecord:
    id: int
    ticket_id: int
    author_id: int
    message: str
    created_at: datetime


def _seed_replies() -> dict[int, ReplyRecord]:
    return {
        1: ReplyRecord(
            id=1,
            ticket_id=1,
            author_id=1,
            message="Submit the ticket before agents can reply on a draft.",
            created_at=datetime.fromisoformat("2026-03-01T11:00:00+00:00"),
        ),
    }


class ReplyRepository:
    def __init__(self) -> None:
        self._replies = dict(_seed_replies())
        self._next_id = max(self._replies.keys(), default=0) + 1

    def list_for_ticket(self, ticket_id: int) -> list[ReplyRecord]:
        rows = [r for r in self._replies.values() if r.ticket_id == ticket_id]
        return sorted(rows, key=lambda r: (r.created_at, r.id))

    def get(self, reply_id: int) -> ReplyRecord | None:
        return self._replies.get(reply_id)

    def count_for_ticket(self, ticket_id: int) -> int:
        return sum(1 for r in self._replies.values() if r.ticket_id == ticket_id)

    def allocate_id(self) -> int:
        reply_id = self._next_id
        self._next_id += 1
        return reply_id

    def add(self, record: ReplyRecord) -> ReplyRecord:
        self._replies[record.id] = record
        return record

    def delete(self, reply_id: int) -> None:
        self._replies.pop(reply_id, None)

    def delete_for_ticket(self, ticket_id: int) -> None:
        doomed = [rid for rid, r in self._replies.items() if r.ticket_id == ticket_id]
        for rid in doomed:
            del self._replies[rid]
