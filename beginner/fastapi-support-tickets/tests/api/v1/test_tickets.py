from fastapi.testclient import TestClient

OPEN_TICKET_ID = 1
CLOSED_TICKET_ID = 3


def test_list_and_filter_status(client: TestClient) -> None:
    all_tickets = client.get("/api/v1/tickets")
    assert all_tickets.status_code == 200
    assert len(all_tickets.json()) == 3

    open_only = client.get("/api/v1/tickets", params={"status": "open"})
    assert len(open_only.json()) == 1

    detail = client.get(f"/api/v1/tickets/{OPEN_TICKET_ID}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["comment_count"] == 2
    assert len(body["comments"]) == 2


def test_add_comment_and_closed_rejects(client: TestClient) -> None:
    created = client.post(
        f"/api/v1/tickets/{OPEN_TICKET_ID}/comments",
        json={
            "author_name": "Alex Rivera",
            "body": "Attaching a HAR file next.",
            "is_internal": False,
        },
    )
    assert created.status_code == 201

    blocked = client.post(
        f"/api/v1/tickets/{CLOSED_TICKET_ID}/comments",
        json={"author_name": "Guest", "body": "Still broken?", "is_internal": False},
    )
    assert blocked.status_code == 409


def test_resolve_and_close_flow(client: TestClient) -> None:
    created = client.post(
        "/api/v1/tickets",
        json={
            "subject": "VPN drops hourly",
            "description": "Disconnects after ~60 minutes.",
            "requester_email": "ops@example.com",
            "priority": "urgent",
        },
    )
    ticket_id = created.json()["id"]

    resolved = client.post(f"/api/v1/tickets/{ticket_id}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert client.post(f"/api/v1/tickets/{ticket_id}/resolve").status_code == 409

    closed = client.post(f"/api/v1/tickets/{ticket_id}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"


def test_reopen_ticket(client: TestClient) -> None:
    reopened = client.post(f"/api/v1/tickets/{CLOSED_TICKET_ID}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert client.post(f"/api/v1/tickets/{CLOSED_TICKET_ID}/reopen").status_code == 409


def test_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/tickets/999").status_code == 404
