from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Media Processing API — see /docs for OpenAPI"


def test_openapi_lists_media_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Media Processing API"
    assert "/api/v1/jobs" in spec["paths"]
    assert "/api/v1/assets" in spec["paths"]
