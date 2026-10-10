"""Booking rules, overlap checks, and status transitions live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.appointment_repository import AppointmentRecord, AppointmentRepository
from app.repositories.provider_repository import ProviderRecord, ProviderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.appointment import (
    MAX_DURATION_HOURS,
    MIN_DURATION_MINUTES,
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.schemas.provider import ProviderCreate, ProviderRead, ProviderUpdate
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CONFIRMED: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED},
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
}


def _intervals_overlap(
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> bool:
    return a_start < b_end and b_start < a_end


class AppointmentService:
    def __init__(
        self,
        *,
        providers: ProviderRepository,
        appointments: AppointmentRepository,
        users: UserRepository,
    ) -> None:
        self._providers = providers
        self._appointments = appointments
        self._users = users

    def list_providers(
        self,
        actor: UserRead,
        *,
        include_inactive: bool,
    ) -> list[ProviderRead]:
        if include_inactive and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only a platform admin can include inactive providers")
        rows = self._providers.list_all()
        if not include_inactive:
            rows = [provider for provider in rows if provider.is_active]
        rows.sort(key=lambda provider: provider.id)
        return [self._provider_read(row) for row in rows]

    def create_provider(self, actor: UserRead, payload: ProviderCreate) -> ProviderRead:
        self._require_admin(actor, "Only a platform admin can add providers")
        record = self._providers.add(
            ProviderRecord(
                id=self._providers.allocate_id(),
                name=payload.name,
                specialty=payload.specialty,
                is_active=True,
            )
        )
        return self._provider_read(record)

    def get_provider(self, actor: UserRead, provider_id: int) -> ProviderRead:
        record = self._require_provider(provider_id)
        if not record.is_active and actor.role is not UserRole.ADMIN:
            raise NotFoundError("Provider", provider_id)
        return self._provider_read(record)

    def update_provider(
        self,
        actor: UserRead,
        provider_id: int,
        payload: ProviderUpdate,
    ) -> ProviderRead:
        self._require_admin(actor, "Only a platform admin can update providers")
        record = self._require_provider(provider_id)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes:
            record.name = changes["name"]
        if "specialty" in changes:
            record.specialty = changes["specialty"]
        self._providers.save(record)
        return self._provider_read(record)

    def deactivate_provider(self, actor: UserRead, provider_id: int) -> ProviderRead:
        self._require_admin(actor, "Only a platform admin can deactivate providers")
        record = self._require_provider(provider_id)
        record.is_active = False
        self._providers.save(record)
        return self._provider_read(record)

    def activate_provider(self, actor: UserRead, provider_id: int) -> ProviderRead:
        self._require_admin(actor, "Only a platform admin can activate providers")
        record = self._require_provider(provider_id)
        record.is_active = True
        self._providers.save(record)
        return self._provider_read(record)

    def list_appointments(
        self,
        actor: UserRead,
        *,
        status: AppointmentStatus | None,
        provider_id: int | None,
        user_id: int | None,
        from_time: datetime | None,
        to_time: datetime | None,
    ) -> list[AppointmentRead]:
        rows = self._appointments.list_all()
        if actor.role is not UserRole.ADMIN:
            rows = [row for row in rows if row.user_id == actor.id]
        elif user_id is not None:
            rows = [row for row in rows if row.user_id == user_id]
        if status is not None:
            rows = [row for row in rows if row.status is status]
        if provider_id is not None:
            rows = [row for row in rows if row.provider_id == provider_id]
        if from_time is not None:
            rows = [row for row in rows if row.ends_at >= from_time]
        if to_time is not None:
            rows = [row for row in rows if row.starts_at <= to_time]
        rows.sort(key=lambda row: (row.starts_at, row.id))
        return [self._appointment_read(row) for row in rows]

    def get_appointment(self, actor: UserRead, appointment_id: int) -> AppointmentRead:
        return self._appointment_read(self._visible_appointment(actor, appointment_id))

    def book_appointment(self, actor: UserRead, payload: AppointmentCreate) -> AppointmentRead:
        provider = self._active_provider(payload.provider_id)
        self._assert_no_overlap(
            provider_id=provider.id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            except_id=None,
        )
        now = datetime.now(UTC)
        record = self._appointments.add(
            AppointmentRecord(
                id=self._appointments.allocate_id(),
                user_id=actor.id,
                provider_id=provider.id,
                title=payload.title,
                notes=payload.notes,
                status=AppointmentStatus.SCHEDULED,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
                created_at=now,
            )
        )
        return self._appointment_read(record)

    def update_appointment(
        self,
        actor: UserRead,
        appointment_id: int,
        payload: AppointmentUpdate,
    ) -> AppointmentRead:
        record = self._visible_appointment(actor, appointment_id)
        self._require_owner_or_admin(actor, record, "Only the client or an admin can edit this")
        if record.status is not AppointmentStatus.SCHEDULED:
            raise ConflictError("Only scheduled appointments can be edited")
        changes = payload.model_dump(exclude_unset=True)
        starts = changes.get("starts_at", record.starts_at)
        ends = changes.get("ends_at", record.ends_at)
        if ends <= starts:
            raise ConflictError("ends_at must be after starts_at")
        self._validate_duration(starts, ends)
        if "starts_at" in changes or "ends_at" in changes:
            self._assert_no_overlap(
                provider_id=record.provider_id,
                starts_at=starts,
                ends_at=ends,
                except_id=record.id,
            )
        if "title" in changes:
            record.title = changes["title"]
        if "notes" in changes:
            record.notes = changes["notes"]
        record.starts_at = starts
        record.ends_at = ends
        self._appointments.save(record)
        return self._appointment_read(record)

    def confirm_appointment(self, actor: UserRead, appointment_id: int) -> AppointmentRead:
        return self._transition(
            actor,
            appointment_id,
            target=AppointmentStatus.CONFIRMED,
            admin_only=True,
            message="Only a platform admin can confirm appointments",
        )

    def complete_appointment(self, actor: UserRead, appointment_id: int) -> AppointmentRead:
        return self._transition(
            actor,
            appointment_id,
            target=AppointmentStatus.COMPLETED,
            admin_only=True,
            message="Only a platform admin can complete appointments",
        )

    def cancel_appointment(self, actor: UserRead, appointment_id: int) -> AppointmentRead:
        record = self._visible_appointment(actor, appointment_id)
        if actor.role is not UserRole.ADMIN and actor.id != record.user_id:
            raise ForbiddenError("Only the client or an admin can cancel this appointment")
        return self._transition(
            actor,
            appointment_id,
            target=AppointmentStatus.CANCELLED,
            admin_only=False,
            message="",
            record=record,
        )

    def _transition(
        self,
        actor: UserRead,
        appointment_id: int,
        *,
        target: AppointmentStatus,
        admin_only: bool,
        message: str,
        record: AppointmentRecord | None = None,
    ) -> AppointmentRead:
        if admin_only:
            self._require_admin(actor, message)
        row = record or self._visible_appointment(actor, appointment_id)
        allowed = _TRANSITIONS[row.status]
        if target not in allowed:
            raise ConflictError(
                f"Cannot move an appointment from {row.status.value} to {target.value}"
            )
        row.status = target
        self._appointments.save(row)
        return self._appointment_read(row)

    def _assert_no_overlap(
        self,
        *,
        provider_id: int,
        starts_at: datetime,
        ends_at: datetime,
        except_id: int | None,
    ) -> None:
        for existing in self._appointments.list_all():
            if existing.provider_id != provider_id:
                continue
            if existing.id == except_id:
                continue
            if existing.status is AppointmentStatus.CANCELLED:
                continue
            if _intervals_overlap(starts_at, ends_at, existing.starts_at, existing.ends_at):
                raise ConflictError(
                    "This provider already has an appointment in that time window"
                )

    def _validate_duration(self, starts_at: datetime, ends_at: datetime) -> None:
        minutes = (ends_at - starts_at).total_seconds() / 60
        if minutes < MIN_DURATION_MINUTES:
            raise ConflictError(f"Appointments must be at least {MIN_DURATION_MINUTES} minutes")
        if minutes > MAX_DURATION_HOURS * 60:
            raise ConflictError(f"Appointments cannot exceed {MAX_DURATION_HOURS} hours")

    def _visible_appointment(self, actor: UserRead, appointment_id: int) -> AppointmentRecord:
        record = self._appointments.get(appointment_id)
        if record is None:
            raise NotFoundError("Appointment", appointment_id)
        if actor.role is not UserRole.ADMIN and actor.id != record.user_id:
            raise NotFoundError("Appointment", appointment_id)
        return record

    def _require_provider(self, provider_id: int) -> ProviderRecord:
        record = self._providers.get(provider_id)
        if record is None:
            raise NotFoundError("Provider", provider_id)
        return record

    def _active_provider(self, provider_id: int) -> ProviderRecord:
        record = self._require_provider(provider_id)
        if not record.is_active:
            raise ConflictError("Cannot book with an inactive provider")
        return record

    def _provider_read(self, record: ProviderRecord) -> ProviderRead:
        return ProviderRead(
            id=record.id,
            name=record.name,
            specialty=record.specialty,
            is_active=record.is_active,
        )

    def _appointment_read(self, record: AppointmentRecord) -> AppointmentRead:
        client = self._users.get_by_id(record.user_id)
        provider = self._require_provider(record.provider_id)
        return AppointmentRead(
            id=record.id,
            user_id=record.user_id,
            client_name=client.full_name if client is not None else "Unknown",
            provider_id=record.provider_id,
            provider_name=provider.name,
            title=record.title,
            notes=record.notes,
            status=record.status,
            starts_at=record.starts_at,
            ends_at=record.ends_at,
            created_at=record.created_at,
        )

    def _require_admin(self, actor: UserRead, message: str) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError(message)

    def _require_owner_or_admin(
        self,
        actor: UserRead,
        record: AppointmentRecord,
        message: str,
    ) -> None:
        if actor.role is not UserRole.ADMIN and actor.id != record.user_id:
            raise ForbiddenError(message)
