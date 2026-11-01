from fastapi.testclient import TestClient

from tests.api.v1.helpers import demo_headers, register_headers


def test_run_customer_360(client: TestClient) -> None:
    headers = demo_headers(client)
    run = client.post("/api/v1/aggregates/customer-360/runs", headers=headers)
    assert run.status_code == 201
    body = run.json()
    assert body["partial"] is False
    keys = {fragment["key"] for fragment in body["fragments"]}
    assert keys == {"profile", "recent_orders"}
    profile = next(f for f in body["fragments"] if f["key"] == "profile")
    assert profile["status_code"] == 200
    assert profile["data"]["email"] == "demo@example.com"


def test_draft_aggregate_cannot_run(client: TestClient) -> None:
    headers = demo_headers(client)
    response = client.post("/api/v1/aggregates/draft-dashboard/runs", headers=headers)
    assert response.status_code == 409


def test_idempotency_replays_run(client: TestClient) -> None:
    headers = demo_headers(client)
    headers["Idempotency-Key"] = "run-once-abc"
    first = client.post("/api/v1/aggregates/customer-360/runs", headers=headers)
    second = client.post("/api/v1/aggregates/customer-360/runs", headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_publish_and_run_custom_plan(client: TestClient) -> None:
    headers = register_headers(client, "builder@example.com")
    source = client.post(
        "/api/v1/sources",
        headers=headers,
        json={
            "slug": "my-users",
            "display_name": "Users",
            "base_url": "https://mock.local/users",
            "mock_catalog": "users",
        },
    )
    assert source.status_code == 201

    plan = client.post(
        "/api/v1/aggregates",
        headers=headers,
        json={
            "slug": "prefs-only",
            "title": "Preferences",
            "steps": [
                {"key": "prefs", "source_slug": "my-users", "path": "/v1/preferences"},
            ],
        },
    )
    assert plan.status_code == 201
    assert plan.json()["status"] == "draft"

    published = client.post("/api/v1/aggregates/prefs-only/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    run = client.post("/api/v1/aggregates/prefs-only/runs", headers=headers)
    assert run.status_code == 201
    assert run.json()["fragments"][0]["data"]["theme"] == "dark"
