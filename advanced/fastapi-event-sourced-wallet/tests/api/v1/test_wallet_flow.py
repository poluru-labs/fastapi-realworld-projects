from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, auth_headers


def test_admin_seed_wallet(client: TestClient) -> None:
    headers = admin_headers(client)
    wallets = client.get("/api/v1/wallets", headers=headers)
    assert wallets.status_code == 200
    row = next(w for w in wallets.json() if w["name"] == "Demo Treasury")
    assert row["balance_cents"] == 100_000
    assert row["version"] == 2

    events = client.get(f"/api/v1/wallets/{row['id']}/events", headers=headers)
    assert len(events.json()) == 2


def test_create_deposit_idempotency(client: TestClient) -> None:
    headers = auth_headers(client, "alice@example.com")
    idem = {"Idempotency-Key": "create-alice-wallet"}

    created = client.post(
        "/api/v1/wallets",
        headers={**headers, **idem},
        json={"name": "Spending", "currency": "USD"},
    )
    assert created.status_code == 201
    wallet = created.json()
    assert wallet["version"] == 1

    again = client.post(
        "/api/v1/wallets",
        headers={**headers, **idem},
        json={"name": "Spending", "currency": "USD"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == wallet["id"]

    deposit = client.post(
        f"/api/v1/wallets/{wallet['id']}/deposits",
        headers={**headers, "Idempotency-Key": "dep-1"},
        json={"amount_cents": 5000, "expected_version": 1, "memo": "Top up"},
    )
    assert deposit.status_code == 200
    assert deposit.json()["balance_cents"] == 5000
    assert deposit.json()["version"] == 2


def test_withdraw_insufficient_funds(client: TestClient) -> None:
    headers = auth_headers(client, "bob@example.com")
    wallet = client.post(
        "/api/v1/wallets",
        headers={**headers, "Idempotency-Key": "bob-wallet"},
        json={"name": "Cash", "currency": "USD"},
    ).json()

    failed = client.post(
        f"/api/v1/wallets/{wallet['id']}/withdrawals",
        headers={**headers, "Idempotency-Key": "wd-fail"},
        json={"amount_cents": 100, "expected_version": 1},
    )
    assert failed.status_code == 409


def test_transfer_and_version_conflict(client: TestClient) -> None:
    headers = auth_headers(client, "carol@example.com")
    a = client.post(
        "/api/v1/wallets",
        headers={**headers, "Idempotency-Key": "wallet-a"},
        json={"name": "A", "currency": "USD"},
    ).json()
    b = client.post(
        "/api/v1/wallets",
        headers={**headers, "Idempotency-Key": "wallet-b"},
        json={"name": "B", "currency": "USD"},
    ).json()
    funded = client.post(
        f"/api/v1/wallets/{a['id']}/deposits",
        headers={**headers, "Idempotency-Key": "fund-a"},
        json={"amount_cents": 2000, "expected_version": 1},
    ).json()

    moved = client.post(
        "/api/v1/wallets/transfers",
        headers={**headers, "Idempotency-Key": "xfer-1"},
        json={
            "from_wallet_id": a["id"],
            "to_wallet_id": b["id"],
            "amount_cents": 750,
            "expected_version": funded["version"],
        },
    )
    assert moved.status_code == 200
    body = moved.json()
    assert body["from_wallet"]["balance_cents"] == 1250
    assert body["to_wallet"]["balance_cents"] == 750

    stale = client.post(
        f"/api/v1/wallets/{a['id']}/deposits",
        headers={**headers, "Idempotency-Key": "stale-dep"},
        json={"amount_cents": 100, "expected_version": funded["version"]},
    )
    assert stale.status_code == 409


def test_other_users_wallet_not_found(client: TestClient) -> None:
    owner = auth_headers(client, "dave@example.com")
    other = auth_headers(client, "erin@example.com")
    wallet = client.post(
        "/api/v1/wallets",
        headers={**owner, "Idempotency-Key": "dave-w"},
        json={"name": "Secret", "currency": "USD"},
    ).json()
    response = client.get(f"/api/v1/wallets/{wallet['id']}", headers=other)
    assert response.status_code == 404
