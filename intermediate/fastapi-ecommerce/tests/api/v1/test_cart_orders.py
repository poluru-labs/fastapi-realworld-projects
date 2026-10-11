from fastapi.testclient import TestClient

from tests.api.v1.helpers import register_headers


def test_cart_checkout_decrements_stock(client: TestClient) -> None:
    headers = register_headers(client, "shopper@example.com")

    cart = client.put(
        "/api/v1/cart/lines",
        headers=headers,
        json={"product_slug": "usb-c-hub", "quantity": 2},
    )
    assert cart.status_code == 200
    assert cart.json()["subtotal_cents"] == 4999 * 2

    order = client.post("/api/v1/orders", headers=headers, json={"note": "Thanks"})
    assert order.status_code == 201
    assert order.json()["status"] == "placed"
    assert order.json()["total_cents"] == 4999 * 2

    product = client.get("/api/v1/products/usb-c-hub")
    assert product.json()["stock"] == 8

    empty = client.get("/api/v1/cart", headers=headers)
    assert empty.json()["items"] == []


def test_checkout_empty_cart_conflict(client: TestClient) -> None:
    headers = register_headers(client, "empty@example.com")
    response = client.post("/api/v1/orders", headers=headers, json={})
    assert response.status_code == 409


def test_cancel_order_restock(client: TestClient) -> None:
    headers = register_headers(client, "cancel@example.com")
    client.put(
        "/api/v1/cart/lines",
        headers=headers,
        json={"product_slug": "usb-c-hub", "quantity": 1},
    )
    order = client.post("/api/v1/orders", headers=headers, json={}).json()
    stock_after = client.get("/api/v1/products/usb-c-hub").json()["stock"]

    cancelled = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    stock_restored = client.get("/api/v1/products/usb-c-hub").json()["stock"]
    assert stock_restored == stock_after + 1


def test_other_users_order_is_not_found(client: TestClient) -> None:
    owner = register_headers(client, "owner@example.com")
    other = register_headers(client, "other@example.com")
    client.put(
        "/api/v1/cart/lines",
        headers=owner,
        json={"product_slug": "usb-c-hub", "quantity": 1},
    )
    order = client.post("/api/v1/orders", headers=owner, json={}).json()
    response = client.get(f"/api/v1/orders/{order['id']}", headers=other)
    assert response.status_code == 404


def test_oversell_cart_line_conflict(client: TestClient) -> None:
    headers = register_headers(client, "greedy@example.com")
    response = client.put(
        "/api/v1/cart/lines",
        headers=headers,
        json={"product_slug": "usb-c-hub", "quantity": 11},
    )
    assert response.status_code == 409
