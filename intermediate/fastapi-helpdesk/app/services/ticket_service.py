"""Ticket visibility, workflow transitions, and assignment rules."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.reply_repository import ReplyRepository
from app.repositories.ticket_repository import TicketRecord, TicketRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ticket import (
    CategoryCount,
    TicketCreate,
    TicketPage,
    TicketPriority,
    TicketRead,
    TicketStatus,
    TicketUpdate,
    slugify,
)
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.DRAFT: {TicketStatus.OPEN},
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.IN_PROGRESS: {TicketStatus.RESOLVED, TicketStatus.OPEN},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.OPEN},
    TicketStatus.CLOSED: {TicketStatus.OPEN},
}

_ACTIVE_STATUSES = {
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.RESOLVED,
}


def _can_view(actor: UserRead | None, record: TicketRecord) -> bool:
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    if actor.id == record.requester_id:
        return True
    if record.assignee_id is not None and actor.id == record.assignee_id:
        return True
    return False


class TicketService:
    def __init__(
        self,
        *,
        tickets: TicketRepository,
        replies: ReplyRepository,
        users: UserRepository,
    ) -> None:
        self._tickets = tickets
        self._replies = replies
        self._users = users

    def list_queue(
        self,
        actor: UserRead,
        *,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        tag: str | None,
        assignee_id: int | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> TicketPage:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Admin role required to list the support queue")
        rows = [t for t in self._tickets.list_all() if t.status is not TicketStatus.DRAFT]
        rows = self._filter_rows(
            rows,
            status=status,
            priority=priority,
            tag=tag,
            assignee_id=assignee_id,
            query=query,
        )
        rows.sort(key=lambda t: (t.updated_at, t.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def list_mine(
        self,
        actor: UserRead,
        *,
        status: TicketStatus | None,
        limit: int,
        offset: int,
    ) -> TicketPage:
        rows = [t for t in self._tickets.list_all() if t.requester_id == actor.id]
        if status is not None:
            rows = [t for t in rows if t.status is status]
        rows.sort(key=lambda t: (t.updated_at, t.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def list_assigned(
        self,
        actor: UserRead,
        *,
        status: TicketStatus | None,
        limit: int,
        offset: int,
    ) -> TicketPage:
        rows = [
            t
            for t in self._tickets.list_all()
            if t.assignee_id == actor.id and t.status is not TicketStatus.DRAFT
        ]
        if status is not None:
            rows = [t for t in rows if t.status is status]
        rows.sort(key=lambda t: (t.updated_at, t.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def get_ticket(self, actor: UserRead, slug: str) -> TicketRead:
        return self._to_read(self.visible_record(actor, slug))

    def visible_record(self, actor: UserRead, slug: str) -> TicketRecord:
        record = self._tickets.get_by_slug(slug)
        if record is None or not _can_view(actor, record):
            raise NotFoundError("Ticket", slug)
        return record

    def allows_replies(self, record: TicketRecord) -> bool:
        return record.status in _ACTIVE_STATUSES

    def create_ticket(self, actor: UserRead, payload: TicketCreate) -> TicketRead:
        slug = payload.slug or slugify(payload.title)
        if self._tickets.slug_taken(slug):
            raise ConflictError("Another ticket already uses this slug")
        now = datetime.now(UTC)
        record = self._tickets.add(
            TicketRecord(
                id=self._tickets.allocate_id(),
                requester_id=actor.id,
                assignee_id=None,
                title=payload.title,
                slug=slug,
                summary=payload.summary,
                description=payload.description,
                status=TicketStatus.DRAFT,
                priority=payload.priority,
                tags=list(payload.tags),
                created_at=now,
                updated_at=now,
                opened_at=None,
            )
        )
        return self._to_read(record)

    def update_ticket(self, actor: UserRead, slug: str, payload: TicketUpdate) -> TicketRead:
        record = self.visible_record(actor, slug)
        changes = payload.model_dump(exclude_unset=True)
        content_keys = {"title", "summary", "description", "priority", "tags"}

        if content_keys & changes.keys():
            if actor.id != record.requester_id:
                raise ForbiddenError("Only the requester can edit ticket content")

        if "assignee_id" in changes:
            if actor.role is not UserRole.ADMIN:
                raise ForbiddenError("Only an admin can assign tickets")
            assignee_id = changes["assignee_id"]
            if assignee_id is not None:
                assignee = self._users.get_by_id(assignee_id)
                if assignee is None or not assignee.is_active:
                    raise NotFoundError("User", assignee_id)

        if "title" in changes:
            record.title = changes["title"]
        if "summary" in changes:
            record.summary = changes["summary"]
        if "description" in changes:
            record.description = changes["description"]
        if "priority" in changes:
            record.priority = changes["priority"]
        if "tags" in changes:
            record.tags = list(changes["tags"])
        if "assignee_id" in changes:
            record.assignee_id = changes["assignee_id"]

        record.updated_at = datetime.now(UTC)
        self._tickets.save(record)
        return self._to_read(record)

    def submit(self, actor: UserRead, slug: str) -> TicketRead:
        record = self.visible_record(actor, slug)
        self._require_requester(actor, record)
        self._move(record, TicketStatus.DRAFT, TicketStatus.OPEN, "Only a draft can be submitted")
        now = datetime.now(UTC)
        record.opened_at = now
        record.updated_at = now
        self._tickets.save(record)
        return self._to_read(record)

    def start(self, actor: UserRead, slug: str) -> TicketRead:
        record = self.visible_record(actor, slug)
        self._require_agent(actor, record)
        self._move(
            record,
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            "Only an open ticket can start",
        )
        record.updated_at = datetime.now(UTC)
        self._tickets.save(record)
        return self._to_read(record)

    def resolve(self, actor: UserRead, slug: str) -> TicketRead:
        record = self.visible_record(actor, slug)
        self._require_agent(actor, record)
        if record.status not in {TicketStatus.OPEN, TicketStatus.IN_PROGRESS}:
            raise ConflictError(
                "Only open or in-progress tickets can be resolved. "
                f"This ticket is {record.status.value}"
            )
        record.status = TicketStatus.RESOLVED
        record.updated_at = datetime.now(UTC)
        self._tickets.save(record)
        return self._to_read(record)

    def close(self, actor: UserRead, slug: str) -> TicketRead:
        record = self.visible_record(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.requester_id:
            raise ForbiddenError("Only the requester or an admin can close this ticket")
        closable = {
            TicketStatus.RESOLVED,
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
        }
        if record.status not in closable:
            raise ConflictError(
                f"Cannot close from status {record.status.value}. Resolve first or use reopen."
            )
        record.status = TicketStatus.CLOSED
        record.updated_at = datetime.now(UTC)
        self._tickets.save(record)
        return self._to_read(record)

    def reopen(self, actor: UserRead, slug: str) -> TicketRead:
        record = self.visible_record(actor, slug)
        self._require_requester_or_admin(actor, record)
        self._move(
            record,
            TicketStatus.CLOSED,
            TicketStatus.OPEN,
            "Only a closed ticket can be reopened",
        )
        record.updated_at = datetime.now(UTC)
        self._tickets.save(record)
        return self._to_read(record)

    def delete_ticket(self, actor: UserRead, slug: str) -> None:
        record = self.visible_record(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.requester_id:
            raise ForbiddenError("Only the requester or an admin can delete this ticket")
        self._replies.delete_for_ticket(record.id)
        self._tickets.delete(record.id)

    def list_categories(self) -> list[CategoryCount]:
        counts: dict[str, int] = {}
        for ticket in self._tickets.list_all():
            if ticket.status is TicketStatus.DRAFT:
                continue
            for tag in ticket.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [CategoryCount(name=n, ticket_count=counts[n]) for n in sorted(counts)]

    def _filter_rows(
        self,
        rows: list[TicketRecord],
        *,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        tag: str | None,
        assignee_id: int | None,
        query: str | None,
    ) -> list[TicketRecord]:
        if status is not None:
            rows = [t for t in rows if t.status is status]
        if priority is not None:
            rows = [t for t in rows if t.priority is priority]
        if assignee_id is not None:
            rows = [t for t in rows if t.assignee_id == assignee_id]
        if tag is not None:
            needle = tag.strip().casefold()
            rows = [t for t in rows if needle in t.tags]
        if query is not None:
            q = query.casefold()
            rows = [
                t
                for t in rows
                if q in t.title.casefold()
                or q in t.summary.casefold()
                or q in t.description.casefold()
            ]
        return rows

    def _page(self, rows: list[TicketRecord], *, limit: int, offset: int) -> TicketPage:
        return TicketPage(
            items=[self._to_read(t) for t in rows[offset : offset + limit]],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def _to_read(self, record: TicketRecord) -> TicketRead:
        requester = self._users.get_by_id(record.requester_id)
        assignee = (
            self._users.get_by_id(record.assignee_id) if record.assignee_id is not None else None
        )
        return TicketRead(
            id=record.id,
            slug=record.slug,
            title=record.title,
            summary=record.summary,
            description=record.description,
            status=record.status,
            priority=record.priority,
            tags=list(record.tags),
            requester_id=record.requester_id,
            requester_name=requester.full_name if requester else "Unknown",
            assignee_id=record.assignee_id,
            assignee_name=assignee.full_name if assignee else None,
            reply_count=self._replies.count_for_ticket(record.id),
            created_at=record.created_at,
            updated_at=record.updated_at,
            opened_at=record.opened_at,
        )

    def _require_requester(self, actor: UserRead, record: TicketRecord) -> None:
        if actor.id != record.requester_id:
            raise ForbiddenError("Only the requester can perform this action")

    def _require_agent(self, actor: UserRead, record: TicketRecord) -> None:
        if actor.role is UserRole.ADMIN:
            return
        if record.assignee_id == actor.id:
            return
        raise ForbiddenError("Only the assignee or an admin can perform this action")

    def _require_requester_or_admin(self, actor: UserRead, record: TicketRecord) -> None:
        if actor.role is UserRole.ADMIN or actor.id == record.requester_id:
            return
        raise ForbiddenError("Only the requester or an admin can perform this action")

    def _move(
        self,
        record: TicketRecord,
        source: TicketStatus,
        target: TicketStatus,
        message: str,
    ) -> None:
        allowed = _TRANSITIONS[record.status]
        if record.status is not source or target not in allowed:
            raise ConflictError(f"{message}. This ticket is {record.status.value}")
        record.status = target
