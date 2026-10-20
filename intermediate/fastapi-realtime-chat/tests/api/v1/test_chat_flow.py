from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers

GENERAL = "general"
PRIVATE = "team-leads"


def test_discover_and_private_room_is_hidden(client: TestClient) -> None:
    listed = client.get("/api/v1/rooms")
    assert listed.status_code == 200
    slugs = [room["slug"] for room in listed.json()]
    assert GENERAL in slugs
    assert PRIVATE not in slugs

    stranger = register_headers(client, "stranger@example.com")[0]
    hidden = client.get(f"/api/v1/rooms/{PRIVATE}", headers=stranger)
    assert hidden.status_code == 404


def test_join_send_and_cursor_history(client: TestClient) -> None:
    headers, _token = register_headers(client, "chatter@example.com", full_name="Chatter")
    joined = client.post(f"/api/v1/rooms/{GENERAL}/join", headers=headers)
    assert joined.status_code == 200

    sent = client.post(
        f"/api/v1/rooms/{GENERAL}/messages",
        headers=headers,
        json={"body": "Hello from REST"},
    )
    assert sent.status_code == 201
    assert sent.json()["sequence"] == 2

    page = client.get(
        f"/api/v1/rooms/{GENERAL}/messages",
        headers=headers,
        params={"after_sequence": 1},
    )
    assert page.status_code == 200
    assert [item["body"] for item in page.json()["items"]] == ["Hello from REST"]

    cursor = client.put(
        f"/api/v1/rooms/{GENERAL}/read-cursor",
        headers=headers,
        json={"last_read_sequence": 2},
    )
    assert cursor.status_code == 200
    assert cursor.json()["last_read_sequence"] == 2


def test_websocket_receives_broadcast(client: TestClient) -> None:
    headers, token = register_headers(client, "live@example.com", full_name="Live User")
    assert client.post(f"/api/v1/rooms/{GENERAL}/join", headers=headers).status_code == 200

    with client.websocket_connect(
        f"/api/v1/ws/rooms/{GENERAL}?access_token={token}"
    ) as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"

        posted = client.post(
            f"/api/v1/rooms/{GENERAL}/messages",
            headers=headers,
            json={"body": "Push me"},
        )
        assert posted.status_code == 201

        event = websocket.receive_json()
        assert event["type"] == "message"
        assert event["payload"]["body"] == "Push me"


def test_admin_invite_to_private_room(client: TestClient) -> None:
    member_headers, _ = register_headers(client, "lead@example.com")
    admin, _ = admin_headers(client)
    invited = client.post(f"/api/v1/rooms/{PRIVATE}/invite/2", headers=admin)
    assert invited.status_code == 200

    visible = client.get(f"/api/v1/rooms/{PRIVATE}", headers=member_headers)
    assert visible.status_code == 200
