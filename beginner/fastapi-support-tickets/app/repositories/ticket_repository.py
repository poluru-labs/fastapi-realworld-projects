from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.schemas.ticket import TicketPriority, TicketStatus


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class TicketRecord:
    id: int
    subject: str
    description: str
    requester_email: str
    priority: TicketPriority
    status: TicketStatus
    assignee: str | None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class CommentRecord:
    id: int
    ticket_id: int
    author_name: str
    body: str
    is_internal: bool
    created_at: datetime = field(default_factory=_utcnow)


def _seed() -> tuple[dict[int, TicketRecord], dict[int, CommentRecord]]:
    tickets = {
        1: TicketRecord(
            id=1,
            subject="Login page returns 500",
            description="Happens after entering valid credentials on Chrome.",
            requester_email="alex@example.com",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            assignee=None,
            created_at=datetime.fromisoformat("2026-03-01T09:15:00+00:00"),
            updated_at=datetime.fromisoformat("2026-03-01T09:15:00+00:00"),
        ),
        2: TicketRecord(
            id=2,
            subject="Invoice total looks wrong",
            description="March invoice shows double the expected seat count.",
            requester_email="billing@example.com",
            priority=TicketPriority.HIGH,
            status=TicketStatus.IN_PROGRESS,
            assignee="Jordan Lee",
            created_at=datetime.fromisoformat("2026-03-02T14:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-03-03T10:30:00+00:00"),
        ),
        3: TicketRecord(
            id=3,
            subject="Typo on pricing page",
            description="Footer says 'annualy' instead of 'annually'.",
            requester_email="sam@example.com",
            priority=TicketPriority.LOW,
            status=TicketStatus.CLOSED,
            assignee="Jordan Lee",
            created_at=datetime.fromisoformat("2026-02-20T11:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-02-21T16:45:00+00:00"),
        ),
    }
    comments = {
        1: CommentRecord(
            id=1,
            ticket_id=1,
            author_name="Alex Rivera",
            body="Started after yesterday's deploy.",
            is_internal=False,
            created_at=datetime.fromisoformat("2026-03-01T09:20:00+00:00"),
        ),
        2: CommentRecord(
            id=2,
            ticket_id=1,
            author_name="Support Agent",
            body="Checking error logs for correlation id.",
            is_internal=True,
            created_at=datetime.fromisoformat("2026-03-01T10:00:00+00:00"),
        ),
        3: CommentRecord(
            id=3,
            ticket_id=2,
            author_name="Jordan Lee",
            body="Finance team confirmed seat count mismatch.",
            is_internal=False,
            created_at=datetime.fromisoformat("2026-03-03T10:30:00+00:00"),
        ),
    }
    return tickets, comments


class TicketRepository:
    """In-memory support tickets and comments."""

    def __init__(self) -> None:
        self._tickets, self._comments = _seed()
        self._next_ticket_id = max(self._tickets.keys(), default=0) + 1
        self._next_comment_id = max(self._comments.keys(), default=0) + 1

    def list_tickets(self) -> list[TicketRecord]:
        return list(self._tickets.values())

    def get_ticket(self, ticket_id: int) -> TicketRecord | None:
        return self._tickets.get(ticket_id)

    def create_ticket(
        self,
        *,
        subject: str,
        description: str,
        requester_email: str,
        priority: TicketPriority,
    ) -> TicketRecord:
        ticket_id = self._next_ticket_id
        self._next_ticket_id += 1
        record = TicketRecord(
            id=ticket_id,
            subject=subject,
            description=description,
            requester_email=requester_email.lower(),
            priority=priority,
            status=TicketStatus.OPEN,
            assignee=None,
        )
        self._tickets[ticket_id] = record
        return record

    def update_ticket(
        self,
        ticket_id: int,
        *,
        subject: str | None,
        description: str | None,
        priority: TicketPriority | None,
        assignee: str | None,
        assignee_set: bool,
        status: TicketStatus | None,
    ) -> TicketRecord | None:
        record = self._tickets.get(ticket_id)
        if record is None:
            return None
        if subject is not None:
            record.subject = subject
        if description is not None:
            record.description = description
        if priority is not None:
            record.priority = priority
        if assignee_set:
            record.assignee = assignee
        if status is not None:
            record.status = status
        record.updated_at = _utcnow()
        return record

    def delete_ticket(self, ticket_id: int) -> TicketRecord | None:
        record = self._tickets.pop(ticket_id, None)
        if record is None:
            return None
        to_remove = [
            cid for cid, comment in self._comments.items() if comment.ticket_id == ticket_id
        ]
        for cid in to_remove:
            del self._comments[cid]
        return record

    def set_status(self, ticket_id: int, status: TicketStatus) -> TicketRecord | None:
        record = self._tickets.get(ticket_id)
        if record is None:
            return None
        record.status = status
        record.updated_at = _utcnow()
        return record

    def list_comments(self, ticket_id: int) -> list[CommentRecord]:
        rows = [comment for comment in self._comments.values() if comment.ticket_id == ticket_id]
        rows.sort(key=lambda comment: comment.created_at)
        return rows

    def comment_count(self, ticket_id: int) -> int:
        return len(self.list_comments(ticket_id))

    def add_comment(
        self,
        ticket_id: int,
        *,
        author_name: str,
        body: str,
        is_internal: bool,
    ) -> CommentRecord | None:
        if ticket_id not in self._tickets:
            return None
        comment_id = self._next_comment_id
        self._next_comment_id += 1
        record = CommentRecord(
            id=comment_id,
            ticket_id=ticket_id,
            author_name=author_name,
            body=body,
            is_internal=is_internal,
        )
        self._comments[comment_id] = record
        self._tickets[ticket_id].updated_at = _utcnow()
        return record


@lru_cache
def get_ticket_repository() -> TicketRepository:
    return TicketRepository()
