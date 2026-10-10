from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers


def test_register_and_waitlist(client: TestClient) -> None:
    user_a = register_headers(client, "alice@example.com")
    user_b = register_headers(client, "bob@example.com")

    first = client.post(
        "/api/v1/registrations",
        headers=user_a,
        json={"event_slug": "fastapi-meetup"},
    )
    assert first.status_code == 201
    assert first.json()["status"] == "registered"

    second = client.post(
        "/api/v1/registrations",
        headers=user_b,
        json={"event_slug": "fastapi-meetup"},
    )
    assert second.status_code == 201
    assert second.json()["status"] == "waitlisted"


def test_cancel_promotes_waitlist(client: TestClient) -> None:
    admin = admin_headers(client)
    user_a = register_headers(client, "carol@example.com", full_name="Carol")
    user_b = register_headers(client, "dana@example.com", full_name="Dana")

    reg_a = client.post(
        "/api/v1/registrations",
        headers=user_a,
        json={"event_slug": "fastapi-meetup"},
    ).json()
    reg_b = client.post(
        "/api/v1/registrations",
        headers=user_b,
        json={"event_slug": "fastapi-meetup"},
    ).json()
    assert reg_b["status"] == "waitlisted"

    cancelled = client.post(
        f"/api/v1/registrations/{reg_a['id']}/cancel",
        headers=user_a,
    )
    assert cancelled.status_code == 200

    rows = client.get("/api/v1/events/fastapi-meetup/registrations", headers=admin)
    promoted = next(row for row in rows.json() if row["id"] == reg_b["id"])
    assert promoted["status"] == "registered"


def test_duplicate_registration_conflict(client: TestClient) -> None:
    headers = register_headers(client, "eve@example.com")
    payload = {"event_slug": "fastapi-meetup"}
    assert client.post("/api/v1/registrations", headers=headers, json=payload).status_code == 201
    again = client.post("/api/v1/registrations", headers=headers, json=payload)
    assert again.status_code == 409


def test_other_users_registration_is_not_found(client: TestClient) -> None:
    owner = register_headers(client, "frank@example.com")
    other = register_headers(client, "gina@example.com")
    created = client.post(
        "/api/v1/registrations",
        headers=owner,
        json={"event_slug": "fastapi-meetup"},
    ).json()
    response = client.get(f"/api/v1/registrations/{created['id']}", headers=other)
    assert response.status_code == 404
