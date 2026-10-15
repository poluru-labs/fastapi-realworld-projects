from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, IdempotencyKey, WebhookHttpClient
from app.schemas.webhook import WebhookDeliveryRead
from app.services.delivery_service import DeliveryService

router = APIRouter(prefix="/webhook-deliveries", tags=["webhook-deliveries"])


@router.post(
    "/{delivery_id}/retry",
    response_model=WebhookDeliveryRead,
    summary="Retry a failed delivery",
    description=(
        "Creates a new attempt row with an incremented `attempt_number`. "
        "Requires **Idempotency-Key**."
    ),
)
async def retry_delivery(
    delivery_id: int,
    user: CurrentUser,
    session: DbSession,
    http_client: WebhookHttpClient,
    idempotency_key: IdempotencyKey,
) -> WebhookDeliveryRead:
    return await DeliveryService(session, http_client).retry_delivery(
        user,
        delivery_id,
        idempotency_key=idempotency_key,
    )
