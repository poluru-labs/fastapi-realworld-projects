from fastapi.testclient import TestClient

from tests.api.v1.helpers import ADMIN_HEADERS, RUNNER_HEADERS, runner_with_idempotency


def test_seed_workflow_listed(client: TestClient) -> None:
    response = client.get("/api/v1/agent-workflows", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    slugs = [row["slug"] for row in response.json()]
    assert "research-assistant" in slugs


def test_run_research_assistant(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent-runs",
        headers=runner_with_idempotency("run-research-1"),
        json={"workflow_slug": "research-assistant", "input": {"goal": "vector databases"}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["steps"]) == 3
    assert body["steps"][0]["step_key"] == "plan"


def test_run_idempotent(client: TestClient) -> None:
    headers = runner_with_idempotency("run-idem-1")
    payload = {"workflow_slug": "research-assistant", "input": {"goal": "cache"}}
    first = client.post("/api/v1/agent-runs", headers=headers, json=payload)
    second = client.post("/api/v1/agent-runs", headers=headers, json=payload)
    assert first.json()["id"] == second.json()["id"]


def test_draft_workflow_cannot_run(client: TestClient) -> None:
    created = client.post(
        "/api/v1/agent-workflows",
        headers=ADMIN_HEADERS,
        json={
            "slug": "draft-only",
            "name": "Draft",
            "steps": [{"key": "a", "type": "agent", "prompt_template": "Hi {name}"}],
        },
    )
    assert created.status_code == 201

    denied = client.post(
        "/api/v1/agent-runs",
        headers=runner_with_idempotency("run-draft-1"),
        json={"workflow_slug": "draft-only", "input": {"name": "x"}},
    )
    assert denied.status_code == 400


def test_publish_and_run(client: TestClient) -> None:
    client.post(
        "/api/v1/agent-workflows",
        headers=ADMIN_HEADERS,
        json={
            "slug": "hello-flow",
            "name": "Hello",
            "steps": [{"key": "greet", "type": "agent", "prompt_template": "Hello {who}"}],
        },
    )
    client.post("/api/v1/agent-workflows/hello-flow/publish", headers=ADMIN_HEADERS)
    ok = client.post(
        "/api/v1/agent-runs",
        headers=runner_with_idempotency("run-hello-1"),
        json={"workflow_slug": "hello-flow", "input": {"who": "agent"}},
    )
    assert ok.status_code == 201
    assert ok.json()["steps"][0]["step_type"] == "agent"


def test_get_run_runner(client: TestClient) -> None:
    created = client.post(
        "/api/v1/agent-runs",
        headers=runner_with_idempotency("run-get-1"),
        json={"workflow_slug": "research-assistant", "input": {"goal": "testing"}},
    ).json()
    response = client.get(f"/api/v1/agent-runs/{created['id']}", headers=RUNNER_HEADERS)
    assert response.status_code == 200


def test_list_runs_admin(client: TestClient) -> None:
    denied = client.get("/api/v1/agent-runs", headers=RUNNER_HEADERS)
    assert denied.status_code == 401
    allowed = client.get("/api/v1/agent-runs", headers=ADMIN_HEADERS)
    assert allowed.status_code == 200
