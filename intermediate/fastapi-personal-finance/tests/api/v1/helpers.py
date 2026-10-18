from fastapi.testclient import TestClient


def register_headers(
    client: TestClient,
    email: str,
    *,
    password: str = "SecurePass1!",
    full_name: str = "Test User",
) -> dict[str, str]:
    created = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert created.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_account(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Side checking",
    **extra: object,
) -> dict:
    payload: dict = {
        "name": name,
        "account_type": "checking",
        "currency": "USD",
        "opening_balance": 100.0,
    }
    payload.update(extra)
    response = client.post("/api/v1/accounts", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()
