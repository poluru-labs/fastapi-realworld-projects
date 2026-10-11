from fastapi import APIRouter, Body, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.hold import HoldCreate, HoldRead
from app.services.hold_service import HoldService

router = APIRouter(prefix="/holds", tags=["holds"])

_HOLD_EXAMPLE = {
    "general": {
        "summary": "Hold two general tickets",
        "description": "Hold TTL defaults to 15 minutes (see HOLD_TTL_MINUTES).",
        "value": {"tier_id": 1, "quantity": 2},
    }
}


@router.get("/mine", response_model=list[HoldRead], summary="Your active holds")
async def list_my_holds(
    actor: CurrentUser,
    session: DbSession,
    settings: AppSettings,
) -> list[HoldRead]:
    return await HoldService(session, settings).list_mine(actor)


@router.post(
    "",
    response_model=HoldRead,
    status_code=status.HTTP_201_CREATED,
    summary="Hold tickets",
    description=(
        "Soft-reserves capacity without charging. Expired holds are marked automatically "
        "on the next availability check."
    ),
)
async def create_hold(
    actor: CurrentUser,
    session: DbSession,
    settings: AppSettings,
    payload: HoldCreate = Body(openapi_examples=_HOLD_EXAMPLE),
) -> HoldRead:
    return await HoldService(session, settings).create_hold(actor, payload)


@router.delete("/{hold_id}", response_model=HoldRead, summary="Release a hold early")
async def release_hold(
    hold_id: int,
    actor: CurrentUser,
    session: DbSession,
    settings: AppSettings,
) -> HoldRead:
    return await HoldService(session, settings).release_hold(actor, hold_id)
