from app.core.exceptions import NotFoundError
from app.repositories.flashcard_repository import FlashcardRepository
from app.schemas.flashcard import (
    CardCreate,
    CardFrontRead,
    CardRead,
    CardUpdate,
    DeckCreate,
    DeckDetail,
    DeckRead,
    DeckUpdate,
    StudySession,
)


class FlashcardService:
    def __init__(self, repository: FlashcardRepository) -> None:
        self._repo = repository

    def list_decks(self) -> list[DeckRead]:
        return [self._deck_read(deck) for deck in self._repo.list_decks()]

    def get_deck_detail(self, deck_id: int) -> DeckDetail:
        deck = self._require_deck(deck_id)
        cards = self._repo.list_cards(deck_id)
        return DeckDetail(
            **self._deck_read(deck).model_dump(),
            cards=[self._card_read(card) for card in cards],
        )

    def create_deck(self, payload: DeckCreate) -> DeckRead:
        record = self._repo.create_deck(title=payload.title, description=payload.description)
        return self._deck_read(record)

    def update_deck(self, deck_id: int, payload: DeckUpdate) -> DeckRead:
        fields = payload.model_dump(exclude_unset=True)
        record = self._repo.update_deck(
            deck_id,
            title=fields.get("title"),
            description=fields.get("description"),
        )
        if record is None:
            raise NotFoundError("Deck", deck_id)
        return self._deck_read(record)

    def delete_deck(self, deck_id: int) -> None:
        if self._repo.delete_deck(deck_id) is None:
            raise NotFoundError("Deck", deck_id)

    def study_session(self, deck_id: int) -> StudySession:
        deck = self._require_deck(deck_id)
        cards = self._repo.list_cards(deck_id)
        return StudySession(
            deck_id=deck.id,
            title=deck.title,
            cards=[self._card_front_read(card) for card in cards],
        )

    def list_cards(self, deck_id: int) -> list[CardRead]:
        self._require_deck(deck_id)
        return [self._card_read(card) for card in self._repo.list_cards(deck_id)]

    def add_card(self, deck_id: int, payload: CardCreate) -> CardRead:
        self._require_deck(deck_id)
        record = self._repo.add_card(
            deck_id,
            front=payload.front,
            back=payload.back,
            hint=payload.hint,
        )
        if record is None:
            raise NotFoundError("Deck", deck_id)
        return self._card_read(record)

    def get_card(self, card_id: int) -> CardRead:
        return self._card_read(self._require_card(card_id))

    def update_card(self, card_id: int, payload: CardUpdate) -> CardRead:
        fields = payload.model_dump(exclude_unset=True)
        record = self._repo.update_card(
            card_id,
            front=fields.get("front"),
            back=fields.get("back"),
            hint=fields.get("hint"),
        )
        if record is None:
            raise NotFoundError("Card", card_id)
        return self._card_read(record)

    def delete_card(self, card_id: int) -> None:
        if self._repo.delete_card(card_id) is None:
            raise NotFoundError("Card", card_id)

    def _require_deck(self, deck_id: int):
        deck = self._repo.get_deck(deck_id)
        if deck is None:
            raise NotFoundError("Deck", deck_id)
        return deck

    def _require_card(self, card_id: int):
        card = self._repo.get_card(card_id)
        if card is None:
            raise NotFoundError("Card", card_id)
        return card

    def _deck_read(self, deck) -> DeckRead:
        return DeckRead(
            id=deck.id,
            title=deck.title,
            description=deck.description,
            card_count=self._repo.card_count(deck.id),
            created_at=deck.created_at,
            updated_at=deck.updated_at,
        )

    @staticmethod
    def _card_read(card) -> CardRead:
        return CardRead(
            id=card.id,
            deck_id=card.deck_id,
            front=card.front,
            back=card.back,
            hint=card.hint,
            position=card.position,
        )

    @staticmethod
    def _card_front_read(card) -> CardFrontRead:
        return CardFrontRead(
            id=card.id,
            deck_id=card.deck_id,
            front=card.front,
            hint=card.hint,
            position=card.position,
        )
