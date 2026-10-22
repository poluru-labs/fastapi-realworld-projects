from fastapi.testclient import TestClient

SPANISH_DECK = 1


def test_list_seed_decks(client: TestClient) -> None:
    response = client.get("/api/v1/decks")
    assert response.status_code == 200
    decks = response.json()
    assert len(decks) == 2
    spanish = next(d for d in decks if d["id"] == SPANISH_DECK)
    assert spanish["card_count"] == 3


def test_study_hides_back_and_flip_reveals(client: TestClient) -> None:
    study = client.get(f"/api/v1/decks/{SPANISH_DECK}/study")
    assert study.status_code == 200
    cards = study.json()["cards"]
    assert len(cards) == 3
    assert "back" not in cards[0]

    flip = client.get(f"/api/v1/cards/{cards[0]['id']}")
    assert flip.status_code == 200
    assert flip.json()["back"] == "Hello"


def test_create_deck_and_card(client: TestClient) -> None:
    deck = client.post(
        "/api/v1/decks",
        json={"title": "Colors", "description": "Basic colors"},
    )
    assert deck.status_code == 201
    deck_id = deck.json()["id"]

    card = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "Red", "back": "Rojo"},
    )
    assert card.status_code == 201
    assert card.json()["position"] == 1


def test_delete_deck_removes_cards(client: TestClient) -> None:
    deck = client.post("/api/v1/decks", json={"title": "Temp", "description": ""})
    deck_id = deck.json()["id"]
    created = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "A", "back": "B"},
    )
    card_id = created.json()["id"]

    assert client.delete(f"/api/v1/decks/{deck_id}").status_code == 204
    assert client.get(f"/api/v1/cards/{card_id}").status_code == 404


def test_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/decks/999").status_code == 404
