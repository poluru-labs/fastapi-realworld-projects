from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "API Aggregator" in response.json()["message"]


def test_openapi_describes_aggregates(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "API Aggregator"
    assert "/api/v1/aggregates/{slug}/runs" in spec["paths"]
