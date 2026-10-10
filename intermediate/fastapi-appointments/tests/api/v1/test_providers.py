from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers


def test_list_providers(client: TestClient) -> None:
    headers = register_headers(client, "viewer@example.com")
    listed = client.get("/api/v1/providers", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2


def test_admin_manages_providers(client: TestClient) -> None:
    user = register_headers(client, "user@example.com")
    admin = admin_headers(client)

    denied = client.post(
        "/api/v1/providers",
        headers=user,
        json={"name": "Dr Nope"},
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/v1/providers",
        headers=admin,
        json={"name": "Dr Sam Rivera", "specialty": "Evening clinic"},
    )
    assert created.status_code == 201
    provider_id = created.json()["id"]

    deactivated = client.post(f"/api/v1/providers/{provider_id}/deactivate", headers=admin)
    assert deactivated.json()["is_active"] is False

    hidden = client.get(f"/api/v1/providers/{provider_id}", headers=user)
    assert hidden.status_code == 404

    book_fail = client.post(
        "/api/v1/appointments",
        headers=user,
        json={
            "provider_id": provider_id,
            "title": "No room",
            "starts_at": "2026-12-11T10:00:00+00:00",
            "ends_at": "2026-12-11T10:30:00+00:00",
        },
    )
    assert book_fail.status_code == 409
