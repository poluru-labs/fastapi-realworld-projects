from fastapi.testclient import TestClient


def test_list_filter_and_get(client: TestClient) -> None:
    all_links = client.get("/api/v1/links")
    assert all_links.status_code == 200
    assert len(all_links.json()) == 3

    active = client.get("/api/v1/links", params={"is_active": "true"})
    assert len(active.json()) == 2

    docs = client.get("/api/v1/links/docs")
    assert docs.status_code == 200
    assert docs.json()["click_count"] == 12
    assert docs.json()["redirect_path"] == "/api/v1/r/docs"


def test_create_and_duplicate_code(client: TestClient) -> None:
    created = client.post(
        "/api/v1/links",
        json={
            "target_url": "https://example.com/blog",
            "title": "Blog",
            "custom_code": "blog",
        },
    )
    assert created.status_code == 201
    assert created.json()["code"] == "blog"

    dup = client.post(
        "/api/v1/links",
        json={
            "target_url": "https://example.com/other",
            "custom_code": "docs",
        },
    )
    assert dup.status_code == 409


def test_redirect_and_click_count(client: TestClient) -> None:
    before = client.get("/api/v1/links/github").json()["click_count"]
    response = client.get("/api/v1/r/github", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://github.com/tiangolo/fastapi"
    after = client.get("/api/v1/links/github").json()["click_count"]
    assert after == before + 1


def test_inactive_link_returns_gone(client: TestClient) -> None:
    assert client.get("/api/v1/r/old-sale", follow_redirects=False).status_code == 410


def test_deactivate_via_patch(client: TestClient) -> None:
    updated = client.patch(
        "/api/v1/links/github",
        json={"is_active": False},
    )
    assert updated.status_code == 200
    assert client.get("/api/v1/r/github", follow_redirects=False).status_code == 410


def test_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/links/missing").status_code == 404
