from dataclasses import dataclass
from datetime import datetime

from app.schemas.appointment import AppointmentStatus


@dataclass
class AppointmentRecord:
    id: int
    user_id: int
    provider_id: int
    title: str
    notes: str
    status: AppointmentStatus
    starts_at: datetime
    ends_at: datetime
    created_at: datetime


def _seed_appointments() -> dict[int, AppointmentRecord]:
    return {
        1: AppointmentRecord(
            id=1,
            user_id=1,
            provider_id=1,
            title="Platform onboarding",
            notes="Seed visit for the admin account.",
            status=AppointmentStatus.CONFIRMED,
            starts_at=datetime.fromisoformat("2026-12-01T15:00:00+00:00"),
            ends_at=datetime.fromisoformat("2026-12-01T15:30:00+00:00"),
            created_at=datetime.fromisoformat("2026-11-01T10:00:00+00:00"),
        ),
        2: AppointmentRecord(
            id=2,
            user_id=1,
            provider_id=2,
            title="Follow-up slot",
            notes="Overlaps are checked on create.",
            status=AppointmentStatus.SCHEDULED,
            starts_at=datetime.fromisoformat("2026-12-02T14:00:00+00:00"),
            ends_at=datetime.fromisoformat("2026-12-02T14:45:00+00:00"),
            created_at=datetime.fromisoformat("2026-11-02T10:00:00+00:00"),
        ),
    }


class AppointmentRepository:
    def __init__(self) -> None:
        self._appointments = dict(_seed_appointments())
        self._next_id = max(self._appointments.keys(), default=0) + 1

    def list_all(self) -> list[AppointmentRecord]:
        return list(self._appointments.values())

    def get(self, appointment_id: int) -> AppointmentRecord | None:
        return self._appointments.get(appointment_id)

    def add(self, record: AppointmentRecord) -> AppointmentRecord:
        self._appointments[record.id] = record
        return record

    def save(self, record: AppointmentRecord) -> None:
        self._appointments[record.id] = record

    def allocate_id(self) -> int:
        appointment_id = self._next_id
        self._next_id += 1
        return appointment_id
