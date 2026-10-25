from fastapi.testclient import TestClient


def test_list_polls(client: TestClient) -> None:
    response = client.get("/api/v1/polls")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["question"] == "What is your favorite programming language?"


def test_get_poll_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/polls/999")
    assert response.status_code == 404


def test_create_poll(client: TestClient) -> None:
    response = client.post(
        "/api/v1/polls",
        json={
            "question": "Coffee or tea?",
            "options": ["Coffee", "Tea"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["question"] == "Coffee or tea?"
    assert body["id"] == 3
    assert len(body["options"]) == 2


def test_cast_vote(client: TestClient) -> None:
    before = client.get("/api/v1/polls/1").json()
    go_votes = next(option["votes"] for option in before["options"] if option["text"] == "Go")

    response = client.post("/api/v1/polls/1/votes", json={"option_id": 3})
    assert response.status_code == 200
    after = response.json()
    go_after = next(option for option in after["options"] if option["text"] == "Go")
    assert go_after["votes"] == go_votes + 1


def test_cast_vote_invalid_option(client: TestClient) -> None:
    response = client.post("/api/v1/polls/1/votes", json={"option_id": 99})
    assert response.status_code == 404


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
