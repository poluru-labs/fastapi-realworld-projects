from fastapi.testclient import TestClient

from tests.api.v1.helpers import auth_headers


def test_public_events_list(client: TestClient) -> None:
    response = client.get("/api/v1/events")
    assert response.status_code == 200
    assert response.json()[0]["slug"] == "jazz-night"


def test_hold_confirm_idempotent(client: TestClient) -> None:
    headers = auth_headers(client, "fan@example.com")
    event = client.get("/api/v1/events/jazz-night").json()
    tier_id = next(t["id"] for t in event["tiers"] if t["name"] == "General Admission")

    hold = client.post(
        "/api/v1/holds",
        headers=headers,
        json={"tier_id": tier_id, "quantity": 2},
    )
    assert hold.status_code == 201
    hold_id = hold.json()["id"]

    confirm_headers = {**headers, "Idempotency-Key": "checkout-1"}
    first = client.post(
        "/api/v1/bookings",
        headers=confirm_headers,
        json={"hold_id": hold_id},
    )
    assert first.status_code == 201
    code = first.json()["confirmation_code"]

    second = client.post(
        "/api/v1/bookings",
        headers=confirm_headers,
        json={"hold_id": hold_id},
    )
    assert second.status_code == 201
    assert second.json()["confirmation_code"] == code


def test_availability_reflects_hold(client: TestClient) -> None:
    headers = auth_headers(client, "holds@example.com")
    event = client.get("/api/v1/events/jazz-night").json()
    tier_id = event["tiers"][0]["id"]
    before = event["tiers"][0]["quantity_available"]

    client.post("/api/v1/holds", headers=headers, json={"tier_id": tier_id, "quantity": 3})

    after = client.get("/api/v1/events/jazz-night").json()["tiers"][0]["quantity_available"]
    assert after == before - 3


def test_other_users_booking_hidden(client: TestClient) -> None:
    owner = auth_headers(client, "owner@example.com")
    other = auth_headers(client, "other@example.com")
    tier_id = client.get("/api/v1/events/jazz-night").json()["tiers"][0]["id"]
    hold_id = client.post(
        "/api/v1/holds",
        headers=owner,
        json={"tier_id": tier_id, "quantity": 1},
    ).json()["id"]
    booking_id = client.post(
        "/api/v1/bookings",
        headers={**owner, "Idempotency-Key": "o1"},
        json={"hold_id": hold_id},
    ).json()["id"]

    hidden = client.get(f"/api/v1/bookings/{booking_id}", headers=other)
    assert hidden.status_code == 404
