import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.sandbox_runner import run_python, validate_source
from app.models.execution import ExecutionPolicy, ExecutionRun
from app.repositories.execution_repository import ExecutionRepository
from app.schemas.execution import (
    PolicyRead,
    PolicyUpdate,
    RunCreate,
    RunLanguage,
    RunRead,
    RunStatus,
)


class ExecutionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ExecutionRepository(session)

    async def get_policy(self) -> PolicyRead:
        policy = await self._require_policy()
        return self._policy_read(policy)

    async def update_policy(self, payload: PolicyUpdate) -> PolicyRead:
        policy = await self._require_policy()
        changes = payload.model_dump(exclude_unset=True)
        if "max_source_bytes" in changes and changes["max_source_bytes"] is not None:
            policy.max_source_bytes = changes["max_source_bytes"]
        if "max_timeout_ms" in changes and changes["max_timeout_ms"] is not None:
            policy.max_timeout_ms = changes["max_timeout_ms"]
        if "allowed_languages" in changes and changes["allowed_languages"] is not None:
            policy.allowed_languages = ",".join(lang.value for lang in changes["allowed_languages"])
        policy.updated_at = datetime.now(UTC)
        await self._repo.save_policy(policy)
        await self._session.commit()
        return self._policy_read(policy)

    async def create_run(
        self,
        payload: RunCreate,
        *,
        idempotency_key: str,
    ) -> RunRead:
        existing = await self._repo.get_run_by_idempotency(idempotency_key)
        if existing is not None:
            return self._run_read(existing)

        policy = await self._require_policy()
        allowed = {part.strip() for part in policy.allowed_languages.split(",") if part.strip()}
        if payload.language.value not in allowed:
            raise AppError(f"Language {payload.language.value!r} is not allowed")

        now = datetime.now(UTC)
        run = ExecutionRun(
            language=payload.language.value,
            source_code=payload.source,
            status=RunStatus.REJECTED.value,
            stdout="",
            stderr="",
            exit_code=None,
            runtime_ms=0,
            idempotency_key=idempotency_key,
            created_at=now,
            finished_at=None,
        )

        try:
            validate_source(payload.source, max_bytes=policy.max_source_bytes)
        except AppError as exc:
            run.status = RunStatus.REJECTED.value
            run.stderr = exc.message
            run.finished_at = datetime.now(UTC)
            await self._repo.add_run(run)
            await self._session.commit()
            return self._run_read(run)

        timeout_s = policy.max_timeout_ms / 1000
        try:
            exit_code, stdout, stderr, runtime_ms = await asyncio.wait_for(
                asyncio.to_thread(run_python, payload.source),
                timeout=timeout_s,
            )
            run.status = RunStatus.COMPLETED.value if exit_code == 0 else RunStatus.FAILED.value
            run.stdout = stdout
            run.stderr = stderr
            run.exit_code = exit_code
            run.runtime_ms = runtime_ms
        except TimeoutError:
            run.status = RunStatus.TIMEOUT.value
            run.stderr = f"Execution exceeded {policy.max_timeout_ms} ms"
            run.runtime_ms = policy.max_timeout_ms

        run.finished_at = datetime.now(UTC)
        await self._repo.add_run(run)
        await self._session.commit()
        return self._run_read(run)

    async def get_run(self, run_id: int) -> RunRead:
        run = await self._repo.get_run(run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        return self._run_read(run)

    async def list_runs(self, *, limit: int, offset: int) -> list[RunRead]:
        rows = await self._repo.list_runs(limit=limit, offset=offset)
        return [self._run_read(row) for row in rows]

    async def _require_policy(self) -> ExecutionPolicy:
        policy = await self._repo.get_policy()
        if policy is None:
            raise NotFoundError("Execution policy", 1)
        return policy

    @staticmethod
    def _policy_read(policy: ExecutionPolicy) -> PolicyRead:
        languages = [
            RunLanguage(part.strip())
            for part in policy.allowed_languages.split(",")
            if part.strip()
        ]
        return PolicyRead(
            max_source_bytes=policy.max_source_bytes,
            max_timeout_ms=policy.max_timeout_ms,
            allowed_languages=languages,
            updated_at=policy.updated_at,
        )

    @staticmethod
    def _run_read(run: ExecutionRun) -> RunRead:
        return RunRead(
            id=run.id,
            language=RunLanguage(run.language),
            source=run.source_code,
            status=RunStatus(run.status),
            stdout=run.stdout,
            stderr=run.stderr,
            exit_code=run.exit_code,
            runtime_ms=run.runtime_ms,
            idempotency_key=run.idempotency_key,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
