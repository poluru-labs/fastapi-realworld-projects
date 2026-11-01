from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.monitor_repository import CheckRecord, MonitorRecord, MonitorRepository
from app.schemas.monitor import (
    CheckResultRead,
    CheckStatus,
    MonitorCreate,
    MonitorRead,
    MonitorUpdate,
    StatusPageRead,
    slugify,
)
from app.schemas.user import UserRead, UserRole
from app.services.probe_client import ProbeClient


class MonitorService:
    def __init__(self, repository: MonitorRepository, probe: ProbeClient) -> None:
        self._repo = repository
        self._probe = probe

    def list_monitors(self, actor: UserRead) -> list[MonitorRead]:
        rows = self._repo.list_monitors()
        if actor.role is not UserRole.ADMIN:
            rows = [row for row in rows if row.owner_id == actor.id]
        rows.sort(key=lambda row: row.slug)
        return [self._read(row) for row in rows]

    def get_monitor(self, actor: UserRead, slug: str) -> MonitorRead:
        return self._read(self._visible_monitor(actor, slug))

    def create_monitor(self, actor: UserRead, payload: MonitorCreate) -> MonitorRead:
        slug = payload.slug or slugify(payload.name)
        if not slug:
            raise ConflictError("Could not derive a monitor slug from the name")
        if self._repo.slug_taken(slug):
            raise ConflictError("Another monitor already uses this slug")
        now = datetime.now(UTC)
        record = MonitorRecord(
            id=self._repo.allocate_monitor_id(),
            slug=slug,
            name=payload.name,
            target_url=str(payload.target_url),
            expected_status=payload.expected_status,
            is_active=True,
            is_public=payload.is_public,
            owner_id=actor.id,
            created_at=now,
        )
        self._repo.add_monitor(record)
        return self._read(record)

    def update_monitor(
        self,
        actor: UserRead,
        slug: str,
        payload: MonitorUpdate,
    ) -> MonitorRead:
        record = self._owned_monitor(actor, slug)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            record.name = changes["name"]
        if "target_url" in changes and changes["target_url"] is not None:
            record.target_url = str(changes["target_url"])
        if "expected_status" in changes and changes["expected_status"] is not None:
            record.expected_status = changes["expected_status"]
        if "is_public" in changes and changes["is_public"] is not None:
            record.is_public = changes["is_public"]
        self._repo.save_monitor(record)
        return self._read(record)

    def delete_monitor(self, actor: UserRead, slug: str) -> None:
        record = self._owned_monitor(actor, slug)
        self._repo.delete_monitor(record.id)

    def pause_monitor(self, actor: UserRead, slug: str) -> MonitorRead:
        record = self._owned_monitor(actor, slug)
        if not record.is_active:
            raise ConflictError("Monitor is already paused")
        record.is_active = False
        self._repo.save_monitor(record)
        return self._read(record)

    def resume_monitor(self, actor: UserRead, slug: str) -> MonitorRead:
        record = self._owned_monitor(actor, slug)
        if record.is_active:
            raise ConflictError("Monitor is already active")
        record.is_active = True
        self._repo.save_monitor(record)
        return self._read(record)

    async def run_check(self, actor: UserRead, slug: str) -> CheckResultRead:
        record = self._visible_monitor(actor, slug)
        if not record.is_active:
            raise ConflictError("Monitor is paused")
        return await self._execute_check(record)

    def list_checks(self, actor: UserRead, slug: str, *, limit: int) -> list[CheckResultRead]:
        record = self._visible_monitor(actor, slug)
        return [
            self._check_read(record.slug, check)
            for check in self._repo.list_checks(record.id, limit=limit)
        ]

    def public_status(self, slug: str) -> StatusPageRead:
        record = self._repo.get_monitor_by_slug(slug)
        if record is None or not record.is_public:
            raise NotFoundError("Status page", slug)
        latest = self._repo.latest_check(record.id)
        recent = self._repo.list_checks(record.id, limit=5)
        status = latest.status if latest is not None else CheckStatus.DOWN
        return StatusPageRead(
            slug=record.slug,
            name=record.name,
            status=status,
            target_url=record.target_url,
            last_checked_at=latest.checked_at if latest else None,
            latency_ms=latest.latency_ms if latest else None,
            recent_checks=[self._check_read(record.slug, row) for row in recent],
        )

    async def _execute_check(self, record: MonitorRecord) -> CheckResultRead:
        status, http_status, latency_ms, message = await self._probe.probe(
            target_url=record.target_url,
            expected_status=record.expected_status,
        )
        now = datetime.now(UTC)
        check = CheckRecord(
            id=self._repo.allocate_check_id(),
            monitor_id=record.id,
            status=status,
            http_status=http_status,
            latency_ms=latency_ms,
            message=message,
            checked_at=now,
        )
        self._repo.add_check(check)
        return self._check_read(record.slug, check)

    def _visible_monitor(self, actor: UserRead, slug: str) -> MonitorRecord:
        record = self._repo.get_monitor_by_slug(slug)
        if record is None or (record.owner_id != actor.id and actor.role is not UserRole.ADMIN):
            raise NotFoundError("Monitor", slug)
        return record

    def _owned_monitor(self, actor: UserRead, slug: str) -> MonitorRecord:
        record = self._repo.get_monitor_by_slug(slug)
        if record is None or record.owner_id != actor.id:
            raise NotFoundError("Monitor", slug)
        return record

    def _read(self, record: MonitorRecord) -> MonitorRead:
        latest = self._repo.latest_check(record.id)
        status_page = f"/api/v1/status/{record.slug}" if record.is_public else None
        return MonitorRead(
            id=record.id,
            slug=record.slug,
            name=record.name,
            target_url=record.target_url,
            expected_status=record.expected_status,
            is_active=record.is_active,
            is_public=record.is_public,
            owner_id=record.owner_id,
            last_status=latest.status if latest else None,
            last_checked_at=latest.checked_at if latest else None,
            status_page_path=status_page,
            created_at=record.created_at,
        )

    @staticmethod
    def _check_read(monitor_slug: str, check: CheckRecord) -> CheckResultRead:
        return CheckResultRead(
            id=check.id,
            monitor_slug=monitor_slug,
            status=check.status,
            http_status=check.http_status,
            latency_ms=check.latency_ms,
            message=check.message,
            checked_at=check.checked_at,
        )
