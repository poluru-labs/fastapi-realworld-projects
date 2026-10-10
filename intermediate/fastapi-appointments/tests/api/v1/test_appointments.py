from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers


def test_appointments_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/appointments").status_code == 401


def test_admin_sees_all_client_sees_own(client: TestClient) -> None:
    admin = admin_headers(client)
    user = register_headers(client, "client@example.com")

    admin_list = client.get("/api/v1/appointments", headers=admin)
    assert len(admin_list.json()) == 2

    user_list = client.get("/api/v1/appointments", headers=user)
    assert user_list.json() == []

    hidden = client.get("/api/v1/appointments/1", headers=user)
    assert hidden.status_code == 404


def test_book_overlap_and_cancel(client: TestClient) -> None:
    user = register_headers(client, "booker@example.com", full_name="Booker")
    slot = {
        "provider_id": 1,
        "title": "Checkup",
        "starts_at": "2026-12-10T10:00:00+00:00",
        "ends_at": "2026-12-10T10:30:00+00:00",
    }
    booked = client.post("/api/v1/appointments", headers=user, json=slot)
    assert booked.status_code == 201
    appointment_id = booked.json()["id"]
    assert booked.json()["status"] == "scheduled"
    assert booked.json()["client_name"] == "Booker"

    overlap = client.post(
        "/api/v1/appointments",
        headers=user,
        json={
            **slot,
            "title": "Conflict",
            "starts_at": "2026-12-10T10:15:00+00:00",
            "ends_at": "2026-12-10T11:00:00+00:00",
        },
    )
    assert overlap.status_code == 409

    cancelled = client.post(f"/api/v1/appointments/{appointment_id}/cancel", headers=user)
    assert cancelled.json()["status"] == "cancelled"

    after_cancel = client.post("/api/v1/appointments", headers=user, json=slot)
    assert after_cancel.status_code == 201


def test_confirm_complete_flow(client: TestClient) -> None:
    user = register_headers(client, "flow@example.com")
    admin = admin_headers(client)
    created = client.post(
        "/api/v1/appointments",
        headers=user,
        json={
            "provider_id": 2,
            "title": "Flow visit",
            "starts_at": "2026-12-15T09:00:00+00:00",
            "ends_at": "2026-12-15T09:30:00+00:00",
        },
    ).json()
    appointment_id = created["id"]

    denied = client.post(f"/api/v1/appointments/{appointment_id}/confirm", headers=user)
    assert denied.status_code == 403

    early_complete = client.post(
        f"/api/v1/appointments/{appointment_id}/complete",
        headers=admin,
    )
    assert early_complete.status_code == 409

    confirmed = client.post(f"/api/v1/appointments/{appointment_id}/confirm", headers=admin)
    assert confirmed.json()["status"] == "confirmed"

    completed = client.post(f"/api/v1/appointments/{appointment_id}/complete", headers=admin)
    assert completed.json()["status"] == "completed"


def test_reschedule_while_scheduled(client: TestClient) -> None:
    user = register_headers(client, "move@example.com")
    created = client.post(
        "/api/v1/appointments",
        headers=user,
        json={
            "provider_id": 2,
            "title": "Move me",
            "starts_at": "2026-12-20T14:00:00+00:00",
            "ends_at": "2026-12-20T14:30:00+00:00",
        },
    ).json()
    appointment_id = created["id"]

    moved = client.patch(
        f"/api/v1/appointments/{appointment_id}",
        headers=user,
        json={
            "starts_at": "2026-12-20T16:00:00+00:00",
            "ends_at": "2026-12-20T16:30:00+00:00",
        },
    )
    assert moved.status_code == 200

    client.post(f"/api/v1/appointments/{appointment_id}/cancel", headers=user)
    blocked = client.patch(
        f"/api/v1/appointments/{appointment_id}",
        headers=user,
        json={"title": "Too late"},
    )
    assert blocked.status_code == 409


def test_openapi_documents_booking(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Appointments API"
    assert "overlap" in spec["info"]["description"].lower()
    book = spec["paths"]["/api/v1/appointments"]["post"]
    assert "checkup" in book["requestBody"]["content"]["application/json"]["examples"]
