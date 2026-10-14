"""Workflow instances, append-only history, idempotency, and optimistic concurrency."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.workflow import WorkflowEvent, WorkflowInstance
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workflow_repository import (
    WorkflowDefinitionRepository,
    WorkflowInstanceRepository,
)
from app.schemas.user import UserRead, UserRole
from app.schemas.workflow import (
    DefinitionStatus,
    InstanceStart,
    InstanceStatus,
    TransitionCommand,
    WorkflowEventRead,
    WorkflowEventType,
    WorkflowInstanceRead,
)
from app.services.workflow_helpers import actor_may_fire, find_transition


class InstanceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._definitions = WorkflowDefinitionRepository(session)
        self._instances = WorkflowInstanceRepository(session)
        self._users = UserRepository(session)
        self._idempotency = IdempotencyRepository(session)

    async def list_instances(self, actor: UserRead) -> list[WorkflowInstanceRead]:
        if actor.role is UserRole.ADMIN:
            rows = await self._instances.list_all()
        else:
            rows = await self._instances.list_for_owner(actor.id)
        return [await self._to_read(row) for row in rows]

    async def get_instance(self, actor: UserRead, instance_id: int) -> WorkflowInstanceRead:
        row = await self._require_visible(actor, instance_id)
        return await self._to_read(row)

    async def list_events(self, actor: UserRead, instance_id: int) -> list[WorkflowEventRead]:
        await self._require_visible(actor, instance_id)
        rows = await self._instances.list_events(instance_id)
        return [WorkflowEventRead.model_validate(event) for event in rows]

    async def start_instance(
        self,
        actor: UserRead,
        payload: InstanceStart,
        *,
        idempotency_key: str,
    ) -> WorkflowInstanceRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        definition = await self._definitions.get_by_slug(payload.definition_slug)
        if definition is None or definition.status != DefinitionStatus.PUBLISHED.value:
            raise NotFoundError("WorkflowDefinition", payload.definition_slug)

        now = datetime.now(UTC)
        instance = WorkflowInstance(
            definition_id=definition.id,
            owner_id=actor.id,
            current_state=definition.initial_state,
            status=InstanceStatus.ACTIVE.value,
            context=dict(payload.context),
            version=1,
            created_at=now,
            updated_at=now,
        )
        await self._instances.add(instance)
        await self._instances.append_event(
            WorkflowEvent(
                instance_id=instance.id,
                sequence=1,
                event_type=WorkflowEventType.INSTANCE_STARTED.value,
                from_state=None,
                to_state=definition.initial_state,
                action=None,
                payload={
                    "definition_slug": definition.slug,
                    "context": dict(payload.context),
                },
                actor_id=actor.id,
                created_at=now,
            )
        )
        result = await self._to_read(instance)
        await self._store_idempotent(actor, idempotency_key, result, status_code=201)
        await self._session.commit()
        return result

    async def transition(
        self,
        actor: UserRead,
        instance_id: int,
        payload: TransitionCommand,
        *,
        idempotency_key: str,
    ) -> WorkflowInstanceRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        instance = await self._locked_visible(actor, instance_id)
        if instance.status != InstanceStatus.ACTIVE.value:
            raise ConflictError("Completed workflow instances cannot transition")
        if instance.version != payload.expected_version:
            raise ConflictError(
                "Stale instance version: "
                f"expected {payload.expected_version}, current {instance.version}"
            )

        definition = await self._definitions.get_by_id(instance.definition_id)
        if definition is None:
            raise NotFoundError("WorkflowDefinition", instance.definition_id)

        edge = find_transition(
            definition,
            action=payload.action,
            from_state=instance.current_state,
        )
        if not actor_may_fire(actor, edge):
            raise ForbiddenError("Your role cannot perform this workflow action")

        merged_context = {**instance.context, **payload.context_patch}
        from_state = instance.current_state
        to_state = edge.to_state
        next_version = instance.version + 1
        now = datetime.now(UTC)

        instance.current_state = to_state
        instance.context = merged_context
        instance.version = next_version
        instance.updated_at = now
        if to_state in definition.terminal_states:
            instance.status = InstanceStatus.COMPLETED.value

        await self._instances.append_event(
            WorkflowEvent(
                instance_id=instance.id,
                sequence=next_version,
                event_type=WorkflowEventType.STATE_CHANGED.value,
                from_state=from_state,
                to_state=to_state,
                action=payload.action,
                payload={
                    "note": payload.note,
                    "context": merged_context,
                },
                actor_id=actor.id,
                created_at=now,
            )
        )
        result = await self._to_read(instance)
        await self._store_idempotent(actor, idempotency_key, result, status_code=200)
        await self._session.commit()
        return result

    async def _require_visible(self, actor: UserRead, instance_id: int) -> WorkflowInstance:
        row = await self._instances.get(instance_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("WorkflowInstance", instance_id)
        return row

    async def _locked_visible(self, actor: UserRead, instance_id: int) -> WorkflowInstance:
        row = await self._instances.get_for_update(instance_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("WorkflowInstance", instance_id)
        return row

    @staticmethod
    def _can_view(actor: UserRead, row: WorkflowInstance) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return row.owner_id == actor.id

    async def _to_read(self, row: WorkflowInstance) -> WorkflowInstanceRead:
        definition = await self._definitions.get_by_id(row.definition_id)
        owner = await self._users.get_by_id(row.owner_id)
        slug = definition.slug if definition else "unknown"
        owner_name = owner.full_name if owner else "Unknown"
        return WorkflowInstanceRead(
            id=row.id,
            definition_id=row.definition_id,
            definition_slug=slug,
            owner_id=row.owner_id,
            owner_name=owner_name,
            current_state=row.current_state,
            status=InstanceStatus(row.status),
            context=dict(row.context),
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _load_idempotent(
        self, actor: UserRead, key: str
    ) -> WorkflowInstanceRead | None:
        row = await self._idempotency.get(key)
        if row is None:
            return None
        if row.user_id != actor.id:
            raise ConflictError("Idempotency key belongs to another user")
        return WorkflowInstanceRead.model_validate_json(row.response_json)

    async def _store_idempotent(
        self,
        actor: UserRead,
        key: str,
        result: WorkflowInstanceRead,
        *,
        status_code: int,
    ) -> None:
        await self._idempotency.save(
            key=key,
            user_id=actor.id,
            response_json=result.model_dump_json(),
            status_code=status_code,
        )
