from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers


def test_subscribe_and_cancel(client: TestClient) -> None:
    headers = register_headers(client, "alice@example.com")
    created = client.post(
        "/api/v1/subscriptions",
        headers=headers,
        json={"plan_slug": "starter-monthly"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "active"
    assert created.json()["interval"] == "monthly"
    sub_id = created.json()["id"]

    cancelled = client.post(f"/api/v1/subscriptions/{sub_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_duplicate_subscription_conflict(client: TestClient) -> None:
    headers = register_headers(client, "bob@example.com")
    payload = {"plan_slug": "pro-yearly"}
    assert client.post("/api/v1/subscriptions", headers=headers, json=payload).status_code == 201
    again = client.post("/api/v1/subscriptions", headers=headers, json=payload)
    assert again.status_code == 409


def test_admin_lists_plan_subscribers(client: TestClient) -> None:
    user = register_headers(client, "carol@example.com")
    client.post(
        "/api/v1/subscriptions",
        headers=user,
        json={"plan_slug": "starter-monthly"},
    )
    admin = admin_headers(client)
    rows = client.get("/api/v1/plans/starter-monthly/subscriptions", headers=admin)
    assert rows.status_code == 200
    assert len(rows.json()) >= 1


def test_other_users_subscription_is_not_found(client: TestClient) -> None:
    owner = register_headers(client, "dave@example.com")
    other = register_headers(client, "erin@example.com")
    created = client.post(
        "/api/v1/subscriptions",
        headers=owner,
        json={"plan_slug": "starter-monthly"},
    ).json()
    response = client.get(f"/api/v1/subscriptions/{created['id']}", headers=other)
    assert response.status_code == 404
