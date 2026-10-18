from fastapi.testclient import TestClient


def test_list_products_featured_first(client: TestClient) -> None:
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["featured"] is True
    assert data[0]["sku"] == "HUB-USBC-7IN1"
    assert data[0]["in_stock"] is True


def test_list_categories(client: TestClient) -> None:
    response = client.get("/api/v1/products/categories")
    assert response.status_code == 200
    categories = response.json()["categories"]
    assert "accessories" in categories
    assert "peripherals" in categories
    assert categories == sorted(categories)


def test_get_by_sku_case_insensitive(client: TestClient) -> None:
    response = client.get("/api/v1/products/by-sku/hub-usbc-7in1")
    assert response.status_code == 200
    assert response.json()["name"] == "USB-C 7-in-1 Hub"


def test_create_and_in_stock_derived(client: TestClient) -> None:
    payload = {
        "sku": "stand-laptop-alu",
        "name": "Aluminum laptop stand",
        "price": 39.0,
        "category": "Accessories",
        "tags": ["desk", "Desk"],
        "stock_quantity": 10,
    }
    created = client.post("/api/v1/products", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["sku"] == "STAND-LAPTOP-ALU"
    assert body["tags"] == ["desk"]
    assert body["in_stock"] is True


def test_duplicate_sku_conflict(client: TestClient) -> None:
    response = client.post(
        "/api/v1/products",
        json={
            "sku": "mouse-wireless-mx",
            "name": "Clone",
            "price": 1.0,
            "category": "peripherals",
        },
    )
    assert response.status_code == 409
    assert "SKU" in response.json()["detail"]


def test_search_and_category_filter(client: TestClient) -> None:
    by_category = client.get("/api/v1/products", params={"category": "peripherals"})
    assert by_category.status_code == 200
    assert len(by_category.json()) == 1

    by_search = client.get("/api/v1/products", params={"search": "hdmi"})
    assert by_search.status_code == 200
    assert len(by_search.json()) == 1


def test_discontinue_hides_from_default_list(client: TestClient) -> None:
    discontinued = client.post("/api/v1/products/2/discontinue")
    assert discontinued.status_code == 200
    assert discontinued.json()["discontinued"] is True

    active = client.get("/api/v1/products")
    assert all(p["id"] != 2 for p in active.json())

    archived = client.get("/api/v1/products", params={"discontinued": True})
    ids = {p["id"] for p in archived.json()}
    assert 2 in ids
    assert 3 in ids


def test_out_of_stock_in_stock_false(client: TestClient) -> None:
    response = client.get("/api/v1/products/3")
    assert response.status_code == 200
    assert response.json()["stock_quantity"] == 0
    assert response.json()["in_stock"] is False


def test_delete_product_not_found(client: TestClient) -> None:
    missing = client.get("/api/v1/products/999")
    assert missing.status_code == 404

    deleted = client.delete("/api/v1/products/1")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "id": 1}


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
