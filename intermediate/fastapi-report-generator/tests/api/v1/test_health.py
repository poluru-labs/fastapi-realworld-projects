from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Report Generator API — see /docs for OpenAPI"


def test_openapi_lists_report_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Report Generator API"
    assert "/api/v1/reports/runs" in spec["paths"]
