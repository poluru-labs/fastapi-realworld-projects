"""Publish events, sign outbound HTTP calls, record delivery attempts."""

import json
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.webhook_signing import sign_payload
from app.models.webhook import WebhookDelivery, WebhookEndpoint, WebhookEvent
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.webhook_repository import (
    WebhookDeliveryRepository,
    WebhookEndpointRepository,
    WebhookEventRepository,
)
from app.schemas.user import UserRead, UserRole
from app.schemas.webhook import (
    DeliveryStatus,
    WebhookDeliveryRead,
    WebhookEventCreate,
    WebhookEventRead,
)


def endpoint_matches_event(endpoint: WebhookEndpoint, event_type: str) -> bool:
    types = endpoint.event_types or ["*"]
    if "*" in types:
        return True
    return event_type in types


class DeliveryService:
    def __init__(
        self,
        session: AsyncSession,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._session = session
        self._http = http_client
        self._endpoints = WebhookEndpointRepository(session)
        self._events = WebhookEventRepository(session)
        self._deliveries = WebhookDeliveryRepository(session)
        self._idempotency = IdempotencyRepository(session)

    async def list_events(self, actor: UserRead) -> list[WebhookEventRead]:
        rows = await self._events.list_for_owner(actor.id)
        return [WebhookEventRead.model_validate(row) for row in rows]

    async def get_event(self, actor: UserRead, event_id: int) -> WebhookEventRead:
        row = await self._require_event(actor, event_id)
        return WebhookEventRead.model_validate(row)

    async def list_deliveries(self, actor: UserRead, event_id: int) -> list[WebhookDeliveryRead]:
        await self._require_event(actor, event_id)
        rows = await self._deliveries.list_for_event(event_id)
        return [await self._delivery_read(row) for row in rows]

    async def publish_event(
        self,
        actor: UserRead,
        payload: WebhookEventCreate,
        *,
        idempotency_key: str,
    ) -> WebhookEventRead:
        existing = await self._events.get_by_idempotency(actor.id, idempotency_key)
        if existing is not None:
            return WebhookEventRead.model_validate(existing)

        event = WebhookEvent(
            owner_id=actor.id,
            event_type=payload.event_type,
            payload=dict(payload.payload),
            idempotency_key=idempotency_key,
        )
        await self._events.add(event)

        targets = await self._endpoints.list_enabled_for_owner(actor.id)
        for endpoint in targets:
            if endpoint_matches_event(endpoint, payload.event_type):
                await self._attempt_delivery(event=event, endpoint=endpoint, attempt_number=1)

        await self._session.commit()
        return WebhookEventRead.model_validate(event)

    async def retry_delivery(
        self,
        actor: UserRead,
        delivery_id: int,
        *,
        idempotency_key: str,
    ) -> WebhookDeliveryRead:
        row = await self._deliveries.get(delivery_id)
        if row is None:
            raise NotFoundError("WebhookDelivery", delivery_id)
        event = await self._events.get(row.event_id)
        endpoint = await self._endpoints.get(row.endpoint_id)
        if event is None or endpoint is None:
            raise NotFoundError("WebhookDelivery", delivery_id)
        if not self._can_view(actor, event):
            raise NotFoundError("WebhookDelivery", delivery_id)
        if row.status == DeliveryStatus.SUCCEEDED.value:
            raise ConflictError("Delivery already succeeded")

        cached = await self._load_retry_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        next_attempt = row.attempt_number + 1
        delivery = await self._attempt_delivery(
            event=event,
            endpoint=endpoint,
            attempt_number=next_attempt,
        )
        result = await self._delivery_read(delivery)
        await self._store_retry_idempotent(actor, idempotency_key, result)
        await self._session.commit()
        return result

    async def _attempt_delivery(
        self,
        *,
        event: WebhookEvent,
        endpoint: WebhookEndpoint,
        attempt_number: int,
    ) -> WebhookDelivery:
        started = time.perf_counter()
        body_dict = {
            "id": event.id,
            "type": event.event_type,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "data": event.payload,
        }
        body = json.dumps(body_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
        timestamp = str(int(datetime.now(UTC).timestamp()))
        signature = sign_payload(
            secret=endpoint.signing_secret,
            timestamp=timestamp,
            body=body,
        )
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Id": str(event.id),
            "X-Webhook-Event": event.event_type,
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": f"sha256={signature}",
        }

        status = DeliveryStatus.FAILED
        http_status: int | None = None
        error_detail: str | None = None
        if self._http is None:
            raise RuntimeError("HTTP client required for webhook delivery")

        try:
            response = await self._http.post(endpoint.url, content=body, headers=headers)
            http_status = response.status_code
            if 200 <= response.status_code < 300:
                status = DeliveryStatus.SUCCEEDED
            else:
                error_detail = f"HTTP {response.status_code}: {response.text[:500]}"
        except httpx.HTTPError as exc:
            error_detail = str(exc)

        duration_ms = int((time.perf_counter() - started) * 1000)
        now = datetime.now(UTC)
        delivery = WebhookDelivery(
            event_id=event.id,
            endpoint_id=endpoint.id,
            attempt_number=attempt_number,
            status=status.value,
            http_status=http_status,
            error_detail=error_detail,
            duration_ms=duration_ms,
            completed_at=now,
        )
        await self._deliveries.add(delivery)
        return delivery

    async def _require_event(self, actor: UserRead, event_id: int) -> WebhookEvent:
        row = await self._events.get(event_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("WebhookEvent", event_id)
        return row

    async def _delivery_read(self, row: WebhookDelivery) -> WebhookDeliveryRead:
        endpoint = await self._endpoints.get(row.endpoint_id)
        url = endpoint.url if endpoint else "unknown"
        return WebhookDeliveryRead(
            id=row.id,
            event_id=row.event_id,
            endpoint_id=row.endpoint_id,
            endpoint_url=url,
            attempt_number=row.attempt_number,
            status=DeliveryStatus(row.status),
            http_status=row.http_status,
            error_detail=row.error_detail,
            duration_ms=row.duration_ms,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )

    async def _load_retry_idempotent(
        self, actor: UserRead, key: str
    ) -> WebhookDeliveryRead | None:
        row = await self._idempotency.get(key)
        if row is None:
            return None
        if row.user_id != actor.id:
            raise ConflictError("Idempotency key belongs to another user")
        return WebhookDeliveryRead.model_validate_json(row.response_json)

    async def _store_retry_idempotent(
        self,
        actor: UserRead,
        key: str,
        result: WebhookDeliveryRead,
    ) -> None:
        await self._idempotency.save(
            key=key,
            user_id=actor.id,
            response_json=result.model_dump_json(),
            status_code=200,
        )

    @staticmethod
    def _can_view(actor: UserRead, event: WebhookEvent) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return event.owner_id == actor.id
