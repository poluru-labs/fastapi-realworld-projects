from fastapi.testclient import TestClient

MEETUP_ID = 1
CANCELLED_ID = 2


def test_list_and_filter_status(client: TestClient) -> None:
    all_events = client.get("/api/v1/events")
    assert all_events.status_code == 200
    assert len(all_events.json()) == 3

    scheduled = client.get("/api/v1/events", params={"status": "scheduled"})
    assert len(scheduled.json()) == 2

    meetup = client.get(f"/api/v1/events/{MEETUP_ID}")
    assert meetup.status_code == 200
    body = meetup.json()
    assert body["registration_count"] == 2
    assert len(body["registrations"]) == 2


def test_register_and_duplicate_email(client: TestClient) -> None:
    created = client.post(
        f"/api/v1/events/{MEETUP_ID}/registrations",
        json={"name": "New Person", "email": "new@example.com"},
    )
    assert created.status_code == 201

    dup = client.post(
        f"/api/v1/events/{MEETUP_ID}/registrations",
        json={"name": "Alex Again", "email": "alex@example.com"},
    )
    assert dup.status_code == 409


def test_cancelled_event_rejects_registration(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/events/{CANCELLED_ID}/registrations",
        json={"name": "Guest", "email": "guest@example.com"},
    )
    assert response.status_code == 409


def test_cancel_event(client: TestClient) -> None:
    created = client.post(
        "/api/v1/events",
        json={
            "title": "Temp talk",
            "location": "Room 1",
            "starts_at": "2026-06-01T15:00:00+00:00",
            "ends_at": "2026-06-01T16:00:00+00:00",
        },
    )
    event_id = created.json()["id"]
    cancelled = client.post(f"/api/v1/events/{event_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(f"/api/v1/events/{event_id}/cancel").status_code == 409


def test_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/events/999").status_code == 404
