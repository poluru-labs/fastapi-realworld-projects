from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, auth_headers


def test_register_login_and_me(client: TestClient) -> None:
    headers = auth_headers(client, "dev@example.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "dev@example.com"


def test_admin_login(client: TestClient) -> None:
    headers = admin_headers(client)
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["role"] == "admin"
