from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_post, register_headers

SEED_PUBLISHED = "writing-apis-that-teach"


def test_followers_only_post_hidden_from_explore_and_strangers(client: TestClient) -> None:
    author = admin_headers(client)
    created = create_post(
        client,
        author,
        title="Inner circle update",
        visibility="followers",
    )
    published = client.post(f"/api/v1/posts/{created['slug']}/publish", headers=author)
    assert published.status_code == 200

    explore = client.get("/api/v1/posts")
    assert all(item["slug"] != created["slug"] for item in explore.json()["items"])

    stranger = register_headers(client, "stranger@example.com")
    hidden = client.get(f"/api/v1/posts/{created['slug']}", headers=stranger)
    assert hidden.status_code == 404

    follow = client.post("/api/v1/users/1/follow", headers=stranger)
    assert follow.status_code == 200
    visible = client.get(f"/api/v1/posts/{created['slug']}", headers=stranger)
    assert visible.status_code == 200
    assert visible.json()["visibility"] == "followers"


def test_home_feed_includes_followed_authors(client: TestClient) -> None:
    poster = register_headers(client, "poster@example.com", full_name="Poster")
    created = create_post(client, poster, title="Feed item alpha")
    slug = created["slug"]
    assert client.post(f"/api/v1/posts/{slug}/publish", headers=poster).status_code == 200

    reader = register_headers(client, "reader@example.com")
    assert client.post("/api/v1/users/2/follow", headers=reader).status_code == 200

    feed = client.get("/api/v1/feed", headers=reader)
    assert feed.status_code == 200
    slugs = [item["slug"] for item in feed.json()["items"]]
    assert slug in slugs
    assert SEED_PUBLISHED not in slugs


def test_like_and_unlike(client: TestClient) -> None:
    fan = register_headers(client, "fan@example.com")
    liked = client.post(f"/api/v1/posts/{SEED_PUBLISHED}/like", headers=fan)
    assert liked.status_code == 200
    body = liked.json()
    assert body["like_count"] == 1
    assert body["liked_by_me"] is True

    again = client.post(f"/api/v1/posts/{SEED_PUBLISHED}/like", headers=fan)
    assert again.status_code == 409

    unliked = client.delete(f"/api/v1/posts/{SEED_PUBLISHED}/like", headers=fan)
    assert unliked.status_code == 200
    assert unliked.json()["like_count"] == 0
    assert unliked.json()["liked_by_me"] is False
