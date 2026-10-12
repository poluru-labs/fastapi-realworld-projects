from fastapi.testclient import TestClient


def test_list_seed_recipes(client: TestClient) -> None:
    response = client.get("/api/v1/recipes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["title"] == "Weeknight Pasta"
    assert data[0]["featured"] is True


def test_list_cuisines(client: TestClient) -> None:
    response = client.get("/api/v1/recipes/cuisines")
    assert response.status_code == 200
    assert response.json() == ["American", "Italian"]


def test_search_and_filters(client: TestClient) -> None:
    veg = client.get("/api/v1/recipes", params={"vegetarian": True})
    assert len(veg.json()) == 2

    quick = client.get("/api/v1/recipes", params={"max_total_minutes": 30})
    assert len(quick.json()) == 1
    assert quick.json()[0]["title"] == "Weeknight Pasta"


def test_get_recipe_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/recipes/999")
    assert response.status_code == 404


def test_create_and_duplicate_source_url(client: TestClient) -> None:
    created = client.post(
        "/api/v1/recipes",
        json={
            "title": "New Dish",
            "chef": "Chef Test",
            "source_url": "https://example.com/new",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == 4
    assert created.json()["total_minutes"] is None

    conflict = client.post(
        "/api/v1/recipes",
        json={
            "title": "Other",
            "chef": "Other",
            "source_url": "https://example.com/new/",
        },
    )
    assert conflict.status_code == 409


def test_feature_and_delete(client: TestClient) -> None:
    response = client.post("/api/v1/recipes/2/feature")
    assert response.status_code == 200
    assert response.json()["featured"] is True

    deleted = client.delete("/api/v1/recipes/3")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
