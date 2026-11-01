from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Uptime Monitor API" in response.json()["message"]


def test_openapi_monitors(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Uptime Monitor API"
    assert "/api/v1/monitors/{slug}/checks" in spec["paths"]
