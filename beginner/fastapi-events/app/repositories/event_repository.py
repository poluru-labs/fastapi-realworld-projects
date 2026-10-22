from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.schemas.event import EventStatus


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class EventRecord:
    id: int
    title: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    status: EventStatus
    max_attendees: int | None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class RegistrationRecord:
    id: int
    event_id: int
    name: str
    email: str
    registered_at: datetime = field(default_factory=_utcnow)


def _seed() -> tuple[dict[int, EventRecord], dict[int, RegistrationRecord]]:
    events = {
        1: EventRecord(
            id=1,
            title="Python meetup",
            description="Lightning talks and networking for local developers.",
            location="Community hub — main hall",
            starts_at=datetime.fromisoformat("2026-04-10T17:30:00+00:00"),
            ends_at=datetime.fromisoformat("2026-04-10T20:00:00+00:00"),
            status=EventStatus.SCHEDULED,
            max_attendees=50,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        ),
        2: EventRecord(
            id=2,
            title="Cancelled workshop",
            description="This session was called off — kept as a seed for status filters.",
            location="Online",
            starts_at=datetime.fromisoformat("2026-03-01T14:00:00+00:00"),
            ends_at=datetime.fromisoformat("2026-03-01T16:00:00+00:00"),
            status=EventStatus.CANCELLED,
            max_attendees=30,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        ),
        3: EventRecord(
            id=3,
            title="Open house",
            description="Drop in anytime during the window.",
            location="Campus lab 204",
            starts_at=datetime.fromisoformat("2026-05-01T10:00:00+00:00"),
            ends_at=datetime.fromisoformat("2026-05-01T12:00:00+00:00"),
            status=EventStatus.SCHEDULED,
            max_attendees=None,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        ),
    }
    registrations = {
        1: RegistrationRecord(
            id=1,
            event_id=1,
            name="Alex Rivera",
            email="alex@example.com",
            registered_at=datetime.fromisoformat("2026-03-15T09:00:00+00:00"),
        ),
        2: RegistrationRecord(
            id=2,
            event_id=1,
            name="Sam Lee",
            email="sam@example.com",
            registered_at=datetime.fromisoformat("2026-03-16T11:00:00+00:00"),
        ),
    }
    return events, registrations


class EventRepository:
    """In-memory events and registrations."""

    def __init__(self) -> None:
        self._events, self._registrations = _seed()
        self._next_event_id = max(self._events.keys(), default=0) + 1
        self._next_registration_id = max(self._registrations.keys(), default=0) + 1

    def list_events(self) -> list[EventRecord]:
        return list(self._events.values())

    def get_event(self, event_id: int) -> EventRecord | None:
        return self._events.get(event_id)

    def create_event(
        self,
        *,
        title: str,
        description: str,
        location: str,
        starts_at: datetime,
        ends_at: datetime,
        max_attendees: int | None,
    ) -> EventRecord:
        event_id = self._next_event_id
        self._next_event_id += 1
        record = EventRecord(
            id=event_id,
            title=title,
            description=description,
            location=location,
            starts_at=starts_at,
            ends_at=ends_at,
            status=EventStatus.SCHEDULED,
            max_attendees=max_attendees,
        )
        self._events[event_id] = record
        return record

    def update_event(
        self,
        event_id: int,
        *,
        title: str | None,
        description: str | None,
        location: str | None,
        starts_at: datetime | None,
        ends_at: datetime | None,
        max_attendees: int | None,
        max_attendees_set: bool,
    ) -> EventRecord | None:
        record = self._events.get(event_id)
        if record is None:
            return None
        if title is not None:
            record.title = title
        if description is not None:
            record.description = description
        if location is not None:
            record.location = location
        if starts_at is not None:
            record.starts_at = starts_at
        if ends_at is not None:
            record.ends_at = ends_at
        if max_attendees_set:
            record.max_attendees = max_attendees
        if record.ends_at <= record.starts_at:
            raise ValueError("ends_at must be after starts_at")
        record.updated_at = _utcnow()
        return record

    def delete_event(self, event_id: int) -> EventRecord | None:
        record = self._events.pop(event_id, None)
        if record is None:
            return None
        to_remove = [
            reg_id for reg_id, reg in self._registrations.items() if reg.event_id == event_id
        ]
        for reg_id in to_remove:
            del self._registrations[reg_id]
        return record

    def cancel_event(self, event_id: int) -> EventRecord | None:
        record = self._events.get(event_id)
        if record is None:
            return None
        record.status = EventStatus.CANCELLED
        record.updated_at = _utcnow()
        return record

    def list_registrations(self, event_id: int) -> list[RegistrationRecord]:
        rows = [reg for reg in self._registrations.values() if reg.event_id == event_id]
        rows.sort(key=lambda reg: reg.registered_at)
        return rows

    def registration_count(self, event_id: int) -> int:
        return len(self.list_registrations(event_id))

    def email_registered(self, event_id: int, email: str) -> bool:
        target = email.lower()
        return any(
            reg.event_id == event_id and reg.email.lower() == target
            for reg in self._registrations.values()
        )

    def add_registration(
        self,
        event_id: int,
        *,
        name: str,
        email: str,
    ) -> RegistrationRecord | None:
        if event_id not in self._events:
            return None
        reg_id = self._next_registration_id
        self._next_registration_id += 1
        record = RegistrationRecord(
            id=reg_id,
            event_id=event_id,
            name=name,
            email=email.lower(),
        )
        self._registrations[reg_id] = record
        self._events[event_id].updated_at = _utcnow()
        return record


@lru_cache
def get_event_repository() -> EventRepository:
    return EventRepository()
