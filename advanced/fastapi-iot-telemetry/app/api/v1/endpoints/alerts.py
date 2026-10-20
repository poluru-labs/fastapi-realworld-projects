from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.telemetry import (
    DEVICE_KEY_PATTERN,
    AlertEvaluation,
    AlertRuleCreate,
    AlertRuleRead,
)
from app.services.alert_service import AlertService

router = APIRouter()

DeviceKey = Annotated[
    str,
    Path(pattern=DEVICE_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[AlertRuleRead],
    summary="List alert rules",
)
async def list_rules(_: AdminKey, session: DbSession, device_key: DeviceKey) -> list[AlertRuleRead]:
    return await AlertService(session).list_rules(device_key)


@router.post(
    "",
    response_model=AlertRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an alert rule",
    description=(
        "Evaluates the **maximum** metric value in the window against the threshold "
        "using the chosen comparator."
    ),
)
async def create_rule(
    _: AdminKey,
    session: DbSession,
    device_key: DeviceKey,
    payload: AlertRuleCreate,
) -> AlertRuleRead:
    return await AlertService(session).create_rule(device_key, payload)


@router.post(
    "/{rule_id}/disable",
    response_model=AlertRuleRead,
    summary="Disable a rule",
)
async def disable_rule(
    _: AdminKey,
    session: DbSession,
    device_key: DeviceKey,
    rule_id: int,
) -> AlertRuleRead:
    return await AlertService(session).disable_rule(device_key, rule_id)


@router.get(
    "/evaluate",
    response_model=list[AlertEvaluation],
    summary="Evaluate enabled rules",
)
async def evaluate_rules(
    _: AdminKey,
    session: DbSession,
    device_key: DeviceKey,
) -> list[AlertEvaluation]:
    return await AlertService(session).evaluate(device_key)
