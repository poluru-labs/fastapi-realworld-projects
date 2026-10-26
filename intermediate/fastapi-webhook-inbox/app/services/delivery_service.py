from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.webhook_repository import DeliveryRecord, WebhookRepository
from app.schemas.user import UserRead, UserRole
from app.schemas.webhook import DeliveryIngest, DeliveryRead, DeliveryStatus, EndpointStatus


class DeliveryService:
    def __init__(self, repository: WebhookRepository) -> None:
        self._repo = repository

    def list_deliveries(
        self,
        current_user: UserRead,
        *,
        endpoint_slug: str | None,
        status: DeliveryStatus | None,
    ) -> list[DeliveryRead]:
        rows = self._visible_deliveries(current_user, endpoint_slug)
        if status is not None:
            rows = [row for row in rows if row.status is status]
        rows.sort(key=lambda row: row.received_at, reverse=True)
        return [self._read(row) for row in rows]

    def list_for_endpoint(self, current_user: UserRead, slug: str) -> list[DeliveryRead]:
        endpoint = self._require_endpoint_access(current_user, slug)
        rows = self._repo.list_deliveries_for_endpoint(endpoint.id)
        return [self._read(row) for row in rows]

    def get_delivery(self, current_user: UserRead, delivery_id: int) -> DeliveryRead:
        return self._read(self._require_delivery_access(current_user, delivery_id))

    def ack(self, current_user: UserRead, delivery_id: int) -> DeliveryRead:
        delivery = self._require_delivery_access(current_user, delivery_id)
        if delivery.status is DeliveryStatus.ACKED:
            raise ConflictError("Delivery is already acknowledged")
        delivery.status = DeliveryStatus.ACKED
        delivery.acked_at = datetime.now(UTC)
        return self._read(delivery)

    def ingest(
        self,
        slug: str,
        token: str,
        idempotency_key: str,
        payload: DeliveryIngest,
    ) -> DeliveryRead:
        from app.core.webhook_tokens import verify_webhook_token

        endpoint = self._repo.get_endpoint_by_slug(slug)
        if endpoint is None or not verify_webhook_token(token, endpoint.token_hash):
            raise NotFoundError("Endpoint", slug)
        if endpoint.status is EndpointStatus.PAUSED:
            raise ConflictError("Endpoint is paused and does not accept deliveries")

        cached = self._repo.get_idempotency(endpoint.id, idempotency_key)
        if cached is not None:
            delivery = self._repo.get_delivery(cached.delivery_id)
            if delivery is None:
                raise NotFoundError("Delivery", cached.delivery_id)
            return DeliveryRead.model_validate_json(cached.response_json)

        now = datetime.now(UTC)
        delivery = DeliveryRecord(
            id=self._repo.allocate_delivery_id(),
            endpoint_id=endpoint.id,
            event_type=payload.event_type,
            payload=dict(payload.payload),
            status=DeliveryStatus.PENDING,
            retry_count=0,
            idempotency_key=idempotency_key,
            received_at=now,
        )
        self._repo.add_delivery(delivery)
        body = self._read(delivery)
        from app.repositories.webhook_repository import IngestIdempotencyRecord

        self._repo.save_idempotency(
            IngestIdempotencyRecord(
                endpoint_id=endpoint.id,
                idempotency_key=idempotency_key,
                delivery_id=delivery.id,
                response_json=body.model_dump_json(),
            )
        )
        return body

    def _visible_deliveries(
        self,
        current_user: UserRead,
        endpoint_slug: str | None,
    ) -> list[DeliveryRecord]:
        if endpoint_slug is not None:
            endpoint = self._require_endpoint_access(current_user, endpoint_slug)
            return self._repo.list_deliveries_for_endpoint(endpoint.id)
        if current_user.role is UserRole.ADMIN:
            endpoint_ids = {row.id for row in self._repo.list_endpoints()}
        else:
            endpoint_ids = {row.id for row in self._repo.list_endpoints_for_owner(current_user.id)}
        return [row for row in self._repo.list_deliveries() if row.endpoint_id in endpoint_ids]

    def _require_endpoint_access(self, current_user: UserRead, slug: str):
        record = self._repo.get_endpoint_by_slug(slug)
        if record is None:
            raise NotFoundError("Endpoint", slug)
        if current_user.role is not UserRole.ADMIN and record.owner_id != current_user.id:
            raise NotFoundError("Endpoint", slug)
        return record

    def _require_delivery_access(self, current_user: UserRead, delivery_id: int) -> DeliveryRecord:
        delivery = self._repo.get_delivery(delivery_id)
        if delivery is None:
            raise NotFoundError("Delivery", delivery_id)
        endpoint = self._repo.get_endpoint_by_id(delivery.endpoint_id)
        if endpoint is None:
            raise NotFoundError("Delivery", delivery_id)
        if current_user.role is not UserRole.ADMIN and endpoint.owner_id != current_user.id:
            raise NotFoundError("Delivery", delivery_id)
        return delivery

    def _read(self, delivery: DeliveryRecord) -> DeliveryRead:
        endpoint = self._repo.get_endpoint_by_id(delivery.endpoint_id)
        slug = endpoint.slug if endpoint is not None else "unknown"
        return DeliveryRead(
            id=delivery.id,
            endpoint_id=delivery.endpoint_id,
            endpoint_slug=slug,
            event_type=delivery.event_type,
            payload=delivery.payload,
            status=delivery.status,
            retry_count=delivery.retry_count,
            received_at=delivery.received_at,
            acked_at=delivery.acked_at,
        )
