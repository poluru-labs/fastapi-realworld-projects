from fastapi.testclient import TestClient

from tests.api.v1.helpers import ADMIN_HEADERS, RUNNER_HEADERS, runner_with_idempotency


def test_get_policy(client: TestClient) -> None:
    response = client.get("/api/v1/execution/policy", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["max_source_bytes"] == 8192
    assert body["allowed_languages"] == ["python"]


def test_create_run_success(client: TestClient) -> None:
    response = client.post(
        "/api/v1/execution/runs",
        headers=runner_with_idempotency("run-ok-1"),
        json={"language": "python", "source": "print(2 + 2)"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["stdout"].strip() == "4"
    assert body["exit_code"] == 0


def test_create_run_idempotent(client: TestClient) -> None:
    headers = runner_with_idempotency("run-idem-1")
    payload = {"language": "python", "source": "print('once')"}
    first = client.post("/api/v1/execution/runs", headers=headers, json=payload)
    second = client.post("/api/v1/execution/runs", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_create_run_rejects_import(client: TestClient) -> None:
    response = client.post(
        "/api/v1/execution/runs",
        headers=runner_with_idempotency("run-reject-1"),
        json={"language": "python", "source": "import os\nprint(os.getcwd())"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "rejected"
    assert "import" in body["stderr"].lower() or "Forbidden" in body["stderr"]


def test_create_run_requires_idempotency(client: TestClient) -> None:
    response = client.post(
        "/api/v1/execution/runs",
        headers=RUNNER_HEADERS,
        json={"language": "python", "source": "print(1)"},
    )
    assert response.status_code == 403


def test_get_run_runner_key(client: TestClient) -> None:
    created = client.post(
        "/api/v1/execution/runs",
        headers=runner_with_idempotency("run-get-1"),
        json={"language": "python", "source": "print('hi')"},
    ).json()
    response = client.get(
        f"/api/v1/execution/runs/{created['id']}",
        headers=RUNNER_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["stdout"].strip() == "hi"


def test_list_runs_admin_only(client: TestClient) -> None:
    denied = client.get("/api/v1/execution/runs", headers=RUNNER_HEADERS)
    assert denied.status_code == 401
    allowed = client.get("/api/v1/execution/runs", headers=ADMIN_HEADERS)
    assert allowed.status_code == 200
    assert len(allowed.json()) >= 1


def test_patch_policy(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/execution/policy",
        headers=ADMIN_HEADERS,
        json={"max_timeout_ms": 1500},
    )
    assert response.status_code == 200
    assert response.json()["max_timeout_ms"] == 1500
