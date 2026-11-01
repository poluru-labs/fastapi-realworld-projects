from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Document Library API" in response.json()["message"]


def test_openapi_nested_documents(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Document Library API"
    assert "/api/v1/folders/{folder_slug}/documents/{doc_slug}" in spec["paths"]
