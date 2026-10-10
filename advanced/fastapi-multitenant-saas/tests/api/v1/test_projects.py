from fastapi.testclient import TestClient


def test_project_crud(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"name": "Alpha", "description": "First project"},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    listed = client.get("/api/v1/projects", headers=auth_headers)
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"name": "Alpha Renamed"},
    )
    assert patched.json()["name"] == "Alpha Renamed"

    deleted = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert deleted.status_code == 204


def test_free_plan_project_limit(client: TestClient, auth_headers: dict[str, str]) -> None:
    for index in range(3):
        response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"name": f"P{index}", "description": ""},
        )
        assert response.status_code == 201

    blocked = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"name": "Overflow", "description": ""},
    )
    assert blocked.status_code == 409


def test_wrong_tenant_slug_is_forbidden(client: TestClient, auth_headers: dict[str, str]) -> None:
    headers = {
        **auth_headers,
        "X-Tenant-Slug": "unknown-slug",
    }
    response = client.get("/api/v1/projects", headers=headers)
    assert response.status_code == 404
