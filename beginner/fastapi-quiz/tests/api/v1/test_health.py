from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Quiz API — see /docs for OpenAPI"


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_openapi_lists_quiz_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Quiz API"
    assert "/api/v1/quizzes/{quiz_id}/play" in spec["paths"]
    assert "/api/v1/quizzes/{quiz_id}/submit" in spec["paths"]
