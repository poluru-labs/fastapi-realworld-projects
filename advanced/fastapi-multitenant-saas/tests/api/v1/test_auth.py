from fastapi.testclient import TestClient


def test_register_login_refresh(client: TestClient) -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dev@example.com",
            "password": "SecurePass123!",
            "full_name": "Dev User",
            "tenant_name": "Dev Co",
            "tenant_slug": "dev-co",
        },
    )
    assert reg.status_code == 201
    tokens = reg.json()["tokens"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "dev@example.com", "password": "SecurePass123!"},
    )
    assert login.status_code == 200

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert logout.status_code == 204


def test_register_duplicate_email(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@acme.example",
            "password": "SecurePass123!",
            "full_name": "Other",
            "tenant_name": "Other",
            "tenant_slug": "other-co",
        },
    )
    assert response.status_code == 409
