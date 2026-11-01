from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runner import execute_steps
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.agent_workflow import AgentStepLog, AgentWorkflowDefinition, AgentWorkflowRun
from app.repositories.agent_workflow_repository import AgentWorkflowRepository
from app.schemas.agent_workflow import (
    RunCreate,
    RunRead,
    RunStatus,
    StepLogRead,
    StepStatus,
    StepType,
    WorkflowDefinitionCreate,
    WorkflowDefinitionRead,
    WorkflowDefinitionUpdate,
    WorkflowStatus,
)


class AgentWorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AgentWorkflowRepository(session)

    async def create_definition(self, payload: WorkflowDefinitionCreate) -> WorkflowDefinitionRead:
        if await self._repo.slug_exists(payload.slug):
            raise ConflictError(f"Workflow slug {payload.slug!r} already exists")
        row = AgentWorkflowDefinition(
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            status=WorkflowStatus.DRAFT.value,
            steps=[step.model_dump(mode="json") for step in payload.steps],
        )
        await self._repo.add_definition(row)
        await self._session.commit()
        return WorkflowDefinitionRead.model_validate(row)

    async def list_definitions(self) -> list[WorkflowDefinitionRead]:
        rows = await self._repo.list_definitions()
        return [WorkflowDefinitionRead.model_validate(row) for row in rows]

    async def get_definition(self, slug: str) -> WorkflowDefinitionRead:
        row = await self._require_definition(slug)
        return WorkflowDefinitionRead.model_validate(row)

    async def update_definition(
        self,
        slug: str,
        payload: WorkflowDefinitionUpdate,
    ) -> WorkflowDefinitionRead:
        row = await self._require_definition(slug)
        if row.status != WorkflowStatus.DRAFT.value:
            raise AppError("Only draft workflows can be edited")
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            row.name = changes["name"]
        if "description" in changes and changes["description"] is not None:
            row.description = changes["description"]
        if "steps" in changes and changes["steps"] is not None:
            row.steps = [step.model_dump(mode="json") for step in payload.steps or []]
        row.updated_at = datetime.now(UTC)
        await self._session.commit()
        return WorkflowDefinitionRead.model_validate(row)

    async def publish_definition(self, slug: str) -> WorkflowDefinitionRead:
        row = await self._require_definition(slug)
        if row.status != WorkflowStatus.DRAFT.value:
            raise AppError("Only draft workflows can be published")
        row.status = WorkflowStatus.PUBLISHED.value
        row.updated_at = datetime.now(UTC)
        await self._session.commit()
        return WorkflowDefinitionRead.model_validate(row)

    async def create_run(self, payload: RunCreate, *, idempotency_key: str) -> RunRead:
        existing = await self._repo.get_run_by_idempotency(idempotency_key)
        if existing is not None:
            return await self._run_read(existing)

        definition = await self._repo.get_definition_by_slug(payload.workflow_slug.lower())
        if definition is None:
            raise NotFoundError("Workflow", payload.workflow_slug)
        if definition.status != WorkflowStatus.PUBLISHED.value:
            raise AppError("Workflow is not published")

        status, output, context, logs = execute_steps(
            steps=definition.steps,
            run_input=payload.input,
        )
        now = datetime.now(UTC)
        run = AgentWorkflowRun(
            definition_id=definition.id,
            workflow_slug=definition.slug,
            status=status.value,
            input_payload=payload.input,
            output_payload=output,
            context_payload=context,
            idempotency_key=idempotency_key,
            created_at=now,
            finished_at=now,
        )
        await self._repo.add_run(run)
        await self._repo.add_step_logs(
            [
                AgentStepLog(
                    run_id=run.id,
                    sequence=log["sequence"],
                    step_key=log["step_key"],
                    step_type=log["step_type"],
                    status=log["status"],
                    input_payload=log["input_payload"],
                    output_payload=log["output_payload"],
                )
                for log in logs
            ]
        )
        await self._session.commit()
        return await self._run_read(run)

    async def get_run(self, run_id: int) -> RunRead:
        run = await self._repo.get_run(run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        return await self._run_read(run)

    async def list_runs(self, *, limit: int, offset: int) -> list[RunRead]:
        rows = await self._repo.list_runs(limit=limit, offset=offset)
        return [await self._run_read(row) for row in rows]

    async def _require_definition(self, slug: str) -> AgentWorkflowDefinition:
        row = await self._repo.get_definition_by_slug(slug.lower())
        if row is None:
            raise NotFoundError("Workflow", slug)
        return row

    async def _run_read(self, run: AgentWorkflowRun) -> RunRead:
        logs = await self._repo.list_step_logs(run.id)
        return RunRead(
            id=run.id,
            workflow_slug=run.workflow_slug,
            status=RunStatus(run.status),
            input=run.input_payload,
            output=run.output_payload,
            context=run.context_payload,
            idempotency_key=run.idempotency_key,
            steps=[
                StepLogRead(
                    sequence=log.sequence,
                    step_key=log.step_key,
                    step_type=StepType(log.step_type),
                    status=StepStatus(log.status),
                    input_payload=log.input_payload,
                    output_payload=log.output_payload,
                    created_at=log.created_at,
                )
                for log in logs
            ],
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
