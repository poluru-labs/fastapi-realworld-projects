from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, auth_headers


def test_onboarding_happy_path(client: TestClient) -> None:
    user = auth_headers(client, "hire@example.com")
    started = client.post(
        "/api/v1/workflow-instances",
        headers={**user, "Idempotency-Key": "start-hire"},
        json={
            "definition_slug": "employee-onboarding",
            "context": {"employee_email": "hire@example.com"},
        },
    )
    assert started.status_code == 201
    instance = started.json()
    assert instance["current_state"] == "invite_sent"
    assert instance["version"] == 1
    instance_id = instance["id"]

    again = client.post(
        "/api/v1/workflow-instances",
        headers={**user, "Idempotency-Key": "start-hire"},
        json={
            "definition_slug": "employee-onboarding",
            "context": {"employee_email": "hire@example.com"},
        },
    )
    assert again.json()["id"] == instance_id

    profile = client.post(
        f"/api/v1/workflow-instances/{instance_id}/transitions",
        headers={**user, "Idempotency-Key": "profile-done"},
        json={
            "action": "complete_profile",
            "expected_version": 1,
            "context_patch": {"profile_completed": True},
        },
    )
    assert profile.status_code == 200
    assert profile.json()["current_state"] == "profile_complete"
    assert profile.json()["version"] == 2

    admin = admin_headers(client)
    blocked = client.post(
        f"/api/v1/workflow-instances/{instance_id}/transitions",
        headers={**user, "Idempotency-Key": "approve-fail"},
        json={"action": "approve", "expected_version": 2},
    )
    assert blocked.status_code == 403

    approved = client.post(
        f"/api/v1/workflow-instances/{instance_id}/transitions",
        headers={**admin, "Idempotency-Key": "approve-ok"},
        json={"action": "approve", "expected_version": 2},
    )
    assert approved.status_code == 200
    assert approved.json()["current_state"] == "manager_approved"

    activated = client.post(
        f"/api/v1/workflow-instances/{instance_id}/transitions",
        headers={**admin, "Idempotency-Key": "activate-ok"},
        json={"action": "activate", "expected_version": 3},
    )
    assert activated.status_code == 200
    body = activated.json()
    assert body["current_state"] == "active"
    assert body["status"] == "completed"

    events = client.get(f"/api/v1/workflow-instances/{instance_id}/events", headers=user)
    assert len(events.json()) == 4


def test_stale_version_conflict(client: TestClient) -> None:
    user = auth_headers(client, "stale@example.com")
    instance = client.post(
        "/api/v1/workflow-instances",
        headers={**user, "Idempotency-Key": "stale-start"},
        json={"definition_slug": "employee-onboarding", "context": {}},
    ).json()

    stale = client.post(
        f"/api/v1/workflow-instances/{instance['id']}/transitions",
        headers={**user, "Idempotency-Key": "stale-tx"},
        json={"action": "complete_profile", "expected_version": 99},
    )
    assert stale.status_code == 409


def test_other_users_instance_not_found(client: TestClient) -> None:
    owner = auth_headers(client, "owner@example.com")
    other = auth_headers(client, "other@example.com")
    instance = client.post(
        "/api/v1/workflow-instances",
        headers={**owner, "Idempotency-Key": "owner-start"},
        json={"definition_slug": "employee-onboarding", "context": {}},
    ).json()
    response = client.get(f"/api/v1/workflow-instances/{instance['id']}", headers=other)
    assert response.status_code == 404


def test_draft_definition_hidden_from_guests(client: TestClient) -> None:
    response = client.get("/api/v1/workflow-definitions/draft-internal")
    assert response.status_code == 404
