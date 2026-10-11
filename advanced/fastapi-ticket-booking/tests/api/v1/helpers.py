from fastapi.testclient import TestClient


def auth_headers(
    client: TestClient,
    email: str,
    *,
    password: str = "SecurePass123!",
) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Fan"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
