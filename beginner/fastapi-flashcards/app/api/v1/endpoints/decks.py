from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_flashcard_service
from app.schemas.flashcard import (
    CardCreate,
    CardRead,
    DeckCreate,
    DeckDetail,
    DeckRead,
    DeckUpdate,
    StudySession,
)
from app.services.flashcard_service import FlashcardService

router = APIRouter()


@router.get(
    "",
    response_model=list[DeckRead],
    summary="List decks",
    description="All decks with live `card_count`, sorted by title.",
)
def list_decks(
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> list[DeckRead]:
    return service.list_decks()


@router.post(
    "",
    response_model=DeckRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a deck",
)
def create_deck(
    payload: DeckCreate,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> DeckRead:
    return service.create_deck(payload)


@router.get(
    "/{deck_id}",
    response_model=DeckDetail,
    summary="Deck with all cards",
    description="Authoring view — includes every card's **back** text.",
)
def get_deck(
    deck_id: int,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> DeckDetail:
    return service.get_deck_detail(deck_id)


@router.patch(
    "/{deck_id}",
    response_model=DeckRead,
    summary="Update deck metadata",
)
def update_deck(
    deck_id: int,
    payload: DeckUpdate,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> DeckRead:
    return service.update_deck(deck_id, payload)


@router.delete(
    "/{deck_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deck",
    description="Removes the deck and all of its cards.",
)
def delete_deck(
    deck_id: int,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> None:
    service.delete_deck(deck_id)


@router.get(
    "/{deck_id}/study",
    response_model=StudySession,
    summary="Study session (front side only)",
    description=(
        "Returns prompts without **back** text so a client can flip to "
        "`GET /api/v1/cards/{id}` when the learner reveals the answer."
    ),
)
def study_deck(
    deck_id: int,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> StudySession:
    return service.study_session(deck_id)


@router.get(
    "/{deck_id}/cards",
    response_model=list[CardRead],
    summary="List cards in a deck",
)
def list_cards_in_deck(
    deck_id: int,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> list[CardRead]:
    return service.list_cards(deck_id)


@router.post(
    "/{deck_id}/cards",
    response_model=CardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a card",
    description="Appends at the next position in the deck.",
)
def add_card(
    deck_id: int,
    payload: CardCreate,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> CardRead:
    return service.add_card(deck_id, payload)
