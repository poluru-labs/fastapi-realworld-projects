from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import TelemetryAlertRule


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_device(self, device_id: int) -> list[TelemetryAlertRule]:
        result = await self._session.scalars(
            select(TelemetryAlertRule)
            .where(TelemetryAlertRule.device_id == device_id)
            .order_by(TelemetryAlertRule.id)
        )
        return list(result)

    async def get(self, rule_id: int) -> TelemetryAlertRule | None:
        return await self._session.get(TelemetryAlertRule, rule_id)

    async def add(self, rule: TelemetryAlertRule) -> TelemetryAlertRule:
        self._session.add(rule)
        await self._session.flush()
        return rule

    async def save(self) -> None:
        await self._session.flush()
