from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.event import EventStatus


@dataclass
class EventRecord:
    id: int
    slug: str
    title: str
    summary: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    status: EventStatus
    organizer_id: int
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    published_at: datetime | None = None


def _seed_events() -> dict[int, EventRecord]:
    return {
        1: EventRecord(
            id=1,
            slug="fastapi-meetup",
            title="FastAPI Meetup",
            summary="An evening of API design tips.",
            description="Talks on OpenAPI, dependency injection, and testing.",
            location="Community Hall A",
            starts_at=datetime.fromisoformat("2026-11-15T18:00:00+00:00"),
            ends_at=datetime.fromisoformat("2026-11-15T21:00:00+00:00"),
            capacity=2,
            status=EventStatus.PUBLISHED,
            organizer_id=1,
            tags=["fastapi", "meetup"],
            created_at=datetime.fromisoformat("2026-10-01T12:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-10-05T12:00:00+00:00"),
            published_at=datetime.fromisoformat("2026-10-05T12:00:00+00:00"),
        ),
        2: EventRecord(
            id=2,
            slug="draft-planning-session",
            title="Draft planning session",
            summary="Not visible to the public yet.",
            description="Internal run-through.",
            location="Online",
            starts_at=datetime.fromisoformat("2026-12-01T15:00:00+00:00"),
            ends_at=datetime.fromisoformat("2026-12-01T16:00:00+00:00"),
            capacity=20,
            status=EventStatus.DRAFT,
            organizer_id=1,
            tags=["internal"],
            created_at=datetime.fromisoformat("2026-10-02T12:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-10-02T12:00:00+00:00"),
            published_at=None,
        ),
    }


class EventRepository:
    def __init__(self) -> None:
        self._events = dict(_seed_events())
        self._by_slug = {event.slug: event for event in self._events.values()}
        self._next_id = max(self._events.keys(), default=0) + 1

    def list_all(self) -> list[EventRecord]:
        return list(self._events.values())

    def get(self, event_id: int) -> EventRecord | None:
        return self._events.get(event_id)

    def get_by_slug(self, slug: str) -> EventRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str, *, except_id: int | None = None) -> bool:
        existing = self._by_slug.get(slug)
        if existing is None:
            return False
        if except_id is not None and existing.id == except_id:
            return False
        return True

    def add(self, record: EventRecord) -> EventRecord:
        self._events[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: EventRecord) -> None:
        previous = self._events.get(record.id)
        if previous is not None and previous.slug != record.slug:
            self._by_slug.pop(previous.slug, None)
        self._events[record.id] = record
        self._by_slug[record.slug] = record

    def allocate_id(self) -> int:
        event_id = self._next_id
        self._next_id += 1
        return event_id
