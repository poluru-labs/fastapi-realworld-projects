"""Registration capacity, waitlist, and ownership rules live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.event_repository import EventRepository
from app.repositories.registration_repository import RegistrationRecord, RegistrationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.event import EventStatus
from app.schemas.registration import RegistrationCreate, RegistrationRead, RegistrationStatus
from app.schemas.user import UserRead, UserRole
from app.services.event_service import _can_view


class RegistrationService:
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

    def list_registrations(
        self,
        actor: UserRead,
        *,
        event_id: int | None,
        status: RegistrationStatus | None,
    ) -> list[RegistrationRead]:
        if actor.role is UserRole.ADMIN:
            rows = self._registrations.list_all()
            if event_id is not None:
                rows = [row for row in rows if row.event_id == event_id]
        else:
            rows = self._registrations.list_for_user(actor.id)
            if event_id is not None:
                rows = [row for row in rows if row.event_id == event_id]

        if status is not None:
            rows = [row for row in rows if row.status is status]

        rows.sort(key=lambda row: (row.created_at, row.id))
        return [self._to_read(row) for row in rows]

    def list_for_event_slug(self, actor: UserRead, slug: str) -> list[RegistrationRead]:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only a platform admin can list every attendee for an event")
        event = self._events.get_by_slug(slug)
        if event is None:
            raise NotFoundError("Event", slug)
        return self.list_registrations(actor, event_id=event.id, status=None)

    def get_registration(self, actor: UserRead, registration_id: int) -> RegistrationRead:
        row = self._registrations.get(registration_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Registration", registration_id)
        return self._to_read(row)

    def register(self, actor: UserRead, payload: RegistrationCreate) -> RegistrationRead:
        event = self._events.get_by_slug(payload.event_slug)
        if event is None or not _can_view(actor, event):
            raise NotFoundError("Event", payload.event_slug)
        if event.status is not EventStatus.PUBLISHED:
            raise ConflictError("Registrations are only open for published events")

        existing = self._registrations.active_for_user_event(
            user_id=actor.id,
            event_id=event.id,
        )
        if existing is not None:
            raise ConflictError("You already have an active registration for this event")

        registered_count = self._registrations.count_registered(event.id)
        status = (
            RegistrationStatus.REGISTERED
            if registered_count < event.capacity
            else RegistrationStatus.WAITLISTED
        )
        now = datetime.now(UTC)
        record = RegistrationRecord(
            id=self._registrations.allocate_id(),
            event_id=event.id,
            user_id=actor.id,
            status=status,
            created_at=now,
        )
        self._registrations.add(record)
        return self._to_read(record)

    def cancel(self, actor: UserRead, registration_id: int) -> RegistrationRead:
        row = self._registrations.get(registration_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Registration", registration_id)

        if row.status is RegistrationStatus.CANCELLED:
            raise ConflictError("Registration is already cancelled")

        if actor.role is not UserRole.ADMIN and row.user_id != actor.id:
            raise ForbiddenError()

        was_registered = row.status is RegistrationStatus.REGISTERED
        row.status = RegistrationStatus.CANCELLED
        self._registrations.save(row)

        if was_registered:
            self._promote_waitlist(row.event_id)

        return self._to_read(row)

    def _promote_waitlist(self, event_id: int) -> None:
        event = self._events.get(event_id)
        if event is None:
            return
        if self._registrations.count_registered(event_id) >= event.capacity:
            return
        next_wait = self._registrations.oldest_waitlisted(event_id)
        if next_wait is None:
            return
        next_wait.status = RegistrationStatus.REGISTERED
        self._registrations.save(next_wait)

    def _can_view(self, actor: UserRead, row: RegistrationRecord) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return row.user_id == actor.id

    def _to_read(self, row: RegistrationRecord) -> RegistrationRead:
        event = self._events.get(row.event_id)
        user = self._users.get_by_id(row.user_id)
        return RegistrationRead(
            id=row.id,
            event_id=row.event_id,
            event_slug=event.slug if event else "unknown",
            event_title=event.title if event else "Unknown event",
            user_id=row.user_id,
            attendee_name=user.full_name if user else "Unknown",
            status=row.status,
            created_at=row.created_at,
        )
