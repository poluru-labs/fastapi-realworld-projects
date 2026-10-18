from fastapi.testclient import TestClient


def test_list_items(client: TestClient) -> None:
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "Widget A"


def test_get_item_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/items/999")
    assert response.status_code == 404


def test_create_item(client: TestClient) -> None:
    response = client.post(
        "/api/v1/items",
        json={"name": "New", "price": 1.0, "in_stock": True},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "New"
    assert body["id"] == 4


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
