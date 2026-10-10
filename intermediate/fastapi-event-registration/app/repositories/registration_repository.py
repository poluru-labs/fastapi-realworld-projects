from dataclasses import dataclass
from datetime import datetime

from app.schemas.registration import RegistrationStatus


@dataclass
class RegistrationRecord:
    id: int
    event_id: int
    user_id: int
    status: RegistrationStatus
    created_at: datetime


def _seed_registrations() -> dict[int, RegistrationRecord]:
    return {
        1: RegistrationRecord(
            id=1,
            event_id=1,
            user_id=1,
            status=RegistrationStatus.REGISTERED,
            created_at=datetime.fromisoformat("2026-10-06T09:00:00+00:00"),
        ),
    }


class RegistrationRepository:
    def __init__(self) -> None:
        self._rows = dict(_seed_registrations())
        self._next_id = max(self._rows.keys(), default=0) + 1

    def list_all(self) -> list[RegistrationRecord]:
        return list(self._rows.values())

    def get(self, registration_id: int) -> RegistrationRecord | None:
        return self._rows.get(registration_id)

    def add(self, record: RegistrationRecord) -> RegistrationRecord:
        self._rows[record.id] = record
        return record

    def save(self, record: RegistrationRecord) -> None:
        self._rows[record.id] = record

    def allocate_id(self) -> int:
        registration_id = self._next_id
        self._next_id += 1
        return registration_id

    def list_for_event(self, event_id: int) -> list[RegistrationRecord]:
        return [row for row in self._rows.values() if row.event_id == event_id]

    def list_for_user(self, user_id: int) -> list[RegistrationRecord]:
        return [row for row in self._rows.values() if row.user_id == user_id]

    def active_for_user_event(self, *, user_id: int, event_id: int) -> RegistrationRecord | None:
        for row in self._rows.values():
            if row.user_id != user_id or row.event_id != event_id:
                continue
            if row.status in (RegistrationStatus.REGISTERED, RegistrationStatus.WAITLISTED):
                return row
        return None

    def count_registered(self, event_id: int) -> int:
        return sum(
            1
            for row in self._rows.values()
            if row.event_id == event_id and row.status is RegistrationStatus.REGISTERED
        )

    def count_waitlisted(self, event_id: int) -> int:
        return sum(
            1
            for row in self._rows.values()
            if row.event_id == event_id and row.status is RegistrationStatus.WAITLISTED
        )

    def oldest_waitlisted(self, event_id: int) -> RegistrationRecord | None:
        rows = [
            row
            for row in self._rows.values()
            if row.event_id == event_id and row.status is RegistrationStatus.WAITLISTED
        ]
        if not rows:
            return None
        return min(rows, key=lambda row: (row.created_at, row.id))
