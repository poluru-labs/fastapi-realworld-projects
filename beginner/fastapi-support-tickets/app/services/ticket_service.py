from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import (
    CommentCreate,
    CommentRead,
    TicketCreate,
    TicketDetail,
    TicketPriority,
    TicketRead,
    TicketStatus,
    TicketUpdate,
)


class TicketService:
    def __init__(self, repository: TicketRepository) -> None:
        self._repo = repository

    def list_tickets(
        self,
        *,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        q: str | None,
    ) -> list[TicketRead]:
        rows = self._repo.list_tickets()
        if status is not None:
            rows = [ticket for ticket in rows if ticket.status is status]
        if priority is not None:
            rows = [ticket for ticket in rows if ticket.priority is priority]
        if q:
            needle = q.casefold()
            rows = [
                ticket
                for ticket in rows
                if needle in ticket.subject.casefold() or needle in ticket.description.casefold()
            ]
        rows.sort(key=lambda ticket: ticket.updated_at, reverse=True)
        return [self._ticket_read(ticket) for ticket in rows]

    def get_ticket_detail(self, ticket_id: int) -> TicketDetail:
        ticket = self._require_ticket(ticket_id)
        comments = self._repo.list_comments(ticket_id)
        return TicketDetail(
            **self._ticket_read(ticket).model_dump(),
            comments=[self._comment_read(comment) for comment in comments],
        )

    def create_ticket(self, payload: TicketCreate) -> TicketRead:
        record = self._repo.create_ticket(
            subject=payload.subject,
            description=payload.description,
            requester_email=str(payload.requester_email),
            priority=payload.priority,
        )
        return self._ticket_read(record)

    def update_ticket(self, ticket_id: int, payload: TicketUpdate) -> TicketRead:
        fields = payload.model_dump(exclude_unset=True)
        assignee_set = "assignee" in fields
        record = self._repo.update_ticket(
            ticket_id,
            subject=fields.get("subject"),
            description=fields.get("description"),
            priority=fields.get("priority"),
            assignee=fields.get("assignee"),
            assignee_set=assignee_set,
            status=fields.get("status"),
        )
        if record is None:
            raise NotFoundError("Ticket", ticket_id)
        return self._ticket_read(record)

    def delete_ticket(self, ticket_id: int) -> None:
        if self._repo.delete_ticket(ticket_id) is None:
            raise NotFoundError("Ticket", ticket_id)

    def list_comments(self, ticket_id: int) -> list[CommentRead]:
        self._require_ticket(ticket_id)
        return [self._comment_read(comment) for comment in self._repo.list_comments(ticket_id)]

    def add_comment(self, ticket_id: int, payload: CommentCreate) -> CommentRead:
        ticket = self._require_ticket(ticket_id)
        if ticket.status is TicketStatus.CLOSED:
            raise ConflictError("Closed tickets do not accept new comments")
        record = self._repo.add_comment(
            ticket_id,
            author_name=payload.author_name,
            body=payload.body,
            is_internal=payload.is_internal,
        )
        if record is None:
            raise NotFoundError("Ticket", ticket_id)
        return self._comment_read(record)

    def resolve_ticket(self, ticket_id: int) -> TicketRead:
        ticket = self._require_ticket(ticket_id)
        if ticket.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED}:
            raise ConflictError("Ticket is already resolved or closed")
        updated = self._repo.set_status(ticket_id, TicketStatus.RESOLVED)
        assert updated is not None
        return self._ticket_read(updated)

    def close_ticket(self, ticket_id: int) -> TicketRead:
        ticket = self._require_ticket(ticket_id)
        if ticket.status is TicketStatus.CLOSED:
            raise ConflictError("Ticket is already closed")
        updated = self._repo.set_status(ticket_id, TicketStatus.CLOSED)
        assert updated is not None
        return self._ticket_read(updated)

    def reopen_ticket(self, ticket_id: int) -> TicketRead:
        ticket = self._require_ticket(ticket_id)
        if ticket.status in {TicketStatus.OPEN, TicketStatus.IN_PROGRESS}:
            raise ConflictError("Ticket is already open")
        updated = self._repo.set_status(ticket_id, TicketStatus.OPEN)
        assert updated is not None
        return self._ticket_read(updated)

    def _require_ticket(self, ticket_id: int):
        ticket = self._repo.get_ticket(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket", ticket_id)
        return ticket

    def _ticket_read(self, ticket) -> TicketRead:
        return TicketRead(
            id=ticket.id,
            subject=ticket.subject,
            description=ticket.description,
            requester_email=ticket.requester_email,
            priority=ticket.priority,
            status=ticket.status,
            assignee=ticket.assignee,
            comment_count=self._repo.comment_count(ticket.id),
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )

    @staticmethod
    def _comment_read(comment) -> CommentRead:
        return CommentRead(
            id=comment.id,
            ticket_id=comment.ticket_id,
            author_name=comment.author_name,
            body=comment.body,
            is_internal=comment.is_internal,
            created_at=comment.created_at,
        )
