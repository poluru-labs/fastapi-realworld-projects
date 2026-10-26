from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from app.core.webhook_tokens import hash_webhook_token
from app.schemas.webhook import DeliveryStatus, EndpointStatus

SEED_WEBHOOK_TOKEN = "seed-webhook-billing-stripe"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class EndpointRecord:
    id: int
    owner_id: int
    slug: str
    name: str
    description: str
    status: EndpointStatus
    token_hash: str
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class DeliveryRecord:
    id: int
    endpoint_id: int
    event_type: str
    payload: dict[str, Any]
    status: DeliveryStatus
    retry_count: int
    idempotency_key: str | None
    received_at: datetime = field(default_factory=_utcnow)
    acked_at: datetime | None = None


@dataclass
class IngestIdempotencyRecord:
    endpoint_id: int
    idempotency_key: str
    delivery_id: int
    response_json: str


def _seed() -> tuple[dict[str, EndpointRecord], dict[int, DeliveryRecord]]:
    now = _utcnow()
    endpoints = {
        "billing-stripe": EndpointRecord(
            id=1,
            owner_id=1,
            slug="billing-stripe",
            name="Stripe billing",
            description="Sample checkout and invoice webhooks.",
            status=EndpointStatus.ACTIVE,
            token_hash=hash_webhook_token(SEED_WEBHOOK_TOKEN),
            created_at=now,
        ),
        "crm-sync": EndpointRecord(
            id=2,
            owner_id=2,
            slug="crm-sync",
            name="CRM sync",
            description="Demo user endpoint (paused in seed).",
            status=EndpointStatus.PAUSED,
            token_hash=hash_webhook_token("seed-webhook-crm-sync"),
            created_at=now,
        ),
    }
    deliveries = {
        1: DeliveryRecord(
            id=1,
            endpoint_id=1,
            event_type="invoice.paid",
            payload={"id": "inv_seed_1", "amount": 1200},
            status=DeliveryStatus.PENDING,
            retry_count=0,
            idempotency_key=None,
            received_at=datetime.fromisoformat("2026-03-10T10:00:00+00:00"),
        ),
        2: DeliveryRecord(
            id=2,
            endpoint_id=1,
            event_type="customer.created",
            payload={"id": "cus_seed_1"},
            status=DeliveryStatus.ACKED,
            retry_count=0,
            idempotency_key=None,
            received_at=datetime.fromisoformat("2026-03-09T15:30:00+00:00"),
            acked_at=datetime.fromisoformat("2026-03-09T16:00:00+00:00"),
        ),
    }
    return endpoints, deliveries


class WebhookRepository:
    def __init__(self) -> None:
        self._endpoints, self._deliveries = _seed()
        self._idempotency: dict[tuple[int, str], IngestIdempotencyRecord] = {}
        self._next_endpoint_id = 3
        self._next_delivery_id = 3

    def list_endpoints(self) -> list[EndpointRecord]:
        return list(self._endpoints.values())

    def list_endpoints_for_owner(self, owner_id: int) -> list[EndpointRecord]:
        return [row for row in self._endpoints.values() if row.owner_id == owner_id]

    def get_endpoint_by_slug(self, slug: str) -> EndpointRecord | None:
        return self._endpoints.get(slug)

    def get_endpoint_by_id(self, endpoint_id: int) -> EndpointRecord | None:
        for row in self._endpoints.values():
            if row.id == endpoint_id:
                return row
        return None

    def slug_exists(self, slug: str) -> bool:
        return slug in self._endpoints

    def add_endpoint(self, record: EndpointRecord) -> EndpointRecord:
        self._endpoints[record.slug] = record
        return record

    def allocate_endpoint_id(self) -> int:
        endpoint_id = self._next_endpoint_id
        self._next_endpoint_id += 1
        return endpoint_id

    def delete_endpoint(self, slug: str) -> EndpointRecord | None:
        record = self._endpoints.pop(slug, None)
        if record is None:
            return None
        to_remove = [did for did, d in self._deliveries.items() if d.endpoint_id == record.id]
        for did in to_remove:
            del self._deliveries[did]
        return record

    def list_deliveries(self) -> list[DeliveryRecord]:
        return list(self._deliveries.values())

    def list_deliveries_for_endpoint(self, endpoint_id: int) -> list[DeliveryRecord]:
        rows = [row for row in self._deliveries.values() if row.endpoint_id == endpoint_id]
        rows.sort(key=lambda row: row.received_at, reverse=True)
        return rows

    def get_delivery(self, delivery_id: int) -> DeliveryRecord | None:
        return self._deliveries.get(delivery_id)

    def add_delivery(self, record: DeliveryRecord) -> DeliveryRecord:
        self._deliveries[record.id] = record
        return record

    def allocate_delivery_id(self) -> int:
        delivery_id = self._next_delivery_id
        self._next_delivery_id += 1
        return delivery_id

    def delivery_count(self, endpoint_id: int) -> int:
        return len(self.list_deliveries_for_endpoint(endpoint_id))

    def pending_count(self, endpoint_id: int) -> int:
        return sum(
            1
            for row in self._deliveries.values()
            if row.endpoint_id == endpoint_id and row.status is DeliveryStatus.PENDING
        )

    def get_idempotency(
        self,
        endpoint_id: int,
        idempotency_key: str,
    ) -> IngestIdempotencyRecord | None:
        return self._idempotency.get((endpoint_id, idempotency_key))

    def save_idempotency(self, record: IngestIdempotencyRecord) -> None:
        self._idempotency[(record.endpoint_id, record.idempotency_key)] = record


@lru_cache
def get_webhook_repository() -> WebhookRepository:
    return WebhookRepository()
