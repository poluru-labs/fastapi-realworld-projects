from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers

SEED_DRAFT = "draft-seasonal-soup"


def test_public_menu_hides_drafts_and_sold_out(client: TestClient) -> None:
    menu = client.get("/api/v1/menu")
    assert menu.status_code == 200
    slugs = {row["slug"] for row in menu.json()}
    assert slugs == {"classic-burger", "fries"}
    assert client.get(f"/api/v1/menu/{SEED_DRAFT}").status_code == 404

    admin = admin_headers(client)
    assert client.get(f"/api/v1/menu/{SEED_DRAFT}", headers=admin).status_code == 200

    sold = client.post("/api/v1/menu/fries/sold-out", headers=admin)
    assert sold.status_code == 200
    assert client.get("/api/v1/menu/fries").status_code == 404

    client.post("/api/v1/menu/fries/restock", headers=admin)


def test_admin_creates_and_activates_menu_item(client: TestClient) -> None:
    admin = admin_headers(client)
    created = client.post(
        "/api/v1/menu",
        headers=admin,
        json={
            "name": "Iced Tea",
            "description": "House brewed.",
            "price_cents": 299,
            "category": "Drinks",
        },
    )
    assert created.status_code == 201
    slug = created.json()["slug"]
    assert created.json()["status"] == "draft"
    assert client.get(f"/api/v1/menu/{slug}").status_code == 404

    activated = client.post(f"/api/v1/menu/{slug}/activate", headers=admin)
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    assert client.get(f"/api/v1/menu/{slug}").json()["slug"] == slug


def test_non_admin_cannot_manage_menu(client: TestClient) -> None:
    user = register_headers(client, "guest@example.com")
    response = client.post(
        "/api/v1/menu",
        headers=user,
        json={
            "name": "Secret special",
            "description": "Nope",
            "price_cents": 100,
            "category": "Mains",
        },
    )
    assert response.status_code == 403
