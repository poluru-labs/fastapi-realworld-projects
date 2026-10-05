from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Text Analyzer API — see /docs for OpenAPI"


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_swagger_and_redoc(client: TestClient) -> None:
    docs = client.get("/docs")
    redoc = client.get("/redoc")
    assert docs.status_code == 200
    assert "swagger" in docs.text.lower()
    assert redoc.status_code == 200
    assert "redoc" in redoc.text.lower()


def test_openapi_lists_routes_and_examples(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Text Analyzer API"
    assert "/api/v1/options" in spec["paths"]
    assert "/api/v1/analyze" in spec["paths"]
    assert "/api/v1/transform" in spec["paths"]
    analyze = spec["paths"]["/api/v1/analyze"]["post"]["requestBody"]["content"]
    transform = spec["paths"]["/api/v1/transform"]["post"]["requestBody"]["content"]
    assert "palindrome" in analyze["application/json"]["examples"]
    assert "slug" in transform["application/json"]["examples"]
