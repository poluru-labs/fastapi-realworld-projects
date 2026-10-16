def test_list_bookmarks_pins_first(client):
    response = client.get("/api/v1/bookmarks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["pinned"] is True
    assert data[0]["title"] == "FastAPI documentation"


def test_list_tags(client):
    response = client.get("/api/v1/bookmarks/tags")
    assert response.status_code == 200
    tags = response.json()["tags"]
    assert "python" in tags
    assert tags == sorted(tags)


def test_create_and_get_bookmark(client):
    payload = {
        "title": "Starlette",
        "url": "https://www.starlette.io/",
        "tags": ["Python", "python", "web"],
        "note": "ASGI toolkit",
    }
    created = client.post("/api/v1/bookmarks", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["tags"] == ["python", "web"]
    bookmark_id = body["id"]

    fetched = client.get(f"/api/v1/bookmarks/{bookmark_id}")
    assert fetched.status_code == 200
    assert fetched.json()["url"].startswith("https://www.starlette.io")


def test_duplicate_url_conflict(client):
    payload = {
        "title": "Duplicate",
        "url": "https://fastapi.tiangolo.com",
    }
    response = client.post("/api/v1/bookmarks", json=payload)
    assert response.status_code == 409
    assert "URL" in response.json()["detail"]


def test_search_and_tag_filter(client):
    by_tag = client.get("/api/v1/bookmarks", params={"tag": "docs"})
    assert by_tag.status_code == 200
    assert len(by_tag.json()) == 1

    by_search = client.get("/api/v1/bookmarks", params={"search": "python.org"})
    assert by_search.status_code == 200
    assert len(by_search.json()) == 1


def test_archive_hides_from_default_list(client):
    archived = client.post("/api/v1/bookmarks/2/archive")
    assert archived.status_code == 200
    assert archived.json()["archived"] is True

    active = client.get("/api/v1/bookmarks")
    assert all(b["id"] != 2 for b in active.json())

    archived_list = client.get("/api/v1/bookmarks", params={"archived": True})
    assert len(archived_list.json()) == 1
    assert archived_list.json()[0]["id"] == 2


def test_delete_bookmark_not_found(client):
    missing = client.get("/api/v1/bookmarks/999")
    assert missing.status_code == 404

    deleted = client.delete("/api/v1/bookmarks/1")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "id": 1}
