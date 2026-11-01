from fastapi.testclient import TestClient

from tests.api.v1.helpers import demo_headers, seed_api_key_headers


def test_seed_key_whoami(client: TestClient) -> None:
    response = client.get("/api/v1/access/whoami", headers=seed_api_key_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["auth_method"] == "api_key"
    assert body["email"] == "demo@example.com"
    assert "projects:read" in body["scopes"]


def test_list_projects_with_api_key(client: TestClient) -> None:
    response = client.get("/api/v1/access/projects", headers=seed_api_key_headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_scope_enforcement(client: TestClient) -> None:
    headers = demo_headers(client)
    created = client.post(
        "/api/v1/keys",
        headers=headers,
        json={"name": "Metrics only", "scopes": ["metrics:read"]},
    )
    secret = created.json()["secret"]
    denied = client.get("/api/v1/access/projects", headers={"X-Api-Key": secret})
    assert denied.status_code == 403


def test_jwt_bypasses_scopes(client: TestClient) -> None:
    headers = demo_headers(client)
    response = client.get("/api/v1/access/projects", headers=headers)
    assert response.status_code == 200


def test_create_project_with_write_scope(client: TestClient) -> None:
    response = client.post(
        "/api/v1/access/projects",
        headers=seed_api_key_headers(),
        json={"name": "Webhook service", "description": "Outbound integrations"},
    )
    assert response.status_code == 201
