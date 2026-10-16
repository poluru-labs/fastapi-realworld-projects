import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.scheduler import ScheduledRun
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.run_repository import RunRepository
from app.repositories.worker_repository import WorkerRepository
from app.schemas.scheduler import (
    ClaimRunRequest,
    CompleteRunRequest,
    RunOutcome,
    RunStatus,
    ScheduledRunRead,
    TriggerRunRequest,
    WorkerHeartbeat,
    WorkerRegister,
)
from app.schemas.user import UserRead, UserRole
from app.services.schedule_service import ScheduleService


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class RunService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._runs = RunRepository(session)
        self._workers = WorkerRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._schedules = ScheduleService(session)

    async def list_mine(
        self,
        actor: UserRead,
        *,
        limit: int,
        offset: int,
    ) -> list[ScheduledRunRead]:
        rows = await self._runs.list_for_owner(actor.id, limit=limit, offset=offset)
        return [ScheduledRunRead.model_validate(row) for row in rows]

    async def get_run(self, actor: UserRead, run_id: int) -> ScheduledRunRead:
        row = await self._require_visible(actor, run_id)
        return ScheduledRunRead.model_validate(row)

    async def trigger(
        self,
        actor: UserRead,
        slug: str,
        payload: TriggerRunRequest,
        *,
        idempotency_key: str,
    ) -> ScheduledRunRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        schedule = await self._schedules.require_triggerable(slug)
        now = datetime.now(UTC)
        scheduled_for = payload.scheduled_for or now
        if scheduled_for.tzinfo is None:
            scheduled_for = scheduled_for.replace(tzinfo=UTC)
        merged_payload = dict(schedule.default_payload)
        merged_payload.update(payload.payload)

        run = ScheduledRun(
            schedule_id=schedule.id,
            owner_id=actor.id,
            task_type=schedule.task_type,
            payload=merged_payload,
            status=RunStatus.PENDING.value,
            scheduled_for=scheduled_for,
            max_attempts=schedule.max_attempts,
            retry_delay_seconds=schedule.retry_delay_seconds,
            version=1,
            created_at=now,
        )
        await self._runs.add(run)
        await self._session.commit()
        body = ScheduledRunRead.model_validate(run)
        await self._store_idempotent(actor, idempotency_key, body)
        await self._session.commit()
        return body

    async def cancel(self, actor: UserRead, run_id: int) -> ScheduledRunRead:
        row = await self._require_visible(actor, run_id)
        if row.status not in {RunStatus.PENDING.value, RunStatus.RUNNING.value}:
            raise ConflictError("Only pending or running work can be cancelled")
        if actor.role is not UserRole.ADMIN and actor.id != row.owner_id:
            raise ForbiddenError("Only the run owner or an admin can cancel")
        row.status = RunStatus.CANCELLED.value
        row.lease_holder = None
        row.lease_expires_at = None
        row.finished_at = datetime.now(UTC)
        row.version += 1
        await self._runs.save()
        await self._session.commit()
        return ScheduledRunRead.model_validate(row)

    async def register_worker(self, actor: UserRead, payload: WorkerRegister) -> dict[str, str]:
        now = datetime.now(UTC)
        await self._workers.upsert(
            worker_id=payload.worker_id,
            registered_by_id=actor.id,
            capabilities=payload.capabilities,
            now=now,
        )
        await self._session.commit()
        return {"worker_id": payload.worker_id, "status": "registered"}

    async def heartbeat(self, actor: UserRead, payload: WorkerHeartbeat) -> dict[str, str]:
        node = await self._workers.get(payload.worker_id)
        if node is None:
            raise NotFoundError("Worker", payload.worker_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only heartbeat workers you registered")
        await self._workers.heartbeat(payload.worker_id, datetime.now(UTC))
        await self._session.commit()
        return {"worker_id": payload.worker_id, "status": "ok"}

    async def claim(self, actor: UserRead, payload: ClaimRunRequest) -> ScheduledRunRead:
        node = await self._workers.get(payload.worker_id)
        if node is None:
            raise NotFoundError("Worker", payload.worker_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only claim with workers you registered")

        now = datetime.now(UTC)
        run = await self._runs.find_claimable(task_types=list(node.capabilities), now=now)
        if run is None:
            raise NotFoundError("ClaimableRun", "none")

        lease = timedelta(seconds=self._settings.worker_lease_seconds)
        run.status = RunStatus.RUNNING.value
        run.lease_holder = payload.worker_id
        run.lease_expires_at = now + lease
        run.attempt_count += 1
        if run.started_at is None:
            run.started_at = now
        run.version += 1
        await self._runs.save()
        await self._session.commit()
        return ScheduledRunRead.model_validate(run)

    async def complete(
        self,
        actor: UserRead,
        run_id: int,
        payload: CompleteRunRequest,
    ) -> ScheduledRunRead:
        row = await self._runs.get(run_id)
        if row is None:
            raise NotFoundError("ScheduledRun", run_id)
        node = await self._workers.get(payload.worker_id)
        if node is None:
            raise NotFoundError("Worker", payload.worker_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only complete runs with workers you registered")

        if row.status != RunStatus.RUNNING.value:
            raise ConflictError("Run is not in running state")
        if row.lease_holder != payload.worker_id:
            raise ForbiddenError("This worker does not hold the lease for this run")
        now = datetime.now(UTC)
        lease_expires = _as_utc(row.lease_expires_at)
        if lease_expires is not None and lease_expires < now:
            raise ConflictError("Lease expired; run may be reclaimed")
        if row.version != payload.expected_version:
            raise ConflictError(
                f"Stale version: expected {payload.expected_version}, current is {row.version}"
            )

        if payload.outcome is RunOutcome.SUCCESS:
            row.status = RunStatus.SUCCEEDED.value
            row.result = dict(payload.result)
            row.error_message = None
            row.finished_at = now
            row.lease_holder = None
            row.lease_expires_at = None
            row.version += 1
        else:
            message = (payload.error_message or "Worker reported failure").strip()
            if row.attempt_count < row.max_attempts:
                row.status = RunStatus.PENDING.value
                row.error_message = message
                row.scheduled_for = now + timedelta(seconds=row.retry_delay_seconds)
                row.lease_holder = None
                row.lease_expires_at = None
                row.version += 1
            else:
                row.status = RunStatus.FAILED.value
                row.error_message = message
                row.finished_at = now
                row.lease_holder = None
                row.lease_expires_at = None
                row.version += 1

        await self._runs.save()
        await self._session.commit()
        return ScheduledRunRead.model_validate(row)

    async def _require_visible(self, actor: UserRead, run_id: int) -> ScheduledRun:
        row = await self._runs.get(run_id)
        if row is None:
            raise NotFoundError("ScheduledRun", run_id)
        if actor.role is not UserRole.ADMIN and actor.id != row.owner_id:
            raise NotFoundError("ScheduledRun", run_id)
        return row

    async def _load_idempotent(
        self,
        actor: UserRead,
        key: str,
    ) -> ScheduledRunRead | None:
        record = await self._idempotency.get(key)
        if record is None:
            return None
        if record.user_id != actor.id:
            raise ConflictError("Idempotency-Key was used by another user")
        data = json.loads(record.response_json)
        return ScheduledRunRead.model_validate(data)

    async def _store_idempotent(
        self,
        actor: UserRead,
        key: str,
        body: ScheduledRunRead,
    ) -> None:
        await self._idempotency.save(
            key=key,
            user_id=actor.id,
            response_json=body.model_dump_json(),
            status_code=201,
        )
