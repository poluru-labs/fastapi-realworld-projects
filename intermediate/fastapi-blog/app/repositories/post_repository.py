from dataclasses import dataclass
from datetime import datetime

from app.schemas.post import PostStatus


@dataclass
class PostRecord:
    id: int
    author_id: int
    title: str
    slug: str
    summary: str
    body: str
    status: PostStatus
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


def _seed_posts() -> dict[int, PostRecord]:
    published_at = datetime.fromisoformat("2026-03-01T15:00:00+00:00")
    drafted_at = datetime.fromisoformat("2026-03-02T15:00:00+00:00")
    return {
        1: PostRecord(
            id=1,
            author_id=1,
            title="Writing APIs that teach",
            slug="writing-apis-that-teach",
            summary="Public posts, private drafts, and comments.",
            body=(
                "A published post is readable without a token. "
                "A draft is visible to its author and to admins."
            ),
            status=PostStatus.PUBLISHED,
            tags=["fastapi", "docs"],
            created_at=published_at,
            updated_at=published_at,
            published_at=published_at,
        ),
        2: PostRecord(
            id=2,
            author_id=1,
            title="Draft pagination notes",
            slug="draft-pagination-notes",
            summary="Not on the public list.",
            body="This draft exists so you can see a 404 without a token.",
            status=PostStatus.DRAFT,
            tags=["pagination"],
            created_at=drafted_at,
            updated_at=drafted_at,
            published_at=None,
        ),
    }


class PostRepository:
    """In-memory posts keyed by id and slug. A restart drops everything except the seed."""

    def __init__(self) -> None:
        self._by_id = dict(_seed_posts())
        self._by_slug = {post.slug: post for post in self._by_id.values()}
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_all(self) -> list[PostRecord]:
        return list(self._by_id.values())

    def get_by_slug(self, slug: str) -> PostRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str) -> bool:
        return slug in self._by_slug

    def allocate_id(self) -> int:
        post_id = self._next_id
        self._next_id += 1
        return post_id

    def add(self, record: PostRecord) -> PostRecord:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: PostRecord) -> None:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record

    def delete(self, post_id: int) -> None:
        record = self._by_id.pop(post_id, None)
        if record is not None:
            self._by_slug.pop(record.slug, None)
