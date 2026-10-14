from fastapi.testclient import TestClient


def test_list_flagged_first(client: TestClient) -> None:
    response = client.get("/api/v1/expenses")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["merchant"] == "Cloud Tools"
    assert data[0]["flagged"] is True


def test_summary(client: TestClient) -> None:
    response = client.get(
        "/api/v1/expenses/summary",
        params={"from_date": "2026-10-01", "to_date": "2026-10-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert body["total_cents"] == 450 + 8500 + 1200


def test_list_categories(client: TestClient) -> None:
    response = client.get("/api/v1/expenses/categories")
    assert response.status_code == 200
    assert response.json() == ["Food", "Software", "Transport"]


def test_create_and_duplicate_receipt(client: TestClient) -> None:
    created = client.post(
        "/api/v1/expenses",
        json={
            "merchant": "Bookstore",
            "amount_cents": 1999,
            "category": "Education",
            "spent_on": "2026-10-05",
            "receipt_ref": "RCPT-NEW",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == 4

    conflict = client.post(
        "/api/v1/expenses",
        json={
            "merchant": "Other",
            "amount_cents": 100,
            "spent_on": "2026-10-06",
            "receipt_ref": "rcpt-new",
        },
    )
    assert conflict.status_code == 409


def test_date_filter(client: TestClient) -> None:
    response = client.get("/api/v1/expenses", params={"from_date": "2026-10-03"})
    assert len(response.json()) == 1
    assert response.json()[0]["merchant"] == "Cloud Tools"


def test_unflag_and_delete(client: TestClient) -> None:
    unflag = client.post("/api/v1/expenses/3/unflag")
    assert unflag.status_code == 200
    assert unflag.json()["flagged"] is False

    deleted = client.delete("/api/v1/expenses/2")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
