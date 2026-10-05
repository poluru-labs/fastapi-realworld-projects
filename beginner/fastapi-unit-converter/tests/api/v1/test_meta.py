from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Unit Converter API — see /docs for OpenAPI"


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
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "Unit Converter API"
    assert "/api/v1/units" in spec["paths"]
    assert "/api/v1/units/{category}" in spec["paths"]
    assert "/api/v1/convert" in spec["paths"]
    examples = spec["paths"]["/api/v1/convert"]["post"]["requestBody"]["content"][
        "application/json"
    ]["examples"]
    assert "boiling_point" in examples
    assert examples["boiling_point"]["value"]["to_unit"] == "fahrenheit"
