from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers


def test_products_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/products").status_code == 401


def test_list_seed_and_low_stock_filter(client: TestClient) -> None:
    headers = register_headers(client, "viewer@example.com")
    listed = client.get("/api/v1/products", headers=headers)
    assert listed.status_code == 200
    skus = [item["sku"] for item in listed.json()]
    assert skus == ["CABLE-C", "GADGET-B", "WIDGET-A"]

    low = client.get("/api/v1/products", headers=headers, params={"low_stock": True})
    assert {item["sku"] for item in low.json()} == {"CABLE-C", "GADGET-B"}
    assert all(item["is_low_stock"] for item in low.json())

    search = client.get("/api/v1/products", headers=headers, params={"search": "widget"})
    assert [item["sku"] for item in search.json()] == ["WIDGET-A"]


def test_movements_and_receive(client: TestClient) -> None:
    headers = register_headers(client, "clerk@example.com", full_name="Clerk")
    before = client.get("/api/v1/products/CABLE-C", headers=headers).json()
    assert before["quantity_on_hand"] == 0
    assert before["is_low_stock"] is True

    received = client.post(
        "/api/v1/products/CABLE-C/receive",
        headers=headers,
        json={"quantity": 5, "note": "Truck 12"},
    )
    assert received.status_code == 200
    assert received.json()["quantity_on_hand"] == 5
    assert received.json()["is_low_stock"] is False

    ledger = client.get("/api/v1/products/CABLE-C/movements", headers=headers)
    assert ledger.status_code == 200
    page = ledger.json()
    assert page["total"] >= 1
    assert page["items"][0]["movement_type"] == "receive"
    assert page["items"][0]["delta"] == 5
    assert page["items"][0]["actor_name"] == "Clerk"


def test_oversell_returns_409(client: TestClient) -> None:
    headers = register_headers(client, "seller@example.com")
    fail = client.post(
        "/api/v1/products/GADGET-B/sale",
        headers=headers,
        json={"quantity": 100},
    )
    assert fail.status_code == 409
    assert "Not enough stock" in fail.json()["detail"]

    ok = client.post(
        "/api/v1/products/GADGET-B/sale",
        headers=headers,
        json={"quantity": 1},
    )
    assert ok.status_code == 200
    assert ok.json()["quantity_on_hand"] == 2


def test_adjust_and_zero_delta(client: TestClient) -> None:
    headers = register_headers(client, "counter@example.com")
    adjusted = client.post(
        "/api/v1/products/WIDGET-A/adjust",
        headers=headers,
        json={"delta": -2, "note": "Damaged"},
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["quantity_on_hand"] == 8

    zero = client.post(
        "/api/v1/products/WIDGET-A/adjust",
        headers=headers,
        json={"delta": 0},
    )
    assert zero.status_code == 409


def test_admin_catalog_and_deactivate(client: TestClient) -> None:
    user = register_headers(client, "user@example.com")
    admin = admin_headers(client)

    denied = client.post(
        "/api/v1/products",
        headers=user,
        json={"sku": "NOPE-1", "name": "Nope"},
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/v1/products",
        headers=admin,
        json={"sku": "label-d", "name": "Labels", "quantity_on_hand": 2, "reorder_level": 5},
    )
    assert created.status_code == 201
    assert created.json()["sku"] == "LABEL-D"
    assert created.json()["is_low_stock"] is True

    duplicate = client.post(
        "/api/v1/products",
        headers=admin,
        json={"sku": "LABEL-D", "name": "Again"},
    )
    assert duplicate.status_code == 409

    deactivated = client.post("/api/v1/products/LABEL-D/deactivate", headers=admin)
    assert deactivated.json()["is_active"] is False

    hidden = client.get("/api/v1/products/LABEL-D", headers=user)
    assert hidden.status_code == 404

    admin_view = client.get("/api/v1/products/LABEL-D", headers=admin)
    assert admin_view.status_code == 200

    include = client.get(
        "/api/v1/products",
        headers=admin,
        params={"include_inactive": True},
    )
    assert "LABEL-D" in [item["sku"] for item in include.json()]

    blocked = client.post(
        "/api/v1/products/LABEL-D/sale",
        headers=admin,
        json={"quantity": 1},
    )
    assert blocked.status_code == 409

    activated = client.post("/api/v1/products/LABEL-D/activate", headers=admin)
    assert activated.json()["is_active"] is True


def test_include_inactive_forbidden_for_user(client: TestClient) -> None:
    headers = register_headers(client, "regular@example.com")
    response = client.get(
        "/api/v1/products",
        headers=headers,
        params={"include_inactive": True},
    )
    assert response.status_code == 403


def test_openapi_documents_inventory(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Inventory API"
    assert "receive" in spec["info"]["description"].lower()
    sale = spec["paths"]["/api/v1/products/{sku}/sale"]["post"]
    assert "409" in sale["responses"]
    create = spec["paths"]["/api/v1/products"]["post"]
    assert "new_sku" in create["requestBody"]["content"]["application/json"]["examples"]
