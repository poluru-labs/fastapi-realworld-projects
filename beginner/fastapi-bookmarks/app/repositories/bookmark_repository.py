from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.core.exceptions import ConflictError, NotFoundError


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _url_key(url: str) -> str:
    return url.strip().rstrip("/").lower()


@dataclass
class BookmarkRecord:
    id: int
    title: str
    url: str
    tags: list[str] = field(default_factory=list)
    note: str = ""
    pinned: bool = False
    archived: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


class BookmarkRepository:
    def __init__(self) -> None:
        now = _utcnow()
        self._records: dict[int, BookmarkRecord] = {
            1: BookmarkRecord(
                id=1,
                title="FastAPI documentation",
                url="https://fastapi.tiangolo.com/",
                tags=["python", "docs", "api"],
                note="Official reference and tutorials.",
                pinned=True,
                created_at=now,
                updated_at=now,
            ),
            2: BookmarkRecord(
                id=2,
                title="Python tutorial",
                url="https://docs.python.org/3/tutorial/",
                tags=["python", "learning"],
                created_at=now,
                updated_at=now,
            ),
        }
        self._next_id = 3
        self._url_index: dict[str, int] = {
            _url_key(r.url): r.id for r in self._records.values()
        }

    def _touch(self, record: BookmarkRecord) -> None:
        record.updated_at = _utcnow()

    def _register_url(self, url: str, bookmark_id: int) -> None:
        self._url_index[_url_key(url)] = bookmark_id

    def _unregister_url(self, url: str) -> None:
        self._url_index.pop(_url_key(url), None)

    def list_tags(self) -> list[str]:
        tags: set[str] = set()
        for r in self._records.values():
            tags.update(r.tags)
        return sorted(tags)

    def list_bookmarks(
        self,
        *,
        tag: str | None = None,
        search: str | None = None,
        pinned: bool | None = None,
        archived: bool = False,
    ) -> list[BookmarkRecord]:
        rows = [r for r in self._records.values() if r.archived == archived]
        if tag is not None:
            needle = tag.strip().lower()
            rows = [r for r in rows if needle in r.tags]
        if pinned is not None:
            rows = [r for r in rows if r.pinned == pinned]
        if search:
            q = search.strip().lower()
            rows = [
                r
                for r in rows
                if q in r.title.lower()
                or q in r.url.lower()
                or q in r.note.lower()
                or any(q in t for t in r.tags)
            ]
        rows.sort(key=lambda r: (-int(r.pinned), r.title.lower()))
        return rows

    def get(self, bookmark_id: int) -> BookmarkRecord:
        record = self._records.get(bookmark_id)
        if record is None:
            raise NotFoundError("Bookmark", bookmark_id)
        return record

    def create(
        self,
        *,
        title: str,
        url: str,
        tags: list[str],
        note: str,
        pinned: bool,
    ) -> BookmarkRecord:
        key = _url_key(url)
        if key in self._url_index:
            raise ConflictError("A bookmark with this URL already exists.")
        record = BookmarkRecord(
            id=self._next_id,
            title=title,
            url=url,
            tags=tags,
            note=note,
            pinned=pinned,
        )
        self._next_id += 1
        self._records[record.id] = record
        self._register_url(url, record.id)
        return record

    def update(
        self,
        bookmark_id: int,
        *,
        title: str | None = None,
        url: str | None = None,
        tags: list[str] | None = None,
        note: str | None = None,
        pinned: bool | None = None,
    ) -> BookmarkRecord:
        record = self.get(bookmark_id)
        if url is not None and _url_key(url) != _url_key(record.url):
            key = _url_key(url)
            if key in self._url_index and self._url_index[key] != bookmark_id:
                raise ConflictError("A bookmark with this URL already exists.")
            self._unregister_url(record.url)
            record.url = url
            self._register_url(url, bookmark_id)
        if title is not None:
            record.title = title
        if tags is not None:
            record.tags = tags
        if note is not None:
            record.note = note
        if pinned is not None:
            record.pinned = pinned
        self._touch(record)
        return record

    def set_pinned(self, bookmark_id: int, *, pinned: bool) -> BookmarkRecord:
        record = self.get(bookmark_id)
        record.pinned = pinned
        self._touch(record)
        return record

    def set_archived(self, bookmark_id: int, *, archived: bool) -> BookmarkRecord:
        record = self.get(bookmark_id)
        record.archived = archived
        self._touch(record)
        return record

    def delete(self, bookmark_id: int) -> None:
        record = self.get(bookmark_id)
        self._unregister_url(record.url)
        del self._records[bookmark_id]


@lru_cache
def get_bookmark_repository() -> BookmarkRepository:
    return BookmarkRepository()
