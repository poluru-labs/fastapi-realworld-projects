from typing import Annotated

from fastapi import APIRouter, Body, Path, status

from app.api.deps import (
    AppSettings,
    CurrentUser,
    DbSession,
    IdempotencyKey,
    OptionalUser,
)
from app.schemas.scheduler import (
    SLUG_PATTERN,
    ScheduleCreate,
    ScheduledRunRead,
    ScheduleRead,
    ScheduleUpdate,
    TriggerRunRequest,
)
from app.services.run_service import RunService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])

Slug = Annotated[str, Path(pattern=SLUG_PATTERN.pattern, min_length=1, max_length=64)]

_OPTIONAL_BEARER = {"security": [{}, {"HTTPBearer": []}]}

_CREATE_EXAMPLES = {
    "interval": {
        "summary": "Interval schedule (draft until publish)",
        "value": {
            "name": "Hourly sync",
            "schedule_kind": "interval",
            "interval_seconds": 3600,
            "task_type": "sync",
            "default_payload": {"target": "warehouse"},
        },
    }
}

_TRIGGER_EXAMPLES = {
    "default_payload": {
        "summary": "Merge payload with schedule defaults",
        "value": {"payload": {"report_name": "daily-summary"}},
    }
}


@router.get("", response_model=list[ScheduleRead], summary="List published schedules")
async def list_schedules(session: DbSession) -> list[ScheduleRead]:
    return await ScheduleService(session).list_published()


@router.get("/mine", response_model=list[ScheduleRead], summary="List schedules you own")
async def list_my_schedules(session: DbSession, user: CurrentUser) -> list[ScheduleRead]:
    return await ScheduleService(session).list_mine(user)


@router.post(
    "",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft schedule",
)
async def create_schedule(
    payload: Annotated[ScheduleCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    session: DbSession,
    user: CurrentUser,
) -> ScheduleRead:
    return await ScheduleService(session).create_schedule(user, payload)


@router.get(
    "/{slug}",
    response_model=ScheduleRead,
    summary="Get one schedule",
    description="Published schedules are public. Drafts require owner or admin token.",
    openapi_extra=_OPTIONAL_BEARER,
)
async def get_schedule(
    slug: Slug,
    session: DbSession,
    user: OptionalUser,
) -> ScheduleRead:
    return await ScheduleService(session).get_schedule(user, slug)


@router.patch("/{slug}", response_model=ScheduleRead, summary="Update schedule (owner)")
async def update_schedule(
    slug: Slug,
    payload: ScheduleUpdate,
    session: DbSession,
    user: CurrentUser,
) -> ScheduleRead:
    return await ScheduleService(session).update_schedule(user, slug, payload)


@router.post("/{slug}/publish", response_model=ScheduleRead, summary="Publish draft")
async def publish_schedule(slug: Slug, session: DbSession, user: CurrentUser) -> ScheduleRead:
    return await ScheduleService(session).publish(user, slug)


@router.post("/{slug}/pause", response_model=ScheduleRead, summary="Pause published schedule")
async def pause_schedule(slug: Slug, session: DbSession, user: CurrentUser) -> ScheduleRead:
    return await ScheduleService(session).pause(user, slug)


@router.post("/{slug}/resume", response_model=ScheduleRead, summary="Resume paused schedule")
async def resume_schedule(slug: Slug, session: DbSession, user: CurrentUser) -> ScheduleRead:
    return await ScheduleService(session).resume(user, slug)


@router.post("/{slug}/archive", response_model=ScheduleRead, summary="Archive schedule")
async def archive_schedule(slug: Slug, session: DbSession, user: CurrentUser) -> ScheduleRead:
    return await ScheduleService(session).archive(user, slug)


@router.post("/{slug}/restore", response_model=ScheduleRead, summary="Restore archived to draft")
async def restore_schedule(slug: Slug, session: DbSession, user: CurrentUser) -> ScheduleRead:
    return await ScheduleService(session).restore(user, slug)


@router.post(
    "/{slug}/trigger",
    response_model=ScheduledRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue a run now",
    description=(
        "Requires **Idempotency-Key**. Schedule must be **published**. "
        "Workers claim pending runs with a time-bounded lease."
    ),
)
async def trigger_schedule(
    slug: Slug,
    payload: Annotated[TriggerRunRequest, Body(openapi_examples=_TRIGGER_EXAMPLES)],
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
    idempotency_key: IdempotencyKey,
) -> ScheduledRunRead:
    return await RunService(session, settings).trigger(
        user,
        slug,
        payload,
        idempotency_key=idempotency_key,
    )
