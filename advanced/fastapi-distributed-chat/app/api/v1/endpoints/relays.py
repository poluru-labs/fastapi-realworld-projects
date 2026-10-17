from typing import Annotated

from fastapi import APIRouter, Body

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.chat import (
    ClaimDeliveryRequest,
    CompleteDeliveryRequest,
    DeliveryRead,
    RelayHeartbeat,
    RelayRegister,
)
from app.services.delivery_service import DeliveryService

router = APIRouter(prefix="/relays", tags=["relays"])

_REGISTER_EXAMPLES = {
    "general_relay": {
        "summary": "Relay limited to the general room",
        "value": {"relay_id": "edge-us-east-1", "room_slugs": ["general"]},
    }
}


@router.post(
    "/register",
    summary="Register a relay identity",
    description=(
        "Empty **room_slugs** means the relay may claim deliveries for any room. "
        "Otherwise only listed slugs are considered during claim."
    ),
)
async def register_relay(
    payload: Annotated[RelayRegister, Body(openapi_examples=_REGISTER_EXAMPLES)],
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> dict[str, str]:
    return await DeliveryService(session, settings).register_relay(user, payload)


@router.post("/heartbeat", summary="Refresh relay liveness")
async def relay_heartbeat(
    payload: RelayHeartbeat,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> dict[str, str]:
    return await DeliveryService(session, settings).heartbeat(user, payload)


@router.post(
    "/claim",
    response_model=DeliveryRead,
    summary="Claim the next pending delivery",
    description=(
        "Finds the oldest **pending** outbox row whose lease is free or expired, "
        "optionally filtered by the relay's **room_slugs**. Sets status to **delivering**."
    ),
)
async def claim_delivery(
    payload: ClaimDeliveryRequest,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> DeliveryRead:
    return await DeliveryService(session, settings).claim(user, payload)


@router.post(
    "/deliveries/{delivery_id}/complete",
    response_model=DeliveryRead,
    summary="Mark a leased delivery as delivered",
    description=(
        "Requires matching **relay_id**, valid lease, and **expected_version**. "
        "Stale relays receive **409** after another claim or completion."
    ),
)
async def complete_delivery(
    delivery_id: int,
    payload: CompleteDeliveryRequest,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> DeliveryRead:
    return await DeliveryService(session, settings).complete(user, delivery_id, payload)
