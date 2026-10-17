from fastapi.testclient import TestClient

from tests.api.v1.helpers import auth_headers


def test_send_idempotent_and_relay_delivery(client: TestClient) -> None:
    sender = auth_headers(client, "sender@example.com")
    recipient = auth_headers(client, "recipient@example.com")

    client.post("/api/v1/rooms/general/join", headers=recipient)
    client.post("/api/v1/rooms/general/join", headers=sender)

    sent = client.post(
        "/api/v1/rooms/general/messages",
        headers={**sender, "Idempotency-Key": "msg-1"},
        json={"body": "Hello relay world"},
    )
    assert sent.status_code == 201
    message = sent.json()
    assert message["sequence"] == 2
    assert message["body"] == "Hello relay world"

    again = client.post(
        "/api/v1/rooms/general/messages",
        headers={**sender, "Idempotency-Key": "msg-1"},
        json={"body": "ignored"},
    )
    assert again.json()["id"] == message["id"]

    relay_user = auth_headers(client, "relay@example.com")
    client.post(
        "/api/v1/relays/register",
        headers=relay_user,
        json={"relay_id": "relay-a", "room_slugs": ["general"]},
    )
    claimed = client.post(
        "/api/v1/relays/claim",
        headers=relay_user,
        json={"relay_id": "relay-a"},
    )
    assert claimed.status_code == 200
    delivery = claimed.json()
    assert delivery["recipient_id"] != message["author_id"]
    assert delivery["status"] == "delivering"
    version = delivery["version"]

    completed = client.post(
        f"/api/v1/relays/deliveries/{delivery['id']}/complete",
        headers=relay_user,
        json={"relay_id": "relay-a", "expected_version": version},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "delivered"


def test_private_room_hidden_from_non_members(client: TestClient) -> None:
    outsider = auth_headers(client, "outsider@example.com")
    hidden = client.get("/api/v1/rooms/private-ops", headers=outsider)
    assert hidden.status_code == 404


def test_stale_version_on_relay_complete(client: TestClient) -> None:
    alice = auth_headers(client, "alice@example.com")
    bob = auth_headers(client, "bob@example.com")
    client.post("/api/v1/rooms/general/join", headers=alice)
    client.post("/api/v1/rooms/general/join", headers=bob)

    client.post(
        "/api/v1/rooms/general/messages",
        headers={**alice, "Idempotency-Key": "alice-msg"},
        json={"body": "ping"},
    )

    relay_owner = auth_headers(client, "relay-owner@example.com")
    client.post(
        "/api/v1/relays/register",
        headers=relay_owner,
        json={"relay_id": "relay-stale", "room_slugs": []},
    )
    delivery = client.post(
        "/api/v1/relays/claim",
        headers=relay_owner,
        json={"relay_id": "relay-stale"},
    ).json()

    stale = client.post(
        f"/api/v1/relays/deliveries/{delivery['id']}/complete",
        headers=relay_owner,
        json={"relay_id": "relay-stale", "expected_version": delivery["version"] - 1},
    )
    assert stale.status_code == 409


def test_message_cursor_and_read_state(client: TestClient) -> None:
    reader = auth_headers(client, "reader@example.com")
    client.post("/api/v1/rooms/general/join", headers=reader)

    page = client.get(
        "/api/v1/rooms/general/messages?after_sequence=0",
        headers=reader,
    )
    assert page.status_code == 200
    messages = page.json()
    assert len(messages) >= 1
    latest = max(row["sequence"] for row in messages)

    updated = client.patch(
        "/api/v1/rooms/general/members/me/read",
        headers=reader,
        json={"last_read_sequence": latest},
    )
    assert updated.status_code == 200
    assert updated.json()["last_read_sequence"] == latest
