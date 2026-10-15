from fastapi.testclient import TestClient


def test_list_paused_last(client: TestClient) -> None:
    response = client.get("/api/v1/habits")
    assert response.status_code == 200
    data = response.json()
    assert data[-1]["name"] == "Evening meditation"
    assert data[-1]["paused"] is True


def test_streak_stats(client: TestClient) -> None:
    response = client.get(
        "/api/v1/habits/1/stats",
        params={"week_of": "2026-10-14"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_streak"] == 3
    assert body["total_check_ins"] == 3
    assert body["check_ins_this_week"] == 3


def test_list_categories(client: TestClient) -> None:
    assert client.get("/api/v1/habits/categories").json() == ["Health", "Learning"]


def test_check_in_and_duplicate_day(client: TestClient) -> None:
    created = client.post(
        "/api/v1/habits/2/check-ins",
        json={"checked_on": "2026-10-15", "note": "Chapter 3"},
    )
    assert created.status_code == 201

    conflict = client.post(
        "/api/v1/habits/2/check-ins",
        json={"checked_on": "2026-10-15"},
    )
    assert conflict.status_code == 409


def test_paused_habit_rejects_check_in(client: TestClient) -> None:
    response = client.post(
        "/api/v1/habits/3/check-ins",
        json={"checked_on": "2026-10-15"},
    )
    assert response.status_code == 409


def test_create_habit_and_delete_check_in(client: TestClient) -> None:
    habit = client.post(
        "/api/v1/habits",
        json={"name": "Stretch", "category": "Health", "target_days_per_week": 3},
    )
    assert habit.status_code == 201
    habit_id = habit.json()["id"]

    check_in = client.post(
        f"/api/v1/habits/{habit_id}/check-ins",
        json={"checked_on": "2026-10-01"},
    ).json()

    deleted = client.delete(f"/api/v1/habits/{habit_id}/check-ins/{check_in['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
