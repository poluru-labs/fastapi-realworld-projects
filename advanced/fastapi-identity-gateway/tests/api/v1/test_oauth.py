from fastapi.testclient import TestClient

from tests.api.v1.helpers import (
    ADMIN_HEADERS,
    SEED_CLIENT_ID,
    SEED_CLIENT_SECRET,
    SEED_REDIRECT_URI,
)


def test_openid_configuration(client: TestClient) -> None:
    response = client.get("/api/v1/oauth/.well-known/openid-configuration")
    assert response.status_code == 200
    body = response.json()
    assert body["token_endpoint"].endswith("/api/v1/oauth/token")


def test_client_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": SEED_CLIENT_ID,
            "client_secret": SEED_CLIENT_SECRET,
            "scope": "api:read",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert "api:read" in body["scope"]


def test_authorization_code_flow(client: TestClient, user_headers: dict[str, str]) -> None:
    auth = client.post(
        "/api/v1/oauth/authorize",
        headers=user_headers,
        json={
            "client_id": SEED_CLIENT_ID,
            "redirect_uri": SEED_REDIRECT_URI,
            "scope": "openid profile email",
        },
    )
    assert auth.status_code == 200
    code = auth.json()["code"]

    token = client.post(
        "/api/v1/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": SEED_CLIENT_ID,
            "client_secret": SEED_CLIENT_SECRET,
            "code": code,
            "redirect_uri": SEED_REDIRECT_URI,
        },
    )
    assert token.status_code == 200
    access = token.json()["access_token"]

    userinfo = client.get(
        "/api/v1/oauth/userinfo",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert userinfo.status_code == 200
    assert userinfo.json()["email"] == "demo@example.com"

    introspect = client.post(
        "/api/v1/oauth/introspect",
        headers=ADMIN_HEADERS,
        json={"token": access},
    )
    assert introspect.status_code == 200
    assert introspect.json()["active"] is True


def test_admin_list_clients(client: TestClient) -> None:
    response = client.get("/api/v1/oauth/clients", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert any(row["client_id"] == SEED_CLIENT_ID for row in response.json())
