from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AlertRule


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_stream(self, stream_id: int) -> list[AlertRule]:
        result = await self._session.scalars(
            select(AlertRule)
            .where(AlertRule.stream_id == stream_id)
            .order_by(AlertRule.id)
        )
        return list(result)

    async def get(self, rule_id: int) -> AlertRule | None:
        return await self._session.get(AlertRule, rule_id)

    async def add(self, rule: AlertRule) -> AlertRule:
        self._session.add(rule)
        await self._session.flush()
        return rule

    async def save(self) -> None:
        await self._session.flush()
