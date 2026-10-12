from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_post, register_headers

SEED_PUBLISHED = "writing-apis-that-teach"
SEED_DRAFT = "draft-pagination-notes"


def test_public_list_hides_drafts(client: TestClient) -> None:
    listed = client.get("/api/v1/posts")
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["slug"] == SEED_PUBLISHED
    assert page["items"][0]["status"] == "published"
    assert page["items"][0]["comment_count"] == 1

    hidden = client.get("/api/v1/posts", params={"status": "draft", "tag": "pagination"})
    assert hidden.status_code == 200
    assert hidden.json()["items"] == []

    draft = client.get(f"/api/v1/posts/{SEED_DRAFT}")
    assert draft.status_code == 404
    assert draft.json()["detail"] == f"Post {SEED_DRAFT} not found"


def test_filters_combine_and_search_the_body(client: TestClient) -> None:
    by_tag = client.get("/api/v1/posts", params={"tag": "FastAPI"})
    assert [item["slug"] for item in by_tag.json()["items"]] == [SEED_PUBLISHED]

    by_author = client.get("/api/v1/posts", params={"author_id": 1, "q": "without a token"})
    assert [item["slug"] for item in by_author.json()["items"]] == [SEED_PUBLISHED]

    missed = client.get("/api/v1/posts", params={"q": "pagination"})
    assert missed.json()["total"] == 0


def test_pagination_reports_the_unpaged_total(client: TestClient) -> None:
    author = register_headers(client, "pager@example.com", full_name="Pager")
    for index in range(2):
        created = create_post(client, author, title=f"Page note {index}")
        published = client.post(f"/api/v1/posts/{created['slug']}/publish", headers=author)
        assert published.status_code == 200

    first = client.get("/api/v1/posts", params={"limit": 1, "offset": 0}).json()
    second = client.get("/api/v1/posts", params={"limit": 1, "offset": 1}).json()
    beyond = client.get("/api/v1/posts", params={"limit": 1, "offset": 20}).json()

    assert first["total"] == second["total"] == 3
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert beyond["items"] == []
    assert beyond["total"] == 3


def test_create_slug_rules(client: TestClient) -> None:
    author = register_headers(client, "author@example.com", full_name="Ada Author")
    created = create_post(client, author, title="Hello, World!")
    assert created["slug"] == "hello-world"
    assert created["status"] == "draft"
    assert created["author_name"] == "Ada Author"
    assert created["published_at"] is None
    assert created["tags"] == ["fastapi"]

    folded = create_post(
        client,
        author,
        title="Tag folding",
        tags=["FastAPI", "fastapi", "docs"],
    )
    assert folded["tags"] == ["fastapi", "docs"]

    custom = create_post(client, author, title="Hello, World!", slug="second-hello")
    assert custom["slug"] == "second-hello"

    duplicate = client.post(
        "/api/v1/posts",
        headers=author,
        json={"title": "Hello, World!", "body": "Again."},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Another post already uses this slug"

    symbols = client.post(
        "/api/v1/posts",
        headers=author,
        json={"title": "!!!", "body": "No letters."},
    )
    assert symbols.status_code == 422

    bad_tag = client.post(
        "/api/v1/posts",
        headers=author,
        json={"title": "Bad tag", "body": "Nope.", "tags": ["fast api"]},
    )
    assert bad_tag.status_code == 422


def test_draft_visibility(client: TestClient) -> None:
    author = register_headers(client, "writer@example.com", full_name="Writer")
    stranger = register_headers(client, "reader@example.com", full_name="Reader")
    created = create_post(client, author, title="Private draft")
    slug = created["slug"]

    own = client.get(f"/api/v1/posts/{slug}", headers=author)
    assert own.status_code == 200
    assert own.json()["status"] == "draft"

    hidden = client.get(f"/api/v1/posts/{slug}", headers=stranger)
    assert hidden.status_code == 404

    admin = client.get(f"/api/v1/posts/{slug}", headers=admin_headers(client))
    assert admin.status_code == 200

    mine = client.get("/api/v1/posts/mine", headers=author).json()
    assert [item["slug"] for item in mine["items"]] == [slug]

    admin_mine = client.get("/api/v1/posts/mine", headers=admin_headers(client)).json()
    assert slug not in [item["slug"] for item in admin_mine["items"]]
    assert SEED_DRAFT in [item["slug"] for item in admin_mine["items"]]


def test_publish_unpublish_archive_and_restore(client: TestClient) -> None:
    author = register_headers(client, "editor@example.com", full_name="Editor")
    created = create_post(client, author, title="Status walk")
    slug = created["slug"]

    too_soon = client.post(f"/api/v1/posts/{slug}/archive", headers=author)
    assert too_soon.status_code == 409
    assert "Only a published post can be archived" in too_soon.json()["detail"]

    published = client.post(f"/api/v1/posts/{slug}/publish", headers=author)
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None
    assert client.get(f"/api/v1/posts/{slug}").status_code == 200

    again = client.post(f"/api/v1/posts/{slug}/publish", headers=author)
    assert again.status_code == 409

    draft_again = client.post(f"/api/v1/posts/{slug}/unpublish", headers=author)
    assert draft_again.status_code == 200
    assert draft_again.json()["status"] == "draft"
    assert draft_again.json()["published_at"] is None
    assert client.get(f"/api/v1/posts/{slug}").status_code == 404

    client.post(f"/api/v1/posts/{slug}/publish", headers=author)
    archived = client.post(f"/api/v1/posts/{slug}/archive", headers=admin_headers(client))
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["published_at"] is not None
    assert client.get(f"/api/v1/posts/{slug}").status_code == 404

    restored = client.post(f"/api/v1/posts/{slug}/restore", headers=author)
    assert restored.status_code == 200
    assert restored.json()["status"] == "draft"
    assert restored.json()["published_at"] is None


def test_edit_and_delete_permissions(client: TestClient) -> None:
    author = register_headers(client, "owner@example.com", full_name="Owner")
    stranger = register_headers(client, "other@example.com", full_name="Other")
    created = create_post(client, author, title="Owned piece")
    slug = created["slug"]

    sneaky = client.patch(
        f"/api/v1/posts/{slug}",
        headers=stranger,
        json={"title": "Taken"},
    )
    assert sneaky.status_code == 404

    client.post(f"/api/v1/posts/{slug}/publish", headers=author)
    forbidden = client.patch(
        f"/api/v1/posts/{slug}",
        headers=stranger,
        json={"title": "Taken"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Only the author can edit this post"

    admin_edit = client.patch(
        f"/api/v1/posts/{slug}",
        headers=admin_headers(client),
        json={"body": "Rewritten by admin."},
    )
    assert admin_edit.status_code == 403

    still_draft = create_post(client, author, title="Unpublished notes")
    admin_publish = client.post(
        f"/api/v1/posts/{still_draft['slug']}/publish",
        headers=admin_headers(client),
    )
    assert admin_publish.status_code == 403
    assert admin_publish.json()["detail"] == "Only the author can publish this post"

    cannot_delete = client.delete(f"/api/v1/posts/{slug}", headers=stranger)
    assert cannot_delete.status_code == 403

    edited = client.patch(
        f"/api/v1/posts/{slug}",
        headers=author,
        json={"title": "Renamed", "tags": []},
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "Renamed"
    assert edited.json()["slug"] == slug
    assert edited.json()["tags"] == []

    removed = client.delete(f"/api/v1/posts/{slug}", headers=admin_headers(client))
    assert removed.status_code == 204
    assert client.get(f"/api/v1/posts/{slug}", headers=author).status_code == 404


def test_bad_token_is_not_anonymous(client: TestClient) -> None:
    ok = client.get(f"/api/v1/posts/{SEED_PUBLISHED}")
    assert ok.status_code == 200

    bad = client.get(
        f"/api/v1/posts/{SEED_PUBLISHED}",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert bad.status_code == 401


def test_tags_count_published_posts_only(client: TestClient) -> None:
    tags = client.get("/api/v1/tags")
    assert tags.status_code == 200
    counted = {item["name"]: item["post_count"] for item in tags.json()}
    assert counted == {"docs": 1, "fastapi": 1}

    author = register_headers(client, "tagger@example.com")
    created = create_post(client, author, title="Soon live", tags=["pagination"])
    still = {item["name"] for item in client.get("/api/v1/tags").json()}
    assert "pagination" not in still

    client.post(f"/api/v1/posts/{created['slug']}/publish", headers=author)
    after = {item["name"]: item["post_count"] for item in client.get("/api/v1/tags").json()}
    assert after["pagination"] == 1


def test_openapi_documents_visibility_and_publish(client: TestClient) -> None:
    root = client.get("/")
    assert "/docs" in root.json()["message"]

    schema = client.get("/openapi.json").json()
    description = schema["info"]["description"].lower()
    assert "draft" in description
    assert "404" in description

    read_one = schema["paths"]["/api/v1/posts/{slug}"]["get"]
    assert read_one["security"] == [{}, {"OAuth2PasswordBearer": []}]
    comments = schema["paths"]["/api/v1/posts/{slug}/comments"]["get"]
    assert comments["security"] == [{}, {"OAuth2PasswordBearer": []}]

    publish = schema["paths"]["/api/v1/posts/{slug}/publish"]["post"]
    assert "draft" in publish["description"]
    assert publish["summary"] == "Publish a draft"

    create = schema["paths"]["/api/v1/posts"]["post"]
    examples = create["requestBody"]["content"]["application/json"]["examples"]
    assert "from_title" in examples
    assert "custom_slug" in examples
