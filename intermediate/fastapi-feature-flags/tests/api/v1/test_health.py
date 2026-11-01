from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Feature Flags API" in response.json()["message"]


def test_openapi_runtime(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Feature Flags API"
    assert "/api/v1/runtime/evaluate" in spec["paths"]
