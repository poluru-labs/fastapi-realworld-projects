from fastapi.testclient import TestClient


def auth_headers(
    client: TestClient,
    email: str,
    *,
    password: str = "SecurePass123!",
) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Shopper"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
