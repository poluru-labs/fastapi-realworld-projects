from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Support Tickets API — see /docs for OpenAPI"


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_openapi_lists_ticket_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Support Tickets API"
    assert "/api/v1/tickets/{ticket_id}/comments" in spec["paths"]
