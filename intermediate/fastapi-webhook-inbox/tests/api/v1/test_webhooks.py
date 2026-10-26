from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, ingest_headers

INGEST_BODY = {
    "event_type": "invoice.paid",
    "payload": {"id": "inv_test", "amount": 500},
}


def test_admin_lists_endpoints_and_inbox(client: TestClient) -> None:
    headers = admin_headers(client)
    endpoints = client.get("/api/v1/endpoints", headers=headers)
    assert endpoints.status_code == 200
    assert len(endpoints.json()) == 2

    inbox = client.get("/api/v1/endpoints/billing-stripe/deliveries", headers=headers)
    assert inbox.status_code == 200
    assert len(inbox.json()) == 2

    pending = client.get(
        "/api/v1/deliveries",
        headers=headers,
        params={"status": "pending"},
    )
    assert len(pending.json()) >= 1


def test_ingest_idempotency(client: TestClient) -> None:
    headers = ingest_headers(idempotency_key="wh-1")
    first = client.post(
        "/api/v1/hooks/billing-stripe/deliveries",
        headers=headers,
        json=INGEST_BODY,
    )
    assert first.status_code == 201
    delivery_id = first.json()["id"]

    retry = client.post(
        "/api/v1/hooks/billing-stripe/deliveries",
        headers=headers,
        json=INGEST_BODY,
    )
    assert retry.status_code == 201
    assert retry.json()["id"] == delivery_id


def test_ack_delivery(client: TestClient) -> None:
    headers = admin_headers(client)
    created = client.post(
        "/api/v1/hooks/billing-stripe/deliveries",
        headers=ingest_headers(idempotency_key="wh-ack"),
        json={"event_type": "ping", "payload": {}},
    )
    delivery_id = created.json()["id"]

    acked = client.post(f"/api/v1/deliveries/{delivery_id}/ack", headers=headers)
    assert acked.status_code == 200
    assert acked.json()["status"] == "acked"
    assert client.post(f"/api/v1/deliveries/{delivery_id}/ack", headers=headers).status_code == 409


def test_paused_endpoint_rejects_ingest(client: TestClient) -> None:
    response = client.post(
        "/api/v1/hooks/crm-sync/deliveries",
        headers={
            "X-Webhook-Token": "seed-webhook-crm-sync",
            "Idempotency-Key": "crm-1",
        },
        json=INGEST_BODY,
    )
    assert response.status_code == 409


def test_bad_token_is_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/v1/hooks/billing-stripe/deliveries",
        headers={
            "X-Webhook-Token": "wrong-token",
            "Idempotency-Key": "bad-1",
        },
        json=INGEST_BODY,
    )
    assert response.status_code == 404
