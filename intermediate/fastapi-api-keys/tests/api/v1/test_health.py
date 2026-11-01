from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "API Keys Service" in response.json()["message"]


def test_openapi_lists_access_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "API Keys Service"
    assert "/api/v1/access/whoami" in spec["paths"]
