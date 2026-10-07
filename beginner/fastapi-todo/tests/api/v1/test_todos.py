from fastapi.testclient import TestClient


def test_root_and_health(client: TestClient) -> None:
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["message"] == "Todo API — see /docs for OpenAPI"
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_list_seed_todos(client: TestClient) -> None:
    response = client.get("/api/v1/todos")
    assert response.status_code == 200
    titles = [todo["title"] for todo in response.json()]
    assert titles == ["Buy groceries", "Read the FastAPI tutorial", "Set up the project"]


def test_filter_open_and_high_priority(client: TestClient) -> None:
    open_tasks = client.get("/api/v1/todos", params={"completed": False})
    assert [todo["id"] for todo in open_tasks.json()] == [1, 2]
    high = client.get("/api/v1/todos", params={"priority": "high", "completed": False})
    assert [todo["title"] for todo in high.json()] == ["Read the FastAPI tutorial"]


def test_create_trims_title_and_defaults(client: TestClient) -> None:
    response = client.post(
        "/api/v1/todos",
        json={"title": "  Write the README  ", "notes": "  curl examples  "},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 4
    assert body["title"] == "Write the README"
    assert body["notes"] == "curl examples"
    assert body["priority"] == "medium"
    assert body["completed"] is False


def test_patch_changes_only_sent_fields(client: TestClient) -> None:
    response = client.patch("/api/v1/todos/1", json={"priority": "high"})
    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "high"
    assert body["title"] == "Buy groceries"
    assert body["completed"] is False


def test_complete_and_reopen_are_idempotent(client: TestClient) -> None:
    done = client.post("/api/v1/todos/1/complete")
    assert done.status_code == 200
    assert done.json()["completed"] is True
    again = client.post("/api/v1/todos/1/complete")
    assert again.json()["completed"] is True
    opened = client.post("/api/v1/todos/3/reopen")
    assert opened.json()["completed"] is False
    still_open = client.post("/api/v1/todos/1/reopen")
    assert still_open.json()["completed"] is False


def test_delete_returns_snapshot_then_404(client: TestClient) -> None:
    deleted = client.delete("/api/v1/todos/2")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert deleted.json()["todo"]["title"] == "Read the FastAPI tutorial"
    missing = client.get("/api/v1/todos/2")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Todo 2 not found"}


def test_blank_title_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/todos", json={"title": "   "})
    assert response.status_code == 422


def test_unknown_priority_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/todos", params={"priority": "urgent"})
    assert response.status_code == 422


def test_openapi_title(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Todo API"
    assert "/api/v1/todos/{todo_id}/complete" in spec["paths"]
