from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_account, register_headers

SEED_CHECKING = "checking-main"


def test_admin_lists_all_accounts(client: TestClient) -> None:
    page = client.get("/api/v1/accounts", headers=admin_headers(client))
    assert page.status_code == 200
    assert page.json()["total"] == 2

    stranger = register_headers(client, "accounts@example.com")
    denied = client.get("/api/v1/accounts", headers=stranger)
    assert denied.status_code == 403


def test_balance_excludes_drafts(client: TestClient) -> None:
    admin = admin_headers(client)
    account = client.get(f"/api/v1/accounts/{SEED_CHECKING}", headers=admin).json()
    assert account["opening_balance"] == 1000.0
    assert account["current_balance"] == 4154.8


def test_other_users_account_not_found(client: TestClient) -> None:
    owner = register_headers(client, "owner@example.com")
    other = register_headers(client, "other@example.com")
    slug = create_account(client, owner, name="Private pot")["slug"]
    hidden = client.get(f"/api/v1/accounts/{slug}", headers=other)
    assert hidden.status_code == 404


def test_draft_post_and_void(client: TestClient) -> None:
    user = register_headers(client, "spender@example.com")
    slug = create_account(client, user, name="Daily checking", opening_balance=500.0)["slug"]

    draft = client.post(
        f"/api/v1/accounts/{slug}/transactions",
        headers=user,
        json={
            "amount": -25.0,
            "category": "dining",
            "payee": "Bistro",
            "occurred_on": "2026-02-05",
        },
    )
    assert draft.status_code == 201
    tx_id = draft.json()["id"]
    assert draft.json()["status"] == "draft"

    before = client.get(f"/api/v1/accounts/{slug}", headers=user).json()
    assert before["current_balance"] == 500.0

    posted = client.post(
        f"/api/v1/accounts/{slug}/transactions/{tx_id}/post",
        headers=user,
    )
    assert posted.status_code == 200
    after_post = client.get(f"/api/v1/accounts/{slug}", headers=user).json()
    assert after_post["current_balance"] == 475.0

    voided = client.post(
        f"/api/v1/accounts/{slug}/transactions/{tx_id}/void",
        headers=user,
    )
    assert voided.json()["status"] == "voided"
    after_void = client.get(f"/api/v1/accounts/{slug}", headers=user).json()
    assert after_void["current_balance"] == 500.0


def test_spending_categories_posted_expenses_only(client: TestClient) -> None:
    admin = admin_headers(client)
    summary = client.get("/api/v1/spending/categories", headers=admin)
    assert summary.status_code == 200
    rows = {item["category"]: item["total_spent"] for item in summary.json()}
    assert rows["groceries"] == 45.2
    assert "salary" not in rows
    assert "dining" not in rows
