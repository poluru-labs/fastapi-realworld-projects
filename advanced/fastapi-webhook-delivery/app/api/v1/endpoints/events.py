from typing import Annotated

from fastapi import APIRouter, Body, status

from app.api.deps import CurrentUser, DbSession, IdempotencyKey, WebhookHttpClient
from app.schemas.webhook import (
    WebhookDeliveryRead,
    WebhookEventCreate,
    WebhookEventRead,
)
from app.services.delivery_service import DeliveryService

router = APIRouter(prefix="/webhook-events", tags=["webhook-events"])

_PUBLISH_EXAMPLES = {
    "order": {
        "summary": "Publish an order.created event",
        "description": (
            "Fans out to every **enabled** endpoint whose `event_types` match. "
            "Requires **Idempotency-Key** so retries do not double-deliver."
        ),
        "value": {
            "event_type": "order.created",
            "payload": {"order_id": "ord_123", "total_cents": 4999},
        },
    }
}


@router.get("", response_model=list[WebhookEventRead], summary="List events you published")
async def list_events(user: CurrentUser, session: DbSession) -> list[WebhookEventRead]:
    return await DeliveryService(session).list_events(user)


@router.get(
    "/{event_id}",
    response_model=WebhookEventRead,
    summary="Get one published event",
)
async def get_event(
    event_id: int,
    user: CurrentUser,
    session: DbSession,
) -> WebhookEventRead:
    return await DeliveryService(session).get_event(user, event_id)


@router.get(
    "/{event_id}/deliveries",
    response_model=list[WebhookDeliveryRead],
    summary="List delivery attempts for an event",
)
async def list_event_deliveries(
    event_id: int,
    user: CurrentUser,
    session: DbSession,
) -> list[WebhookDeliveryRead]:
    return await DeliveryService(session).list_deliveries(user, event_id)


@router.post(
    "",
    response_model=WebhookEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Publish an event and deliver webhooks",
)
async def publish_event(
    user: CurrentUser,
    session: DbSession,
    http_client: WebhookHttpClient,
    idempotency_key: IdempotencyKey,
    payload: Annotated[WebhookEventCreate, Body(openapi_examples=_PUBLISH_EXAMPLES)],
) -> WebhookEventRead:
    return await DeliveryService(session, http_client).publish_event(
        user,
        payload,
        idempotency_key=idempotency_key,
    )
