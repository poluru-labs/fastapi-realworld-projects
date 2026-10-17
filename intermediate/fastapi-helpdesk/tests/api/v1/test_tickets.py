from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_ticket, register_headers

SEED_OPEN = "cannot-reset-password"
SEED_DRAFT = "draft-vpn-request"


def test_admin_queue_excludes_drafts(client: TestClient) -> None:
    queue = client.get("/api/v1/tickets", headers=admin_headers(client))
    assert queue.status_code == 200
    page = queue.json()
    assert page["total"] == 1
    assert page["items"][0]["slug"] == SEED_OPEN
    assert page["items"][0]["reply_count"] == 1

    stranger = register_headers(client, "queue@example.com")
    denied = client.get("/api/v1/tickets", headers=stranger)
    assert denied.status_code == 403


def test_draft_hidden_from_other_users(client: TestClient) -> None:
    stranger = register_headers(client, "reader@example.com")
    hidden = client.get(f"/api/v1/tickets/{SEED_DRAFT}", headers=stranger)
    assert hidden.status_code == 404

    admin = client.get(f"/api/v1/tickets/{SEED_DRAFT}", headers=admin_headers(client))
    assert admin.status_code == 200


def test_submit_and_workflow(client: TestClient) -> None:
    requester = register_headers(client, "customer@example.com")
    created = create_ticket(client, requester, title="Login issue")
    slug = created["slug"]
    assert created["status"] == "draft"

    client.post(f"/api/v1/tickets/{slug}/submit", headers=requester)
    submitted = client.get(f"/api/v1/tickets/{slug}", headers=requester).json()
    assert submitted["status"] == "open"

    admin = admin_headers(client)
    client.patch(
        f"/api/v1/tickets/{slug}",
        headers=admin,
        json={"assignee_id": 1},
    )
    started = client.post(f"/api/v1/tickets/{slug}/start", headers=admin)
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"

    resolved = client.post(f"/api/v1/tickets/{slug}/resolve", headers=admin)
    assert resolved.json()["status"] == "resolved"

    closed = client.post(f"/api/v1/tickets/{slug}/close", headers=requester)
    assert closed.json()["status"] == "closed"


def test_other_users_ticket_not_found(client: TestClient) -> None:
    owner = register_headers(client, "owner@example.com")
    other = register_headers(client, "other@example.com")
    ticket = create_ticket(client, owner, title="Private issue")
    client.post(f"/api/v1/tickets/{ticket['slug']}/submit", headers=owner)
    hidden = client.get(f"/api/v1/tickets/{ticket['slug']}", headers=other)
    assert hidden.status_code == 404


def test_categories_count_submitted_only(client: TestClient) -> None:
    cats = client.get("/api/v1/categories")
    assert cats.status_code == 200
    counted = {item["name"]: item["ticket_count"] for item in cats.json()}
    assert counted == {"account": 1, "auth": 1}
    assert "vpn" not in counted
