from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, demo_headers, register_headers


def test_inbox_unread_filter_and_count(client: TestClient) -> None:
    headers = admin_headers(client)
    inbox = client.get("/api/v1/notifications", headers=headers)
    assert inbox.status_code == 200
    body = inbox.json()
    assert body["total"] == 3

    unread = client.get("/api/v1/notifications", headers=headers, params={"unread_only": True})
    assert unread.status_code == 200
    assert unread.json()["total"] == 2

    count = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count.status_code == 200
    assert count.json()["unread"] == 2


def test_mark_read_and_conflict(client: TestClient) -> None:
    headers = admin_headers(client)
    marked = client.post("/api/v1/notifications/1/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    again = client.post("/api/v1/notifications/1/read", headers=headers)
    assert again.status_code == 409


def test_cannot_read_another_users_notification(client: TestClient) -> None:
    demo = demo_headers(client)
    response = client.get("/api/v1/notifications/1", headers=demo)
    assert response.status_code == 404


def test_mark_all_read(client: TestClient) -> None:
    headers = admin_headers(client)
    cleared = client.post("/api/v1/notifications/read-all", headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["unread"] == 0


def test_admin_dispatch_and_preferences(client: TestClient) -> None:
    user_headers = register_headers(client, "notify@example.com")
    me = client.get("/api/v1/auth/me", headers=user_headers)
    user_id = me.json()["id"]

    admin = admin_headers(client)
    sent = client.post(
        "/api/v1/notifications/dispatch",
        headers=admin,
        json={
            "user_id": user_id,
            "type": "billing",
            "title": "Invoice ready",
            "body": "Your March invoice is available.",
            "data": {"invoice_id": "inv_123"},
        },
    )
    assert sent.status_code == 201

    inbox = client.get("/api/v1/notifications", headers=user_headers)
    assert inbox.json()["total"] == 1

    prefs = client.patch(
        "/api/v1/notifications/preferences",
        headers=user_headers,
        json={"push_enabled": False},
    )
    assert prefs.status_code == 200
    assert prefs.json()["push_enabled"] is False


def test_delete_notification(client: TestClient) -> None:
    headers = demo_headers(client)
    deleted = client.delete("/api/v1/notifications/4", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/notifications/4", headers=headers).status_code == 404
