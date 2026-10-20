from fastapi.testclient import TestClient


def register_headers(
    client: TestClient,
    email: str,
    *,
    password: str = "SecurePass1!",
    full_name: str = "Test User",
) -> tuple[dict[str, str], str]:
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
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


def admin_headers(client: TestClient) -> tuple[dict[str, str], str]:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token
