from fastapi.testclient import TestClient


def test_tenant_isolation_header_required(client: TestClient, auth_headers: dict[str, str]) -> None:
    headers = {"Authorization": auth_headers["Authorization"]}
    response = client.get("/api/v1/tenants/current", headers=headers)
    assert response.status_code == 403


def test_list_mine_and_current(client: TestClient, auth_headers: dict[str, str]) -> None:
    mine = client.get("/api/v1/tenants/mine", headers=auth_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["tenant"]["slug"] == "acme-corp"

    current = client.get("/api/v1/tenants/current", headers=auth_headers)
    assert current.status_code == 200
    assert current.json()["slug"] == "acme-corp"


def test_invite_member(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "member@example.com",
            "password": "SecurePass123!",
            "full_name": "Member",
            "tenant_name": "Other Tenant",
            "tenant_slug": "other-tenant",
        },
    )
    invite = client.post(
        "/api/v1/tenants/current/members",
        headers=auth_headers,
        json={"email": "member@example.com", "role": "member"},
    )
    assert invite.status_code == 201

    members = client.get("/api/v1/tenants/current/members", headers=auth_headers)
    assert len(members.json()) == 2
