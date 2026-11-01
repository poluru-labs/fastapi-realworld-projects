from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from app.schemas.monitor import CheckStatus


@dataclass
class MonitorRecord:
    id: int
    slug: str
    name: str
    target_url: str
    expected_status: int
    is_active: bool
    is_public: bool
    owner_id: int
    created_at: datetime


@dataclass
class CheckRecord:
    id: int
    monitor_id: int
    status: CheckStatus
    http_status: int | None
    latency_ms: int
    message: str
    checked_at: datetime


def _seed() -> tuple[dict[int, MonitorRecord], list[CheckRecord]]:
    created = datetime.fromisoformat("2026-02-01T10:00:00+00:00")
    checked = datetime.fromisoformat("2026-03-10T12:00:00+00:00")
    monitors = {
        1: MonitorRecord(
            id=1,
            slug="api-gateway",
            name="API gateway",
            target_url="https://mock.local/healthy",
            expected_status=200,
            is_active=True,
            is_public=True,
            owner_id=2,
            created_at=created,
        ),
        2: MonitorRecord(
            id=2,
            slug="billing-service",
            name="Billing service",
            target_url="https://mock.local/down",
            expected_status=200,
            is_active=True,
            is_public=False,
            owner_id=2,
            created_at=created,
        ),
        3: MonitorRecord(
            id=3,
            slug="docs-site",
            name="Documentation site",
            target_url="https://mock.local/slow",
            expected_status=200,
            is_active=True,
            is_public=True,
            owner_id=2,
            created_at=created,
        ),
    }
    checks = [
        CheckRecord(
            id=1,
            monitor_id=1,
            status=CheckStatus.UP,
            http_status=200,
            latency_ms=32,
            message="OK",
            checked_at=checked,
        ),
        CheckRecord(
            id=2,
            monitor_id=2,
            status=CheckStatus.DOWN,
            http_status=503,
            latency_ms=120,
            message="Simulated connection failure",
            checked_at=checked,
        ),
        CheckRecord(
            id=3,
            monitor_id=3,
            status=CheckStatus.DEGRADED,
            http_status=200,
            latency_ms=2500,
            message="Response slower than 2s threshold",
            checked_at=checked,
        ),
    ]
    return monitors, checks


class MonitorRepository:
    def __init__(self) -> None:
        monitors, checks = _seed()
        self._monitors = monitors
        self._checks = checks
        self._next_monitor_id = max(self._monitors.keys(), default=0) + 1
        self._next_check_id = max((check.id for check in checks), default=0) + 1

    def list_monitors(self) -> list[MonitorRecord]:
        return list(self._monitors.values())

    def get_monitor(self, monitor_id: int) -> MonitorRecord | None:
        return self._monitors.get(monitor_id)

    def get_monitor_by_slug(self, slug: str) -> MonitorRecord | None:
        for record in self._monitors.values():
            if record.slug == slug:
                return record
        return None

    def slug_taken(self, slug: str) -> bool:
        return self.get_monitor_by_slug(slug) is not None

    def add_monitor(self, record: MonitorRecord) -> MonitorRecord:
        self._monitors[record.id] = record
        return record

    def save_monitor(self, record: MonitorRecord) -> None:
        self._monitors[record.id] = record

    def delete_monitor(self, monitor_id: int) -> None:
        self._monitors.pop(monitor_id, None)
        self._checks = [check for check in self._checks if check.monitor_id != monitor_id]

    def allocate_monitor_id(self) -> int:
        monitor_id = self._next_monitor_id
        self._next_monitor_id += 1
        return monitor_id

    def add_check(self, record: CheckRecord) -> CheckRecord:
        self._checks.append(record)
        return record

    def allocate_check_id(self) -> int:
        check_id = self._next_check_id
        self._next_check_id += 1
        return check_id

    def list_checks(self, monitor_id: int, *, limit: int) -> list[CheckRecord]:
        rows = [check for check in self._checks if check.monitor_id == monitor_id]
        rows.sort(key=lambda row: row.checked_at, reverse=True)
        return rows[:limit]

    def latest_check(self, monitor_id: int) -> CheckRecord | None:
        rows = self.list_checks(monitor_id, limit=1)
        return rows[0] if rows else None


@lru_cache
def get_monitor_repository() -> MonitorRepository:
    return MonitorRepository()
