from fastapi.testclient import TestClient


def test_root_and_health(client: TestClient) -> None:
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["message"] == "Notes API — see /docs for OpenAPI"
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_list_seed_notes_pinned_first(client: TestClient) -> None:
    response = client.get("/api/v1/notes")
    assert response.status_code == 200
    notes = response.json()
    assert [note["title"] for note in notes] == [
        "Meeting notes",
        "Grocery list",
        "FastAPI reading",
    ]
    assert notes[0]["pinned"] is True
    assert notes[1]["pinned"] is False


def test_filter_and_search(client: TestClient) -> None:
    unpinned = client.get("/api/v1/notes", params={"pinned": False})
    assert [note["id"] for note in unpinned.json()] == [2, 3]

    milk = client.get("/api/v1/notes", params={"search": "MILK"})
    assert [note["title"] for note in milk.json()] == ["Grocery list"]

    both = client.get("/api/v1/notes", params={"pinned": False, "search": "api"})
    assert [note["title"] for note in both.json()] == ["FastAPI reading"]

    blank = client.get("/api/v1/notes", params={"search": "   "})
    assert len(blank.json()) == 3


def test_create_trims_title_and_defaults(client: TestClient) -> None:
    response = client.post(
        "/api/v1/notes",
        json={"title": "  Desk setup  ", "body": "  Monitor and lamp  "},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 4
    assert body["title"] == "Desk setup"
    assert body["body"] == "Monitor and lamp"
    assert body["pinned"] is False


def test_patch_changes_only_sent_fields(client: TestClient) -> None:
    response = client.patch("/api/v1/notes/2", json={"body": "Milk, bread, and eggs"})
    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "Milk, bread, and eggs"
    assert body["title"] == "Grocery list"
    assert body["pinned"] is False


def test_pin_and_unpin_are_idempotent_and_reorder(client: TestClient) -> None:
    pinned = client.post("/api/v1/notes/3/pin")
    assert pinned.status_code == 200
    assert pinned.json()["pinned"] is True
    again = client.post("/api/v1/notes/3/pin")
    assert again.json()["pinned"] is True

    order = [note["id"] for note in client.get("/api/v1/notes").json()]
    assert order == [1, 3, 2]

    opened = client.post("/api/v1/notes/1/unpin")
    assert opened.json()["pinned"] is False
    still_open = client.post("/api/v1/notes/2/unpin")
    assert still_open.json()["pinned"] is False

    reordered = [note["id"] for note in client.get("/api/v1/notes").json()]
    assert reordered == [3, 1, 2]


def test_delete_returns_snapshot_then_404(client: TestClient) -> None:
    deleted = client.delete("/api/v1/notes/2")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert deleted.json()["note"]["title"] == "Grocery list"
    missing = client.get("/api/v1/notes/2")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Note 2 not found"}


def test_blank_title_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/notes", json={"title": "   "})
    assert response.status_code == 422


def test_openapi_describes_notes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Notes API"
    assert "pinned" in spec["info"]["description"]
    assert "/api/v1/notes/{note_id}/pin" in spec["paths"]
    examples = spec["paths"]["/api/v1/notes"]["post"]["requestBody"]["content"]["application/json"]
    assert "pinned_note" in examples["examples"]
