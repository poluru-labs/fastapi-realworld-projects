from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.analytics import AlertRule
from app.repositories.alert_repository import AlertRepository
from app.repositories.event_repository import EventRepository
from app.repositories.stream_repository import StreamRepository
from app.schemas.analytics import AlertEvaluation, AlertRuleCreate, AlertRuleRead, AlertStatus


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._streams = StreamRepository(session)
        self._alerts = AlertRepository(session)
        self._events = EventRepository(session)

    async def list_rules(self, stream_key: str) -> list[AlertRuleRead]:
        stream = await self._require_stream(stream_key)
        rows = await self._alerts.list_for_stream(stream.id)
        return [AlertRuleRead.model_validate(row) for row in rows]

    async def create_rule(self, stream_key: str, payload: AlertRuleCreate) -> AlertRuleRead:
        stream = await self._require_stream(stream_key)
        rule = AlertRule(
            stream_id=stream.id,
            name=payload.name,
            window_minutes=payload.window_minutes,
            threshold_count=payload.threshold_count,
            status=AlertStatus.ENABLED.value,
            created_at=datetime.now(UTC),
        )
        await self._alerts.add(rule)
        await self._session.commit()
        return AlertRuleRead.model_validate(rule)

    async def disable_rule(self, stream_key: str, rule_id: int) -> AlertRuleRead:
        stream = await self._require_stream(stream_key)
        rule = await self._require_rule(rule_id, stream.id)
        if rule.status == AlertStatus.DISABLED.value:
            raise ConflictError("Rule is already disabled")
        rule.status = AlertStatus.DISABLED.value
        await self._alerts.save()
        await self._session.commit()
        return AlertRuleRead.model_validate(rule)

    async def evaluate(self, stream_key: str) -> list[AlertEvaluation]:
        stream = await self._require_stream(stream_key)
        rules = await self._alerts.list_for_stream(stream.id)
        now = datetime.now(UTC)
        results: list[AlertEvaluation] = []
        for rule in rules:
            if rule.status != AlertStatus.ENABLED.value:
                continue
            since = now - timedelta(minutes=rule.window_minutes)
            observed = await self._events.count_since(stream.id, since)
            firing = observed >= rule.threshold_count
            results.append(
                AlertEvaluation(
                    rule=AlertRuleRead.model_validate(rule),
                    observed_count=observed,
                    firing=firing,
                )
            )
        return results

    async def _require_stream(self, key: str):
        stream = await self._streams.get_by_key(key)
        if stream is None:
            raise NotFoundError("Stream", key)
        return stream

    async def _require_rule(self, rule_id: int, stream_id: int) -> AlertRule:
        rule = await self._alerts.get(rule_id)
        if rule is None or rule.stream_id != stream_id:
            raise NotFoundError("AlertRule", rule_id)
        return rule
