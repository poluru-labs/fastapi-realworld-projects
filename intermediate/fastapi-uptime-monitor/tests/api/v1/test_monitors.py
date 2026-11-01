from fastapi.testclient import TestClient

from tests.api.v1.helpers import demo_headers


def test_public_status_page(client: TestClient) -> None:
    response = client.get("/api/v1/status/api-gateway")
    assert response.status_code == 200
    assert response.json()["status"] == "up"


def test_private_status_hidden(client: TestClient) -> None:
    assert client.get("/api/v1/status/billing-service").status_code == 404


def test_run_check(client: TestClient) -> None:
    headers = demo_headers(client)
    run = client.post("/api/v1/monitors/api-gateway/checks", headers=headers)
    assert run.status_code == 201
    assert run.json()["status"] == "up"


def test_pause_blocks_check(client: TestClient) -> None:
    headers = demo_headers(client)
    client.post("/api/v1/monitors/api-gateway/pause", headers=headers)
    blocked = client.post("/api/v1/monitors/api-gateway/checks", headers=headers)
    assert blocked.status_code == 409


def test_create_monitor(client: TestClient) -> None:
    headers = demo_headers(client)
    created = client.post(
        "/api/v1/monitors",
        headers=headers,
        json={
            "name": "Marketing site",
            "target_url": "https://mock.local/healthy",
            "is_public": True,
        },
    )
    assert created.status_code == 201
    assert created.json()["status_page_path"] == f"/api/v1/status/{created.json()['slug']}"
