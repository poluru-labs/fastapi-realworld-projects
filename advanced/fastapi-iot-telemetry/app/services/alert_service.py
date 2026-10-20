from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.telemetry import TelemetryAlertRule
from app.repositories.alert_repository import AlertRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.reading_repository import ReadingRepository
from app.schemas.telemetry import (
    AlertEvaluation,
    AlertRuleCreate,
    AlertRuleRead,
    AlertStatus,
    Comparator,
)


def _compare(observed: float, threshold: float, comparator: Comparator) -> bool:
    if comparator is Comparator.GTE:
        return observed >= threshold
    if comparator is Comparator.GT:
        return observed > threshold
    if comparator is Comparator.LTE:
        return observed <= threshold
    return observed < threshold


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._devices = DeviceRepository(session)
        self._alerts = AlertRepository(session)
        self._readings = ReadingRepository(session)

    async def list_rules(self, device_key: str) -> list[AlertRuleRead]:
        device = await self._require_device(device_key)
        rows = await self._alerts.list_for_device(device.id)
        return [AlertRuleRead.model_validate(row) for row in rows]

    async def create_rule(self, device_key: str, payload: AlertRuleCreate) -> AlertRuleRead:
        device = await self._require_device(device_key)
        rule = TelemetryAlertRule(
            device_id=device.id,
            name=payload.name,
            metric_key=payload.metric_key,
            window_minutes=payload.window_minutes,
            threshold=payload.threshold,
            comparator=payload.comparator.value,
            status=AlertStatus.ENABLED.value,
            created_at=datetime.now(UTC),
        )
        await self._alerts.add(rule)
        await self._session.commit()
        return AlertRuleRead.model_validate(rule)

    async def disable_rule(self, device_key: str, rule_id: int) -> AlertRuleRead:
        device = await self._require_device(device_key)
        rule = await self._require_rule(rule_id, device.id)
        if rule.status == AlertStatus.DISABLED.value:
            raise ConflictError("Rule is already disabled")
        rule.status = AlertStatus.DISABLED.value
        await self._alerts.save()
        await self._session.commit()
        return AlertRuleRead.model_validate(rule)

    async def evaluate(self, device_key: str) -> list[AlertEvaluation]:
        device = await self._require_device(device_key)
        rules = await self._alerts.list_for_device(device.id)
        now = datetime.now(UTC)
        results: list[AlertEvaluation] = []
        for rule in rules:
            if rule.status != AlertStatus.ENABLED.value:
                continue
            since = now - timedelta(minutes=rule.window_minutes)
            rows = await self._readings.list_since(device.id, since)
            values: list[float] = []
            for row in rows:
                raw = row.metrics.get(rule.metric_key)
                if isinstance(raw, bool):
                    values.append(1.0 if raw else 0.0)
                elif isinstance(raw, (int, float)):
                    values.append(float(raw))
            observed = max(values) if values else None
            firing = False
            if observed is not None:
                firing = _compare(observed, rule.threshold, Comparator(rule.comparator))
            results.append(
                AlertEvaluation(
                    rule=AlertRuleRead.model_validate(rule),
                    observed_value=observed,
                    firing=firing,
                )
            )
        return results

    async def _require_device(self, key: str):
        device = await self._devices.get_by_key(key)
        if device is None:
            raise NotFoundError("Device", key)
        return device

    async def _require_rule(self, rule_id: int, device_id: int) -> TelemetryAlertRule:
        rule = await self._alerts.get(rule_id)
        if rule is None or rule.device_id != device_id:
            raise NotFoundError("AlertRule", rule_id)
        return rule
