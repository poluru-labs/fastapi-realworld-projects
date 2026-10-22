from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class DeckRecord:
    id: int
    title: str
    description: str
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class CardRecord:
    id: int
    deck_id: int
    front: str
    back: str
    hint: str | None
    position: int


def _seed() -> tuple[dict[int, DeckRecord], dict[int, CardRecord]]:
    now = _utcnow()
    decks = {
        1: DeckRecord(
            id=1,
            title="Spanish basics",
            description="Everyday vocabulary for beginners.",
            created_at=now,
            updated_at=now,
        ),
        2: DeckRecord(
            id=2,
            title="HTTP verbs",
            description="Methods you see in REST APIs.",
            created_at=now,
            updated_at=now,
        ),
    }
    cards = {
        1: CardRecord(
            id=1,
            deck_id=1,
            front="Hola",
            back="Hello",
            hint="Greeting",
            position=1,
        ),
        2: CardRecord(
            id=2,
            deck_id=1,
            front="Gracias",
            back="Thank you",
            hint=None,
            position=2,
        ),
        3: CardRecord(
            id=3,
            deck_id=1,
            front="Adiós",
            back="Goodbye",
            hint=None,
            position=3,
        ),
        4: CardRecord(
            id=4,
            deck_id=2,
            front="GET",
            back="Read a resource without changing it.",
            hint="Safe and idempotent",
            position=1,
        ),
        5: CardRecord(
            id=5,
            deck_id=2,
            front="POST",
            back="Create a resource or submit data.",
            hint="Often returns 201 Created",
            position=2,
        ),
    }
    return decks, cards


class FlashcardRepository:
    """In-memory decks and cards. Restart restores seed data only."""

    def __init__(self) -> None:
        self._decks, self._cards = _seed()
        self._next_deck_id = max(self._decks.keys(), default=0) + 1
        self._next_card_id = max(self._cards.keys(), default=0) + 1

    def list_decks(self) -> list[DeckRecord]:
        rows = list(self._decks.values())
        rows.sort(key=lambda deck: (deck.title.casefold(), deck.id))
        return rows

    def get_deck(self, deck_id: int) -> DeckRecord | None:
        return self._decks.get(deck_id)

    def create_deck(self, *, title: str, description: str) -> DeckRecord:
        deck_id = self._next_deck_id
        self._next_deck_id += 1
        record = DeckRecord(id=deck_id, title=title, description=description)
        self._decks[deck_id] = record
        return record

    def update_deck(
        self,
        deck_id: int,
        *,
        title: str | None,
        description: str | None,
    ) -> DeckRecord | None:
        record = self._decks.get(deck_id)
        if record is None:
            return None
        if title is not None:
            record.title = title
        if description is not None:
            record.description = description
        record.updated_at = _utcnow()
        return record

    def delete_deck(self, deck_id: int) -> DeckRecord | None:
        record = self._decks.pop(deck_id, None)
        if record is None:
            return None
        to_remove = [card_id for card_id, card in self._cards.items() if card.deck_id == deck_id]
        for card_id in to_remove:
            del self._cards[card_id]
        return record

    def list_cards(self, deck_id: int) -> list[CardRecord]:
        if deck_id not in self._decks:
            return []
        rows = [card for card in self._cards.values() if card.deck_id == deck_id]
        rows.sort(key=lambda card: card.position)
        return rows

    def get_card(self, card_id: int) -> CardRecord | None:
        return self._cards.get(card_id)

    def add_card(
        self,
        deck_id: int,
        *,
        front: str,
        back: str,
        hint: str | None,
    ) -> CardRecord | None:
        if deck_id not in self._decks:
            return None
        position = len(self.list_cards(deck_id)) + 1
        card_id = self._next_card_id
        self._next_card_id += 1
        record = CardRecord(
            id=card_id,
            deck_id=deck_id,
            front=front,
            back=back,
            hint=hint,
            position=position,
        )
        self._cards[card_id] = record
        self._decks[deck_id].updated_at = _utcnow()
        return record

    def update_card(
        self,
        card_id: int,
        *,
        front: str | None,
        back: str | None,
        hint: str | None,
    ) -> CardRecord | None:
        record = self._cards.get(card_id)
        if record is None:
            return None
        if front is not None:
            record.front = front
        if back is not None:
            record.back = back
        if hint is not None:
            record.hint = hint.strip() or None
        self._decks[record.deck_id].updated_at = _utcnow()
        return record

    def delete_card(self, card_id: int) -> CardRecord | None:
        record = self._cards.pop(card_id, None)
        if record is None:
            return None
        remaining = self.list_cards(record.deck_id)
        for index, card in enumerate(remaining, start=1):
            card.position = index
        self._decks[record.deck_id].updated_at = _utcnow()
        return record

    def card_count(self, deck_id: int) -> int:
        return len(self.list_cards(deck_id))


@lru_cache
def get_flashcard_repository() -> FlashcardRepository:
    return FlashcardRepository()
