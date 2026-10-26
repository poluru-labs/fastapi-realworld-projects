from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import IdempotencyKey, WebhookToken, get_delivery_service
from app.schemas.webhook import SLUG_PATTERN, DeliveryIngest, DeliveryRead
from app.services.delivery_service import DeliveryService

router = APIRouter()

HookSlug = Annotated[
    str,
    Path(pattern=SLUG_PATTERN.pattern, min_length=2, max_length=64),
]


@router.post(
    "/{slug}/deliveries",
    response_model=DeliveryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a webhook delivery",
    description=(
        "Public ingest for senders. Requires **X-Webhook-Token** and **Idempotency-Key**. "
        "Invalid slug or token returns **404**. Paused endpoints return **409**."
    ),
)
def ingest_delivery(
    slug: HookSlug,
    token: WebhookToken,
    idempotency_key: IdempotencyKey,
    payload: DeliveryIngest,
    service: Annotated[DeliveryService, Depends(get_delivery_service)],
) -> DeliveryRead:
    return service.ingest(slug, token, idempotency_key, payload)
