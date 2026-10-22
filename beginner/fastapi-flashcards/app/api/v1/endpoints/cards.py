from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_flashcard_service
from app.schemas.flashcard import CardRead, CardUpdate
from app.services.flashcard_service import FlashcardService

router = APIRouter()


@router.get(
    "/{card_id}",
    response_model=CardRead,
    summary="Reveal a card (flip)",
    description="Full front and **back** — use after the learner checks their guess.",
)
def get_card(
    card_id: int,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> CardRead:
    return service.get_card(card_id)


@router.patch(
    "/{card_id}",
    response_model=CardRead,
    summary="Edit a card",
)
def update_card(
    card_id: int,
    payload: CardUpdate,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> CardRead:
    return service.update_card(card_id, payload)


@router.delete(
    "/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a card",
)
def delete_card(
    card_id: int,
    service: Annotated[FlashcardService, Depends(get_flashcard_service)],
) -> None:
    service.delete_card(card_id)
