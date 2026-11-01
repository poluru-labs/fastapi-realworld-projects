from fastapi.testclient import TestClient

from tests.api.v1.helpers import ADMIN_HEADERS


def test_viewer_sees_only_public_documents(
    client: TestClient,
    viewer_headers: dict[str, str],
) -> None:
    response = client.get("/api/v1/documents", headers=viewer_headers)
    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert "Public FAQ" in titles
    assert "Internal roadmap" not in titles
    assert "Secret acquisition plan" not in titles


def test_editor_sees_internal_not_secret(
    client: TestClient,
    editor_headers: dict[str, str],
) -> None:
    response = client.get("/api/v1/documents", headers=editor_headers)
    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert "Public FAQ" in titles
    assert "Internal roadmap" in titles
    assert "Secret acquisition plan" not in titles


def test_evaluate_denied_for_viewer_on_secret(
    client: TestClient,
    viewer_headers: dict[str, str],
) -> None:
    evaluate = client.post(
        "/api/v1/policy/evaluate",
        headers=viewer_headers,
        json={
            "action": "documents:read",
            "resource": "document/99",
            "resource_attributes": {"classification": "secret"},
        },
    )
    assert evaluate.status_code == 200
    assert evaluate.json()["allowed"] is False


def test_editor_can_create_document(client: TestClient, editor_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/documents",
        headers=editor_headers,
        json={"title": "New note", "classification": "public", "body": "hello"},
    )
    assert response.status_code == 201


def test_admin_lists_rules(client: TestClient) -> None:
    response = client.get("/api/v1/policy/rules", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) >= 2
