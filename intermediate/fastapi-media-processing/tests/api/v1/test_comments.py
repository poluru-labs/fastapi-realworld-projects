from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_post, register_headers

SEED_PUBLISHED = "writing-apis-that-teach"
SEED_DRAFT = "draft-pagination-notes"


def test_comments_follow_publish_state(client: TestClient) -> None:
    author = register_headers(client, "commenter@example.com", full_name="Commenter")
    stranger = register_headers(client, "lurker@example.com", full_name="Lurker")
    created = create_post(client, author, title="Comment target")
    slug = created["slug"]

    on_draft = client.post(
        f"/api/v1/posts/{slug}/comments",
        headers=author,
        json={"body": "Too early."},
    )
    assert on_draft.status_code == 409
    assert on_draft.json()["detail"] == "Only published posts accept comments"

    hidden = client.post(
        f"/api/v1/posts/{slug}/comments",
        headers=stranger,
        json={"body": "Cannot see this."},
    )
    assert hidden.status_code == 404

    missing_token = client.post(
        f"/api/v1/posts/{SEED_PUBLISHED}/comments",
        json={"body": "Hello."},
    )
    assert missing_token.status_code == 401

    client.post(f"/api/v1/posts/{slug}/publish", headers=author)
    created_comment = client.post(
        f"/api/v1/posts/{slug}/comments",
        headers=stranger,
        json={"body": "  Now it is public.  "},
    )
    assert created_comment.status_code == 201
    body = created_comment.json()
    assert body["body"] == "Now it is public."
    assert body["author_name"] == "Lurker"

    listed = client.get(f"/api/v1/posts/{slug}/comments")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == body["id"]

    post = client.get(f"/api/v1/posts/{slug}").json()
    assert post["comment_count"] == 1


def test_who_can_delete_a_comment(client: TestClient) -> None:
    author = register_headers(client, "poster@example.com", full_name="Poster")
    commenter = register_headers(client, "fan@example.com", full_name="Fan")
    stranger = register_headers(client, "passer@example.com", full_name="Passer")
    created = create_post(client, author, title="Moderation")
    slug = created["slug"]
    client.post(f"/api/v1/posts/{slug}/publish", headers=author)

    first = client.post(
        f"/api/v1/posts/{slug}/comments",
        headers=commenter,
        json={"body": "First."},
    ).json()
    second = client.post(
        f"/api/v1/posts/{slug}/comments",
        headers=commenter,
        json={"body": "Second."},
    ).json()
    third = client.post(
        f"/api/v1/posts/{slug}/comments",
        headers=author,
        json={"body": "Third."},
    ).json()

    denied = client.delete(
        f"/api/v1/posts/{slug}/comments/{first['id']}",
        headers=stranger,
    )
    assert denied.status_code == 403

    by_commenter = client.delete(
        f"/api/v1/posts/{slug}/comments/{first['id']}",
        headers=commenter,
    )
    assert by_commenter.status_code == 204

    by_post_author = client.delete(
        f"/api/v1/posts/{slug}/comments/{second['id']}",
        headers=author,
    )
    assert by_post_author.status_code == 204

    by_admin = client.delete(
        f"/api/v1/posts/{slug}/comments/{third['id']}",
        headers=admin_headers(client),
    )
    assert by_admin.status_code == 204
    assert client.get(f"/api/v1/posts/{slug}/comments").json()["total"] == 0


def test_comment_must_belong_to_the_post_in_the_path(client: TestClient) -> None:
    seed_comments = client.get(f"/api/v1/posts/{SEED_PUBLISHED}/comments").json()
    seed_comment_id = seed_comments["items"][0]["id"]

    author = register_headers(client, "otherpost@example.com")
    created = create_post(client, author, title="Different post")
    client.post(f"/api/v1/posts/{created['slug']}/publish", headers=author)

    missing = client.delete(
        f"/api/v1/posts/{created['slug']}/comments/{seed_comment_id}",
        headers=author,
    )
    assert missing.status_code == 404

    draft_list = client.get(f"/api/v1/posts/{SEED_DRAFT}/comments")
    assert draft_list.status_code == 404
    admin_list = client.get(
        f"/api/v1/posts/{SEED_DRAFT}/comments",
        headers=admin_headers(client),
    )
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 0


def test_deleting_a_post_deletes_its_comments(client: TestClient) -> None:
    author = register_headers(client, "cleaner@example.com")
    created = create_post(client, author, title="Temporary")
    slug = created["slug"]
    client.post(f"/api/v1/posts/{slug}/publish", headers=author)
    comment = client.post(
        f"/api/v1/posts/{slug}/comments",
        headers=author,
        json={"body": "Gone with the post."},
    ).json()

    removed = client.delete(f"/api/v1/posts/{slug}", headers=author)
    assert removed.status_code == 204

    leftover = client.delete(
        f"/api/v1/posts/{slug}/comments/{comment['id']}",
        headers=author,
    )
    assert leftover.status_code == 404
