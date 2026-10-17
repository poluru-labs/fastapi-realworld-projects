from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_ticket, register_headers

SEED_OPEN = "cannot-reset-password"


def test_replies_on_active_ticket(client: TestClient) -> None:
    user = register_headers(client, "replier@example.com")
    admin = admin_headers(client)

    on_draft = create_ticket(client, user, title="Draft thread")
    draft_slug = on_draft["slug"]
    blocked = client.post(
        f"/api/v1/tickets/{draft_slug}/replies",
        headers=user,
        json={"message": "Too early."},
    )
    assert blocked.status_code == 409

    listed = client.get(f"/api/v1/tickets/{SEED_OPEN}/replies", headers=admin)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    created = client.post(
        f"/api/v1/tickets/{SEED_OPEN}/replies",
        headers=admin,
        json={"message": "  Still broken.  "},
    )
    assert created.status_code == 201
    assert created.json()["message"] == "Still broken."

    own = create_ticket(client, user, title="My open issue")
    client.post(f"/api/v1/tickets/{own['slug']}/submit", headers=user)
    customer_reply = client.post(
        f"/api/v1/tickets/{own['slug']}/replies",
        headers=user,
        json={"message": "Following up."},
    )
    assert customer_reply.status_code == 201


def test_reply_requires_auth(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/tickets/{SEED_OPEN}/replies",
        json={"message": "Hello."},
    )
    assert response.status_code == 401
