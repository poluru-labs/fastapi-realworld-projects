from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_quiz_service
from app.schemas.quiz import (
    QuestionAuthorRead,
    QuestionCreate,
    QuizAuthorDetail,
    QuizCreate,
    QuizPlayerDetail,
    QuizRead,
    QuizStatus,
    QuizSubmit,
    QuizSubmitResult,
    QuizUpdate,
)
from app.services.quiz_service import QuizService

router = APIRouter()


@router.get(
    "",
    response_model=list[QuizRead],
    summary="List quizzes",
    description=(
        "Defaults to **published** quizzes for takers. Pass `status=draft` to see work in progress."
    ),
)
def list_quizzes(
    service: Annotated[QuizService, Depends(get_quiz_service)],
    quiz_status: Annotated[
        QuizStatus | None,
        Query(alias="status", description="Filter by status. Omit to list published only."),
    ] = None,
) -> list[QuizRead]:
    effective = quiz_status if quiz_status is not None else QuizStatus.PUBLISHED
    return service.list_quizzes(status=effective)


@router.post(
    "",
    response_model=QuizRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft quiz",
)
def create_quiz(
    payload: QuizCreate,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizRead:
    return service.create_quiz(payload)


@router.get(
    "/{quiz_id}",
    response_model=QuizAuthorDetail,
    summary="Author view with answer key",
    description="Includes `correct_index` for each question. Works for any status.",
)
def get_quiz_author(
    quiz_id: int,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizAuthorDetail:
    return service.get_quiz_for_author(quiz_id)


@router.get(
    "/{quiz_id}/play",
    response_model=QuizPlayerDetail,
    summary="Take a published quiz",
    description="Hides correct answers. Draft and archived quizzes return **404**.",
    responses={404: {"description": "Quiz is not published."}},
)
def get_quiz_player(
    quiz_id: int,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizPlayerDetail:
    return service.get_quiz_for_player(quiz_id)


@router.patch(
    "/{quiz_id}",
    response_model=QuizRead,
    summary="Update quiz metadata",
)
def update_quiz(
    quiz_id: int,
    payload: QuizUpdate,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizRead:
    return service.update_quiz(quiz_id, payload)


@router.post(
    "/{quiz_id}/publish",
    response_model=QuizRead,
    summary="Publish a draft",
    responses={409: {"description": "Not a draft or no questions yet."}},
)
def publish_quiz(
    quiz_id: int,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizRead:
    return service.publish(quiz_id)


@router.post(
    "/{quiz_id}/unpublish",
    response_model=QuizRead,
    summary="Return a published quiz to draft",
)
def unpublish_quiz(
    quiz_id: int,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizRead:
    return service.unpublish(quiz_id)


@router.post(
    "/{quiz_id}/archive",
    response_model=QuizRead,
    summary="Archive a published quiz",
)
def archive_quiz(
    quiz_id: int,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizRead:
    return service.archive(quiz_id)


@router.post(
    "/{quiz_id}/restore",
    response_model=QuizRead,
    summary="Restore an archived quiz to draft",
)
def restore_quiz(
    quiz_id: int,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizRead:
    return service.restore(quiz_id)


@router.post(
    "/{quiz_id}/submit",
    response_model=QuizSubmitResult,
    summary="Submit answers and score the attempt",
    description=(
        "Published quizzes only. Send one answer per question you want graded; "
        "unanswered questions count as incorrect in the score denominator."
    ),
    responses={409: {"description": "Quiz is not published or answers are invalid."}},
)
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmit,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuizSubmitResult:
    return service.submit(quiz_id, payload)


@router.post(
    "/{quiz_id}/questions",
    response_model=QuestionAuthorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a question",
    description="Draft quizzes only. Positions are assigned automatically.",
    responses={409: {"description": "Quiz is not a draft."}},
)
def add_question(
    quiz_id: int,
    payload: QuestionCreate,
    service: Annotated[QuizService, Depends(get_quiz_service)],
) -> QuestionAuthorRead:
    return service.add_question(quiz_id, payload)
