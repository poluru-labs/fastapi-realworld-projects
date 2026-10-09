from fastapi.testclient import TestClient


def test_root_and_health(client: TestClient) -> None:
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["message"] == "Contact Book API — see /docs for OpenAPI"
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_list_seed_favorites_first(client: TestClient) -> None:
    response = client.get("/api/v1/contacts")
    assert response.status_code == 200
    names = [contact["full_name"] for contact in response.json()]
    assert names == ["Ada Lovelace", "Grace Hopper", "Lin Phone-only"]
    assert response.json()[0]["favorite"] is True


def test_search_and_favorite_filter(client: TestClient) -> None:
    by_company = client.get("/api/v1/contacts", params={"search": "compilers"})
    assert [c["full_name"] for c in by_company.json()] == ["Grace Hopper"]

    phone_only = client.get("/api/v1/contacts", params={"search": "555-0199"})
    assert phone_only.json()[0]["email"] is None

    favorites = client.get("/api/v1/contacts", params={"favorite": True})
    assert [c["id"] for c in favorites.json()] == [1]

    blank = client.get("/api/v1/contacts", params={"search": "   "})
    assert len(blank.json()) == 3


def test_create_and_duplicate_email(client: TestClient) -> None:
    created = client.post(
        "/api/v1/contacts",
        json={
            "full_name": "  Sam Rivera  ",
            "email": "sam@example.com",
            "phone": " 555 ",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 4
    assert body["full_name"] == "Sam Rivera"
    assert body["phone"] == "555"

    duplicate = client.post(
        "/api/v1/contacts",
        json={"full_name": "Copy", "email": "SAM@example.com"},
    )
    assert duplicate.status_code == 409

    no_email = client.post(
        "/api/v1/contacts",
        json={"full_name": "Lobby", "phone": "+1"},
    )
    assert no_email.status_code == 201
    assert no_email.json()["email"] is None


def test_patch_clear_email_and_conflict(client: TestClient) -> None:
    patched = client.patch("/api/v1/contacts/2", json={"company": "Navy"})
    assert patched.json()["company"] == "Navy"
    assert patched.json()["full_name"] == "Grace Hopper"

    steal = client.patch("/api/v1/contacts/3", json={"email": "ada@example.com"})
    assert steal.status_code == 409

    cleared = client.patch("/api/v1/contacts/2", json={"email": ""})
    assert cleared.json()["email"] is None


def test_favorite_unfavorite_and_delete(client: TestClient) -> None:
    fav = client.post("/api/v1/contacts/2/favorite")
    assert fav.json()["favorite"] is True
    again = client.post("/api/v1/contacts/2/favorite")
    assert again.json()["favorite"] is True

    order = [c["id"] for c in client.get("/api/v1/contacts").json()]
    assert order[:2] == [1, 2]

    unfav = client.post("/api/v1/contacts/1/unfavorite")
    assert unfav.json()["favorite"] is False

    deleted = client.delete("/api/v1/contacts/3")
    assert deleted.json()["deleted"] is True
    assert deleted.json()["contact"]["full_name"] == "Lin Phone-only"
    assert client.get("/api/v1/contacts/3").status_code == 404


def test_invalid_email_and_blank_name(client: TestClient) -> None:
    bad_email = client.post(
        "/api/v1/contacts",
        json={"full_name": "X", "email": "not-an-email"},
    )
    assert bad_email.status_code == 422
    assert client.post("/api/v1/contacts", json={"full_name": "   "}).status_code == 422


def test_openapi_describes_contacts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Contact Book API"
    assert "favorite" in spec["info"]["description"]
    assert "/api/v1/contacts/{contact_id}/favorite" in spec["paths"]
    create_path = spec["paths"]["/api/v1/contacts"]["post"]
    examples = create_path["requestBody"]["content"]["application/json"]
    assert "phone_only" in examples["examples"]
