def test_list_entries_starred_first(client):
    response = client.get("/api/v1/entries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["starred"] is True
    assert data[0]["entry_date"] == "2026-10-14"


def test_list_tags(client):
    response = client.get("/api/v1/entries/tags")
    assert response.status_code == 200
    tags = response.json()["tags"]
    assert "work" in tags
    assert tags == sorted(tags)


def test_create_and_get_by_date(client):
    payload = {
        "entry_date": "2026-10-16",
        "title": "New day",
        "body": "Notes for the journal.",
        "mood": "good",
        "tags": ["Life", "life"],
    }
    created = client.post("/api/v1/entries", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["tags"] == ["life"]
    assert body["mood"] == "good"

    by_date = client.get("/api/v1/entries/by-date/2026-10-16")
    assert by_date.status_code == 200
    assert by_date.json()["id"] == body["id"]


def test_duplicate_date_conflict(client):
    response = client.post(
        "/api/v1/entries",
        json={
            "entry_date": "2026-10-14",
            "body": "Duplicate day.",
        },
    )
    assert response.status_code == 409
    assert "2026-10-14" in response.json()["detail"]


def test_filters(client):
    by_mood = client.get("/api/v1/entries", params={"mood": "okay"})
    assert len(by_mood.json()) == 1

    by_range = client.get(
        "/api/v1/entries",
        params={"date_from": "2026-10-15", "date_to": "2026-10-15"},
    )
    assert len(by_range.json()) == 1
    assert by_range.json()[0]["entry_date"] == "2026-10-15"


def test_star_and_delete(client):
    starred = client.post("/api/v1/entries/2/star")
    assert starred.status_code == 200
    assert starred.json()["starred"] is True

    deleted = client.delete("/api/v1/entries/1")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "id": 1}

    missing = client.get("/api/v1/entries/1")
    assert missing.status_code == 404
