from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers


def test_public_list_is_published_only(client: TestClient) -> None:
    response = client.get("/api/v1/events")
    assert response.status_code == 200
    slugs = {row["slug"] for row in response.json()}
    assert slugs == {"fastapi-meetup"}


def test_draft_event_is_hidden(client: TestClient) -> None:
    response = client.get("/api/v1/events/draft-planning-session")
    assert response.status_code == 404


def test_admin_can_read_draft(client: TestClient) -> None:
    headers = admin_headers(client)
    response = client.get("/api/v1/events/draft-planning-session", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_admin_create_publish_flow(client: TestClient) -> None:
    headers = admin_headers(client)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Workshop Day",
            "starts_at": "2027-01-10T10:00:00+00:00",
            "ends_at": "2027-01-10T12:00:00+00:00",
            "capacity": 10,
        },
    )
    assert created.status_code == 201
    slug = created.json()["slug"]
    assert created.json()["status"] == "draft"

    published = client.post(f"/api/v1/events/{slug}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"


def test_tags_on_published_events(client: TestClient) -> None:
    response = client.get("/api/v1/tags")
    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert "fastapi" in names
    assert "internal" not in names
