from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.event_repository import EventRepository
from app.schemas.event import (
    EventCreate,
    EventDetail,
    EventRead,
    EventStatus,
    EventUpdate,
    RegistrationCreate,
    RegistrationRead,
)


class EventService:
    def __init__(self, repository: EventRepository) -> None:
        self._repo = repository

    def list_events(
        self,
        *,
        status: EventStatus | None,
        starts_after: datetime | None,
        starts_before: datetime | None,
        q: str | None,
    ) -> list[EventRead]:
        rows = self._repo.list_events()
        if status is not None:
            rows = [event for event in rows if event.status is status]
        if starts_after is not None:
            rows = [event for event in rows if event.starts_at >= starts_after]
        if starts_before is not None:
            rows = [event for event in rows if event.starts_at <= starts_before]
        if q:
            needle = q.casefold()
            rows = [
                event
                for event in rows
                if needle in event.title.casefold() or needle in event.description.casefold()
            ]
        rows.sort(key=lambda event: event.starts_at)
        return [self._event_read(event) for event in rows]

    def get_event_detail(self, event_id: int) -> EventDetail:
        event = self._require_event(event_id)
        regs = self._repo.list_registrations(event_id)
        return EventDetail(
            **self._event_read(event).model_dump(),
            registrations=[self._registration_read(reg) for reg in regs],
        )

    def create_event(self, payload: EventCreate) -> EventRead:
        record = self._repo.create_event(
            title=payload.title,
            description=payload.description,
            location=payload.location,
            starts_at=self._ensure_aware(payload.starts_at),
            ends_at=self._ensure_aware(payload.ends_at),
            max_attendees=payload.max_attendees,
        )
        return self._event_read(record)

    def update_event(self, event_id: int, payload: EventUpdate) -> EventRead:
        fields = payload.model_dump(exclude_unset=True)
        max_set = "max_attendees" in fields
        try:
            record = self._repo.update_event(
                event_id,
                title=fields.get("title"),
                description=fields.get("description"),
                location=fields.get("location"),
                starts_at=self._ensure_aware(fields["starts_at"])
                if fields.get("starts_at") is not None
                else None,
                ends_at=self._ensure_aware(fields["ends_at"])
                if fields.get("ends_at") is not None
                else None,
                max_attendees=fields.get("max_attendees"),
                max_attendees_set=max_set,
            )
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        if record is None:
            raise NotFoundError("Event", event_id)
        return self._event_read(record)

    def delete_event(self, event_id: int) -> None:
        if self._repo.delete_event(event_id) is None:
            raise NotFoundError("Event", event_id)

    def cancel_event(self, event_id: int) -> EventRead:
        record = self._repo.get_event(event_id)
        if record is None:
            raise NotFoundError("Event", event_id)
        if record.status is EventStatus.CANCELLED:
            raise ConflictError("Event is already cancelled")
        updated = self._repo.cancel_event(event_id)
        assert updated is not None
        return self._event_read(updated)

    def list_registrations(self, event_id: int) -> list[RegistrationRead]:
        self._require_event(event_id)
        return [self._registration_read(reg) for reg in self._repo.list_registrations(event_id)]

    def register(self, event_id: int, payload: RegistrationCreate) -> RegistrationRead:
        event = self._require_event(event_id)
        if event.status is EventStatus.CANCELLED:
            raise ConflictError("Cancelled events do not accept registrations")
        if self._repo.email_registered(event_id, payload.email):
            raise ConflictError("This email is already registered for the event")
        if event.max_attendees is not None:
            if self._repo.registration_count(event_id) >= event.max_attendees:
                raise ConflictError("Event is at capacity")
        record = self._repo.add_registration(
            event_id,
            name=payload.name,
            email=str(payload.email),
        )
        if record is None:
            raise NotFoundError("Event", event_id)
        return self._registration_read(record)

    def _require_event(self, event_id: int):
        event = self._repo.get_event(event_id)
        if event is None:
            raise NotFoundError("Event", event_id)
        return event

    def _event_read(self, event) -> EventRead:
        return EventRead(
            id=event.id,
            title=event.title,
            description=event.description,
            location=event.location,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            status=event.status,
            max_attendees=event.max_attendees,
            registration_count=self._repo.registration_count(event.id),
        )

    @staticmethod
    def _registration_read(reg) -> RegistrationRead:
        return RegistrationRead(
            id=reg.id,
            event_id=reg.event_id,
            name=reg.name,
            email=reg.email,
            registered_at=reg.registered_at,
        )

    @staticmethod
    def _ensure_aware(when: datetime) -> datetime:
        if when.tzinfo is None:
            return when.replace(tzinfo=UTC)
        return when
