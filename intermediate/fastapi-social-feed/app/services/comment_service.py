"""Comments follow the post's visibility, then one extra rule: the post must be published."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.comment_repository import CommentRecord, CommentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentCreate, CommentPage, CommentRead
from app.schemas.post import PostStatus
from app.schemas.user import UserRead, UserRole
from app.services.post_service import PostService


class CommentService:
    def __init__(
        self,
        *,
        posts: PostService,
        comments: CommentRepository,
        users: UserRepository,
    ) -> None:
        self._posts = posts
        self._comments = comments
        self._users = users

    def list_comments(
        self,
        actor: UserRead | None,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> CommentPage:
        post = self._posts.visible_record(actor, slug)
        rows = self._comments.list_for_post(post.id)
        window = rows[offset : offset + limit]
        return CommentPage(
            items=[self._to_read(comment) for comment in window],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def create_comment(self, actor: UserRead, slug: str, payload: CommentCreate) -> CommentRead:
        post = self._posts.visible_record(actor, slug)
        if post.status is not PostStatus.PUBLISHED:
            raise ConflictError("Only published posts accept comments")
        record = self._comments.add(
            CommentRecord(
                id=self._comments.allocate_id(),
                post_id=post.id,
                author_id=actor.id,
                body=payload.body,
                created_at=datetime.now(UTC),
            )
        )
        return self._to_read(record)

    def delete_comment(self, actor: UserRead, slug: str, comment_id: int) -> None:
        post = self._posts.visible_record(actor, slug)
        comment = self._comments.get(comment_id)
        if comment is None or comment.post_id != post.id:
            raise NotFoundError("Comment", comment_id)
        is_comment_author = actor.id == comment.author_id
        is_post_author = actor.id == post.author_id
        if actor.role is not UserRole.ADMIN and not is_comment_author and not is_post_author:
            raise ForbiddenError(
                "Only the comment author, the post author, or an admin can delete this comment"
            )
        self._comments.delete(comment_id)

    def _to_read(self, record: CommentRecord) -> CommentRead:
        author = self._users.get_by_id(record.author_id)
        return CommentRead(
            id=record.id,
            post_id=record.post_id,
            body=record.body,
            author_id=record.author_id,
            author_name=author.full_name if author is not None else "Unknown",
            created_at=record.created_at,
        )
