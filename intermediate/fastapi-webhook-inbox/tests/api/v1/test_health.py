from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Webhook Inbox API — see /docs for OpenAPI"


def test_openapi_lists_webhook_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Webhook Inbox API"
    assert "/api/v1/hooks/{slug}/deliveries" in spec["paths"]
