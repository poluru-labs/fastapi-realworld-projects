from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.reply_repository import ReplyRecord, ReplyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.reply import ReplyCreate, ReplyPage, ReplyRead
from app.schemas.user import UserRead, UserRole
from app.services.ticket_service import TicketService


class ReplyService:
    def __init__(
        self,
        *,
        tickets: TicketService,
        replies: ReplyRepository,
        users: UserRepository,
    ) -> None:
        self._tickets = tickets
        self._replies = replies
        self._users = users

    def list_replies(
        self,
        actor: UserRead,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> ReplyPage:
        ticket = self._tickets.visible_record(actor, slug)
        rows = self._replies.list_for_ticket(ticket.id)
        window = rows[offset : offset + limit]
        return ReplyPage(
            items=[self._to_read(row) for row in window],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def create_reply(self, actor: UserRead, slug: str, payload: ReplyCreate) -> ReplyRead:
        ticket = self._tickets.visible_record(actor, slug)
        if not self._tickets.allows_replies(ticket):
            raise ConflictError("Replies are not accepted on draft or closed tickets")
        record = self._replies.add(
            ReplyRecord(
                id=self._replies.allocate_id(),
                ticket_id=ticket.id,
                author_id=actor.id,
                message=payload.message,
                created_at=datetime.now(UTC),
            )
        )
        return self._to_read(record)

    def delete_reply(self, actor: UserRead, slug: str, reply_id: int) -> None:
        ticket = self._tickets.visible_record(actor, slug)
        reply = self._replies.get(reply_id)
        if reply is None or reply.ticket_id != ticket.id:
            raise NotFoundError("Reply", reply_id)
        is_author = actor.id == reply.author_id
        is_requester = actor.id == ticket.requester_id
        if actor.role is not UserRole.ADMIN and not is_author and not is_requester:
            raise ForbiddenError(
                "Only the reply author, the requester, or an admin can delete this reply"
            )
        self._replies.delete(reply_id)

    def _to_read(self, record: ReplyRecord) -> ReplyRead:
        author = self._users.get_by_id(record.author_id)
        return ReplyRead(
            id=record.id,
            ticket_id=record.ticket_id,
            message=record.message,
            author_id=record.author_id,
            author_name=author.full_name if author is not None else "Unknown",
            created_at=record.created_at,
        )
