from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers


def test_public_list_is_active_only(client: TestClient) -> None:
    response = client.get("/api/v1/plans")
    assert response.status_code == 200
    slugs = {row["slug"] for row in response.json()}
    assert slugs == {"starter-monthly", "pro-yearly"}


def test_draft_plan_is_hidden(client: TestClient) -> None:
    response = client.get("/api/v1/plans/draft-internal")
    assert response.status_code == 404


def test_admin_can_read_draft(client: TestClient) -> None:
    headers = admin_headers(client)
    response = client.get("/api/v1/plans/draft-internal", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_admin_create_activate_flow(client: TestClient) -> None:
    headers = admin_headers(client)
    created = client.post(
        "/api/v1/plans",
        headers=headers,
        json={
            "name": "Business Monthly",
            "price_cents": 7900,
            "interval": "monthly",
        },
    )
    assert created.status_code == 201
    slug = created.json()["slug"]
    assert created.json()["status"] == "draft"

    activated = client.post(f"/api/v1/plans/{slug}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"


def test_tags_on_active_plans(client: TestClient) -> None:
    response = client.get("/api/v1/tags")
    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert "starter" in names
    assert "internal" not in names
