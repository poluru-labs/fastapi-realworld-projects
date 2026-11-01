from fastapi.testclient import TestClient


def test_register_and_login(client: TestClient) -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "SecurePass123!",
            "full_name": "New User",
            "tenant_name": "New Co",
            "tenant_slug": "new-co",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["tokens"]["access_token"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "new@example.com", "password": "SecurePass123!"},
    )
    assert login.status_code == 200


def test_list_tenants_mine(client: TestClient, tenant_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/tenants/mine", headers=tenant_headers)
    assert response.status_code == 200
    slugs = [row["tenant"]["slug"] for row in response.json()]
    assert "acme-corp" in slugs
