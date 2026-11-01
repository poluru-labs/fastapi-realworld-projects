from fastapi.testclient import TestClient

from tests.api.v1.helpers import demo_headers, register_headers


def test_demo_lists_seed_sources(client: TestClient) -> None:
    headers = demo_headers(client)
    response = client.get("/api/v1/sources", headers=headers)
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()}
    assert slugs == {"users-svc", "orders-svc"}


def test_create_source(client: TestClient) -> None:
    headers = register_headers(client, "integrator@example.com")
    created = client.post(
        "/api/v1/sources",
        headers=headers,
        json={
            "slug": "inventory-svc",
            "display_name": "Inventory",
            "base_url": "https://mock.local/inventory",
            "mock_catalog": "inventory",
        },
    )
    assert created.status_code == 201
    assert created.json()["mock_catalog"] == "inventory"


def test_other_user_cannot_see_source(client: TestClient) -> None:
    headers = register_headers(client, "outsider@example.com")
    response = client.get("/api/v1/sources/users-svc", headers=headers)
    assert response.status_code == 404
