from dataclasses import dataclass
from datetime import datetime


@dataclass
class CommentRecord:
    id: int
    post_id: int
    author_id: int
    body: str
    created_at: datetime


def _seed_comments() -> dict[int, CommentRecord]:
    return {
        1: CommentRecord(
            id=1,
            post_id=1,
            author_id=1,
            body="Publish first. Comments on a draft return 409.",
            created_at=datetime.fromisoformat("2026-03-01T16:00:00+00:00"),
        ),
    }


class CommentRepository:
    """In-memory comments. Deleted with their post."""

    def __init__(self) -> None:
        self._comments = dict(_seed_comments())
        self._next_id = max(self._comments.keys(), default=0) + 1

    def list_for_post(self, post_id: int) -> list[CommentRecord]:
        rows = [comment for comment in self._comments.values() if comment.post_id == post_id]
        return sorted(rows, key=lambda comment: (comment.created_at, comment.id))

    def get(self, comment_id: int) -> CommentRecord | None:
        return self._comments.get(comment_id)

    def count_for_post(self, post_id: int) -> int:
        return sum(1 for comment in self._comments.values() if comment.post_id == post_id)

    def allocate_id(self) -> int:
        comment_id = self._next_id
        self._next_id += 1
        return comment_id

    def add(self, record: CommentRecord) -> CommentRecord:
        self._comments[record.id] = record
        return record

    def delete(self, comment_id: int) -> None:
        self._comments.pop(comment_id, None)

    def delete_for_post(self, post_id: int) -> None:
        doomed = [
            comment_id
            for comment_id, comment in self._comments.items()
            if comment.post_id == post_id
        ]
        for comment_id in doomed:
            del self._comments[comment_id]
