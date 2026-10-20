from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_quiz_service
from app.schemas.quiz import QuestionAuthorRead, QuestionUpdate
from app.services.quiz_service import QuizService

router = APIRouter()


@router.patch(
    "/{question_id}",
    response_model=QuestionAuthorRead,
    summary="Edit a question",
    responses={409: {"description": "Quiz is not a draft."}},
)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuestionAuthorRead:
    return service.update_question(question_id, payload)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question",
)
def delete_question(
    question_id: int,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> None:
    service.delete_question(question_id)
