from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import ExecutionPolicy, ExecutionRun
from app.schemas.execution import RunLanguage, RunStatus


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.get(ExecutionPolicy, 1)
    if existing is not None:
        return

    now = datetime.now(UTC)
    policy = ExecutionPolicy(
        id=1,
        max_source_bytes=8_192,
        max_timeout_ms=2_000,
        allowed_languages=RunLanguage.PYTHON.value,
        updated_at=now,
    )
    session.add(policy)
    await session.flush()

    sample = ExecutionRun(
        language=RunLanguage.PYTHON.value,
        source_code='print("seed hello")',
        status=RunStatus.COMPLETED.value,
        stdout="seed hello\n",
        stderr="",
        exit_code=0,
        runtime_ms=1,
        idempotency_key="seed-run-hello",
        created_at=now,
        finished_at=now,
    )
    session.add(sample)
    await session.commit()
