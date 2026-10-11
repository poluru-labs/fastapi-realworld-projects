from fastapi.testclient import TestClient


def test_list_seed_movies(client: TestClient) -> None:
    response = client.get("/api/v1/movies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["title"] == "Inception"
    assert data[0]["pinned"] is True


def test_list_genres(client: TestClient) -> None:
    response = client.get("/api/v1/movies/genres")
    assert response.status_code == 200
    assert response.json() == ["Animation", "Drama", "Science Fiction"]


def test_search_and_status_filter(client: TestClient) -> None:
    by_status = client.get("/api/v1/movies", params={"status": "watched"})
    assert len(by_status.json()) == 1
    assert by_status.json()[0]["title"] == "Spirited Away"

    search = client.get("/api/v1/movies", params={"search": "nolan"})
    assert len(search.json()) == 1
    assert search.json()[0]["director"] == "Christopher Nolan"


def test_get_movie_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/movies/999")
    assert response.status_code == 404


def test_create_and_duplicate_imdb_id(client: TestClient) -> None:
    created = client.post(
        "/api/v1/movies",
        json={
            "title": "New Film",
            "director": "New Director",
            "imdb_id": "tt0000001",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == 4

    conflict = client.post(
        "/api/v1/movies",
        json={
            "title": "Other",
            "director": "Other",
            "imdb_id": "TT0000001",
        },
    )
    assert conflict.status_code == 409


def test_pin_and_mark_watched(client: TestClient) -> None:
    response = client.post("/api/v1/movies/2/pin")
    assert response.status_code == 200
    assert response.json()["pinned"] is True

    watched = client.post("/api/v1/movies/2/mark-watched")
    assert watched.status_code == 200
    assert watched.json()["status"] == "watched"


def test_delete_movie(client: TestClient) -> None:
    response = client.delete("/api/v1/movies/3")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
