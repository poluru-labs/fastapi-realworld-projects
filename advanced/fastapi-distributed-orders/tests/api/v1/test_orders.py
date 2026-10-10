from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, auth_headers


def _create_order(client: TestClient, headers: dict[str, str], key: str) -> dict:
    response = client.post(
        "/api/v1/orders",
        headers={**headers, "Idempotency-Key": key, "X-Request-ID": "trace-abc"},
        json={"items": [{"sku": "WIDGET-1", "quantity": 1}]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_idempotent_create(client: TestClient) -> None:
    headers = auth_headers(client, "idempotent@example.com")
    first = _create_order(client, headers, "key-1")
    second = _create_order(client, headers, "key-1")
    assert second["id"] == first["id"]
    assert second["correlation_id"] == "trace-abc"


def test_order_lifecycle(client: TestClient) -> None:
    headers = auth_headers(client, "lifecycle@example.com")
    order = _create_order(client, headers, "life-1")
    version = order["version"]

    paid = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=headers,
        json={"expected_version": version},
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"

    fulfilled = client.post(
        f"/api/v1/orders/{order['id']}/fulfill",
        headers=headers,
        json={"expected_version": paid.json()["version"]},
    )
    assert fulfilled.json()["status"] == "fulfilled"


def test_version_conflict(client: TestClient) -> None:
    headers = auth_headers(client, "version@example.com")
    order = _create_order(client, headers, "ver-1")
    conflict = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=headers,
        json={"expected_version": 999},
    )
    assert conflict.status_code == 409


def test_outbox_after_create(client: TestClient) -> None:
    headers = auth_headers(client, "outbox@example.com")
    _create_order(client, headers, "out-1")
    admin = admin_headers(client)
    events = client.get("/api/v1/outbox", headers=admin)
    assert events.status_code == 200
    assert any(row["event_type"] == "order.created" for row in events.json())


def test_other_user_order_hidden(client: TestClient) -> None:
    owner = auth_headers(client, "owner@example.com")
    other = auth_headers(client, "other@example.com")
    order = _create_order(client, owner, "hide-1")
    response = client.get(f"/api/v1/orders/{order['id']}", headers=other)
    assert response.status_code == 404
