from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str, password: str) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_register_login_and_me(client: TestClient) -> None:
    tokens = _register_and_login(client, "dev@example.com", "SecurePass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "dev@example.com"


def test_refresh_rotates_token(client: TestClient) -> None:
    tokens = _register_and_login(client, "refresh@example.com", "SecurePass1!")
    old_refresh = tokens["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    new_pair = refreshed.json()
    assert new_pair["refresh_token"] != old_refresh

    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


def test_logout_revokes_refresh(client: TestClient) -> None:
    tokens = _register_and_login(client, "logout@example.com", "SecurePass1!")
    refresh = tokens["refresh_token"]

    out = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 200

    again = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert again.status_code == 401


def test_admin_can_list_users(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    users = client.get("/api/v1/users", headers=headers)
    assert users.status_code == 200
    assert len(users.json()) >= 1


def test_non_admin_cannot_list_users(client: TestClient) -> None:
    tokens = _register_and_login(client, "user@example.com", "SecurePass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    users = client.get("/api/v1/users", headers=headers)
    assert users.status_code == 403


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
