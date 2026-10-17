from dataclasses import dataclass
from datetime import datetime

from app.schemas.ticket import TicketPriority, TicketStatus


@dataclass
class TicketRecord:
    id: int
    requester_id: int
    assignee_id: int | None
    title: str
    slug: str
    summary: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    opened_at: datetime | None


def _seed_tickets() -> dict[int, TicketRecord]:
    opened = datetime.fromisoformat("2026-03-01T10:00:00+00:00")
    drafted = datetime.fromisoformat("2026-03-02T11:00:00+00:00")
    return {
        1: TicketRecord(
            id=1,
            requester_id=1,
            assignee_id=1,
            title="Cannot reset password",
            slug="cannot-reset-password",
            summary="Reset email link expires immediately.",
            description=(
                "When I click the password reset link, the page says the token expired. "
                "This started yesterday afternoon."
            ),
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            tags=["account", "auth"],
            created_at=opened,
            updated_at=opened,
            opened_at=opened,
        ),
        2: TicketRecord(
            id=2,
            requester_id=1,
            assignee_id=None,
            title="Draft VPN access request",
            slug="draft-vpn-request",
            summary="Not submitted yet.",
            description="Internal draft for VPN credentials.",
            status=TicketStatus.DRAFT,
            priority=TicketPriority.NORMAL,
            tags=["vpn"],
            created_at=drafted,
            updated_at=drafted,
            opened_at=None,
        ),
    }


class TicketRepository:
    def __init__(self) -> None:
        self._by_id = dict(_seed_tickets())
        self._by_slug = {t.slug: t for t in self._by_id.values()}
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_all(self) -> list[TicketRecord]:
        return list(self._by_id.values())

    def get_by_slug(self, slug: str) -> TicketRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str) -> bool:
        return slug in self._by_slug

    def allocate_id(self) -> int:
        ticket_id = self._next_id
        self._next_id += 1
        return ticket_id

    def add(self, record: TicketRecord) -> TicketRecord:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: TicketRecord) -> None:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record

    def delete(self, ticket_id: int) -> None:
        record = self._by_id.pop(ticket_id, None)
        if record is not None:
            self._by_slug.pop(record.slug, None)
