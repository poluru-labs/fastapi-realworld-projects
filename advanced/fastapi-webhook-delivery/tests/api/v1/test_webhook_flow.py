import json

from fastapi.testclient import TestClient

from app.api.v1.endpoints.capture import CAPTURED
from app.core.webhook_signing import verify_signature
from tests.api.v1.helpers import auth_headers


def test_publish_delivers_to_capture_with_signature(client: TestClient) -> None:
    headers = auth_headers(client, "publisher@example.com")
    created = client.post(
        "/api/v1/webhook-endpoints",
        headers=headers,
        json={
            "url": "http://testserver/api/v1/dev/capture",
            "description": "Test sink",
            "event_types": ["order.created"],
        },
    )
    assert created.status_code == 201
    secret = created.json()["signing_secret"]

    published = client.post(
        "/api/v1/webhook-events",
        headers={**headers, "Idempotency-Key": "evt-1"},
        json={
            "event_type": "order.created",
            "payload": {"order_id": "ord_1"},
        },
    )
    assert published.status_code == 201
    event_id = published.json()["id"]

    again = client.post(
        "/api/v1/webhook-events",
        headers={**headers, "Idempotency-Key": "evt-1"},
        json={"event_type": "order.created", "payload": {"order_id": "ord_1"}},
    )
    assert again.json()["id"] == event_id

    assert len(CAPTURED) == 1
    captured = CAPTURED[0]
    body = captured["body"].encode("utf-8")
    timestamp = captured["timestamp"]
    hdrs = {key.lower(): value for key, value in captured["headers"].items()}
    signature_hex = hdrs["x-webhook-signature"].removeprefix("sha256=")
    assert verify_signature(
        secret=secret,
        timestamp=timestamp,
        body=body,
        signature_hex=signature_hex,
    )
    payload = json.loads(captured["body"])
    assert payload["type"] == "order.created"

    deliveries = client.get(f"/api/v1/webhook-events/{event_id}/deliveries", headers=headers)
    assert deliveries.status_code == 200
    assert deliveries.json()[0]["status"] == "succeeded"


def test_event_type_filter_skips_non_matching_endpoint(client: TestClient) -> None:
    headers = auth_headers(client, "filter@example.com")
    client.post(
        "/api/v1/webhook-endpoints",
        headers=headers,
        json={
            "url": "http://testserver/api/v1/dev/capture",
            "event_types": ["invoice.paid"],
        },
    )
    before = len(CAPTURED)
    client.post(
        "/api/v1/webhook-events",
        headers={**headers, "Idempotency-Key": "evt-2"},
        json={"event_type": "order.created", "payload": {}},
    )
    assert len(CAPTURED) == before


def test_other_users_event_not_found(client: TestClient) -> None:
    owner = auth_headers(client, "owner@example.com")
    other = auth_headers(client, "other@example.com")
    client.post(
        "/api/v1/webhook-endpoints",
        headers=owner,
        json={"url": "http://testserver/api/v1/dev/capture", "event_types": ["*"]},
    )
    event = client.post(
        "/api/v1/webhook-events",
        headers={**owner, "Idempotency-Key": "evt-3"},
        json={"event_type": "ping", "payload": {}},
    ).json()
    response = client.get(f"/api/v1/webhook-events/{event['id']}", headers=other)
    assert response.status_code == 404
