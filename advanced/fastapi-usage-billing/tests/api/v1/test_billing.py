from decimal import Decimal

from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Key": "test-admin-key"}


def _create_customer(client: TestClient, external_id: str = "acct_test") -> dict:
    response = client.post(
        "/api/v1/customers",
        headers=ADMIN,
        json={"external_id": external_id, "name": "Test Co"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_catalog_and_admin_gate(client: TestClient) -> None:
    meters = client.get("/api/v1/meters").json()
    assert {meter["code"] for meter in meters} == {"api_calls", "tokens"}

    denied = client.post("/api/v1/customers", json={"external_id": "x", "name": "Y"})
    assert denied.status_code == 401


def test_usage_idempotency_and_invoice_preview(client: TestClient) -> None:
    created = _create_customer(client)
    customer_id = created["id"]
    api_key = {"X-Api-Key": created["api_key"]}

    sub = client.post(
        f"/api/v1/customers/{customer_id}/subscriptions",
        headers=ADMIN,
        json={"plan_code": "starter"},
    )
    assert sub.status_code == 201

    event_body = {
        "meter_code": "api_calls",
        "quantity": "10050",
        "idempotency_key": "evt-1",
    }
    first = client.post("/api/v1/usage/events", headers=api_key, json=event_body)
    second = client.post("/api/v1/usage/events", headers=api_key, json=event_body)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    summary = client.get("/api/v1/me/usage/summary", headers=api_key).json()
    assert Decimal(summary["totals"][0]["quantity"]) == Decimal("10050")

    preview = client.get(f"/api/v1/customers/{customer_id}/invoices/preview", headers=ADMIN)
    assert preview.status_code == 200
    body = preview.json()
    assert body["total_cents"] == 50
    assert Decimal(body["lines"][0]["billable_quantity"]) == Decimal("50")

    invoice = client.post(f"/api/v1/customers/{customer_id}/invoices", headers=ADMIN)
    assert invoice.status_code == 201
    assert invoice.json()["total_cents"] == 50

    again = client.post(f"/api/v1/customers/{customer_id}/invoices", headers=ADMIN)
    assert again.status_code == 409
