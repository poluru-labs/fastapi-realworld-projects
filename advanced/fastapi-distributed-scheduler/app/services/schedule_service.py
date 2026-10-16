from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.scheduler import Schedule
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.scheduler import (
    ScheduleCreate,
    ScheduleRead,
    ScheduleStatus,
    ScheduleUpdate,
    slugify,
)
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[ScheduleStatus, set[ScheduleStatus]] = {
    ScheduleStatus.DRAFT: {ScheduleStatus.PUBLISHED},
    ScheduleStatus.PUBLISHED: {
        ScheduleStatus.PAUSED,
        ScheduleStatus.ARCHIVED,
        ScheduleStatus.DRAFT,
    },
    ScheduleStatus.PAUSED: {ScheduleStatus.PUBLISHED, ScheduleStatus.ARCHIVED},
    ScheduleStatus.ARCHIVED: {ScheduleStatus.DRAFT},
}


def _can_view(actor: UserRead | None, schedule: Schedule) -> bool:
    if schedule.status == ScheduleStatus.PUBLISHED.value:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == schedule.owner_id


class ScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._schedules = ScheduleRepository(session)

    async def list_published(self) -> list[ScheduleRead]:
        rows = await self._schedules.list_published()
        return [ScheduleRead.model_validate(row) for row in rows]

    async def list_mine(self, actor: UserRead) -> list[ScheduleRead]:
        rows = await self._schedules.list_for_owner(actor.id)
        return [ScheduleRead.model_validate(row) for row in rows]

    async def get_schedule(self, actor: UserRead | None, slug: str) -> ScheduleRead:
        row = await self._visible(actor, slug)
        return ScheduleRead.model_validate(row)

    async def require_triggerable(self, slug: str) -> Schedule:
        row = await self._schedules.get_by_slug(slug)
        if row is None or row.status != ScheduleStatus.PUBLISHED.value:
            raise NotFoundError("Schedule", slug)
        return row

    async def create_schedule(self, actor: UserRead, payload: ScheduleCreate) -> ScheduleRead:
        slug = payload.slug or slugify(payload.name)
        if await self._schedules.get_by_slug(slug) is not None:
            raise ConflictError("Another schedule already uses this slug")
        now = datetime.now(UTC)
        row = Schedule(
            slug=slug,
            name=payload.name,
            description=payload.description,
            status=ScheduleStatus.DRAFT.value,
            schedule_kind=payload.schedule_kind.value,
            cron_expression=payload.cron_expression,
            interval_seconds=payload.interval_seconds,
            timezone=payload.timezone,
            task_type=payload.task_type,
            default_payload=dict(payload.default_payload),
            max_attempts=payload.max_attempts,
            retry_delay_seconds=payload.retry_delay_seconds,
            owner_id=actor.id,
            created_at=now,
            updated_at=now,
        )
        await self._schedules.add(row)
        await self._session.commit()
        return ScheduleRead.model_validate(row)

    async def update_schedule(
        self,
        actor: UserRead,
        slug: str,
        payload: ScheduleUpdate,
    ) -> ScheduleRead:
        row = await self._visible(actor, slug)
        self._require_owner(actor, row)
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await self._schedules.save()
        await self._session.commit()
        return ScheduleRead.model_validate(row)

    async def publish(self, actor: UserRead, slug: str) -> ScheduleRead:
        return await self._transition(
            actor,
            slug,
            source=ScheduleStatus.DRAFT,
            target=ScheduleStatus.PUBLISHED,
            message="Only a draft can be published",
            set_published_at=True,
        )

    async def pause(self, actor: UserRead, slug: str) -> ScheduleRead:
        return await self._transition(
            actor,
            slug,
            source=ScheduleStatus.PUBLISHED,
            target=ScheduleStatus.PAUSED,
            message="Only a published schedule can be paused",
        )

    async def resume(self, actor: UserRead, slug: str) -> ScheduleRead:
        return await self._transition(
            actor,
            slug,
            source=ScheduleStatus.PAUSED,
            target=ScheduleStatus.PUBLISHED,
            message="Only a paused schedule can be resumed",
        )

    async def archive(self, actor: UserRead, slug: str) -> ScheduleRead:
        row = await self._visible(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != row.owner_id:
            raise ForbiddenError("Only the owner or an admin can archive this schedule")
        if row.status not in {
            ScheduleStatus.PUBLISHED.value,
            ScheduleStatus.PAUSED.value,
        }:
            raise ConflictError(
                f"Only a published or paused schedule can be archived. "
                f"This schedule is {row.status}"
            )
        row.status = ScheduleStatus.ARCHIVED.value
        row.updated_at = datetime.now(UTC)
        await self._schedules.save()
        await self._session.commit()
        return ScheduleRead.model_validate(row)

    async def restore(self, actor: UserRead, slug: str) -> ScheduleRead:
        return await self._transition(
            actor,
            slug,
            source=ScheduleStatus.ARCHIVED,
            target=ScheduleStatus.DRAFT,
            message="Only an archived schedule can be restored",
            clear_published_at=True,
        )

    async def _transition(
        self,
        actor: UserRead,
        slug: str,
        *,
        source: ScheduleStatus,
        target: ScheduleStatus,
        message: str,
        set_published_at: bool = False,
        clear_published_at: bool = False,
    ) -> ScheduleRead:
        row = await self._visible(actor, slug)
        self._require_owner(actor, row)
        allowed = _TRANSITIONS[ScheduleStatus(row.status)]
        if row.status != source.value or target not in allowed:
            raise ConflictError(f"{message}. This schedule is {row.status}")
        now = datetime.now(UTC)
        row.status = target.value
        row.updated_at = now
        if set_published_at:
            row.published_at = now
        if clear_published_at:
            row.published_at = None
        await self._schedules.save()
        await self._session.commit()
        return ScheduleRead.model_validate(row)

    async def _visible(self, actor: UserRead | None, slug: str) -> Schedule:
        row = await self._schedules.get_by_slug(slug)
        if row is None or not _can_view(actor, row):
            raise NotFoundError("Schedule", slug)
        return row

    def _require_owner(self, actor: UserRead, row: Schedule) -> None:
        if actor.id != row.owner_id:
            raise ForbiddenError("Only the owner can change this schedule")
