from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.analytics import (
    STREAM_KEY_PATTERN,
    AlertEvaluation,
    AlertRuleCreate,
    AlertRuleRead,
)
from app.services.alert_service import AlertService

router = APIRouter()

StreamKey = Annotated[
    str,
    Path(pattern=STREAM_KEY_PATTERN.pattern, min_length=1, max_length=64),
]


@router.get(
    "",
    response_model=list[AlertRuleRead],
    summary="List alert rules",
    description="Admin key required.",
)
async def list_alert_rules(
    _: AdminKey,
    session: DbSession,
    stream_key: StreamKey,
) -> list[AlertRuleRead]:
    return await AlertService(session).list_rules(stream_key)


@router.post(
    "",
    response_model=AlertRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an alert rule",
    description=(
        "Fires when the count of events with `occurred_at` in the last "
        "`window_minutes` is **greater than or equal to** `threshold_count`."
    ),
)
async def create_alert_rule(
    _: AdminKey,
    session: DbSession,
    stream_key: StreamKey,
    payload: AlertRuleCreate,
) -> AlertRuleRead:
    return await AlertService(session).create_rule(stream_key, payload)


@router.post(
    "/{rule_id}/disable",
    response_model=AlertRuleRead,
    summary="Disable a rule",
)
async def disable_alert_rule(
    _: AdminKey,
    session: DbSession,
    stream_key: StreamKey,
    rule_id: int,
) -> AlertRuleRead:
    return await AlertService(session).disable_rule(stream_key, rule_id)


@router.get(
    "/evaluate",
    response_model=list[AlertEvaluation],
    summary="Evaluate enabled rules now",
    description=(
        "Admin key required. This is a synchronous check for demos; production "
        "systems would schedule evaluators or stream processors."
    ),
)
async def evaluate_alerts(
    _: AdminKey,
    session: DbSession,
    stream_key: StreamKey,
) -> list[AlertEvaluation]:
    return await AlertService(session).evaluate(stream_key)
