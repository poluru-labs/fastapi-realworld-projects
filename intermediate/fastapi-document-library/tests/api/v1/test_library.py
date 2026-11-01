from fastapi.testclient import TestClient

from tests.api.v1.helpers import demo_headers


def test_public_library_lists_published(client: TestClient) -> None:
    response = client.get("/api/v1/library/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    slugs = {(item["folder_slug"], item["slug"]) for item in body["items"]}
    assert ("product-docs", "getting-started") in slugs


def test_draft_hidden_without_token(client: TestClient) -> None:
    assert (
        client.get("/api/v1/folders/product-docs/documents/roadmap-draft").status_code == 404
    )


def test_author_reads_draft(client: TestClient) -> None:
    headers = demo_headers(client)
    response = client.get(
        "/api/v1/folders/product-docs/documents/roadmap-draft",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_publish_creates_revision(client: TestClient) -> None:
    headers = demo_headers(client)
    published = client.post(
        "/api/v1/folders/product-docs/documents/roadmap-draft/publish",
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["version"] == 1

    revisions = client.get(
        "/api/v1/folders/product-docs/documents/roadmap-draft/revisions",
        headers=headers,
    )
    assert revisions.status_code == 200
    assert len(revisions.json()) == 1


def test_create_folder_and_document(client: TestClient) -> None:
    headers = demo_headers(client)
    folder = client.post(
        "/api/v1/folders",
        headers=headers,
        json={"name": "Legal", "slug": "legal"},
    )
    assert folder.status_code == 201

    doc = client.post(
        "/api/v1/folders/legal/documents",
        headers=headers,
        json={
            "title": "Privacy policy",
            "body": "We respect your data.",
            "tags": ["legal"],
        },
    )
    assert doc.status_code == 201
    assert doc.json()["status"] == "draft"
