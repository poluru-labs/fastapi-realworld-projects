from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Resumable Files API — see /docs for OpenAPI"
    assert response.headers["x-request-id"]


def test_liveness(client: TestClient) -> None:
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}


def test_readiness(client: TestClient) -> None:
    assert client.get("/api/v1/health/ready").json() == {"status": "ok", "database": "ok"}


def test_openapi_lists_upload_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Resumable Files API"
    assert "/api/v1/uploads/{upload_key}/parts" in spec["paths"]
