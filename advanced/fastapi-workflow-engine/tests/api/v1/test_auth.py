from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, auth_headers


def test_register_login_and_me(client: TestClient) -> None:
    headers = auth_headers(client, "dev@example.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "dev@example.com"


def test_admin_can_list_published_definitions(client: TestClient) -> None:
    rows = client.get("/api/v1/workflow-definitions")
    assert rows.status_code == 200
    slugs = {row["slug"] for row in rows.json()}
    assert "employee-onboarding" in slugs
    assert "draft-internal" not in slugs


def test_admin_sees_draft_definition(client: TestClient) -> None:
    headers = admin_headers(client)
    draft = client.get("/api/v1/workflow-definitions/draft-internal", headers=headers)
    assert draft.status_code == 200
    assert draft.json()["status"] == "draft"
