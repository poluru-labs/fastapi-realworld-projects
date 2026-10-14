"""Workflow definition catalog and admin lifecycle."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.workflow import WorkflowDefinition
from app.repositories.workflow_repository import WorkflowDefinitionRepository
from app.schemas.user import UserRead, UserRole
from app.schemas.workflow import (
    DefinitionStatus,
    WorkflowDefinitionCreate,
    WorkflowDefinitionRead,
    WorkflowDefinitionUpdate,
)
from app.services.workflow_helpers import (
    definition_can_view,
    ensure_draft,
    merge_definition_update,
    parse_transitions,
)


class DefinitionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._definitions = WorkflowDefinitionRepository(session)

    async def list_definitions(
        self,
        actor: UserRead | None,
        *,
        status: DefinitionStatus | None,
    ) -> list[WorkflowDefinitionRead]:
        rows = await self._definitions.list_all()
        if actor is None or actor.role is not UserRole.ADMIN:
            rows = [row for row in rows if row.status == DefinitionStatus.PUBLISHED.value]
        elif status is not None:
            rows = [row for row in rows if row.status == status.value]
        return [self._to_read(row) for row in rows]

    async def get_definition(self, actor: UserRead | None, slug: str) -> WorkflowDefinitionRead:
        row = await self._definitions.get_by_slug(slug)
        if row is None or not definition_can_view(actor, row):
            raise NotFoundError("WorkflowDefinition", slug)
        return self._to_read(row)

    async def create_definition(
        self,
        actor: UserRead,
        payload: WorkflowDefinitionCreate,
    ) -> WorkflowDefinitionRead:
        self._require_admin(actor)
        if await self._definitions.slug_taken(payload.slug):
            raise ConflictError("Another workflow already uses this slug")
        now = datetime.now(UTC)
        row = WorkflowDefinition(
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            status=DefinitionStatus.DRAFT.value,
            initial_state=payload.initial_state,
            states=payload.states,
            transitions=[edge.model_dump(by_alias=True) for edge in payload.transitions],
            terminal_states=payload.terminal_states,
            created_at=now,
            updated_at=now,
        )
        await self._definitions.add(row)
        await self._session.commit()
        return self._to_read(row)

    async def update_definition(
        self,
        actor: UserRead,
        slug: str,
        payload: WorkflowDefinitionUpdate,
    ) -> WorkflowDefinitionRead:
        self._require_admin(actor)
        row = await self._require_row(slug)
        ensure_draft(row)
        merged = merge_definition_update(row, payload)
        row.name = merged.name
        row.description = merged.description
        row.initial_state = merged.initial_state
        row.states = merged.states
        row.transitions = [edge.model_dump(by_alias=True) for edge in merged.transitions]
        row.terminal_states = merged.terminal_states
        row.updated_at = datetime.now(UTC)
        await self._session.commit()
        return self._to_read(row)

    async def publish(self, actor: UserRead, slug: str) -> WorkflowDefinitionRead:
        return await self._transition(actor, slug, DefinitionStatus.PUBLISHED)

    async def archive(self, actor: UserRead, slug: str) -> WorkflowDefinitionRead:
        return await self._transition(actor, slug, DefinitionStatus.ARCHIVED)

    async def restore_draft(self, actor: UserRead, slug: str) -> WorkflowDefinitionRead:
        return await self._transition(actor, slug, DefinitionStatus.DRAFT)

    async def _transition(
        self,
        actor: UserRead,
        slug: str,
        target: DefinitionStatus,
    ) -> WorkflowDefinitionRead:
        self._require_admin(actor)
        row = await self._require_row(slug)
        allowed = _DEFINITION_TRANSITIONS.get(DefinitionStatus(row.status), set())
        if target not in allowed:
            raise ConflictError(
                f"Cannot move definition from {row.status} to {target.value}"
            )
        row.status = target.value
        row.updated_at = datetime.now(UTC)
        await self._session.commit()
        return self._to_read(row)

    async def _require_row(self, slug: str) -> WorkflowDefinition:
        row = await self._definitions.get_by_slug(slug)
        if row is None:
            raise NotFoundError("WorkflowDefinition", slug)
        return row

    @staticmethod
    def _require_admin(actor: UserRead) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Admin role required")

    @staticmethod
    def _to_read(row: WorkflowDefinition) -> WorkflowDefinitionRead:
        transitions = parse_transitions(row.transitions)
        return WorkflowDefinitionRead(
            id=row.id,
            slug=row.slug,
            name=row.name,
            description=row.description,
            status=DefinitionStatus(row.status),
            initial_state=row.initial_state,
            states=list(row.states),
            transitions=transitions,
            terminal_states=list(row.terminal_states),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


_DEFINITION_TRANSITIONS: dict[DefinitionStatus, set[DefinitionStatus]] = {
    DefinitionStatus.DRAFT: {DefinitionStatus.PUBLISHED, DefinitionStatus.ARCHIVED},
    DefinitionStatus.PUBLISHED: {DefinitionStatus.DRAFT, DefinitionStatus.ARCHIVED},
    DefinitionStatus.ARCHIVED: {DefinitionStatus.DRAFT},
}
