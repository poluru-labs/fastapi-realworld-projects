from fastapi.testclient import TestClient


def test_list_seed_books(client: TestClient) -> None:
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["title"] == "The Pragmatic Programmer"
    assert data[0]["featured"] is True


def test_list_genres(client: TestClient) -> None:
    response = client.get("/api/v1/books/genres")
    assert response.status_code == 200
    assert response.json() == ["Science Fiction", "Software"]


def test_search_and_genre_filter(client: TestClient) -> None:
    by_genre = client.get("/api/v1/books", params={"genre": "Software"})
    assert len(by_genre.json()) == 2

    search = client.get("/api/v1/books", params={"search": "dune"})
    assert len(search.json()) == 1
    assert search.json()[0]["author"] == "Frank Herbert"


def test_get_book_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/books/999")
    assert response.status_code == 404


def test_create_and_duplicate_isbn(client: TestClient) -> None:
    created = client.post(
        "/api/v1/books",
        json={
            "title": "New Title",
            "author": "New Author",
            "isbn": "978-0000000001",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == 4

    conflict = client.post(
        "/api/v1/books",
        json={
            "title": "Other",
            "author": "Other",
            "isbn": "9780000000001",
        },
    )
    assert conflict.status_code == 409


def test_feature_and_available_filter(client: TestClient) -> None:
    response = client.post("/api/v1/books/2/feature")
    assert response.status_code == 200
    assert response.json()["featured"] is True

    unavailable = client.get("/api/v1/books", params={"available": False})
    assert len(unavailable.json()) == 1


def test_delete_book(client: TestClient) -> None:
    response = client.delete("/api/v1/books/3")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
