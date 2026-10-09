"""Who can see a post, who can change it, and which status moves are legal.

Routes only parse HTTP. Change a rule in this module.
"""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRecord, PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post import (
    PostCreate,
    PostPage,
    PostRead,
    PostStatus,
    PostUpdate,
    TagCount,
    slugify,
)
from app.schemas.user import UserRead, UserRole

# Legal moves. Repeating the current status is a 409, not a no-op.
_TRANSITIONS: dict[PostStatus, set[PostStatus]] = {
    PostStatus.DRAFT: {PostStatus.PUBLISHED},
    PostStatus.PUBLISHED: {PostStatus.DRAFT, PostStatus.ARCHIVED},
    PostStatus.ARCHIVED: {PostStatus.DRAFT},
}


def _can_view(actor: UserRead | None, record: PostRecord) -> bool:
    """Published posts are public. Anything else is the author or a platform admin."""
    if record.status is PostStatus.PUBLISHED:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == record.author_id


class PostService:
    def __init__(
        self,
        *,
        posts: PostRepository,
        comments: CommentRepository,
        users: UserRepository,
    ) -> None:
        self._posts = posts
        self._comments = comments
        self._users = users

    def list_published(
        self,
        *,
        tag: str | None,
        author_id: int | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> PostPage:
        rows = [
            post
            for post in self._posts.list_all()
            if post.status is PostStatus.PUBLISHED
            and self._matches(post, tag=tag, author_id=author_id, query=query)
        ]
        rows.sort(key=lambda post: (post.published_at or post.created_at, post.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def list_mine(
        self,
        actor: UserRead,
        *,
        status: PostStatus | None,
        limit: int,
        offset: int,
    ) -> PostPage:
        rows = [post for post in self._posts.list_all() if post.author_id == actor.id]
        if status is not None:
            rows = [post for post in rows if post.status is status]
        rows.sort(key=lambda post: (post.updated_at, post.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def get_post(self, actor: UserRead | None, slug: str) -> PostRead:
        return self._to_read(self.visible_record(actor, slug))

    def visible_record(self, actor: UserRead | None, slug: str) -> PostRecord:
        record = self._posts.get_by_slug(slug)
        # Hidden posts look missing. A 403 would tell the caller the draft exists.
        if record is None or not _can_view(actor, record):
            raise NotFoundError("Post", slug)
        return record

    def create_post(self, actor: UserRead, payload: PostCreate) -> PostRead:
        slug = payload.slug or slugify(payload.title)
        if self._posts.slug_taken(slug):
            raise ConflictError("Another post already uses this slug")
        now = datetime.now(UTC)
        record = self._posts.add(
            PostRecord(
                id=self._posts.allocate_id(),
                author_id=actor.id,
                title=payload.title,
                slug=slug,
                summary=payload.summary,
                body=payload.body,
                status=PostStatus.DRAFT,
                tags=list(payload.tags),
                created_at=now,
                updated_at=now,
                published_at=None,
            )
        )
        return self._to_read(record)

    def update_post(self, actor: UserRead, slug: str, payload: PostUpdate) -> PostRead:
        record = self.visible_record(actor, slug)
        self._require_author(actor, record, "Only the author can edit this post")
        changes = payload.model_dump(exclude_unset=True)
        if "title" in changes:
            record.title = changes["title"]
        if "summary" in changes:
            record.summary = changes["summary"]
        if "body" in changes:
            record.body = changes["body"]
        if "tags" in changes:
            record.tags = list(changes["tags"])
        record.updated_at = datetime.now(UTC)
        self._posts.save(record)
        return self._to_read(record)

    def publish(self, actor: UserRead, slug: str) -> PostRead:
        record = self.visible_record(actor, slug)
        self._require_author(actor, record, "Only the author can publish this post")
        self._move(
            record,
            source=PostStatus.DRAFT,
            target=PostStatus.PUBLISHED,
            message="Only a draft can be published",
        )
        now = datetime.now(UTC)
        record.published_at = now
        record.updated_at = now
        self._posts.save(record)
        return self._to_read(record)

    def unpublish(self, actor: UserRead, slug: str) -> PostRead:
        record = self.visible_record(actor, slug)
        self._require_author(actor, record, "Only the author can unpublish this post")
        self._move(
            record,
            source=PostStatus.PUBLISHED,
            target=PostStatus.DRAFT,
            message="Only a published post can be unpublished",
        )
        record.published_at = None
        record.updated_at = datetime.now(UTC)
        self._posts.save(record)
        return self._to_read(record)

    def archive(self, actor: UserRead, slug: str) -> PostRead:
        record = self.visible_record(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.author_id:
            raise ForbiddenError("Only the author or an admin can archive this post")
        self._move(
            record,
            source=PostStatus.PUBLISHED,
            target=PostStatus.ARCHIVED,
            message="Only a published post can be archived",
        )
        record.updated_at = datetime.now(UTC)
        self._posts.save(record)
        return self._to_read(record)

    def restore(self, actor: UserRead, slug: str) -> PostRead:
        record = self.visible_record(actor, slug)
        self._require_author(actor, record, "Only the author can restore this post")
        self._move(
            record,
            source=PostStatus.ARCHIVED,
            target=PostStatus.DRAFT,
            message="Only an archived post can be restored",
        )
        record.published_at = None
        record.updated_at = datetime.now(UTC)
        self._posts.save(record)
        return self._to_read(record)

    def delete_post(self, actor: UserRead, slug: str) -> None:
        record = self.visible_record(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.author_id:
            raise ForbiddenError("Only the author or an admin can delete this post")
        self._comments.delete_for_post(record.id)
        self._posts.delete(record.id)

    def list_tags(self) -> list[TagCount]:
        counts: dict[str, int] = {}
        for post in self._posts.list_all():
            if post.status is not PostStatus.PUBLISHED:
                continue
            for tag in post.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [TagCount(name=name, post_count=counts[name]) for name in sorted(counts)]

    def _matches(
        self,
        post: PostRecord,
        *,
        tag: str | None,
        author_id: int | None,
        query: str | None,
    ) -> bool:
        if author_id is not None and post.author_id != author_id:
            return False
        if tag is not None and tag.strip().casefold() not in post.tags:
            return False
        if query is not None:
            needle = query.casefold()
            haystack = f"{post.title}\n{post.summary}\n{post.body}".casefold()
            if needle not in haystack:
                return False
        return True

    def _page(self, rows: list[PostRecord], *, limit: int, offset: int) -> PostPage:
        return PostPage(
            items=[self._to_read(post) for post in rows[offset : offset + limit]],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def _to_read(self, record: PostRecord) -> PostRead:
        author = self._users.get_by_id(record.author_id)
        return PostRead(
            id=record.id,
            title=record.title,
            slug=record.slug,
            summary=record.summary,
            body=record.body,
            status=record.status,
            tags=list(record.tags),
            author_id=record.author_id,
            author_name=author.full_name if author is not None else "Unknown",
            comment_count=self._comments.count_for_post(record.id),
            created_at=record.created_at,
            updated_at=record.updated_at,
            published_at=record.published_at,
        )

    def _require_author(self, actor: UserRead, record: PostRecord, message: str) -> None:
        if actor.id != record.author_id:
            raise ForbiddenError(message)

    def _move(
        self,
        record: PostRecord,
        *,
        source: PostStatus,
        target: PostStatus,
        message: str,
    ) -> None:
        allowed = _TRANSITIONS[record.status]
        if record.status is not source or target not in allowed:
            raise ConflictError(f"{message}. This post is {record.status.value}")
        record.status = target
