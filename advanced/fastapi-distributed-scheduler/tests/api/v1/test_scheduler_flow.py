from fastapi.testclient import TestClient

from tests.api.v1.helpers import auth_headers


def test_trigger_claim_and_complete(client: TestClient) -> None:
    operator = auth_headers(client, "ops@example.com")
    triggered = client.post(
        "/api/v1/schedules/nightly-report/trigger",
        headers={**operator, "Idempotency-Key": "run-report-1"},
        json={"payload": {"report_name": "ops-daily"}},
    )
    assert triggered.status_code == 201
    run = triggered.json()
    assert run["status"] == "pending"
    assert run["payload"]["format"] == "pdf"
    assert run["payload"]["report_name"] == "ops-daily"
    run_id = run["id"]

    again = client.post(
        "/api/v1/schedules/nightly-report/trigger",
        headers={**operator, "Idempotency-Key": "run-report-1"},
        json={"payload": {}},
    )
    assert again.json()["id"] == run_id

    registered = client.post(
        "/api/v1/workers/register",
        headers=operator,
        json={"worker_id": "worker-1", "capabilities": ["report"]},
    )
    assert registered.status_code == 200

    claimed = client.post(
        "/api/v1/workers/claim",
        headers=operator,
        json={"worker_id": "worker-1"},
    )
    assert claimed.status_code == 200
    leased = claimed.json()
    assert leased["id"] == run_id
    assert leased["status"] == "running"
    assert leased["lease_holder"] == "worker-1"
    version = leased["version"]

    completed = client.post(
        f"/api/v1/workers/runs/{run_id}/complete",
        headers=operator,
        json={
            "worker_id": "worker-1",
            "expected_version": version,
            "outcome": "success",
            "result": {"rows": 42},
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "succeeded"
    assert completed.json()["result"] == {"rows": 42}


def test_stale_version_on_complete(client: TestClient) -> None:
    user = auth_headers(client, "stale@example.com")
    run_id = client.post(
        "/api/v1/schedules/nightly-report/trigger",
        headers={**user, "Idempotency-Key": "stale-run"},
        json={},
    ).json()["id"]
    client.post(
        "/api/v1/workers/register",
        headers=user,
        json={"worker_id": "w-stale", "capabilities": ["report"]},
    )
    leased = client.post(
        "/api/v1/workers/claim",
        headers=user,
        json={"worker_id": "w-stale"},
    ).json()

    stale = client.post(
        f"/api/v1/workers/runs/{run_id}/complete",
        headers=user,
        json={
            "worker_id": "w-stale",
            "expected_version": leased["version"] - 1,
            "outcome": "success",
        },
    )
    assert stale.status_code == 409


def test_other_users_run_is_not_found(client: TestClient) -> None:
    owner = auth_headers(client, "owner@example.com")
    other = auth_headers(client, "other@example.com")
    run_id = client.post(
        "/api/v1/schedules/nightly-report/trigger",
        headers={**owner, "Idempotency-Key": "owner-run"},
        json={},
    ).json()["id"]
    hidden = client.get(f"/api/v1/runs/{run_id}", headers=other)
    assert hidden.status_code == 404


def test_draft_schedule_cannot_be_triggered(client: TestClient) -> None:
    user = auth_headers(client, "trigger@example.com")
    response = client.post(
        "/api/v1/schedules/draft-cleanup/trigger",
        headers={**user, "Idempotency-Key": "draft-trigger"},
        json={},
    )
    assert response.status_code == 404
