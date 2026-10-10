"""Event visibility, publish workflow, and admin edits live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.event_repository import EventRecord, EventRepository
from app.repositories.registration_repository import RegistrationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.event import EventCreate, EventRead, EventStatus, EventUpdate, TagCount, slugify
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.DRAFT: {EventStatus.PUBLISHED, EventStatus.CANCELLED},
    EventStatus.PUBLISHED: {EventStatus.DRAFT, EventStatus.CANCELLED},
    EventStatus.CANCELLED: set(),
}


def _can_view(actor: UserRead | None, record: EventRecord) -> bool:
    if record.status is EventStatus.PUBLISHED:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == record.organizer_id


class EventService:
    def __init__(
        self,
        *,
        events: EventRepository,
        registrations: RegistrationRepository,
        users: UserRepository,
    ) -> None:
        self._events = events
        self._registrations = registrations
        self._users = users

    def list_events(
        self,
        actor: UserRead | None,
        *,
        status: EventStatus | None,
        tag: str | None,
        query: str | None,
    ) -> list[EventRead]:
        rows = self._events.list_all()
        if actor is None or actor.role is not UserRole.ADMIN:
            rows = [event for event in rows if event.status is EventStatus.PUBLISHED]
        elif status is not None:
            rows = [event for event in rows if event.status is status]

        if tag is not None:
            needle = tag.strip().casefold()
            if needle:
                rows = [event for event in rows if needle in event.tags]
        if query is not None:
            needle = query.strip().casefold()
            if needle:
                rows = [
                    event
                    for event in rows
                    if needle in event.title.casefold()
                    or needle in event.summary.casefold()
                    or needle in event.location.casefold()
                ]

        rows.sort(key=lambda event: (event.starts_at, event.id))
        return [self._to_read(event) for event in rows]

    def get_event(self, actor: UserRead | None, slug: str) -> EventRead:
        return self._to_read(self.visible_record(actor, slug))

    def visible_record(self, actor: UserRead | None, slug: str) -> EventRecord:
        record = self._events.get_by_slug(slug)
        if record is None or not _can_view(actor, record):
            raise NotFoundError("Event", slug)
        return record

    def create_event(self, actor: UserRead, payload: EventCreate) -> EventRead:
        self._require_admin(actor, "Only a platform admin can create events")
        slug = payload.slug or slugify(payload.title)
        if not slug:
            raise ConflictError("Could not derive a slug from the title")
        if self._events.slug_taken(slug):
            raise ConflictError("Another event already uses this slug")
        now = datetime.now(UTC)
        record = EventRecord(
            id=self._events.allocate_id(),
            slug=slug,
            title=payload.title,
            summary=payload.summary,
            description=payload.description,
            location=payload.location,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            capacity=payload.capacity,
            status=EventStatus.DRAFT,
            organizer_id=actor.id,
            tags=payload.tags,
            created_at=now,
            updated_at=now,
            published_at=None,
        )
        self._events.add(record)
        return self._to_read(record)

    def update_event(self, actor: UserRead, slug: str, payload: EventUpdate) -> EventRead:
        self._require_admin(actor, "Only a platform admin can update events")
        record = self._require_event(slug)
        if record.status is not EventStatus.DRAFT:
            raise ConflictError("Only draft events can be edited")
        changes = payload.model_dump(exclude_unset=True)
        if "title" in changes:
            record.title = changes["title"]
        if "summary" in changes:
            record.summary = changes["summary"]
        if "description" in changes:
            record.description = changes["description"]
        if "location" in changes:
            record.location = changes["location"]
        if "starts_at" in changes:
            record.starts_at = changes["starts_at"]
        if "ends_at" in changes:
            record.ends_at = changes["ends_at"]
        if "capacity" in changes:
            registered = self._registrations.count_registered(record.id)
            if changes["capacity"] < registered:
                raise ConflictError("Capacity cannot be below current registered count")
            record.capacity = changes["capacity"]
        if "tags" in changes:
            record.tags = changes["tags"]
        if record.ends_at <= record.starts_at:
            raise ConflictError("ends_at must be after starts_at")
        record.updated_at = datetime.now(UTC)
        self._events.save(record)
        return self._to_read(record)

    def transition(self, actor: UserRead, slug: str, target: EventStatus) -> EventRead:
        self._require_admin(actor, "Only a platform admin can change event status")
        record = self._require_event(slug)
        allowed = _TRANSITIONS.get(record.status, set())
        if target not in allowed:
            raise ConflictError(f"Cannot move from {record.status.value} to {target.value}")
        if target is EventStatus.DRAFT and self._has_active_registrations(record.id):
            raise ConflictError("Unpublish blocked while registrations or waitlist entries exist")
        now = datetime.now(UTC)
        record.status = target
        record.updated_at = now
        if target is EventStatus.PUBLISHED:
            record.published_at = now
        if target is EventStatus.CANCELLED:
            self._cancel_all_active_registrations(record.id)
        self._events.save(record)
        return self._to_read(record)

    def list_tags(self) -> list[TagCount]:
        counts: dict[str, int] = {}
        for event in self._events.list_all():
            if event.status is not EventStatus.PUBLISHED:
                continue
            for tag in event.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [TagCount(name=name, count=count) for name, count in sorted(counts.items())]

    def _cancel_all_active_registrations(self, event_id: int) -> None:
        from app.schemas.registration import RegistrationStatus

        for row in self._registrations.list_for_event(event_id):
            if row.status in (RegistrationStatus.REGISTERED, RegistrationStatus.WAITLISTED):
                row.status = RegistrationStatus.CANCELLED
                self._registrations.save(row)

    def _has_active_registrations(self, event_id: int) -> bool:
        from app.schemas.registration import RegistrationStatus

        return any(
            row.status in (RegistrationStatus.REGISTERED, RegistrationStatus.WAITLISTED)
            for row in self._registrations.list_for_event(event_id)
        )

    def _require_event(self, slug: str) -> EventRecord:
        record = self._events.get_by_slug(slug)
        if record is None:
            raise NotFoundError("Event", slug)
        return record

    def _to_read(self, record: EventRecord) -> EventRead:
        organizer = self._users.get_by_id(record.organizer_id)
        organizer_name = organizer.full_name if organizer else "Unknown"
        registered = self._registrations.count_registered(record.id)
        waitlist = self._registrations.count_waitlisted(record.id)
        return EventRead(
            id=record.id,
            slug=record.slug,
            title=record.title,
            summary=record.summary,
            description=record.description,
            location=record.location,
            starts_at=record.starts_at,
            ends_at=record.ends_at,
            capacity=record.capacity,
            status=record.status,
            organizer_id=record.organizer_id,
            organizer_name=organizer_name,
            tags=record.tags,
            registered_count=registered,
            waitlist_count=waitlist,
            seats_available=max(0, record.capacity - registered),
            created_at=record.created_at,
            updated_at=record.updated_at,
            published_at=record.published_at,
        )

    @staticmethod
    def _require_admin(actor: UserRead, message: str) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError(message)
