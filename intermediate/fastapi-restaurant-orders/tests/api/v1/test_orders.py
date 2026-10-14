from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers


def _lunch_payload() -> dict:
    return {
        "lines": [
            {"menu_item_slug": "classic-burger", "quantity": 1},
            {"menu_item_slug": "fries", "quantity": 2},
        ],
        "note": "Extra ketchup",
    }


def test_place_order_and_kitchen_flow(client: TestClient) -> None:
    customer = register_headers(client, "diner@example.com")
    placed = client.post("/api/v1/orders", headers=customer, json=_lunch_payload())
    assert placed.status_code == 201
    body = placed.json()
    assert body["status"] == "placed"
    assert body["total_cents"] == 1299 + 499 * 2
    order_id = body["id"]

    admin = admin_headers(client)
    blocked = client.post(
        f"/api/v1/orders/{order_id}/start-preparing",
        headers=customer,
    )
    assert blocked.status_code == 403

    preparing = client.post(f"/api/v1/orders/{order_id}/start-preparing", headers=admin)
    assert preparing.status_code == 200
    assert preparing.json()["status"] == "preparing"

    ready = client.post(f"/api/v1/orders/{order_id}/mark-ready", headers=admin)
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    done = client.post(f"/api/v1/orders/{order_id}/complete", headers=customer)
    assert done.status_code == 200
    assert done.json()["status"] == "completed"


def test_customer_cancel_while_placed(client: TestClient) -> None:
    customer = register_headers(client, "cancel@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=customer,
        json={"lines": [{"menu_item_slug": "fries", "quantity": 1}]},
    ).json()
    cancelled = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=customer)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_customer_cannot_cancel_after_preparing(client: TestClient) -> None:
    customer = register_headers(client, "late@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=customer,
        json={"lines": [{"menu_item_slug": "fries", "quantity": 1}]},
    ).json()
    admin = admin_headers(client)
    client.post(f"/api/v1/orders/{order['id']}/start-preparing", headers=admin)
    blocked = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=customer)
    assert blocked.status_code == 403


def test_other_users_order_is_not_found(client: TestClient) -> None:
    owner = register_headers(client, "owner@example.com")
    other = register_headers(client, "other@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=owner,
        json={"lines": [{"menu_item_slug": "fries", "quantity": 1}]},
    ).json()
    response = client.get(f"/api/v1/orders/{order['id']}", headers=other)
    assert response.status_code == 404


def test_admin_lists_all_orders(client: TestClient) -> None:
    customer = register_headers(client, "listed@example.com")
    client.post(
        "/api/v1/orders",
        headers=customer,
        json={"lines": [{"menu_item_slug": "classic-burger", "quantity": 1}]},
    )
    admin = admin_headers(client)
    rows = client.get("/api/v1/orders", headers=admin)
    assert rows.status_code == 200
    assert len(rows.json()) >= 1
