from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from functools import lru_cache

from app.core.exceptions import ConflictError, NotFoundError


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class EntryRecord:
    id: int
    entry_date: date
    title: str
    body: str
    mood: str | None
    tags: list[str] = field(default_factory=list)
    starred: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


class EntryRepository:
    def __init__(self) -> None:
        now = _utcnow()
        self._records: dict[int, EntryRecord] = {
            1: EntryRecord(
                id=1,
                entry_date=date(2026, 10, 14),
                title="Shipped the habit tracker",
                body="Finished wiring tests and OpenAPI examples. Felt productive.",
                mood="great",
                tags=["work", "fastapi"],
                starred=True,
                created_at=now,
                updated_at=now,
            ),
            2: EntryRecord(
                id=2,
                entry_date=date(2026, 10, 15),
                title="Reading day",
                body="Slow afternoon. Caught up on docs instead of coding.",
                mood="okay",
                tags=["learning"],
                created_at=now,
                updated_at=now,
            ),
        }
        self._by_date: dict[date, int] = {r.entry_date: r.id for r in self._records.values()}
        self._next_id = 3

    def _touch(self, record: EntryRecord) -> None:
        record.updated_at = _utcnow()

    def list_tags(self) -> list[str]:
        tags: set[str] = set()
        for r in self._records.values():
            tags.update(r.tags)
        return sorted(tags)

    def list_entries(
        self,
        *,
        tag: str | None,
        mood: str | None,
        search: str | None,
        starred: bool | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[EntryRecord]:
        rows = list(self._records.values())
        if tag is not None:
            needle = tag.strip().lower()
            rows = [r for r in rows if needle in r.tags]
        if mood is not None:
            rows = [r for r in rows if r.mood == mood.strip().lower()]
        if starred is not None:
            rows = [r for r in rows if r.starred == starred]
        if date_from is not None:
            rows = [r for r in rows if r.entry_date >= date_from]
        if date_to is not None:
            rows = [r for r in rows if r.entry_date <= date_to]
        if search:
            q = search.strip().lower()
            rows = [
                r
                for r in rows
                if q in r.title.lower()
                or q in r.body.lower()
                or any(q in t for t in r.tags)
            ]
        rows.sort(key=lambda r: (-int(r.starred), -r.entry_date.toordinal(), -r.id))
        return rows

    def get(self, entry_id: int) -> EntryRecord:
        record = self._records.get(entry_id)
        if record is None:
            raise NotFoundError("Entry", entry_id)
        return record

    def get_by_date(self, entry_date: date) -> EntryRecord | None:
        entry_id = self._by_date.get(entry_date)
        if entry_id is None:
            return None
        return self._records.get(entry_id)

    def create(
        self,
        *,
        entry_date: date,
        title: str,
        body: str,
        mood: str | None,
        tags: list[str],
        starred: bool,
    ) -> EntryRecord:
        if entry_date in self._by_date:
            raise ConflictError(f"An entry already exists for {entry_date.isoformat()}")
        record = EntryRecord(
            id=self._next_id,
            entry_date=entry_date,
            title=title,
            body=body,
            mood=mood,
            tags=tags,
            starred=starred,
        )
        self._next_id += 1
        self._records[record.id] = record
        self._by_date[entry_date] = record.id
        return record

    def mark_updated(self, record: EntryRecord) -> None:
        self._touch(record)

    def set_starred(self, entry_id: int, *, starred: bool) -> EntryRecord:
        record = self.get(entry_id)
        record.starred = starred
        self._touch(record)
        return record

    def delete(self, entry_id: int) -> None:
        record = self.get(entry_id)
        self._by_date.pop(record.entry_date, None)
        del self._records[entry_id]


@lru_cache
def get_entry_repository() -> EntryRepository:
    return EntryRepository()
